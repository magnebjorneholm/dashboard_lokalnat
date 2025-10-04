"""
Beräknar geografisk grannsnittseffektivitet och effektivitetsgap (eff_gap) med valbar metod.

Modellspecifikation:
- Relativ effektivitet definieras som skillnaden mellan ett företags effektivitet 
  och medeleffektiviteten bland geografiska grannar.
- Två metoder stöds:
    - KNN: närmaste k grannar baserat på centroidavstånd.
    - DistanceBand: alla grannar inom angivet avstånd (t.ex. 50 km).

Viktigt: GeoDataFrame måste vara i EPSG:3006 (SWEREF99 TM) för korrekta meteravstånd.
"""

import geopandas as gpd
import numpy as np
from libpysal.weights import KNN, DistanceBand
from typing import Literal

REQUIRED_CRS = 3006  # SWEREF99 TM


def validate_spatial_inputs(gdf: gpd.GeoDataFrame, method: str, k: int = None, indikator: str = None):
    """
    Validerar att GeoDataFrame är lämplig för spatial analys.
    
    Args:
        gdf: GeoDataFrame att validera
        method: 'knn' eller 'distanceband'
        k: Antal grannar (om method='knn')
        indikator: Kolumnnamn för värde att jämföra
    
    Raises:
        TypeError: Om input inte är GeoDataFrame
        ValueError: Om CRS saknas, är fel, dataset är för litet, eller indikator saknas
    """
    if not isinstance(gdf, gpd.GeoDataFrame):
        raise TypeError(f"Förväntar GeoDataFrame, fick {type(gdf)}")
    
    if gdf.crs is None:
        raise ValueError(
            "GeoDataFrame saknar CRS – kan inte beräkna avstånd.\n"
            "Projicera data till EPSG:3006 innan analys."
        )
    
    if gdf.crs.to_epsg() != REQUIRED_CRS:
        raise ValueError(
            f"GeoDataFrame måste vara i EPSG:{REQUIRED_CRS} (SWEREF99 TM) för korrekta meteravstånd.\n"
            f"Nuvarande CRS: {gdf.crs}\n"
            f"Använd: gdf = gdf.to_crs({REQUIRED_CRS})"
        )
    
    # Validera indikator-kolumn
    if indikator is not None and indikator not in gdf.columns:
        raise ValueError(
            f"Indikator-kolumn '{indikator}' finns inte i GeoDataFrame.\n"
            f"Tillgängliga kolumner: {list(gdf.columns)}"
        )
    
    # Validera dataset-storlek för KNN
    if method == "knn" and k is not None:
        if len(gdf) <= k:
            raise ValueError(
                f"KNN med k={k} kräver minst {k+1} objekt.\n"
                f"Dataset har bara {len(gdf)} objekt.\n"
                f"Minska k eller använd distanceband-metoden."
            )


def lägg_till_grannsnitt(
    gdf: gpd.GeoDataFrame,
    indikator: str = "Effektivitet",
    method: Literal["knn", "distanceband"] = "knn",
    k: int = 4,
    distance_threshold: int = 50000,
    avståndsviktning: bool = False
) -> gpd.GeoDataFrame:
    """
    Beräknar grannsnittseffektivitet och effektivitetsgap.
    
    Args:
        gdf: GeoDataFrame med geometrier och indikatorvärden (måste vara EPSG:3006)
        indikator: Kolumnnamn för värde att jämföra (t.ex. 'Effektivitet')
        method: 'knn' eller 'distanceband'
        k: Antal närmaste grannar (om method='knn')
        distance_threshold: Max avstånd i meter (om method='distanceband')
        avståndsviktning: Om True, vikta grannar med 1/avstånd
    
    Returns:
        GeoDataFrame med tillagda kolumner:
            - grannsnitt: Medeleffektivitet bland grannar
            - eff_gap: Skillnad mot grannsnitt (positivt = bättre än grannar)
    
    Raises:
        ValueError: Om CRS är fel, dataset för litet, eller indikator saknas/har NaN
    """
    # Validera input
    validate_spatial_inputs(gdf, method, k if method == "knn" else None, indikator)
    
    # Kontrollera att indikator-kolumnen inte har NaN-värden
    if gdf[indikator].isna().any():
        n_nan = gdf[indikator].isna().sum()
        raise ValueError(
            f"Indikator-kolumn '{indikator}' innehåller {n_nan} NaN-värden.\n"
            f"Filtrera bort rader med saknade värden innan grannskapsanalys:\n"
            f"gdf = gdf[gdf['{indikator}'].notna()]"
        )
    
    gdf = gdf.copy()
    gdf["centroid"] = gdf.geometry.centroid
    värden = gdf[indikator].values
    
    # Bygg viktmatris
    if method == "knn":
        w = KNN.from_dataframe(gdf.set_geometry("centroid"), k=k)
        dists = w.full()[1]
    elif method == "distanceband":
        w = DistanceBand.from_dataframe(
            gdf.set_geometry("centroid"),
            threshold=distance_threshold,
            silence_warnings=True,
            binary=not avståndsviktning
        )
        dists = w.full()[1]
    else:
        raise ValueError(f"Ogiltig metod: {method}. Välj 'knn' eller 'distanceband'.")
    
    # Beräkna grannsnitt
    if avståndsviktning:
        # Använd epsilon istället för 1 meter för bättre precision
        weights = 1 / np.maximum(dists, 1e-6)  # Numerisk stabilitet
        weighted_vals = w.sparse.multiply(weights) @ värden
        norm = w.sparse.multiply(weights).sum(axis=1).A1
        
        # Hantera eventuella division-by-zero
        with np.errstate(divide='ignore', invalid='ignore'):
            grannsnitt = np.where(norm > 0, weighted_vals / norm, np.nan)
    else:
        card = np.array(list(w.cardinalities.values()))
        
        # Hantera eventuella division-by-zero
        with np.errstate(divide='ignore', invalid='ignore'):
            grannsnitt = np.where(card > 0, (w.sparse @ värden) / card, np.nan)
    
    gdf["grannsnitt"] = grannsnitt
    gdf["eff_gap"] = gdf[indikator] - gdf["grannsnitt"]
    gdf = gdf.drop(columns=["centroid"])
    
    # Återställ Företag-kolumn om den fanns
    # Detta behövs eftersom merge kan duplicera eller förlora kolumnen
    if "Företag" in gdf.columns:
        namn_df = gdf[["REId", "Företag"]].drop_duplicates()
        gdf = gdf.drop(columns=["Företag"])
        gdf = gdf.merge(namn_df, on="REId", how="left")
    
    return gdf


def get_spatial_summary_stats(gdf: gpd.GeoDataFrame, indikator: str = "Effektivitet") -> dict:
    """
    Beräknar sammanfattande statistik för grannskapsanalys.
    
    Args:
        gdf: GeoDataFrame med grannsnitt och eff_gap kolumner
        indikator: Kolumnnamn för grundindikator
    
    Returns:
        Dict med statistik:
            - mean_gap: Medel effektivitetsgap
            - std_gap: Standardavvikelse för gap
            - max_gap: Största positiva gap (bäst vs grannar)
            - min_gap: Största negativa gap (sämst vs grannar)
            - pct_above_neighbors: Andel som är bättre än grannar
    """
    if 'eff_gap' not in gdf.columns or 'grannsnitt' not in gdf.columns:
        raise ValueError("GeoDataFrame saknar grannsnitt eller eff_gap kolumner. Kör lägg_till_grannsnitt först.")
    
    # Filtrera bort eventuella NaN från grannskapsberäkningen
    gdf_clean = gdf.dropna(subset=['eff_gap', 'grannsnitt'])
    
    return {
        'mean_gap': gdf_clean['eff_gap'].mean(),
        'std_gap': gdf_clean['eff_gap'].std(),
        'max_gap': gdf_clean['eff_gap'].max(),
        'min_gap': gdf_clean['eff_gap'].min(),
        'pct_above_neighbors': (gdf_clean['eff_gap'] > 0).sum() / len(gdf_clean) * 100,
        'n_analyzed': len(gdf_clean)
    }
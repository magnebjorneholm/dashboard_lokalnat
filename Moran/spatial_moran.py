"""
Spatial Moran's I-analys för DEA-effektivitet.

Beräknar global och lokal spatial autokorrelation (Moran's I och LISA).
"""

import geopandas as gpd
import pandas as pd
import numpy as np
from typing import Optional, Literal, Tuple
from libpysal.weights import KNN, DistanceBand
from esda.moran import Moran, Moran_Local

from effektiviseringskrav.backend.heatmap_utils import (
    load_shapes_for_dea,
    merge_dea_with_geodata,
    aggregate_to_unique_geometries
)


def beräkna_global_morans_i(
    gdf: gpd.GeoDataFrame,
    indikator: str = "Effektivitet",
    method: Literal["knn", "distanceband"] = "knn",
    k: int = 4,
    distance_threshold: int = 50000,
    permutations: int = 999
) -> dict:
    """
    Beräknar global Moran's I för spatial autokorrelation.
    
    Args:
        gdf: GeoDataFrame med geometrier och indikatorvärden (måste vara EPSG:3006)
        indikator: Kolumnnamn för värde att analysera
        method: 'knn' eller 'distanceband'
        k: Antal grannar (om method='knn')
        distance_threshold: Avstånd i meter (om method='distanceband')
        permutations: Antal permutationer för signifikanstest
        
    Returns:
        Dict med Moran's I-statistik och signifikans
    """
    # Filtrera bort missing values
    gdf_clean = gdf[gdf[indikator].notna()].copy()
    
    if len(gdf_clean) < 3:
        raise ValueError("Behöver minst 3 observationer för Moran's I")
    
    # Skapa viktmatris
    if method == "knn":
        w = KNN.from_dataframe(gdf_clean, k=k)
    elif method == "distanceband":
        w = DistanceBand.from_dataframe(
            gdf_clean, 
            threshold=distance_threshold,
            binary=True
        )
    else:
        raise ValueError(f"Okänd metod: {method}")
    
    # Row-standardisera viktmatrisen (rekommenderat för Moran's I)
    w.transform = 'r'
    
    # Beräkna Moran's I
    y = gdf_clean[indikator].values
    moran = Moran(y, w, permutations=permutations)
    
    return {
        'I': moran.I,
        'expected_I': moran.EI,
        'variance_I': moran.VI_norm,
        'z_score': moran.z_norm,
        'p_value_norm': moran.p_norm,
        'p_value_sim': moran.p_sim,
        'interpretation': _interpret_morans_i(moran.I, moran.p_sim)
    }


def beräkna_lokal_morans_i(
    gdf: gpd.GeoDataFrame,
    indikator: str = "Effektivitet",
    method: Literal["knn", "distanceband"] = "knn",
    k: int = 4,
    distance_threshold: int = 50000,
    permutations: int = 999,
    significance_level: float = 0.05
) -> gpd.GeoDataFrame:
    """
    Beräknar lokal Moran's I (LISA) och identifierar kluster.
    
    Kluster definieras AUTOMATISKT som:
    - HH (High-High): Höga värden omgivna av höga värden
    - LL (Low-Low): Låga värden omgivna av låga värden
    - HL (High-Low): Höga värden omgivna av låga värden (spatial outlier)
    - LH (Low-High): Låga värden omgivna av höga värden (spatial outlier)
    - NS (Not Significant): Ingen signifikant spatial association
    
    Args:
        gdf: GeoDataFrame med geometrier och indikatorvärden
        indikator: Kolumnnamn för värde att analysera
        method: 'knn' eller 'distanceband'
        k: Antal grannar (om method='knn')
        distance_threshold: Avstånd i meter (om method='distanceband')
        permutations: Antal permutationer för signifikanstest
        significance_level: Signifikansnivå (default 0.05)
        
    Returns:
        GeoDataFrame med LISA-resultat och kluster-klassificering
    """
    # Filtrera bort missing values
    gdf_clean = gdf[gdf[indikator].notna()].copy().reset_index(drop=True)
    
    if len(gdf_clean) < 3:
        raise ValueError("Behöver minst 3 observationer för LISA")
    
    # Skapa viktmatris
    if method == "knn":
        w = KNN.from_dataframe(gdf_clean, k=k)
    elif method == "distanceband":
        w = DistanceBand.from_dataframe(
            gdf_clean, 
            threshold=distance_threshold,
            binary=True
        )
    else:
        raise ValueError(f"Okänd metod: {method}")
    
    # Row-standardisera
    w.transform = 'r'
    
    # Beräkna lokal Moran's I
    y = gdf_clean[indikator].values
    lisa = Moran_Local(y, w, permutations=permutations)
    
    # Lägg till resultat i GeoDataFrame
    gdf_clean['lisa_I'] = lisa.Is  # Lokalt Moran's I-värde
    gdf_clean['lisa_p_sim'] = lisa.p_sim  # P-värde från simulering
    gdf_clean['lisa_quadrant'] = lisa.q  # Kvadrant (1=HH, 2=LH, 3=LL, 4=HL)
    
    # Klassificera kluster baserat på signifikans
    gdf_clean['lisa_cluster'] = _classify_lisa_clusters(
        lisa.q, 
        lisa.p_sim, 
        significance_level
    )
    
    # Lägg till beskrivande text
    gdf_clean['lisa_cluster_name'] = gdf_clean['lisa_cluster'].map({
        'HH': 'Högt-Högt kluster',
        'LL': 'Lågt-Lågt kluster',
        'HL': 'Högt-Lågt outlier',
        'LH': 'Lågt-Högt outlier',
        'NS': 'Ej signifikant'
    })
    
    return gdf_clean


def _classify_lisa_clusters(
    quadrants: np.ndarray, 
    p_values: np.ndarray, 
    alpha: float = 0.05
) -> np.ndarray:
    """
    Klassificerar LISA-kluster baserat på kvadrant och signifikans.
    
    Kvadranter från esda.moran.Moran_Local:
    - 1: HH (High-High)
    - 2: LH (Low-High)
    - 3: LL (Low-Low)
    - 4: HL (High-Low)
    """
    clusters = np.full(len(quadrants), 'NS', dtype=object)
    
    # Endast signifikanta klassificeras
    significant = p_values <= alpha
    
    clusters[(quadrants == 1) & significant] = 'HH'
    clusters[(quadrants == 2) & significant] = 'LH'
    clusters[(quadrants == 3) & significant] = 'LL'
    clusters[(quadrants == 4) & significant] = 'HL'
    
    return clusters


def _interpret_morans_i(I: float, p_value: float, alpha: float = 0.05) -> str:
    """Tolkar Moran's I-resultat."""
    if p_value > alpha:
        return f"Ingen signifikant spatial autokorrelation (I={I:.3f}, p={p_value:.3f})"
    elif I > 0:
        return f"Signifikant positiv spatial autokorrelation (I={I:.3f}, p={p_value:.3f}) - liknande värden klustrar geografiskt"
    else:
        return f"Signifikant negativ spatial autokorrelation (I={I:.3f}, p={p_value:.3f}) - olika värden klustrar geografiskt"


def kör_komplett_spatial_analys(
    dea_result: pd.DataFrame,
    indikator: str = "Effektivitet",
    method: str = "knn",
    k: int = 4,
    distance_threshold: int = 50000
) -> Tuple[dict, gpd.GeoDataFrame]:
    """
    Kör både global och lokal Moran's I-analys på DEA-resultat.
    
    Args:
        dea_result: DataFrame med DEA-resultat från run_dea_model()
        indikator: Kolumn att analysera (t.ex. "Effektivitet")
        method: 'knn' eller 'distanceband'
        k: Antal grannar för KNN
        distance_threshold: Avstånd i meter för distanceband
        
    Returns:
        Tuple med (global_stats, gdf_med_lisa_resultat)
    """
    # Ladda och förbered geografisk data
    gdf_shapes, _ = load_shapes_for_dea()
    gdf_merged, _ = merge_dea_with_geodata(gdf_shapes, dea_result, value_column=indikator)
    gdf_agg = aggregate_to_unique_geometries(gdf_merged, value_column=indikator)
    
    # Global Moran's I
    global_stats = beräkna_global_morans_i(
        gdf_agg,
        indikator=indikator,
        method=method,
        k=k,
        distance_threshold=distance_threshold
    )
    
    # Lokal Moran's I (LISA)
    gdf_lisa = beräkna_lokal_morans_i(
        gdf_agg,
        indikator=indikator,
        method=method,
        k=k,
        distance_threshold=distance_threshold
    )
    
    return global_stats, gdf_lisa


# ============================================================================
# HJÄLPFUNKTIONER FÖR VISUALISERING OCH RAPPORTERING
# ============================================================================

def sammanfatta_lisa_resultat(gdf_lisa: gpd.GeoDataFrame) -> dict:
    """Sammanfattar LISA-resultat för rapportering."""
    cluster_counts = gdf_lisa['lisa_cluster'].value_counts().to_dict()
    
    total = len(gdf_lisa)
    pct_significant = (total - cluster_counts.get('NS', 0)) / total * 100
    
    return {
        'total_områden': total,
        'andel_signifikanta': pct_significant,
        'HH_kluster': cluster_counts.get('HH', 0),
        'LL_kluster': cluster_counts.get('LL', 0),
        'HL_outliers': cluster_counts.get('HL', 0),
        'LH_outliers': cluster_counts.get('LH', 0),
        'ej_signifikanta': cluster_counts.get('NS', 0)
    }


def hämta_kluster_områden(
    gdf_lisa: gpd.GeoDataFrame, 
    kluster_typ: str,
    indikator: str = None
) -> pd.DataFrame:
    """
    Hämtar alla områden av en viss kluster-typ.
    
    Args:
        gdf_lisa: GeoDataFrame från beräkna_lokal_morans_i()
        kluster_typ: 'HH', 'LL', 'HL', 'LH', eller 'NS'
        indikator: Kolumnnamn för indikator (om None, detekteras automatiskt)
        
    Returns:
        DataFrame med områden som tillhör kluster-typen
    """
    result = gdf_lisa[gdf_lisa['lisa_cluster'] == kluster_typ].copy()
    
    # Sortera efter lokalt Moran's I-värde
    result = result.sort_values('lisa_I', ascending=False)
    
    # Hitta indikator-kolumn automatiskt om inte angiven
    if indikator is None:
        # Leta efter vanliga indikatorer
        possible_indicators = ['Effektivitet', 'Supereffektivitet', 'effektivitet', 'supereffektivitet']
        for col in possible_indicators:
            if col in result.columns:
                indikator = col
                break
        
        # Om fortfarande inte hittat, använd första numeriska kolumn som inte är lisa_*
        if indikator is None:
            numeric_cols = result.select_dtypes(include=[np.number]).columns
            non_lisa_cols = [c for c in numeric_cols if not c.startswith('lisa_')]
            if non_lisa_cols:
                indikator = non_lisa_cols[0]
    
    # Välj relevanta kolumner
    cols = ['REId', indikator, 'lisa_I', 'lisa_p_sim', 'lisa_cluster_name']
    if 'Företag' in result.columns:
        cols.insert(1, 'Företag')
    
    # Filtrera till endast kolumner som finns
    cols = [c for c in cols if c in result.columns]
    
    return result[cols].reset_index(drop=True)
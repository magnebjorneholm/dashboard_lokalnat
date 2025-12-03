"""
utils/heatmap_utils.py - Heatmap-visualisering för geografisk data
==================================================================

Innehåller funktioner för att:
- Ladda och validera shapefile-data
- Merge DEA-resultat med geodata
- Skapa efficiency-heatmaps
"""

import geopandas as gpd
import pandas as pd
from typing import Tuple, Dict, Optional, Set

# Konstanter
REQUIRED_COLUMNS = ["FöretagNa", "Orgnr", "Redovisnin", "Länktillp"]
EXPECTED_CRS = 3006  # SWEREF99 TM
SHAPEFILE_PATH = "data/Samtliga nätföretags del- och verksamhetsområden.shp"
RECONCILIATION_PATH = "data/reconciliation_id_network_firm_dmu.csv"


def load_valid_reid_registry() -> Tuple[Set[str], Set[str], pd.DataFrame]:
    """
    Laddar den auktoritativa listan över giltiga REId från reconciliation-filen.
    
    Returns:
        Tuple med:
        - Set av alla giltiga REId (159 st)
        - Set av REId som förväntas ha DEA-data (exkl. RER med motsvarande REL)
        - Full DataFrame med reconciliation-data
    """
    try:
        df_recon = pd.read_csv(RECONCILIATION_PATH)
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Reconciliation-fil hittades inte: {RECONCILIATION_PATH}\n"
            "Denna fil är obligatorisk och definierar vilka REId som är giltiga."
        )
    
    valid_reid = set(df_recon['id_network_string'].dropna().unique())
    
    expected_dea_mask = (df_recon['in_data_modeller'] == True) | (df_recon['in_data_modeller'] == "True")
    expected_dea_reid = set(df_recon.loc[expected_dea_mask, 'id_network_string'].dropna().unique())
    
    rer_with_dmu = df_recon[
        (df_recon['id_network_string'].str.startswith('RER')) & 
        (expected_dea_mask) &
        (df_recon['DMU'].notna())
    ]
    
    for _, rer_row in rer_with_dmu.iterrows():
        dmu = rer_row['DMU']
        has_rel = df_recon[
            (df_recon['DMU'] == dmu) & 
            (df_recon['id_network_string'].str.startswith('REL'))
        ].shape[0] > 0
        
        if has_rel:
            expected_dea_reid.discard(rer_row['id_network_string'])
    
    return valid_reid, expected_dea_reid, df_recon


def load_shapes_for_dea() -> Tuple[gpd.GeoDataFrame, Dict]:
    """
    Laddar shapefile och filtrerar till ENDAST giltiga REId enligt reconciliation-filen.
    
    Returns:
        Tuple av (GeoDataFrame, metadata_dict)
    """
    valid_reid, expected_dea_reid, df_recon = load_valid_reid_registry()
    
    try:
        gdf = gpd.read_file(SHAPEFILE_PATH)
    except Exception as e:
        raise FileNotFoundError(f"Kunde inte läsa shapefile: {SHAPEFILE_PATH}. Fel: {e}")
    
    missing_cols = [c for c in REQUIRED_COLUMNS if c not in gdf.columns]
    if missing_cols:
        raise ValueError(
            f"Shapefile saknar obligatoriska kolumner: {missing_cols}\n"
            f"Tillgängliga kolumner: {list(gdf.columns)}"
        )
    
    if gdf.crs is None:
        raise ValueError("Shapefile saknar CRS-information (.prj-fil saknas?)")
    
    if gdf.crs.to_epsg() != EXPECTED_CRS:
        gdf = gdf.to_crs(EXPECTED_CRS)
    
    invalid_mask = ~gdf.geometry.is_valid
    n_invalid = invalid_mask.sum()
    if n_invalid > 0:
        gdf.loc[invalid_mask, "geometry"] = gdf.loc[invalid_mask, "geometry"].buffer(0)
    
    n_original = len(gdf)
    
    gdf["REId_list"] = gdf["Redovisnin"].astype(str).str.split(",")
    gdf = gdf.explode("REId_list").reset_index(drop=True)
    gdf["REId"] = gdf["REId_list"].str.strip()
    gdf = gdf.drop(columns=["REId_list", "Redovisnin"])
    
    n_after_explode = len(gdf)
    
    shapefile_reid = set(gdf["REId"].unique())
    gdf_filtered = gdf[gdf["REId"].isin(valid_reid)].copy()
    
    n_filtered_out = n_after_explode - len(gdf_filtered)
    excluded_reid = shapefile_reid - valid_reid
    
    gdf_filtered["geom_id"] = gdf_filtered["geometry"].apply(lambda g: g.wkb_hex)
    
    excluded_by_type = {}
    for reid in excluded_reid:
        net_type = reid[:3] if len(reid) >= 3 else "Okänd"
        excluded_by_type[net_type] = excluded_by_type.get(net_type, 0) + 1
    
    kept_by_type = {}
    for reid in gdf_filtered["REId"].unique():
        net_type = reid[:3]
        kept_by_type[net_type] = kept_by_type.get(net_type, 0) + 1
    
    metadata = {
        "shapefile_path": SHAPEFILE_PATH,
        "reconciliation_path": RECONCILIATION_PATH,
        "crs": str(gdf_filtered.crs),
        "n_polygons_original": n_original,
        "n_rows_after_explode": n_after_explode,
        "n_filtered_out": n_filtered_out,
        "n_valid_remaining": len(gdf_filtered),
        "n_unique_valid_reid": gdf_filtered["REId"].nunique(),
        "n_unique_geoms": gdf_filtered["geom_id"].nunique(),
        "n_invalid_fixed": n_invalid,
        "valid_reid_total": len(valid_reid),
        "expected_dea_reid_total": len(expected_dea_reid),
        "excluded_reid": list(excluded_reid),
        "excluded_by_type": excluded_by_type,
        "kept_by_type": kept_by_type,
    }
    
    return gdf_filtered, metadata


def merge_dea_with_geodata(
    gdf_shapes: gpd.GeoDataFrame, 
    df_dea: pd.DataFrame,
    value_column: str = "Effektivitet"
) -> Tuple[gpd.GeoDataFrame, Dict]:
    """
    Mergar DEA-resultat med geodata och rapporterar matchningskvalitet.
    
    Args:
        gdf_shapes: GeoDataFrame med shapefile-data
        df_dea: DataFrame med DEA-resultat
        value_column: Kolumnnamn för effektivitetsvärden
        
    Returns:
        Tuple av (merged GeoDataFrame, match_stats dict)
    """
    valid_reid, expected_dea_reid, df_recon = load_valid_reid_registry()
    
    required_cols = ["REId", value_column]
    
    foretag_col = None
    for col in df_dea.columns:
        if any(variant in col.lower() for variant in ['företag', 'foretag']):
            foretag_col = col
            break
    
    if foretag_col:
        required_cols.append(foretag_col)
    
    missing_cols = [c for c in required_cols if c not in df_dea.columns]
    if missing_cols:
        raise ValueError(f"DEA-resultat saknar kolumner: {missing_cols}")
    
    df_merge = df_dea[required_cols].copy()
    df_merge["REId"] = df_merge["REId"].str.strip().str.upper()
    
    if foretag_col and foretag_col != "Företag":
        df_merge = df_merge.rename(columns={foretag_col: "Företag"})
    
    shape_reid = set(gdf_shapes["REId"].str.strip().str.upper())
    dea_reid = set(df_merge["REId"])
    
    matched_reid = shape_reid & dea_reid
    only_in_shape = shape_reid - dea_reid
    only_in_dea = dea_reid - shape_reid
    
    expected_but_missing = only_in_shape & expected_dea_reid
    ok_to_miss = only_in_shape - expected_dea_reid
    
    gdf_shapes_clean = gdf_shapes.copy()
    gdf_shapes_clean["REId"] = gdf_shapes_clean["REId"].str.strip().str.upper()
    
    gdf_merged = gdf_shapes_clean.merge(df_merge, on="REId", how="left")
    
    missing_rows = gdf_merged[value_column].isna().sum()
    total_rows = len(gdf_merged)
    
    match_stats = {
        "total_shapes": len(shape_reid),
        "total_dea": len(dea_reid),
        "matched": len(matched_reid),
        "match_rate": len(matched_reid) / len(shape_reid) if len(shape_reid) > 0 else 0,
        "expected_but_missing": list(expected_but_missing),
        "ok_to_miss": list(ok_to_miss),
        "only_in_dea": list(only_in_dea),
        "only_in_shapes": list(only_in_shape),
        "missing_rows_after_merge": missing_rows,
        "missing_rate_rows": missing_rows / total_rows if total_rows > 0 else 0,
        "total_valid_reid": len(valid_reid),
        "total_expected_dea_reid": len(expected_dea_reid),
    }
    
    return gdf_merged, match_stats


def aggregate_to_unique_geometries(
    gdf: gpd.GeoDataFrame,
    value_column: str = "Effektivitet"
) -> gpd.GeoDataFrame:
    """
    Aggregerar till unika geometrier.
    
    Args:
        gdf: GeoDataFrame med eventuellt duplicerade geometrier
        value_column: Kolumnnamn för värden att aggregera
        
    Returns:
        GeoDataFrame med unika geometrier
    """
    preserve_cols = {
        "geometry": "first",
        value_column: "mean"
    }
    
    if "Företag" in gdf.columns:
        preserve_cols["Företag"] = "first"
    
    if "REId" in gdf.columns:
        preserve_cols["REId"] = lambda x: ", ".join(x.unique())
    
    gdf_agg = gdf.groupby("geom_id").agg(preserve_cols).reset_index()
    gdf_agg = gpd.GeoDataFrame(gdf_agg, geometry="geometry", crs=gdf.crs)
    
    return gdf_agg


def create_heatmap(
    df_dea: pd.DataFrame,
    value_column: str = "Effektivitet",
    title: str = "Efficiency Heatmap"
) -> Tuple[gpd.GeoDataFrame, Dict, Dict]:
    """
    Skapar heatmap från DEA-resultat.
    
    Wrapper-funktion som orchestrerar hela processen:
    1. Laddar shapefile
    2. Mergar med DEA-data
    3. Aggregerar till unika geometrier
    
    Args:
        df_dea: DataFrame med DEA-resultat (måste innehålla REId och value_column)
        value_column: Kolumnnamn för värden att visualisera
        title: Titel för heatmap
        
    Returns:
        Tuple av (GeoDataFrame för plotting, metadata, match_stats)
    """
    gdf_shapes, metadata = load_shapes_for_dea()
    gdf_merged, match_stats = merge_dea_with_geodata(gdf_shapes, df_dea, value_column)
    gdf_final = aggregate_to_unique_geometries(gdf_merged, value_column)
    
    return gdf_final, metadata, match_stats


def create_efficiency_heatmap(df_dea: pd.DataFrame) -> Tuple[gpd.GeoDataFrame, Dict, Dict]:
    """
    Skapar efficiency-heatmap från DEA-resultat.
    
    Convenience-funktion specifikt för efficiency-visualisering.
    
    Args:
        df_dea: DataFrame med DEA-resultat (måste innehålla REId och Effektivitet)
        
    Returns:
        Tuple av (GeoDataFrame för plotting, metadata, match_stats)
    """
    return create_heatmap(df_dea, value_column="Effektivitet", title="Efficiency Analysis")
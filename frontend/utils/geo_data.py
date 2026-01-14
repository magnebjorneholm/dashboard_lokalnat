"""
frontend/utils/geo_data.py

Loads and prepares geodata for efficiency visualization.
Simplified for REL (local networks) only.
"""

import geopandas as gpd
import pandas as pd
from pathlib import Path
from typing import Tuple, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from pipeline.core import PipelineResult

EXPECTED_CRS = 3006  # SWEREF99 TM


def load_shapefile(shapefile_path: str | Path) -> gpd.GeoDataFrame:
    """
    Load and prepare shapefile for DEA visualization.
    Filters to REL (local networks) only.
    
    Args:
        shapefile_path: Path to .shp file
        
    Returns:
        GeoDataFrame with one row per REL, columns: REId, Företag, geometry
    """
    gdf = gpd.read_file(shapefile_path)
    
    if gdf.crs is None:
        raise ValueError("Shapefile missing CRS")
    
    if gdf.crs.to_epsg() != EXPECTED_CRS:
        gdf = gdf.to_crs(EXPECTED_CRS)
    
    # Fix invalid geometries
    invalid_mask = ~gdf.geometry.is_valid
    if invalid_mask.any():
        gdf.loc[invalid_mask, "geometry"] = gdf.loc[invalid_mask, "geometry"].buffer(0)
    
    # Explode comma-separated REId values
    gdf["REId_list"] = gdf["Redovisnin"].astype(str).str.split(",")
    gdf = gdf.explode("REId_list").reset_index(drop=True)
    gdf["REId"] = gdf["REId_list"].str.strip().str.replace(r'\r\n', '', regex=True)
    
    # Filter to REL only
    gdf = gdf[gdf["REId"].str.startswith("REL", na=False)].copy()
    
    # Clean up columns
    gdf = gdf.rename(columns={"FöretagNa": "Företag"})
    gdf = gdf[["REId", "Företag", "geometry"]].copy()
    
    # Add geometry ID for later aggregation
    gdf["geom_id"] = gdf["geometry"].apply(lambda g: g.wkb_hex)
    
    return gdf


def merge_with_dea_results(
    gdf: gpd.GeoDataFrame,
    dea_results: pd.DataFrame,
    value_column: str = "Effektivitet"
) -> gpd.GeoDataFrame:
    """
    Merge geodata with DEA results.
    
    Args:
        gdf: GeoDataFrame from load_shapefile()
        dea_results: DataFrame with REId and value_column
        value_column: Column to visualize
        
    Returns:
        Merged GeoDataFrame
    """
    required_cols = ["REId", value_column]
    missing = [c for c in required_cols if c not in dea_results.columns]
    if missing:
        raise ValueError(f"DEA results missing columns: {missing}")
    
    # Prepare DEA data
    df_merge = dea_results[["REId", value_column]].copy()
    df_merge["REId"] = df_merge["REId"].str.strip().str.upper()
    
    # Prepare geodata
    gdf = gdf.copy()
    gdf["REId"] = gdf["REId"].str.strip().str.upper()
    
    # Merge
    gdf_merged = gdf.merge(df_merge, on="REId", how="left")
    
    return gdf_merged


def aggregate_geometries(
    gdf: gpd.GeoDataFrame,
    value_column: str = "Effektivitet"
) -> gpd.GeoDataFrame:
    """
    Aggregate to unique geometries (handles multi-REId polygons).
    
    Args:
        gdf: Merged GeoDataFrame
        value_column: Column to aggregate (mean)
        
    Returns:
        Aggregated GeoDataFrame with unique geometries
    """
    agg_dict = {
        "geometry": "first",
        value_column: "mean",
        "Företag": "first",
        "REId": lambda x: ", ".join(x.unique())
    }
    
    gdf_agg = gdf.groupby("geom_id").agg(agg_dict).reset_index(drop=True)
    gdf_agg = gpd.GeoDataFrame(gdf_agg, geometry="geometry", crs=gdf.crs)
    
    return gdf_agg


def prepare_map_data(
    shapefile_path: str | Path,
    dea_results: pd.DataFrame,
    value_column: str = "Effektivitet"
) -> gpd.GeoDataFrame:
    """
    Convenience function: load, merge, aggregate in one call.
    
    Args:
        shapefile_path: Path to shapefile
        dea_results: DataFrame with REId and value_column
        value_column: Column to visualize
        
    Returns:
        GeoDataFrame ready for visualization
    """
    gdf = load_shapefile(shapefile_path)
    gdf = merge_with_dea_results(gdf, dea_results, value_column)
    gdf = aggregate_geometries(gdf, value_column)
    return gdf


def prepare_map_data_from_pipeline(
    shapefile_path: str | Path,
    pipeline_result: "PipelineResult",
    value_column: str = "Effektivitet"
) -> Tuple[gpd.GeoDataFrame, Optional[gpd.GeoDataFrame]]:
    """
    Prepare map data from PipelineResult, with user company highlighted.
    
    Args:
        shapefile_path: Path to shapefile
        pipeline_result: PipelineResult object
        value_column: Column to visualize
        
    Returns:
        Tuple of (all_data, user_company_data)
    """
    dea_results = pipeline_result.dea.dea_results
    user_reid = pipeline_result.user_reid
    
    gdf = load_shapefile(shapefile_path)
    gdf_merged = merge_with_dea_results(gdf, dea_results, value_column)
    
    # Extract user company geometries before aggregation
    user_geoms = gdf_merged[gdf_merged["REId"].str.upper() == user_reid.upper()].copy()
    
    # Aggregate for main map
    gdf_agg = aggregate_geometries(gdf_merged, value_column)
    
    return gdf_agg, user_geoms if not user_geoms.empty else None
"""
frontend/utils/geo_data.py

Loads and prepares geodata for efficiency visualization.
Simplified for REL (local networks) only.
Aggregates by REId (concession area), not by geometry.
"""

import geopandas as gpd
import pandas as pd
from pathlib import Path
from shapely.ops import unary_union
from typing import Tuple, Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from pipeline.core import PipelineResult

from config.column_names import (
    COL_DEA_EFFICIENCY, COL_DEA_SUPER_EFF, COL_EFF_REQ_ANNUAL,
    COL_REVENUE_FRAME, COL_CAPITAL_COST_PERIOD, COL_CONTROLLABLE_PERIOD,
)

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

    # Clean up columns — "FöretagNa" is the shapefile's column (external source, not renamed)
    gdf = gdf.rename(columns={"FöretagNa": "Företag"})
    gdf = gdf[["REId", "Företag", "geometry"]].copy()

    return gdf


def merge_with_dea_results(
    gdf: gpd.GeoDataFrame,
    dea_results: pd.DataFrame,
    value_columns: str | List[str] = COL_DEA_EFFICIENCY
) -> gpd.GeoDataFrame:
    """
    Merge geodata with DEA results.

    Args:
        gdf: GeoDataFrame from load_shapefile()
        dea_results: DataFrame with REId and value columns
        value_columns: Column(s) to include from DEA results

    Returns:
        Merged GeoDataFrame
    """
    if isinstance(value_columns, str):
        value_columns = [value_columns]

    required_cols = ["REId"] + value_columns
    available = [c for c in required_cols if c in dea_results.columns]

    if "REId" not in available:
        raise ValueError("DEA results missing required column: REId")

    value_columns = [c for c in value_columns if c in dea_results.columns]

    cols_to_merge = ["REId"] + value_columns
    df_merge = dea_results[cols_to_merge].copy()
    df_merge["REId"] = df_merge["REId"].str.strip().str.upper()

    gdf = gdf.copy()
    gdf["REId"] = gdf["REId"].str.strip().str.upper()

    gdf_merged = gdf.merge(df_merge, on="REId", how="left")

    return gdf_merged


def aggregate_by_reid(
    gdf: gpd.GeoDataFrame,
    value_columns: str | List[str] = COL_DEA_EFFICIENCY
) -> gpd.GeoDataFrame:
    """
    Aggregate geometries by REId (concession area).
    Each REL gets one row with unified geometry.

    Args:
        gdf: Merged GeoDataFrame (may have multiple rows per REId)
        value_columns: Column(s) to preserve

    Returns:
        GeoDataFrame with one row per REId
    """
    if isinstance(value_columns, str):
        value_columns = [value_columns]

    crs = gdf.crs

    def aggregate_group(group):
        result = {
            "geometry": unary_union(group.geometry.values),
            "Företag": group["Företag"].iloc[0],
        }

        for col in value_columns:
            if col in group.columns:
                result[col] = group[col].iloc[0]  # Same value for all rows in group

        return pd.Series(result)

    gdf_agg = gdf.groupby("REId").apply(aggregate_group, include_groups=False).reset_index()
    gdf_agg = gpd.GeoDataFrame(gdf_agg, geometry="geometry", crs=crs)

    return gdf_agg


def prepare_map_data(
    shapefile_path: str | Path,
    dea_results: pd.DataFrame,
    value_columns: str | List[str] = COL_DEA_EFFICIENCY
) -> gpd.GeoDataFrame:
    """
    Convenience function: load, merge, aggregate in one call.

    Args:
        shapefile_path: Path to shapefile
        dea_results: DataFrame with REId and value columns
        value_columns: Column(s) to visualize

    Returns:
        GeoDataFrame ready for visualization (one row per REId)
    """
    gdf = load_shapefile(shapefile_path)
    gdf = merge_with_dea_results(gdf, dea_results, value_columns)
    gdf = aggregate_by_reid(gdf, value_columns)
    return gdf


def prepare_map_data_from_pipeline(
    shapefile_path: str | Path,
    pipeline_result: "PipelineResult"
) -> Tuple[gpd.GeoDataFrame, Optional[gpd.GeoDataFrame]]:
    """
    Prepare map data from PipelineResult, with user company highlighted.

    Includes 6 variables for visualization:
    - dea_efficiency, dea_super_efficiency (from DEA)
    - efficiency_requirement_annual (from post_dea.all_eff_reqs)
    - IR_per_CU, CAPEX_per_CU, OPEX_per_CU (calculated per customer)

    Args:
        shapefile_path: Path to shapefile
        pipeline_result: PipelineResult object

    Returns:
        Tuple of (all_data, user_company_data)
    """
    dea_results = pipeline_result.dea.dea_results.copy()
    user_reid = pipeline_result.user_reid.strip().upper()

    # Get CU (customers) from pre_dea
    df_companies = pipeline_result.pre_dea.df_all_companies
    cu_data = df_companies[['REId', 'CU']].copy()
    cu_data['REId'] = cu_data['REId'].str.strip().str.upper()

    # Get efficiency requirement from post_dea.all_eff_reqs
    effkrav_data = pipeline_result.post_dea.all_eff_reqs[['REId', COL_EFF_REQ_ANNUAL]].copy()
    effkrav_data['REId'] = effkrav_data['REId'].str.strip().str.upper()

    # Get revenue frame data from post_dea
    ir_data = pipeline_result.post_dea.all_revenue_frames[
        ['REId', COL_REVENUE_FRAME, COL_CAPITAL_COST_PERIOD, COL_CONTROLLABLE_PERIOD]
    ].copy()
    ir_data['REId'] = ir_data['REId'].str.strip().str.upper()

    # Merge all data sources
    dea_results['REId'] = dea_results['REId'].str.strip().str.upper()

    combined = dea_results.merge(cu_data, on='REId', how='left')
    combined = combined.merge(effkrav_data, on='REId', how='left')
    combined = combined.merge(ir_data, on='REId', how='left')

    # Calculate per-customer values (CU is in thousands, values in tkr)
    combined['IR_per_CU'] = combined[COL_REVENUE_FRAME] / combined['CU']
    combined['CAPEX_per_CU'] = combined[COL_CAPITAL_COST_PERIOD] / combined['CU']
    combined['OPEX_per_CU'] = combined[COL_CONTROLLABLE_PERIOD] / combined['CU']

    # Select columns for map visualization
    value_columns = [
        COL_DEA_EFFICIENCY, COL_DEA_SUPER_EFF, COL_EFF_REQ_ANNUAL,
        'IR_per_CU', 'CAPEX_per_CU', 'OPEX_per_CU'
    ]

    # Aggregate by REId
    gdf_agg = prepare_map_data(shapefile_path, combined, value_columns)

    # Extract user company from aggregated data (same geometry source)
    user_geoms = gdf_agg[gdf_agg["REId"] == user_reid].copy()

    return gdf_agg, user_geoms if not user_geoms.empty else None

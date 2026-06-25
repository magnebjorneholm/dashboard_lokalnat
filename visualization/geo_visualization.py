"""
frontend/utils/geo_visualization.py

Map visualizations for DEA efficiency analysis.
Uses MapLibre renderer (Plotly 5.24+).
Green-red color scheme: green = high efficiency, red = low efficiency.
Percentile-based gradient for better visual differentiation.
"""

import geopandas as gpd
import plotly.graph_objects as go
from typing import Optional, List
import json
import numpy as np
import pandas as pd

from config.column_names import (
    COL_DEA_EFFICIENCY, COL_DEA_SUPER_EFF, COL_EFF_REQ_ANNUAL,
)
from config.colors import COLORS, GEO_COLORSCALE

MAP_STYLES = {
    "light": "carto-positron",
    "dark": "carto-darkmatter",
    "streets": "open-street-map",
    "minimal": "white-bg",
}

# Column name mapping: internal -> display
COLUMN_LABELS = {
    COL_DEA_EFFICIENCY: "Efficiency",
    COL_DEA_SUPER_EFF: "Superefficiency",
    COL_EFF_REQ_ANNUAL: "Efficiency requirement",
    "IR_per_CU": "Revenue cap per customer",
    "CAPEX_per_CU": "Capital cost per customer",
    "OPEX_per_CU": "OPEX per customer",
    "incentive_pct_of_return": "Incentive adj. (% of return)",
}


def get_available_value_columns(gdf: gpd.GeoDataFrame) -> List[str]:
    """
    Returns list of numeric columns suitable for visualization.
    Priority order: efficiency metrics first, then per-customer metrics.
    """
    numeric_cols = gdf.select_dtypes(include=['float64', 'float32', 'int64', 'int32']).columns

    priority_order = [
        COL_DEA_EFFICIENCY, COL_DEA_SUPER_EFF, COL_EFF_REQ_ANNUAL,
        "IR_per_CU", "CAPEX_per_CU", "OPEX_per_CU",
        "incentive_pct_of_return",
    ]
    priority = [c for c in priority_order if c in numeric_cols]

    return priority


def get_column_label(column: str) -> str:
    """Get English display label for column."""
    return COLUMN_LABELS.get(column, column)


def create_efficiency_map(
    gdf: gpd.GeoDataFrame,
    user_geoms: Optional[gpd.GeoDataFrame] = None,
    value_column: str = COL_DEA_EFFICIENCY,
    height: int = 500,
    style: str = "light",
    zoom: float = 3.0
) -> go.Figure:
    """
    Create interactive choropleth map with Plotly (MapLibre renderer).

    Args:
        gdf: GeoDataFrame with one row per REId
        user_geoms: GeoDataFrame with user company for highlighting
        value_column: Column to visualize
        height: Map height in pixels
        style: Map style - "light", "dark", "streets", or "minimal"
        zoom: Initial zoom level (lower = more zoomed out)

    Returns:
        Plotly Figure object
    """
    gdf_plot = gdf.to_crs(4326).copy()

    if value_column not in gdf_plot.columns:
        available = get_available_value_columns(gdf)
        if available:
            value_column = available[0]
        else:
            raise ValueError("No numeric columns available for visualization")

    gdf_plot["hover_text"] = gdf_plot.apply(
        lambda row: _create_hover_text(row, value_column),
        axis=1
    )

    fig = go.Figure()

    geojson = json.loads(gdf_plot.to_json())

    # Use percentile-based mapping for better visual differentiation
    valid_values = gdf_plot[gdf_plot[value_column].notna()][value_column]
    if not valid_values.empty:
        # Convert raw values to percentile ranks (0-100)
        from scipy.stats import rankdata
        ranks = rankdata(valid_values.values, method='average')
        percentiles = (ranks - 1) / max(len(ranks) - 1, 1) * 100

        # Map percentiles back to all rows (NaN stays as -1)
        pct_col = f"_percentile_{value_column}"
        gdf_plot[pct_col] = np.nan
        gdf_plot.loc[valid_values.index, pct_col] = percentiles
        z_values = gdf_plot[pct_col].fillna(-1).values
        zmin = 0
        zmax = 100
    else:
        z_values = gdf_plot[value_column].fillna(-1).values
        zmin = 0
        zmax = 100

    # Muted red-green colorscale from design system
    colorscale = GEO_COLORSCALE

    # Determine colorbar title based on column
    label = COLUMN_LABELS.get(value_column, value_column)

    fig.add_trace(go.Choroplethmap(
        geojson=geojson,
        locations=gdf_plot.index,
        z=z_values,
        colorscale=colorscale,
        zmin=zmin,
        zmax=zmax,
        marker=dict(
            opacity=0.75,
            line=dict(width=0.5, color="#FFFFFF")
        ),
        text=gdf_plot["hover_text"],
        hovertemplate="%{text}<extra></extra>",
        showscale=True,
        colorbar=dict(
            title=dict(text=f"{label}<br>(percentile)", font=dict(size=11)),
            tickvals=[0, 25, 50, 75, 100],
            ticktext=["0th", "25th", "50th", "75th", "100th"],
            len=0.6,
            thickness=12,
            x=1.0,
            xpad=4,
            bgcolor="rgba(255,255,255,0.8)",
            borderwidth=0,
            tickfont=dict(size=10),
        ),
    ))

    if user_geoms is not None and not user_geoms.empty:
        _add_company_highlight(fig, user_geoms)

    map_style = MAP_STYLES.get(style, "carto-positron")

    fig.update_layout(
        map=dict(
            style=map_style,
            center=dict(lat=63.0, lon=16.0),
            zoom=zoom
        ),
        height=height,
        margin=dict(r=0, t=0, l=0, b=0),
        paper_bgcolor=COLORS["bg_page"],
        font=dict(family="Inter, sans-serif", size=11, color=COLORS["text_primary"])
    )

    return fig


def _create_hover_text(row: pd.Series, value_column: str) -> str:
    """
    Create hover text showing all 6 metrics for a map feature.
    The selected value_column is highlighted with bold.
    """
    company = row.get("Företag", "N/A")
    reid = row.get("REId", "N/A")

    lines = [f"<b>{company}</b>", f"REId: {reid}", ""]

    # All metrics to display
    metrics = [
        (COL_DEA_EFFICIENCY, "Efficiency", ".1%", True),
        (COL_DEA_SUPER_EFF, "Superefficiency", ".3f", False),
        (COL_EFF_REQ_ANNUAL, "Efficiency req.", ".2%", True),
        ("IR_per_CU", "Rev. frame/cust.", ",.1f", False),
        ("CAPEX_per_CU", "Capital cost/cust.", ",.1f", False),
        ("OPEX_per_CU", "OPEX/cust.", ",.1f", False),
        ("incentive_pct_of_return", "Incentive/return", ".1%", True),
    ]

    for col, label, fmt, is_percent in metrics:
        value = row.get(col)
        if pd.notna(value):
            if is_percent:
                formatted = f"{value:{fmt}}"
            else:
                formatted = f"{value:{fmt}}"

            # Bold the selected metric
            if col == value_column:
                lines.append(f"<b>{label}: {formatted}</b>")
            else:
                lines.append(f"{label}: {formatted}")
        else:
            lines.append(f"{label}: -")

    return "<br>".join(lines)


def _add_company_highlight(fig: go.Figure, user_geoms: gpd.GeoDataFrame) -> None:
    """Add semi-transparent fill and thick outline for user company areas."""
    company_plot = user_geoms.to_crs(4326).copy()

    # 1. Semi-transparent fill overlay
    geojson = json.loads(company_plot.to_json())
    fig.add_trace(go.Choroplethmap(
        geojson=geojson,
        locations=company_plot.index,
        z=[1] * len(company_plot),
        colorscale=[[0, COLORS["primary"]], [1, COLORS["primary"]]],
        marker=dict(opacity=0.15, line=dict(width=0, color="rgba(0,0,0,0)")),
        showscale=False,
        hoverinfo="skip",
    ))

    # 2. Thick border
    for _, row in company_plot.iterrows():
        geom = row.geometry
        polygons = []

        if geom.geom_type == "Polygon":
            polygons = [geom]
        elif geom.geom_type == "MultiPolygon":
            polygons = list(geom.geoms)

        for poly in polygons:
            coords = list(poly.exterior.coords)
            lons = [c[0] for c in coords]
            lats = [c[1] for c in coords]

            fig.add_trace(go.Scattermap(
                lon=lons,
                lat=lats,
                mode="lines",
                line=dict(width=4, color=COLORS["primary"]),
                showlegend=False,
                hoverinfo="skip"
            ))


def create_variable_selector_options(gdf: gpd.GeoDataFrame) -> List[dict]:
    """
    Creates options for a Streamlit selectbox with English labels.
    """
    columns = get_available_value_columns(gdf)

    return [
        {"value": col, "label": get_column_label(col)}
        for col in columns
    ]

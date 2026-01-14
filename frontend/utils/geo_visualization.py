"""
frontend/utils/geo_visualization.py

Map visualizations for DEA efficiency analysis.
Uses MapLibre renderer (Plotly 5.24+).
Nordic Blue color scheme matching Regumetrica graphical profile.
"""

import geopandas as gpd
import plotly.graph_objects as go
from typing import Optional, List
import json
import pandas as pd


COLORS = {
    "primary": "#2563EB",
    "primary_dark": "#1E40AF",
    "primary_light": "#3B82F6",
    "text": "#0F172A",
    "text_muted": "#475569",
    "bg": "#F8FAFC",
    "highlight": "#DC2626",
}

MAP_STYLES = {
    "light": "carto-positron",
    "dark": "carto-darkmatter",
    "streets": "open-street-map",
    "minimal": "white-bg",
}

# Column name mapping: internal -> display
COLUMN_LABELS = {
    "Effektivitet": "Efficiency",
    "Supereffektivitet": "Superefficiency",
    "eff_gap": "Efficiency gap",
    "potential": "Efficiency potential",
    "grannsnitt": "Neighbor average",
}


def get_available_value_columns(gdf: gpd.GeoDataFrame) -> List[str]:
    """
    Returns list of numeric columns suitable for visualization.
    """
    numeric_cols = gdf.select_dtypes(include=['float64', 'float32', 'int64', 'int32']).columns
    
    priority_order = ["Effektivitet", "Supereffektivitet", "eff_gap", "potential"]
    priority = [c for c in priority_order if c in numeric_cols]
    others = [c for c in numeric_cols if c not in priority and c not in ['geom_id', 'index']]
    
    return priority + others


def get_column_label(column: str) -> str:
    """Get English display label for column."""
    return COLUMN_LABELS.get(column, column)


def create_efficiency_map(
    gdf: gpd.GeoDataFrame,
    user_geoms: Optional[gpd.GeoDataFrame] = None,
    value_column: str = "Effektivitet",
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
    z_values = gdf_plot[value_column].fillna(-1).values
    
    valid_values = gdf_plot[gdf_plot[value_column].notna()][value_column]
    zmin = valid_values.min() if not valid_values.empty else 0
    zmax = valid_values.max() if not valid_values.empty else 1
    
    colorscale = [
        [0, "#CBD5E1"],
        [0.001, "#1E3A5F"],
        [0.3, "#2563EB"],
        [0.6, "#3B82F6"],
        [1, "#93C5FD"]
    ]
    
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
        showscale=False
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
        paper_bgcolor=COLORS["bg"],
        font=dict(family="Inter, sans-serif", size=11, color=COLORS["text"])
    )
    
    return fig


def _create_hover_text(row: pd.Series, value_column: str) -> str:
    """Create hover text for a map feature."""
    company = row.get("Företag", "N/A")
    reid = row.get("REId", "N/A")
    value = row.get(value_column)
    label = get_column_label(value_column)
    
    if pd.notna(value):
        if abs(value) < 10:
            formatted = f"{value:.3f}"
        else:
            formatted = f"{value:,.1f}"
        return f"<b>{company}</b><br>REId: {reid}<br>{label}: {formatted}"
    else:
        return f"<b>{company}</b><br>REId: {reid}<br>No data"


def _add_company_highlight(fig: go.Figure, user_geoms: gpd.GeoDataFrame) -> None:
    """Add red outline for user company areas."""
    company_plot = user_geoms.to_crs(4326).copy()
    
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
                line=dict(width=2.5, color=COLORS["highlight"]),
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
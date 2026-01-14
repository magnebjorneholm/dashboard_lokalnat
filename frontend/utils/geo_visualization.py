"""
frontend/utils/geo_visualization.py

Map visualizations for DEA efficiency analysis.
Nordic Blue color scheme matching Regumetrica graphical profile.
"""

import geopandas as gpd
import plotly.graph_objects as go
from typing import Optional
import json
import pandas as pd


# Nordic Blue color palette (from config.toml)
COLORS = {
    "primary": "#2563EB",
    "primary_dark": "#1E40AF",
    "primary_light": "#3B82F6",
    "text": "#0F172A",
    "text_muted": "#475569",
    "bg": "#F8FAFC",
    "bg_secondary": "#F1F5F9",
    "border": "#E2E8F0",
    "highlight": "#DC2626",  # Red for user company
}


def create_efficiency_map(
    gdf: gpd.GeoDataFrame,
    user_geoms: Optional[gpd.GeoDataFrame] = None,
    value_column: str = "Effektivitet",
    height: int = 500
) -> go.Figure:
    """
    Create interactive choropleth map with Plotly.
    
    Args:
        gdf: GeoDataFrame with aggregated areas (SWEREF99 TM)
        user_geoms: GeoDataFrame with user company areas for highlighting
        value_column: Column to visualize
        height: Map height in pixels
        
    Returns:
        Plotly Figure object
    """
    # Convert to WGS84 for Mapbox
    gdf_plot = gdf.to_crs(4326).copy()
    
    # Prepare hover text
    gdf_plot["hover_text"] = gdf_plot.apply(
        lambda row: _create_hover_text(row, value_column),
        axis=1
    )
    
    fig = go.Figure()
    
    # Main choropleth
    geojson = json.loads(gdf_plot.to_json())
    z_values = gdf_plot[value_column].fillna(-1).values
    
    valid_values = gdf_plot[gdf_plot[value_column].notna()][value_column]
    zmin = valid_values.min() if not valid_values.empty else 0
    zmax = valid_values.max() if not valid_values.empty else 1
    
    # Nordic Blue color scale
    colorscale = [
        [0, "#CBD5E1"],       # Gray for missing
        [0.001, "#1E3A5F"],   # Dark blue
        [0.3, "#2563EB"],     # Primary blue
        [0.6, "#3B82F6"],     # Light blue
        [1, "#93C5FD"]        # Very light blue
    ]
    
    fig.add_trace(go.Choroplethmapbox(
        geojson=geojson,
        locations=gdf_plot.index,
        z=z_values,
        colorscale=colorscale,
        zmin=zmin,
        zmax=zmax,
        marker_opacity=0.75,
        marker_line_width=0.5,
        marker_line_color="#FFFFFF",
        text=gdf_plot["hover_text"],
        hovertemplate="%{text}<extra></extra>",
        colorbar=dict(
            title=dict(text=value_column, font=dict(size=11, color=COLORS["text"])),
            thickness=12,
            len=0.6,
            bgcolor="rgba(255,255,255,0.9)",
            tickfont=dict(size=10, color=COLORS["text_muted"]),
            x=0.98
        )
    ))
    
    # User company highlight
    if user_geoms is not None and not user_geoms.empty:
        _add_company_highlight(fig, user_geoms)
    
    # Layout
    fig.update_layout(
        mapbox=dict(
            style="carto-positron",
            center=dict(lat=62.5, lon=16.0),
            zoom=3.8
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
    
    if pd.notna(value):
        return f"<b>{company}</b><br>REId: {reid}<br>{value_column}: {value:.3f}"
    else:
        return f"<b>{company}</b><br>REId: {reid}<br>No DEA data"


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
            
            fig.add_trace(go.Scattermapbox(
                lon=lons,
                lat=lats,
                mode="lines",
                line=dict(width=2.5, color=COLORS["highlight"]),
                showlegend=False,
                hoverinfo="skip"
            ))
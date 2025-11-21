"""
Kartvisualiseringar för DEA-analys.
====================================

Innehåller funktioner för att skapa interaktiva kartor med Plotly.
Separerad från heatmap_utils.py för tydligare separation mellan
datahantering och visualisering.

Design:
- Tar GeoDataFrame som input
- Returnerar Plotly Figure-objekt
- Ingen databehandling här - endast visualisering
- Vid Dash-migration ersätts denna fil, medan heatmap_utils.py behålls
"""

import geopandas as gpd
import plotly.graph_objects as go
from typing import Optional
import json
import pandas as pd


def plot_efficiency_map_plotly(
    gdf_agg: gpd.GeoDataFrame,
    company_geoms: Optional[gpd.GeoDataFrame] = None,
    value_column: str = "Effektivitet",
    title: Optional[str] = None,
    height: int = 700,
    dark_theme: bool = False
) -> go.Figure:
    """
    Skapar interaktiv choropleth-karta med Plotly.
    
    Args:
        gdf_agg: GeoDataFrame med aggregerade områden (SWEREF99 TM)
        company_geoms: GeoDataFrame med företagets områden för markering
        value_column: Kolumn att visualisera
        title: Kartans titel
        height: Höjd i pixlar
        dark_theme: Om True, använd mörkt tema
        
    Returns:
        Plotly Figure-objekt
    """
    gdf_plot = gdf_agg.to_crs(4326).copy()
    
    # Förbered hover-data
    gdf_plot['hover_text'] = gdf_plot.apply(
        lambda row: (
            f"<b>{row.get('Företag', 'N/A')}</b><br>"
            f"REId: {row.get('REId', 'N/A')}<br>"
            f"{value_column}: {row[value_column]:.3f}" 
            if pd.notna(row[value_column]) 
            else f"<b>{row.get('Företag', 'N/A')}</b><br>REId: {row.get('REId', 'N/A')}<br>Ingen DEA-data"
        ),
        axis=1
    )
    
    fig = go.Figure()
    
    geojson = json.loads(gdf_plot.to_json())
    z_values = gdf_plot[value_column].fillna(-1).values
    
    # Färgschema beroende på tema
    if dark_theme:
        colorscale = [
            [0, "#424242"],      # Mörkgrå för missing
            [0.001, "#0D47A1"],  # Djup mörkblå
            [0.5, "#1976D2"],    # Mellanblå
            [1, "#64B5F6"]       # Ljusblå
        ]
        line_color = '#263238'
        bg_color = '#1E1E1E'
        text_color = '#E0E0E0'
        colorbar_bg = 'rgba(30,30,30,0.8)'
    else:
        colorscale = [
            [0, "#BDBDBD"],      # Grått för missing
            [0.001, "#0D3B66"],  # Mörkblå
            [0.5, "#1976D2"],    # Mellanblå
            [1, "#64B5F6"]       # Ljusblå
        ]
        line_color = 'white'
        bg_color = '#F5F7FA'
        text_color = '#2C3E50'
        colorbar_bg = 'rgba(255,255,255,0.8)'
    
    fig.add_trace(go.Choroplethmapbox(
        geojson=geojson,
        locations=gdf_plot.index,
        z=z_values,
        colorscale=colorscale,
        zmin=gdf_plot[gdf_plot[value_column].notna()][value_column].min() if gdf_plot[value_column].notna().any() else 0,
        zmax=gdf_plot[gdf_plot[value_column].notna()][value_column].max() if gdf_plot[value_column].notna().any() else 1,
        marker_opacity=0.7,
        marker_line_width=0.5,
        marker_line_color=line_color,
        text=gdf_plot['hover_text'],
        hovertemplate='%{text}<extra></extra>',
        colorbar=dict(
            title=value_column,
            thickness=15,
            len=0.7,
            bgcolor=colorbar_bg,
            tickfont=dict(size=10, color=text_color)
        )
    ))
    
    # Företagsmarkering
    if company_geoms is not None:
        company_plot = company_geoms.to_crs(4326).copy()
        
        for idx, row in company_plot.iterrows():
            geom = row.geometry
            
            if geom.geom_type == 'Polygon':
                coords = list(geom.exterior.coords)
                lons = [coord[0] for coord in coords]
                lats = [coord[1] for coord in coords]
                
                fig.add_trace(go.Scattermapbox(
                    lon=lons,
                    lat=lats,
                    mode='lines',
                    line=dict(width=3, color='#D32F2F'),
                    showlegend=False,
                    hoverinfo='skip'
                ))
            elif geom.geom_type == 'MultiPolygon':
                for poly in geom.geoms:
                    coords = list(poly.exterior.coords)
                    lons = [coord[0] for coord in coords]
                    lats = [coord[1] for coord in coords]
                    
                    fig.add_trace(go.Scattermapbox(
                        lon=lons,
                        lat=lats,
                        mode='lines',
                        line=dict(width=3, color='#D32F2F'),
                        showlegend=False,
                        hoverinfo='skip'
                    ))
    
    # Layout
    mapbox_style = "carto-darkmatter" if dark_theme else "carto-positron"
    
    fig.update_layout(
        title={
            'text': title or f"{value_column} per verksamhetsområde",
            'font': {'size': 16, 'color': text_color, 'family': 'sans-serif'},
            'x': 0.5,
            'xanchor': 'center'
        },
        mapbox=dict(
            style=mapbox_style,
            center=dict(lat=62.0, lon=15.0),
            zoom=4
        ),
        height=height,
        margin={"r":0, "t":50, "l":0, "b":0},
        paper_bgcolor=bg_color,
        font=dict(family="sans-serif", size=12, color=text_color)
    )
    
    return fig


def plot_efficiency_map_matplotlib(
    gdf_agg: gpd.GeoDataFrame,
    value_column: str = "Effektivitet",
    title: Optional[str] = None,
    figsize: tuple = (10, 12)
):
    """
    Skapar statisk karta med matplotlib.
    
    Args:
        gdf_agg: GeoDataFrame med aggregerade områden
        value_column: Kolumn att visualisera
        title: Kartans titel
        figsize: Figur-storlek (width, height)
        
    Returns:
        matplotlib Figure-objekt
        
    Note:
        Används för PDF-export eller när interaktivitet ej krävs.
    """
    import matplotlib.pyplot as plt
    
    fig, ax = plt.subplots(figsize=figsize)
    
    gdf_agg.plot(
        column=value_column,
        cmap="Blues",
        linewidth=0.2,
        ax=ax,
        edgecolor="0.8",
        legend=True,
        missing_kwds={
            "color": "lightgray",
            "edgecolor": "white",
            "label": "Utan DEA-data"
        }
    )
    
    if title is None:
        title = f"{value_column} per geografiskt verksamhetsområde"
    
    ax.set_title(title, fontsize=13, pad=20)
    ax.axis("off")
    
    if len(ax.get_figure().get_axes()) > 1:
        cbar = ax.get_figure().get_axes()[1]
        cbar.set_ylabel(value_column, rotation=270, labelpad=20)
    
    plt.tight_layout()
    return fig
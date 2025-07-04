"""
Modellspecifikation:
Visualiserar effektivitet eller effektiviseringskrav geografiskt per nätområde, baserat på DEA- eller PyStoned-modeller.
Matchning sker på REId mellan modellresultat och shapefil från Ei över svenska nätområden.

Motivering:
Geografisk visualisering ger intuitiv översikt av var i landet elnätsföretag är mer eller mindre effektiva
eller utsatta för höga effektiviseringskrav.

Kräver:
- geopandas
- folium
- streamlit_folium
"""

import geopandas as gpd
import pandas as pd
import streamlit as st
import folium
from streamlit_folium import st_folium

@st.cache_data
def load_shapes():
    import geopandas as gpd
    import pandas as pd

    shp_path = "data/Samtliga nätföretags del- och verksamhetsområden.shp"
    gdf = gpd.read_file(shp_path)

    print("\n🗺️ SHAPEFILE LÄST IN")
    print("Kolumner:", list(gdf.columns))
    print("Antal rader före expansion:", len(gdf))

    # Dela REId-listor
    gdf["REId_list"] = gdf["Redovisnin"].astype(str).str.split(",")

    # Skapa en rad per REId
    gdf = gdf.explode("REId_list").reset_index(drop=True)
    gdf["REId"] = gdf["REId_list"].str.strip()
    gdf = gdf.drop(columns=["REId_list"])

    print("Antal rader efter expansion:", len(gdf))
    print("Unika REId:", gdf["REId"].nunique())
    print("Antal saknade REId:", gdf["REId"].isna().sum())

    return gdf


def debug_reid_matchning(gdf_shapes, df_resultat):
    shapefile_reid = set(gdf_shapes["REId"].dropna().unique())
    resultat_reid = set(df_resultat["REId"].dropna().unique())

    saknas_i_resultat = shapefile_reid - resultat_reid
    saknas_i_shapefile = resultat_reid - shapefile_reid

    print("\n🔍 REId-matchning:")
    print(f"REId i shapefilen men saknas i resultatet: {len(saknas_i_resultat)}")
    print("Exempel:", list(saknas_i_resultat)[:5])
    print(f"REId i resultatet men saknas i shapefilen: {len(saknas_i_shapefile)}")
    print("Exempel:", list(saknas_i_shapefile)[:5])


def show_heatmap(df_resultat, karttyp="Statisk", indikator="Effektivitet"):
    st.subheader("Geografisk heatmap")

    # Ladda kartgeometri
    gdf_shapes = load_shapes()

    print("Kolumner i shapefilen:", gdf_shapes.columns)
    print("Unika REId i shapefilen:", gdf_shapes["REId"].nunique())
    print("Totalt antal rader i shapefilen:", len(gdf_shapes))
    print("Antal saknade REId:", gdf_shapes["REId"].isna().sum())


    # Förbered data
    df = df_resultat[["REId", "Företag", indikator]].copy()
    df["REId"] = df["REId"].str.strip()
    gdf = gdf_shapes.merge(df, on="REId", how="left")
    debug_reid_matchning(gdf_shapes, df)

    statisk_vy = (karttyp == "Statisk")

    if statisk_vy:
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(10, 12))
        gdf.plot(
            column=indikator,
            cmap="BuPu",
            linewidth=0.2,
            ax=ax,
            edgecolor="0.8",
            legend=True
        )
        ax.set_title(f"{indikator} per nätområde", fontsize=14)
        ax.axis("off")
        st.pyplot(fig)

    else:
        tooltip_fields = ["Företag", "Delområde", indikator] if indikator in gdf.columns else ["Företag", "Delområde"]
        tooltip_aliases = ["Företag", "Nätområde", indikator] if indikator in gdf.columns else ["Företag", "Nätområde"]

        m = folium.Map(location=[62.0, 15.0], zoom_start=5, tiles="cartodb positron")

        folium.Choropleth(
            geo_data=gdf,
            name="Choropleth",
            data=gdf,
            columns=["REId", indikator],
            key_on="feature.properties.REId",
            fill_color="BuPu",
            fill_opacity=0.7,
            line_opacity=0.2,
            nan_fill_color="gray",
            threshold_scale=[0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
            legend_name=indikator
        ).add_to(m)

        folium.GeoJson(
            gdf,
            name="Nätområden",
            tooltip=folium.features.GeoJsonTooltip(fields=tooltip_fields, aliases=tooltip_aliases)
        ).add_to(m)

        st_folium(m, use_container_width=True)

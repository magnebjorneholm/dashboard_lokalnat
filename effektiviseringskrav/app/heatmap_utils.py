import geopandas as gpd
import streamlit as st

@st.cache_data
def load_shapes():
    shp_path = "effektiviseringskrav/data/Samtliga nätföretags del- och verksamhetsområden.shp"
    gdf = gpd.read_file(shp_path)

    print("\n🗺️ SHAPEFILE LÄST IN")
    print("Kolumner:", list(gdf.columns))
    print("Antal rader före explosion:", len(gdf))

    # Dela upp rader med flera REId
    gdf["REId_list"] = gdf["Redovisnin"].astype(str).str.split(",")
    gdf = gdf.explode("REId_list").reset_index(drop=True)
    gdf["REId"] = gdf["REId_list"].str.strip()
    gdf = gdf.drop(columns=["REId_list"])

    # Skapa ett unikt ID per polygon (baserat på geometrin)
    gdf["geom_id"] = gdf["geometry"].apply(lambda g: hash(g.wkb))

    print("Antal rader efter explosion:", len(gdf))
    print("Unika REId:", gdf["REId"].nunique())
    print("Unika polygoner (geom_id):", gdf["geom_id"].nunique())

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


def create_heatmap(df_resultat, indikator="Effektivitet"):
    st.subheader("Geografisk heatmap")

    gdf_shapes = load_shapes()
    df = df_resultat[["REId", indikator]].copy()
    df["REId"] = df["REId"].str.strip()

    gdf = gdf_shapes.merge(df, on="REId", how="left")
    gdf_agg = gdf.groupby("geom_id").agg({"geometry": "first", indikator: "mean"}).reset_index()
    gdf_agg = gpd.GeoDataFrame(gdf_agg, geometry="geometry", crs=gdf.crs)


    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(10, 12))
    gdf_agg.plot(
            column=indikator,
            cmap="BuPu",
            linewidth=0.2,
            ax=ax,
            edgecolor="0.8",
            legend=True,
            missing_kwds={"color": "lightgray", "edgecolor": "white", "label": "Ingen data"}
        )
    ax.set_title(f"{indikator} per geografiskt verksamhetsområde (medel om flera REId)", fontsize=13)
    ax.axis("off")
    st.pyplot(fig)


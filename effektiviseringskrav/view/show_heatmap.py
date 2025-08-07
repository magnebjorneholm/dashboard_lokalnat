import streamlit as st
from effektiviseringskrav.app.run_logger import list_runs, load_run
from effektiviseringskrav.app.heatmap_utils import show_heatmap, load_shapes
from effektiviseringskrav.app.spatial_analysis import lägg_till_grannsnitt
import geopandas as gpd

def show_heatmap():
    st.header("Geografisk karta")

    runs = list_runs()
    if not runs:
        st.warning("Inga modellkörningar hittades.")
        st.stop()

    run_id = st.selectbox("Välj körning", runs, index=0)
    _, df_resultat = load_run(run_id)

    karttyp = st.selectbox("Välj karttyp", ["Statisk", "Dynamisk"])

    möjliga_indikatorer = ["Effektivitet"]
    if "Supereffektivitet" in df_resultat.columns:
        möjliga_indikatorer.append("Supereffektivitet")

    indikator = st.selectbox("Välj indikator", möjliga_indikatorer)
    if "visa_karta" not in st.session_state:
        st.session_state.visa_karta = False

    if st.button("Visa karta", key="visa_karta_button"):
        st.session_state.visa_karta = True

    if st.session_state.visa_karta:
        show_heatmap(df_resultat, karttyp=karttyp, indikator=indikator)

        st.subheader("Jämför med grannar")

        gdf_shapes = load_shapes()
        df_merge = df_resultat[["REId", "Företag", indikator]].copy()
        gdf_shapes = gdf_shapes.merge(df_merge, on="REId", how="left")
        gdf_shapes = gpd.GeoDataFrame(gdf_shapes, geometry="geometry", crs=gdf_shapes.crs)

        st.subheader("Parametrar")
        metod = st.selectbox("Metod", ["knn", "distanceband"], index=0)
        avståndsviktning = st.checkbox("Använd avståndsviktning", value=False)

        if metod == "knn":
            k_val = st.slider("Antal närmaste grannar (k)", 1, 10, 4)
        else:
            d_val = st.slider("Maximalt avstånd (meter)", 1000, 100000, 50000, step=1000)

        if "visa_grannanalys" not in st.session_state:
            st.session_state.visa_grannanalys = False
            st.session_state.gdf_analys = None
            st.session_state.metodtext = None

        if st.button("Kör grannskapsanalys", key="run_neighbour_analysis"):
            st.session_state.visa_grannanalys = True
            st.session_state.metod_val = metod
            st.session_state.avståndsviktning_val = avståndsviktning

            if metod == "knn":
                st.session_state.k_val = k_val
                gdf_analys = lägg_till_grannsnitt(
                    gdf_shapes,
                    indikator=indikator,
                    method="knn",
                    k=k_val,
                    avståndsviktning=avståndsviktning
                )
                st.session_state.gdf_analys = gdf_analys
                st.session_state.metodtext = f"{k_val} närmaste grannar (centroid-baserat)"

            else:
                st.session_state.d_val = d_val
                gdf_analys = lägg_till_grannsnitt(
                    gdf_shapes,
                    indikator=indikator,
                    method="distanceband",
                    distance_threshold=d_val,
                    avståndsviktning=avståndsviktning
                )
                st.session_state.gdf_analys = gdf_analys
                st.session_state.metodtext = f"alla grannar inom {d_val} meter (centroid-baserat)"

        if st.session_state.visa_grannanalys and st.session_state.gdf_analys is not None:
            with st.expander("Visa analys"):
                st.markdown("**Relativ effektivitet jämfört med geografiska grannar**")
                vikttext = "med avståndsviktning" if st.session_state.avståndsviktning_val else "utan avståndsviktning"
                st.markdown(f"_Baseras på {indikator.lower()} och {st.session_state.metodtext}, {vikttext}._")

                df_grann = st.session_state.gdf_analys[["REId", "Företag", indikator, "grannsnitt", "eff_gap"]].dropna().copy()
                df_grann = df_grann.sort_values("eff_gap")

                st.dataframe(df_grann.style
                             .background_gradient(cmap="RdYlGn", subset=["eff_gap"]),
                             use_container_width=True)

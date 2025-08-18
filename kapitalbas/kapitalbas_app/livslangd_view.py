# livslangd_view.py
import streamlit as st
from kapitalbas.kapitalbas_app.livslangd_simulering import simulate_detail, simulate_overview, simulate_trend

def show_livslangd_view():
    st.header("Livslängdssimulering – snapshot 2023")

    # Tabs
    tab1, tab2, tab3 = st.tabs([
        "Detaljläge (komponentnivå)",
        "Översiktsläge (nät×kategori)",
        "Trendläge (nät×år)"
    ])

    # === Detaljläge ===
    with tab1:
        st.subheader("Detaljläge – komponentnivå")
        eko = st.number_input("Ekonomisk livslängd (år)", 1, 100, 30)
        max_age = st.number_input("Maximal livslängd (år)", eko + 1, 150, 50)
        wacc = st.number_input("Kalkylränta (WACC)", 0.0, 0.2, 0.03, step=0.001, format="%.3f")

        if "final_capbase_sample" not in st.session_state:
            st.error("Dataset final_capbase_sample saknas.")
        else:
            detail_df, detail_agg = simulate_detail(
                st.session_state["final_capbase_sample"],
                default_eko=eko,
                default_max=max_age,
                rate=wacc
            )

            st.write("Summering per nät")
            st.dataframe(detail_agg)
            st.write("Detaljerad komponentlista")
            st.dataframe(detail_df)

    # === Översiktsläge ===
    with tab2:
        st.subheader("Översiktsläge – nät×kategori")
        dep_scale = st.slider("Skalningsfaktor avskrivning", 0.5, 1.5, 1.0, step=0.01)
        return_scale = st.slider("Skalningsfaktor ränta", 0.5, 1.5, 1.0, step=0.01)

        if "capbase_compress_tail" not in st.session_state:
            st.error("Dataset capbase_compress_tail saknas.")
        else:
            overview_df = simulate_overview(
                st.session_state["capbase_compress_tail"],
                scale_dep=dep_scale,
                scale_return=return_scale
            )
            st.dataframe(overview_df)

    # === Trendläge ===
    with tab3:
        st.subheader("Trendläge – nät×år")
        dep_scale = st.slider("Skalningsfaktor avskrivning (trend)", 0.5, 1.5, 1.0, step=0.01)
        return_scale = st.slider("Skalningsfaktor ränta (trend)", 0.5, 1.5, 1.0, step=0.01)

        if "capcost_python" not in st.session_state:
            st.error("Dataset capcost_python saknas.")
        else:
            trend_df = simulate_trend(
                st.session_state["capcost_python"],
                dep_scale=dep_scale,
                return_scale=return_scale
            )
            st.dataframe(trend_df)

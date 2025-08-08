# kapitalbas_app/översikt_view.py

import streamlit as st

def show_översikt(capbase_df):
    """Visar KPI-kort för kapitalbas, avskrivningar och räntor, uppdelat i ordinarie och tail."""
    st.subheader("Översikt – Kapitalbas, Avskrivningar och Ränta (Ordinarie & Tail)")

    networks = sorted(capbase_df['id_network'].unique())
    network_choice = st.selectbox("Välj nät", ["Alla"] + networks)

    if network_choice != "Alla":
        view_df = capbase_df[capbase_df['id_network'] == network_choice]
    else:
        view_df = capbase_df.copy()

    # Kolumngrupper
    nuav_ord_cols = [c for c in view_df.columns if c.startswith("nuav_ord")]
    nuav_tail_cols = [c for c in view_df.columns if c.startswith("nuav_tail")]
    dep_ord_cols = [c for c in view_df.columns if c.startswith("dep_ord")]
    dep_tail_cols = [c for c in view_df.columns if c.startswith("dep_tail")]
    ret_ord_cols = [c for c in view_df.columns if c.startswith("return_ord")]
    ret_tail_cols = [c for c in view_df.columns if c.startswith("return_tail")]

    # Summeringar
    nuav_ord_sum = view_df[nuav_ord_cols].sum().sum()
    nuav_tail_sum = view_df[nuav_tail_cols].sum().sum()
    dep_ord_sum = view_df[dep_ord_cols].sum().sum()
    dep_tail_sum = view_df[dep_tail_cols].sum().sum()
    ret_ord_sum = view_df[ret_ord_cols].sum().sum()
    ret_tail_sum = view_df[ret_tail_cols].sum().sum()

    # KPI-kort
    col1, col2, col3 = st.columns(3)
    col4, col5, col6 = st.columns(3)

    col1.metric("Kapitalbas Ordinarie (MSEK)", f"{nuav_ord_sum/1_000_000:,.1f}")
    col2.metric("Avskrivning Ordinarie (MSEK)", f"{dep_ord_sum/1_000_000:,.1f}")
    col3.metric("Ränta Ordinarie (MSEK)", f"{ret_ord_sum/1_000_000:,.1f}")

    col4.metric("Kapitalbas Tail (MSEK)", f"{nuav_tail_sum/1_000_000:,.1f}")
    col5.metric("Avskrivning Tail (MSEK)", f"{dep_tail_sum/1_000_000:,.1f}")
    col6.metric("Ränta Tail (MSEK)", f"{ret_tail_sum/1_000_000:,.1f}")

    st.caption("*Alla sex värden visas alltid – oavsett periodinställningar i andra sektioner.*")
    st.dataframe(view_df.head(20))

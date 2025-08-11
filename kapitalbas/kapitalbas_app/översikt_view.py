# kapitalbas_app/översikt_view.py
import streamlit as st
from kapitalbas.kapitalbas_app.utils import map_year

def show_översikt(capbase_df, capcost_df):
    """
    Visar KPI-kort för kapitalbas, avskrivningar och räntor (ordinarie & tail).
    Filtrering per år enligt gemensam YEAR_MAP.
    """
    st.subheader("Översikt – Kapitalbas, Avskrivningar och Ränta (Ordinarie & Tail)")

    # Mappa år i båda datamängderna
    capbase_df = map_year(capbase_df)
    capcost_df = map_year(capcost_df)

    # Filtrera på nät
    networks = sorted(capbase_df['id_network'].unique())
    network_choice = st.selectbox("Välj nät", ["Alla"] + networks)

    if network_choice != "Alla":
        cb_df = capbase_df[capbase_df['id_network'] == network_choice]
        cc_df = capcost_df[capcost_df['id_network'] == network_choice]
    else:
        cb_df = capbase_df.copy()
        cc_df = capcost_df.copy()

    # Välj år
    available_years = sorted(cb_df["year"].unique())
    year_choice = st.selectbox("Välj år", available_years)
    cb_df = cb_df[cb_df["year"] == year_choice]
    cc_df = cc_df[cc_df["year"] == year_choice]

    # Summeringar
    nuav_ord_sum = cb_df[[c for c in cb_df.columns if c.startswith("nuav_ord")]].sum().sum()
    nuav_tail_sum = cb_df[[c for c in cb_df.columns if c.startswith("nuav_tail")]].sum().sum()
    dep_ord_sum = cc_df[[c for c in cc_df.columns if c.startswith("dep_ord")]].sum().sum()
    dep_tail_sum = cc_df[[c for c in cc_df.columns if c.startswith("dep_tail")]].sum().sum()
    ret_ord_sum = cc_df[[c for c in cc_df.columns if c.startswith("return_ord")]].sum().sum()
    ret_tail_sum = cc_df[[c for c in cc_df.columns if c.startswith("return_tail")]].sum().sum()

    # KPI-kort (MSEK)
    col1, col2, col3 = st.columns(3)
    col4, col5, col6 = st.columns(3)
    
    col1.metric("Kapitalbas Ordinarie (MSEK)", f"{nuav_ord_sum/1_000_000:,.1f}")
    col2.metric("Avskrivning Ordinarie (MSEK)", f"{dep_ord_sum/1_000_000:,.1f}")
    col3.metric("Ränta Ordinarie (MSEK)", f"{ret_ord_sum/1_000_000:,.1f}")
    col4.metric("Kapitalbas Tail (MSEK)", f"{nuav_tail_sum/1_000_000:,.1f}")
    col5.metric("Avskrivning Tail (MSEK)", f"{dep_tail_sum/1_000_000:,.1f}")
    col6.metric("Ränta Tail (MSEK)", f"{ret_tail_sum/1_000_000:,.1f}")

    st.caption(f"*Data för år {year_choice}. Alla värden i miljoner kronor (MSEK).*")
    st.dataframe(cb_df.head(20))

# -*- coding: utf-8 -*-
"""
capcost_view.py
Visar KPI-kort för kapitalkostnader (capcost_a.parquet) per nät och halvår.

Kolumner som används:
    id_network, time,
    capcost_network, capcost_sum,
    dep_ord, dep_tail,
    nuav_ord, nuav_tail,
    return_ord, return_tail
"""

import streamlit as st
import pandas as pd

# Mappning halvår → kod
TIME_LABEL_TO_CODE = {
    "2024h1": 229,
    "2024h2": 230,
    "2025h1": 231,
    "2025h2": 232,
    "2026h1": 233,
    "2026h2": 234,
    "2027h1": 235,
    "2027h2": 236,
}
CODE_TO_TIME_LABEL = {v: k for k, v in TIME_LABEL_TO_CODE.items()}

KPI_COLUMNS = [
    "capcost_network", "capcost_sum",
    "dep_ord", "dep_tail",
    "nuav_ord", "nuav_tail",
    "return_ord", "return_tail",
]

def fmt_msek(x):
    if pd.isna(x):
        return "–"
    return f"{x / 1_000_000:,.2f} MSEK".replace(",", "\u202f")


# ---------------------------------------------------------------------
# Huvudfunktion som anropas i kapitalbas.py
def show_capcost(capcost_df: pd.DataFrame):
    st.subheader("Kapitalkostnader – KPI")

    # Filter i sidopanel
    with st.sidebar:
        st.subheader("Filter")
        time_label = st.selectbox(
            "Halvår",
            options=list(TIME_LABEL_TO_CODE.keys()),
            index=0
        )
        time_code = TIME_LABEL_TO_CODE[time_label]

        # Sortera numeriskt (int) och lägg till "Alla"
        all_networks = sorted(capcost_df["id_network"].unique())
        network_choice = st.selectbox(
            "Välj nät (id_network)",
            options=["Alla"] + all_networks,
            index=0
        )

    # Filtrera data
    if network_choice != "Alla":
        filt_df = capcost_df[
            (capcost_df["time"] == time_code) &
            (capcost_df["id_network"] == network_choice)
        ]
    else:
        filt_df = capcost_df[capcost_df["time"] == time_code]

    # Summera KPI-värden
    kpi_values = filt_df[KPI_COLUMNS].sum(numeric_only=True)

    st.markdown(f"**KPI för {time_label} · Nät: {network_choice}**")

    # KPI-kort: 2 rader × 4 kolumner
    cols = st.columns(4)
    for i, col in enumerate(KPI_COLUMNS[:4]):
        cols[i].metric(col, fmt_msek(kpi_values[col]))

    cols2 = st.columns(4)
    for i, col in enumerate(KPI_COLUMNS[4:]):
        cols2[i].metric(col, fmt_msek(kpi_values[col]))

    # Expander: visa underlag för beräkning
    with st.expander("Visa underlag för beräkning"):
        tmp = filt_df.copy()
        tmp["time_label"] = tmp["time"].map(CODE_TO_TIME_LABEL)
        st.dataframe(tmp, use_container_width=True, hide_index=True)

        st.download_button(
            label="Ladda ner som CSV",
            data=tmp.to_csv(index=False).encode("utf-8"),
            file_name=f"capcost_underlag_{time_label}_{network_choice}.csv",
            mime="text/csv"
        )

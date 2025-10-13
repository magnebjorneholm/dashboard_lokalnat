# kapitalbas_app/tidsserie_view.py

import streamlit as st
import pandas as pd
import altair as alt

YEAR_MAP = {
    229: 2016, 230: 2017, 231: 2018, 232: 2019,
    233: 2020, 234: 2021, 235: 2022, 236: 2023
}


def show_tidsserie(capcost_df):
    """Visar kapitalkostnad över tid, uppdelat i ränta och avskrivning."""
    st.subheader("Kapitalkostnad över tid – uppdelning i ränta och avskrivning")

    networks = sorted(capcost_df['id_network'].unique())
    network_choice = st.selectbox("Välj nät", ["Alla"] + networks)

    # Arbeta på kopia och mappa år
    ts_df = capcost_df.copy()
    ts_df['year'] = ts_df['time'].map(YEAR_MAP).astype(int)

    if network_choice != "Alla":
        ts_df = ts_df[ts_df['id_network'] == network_choice]

    dep_cols = [c for c in ts_df.columns if c.startswith("dep_")]
    ret_cols = [c for c in ts_df.columns if c.startswith("return_")]

    dep_ts = ts_df.groupby('year')[dep_cols].sum().reset_index()
    ret_ts = ts_df.groupby('year')[ret_cols].sum().reset_index()

    ts_plot = pd.DataFrame({
        'year': dep_ts['year'],
        'Avskrivning': dep_ts[dep_cols].sum(axis=1) / 1_000_000,  # till MSEK
        'Ränta': ret_ts[ret_cols].sum(axis=1) / 1_000_000
    })
    ts_plot['Total'] = ts_plot['Avskrivning'] + ts_plot['Ränta']

    chart_data = ts_plot.melt(
        id_vars='year',
        value_vars=['Avskrivning', 'Ränta', 'Total'],
        var_name='Typ',
        value_name='Belopp'
    )

    chart = alt.Chart(chart_data).mark_line(point=True).encode(
        x=alt.X('year:O', title='År'),
        y=alt.Y('Belopp:Q', title='MSEK'),
        color='Typ:N'
    ).properties(width=700, height=400)

    st.altair_chart(chart, width='stretch')

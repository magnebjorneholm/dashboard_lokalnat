# kapitalbas_app/tidsserie_view.py

import streamlit as st
import pandas as pd
import altair as alt
from kapitalbas.kapitalbas_app.utils import map_year

def show_tidsserie(capcost_df):
    """Visar kapitalkostnad över tid, uppdelat i ränta och avskrivning."""
    st.subheader("Kapitalkostnad över tid – uppdelning i ränta och avskrivning")

    networks = sorted(capcost_df['id_network'].unique())
    network_choice = st.selectbox("Välj nät", ["Alla"] + networks)

    # Karta för att översätta "time" till riktiga år
    capcost_df = map_year(capcost_df, time_col="time", year_col="year")

    # Filtrera per nät
    ts_df = capcost_df.copy()
    if network_choice != "Alla":
        ts_df = ts_df[ts_df['id_network'] == network_choice]

    dep_cols = [c for c in ts_df.columns if c.startswith("dep_")]
    ret_cols = [c for c in ts_df.columns if c.startswith("return_")]

    dep_ts = ts_df.groupby('year')[dep_cols].sum().reset_index()
    ret_ts = ts_df.groupby('year')[ret_cols].sum().reset_index()

    # Skapa ny dataframe för tidsserie
    ts_plot = pd.DataFrame({
        'year': dep_ts['year'],
        'Avskrivning': dep_ts[dep_cols].sum(axis=1),
        'Ränta': ret_ts[ret_cols].sum(axis=1)
    })
    ts_plot['Total'] = ts_plot['Avskrivning'] + ts_plot['Ränta']
    ts_plot[['Avskrivning','Ränta','Total']] = ts_plot[['Avskrivning','Ränta','Total']] / 1_000_000


    # Altair-graf
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

    st.altair_chart(chart, use_container_width=True)

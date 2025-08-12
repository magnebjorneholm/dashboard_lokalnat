import streamlit as st

YEAR_CODE = 236  # 2023

def pick_year_columns(df, year_code=YEAR_CODE):
    """Returnerar bara kolumner för valt år och standardiserar namnen (utan suffix)."""
    suffix = f"_{year_code}"
    cols_map = {}
    for base in ["nuav_ord", "nuav_tail", "dep_ord", "dep_tail", "return_ord", "return_tail"]:
        col_name = f"{base}{suffix}"
        if col_name in df.columns:
            cols_map[col_name] = base
    df_year = df[list(cols_map.keys())].rename(columns=cols_map)
    return df_year

def show_översikt(capbase_df):
    """Visar KPI-kort för kapitalbas, avskrivningar och räntor för 2023."""
    st.subheader(f"Översikt – Kapitalbas, Avskrivningar och Ränta (Ordinarie & Tail), år {YEAR_CODE} → 2023")

    networks = sorted(capbase_df['id_network'].unique())
    network_choice = st.selectbox("Välj nät", ["Alla"] + networks)

    if network_choice != "Alla":
        view_df = capbase_df[capbase_df['id_network'] == network_choice]
    else:
        view_df = capbase_df.copy()

    # Hämta årskolumner (utan suffix)
    year_df = pick_year_columns(view_df, YEAR_CODE)

    # Summera per kategori (i SEK)
    sums = year_df.sum().to_dict()

    # KPI-kort
    col1, col2, col3 = st.columns(3)
    col4, col5, col6 = st.columns(3)

    col1.metric("Kapitalbas Ordinarie (SEK)", f"{sums.get('nuav_ord', 0):,.0f}")
    col2.metric("Avskrivning Ordinarie (SEK)", f"{sums.get('dep_ord', 0):,.0f}")
    col3.metric("Ränta Ordinarie (SEK)", f"{sums.get('return_ord', 0):,.0f}")

    col4.metric("Kapitalbas Tail (SEK)", f"{sums.get('nuav_tail', 0):,.0f}")
    col5.metric("Avskrivning Tail (SEK)", f"{sums.get('dep_tail', 0):,.0f}")
    col6.metric("Ränta Tail (SEK)", f"{sums.get('return_tail', 0):,.0f}")

    st.caption("*Värden visas endast för 2023.*")

    # Bygg tabellen från year_df + id_network och cat_encode
    table_df = view_df[["id_network", "cat_encode"]].reset_index(drop=True)
    table_df = table_df.join(year_df.reset_index(drop=True))

    st.dataframe(table_df.head(20))

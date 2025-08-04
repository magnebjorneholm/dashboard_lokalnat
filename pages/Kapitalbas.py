import streamlit as st
import pandas as pd
import altair as alt
import io

# === CACHE ===
@st.cache_data
def load_main_data():
    capbase = pd.read_parquet("kapitalbas_filer/capbase_compress.parquet")
    capcost = pd.read_parquet("kapitalbas_filer/capcost_python.parquet")
    return capbase, capcost

# === TITEL ===
st.title("Kapitalbas")

# === LADDA DATA ===
capbase, capcost = load_main_data()
networks = sorted(capbase['id_network'].unique())

# === VÄLJ SEKTION ===
sektion = st.sidebar.selectbox("Välj del av kapitalbasen", ["Översikt", "Tidsserie", "QA", "Komponenter", "Policy Playground"])

# === SEKTIONER ===
if sektion == "Översikt":
    # Dynamisk sidopanel för Översikt (endast nätval här)
    network_choice = st.sidebar.selectbox("Välj nät", ["Alla"] + networks)

    st.subheader("Översikt – Kapitalbas, Avskrivningar och Ränta (Ordinarie & Tail)")

    # Filtrera på valt nät
    if network_choice != "Alla":
        view_df = capbase[capbase['id_network'] == network_choice]
    else:
        view_df = capbase.copy()

    # Summera alla ordinarie och tail-kolumner separat
    nuav_ord_cols = [c for c in view_df.columns if c.startswith("nuav_ord")]
    nuav_tail_cols = [c for c in view_df.columns if c.startswith("nuav_tail")]
    dep_ord_cols = [c for c in view_df.columns if c.startswith("dep_ord")]
    dep_tail_cols = [c for c in view_df.columns if c.startswith("dep_tail")]
    ret_ord_cols = [c for c in view_df.columns if c.startswith("return_ord")]
    ret_tail_cols = [c for c in view_df.columns if c.startswith("return_tail")]

    # Räkna ut totalsummor
    nuav_ord_sum = view_df[nuav_ord_cols].sum().sum()
    nuav_tail_sum = view_df[nuav_tail_cols].sum().sum()
    dep_ord_sum = view_df[dep_ord_cols].sum().sum()
    dep_tail_sum = view_df[dep_tail_cols].sum().sum()
    ret_ord_sum = view_df[ret_ord_cols].sum().sum()
    ret_tail_sum = view_df[ret_tail_cols].sum().sum()

    # Visa sex KPI-kort
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




elif sektion == "Tidsserie":
    # Dynamisk sidopanel för Tidsserie
    network_choice = st.sidebar.selectbox("Välj nät", ["Alla"] + networks)

    st.subheader("Kapitalkostnad över tid – uppdelning i ränta och avskrivning")

    # === Rätta årtal ===
    year_map = {229: 2016, 230: 2017, 231: 2018, 232: 2019,
                233: 2020, 234: 2021, 235: 2022, 236: 2023}
    capcost['year'] = capcost['time'].map(year_map).astype(int)

    # Filtrera per nät
    ts_df = capcost.copy()
    if network_choice != "Alla":
        ts_df = ts_df[ts_df['id_network'] == network_choice]

    dep_cols = [c for c in ts_df.columns if c.startswith("dep_")]
    ret_cols = [c for c in ts_df.columns if c.startswith("return_")]

    dep_ts = ts_df.groupby('year')[dep_cols].sum().reset_index()
    ret_ts = ts_df.groupby('year')[ret_cols].sum().reset_index()

    ts_plot = pd.DataFrame({
        'year': dep_ts['year'],
        'Avskrivning': dep_ts[dep_cols].sum(axis=1),
        'Ränta': ret_ts[ret_cols].sum(axis=1)
    })
    ts_plot['Total'] = ts_plot['Avskrivning'] + ts_plot['Ränta']

    # === Altair Chart för snygga årtal ===
    chart_data = ts_plot.melt(id_vars='year', value_vars=['Avskrivning', 'Ränta', 'Total'], var_name='Typ', value_name='Belopp')
    chart = alt.Chart(chart_data).mark_line(point=True).encode(
        x=alt.X('year:O', title='År'),
        y=alt.Y('Belopp:Q', title='MSEK'),
        color='Typ:N'
    ).properties(width=700, height=400)

    st.altair_chart(chart, use_container_width=True)



elif sektion == "QA":
    # Dynamisk sidopanel för QA (just nu minimal)
    st.sidebar.info("QA-fliken använder inga filter ännu.")

    st.subheader("QA – Jämför aggregeringar")
    st.warning("QA-fliken är pausad tills vi har en 'light' komponentladdning.")



elif sektion == "Komponenter":
    st.subheader("Komponenter – Analys på anläggningsnivå")
    st.warning("Negativa värden förekommer (även i metafil), se över varför det är så och om man kan separera? (om det är önskat).")

    # === Ladda komponentdata (cacheat för prestanda) ===
    @st.cache_data
    def load_component_data():
        return pd.read_parquet("kapitalbas_filer/final_capbase_sample.parquet")
    
    comp_df = load_component_data()

    # === Skapa ålder utifrån time_invest ===
    year_map = {
    229: 2016, 230: 2017, 231: 2018, 232: 2019,
    233: 2020, 234: 2021, 235: 2022, 236: 2023
    }
    comp_df["year"] = comp_df["time_invest"].map(year_map)
    comp_df = comp_df.dropna(subset=["year"])  # uteslut komponenter med okänd årskod
    comp_df["age"] = 2024 - comp_df["year"]

    # === Unika nät, kategorier och subkategorier ===
    networks = sorted(comp_df["id_network"].unique())
    categories = sorted(comp_df["cat"].dropna().unique())
    subcategories = sorted(comp_df["subcat"].dropna().unique())

    # === Sidopanel ===
    selected_network = st.sidebar.selectbox("Välj nät", networks)
    min_age = int(comp_df["age"].min())
    max_age = int(comp_df["age"].max())
    age_range = st.sidebar.slider("Filtrera ålder (år)", min_value=min_age, max_value=max_age, value=(min_age, max_age))
    selected_cats = st.sidebar.multiselect("Filtrera kategori (cat)", options=categories, default=categories)
    selected_subcats = st.sidebar.multiselect("Filtrera subkategori (subcat)", options=subcategories, default=subcategories)

    # === Filtrera datan ===
    filtered_df = comp_df[
        (comp_df["id_network"] == selected_network) &
        (comp_df["age"].between(age_range[0], age_range[1])) &
        (comp_df["cat"].isin(selected_cats)) &
        (comp_df["subcat"].isin(selected_subcats))
    ]

    # === DEBUG: visa antalet rader som matchar varje steg ===
    with st.expander("🔎 Felsök filtrering"):
        st.write(f"Antal rader totalt i nät {selected_network}: {len(comp_df[comp_df['id_network'] == selected_network])}")
        st.write(f"Efter åldersfilter: {len(comp_df[(comp_df['id_network'] == selected_network) & comp_df['age'].between(age_range[0], age_range[1])] )}")
        st.write(f"Efter kategori-filter: {len(comp_df[(comp_df['id_network'] == selected_network) & comp_df['cat'].isin(selected_cats)])}")
        st.write(f"Efter subkategori-filter: {len(comp_df[(comp_df['id_network'] == selected_network) & comp_df['subcat'].isin(selected_subcats)])}")
        st.write(f"🔴 Slutlig filtrerad tabell: {len(filtered_df)} rader")

    # === Visa tabell ===
    st.markdown(f"### Komponenter i nät {selected_network}")
    st.dataframe(
        filtered_df[["id_component", "cat", "subcat", "techspec", "volt", "time_invest", "age", "nuav"]]
        .sort_values("age", ascending=False)
        .reset_index(drop=True),
        use_container_width=True
    )

    # === Diagram 1: Antal komponenter per kategori ===
    cat_count = filtered_df["cat"].value_counts().reset_index()
    cat_count.columns = ["Kategori", "Antal"]

    st.markdown("### Antal komponenter per kategori")
    st.bar_chart(cat_count.set_index("Kategori"))

    # === Diagram 2: Åldersfördelning (korrigerad) ===
    st.markdown("### Åldersfördelning")

    age_bins = pd.cut(filtered_df["age"], bins=range(0, 81, 5))
    age_dist = age_bins.value_counts().sort_index()

    # Etikettera och sortera kategorier korrekt
    labels = [f"{int(i.left)}–{int(i.right)} år" for i in age_dist.index]
    age_dist.index = pd.CategoricalIndex(labels, ordered=True, categories=labels)

    st.bar_chart(age_dist)

    # === Export-knapp för filtrerad komponenttabell ===
    st.markdown("### Exportera till Excel")

    if not filtered_df.empty:
        export_cols = ["id_component", "cat", "subcat", "techspec", "volt", "time_invest", "age", "nuav"]
        to_export = filtered_df[export_cols].sort_values("age", ascending=False)

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            to_export.to_excel(writer, sheet_name="Komponenter", index=False)
        buffer.seek(0)

        st.download_button(
            label="📥 Ladda ner som Excel",
            data=buffer,
            file_name=f"komponenter_nät_{selected_network}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("Ingen data att exportera – kontrollera filtren.")



elif sektion == "Policy Playground":
    # Dynamisk sidopanel för Policy Playground
    network_choice = st.sidebar.selectbox("Välj nät", ["Alla"] + networks)

    st.subheader("Policy Playground – simulera olika regleringsscenarier")
    st.write("Testa olika kalkylräntor (WACC) och värderingsprinciper (KPI-baserad kapitalbas)")

    # === TABS ===
    tab1, tab2 = st.tabs(["Kalkylränta (WACC)", "KPI-simulering"])

    # === TAB 1: WACC ===
    with tab1:
        st.markdown("#### Simulera ändrad kalkylränta")

        if network_choice != "Alla":
            scenario_df = capbase[capbase['id_network'] == network_choice].copy()
        else:
            scenario_df = capbase.copy()

        wacc_change = st.slider("Ändra kalkylräntan (WACC) ± %", -3.0, 3.0, 0.0, step=0.25)
        rate_factor = 1 + (wacc_change/100)

        ord_cols = [c for c in scenario_df.columns if c.startswith("return_ord")]
        tail_cols = [c for c in scenario_df.columns if c.startswith("return_tail")]

        return_ord_sum = scenario_df[ord_cols].sum().sum() * rate_factor
        return_tail_sum = scenario_df[tail_cols].sum().sum() * rate_factor
        return_total_sum = return_ord_sum + return_tail_sum

        col1, col2, col3 = st.columns(3)
        col1.metric("Total ränta (MSEK)", f"{return_total_sum/1_000_000:,.1f}")
        col2.metric("Ordinarie ränta (MSEK)", f"{return_ord_sum/1_000_000:,.1f}")
        col3.metric("Tail-ränta (MSEK)", f"{return_tail_sum/1_000_000:,.1f}")

   # === TAB 2: KPI-simulering ===
    with tab2:
        st.markdown("#### Simulera förmögenhetsbevarande värdering (KPI-indexering)")

        st.warning("Datafel i nuläget, läs labbjournal")
import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(layout="wide")

# --- 📂 Läs in filer och cacha
@st.cache_data
def load_data():
    capbase = pd.read_parquet("kapitalbas_filer/capbase_compress.parquet")
    capcost = pd.read_parquet("kapitalbas_filer/capcost_python.parquet")
    final_cap = pd.read_parquet("kapitalbas_filer/final_capbase.parquet")
    depreciation = pd.read_parquet("kapitalbas_filer/depreciation.parquet")
    return capbase, capcost, final_cap, depreciation

capbase, capcost, final_cap, depreciation = load_data()

# --- 🗂 Sidebar
st.sidebar.header("Kapitalbasfilter")
networks = sorted(capbase['id_network'].unique())
network_choice = st.sidebar.selectbox("Välj nät", ["Alla"] + networks)
period_choice = st.sidebar.radio("Period", ["Ordinarie", "Tail"])

prefix = "nuav_ord_" if period_choice == "Ordinarie" else "nuav_tail_"
dep_prefix = "dep_ord_" if period_choice == "Ordinarie" else "dep_tail_"
ret_prefix = "return_ord_" if period_choice == "Ordinarie" else "return_tail_"

# --- 📊 Tabs
tab1, tab2, tab3, tab4 = st.tabs(["Översikt", "Tidsserie", "Drill-down", "QA"])

with tab1:
    st.subheader("Översikt av kapitalbas")

    df_view = capbase.copy()
    if network_choice != "Alla":
        df_view = df_view[df_view['id_network'] == network_choice]

    # KPI
    nuav_cols = [c for c in df_view.columns if c.startswith(prefix)]
    dep_cols = [c for c in df_view.columns if c.startswith(dep_prefix)]
    ret_cols = [c for c in df_view.columns if c.startswith(ret_prefix)]

    kpi_value = df_view[nuav_cols].sum().sum()
    kpi_dep = df_view[dep_cols].sum().sum()
    kpi_ret = df_view[ret_cols].sum().sum()

    col1, col2, col3 = st.columns(3)
    col1.metric("Kapitalbas (MSEK)", f"{kpi_value/1_000_000:,.1f}")
    col2.metric("Avskrivningar (MSEK)", f"{kpi_dep/1_000_000:,.1f}")
    col3.metric("Ränta (MSEK)", f"{kpi_ret/1_000_000:,.1f}")

    # Diagram: kapitalbas per kategori
    plot_df = df_view.groupby("cat_encode")[nuav_cols].sum().sum(axis=1).reset_index()
    plot_df.columns = ["Kategori", "Kapitalbas"]

    st.bar_chart(plot_df.set_index("Kategori"))

with tab2:
    st.subheader("Kapitalkostnad – tidsserie")

    ts_df = capcost.copy()
    if network_choice != "Alla":
        ts_df = ts_df[ts_df['id_network'] == network_choice]

    ts_group = ts_df.groupby("time")["capcost_sum"].sum().reset_index()

    st.line_chart(ts_group.set_index("time"))

    # CAGR-beräkning (2018–2024)
    start_val = ts_group.loc[ts_group['time'] == 2018, "capcost_sum"].values[0]
    end_val = ts_group.loc[ts_group['time'] == 2024, "capcost_sum"].values[0]
    cagr = (end_val/start_val)**(1/6) - 1
    st.caption(f"📈 CAGR 2018–2024: {cagr*100:.2f} %")

with tab3:
    st.subheader("Drill-down till komponentnivå")

    if network_choice == "Alla":
        st.warning("Välj ett nät för att se komponenterna.")
    else:
        comp_df = final_cap[final_cap['id_network'] == network_choice]
        st.write(f"Visar {len(comp_df):,} komponenter för nät {network_choice}")

        # Visa en liten tabell
        st.dataframe(comp_df[["id_component", "cat_encode", "time_from", "nuav_2022_existing"]].head(50))

with tab4:
    st.subheader("QA – Advanced")

    # Jämförelse mellan capbase_compress och final_capbase (summor)
    capbase_sum = capbase.groupby("id_network")[nuav_cols].sum().sum(axis=1)
    final_sum = final_cap.groupby("id_network")["nuav_2022_existing"].sum()
    qa_df = pd.DataFrame({"compress_sum": capbase_sum, "final_sum": final_sum})
    qa_df["diff"] = qa_df["compress_sum"] - qa_df["final_sum"]

    st.dataframe(qa_df.head(50))

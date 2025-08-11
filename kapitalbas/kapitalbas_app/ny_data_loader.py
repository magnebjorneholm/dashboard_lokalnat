import pandas as pd
import re
import streamlit as st

# Fast tidskodsmappning enligt nuvarande Ei-format
YEAR_MAP = {
    226: 2013, 227: 2014, 228: 2015, 229: 2016, 230: 2017,
    231: 2018, 232: 2019, 233: 2020, 234: 2021, 235: 2022, 236: 2023
}

desired_id_cols = ["id_component", "id_network", "cat", "subcat"]

def pivot_with_time(df: pd.DataFrame, desired_id_cols: list) -> pd.DataFrame:
    df = df.copy()

    # Säkerställ year från time om möjligt
    if "time" in df.columns and "year" not in df.columns:
        df["year"] = df["time"].map(YEAR_MAP)

    # Identifiera kolumner med årssuffix 226–236
    year_pattern = re.compile(r"(.+?)_(22[6-9]|23[0-6])$")
    value_vars = [c for c in df.columns if year_pattern.match(c)]

    if not value_vars:
        # Ingen pivotering behövs
        return df

    # ID-kolumner som finns i df
    wanted_ids = [c for c in desired_id_cols if c in df.columns]

    # Konstanta kolumner utan suffix (för att behålla metadata)
    non_suffix_cols = [
        c for c in df.columns
        if c not in wanted_ids and not year_pattern.match(c)
    ]

    id_cols = wanted_ids + non_suffix_cols

    # Melt till long-format
    long_df = df.melt(
        id_vars=id_cols,
        value_vars=value_vars,
        var_name="variable_time",
        value_name="value"
    )

    # Separera variabelnamn och tidskod
    long_df[["variable", "time"]] = long_df["variable_time"].str.rsplit("_", n=1, expand=True)
    long_df["time"] = pd.to_numeric(long_df["time"], errors="coerce").astype("Int64")
    long_df["year"] = long_df["time"].map(YEAR_MAP)

    # Unik-nyckel-check före pivotering
    key_cols = id_cols + ["time", "year", "variable"]
    if long_df[key_cols].duplicated().any():
        dups = long_df[long_df[key_cols].duplicated()][key_cols].head(5)
        raise ValueError(
            "Duplikat vid pivotering – nyckeln är inte unik. Exempel på dubbletter:\n"
            f"{dups}"
        )

    # Pivot tillbaka till wide-format
    df_pivoted = (
        long_df
        .drop(columns=["variable_time"])
        .pivot(index=id_cols + ["time", "year"], columns="variable", values="value")
        .reset_index()
    )

    # Platta ut kolumnindex om pivot skapat MultiIndex
    df_pivoted.columns = [str(c) for c in df_pivoted.columns]

    return df_pivoted


# ===== Laddningsfunktioner med caching =====
@st.cache_data
def load_final_capbase():
    return pivot_with_time(pd.read_parquet("kapitalbas/kapitalbas_filer/final_capbase.parquet"), desired_id_cols)

@st.cache_data
def load_depreciation_compress():
    return pivot_with_time(pd.read_parquet("kapitalbas/kapitalbas_filer/depreciation_compress.parquet"), desired_id_cols)

@st.cache_data
def load_capbase_compress_tail():
    return pivot_with_time(pd.read_parquet("kapitalbas/kapitalbas_filer/capbase_compress_tail.parquet"), desired_id_cols)

@st.cache_data
def load_returns_compress_p():
    return pivot_with_time(pd.read_parquet("kapitalbas/kapitalbas_filer/returns_compress_p.parquet"), desired_id_cols)

@st.cache_data
def load_returns_compress():
    return pivot_with_time(pd.read_parquet("kapitalbas/kapitalbas_filer/returns_compress.parquet"), desired_id_cols)

@st.cache_data
def load_depreciation():
    return pivot_with_time(pd.read_parquet("kapitalbas/kapitalbas_filer/depreciation.parquet"), desired_id_cols)

@st.cache_data
def load_capbase_compress():
    return pivot_with_time(pd.read_parquet("kapitalbas/kapitalbas_filer/capbase_compress.parquet"), desired_id_cols)

@st.cache_data
def load_capcost_python():
    return pivot_with_time(pd.read_parquet("kapitalbas/kapitalbas_filer/capcost_python.parquet"), desired_id_cols)

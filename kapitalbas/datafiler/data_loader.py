import streamlit as st
import pandas as pd


@st.cache_data
def load_dmu_volymer():
    return pd.read_csv("effektiviseringskrav/data/dmu_volymer.csv")

@st.cache_data  
def load_reconciliation():
    return pd.read_csv("effektiviseringskrav/data/reconciliation_id_network_firm_dmu.csv")

# === MELLANDATA ===

@st.cache_data
def load_capbase_b_sample():
    return pd.read_parquet("kapitalbas/datafiler/mellandata/capbase_b_sample.parquet")

@st.cache_data
def load_capbase_b():
    return pd.read_parquet("kapitalbas/datafiler/mellandata/capbase_b.parquet")

@st.cache_data
def load_capbase_compress_tail_sample():
    return pd.read_parquet("kapitalbas/datafiler/mellandata/capbase_compress_tail_sample.parquet")

@st.cache_data
def load_capbase_compress_tail():
    return pd.read_parquet("kapitalbas/datafiler/mellandata/capbase_compress_tail.parquet")

@st.cache_data
def load_capbase_compress():
    return pd.read_parquet("kapitalbas/datafiler/mellandata/capbase_compress.parquet")

@st.cache_data
def load_depreciation_compress_sample():
    return pd.read_parquet("kapitalbas/datafiler/mellandata/depreciation_compress_sample_1_and_3035.parquet")

@st.cache_data
def load_depreciation_compress():
    return pd.read_parquet("kapitalbas/datafiler/mellandata/depreciation_compress.parquet")

@st.cache_data
def load_depreciation():
    return pd.read_parquet("kapitalbas/datafiler/mellandata/depreciation.parquet")

@st.cache_data
def load_returns_compress_sample():
    return pd.read_parquet("kapitalbas/datafiler/mellandata/returns_compress_sample.parquet")

@st.cache_data
def load_returns_compress():
    return pd.read_parquet("kapitalbas/datafiler/mellandata/returns_compress.parquet")


# === RÅDATA ===

@st.cache_data
def load_capbase_a_sample():
    return pd.read_parquet("kapitalbas/datafiler/rådata/capbase_a_sample.parquet")

@st.cache_data
def load_capbase_a():
    return pd.read_parquet("kapitalbas/datafiler/rådata/capbase_a.parquet")


# === SLUTDATA ===

@st.cache_data
def load_capcost_a_sample():
    return pd.read_parquet("kapitalbas/datafiler/slutdata/capcost_a_sample_1_and_3035.parquet")

@st.cache_data
def load_capcost_a():
   return pd.read_parquet("kapitalbas/datafiler/slutdata/capcost_a.parquet")

@st.cache_data
def load_capcost_python():
    return pd.read_parquet("kapitalbas/datafiler/slutdata/capcost_python.parquet")

@st.cache_data
def load_final_capbase_sample():
    return pd.read_parquet("kapitalbas/datafiler/slutdata/final_capbase_sample.parquet")

@st.cache_data
def load_final_capbase():
    return pd.read_parquet("kapitalbas/datafiler/slutdata/final_capbase.parquet")

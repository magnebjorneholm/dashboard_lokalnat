# kapitalbas_app/data_loader.py

import streamlit as st
import pandas as pd

# === HUVUDDATA ===

@st.cache_data
def load_main_data():
    """Laddar aggregerad kapitalbas samt kapitalkostnader."""
    capbase = pd.read_parquet("kapitalbas/kapitalbas_filer/capbase_compress.parquet")
    capcost = pd.read_parquet("kapitalbas/kapitalbas_filer/capcost_python.parquet")
    return capbase, capcost

# === KOMPONENTDATA ===

@st.cache_data
def load_component_sample():
    """Laddar komponentdata för tre representativa nät (sample)."""
    return pd.read_parquet("kapitalbas/kapitalbas_filer/final_capbase_sample.parquet")

# === TAILDATA ===

@st.cache_data
def load_tail_sample():
    """Laddar tail-data för tre representativa nät."""
    return pd.read_parquet("kapitalbas/kapitalbas_filer/capbase_compress_tail_sample.parquet")

@st.cache_data
def load_tail_full():
    """Laddar tail-data för alla nät (full population)."""
    return pd.read_parquet("kapitalbas/kapitalbas_filer/capbase_compress_tail.parquet")

# === ÖVRIGA MÖJLIGA DATAKÄLLOR ===

@st.cache_data
def load_returns():
    """Laddar nätaggregerade räntor (nominell och prisjusterad)."""
    return pd.read_parquet("kapitalbas/kapitalbas_filer/returns_compress.parquet")

@st.cache_data
def load_depreciation():
    """Laddar aggregerade avskrivningar (matchar kapitalbas tail-tabellen)."""
    return pd.read_parquet("kapitalbas/kapitalbas_filer/depreciation_compress.parquet")

@st.cache_data
def load_capcost_legacy():
    """Laddar äldre kapitalkostnadsflöde (referensdata)."""
    return pd.read_parquet("kapitalbas/kapitalbas_filer/capcost.parquet")

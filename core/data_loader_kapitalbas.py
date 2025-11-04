"""
core/data_loader_kapitalbas.py

Kapitalbas-specifik datainläsning.
Laddar rådata och bearbetade filer från kapitalkostnad/data.

Används av:
- KENT-pipeline (beräkningskedjan)
- Kapitalbas-visualiseringar
"""

import streamlit as st
import pandas as pd


# === RÅDATA ===

@st.cache_data
def load_capbase_a() -> pd.DataFrame:
    """
    Laddar rådata från KENT-inrapportering (capbase_a.parquet).

    Innehåller 510,281 rader × 33 kolumner med:
    - id_comptype, id_component, id_network
    - cat_encode, nuav, ekdep, maxdep
    - Och alla andra KENT-komponenter

    Används av:
    - foretag/view/kent_full_pipeline.py (företagsspecifik beräkningskedja)
    - kapitalbas/beräkningsfiler/Beräkningskedja_capcost/beräkningskedja.py
    """
    try:
        return pd.read_parquet("kapitalkostnad/data/capbase_a.parquet")
    except Exception as e:
        st.error(f"Kunde inte ladda capbase_a rådata: {e}")
        return pd.DataFrame()


# NOTERA: Alla andra funktioner (load_capbase_b, load_capbase_compress, etc.)
# har tagits bort eftersom dessa datafiler inte används i någon aktiv modul.
# De kan återinföras om de behövs i framtiden.

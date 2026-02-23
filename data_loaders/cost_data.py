"""
data_loaders/cost_data.py

Loaders for controllable/non-controllable grunddata parquet files.
Follows the caching pattern from rab_data.py.
"""

import pandas as pd
from pathlib import Path
from typing import Optional
import streamlit as st

# Paths
CONTROLLABLE_DETAIL_PATH = "data/opex/controllable_a.parquet"
CONTROLLABLE_META_PATH = "data/opex/controllable_meta.parquet"
NON_CONTROLLABLE_DETAIL_PATH = "data/opex/non_controllable_a.parquet"


def _find_parquet(filename: str, data_path: Optional[str] = None) -> Path:
    """Find a parquet file in standard locations."""
    candidates = []
    if data_path:
        candidates.append(Path(data_path) / filename)
    candidates.extend([
        Path(filename),
        Path("data") / Path(filename).name,
    ])
    for p in candidates:
        if p.exists():
            return p
    raise FileNotFoundError(f"Could not find {filename}. Tried: {[str(p) for p in candidates]}")


@st.cache_data(ttl=3600, show_spinner=False)
def load_controllable_detail(data_path: Optional[str] = None) -> pd.DataFrame:
    """Load controllable_a.parquet (company × category × year)."""
    path = _find_parquet(CONTROLLABLE_DETAIL_PATH, data_path)
    return pd.read_parquet(path)


@st.cache_data(ttl=3600, show_spinner=False)
def load_controllable_meta(data_path: Optional[str] = None) -> pd.DataFrame:
    """Load controllable_meta.parquet (one row per company)."""
    path = _find_parquet(CONTROLLABLE_META_PATH, data_path)
    return pd.read_parquet(path)


@st.cache_data(ttl=3600, show_spinner=False)
def load_non_controllable_detail(data_path: Optional[str] = None) -> pd.DataFrame:
    """Load non_controllable_a.parquet (company × kent_category × year)."""
    path = _find_parquet(NON_CONTROLLABLE_DETAIL_PATH, data_path)
    return pd.read_parquet(path)

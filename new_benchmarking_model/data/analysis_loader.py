"""
analysis_loader.py — load the committed TOTEX/CAPEX-decomposition analysis tables that
feed the new-benchmarking "Placeholder" chart group.

These tables are the offline output of the analysis in new_benchmarking_model/analysis/
(channel isolation, Shapley attribution, urban proxies). They are sector-level and
identical for every user — computed once offline (heavy live DEA), never recomputed at
request time, the firm is only highlighted. ANALYSIS_OUT_DIR is the single source path.

Pure read of the .csv tables; returns None on any missing/unreadable file so the chart
group degrades to an info note instead of breaking the page.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd
import streamlit as st

# repo root = three levels up: new_benchmarking_model/data/analysis_loader.py
REPO_ROOT = Path(__file__).resolve().parents[2]

# Single source path for the committed analysis tables.
ANALYSIS_OUT_DIR = REPO_ROOT / "new_benchmarking_model" / "analysis" / "out"

_CHANNELS_CSV = "s3_channels.csv"      # per-company channel contributions + urbanity (s3)
_SLOPES_CSV = "s3_slopes.csv"          # channel OLS slopes + bootstrap CIs (s3)
_SHAPLEY_CSV = "s5_shapley_percompany.csv"  # per-company Shapley contributions (s5)
_RESIDUAL_CSV = "s5_residual_decomp.csv"    # residual split: mechanic / input / corners (s5)


def _read(name: str) -> Optional[pd.DataFrame]:
    """Read one analysis table, or None if it is missing/unreadable."""
    path = ANALYSIS_OUT_DIR / name
    try:
        if not path.exists():
            return None
        return pd.read_csv(path)
    except Exception:
        return None


@st.cache_data(ttl=3600)
def load_channels() -> Optional[pd.DataFrame]:
    """Per-company channel contributions (dA_pp, dB_pp) + urbanity_index. None if absent."""
    return _read(_CHANNELS_CSV)


@st.cache_data(ttl=3600)
def load_slopes() -> Optional[pd.DataFrame]:
    """Channel slopes + bootstrap CIs (slope, boot_ci_low, boot_ci_high). None if absent."""
    return _read(_SLOPES_CSV)


@st.cache_data(ttl=3600)
def load_shapley() -> Optional[pd.DataFrame]:
    """Per-company Shapley contributions (phi_*) + residual_vs_current_pp. None if absent."""
    return _read(_SHAPLEY_CSV)


@st.cache_data(ttl=3600)
def load_residual_decomp() -> Optional[pd.DataFrame]:
    """Residual split: phi_mechanic / phi_input + corner values (C1, C4). None if absent."""
    return _read(_RESIDUAL_CSV)

"""
Company directory helpers.

Single source for the company list / name lookups used by the sidebar company
selectors (streamlit_app.py) and the registration dropdown (auth_dialog.py).
Names come from the curated baseline (`COL_DISPLAY_NAME` = "Short (REId)").

Lazily imports the (heavy) baseline loader and caches the result.
"""

from typing import List, Tuple, Dict

import streamlit as st

from config.column_names import (
    COL_COMPANY_NAME,
    COL_COMPANY_NAME_SHORT,
    COL_DISPLAY_NAME,
)


@st.cache_data(ttl=3600)
def get_company_records() -> List[dict]:
    """All companies as dicts with REId + curated names, sorted by short name.

    Each record: {"REId", COL_COMPANY_NAME, COL_COMPANY_NAME_SHORT,
    COL_DISPLAY_NAME, "display"}. Returns [] if baseline data is unavailable.
    """
    try:
        from data_loaders.baseline_data import load_baseline_data
        baseline = load_baseline_data()
        df = baseline.df_all_companies[
            ["REId", COL_COMPANY_NAME, COL_COMPANY_NAME_SHORT, COL_DISPLAY_NAME]
        ].copy()
        df["display"] = df[COL_DISPLAY_NAME]
        return df.sort_values(COL_COMPANY_NAME_SHORT).to_dict("records")
    except Exception:
        return []


@st.cache_data(ttl=3600)
def get_company_name_lookup() -> Dict[str, str]:
    """REId -> short company name."""
    try:
        from data_loaders.baseline_data import load_baseline_data
        baseline = load_baseline_data()
        df = baseline.df_all_companies[["REId", COL_COMPANY_NAME_SHORT]].copy()
        return dict(zip(df["REId"], df[COL_COMPANY_NAME_SHORT]))
    except Exception:
        return {}


@st.cache_data(ttl=3600)
def get_company_full_name_lookup() -> Dict[str, str]:
    """REId -> full company name (e.g. 'Ellevio AB')."""
    try:
        from data_loaders.baseline_data import load_baseline_data
        baseline = load_baseline_data()
        df = baseline.df_all_companies[["REId", COL_COMPANY_NAME]].copy()
        return dict(zip(df["REId"], df[COL_COMPANY_NAME]))
    except Exception:
        return {}


def get_company_display(reid: str) -> str:
    """Display string 'Short (REId)', or the bare REId if lookup fails."""
    if not reid:
        return "None"
    name = get_company_name_lookup().get(reid)
    return f"{name} ({reid})" if name else reid


def get_company_full_name(reid: str) -> str:
    """Full company name for `reid` (for greetings); falls back to display/REId."""
    if not reid:
        return ""
    return get_company_full_name_lookup().get(reid) or get_company_display(reid)


def get_company_options() -> List[Tuple[str, str]]:
    """[(display, REId), ...] sorted by short name — for selectboxes."""
    return [(c["display"], c["REId"]) for c in get_company_records()]

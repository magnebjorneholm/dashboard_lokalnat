"""
State Manager for Regumetrica UI.

Hanterar session state initialisering, reset och atkomst.
"""

import streamlit as st
import copy
from typing import Dict, Any

# Explicit default-struktur for alla modules
DEFAULT_UI_CONFIG: Dict[str, Dict[str, Any]] = {
    "m1_asset_base": {
        "normvalue_adjustments": None,  # Dict[int, float] {cat_encode: multiplier}
        "normvalue_level": "cat",       # 'cat' eller 'subcat'
    },
    "m2_depreciation": {
        "lifetime_adjustments": None,   # Dict[int, Dict[str, int]] {cat_encode: {'ekdep': val, 'maxdep': val}}
        "lifetime_level": "cat",        # 'cat' eller 'subcat'
    },
    "m3_cost_of_capital": {
        "wacc_override": None,  # None = anvand baseline (0.0453)
    },
    "m4_operating_exp": {
        "paverkbara_method": "OPEX",  # "OPEX" eller "TOTEX"
    },
    "m5_efficiency": {
        "trunkering_max": None,    # None = baseline (0.30)
        "trunkering_min": None,    # None = baseline (0.162416)
        "outlier_krav": None,      # None = baseline (0.01)
        "kunddelning": None,       # None = baseline (0.50)
        "realiseringstid": None,   # None = baseline (8)
        "tillsynsperiod": None,    # None = baseline (4)
    },
    "addon_benchmarking": {
        "dea_method": "baseline",  # "baseline" eller "custom"
        "dea_inputs": ["CAPEX", "OPEXp"],
        "dea_outputs": ["CU", "MW", "NS", "MWhl", "MWhh"],
        "dea_rts": "crs",
        "dea_multiplier": 2.0,  # Outlier IQR multiplier
        "dea_q_lower": 25.0,    # Nedre percentil
        "dea_q_upper": 75.0,    # Ovre percentil
    }
}


def init_session_state() -> None:
    """Initialisera session state vid app-start."""
    defaults = {
        "user_reid": None,
        "ui_config": copy.deepcopy(DEFAULT_UI_CONFIG),
        "baseline_result": None,
        "case_result": None,
        "calculation_done": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_case() -> None:
    """Aterstall till nytt case (behall user_reid)."""
    st.session_state["ui_config"] = copy.deepcopy(DEFAULT_UI_CONFIG)
    st.session_state["case_result"] = None
    st.session_state["calculation_done"] = False


def get_module_config(module_key: str) -> Dict[str, Any]:
    """Hamta config for en specifik module."""
    return st.session_state.get("ui_config", {}).get(module_key, {})


def set_module_config(module_key: str, config: Dict[str, Any]) -> None:
    """Satt config for en specifik module."""
    if "ui_config" not in st.session_state:
        st.session_state["ui_config"] = copy.deepcopy(DEFAULT_UI_CONFIG)
    st.session_state["ui_config"][module_key] = config


def get_user_reid() -> str | None:
    """Hamta valt foretags REId."""
    return st.session_state.get("user_reid")


def set_user_reid(reid: str) -> None:
    """Satt valt foretags REId."""
    st.session_state["user_reid"] = reid
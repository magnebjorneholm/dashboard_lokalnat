"""
State Manager för Regumetrica UI.

Hanterar session state initialisering, reset och åtkomst.
"""

import streamlit as st
import copy
from typing import Dict, Any

# Explicit default-struktur för alla modules
DEFAULT_UI_CONFIG: Dict[str, Dict[str, Any]] = {
    "m1_asset_base": {
        # Placeholder för framtida parametrar
    },
    "m2_depreciation": {
        # Placeholder för framtida parametrar
    },
    "m3_cost_of_capital": {
        "wacc_override": None,  # None = använd baseline (0.0453)
    },
    "m4_operating_exp": {
        "paverkbara_method": "OPEX",  # "OPEX" eller "TOTEX"
    },
    "m5_efficiency": {
        "trunkering_max": None,  # None = baseline (0.30)
        "trunkering_min": None,  # None = baseline (0.162416)
        "outlier_krav": None,    # None = baseline (0.01)
    },
    "addon_benchmarking": {
        "dea_method": "baseline",  # "baseline" eller "custom"
        "dea_inputs": ["CAPEX", "OPEXp"],
        "dea_outputs": ["CU", "MW", "NS", "MWhl", "MWhh"],
        "dea_rts": "crs",
        "dea_multiplier": 2.0,  # Outlier IQR multiplier
        "dea_q_lower": 25.0,    # Nedre percentil
        "dea_q_upper": 75.0,    # Övre percentil
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
    """Återställ till nytt case (behåll user_reid)."""
    st.session_state["ui_config"] = copy.deepcopy(DEFAULT_UI_CONFIG)
    st.session_state["case_result"] = None
    st.session_state["calculation_done"] = False


def get_module_config(module_key: str) -> Dict[str, Any]:
    """Hämta config för en specifik module."""
    return st.session_state.get("ui_config", {}).get(module_key, {})


def set_module_config(module_key: str, config: Dict[str, Any]) -> None:
    """Sätt config för en specifik module."""
    if "ui_config" not in st.session_state:
        st.session_state["ui_config"] = copy.deepcopy(DEFAULT_UI_CONFIG)
    st.session_state["ui_config"][module_key] = config


def get_user_reid() -> str | None:
    """Hämta valt företags REId."""
    return st.session_state.get("user_reid")


def set_user_reid(reid: str) -> None:
    """Sätt valt företags REId."""
    st.session_state["user_reid"] = reid
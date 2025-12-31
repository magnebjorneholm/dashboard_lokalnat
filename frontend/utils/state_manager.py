"""
State Manager for Regumetrica UI.

Hanterar session state initialisering, reset och åtkomst.
"""

import streamlit as st
import copy
from typing import Dict, Any

# Explicit default-struktur för alla modules
DEFAULT_UI_CONFIG: Dict[str, Dict[str, Any]] = {
    "m1_asset_base": {
        "normvalue_adjustments": None,  # Dict[int, float] {cat_encode: multiplier}
        "normvalue_level": "cat",       # 'cat' eller 'subcat'
        "kent_file_bytes": None,        # Uppladdad KENT-fil som bytes
        "kent_file_name": None,         # Filnamn för visning
    },
    "m2_depreciation": {
        "lifetime_adjustments": None,   # Dict[int, Dict[str, int]] {cat_encode: {'ekdep': val, 'maxdep': val}}
        "lifetime_level": "cat",        # 'cat' eller 'subcat'
    },
    "m3_cost_of_capital": {
        "wacc_override": None,  # None = använd baseline (0.0453)
    },
    "m3_quality_adjustments": {
        # === On/off switchar ===
        "enable_quality": True,
        "enable_netloss": True,
        "enable_load": True,
        
        # === 3.3 Kvalitetsincitament ===
        # CEMI-korrigering
        "adj_max_cemi4": None,  # None = baseline (0.25)
        
        # AIT-kostnader per kundtyp (kr/kWh)
        # Dict med (ann, sni) -> float, t.ex. {('o', 1): 34.35, ('a', 1): 14.10, ...}
        "ait_costs": None,  # None = baseline
        
        # AIF-kostnader per kundtyp (kr/kW)
        # Dict med (ann, sni) -> float
        "aif_costs": None,  # None = baseline
        
        # === 3.4 Nätförlustincitament ===
        # Delningsfaktor
        "sharing_netloss": None,  # None = baseline (0.75)
        
        # Elpris per år (kr/MWh)
        # Dict med year -> float, t.ex. {2024: 753.44, 2025: 753.44, ...}
        "k_nf": None,  # None = baseline
        
        # === 3.6 Begränsningar ===
        # Max aggregerat incitament (andel av avkastning)
        "adj_max_agg": None,  # None = baseline (1/3)
        
        # === 3.7 KPI-faktorer (avancerat) ===
        # Prisjustering till 2022 års priser, per år
        # Dict med year -> float, t.ex. {2024: 1.1546, ...}
        "kpi": None,  # None = baseline
    },
    "m3_incentive_variables": {
        # === Företagsspecifika incitamentvariabler ===
        # Alla värden är None = använd baseline från all_adjust_vars.csv
        # Om ett värde sätts, appliceras det på ALLA år (2024-2027)
        
        # --- 30.2 Nätförlust ---
        "nf_norm": None,      # Nätförlust norm (andel)
        "nf_obs": None,       # Nätförlust observerad (andel)
        "e_in": None,         # Energi in (MWh)
        
        # --- 30.3 Belastning ---
        "ug_norm": None,      # Utnyttjandegrad norm (andel)
        "ug_obs": None,       # Utnyttjandegrad observerad (andel)
        "k_upstream": None,   # Kostnad överliggande nät (kr)
        
        # --- 30.4 Kvalitet (CEMI4) ---
        "cemi4_norm": None,   # CEMI4 norm (andel)
        "cemi4_obs": None,    # CEMI4 observerad (andel)
        
        # --- 30.4 Kvalitet (AIF observerade) ---
        "aif_a_1_obs": None, "aif_a_2_obs": None, "aif_a_3_obs": None,
        "aif_a_4_obs": None, "aif_a_5_obs": None, "aif_a_6_obs": None,
        "aif_o_1_obs": None, "aif_o_2_obs": None, "aif_o_3_obs": None,
        "aif_o_4_obs": None, "aif_o_5_obs": None, "aif_o_6_obs": None,
        
        # --- 30.4 Kvalitet (AIF norm) ---
        "aif_a_1_norm": None, "aif_a_2_norm": None, "aif_a_3_norm": None,
        "aif_a_4_norm": None, "aif_a_5_norm": None, "aif_a_6_norm": None,
        "aif_o_1_norm": None, "aif_o_2_norm": None, "aif_o_3_norm": None,
        "aif_o_4_norm": None, "aif_o_5_norm": None, "aif_o_6_norm": None,
        
        # --- 30.4 Kvalitet (AIT observerade) ---
        "ait_a_1_obs": None, "ait_a_2_obs": None, "ait_a_3_obs": None,
        "ait_a_4_obs": None, "ait_a_5_obs": None, "ait_a_6_obs": None,
        "ait_o_1_obs": None, "ait_o_2_obs": None, "ait_o_3_obs": None,
        "ait_o_4_obs": None, "ait_o_5_obs": None, "ait_o_6_obs": None,
        
        # --- 30.4 Kvalitet (AIT norm) ---
        "ait_a_1_norm": None, "ait_a_2_norm": None, "ait_a_3_norm": None,
        "ait_a_4_norm": None, "ait_a_5_norm": None, "ait_a_6_norm": None,
        "ait_o_1_norm": None, "ait_o_2_norm": None, "ait_o_3_norm": None,
        "ait_o_4_norm": None, "ait_o_5_norm": None, "ait_o_6_norm": None,
        
        # --- 30.4 Kvalitet (ÅME per kundtyp) ---
        "ame_1": None, "ame_2": None, "ame_3": None,
        "ame_4": None, "ame_5": None, "ame_6": None,
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
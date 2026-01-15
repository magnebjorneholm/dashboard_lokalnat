"""
State Manager for Regumetrica UI.

Handles session state initialization, reset and access.
"""

import streamlit as st
import copy
from typing import Dict, Any, Optional, Set


# Explicit default structure for all modules
DEFAULT_UI_CONFIG: Dict[str, Dict[str, Any]] = {
    "m1_asset_base": {
        # Parameters (affect all companies)
        "general_scaling": None,    # float, 1.0 = no change (Param 1.1.1)
        "cat_scaling": None,        # Dict[int, float] {cat_encode: factor} (Param 1.2.X)
        
        # Variables (affect logged-in company only)
        "var_scaling": None,        # Dict[int, float] {cat_encode: factor} (Var 10.X)
        
        # KENT upload (overrides var_scaling)
        "kent_file_bytes": None,    # Uploaded KENT file as bytes
        "kent_file_name": None,     # Filename for display
    },
    "m2_depreciation": {
        "lifetime_adjustments": None,   # Dict[int, Dict[str, int]] {cat_encode: {'ekdep': val, 'maxdep': val}}
        "lifetime_level": "cat",        # 'cat' or 'subcat'
    },
    "m3_cost_of_capital": {
        "wacc_override": None,  # None = use baseline (0.0453)
    },
    "m3_quality_adjustments": {
        # === On/off switches ===
        "enable_quality": True,
        "enable_netloss": True,
        "enable_load": True,
        
        # === 3.3 Quality incentive ===
        "adj_max_cemi4": None,  # None = baseline (0.25)
        "ait_costs": None,      # Dict with (ann, sni) -> float
        "aif_costs": None,      # Dict with (ann, sni) -> float
        
        # === 3.4 Network loss incentive ===
        "sharing_netloss": None,  # None = baseline (0.75)
        "k_nf": None,             # Dict with year -> float
        
        # === 3.6 Limits ===
        "adj_max_agg": None,  # None = baseline (1/3)
        
        # === 3.7 KPI factors ===
        "kpi": None,  # Dict with year -> float
    },
    "m3_incentive_variables": {
        # === Company-specific incentive variables ===
        # All values None = use baseline from all_adjust_vars.csv
        
        # --- 30.2 Network loss ---
        "nf_norm": None,
        "nf_obs": None,
        "e_in": None,
        
        # --- 30.3 Load ---
        "ug_norm": None,
        "ug_obs": None,
        "k_upstream": None,
        
        # --- 30.4 Quality (CEMI4) ---
        "cemi4_norm": None,
        "cemi4_obs": None,
        
        # --- 30.4 Quality (AIF observed) ---
        "aif_a_1_obs": None, "aif_a_2_obs": None, "aif_a_3_obs": None,
        "aif_a_4_obs": None, "aif_a_5_obs": None, "aif_a_6_obs": None,
        "aif_o_1_obs": None, "aif_o_2_obs": None, "aif_o_3_obs": None,
        "aif_o_4_obs": None, "aif_o_5_obs": None, "aif_o_6_obs": None,
        
        # --- 30.4 Quality (AIF norm) ---
        "aif_a_1_norm": None, "aif_a_2_norm": None, "aif_a_3_norm": None,
        "aif_a_4_norm": None, "aif_a_5_norm": None, "aif_a_6_norm": None,
        "aif_o_1_norm": None, "aif_o_2_norm": None, "aif_o_3_norm": None,
        "aif_o_4_norm": None, "aif_o_5_norm": None, "aif_o_6_norm": None,
        
        # --- 30.4 Quality (AIT observed) ---
        "ait_a_1_obs": None, "ait_a_2_obs": None, "ait_a_3_obs": None,
        "ait_a_4_obs": None, "ait_a_5_obs": None, "ait_a_6_obs": None,
        "ait_o_1_obs": None, "ait_o_2_obs": None, "ait_o_3_obs": None,
        "ait_o_4_obs": None, "ait_o_5_obs": None, "ait_o_6_obs": None,
        
        # --- 30.4 Quality (AIT norm) ---
        "ait_a_1_norm": None, "ait_a_2_norm": None, "ait_a_3_norm": None,
        "ait_a_4_norm": None, "ait_a_5_norm": None, "ait_a_6_norm": None,
        "ait_o_1_norm": None, "ait_o_2_norm": None, "ait_o_3_norm": None,
        "ait_o_4_norm": None, "ait_o_5_norm": None, "ait_o_6_norm": None,
        
        # --- 30.4 Quality (AME per customer type) ---
        "ame_1": None, "ame_2": None, "ame_3": None,
        "ame_4": None, "ame_5": None, "ame_6": None,
    },
    "m4_operating_exp": {
        "paverkbara_method": "OPEX",  # "OPEX" or "TOTEX"
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
        "dea_method": "baseline",  # "baseline" or "custom"
        "dea_inputs": ["CAPEX", "OPEXp"],
        "dea_outputs": ["CU", "MW", "NS", "MWhl", "MWhh"],
        "dea_rts": "crs",
        "dea_multiplier": 2.0,
        "dea_q_lower": 25.0,
        "dea_q_upper": 75.0,
    }
}

# Mapping: module_key -> list of ui_config keys
MODULE_TO_CONFIG_KEYS: Dict[str, list] = {
    "m1": ["m1_asset_base"],
    "m2": ["m2_depreciation"],
    "m3": ["m3_cost_of_capital", "m3_quality_adjustments", "m3_incentive_variables"],
    "m4": ["m4_operating_exp"],
    "m5": ["m5_efficiency"],
    "m7": ["addon_benchmarking"],
}


def init_session_state() -> None:
    """Initialize session state at app start."""
    defaults = {
        # Company selection
        "user_reid": None,
        "user_id_network": None,
        
        # Module configuration
        "ui_config": copy.deepcopy(DEFAULT_UI_CONFIG),
        
        # Calculation results
        "baseline_result": None,
        "case_result": None,
        "calculation_done": False,
        
        # Case management
        "case_id": None,              # UUID if saved, None if new
        "case_name": None,            # User-provided name
        "case_notes": "",             # User's detailed notes
        "selected_modules": set(),    # Modules to configure (empty = all)
        "saved_cases_count": 0,       # For default naming "Case N"
        "case_saved": False,          # True after successful save
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_case() -> None:
    """Reset to new case (keep user_reid and saved_cases_count)."""
    st.session_state["ui_config"] = copy.deepcopy(DEFAULT_UI_CONFIG)
    st.session_state["case_result"] = None
    st.session_state["baseline_result"] = None
    st.session_state["calculation_done"] = False
    
    # Reset case management state
    st.session_state["case_id"] = None
    st.session_state["case_name"] = None
    st.session_state["case_notes"] = ""
    st.session_state["selected_modules"] = set()
    st.session_state["case_saved"] = False
    
    # Clear module checkbox widget keys
    _clear_module_checkbox_keys()


def _clear_module_checkbox_keys() -> None:
    """Clear module checkbox widget keys to force re-initialization."""
    for module_key in MODULE_TO_CONFIG_KEYS.keys():
        widget_key = f"module_select_{module_key}"
        if widget_key in st.session_state:
            del st.session_state[widget_key]


def get_module_config(module_key: str) -> Dict[str, Any]:
    """Get config for a specific module."""
    return st.session_state.get("ui_config", {}).get(module_key, {})


def set_module_config(module_key: str, config: Dict[str, Any]) -> None:
    """Set config for a specific module."""
    if "ui_config" not in st.session_state:
        st.session_state["ui_config"] = copy.deepcopy(DEFAULT_UI_CONFIG)
    st.session_state["ui_config"][module_key] = config


def get_user_reid() -> Optional[str]:
    """Get selected company's REId."""
    return st.session_state.get("user_reid")


def set_user_reid(reid: str) -> None:
    """Set selected company's REId."""
    st.session_state["user_reid"] = reid
    # Also set id_network
    if reid and reid.startswith("REL"):
        try:
            numeric_part = reid.replace("REL", "").lstrip("0")
            st.session_state["user_id_network"] = int(numeric_part) if numeric_part else 0
        except ValueError:
            st.session_state["user_id_network"] = None


def get_user_id_network() -> Optional[int]:
    """Get selected company's id_network."""
    return st.session_state.get("user_id_network")


# =============================================================================
# CASE MANAGEMENT FUNCTIONS
# =============================================================================

def get_case_name() -> Optional[str]:
    """Get current case name."""
    return st.session_state.get("case_name")


def set_case_name(name: str) -> None:
    """Set current case name."""
    st.session_state["case_name"] = name


def get_case_notes() -> str:
    """Get current case notes."""
    return st.session_state.get("case_notes", "")


def set_case_notes(notes: str) -> None:
    """Set current case notes."""
    st.session_state["case_notes"] = notes


def get_selected_modules() -> Set[str]:
    """Get set of selected module keys."""
    return st.session_state.get("selected_modules", set())


def set_selected_modules(modules: Set[str]) -> None:
    """Set selected module keys."""
    st.session_state["selected_modules"] = modules


def is_module_selected(module_key: str) -> bool:
    """
    Check if a module should be rendered/applied.
    
    Returns True only if module is explicitly selected.
    Empty selection = baseline only (no modules rendered/applied).
    """
    selected = get_selected_modules()
    return module_key in selected


def get_default_case_name() -> str:
    """Generate default case name based on saved cases count."""
    count = st.session_state.get("saved_cases_count", 0)
    return f"Case {count + 1}"


def increment_saved_cases_count() -> None:
    """Increment the saved cases counter."""
    current = st.session_state.get("saved_cases_count", 0)
    st.session_state["saved_cases_count"] = current + 1


def set_saved_cases_count(count: int) -> None:
    """Set the saved cases count (used when loading from storage)."""
    st.session_state["saved_cases_count"] = count


def get_case_id() -> Optional[str]:
    """Get current case ID (None if not saved)."""
    return st.session_state.get("case_id")


def set_case_id(case_id: str) -> None:
    """Set current case ID."""
    st.session_state["case_id"] = case_id


def is_case_saved() -> bool:
    """Check if current case has been saved."""
    return st.session_state.get("case_saved", False)


def mark_case_saved() -> None:
    """Mark current case as saved."""
    st.session_state["case_saved"] = True


def mark_case_unsaved() -> None:
    """Mark current case as unsaved (after modifications)."""
    st.session_state["case_saved"] = False


# =============================================================================
# FILTERED CONFIG FOR CALCULATION
# =============================================================================

def get_filtered_ui_config() -> Dict[str, Any]:
    """
    Get ui_config filtered by selected_modules.
    
    Only modules in selected_modules retain their modified values.
    Unselected modules are reset to baseline defaults.
    
    This ensures that only explicitly selected modules affect the calculation.
    
    Returns:
        Filtered ui_config dict (deep copy, safe to modify)
    """
    ui_config = st.session_state.get("ui_config", {})
    selected = get_selected_modules()
    
    # If no modules selected, return defaults (baseline run)
    if len(selected) == 0:
        return copy.deepcopy(DEFAULT_UI_CONFIG)
    
    # Start with deep copy of current config
    filtered = copy.deepcopy(ui_config)
    
    # Reset unselected modules to defaults
    for module_key, config_keys in MODULE_TO_CONFIG_KEYS.items():
        if module_key not in selected:
            for config_key in config_keys:
                if config_key in DEFAULT_UI_CONFIG:
                    filtered[config_key] = copy.deepcopy(DEFAULT_UI_CONFIG[config_key])
    
    return filtered


def get_active_module_changes() -> Dict[str, bool]:
    """
    Get which modules have active (applied) changes.
    
    A module has active changes if:
    1. It is selected in selected_modules
    2. Its ui_config differs from defaults
    
    Returns:
        Dict mapping module_key to has_changes bool
    """
    ui_config = st.session_state.get("ui_config", {})
    selected = get_selected_modules()
    
    result = {}
    
    for module_key, config_keys in MODULE_TO_CONFIG_KEYS.items():
        # If not selected, no active changes
        if len(selected) > 0 and module_key not in selected:
            result[module_key] = False
            continue
        
        # Check if any config differs from default
        has_changes = False
        for config_key in config_keys:
            current = ui_config.get(config_key, {})
            default = DEFAULT_UI_CONFIG.get(config_key, {})
            if current != default:
                has_changes = True
                break
        
        result[module_key] = has_changes
    
    return result
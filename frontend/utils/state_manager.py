"""
State Manager for Regumetrica UI.

Handles session state initialization, reset and access.
Supports section-level selection for modules with multiple configuration areas.
"""

import streamlit as st
import copy
from typing import Dict, Any, Optional, Set

from frontend.common.module_registry import (
    ALL_MODULES,
    parse_selection_key,
    build_selection_key,
    get_ui_config_keys_for_selection,
    get_module,
)


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
    },
    "m3_incentive_variables": {
        # 30.2 Network loss
        "nf_norm": None,
        "nf_obs": None,
        "e_in": None,
        
        # 30.3 Utilization
        "ug_norm": None,
        "ug_obs": None,
        "k_upstream": None,
        
        # 30.4 CEMI4
        "cemi4_norm": None,
        "cemi4_obs": None,
        
        # 30.4 AME per customer type (sni 1-6)
        # 30.4 AIT/AIF stored dynamically
    },
    "m4_operating_exp": {
        "opex_override": None,  # Dict[year, float] or None
    },
    "m5_efficiency": {
        "trunkering_max": None,  # None = baseline (1.0)
        "trunkering_min": None,  # None = baseline (0.85)
        "efficiency_override": None,  # float or None
    },
    "addon_benchmarking": {
        "dea_method": "baseline",  # 'baseline' or 'custom'
        "dea_inputs": None,        # List[str] - input variable names
        "dea_outputs": None,       # List[str] - output variable names
        "dea_rts": "crs",          # 'crs' or 'vrs'
        "dea_orientation": "input",  # 'input' or 'output'
    },
}


# =============================================================================
# REID / ID_NETWORK CONVERSION
# =============================================================================

def reid_to_id_network(reid: str) -> Optional[int]:
    """
    Convert REId to id_network.
    
    REId format: "REL00886" -> 886
    This is the single source of truth for this conversion.
    
    Args:
        reid: REId string (e.g., "REL00886")
        
    Returns:
        id_network as int, or None if invalid
    """
    if not reid or not isinstance(reid, str):
        return None
    if not reid.startswith("REL"):
        return None
    try:
        numeric_part = reid.replace("REL", "").lstrip("0")
        return int(numeric_part) if numeric_part else 0
    except ValueError:
        return None


# =============================================================================
# STATE INITIALIZATION
# =============================================================================

def init_session_state() -> None:
    """Initialize session state with defaults if not present."""
    defaults = {
        # Company selection - user_reid is the ONLY authoritative key
        "user_reid": None,
        # NOTE: user_id_network is NOT stored - derived on-demand via get_user_id_network()
        
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
        "selected_modules": set(),    # Now contains "m1", "m3.wacc", etc.
        "saved_cases_count": 0,       # For default naming "Case N"
        "case_saved": False,          # True after successful save
        
        # Authentication
        "auth_user": None,            # Firebase user object
        "auth_token": None,           # Firebase ID token
        "auth_email": None,           # User's email
        "auth_uid": None,             # Firebase UID
        "auth_role": None,            # 'company' or 'regulator'
        "auth_reid": None,            # REId from claims (company users)
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
    
    # Clear module/section checkbox widget keys
    _clear_selection_widget_keys()


def _clear_selection_widget_keys() -> None:
    """Clear module/section checkbox widget keys to force re-initialization."""
    keys_to_clear = [k for k in st.session_state.keys() 
                     if k.startswith("module_select_") or k.startswith("section_select_")]
    for key in keys_to_clear:
        del st.session_state[key]


# =============================================================================
# MODULE CONFIG FUNCTIONS
# =============================================================================

def get_module_config(module_key: str) -> Dict[str, Any]:
    """Get config for a specific module."""
    return st.session_state.get("ui_config", {}).get(module_key, {})


def set_module_config(module_key: str, config: Dict[str, Any]) -> None:
    """Set config for a specific module."""
    if "ui_config" not in st.session_state:
        st.session_state["ui_config"] = copy.deepcopy(DEFAULT_UI_CONFIG)
    st.session_state["ui_config"][module_key] = config


# =============================================================================
# USER REID FUNCTIONS (Single Source of Truth)
# =============================================================================

def get_user_reid() -> Optional[str]:
    """Get selected company's REId."""
    return st.session_state.get("user_reid")


def set_user_reid(reid: str) -> None:
    """
    Set selected company's REId.
    
    This is the ONLY function that should set user_reid.
    id_network is derived on-demand, not stored.
    """
    st.session_state["user_reid"] = reid


def get_user_id_network() -> Optional[int]:
    """
    Get selected company's id_network.
    
    DERIVED on-demand from user_reid - not stored separately.
    This eliminates synchronization issues.
    """
    reid = st.session_state.get("user_reid")
    return reid_to_id_network(reid)


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


def get_case_id() -> Optional[str]:
    """Get current case ID (None if not saved)."""
    return st.session_state.get("case_id")


def set_case_id(case_id: str) -> None:
    """Set current case ID."""
    st.session_state["case_id"] = case_id


def mark_case_saved() -> None:
    """Mark current case as saved."""
    st.session_state["case_saved"] = True


def is_case_saved() -> bool:
    """Check if current case has been saved."""
    return st.session_state.get("case_saved", False)


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


# =============================================================================
# SELECTION FUNCTIONS (Module and Section level)
# =============================================================================

def get_selected_modules() -> Set[str]:
    """
    Get set of selected module/section keys.
    
    Returns keys like: {"m1", "m3.wacc", "m3.incentive_params", "m5"}
    """
    return st.session_state.get("selected_modules", set())


def set_selected_modules(modules: Set[str]) -> None:
    """Set selected module/section keys."""
    st.session_state["selected_modules"] = modules


def is_module_selected(module_key: str) -> bool:
    """
    Check if a module has any selection (module itself or any section).
    
    For modules without sections: checks if module_key in selected.
    For modules with sections: checks if any section is selected.
    """
    selected = get_selected_modules()
    module = get_module(module_key)
    
    if not module.has_sections:
        return module_key in selected
    
    # Check if any section is selected
    for section in module.sections:
        if build_selection_key(module_key, section.key) in selected:
            return True
    return False


def is_section_selected(module_key: str, section_key: str) -> bool:
    """
    Check if a specific section is selected.
    
    Args:
        module_key: e.g., "m3"
        section_key: e.g., "wacc"
    """
    selected = get_selected_modules()
    selection_key = build_selection_key(module_key, section_key)
    return selection_key in selected


def is_selection_key_selected(selection_key: str) -> bool:
    """
    Check if a selection key is selected.
    
    Works for both module keys ("m1") and section keys ("m3.wacc").
    """
    module_key, section_key = parse_selection_key(selection_key)
    
    if section_key:
        return is_section_selected(module_key, section_key)
    else:
        return is_module_selected(module_key)


# =============================================================================
# FILTERED CONFIG (for selected modules/sections only)
# =============================================================================

def get_filtered_ui_config() -> Dict[str, Any]:
    """
    Get ui_config filtered to only include selected modules/sections.
    
    Non-selected items are reset to DEFAULT_UI_CONFIG values.
    This ensures only explicitly selected modules affect calculations.
    """
    selected = get_selected_modules()
    full_config = st.session_state.get("ui_config", {})
    
    # Start with default config
    filtered = copy.deepcopy(DEFAULT_UI_CONFIG)
    
    # Override with actual values for selected items only
    for selection_key in selected:
        config_keys = get_ui_config_keys_for_selection(selection_key)
        for config_key in config_keys:
            if config_key in full_config:
                filtered[config_key] = copy.deepcopy(full_config[config_key])
    
    return filtered


# =============================================================================
# AUTHENTICATION HELPERS
# =============================================================================

def is_authenticated() -> bool:
    """Check if user is authenticated via Firebase."""
    return st.session_state.get("auth_user") is not None


def get_auth_role() -> Optional[str]:
    """Get authenticated user's role ('company' or 'regulator')."""
    return st.session_state.get("auth_role")


def get_auth_reid() -> Optional[str]:
    """Get authenticated user's REId (for company users)."""
    return st.session_state.get("auth_reid")


def get_auth_email() -> Optional[str]:
    """Get authenticated user's email."""
    return st.session_state.get("auth_email")


def is_regulator() -> bool:
    """Check if authenticated user is a regulator."""
    return get_auth_role() == "regulator"
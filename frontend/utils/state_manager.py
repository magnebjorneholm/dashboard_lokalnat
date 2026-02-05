"""
State Manager for Regumetrica UI.

Handles session state initialization, reset and access.
Supports section-level selection for modules with multiple configuration areas.
"""

import streamlit as st
import copy
from datetime import datetime
from typing import Dict, Any, List, Optional, Set

from frontend.common.module_registry import (
    ALL_MODULES,
    parse_selection_key,
    build_selection_key,
    get_ui_config_keys_for_selection,
    get_module,
)

# Maximum number of result snapshots per session
MAX_SNAPSHOTS = 5


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
        
        # Snapshot system: main config backup + snapshot list
        "main_ui_config": None,       # Frozen copy of ui_config at last save/load/promote
        "main_selected_modules": None,  # Frozen copy of selected_modules
        "main_case_result": None,     # The main calculation result (PipelineResult)
        "result_snapshots": [],       # List of snapshot dicts (session-only, max MAX_SNAPSHOTS)
        
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
    
    # Reset snapshot system
    st.session_state["main_ui_config"] = None
    st.session_state["main_selected_modules"] = None
    st.session_state["main_case_result"] = None
    st.session_state["result_snapshots"] = []
    
    # Clear module/section checkbox widget keys
    _clear_selection_widget_keys()
    # Clear all config-related widget keys so widgets re-init from ui_config
    _clear_config_widget_keys()


def _clear_selection_widget_keys() -> None:
    """Clear module/section checkbox widget keys to force re-initialization."""
    keys_to_clear = [k for k in st.session_state.keys() 
                     if k.startswith("module_select_") or k.startswith("section_select_")]
    for key in keys_to_clear:
        del st.session_state[key]


def _clear_config_widget_keys() -> None:
    """Clear all config-related widget keys so Streamlit will reinitialize them.

    This removes keys that begin with common widget prefixes used by modules.
    The list is intentionally conservative but can be extended if new prefixes
    are introduced. Operates directly on `st.session_state`.
    """
    prefixes = [
    "m1_", "m2_", "m3_", "m4_", "m5_", "m5_eff_",
    "addon_", "wacc_", "scaling_",
    ]

    keys_to_clear = [k for k in list(st.session_state.keys()) if any(k.startswith(p) for p in prefixes)]
    for k in keys_to_clear:
        try:
            del st.session_state[k]
        except Exception:
            # Ignore if already removed concurrently
            pass


def get_config_value(module_key: str, param_key: str, default: Any):
    """Read a configuration value from `ui_config` with fallback to `default`.

    If the stored config contains `None` for the parameter, the `default` is
    returned so widgets initialize with baseline values.
    """
    ui = st.session_state.get("ui_config", {})
    module = ui.get(module_key, {}) if isinstance(ui, dict) else {}
    val = module.get(param_key) if isinstance(module, dict) else None
    return default if val is None else val


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


# =============================================================================
# SNAPSHOT SYSTEM
# =============================================================================

def has_main_config() -> bool:
    """Check if a main configuration has been established (first calculation done).

    Uses main_case_result as the gate rather than main_ui_config because
    apply_case_to_session sets main_ui_config at load time (before any
    calculation).  Checking main_case_result ensures restore_main_config
    only triggers after the first actual pipeline run.
    """
    return st.session_state.get("main_case_result") is not None


def set_main_config(
    ui_config: Dict[str, Any],
    selected_modules: Set[str],
    case_result: Any
) -> None:
    """
    Freeze current config as the main config.
    Called after first calculation or after promote.
    
    Args:
        ui_config: The ui_config dict used for this calculation
        selected_modules: The selected modules at calculation time
        case_result: The PipelineResult from this calculation
    """
    st.session_state["main_ui_config"] = copy.deepcopy(ui_config)
    st.session_state["main_selected_modules"] = set(selected_modules)
    st.session_state["main_case_result"] = case_result


def restore_main_config() -> None:
    """
    Restore ui_config, selected_modules and case_result from main config.
    
    Called when user navigates to Define or Configure pages after a
    snapshot-candidate calculation, to ensure they start from the
    committed main configuration rather than the experimental state.
    
    Also restores case_result so that is_snapshot_calculation() returns
    False after restore, preventing re-triggering on subsequent reruns.
    
    Clears widget keys so Streamlit reinitializes from restored config.
    No-op if main config doesn't exist yet.
    """
    if not has_main_config():
        return
    
    st.session_state["ui_config"] = copy.deepcopy(
        st.session_state["main_ui_config"]
    )
    st.session_state["selected_modules"] = set(
        st.session_state["main_selected_modules"]
    )
    st.session_state["case_result"] = st.session_state["main_case_result"]
    
    _clear_selection_widget_keys()
    _clear_config_widget_keys()


def get_snapshots() -> List[Dict[str, Any]]:
    """Get current snapshot list."""
    return st.session_state.get("result_snapshots", [])


def add_snapshot(
    name: str,
    description: str,
    ui_config: Dict[str, Any],
    selected_modules: Set[str],
    case_result: Any
) -> bool:
    """
    Add a result snapshot.
    
    Args:
        name: User-provided snapshot name
        description: User-provided description (can be empty)
        ui_config: Deep copy of ui_config at calculation time
        selected_modules: Copy of selected_modules at calculation time
        case_result: The PipelineResult to snapshot
    
    Returns:
        True if added, False if at max capacity
    """
    snapshots = st.session_state.get("result_snapshots", [])
    
    if len(snapshots) >= MAX_SNAPSHOTS:
        return False
    
    snapshot = {
        "name": name,
        "description": description,
        "ui_config": copy.deepcopy(ui_config),
        "selected_modules": set(selected_modules),
        "case_result": case_result,
        "timestamp": datetime.now().isoformat(),
    }
    
    snapshots.append(snapshot)
    st.session_state["result_snapshots"] = snapshots
    return True


def remove_snapshot(index: int) -> None:
    """Remove snapshot by index."""
    snapshots = st.session_state.get("result_snapshots", [])
    if 0 <= index < len(snapshots):
        snapshots.pop(index)
        st.session_state["result_snapshots"] = snapshots


def promote_snapshot(index: int) -> None:
    """
    Promote a snapshot to become the new main config.
    
    Copies the snapshot's config/modules/result to main_* keys and
    to the working ui_config/selected_modules. Removes the snapshot
    from the list and marks case as unsaved (Firebase is now outdated).
    """
    snapshots = st.session_state.get("result_snapshots", [])
    if not (0 <= index < len(snapshots)):
        return
    
    snapshot = snapshots[index]
    
    # Update main config
    st.session_state["main_ui_config"] = copy.deepcopy(snapshot["ui_config"])
    st.session_state["main_selected_modules"] = set(snapshot["selected_modules"])
    st.session_state["main_case_result"] = snapshot["case_result"]
    
    # Update working state
    st.session_state["ui_config"] = copy.deepcopy(snapshot["ui_config"])
    st.session_state["selected_modules"] = set(snapshot["selected_modules"])
    st.session_state["case_result"] = snapshot["case_result"]
    
    # Mark case as unsaved (Firebase version is now outdated)
    st.session_state["case_saved"] = False
    
    # Remove promoted snapshot from list
    snapshots.pop(index)
    st.session_state["result_snapshots"] = snapshots


def is_snapshot_calculation() -> bool:
    """
    Check if current case_result is a snapshot candidate (not the main result).
    
    Returns True if main exists AND current case_result is a different object
    than main_case_result. Returns False if no main exists (first calc)
    or if viewing the main result.
    """
    if not has_main_config():
        return False
    
    main_result = st.session_state.get("main_case_result")
    current_result = st.session_state.get("case_result")
    
    if main_result is None or current_result is None:
        return False
    
    # Identity check -- same object means it's the main result
    return main_result is not current_result
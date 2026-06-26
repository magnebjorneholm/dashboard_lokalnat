"""
State Manager for Regumetrica UI.

Handles session state initialization, reset and access.
Supports section-level selection for modules with multiple configuration areas.
"""

import hashlib
import json
import streamlit as st
import copy
from typing import Dict, Any, Optional, Set

from config.module_registry import (
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
    },
    "m3_cost_of_capital": {
        "wacc_override": None,  # None = use baseline (0.0453)
    },
    "m3_quality_adjustments": {
        # === On/off switches ===
        "enable_quality": True,
        "enable_netloss": True,
        "enable_load": True,
        
        # === Quality (section 3.3); params carry 3.6.x IDs ===
        "adj_max_cemi4": None,  # CEMI4 correction factor 3.6.6; None = baseline (0.25)
        "ait_costs": None,      # ILE 3.6.7-3.6.18; Dict with (ann, sni) -> float
        "aif_costs": None,      # ILEffekt 3.6.19-3.6.30; Dict with (ann, sni) -> float

        # === Network loss (section 3.4) ===
        "sharing_netloss": None,  # 3.4.2; None = baseline (0.75)
        "k_nf": None,             # 3.4.3 electricity price; Dict with year -> float

        # === Aggregate cap (3.3.1) ===
        "adj_max_agg": None,  # 3.3.1 max total adjustment; None = baseline (1/3)

        # === KPI indexation factors (3.7.1-3.7.4) ===
        "kpi": None,          # Dict with year -> float
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
        "opex_scaling": None,                  # float multiplier (Param 4.1.1)
        "flex_scaling": None,                  # float multiplier (Param 4.1.2)
        "non_adj_scaling": None,               # float multiplier (Param 4.1.3)
        "opex_override": None,                 # float in tkr (Var 40.1.1)
        "flex_override": None,                 # float in tkr (Var 40.1.2)
        "non_controllable_override": None,     # float in tkr (Var 40.2.1)
    },
    "m5_efficiency": {
        "trunkering_max": None,     # 5.2.1 max potential cap; None = baseline (0.30)
        "trunkering_min": None,     # derived from outlier_krav; explicit override only
        "outlier_krav": None,       # 5.3.1 min annual requirement; None = baseline (0.01)
        "realiseringstid": None,    # 5.2.2 realization time; None = baseline (8)
        "kunddelning": None,        # 5.2.3 customer sharing; None = baseline (0.50)
        "paverkbara_method": None,  # 5.4.1 cost base "OPEX"/"TOTEX"; None = baseline (OPEX)
    },
    "m5_benchmarking": {
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
    Convert REId to id_network. Returns None on invalid input.

    Wraps config.case_definition.reid_to_id_network with None-safe handling.
    """
    if not reid or not isinstance(reid, str):
        return None
    try:
        from config.case_definition import reid_to_id_network as _reid_to_id_network
        return _reid_to_id_network(reid)
    except (ValueError, AttributeError):
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
        "_baseline_reid": None,  # tracks which company's baseline pipeline result is cached

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

        # Computed reference: config/modules used in last pipeline run
        "computed_ui_config": None,
        "computed_selected_modules": None,

        # Saved reference: config/modules as last persisted to DB (save or load)
        "saved_ui_config": None,
        "saved_selected_modules": None,

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

    # Reset computed and saved references
    st.session_state["computed_ui_config"] = None
    st.session_state["computed_selected_modules"] = None
    st.session_state["saved_ui_config"] = None
    st.session_state["saved_selected_modules"] = None

    # Clear module/section checkbox widget keys
    _clear_selection_widget_keys()
    # Clear all config-related widget keys so widgets re-init from ui_config
    _clear_config_widget_keys()
    # Reset case identity widgets to empty (setting value, not popping,
    # because Streamlit's internal widget cache ignores popped keys)
    st.session_state["cm_case_name"] = ""
    st.session_state["cm_case_notes"] = ""
    # Clear selectbox/multiselect so they reinitialize
    for key in ("cm_case_select", "cm_compare_multiselect"):
        st.session_state.pop(key, None)

    # Drop the server-side working-state snapshot for this user (lazy import to
    # avoid a load-order cycle with working_state_store).
    from frontend.utils.working_state_store import clear_working_state
    clear_working_state()


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
    keys_to_clear = [
        k for k in list(st.session_state.keys())
        if any(k.startswith(p) for p in _CONFIG_WIDGET_PREFIXES)
    ]
    for k in keys_to_clear:
        try:
            del st.session_state[k]
        except Exception:
            # Ignore if already removed concurrently
            pass


_CONFIG_WIDGET_PREFIXES = (
    "m1_", "m2_", "m3_", "m4_", "m5_", "m5_eff_",
    "addon_", "wacc_", "scaling_",
)


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

    If the company changes, clears calculation results
    to prevent stale data from appearing for the wrong company.
    ui_config and selected_modules are NOT reset so that regulators
    can apply the same configuration across companies.
    """
    previous = st.session_state.get("user_reid")
    st.session_state["user_reid"] = reid

    if previous is not None and previous != reid:
        # Company changed -- clear stale results
        st.session_state["case_result"] = None
        st.session_state["baseline_result"] = None
        st.session_state["calculation_done"] = False
        st.session_state["_baseline_reid"] = None

        # Clear computed reference (results are company-specific)
        st.session_state["computed_ui_config"] = None
        st.session_state["computed_selected_modules"] = None


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
# COMPUTED & SAVED REFERENCE
# =============================================================================

def set_computed_config(
    ui_config: Dict[str, Any],
    selected_modules: Set[str],
) -> None:
    """Store a frozen copy of the config used in the last pipeline run."""
    from datetime import datetime
    st.session_state["computed_ui_config"] = copy.deepcopy(ui_config)
    st.session_state["computed_selected_modules"] = set(selected_modules)
    st.session_state["computed_at"] = datetime.now()


def get_computed_config():
    """Return (computed_ui_config, computed_selected_modules) or (None, None)."""
    return (
        st.session_state.get("computed_ui_config"),
        st.session_state.get("computed_selected_modules"),
    )


def get_computed_at():
    """Return the datetime of the last computation, or None."""
    return st.session_state.get("computed_at")


def set_saved_reference(
    ui_config: Dict[str, Any],
    selected_modules: Set[str],
) -> None:
    """Store a frozen copy of the config as it exists in the database."""
    st.session_state["saved_ui_config"] = copy.deepcopy(ui_config)
    st.session_state["saved_selected_modules"] = set(selected_modules)


def has_saved_reference() -> bool:
    """True if a saved config reference exists (case was saved or loaded)."""
    return st.session_state.get("saved_ui_config") is not None


def _configs_equal(a: Any, b: Any, tol: float = 1e-9) -> bool:
    """Deep comparison of config values with float tolerance."""
    if type(a) != type(b):
        return False
    if isinstance(a, dict):
        if a.keys() != b.keys():
            return False
        return all(_configs_equal(a[k], b[k], tol) for k in a)
    if isinstance(a, float):
        return abs(a - b) < tol
    if isinstance(a, (list, tuple)):
        if len(a) != len(b):
            return False
        return all(_configs_equal(x, y, tol) for x, y in zip(a, b))
    if isinstance(a, set):
        return a == b
    return a == b


def _make_hash_serializable(obj: Any) -> Any:
    """Convert obj to a JSON-safe form for hashing. Bytes are replaced with
    a length placeholder so that the hash depends on presence/size but not
    on compression-level differences."""
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj
    if isinstance(obj, bytes):
        return f"<bytes:{len(obj)}>"
    if isinstance(obj, set):
        return sorted(str(v) for v in obj)
    if isinstance(obj, (list, tuple)):
        return [_make_hash_serializable(v) for v in obj]
    if isinstance(obj, dict):
        return {str(k): _make_hash_serializable(v) for k, v in sorted(obj.items(), key=lambda x: str(x[0]))}
    return str(obj)


def compute_config_hash(ui_config: dict, selected_modules: set) -> str:
    """Deterministic hash of a case configuration.

    Returns the first 16 hex characters of a SHA-256 digest.  Used to detect
    whether a result snapshot still matches the current config.
    """
    payload = {
        "ui_config": _make_hash_serializable(ui_config),
        "selected_modules": sorted(str(m) for m in selected_modules),
    }
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def has_unsaved_changes() -> bool:
    """True if working config differs from the saved reference.

    Returns False when no saved reference exists (new case, nothing to compare).
    Returns True when working state differs from the last saved/loaded config.
    """
    saved_ui = st.session_state.get("saved_ui_config")
    if saved_ui is None:
        return False
    saved_modules = st.session_state.get("saved_selected_modules", set())
    current_ui = st.session_state.get("ui_config", {})
    current_modules = get_selected_modules()
    return not _configs_equal(current_ui, saved_ui) or current_modules != saved_modules


def has_config_changed_since_compute() -> bool:
    """True if working config differs from what was last computed.

    Used to warn users that results may be outdated after editing config.
    Returns False when no computation has been done yet.
    """
    computed_ui = st.session_state.get("computed_ui_config")
    if computed_ui is None:
        return False
    computed_modules = st.session_state.get("computed_selected_modules", set())
    current_ui = st.session_state.get("ui_config", {})
    current_modules = get_selected_modules()
    return not _configs_equal(current_ui, computed_ui) or current_modules != computed_modules


def revert_to_saved() -> None:
    """Revert working state to the saved reference (or defaults for new cases).

    Clears computation results and widget keys so editors reinitialize.
    """
    saved_ui = st.session_state.get("saved_ui_config")
    saved_modules = st.session_state.get("saved_selected_modules")

    if saved_ui is not None:
        st.session_state["ui_config"] = copy.deepcopy(saved_ui)
        st.session_state["selected_modules"] = set(saved_modules)
    else:
        # No saved case — revert to baseline defaults
        st.session_state["ui_config"] = copy.deepcopy(DEFAULT_UI_CONFIG)
        st.session_state["selected_modules"] = set()

    # Clear computation state
    st.session_state["case_result"] = None
    st.session_state["calculation_done"] = False
    st.session_state["computed_ui_config"] = None
    st.session_state["computed_selected_modules"] = None

    _clear_selection_widget_keys()
    _clear_config_widget_keys()
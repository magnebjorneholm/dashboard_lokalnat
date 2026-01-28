"""
Module 3: Incentive Variables

Company-specific input variables for cost of capital adjustments.
Variable-IDs: 30.2 (network loss), 30.3 (utilization), 30.4 (interruption)

Override values apply to ALL years (2024-2027).

Section-based rendering:
- render_incentive_vars() -> 30.X Incentive variables
"""

import streamlit as st
from typing import Dict, Any, List, Tuple

from frontend.utils.state_manager import get_user_reid
from data_loaders.incentive_data import get_user_baseline_variables

MODULE_KEY = "m3_incentive_variables"

# Customer type display order per User Manual Table 9
CUSTOMER_TYPES: List[Tuple[int, int, str]] = [
    (1, 5, "Household"),
    (2, 1, "Agriculture"),
    (3, 3, "Trade/Services"),
    (4, 2, "Industry"),
    (5, 4, "Public sector"),
    (6, 6, "Boundary points"),
]

# Variable-ID mapping per User Manual Table 9
VARIABLE_METADATA = {
    # 30.2 Network loss adjustment
    "nf_norm": ("30.2.1", "Network loss norm", "share", "%.4f"),
    "nf_obs": ("30.2.2", "Network loss observed", "share", "%.4f"),
    "e_in": ("30.2.3", "Energy input", "MWh", "%.0f"),
    
    # 30.3 Utilization rate adjustment
    "ug_norm": ("30.3.1", "Utilization rate norm", "share", "%.4f"),
    "ug_obs": ("30.3.2", "Utilization rate observed", "share", "%.4f"),
    "k_upstream": ("30.3.3", "Cost for upstream network", "kr", "%.0f"),
    
    # 30.4 Interruption adjustment - CEMI4
    "cemi4_norm": ("30.4.1", "CEMI4 norm", "share", "%.4f"),
    "cemi4_obs": ("30.4.2", "CEMI4 observed", "share", "%.4f"),
}

# AME Variable-IDs per customer type (UM Table 9: 30.4.3-30.4.8)
AME_VARIABLE_IDS = {5: "30.4.3", 1: "30.4.4", 3: "30.4.5", 2: "30.4.6", 4: "30.4.7", 6: "30.4.8"}

# AIT Variable-IDs per customer type (UM Table 9: 30.4.9-30.4.32)
AIT_VARIABLE_IDS = {
    # Household (SNI 5)
    (5, 'o', 'norm'): "30.4.9", (5, 'a', 'norm'): "30.4.10",
    (5, 'o', 'obs'): "30.4.11", (5, 'a', 'obs'): "30.4.12",
    # Agriculture (SNI 1)
    (1, 'o', 'norm'): "30.4.13", (1, 'a', 'norm'): "30.4.14",
    (1, 'o', 'obs'): "30.4.15", (1, 'a', 'obs'): "30.4.16",
    # Trade/Services (SNI 3)
    (3, 'o', 'norm'): "30.4.17", (3, 'a', 'norm'): "30.4.18",
    (3, 'o', 'obs'): "30.4.19", (3, 'a', 'obs'): "30.4.20",
    # Industry (SNI 2)
    (2, 'o', 'norm'): "30.4.21", (2, 'a', 'norm'): "30.4.22",
    (2, 'o', 'obs'): "30.4.23", (2, 'a', 'obs'): "30.4.24",
    # Public sector (SNI 4)
    (4, 'o', 'norm'): "30.4.25", (4, 'a', 'norm'): "30.4.26",
    (4, 'o', 'obs'): "30.4.27", (4, 'a', 'obs'): "30.4.28",
    # Boundary points (SNI 6)
    (6, 'o', 'norm'): "30.4.29", (6, 'a', 'norm'): "30.4.30",
    (6, 'o', 'obs'): "30.4.31", (6, 'a', 'obs'): "30.4.32",
}

# AIF Variable-IDs per customer type (UM Table 9: 30.4.33-30.4.56)
AIF_VARIABLE_IDS = {
    # Household (SNI 5)
    (5, 'o', 'norm'): "30.4.33", (5, 'a', 'norm'): "30.4.34",
    (5, 'o', 'obs'): "30.4.35", (5, 'a', 'obs'): "30.4.36",
    # Agriculture (SNI 1)
    (1, 'o', 'norm'): "30.4.37", (1, 'a', 'norm'): "30.4.38",
    (1, 'o', 'obs'): "30.4.39", (1, 'a', 'obs'): "30.4.40",
    # Trade/Services (SNI 3)
    (3, 'o', 'norm'): "30.4.41", (3, 'a', 'norm'): "30.4.42",
    (3, 'o', 'obs'): "30.4.43", (3, 'a', 'obs'): "30.4.44",
    # Industry (SNI 2)
    (2, 'o', 'norm'): "30.4.45", (2, 'a', 'norm'): "30.4.46",
    (2, 'o', 'obs'): "30.4.47", (2, 'a', 'obs'): "30.4.48",
    # Public sector (SNI 4)
    (4, 'o', 'norm'): "30.4.49", (4, 'a', 'norm'): "30.4.50",
    (4, 'o', 'obs'): "30.4.51", (4, 'a', 'obs'): "30.4.52",
    # Boundary points (SNI 6)
    (6, 'o', 'norm'): "30.4.53", (6, 'a', 'norm'): "30.4.54",
    (6, 'o', 'obs'): "30.4.55", (6, 'a', 'obs'): "30.4.56",
}


# =============================================================================
# SECTION RENDER FUNCTION
# =============================================================================

def render_incentive_vars() -> Dict[str, Any]:
    """
    Render M3 incentive variables section: 30.X variables.
    
    Displays company-specific variables with baseline values from 2024.
    User can override any variable; the new value applies to all years.
    
    Returns:
        Dict with variable overrides: {column_name: new_value, ...}
        Only includes variables that differ from baseline.
    """
    config: Dict[str, Any] = {}
    
    st.caption("Variables 30.X: Company-specific incentive inputs. Values shown are baseline (2024).")
    
    user_reid = get_user_reid()
    if not user_reid:
        st.warning("Select a company in the sidebar to view variables.")
        return config
    
    baseline = _load_baseline_cached(user_reid)
    
    if not baseline:
        st.error(f"Could not load baseline data for {user_reid}")
        return config
    
    # 30.2 Network loss adjustment
    with st.expander("30.2 Network loss adjustment", expanded=False):
        _render_netloss_variables(config, baseline)
    
    # 30.3 Utilization rate adjustment
    with st.expander("30.3 Utilization rate adjustment", expanded=False):
        _render_utilization_variables(config, baseline)
    
    # 30.4 Interruption adjustment
    with st.expander("30.4 Interruption adjustment (CEMI4)", expanded=False):
        _render_cemi4_variables(config, baseline)
    
    with st.expander("30.4 Interruption adjustment (AIT observed)", expanded=False):
        _render_ait_obs_variables(config, baseline)
    
    with st.expander("30.4 Interruption adjustment (AIT norm)", expanded=False):
        _render_ait_norm_variables(config, baseline)
    
    with st.expander("30.4 Interruption adjustment (AIF observed)", expanded=False):
        _render_aif_obs_variables(config, baseline)
    
    with st.expander("30.4 Interruption adjustment (AIF norm)", expanded=False):
        _render_aif_norm_variables(config, baseline)
    
    with st.expander("30.4 Interruption adjustment (Annual average power)", expanded=False):
        _render_ame_variables(config, baseline)
    
    return config

# =============================================================================
# HELPERS
# =============================================================================

@st.cache_data(ttl=3600, show_spinner="Loading baseline variables...")
def _load_baseline_cached(user_reid: str) -> Dict[str, float]:
    """Cached loading of baseline variables for a company."""
    return get_user_baseline_variables(user_reid, year=2024)


def _render_variable_input(
    config: Dict[str, Any],
    baseline: Dict[str, float],
    var_name: str,
    var_id: str,
    label: str,
    unit: str,
    format_str: str = "%.4f",
    min_value: float = None,
    max_value: float = None,
    step: float = None,
) -> None:
    """Render a single variable input with baseline comparison."""
    baseline_value = baseline.get(var_name)
    
    if baseline_value is None:
        st.caption(f"{var_id} {label}: *No baseline data*")
        return
    
    current_config = st.session_state.get("ui_config", {}).get(MODULE_KEY, {})
    current_override = current_config.get(var_name)
    
    display_value = current_override if current_override is not None else baseline_value
    
    if step is None:
        if abs(baseline_value) < 1:
            step = 0.0001
        elif abs(baseline_value) < 100:
            step = 0.1
        else:
            step = 100.0
    
    new_value = st.number_input(
        f"{var_id} {label}",
        value=float(display_value),
        min_value=min_value,
        max_value=max_value,
        step=step,
        format=format_str,
        key=f"{MODULE_KEY}_{var_name}",
        help=f"Unit: {unit}"
    )
    
    is_modified = current_override is not None or abs(new_value - baseline_value) > 1e-9
    
    if is_modified:
        st.caption(f":orange[Modified] (baseline: {baseline_value:{format_str.replace('%', '')}})")
        config[var_name] = new_value
    else:
        config[var_name] = None


def _render_netloss_variables(config: Dict[str, Any], baseline: Dict[str, float]) -> None:
    """Render 30.2 Network loss adjustment variables."""
    for var_name in ["nf_norm", "nf_obs", "e_in"]:
        meta = VARIABLE_METADATA[var_name]
        _render_variable_input(
            config, baseline,
            var_name=var_name,
            var_id=meta[0],
            label=meta[1],
            unit=meta[2],
            format_str=meta[3],
            min_value=0.0,
        )


def _render_utilization_variables(config: Dict[str, Any], baseline: Dict[str, float]) -> None:
    """Render 30.3 Utilization rate adjustment variables."""
    for var_name in ["ug_norm", "ug_obs", "k_upstream"]:
        meta = VARIABLE_METADATA[var_name]
        max_val = 1.0 if "share" in meta[2] else None
        _render_variable_input(
            config, baseline,
            var_name=var_name,
            var_id=meta[0],
            label=meta[1],
            unit=meta[2],
            format_str=meta[3],
            min_value=0.0,
            max_value=max_val,
        )


def _render_cemi4_variables(config: Dict[str, Any], baseline: Dict[str, float]) -> None:
    """Render 30.4 CEMI4 variables."""
    for var_name in ["cemi4_norm", "cemi4_obs"]:
        meta = VARIABLE_METADATA[var_name]
        _render_variable_input(
            config, baseline,
            var_name=var_name,
            var_id=meta[0],
            label=meta[1],
            unit=meta[2],
            format_str=meta[3],
            min_value=0.0,
            max_value=1.0,
        )


def _render_ait_obs_variables(config: Dict[str, Any], baseline: Dict[str, float]) -> None:
    """Render AIT observed variables."""
    st.markdown("**Unplanned**")
    for _, sni, customer_label in CUSTOMER_TYPES:
        var_name = f"ait_o_{sni}_obs"
        var_id = AIT_VARIABLE_IDS.get((sni, 'o', 'obs'), "")
        _render_variable_input(
            config, baseline,
            var_name=var_name,
            var_id=var_id,
            label=f"AIT {customer_label}",
            unit="hours",
            format_str="%.6f",
            min_value=0.0,
        )
    
    st.divider()
    
    st.markdown("**Planned**")
    for _, sni, customer_label in CUSTOMER_TYPES:
        var_name = f"ait_a_{sni}_obs"
        var_id = AIT_VARIABLE_IDS.get((sni, 'a', 'obs'), "")
        _render_variable_input(
            config, baseline,
            var_name=var_name,
            var_id=var_id,
            label=f"AIT {customer_label}",
            unit="hours",
            format_str="%.6f",
            min_value=0.0,
        )


def _render_ait_norm_variables(config: Dict[str, Any], baseline: Dict[str, float]) -> None:
    """Render AIT norm variables."""
    st.markdown("**Unplanned**")
    for _, sni, customer_label in CUSTOMER_TYPES:
        var_name = f"ait_o_{sni}_norm"
        var_id = AIT_VARIABLE_IDS.get((sni, 'o', 'norm'), "")
        _render_variable_input(
            config, baseline,
            var_name=var_name,
            var_id=var_id,
            label=f"AIT {customer_label}",
            unit="hours",
            format_str="%.6f",
            min_value=0.0,
        )
    
    st.divider()
    
    st.markdown("**Planned**")
    for _, sni, customer_label in CUSTOMER_TYPES:
        var_name = f"ait_a_{sni}_norm"
        var_id = AIT_VARIABLE_IDS.get((sni, 'a', 'norm'), "")
        _render_variable_input(
            config, baseline,
            var_name=var_name,
            var_id=var_id,
            label=f"AIT {customer_label}",
            unit="hours",
            format_str="%.6f",
            min_value=0.0,
        )


def _render_aif_obs_variables(config: Dict[str, Any], baseline: Dict[str, float]) -> None:
    """Render AIF observed variables."""
    st.markdown("**Unplanned**")
    for _, sni, customer_label in CUSTOMER_TYPES:
        var_name = f"aif_o_{sni}_obs"
        var_id = AIF_VARIABLE_IDS.get((sni, 'o', 'obs'), "")
        _render_variable_input(
            config, baseline,
            var_name=var_name,
            var_id=var_id,
            label=f"AIF {customer_label}",
            unit="count",
            format_str="%.6f",
            min_value=0.0,
        )
    
    st.divider()
    
    st.markdown("**Planned**")
    for _, sni, customer_label in CUSTOMER_TYPES:
        var_name = f"aif_a_{sni}_obs"
        var_id = AIF_VARIABLE_IDS.get((sni, 'a', 'obs'), "")
        _render_variable_input(
            config, baseline,
            var_name=var_name,
            var_id=var_id,
            label=f"AIF {customer_label}",
            unit="count",
            format_str="%.6f",
            min_value=0.0,
        )


def _render_aif_norm_variables(config: Dict[str, Any], baseline: Dict[str, float]) -> None:
    """Render AIF norm variables."""
    st.markdown("**Unplanned**")
    for _, sni, customer_label in CUSTOMER_TYPES:
        var_name = f"aif_o_{sni}_norm"
        var_id = AIF_VARIABLE_IDS.get((sni, 'o', 'norm'), "")
        _render_variable_input(
            config, baseline,
            var_name=var_name,
            var_id=var_id,
            label=f"AIF {customer_label}",
            unit="count",
            format_str="%.6f",
            min_value=0.0,
        )
    
    st.divider()
    
    st.markdown("**Planned**")
    for _, sni, customer_label in CUSTOMER_TYPES:
        var_name = f"aif_a_{sni}_norm"
        var_id = AIF_VARIABLE_IDS.get((sni, 'a', 'norm'), "")
        _render_variable_input(
            config, baseline,
            var_name=var_name,
            var_id=var_id,
            label=f"AIF {customer_label}",
            unit="count",
            format_str="%.6f",
            min_value=0.0,
        )


def _render_ame_variables(config: Dict[str, Any], baseline: Dict[str, float]) -> None:
    """Render Annual average power variables (30.4.3-30.4.8)."""
    for _, sni, customer_label in CUSTOMER_TYPES:
        var_name = f"ame_{sni}"
        var_id = AME_VARIABLE_IDS.get(sni, "")
        _render_variable_input(
            config, baseline,
            var_name=var_name,
            var_id=var_id,
            label=f"Annual average power - {customer_label}",
            unit="kW",
            format_str="%.1f",
            min_value=0.0,
            step=100.0,
        )
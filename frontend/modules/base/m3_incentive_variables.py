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
from config.formatting import format_number
from config.glossary import (
    CUSTOMER_TYPES_ORDERED as CUSTOMER_TYPES,
    INCENTIVE_VARIABLE_META as VARIABLE_METADATA,
    VID_AME as AME_VARIABLE_IDS,
    VID_AIT as AIT_VARIABLE_IDS,
    VID_AIF as AIF_VARIABLE_IDS,
)

MODULE_KEY = "m3_incentive_variables"


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
    
    st.markdown("##### 30.X Incentive Variables")
    st.caption("Company-specific inputs. Values shown are baseline (2024).")
    
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
        _decimals = int(format_str.split('.')[1].rstrip('f')) if '.' in format_str else 0
        st.caption(f":orange[Modified] (baseline: {format_number(baseline_value, _decimals)})")
        config[var_name] = new_value
    else:
        config[var_name] = None


def _render_netloss_variables(config: Dict[str, Any], baseline: Dict[str, float]) -> None:
    """Render 30.2 Network loss adjustment variables."""
    for var_name in ["nf_norm", "nf_obs", "e_in"]:
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
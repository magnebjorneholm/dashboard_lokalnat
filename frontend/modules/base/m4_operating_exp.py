"""
Module 4: Operating Expenditures

Parameters (all 148 companies):
- 4.1.1 Scaling factor adjustable OPEX
- 4.1.2 Scaling factor flexibility services
- 4.1.3 Scaling factor non-adjustable OPEX

Variables (user's company only):
- 40.1.1 Adjusted OPEX (OPEXp)
- 40.1.2 Flexibility service cost
- 40.2.1 Total non-adjustable costs

Section-based rendering:
- render_scaling()   -> 4.1.1-4.1.3 parameter scaling
- render_opex_vars() -> 40.1.1, 40.1.2, 40.2.1 variable overrides
"""

import streamlit as st
from typing import Dict, Any

from frontend.common.parameter_input import parameter_input
from frontend.utils.state_manager import get_config_value
from config.glossary import (
    PID_OPEX_SCALING, PID_FLEX_SCALING, PID_NON_ADJ_SCALING,
    VID_OPEX_ADJUSTABLE, VID_FLEX_SERVICE, VID_NON_ADJUSTABLE,
    get_description,
)

MODULE_KEY = "m4_operating_exp"


def render_scaling() -> Dict[str, Any]:
    """
    Render M4 scaling section: 3 parameter inputs (4.1.1-4.1.3).

    Returns:
        Dict with opex_scaling, flex_scaling, non_adj_scaling (only non-default)
    """
    config: Dict[str, Any] = {}

    st.markdown("##### 4.1 OPEX scaling factors")
    st.caption(
        "Scale operating expenditure components for all 148 companies. "
        "Adjustable OPEX (4.1.1) affects DEA input and triggers re-run. "
        "Flexibility (4.1.2) and non-adjustable (4.1.3) affect revenue frame only."
    )

    # 4.1.1 Scaling factor adjustable OPEX
    val, changed = parameter_input(
        module_key=MODULE_KEY,
        param_id=PID_OPEX_SCALING,
        label=get_description(PID_OPEX_SCALING),
        baseline=1.0,
        value=get_config_value(MODULE_KEY, "opex_scaling", 1.0),
        min_val=0.50,
        max_val=2.00,
        step=0.01,
        format_str="%.2f",
        help_text="Multiplicative scaling for adjustable OPEX (OPEXp). Affects DEA.",
    )
    if changed:
        config["opex_scaling"] = val

    # 4.1.2 Scaling factor flexibility services
    val, changed = parameter_input(
        module_key=MODULE_KEY,
        param_id=PID_FLEX_SCALING,
        label=get_description(PID_FLEX_SCALING),
        baseline=1.0,
        value=get_config_value(MODULE_KEY, "flex_scaling", 1.0),
        min_val=0.50,
        max_val=2.00,
        step=0.01,
        format_str="%.2f",
        help_text="Multiplicative scaling for flexibility service costs. RF only.",
    )
    if changed:
        config["flex_scaling"] = val

    # 4.1.3 Scaling factor non-adjustable OPEX
    val, changed = parameter_input(
        module_key=MODULE_KEY,
        param_id=PID_NON_ADJ_SCALING,
        label=get_description(PID_NON_ADJ_SCALING),
        baseline=1.0,
        value=get_config_value(MODULE_KEY, "non_adj_scaling", 1.0),
        min_val=0.50,
        max_val=2.00,
        step=0.01,
        format_str="%.2f",
        help_text="Multiplicative scaling for non-adjustable costs. RF only.",
    )
    if changed:
        config["non_adj_scaling"] = val

    return config


def render_opex_vars() -> Dict[str, Any]:
    """
    Render M4 variables section: 40.1.1, 40.1.2, 40.2.1.

    Loads user's baseline values and presents number_input for overrides.

    Returns:
        Dict with opex_override, flex_override, non_controllable_override (only overridden)
    """
    config: Dict[str, Any] = {}

    st.markdown("##### 40.X OPEX variables (company-specific)")
    st.caption(
        "Override OPEX values for your company. "
        "Variable overrides trump parameter scaling for your company. "
        "Values in tkr."
    )

    baselines = _load_user_baselines()

    # 40.1.1 Adjusted OPEX (OPEXp)
    bl_opex = baselines.get("opex", 0.0)
    current_opex = get_config_value(MODULE_KEY, "opex_override", None)
    val = st.number_input(
        f"{VID_OPEX_ADJUSTABLE} — {get_description(VID_OPEX_ADJUSTABLE)} (baseline: {bl_opex:,.0f} tkr)",
        value=current_opex if current_opex is not None else bl_opex,
        min_value=0.0,
        step=1000.0,
        format="%.0f",
        key=f"{MODULE_KEY}_var_opex",
        help="Annual OPEXp in tkr. Trumps 4.1.1 scaling for your company.",
    )
    if abs(val - bl_opex) > 0.5:
        config["opex_override"] = val
        st.caption(f":orange[Modified] {VID_OPEX_ADJUSTABLE}: {val:,.0f} tkr (baseline {bl_opex:,.0f})")

    # 40.1.2 Flexibility service cost
    bl_flex = baselines.get("flex", 0.0)
    current_flex = get_config_value(MODULE_KEY, "flex_override", None)
    val = st.number_input(
        f"{VID_FLEX_SERVICE} — {get_description(VID_FLEX_SERVICE)} (baseline: {bl_flex:,.0f} tkr)",
        value=current_flex if current_flex is not None else bl_flex,
        min_value=0.0,
        step=1000.0,
        format="%.0f",
        key=f"{MODULE_KEY}_var_flex",
        help="Period total for flexibility services in tkr. Trumps 4.1.2 scaling.",
    )
    if abs(val - bl_flex) > 0.5:
        config["flex_override"] = val
        st.caption(f":orange[Modified] {VID_FLEX_SERVICE}: {val:,.0f} tkr (baseline {bl_flex:,.0f})")

    # 40.2.1 Total non-adjustable costs
    bl_nc = baselines.get("non_controllable", 0.0)
    current_nc = get_config_value(MODULE_KEY, "non_controllable_override", None)
    val = st.number_input(
        f"{VID_NON_ADJUSTABLE} — {get_description(VID_NON_ADJUSTABLE)} (baseline: {bl_nc:,.0f} tkr)",
        value=current_nc if current_nc is not None else bl_nc,
        min_value=0.0,
        step=1000.0,
        format="%.0f",
        key=f"{MODULE_KEY}_var_nc",
        help="Period total for non-adjustable costs in tkr. Trumps 4.1.3 scaling.",
    )
    if abs(val - bl_nc) > 0.5:
        config["non_controllable_override"] = val
        st.caption(f":orange[Modified] {VID_NON_ADJUSTABLE}: {val:,.0f} tkr (baseline {bl_nc:,.0f})")

    return config


# =============================================================================
# BASELINE LOADER (cached)
# =============================================================================

@st.cache_data(ttl=3600)
def _load_user_baselines_cached(user_reid: str) -> Dict[str, float]:
    """Load baseline OPEX values for user's company."""
    from config.column_names import COL_CONTROLLABLE_AVG, COL_NON_CONTROLLABLE, COL_FLEXIBILITY
    from data_loaders.baseline_data import load_baseline_data
    from calculations.cost_aggregation import aggregate_controllable, aggregate_non_controllable

    baseline = load_baseline_data()

    # OPEXp from df_all_companies (already = SDF-derived medelvärde + neo/4)
    row = baseline.df_all_companies[baseline.df_all_companies["REId"] == user_reid]
    opex = float(row[COL_CONTROLLABLE_AVG].iloc[0]) if not row.empty else 0.0

    # Flexibility from sdf_ir
    ir_row = baseline.sdf_ir[baseline.sdf_ir["REId"] == user_reid]
    flex = float(ir_row[COL_FLEXIBILITY].iloc[0]) if not ir_row.empty else 0.0

    # Non-controllable from aggregation
    nc_result = aggregate_non_controllable(baseline.non_controllable_detail)
    nc_row = nc_result[nc_result["REId"] == user_reid]
    nc = float(nc_row[COL_NON_CONTROLLABLE].iloc[0]) if not nc_row.empty else 0.0

    return {"opex": opex, "flex": flex, "non_controllable": nc}


def _load_user_baselines() -> Dict[str, float]:
    """Get baseline values for current user (from session state)."""
    user_reid = st.session_state.get("user_reid", "")
    if not user_reid:
        return {"opex": 0.0, "flex": 0.0, "non_controllable": 0.0}
    try:
        return _load_user_baselines_cached(user_reid)
    except Exception:
        return {"opex": 0.0, "flex": 0.0, "non_controllable": 0.0}

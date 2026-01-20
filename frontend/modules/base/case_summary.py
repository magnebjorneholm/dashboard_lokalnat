"""
Module: Case Summary

Displays complete summary of all case parameters before calculation.
Shows baseline vs modified values with visual highlighting.
Contains the CALCULATE REVENUE FRAME button.
"""

import streamlit as st
import pandas as pd
from typing import Dict, Any, List, Tuple
import copy

from frontend.utils.state_manager import (
    DEFAULT_UI_CONFIG,
    get_module_config,
    set_module_config,
    get_selected_modules,
    get_filtered_ui_config,
    is_module_selected,
)
from frontend.common.asset_categories import (
    ASSET_CATEGORIES,
    CATEGORY_BY_CODE,
    get_category_name,
)

from frontend.modules.base.m3_cost_of_capital import (
    BASELINE_WACC,
    BASELINE_INCENTIVE,
)
from frontend.modules.base.m5_efficiency import (
    BASELINE_MAX_POTENTIAL,
    BASELINE_REALIZATION_TIME,
    BASELINE_CUSTOMER_SHARING,
    BASELINE_MIN_REQUIREMENT,
)

MODULE_KEY = "case_summary"


def render() -> None:
    """
    Render Case Summary with tabs.
    
    Displays all parameters organized by module with baseline/modified status.
    Modified modules have orange tab names.
    Includes reset buttons per module and the main CALCULATE button.
    """
    st.subheader("Case Summary")
    
    selected_modules = get_selected_modules()
    
    if selected_modules:
        st.caption(
            f"Review parameters for {len(selected_modules)} selected module(s). "
            "Unselected modules will use baseline values."
        )
    else:
        st.caption("No modules selected. Running baseline simulation.")
    
    filtered_config = get_filtered_ui_config()
    
    # Pre-compute selection status for each module
    # Uses is_module_selected() which handles section keys (e.g., "m1.scaling")
    is_selected = {
        "m1": len(selected_modules) == 0 or is_module_selected("m1"),
        "m2": len(selected_modules) == 0 or is_module_selected("m2"),
        "m3": len(selected_modules) == 0 or is_module_selected("m3"),
        "m4": len(selected_modules) == 0 or is_module_selected("m4"),
        "m5": len(selected_modules) == 0 or is_module_selected("m5"),
        "m7": len(selected_modules) == 0 or is_module_selected("m7"),
    }
    
    has_changes = {
        "m1": _check_module_1_changes(filtered_config) and is_selected["m1"],
        "m2": _check_module_2_changes(filtered_config) and is_selected["m2"],
        "m3": _check_module_3_changes(filtered_config) and is_selected["m3"],
        "m4": _check_module_4_changes(filtered_config) and is_selected["m4"],
        "m5": _check_module_5_changes(filtered_config) and is_selected["m5"],
        "m7": _check_module_7_changes(filtered_config) and is_selected["m7"],
    }
    
    has_any_changes = any(has_changes.values())
    
    # Build tab labels - orange if modified
    def tab_label(key: str, name: str) -> str:
        if not is_selected[key]:
            return f":gray[{name}]"
        elif has_changes[key]:
            return f":orange[{name}]"
        return name
    
    tab_labels = [
        tab_label("m1", "1: Regulatory asset base"),
        tab_label("m2", "2: Depreciation"),
        tab_label("m3", "3: Cost of capital"),
        tab_label("m4", "4: Operating expenditures"),
        tab_label("m5", "5: Efficiency incentive"),
        tab_label("m7", "7: Add-on modules"),
    ]
    
    tabs = st.tabs(tab_labels)
    
    with tabs[0]:
        _render_module_1_content(filtered_config, is_selected["m1"], has_changes["m1"])
    
    with tabs[1]:
        _render_module_2_content(filtered_config, is_selected["m2"], has_changes["m2"])
    
    with tabs[2]:
        _render_module_3_content(filtered_config, is_selected["m3"], has_changes["m3"])
    
    with tabs[3]:
        _render_module_4_content(filtered_config, is_selected["m4"], has_changes["m4"])
    
    with tabs[4]:
        _render_module_5_content(filtered_config, is_selected["m5"], has_changes["m5"])
    
    with tabs[5]:
        _render_module_7_content(filtered_config, is_selected["m7"], has_changes["m7"])
    
    # Summary status
    st.divider()
    
    if has_any_changes:
        st.warning("This case has modified parameters (orange tabs above).")
    else:
        st.info("All parameters at baseline values.")
    
    # CALCULATE button
    st.divider()
    
    if st.button("CALCULATE REVENUE FRAME", type="primary", width="stretch"):
        _run_calculation()


# =============================================================================
# CHANGE DETECTION FUNCTIONS
# =============================================================================

def _check_module_1_changes(ui_config: Dict[str, Any]) -> bool:
    """Check if Module 1 has any changes."""
    m1 = ui_config.get("m1_asset_base", {})
    kent_uploaded = m1.get("kent_file_bytes") is not None
    general_scaling = m1.get("general_scaling")
    cat_scaling = m1.get("cat_scaling")
    var_scaling = m1.get("var_scaling")
    
    has_general = general_scaling is not None and general_scaling != 1.0
    has_cat = cat_scaling is not None and len(cat_scaling) > 0
    has_var = var_scaling is not None and len(var_scaling) > 0
    
    return kent_uploaded or has_general or has_cat or has_var


def _check_module_2_changes(ui_config: Dict[str, Any]) -> bool:
    """Check if Module 2 has any changes."""
    m2 = ui_config.get("m2_depreciation", {})
    lifetime_adj = m2.get("lifetime_adjustments")
    return lifetime_adj is not None and len(lifetime_adj) > 0


def _check_module_3_changes(ui_config: Dict[str, Any]) -> bool:
    """Check if Module 3 has any changes."""
    m3_wacc = ui_config.get("m3_cost_of_capital", {})
    m3_qual = ui_config.get("m3_quality_adjustments", {})
    m3_vars = ui_config.get("m3_incentive_variables", {})
    
    wacc_changed = m3_wacc.get("wacc_override") is not None
    
    qual_changes = (
        m3_qual.get("adj_max_agg") is not None or
        m3_qual.get("adj_max_cemi4") is not None or
        m3_qual.get("sharing_netloss") is not None or
        not m3_qual.get("enable_quality", True) or
        not m3_qual.get("enable_netloss", True) or
        not m3_qual.get("enable_load", True)
    )
    
    var_changes = any(v is not None for v in m3_vars.values())
    
    return wacc_changed or qual_changes or var_changes


def _check_module_4_changes(ui_config: Dict[str, Any]) -> bool:
    """Check if Module 4 has any changes."""
    # M4 has no configurable parameters currently
    # 5.4.1 (paverkbara_method) moved to M5
    return False


def _check_module_5_changes(ui_config: Dict[str, Any]) -> bool:
    """Check if Module 5 has any changes."""
    m5 = ui_config.get("m5_efficiency", {})
    return (
        m5.get("trunkering_max") is not None or
        m5.get("realiseringstid") is not None or
        m5.get("kunddelning") is not None or
        m5.get("outlier_krav") is not None or
        m5.get("trunkering_min") is not None or
        m5.get("paverkbara_method") is not None  # 5.4.1 moved from M4
    )


def _check_module_7_changes(ui_config: Dict[str, Any]) -> bool:
    """Check if Module 7 has any changes."""
    addon = ui_config.get("addon_benchmarking", {})
    return addon.get("dea_method") == "custom"


# =============================================================================
# TAB CONTENT RENDERING FUNCTIONS
# =============================================================================

def _render_module_1_content(ui_config: Dict[str, Any], is_selected: bool, has_changes: bool) -> None:
    """Render Module 1: Regulatory asset base valuation content."""
    if not is_selected:
        st.caption("Module not selected - using baseline values")
        return
    
    m1 = ui_config.get("m1_asset_base", {})
    
    # Reset button
    if has_changes:
        if st.button("Reset to baseline", key=f"{MODULE_KEY}_reset_m1"):
            _reset_module("m1_asset_base")
            st.rerun()
    
    kent_uploaded = m1.get("kent_file_bytes") is not None
    general_scaling = m1.get("general_scaling")
    cat_scaling = m1.get("cat_scaling")
    var_scaling = m1.get("var_scaling")
    
    has_general = general_scaling is not None and general_scaling != 1.0
    has_cat = cat_scaling is not None and len(cat_scaling) > 0
    has_var = var_scaling is not None and len(var_scaling) > 0
    
    # Data source
    st.markdown("**Data source**")
    if kent_uploaded:
        kent_name = m1.get("kent_file_name", "Unknown")
        st.markdown(f":orange[KENT upload: {kent_name}]")
    elif has_var:
        n_var = len(var_scaling)
        st.markdown(f":orange[Variable scaling: {n_var} categories adjusted]")
    else:
        st.markdown("Baseline (capbase_a)")
    
    st.markdown("")
    
    # General scaling factor
    st.markdown("**General scaling factor (1.1.1)**")
    if has_general:
        pct = (general_scaling - 1.0) * 100
        st.markdown(f":orange[{general_scaling:.2f} ({pct:+.1f}%)]")
    else:
        st.markdown("1.00 (baseline)")
    
    st.markdown("")
    
    # Category scaling factors
    st.markdown("**Category scaling factors (1.2.X)**")
    if has_cat:
        rows = []
        for cat_encode, factor in cat_scaling.items():
            cat_name = get_category_name(int(cat_encode))
            cat = CATEGORY_BY_CODE.get(int(cat_encode))
            param_id = cat.scaling_param_id if cat else f"1.2.{cat_encode}"
            pct_change = (factor - 1.0) * 100
            rows.append({
                "Param-ID": param_id,
                "Category": cat_name[:40] + "..." if len(cat_name) > 40 else cat_name,
                "Baseline": "1.00",
                "Value": f"{factor:.2f}",
                "Change": f"{pct_change:+.1f}%",
            })
        df = pd.DataFrame(rows)
        st.dataframe(df, width="stretch", hide_index=True)
    else:
        st.caption("All category scaling factors at baseline (1.00)")
    
    # Variable scaling
    if has_var:
        st.markdown("")
        st.markdown("**Asset quantity scaling (10.X)**")
        rows = []
        for cat_encode, factor in var_scaling.items():
            cat_name = get_category_name(int(cat_encode))
            var_id = f"10.{int(cat_encode) + 1}"
            pct_change = (factor - 1.0) * 100
            rows.append({
                "Var-ID": var_id,
                "Category": cat_name[:40] + "..." if len(cat_name) > 40 else cat_name,
                "Scaling": f"{factor:.2f}",
                "Change": f"{pct_change:+.1f}%",
            })
        df = pd.DataFrame(rows)
        st.dataframe(df, width="stretch", hide_index=True)


def _render_module_2_content(ui_config: Dict[str, Any], is_selected: bool, has_changes: bool) -> None:
    """Render Module 2: Depreciation content."""
    if not is_selected:
        st.caption("Module not selected - using baseline values")
        return
    
    m2 = ui_config.get("m2_depreciation", {})
    
    if has_changes:
        if st.button("Reset to baseline", key=f"{MODULE_KEY}_reset_m2"):
            _reset_module("m2_depreciation")
            st.rerun()
    
    st.markdown("**Asset lifetimes (2.X.1, 2.X.2)**")
    
    lifetime_adj = m2.get("lifetime_adjustments")
    if lifetime_adj:
        rows = []
        for cat_encode, changes in lifetime_adj.items():
            cat = CATEGORY_BY_CODE.get(int(cat_encode))
            cat_name = cat.name if cat else f"Category {cat_encode}"
            
            if 'ekdep' in changes:
                baseline_ek = cat.ekdep if cat else "?"
                rows.append({
                    "Category": cat_name[:30],
                    "Parameter": "Ordinary lifetime",
                    "Baseline": str(baseline_ek),
                    "Value": str(changes['ekdep']),
                })
            if 'maxdep' in changes:
                baseline_max = cat.maxdep if cat else "?"
                rows.append({
                    "Category": cat_name[:30],
                    "Parameter": "Tail lifetime",
                    "Baseline": str(baseline_max),
                    "Value": str(changes['maxdep']),
                })
        
        if rows:
            df = pd.DataFrame(rows)
            st.dataframe(df, width="stretch", hide_index=True)
    else:
        st.caption("All lifetime parameters at baseline")


def _render_module_3_content(ui_config: Dict[str, Any], is_selected: bool, has_changes: bool) -> None:
    """Render Module 3: Cost of capital content."""
    if not is_selected:
        st.caption("Module not selected - using baseline values")
        return
    
    m3_wacc = ui_config.get("m3_cost_of_capital", {})
    m3_qual = ui_config.get("m3_quality_adjustments", {})
    m3_vars = ui_config.get("m3_incentive_variables", {})
    
    if has_changes:
        if st.button("Reset to baseline", key=f"{MODULE_KEY}_reset_m3"):
            _reset_module("m3_cost_of_capital")
            _reset_module("m3_quality_adjustments")
            _reset_module("m3_incentive_variables")
            st.rerun()
    
    # WACC
    st.markdown("**WACC (3.2.5)**")
    wacc_changed = m3_wacc.get("wacc_override") is not None
    if wacc_changed:
        wacc = m3_wacc["wacc_override"]
        st.markdown(f":orange[{wacc:.4f} ({wacc*100:.2f}%)]")
    else:
        st.markdown(f"{BASELINE_WACC:.4f} ({BASELINE_WACC*100:.2f}%) - baseline")
    
    # Quality adjustments
    qual_changes = []
    if m3_qual.get("adj_max_agg") is not None:
        qual_changes.append(f"Max aggregate: {m3_qual['adj_max_agg']:.2%}")
    if m3_qual.get("adj_max_cemi4") is not None:
        qual_changes.append(f"Max CEMI4: {m3_qual['adj_max_cemi4']:.2%}")
    if m3_qual.get("sharing_netloss") is not None:
        qual_changes.append(f"Netloss sharing: {m3_qual['sharing_netloss']:.0%}")
    if not m3_qual.get("enable_quality", True):
        qual_changes.append("Quality incentive OFF")
    if not m3_qual.get("enable_netloss", True):
        qual_changes.append("Network loss incentive OFF")
    if not m3_qual.get("enable_load", True):
        qual_changes.append("Load incentive OFF")
    
    if qual_changes:
        st.markdown("")
        st.markdown("**Quality adjustments**")
        for change in qual_changes:
            st.markdown(f":orange[- {change}]")
    
    # Variable overrides
    var_changes = [k for k, v in m3_vars.items() if v is not None]
    if var_changes:
        st.markdown("")
        st.markdown("**Incentive variable overrides**")
        st.caption(f"{len(var_changes)} variable(s) modified")


def _render_module_4_content(ui_config: Dict[str, Any], is_selected: bool, has_changes: bool) -> None:
    """Render Module 4: Operating expenditures content."""
    if not is_selected:
        st.caption("Module not selected - using baseline values")
        return
    
    # M4 currently has no configurable parameters
    # 5.4.1 (paverkbara_method) is now in M5
    st.caption("OPEX parameters planned for future release.")


def _render_module_5_content(ui_config: Dict[str, Any], is_selected: bool, has_changes: bool) -> None:
    """Render Module 5: Efficiency incentive content."""
    if not is_selected:
        st.caption("Module not selected - using baseline values")
        return
    
    m5 = ui_config.get("m5_efficiency", {})
    
    if has_changes:
        if st.button("Reset to baseline", key=f"{MODULE_KEY}_reset_m5"):
            _reset_module("m5_efficiency")
            st.rerun()
    
    # 5.2-5.3 Efficiency requirement parameters
    changes = []
    if m5.get("trunkering_max") is not None:
        changes.append(("5.2.1 Truncation max", BASELINE_MAX_POTENTIAL, m5["trunkering_max"]))
    if m5.get("realiseringstid") is not None:
        changes.append(("5.2.2 Realization time", BASELINE_REALIZATION_TIME, m5["realiseringstid"]))
    if m5.get("kunddelning") is not None:
        changes.append(("5.2.3 Customer sharing", BASELINE_CUSTOMER_SHARING, m5["kunddelning"]))
    if m5.get("outlier_krav") is not None:
        changes.append(("5.3.1 Outlier requirement", BASELINE_MIN_REQUIREMENT, m5["outlier_krav"]))
    if m5.get("trunkering_min") is not None:
        changes.append(("5.3.2 Truncation min", 0.162416, m5["trunkering_min"]))
    
    if changes:
        rows = []
        for param_id, baseline, value in changes:
            if isinstance(baseline, float) and baseline < 1:
                rows.append({
                    "Parameter": param_id,
                    "Baseline": f"{baseline:.2%}",
                    "Value": f"{value:.2%}",
                })
            else:
                rows.append({
                    "Parameter": param_id,
                    "Baseline": str(baseline),
                    "Value": str(value),
                })
        df = pd.DataFrame(rows)
        st.dataframe(df, width="stretch", hide_index=True)
    else:
        st.caption("All efficiency parameters at baseline")
    
    # 5.4.1 Cost base application (moved from M4)
    st.markdown("")
    st.markdown("**Cost base application (5.4.1)**")
    method = m5.get("paverkbara_method")
    if method is not None:
        st.markdown(f":orange[{method}]")
    else:
        st.markdown("OPEX (baseline)")


def _render_module_7_content(ui_config: Dict[str, Any], is_selected: bool, has_changes: bool) -> None:
    """Render Module 7: Add-on modules content."""
    if not is_selected:
        st.caption("Module not selected - using baseline values")
        return
    
    addon = ui_config.get("addon_benchmarking", {})
    
    if has_changes:
        if st.button("Reset to baseline", key=f"{MODULE_KEY}_reset_m7"):
            _reset_module("addon_benchmarking")
            st.rerun()
    
    st.markdown("**DEA Benchmarking**")
    if addon.get("dea_method") == "custom":
        st.markdown(":orange[Custom DEA model]")
        st.caption(f"Inputs: {addon.get('dea_inputs', [])}")
        st.caption(f"Outputs: {addon.get('dea_outputs', [])}")
        st.caption(f"RTS: {addon.get('dea_rts', 'crs')}")
    else:
        st.markdown("Baseline DEA model")


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _reset_module(module_key: str) -> None:
    """Reset a module to its default configuration."""
    if "ui_config" in st.session_state:
        if module_key in DEFAULT_UI_CONFIG:
            st.session_state["ui_config"][module_key] = copy.deepcopy(
                DEFAULT_UI_CONFIG[module_key]
            )


def _run_calculation() -> None:
    """
    Run the revenue frame calculation pipeline.
    
    Uses get_filtered_ui_config() to ensure only selected modules
    have their modifications applied.
    """
    from frontend.utils.state_manager import get_user_reid, get_filtered_ui_config
    from frontend.utils.config_adapter import build_case_definition
    
    user_reid = get_user_reid()
    
    if user_reid is None:
        st.error("No company selected. Please select a company in the sidebar.")
        return
    
    with st.status("Running calculation...", expanded=True) as status:
        try:
            st.write("Loading baseline data...")
            from data_loaders.baseline_data import load_baseline_data
            baseline_data = load_baseline_data()
            
            st.write("Retrieving baseline...")
            from config.case_definition import get_baseline_config
            from pipeline.core import run_pipeline
            
            baseline_config = get_baseline_config(user_reid)
            baseline_result = run_pipeline(baseline_data, baseline_config)
            st.session_state["baseline_result"] = baseline_result
            
            st.write("Building case...")
            filtered_config = get_filtered_ui_config()
            case_definition = build_case_definition(
                user_reid,
                filtered_config
            )
            
            st.write("Calculating revenue frame...")
            case_result = run_pipeline(baseline_data, case_definition)
            st.session_state["case_result"] = case_result
            
            st.session_state["calculation_done"] = True
            status.update(label="Calculation complete", state="complete")
            
        except ValueError as e:
            st.error(f"Configuration error: {e}")
            status.update(label="Error", state="error")
            return
        except Exception as e:
            st.error(f"Calculation error: {e}")
            with st.expander("Technical details"):
                st.exception(e)
            status.update(label="Error", state="error")
            return
    
    st.switch_page("pages/2_results.py")
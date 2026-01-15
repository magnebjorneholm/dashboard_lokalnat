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
)
from frontend.common.asset_categories import (
    ASSET_CATEGORIES,
    CATEGORY_BY_CODE,
    get_category_name,
)

# Import baseline values from respective modules
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
    Render Case Summary tab.
    
    Displays all parameters organized by module with baseline/modified status.
    Includes reset buttons per module and the main CALCULATE button.
    """
    st.subheader("Case Summary")
    st.caption("Review all parameters before running the calculation.")
    
    ui_config = st.session_state.get("ui_config", {})
    
    has_any_changes = False
    
    # --- Module 1: Regulatory asset base valuation ---
    changed_1 = _render_module_1(ui_config)
    has_any_changes = has_any_changes or changed_1
    
    # --- Module 2: Depreciation ---
    changed_2 = _render_module_2(ui_config)
    has_any_changes = has_any_changes or changed_2
    
    # --- Module 3: Cost of capital ---
    changed_3 = _render_module_3(ui_config)
    has_any_changes = has_any_changes or changed_3
    
    # --- Module 4: Operating expenditures ---
    changed_4 = _render_module_4(ui_config)
    has_any_changes = has_any_changes or changed_4
    
    # --- Module 5: Efficiency incentive ---
    changed_5 = _render_module_5(ui_config)
    has_any_changes = has_any_changes or changed_5
    
    # --- Module 7: Add-on modules ---
    changed_7 = _render_module_7(ui_config)
    has_any_changes = has_any_changes or changed_7
    
    # --- Summary status ---
    st.divider()
    
    if has_any_changes:
        st.warning("This case has modified parameters (highlighted in orange above).")
    else:
        st.info("All parameters at baseline values.")
    
    # --- CALCULATE button ---
    st.divider()
    
    if st.button("CALCULATE REVENUE FRAME", type="primary", use_container_width=True):
        _run_calculation()


def _render_module_1(ui_config: Dict[str, Any]) -> bool:
    """Render Module 1: Regulatory asset base valuation. Returns True if has changes."""
    m1 = ui_config.get("m1_asset_base", {})
    
    has_changes = False
    
    # Check for changes (new keys)
    kent_uploaded = m1.get("kent_file_bytes") is not None
    general_scaling = m1.get("general_scaling")
    cat_scaling = m1.get("cat_scaling")
    var_scaling = m1.get("var_scaling")
    
    has_general = general_scaling is not None and general_scaling != 1.0
    has_cat = cat_scaling is not None and len(cat_scaling) > 0
    has_var = var_scaling is not None and len(var_scaling) > 0
    
    if kent_uploaded or has_general or has_cat or has_var:
        has_changes = True
    
    # Header with reset button
    col1, col2 = st.columns([5, 1])
    with col1:
        expander_label = "1. Regulatory asset base valuation"
        if has_changes:
            expander_label += " :orange[(modified)]"
        expanded = has_changes
    with col2:
        if has_changes:
            if st.button("Reset", key=f"{MODULE_KEY}_reset_m1", use_container_width=True):
                _reset_module("m1_asset_base")
                st.rerun()
    
    with st.expander(expander_label, expanded=expanded):
        # Data source (company-specific)
        st.markdown("**Data source (company-specific)**")
        if kent_uploaded:
            kent_name = m1.get("kent_file_name", "Unknown")
            st.markdown(f":orange[KENT upload: {kent_name}]")
        elif has_var:
            n_var = len(var_scaling)
            st.markdown(f":orange[Variable scaling: {n_var} categories adjusted]")
        else:
            st.markdown("Baseline (capbase_a)")
        
        st.markdown("")
        
        # General scaling factor (1.1.1)
        st.markdown("**General scaling factor (1.1.1)**")
        if has_general:
            pct = (general_scaling - 1.0) * 100
            st.markdown(f":orange[{general_scaling:.2f} ({pct:+.1f}%)]")
        else:
            st.markdown("1.00 (baseline)")
        
        st.markdown("")
        
        # Category scaling factors (1.2.X)
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
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.caption("All category scaling factors at baseline (1.00)")
        
        # Variable scaling (10.X) - company specific
        if has_var:
            st.markdown("")
            st.markdown("**Asset quantity scaling (10.X) - company specific**")
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
            st.dataframe(df, use_container_width=True, hide_index=True)
    
    return has_changes


def _render_module_2(ui_config: Dict[str, Any]) -> bool:
    """Render Module 2: Depreciation. Returns True if has changes."""
    m2 = ui_config.get("m2_depreciation", {})
    
    lifetime_adj = m2.get("lifetime_adjustments")
    has_changes = lifetime_adj is not None and len(lifetime_adj) > 0
    
    col1, col2 = st.columns([5, 1])
    with col1:
        expander_label = "2. Depreciation"
        if has_changes:
            expander_label += " :orange[(modified)]"
    with col2:
        if has_changes:
            if st.button("Reset", key=f"{MODULE_KEY}_reset_m2", use_container_width=True):
                _reset_module("m2_depreciation")
                st.rerun()
    
    with st.expander(expander_label, expanded=has_changes):
        st.markdown("**Asset lifetimes (2.X.1, 2.X.2)**")
        
        if lifetime_adj:
            rows = []
            for cat_encode, changes in lifetime_adj.items():
                cat = CATEGORY_BY_CODE.get(int(cat_encode))
                cat_name = cat.name if cat else f"Category {cat_encode}"
                
                if 'ekdep' in changes:
                    baseline_ek = cat.ekdep if cat else "?"
                    rows.append({
                        "Param-ID": cat.param_id_ekdep if cat else f"2.{cat_encode}.1",
                        "Category": cat_name[:35] + "..." if len(cat_name) > 35 else cat_name,
                        "Type": "Ordinary",
                        "Baseline": f"{baseline_ek} yrs",
                        "Value": f"{changes['ekdep']} yrs",
                    })
                
                if 'maxdep' in changes:
                    baseline_max = cat.maxdep if cat else "?"
                    rows.append({
                        "Param-ID": cat.param_id_maxdep if cat else f"2.{cat_encode}.2",
                        "Category": cat_name[:35] + "..." if len(cat_name) > 35 else cat_name,
                        "Type": "Tail",
                        "Baseline": f"{baseline_max} yrs",
                        "Value": f"{changes['maxdep']} yrs",
                    })
            
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.caption("All lifetimes at baseline values")
    
    return has_changes


def _render_module_3(ui_config: Dict[str, Any]) -> bool:
    """Render Module 3: Cost of capital. Returns True if has changes."""
    m3_wacc = ui_config.get("m3_cost_of_capital", {})
    m3_qual = ui_config.get("m3_quality_adjustments", {})
    m3_vars = ui_config.get("m3_incentive_variables", {})
    
    wacc_changed = m3_wacc.get("wacc_override") is not None
    
    qual_changes = []
    if m3_qual.get("adj_max_cemi4") is not None:
        qual_changes.append("CEMI4 adjustment")
    if m3_qual.get("sharing_netloss") is not None:
        qual_changes.append("Network loss sharing")
    if m3_qual.get("adj_max_agg") is not None:
        qual_changes.append("Max aggregate adjustment")
    if m3_qual.get("k_nf") is not None:
        qual_changes.append("Electricity price (K_NF)")
    if m3_qual.get("kpi") is not None:
        qual_changes.append("KPI factors")
    if m3_qual.get("ait_costs") is not None:
        qual_changes.append("AIT costs")
    if m3_qual.get("aif_costs") is not None:
        qual_changes.append("AIF costs")
    if not m3_qual.get("enable_quality", True):
        qual_changes.append("Quality incentive OFF")
    if not m3_qual.get("enable_netloss", True):
        qual_changes.append("Network loss incentive OFF")
    if not m3_qual.get("enable_load", True):
        qual_changes.append("Load incentive OFF")
    
    var_changes = [k for k, v in m3_vars.items() if v is not None]
    
    has_changes = wacc_changed or len(qual_changes) > 0 or len(var_changes) > 0
    
    col1, col2 = st.columns([5, 1])
    with col1:
        expander_label = "3. Cost of capital"
        if has_changes:
            expander_label += " :orange[(modified)]"
    with col2:
        if has_changes:
            if st.button("Reset", key=f"{MODULE_KEY}_reset_m3", use_container_width=True):
                _reset_module("m3_cost_of_capital")
                _reset_module("m3_quality_adjustments")
                _reset_module("m3_incentive_variables")
                st.rerun()
    
    with st.expander(expander_label, expanded=has_changes):
        # WACC
        st.markdown("**WACC (3.2.5)**")
        if wacc_changed:
            wacc = m3_wacc["wacc_override"]
            st.markdown(f":orange[{wacc:.4f} ({wacc*100:.2f}%)]")
        else:
            st.markdown(f"{BASELINE_WACC:.4f} ({BASELINE_WACC*100:.2f}%) - baseline")
        
        # Quality adjustments
        if qual_changes:
            st.markdown("")
            st.markdown("**Quality adjustments**")
            for change in qual_changes:
                st.markdown(f":orange[- {change}]")
        
        # Variable overrides
        if var_changes:
            st.markdown("")
            st.markdown("**Incentive variable overrides**")
            st.caption(f"{len(var_changes)} variable(s) modified")
    
    return has_changes


def _render_module_4(ui_config: Dict[str, Any]) -> bool:
    """Render Module 4: Operating expenditures. Returns True if has changes."""
    m4 = ui_config.get("m4_operating_exp", {})
    
    method = m4.get("paverkbara_method", "OPEX")
    has_changes = method != "OPEX"
    
    col1, col2 = st.columns([5, 1])
    with col1:
        expander_label = "4. Operating expenditures"
        if has_changes:
            expander_label += " :orange[(modified)]"
    with col2:
        if has_changes:
            if st.button("Reset", key=f"{MODULE_KEY}_reset_m4", use_container_width=True):
                _reset_module("m4_operating_exp")
                st.rerun()
    
    with st.expander(expander_label, expanded=has_changes):
        st.markdown("**Adjustable costs method (5.4.1)**")
        if has_changes:
            st.markdown(f":orange[{method}]")
        else:
            st.markdown("OPEX (baseline)")
    
    return has_changes


def _render_module_5(ui_config: Dict[str, Any]) -> bool:
    """Render Module 5: Efficiency incentive. Returns True if has changes."""
    m5 = ui_config.get("m5_efficiency", {})
    
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
    
    has_changes = len(changes) > 0
    
    col1, col2 = st.columns([5, 1])
    with col1:
        expander_label = "5. Efficiency incentive"
        if has_changes:
            expander_label += " :orange[(modified)]"
    with col2:
        if has_changes:
            if st.button("Reset", key=f"{MODULE_KEY}_reset_m5", use_container_width=True):
                _reset_module("m5_efficiency")
                st.rerun()
    
    with st.expander(expander_label, expanded=has_changes):
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
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.caption("All efficiency parameters at baseline")
    
    return has_changes


def _render_module_7(ui_config: Dict[str, Any]) -> bool:
    """Render Module 7: Add-on modules. Returns True if has changes."""
    addon = ui_config.get("addon_benchmarking", {})
    
    has_changes = addon.get("dea_method") == "custom"
    
    col1, col2 = st.columns([5, 1])
    with col1:
        expander_label = "7. Add-on modules"
        if has_changes:
            expander_label += " :orange[(modified)]"
    with col2:
        if has_changes:
            if st.button("Reset", key=f"{MODULE_KEY}_reset_m7", use_container_width=True):
                _reset_module("addon_benchmarking")
                st.rerun()
    
    with st.expander(expander_label, expanded=has_changes):
        st.markdown("**DEA Benchmarking**")
        if has_changes:
            st.markdown(":orange[Custom DEA model]")
            st.caption(f"Inputs: {addon.get('dea_inputs', [])}")
            st.caption(f"Outputs: {addon.get('dea_outputs', [])}")
            st.caption(f"RTS: {addon.get('dea_rts', 'crs')}")
        else:
            st.markdown("Baseline DEA model")
    
    return has_changes


def _reset_module(module_key: str) -> None:
    """Reset a module to its default configuration."""
    if "ui_config" in st.session_state:
        if module_key in DEFAULT_UI_CONFIG:
            st.session_state["ui_config"][module_key] = copy.deepcopy(
                DEFAULT_UI_CONFIG[module_key]
            )


def _run_calculation() -> None:
    """Run the revenue frame calculation pipeline."""
    from frontend.utils.state_manager import get_user_reid
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
            case_definition = build_case_definition(
                user_reid,
                st.session_state["ui_config"]
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
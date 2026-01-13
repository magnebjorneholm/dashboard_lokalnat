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
    
    # Get current ui_config
    ui_config = st.session_state.get("ui_config", {})
    
    # Track if any changes exist
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
    
    # Check for changes
    kent_uploaded = m1.get("kent_file_bytes") is not None
    rab_modified = m1.get("rab_has_changes", False)
    normvalue_adj = m1.get("normvalue_adjustments")
    
    if kent_uploaded or rab_modified or normvalue_adj:
        has_changes = True
    
    # Header with reset button
    col1, col2 = st.columns([5, 1])
    with col1:
        expander_label = "1. Regulatory asset base valuation"
        if has_changes:
            expander_label += " :orange[(modified)]"
        expanded = has_changes  # Auto-expand if has changes
    with col2:
        if has_changes:
            if st.button("Reset", key=f"{MODULE_KEY}_reset_m1", use_container_width=True):
                _reset_module("m1_asset_base")
                st.rerun()
    
    with st.expander(expander_label, expanded=expanded):
        # Data source
        st.markdown("**Data source**")
        if kent_uploaded:
            kent_name = m1.get("kent_file_name", "Unknown")
            st.markdown(f":orange[KENT upload: {kent_name}]")
        elif rab_modified:
            st.markdown(":orange[RAB editor (modified)]")
        else:
            st.markdown("Baseline (capbase_a)")
        
        st.markdown("")
        
        # Scaling factors
        st.markdown("**Scaling factors (1.2.X)**")
        if normvalue_adj:
            rows = []
            for cat_encode, multiplier in normvalue_adj.items():
                cat_name = get_category_name(int(cat_encode))
                cat = CATEGORY_BY_CODE.get(int(cat_encode))
                param_id = cat.scaling_param_id if cat else f"1.2.{cat_encode}"
                pct_change = (multiplier - 1.0) * 100
                rows.append({
                    "Parameter-ID": param_id,
                    "Category": cat_name[:40] + "..." if len(cat_name) > 40 else cat_name,
                    "Baseline": "1.00",
                    "Value": f"{multiplier:.2f}",
                    "Change": f"{pct_change:+.1f}%",
                })
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.caption("All scaling factors at baseline (1.00)")
    
    return has_changes


def _render_module_2(ui_config: Dict[str, Any]) -> bool:
    """Render Module 2: Depreciation. Returns True if has changes."""
    m2 = ui_config.get("m2_depreciation", {})
    
    lifetime_adj = m2.get("lifetime_adjustments")
    has_changes = lifetime_adj is not None and len(lifetime_adj) > 0
    
    # Header with reset button
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
                        "Parameter-ID": cat.param_id_ekdep if cat else f"2.{cat_encode}.1",
                        "Category": cat_name[:35] + "..." if len(cat_name) > 35 else cat_name,
                        "Type": "Ordinary",
                        "Baseline": f"{baseline_ek} yrs",
                        "Value": f"{changes['ekdep']} yrs",
                    })
                
                if 'maxdep' in changes:
                    baseline_max = cat.maxdep if cat else "?"
                    rows.append({
                        "Parameter-ID": cat.param_id_maxdep if cat else f"2.{cat_encode}.2",
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
    
    # Check for changes
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
    
    # Check incentive variables
    var_changes = [k for k, v in m3_vars.items() if v is not None]
    
    has_changes = wacc_changed or len(qual_changes) > 0 or len(var_changes) > 0
    
    # Header with reset button
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
            wacc_val = m3_wacc.get("wacc_override")
            st.markdown(f":orange[{wacc_val:.4f}] (baseline: {BASELINE_WACC:.4f})")
        else:
            st.markdown(f"{BASELINE_WACC:.4f} (baseline)")
        
        st.markdown("")
        
        # Quality adjustments
        st.markdown("**Cost of capital adjustments (3.3-3.6)**")
        if qual_changes:
            for change in qual_changes:
                st.markdown(f"- :orange[{change}]")
        else:
            st.caption("All adjustment parameters at baseline")
        
        # Incentive toggles
        st.markdown("")
        st.markdown("**Incentive toggles**")
        col1, col2, col3 = st.columns(3)
        with col1:
            qual_on = m3_qual.get("enable_quality", True)
            if qual_on:
                st.markdown("Quality: ON")
            else:
                st.markdown(":orange[Quality: OFF]")
        with col2:
            netloss_on = m3_qual.get("enable_netloss", True)
            if netloss_on:
                st.markdown("Network loss: ON")
            else:
                st.markdown(":orange[Network loss: OFF]")
        with col3:
            load_on = m3_qual.get("enable_load", True)
            if load_on:
                st.markdown("Load: ON")
            else:
                st.markdown(":orange[Load: OFF]")
        
        # Incentive variables
        if var_changes:
            st.markdown("")
            st.markdown("**Company-specific incentive variables**")
            st.markdown(f":orange[{len(var_changes)} variable(s) modified]")
    
    return has_changes


def _render_module_4(ui_config: Dict[str, Any]) -> bool:
    """Render Module 4: Operating expenditures. Returns True if has changes."""
    m4 = ui_config.get("m4_operating_exp", {})
    
    method = m4.get("paverkbara_method", "OPEX")
    has_changes = method != "OPEX"
    
    # Header with reset button
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
        st.markdown("**Cost base for efficiency requirement (5.4.1)**")
        if has_changes:
            st.markdown(f":orange[{method}] (baseline: OPEX)")
        else:
            st.markdown(f"{method} (baseline)")
    
    return has_changes


def _render_module_5(ui_config: Dict[str, Any]) -> bool:
    """Render Module 5: Efficiency incentive. Returns True if has changes."""
    m5 = ui_config.get("m5_efficiency", {})
    
    # Build parameter list
    params = [
        ("5.2.1", "Maximum efficiency potential cap", 
         m5.get("trunkering_max"), BASELINE_MAX_POTENTIAL, "{:.0%}"),
        ("5.2.2", "Realization time", 
         m5.get("realiseringstid"), BASELINE_REALIZATION_TIME, "{} years"),
        ("5.2.3", "Customer sharing factor", 
         m5.get("kunddelning"), BASELINE_CUSTOMER_SHARING, "{:.0%}"),
        ("5.3.1", "Minimum annual requirement", 
         m5.get("outlier_krav"), BASELINE_MIN_REQUIREMENT, "{:.1%}"),
    ]
    
    changes = [(p[0], p[1], p[2], p[3], p[4]) for p in params if p[2] is not None]
    has_changes = len(changes) > 0
    
    # Header with reset button
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
        st.markdown("**Efficiency requirement parameters**")
        
        rows = []
        for param_id, desc, value, baseline, fmt in params:
            if value is not None:
                rows.append({
                    "Parameter-ID": param_id,
                    "Description": desc,
                    "Baseline": fmt.format(baseline),
                    "Value": f":orange[{fmt.format(value)}]",
                })
            else:
                rows.append({
                    "Parameter-ID": param_id,
                    "Description": desc,
                    "Baseline": fmt.format(baseline),
                    "Value": fmt.format(baseline),
                })
        
        # Display as formatted text instead of dataframe for orange highlighting
        for row in rows:
            if ":orange[" in row["Value"]:
                st.markdown(f"**{row['Parameter-ID']}** {row['Description']}: {row['Value']} (baseline: {row['Baseline']})")
            else:
                st.caption(f"{row['Parameter-ID']} {row['Description']}: {row['Value']}")
    
    return has_changes


def _render_module_7(ui_config: Dict[str, Any]) -> bool:
    """Render Module 7: Add-on modules. Returns True if has changes."""
    addon = ui_config.get("addon_benchmarking", {})
    
    dea_method = addon.get("dea_method", "baseline")
    has_changes = dea_method != "baseline"
    
    # Header with reset button
    col1, col2 = st.columns([5, 1])
    with col1:
        expander_label = "7. Add-on modules"
        if has_changes:
            expander_label += " :orange[(modified)]"
    with col2:
        if has_changes:
            if st.button("Reset", key=f"{MODULE_KEY}_reset_addon", use_container_width=True):
                _reset_module("addon_benchmarking")
                st.rerun()
    
    with st.expander(expander_label, expanded=has_changes):
        st.markdown("**Benchmarking module (7.1)**")
        
        if dea_method == "custom":
            st.markdown(":orange[Custom DEA configuration]")
            
            inputs = addon.get("dea_inputs", [])
            outputs = addon.get("dea_outputs", [])
            rts = addon.get("dea_rts", "crs")
            
            st.markdown(f"- Inputs: {', '.join(inputs)}")
            st.markdown(f"- Outputs: {', '.join(outputs)}")
            st.markdown(f"- Returns to scale: {rts.upper()}")
        else:
            st.markdown("DEA method: Baseline (Ei's official model)")
    
    return has_changes


def _reset_module(module_key: str) -> None:
    """Reset a module to default values."""
    if module_key in DEFAULT_UI_CONFIG:
        default = copy.deepcopy(DEFAULT_UI_CONFIG[module_key])
        st.session_state["ui_config"][module_key] = default


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
            # Load baseline data (cached)
            st.write("Loading baseline data...")
            from data_loaders.baseline_data import load_baseline_data
            baseline_data = load_baseline_data()
            
            # Get baseline result (cached per company)
            st.write("Retrieving baseline...")
            from config.case_definition import get_baseline_config
            from pipeline.core import run_pipeline
            
            baseline_config = get_baseline_config(user_reid)
            baseline_result = run_pipeline(baseline_data, baseline_config)
            st.session_state["baseline_result"] = baseline_result
            
            # Build case definition
            st.write("Building case...")
            case_definition = build_case_definition(
                user_reid,
                st.session_state["ui_config"]
            )
            
            # Run pipeline
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
    
    # Navigate to results
    st.switch_page("pages/2_results.py")
"""
Module 3: Cost of Capital

Handles WACC and related parameters.
Parameter-IDs: 3.1.X (base), 3.2.X (derived), 3.3-3.6 (adjustments)
Variable-IDs: 30.X

Section-based rendering:
- render_wacc() -> 3.1-3.2 WACC parameters
- render_incentive_params() -> 3.3-3.6 Incentive parameters
"""

import streamlit as st
import pandas as pd
from typing import Dict, Any

from calculations.wacc_calculations import (
    CAPMInputs,
    calculate_wacc,
    BASELINE_WACC,
)
from frontend.common.formatting import format_percent, format_number
from frontend.utils.state_manager import get_config_value

MODULE_KEY = "m3_cost_of_capital"
MODULE_KEY_QA = "m3_quality_adjustments"

# Baseline CAPM parameters (from User Manual Table 6)
BASELINE_CAPM = CAPMInputs()

# Baseline derived parameters (calculated from CAPM baseline)
BASELINE_DERIVED = {
    "cost_of_equity_nominal": 0.0645,   # Re: Rf + beta * MRP
    "cost_of_debt_nominal": 0.0401,     # Rd: Rf + credit spread
    "debt_ratio": 0.36,                  # S: debt ratio
    "tax_rate": 0.206,                   # tau: corporate tax
    "inflation": 0.0202,                 # pi: CPIF
    "wacc_nominal_pre_tax": 0.0664,      # WACC nominal
    "wacc_real_pre_tax": BASELINE_WACC,  # 0.0453
}

# Customer types for AIT/AIF (Swedish regulatory terms)
SNI_LABELS = {
    1: "Jordbruk",
    2: "Industri",
    3: "Handel/tjanster",
    4: "Offentlig verksamhet",
    5: "Hushall",
    6: "Granspunkt",
}

# Baseline values for incentive parameters
BASELINE_INCENTIVE = {
    "enable_quality": True,
    "enable_netloss": True,
    "enable_load": True,
    "adj_max_agg": 1/3,
    "adj_max_cemi4": 0.25,
    "sharing_netloss": 0.75,
    "kpi": {2024: 1.1546, 2025: 1.1546, 2026: 1.1546, 2027: 1.1546},
    "k_nf": {2024: 753.44, 2025: 753.44, 2026: 753.44, 2027: 753.44},
    "ait_costs": {
        "o_1": 34.35, "o_2": 159.96, "o_3": 175.06,
        "o_4": 96.97, "o_5": 5.84, "o_6": 96.01,
        "a_1": 14.10, "a_2": 76.00, "a_3": 79.31,
        "a_4": 43.70, "a_5": 4.98, "a_6": 45.16,
    },
    "aif_costs": {
        "o_1": 9.78, "o_2": 70.75, "o_3": 17.78,
        "o_4": 7.65, "o_5": 1.95, "o_6": 22.18,
        "a_1": 1.72, "a_2": 20.71, "a_3": 5.94,
        "a_4": 0.92, "a_5": 1.85, "a_6": 7.08,
    },
}


# =============================================================================
# SECTION RENDER FUNCTIONS
# =============================================================================

def render_wacc() -> Dict[str, Any]:
    """
    Render M3 WACC section: 3.1-3.2 WACC parameters.
    
    Three input methods via radio button:
    1. CAPM components - calculate from base parameters
    2. Derived parameters - modify Re, Rd, S, tau, pi directly
    3. Direct input - enter WACC directly
    
    Returns:
        Dict with wacc_override or empty if baseline
    """
    config: Dict[str, Any] = {}
    
    st.markdown("##### 3.1-3.2 WACC Parameters")
    
    # Initialize session state
    if f"{MODULE_KEY}_current_wacc" not in st.session_state:
        st.session_state[f"{MODULE_KEY}_current_wacc"] = get_config_value(MODULE_KEY, "wacc_override", BASELINE_WACC)
    
    # === INPUT METHOD VIA RADIO ===
    input_method = st.radio(
        "Input method",
        options=["Base parameters", "Derived", "Direct input"],
        index=0,
        key=f"{MODULE_KEY}_input_method",
        horizontal=True,
        help="WACC specification method"
    )
    
    # === 1. CAPM COMPONENTS ===
    if input_method == "Base parameters":
        _render_capm_section()
    
    # === 2. DERIVED ===
    elif input_method == "Derived":
        _render_derived_section()
    
    # === 3. DIRECT INPUT ===
    else:
        _render_direct_section()
    
    # --- Set config based on current value ---
    current_wacc = st.session_state[f"{MODULE_KEY}_current_wacc"]
    if abs(current_wacc - BASELINE_WACC) > 0.0001:
        config["wacc_override"] = current_wacc

    # Persist current widget values into config so they are restored when loading a case
    # Read from session_state keys if present and store under module config
    widget_map = {
        f"{MODULE_KEY}_debt_ratio": "debt_ratio",
        f"{MODULE_KEY}_asset_beta": "asset_beta",
        f"{MODULE_KEY}_risk_free_rate": "risk_free_rate",
        f"{MODULE_KEY}_market_risk_premium": "market_risk_premium",
        f"{MODULE_KEY}_credit_risk_premium": "credit_risk_premium",
        f"{MODULE_KEY}_tax_rate": "tax_rate",
        f"{MODULE_KEY}_inflation": "inflation",
        f"{MODULE_KEY}_cost_of_equity": "cost_of_equity",
        f"{MODULE_KEY}_cost_of_debt": "cost_of_debt",
        f"{MODULE_KEY}_debt_ratio_derived": "debt_ratio_derived",
        f"{MODULE_KEY}_tax_rate_derived": "tax_rate_derived",
        f"{MODULE_KEY}_inflation_derived": "inflation_derived",
        f"{MODULE_KEY}_direct_wacc": "direct_wacc",
    }

    for widget_key, param_name in widget_map.items():
        if widget_key in st.session_state:
            val = st.session_state.get(widget_key)
            # store numeric values (or booleans) directly
            config[param_name] = val
    
    return config


def render_incentive_params() -> Dict[str, Any]:
    """
    Render M3 incentive parameters section: 3.3-3.6 parameters.
    
    Includes:
    - 3.3 Quality adjustment parameters (CEMI4, AIT/AIF costs)
    - 3.4 Network loss parameters
    - 3.5 Utilization rate parameters
    - 3.6 Aggregate cap
    - 3.7 KPI factors
    
    Returns:
        Dict with incentive parameter overrides
    """
    config: Dict[str, Any] = {}
    
    st.markdown("##### 3.3-3.6 Incentive Parameters")
    
    # Enable/disable toggles
    col1, col2, col3 = st.columns(3)
    
    with col1:
        enable_quality = st.checkbox(
            "3.3 Quality adjustment",
                value=get_config_value(MODULE_KEY_QA, "enable_quality", BASELINE_INCENTIVE["enable_quality"]),
            key=f"{MODULE_KEY_QA}_enable_quality",
            help="Enable quality (interruption) adjustment"
        )
        if enable_quality != BASELINE_INCENTIVE["enable_quality"]:
            config["enable_quality"] = enable_quality
    
    with col2:
        enable_netloss = st.checkbox(
            "3.4 Network loss",
                value=get_config_value(MODULE_KEY_QA, "enable_netloss", BASELINE_INCENTIVE["enable_netloss"]),
            key=f"{MODULE_KEY_QA}_enable_netloss",
            help="Enable network loss adjustment"
        )
        if enable_netloss != BASELINE_INCENTIVE["enable_netloss"]:
            config["enable_netloss"] = enable_netloss
    
    with col3:
        enable_load = st.checkbox(
            "3.5 Utilization rate",
                value=get_config_value(MODULE_KEY_QA, "enable_load", BASELINE_INCENTIVE["enable_load"]),
            key=f"{MODULE_KEY_QA}_enable_load",
            help="Enable utilization rate adjustment"
        )
        if enable_load != BASELINE_INCENTIVE["enable_load"]:
            config["enable_load"] = enable_load
    
    st.divider()
    
    # === INDIVIDUAL SECTIONS ===
    with st.expander("3.3 Quality adjustment parameters", expanded=False):
        _render_quality_section(config)
    
    with st.expander("3.4 Network loss adjustment parameters", expanded=False):
        _render_netloss_section(config)
    
    with st.expander("3.5 Utilization rate adjustment parameters", expanded=False):
        _render_load_section(config)
    
    with st.expander("3.6 Aggregate adjustment cap", expanded=False):
        _render_caps_section(config)
    
    with st.expander("3.7 KPI factors", expanded=False):
        _render_kpi_section(config)
    
    return config


# =============================================================================
# WACC CALCULATION HELPERS
# =============================================================================

def _calculate_wacc_from_derived(
    cost_of_equity: float,
    cost_of_debt: float,
    debt_ratio: float,
    tax_rate: float,
    inflation: float
) -> tuple[float, float]:
    """
    Calculate WACC from derived parameters.
    
    Formulas:
        WACC_nom_after_tax = (1 - S) * Re + S * Rd * (1 - tau)
        WACC_nom_pre_tax   = WACC_nom_after_tax / (1 - tau)
        WACC_real          = (1 + WACC_nom_pre_tax) / (1 + pi) - 1
    """
    wacc_nominal_after_tax = (
        (1 - debt_ratio) * cost_of_equity + 
        debt_ratio * cost_of_debt * (1 - tax_rate)
    )
    wacc_nominal_pre_tax = wacc_nominal_after_tax / (1 - tax_rate)
    wacc_real_pre_tax = (1 + wacc_nominal_pre_tax) / (1 + inflation) - 1
    
    return wacc_nominal_pre_tax, wacc_real_pre_tax


def _render_apply_row(new_wacc: float, button_key: str) -> None:
    """Render Apply/Reset buttons and current WACC info (vertical layout)."""
    current_wacc = st.session_state[f"{MODULE_KEY}_current_wacc"]
    
    col1, col2 = st.columns(2)
    with col1:
            st.button(
            "Update active WACC",
            key=button_key,
            type="primary",
            on_click=_set_wacc,
            args=(new_wacc,),
            width='stretch'
        )
    with col2:
        st.button(
            "Reset",
            key=f"{button_key}_reset",
            on_click=_set_wacc,
            args=(BASELINE_WACC,),
            width='stretch'
        )
    
    st.caption(f"Active WACC: **{format_percent(current_wacc)}**")


def _set_wacc(value: float) -> None:
    """Callback to set WACC value."""
    st.session_state[f"{MODULE_KEY}_current_wacc"] = value


# =============================================================================
# WACC INPUT SECTIONS
# =============================================================================

def _render_capm_section() -> None:
    """Render 3.1 Base parameters with derived values display."""
    st.markdown("##### 3.1 Base parameters")
    st.caption("WACC derived from CAPM inputs")
    
    col1, col2 = st.columns(2)
    
    with col1:
        debt_ratio = st.number_input(
            "3.1.1 Debt ratio (S)",
            value=get_config_value(MODULE_KEY, "debt_ratio", BASELINE_CAPM.debt_ratio),
            min_value=0.0,
            max_value=0.99,
            step=0.01,
            format="%.2f",
            key=f"{MODULE_KEY}_debt_ratio",
            help="Debt share of total capital D/(D+E)"
        )
        
        asset_beta = st.number_input(
            "3.1.2 Asset beta",
            value=get_config_value(MODULE_KEY, "asset_beta", BASELINE_CAPM.asset_beta),
            min_value=0.0,
            max_value=2.0,
            step=0.01,
            format="%.2f",
            key=f"{MODULE_KEY}_asset_beta",
            help="Systematic risk (unlevered assets)"
        )
        
        risk_free_rate = st.number_input(
            "3.1.3 Risk-free rate (Rf)",
            value=get_config_value(MODULE_KEY, "risk_free_rate", BASELINE_CAPM.risk_free_rate),
            min_value=0.0,
            max_value=0.20,
            step=0.001,
            format="%.4f",
            key=f"{MODULE_KEY}_risk_free_rate",
            help="10-year Swedish government bond yield"
        )
        
        market_risk_premium = st.number_input(
            "3.1.4 Market risk premium",
            value=get_config_value(MODULE_KEY, "market_risk_premium", BASELINE_CAPM.market_risk_premium),
            min_value=0.0,
            max_value=0.20,
            step=0.001,
            format="%.4f",
            key=f"{MODULE_KEY}_market_risk_premium",
            help="Expected excess return vs. risk-free rate"
        )
    
    with col2:
        credit_risk_premium = st.number_input(
            "3.1.5 Credit risk premium",
            value=get_config_value(MODULE_KEY, "credit_risk_premium", BASELINE_CAPM.credit_risk_premium),
            min_value=0.0,
            max_value=0.10,
            step=0.001,
            format="%.4f",
            key=f"{MODULE_KEY}_credit_risk_premium",
            help="Spread over risk-free for debt"
        )
        
        tax_rate = st.number_input(
            "3.1.6 Corporate tax rate (tau)",
            value=get_config_value(MODULE_KEY, "tax_rate", BASELINE_CAPM.tax_rate),
            min_value=0.0,
            max_value=0.50,
            step=0.001,
            format="%.3f",
            key=f"{MODULE_KEY}_tax_rate",
            help="Swedish corporate tax rate"
        )
        
        inflation = st.number_input(
            "3.1.7 Inflation (pi)",
            value=get_config_value(MODULE_KEY, "inflation", BASELINE_CAPM.inflation),
            min_value=-0.05,
            max_value=0.20,
            step=0.001,
            format="%.4f",
            key=f"{MODULE_KEY}_inflation",
            help="CPIF inflation rate"
        )
    
    # Calculate WACC from inputs
    capm_inputs = CAPMInputs(
        debt_ratio=debt_ratio,
        asset_beta=asset_beta,
        risk_free_rate=risk_free_rate,
        market_risk_premium=market_risk_premium,
        credit_risk_premium=credit_risk_premium,
        tax_rate=tax_rate,
        inflation=inflation,
    )
    
    try:
        result = calculate_wacc(capm_inputs)
        calculated_wacc = result.wacc_real_pre_tax
        
        # Show derived parameters (read-only)
        st.divider()
        st.markdown("##### 3.2 Derived")

        col1, col2 = st.columns(2)
        with col1:
            with st.container(border=True):
                st.metric("3.2.1 Equity beta", format_number(result.equity_beta, 4))
            with st.container(border=True):
                st.metric("3.2.2 Cost of equity (Re)", format_percent(result.cost_of_equity_nominal))
        with col2:
            with st.container(border=True):
                st.metric("3.2.3 Cost of debt (Rd)", format_percent(result.cost_of_debt_nominal))

        # Final WACC
        with st.container(border=True):
            st.metric("3.2.5 Calculated WACC (real, pre-tax)", format_percent(calculated_wacc))
        
        _render_apply_row(calculated_wacc, f"{MODULE_KEY}_apply_capm")
            
    except ValueError as e:
        st.error(f"Calculation error: {e}")


def _render_derived_section() -> None:
    """Render 3.2 Derived parameters."""
    st.markdown("##### 3.2 Derived parameters")
    st.caption("Modify intermediate values directly")
    
    col1, col2 = st.columns(2)
    
    with col1:
        cost_of_equity = st.number_input(
            "3.2.1 Cost of equity (Re)",
            value=get_config_value(MODULE_KEY, "cost_of_equity", BASELINE_DERIVED["cost_of_equity_nominal"]),
            min_value=0.0,
            max_value=0.30,
            step=0.001,
            format="%.4f",
            key=f"{MODULE_KEY}_cost_of_equity",
            help="Nominal cost of equity"
        )
        
        cost_of_debt = st.number_input(
            "3.2.2 Cost of debt (Rd)",
            value=get_config_value(MODULE_KEY, "cost_of_debt", BASELINE_DERIVED["cost_of_debt_nominal"]),
            min_value=0.0,
            max_value=0.20,
            step=0.001,
            format="%.4f",
            key=f"{MODULE_KEY}_cost_of_debt",
            help="Nominal cost of debt"
        )
        
        debt_ratio = st.number_input(
            "3.2.3 Debt ratio (S)",
            value=get_config_value(MODULE_KEY, "debt_ratio_derived", BASELINE_DERIVED["debt_ratio"]),
            min_value=0.0,
            max_value=0.99,
            step=0.01,
            format="%.2f",
            key=f"{MODULE_KEY}_debt_ratio_derived",
            help="Debt share D/(D+E)"
        )
    
    with col2:
        tax_rate = st.number_input(
            "3.2.4 Tax rate (tau)",
            value=get_config_value(MODULE_KEY, "tax_rate_derived", BASELINE_DERIVED["tax_rate"]),
            min_value=0.0,
            max_value=0.50,
            step=0.001,
            format="%.3f",
            key=f"{MODULE_KEY}_tax_rate_derived",
            help="Corporate tax rate"
        )
        
        inflation = st.number_input(
            "3.2.5 Inflation (pi)",
            value=get_config_value(MODULE_KEY, "inflation_derived", BASELINE_DERIVED["inflation"]),
            min_value=-0.05,
            max_value=0.20,
            step=0.001,
            format="%.4f",
            key=f"{MODULE_KEY}_inflation_derived",
            help="CPIF inflation"
        )
    
    # Calculate
    wacc_nom, wacc_real = _calculate_wacc_from_derived(
        cost_of_equity, cost_of_debt, debt_ratio, tax_rate, inflation
    )
    
    # Final WACC with delta
    st.divider()
    with st.container(border=True):
        delta = wacc_real - BASELINE_WACC
        st.metric(
            "Calculated WACC (real, pre-tax)",
            format_percent(wacc_real),
            delta=f"{delta*100:+.2f} pp" if abs(delta) > 0.0001 else None
        )
    
    _render_apply_row(wacc_real, f"{MODULE_KEY}_apply_derived")


def _render_direct_section() -> None:
    """Render direct WACC input."""
    st.markdown("##### Direct input")
    st.caption("Enter WACC directly (real, pre-tax)")
    
    direct_wacc = st.number_input(
        "WACC (real, pre-tax)",
        value=get_config_value(MODULE_KEY, "direct_wacc", BASELINE_WACC),
        min_value=0.01,
        max_value=0.15,
        step=0.0001,
        format="%.4f",
        key=f"{MODULE_KEY}_direct_wacc",
        help="Direct WACC entry"
    )
    
    # Show baseline comparison if modified
    if abs(direct_wacc - BASELINE_WACC) > 0.0001:
        delta = direct_wacc - BASELINE_WACC
        st.caption(f"= {format_percent(direct_wacc)} :orange[({delta*100:+.2f} pp from baseline)]")
    
    _render_apply_row(direct_wacc, f"{MODULE_KEY}_apply_direct")


# =============================================================================
# INCENTIVE PARAMETER SECTIONS
# =============================================================================

def _render_quality_section(config: Dict[str, Any]) -> None:
    """Render 3.3 Quality adjustment parameters."""
    
    # CEMI adjustment
    st.markdown("###### CEMI adjustment")
    adj_max_cemi4 = st.slider(
        "Max CEMI4 adjustment",
        min_value=0.0,
        max_value=1.0,
            value=get_config_value(MODULE_KEY_QA, "adj_max_cemi4", BASELINE_INCENTIVE["adj_max_cemi4"]),
        step=0.05,
        format="%.2f",
        key=f"{MODULE_KEY_QA}_adj_max_cemi4",
        help="Maximum share of incentive reducible for worsened CEMI4"
    )
    
    if abs(adj_max_cemi4 - BASELINE_INCENTIVE["adj_max_cemi4"]) > 0.001:
        config["adj_max_cemi4"] = adj_max_cemi4
        st.caption(f":orange[Modified] (baseline: {BASELINE_INCENTIVE['adj_max_cemi4']:.2f})")
    
    st.divider()
    
    # AIT costs
    st.markdown("###### AIT costs (SEK/kWh)")
    ait_df = _create_cost_dataframe("ait")
    edited_ait = st.data_editor(
        ait_df,
        key=f"{MODULE_KEY_QA}_ait_editor",
        width='stretch',
        hide_index=False,
        column_config={
            "Unannounced": st.column_config.NumberColumn(format="%.2f"),
            "Announced": st.column_config.NumberColumn(format="%.2f"),
        }
    )
    ait_costs = _dataframe_to_cost_dict(edited_ait, "ait")
    if ait_costs != BASELINE_INCENTIVE["ait_costs"]:
        config["ait_costs"] = ait_costs
        st.caption(":orange[AIT costs modified]")
    
    st.divider()
    
    # AIF costs
    st.markdown("###### AIF costs (SEK/kW)")
    aif_df = _create_cost_dataframe("aif")
    edited_aif = st.data_editor(
        aif_df,
        key=f"{MODULE_KEY_QA}_aif_editor",
        width='stretch',
        hide_index=False,
        column_config={
            "Unannounced": st.column_config.NumberColumn(format="%.2f"),
            "Announced": st.column_config.NumberColumn(format="%.2f"),
        }
    )
    aif_costs = _dataframe_to_cost_dict(edited_aif, "aif")
    if aif_costs != BASELINE_INCENTIVE["aif_costs"]:
        config["aif_costs"] = aif_costs
        st.caption(":orange[AIF costs modified]")


def _render_netloss_section(config: Dict[str, Any]) -> None:
    """Render 3.4 Network loss adjustment parameters."""
    
    col1, col2 = st.columns(2)
    
    with col1:
        sharing = st.slider(
            "Sharing factor",
            min_value=0.0,
            max_value=1.0,
            value=get_config_value(MODULE_KEY_QA, "sharing_netloss", BASELINE_INCENTIVE["sharing_netloss"]),
            step=0.05,
            format="%.2f",
            key=f"{MODULE_KEY_QA}_sharing_netloss",
            help="Share of gain or loss retained by company"
        )
        
        if abs(sharing - BASELINE_INCENTIVE["sharing_netloss"]) > 0.001:
            config["sharing_netloss"] = sharing
            st.caption(f":orange[Modified] (baseline: {BASELINE_INCENTIVE['sharing_netloss']:.2f})")
    
    with col2:
        st.markdown("**Electricity price (K_NF) per year**")
        k_nf_df = _create_yearly_dataframe("k_nf", "Price (SEK/MWh)")
        edited_k_nf = st.data_editor(
            k_nf_df,
            key=f"{MODULE_KEY_QA}_k_nf_editor",
            width='stretch',
            hide_index=False,
            column_config={
                "Price (SEK/MWh)": st.column_config.NumberColumn(format="%.2f"),
            }
        )
        k_nf_dict = _dataframe_to_yearly_dict(edited_k_nf, "Price (SEK/MWh)")
        if k_nf_dict != BASELINE_INCENTIVE["k_nf"]:
            config["k_nf"] = k_nf_dict
            st.caption(":orange[Electricity price modified]")


def _render_load_section(config: Dict[str, Any]) -> None:
    """Render 3.5 Utilization rate adjustment parameters."""
    st.info("Computed automatically based on company data. Use toggle above to enable/disable.")


def _render_caps_section(config: Dict[str, Any]) -> None:
    """Render 3.6 Aggregate adjustment cap parameters."""
    st.markdown("Maximum aggregate incentive adjustment (share of WACC)")
    
    adj_agg = st.slider(
        "Max total per year",
        min_value=0.0,
        max_value=1.0,
        value=get_config_value(MODULE_KEY_QA, "adj_max_agg", BASELINE_INCENTIVE["adj_max_agg"]),
        step=0.05,
        format="%.3f",
        key=f"{MODULE_KEY_QA}_adj_max_agg",
        help="Maximum aggregate incentive adjustment per year"
    )
    
    if abs(adj_agg - BASELINE_INCENTIVE["adj_max_agg"]) > 0.001:
        config["adj_max_agg"] = adj_agg
        st.caption(f":orange[Modified] (baseline: {BASELINE_INCENTIVE['adj_max_agg']:.3f})")


def _render_kpi_section(config: Dict[str, Any]) -> None:
    """Render 3.7 KPI factors."""
    st.markdown("KPI factors for indexation to 2022 prices.")
    
    kpi_df = _create_yearly_dataframe("kpi", "KPI factor")
    edited_kpi = st.data_editor(
        kpi_df,
        key=f"{MODULE_KEY_QA}_kpi_editor",
        width='stretch',
        hide_index=False,
        column_config={
            "KPI factor": st.column_config.NumberColumn(format="%.4f"),
        }
    )
    kpi_dict = _dataframe_to_yearly_dict(edited_kpi, "KPI factor")
    if kpi_dict != BASELINE_INCENTIVE["kpi"]:
        config["kpi"] = kpi_dict
        st.caption(":orange[KPI factors modified]")


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _create_cost_dataframe(cost_type: str) -> pd.DataFrame:
    """Create DataFrame for AIT/AIF costs."""
    baseline = get_config_value(MODULE_KEY_QA, f"{cost_type}_costs", BASELINE_INCENTIVE[f"{cost_type}_costs"])
    
    data = []
    for sni, label in SNI_LABELS.items():
        data.append({
            "Customer type": label,
            "Unannounced": baseline[f"o_{sni}"],
            "Announced": baseline[f"a_{sni}"],
        })
    
    df = pd.DataFrame(data)
    df = df.set_index("Customer type")
    return df


def _dataframe_to_cost_dict(df: pd.DataFrame, cost_type: str) -> Dict[str, float]:
    """Convert DataFrame back to cost dict."""
    result = {}
    label_to_sni = {v: k for k, v in SNI_LABELS.items()}
    
    for label in df.index:
        sni = label_to_sni.get(label)
        if sni is not None:
            result[f"o_{sni}"] = float(df.loc[label, "Unannounced"])
            result[f"a_{sni}"] = float(df.loc[label, "Announced"])
    
    return result


def _create_yearly_dataframe(param_key: str, column_name: str) -> pd.DataFrame:
    """Create DataFrame for per-year parameters."""
    baseline = get_config_value(MODULE_KEY_QA, param_key, BASELINE_INCENTIVE[param_key])
    
    data = []
    for year in [2024, 2025, 2026, 2027]:
        data.append({
            "Year": year,
            column_name: baseline[year],
        })
    
    df = pd.DataFrame(data)
    df = df.set_index("Year")
    return df


def _dataframe_to_yearly_dict(df: pd.DataFrame, column_name: str) -> Dict[int, float]:
    """Convert DataFrame back to yearly dict."""
    result = {}
    for year in df.index:
        result[int(year)] = float(df.loc[year, column_name])
    return result
"""
Module 3: Cost of Capital

Handles WACC and related parameters.
Parameter-IDs: 3.1.X (base), 3.2.X (derived), 3.3-3.6 (adjustments)
Variable-IDs: 30.X
"""

import streamlit as st
import pandas as pd
from typing import Dict, Any

from calculations.wacc_calculations import (
    CAPMInputs,
    calculate_wacc,
    BASELINE_WACC,
)
from frontend.common.formatting import format_percent

MODULE_KEY = "m3_cost_of_capital"
MODULE_KEY_QA = "m3_quality_adjustments"

# Baseline CAPM parameters (from User Manual Table 6)
BASELINE_CAPM = CAPMInputs()

# Baseline derived parameters (calculated from CAPM baseline)
BASELINE_DERIVED = {
    "cost_of_equity_nominal": 0.0645,   # Re: Rf + βₑ × MRP
    "cost_of_debt_nominal": 0.0401,     # Rd: Rf + credit spread
    "debt_ratio": 0.36,                  # S: debt ratio
    "tax_rate": 0.206,                   # τ: corporate tax
    "inflation": 0.0202,                 # π: CPIF
    "wacc_nominal_pre_tax": 0.0664,      # WACC nominal
    "wacc_real_pre_tax": BASELINE_WACC,  # 0.0453
}

# Customer types for AIT/AIF (Swedish regulatory terms)
SNI_LABELS = {
    1: "Jordbruk",
    2: "Industri",
    3: "Handel/tjänster",
    4: "Offentlig verksamhet",
    5: "Hushåll",
    6: "Gränspunkt",
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
        WACC_nom_after_tax = (1 - S) × Re + S × Rd × (1 - τ)
        WACC_nom_pre_tax   = WACC_nom_after_tax / (1 - τ)
        WACC_real          = (1 + WACC_nom_pre_tax) / (1 + π) - 1
    
    Args:
        cost_of_equity: Re - Cost of equity (nominal, after tax)
        cost_of_debt: Rd - Cost of debt (nominal, pre-tax)
        debt_ratio: S - Debt ratio D/(D+E)
        tax_rate: τ - Corporate tax rate
        inflation: π - Inflation (CPIF)
    
    Returns:
        Tuple (wacc_nominal_pre_tax, wacc_real_pre_tax)
    """
    # WACC after tax (weighted average)
    wacc_nominal_after_tax = (
        (1 - debt_ratio) * cost_of_equity + 
        debt_ratio * cost_of_debt * (1 - tax_rate)
    )
    
    # Convert to pre-tax
    wacc_nominal_pre_tax = wacc_nominal_after_tax / (1 - tax_rate)
    
    # Fisher: nominal → real
    wacc_real_pre_tax = (1 + wacc_nominal_pre_tax) / (1 + inflation) - 1
    
    return wacc_nominal_pre_tax, wacc_real_pre_tax


def _render_apply_row(new_wacc: float, button_key: str) -> None:
    """
    Render Apply/Reset buttons and current WACC info in a single row.
    
    Layout: [Apply][Reset][Current WACC info]
    """
    current_wacc = st.session_state[f"{MODULE_KEY}_current_wacc"]
    
    cols = st.columns([0.8, 0.8, 2.5, 10])
    
    with cols[0]:
        st.button("Apply", key=button_key, type="primary", on_click=_set_wacc, args=(new_wacc,))
    
    with cols[1]:
        st.button("Reset", key=f"{button_key}_reset", on_click=_set_wacc, args=(BASELINE_WACC,))
    
    with cols[2]:
        st.markdown(f"<p style='margin-top: 16px;'>Active WACC: <b>{format_percent(current_wacc)}</b></p>", unsafe_allow_html=True)


def _set_wacc(value: float) -> None:
    """Callback to set WACC value."""
    st.session_state[f"{MODULE_KEY}_current_wacc"] = value


def render() -> Dict[str, Any]:
    """
    Render Module 3: Cost of capital.
    
    Three input methods via radio button:
    1. CAPM components - calculate from base parameters
    2. Derived parameters - modify Re, Rd, S, τ, π directly
    3. Direct input - enter WACC directly
    
    Returns:
        Dict with user selections:
        - wacc_override: New WACC value or None for baseline
    """
    config: Dict[str, Any] = {}
    
    st.subheader("3. Cost of Capital")
    
    # Initialize session state
    if f"{MODULE_KEY}_current_wacc" not in st.session_state:
        st.session_state[f"{MODULE_KEY}_current_wacc"] = BASELINE_WACC
    
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
    
    return config


def _render_capm_section() -> None:
    """Render 3.1 Base parameters with LaTeX formulas."""
    st.markdown("##### 3.1 Base parameters")
    st.caption("WACC derived from CAPM inputs")
    
    col1, col2 = st.columns(2)
    
    with col1:
        debt_ratio = st.number_input(
            "3.1.1 Debt ratio (S)",
            value=BASELINE_CAPM.debt_ratio,
            min_value=0.0,
            max_value=0.99,
            step=0.01,
            format="%.2f",
            key=f"{MODULE_KEY}_debt_ratio",
            help="Debt share of total capital D/(D+E)"
        )
        
        asset_beta = st.number_input(
            "3.1.2 Asset beta",
            value=BASELINE_CAPM.asset_beta,
            min_value=0.0,
            max_value=2.0,
            step=0.01,
            format="%.2f",
            key=f"{MODULE_KEY}_asset_beta",
            help="Systematic risk (unlevered assets)"
        )
        
        risk_free_rate = st.number_input(
            "3.1.3 Risk-free rate (Rf)",
            value=BASELINE_CAPM.risk_free_rate,
            min_value=0.0,
            max_value=0.20,
            step=0.001,
            format="%.4f",
            key=f"{MODULE_KEY}_risk_free_rate",
            help="10-year Swedish government bond yield"
        )
        
        market_risk_premium = st.number_input(
            "3.1.4 Market risk premium",
            value=BASELINE_CAPM.market_risk_premium,
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
            value=BASELINE_CAPM.credit_risk_premium,
            min_value=0.0,
            max_value=0.10,
            step=0.001,
            format="%.4f",
            key=f"{MODULE_KEY}_credit_risk_premium",
            help="Company credit risk premium"
        )
        
        tax_rate = st.number_input(
            "3.1.6 Tax rate (τ)",
            value=BASELINE_CAPM.tax_rate,
            min_value=0.0,
            max_value=0.50,
            step=0.001,
            format="%.3f",
            key=f"{MODULE_KEY}_tax_rate",
            help="Corporate tax rate"
        )
        
        inflation = st.number_input(
            "3.1.7 Inflation (π, CPIF)",
            value=BASELINE_CAPM.inflation,
            min_value=0.0,
            max_value=0.20,
            step=0.001,
            format="%.4f",
            key=f"{MODULE_KEY}_inflation",
            help="Expected inflation (CPIF)"
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
                st.metric("3.2.1 Equity beta", f"{result.equity_beta:.4f}")
            with st.container(border=True):
                st.metric("3.2.2 Cost of equity (Re)", format_percent(result.cost_of_equity_nominal))
        with col2:
            with st.container(border=True):
                st.metric("3.2.3 Cost of debt (Rd)", format_percent(result.cost_of_debt_nominal))

        # Final WACC and Apply/Reset/Info row
        with st.container(border=True):
            st.metric("Final WACC", format_percent(calculated_wacc))
        
        _render_apply_row(calculated_wacc, f"{MODULE_KEY}_use_capm")
            
    except ValueError as e:
        st.error(f"Calculation error: {e}")


def _render_derived_section() -> None:
    """
    Render 3.2 Derived parameters for direct input.
    
    Inputs: Re, Rd, S, τ, π
    Output: WACC nominal and real (calculated)
    """
    st.markdown("##### 3.2 Derived")
    st.caption("Direct input of equity and debt costs")
    
    col1, col2 = st.columns(2)
    
    with col1:
        cost_of_equity = st.number_input(
            "3.2.2 Cost of equity (Re)",
            value=BASELINE_DERIVED["cost_of_equity_nominal"],
            min_value=0.0,
            max_value=0.30,
            step=0.001,
            format="%.4f",
            key=f"{MODULE_KEY}_derived_cost_equity",
            help="Nominal cost of equity (post-tax). Baseline: Rf + βₑ × MRP"
        )
        
        cost_of_debt = st.number_input(
            "3.2.3 Cost of debt (Rd)",
            value=BASELINE_DERIVED["cost_of_debt_nominal"],
            min_value=0.0,
            max_value=0.20,
            step=0.001,
            format="%.4f",
            key=f"{MODULE_KEY}_derived_cost_debt",
            help="Nominal cost of debt (pre-tax). Baseline: Rf + credit risk premium"
        )
        
        debt_ratio = st.number_input(
            "3.1.1 Debt ratio (S)",
            value=BASELINE_DERIVED["debt_ratio"],
            min_value=0.0,
            max_value=0.99,
            step=0.01,
            format="%.2f",
            key=f"{MODULE_KEY}_derived_debt_ratio",
            help="Debt share of total capital D/(D+E)"
        )
    
    with col2:
        tax_rate = st.number_input(
            "3.1.6 Tax rate (τ)",
            value=BASELINE_DERIVED["tax_rate"],
            min_value=0.0,
            max_value=0.50,
            step=0.001,
            format="%.3f",
            key=f"{MODULE_KEY}_derived_tax_rate",
            help="Corporate tax rate"
        )
        
        inflation = st.number_input(
            "3.1.7 Inflation (π, CPIF)",
            value=BASELINE_DERIVED["inflation"],
            min_value=0.0,
            max_value=0.20,
            step=0.001,
            format="%.4f",
            key=f"{MODULE_KEY}_derived_inflation",
            help="Expected inflation for Fisher conversion"
        )
    
    # Calculate WACC from derived parameters
    wacc_nominal, wacc_real = _calculate_wacc_from_derived(
        cost_of_equity=cost_of_equity,
        cost_of_debt=cost_of_debt,
        debt_ratio=debt_ratio,
        tax_rate=tax_rate,
        inflation=inflation
    )
    
    # Final WACC and Apply/Reset/Info row
    st.divider()
    with st.container(border=True):
        delta = wacc_real - BASELINE_WACC
        st.metric(
            "Final WACC",
            format_percent(wacc_real),
            delta=f"{delta*100:+.2f} pp" if abs(delta) > 0.0001 else None
        )
    
    _render_apply_row(wacc_real, f"{MODULE_KEY}_use_derived")


def _render_direct_section() -> None:
    """Render direct WACC input."""
    st.markdown("##### 3.2.5 Direct input")
    st.caption("Direct WACC input")
    
    direct_wacc = st.number_input(
        "Real WACC pre-tax",
        value=BASELINE_WACC,
        min_value=0.01,
        max_value=0.15,
        step=0.0001,
        format="%.4f",
        key=f"{MODULE_KEY}_direct_wacc",
        help="Direct WACC entry"
    )
    
    # Show as percent with baseline comparison if modified
    if abs(direct_wacc - BASELINE_WACC) > 0.0001:
        delta = direct_wacc - BASELINE_WACC
        st.caption(f"= {format_percent(direct_wacc)} :orange[({delta*100:+.2f} pp from baseline)]")
    
    _render_apply_row(direct_wacc, f"{MODULE_KEY}_use_direct")


# =============================================================================
# QUALITY ADJUSTMENTS (3.3-3.6)
# =============================================================================

def render_quality_adjustments() -> Dict[str, Any]:
    """
    Render Quality Adjustments (3.3-3.6).
    
    All inputs are always displayed. Only values differing from baseline
    are saved to config.
    
    Returns:
        Dict with modified incentive parameters
    """
    config: Dict[str, Any] = {}
    
    st.subheader("3.3-3.6 Quality Adjustments")
    st.caption("Adjust cost of capital for quality, network loss and utilization")
    
    # === ENABLE/DISABLE ===
    st.markdown("##### Enable adjustments")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        enable_quality = st.checkbox(
            "3.3 Quality",
            value=BASELINE_INCENTIVE["enable_quality"],
            key=f"{MODULE_KEY_QA}_enable_quality",
            help="Enable quality adjustment (CEMI/AIT/AIF)"
        )
        if enable_quality != BASELINE_INCENTIVE["enable_quality"]:
            config["enable_quality"] = enable_quality
    
    with col2:
        enable_netloss = st.checkbox(
            "3.4 Network loss",
            value=BASELINE_INCENTIVE["enable_netloss"],
            key=f"{MODULE_KEY_QA}_enable_netloss",
            help="Enable network loss adjustment"
        )
        if enable_netloss != BASELINE_INCENTIVE["enable_netloss"]:
            config["enable_netloss"] = enable_netloss
    
    with col3:
        enable_load = st.checkbox(
            "3.5 Utilization rate",
            value=BASELINE_INCENTIVE["enable_load"],
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


def _render_quality_section(config: Dict[str, Any]) -> None:
    """Render 3.3 Quality adjustment parameters."""
    
    # CEMI adjustment
    st.markdown("###### CEMI adjustment")
    adj_max_cemi4 = st.slider(
        "Max CEMI4 adjustment",
        min_value=0.0,
        max_value=1.0,
        value=BASELINE_INCENTIVE["adj_max_cemi4"],
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
        use_container_width=True,
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
        use_container_width=True,
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
            value=BASELINE_INCENTIVE["sharing_netloss"],
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
            use_container_width=True,
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
        value=BASELINE_INCENTIVE["adj_max_agg"],
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
        use_container_width=True,
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
    baseline = BASELINE_INCENTIVE[f"{cost_type}_costs"]
    
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
    baseline = BASELINE_INCENTIVE[param_key]
    
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
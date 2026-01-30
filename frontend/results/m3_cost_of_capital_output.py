"""
M3 Cost of Capital - Output Display

Displays WACC calculation chain based on input method:
- "capm": Full chain 3.1.X (base) -> 3.2.X (derived) -> WACC
- "derived": Partial chain 3.2.X (derived) -> WACC
- "direct" or "baseline": Only final WACC (3.2.5)

Variable-IDs:
- 3.1.X: CAPM base parameters
- 3.2.X: Derived WACC values
- 30.2.5: Network loss adjustment
- 30.3.5: Utilization rate adjustment
- 30.4.59: Quality adjustment
- 30.5.2: Total incentive adjustment
"""

import streamlit as st
import pandas as pd
from typing import Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from pipeline.core import PipelineResult


# Baseline values for comparison
BASELINE_CAPM = {
    "debt_ratio": 0.36,
    "asset_beta": 0.37,
    "risk_free_rate": 0.0287,
    "market_risk_premium": 0.0668,
    "credit_risk_premium": 0.0114,
    "tax_rate": 0.206,
    "inflation": 0.0202,
}

BASELINE_DERIVED = {
    "equity_beta": 0.54,
    "cost_of_equity_nominal": 0.0645,
    "cost_of_debt_nominal": 0.0401,
    "wacc_nominal_pre_tax": 0.0664,
    "wacc_real_pre_tax": 0.0453,
}

BASELINE_WACC = 0.0453


def _format_tkr(value: float, show_sign: bool = False) -> str:
    if pd.isna(value):
        return "-"
    if show_sign and value > 0:
        return f"+{value:,.0f}"
    return f"{value:,.0f}"


def _format_percent(value: float, decimals: int = 2) -> str:
    if pd.isna(value):
        return "-"
    return f"{value*100:.{decimals}f}%"


def _format_number(value: float, decimals: int = 4) -> str:
    if pd.isna(value):
        return "-"
    return f"{value:.{decimals}f}"


def _calc_delta(case_val: float, baseline_val: float) -> tuple:
    if pd.isna(case_val) or pd.isna(baseline_val):
        return None, None
    delta_abs = case_val - baseline_val
    delta_pct = (delta_abs / baseline_val * 100) if baseline_val != 0 else 0
    return delta_abs, delta_pct


def render(
    case: "PipelineResult",
    baseline: "PipelineResult",
    ui_config: Dict[str, Any]
) -> None:
    """Render M3 cost of capital outputs."""
    
    case_ir = case.post_dea.user_intaktsram
    baseline_ir = baseline.post_dea.user_intaktsram
    
    # Get WACC chain info from pre_dea
    wacc_input_method = getattr(case.pre_dea, 'wacc_input_method', 'baseline')
    wacc_inputs = getattr(case.pre_dea, 'wacc_inputs', None)
    wacc_derived = getattr(case.pre_dea, 'wacc_derived', None)
    wacc_case = case.pre_dea.wacc_used or BASELINE_WACC
    
    # === WACC SECTION ===
    _render_wacc_section(wacc_input_method, wacc_inputs, wacc_derived, wacc_case)
    
    st.divider()
    
    # === INCENTIVE ADJUSTMENTS SECTION ===
    _render_incentive_section(case_ir, baseline_ir)
    
    st.divider()
    
    # === FUTURE: DETAILED INCENTIVE BREAKDOWN ===
    _render_incentive_placeholder()


def _render_wacc_section(
    wacc_input_method: str,
    wacc_inputs: dict,
    wacc_derived: dict,
    wacc_case: float
) -> None:
    """Render WACC parameters based on input method."""
    
    st.markdown("**WACC Parameters**")
    
    method_labels = {
        "capm": "CAPM (base parameters)",
        "derived": "Derived parameters",
        "direct": "Direct input",
        "baseline": "Baseline",
    }
    st.caption(f"Input method: {method_labels.get(wacc_input_method, wacc_input_method)}")
    
    # === CAPM: Show 3.1.X base parameters ===
    if wacc_input_method == "capm" and wacc_inputs:
        st.markdown("##### 3.1 Base Parameters")
        
        capm_params = [
            ("3.1.1", "Debt ratio (S)", "debt_ratio", "ratio"),
            ("3.1.2", "Asset beta", "asset_beta", "ratio"),
            ("3.1.3", "Risk-free rate (Rf)", "risk_free_rate", "percent"),
            ("3.1.4", "Market risk premium", "market_risk_premium", "percent"),
            ("3.1.5", "Credit risk premium", "credit_risk_premium", "percent"),
            ("3.1.6", "Tax rate (tau)", "tax_rate", "percent"),
            ("3.1.7", "Inflation (pi)", "inflation", "percent"),
        ]
        
        capm_rows = []
        for var_id, label, key, fmt in capm_params:
            case_val = wacc_inputs.get(key, BASELINE_CAPM[key])
            baseline_val = BASELINE_CAPM[key]
            delta, _ = _calc_delta(case_val, baseline_val)
            
            if fmt == "percent":
                case_str = _format_percent(case_val, 2)
                baseline_str = _format_percent(baseline_val, 2)
                delta_str = f"{delta*100:+.2f} pp" if delta and abs(delta) > 0.0001 else "-"
            else:
                case_str = _format_number(case_val, 2)
                baseline_str = _format_number(baseline_val, 2)
                delta_str = f"{delta:+.2f}" if delta and abs(delta) > 0.001 else "-"
            
            capm_rows.append({
                "ID": var_id,
                "Parameter": label,
                "Case": case_str,
                "Baseline": baseline_str,
                "Delta": delta_str,
            })
        
        st.dataframe(pd.DataFrame(capm_rows), hide_index=True, use_container_width=True)
        st.markdown("")
    
    # === CAPM or DERIVED: Show 3.2.X derived values ===
    if wacc_input_method in ["capm", "derived"] and wacc_derived:
        st.markdown("##### 3.2 Derived Values")
        
        derived_params = [
            ("3.2.1", "Equity beta", "equity_beta", "ratio"),
            ("3.2.2", "Cost of equity (Re)", "cost_of_equity_nominal", "percent"),
            ("3.2.3", "Cost of debt (Rd)", "cost_of_debt_nominal", "percent"),
            ("3.2.4", "WACC nominal pre-tax", "wacc_nominal_pre_tax", "percent"),
            ("3.2.5", "WACC real pre-tax", "wacc_real_pre_tax", "percent"),
        ]
        
        derived_rows = []
        for var_id, label, key, fmt in derived_params:
            case_val = wacc_derived.get(key)
            baseline_val = BASELINE_DERIVED.get(key)
            
            if case_val is None or baseline_val is None:
                continue
            
            delta, _ = _calc_delta(case_val, baseline_val)
            
            if fmt == "percent":
                case_str = _format_percent(case_val, 2)
                baseline_str = _format_percent(baseline_val, 2)
                delta_str = f"{delta*100:+.2f} pp" if delta and abs(delta) > 0.0001 else "-"
            else:
                case_str = _format_number(case_val, 2)
                baseline_str = _format_number(baseline_val, 2)
                delta_str = f"{delta:+.2f}" if delta and abs(delta) > 0.001 else "-"
            
            derived_rows.append({
                "ID": var_id,
                "Parameter": label,
                "Case": case_str,
                "Baseline": baseline_str,
                "Delta": delta_str,
            })
        
        st.dataframe(pd.DataFrame(derived_rows), hide_index=True, use_container_width=True)
    
    # === DIRECT or BASELINE: Show only final WACC ===
    elif wacc_input_method in ["direct", "baseline"]:
        st.markdown("##### 3.2.5 WACC (real, pre-tax)")
        
        wacc_delta = wacc_case - BASELINE_WACC
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric(
                "Applied WACC",
                _format_percent(wacc_case, 2),
                delta=f"{wacc_delta*100:+.2f} pp" if abs(wacc_delta) > 0.0001 else None
            )
        with col2:
            st.metric("Baseline WACC", _format_percent(BASELINE_WACC, 2))


def _render_incentive_section(case_ir: pd.Series, baseline_ir: pd.Series) -> None:
    """Render incentive adjustments summary."""
    
    st.markdown("**Incentive Adjustments**")
    
    inc_components = [
        ("30.2.5", "Network loss adjustment", "Natforlustjustering_Total"),
        ("30.3.5", "Utilization rate adjustment", "Belastningsjustering_Total"),
        ("30.4.59", "Quality adjustment", "Kvalitetsjustering_Total"),
    ]
    
    inc_rows = []
    for var_id, label, col_key in inc_components:
        c_val = case_ir.get(col_key, 0)
        b_val = baseline_ir.get(col_key, 0)
        delta_abs, _ = _calc_delta(c_val, b_val)
        inc_rows.append({
            "ID": var_id,
            "Component": label,
            "Case (tkr)": _format_tkr(c_val, show_sign=True),
            "Baseline (tkr)": _format_tkr(b_val, show_sign=True),
            "Delta (tkr)": _format_tkr(delta_abs, show_sign=True) if delta_abs is not None else "-",
        })
    
    # Total row
    total_case = case_ir.get("Incitamentjustering_Total", 0)
    total_baseline = baseline_ir.get("Incitamentjustering_Total", 0)
    total_delta, _ = _calc_delta(total_case, total_baseline)
    inc_rows.append({
        "ID": "30.5.2",
        "Component": "Total incentive adjustment",
        "Case (tkr)": _format_tkr(total_case, show_sign=True),
        "Baseline (tkr)": _format_tkr(total_baseline, show_sign=True),
        "Delta (tkr)": _format_tkr(total_delta, show_sign=True) if total_delta is not None else "-",
    })
    
    st.dataframe(pd.DataFrame(inc_rows), hide_index=True, use_container_width=True)
    
    if case_ir.get('Missing_Incentive_Data', False):
        st.warning("Incentive data incomplete for this company.")


def _render_incentive_placeholder() -> None:
    """Placeholder for detailed incentive breakdown (future feature)."""
    
    with st.expander("Detailed incentive breakdown", expanded=False):
        st.info(
            "Detailed per-year and per-component incentive breakdown will be added in a future update. "
            "This will include:\n"
            "- Per-year breakdown of quality, network loss, and utilization adjustments\n"
            "- CEMI4, AIT, and AIF component details\n"
            "- Norm vs. observed values comparison"
        )
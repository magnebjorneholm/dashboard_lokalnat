"""
M3 Cost of Capital - Output Display

Variable-IDs:
- 3.2.5: WACC (real, pre-tax)
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


def _format_tkr(value: float, show_sign: bool = False) -> str:
    if pd.isna(value):
        return "-"
    if show_sign and value > 0:
        return f"+{value:,.0f}"
    return f"{value:,.0f}"


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
    
    # WACC
    st.markdown("**3.2.5 WACC (real, pre-tax)**")
    
    wacc_case = case.pre_dea.wacc_used or 0.0453
    wacc_baseline = 0.0453
    wacc_delta = wacc_case - wacc_baseline
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric(
            "Applied WACC",
            f"{wacc_case:.2%}",
            delta=f"{wacc_delta*100:+.2f} pp" if abs(wacc_delta) > 0.0001 else None
        )
    with col2:
        st.metric("Baseline WACC", f"{wacc_baseline:.2%}")
    
    st.markdown("")
    st.markdown("**Incentive adjustments**")
    
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

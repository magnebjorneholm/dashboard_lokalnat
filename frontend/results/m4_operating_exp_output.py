"""
M4 Operating Expenditures - Output Display

Variable-IDs:
- 40.1.1: Controllable costs (påverkbara)
- 40.1.2: Flexibility services
- 40.2.1: Non-controllable costs (opåverkbara)
"""

import streamlit as st
import pandas as pd
from typing import Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from pipeline.core import PipelineResult

from config.column_names import (
    COL_CONTROLLABLE_PERIOD, COL_CONTROLLABLE_BEFORE,
    COL_OPEX_BEFORE, COL_EFFICIENCY_DEDUCTION,
    COL_METHOD_USED, COL_NON_CONTROLLABLE,
    COL_FLEXIBILITY, COL_INTERRUPTION, COL_STATE_DEDUCTION,
)
from config.glossary import VID_OPEX_ADJUSTABLE, VID_FLEX_SERVICE, VID_NON_ADJUSTABLE
from pipeline.result_helpers import fmt_tkr as _format_tkr, calc_delta as _calc_delta


def render(
    case: "PipelineResult",
    baseline: "PipelineResult",
    ui_config: Dict[str, Any]
) -> None:
    """Render M4 operating expenditures outputs."""
    
    case_ir = case.post_dea.user_revenue_frame
    baseline_ir = baseline.post_dea.user_revenue_frame

    # Controllable costs (before efficiency deduction = the user's input OPEXp)
    st.markdown("**40.1 Controllable costs**")

    # 40.1.1: Show before-efficiency value (matches diagram's "Controllable costs" box)
    pav_before_case = float(case_ir.get(COL_OPEX_BEFORE, case_ir.get(COL_CONTROLLABLE_BEFORE, 0)))
    pav_before_baseline = float(baseline_ir.get(COL_OPEX_BEFORE, baseline_ir.get(COL_CONTROLLABLE_BEFORE, 0)))
    _, pav_pct = _calc_delta(pav_before_case, pav_before_baseline)

    # After efficiency (for reference)
    pav_after_case = float(case_ir.get(COL_CONTROLLABLE_PERIOD, 0))
    pav_after_baseline = float(baseline_ir.get(COL_CONTROLLABLE_PERIOD, 0))

    # Efficiency deduction
    eff_deduction_case = float(case_ir.get(COL_EFFICIENCY_DEDUCTION, 0))

    method_used = case_ir.get(COL_METHOD_USED, 'OPEX')

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(
            f"{VID_OPEX_ADJUSTABLE} Controllable costs",
            f"{pav_before_case:,.0f} tkr",
            delta=f"{pav_pct:+.1f}%" if pav_pct else None
        )
    with col2:
        st.metric("Baseline", f"{pav_before_baseline:,.0f} tkr")
    with col3:
        st.metric("Method", method_used)

    # Show after-efficiency breakdown
    if eff_deduction_case > 0:
        st.caption(
            f"After efficiency deduction: {pav_after_case:,.0f} tkr "
            f"(deduction: -{eff_deduction_case:,.0f} tkr)"
        )
    
    # Non-controllable costs
    st.markdown("")
    st.markdown("**40.2 Non-controllable costs (opåverkbara)**")
    
    opav_case = case_ir.get(COL_NON_CONTROLLABLE, 0)
    opav_baseline = baseline_ir.get(COL_NON_CONTROLLABLE, 0)
    _, opav_pct = _calc_delta(opav_case, opav_baseline)
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric(
            f"{VID_NON_ADJUSTABLE} Non-controllable costs",
            f"{opav_case:,.0f} tkr",
            delta=f"{opav_pct:+.1f}%" if opav_pct else None
        )
    with col2:
        st.metric("Baseline", f"{opav_baseline:,.0f} tkr")
    
    # Other components
    st.markdown("")
    st.markdown("**Other OPEX components**")
    
    other_components = [
        (VID_FLEX_SERVICE, "Flexibility services", COL_FLEXIBILITY),
        ("-", "Interruption compensation (12-24h)", COL_INTERRUPTION),
        ("-", "State aid deduction", COL_STATE_DEDUCTION),
    ]
    
    other_rows = []
    for var_id, label, col_key in other_components:
        c_val = case_ir.get(col_key, 0)
        b_val = baseline_ir.get(col_key, 0)
        if col_key == COL_STATE_DEDUCTION:
            c_val = -c_val if c_val else 0
            b_val = -b_val if b_val else 0
        delta_abs, _ = _calc_delta(c_val, b_val)
        other_rows.append({
            "ID": var_id,
            "Component": label,
            "Case (tkr)": _format_tkr(c_val),
            "Baseline (tkr)": _format_tkr(b_val),
            "Delta (tkr)": _format_tkr(delta_abs, show_sign=True) if delta_abs is not None else "-",
        })
    
    st.dataframe(pd.DataFrame(other_rows), hide_index=True, width='stretch')

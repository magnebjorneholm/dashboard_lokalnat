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
    COL_CONTROLLABLE_PERIOD, COL_METHOD_USED, COL_NON_CONTROLLABLE,
    COL_FLEXIBILITY, COL_INTERRUPTION, COL_STATE_DEDUCTION,
)
from frontend.common.result_helpers import fmt_tkr as _format_tkr, calc_delta as _calc_delta


def render(
    case: "PipelineResult",
    baseline: "PipelineResult",
    ui_config: Dict[str, Any]
) -> None:
    """Render M4 operating expenditures outputs."""
    
    case_ir = case.post_dea.user_revenue_frame
    baseline_ir = baseline.post_dea.user_revenue_frame

    # Controllable costs
    st.markdown("**40.1 Controllable costs**")
    
    pav_case = case_ir.get(COL_CONTROLLABLE_PERIOD, 0)
    pav_baseline = baseline_ir.get(COL_CONTROLLABLE_PERIOD, 0)
    _, pav_pct = _calc_delta(pav_case, pav_baseline)
    
    method_used = case_ir.get(COL_METHOD_USED, 'OPEX')
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(
            "40.1.1 Controllable costs",
            f"{pav_case:,.0f} tkr",
            delta=f"{pav_pct:+.1f}%" if pav_pct else None
        )
    with col2:
        st.metric("Baseline", f"{pav_baseline:,.0f} tkr")
    with col3:
        st.metric("Method", method_used)
    
    # Non-controllable costs
    st.markdown("")
    st.markdown("**40.2 Non-controllable costs (opåverkbara)**")
    
    opav_case = case_ir.get(COL_NON_CONTROLLABLE, 0)
    opav_baseline = baseline_ir.get(COL_NON_CONTROLLABLE, 0)
    _, opav_pct = _calc_delta(opav_case, opav_baseline)
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric(
            "40.2.1 Non-controllable costs",
            f"{opav_case:,.0f} tkr",
            delta=f"{opav_pct:+.1f}%" if opav_pct else None
        )
    with col2:
        st.metric("Baseline", f"{opav_baseline:,.0f} tkr")
    
    # Other components
    st.markdown("")
    st.markdown("**Other OPEX components**")
    
    other_components = [
        ("40.1.2", "Flexibility services", COL_FLEXIBILITY),
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

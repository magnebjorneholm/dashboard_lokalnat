"""
M5 Efficiency Incentive - Output Display

Variable-IDs:
- 50.3.1: Efficiency score
- 50.3.2: Super-efficiency score
- 50.3.3: Efficiency potential
- 50.3.4: Applied efficiency requirement
- 50.4.1: OPEX efficiency adjustment
- 50.4.3: OPEX after adjustment
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


def render(
    case: "PipelineResult",
    baseline: "PipelineResult",
    ui_config: Dict[str, Any],
    user_reid: str = None
) -> None:
    """Render M5 efficiency incentive outputs."""
    
    case_ir = case.post_dea.user_intaktsram
    baseline_ir = baseline.post_dea.user_intaktsram
    
    st.markdown("**50.3 DEA efficiency measures**")
    
    eff_case = case.extraction.efficiency
    eff_baseline = baseline.extraction.efficiency
    potential_case = case.extraction.potential
    effkrav_case = case.post_dea.user_effkrav_proc
    effkrav_baseline = baseline.post_dea.user_effkrav_proc
    is_outlier = case.extraction.is_outlier
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        eff_delta = (eff_case - eff_baseline) if eff_case and eff_baseline else None
        st.metric(
            "50.3.1 Efficiency score",
            f"{eff_case:.3f}" if eff_case else "-",
            delta=f"{eff_delta:+.3f}" if eff_delta and abs(eff_delta) > 0.0001 else None
        )
    
    with col2:
        st.metric(
            "50.3.3 Efficiency potential",
            f"{potential_case:.1%}" if potential_case is not None else "-"
        )
    
    with col3:
        effkrav_delta = (effkrav_case - effkrav_baseline) if effkrav_case and effkrav_baseline else None
        st.metric(
            "50.3.4 Applied requirement",
            f"{effkrav_case:.2%}" if effkrav_case else "-",
            delta=f"{effkrav_delta*100:+.2f} pp" if effkrav_delta and abs(effkrav_delta) > 0.0001 else None
        )
    
    # Super-efficiency if available
    if user_reid and hasattr(case.dea, 'dea_results') and case.dea.dea_results is not None:
        dea_df = case.dea.dea_results
        user_row = dea_df[dea_df['REId'] == user_reid]
        if not user_row.empty and 'Supereffektivitet' in user_row.columns:
            super_eff = user_row['Supereffektivitet'].iloc[0]
            st.metric("50.3.2 Super-efficiency score", f"{super_eff:.3f}")
    
    # Outlier status
    if is_outlier:
        st.warning("This company is classified as an outlier in the DEA analysis (fixed 1% requirement applies).")
    
    st.markdown("")
    st.markdown("**50.4 Efficiency-adjusted costs**")
    
    # Calculate efficiency adjustment amounts
    pav_baseline_val = baseline_ir.get('Paverkbara_Periodsumma', 0)
    pav_efter_case = case_ir.get('Paverkbara_Periodsumma', 0)
    pav_efter_baseline = baseline_ir.get('Paverkbara_Periodsumma', 0)
    
    eff_adj_case = pav_baseline_val - pav_efter_case
    eff_adj_baseline = pav_baseline_val - pav_efter_baseline
    
    eff_rows = [
        {
            "ID": "50.4.1",
            "Component": "OPEX efficiency adjustment",
            "Case (tkr)": _format_tkr(eff_adj_case, show_sign=True),
            "Baseline (tkr)": _format_tkr(eff_adj_baseline, show_sign=True),
        },
        {
            "ID": "50.4.3",
            "Component": "OPEX after adjustment",
            "Case (tkr)": _format_tkr(pav_efter_case),
            "Baseline (tkr)": _format_tkr(pav_efter_baseline),
        },
    ]
    
    st.dataframe(pd.DataFrame(eff_rows), hide_index=True, use_container_width=True)

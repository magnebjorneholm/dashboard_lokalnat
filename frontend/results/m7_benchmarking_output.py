"""
M7 Benchmarking - Output Display

Shows DEA specification and comparison between baseline and custom DEA.
"""

import streamlit as st
import pandas as pd
from typing import Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from pipeline.core import PipelineResult


def render(
    case: "PipelineResult",
    baseline: "PipelineResult",
    ui_config: Dict[str, Any]
) -> None:
    """Render M7 benchmarking outputs."""
    
    addon_config = ui_config.get("addon_benchmarking", {})
    dea_method = addon_config.get("dea_method", "baseline")
    
    st.markdown("**DEA specification**")
    
    if dea_method == "custom":
        dea_inputs = addon_config.get("dea_inputs", [])
        dea_outputs = addon_config.get("dea_outputs", [])
        dea_rts = addon_config.get("dea_rts", "crs")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Inputs:**")
            for inp in dea_inputs:
                st.markdown(f"- {inp}")
        with col2:
            st.markdown("**Outputs:**")
            for out in dea_outputs:
                st.markdown(f"- {out}")
        
        st.markdown(f"**Returns to scale:** {dea_rts.upper()}")
        
        st.markdown("")
        st.markdown("**Comparison: Baseline vs Custom DEA**")
        
        # Get baseline and case efficiency
        eff_baseline_val = baseline.extraction.efficiency
        eff_case_val = case.extraction.efficiency
        pot_baseline_val = baseline.extraction.potential
        pot_case_val = case.extraction.potential
        effkrav_baseline = baseline.post_dea.user_effkrav_proc
        effkrav_case = case.post_dea.user_effkrav_proc
        
        comp_rows = [
            {
                "Metric": "Efficiency score",
                "Baseline DEA": f"{eff_baseline_val:.3f}" if eff_baseline_val else "-",
                "Custom DEA": f"{eff_case_val:.3f}" if eff_case_val else "-",
                "Delta": f"{(eff_case_val - eff_baseline_val):+.3f}" if eff_case_val and eff_baseline_val else "-",
            },
            {
                "Metric": "Efficiency potential",
                "Baseline DEA": f"{pot_baseline_val:.1%}" if pot_baseline_val is not None else "-",
                "Custom DEA": f"{pot_case_val:.1%}" if pot_case_val is not None else "-",
                "Delta": f"{(pot_case_val - pot_baseline_val)*100:+.1f} pp" if pot_case_val is not None and pot_baseline_val is not None else "-",
            },
            {
                "Metric": "Applied requirement",
                "Baseline DEA": f"{effkrav_baseline:.2%}" if effkrav_baseline else "-",
                "Custom DEA": f"{effkrav_case:.2%}" if effkrav_case else "-",
                "Delta": f"{(effkrav_case - effkrav_baseline)*100:+.2f} pp" if effkrav_case and effkrav_baseline else "-",
            },
        ]
        
        st.dataframe(pd.DataFrame(comp_rows), hide_index=True, width='stretch')
        
    else:
        st.info("Using Ei's baseline DEA model.")
        st.caption("Select 'M7 Benchmarking' in Define and configure custom DEA inputs/outputs to run alternative efficiency analysis.")

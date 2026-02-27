"""
M7 Benchmarking - Output Display

Shows DEA specification and comparison between baseline and custom DEA.
"""

import streamlit as st
import pandas as pd
from typing import Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from pipeline.core import PipelineResult

from config.formatting import format_percent, format_pp


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
        effkrav_baseline = baseline.post_dea.user_eff_req_pct
        effkrav_case = case.post_dea.user_eff_req_pct
        
        _score_delta = f"{(eff_case_val - eff_baseline_val):+.3f}".replace(".", ",") if eff_case_val and eff_baseline_val else "-"
        comp_rows = [
            {
                "Metric": "Efficiency score",
                "Baseline DEA": f"{eff_baseline_val:.3f}".replace(".", ",") if eff_baseline_val else "-",
                "Custom DEA": f"{eff_case_val:.3f}".replace(".", ",") if eff_case_val else "-",
                "Delta": _score_delta,
            },
            {
                "Metric": "Efficiency potential",
                "Baseline DEA": format_percent(pot_baseline_val, 1) if pot_baseline_val is not None else "-",
                "Custom DEA": format_percent(pot_case_val, 1) if pot_case_val is not None else "-",
                "Delta": format_pp(pot_case_val - pot_baseline_val, 1) if pot_case_val is not None and pot_baseline_val is not None else "-",
            },
            {
                "Metric": "Applied requirement",
                "Baseline DEA": format_percent(effkrav_baseline) if effkrav_baseline else "-",
                "Custom DEA": format_percent(effkrav_case) if effkrav_case else "-",
                "Delta": format_pp(effkrav_case - effkrav_baseline) if effkrav_case and effkrav_baseline else "-",
            },
        ]

        st.dataframe(
            pd.DataFrame(comp_rows),
            hide_index=True,
            width='stretch',
            column_config={
                "Metric": st.column_config.TextColumn("Metric", width="medium"),
                "Baseline DEA": st.column_config.TextColumn("Baseline DEA", width="small"),
                "Custom DEA": st.column_config.TextColumn("Custom DEA", width="small"),
                "Delta": st.column_config.TextColumn("Delta", width="small"),
            },
        )
        
    else:
        st.info("Using Ei's baseline DEA model.")
        st.caption("Select 'M7 Benchmarking' in Define and configure custom DEA inputs/outputs to run alternative efficiency analysis.")

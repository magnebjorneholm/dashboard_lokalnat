"""
M7 Benchmarking - Output Display

Shows DEA/StoNED specification and comparison between baseline and case efficiency.
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

    if dea_method == "stoned":
        _render_stoned_output(case, baseline, addon_config)
        return

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


def _render_stoned_output(
    case: "PipelineResult",
    baseline: "PipelineResult",
    addon_config: Dict[str, Any],
) -> None:
    """Render StoNED output with model spec and baseline comparison."""
    from data_loaders.stoned_data import load_stoned_model_registry

    model_id = addon_config.get("stoned_model_id", "")
    registry = load_stoned_model_registry()
    info = registry.get(model_id, {})

    st.markdown("**StoNED specification**")

    if info:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Model:** {info.get('label', model_id)}")
            st.markdown(f"**Cost variable:** {info.get('cost_variable', '-')}")
        with col2:
            outputs = info.get("output_variables", [])
            st.markdown(f"**Outputs:** {', '.join(outputs)}")
            rts_label = "VRS" if info.get("rts") == "vrs" else "CRS"
            st.markdown(f"**RTS:** {rts_label}")

    st.markdown("")
    st.markdown("**Comparison: Baseline DEA vs StoNED**")

    eff_baseline_val = baseline.extraction.efficiency
    eff_case_val = case.extraction.efficiency
    pot_baseline_val = baseline.extraction.potential
    pot_case_val = case.extraction.potential
    effkrav_baseline = baseline.post_dea.user_eff_req_pct
    effkrav_case = case.post_dea.user_eff_req_pct

    _score_delta = (
        f"{(eff_case_val - eff_baseline_val):+.3f}".replace(".", ",")
        if eff_case_val and eff_baseline_val
        else "-"
    )
    comp_rows = [
        {
            "Metric": "Efficiency score",
            "Baseline DEA": f"{eff_baseline_val:.3f}".replace(".", ",") if eff_baseline_val else "-",
            "StoNED": f"{eff_case_val:.3f}".replace(".", ",") if eff_case_val else "-",
            "Delta": _score_delta,
        },
        {
            "Metric": "Efficiency potential",
            "Baseline DEA": format_percent(pot_baseline_val, 1) if pot_baseline_val is not None else "-",
            "StoNED": format_percent(pot_case_val, 1) if pot_case_val is not None else "-",
            "Delta": format_pp(pot_case_val - pot_baseline_val, 1) if pot_case_val is not None and pot_baseline_val is not None else "-",
        },
        {
            "Metric": "Applied requirement",
            "Baseline DEA": format_percent(effkrav_baseline) if effkrav_baseline else "-",
            "StoNED": format_percent(effkrav_case) if effkrav_case else "-",
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
            "StoNED": st.column_config.TextColumn("StoNED", width="small"),
            "Delta": st.column_config.TextColumn("Delta", width="small"),
        },
    )

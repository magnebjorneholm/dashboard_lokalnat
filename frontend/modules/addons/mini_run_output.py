"""
M7 Benchmarking - Mini-run inline results.

Renders DEA mini-run results inside the M7 config tab, reusing M5's
efficiency distribution and summary visualizations.
"""

import streamlit as st
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pipeline.mini_run import MiniRunResult

from config.column_names import COL_DEA_EFFICIENCY
from frontend.results._efficiency_charts import (
    get_params,
    render_efficiency_distributions,
    render_efficiency_summary,
)


def render_mini_results(
    result: "MiniRunResult",
    baseline: "MiniRunResult",
) -> None:
    """Render mini-run results inline in the M7 tab."""

    st.divider()
    dea_method = result.dea_method if hasattr(result, "dea_method") else "dea"
    label = "StoNED results" if dea_method == "stoned" else "DEA results"
    st.markdown(f"**{label}** (mini-run)")

    # Build params from current M5 ui_config
    m5_config = st.session_state.get("ui_config", {}).get("m5_efficiency", {})
    params = get_params(m5_config)

    # --- Block 1: Distribution histograms ---
    eff_scores = result.dea_results[COL_DEA_EFFICIENCY].dropna().values

    render_efficiency_distributions(
        eff_scores=eff_scores,
        eff_case=result.user_efficiency,
        eff_baseline=baseline.user_efficiency,
        effkrav_all_df=result.dea_results,
        effkrav_case=result.user_eff_req_annual,
        effkrav_baseline=baseline.user_eff_req_annual,
        params=params,
        key_prefix="m7_mini",
    )

    st.divider()

    # --- Block 2: Company efficiency KPI row ---
    super_eff = result.user_super_efficiency
    if super_eff is not None and super_eff <= 1.0:
        super_eff = None

    render_efficiency_summary(
        eff_case=result.user_efficiency,
        eff_baseline=baseline.user_efficiency,
        potential_case=result.user_potential,
        potential_baseline=baseline.user_potential,
        effkrav_case=result.user_eff_req_annual,
        effkrav_baseline=baseline.user_eff_req_annual,
        is_outlier=result.user_is_outlier,
        super_eff=super_eff,
        case_rank=result.user_rank,
        bl_rank=baseline.user_rank,
        n_total=result.n_companies,
        params=params,
        show_detail_tables=False,
    )

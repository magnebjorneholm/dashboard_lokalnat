"""
M5 Efficiency Incentive - Output Display

Two visual blocks:
1. Efficiency Distribution -- Two Plotly histograms side-by-side:
   (a) Efficiency scores with truncation zone overlay and company markers.
   (b) Annual efficiency requirements distribution with company marker.
2. Company Efficiency Summary -- KPI hero row (4 metrics: score, rank,
   truncated potential, annual requirement) + super-efficiency badge +
   outlier warning + 50.3 measures table + parameters.

Cost impact (efficiency-adjusted costs) is shown in M4 as part of the
OPEX composition waterfall, avoiding duplication.

Variable-IDs:
- 5.2.1-5.3.1: Efficiency calculation parameters
- 50.3.1: Efficiency score
- 50.3.2: Super-efficiency score
- 50.3.3: Efficiency potential (raw)
- 50.3.4: Applied efficiency potential (truncated)
"""

import streamlit as st
import pandas as pd
from typing import Dict, Any, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from pipeline.core import PipelineResult

from config.column_names import (
    COL_DEA_EFFICIENCY, COL_DEA_SUPER_EFF,
    COL_REID,
)
from frontend.results._efficiency_charts import (
    get_params,
    render_efficiency_distributions,
    render_efficiency_summary,
)


# ============================================================================
# HELPERS
# ============================================================================

def _compute_rank(dea_results: pd.DataFrame, user_reid: str) -> Tuple[Optional[int], int]:
    """Compute user's rank among all companies by efficiency score (1 = best).

    Returns (rank, total). rank is None if user not found.
    """
    if dea_results is None or dea_results.empty:
        return None, 0
    df = dea_results[[COL_REID, COL_DEA_EFFICIENCY]].dropna(subset=[COL_DEA_EFFICIENCY])
    df = df.sort_values(COL_DEA_EFFICIENCY, ascending=False).reset_index(drop=True)
    total = len(df)
    matches = df.index[df[COL_REID] == user_reid]
    if len(matches) == 0:
        return None, total
    rank = int(matches[0]) + 1  # 0-indexed -> 1-indexed
    return rank, total


def _get_super_efficiency(case, user_reid):
    """Extract super-efficiency score if available and > 1.0."""
    if not user_reid or not hasattr(case.dea, "dea_results") or case.dea.dea_results is None:
        return None
    dea_df = case.dea.dea_results
    user_row = dea_df[dea_df[COL_REID] == user_reid]
    if user_row.empty or COL_DEA_SUPER_EFF not in user_row.columns:
        return None
    val = user_row[COL_DEA_SUPER_EFF].iloc[0]
    if val is not None and not pd.isna(val) and val > 1.0:
        return val
    return None


# ============================================================================
# MAIN RENDER
# ============================================================================

def render(
    case: "PipelineResult",
    baseline: "PipelineResult",
    ui_config: Dict[str, Any],
    user_reid: str = None
) -> None:
    """Render M5 efficiency incentive outputs."""

    m5_config = ui_config.get("m5_efficiency", {})
    params = get_params(m5_config)

    # --- Block 1: Distributions (shared) ---
    dea_case = case.dea.dea_results.copy()
    eff_scores = dea_case[COL_DEA_EFFICIENCY].dropna().values
    effkrav_df = case.post_dea.all_eff_reqs

    render_efficiency_distributions(
        eff_scores=eff_scores,
        eff_case=case.extraction.efficiency,
        eff_baseline=baseline.extraction.efficiency,
        effkrav_all_df=effkrav_df,
        effkrav_case=case.post_dea.user_eff_req_pct,
        effkrav_baseline=baseline.post_dea.user_eff_req_pct,
        params=params,
        key_prefix="m5",
    )

    st.divider()

    # --- Block 2: Company efficiency summary (shared) ---
    super_eff = _get_super_efficiency(case, user_reid)
    case_rank, case_total = _compute_rank(case.dea.dea_results, user_reid)
    bl_rank, _ = _compute_rank(baseline.dea.dea_results, user_reid)

    render_efficiency_summary(
        eff_case=case.extraction.efficiency,
        eff_baseline=baseline.extraction.efficiency,
        potential_case=case.extraction.potential,
        potential_baseline=baseline.extraction.potential,
        effkrav_case=case.post_dea.user_eff_req_pct,
        effkrav_baseline=baseline.post_dea.user_eff_req_pct,
        is_outlier=case.extraction.is_outlier,
        super_eff=super_eff,
        case_rank=case_rank,
        bl_rank=bl_rank,
        n_total=case_total,
        params=params,
        show_detail_tables=True,
    )






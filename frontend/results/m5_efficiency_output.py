"""
M5 Efficiency Incentive - Output Display

Three visual blocks:
1. Efficiency Distribution -- Two Plotly histograms side-by-side:
   (a) Efficiency scores with truncation zone overlay and company markers.
   (b) Annual efficiency requirements distribution with company marker.
2. Company Efficiency Summary -- KPI hero row (4 metrics: score, rank,
   truncated potential, annual requirement) + super-efficiency badge +
   outlier warning.
3. Cost Impact -- Horizontal waterfall showing how efficiency deductions
   affect the cost base (OPEX/CAPEX before → deductions → controllable after).

Variable-IDs:
- 5.2.1-5.3.1: Efficiency calculation parameters
- 50.3.1: Efficiency score
- 50.3.2: Super-efficiency score
- 50.3.3: Efficiency potential (raw)
- 50.3.4: Applied efficiency potential (truncated)
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from typing import Dict, Any, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from pipeline.core import PipelineResult

from config.column_names import (
    COL_DEA_EFFICIENCY, COL_DEA_SUPER_EFF, COL_REID,
    COL_OPEX_BEFORE, COL_CAPEX_BEFORE,
    COL_OPEX_EFF_DEDUCTION, COL_CAPEX_EFF_DEDUCTION,
    COL_CONTROLLABLE_PERIOD,
    COL_OPEX_SHARE, COL_CAPEX_SHARE, COL_METHOD_USED,
)
from config.colors import COLORS, get_plotly_template
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
        show_detail_tables=False,
    )

    st.divider()

    # --- Block 3: Cost impact waterfall ---
    _render_cost_impact_waterfall(case, baseline)


# ============================================================================
# COST IMPACT WATERFALL
# ============================================================================

def _render_cost_impact_waterfall(
    case: "PipelineResult",
    baseline: "PipelineResult",
) -> None:
    """Horizontal waterfall: cost bases → efficiency deductions → controllable after."""

    case_rf = case.post_dea.user_revenue_frame
    bl_rf = baseline.post_dea.user_revenue_frame

    # Extract values (tkr)
    opex_before = float(case_rf.get(COL_OPEX_BEFORE, 0))
    capex_before = float(case_rf.get(COL_CAPEX_BEFORE, 0))
    opex_ded = float(case_rf.get(COL_OPEX_EFF_DEDUCTION, 0))
    capex_ded = float(case_rf.get(COL_CAPEX_EFF_DEDUCTION, 0))
    ctrl_after = float(case_rf.get(COL_CONTROLLABLE_PERIOD, 0))
    opex_share = float(case_rf.get(COL_OPEX_SHARE, 1.0))
    capex_share = float(case_rf.get(COL_CAPEX_SHARE, 0.0))

    # Baseline values for hover
    bl_opex_before = float(bl_rf.get(COL_OPEX_BEFORE, 0))
    bl_capex_before = float(bl_rf.get(COL_CAPEX_BEFORE, 0))
    bl_opex_ded = float(bl_rf.get(COL_OPEX_EFF_DEDUCTION, 0))
    bl_capex_ded = float(bl_rf.get(COL_CAPEX_EFF_DEDUCTION, 0))
    bl_ctrl_after = float(bl_rf.get(COL_CONTROLLABLE_PERIOD, 0))

    st.subheader("Cost impact")

    # Waterfall components: (label, case_val_tkr, baseline_val_tkr, negate, measure)
    components = [
        (f"OPEX before ({opex_share:.0%})",   opex_before,  bl_opex_before,  False, "relative"),
        (f"CAPEX before ({capex_share:.0%})",  capex_before, bl_capex_before, False, "relative"),
        ("OPEX efficiency deduction",          opex_ded,     bl_opex_ded,     True,  "relative"),
        ("CAPEX efficiency deduction",         capex_ded,    bl_capex_ded,    True,  "relative"),
        ("Controllable after",                 ctrl_after,   bl_ctrl_after,   False, "total"),
    ]

    labels = []
    values = []
    measures = []
    hovers = []

    for label, case_val, bl_val, negate, measure in components:
        val_msek = case_val / 1e3
        bl_msek = bl_val / 1e3
        if negate:
            val_msek = -val_msek
            bl_msek = -bl_msek
        delta_msek = val_msek - bl_msek

        labels.append(label)
        values.append(val_msek)
        measures.append(measure)

        if measure == "total":
            delta_str = f"<br>Baseline: {bl_msek:,.1f} MSEK" if abs(delta_msek) > 0.05 else ""
            hovers.append(f"<b>{label}</b><br>{val_msek:,.1f} MSEK{delta_str}")
        else:
            delta_str = f"<br>Delta: {delta_msek:+,.1f} MSEK" if abs(delta_msek) > 0.05 else ""
            hovers.append(f"<b>{label}</b><br>{val_msek:+,.1f} MSEK{delta_str}")

    tmpl = get_plotly_template()

    fig = go.Figure(go.Waterfall(
        orientation="h",
        y=labels,
        x=values,
        measure=measures,
        textposition="outside",
        text=[
            f"{v:+,.1f}" if m != "total" and abs(v) > 0.05
            else (f"{v:,.1f}" if m == "total" else "±0")
            for v, m in zip(values, measures)
        ],
        textfont=dict(size=11, family="Inter, sans-serif"),
        connector=dict(line=dict(color=COLORS["bg_muted"], width=1, dash="dot")),
        increasing=dict(marker=dict(color=COLORS["success"])),
        decreasing=dict(marker=dict(color=COLORS["error"])),
        totals=dict(marker=dict(color=COLORS["primary"])),
        hovertext=hovers,
        hovertemplate="%{hovertext}<extra></extra>",
    ))

    # Zero-value markers
    running = 0.0
    zero_y, zero_x = [], []
    for label, val, measure in zip(labels, values, measures):
        if measure == "relative":
            if abs(val) < 0.05:
                zero_y.append(label)
                zero_x.append(running)
            running += val

    if zero_y:
        fig.add_trace(go.Scatter(
            x=zero_x, y=zero_y,
            mode="markers",
            marker=dict(
                symbol="line-ns", size=16,
                line=dict(width=2, color=COLORS["text_muted"]),
                color=COLORS["text_muted"],
            ),
            showlegend=False, hoverinfo="skip",
        ))

    fig.update_layout(
        font=tmpl.get("font", {}),
        paper_bgcolor=tmpl.get("paper_bgcolor", "rgba(0,0,0,0)"),
        plot_bgcolor=tmpl.get("plot_bgcolor", "rgba(0,0,0,0)"),
        margin=dict(l=10, r=80, t=10, b=40),
        height=max(250, len(labels) * 50),
        xaxis=dict(
            title="MSEK",
            showgrid=False,
            zeroline=True,
            zerolinecolor=COLORS["bg_muted"],
            zerolinewidth=1,
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor=COLORS["bg_muted"],
            tickson="boundaries",
            automargin=True,
            autorange="reversed",
        ),
        showlegend=False,
    )

    st.plotly_chart(fig, key="m5_cost_impact_waterfall", width="stretch", config={"displayModeBar": False})

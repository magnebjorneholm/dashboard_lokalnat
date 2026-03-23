"""
M5 Efficiency Incentive - Output Display

Three visual blocks:
1. Efficiency Distribution -- Two Plotly histograms side-by-side:
   (a) Efficiency scores with truncation zone overlay and company markers.
   (b) Annual efficiency requirements distribution with company marker.
2. Company Efficiency Summary -- KPI hero row (4 metrics: score, rank,
   truncated potential, annual requirement) + super-efficiency badge +
   outlier warning + 50.3 measures table + parameters.
3. Efficiency Cost Impact -- KPI hero row (3 metrics: total deduction,
   method, controllable after) + Plotly waterfall chart showing how
   efficiency deductions affect the cost base (OPEX or OPEX+CAPEX).

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
    COL_DEA_EFFICIENCY, COL_DEA_SUPER_EFF,
    COL_REID,
)
from frontend.results._efficiency_charts import (
    get_params,
    render_efficiency_distributions,
    render_efficiency_summary,
)
from frontend.common.styling import COLORS, get_plotly_template
from visualization.diagram_data import prepare_diagram_data
from pipeline.result_helpers import fmt_msek, fmt_delta_msek


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

    st.divider()

    # --- Block 3: Efficiency cost impact waterfall ---
    _render_efficiency_cost_impact(case, baseline)


# ============================================================================
# BLOCK 3: EFFICIENCY COST IMPACT WATERFALL
# ============================================================================

def _render_efficiency_cost_impact(
    case: "PipelineResult",
    baseline: "PipelineResult",
) -> None:
    """Render efficiency cost impact: KPI hero row + waterfall chart."""
    dd = prepare_diagram_data(case_result=case, baseline_result=baseline)
    method = dd.get('method', 'OPEX')

    # --- Extract values for KPIs (tkr) ---
    opex_eff = dd['opex_effektivisering']['value']
    opex_eff_bl = dd['opex_effektivisering']['baseline']
    capex_eff = dd['capex_effektivisering']['value']
    capex_eff_bl = dd['capex_effektivisering']['baseline']
    total_ded = opex_eff + capex_eff
    total_ded_bl = opex_eff_bl + capex_eff_bl

    ctrl_before = dd['paverkbara']['value']
    ctrl_after = ctrl_before - opex_eff
    ctrl_after_bl = dd['paverkbara']['baseline'] - opex_eff_bl

    # --- KPI hero row ---
    st.markdown("**Efficiency cost impact**")

    col1, col2, col3 = st.columns(3)
    with col1:
        delta_ded = total_ded - total_ded_bl
        st.metric(
            label="Total efficiency deduction",
            value=fmt_msek(total_ded),
            delta=fmt_delta_msek(delta_ded) if abs(delta_ded) > 1 else None,
            delta_color="inverse",
        )
    with col2:
        st.metric(label="Method", value=method)
    with col3:
        delta_after = ctrl_after - ctrl_after_bl
        st.metric(
            label="Controllable after efficiency",
            value=fmt_msek(ctrl_after),
            delta=fmt_delta_msek(delta_after) if abs(delta_after) > 1 else None,
        )

    # --- Build waterfall arrays ---
    if method == 'TOTEX':
        opex_before_msek = ctrl_before / 1e3
        opex_eff_msek = opex_eff / 1e3
        capex_before_msek = (
            dd['avskrivningar']['value'] + dd['avkastning']['value']
        ) / 1e3
        capex_eff_msek = capex_eff / 1e3

        wf_labels = [
            "OPEX Before",
            "OPEX eff. deduction",
            "OPEX After",
            "CAPEX Before",
            "CAPEX eff. deduction",
            "CAPEX After",
        ]
        wf_values = [
            opex_before_msek,
            -opex_eff_msek,
            0,
            capex_before_msek,
            -capex_eff_msek,
            0,
        ]
        wf_measures = [
            "relative", "relative", "total",
            "relative", "relative", "total",
        ]
    else:
        ctrl_before_msek = ctrl_before / 1e3
        eff_ded_msek = opex_eff / 1e3

        wf_labels = [
            "Controllable Before",
            "Efficiency deduction",
            "Controllable After",
        ]
        wf_values = [ctrl_before_msek, -eff_ded_msek, 0]
        wf_measures = ["relative", "relative", "total"]

    # --- Build hover text ---
    wf_hover = []
    for label, val, measure in zip(wf_labels, wf_values, wf_measures):
        if measure == "total":
            wf_hover.append(f"<b>{label}</b>")
        else:
            wf_hover.append(f"<b>{label}</b><br>{val:+,.1f} MSEK")

    # --- Render waterfall ---
    tmpl = get_plotly_template()

    fig = go.Figure(go.Waterfall(
        orientation="h",
        y=wf_labels,
        x=wf_values,
        measure=wf_measures,
        textposition="outside",
        text=[
            f"{v:+,.1f}" if m != "total" and abs(v) > 0.05
            else (f"{v:,.1f}" if m == "total" else "")
            for v, m in zip(wf_values, wf_measures)
        ],
        textfont=dict(size=11, family="Inter, sans-serif"),
        connector=dict(
            line=dict(color=COLORS["bg_muted"], width=1, dash="dot")
        ),
        increasing=dict(marker=dict(color=COLORS["success"])),
        decreasing=dict(marker=dict(color=COLORS["error"])),
        totals=dict(marker=dict(color=COLORS["primary"])),
        hovertext=wf_hover,
        hovertemplate="%{hovertext}<extra></extra>",
    ))

    # Zero-value markers (thin line for ~0 deductions)
    running = 0.0
    zero_y = []
    zero_x = []
    for label, val, measure in zip(wf_labels, wf_values, wf_measures):
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
                symbol="line-ns",
                size=16,
                line=dict(width=2, color=COLORS["text_muted"]),
                color=COLORS["text_muted"],
            ),
            showlegend=False,
            hoverinfo="skip",
        ))

    fig.update_layout(
        font=tmpl.get("font", {}),
        paper_bgcolor=tmpl.get("paper_bgcolor", "rgba(0,0,0,0)"),
        plot_bgcolor=tmpl.get("plot_bgcolor", "rgba(0,0,0,0)"),
        margin=dict(l=10, r=80, t=10, b=40),
        height=max(200, len(wf_labels) * 50),
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

    st.plotly_chart(
        fig, key="m5_eff_waterfall", width='stretch',
        config={"displayModeBar": False},
    )


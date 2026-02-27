"""
M5 Efficiency Incentive - Output Display

Four visual blocks:
1. Efficiency Distribution -- Two Plotly histograms side-by-side:
   (a) Efficiency scores with truncation zone overlay and company markers.
   (b) Annual efficiency requirements distribution with company marker.
2. Company Efficiency Summary -- KPI hero row (4 metrics: score, rank,
   truncated potential, annual requirement) + super-efficiency badge +
   percentile bar + 50.3 measures table + parameters.
3. Frontier Scatter Plot -- 148 companies on TOTEX vs CU plane with
   efficient frontier line and user company highlighted.
4. Cost Impact -- Plotly waterfall showing cost base -> efficiency deduction
   -> net, adapting to OPEX vs TOTEX method, with baseline reference when
   delta exists.  Summary metric above the chart, detail table directly visible.

Variable-IDs:
- 5.2.1-5.3.1: Efficiency calculation parameters
- 50.3.1: Efficiency score
- 50.3.2: Super-efficiency score
- 50.3.3: Efficiency potential (raw)
- 50.3.4: Applied efficiency potential (truncated)
- 50.4.1: OPEX efficiency adjustment
- 50.4.2: CAPEX efficiency adjustment (TOTEX only)
- 50.4.3: OPEX after adjustment
- 50.4.4: CAPEX after adjustment (TOTEX only)
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from typing import Dict, Any, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from pipeline.core import PipelineResult

from frontend.common.styling import COLORS, CHART_COLORS
from config.colors import (
    WATERFALL_COLORS, SCATTER_COLORS, get_plotly_template_safe,
)
from pipeline.result_helpers import fmt_pct as _fmt_pct, fmt_tkr as _fmt_tkr
from config.formatting import format_pp, format_percent, format_number, format_delta
from config.glossary import (
    VID_OPEX_EFF_ADJUSTMENT, VID_CAPEX_EFF_ADJUSTMENT,
    VID_OPEX_AFTER_EFF, VID_CAPEX_AFTER_EFF,
)
from config.column_names import (
    COL_DEA_EFFICIENCY, COL_DEA_SUPER_EFF, COL_EFF_REQ_ANNUAL,
    COL_METHOD_USED, COL_OPEX_BEFORE, COL_OPEX_AFTER, COL_OPEX_EFF_DEDUCTION,
    COL_CAPEX_BEFORE, COL_CAPEX_AFTER, COL_CAPEX_EFF_DEDUCTION,
    COL_CONTROLLABLE_BEFORE, COL_CONTROLLABLE_PERIOD, COL_EFFICIENCY_DEDUCTION,
    COL_OPEX_SHARE, COL_CAPEX_SHARE,
    COL_CAPITAL_COST_2024, COL_CONTROLLABLE_AVG, COL_CU, COL_COMPANY_NAME,
    COL_IS_OUTLIER, COL_REID,
)
from frontend.results._efficiency_charts import (
    get_params,
    render_efficiency_distributions,
    render_efficiency_summary,
)

# Waterfall colors (from design system)
WF_BASE = WATERFALL_COLORS["base"]
WF_DEDUCTION = WATERFALL_COLORS["deduction"]
WF_TOTAL = WATERFALL_COLORS["total"]

# Scatter plot colors (from design system)
SC_NORMAL = SCATTER_COLORS["normal"]
SC_EFFICIENT = SCATTER_COLORS["efficient"]
SC_OUTLIER = SCATTER_COLORS["outlier"]
SC_USER = SCATTER_COLORS["user"]
SC_FRONTIER = SCATTER_COLORS["frontier"]


# ============================================================================
# HELPERS
# ============================================================================

def _tmpl_safe():
    """Get plotly template dict with xaxis/yaxis removed to avoid conflicts."""
    return get_plotly_template_safe()


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

    case_ir = case.post_dea.user_revenue_frame
    baseline_ir = baseline.post_dea.user_revenue_frame

    # --- Block 1: Distributions (shared) ---
    dea_case = case.dea.dea_results.copy()
    eff_scores = dea_case[COL_DEA_EFFICIENCY].dropna().values

    render_efficiency_distributions(
        eff_scores=eff_scores,
        eff_case=case.extraction.efficiency,
        eff_baseline=baseline.extraction.efficiency,
        effkrav_all_df=case.post_dea.all_eff_reqs,
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

    # --- Block 3: Frontier scatter plot ---
    _render_frontier_scatter(case, baseline, user_reid)

    st.divider()

    # --- Block 4: Cost impact ---
    _render_cost_waterfall(case_ir, baseline_ir, m5_config)


# ============================================================================
# BLOCK 3 -- FRONTIER SCATTER PLOT
# ============================================================================

def _render_frontier_scatter(case, baseline, user_reid):
    """Scatter plot: 148 companies on TOTEX vs CU plane with frontier line."""

    st.markdown("**Frontier Position**")
    st.caption(
        "Each dot represents one of 148 companies plotted by subscriptions (CU) vs "
        "first-year total cost (CAPEX + controllable OPEX). The frontier line connects "
        "efficient companies (efficiency = 1.0), forming the DEA reference envelope."
    )

    # --- Merge pre_dea company data with DEA results ---
    df_companies = case.pre_dea.df_all_companies.copy()
    dea_results = case.dea.dea_results.copy()

    # Ensure we have the needed columns
    if COL_CU not in df_companies.columns or COL_CAPITAL_COST_2024 not in df_companies.columns:
        st.info("Insufficient data for frontier scatter plot.")
        return

    # Compute TOTEX (first year) = capital_cost_2024 + controllable_cost_average
    if COL_CONTROLLABLE_AVG in df_companies.columns:
        df_companies["_totex_first"] = (
            df_companies[COL_CAPITAL_COST_2024].fillna(0)
            + df_companies[COL_CONTROLLABLE_AVG].fillna(0)
        )
    else:
        df_companies["_totex_first"] = df_companies[COL_CAPITAL_COST_2024].fillna(0)

    # Merge with DEA results to get efficiency and outlier status
    dea_cols = [COL_REID, COL_DEA_EFFICIENCY]
    if COL_IS_OUTLIER in dea_results.columns:
        dea_cols.append(COL_IS_OUTLIER)
    if COL_DEA_SUPER_EFF in dea_results.columns:
        dea_cols.append(COL_DEA_SUPER_EFF)

    df = df_companies.merge(dea_results[dea_cols], on=COL_REID, how="left")

    # Company name for hover
    has_name = COL_COMPANY_NAME in df.columns

    # --- Classify companies ---
    df["_is_user"] = df[COL_REID] == user_reid
    df["_is_efficient"] = df[COL_DEA_EFFICIENCY].fillna(0) >= 1.0
    df["_is_outlier"] = df[COL_IS_OUTLIER].fillna(False) if COL_IS_OUTLIER in df.columns else False

    # --- Build figure ---
    layout_kwargs, template = _tmpl_safe()
    fig = go.Figure()

    # Filter groups
    df_normal = df[~df["_is_user"] & ~df["_is_efficient"] & ~df["_is_outlier"]]
    df_outlier = df[~df["_is_user"] & df["_is_outlier"] & ~df["_is_efficient"]]
    df_efficient = df[~df["_is_user"] & df["_is_efficient"]]
    df_user = df[df["_is_user"]]

    def _hover_text(row):
        parts = []
        if has_name and pd.notna(row.get(COL_COMPANY_NAME)):
            parts.append(f"{row[COL_COMPANY_NAME]}")
        parts.append(f"CU: {row[COL_CU]:,.0f}")
        parts.append(f"TOTEX: {row['_totex_first']:,.0f} tkr")
        if pd.notna(row.get(COL_DEA_EFFICIENCY)):
            parts.append(f"Efficiency: {row[COL_DEA_EFFICIENCY]:.3f}")
        return "<br>".join(parts)

    # Normal companies
    if not df_normal.empty:
        fig.add_trace(go.Scatter(
            x=df_normal[COL_CU],
            y=df_normal["_totex_first"],
            mode="markers",
            marker=dict(color=SC_NORMAL, size=6, opacity=0.6),
            hovertext=df_normal.apply(_hover_text, axis=1),
            hoverinfo="text",
            name="Other companies",
            showlegend=True,
        ))

    # Outliers
    if not df_outlier.empty:
        fig.add_trace(go.Scatter(
            x=df_outlier[COL_CU],
            y=df_outlier["_totex_first"],
            mode="markers",
            marker=dict(color=SC_OUTLIER, size=7, opacity=0.8, symbol="diamond"),
            hovertext=df_outlier.apply(_hover_text, axis=1),
            hoverinfo="text",
            name="Outliers",
            showlegend=True,
        ))

    # Efficient companies
    if not df_efficient.empty:
        fig.add_trace(go.Scatter(
            x=df_efficient[COL_CU],
            y=df_efficient["_totex_first"],
            mode="markers",
            marker=dict(color=SC_EFFICIENT, size=8, opacity=0.85, symbol="circle"),
            hovertext=df_efficient.apply(_hover_text, axis=1),
            hoverinfo="text",
            name="Efficient (score = 1.0)",
            showlegend=True,
        ))

    # Frontier line: connect efficient DMUs sorted by CU
    frontier_df = df[df["_is_efficient"] & ~df["_is_user"]].sort_values(COL_CU)
    # Include user if efficient
    if not df_user.empty and df_user["_is_efficient"].iloc[0]:
        frontier_df = pd.concat([frontier_df, df_user]).sort_values(COL_CU)

    if len(frontier_df) >= 2:
        # Add origin point (0,0) for visual completeness
        frontier_x = [0] + frontier_df[COL_CU].tolist()
        frontier_y = [0] + frontier_df["_totex_first"].tolist()
        fig.add_trace(go.Scatter(
            x=frontier_x,
            y=frontier_y,
            mode="lines",
            line=dict(color=SC_FRONTIER, width=2, dash="dot"),
            name="Frontier",
            showlegend=True,
            hoverinfo="skip",
        ))

    # User company (large, on top)
    if not df_user.empty:
        user_row = df_user.iloc[0]
        fig.add_trace(go.Scatter(
            x=[user_row[COL_CU]],
            y=[user_row["_totex_first"]],
            mode="markers+text",
            marker=dict(color=SC_USER, size=14, line=dict(color="white", width=2)),
            text=["Your company"],
            textposition="top center",
            textfont=dict(size=11, color=SC_USER, family="Inter, sans-serif"),
            hovertext=[_hover_text(user_row)],
            hoverinfo="text",
            name="Your company",
            showlegend=True,
        ))

    fig.update_layout(
        **layout_kwargs,
        template=template,
        height=450,
        margin=dict(t=40, b=60, l=60, r=20),
        xaxis_title="Subscriptions (CU)",
        yaxis_title="First-year total cost (tkr)",
        xaxis=dict(
            showgrid=True,
            gridcolor=COLORS["bg_subtle"],
            linecolor=COLORS["bg_muted"],
            rangemode="tozero",
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor=COLORS["bg_subtle"],
            linecolor=COLORS["bg_muted"],
            rangemode="tozero",
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.18,
            xanchor="center",
            x=0.5,
            font=dict(size=11),
        ),
    )

    st.plotly_chart(fig, width='stretch', key="m5_frontier_scatter",
                    config={"displayModeBar": False})


# ============================================================================
# BLOCK 4 -- COST IMPACT (WATERFALL)
# ============================================================================

def _render_cost_waterfall(case_ir, baseline_ir, m5_config):
    """Waterfall chart showing cost base -> efficiency deduction -> net."""

    st.markdown("**50.4 Efficiency-Adjusted Costs**")

    method_used = case_ir.get(COL_METHOD_USED, "OPEX")

    # --- Extract values (with legacy fallback) ---
    opex_fore = case_ir.get(COL_OPEX_BEFORE)
    opex_eff = case_ir.get(COL_OPEX_EFF_DEDUCTION)
    opex_efter = case_ir.get(COL_OPEX_AFTER)

    capex_fore = case_ir.get(COL_CAPEX_BEFORE)
    capex_eff = case_ir.get(COL_CAPEX_EFF_DEDUCTION)
    capex_efter = case_ir.get(COL_CAPEX_AFTER)

    # Legacy fallback
    if opex_fore is None:
        opex_fore = case_ir.get(COL_CONTROLLABLE_BEFORE, 0)
        opex_efter = case_ir.get(COL_CONTROLLABLE_PERIOD, 0)
        opex_eff = case_ir.get(COL_EFFICIENCY_DEDUCTION, 0)
        capex_eff = 0
        capex_fore = 0
        capex_efter = 0

    # Baseline values
    bl_opex_fore = baseline_ir.get(COL_OPEX_BEFORE, baseline_ir.get(COL_CONTROLLABLE_BEFORE, 0))
    bl_opex_eff = baseline_ir.get(COL_OPEX_EFF_DEDUCTION, baseline_ir.get(COL_EFFICIENCY_DEDUCTION, 0))
    bl_opex_efter = baseline_ir.get(COL_OPEX_AFTER, baseline_ir.get(COL_CONTROLLABLE_PERIOD, 0))
    bl_capex_fore = baseline_ir.get(COL_CAPEX_BEFORE, 0)
    bl_capex_eff = baseline_ir.get(COL_CAPEX_EFF_DEDUCTION, 0)
    bl_capex_efter = baseline_ir.get(COL_CAPEX_AFTER, 0)

    # Allocation percentages (TOTEX)
    opex_andel = case_ir.get(COL_OPEX_SHARE)
    capex_andel = case_ir.get(COL_CAPEX_SHARE)

    if method_used == "TOTEX":
        if opex_andel is not None and capex_andel is not None:
            st.caption(f"TOTEX method -- allocation: OPEX {format_percent(opex_andel, 1)} / CAPEX {format_percent(capex_andel, 1)}")
        else:
            st.caption("Cost base: TOTEX")
    else:
        st.caption("Cost base: OPEX")

    # --- Summary metric (moved above waterfall for prominence) ---
    total_eff_case = (opex_eff or 0) + (capex_eff or 0)
    total_eff_baseline = (bl_opex_eff or 0) + (bl_capex_eff or 0)

    if total_eff_case != 0 or total_eff_baseline != 0:
        delta = total_eff_case - total_eff_baseline
        st.metric(
            "Total efficiency adjustment (period)",
            f"-{format_number(total_eff_case)} tkr",
            delta=format_delta(-delta) if abs(delta) > 0.5 else None,
            delta_color="inverse",
        )

    # --- Build waterfall ---
    layout_kwargs, template = _tmpl_safe()

    # Check if there is a meaningful delta vs baseline
    bl_net = (bl_opex_efter or 0) + (bl_capex_efter or 0)
    case_net = (opex_efter or 0) + (capex_efter or 0)
    has_delta = abs(case_net - bl_net) > 0.5

    if method_used == "TOTEX" and capex_fore and capex_fore > 0:
        labels = ["OPEX base", "OPEX eff. adj.", "CAPEX base", "CAPEX eff. adj.", "Net cost"]
        measures = ["absolute", "relative", "relative", "relative", "total"]
        values = [
            opex_fore or 0,
            -(opex_eff or 0),
            capex_fore or 0,
            -(capex_eff or 0),
            0,
        ]
        text_vals = [
            _fmt_tkr(opex_fore),
            _fmt_tkr(-(opex_eff or 0), show_sign=True),
            _fmt_tkr(capex_fore),
            _fmt_tkr(-(capex_eff or 0), show_sign=True),
            _fmt_tkr(case_net),
        ]
    else:
        labels = ["OPEX base", "Efficiency adj.", "Net OPEX"]
        measures = ["absolute", "relative", "total"]
        values = [opex_fore or 0, -(opex_eff or 0), 0]
        text_vals = [
            _fmt_tkr(opex_fore),
            _fmt_tkr(-(opex_eff or 0), show_sign=True),
            _fmt_tkr(opex_efter),
        ]

    fig = go.Figure(go.Waterfall(
        orientation="v",
        measure=measures,
        x=labels,
        y=values,
        text=text_vals,
        textposition="outside",
        textfont=dict(size=11),
        connector=dict(line=dict(color=COLORS["bg_muted"], width=1, dash="dot")),
        increasing=dict(marker_color=WF_BASE),
        decreasing=dict(marker_color=WF_DEDUCTION),
        totals=dict(marker_color=WF_TOTAL),
    ))

    # Baseline reference line (only when case differs from baseline)
    if has_delta:
        fig.add_hline(
            y=bl_net,
            line_dash="dash",
            line_color=COLORS["text_primary"],
            line_width=1.5,
            annotation_text=f"Baseline net: {_fmt_tkr(bl_net)} tkr",
            annotation_position="top right",
            annotation_font_size=11,
            annotation_font_color=COLORS["text_primary"],
            annotation_bgcolor="rgba(255,255,255,0.9)",
            annotation_borderpad=3,
        )

    fig.update_layout(
        **layout_kwargs,
        template=template,
        height=380,
        margin=dict(t=40),
        showlegend=False,
        yaxis_title="tkr",
        xaxis=dict(showgrid=False, linecolor=COLORS["bg_muted"]),
        yaxis=dict(gridcolor=COLORS["bg_subtle"], linecolor=COLORS["bg_muted"]),
    )

    st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})

    # --- Comparison table below waterfall (directly visible, not in expander) ---
    rows = []

    _add_cost_row(rows, "-", "OPEX before efficiency adj.", opex_fore, bl_opex_fore)
    _add_cost_row(rows, VID_OPEX_EFF_ADJUSTMENT, "OPEX efficiency adjustment", -(opex_eff or 0), -(bl_opex_eff or 0), negate_delta=True)
    _add_cost_row(rows, VID_OPEX_AFTER_EFF, "OPEX after efficiency adj.", opex_efter, bl_opex_efter)

    if method_used == "TOTEX":
        rows.append({"ID": "", "Component": "", "Case (tkr)": "", "Baseline (tkr)": "", "Delta (tkr)": ""})
        _add_cost_row(rows, "-", "CAPEX before efficiency adj.", capex_fore, bl_capex_fore)
        _add_cost_row(rows, VID_CAPEX_EFF_ADJUSTMENT, "CAPEX efficiency adjustment", -(capex_eff or 0), -(bl_capex_eff or 0), negate_delta=True)
        _add_cost_row(rows, VID_CAPEX_AFTER_EFF, "CAPEX after efficiency adj.", capex_efter, bl_capex_efter)

    st.dataframe(
        pd.DataFrame(rows),
        hide_index=True,
        width="stretch",
        column_config={
            "ID": st.column_config.TextColumn("ID", width="small"),
            "Component": st.column_config.TextColumn("Component", width="medium"),
            "Case (tkr)": st.column_config.TextColumn("Case (tkr)", width="small"),
            "Baseline (tkr)": st.column_config.TextColumn("Baseline (tkr)", width="small"),
            "Delta (tkr)": st.column_config.TextColumn("Delta (tkr)", width="small"),
        },
    )


def _add_cost_row(rows, var_id, label, case_val, bl_val, negate_delta=False):
    """Append a row to the cost comparison table."""
    case_val = case_val or 0
    bl_val = bl_val or 0
    delta = case_val - bl_val
    if negate_delta:
        delta = -delta
    rows.append({
        "ID": var_id,
        "Component": label,
        "Case (tkr)": _fmt_tkr(case_val, show_sign=(case_val < 0)),
        "Baseline (tkr)": _fmt_tkr(bl_val, show_sign=(bl_val < 0)),
        "Delta (tkr)": _fmt_tkr(delta, show_sign=True) if abs(delta) > 0.5 else "-",
    })

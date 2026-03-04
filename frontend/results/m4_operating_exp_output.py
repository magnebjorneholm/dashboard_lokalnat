"""
M4 Operating Expenditures - Output Display

Layout:
  1. KPI Hero Row (4 metrics: Total OPEX in Revenue Frame, Controllable, Non-controllable, Flexibility)
  2. OPEX Composition Waterfall Chart (Plotly horizontal waterfall)
  3. Controllable Category Breakdown (horizontal bar + detail table from grunddata)
  4. Non-Controllable Category Breakdown (horizontal bar + detail table from grunddata)

Variable-IDs:
- 40.1.1: Controllable costs (påverkbara)
- 40.1.2: Flexibility services
- 40.2.1: Non-controllable costs (opåverkbara)
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from typing import Dict, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from pipeline.core import PipelineResult

from config.column_names import (
    COL_CONTROLLABLE_PERIOD, COL_CONTROLLABLE_BEFORE,
    COL_OPEX_BEFORE, COL_OPEX_EFF_DEDUCTION,
    COL_CAPEX_BEFORE, COL_CAPEX_EFF_DEDUCTION,
    COL_OPEX_SHARE, COL_CAPEX_SHARE,
    COL_EFFICIENCY_DEDUCTION, COL_METHOD_USED,
    COL_NON_CONTROLLABLE, COL_FLEXIBILITY,
    COL_INTERRUPTION, COL_STATE_DEDUCTION,
    COL_CONTROLLABLE_IN_RF,
)
from config.glossary import (
    VID_OPEX_ADJUSTABLE, VID_FLEX_SERVICE, VID_NON_ADJUSTABLE,
)
from frontend.common.styling import COLORS, CHART_COLORS
from config.colors import WATERFALL_COLORS, get_plotly_template_safe
from pipeline.result_helpers import (
    fmt_tkr as _fmt_tkr, fmt_msek as _fmt_msek,
    fmt_delta_msek as _fmt_delta_msek,
)


# ============================================================================
# CONSTANTS
# ============================================================================

# Waterfall colors (from design system)
WF_BASE = WATERFALL_COLORS["base"]
WF_DEDUCTION = WATERFALL_COLORS["deduction"]
WF_TOTAL = WATERFALL_COLORS["total"]

# Category chart colors
CLR_CONTROLLABLE = CHART_COLORS[0]   # Primary Blue
CLR_NONCONTROLLABLE = CHART_COLORS[1]  # Teal

INDEX_COLS = {
    2018: "index_2018", 2019: "index_2019",
    2020: "index_2020", 2021: "index_2021",
}
YEARS_GRUNDDATA = [2018, 2019, 2020, 2021]

# Regex for category code prefixes (RR7320, KENT, RR71, etc.)
import re
_CODE_PREFIX_RE = re.compile(r'^[A-Z][A-Za-z]*\d*$')


# ============================================================================
# HELPERS
# ============================================================================

def _format_category_name(raw: str) -> str:
    """Format raw category name for display.

    'RR7320_power_purchase' → 'Power Purchase (RR7320)'
    'KENT_deductions' → 'Deductions (KENT)'
    'neo_adjustments_per_year' → 'Neo Adjustments Per Year'
    'capital_cost_outside_base' → 'Capital Cost Outside Base'
    """
    parts = raw.split("_", 1)
    if len(parts) == 2 and _CODE_PREFIX_RE.match(parts[0]):
        code = parts[0]
        desc = parts[1].replace("_", " ").title()
        return f"{desc} ({code})"
    return raw.replace("_", " ").title()


def _safe_ir(ir: pd.Series, key: str, default: float = 0.0) -> float:
    """Safely extract a value from revenue frame Series."""
    val = ir.get(key, default)
    return float(val) if pd.notna(val) else default


def _get_controllable_categories(
    detail: pd.DataFrame,
    meta: pd.DataFrame,
    user_reid: str,
) -> Optional[pd.DataFrame]:
    """Aggregate controllable grunddata into per-category 2022-level costs.

    Returns DataFrame with columns: category, amount, share.
    """
    if detail is None or detail.empty or meta is None or meta.empty:
        return None

    user_detail = detail[detail["REId"] == user_reid]
    if user_detail.empty:
        return None

    user_meta = meta[meta["REId"] == user_reid]
    if user_meta.empty:
        return None
    meta_row = user_meta.iloc[0]

    # Exclude KENT_deductions from visual breakdown (internal offset, not a cost category)
    user_detail = user_detail[user_detail["category"] != "KENT_deductions"]

    # Sum per category per year
    yearly = user_detail.groupby(["category", "year"])["amount_nominal"].sum().reset_index()
    pivoted = yearly.pivot(index="category", columns="year", values="amount_nominal").reset_index()

    # Apply index factors and average to 2022-level
    for yr in YEARS_GRUNDDATA:
        idx_col = INDEX_COLS[yr]
        idx_val = meta_row.get(idx_col, 1.0)
        if yr in pivoted.columns:
            pivoted[f"adj_{yr}"] = pivoted[yr] * (idx_val if pd.notna(idx_val) else 1.0)
        else:
            pivoted[f"adj_{yr}"] = 0.0

    adj_cols = [f"adj_{yr}" for yr in YEARS_GRUNDDATA]
    pivoted["amount"] = pivoted[adj_cols].mean(axis=1)

    # Share based on gross (positive amounts only) so positive items sum to ~100%
    gross_total = pivoted.loc[pivoted["amount"] > 0, "amount"].sum()
    pivoted["share"] = (pivoted["amount"] / gross_total * 100) if gross_total > 0 else 0.0

    # Format category names for display
    pivoted["category"] = pivoted["category"].apply(_format_category_name)

    result = pivoted[["category", "amount", "share"]].copy()
    result = result.sort_values("amount", ascending=False).reset_index(drop=True)
    return result


def _get_noncontrollable_categories(
    detail: pd.DataFrame,
    user_reid: str,
) -> Optional[pd.DataFrame]:
    """Aggregate non-controllable grunddata per KENT category.

    Returns DataFrame with columns: kent_category, period_total, share.
    """
    if detail is None or detail.empty:
        return None

    user_detail = detail[detail["REId"] == user_reid]
    if user_detail.empty:
        return None

    # Sum per kent_category across all years (2024-2027)
    cat_totals = user_detail.groupby("kent_category")["amount"].sum().reset_index()
    cat_totals.columns = ["kent_category", "period_total"]

    # Negate (stored as negative costs → display as positive)
    cat_totals["period_total"] = -cat_totals["period_total"]

    # Share based on gross (positive amounts only)
    gross_total = cat_totals.loc[cat_totals["period_total"] > 0, "period_total"].sum()
    cat_totals["share"] = (cat_totals["period_total"] / gross_total * 100) if gross_total > 0 else 0.0

    # Format category names for display
    cat_totals["kent_category"] = cat_totals["kent_category"].apply(_format_category_name)

    cat_totals = cat_totals.sort_values("period_total", ascending=False).reset_index(drop=True)
    return cat_totals


def _tmpl_safe():
    """Get plotly template dict with xaxis/yaxis removed to avoid conflicts."""
    return get_plotly_template_safe()


# ============================================================================
# MAIN RENDER
# ============================================================================

def render(
    case: "PipelineResult",
    baseline: "PipelineResult",
    ui_config: Dict[str, Any],
) -> None:
    """Render M4 operating expenditures outputs."""

    case_ir = case.post_dea.user_revenue_frame
    baseline_ir = baseline.post_dea.user_revenue_frame
    user_reid = case.post_dea.user_reid

    # --- Section 1: KPI Hero ---
    _render_kpi_hero(case_ir, baseline_ir)

    st.divider()

    # --- Section 2: OPEX Waterfall ---
    _render_opex_waterfall(case_ir, baseline_ir)

    st.divider()

    # --- Section 3: Controllable Category Breakdown ---
    ctrl_detail = getattr(baseline.baseline, "controllable_detail", None)
    ctrl_meta = getattr(baseline.baseline, "controllable_meta", None)
    _render_controllable_categories(ctrl_detail, ctrl_meta, user_reid)

    st.divider()

    # --- Section 4: Non-Controllable Category Breakdown ---
    nonctrl_detail = getattr(baseline.baseline, "non_controllable_detail", None)
    _render_noncontrollable_categories(nonctrl_detail, user_reid)

    # (Sections 5-6 removed — info already shown in KPI hero and waterfall above)


# ============================================================================
# SECTION 1 -- KPI HERO ROW
# ============================================================================

def _render_kpi_hero(case_ir: pd.Series, baseline_ir: pd.Series) -> None:
    """4 key metrics: Total OPEX in Revenue Frame, Controllable, Non-controllable, Flexibility."""

    st.markdown("#### 40.1-40.2 Operating Expenditures")

    # Total OPEX in Revenue Frame = controllable_in_rf + non_controllable + flexibility + interruption - state_deduction
    c_ctrl = _safe_ir(case_ir, COL_CONTROLLABLE_IN_RF,
                      _safe_ir(case_ir, COL_CONTROLLABLE_PERIOD))
    c_nonctrl = _safe_ir(case_ir, COL_NON_CONTROLLABLE)
    c_flex = _safe_ir(case_ir, COL_FLEXIBILITY)
    c_inter = _safe_ir(case_ir, COL_INTERRUPTION)
    c_state = _safe_ir(case_ir, COL_STATE_DEDUCTION)
    c_total = c_ctrl + c_nonctrl + c_flex + c_inter - c_state

    b_ctrl = _safe_ir(baseline_ir, COL_CONTROLLABLE_IN_RF,
                      _safe_ir(baseline_ir, COL_CONTROLLABLE_PERIOD))
    b_nonctrl = _safe_ir(baseline_ir, COL_NON_CONTROLLABLE)
    b_flex = _safe_ir(baseline_ir, COL_FLEXIBILITY)
    b_inter = _safe_ir(baseline_ir, COL_INTERRUPTION)
    b_state = _safe_ir(baseline_ir, COL_STATE_DEDUCTION)
    b_total = b_ctrl + b_nonctrl + b_flex + b_inter - b_state

    # Controllable before efficiency
    c_opex_before = _safe_ir(case_ir, COL_OPEX_BEFORE,
                             _safe_ir(case_ir, COL_CONTROLLABLE_BEFORE))
    b_opex_before = _safe_ir(baseline_ir, COL_OPEX_BEFORE,
                             _safe_ir(baseline_ir, COL_CONTROLLABLE_BEFORE))

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Total OPEX in Revenue Frame",
            _fmt_msek(c_total),
            delta=_fmt_delta_msek(c_total - b_total),
        )
    with col2:
        st.metric(
            f"{VID_OPEX_ADJUSTABLE} Controllable OPEX",
            _fmt_msek(c_opex_before),
            delta=_fmt_delta_msek(c_opex_before - b_opex_before),
        )
    with col3:
        st.metric(
            f"{VID_NON_ADJUSTABLE} Non-controllable OPEX",
            _fmt_msek(c_nonctrl),
            delta=_fmt_delta_msek(c_nonctrl - b_nonctrl),
        )
    with col4:
        st.metric(
            f"{VID_FLEX_SERVICE} Flexibility",
            _fmt_msek(c_flex),
            delta=_fmt_delta_msek(c_flex - b_flex),
        )

    method = case_ir.get(COL_METHOD_USED, "OPEX")
    st.caption(
        f"Period total 2024-2027. Values in MSEK. "
        f"Controllable shown before efficiency deduction. Method: {method}."
    )


# ============================================================================
# SECTION 2 -- OPEX COMPOSITION WATERFALL
# ============================================================================

def _render_opex_waterfall(case_ir: pd.Series, baseline_ir: pd.Series) -> None:
    """Horizontal waterfall: controllable → eff deduction → non-ctrl → flex → interrupt → state → total."""

    st.markdown("**OPEX Composition**")

    method = case_ir.get(COL_METHOD_USED, "OPEX")

    # Extract case values (tkr)
    opex_before = _safe_ir(case_ir, COL_OPEX_BEFORE,
                           _safe_ir(case_ir, COL_CONTROLLABLE_BEFORE))
    opex_eff = _safe_ir(case_ir, COL_OPEX_EFF_DEDUCTION,
                        _safe_ir(case_ir, COL_EFFICIENCY_DEDUCTION))
    capex_before = _safe_ir(case_ir, COL_CAPEX_BEFORE)
    capex_eff = _safe_ir(case_ir, COL_CAPEX_EFF_DEDUCTION)
    nonctrl = _safe_ir(case_ir, COL_NON_CONTROLLABLE)
    flex = _safe_ir(case_ir, COL_FLEXIBILITY)
    interrupt = _safe_ir(case_ir, COL_INTERRUPTION)
    state_ded = _safe_ir(case_ir, COL_STATE_DEDUCTION)

    # Build waterfall steps (values in MSEK)
    if method == "TOTEX" and capex_before > 0:
        labels = [
            "OPEX base", "OPEX eff. adj.",
            "CAPEX base", "CAPEX eff. adj.",
            "Non-controllable OPEX", "Flexibility",
            "Interruption", "State deduction",
            "Total OPEX in Revenue Frame",
        ]
        values_tkr = [
            opex_before, -opex_eff,
            capex_before, -capex_eff,
            nonctrl, flex,
            interrupt, -state_ded,
            0,
        ]
        measures = [
            "absolute", "relative",
            "relative", "relative",
            "relative", "relative",
            "relative", "relative",
            "total",
        ]
        opex_share = _safe_ir(case_ir, COL_OPEX_SHARE)
        capex_share = _safe_ir(case_ir, COL_CAPEX_SHARE)
        if opex_share and capex_share:
            st.caption(
                f"TOTEX method -- allocation: OPEX {opex_share*100:.1f}% / "
                f"CAPEX {capex_share*100:.1f}%"
            )
    else:
        labels = [
            "Controllable OPEX (before eff.)", "Efficiency deduction",
            "Non-controllable OPEX", "Flexibility",
            "Interruption", "State deduction",
            "Total OPEX in Revenue Frame",
        ]
        values_tkr = [
            opex_before, -opex_eff,
            nonctrl, flex,
            interrupt, -state_ded,
            0,
        ]
        measures = [
            "absolute", "relative",
            "relative", "relative",
            "relative", "relative",
            "total",
        ]

    values_msek = [v / 1e3 for v in values_tkr]

    # Custom hover text
    hover = []
    for lbl, val, msr in zip(labels, values_msek, measures):
        if msr in ("total", "absolute"):
            hover.append(f"<b>{lbl}</b><br>{val:,.1f} MSEK")
        else:
            hover.append(f"<b>{lbl}</b><br>{val:+,.1f} MSEK")

    # Baseline total for reference line
    b_ctrl_in_rf = _safe_ir(baseline_ir, COL_CONTROLLABLE_IN_RF,
                            _safe_ir(baseline_ir, COL_CONTROLLABLE_PERIOD))
    b_total = (
        b_ctrl_in_rf
        + _safe_ir(baseline_ir, COL_NON_CONTROLLABLE)
        + _safe_ir(baseline_ir, COL_FLEXIBILITY)
        + _safe_ir(baseline_ir, COL_INTERRUPTION)
        - _safe_ir(baseline_ir, COL_STATE_DEDUCTION)
    )
    c_ctrl_in_rf = _safe_ir(case_ir, COL_CONTROLLABLE_IN_RF,
                            _safe_ir(case_ir, COL_CONTROLLABLE_PERIOD))
    c_total = (
        c_ctrl_in_rf
        + _safe_ir(case_ir, COL_NON_CONTROLLABLE)
        + _safe_ir(case_ir, COL_FLEXIBILITY)
        + _safe_ir(case_ir, COL_INTERRUPTION)
        - _safe_ir(case_ir, COL_STATE_DEDUCTION)
    )
    has_delta = abs(c_total - b_total) > 0.5

    layout_kwargs, template = _tmpl_safe()

    fig = go.Figure(go.Waterfall(
        orientation="h",
        y=labels,
        x=values_msek,
        measure=measures,
        textposition="outside",
        text=[
            f"{v:+,.1f}" if m != "total" and abs(v) > 0.05
            else (f"{v:,.1f}" if m == "total" else "")
            for v, m in zip(values_msek, measures)
        ],
        textfont=dict(size=11, family="Inter, sans-serif"),
        connector=dict(
            line=dict(color=COLORS["bg_muted"], width=1, dash="dot")
        ),
        increasing=dict(marker=dict(color=COLORS["success"])),
        decreasing=dict(marker=dict(color=COLORS["error"])),
        totals=dict(marker=dict(color=COLORS["primary"])),
        hovertext=hover,
        hovertemplate="%{hovertext}<extra></extra>",
    ))

    if has_delta:
        fig.add_vline(
            x=b_total / 1e3,
            line_dash="dash",
            line_color=COLORS["text_muted"],
            line_width=1.5,
            annotation_text=f"Baseline: {b_total / 1e3:,.1f} MSEK",
            annotation_position="top right",
            annotation_font_size=10,
            annotation_font_color=COLORS["text_muted"],
            annotation_bgcolor="rgba(255,255,255,0.9)",
            annotation_borderpad=3,
        )

    fig.update_layout(
        **layout_kwargs,
        template=template,
        height=max(350, len(labels) * 42),
        margin=dict(l=10, r=80, t=10, b=40),
        showlegend=False,
        xaxis=dict(
            title="MSEK",
            showgrid=True,
            gridcolor=COLORS["bg_muted"],
            zeroline=True,
            zerolinecolor=COLORS["bg_muted"],
            zerolinewidth=1,
        ),
        yaxis=dict(
            showgrid=False,
            automargin=True,
            autorange="reversed",
        ),
    )

    st.plotly_chart(fig, width='stretch', config={"displayModeBar": False},
                    key="m4_opex_waterfall")


# ============================================================================
# SECTION 3 -- CONTROLLABLE CATEGORY BREAKDOWN
# ============================================================================

def _render_controllable_categories(
    detail: Optional[pd.DataFrame],
    meta: Optional[pd.DataFrame],
    user_reid: str,
) -> None:
    """Horizontal bar chart + table for controllable cost categories from grunddata."""

    st.markdown("**Controllable Operating Expenditures Decomposition**")

    cat_df = _get_controllable_categories(detail, meta, user_reid)
    if cat_df is None or cat_df.empty:
        st.info("Controllable category data not available.")
        return

    st.caption(
        "Baseline cost decomposition by category (2022-level average). "
        "Shows what constitutes the controllable cost base."
    )

    # --- Horizontal bar chart ---
    chart_df = cat_df.sort_values("amount", ascending=True)  # bottom = largest

    layout_kwargs, template = _tmpl_safe()
    fig = go.Figure()

    fig.add_trace(go.Bar(
        y=chart_df["category"],
        x=chart_df["amount"],
        orientation="h",
        marker_color=CLR_CONTROLLABLE,
        hovertemplate="%{y}<br>%{x:,.0f} tkr<extra></extra>",
        showlegend=False,
    ))

    fig.update_layout(
        **layout_kwargs,
        template=template,
        margin=dict(l=10, r=20, t=10, b=30),
        height=max(250, len(cat_df) * 40),
        xaxis=dict(
            title="Annual average (tkr, 2022 level)",
            showgrid=True,
            gridcolor=COLORS["bg_subtle"],
        ),
        yaxis=dict(showgrid=False, automargin=True),
    )

    st.plotly_chart(fig, width='stretch', config={"displayModeBar": False},
                    key="m4_ctrl_categories_chart")

    # --- Detail table ---
    # Use ProgressColumn for share; handle negative values by clamping bar range
    share_min = min(0.0, cat_df["share"].min())
    share_max = max(100.0, cat_df["share"].max())
    st.dataframe(
        cat_df,
        hide_index=True,
        width='stretch',
        column_config={
            "category": st.column_config.TextColumn("Category", width="large"),
            "amount": st.column_config.NumberColumn(
                "Amount (tkr)", format="%.0f",
            ),
            "share": st.column_config.ProgressColumn(
                "Share",
                format="%.1f%%",
                min_value=share_min,
                max_value=share_max,
                width="small",
            ),
        },
        column_order=["category", "amount", "share"],
    )


# ============================================================================
# SECTION 4 -- NON-CONTROLLABLE CATEGORY BREAKDOWN
# ============================================================================

def _render_noncontrollable_categories(
    detail: Optional[pd.DataFrame],
    user_reid: str,
) -> None:
    """Horizontal bar chart + table for non-controllable KENT categories."""

    st.markdown("**Non-Controllable Operating Expenditures Decomposition**")

    cat_df = _get_noncontrollable_categories(detail, user_reid)
    if cat_df is None or cat_df.empty:
        st.info("Non-controllable category data not available.")
        return

    st.caption(
        "Period total 2024-2027 by KENT category. "
        "Shows what constitutes the non-controllable cost base."
    )

    # --- Horizontal bar chart ---
    chart_df = cat_df.sort_values("period_total", ascending=True)

    layout_kwargs, template = _tmpl_safe()
    fig = go.Figure()

    fig.add_trace(go.Bar(
        y=chart_df["kent_category"],
        x=chart_df["period_total"],
        orientation="h",
        marker_color=CLR_NONCONTROLLABLE,
        hovertemplate="%{y}<br>%{x:,.0f} tkr<extra></extra>",
        showlegend=False,
    ))

    fig.update_layout(
        **layout_kwargs,
        template=template,
        margin=dict(l=10, r=20, t=10, b=30),
        height=max(250, len(cat_df) * 40),
        xaxis=dict(
            title="Period total (tkr)",
            showgrid=True,
            gridcolor=COLORS["bg_subtle"],
        ),
        yaxis=dict(showgrid=False, automargin=True),
    )

    st.plotly_chart(fig, width='stretch', config={"displayModeBar": False},
                    key="m4_nonctrl_categories_chart")

    # --- Detail table ---
    share_min = min(0.0, cat_df["share"].min())
    share_max = max(100.0, cat_df["share"].max())
    st.dataframe(
        cat_df,
        hide_index=True,
        width='stretch',
        column_config={
            "kent_category": st.column_config.TextColumn("KENT Category", width="large"),
            "period_total": st.column_config.NumberColumn(
                "Period Total (tkr)", format="%.0f",
            ),
            "share": st.column_config.ProgressColumn(
                "Share",
                format="%.1f%%",
                min_value=share_min,
                max_value=share_max,
                width="small",
            ),
        },
        column_order=["kent_category", "period_total", "share"],
    )

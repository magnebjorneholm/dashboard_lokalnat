"""
M3 Cost of Capital -- Incentive Adjustment Output

Visualises the three regulatory incentive mechanisms that adjust
the allowed return on capital:

  30.2  Network loss incentive    (nätförlustjustering)
  30.3  Utilization incentive     (belastningsjustering)
  30.4  Quality / interruption    (kvalitetsjustering, AIT/AIF + CEMI4)
  30.5  Aggregate incentive total (after individual and aggregate caps)

Layout
------
1. KPI hero row          -- 4 metrics (total + 3 sub-incentives), MSEK
2. Waterfall pipeline    -- step-by-step from raw to final, dropdown for
                            aggregate / per-year view, with cap reference
3. AIT / AIF heatmaps   -- quality incentive by customer type (expander)

All monetary values displayed in MSEK (pipeline data is in kr).

Variable-IDs (User Manual Table 10):
  30.2.4 / 30.2.5   Network loss before / after cap
  30.3.4 / 30.3.5   Utilization before / after cap
  30.4.57 / 58 / 59 Quality before CEMI4, after CEMI4, after cap
  30.5.1 / 30.5.2   Total before / after aggregate cap
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from typing import Dict, Any, Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from pipeline.core import PipelineResult

from frontend.common.styling import COLORS, CHART_COLORS, get_plotly_template
from pipeline.result_helpers import TOLERANCE
from config.column_names import (
    COL_INCENTIVE_TOTAL, COL_QUALITY_INCENTIVE, COL_NETLOSS_INCENTIVE,
    COL_LOAD_INCENTIVE, COL_MISSING_INCENTIVE,
)
from config.glossary import (
    VID_TOTAL_AFTER_AGG_CAP, VID_INTER_AFTER_CAP,
    VID_LOSS_AFTER_CAP, VID_UTIL_AFTER_CAP,
    INCENTIVE_OUTPUT_VAR_IDS,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Colours -- semantic mapping for the three incentive types
CLR_QUALITY = CHART_COLORS[0]      # Primary Blue
CLR_NETLOSS = CHART_COLORS[1]      # Teal
CLR_LOAD = CHART_COLORS[2]         # Violet
CLR_CAP = CHART_COLORS[4]          # Orange  -- cap adjustments
CLR_TOTAL = CHART_COLORS[3]        # Emerald -- totals / subtotals
CLR_NEGATIVE = "#DC2626"           # Red (for negative waterfall bars)
CLR_POSITIVE = "#059669"           # Emerald (for positive waterfall bars)

SNI_LABELS = {
    1: "Agriculture",
    2: "Industry",
    3: "Trade/Serv.",
    4: "Public",
    5: "Household",
    6: "Boundary",
}

# Display order for heatmap rows: planned first, then unplanned
# Each tuple: (ann_code, sni, display_label)
HEATMAP_ROW_ORDER = [
    ("a", 6, "Plan. Boundary"),
    ("a", 5, "Plan. Household"),
    ("a", 4, "Plan. Public"),
    ("a", 3, "Plan. Trade/Serv."),
    ("a", 2, "Plan. Industry"),
    ("a", 1, "Plan. Agriculture"),
    ("o", 6, "Unplan. Boundary"),
    ("o", 5, "Unplan. Household"),
    ("o", 4, "Unplan. Public"),
    ("o", 3, "Unplan. Trade/Serv."),
    ("o", 2, "Unplan. Industry"),
    ("o", 1, "Unplan. Agriculture"),
]

YEARS = [2024, 2025, 2026, 2027]


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def _fmt_msek(v: float) -> str:
    """Format kr value as MSEK string."""
    return f"{v / 1e6:,.2f} MSEK"


def _fmt_delta_msek(d: float) -> Optional[str]:
    """Format delta in kr as MSEK string, return None if negligible."""
    if abs(d) < 1e3:  # less than 1 tkr
        return None
    return f"{d / 1e6:+,.2f} MSEK"


def _kr_to_msek(v: float) -> float:
    return v / 1e6


# ---------------------------------------------------------------------------
# Data extraction helpers
# ---------------------------------------------------------------------------

def _get_incentive_details(
    result: "PipelineResult",
) -> Optional[pd.DataFrame]:
    """Extract user_incentive_details from pipeline result."""
    return getattr(result.post_dea, "user_incentive_details", None)


def _get_ir_value(ir: pd.Series, key: str, default: float = 0.0) -> float:
    """Safely get value from intaktsram Series (values in tkr)."""
    val = ir.get(key, default)
    return float(val) if pd.notna(val) else default


def _year_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Return only year rows (exclude Total)."""
    return df[df["year"] != "Total"]


def _total_row(df: pd.DataFrame) -> pd.Series:
    """Return the Total row as a Series."""
    total = df[df["year"] == "Total"]
    if total.empty:
        return pd.Series(dtype=float)
    return total.iloc[0]


def _safe_col(df: pd.DataFrame, col: str, default: float = 0.0) -> float:
    """Get column value safely from a Series/row."""
    if col in df.index:
        v = df[col]
        return float(v) if pd.notna(v) else default
    return default


# ===================================================================
# MAIN RENDER
# ===================================================================

def render(
    case: "PipelineResult",
    baseline: "PipelineResult",
    ui_config: Dict[str, Any],
) -> None:
    """Render M3 incentive adjustment outputs (30.2 -- 30.5)."""

    case_ir = case.post_dea.user_revenue_frame
    baseline_ir = baseline.post_dea.user_revenue_frame

    case_details = _get_incentive_details(case)
    baseline_details = _get_incentive_details(baseline)

    st.markdown("#### 30.2-30.5 Incentive Adjustments")

    # Missing data warning
    if _get_ir_value(case_ir, COL_MISSING_INCENTIVE, 0):
        st.warning("Incentive data incomplete for this company.")

    # Section 1: KPI Hero
    _render_kpi_hero(case_ir, baseline_ir)

    # Section 2: Waterfall pipeline
    if case_details is not None:
        _render_waterfall_section(case_details, baseline_details)
    else:
        st.info("Detailed incentive data not available for waterfall chart.")

    # Section 3: AIT / AIF heatmaps
    if case_details is not None:
        _render_ait_aif_section(case_details, baseline_details)


# ===================================================================
# SECTION 1: KPI HERO ROW
# ===================================================================

def _render_kpi_hero(case_ir: pd.Series, baseline_ir: pd.Series) -> None:
    """Four key metrics: total + three sub-incentives, in MSEK."""

    # intaktsram values are in tkr -- convert to kr for uniform _fmt_msek
    components = [
        (f"{VID_TOTAL_AFTER_AGG_CAP} Total",    COL_INCENTIVE_TOTAL),
        (f"{VID_INTER_AFTER_CAP} Quality",       COL_QUALITY_INCENTIVE),
        (f"{VID_LOSS_AFTER_CAP} Net loss",       COL_NETLOSS_INCENTIVE),
        (f"{VID_UTIL_AFTER_CAP} Load",           COL_LOAD_INCENTIVE),
    ]

    cols = st.columns(len(components))
    for col, (label, key) in zip(cols, components):
        c_val = _get_ir_value(case_ir, key) * 1000   # tkr -> kr
        b_val = _get_ir_value(baseline_ir, key) * 1000
        delta = c_val - b_val

        with col:
            st.metric(
                label,
                _fmt_msek(c_val),
                delta=_fmt_delta_msek(delta),
                delta_color="normal",
            )

    st.caption(
        "Positive values increase the revenue frame; "
        "negative values decrease it. Values in MSEK."
    )


# ===================================================================
# SECTION 2: WATERFALL PIPELINE
# ===================================================================

def _render_waterfall_section(
    case_details: pd.DataFrame,
    baseline_details: Optional[pd.DataFrame],
) -> None:
    """Waterfall chart showing the incentive calculation pipeline."""

    st.markdown("**Incentive Pipeline**")

    # Dropdown: aggregate (period total) or per-year
    view_options = ["Period total (2024-2027)"] + [str(y) for y in YEARS]
    selected_view = st.selectbox(
        "View",
        options=view_options,
        key="m3_inc_waterfall_view",
        label_visibility="collapsed",
    )

    if selected_view.startswith("Period"):
        row = _total_row(case_details)
    else:
        year = int(selected_view)
        year_rows = case_details[case_details["year"] == year]
        if year_rows.empty:
            st.info(f"No data for {year}.")
            return
        row = year_rows.iloc[0]

    _render_waterfall_chart(row, selected_view)


def _render_waterfall_chart(row: pd.Series, title_suffix: str) -> None:
    """Build and render the Plotly waterfall chart."""

    # Extract values (all in kr)
    loss_raw = _safe_col(row, "loss_incentive_a")
    loss_capped = _safe_col(row, "loss_incentive")
    loss_cap_adj = loss_capped - loss_raw

    util_raw = _safe_col(row, "util_incentive_a")
    util_capped = _safe_col(row, "util_incentive")
    util_cap_adj = util_capped - util_raw

    qual_raw = _safe_col(row, "inc_inter")
    qual_after_cemi4 = _safe_col(row, "inter_incentive_a")
    cemi4_adj = qual_after_cemi4 - qual_raw
    qual_capped = _safe_col(row, "inter_incentive")
    qual_cap_adj = qual_capped - qual_after_cemi4

    total_before_agg = _safe_col(row, "total_before_agg_cap")
    final_total = _safe_col(row, "incentive_total_year")
    agg_cap_adj = final_total - total_before_agg

    # Build waterfall data -- values in MSEK for display
    labels = [
        "Network loss (raw)",
        "Net loss cap adj.",
        "Utilization (raw)",
        "Load cap adj.",
        "Quality (raw)",
        "CEMI4 correction",
        "Quality cap adj.",
        "Sum before agg. cap",
        "Aggregate cap adj.",
        "Final incentive total",
    ]
    values_kr = [
        loss_raw,
        loss_cap_adj,
        util_raw,
        util_cap_adj,
        qual_raw,
        cemi4_adj,
        qual_cap_adj,
        0,  # subtotal -- plotly computes
        agg_cap_adj,
        0,  # total -- plotly computes
    ]
    measures = [
        "relative",  # loss raw
        "relative",  # loss cap
        "relative",  # util raw
        "relative",  # util cap
        "relative",  # quality raw
        "relative",  # cemi4
        "relative",  # quality cap
        "total",     # subtotal
        "relative",  # agg cap
        "total",     # final total
    ]

    values_msek = [v / 1e6 for v in values_kr]

    # Custom text annotations
    text_vals = []
    for v, m in zip(values_msek, measures):
        if m == "total":
            # For subtotals/totals, show the running total
            pass
        text_vals.append(f"{v:+,.2f}" if abs(v) > 0.001 else "0")

    # Colour: raw incentives get their type colour, cap adjustments get orange,
    # totals get emerald
    increasing_color = CLR_POSITIVE
    decreasing_color = CLR_NEGATIVE
    totals_color = COLORS["primary"]

    tmpl = get_plotly_template()

    fig = go.Figure(go.Waterfall(
        orientation="h",
        y=labels,
        x=values_msek,
        measure=measures,
        textposition="outside",
        text=[f"{v:+,.2f}" if abs(v) > 0.001 else "" for v in values_msek],
        textfont=dict(size=11, family="Inter, sans-serif"),
        connector=dict(
            line=dict(color=COLORS["bg_muted"], width=1, dash="dot")
        ),
        increasing=dict(marker=dict(color=CLR_POSITIVE)),
        decreasing=dict(marker=dict(color=CLR_NEGATIVE)),
        totals=dict(marker=dict(color=COLORS["primary"])),
    ))

    fig.update_layout(
        font=tmpl.get("font", {}),
        paper_bgcolor=tmpl.get("paper_bgcolor", "rgba(0,0,0,0)"),
        plot_bgcolor=tmpl.get("plot_bgcolor", "rgba(0,0,0,0)"),
        margin=dict(l=10, r=80, t=10, b=40),
        height=420,
        xaxis=dict(
            title="MSEK",
            showgrid=True,
            gridcolor=COLORS["bg_subtle"],
            zeroline=True,
            zerolinecolor=COLORS["bg_muted"],
            zerolinewidth=1,
        ),
        yaxis=dict(
            showgrid=False,
            automargin=True,
            autorange="reversed",
        ),
        showlegend=False,
    )

    st.plotly_chart(fig, width='stretch', key="m3_inc_waterfall")

    # Cap reference below chart -- styled as a subtle info row
    max_adj = _safe_col(row, "max_adj")
    ret_period = _safe_col(row, "ret_period")
    if ret_period > 0:
        cap_binding = abs(final_total) >= abs(max_adj) * 0.99
        cap_note = " — <b>cap is binding</b>" if cap_binding else ""
        bg = COLORS["bg_subtle"]
        border = COLORS["primary"]
        fg = COLORS["text_secondary"]
        st.markdown(
            f"<div style='background:{bg};border-left:3px solid "
            f"{border};padding:8px 12px;border-radius:4px;margin-top:-8px;"
            f"font-size:0.88em;color:{fg}'>"
            f"Return for cap calculation: <b>{ret_period / 1e6:,.2f} MSEK</b>"
            f" &nbsp;|&nbsp; "
            f"Max adjustment (±1/3): <b>{abs(max_adj) / 1e6:,.2f} MSEK</b>"
            f"{cap_note}</div>",
            unsafe_allow_html=True,
        )


# ===================================================================
# SECTION 3: AIT / AIF HEATMAPS
# ===================================================================

def _render_ait_aif_section(
    case_details: pd.DataFrame,
    baseline_details: Optional[pd.DataFrame],
) -> None:
    """Heatmaps for quality incentive decomposition by customer type."""

    # Check if AIT/AIF columns exist
    ait_cols = [c for c in case_details.columns if c.startswith("inc_ait_")]
    aif_cols = [c for c in case_details.columns if c.startswith("inc_aif_")]

    if not ait_cols and not aif_cols:
        return

    st.markdown("")  # spacing after cap info box

    st.markdown("**Quality Incentive by Customer Type (AIT / AIF)**")

    if ait_cols and aif_cols:
        col_left, col_right = st.columns(2)
        with col_left:
            _render_heatmap(case_details, "ait", "AIT Quality Incentive")
        with col_right:
            _render_heatmap(case_details, "aif", "AIF Quality Incentive")
    elif ait_cols:
        _render_heatmap(case_details, "ait", "AIT Quality Incentive")
    elif aif_cols:
        _render_heatmap(case_details, "aif", "AIF Quality Incentive")

    st.caption(
        "Values in MSEK. Red = positive (revenue increase), "
        "blue = negative (revenue decrease). "
        "Rows: Plan. = planned (aviserat), Unplan. = unplanned (oaviserat)."
    )


def _render_heatmap(
    details: pd.DataFrame,
    indicator: str,      # "ait" or "aif"
    title: str,
) -> None:
    """Render a single AIT or AIF heatmap."""

    year_rows = _year_rows(details)
    if year_rows.empty:
        st.info(f"No {indicator.upper()} data available.")
        return

    # Build the z-matrix (rows = customer types, cols = years)
    y_labels = []
    z_matrix = []

    for ann, sni, label in HEATMAP_ROW_ORDER:
        col_name = f"inc_{indicator}_{ann}_{sni}"
        if col_name not in details.columns:
            continue

        y_labels.append(label)
        row_vals = []
        for year in YEARS:
            yr_data = year_rows[year_rows["year"] == year]
            if yr_data.empty:
                row_vals.append(0.0)
            else:
                val = yr_data.iloc[0].get(col_name, 0)
                row_vals.append(_kr_to_msek(float(val) if pd.notna(val) else 0))
        z_matrix.append(row_vals)

    if not z_matrix:
        st.info(f"No {indicator.upper()} data available.")
        return

    # Determine symmetric colour range
    z_flat = [v for row in z_matrix for v in row]
    z_abs_max = max(abs(min(z_flat)), abs(max(z_flat))) if z_flat else 1
    if z_abs_max < 1e-6:
        z_abs_max = 1e-3  # avoid zero range

    tmpl = get_plotly_template()

    fig = go.Figure(go.Heatmap(
        z=z_matrix,
        x=[str(y) for y in YEARS],
        y=y_labels,
        colorscale="RdBu_r",
        zmid=0,
        zmin=-z_abs_max,
        zmax=z_abs_max,
        colorbar=dict(
            title=dict(text="MSEK", side="right"),
            thickness=12,
            len=0.9,
        ),
        hovertemplate=(
            "%{y}<br>%{x}<br>%{z:,.4f} MSEK<extra></extra>"
        ),
        xgap=2,
        ygap=2,
    ))

    fig.update_layout(
        title=dict(
            text=title,
            font=dict(size=14, family="Inter, sans-serif", color=COLORS["text_primary"]),
            x=0, xanchor="left",
        ),
        font=tmpl.get("font", {}),
        paper_bgcolor=tmpl.get("paper_bgcolor", "rgba(0,0,0,0)"),
        plot_bgcolor=tmpl.get("plot_bgcolor", "rgba(0,0,0,0)"),
        margin=dict(l=10, r=10, t=35, b=30),
        height=max(300, len(y_labels) * 28 + 80),
        xaxis=dict(side="bottom", dtick=1),
        yaxis=dict(automargin=True, autorange="reversed"),
    )

    st.plotly_chart(fig, width='stretch', key=f"m3_inc_{indicator}_heatmap")
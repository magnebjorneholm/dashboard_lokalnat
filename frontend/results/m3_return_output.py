"""
M3 Cost of Capital - Return Output Display

Section 1: Return on Capital by Category (30.1.X)
  - KPI Hero: Total / Ordinarie / Tail (MSEK) + WACC (3.2.5) with delta pp
  - Category composition chart (Plotly horizontal stacked bar)
  - Category detail table with sparklines, delta, ord share
  - Half-year drill-down (expander: chart + table per category)

Variable-IDs:
  3.2.5        WACC real pre-tax (shown as compact metric)
  30.1         Total return on capital
  30.1.2-30.1.18  Return per asset category (ord/tail)

All monetary values displayed in MSEK (tkr / 1000).
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from typing import Dict, Any, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from pipeline.core import PipelineResult

from config.asset_categories import (
    ASSET_CATEGORIES, CATEGORY_BY_CODE, get_category_short_name,
)
from frontend.common.styling import COLORS, CHART_COLORS, get_plotly_template
from pipeline.result_helpers import (
    TIME_LABELS, TIME_CODES_ORDERED, TOLERANCE,
    CLR_CASE_ORD, CLR_CASE_TAIL, CLR_BL_ORD, CLR_BL_TAIL,
    load_baseline_category_data, get_case_category_data,
    aggregate_period, aggregate_halfyears,
    active_categories, halfyear_values,
    fmt_msek, fmt_delta_msek, fmt_pct,
    add_comparison_traces,
)
from config.formatting import format_pp
from calculations.capex.wacc_calculations import BASELINE_WACC
from config.glossary import (
    capital_cost_var_id,
    VID_TOTAL_CAPITAL_COST_ORD,
    VID_TOTAL_CAPITAL_COST_TAIL,
    PID_WACC_REAL,
)


# ---------------------------------------------------------------------------
# Variable-ID helpers
# ---------------------------------------------------------------------------

# Return column names
_ORD, _TAIL, _TOTAL = 'return_ord', 'return_tail', 'return_total'


def _var_id_return(cat_encode: int, component: str = "ord") -> str:
    """30.1.{cat_encode+1}.1 (ord) or 30.1.{cat_encode+1}.2 (tail)"""
    return capital_cost_var_id(cat_encode, component)


def _var_id_return_combined(cat_encode: int) -> str:
    """Combined ID string for table display: '30.1.X.1/.2'"""
    return capital_cost_var_id(cat_encode, "combined")


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Module-local aggregation wrappers
# ---------------------------------------------------------------------------

def _agg_period(df):
    return aggregate_period(df, _ORD, _TAIL, _TOTAL)


def _agg_halfyears(df):
    return aggregate_halfyears(df, _ORD, _TAIL, _TOTAL)


def _active_cats(case_p, bl_p):
    return active_categories(case_p, bl_p, _TOTAL)


# ===================================================================
# MAIN RENDER
# ===================================================================

def render(
    case: "PipelineResult",
    baseline: "PipelineResult",
    ui_config: Dict[str, Any],
) -> None:
    """Render M3 WACC + Return on Capital outputs."""

    wacc_case = case.pre_dea.wacc_used or BASELINE_WACC
    user_id_network = getattr(case.pre_dea, 'user_id_network', None)

    # --- Return on Capital (includes WACC metric in KPI row) ---
    _render_return_section(case, baseline, user_id_network, wacc_case)


# ===================================================================
# SECTION: RETURN ON CAPITAL (30.1)
# ===================================================================

def _render_return_section(
    case: "PipelineResult",
    baseline: "PipelineResult",
    user_id_network: Optional[int],
    wacc_case: float = BASELINE_WACC,
) -> None:
    """Render return on capital by category -- mirrors M1 layout."""

    _sec_prefix = VID_TOTAL_CAPITAL_COST_ORD.rsplit(".", 2)[0]   # "30.1"
    st.markdown(f"#### {_sec_prefix} Return on Capital")

    if user_id_network is None:
        st.warning("User company not identified.")
        return

    # Load data
    baseline_cat = load_baseline_category_data(user_id_network)
    case_cat = get_case_category_data(case, user_id_network)

    if baseline_cat is None or baseline_cat.empty:
        st.info(
            "Baseline category data not available. "
            "Ensure capcost_a.parquet is in the data/rab_and_capex/ directory."
        )
        return

    is_baseline_case = False
    if case_cat is None or case_cat.empty:
        case_cat = baseline_cat.copy()
        is_baseline_case = True

    # Aggregate
    case_period = _agg_period(case_cat)
    bl_period = _agg_period(baseline_cat)
    case_hy = _agg_halfyears(case_cat)

    active_cats = _active_cats(case_period, bl_period)

    if is_baseline_case:
        st.caption(
            "Case uses baseline values (no parameter changes applied to category data)."
        )

    # Sub-sections
    _render_return_kpi(case_period, bl_period, wacc_case)
    st.divider()
    _render_return_category_chart(case_period, bl_period, active_cats)
    st.divider()
    _render_return_category_table(case_period, bl_period, case_hy, active_cats)



# ---------------------------------------------------------------------------
# Return KPI Hero
# ---------------------------------------------------------------------------

def _render_return_kpi(
    case_period: pd.DataFrame,
    bl_period: pd.DataFrame,
    wacc_case: float = BASELINE_WACC,
) -> None:
    """30.1 Total Return -- three return metrics + WACC."""

    c_ord = case_period['return_ord'].sum() if not case_period.empty else 0.0
    c_tail = case_period['return_tail'].sum() if not case_period.empty else 0.0
    c_total = c_ord + c_tail

    b_ord = bl_period['return_ord'].sum() if not bl_period.empty else 0.0
    b_tail = bl_period['return_tail'].sum() if not bl_period.empty else 0.0
    b_total = b_ord + b_tail

    wacc_delta = wacc_case - BASELINE_WACC
    wacc_delta_str = format_pp(wacc_delta) if abs(wacc_delta) > 1e-6 else None

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total", fmt_msek(c_total), fmt_delta_msek(c_total - b_total))
    with col2:
        st.metric("Ordinarie", fmt_msek(c_ord), fmt_delta_msek(c_ord - b_ord))
    with col3:
        st.metric("Tail", fmt_msek(c_tail), fmt_delta_msek(c_tail - b_tail))
    with col4:
        st.metric(f"{PID_WACC_REAL} WACC", fmt_pct(wacc_case), delta=wacc_delta_str)


# ---------------------------------------------------------------------------
# Return Category Chart
# ---------------------------------------------------------------------------

def _render_return_category_chart(
    case_period: pd.DataFrame,
    bl_period: pd.DataFrame,
    active_cats: List[int],
) -> None:
    """Horizontal stacked bar: Case vs Baseline return per category."""

    _first = capital_cost_var_id(1, "ord").rsplit(".", 1)[0]   # "30.1.2"
    _last = capital_cost_var_id(17, "ord").rsplit(".", 1)[0]  # "30.1.18"
    st.markdown(f"#### {_first}-{_last} Return by Category")

    if not active_cats:
        st.info("No category data available.")
        return

    rows = []
    for ce in active_cats:
        c_row = case_period[case_period['cat_encode'] == ce]
        b_row = bl_period[bl_period['cat_encode'] == ce]
        rows.append({
            'cat_encode': ce,
            'label': get_category_short_name(ce),
            'c_ord': float(c_row['return_ord'].iloc[0]) if not c_row.empty else 0.0,
            'c_tail': float(c_row['return_tail'].iloc[0]) if not c_row.empty else 0.0,
            'b_ord': float(b_row['return_ord'].iloc[0]) if not b_row.empty else 0.0,
            'b_tail': float(b_row['return_tail'].iloc[0]) if not b_row.empty else 0.0,
        })

    chart_df = pd.DataFrame(rows)
    chart_df['c_total'] = chart_df['c_ord'] + chart_df['c_tail']
    # Convert to MSEK for chart axis
    for col in ['c_ord', 'c_tail', 'b_ord', 'b_tail', 'c_total']:
        chart_df[col] = chart_df[col] / 1e3
    chart_df = chart_df.sort_values('c_total', ascending=True)

    tmpl = get_plotly_template()
    fig = go.Figure()

    add_comparison_traces(
        fig, chart_df['label'],
        c_ord=chart_df['c_ord'], c_tail=chart_df['c_tail'],
        b_ord=chart_df['b_ord'], b_tail=chart_df['b_tail'],
        orientation='h', unit='MSEK', fmt=',.2f',
    )

    fig.update_layout(
        barmode='stack',
        font=tmpl.get('font', {}),
        paper_bgcolor=tmpl.get('paper_bgcolor', 'rgba(0,0,0,0)'),
        plot_bgcolor=tmpl.get('plot_bgcolor', 'rgba(0,0,0,0)'),
        margin=dict(l=10, r=20, t=10, b=30),
        height=max(250, len(active_cats) * 50),
        xaxis=dict(
            title='Return (MSEK)',
            showgrid=True,
            gridcolor=COLORS['bg_subtle'],
        ),
        yaxis=dict(showgrid=False, automargin=True),
        bargroupgap=0.15,
    )

    st.plotly_chart(fig, width='stretch', key="m3_return_category_chart", config={"displayModeBar": False})


# ---------------------------------------------------------------------------
# Return Category Detail Table
# ---------------------------------------------------------------------------

def _render_return_category_table(
    case_period: pd.DataFrame,
    bl_period: pd.DataFrame,
    case_hy: pd.DataFrame,
    active_cats: List[int],
) -> None:
    """Detailed category table with sparklines and ord-share indicator."""

    if not active_cats:
        return

    rows = []
    for ce in active_cats:
        cat = CATEGORY_BY_CODE.get(ce)
        if cat is None:
            continue

        c_row = case_period[case_period['cat_encode'] == ce]
        b_row = bl_period[bl_period['cat_encode'] == ce]

        c_ord = float(c_row['return_ord'].iloc[0]) if not c_row.empty else 0.0
        c_tail = float(c_row['return_tail'].iloc[0]) if not c_row.empty else 0.0
        c_total = c_ord + c_tail

        b_ord = float(b_row['return_ord'].iloc[0]) if not b_row.empty else 0.0
        b_tail = float(b_row['return_tail'].iloc[0]) if not b_row.empty else 0.0
        b_total = b_ord + b_tail

        delta = c_total - b_total
        delta_pct = (delta / b_total * 100) if abs(b_total) > TOLERANCE else 0.0
        ord_share = (c_ord / c_total * 100) if abs(c_total) > TOLERANCE else 0.0

        # Half-year sparkline (in MSEK)
        hy_vals_tkr = halfyear_values(case_hy, ce, 'return_total')
        hy_vals = [v / 1e3 for v in hy_vals_tkr]

        rows.append({
            'Var-ID': _var_id_return_combined(ce),
            'Category': cat.name,
            'Ord (MSEK)': c_ord / 1e3,
            'Tail (MSEK)': c_tail / 1e3,
            'Total (MSEK)': c_total / 1e3,
            'Delta (MSEK)': delta / 1e3,
            'Delta (%)': delta_pct,
            'Half-years': hy_vals,
            'Ord share': ord_share,
        })

    table_df = pd.DataFrame(rows)

    st.caption(
        "Case period totals in MSEK. Delta vs baseline. "
        "Ord share = share of ordinarie components."
    )

    st.dataframe(
        table_df,
        hide_index=True,
        width='stretch',
        column_config={
            'Var-ID': st.column_config.TextColumn('ID', width='small'),
            'Category': st.column_config.TextColumn('Category', width='large'),
            'Ord (MSEK)': st.column_config.NumberColumn('Ord', format='%.2f'),
            'Tail (MSEK)': st.column_config.NumberColumn('Tail', format='%.2f'),
            'Total (MSEK)': st.column_config.NumberColumn('Total', format='%.2f'),
            'Delta (MSEK)': st.column_config.NumberColumn('Delta', format='%+.2f'),
            'Delta (%)': st.column_config.NumberColumn('Delta %', format='%+.1f%%'),
            'Half-years': st.column_config.BarChartColumn(
                'Half-years (2024H1-2027H2)', width='medium', y_min=0,
            ),
            'Ord share': st.column_config.ProgressColumn(
                'Ord share', format='%.0f%%',
                min_value=0.0, max_value=100.0, width='small',
            ),
        },
        column_order=[
            'Var-ID', 'Category',
            'Ord (MSEK)', 'Tail (MSEK)', 'Total (MSEK)',
            'Delta (MSEK)', 'Delta (%)',
            'Half-years', 'Ord share',
        ],
    )



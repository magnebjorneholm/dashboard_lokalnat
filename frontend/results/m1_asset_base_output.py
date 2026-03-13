"""
M1 Regulatory Asset Base Valuation - Output Display

Variable-IDs: 11.1 (total), 11.2-11.18 (per category)
Displays NUAV (nuanskaffningsvärde) for ordinary and tail components.

This module shows ONLY NUAV values. Depreciation is in M2, Return is in M3.

Layout:
  1. KPI Hero Section (3 metrics: Total, Ordinarie, Svans -- with delta)
  2. Category Composition Chart (Plotly horizontal stacked bar, Case vs Baseline)
  3. Category Detail Table (st.dataframe with sparklines + progress)
  4. Half-year Drill-down (expander: Plotly chart + detail table per category)
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from typing import Dict, Any, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from pipeline.core import PipelineResult

from config.glossary import asset_value_var_id, VID_TOTAL_ASSET_VALUE
from config.asset_categories import (
    ASSET_CATEGORIES, CATEGORY_BY_CODE, get_category_short_name,
)
from frontend.common.styling import COLORS, CHART_COLORS, get_plotly_template
from pipeline.result_helpers import (
    TIME_LABELS, TIME_CODES_ORDERED, TOLERANCE,
    CLR_CASE_ORD, CLR_CASE_TAIL, CLR_BL_ORD, CLR_BL_TAIL,
    load_baseline_category_data, get_case_category_data,
    ensure_component_cols, aggregate_period, aggregate_halfyears,
    active_categories, halfyear_values, hy_row_values,
    fmt_msek, fmt_delta_msek,
    add_comparison_traces,
)


# ---------------------------------------------------------------------------
# Variable-ID helper
# ---------------------------------------------------------------------------

# NUAV column names
_ORD, _TAIL, _TOTAL = 'nuav_ord', 'nuav_tail', 'nuav_total'


def _var_id(cat_encode: int) -> str:
    """Variable-ID for asset value by category (delegates to glossary)."""
    return asset_value_var_id(cat_encode)


def _agg_period(df):
    return aggregate_period(df, _ORD, _TAIL, _TOTAL)


def _agg_halfyears(df):
    return aggregate_halfyears(df, _ORD, _TAIL, _TOTAL)


def _active_cats(case_p, bl_p):
    return active_categories(case_p, bl_p, _TOTAL)


# ---------------------------------------------------------------------------
# Main render
# ---------------------------------------------------------------------------

def render(
    case: "PipelineResult",
    baseline: "PipelineResult",
    ui_config: Dict[str, Any],
) -> None:
    """Render M1 asset base outputs (NUAV only)."""

    user_id_network = getattr(case.pre_dea, 'user_id_network', None)
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
    bl_hy = _agg_halfyears(baseline_cat)

    active_cats = _active_cats(case_period, bl_period)

    if is_baseline_case:
        st.caption(
            "Case uses baseline values (no parameter changes applied to category data)."
        )

    # --- Sections ---
    _render_kpi_hero(case_period, bl_period)
    st.divider()
    _render_category_chart(case_period, bl_period, active_cats)
    st.divider()
    _render_category_table(case_period, bl_period, case_hy, active_cats)
    st.divider()
    _render_halfyear_drilldown(case_hy, bl_hy, active_cats)


# ---------------------------------------------------------------------------
# Section 1: KPI Hero
# ---------------------------------------------------------------------------

def _render_kpi_hero(
    case_period: pd.DataFrame,
    bl_period: pd.DataFrame,
) -> None:
    """11.1 Total NUAV -- three key metrics with delta."""

    st.markdown(f"#### {VID_TOTAL_ASSET_VALUE} Total Asset Value (NUAV)")

    c_ord = case_period['nuav_ord'].sum() if not case_period.empty else 0.0
    c_tail = case_period['nuav_tail'].sum() if not case_period.empty else 0.0
    c_total = c_ord + c_tail

    b_ord = bl_period['nuav_ord'].sum() if not bl_period.empty else 0.0
    b_tail = bl_period['nuav_tail'].sum() if not bl_period.empty else 0.0
    b_total = b_ord + b_tail

    d_total = c_total - b_total
    d_ord = c_ord - b_ord
    d_tail = c_tail - b_tail

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total", fmt_msek(c_total), fmt_delta_msek(d_total))
    with col2:
        st.metric("Ordinary", fmt_msek(c_ord), fmt_delta_msek(d_ord))
    with col3:
        st.metric("Tail", fmt_msek(c_tail), fmt_delta_msek(d_tail))




# ---------------------------------------------------------------------------
# Section 2: Category Composition Chart
# ---------------------------------------------------------------------------

def _render_category_chart(
    case_period: pd.DataFrame,
    bl_period: pd.DataFrame,
    active_cats: List[int],
) -> None:
    """Horizontal stacked bar: Case vs Baseline NUAV per category."""

    st.markdown(
        f"#### {asset_value_var_id(1)}-{asset_value_var_id(17)} "
        f"Asset Value by Category"
    )

    if not active_cats:
        st.info("No category data available.")
        return

    # Build data sorted by case total descending
    rows = []
    for ce in active_cats:
        c_row = case_period[case_period['cat_encode'] == ce]
        b_row = bl_period[bl_period['cat_encode'] == ce]
        rows.append({
            'cat_encode': ce,
            'label': get_category_short_name(ce),
            'c_ord': float(c_row['nuav_ord'].iloc[0]) if not c_row.empty else 0.0,
            'c_tail': float(c_row['nuav_tail'].iloc[0]) if not c_row.empty else 0.0,
            'b_ord': float(b_row['nuav_ord'].iloc[0]) if not b_row.empty else 0.0,
            'b_tail': float(b_row['nuav_tail'].iloc[0]) if not b_row.empty else 0.0,
        })

    chart_df = pd.DataFrame(rows)
    chart_df['c_total'] = chart_df['c_ord'] + chart_df['c_tail']
    chart_df = chart_df.sort_values('c_total', ascending=True)  # bottom = largest

    tmpl = get_plotly_template()
    fig = go.Figure()

    add_comparison_traces(
        fig, chart_df['label'],
        c_ord=chart_df['c_ord'], c_tail=chart_df['c_tail'],
        b_ord=chart_df['b_ord'], b_tail=chart_df['b_tail'],
        orientation='h', unit='tkr', fmt=',.0f',
    )

    fig.update_layout(
        barmode='stack',
        font=tmpl.get('font', {}),
        paper_bgcolor=tmpl.get('paper_bgcolor', 'rgba(0,0,0,0)'),
        plot_bgcolor=tmpl.get('plot_bgcolor', 'rgba(0,0,0,0)'),
        margin=dict(l=10, r=20, t=10, b=30),
        height=max(250, len(active_cats) * 50),
        xaxis=dict(
            title='NUAV (tkr)',
            showgrid=True,
            gridcolor=COLORS['bg_subtle'],
        ),
        yaxis=dict(
            showgrid=False,
            automargin=True,
        ),
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='left',
            x=0,
        ),
        bargroupgap=0.15,
    )

    st.plotly_chart(fig, width='stretch', key="m1_category_chart", config={"displayModeBar": False})


# ---------------------------------------------------------------------------
# Section 3: Category Detail Table
# ---------------------------------------------------------------------------

def _render_category_table(
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

        c_ord = float(c_row['nuav_ord'].iloc[0]) if not c_row.empty else 0.0
        c_tail = float(c_row['nuav_tail'].iloc[0]) if not c_row.empty else 0.0
        c_total = c_ord + c_tail

        b_ord = float(b_row['nuav_ord'].iloc[0]) if not b_row.empty else 0.0
        b_tail = float(b_row['nuav_tail'].iloc[0]) if not b_row.empty else 0.0
        b_total = b_ord + b_tail

        delta = c_total - b_total
        delta_pct = (delta / b_total * 100) if abs(b_total) > TOLERANCE else 0.0

        # Ord share of case total (0-100 for ProgressColumn display)
        ord_share = (c_ord / c_total * 100) if abs(c_total) > TOLERANCE else 0.0

        # Half-year sparkline values
        hy_vals = halfyear_values(case_hy, ce, 'nuav_total')

        rows.append({
            'Var-ID': _var_id(ce),
            'Category': cat.name,
            'Ord (tkr)': c_ord,
            'Tail (tkr)': c_tail,
            'Total (tkr)': c_total,
            'Delta (tkr)': delta,
            'Delta (%)': delta_pct,
            'Half-years': hy_vals,
            'Ord share': ord_share,
        })

    table_df = pd.DataFrame(rows)

    st.caption(
        "Case values in tkr. Delta vs baseline. "
        "Ord share = share of ordinarie components in total."
    )

    st.dataframe(
        table_df,
        hide_index=True,
        width='stretch',
        column_config={
            'Var-ID': st.column_config.TextColumn(
                'ID', width='small',
            ),
            'Category': st.column_config.TextColumn(
                'Category', width='large',
            ),
            'Ord (tkr)': st.column_config.NumberColumn(
                'Ord', format='%.0f',
            ),
            'Tail (tkr)': st.column_config.NumberColumn(
                'Tail', format='%.0f',
            ),
            'Total (tkr)': st.column_config.NumberColumn(
                'Total', format='%.0f',
            ),
            'Delta (tkr)': st.column_config.NumberColumn(
                'Delta', format='%+.0f',
            ),
            'Delta (%)': st.column_config.NumberColumn(
                'Delta %', format='%+.1f%%',
            ),
            'Half-years': st.column_config.BarChartColumn(
                'Half-years (2024H1-2027H2)',
                width='medium',
                y_min=0,
            ),
            'Ord share': st.column_config.ProgressColumn(
                'Ord share',
                format='%.0f%%',
                min_value=0.0,
                max_value=100.0,
                width='small',
            ),
        },
        column_order=[
            'Var-ID', 'Category',
            'Ord (tkr)', 'Tail (tkr)', 'Total (tkr)',
            'Delta (tkr)', 'Delta (%)',
            'Half-years', 'Ord share',
        ],
    )


# ---------------------------------------------------------------------------
# Section 4: Half-year Drill-down
# ---------------------------------------------------------------------------

def _render_halfyear_drilldown(
    case_hy: pd.DataFrame,
    bl_hy: pd.DataFrame,
    active_cats: List[int],
) -> None:
    """Expandable half-year breakdown with chart + table per category."""

    with st.expander("Per-half-year breakdown by category", expanded=False):
        if not active_cats:
            st.info("No category data available.")
            return

        # Dropdown only shows active categories
        cat_options = {
            f"{_var_id(ce)} {CATEGORY_BY_CODE[ce].short_name}": ce
            for ce in active_cats
            if ce in CATEGORY_BY_CODE
        }

        selected_label = st.selectbox(
            "Category",
            options=list(cat_options.keys()),
            key="m1_halfyear_cat_select",
            label_visibility="collapsed",
        )

        if selected_label is None:
            return

        selected_ce = cat_options[selected_label]

        # Build half-year comparison data
        hy_rows = []
        for tc in TIME_CODES_ORDERED:
            label = TIME_LABELS[tc]

            c_vals = hy_row_values(case_hy, selected_ce, tc, _ORD, _TAIL, _TOTAL)
            b_vals = hy_row_values(bl_hy, selected_ce, tc, _ORD, _TAIL, _TOTAL)

            hy_rows.append({
                'Period': label,
                'Case Ord': c_vals[0],
                'Case Tail': c_vals[1],
                'Case Total': c_vals[2],
                'BL Ord': b_vals[0],
                'BL Tail': b_vals[1],
                'BL Total': b_vals[2],
            })

        hy_df = pd.DataFrame(hy_rows)

        # --- Plotly chart ---
        _render_halfyear_chart(hy_df, selected_label)

        # --- Detail table ---
        st.dataframe(
            hy_df,
            hide_index=True,
            width='stretch',
            column_config={
                'Period': st.column_config.TextColumn('Period', width='small'),
                'Case Ord': st.column_config.NumberColumn('Case Ord', format='%.0f'),
                'Case Tail': st.column_config.NumberColumn('Case Tail', format='%.0f'),
                'Case Total': st.column_config.NumberColumn('Case Total', format='%.0f'),
                'BL Ord': st.column_config.NumberColumn('BL Ord', format='%.0f'),
                'BL Tail': st.column_config.NumberColumn('BL Tail', format='%.0f'),
                'BL Total': st.column_config.NumberColumn('BL Total', format='%.0f'),
            },
        )

        st.caption("Values in tkr.")


def _render_halfyear_chart(hy_df: pd.DataFrame, title_label: str) -> None:
    """Stacked bar chart showing Case vs Baseline per half-year."""

    tmpl = get_plotly_template()
    fig = go.Figure()

    add_comparison_traces(
        fig, hy_df['Period'],
        c_ord=hy_df['Case Ord'], c_tail=hy_df['Case Tail'],
        b_ord=hy_df['BL Ord'], b_tail=hy_df['BL Tail'],
        orientation='v', unit='tkr', fmt=',.0f',
    )

    fig.update_layout(
        barmode='stack',
        font=tmpl.get('font', {}),
        paper_bgcolor=tmpl.get('paper_bgcolor', 'rgba(0,0,0,0)'),
        plot_bgcolor=tmpl.get('plot_bgcolor', 'rgba(0,0,0,0)'),
        margin=dict(l=10, r=20, t=10, b=30),
        height=300,
        xaxis=dict(showgrid=False),
        yaxis=dict(
            title='NUAV (tkr)',
            showgrid=True,
            gridcolor=COLORS['bg_subtle'],
        ),
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='left',
            x=0,
        ),
        bargroupgap=0.15,
    )

    st.plotly_chart(fig, width='stretch', key="m1_halfyear_chart", config={"displayModeBar": False})
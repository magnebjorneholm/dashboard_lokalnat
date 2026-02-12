"""
M2 Depreciation - Output Display

Variable-IDs: 20.1.1/20.1.2 (total), 20.2-20.18 (per category)
Displays depreciation for ordinary (.1) and tail (.2) components.

This module shows ONLY depreciation values. NUAV is in M1, Return is in M3.

Layout:
  1. KPI Hero Section (3 metrics: Total, Ordinarie, Svans -- with delta)
  2. Category Composition Chart (Plotly horizontal stacked bar, Case vs Baseline)
  3. Category Detail Table (st.dataframe with sparklines + progress)
  4. Half-year Drill-down (expander: Plotly chart + detail table per category)

All monetary values displayed in MSEK (tkr / 1000).
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from typing import Dict, Any, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from pipeline.core import PipelineResult

from frontend.common.asset_categories import (
    ASSET_CATEGORIES, CATEGORY_BY_CODE, get_category_short_name,
)
from frontend.common.styling import COLORS, CHART_COLORS, get_plotly_template
from frontend.common.result_helpers import (
    TIME_LABELS, TIME_CODES_ORDERED, TOLERANCE, TKR_TO_MSEK,
    CLR_CASE_ORD, CLR_CASE_TAIL, CLR_BL_ORD, CLR_BL_TAIL,
    load_baseline_category_data, get_case_category_data,
    aggregate_period, aggregate_halfyears,
    active_categories, halfyear_values, hy_row_values,
    fmt_msek, fmt_delta_msek,
)
from config.glossary import (
    depreciation_var_id, depreciation_components_var_id,
    VID_TOTAL_DEPRECIATION_ORD, VID_TOTAL_DEPRECIATION_TAIL,
)


# ---------------------------------------------------------------------------
# Variable-ID helper
# ---------------------------------------------------------------------------

# Dep column names
_ORD, _TAIL, _TOTAL = 'dep_ord', 'dep_tail', 'dep_total'


def _var_id(cat_encode: int) -> str:
    """20.{cat_encode + 1}"""
    return depreciation_var_id(cat_encode)


def _var_id_components(cat_encode: int) -> str:
    """20.{cat_encode + 1}.1; 20.{cat_encode + 1}.2"""
    return depreciation_components_var_id(cat_encode)


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
    """Render M2 depreciation outputs."""

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
            "Ensure capcost_a.parquet is in the data/ directory."
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
    """Total Depreciation -- three key metrics with delta."""

    # Derive parent "20.1" from VID_TOTAL_DEPRECIATION_ORD ("20.1.1")
    _dep_parent = VID_TOTAL_DEPRECIATION_ORD.rsplit(".", 1)[0]
    st.markdown(f"#### {_dep_parent} Total Depreciation")

    c_ord = case_period['dep_ord'].sum() if not case_period.empty else 0.0
    c_tail = case_period['dep_tail'].sum() if not case_period.empty else 0.0
    c_total = c_ord + c_tail

    b_ord = bl_period['dep_ord'].sum() if not bl_period.empty else 0.0
    b_tail = bl_period['dep_tail'].sum() if not bl_period.empty else 0.0
    b_total = b_ord + b_tail

    d_total = c_total - b_total
    d_ord = c_ord - b_ord
    d_tail = c_tail - b_tail

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(f"Total ({_dep_parent})", fmt_msek(c_total), fmt_delta_msek(d_total))
    with col2:
        st.metric(f"Ordinarie ({VID_TOTAL_DEPRECIATION_ORD})", fmt_msek(c_ord), fmt_delta_msek(d_ord))
    with col3:
        st.metric(f"Svans ({VID_TOTAL_DEPRECIATION_TAIL})", fmt_msek(c_tail), fmt_delta_msek(d_tail))


# ---------------------------------------------------------------------------
# Section 2: Category Composition Chart
# ---------------------------------------------------------------------------

def _render_category_chart(
    case_period: pd.DataFrame,
    bl_period: pd.DataFrame,
    active_cats: List[int],
) -> None:
    """Horizontal stacked bar: Case vs Baseline depreciation per category."""

    st.markdown("#### 20.2-20.18 Depreciation by Category")

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
            'c_ord': float(c_row['dep_ord'].iloc[0]) / TKR_TO_MSEK if not c_row.empty else 0.0,
            'c_tail': float(c_row['dep_tail'].iloc[0]) / TKR_TO_MSEK if not c_row.empty else 0.0,
            'b_ord': float(b_row['dep_ord'].iloc[0]) / TKR_TO_MSEK if not b_row.empty else 0.0,
            'b_tail': float(b_row['dep_tail'].iloc[0]) / TKR_TO_MSEK if not b_row.empty else 0.0,
        })

    chart_df = pd.DataFrame(rows)
    chart_df['c_total'] = chart_df['c_ord'] + chart_df['c_tail']
    chart_df = chart_df.sort_values('c_total', ascending=True)  # bottom = largest

    tmpl = get_plotly_template()
    fig = go.Figure()

    # Baseline bars (behind)
    fig.add_trace(go.Bar(
        y=chart_df['label'],
        x=chart_df['b_ord'],
        name='Baseline Ord',
        orientation='h',
        marker_color=CLR_BL_ORD,
        offsetgroup='baseline',
        hovertemplate='%{y}<br>Baseline Ord: %{x:,.1f} MSEK<extra></extra>',
    ))
    fig.add_trace(go.Bar(
        y=chart_df['label'],
        x=chart_df['b_tail'],
        name='Baseline Tail',
        orientation='h',
        marker_color=CLR_BL_TAIL,
        offsetgroup='baseline',
        hovertemplate='%{y}<br>Baseline Tail: %{x:,.1f} MSEK<extra></extra>',
    ))

    # Case bars (in front)
    fig.add_trace(go.Bar(
        y=chart_df['label'],
        x=chart_df['c_ord'],
        name='Case Ord',
        orientation='h',
        marker_color=CLR_CASE_ORD,
        offsetgroup='case',
        hovertemplate='%{y}<br>Case Ord: %{x:,.1f} MSEK<extra></extra>',
    ))
    fig.add_trace(go.Bar(
        y=chart_df['label'],
        x=chart_df['c_tail'],
        name='Case Tail',
        orientation='h',
        marker_color=CLR_CASE_TAIL,
        offsetgroup='case',
        hovertemplate='%{y}<br>Case Tail: %{x:,.1f} MSEK<extra></extra>',
    ))

    fig.update_layout(
        barmode='stack',
        font=tmpl.get('font', {}),
        paper_bgcolor=tmpl.get('paper_bgcolor', 'rgba(0,0,0,0)'),
        plot_bgcolor=tmpl.get('plot_bgcolor', 'rgba(0,0,0,0)'),
        margin=dict(l=10, r=20, t=10, b=30),
        height=max(250, len(active_cats) * 50),
        xaxis=dict(
            title='Depreciation (MSEK)',
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

    st.plotly_chart(fig, width='stretch', key="m2_category_chart")


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

        c_ord = float(c_row['dep_ord'].iloc[0]) if not c_row.empty else 0.0
        c_tail = float(c_row['dep_tail'].iloc[0]) if not c_row.empty else 0.0
        c_total = c_ord + c_tail

        b_ord = float(b_row['dep_ord'].iloc[0]) if not b_row.empty else 0.0
        b_tail = float(b_row['dep_tail'].iloc[0]) if not b_row.empty else 0.0
        b_total = b_ord + b_tail

        delta = c_total - b_total
        delta_pct = (delta / b_total * 100) if abs(b_total) > TOLERANCE else 0.0

        # Ord share of case total (0-100 for ProgressColumn display)
        ord_share = (c_ord / c_total * 100) if abs(c_total) > TOLERANCE else 0.0

        # Half-year sparkline values (already in MSEK from helper)
        hy_vals = halfyear_values(case_hy, ce, 'dep_total', divisor=TKR_TO_MSEK)

        rows.append({
            'Var-ID': _var_id(ce),
            'Category': cat.name,
            'Ord (MSEK)': c_ord / TKR_TO_MSEK,
            'Tail (MSEK)': c_tail / TKR_TO_MSEK,
            'Total (MSEK)': c_total / TKR_TO_MSEK,
            'Delta (MSEK)': delta / TKR_TO_MSEK,
            'Delta (%)': delta_pct,
            'Half-years': hy_vals,
            'Ord share': ord_share,
        })

    table_df = pd.DataFrame(rows)

    st.caption(
        "Case values in MSEK. Delta vs baseline. "
        "Ord share = share of ordinarie components in total depreciation."
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
            'Ord (MSEK)': st.column_config.NumberColumn(
                'Ord', format='%.1f',
            ),
            'Tail (MSEK)': st.column_config.NumberColumn(
                'Tail', format='%.1f',
            ),
            'Total (MSEK)': st.column_config.NumberColumn(
                'Total', format='%.1f',
            ),
            'Delta (MSEK)': st.column_config.NumberColumn(
                'Delta', format='%+.1f',
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
            'Ord (MSEK)', 'Tail (MSEK)', 'Total (MSEK)',
            'Delta (MSEK)', 'Delta (%)',
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
            f"{_var_id(ce)} {CATEGORY_BY_CODE[ce].name}": ce
            for ce in active_cats
            if ce in CATEGORY_BY_CODE
        }

        selected_label = st.selectbox(
            "Category",
            options=list(cat_options.keys()),
            key="m2_halfyear_cat_select",
            label_visibility="collapsed",
        )

        if selected_label is None:
            return

        selected_ce = cat_options[selected_label]

        # Build half-year comparison data
        hy_rows = []
        for tc in TIME_CODES_ORDERED:
            label = TIME_LABELS[tc]

            c_vals = hy_row_values(case_hy, selected_ce, tc, _ORD, _TAIL, _TOTAL, divisor=TKR_TO_MSEK)
            b_vals = hy_row_values(bl_hy, selected_ce, tc, _ORD, _TAIL, _TOTAL, divisor=TKR_TO_MSEK)

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
                'Case Ord': st.column_config.NumberColumn('Case Ord', format='%.2f'),
                'Case Tail': st.column_config.NumberColumn('Case Tail', format='%.2f'),
                'Case Total': st.column_config.NumberColumn('Case Total', format='%.2f'),
                'BL Ord': st.column_config.NumberColumn('BL Ord', format='%.2f'),
                'BL Tail': st.column_config.NumberColumn('BL Tail', format='%.2f'),
                'BL Total': st.column_config.NumberColumn('BL Total', format='%.2f'),
            },
        )

        st.caption("Values in MSEK.")


def _render_halfyear_chart(hy_df: pd.DataFrame, title_label: str) -> None:
    """Stacked bar chart showing Case vs Baseline per half-year."""

    tmpl = get_plotly_template()
    fig = go.Figure()

    # Baseline (behind)
    fig.add_trace(go.Bar(
        x=hy_df['Period'],
        y=hy_df['BL Ord'],
        name='Baseline Ord',
        marker_color=CLR_BL_ORD,
        offsetgroup='baseline',
        hovertemplate='%{x}<br>BL Ord: %{y:,.2f} MSEK<extra></extra>',
    ))
    fig.add_trace(go.Bar(
        x=hy_df['Period'],
        y=hy_df['BL Tail'],
        name='Baseline Tail',
        marker_color=CLR_BL_TAIL,
        offsetgroup='baseline',
        hovertemplate='%{x}<br>BL Tail: %{y:,.2f} MSEK<extra></extra>',
    ))

    # Case (in front)
    fig.add_trace(go.Bar(
        x=hy_df['Period'],
        y=hy_df['Case Ord'],
        name='Case Ord',
        marker_color=CLR_CASE_ORD,
        offsetgroup='case',
        hovertemplate='%{x}<br>Case Ord: %{y:,.2f} MSEK<extra></extra>',
    ))
    fig.add_trace(go.Bar(
        x=hy_df['Period'],
        y=hy_df['Case Tail'],
        name='Case Tail',
        marker_color=CLR_CASE_TAIL,
        offsetgroup='case',
        hovertemplate='%{x}<br>Case Tail: %{y:,.2f} MSEK<extra></extra>',
    ))

    fig.update_layout(
        barmode='stack',
        font=tmpl.get('font', {}),
        paper_bgcolor=tmpl.get('paper_bgcolor', 'rgba(0,0,0,0)'),
        plot_bgcolor=tmpl.get('plot_bgcolor', 'rgba(0,0,0,0)'),
        margin=dict(l=10, r=20, t=10, b=30),
        height=300,
        xaxis=dict(showgrid=False),
        yaxis=dict(
            title='Depreciation (MSEK)',
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

    st.plotly_chart(fig, width='stretch', key="m2_halfyear_chart")
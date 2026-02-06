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

from frontend.common.asset_categories import (
    ASSET_CATEGORIES, CATEGORY_BY_CODE, get_category_short_name,
)
from frontend.common.styling import COLORS, CHART_COLORS, get_plotly_template

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TIME_LABELS = {
    229: "2024H1", 230: "2024H2",
    231: "2025H1", 232: "2025H2",
    233: "2026H1", 234: "2026H2",
    235: "2027H1", 236: "2027H2",
}

TIME_CODES_ORDERED = [229, 230, 231, 232, 233, 234, 235, 236]

TOLERANCE = 0.01  # tkr

# Chart colours
CLR_CASE_ORD = CHART_COLORS[0]       # Primary Blue
CLR_CASE_TAIL = "#93C5FD"            # Light blue (blue-300)
CLR_BL_ORD = "#64748B"               # Slate-500
CLR_BL_TAIL = "#CBD5E1"              # Slate-300


# ---------------------------------------------------------------------------
# Variable-ID helper
# ---------------------------------------------------------------------------

def _var_id(cat_encode: int) -> str:
    """11.{cat_encode + 1}"""
    return f"11.{cat_encode + 1}"


# ---------------------------------------------------------------------------
# Data loading / aggregation (unchanged logic, cleaner helpers)
# ---------------------------------------------------------------------------

def _load_baseline_category_data(user_id_network: int) -> Optional[pd.DataFrame]:
    """Load baseline category data for user's company from capcost_a."""
    try:
        from data_loaders.rab_data import load_capcost_a
        df = load_capcost_a()
        return df[df['id_network'] == user_id_network].copy()
    except (FileNotFoundError, ImportError):
        return None


def _get_case_category_data(
    case: "PipelineResult",
    user_id_network: int,
) -> Optional[pd.DataFrame]:
    """Get case category data from pipeline result."""
    df_cat = getattr(case.pre_dea, 'df_by_category', None)
    if df_cat is None:
        return None
    return df_cat[df_cat['id_network'] == user_id_network].copy()


def _ensure_nuav_cols(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure nuav_ord, nuav_tail, nuav_total columns exist."""
    for col in ['nuav_ord', 'nuav_tail']:
        if col not in df.columns:
            df[col] = 0.0
    df['nuav_total'] = df['nuav_ord'] + df['nuav_tail']
    return df


def _aggregate_period(df: Optional[pd.DataFrame]) -> pd.DataFrame:
    """Aggregate half-year data to period totals per category."""
    if df is None or df.empty:
        return pd.DataFrame()
    agg_cols = {c: 'sum' for c in ['nuav_ord', 'nuav_tail'] if c in df.columns}
    if not agg_cols:
        return pd.DataFrame()
    result = df.groupby('cat_encode').agg(agg_cols).reset_index()
    return _ensure_nuav_cols(result)


def _aggregate_halfyears(df: Optional[pd.DataFrame]) -> pd.DataFrame:
    """Keep half-year granularity with nuav totals."""
    if df is None or df.empty:
        return pd.DataFrame()
    result = df.copy()
    result['time_label'] = result['time'].map(TIME_LABELS)
    return _ensure_nuav_cols(result)


def _active_categories(
    case_period: pd.DataFrame,
    baseline_period: pd.DataFrame,
) -> List[int]:
    """Return cat_encode values that have data above tolerance in either set."""
    active = set()
    for df in [case_period, baseline_period]:
        if df.empty:
            continue
        above = df[df['nuav_total'].abs() > TOLERANCE]
        active.update(above['cat_encode'].tolist())
    return sorted(active)


# ---------------------------------------------------------------------------
# Category helpers for half-year sparkline data
# ---------------------------------------------------------------------------

def _halfyear_values(
    df_hy: pd.DataFrame,
    cat_encode: int,
    col: str = 'nuav_total',
) -> List[float]:
    """Extract ordered list of 8 half-year values for one category."""
    if df_hy.empty:
        return [0.0] * 8
    cat_df = df_hy[df_hy['cat_encode'] == cat_encode]
    values = []
    for tc in TIME_CODES_ORDERED:
        row = cat_df[cat_df['time'] == tc]
        values.append(float(row[col].iloc[0]) if not row.empty else 0.0)
    return values


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
    baseline_cat = _load_baseline_category_data(user_id_network)
    case_cat = _get_case_category_data(case, user_id_network)

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
    case_period = _aggregate_period(case_cat)
    bl_period = _aggregate_period(baseline_cat)
    case_hy = _aggregate_halfyears(case_cat)
    bl_hy = _aggregate_halfyears(baseline_cat)

    active_cats = _active_categories(case_period, bl_period)

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

    st.markdown("#### 11.1 Total Asset Value (NUAV)")

    c_ord = case_period['nuav_ord'].sum() if not case_period.empty else 0.0
    c_tail = case_period['nuav_tail'].sum() if not case_period.empty else 0.0
    c_total = c_ord + c_tail

    b_ord = bl_period['nuav_ord'].sum() if not bl_period.empty else 0.0
    b_tail = bl_period['nuav_tail'].sum() if not bl_period.empty else 0.0
    b_total = b_ord + b_tail

    d_total = c_total - b_total
    d_ord = c_ord - b_ord
    d_tail = c_tail - b_tail

    def _fmt_msek(v: float) -> str:
        return f"{v / 1e3:,.1f} MSEK"

    def _fmt_delta(d: float) -> Optional[str]:
        if abs(d) < TOLERANCE:
            return None
        return f"{d / 1e3:+,.1f} MSEK"

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total", _fmt_msek(c_total), _fmt_delta(d_total))
    with col2:
        st.metric("Ordinarie", _fmt_msek(c_ord), _fmt_delta(d_ord))
    with col3:
        st.metric("Svans (tail)", _fmt_msek(c_tail), _fmt_delta(d_tail))




# ---------------------------------------------------------------------------
# Section 2: Category Composition Chart
# ---------------------------------------------------------------------------

def _render_category_chart(
    case_period: pd.DataFrame,
    bl_period: pd.DataFrame,
    active_cats: List[int],
) -> None:
    """Horizontal stacked bar: Case vs Baseline NUAV per category."""

    st.markdown("#### 11.2-11.18 Asset Value by Category")

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

    # Baseline bars (behind)
    fig.add_trace(go.Bar(
        y=chart_df['label'],
        x=chart_df['b_ord'],
        name='Baseline Ord',
        orientation='h',
        marker_color=CLR_BL_ORD,
        offsetgroup='baseline',
        hovertemplate='%{y}<br>Baseline Ord: %{x:,.0f} tkr<extra></extra>',
    ))
    fig.add_trace(go.Bar(
        y=chart_df['label'],
        x=chart_df['b_tail'],
        name='Baseline Tail',
        orientation='h',
        marker_color=CLR_BL_TAIL,
        offsetgroup='baseline',
        hovertemplate='%{y}<br>Baseline Tail: %{x:,.0f} tkr<extra></extra>',
    ))

    # Case bars (in front)
    fig.add_trace(go.Bar(
        y=chart_df['label'],
        x=chart_df['c_ord'],
        name='Case Ord',
        orientation='h',
        marker_color=CLR_CASE_ORD,
        offsetgroup='case',
        hovertemplate='%{y}<br>Case Ord: %{x:,.0f} tkr<extra></extra>',
    ))
    fig.add_trace(go.Bar(
        y=chart_df['label'],
        x=chart_df['c_tail'],
        name='Case Tail',
        orientation='h',
        marker_color=CLR_CASE_TAIL,
        offsetgroup='case',
        hovertemplate='%{y}<br>Case Tail: %{x:,.0f} tkr<extra></extra>',
    ))

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

    st.plotly_chart(fig, use_container_width=True, key="m1_category_chart")


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
        hy_vals = _halfyear_values(case_hy, ce, 'nuav_total')

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
        use_container_width=True,
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

            c_vals = _hy_row_values(case_hy, selected_ce, tc)
            b_vals = _hy_row_values(bl_hy, selected_ce, tc)

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
            use_container_width=True,
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


def _hy_row_values(
    df_hy: pd.DataFrame,
    cat_encode: int,
    time_code: int,
) -> tuple:
    """Return (ord, tail, total) for one category + time code."""
    if df_hy.empty:
        return (0.0, 0.0, 0.0)
    row = df_hy[(df_hy['cat_encode'] == cat_encode) & (df_hy['time'] == time_code)]
    if row.empty:
        return (0.0, 0.0, 0.0)
    return (
        float(row['nuav_ord'].iloc[0]),
        float(row['nuav_tail'].iloc[0]),
        float(row['nuav_total'].iloc[0]),
    )


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
        hovertemplate='%{x}<br>BL Ord: %{y:,.0f} tkr<extra></extra>',
    ))
    fig.add_trace(go.Bar(
        x=hy_df['Period'],
        y=hy_df['BL Tail'],
        name='Baseline Tail',
        marker_color=CLR_BL_TAIL,
        offsetgroup='baseline',
        hovertemplate='%{x}<br>BL Tail: %{y:,.0f} tkr<extra></extra>',
    ))

    # Case (in front)
    fig.add_trace(go.Bar(
        x=hy_df['Period'],
        y=hy_df['Case Ord'],
        name='Case Ord',
        marker_color=CLR_CASE_ORD,
        offsetgroup='case',
        hovertemplate='%{x}<br>Case Ord: %{y:,.0f} tkr<extra></extra>',
    ))
    fig.add_trace(go.Bar(
        x=hy_df['Period'],
        y=hy_df['Case Tail'],
        name='Case Tail',
        marker_color=CLR_CASE_TAIL,
        offsetgroup='case',
        hovertemplate='%{x}<br>Case Tail: %{y:,.0f} tkr<extra></extra>',
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

    st.plotly_chart(fig, use_container_width=True, key="m1_halfyear_chart")
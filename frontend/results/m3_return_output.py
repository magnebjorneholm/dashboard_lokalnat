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

# Chart colours (consistent with M1)
CLR_CASE_ORD = CHART_COLORS[0]       # Primary Blue
CLR_CASE_TAIL = "#93C5FD"            # Light blue (blue-300)
CLR_BL_ORD = "#64748B"               # Slate-500
CLR_BL_TAIL = "#CBD5E1"              # Slate-300

BASELINE_WACC = 0.0453


# ---------------------------------------------------------------------------
# Variable-ID helpers
# ---------------------------------------------------------------------------

def _var_id_return(cat_encode: int, component: str = "ord") -> str:
    """30.1.{cat_encode+1}.1 (ord) or 30.1.{cat_encode+1}.2 (tail)"""
    suffix = "1" if component == "ord" else "2"
    return f"30.1.{cat_encode + 1}.{suffix}"


def _var_id_return_combined(cat_encode: int) -> str:
    """Combined ID string for table display: '30.1.X.1/.2'"""
    return f"30.1.{cat_encode + 1}.1/.2"


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def _fmt_msek(v: float) -> str:
    return f"{v / 1e3:,.1f} MSEK"


def _fmt_delta_msek(d: float) -> Optional[str]:
    if abs(d) < TOLERANCE:
        return None
    return f"{d / 1e3:+,.1f} MSEK"


def _fmt_pct(v: float, decimals: int = 2) -> str:
    if pd.isna(v):
        return "-"
    return f"{v * 100:.{decimals}f}%"


# ---------------------------------------------------------------------------
# Data loading / aggregation (return_ord, return_tail)
# ---------------------------------------------------------------------------

def _load_baseline_category_data(user_id_network: int) -> Optional[pd.DataFrame]:
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
    df_cat = getattr(case.pre_dea, 'df_by_category', None)
    if df_cat is None:
        return None
    return df_cat[df_cat['id_network'] == user_id_network].copy()


def _ensure_return_cols(df: pd.DataFrame) -> pd.DataFrame:
    for col in ['return_ord', 'return_tail']:
        if col not in df.columns:
            df[col] = 0.0
    df['return_total'] = df['return_ord'] + df['return_tail']
    return df


def _aggregate_period(df: Optional[pd.DataFrame]) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    agg_cols = {c: 'sum' for c in ['return_ord', 'return_tail'] if c in df.columns}
    if not agg_cols:
        return pd.DataFrame()
    result = df.groupby('cat_encode').agg(agg_cols).reset_index()
    return _ensure_return_cols(result)


def _aggregate_halfyears(df: Optional[pd.DataFrame]) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    result = df.copy()
    result['time_label'] = result['time'].map(TIME_LABELS)
    return _ensure_return_cols(result)


def _active_categories(
    case_period: pd.DataFrame,
    baseline_period: pd.DataFrame,
) -> List[int]:
    active = set()
    for df in [case_period, baseline_period]:
        if df.empty:
            continue
        above = df[df['return_total'].abs() > TOLERANCE]
        active.update(above['cat_encode'].tolist())
    return sorted(active)


def _halfyear_values(
    df_hy: pd.DataFrame,
    cat_encode: int,
    col: str = 'return_total',
) -> List[float]:
    if df_hy.empty:
        return [0.0] * 8
    cat_df = df_hy[df_hy['cat_encode'] == cat_encode]
    values = []
    for tc in TIME_CODES_ORDERED:
        row = cat_df[cat_df['time'] == tc]
        values.append(float(row[col].iloc[0]) if not row.empty else 0.0)
    return values


def _hy_row_values(
    df_hy: pd.DataFrame,
    cat_encode: int,
    time_code: int,
) -> tuple:
    if df_hy.empty:
        return (0.0, 0.0, 0.0)
    row = df_hy[(df_hy['cat_encode'] == cat_encode) & (df_hy['time'] == time_code)]
    if row.empty:
        return (0.0, 0.0, 0.0)
    return (
        float(row['return_ord'].iloc[0]),
        float(row['return_tail'].iloc[0]),
        float(row['return_total'].iloc[0]),
    )


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

    st.markdown("#### 30.1 Return on Capital")

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

    # Sub-sections
    _render_return_kpi(case_period, bl_period, wacc_case)
    st.divider()
    _render_return_category_chart(case_period, bl_period, active_cats)
    st.divider()
    _render_return_category_table(case_period, bl_period, case_hy, active_cats)
    st.divider()
    _render_return_halfyear_drilldown(case_hy, bl_hy, active_cats)


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
    wacc_delta_str = f"{wacc_delta * 100:+.2f} pp" if abs(wacc_delta) > 1e-6 else None

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total", _fmt_msek(c_total), _fmt_delta_msek(c_total - b_total))
    with col2:
        st.metric("Ordinarie", _fmt_msek(c_ord), _fmt_delta_msek(c_ord - b_ord))
    with col3:
        st.metric("Tail", _fmt_msek(c_tail), _fmt_delta_msek(c_tail - b_tail))
    with col4:
        st.metric("3.2.5 WACC", _fmt_pct(wacc_case), delta=wacc_delta_str)


# ---------------------------------------------------------------------------
# Return Category Chart
# ---------------------------------------------------------------------------

def _render_return_category_chart(
    case_period: pd.DataFrame,
    bl_period: pd.DataFrame,
    active_cats: List[int],
) -> None:
    """Horizontal stacked bar: Case vs Baseline return per category."""

    st.markdown("#### 30.1.2-30.1.18 Return by Category")

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

    # Baseline (behind)
    fig.add_trace(go.Bar(
        y=chart_df['label'], x=chart_df['b_ord'],
        name='Baseline Ord', orientation='h',
        marker_color=CLR_BL_ORD, offsetgroup='baseline',
        hovertemplate='%{y}<br>BL Ord: %{x:,.2f} MSEK<extra></extra>',
    ))
    fig.add_trace(go.Bar(
        y=chart_df['label'], x=chart_df['b_tail'],
        name='Baseline Tail', orientation='h',
        marker_color=CLR_BL_TAIL, offsetgroup='baseline',
        hovertemplate='%{y}<br>BL Tail: %{x:,.2f} MSEK<extra></extra>',
    ))

    # Case (in front)
    fig.add_trace(go.Bar(
        y=chart_df['label'], x=chart_df['c_ord'],
        name='Case Ord', orientation='h',
        marker_color=CLR_CASE_ORD, offsetgroup='case',
        hovertemplate='%{y}<br>Case Ord: %{x:,.2f} MSEK<extra></extra>',
    ))
    fig.add_trace(go.Bar(
        y=chart_df['label'], x=chart_df['c_tail'],
        name='Case Tail', orientation='h',
        marker_color=CLR_CASE_TAIL, offsetgroup='case',
        hovertemplate='%{y}<br>Case Tail: %{x:,.2f} MSEK<extra></extra>',
    ))

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
        legend=dict(
            orientation='h', yanchor='bottom', y=1.02, xanchor='left', x=0,
        ),
        bargroupgap=0.15,
    )

    st.plotly_chart(fig, width='stretch', key="m3_return_category_chart")


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
        hy_vals_tkr = _halfyear_values(case_hy, ce, 'return_total')
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


# ---------------------------------------------------------------------------
# Return Half-year Drill-down
# ---------------------------------------------------------------------------

def _render_return_halfyear_drilldown(
    case_hy: pd.DataFrame,
    bl_hy: pd.DataFrame,
    active_cats: List[int],
) -> None:
    """Expandable half-year breakdown with chart + table per category."""

    with st.expander("Per-half-year breakdown by category", expanded=False):
        if not active_cats:
            st.info("No category data available.")
            return

        cat_options = {
            f"{_var_id_return_combined(ce)} {CATEGORY_BY_CODE[ce].short_name}": ce
            for ce in active_cats
            if ce in CATEGORY_BY_CODE
        }

        selected_label = st.selectbox(
            "Category",
            options=list(cat_options.keys()),
            key="m3_return_halfyear_cat_select",
            label_visibility="collapsed",
        )

        if selected_label is None:
            return

        selected_ce = cat_options[selected_label]

        # Build half-year comparison
        hy_rows = []
        for tc in TIME_CODES_ORDERED:
            label = TIME_LABELS[tc]
            c_vals = _hy_row_values(case_hy, selected_ce, tc)
            b_vals = _hy_row_values(bl_hy, selected_ce, tc)
            hy_rows.append({
                'Period': label,
                'Case Ord': c_vals[0] / 1e3,
                'Case Tail': c_vals[1] / 1e3,
                'Case Total': c_vals[2] / 1e3,
                'BL Ord': b_vals[0] / 1e3,
                'BL Tail': b_vals[1] / 1e3,
                'BL Total': b_vals[2] / 1e3,
            })

        hy_df = pd.DataFrame(hy_rows)

        # Chart
        _render_halfyear_chart(hy_df, selected_label)

        # Table
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
    """Stacked bar chart: Case vs Baseline return per half-year."""

    tmpl = get_plotly_template()
    fig = go.Figure()

    # Baseline (behind)
    fig.add_trace(go.Bar(
        x=hy_df['Period'], y=hy_df['BL Ord'],
        name='Baseline Ord', marker_color=CLR_BL_ORD, offsetgroup='baseline',
        hovertemplate='%{x}<br>BL Ord: %{y:,.2f} MSEK<extra></extra>',
    ))
    fig.add_trace(go.Bar(
        x=hy_df['Period'], y=hy_df['BL Tail'],
        name='Baseline Tail', marker_color=CLR_BL_TAIL, offsetgroup='baseline',
        hovertemplate='%{x}<br>BL Tail: %{y:,.2f} MSEK<extra></extra>',
    ))

    # Case (in front)
    fig.add_trace(go.Bar(
        x=hy_df['Period'], y=hy_df['Case Ord'],
        name='Case Ord', marker_color=CLR_CASE_ORD, offsetgroup='case',
        hovertemplate='%{x}<br>Case Ord: %{y:,.2f} MSEK<extra></extra>',
    ))
    fig.add_trace(go.Bar(
        x=hy_df['Period'], y=hy_df['Case Tail'],
        name='Case Tail', marker_color=CLR_CASE_TAIL, offsetgroup='case',
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
            title='Return (MSEK)',
            showgrid=True,
            gridcolor=COLORS['bg_subtle'],
        ),
        legend=dict(
            orientation='h', yanchor='bottom', y=1.02, xanchor='left', x=0,
        ),
        bargroupgap=0.15,
    )

    st.plotly_chart(fig, width='stretch', key="m3_return_halfyear_chart")
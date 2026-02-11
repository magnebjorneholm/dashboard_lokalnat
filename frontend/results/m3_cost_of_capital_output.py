"""
M3 Cost of Capital - Output Display

Displays WACC calculation chain based on input method:
- "capm": Full chain 3.1.X (base) -> 3.2.X (derived) -> WACC
- "derived": Partial chain 3.2.X (derived) -> WACC
- "direct" or "baseline": Only final WACC (3.2.5)

Also displays return on capital by category (30.1.X).

Variable-IDs:
- 3.1.X: CAPM base parameters
- 3.2.X: Derived WACC values
- 30.1.X: Return on capital by category (ord/tail)
- 30.2.5: Network loss adjustment
- 30.3.5: Utilization rate adjustment
- 30.4.59: Quality adjustment
- 30.5.2: Total incentive adjustment
"""

import streamlit as st
import pandas as pd
from typing import Dict, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from pipeline.core import PipelineResult

from frontend.common.asset_categories import ASSET_CATEGORIES, CATEGORY_BY_CODE
from frontend.common.result_helpers import (
    TIME_LABELS, TOLERANCE,
    load_baseline_category_data, get_case_category_data,
    fmt_tkr as _format_tkr,
    fmt_percent, fmt_number as _format_number,
    calc_delta as _calc_delta,
)
from config.column_names import (
    COL_NETLOSS_INCENTIVE, COL_LOAD_INCENTIVE, COL_QUALITY_INCENTIVE,
    COL_INCENTIVE_TOTAL, COL_MISSING_INCENTIVE,
)


# Baseline values for comparison
BASELINE_CAPM = {
    "debt_ratio": 0.36,
    "asset_beta": 0.37,
    "risk_free_rate": 0.0287,
    "market_risk_premium": 0.0668,
    "credit_risk_premium": 0.0114,
    "tax_rate": 0.206,
    "inflation": 0.0202,
}

BASELINE_DERIVED = {
    "equity_beta": 0.54,
    "cost_of_equity_nominal": 0.0645,
    "cost_of_debt_nominal": 0.0401,
    "wacc_nominal_pre_tax": 0.0664,
    "wacc_real_pre_tax": 0.0453,
}

from calculations.wacc_calculations import BASELINE_WACC


def _format_percent(value: float, decimals: int = 2) -> str:
    """Wrapper: formats decimal (0.0453) as '4.53%'."""
    return fmt_percent(value, decimals=decimals, from_decimal=True)


def render(
    case: "PipelineResult",
    baseline: "PipelineResult",
    ui_config: Dict[str, Any]
) -> None:
    """Render M3 cost of capital outputs (legacy -- calls both sub-renders)."""
    # WACC + Return section now in m3_return_output.py
    from frontend.results.m3_return_output import render as render_return
    render_return(case, baseline, ui_config)
    st.divider()
    # Incentive section remains here
    render_incentives(case, baseline, ui_config)


def render_incentives(
    case: "PipelineResult",
    baseline: "PipelineResult",
    ui_config: Dict[str, Any]
) -> None:
    """Render M3 incentive adjustment outputs (30.2-30.5).

    Public entry point so 2_results.py can call WACC and incentives separately.
    """
    case_ir = case.post_dea.user_revenue_frame
    baseline_ir = baseline.post_dea.user_revenue_frame

    case_incentive_details = getattr(case.post_dea, 'user_incentive_details', None)
    baseline_incentive_details = getattr(baseline.post_dea, 'user_incentive_details', None)

    # === INCENTIVE ADJUSTMENTS SECTION ===
    _render_incentive_section(case_ir, baseline_ir)

    st.divider()

    # === DETAILED INCENTIVE BREAKDOWN ===
    _render_incentive_detailed(case_incentive_details, baseline_incentive_details)


def _get_variable_id_return(cat_encode: int, component: str = "ord") -> str:
    """Get M3 Variable-ID for return from cat_encode. cat_encode 1 -> 30.1.2.1 (ord) or 30.1.2.2 (tail)"""
    suffix = "1" if component == "ord" else "2"
    return f"30.{cat_encode + 1}.{suffix}"


def _aggregate_return_to_period(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate half-year data to period totals for return values."""
    if df is None or df.empty:
        return pd.DataFrame()
    
    agg_cols = {}
    for col in ['return_ord', 'return_tail']:
        if col in df.columns:
            agg_cols[col] = 'sum'
    
    if not agg_cols:
        return pd.DataFrame()
    
    agg_df = df.groupby('cat_encode').agg(agg_cols).reset_index()
    
    for col in ['return_ord', 'return_tail']:
        if col not in agg_df.columns:
            agg_df[col] = 0.0
    
    agg_df['return_total'] = agg_df['return_ord'] + agg_df['return_tail']
    
    return agg_df


def _aggregate_return_to_half_years(df: pd.DataFrame) -> pd.DataFrame:
    """Keep half-year breakdown per category with return values."""
    if df is None or df.empty:
        return pd.DataFrame()
    
    result = df.copy()
    result['time_label'] = result['time'].map(TIME_LABELS)
    
    for col in ['return_ord', 'return_tail']:
        if col not in result.columns:
            result[col] = 0.0
    
    result['return_total'] = result['return_ord'] + result['return_tail']
    
    return result


def _build_return_comparison_table(
    case_period: pd.DataFrame,
    baseline_period: pd.DataFrame
) -> pd.DataFrame:
    """Build comparison table: Case vs Baseline return per category."""
    rows = []
    
    for cat in ASSET_CATEGORIES:
        cat_encode = cat.cat_encode
        var_id_ord = _get_variable_id_return(cat_encode, "ord")
        var_id_tail = _get_variable_id_return(cat_encode, "tail")
        
        # Case values
        case_row = case_period[case_period['cat_encode'] == cat_encode] if not case_period.empty else pd.DataFrame()
        if not case_row.empty:
            c_ord = case_row['return_ord'].iloc[0]
            c_tail = case_row['return_tail'].iloc[0]
            c_total = case_row['return_total'].iloc[0]
        else:
            c_ord = c_tail = c_total = 0.0
        
        # Baseline values
        base_row = baseline_period[baseline_period['cat_encode'] == cat_encode] if not baseline_period.empty else pd.DataFrame()
        if not base_row.empty:
            b_ord = base_row['return_ord'].iloc[0]
            b_tail = base_row['return_tail'].iloc[0]
            b_total = base_row['return_total'].iloc[0]
        else:
            b_ord = b_tail = b_total = 0.0
        
        # Skip categories where both case and baseline are below tolerance
        if abs(c_total) < TOLERANCE and abs(b_total) < TOLERANCE:
            continue
        
        rows.append({
            'Var-ID': f"{var_id_ord}/{var_id_tail}",
            'Category': cat.name,
            'C Ord': c_ord,
            'C Tail': c_tail,
            'C Total': c_total,
            'BL Ord': b_ord,
            'BL Tail': b_tail,
            'BL Total': b_total,
        })
    
    return pd.DataFrame(rows)


def _build_return_halfyear_table(
    case_hy: pd.DataFrame,
    baseline_hy: pd.DataFrame,
    cat_encode: int
) -> pd.DataFrame:
    """Build half-year return comparison for a single category."""
    rows = []
    
    for time_code, label in TIME_LABELS.items():
        # Case
        case_row = case_hy[(case_hy['cat_encode'] == cat_encode) & (case_hy['time'] == time_code)] if not case_hy.empty else pd.DataFrame()
        if not case_row.empty:
            c_ord = case_row['return_ord'].iloc[0]
            c_tail = case_row['return_tail'].iloc[0]
            c_total = case_row['return_total'].iloc[0]
        else:
            c_ord = c_tail = c_total = 0.0
        
        # Baseline
        base_row = baseline_hy[(baseline_hy['cat_encode'] == cat_encode) & (baseline_hy['time'] == time_code)] if not baseline_hy.empty else pd.DataFrame()
        if not base_row.empty:
            b_ord = base_row['return_ord'].iloc[0]
            b_tail = base_row['return_tail'].iloc[0]
            b_total = base_row['return_total'].iloc[0]
        else:
            b_ord = b_tail = b_total = 0.0
        
        rows.append({
            'Period': label,
            'C Ord': c_ord,
            'C Tail': c_tail,
            'C Total': c_total,
            'BL Ord': b_ord,
            'BL Tail': b_tail,
            'BL Total': b_total,
        })
    
    return pd.DataFrame(rows)


def _render_return_by_category(case: "PipelineResult", user_id_network: Optional[int]) -> None:
    """Render return on capital by category section."""
    st.markdown("**30.1 Return on Capital by Category**")
    
    if user_id_network is None:
        st.warning("User company not identified.")
        return
    
    baseline_cat = load_baseline_category_data(user_id_network)
    case_cat = get_case_category_data(case, user_id_network)
    
    if baseline_cat is None or baseline_cat.empty:
        st.info(
            "Baseline category data not available. "
            "Ensure capcost_a.parquet is in the data/ directory."
        )
        return
    
    if case_cat is None or case_cat.empty:
        case_cat = baseline_cat.copy()
        st.caption("Case uses baseline values (no parameter changes applied to category data).")
    
    case_period = _aggregate_return_to_period(case_cat)
    baseline_period = _aggregate_return_to_period(baseline_cat)
    case_hy = _aggregate_return_to_half_years(case_cat)
    baseline_hy = _aggregate_return_to_half_years(baseline_cat)
    
    # Total return section
    c_ord = case_period['return_ord'].sum() if not case_period.empty else 0
    c_tail = case_period['return_tail'].sum() if not case_period.empty else 0
    c_total = c_ord + c_tail
    
    b_ord = baseline_period['return_ord'].sum() if not baseline_period.empty else 0
    b_tail = baseline_period['return_tail'].sum() if not baseline_period.empty else 0
    b_total = b_ord + b_tail
    
    st.caption("Period sum (tkr / 1000 = MSEK)")
    
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    with col1:
        st.metric("Case Ord", f"{c_ord/1e3:,.1f} MSEK")
    with col2:
        st.metric("Case Tail", f"{c_tail/1e3:,.1f} MSEK")
    with col3:
        st.metric("Case Total", f"{c_total/1e3:,.1f} MSEK")
    with col4:
        st.metric("BL Ord", f"{b_ord/1e3:,.1f} MSEK")
    with col5:
        st.metric("BL Tail", f"{b_tail/1e3:,.1f} MSEK")
    with col6:
        st.metric("BL Total", f"{b_total/1e3:,.1f} MSEK")
    
    # Category table
    st.markdown("**30.1.2-30.1.18 Return by Category**")
    comparison_df = _build_return_comparison_table(case_period, baseline_period)
    
    if comparison_df.empty:
        st.info("No category data available for this company.")
    else:
        st.caption("All values in tkr. C=Case, BL=Baseline")
        st.dataframe(
            comparison_df,
            hide_index=True,
            width='stretch',
            column_config={
                'Var-ID': st.column_config.TextColumn('ID', width='small'),
                'Category': st.column_config.TextColumn('Category', width='large'),
                'C Ord': st.column_config.NumberColumn('C Ord', format='%.0f'),
                'C Tail': st.column_config.NumberColumn('C Tail', format='%.0f'),
                'C Total': st.column_config.NumberColumn('C Total', format='%.0f'),
                'BL Ord': st.column_config.NumberColumn('BL Ord', format='%.0f'),
                'BL Tail': st.column_config.NumberColumn('BL Tail', format='%.0f'),
                'BL Total': st.column_config.NumberColumn('BL Total', format='%.0f'),
            }
        )
    
    # Half-year breakdown expander
    with st.expander("Per-half-year breakdown by category", expanded=False):
        st.caption("Select a category (values in tkr):")
        
        cat_names = [cat.name for cat in ASSET_CATEGORIES]
        selected_name = st.selectbox(
            "Category",
            options=cat_names,
            key="m3_halfyear_cat_select",
            label_visibility="collapsed"
        )
        
        selected_cat = next((c for c in ASSET_CATEGORIES if c.name == selected_name), None)
        if selected_cat:
            hy_table = _build_return_halfyear_table(case_hy, baseline_hy, selected_cat.cat_encode)
            
            if not hy_table.empty:
                st.dataframe(
                    hy_table,
                    hide_index=True,
                    width='stretch',
                    column_config={
                        'Period': st.column_config.TextColumn('Period', width='small'),
                        'C Ord': st.column_config.NumberColumn('C Ord', format='%.0f'),
                        'C Tail': st.column_config.NumberColumn('C Tail', format='%.0f'),
                        'C Total': st.column_config.NumberColumn('C Total', format='%.0f'),
                        'BL Ord': st.column_config.NumberColumn('BL Ord', format='%.0f'),
                        'BL Tail': st.column_config.NumberColumn('BL Tail', format='%.0f'),
                        'BL Total': st.column_config.NumberColumn('BL Total', format='%.0f'),
                    }
                )
            else:
                st.info("No data available for this category.")


def _render_wacc_section(
    wacc_input_method: str,
    wacc_inputs: dict,
    wacc_derived: dict,
    wacc_case: float
) -> None:
    """Render WACC parameters based on input method."""
    
    st.markdown("**WACC Parameters**")
    
    method_labels = {
        "capm": "CAPM (base parameters)",
        "derived": "Derived parameters",
        "direct": "Direct input",
        "baseline": "Baseline",
    }
    st.caption(f"Input method: {method_labels.get(wacc_input_method, wacc_input_method)}")
    
    # === CAPM: Show 3.1.X base parameters ===
    if wacc_input_method == "capm" and wacc_inputs:
        st.markdown("##### 3.1 Base Parameters")
        
        capm_params = [
            ("3.1.1", "Debt ratio (S)", "debt_ratio", "ratio"),
            ("3.1.2", "Asset beta", "asset_beta", "ratio"),
            ("3.1.3", "Risk-free rate (Rf)", "risk_free_rate", "percent"),
            ("3.1.4", "Market risk premium", "market_risk_premium", "percent"),
            ("3.1.5", "Credit risk premium", "credit_risk_premium", "percent"),
            ("3.1.6", "Tax rate (tau)", "tax_rate", "percent"),
            ("3.1.7", "Inflation (pi)", "inflation", "percent"),
        ]
        
        capm_rows = []
        for var_id, label, key, fmt in capm_params:
            case_val = wacc_inputs.get(key, BASELINE_CAPM[key])
            baseline_val = BASELINE_CAPM[key]
            delta, _ = _calc_delta(case_val, baseline_val)
            
            if fmt == "percent":
                case_str = _format_percent(case_val, 2)
                baseline_str = _format_percent(baseline_val, 2)
                delta_str = f"{delta*100:+.2f} pp" if delta and abs(delta) > 0.0001 else "-"
            else:
                case_str = _format_number(case_val, 2)
                baseline_str = _format_number(baseline_val, 2)
                delta_str = f"{delta:+.2f}" if delta and abs(delta) > 0.001 else "-"
            
            capm_rows.append({
                "ID": var_id,
                "Parameter": label,
                "Case": case_str,
                "Baseline": baseline_str,
                "Delta": delta_str,
            })
        
        st.dataframe(pd.DataFrame(capm_rows), hide_index=True, width='stretch')
        st.markdown("")
    
    # === CAPM or DERIVED: Show 3.2.X derived values ===
    if wacc_input_method in ["capm", "derived"] and wacc_derived:
        st.markdown("##### 3.2 Derived Values")
        
        derived_params = [
            ("3.2.1", "Equity beta", "equity_beta", "ratio"),
            ("3.2.2", "Cost of equity (Re)", "cost_of_equity_nominal", "percent"),
            ("3.2.3", "Cost of debt (Rd)", "cost_of_debt_nominal", "percent"),
            ("3.2.4", "WACC nominal pre-tax", "wacc_nominal_pre_tax", "percent"),
            ("3.2.5", "WACC real pre-tax", "wacc_real_pre_tax", "percent"),
        ]
        
        derived_rows = []
        for var_id, label, key, fmt in derived_params:
            case_val = wacc_derived.get(key)
            baseline_val = BASELINE_DERIVED.get(key)
            
            if case_val is None or baseline_val is None:
                continue
            
            delta, _ = _calc_delta(case_val, baseline_val)
            
            if fmt == "percent":
                case_str = _format_percent(case_val, 2)
                baseline_str = _format_percent(baseline_val, 2)
                delta_str = f"{delta*100:+.2f} pp" if delta and abs(delta) > 0.0001 else "-"
            else:
                case_str = _format_number(case_val, 2)
                baseline_str = _format_number(baseline_val, 2)
                delta_str = f"{delta:+.2f}" if delta and abs(delta) > 0.001 else "-"
            
            derived_rows.append({
                "ID": var_id,
                "Parameter": label,
                "Case": case_str,
                "Baseline": baseline_str,
                "Delta": delta_str,
            })
        
        st.dataframe(pd.DataFrame(derived_rows), hide_index=True, width='stretch')
    
    # === DIRECT or BASELINE: Show only final WACC ===
    elif wacc_input_method in ["direct", "baseline"]:
        st.markdown("##### 3.2.5 WACC (real, pre-tax)")
        
        wacc_delta = wacc_case - BASELINE_WACC
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric(
                "Applied WACC",
                _format_percent(wacc_case, 2),
                delta=f"{wacc_delta*100:+.2f} pp" if abs(wacc_delta) > 0.0001 else None
            )
        with col2:
            st.metric("Baseline WACC", _format_percent(BASELINE_WACC, 2))


def _render_incentive_section(case_ir: pd.Series, baseline_ir: pd.Series) -> None:
    """Render incentive adjustments summary."""
    
    st.markdown("**Incentive Adjustments**")
    
    inc_components = [
        ("30.2.5", "Network loss adjustment", COL_NETLOSS_INCENTIVE),
        ("30.3.5", "Utilization rate adjustment", COL_LOAD_INCENTIVE),
        ("30.4.59", "Quality adjustment", COL_QUALITY_INCENTIVE),
    ]
    
    inc_rows = []
    for var_id, label, col_key in inc_components:
        c_val = case_ir.get(col_key, 0)
        b_val = baseline_ir.get(col_key, 0)
        delta_abs, _ = _calc_delta(c_val, b_val)
        inc_rows.append({
            "ID": var_id,
            "Component": label,
            "Case (tkr)": _format_tkr(c_val, show_sign=True),
            "Baseline (tkr)": _format_tkr(b_val, show_sign=True),
            "Delta (tkr)": _format_tkr(delta_abs, show_sign=True) if delta_abs is not None else "-",
        })
    
    # Total row
    total_case = case_ir.get(COL_INCENTIVE_TOTAL, 0)
    total_baseline = baseline_ir.get(COL_INCENTIVE_TOTAL, 0)
    total_delta, _ = _calc_delta(total_case, total_baseline)
    inc_rows.append({
        "ID": "30.5.2",
        "Component": "Total incentive adjustment",
        "Case (tkr)": _format_tkr(total_case, show_sign=True),
        "Baseline (tkr)": _format_tkr(total_baseline, show_sign=True),
        "Delta (tkr)": _format_tkr(total_delta, show_sign=True) if total_delta is not None else "-",
    })
    
    st.dataframe(pd.DataFrame(inc_rows), hide_index=True, width='stretch')
    
    if case_ir.get(COL_MISSING_INCENTIVE, False):
        st.warning("Incentive data incomplete for this company.")


def _render_incentive_detailed(
    case_details: Optional[pd.DataFrame],
    baseline_details: Optional[pd.DataFrame]
) -> None:
    """Render detailed per-year incentive breakdown (User Manual Table 10)."""
    
    st.markdown("**Detailed Incentive Breakdown**")
    
    if case_details is None:
        st.info("Detailed incentive data not available.")
        return
    
    # === Per-year main outputs (30.2.4/5, 30.3.4/5, 30.4.57/58/59, 30.5.1/2) ===
    with st.expander("30.2-30.5 Per-year incentive outputs", expanded=True):
        _render_peryear_table(case_details, baseline_details)
    
    # === AIT/AIF per customer type breakdown ===
    with st.expander("Quality incentive by customer type (AIT/AIF)", expanded=False):
        _render_ait_aif_breakdown(case_details, baseline_details)


def _render_peryear_table(
    case_df: pd.DataFrame,
    baseline_df: Optional[pd.DataFrame]
) -> None:
    """Render per-year breakdown table for main incentive variables."""
    
    # Variable-ID mapping for User Manual Table 10
    var_id_map = {
        'loss_incentive_a': '30.2.4',
        'loss_incentive': '30.2.5',
        'util_incentive_a': '30.3.4',
        'util_incentive': '30.3.5',
        'inc_inter': '30.4.57',
        'inter_incentive_a': '30.4.58',
        'inter_incentive': '30.4.59',
        'total_before_agg_cap': '30.5.1',
        'incentive_total_year': '30.5.2',
    }
    
    label_map = {
        'loss_incentive_a': 'Network loss (before cap)',
        'loss_incentive': 'Network loss (after cap)',
        'util_incentive_a': 'Utilization (before cap)',
        'util_incentive': 'Utilization (after cap)',
        'inc_inter': 'Quality (before CEMI4)',
        'inter_incentive_a': 'Quality (after CEMI4)',
        'inter_incentive': 'Quality (after cap)',
        'total_before_agg_cap': 'Total (before agg cap)',
        'incentive_total_year': 'Total (after agg cap)',
    }
    
    # Get year rows (exclude Total row for per-year display)
    case_years = case_df[case_df['year'] != 'Total']
    case_total = case_df[case_df['year'] == 'Total']
    
    baseline_total = None
    if baseline_df is not None and not baseline_df.empty:
        baseline_total = baseline_df[baseline_df['year'] == 'Total']
    
    # Build table: rows = variables, columns = years + totals
    rows = []
    for col_name, var_id in var_id_map.items():
        if col_name not in case_df.columns:
            continue
        
        row = {
            'Var-ID': var_id,
            'Description': label_map.get(col_name, col_name),
        }
        
        # Add Case values for each year
        for _, data_row in case_years.iterrows():
            year = data_row['year']
            val = data_row.get(col_name, 0)
            val_tkr = val / 1000 if pd.notna(val) else 0
            row[f'{year}'] = val_tkr
        
        # Add Case Total
        if not case_total.empty:
            case_tot_val = case_total.iloc[0].get(col_name, 0)
            row['Case Total'] = case_tot_val / 1000 if pd.notna(case_tot_val) else 0
        else:
            row['Case Total'] = 0
        
        # Add Baseline Total and Delta
        if baseline_total is not None and not baseline_total.empty and col_name in baseline_total.columns:
            bl_tot_val = baseline_total.iloc[0].get(col_name, 0)
            bl_tkr = bl_tot_val / 1000 if pd.notna(bl_tot_val) else 0
            row['BL Total'] = bl_tkr
            row['Delta'] = row['Case Total'] - bl_tkr
        else:
            row['BL Total'] = row['Case Total']  # Same as case if no baseline
            row['Delta'] = 0
        
        rows.append(row)
    
    if not rows:
        st.warning("No incentive detail columns available.")
        return
    
    df_display = pd.DataFrame(rows)
    
    st.caption("Values in tkr. Positive = revenue increase, negative = revenue decrease.")
    
    # Configure columns
    column_config = {
        'Var-ID': st.column_config.TextColumn('ID', width='small'),
        'Description': st.column_config.TextColumn('Description', width='medium'),
    }
    
    # Add year columns and totals
    for col in df_display.columns:
        if col not in ['Var-ID', 'Description']:
            column_config[col] = st.column_config.NumberColumn(col, format='%.1f')
    
    st.dataframe(
        df_display,
        hide_index=True,
        width='stretch',
        column_config=column_config
    )
    
    # Show cap info
    if 'max_adj' in case_df.columns and 'ret_period' in case_df.columns:
        with st.expander("Cap calculation reference", expanded=False):
            cap_rows = []
            for _, data_row in case_df.iterrows():
                year = data_row['year']
                ret = data_row.get('ret_period', 0)
                max_adj = data_row.get('max_adj', 0)
                cap_rows.append({
                    'Year': year,
                    'Return (tkr)': ret / 1000 if pd.notna(ret) else 0,
                    'Max adj (tkr)': max_adj / 1000 if pd.notna(max_adj) else 0,
                })
            st.dataframe(pd.DataFrame(cap_rows), hide_index=True, width='stretch')


def _render_ait_aif_breakdown(
    case_df: pd.DataFrame,
    baseline_df: Optional[pd.DataFrame]
) -> None:
    """Render AIT/AIF breakdown per customer type."""
    
    # Customer type labels (SNI codes)
    sni_labels = {
        1: 'Agriculture',
        2: 'Industry',
        3: 'Trade/Services',
        4: 'Public sector',
        5: 'Household',
        6: 'Boundary points',
    }
    
    # Check if AIT/AIF columns exist
    ait_cols = [c for c in case_df.columns if c.startswith('inc_ait_')]
    aif_cols = [c for c in case_df.columns if c.startswith('inc_aif_')]
    
    if not ait_cols and not aif_cols:
        st.info("AIT/AIF per customer type data not available.")
        return
    
    st.caption("Values in tkr. No Variable-ID assigned in User Manual.")
    
    # === AIT Breakdown ===
    if ait_cols:
        st.markdown("**AIT (Average Interruption Time)**")
        _render_indicator_table(case_df, baseline_df, 'ait', sni_labels)
    
    # === AIF Breakdown ===
    if aif_cols:
        st.markdown("**AIF (Average Interruption Frequency)**")
        _render_indicator_table(case_df, baseline_df, 'aif', sni_labels)


def _render_indicator_table(
    case_df: pd.DataFrame,
    baseline_df: Optional[pd.DataFrame],
    indicator: str,  # 'ait' or 'aif'
    sni_labels: dict
) -> None:
    """Render AIT or AIF table by customer type and planned/unplanned."""
    
    # Get year rows (exclude Total row for per-year display)
    case_years = case_df[case_df['year'] != 'Total']
    case_total = case_df[case_df['year'] == 'Total']
    
    baseline_total = None
    if baseline_df is not None and not baseline_df.empty:
        baseline_total = baseline_df[baseline_df['year'] == 'Total']
    
    rows = []
    
    for ann, ann_label in [('o', 'Unplanned'), ('a', 'Planned')]:
        for sni in range(1, 7):
            col_name = f'inc_{indicator}_{ann}_{sni}'
            if col_name not in case_df.columns:
                continue
            
            row = {
                'Var-ID': '',  # No Variable-ID in User Manual
                'Type': ann_label,
                'Customer': sni_labels.get(sni, f'SNI {sni}'),
            }
            
            # Add Case values for each year
            for _, data_row in case_years.iterrows():
                year = data_row['year']
                val = data_row.get(col_name, 0)
                val_tkr = val / 1000 if pd.notna(val) else 0
                row[f'{year}'] = val_tkr
            
            # Add Case Total
            if not case_total.empty:
                case_tot_val = case_total.iloc[0].get(col_name, 0)
                row['Case Total'] = case_tot_val / 1000 if pd.notna(case_tot_val) else 0
            else:
                row['Case Total'] = 0
            
            # Add Baseline Total and Delta
            if baseline_total is not None and not baseline_total.empty and col_name in baseline_total.columns:
                bl_tot_val = baseline_total.iloc[0].get(col_name, 0)
                bl_tkr = bl_tot_val / 1000 if pd.notna(bl_tot_val) else 0
                row['BL Total'] = bl_tkr
                row['Delta'] = row['Case Total'] - bl_tkr
            else:
                row['BL Total'] = row['Case Total']
                row['Delta'] = 0
            
            rows.append(row)
    
    if not rows:
        return
    
    df_display = pd.DataFrame(rows)
    
    column_config = {
        'Var-ID': st.column_config.TextColumn('ID', width='small'),
        'Type': st.column_config.TextColumn('Type', width='small'),
        'Customer': st.column_config.TextColumn('Customer', width='medium'),
    }
    
    for col in df_display.columns:
        if col not in ['Var-ID', 'Type', 'Customer']:
            column_config[col] = st.column_config.NumberColumn(col, format='%.1f')
    
    st.dataframe(
        df_display,
        hide_index=True,
        width='stretch',
        column_config=column_config
    )
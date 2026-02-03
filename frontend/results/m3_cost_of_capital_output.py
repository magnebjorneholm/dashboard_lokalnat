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

# Time code to label mapping
TIME_LABELS = {
    229: "2024H1", 230: "2024H2",
    231: "2025H1", 232: "2025H2",
    233: "2026H1", 234: "2026H2",
    235: "2027H1", 236: "2027H2",
}

TOLERANCE = 0.01  # tkr - threshold for filtering zero categories


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

BASELINE_WACC = 0.0453


def _format_tkr(value: float, show_sign: bool = False) -> str:
    if pd.isna(value):
        return "-"
    if show_sign and value > 0:
        return f"+{value:,.0f}"
    return f"{value:,.0f}"


def _format_percent(value: float, decimals: int = 2) -> str:
    if pd.isna(value):
        return "-"
    return f"{value*100:.{decimals}f}%"


def _format_number(value: float, decimals: int = 4) -> str:
    if pd.isna(value):
        return "-"
    return f"{value:.{decimals}f}"


def _calc_delta(case_val: float, baseline_val: float) -> tuple:
    if pd.isna(case_val) or pd.isna(baseline_val):
        return None, None
    delta_abs = case_val - baseline_val
    delta_pct = (delta_abs / baseline_val * 100) if baseline_val != 0 else 0
    return delta_abs, delta_pct


def render(
    case: "PipelineResult",
    baseline: "PipelineResult",
    ui_config: Dict[str, Any]
) -> None:
    """Render M3 cost of capital outputs."""
    
    case_ir = case.post_dea.user_intaktsram
    baseline_ir = baseline.post_dea.user_intaktsram
    
    # Get WACC chain info from pre_dea
    wacc_input_method = getattr(case.pre_dea, 'wacc_input_method', 'baseline')
    wacc_inputs = getattr(case.pre_dea, 'wacc_inputs', None)
    wacc_derived = getattr(case.pre_dea, 'wacc_derived', None)
    wacc_case = case.pre_dea.wacc_used or BASELINE_WACC
    user_id_network = getattr(case.pre_dea, 'user_id_network', None)
    
    # === WACC SECTION ===
    _render_wacc_section(wacc_input_method, wacc_inputs, wacc_derived, wacc_case)
    
    st.divider()
    
    # === RETURN BY CATEGORY SECTION ===
    _render_return_by_category(case, user_id_network)
    
    st.divider()
    
    # === INCENTIVE ADJUSTMENTS SECTION ===
    _render_incentive_section(case_ir, baseline_ir)
    
    st.divider()
    
    # === FUTURE: DETAILED INCENTIVE BREAKDOWN ===
    _render_incentive_placeholder()


def _get_variable_id_return(cat_encode: int, component: str = "ord") -> str:
    """Get M3 Variable-ID for return from cat_encode. cat_encode 1 -> 30.1.2.1 (ord) or 30.1.2.2 (tail)"""
    suffix = "1" if component == "ord" else "2"
    return f"30.{cat_encode + 1}.{suffix}"


def _load_baseline_category_data(user_id_network: int) -> Optional[pd.DataFrame]:
    """Load baseline category data for user's company."""
    try:
        from data_loaders.rab_data import load_capcost_a
        df = load_capcost_a()
        return df[df['id_network'] == user_id_network].copy()
    except (FileNotFoundError, ImportError):
        return None


def _get_case_category_data(
    case: "PipelineResult", 
    user_id_network: int
) -> Optional[pd.DataFrame]:
    """Get case category data from pipeline result."""
    df_cat = getattr(case.pre_dea, 'df_by_category', None)
    if df_cat is None:
        return None
    return df_cat[df_cat['id_network'] == user_id_network].copy()


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
    
    baseline_cat = _load_baseline_category_data(user_id_network)
    case_cat = _get_case_category_data(case, user_id_network)
    
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
            use_container_width=True,
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
                    use_container_width=True,
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
        
        st.dataframe(pd.DataFrame(capm_rows), hide_index=True, use_container_width=True)
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
        
        st.dataframe(pd.DataFrame(derived_rows), hide_index=True, use_container_width=True)
    
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
        ("30.2.5", "Network loss adjustment", "Natforlustjustering_Total"),
        ("30.3.5", "Utilization rate adjustment", "Belastningsjustering_Total"),
        ("30.4.59", "Quality adjustment", "Kvalitetsjustering_Total"),
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
    total_case = case_ir.get("Incitamentjustering_Total", 0)
    total_baseline = baseline_ir.get("Incitamentjustering_Total", 0)
    total_delta, _ = _calc_delta(total_case, total_baseline)
    inc_rows.append({
        "ID": "30.5.2",
        "Component": "Total incentive adjustment",
        "Case (tkr)": _format_tkr(total_case, show_sign=True),
        "Baseline (tkr)": _format_tkr(total_baseline, show_sign=True),
        "Delta (tkr)": _format_tkr(total_delta, show_sign=True) if total_delta is not None else "-",
    })
    
    st.dataframe(pd.DataFrame(inc_rows), hide_index=True, use_container_width=True)
    
    if case_ir.get('Missing_Incentive_Data', False):
        st.warning("Incentive data incomplete for this company.")


def _render_incentive_placeholder() -> None:
    """Placeholder for detailed incentive breakdown (future feature)."""
    
    with st.expander("Detailed incentive breakdown", expanded=False):
        st.info(
            "Detailed per-year and per-component incentive breakdown will be added in a future update. "
            "This will include:\n"
            "- Per-year breakdown of quality, network loss, and utilization adjustments\n"
            "- CEMI4, AIT, and AIF component details\n"
            "- Norm vs. observed values comparison"
        )
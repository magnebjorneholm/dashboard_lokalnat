"""
M1 Regulatory Asset Base Valuation - Output Display

Variable-IDs: 11.1 (total), 11.2-11.18 (per category)
Displays NUAV (nuanskaffningsvarde) for ordinary and tail components.

This module shows ONLY NUAV values. Depreciation is in M2, Return is in M3.
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


def _get_variable_id(cat_encode: int) -> str:
    """Get M1 Variable-ID from cat_encode. cat_encode 1 -> 11.2"""
    return f"11.{cat_encode + 1}"


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


def _aggregate_to_period(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate half-year data to period totals per category.
    Returns NUAV values (ord, tail, total) per category.
    """
    if df is None or df.empty:
        return pd.DataFrame()
    
    agg_cols = {}
    for col in ['nuav_ord', 'nuav_tail']:
        if col in df.columns:
            agg_cols[col] = 'sum'
    
    if not agg_cols:
        return pd.DataFrame()
    
    agg_df = df.groupby('cat_encode').agg(agg_cols).reset_index()
    
    for col in ['nuav_ord', 'nuav_tail']:
        if col not in agg_df.columns:
            agg_df[col] = 0.0
    
    agg_df['nuav_total'] = agg_df['nuav_ord'] + agg_df['nuav_tail']
    
    return agg_df


def _aggregate_to_half_years(df: pd.DataFrame) -> pd.DataFrame:
    """Keep half-year breakdown per category with NUAV values."""
    if df is None or df.empty:
        return pd.DataFrame()
    
    result = df.copy()
    result['time_label'] = result['time'].map(TIME_LABELS)
    
    for col in ['nuav_ord', 'nuav_tail']:
        if col not in result.columns:
            result[col] = 0.0
    
    result['nuav_total'] = result['nuav_ord'] + result['nuav_tail']
    
    return result


def _build_comparison_table(
    case_period: pd.DataFrame,
    baseline_period: pd.DataFrame
) -> pd.DataFrame:
    """
    Build comparison table: Case vs Baseline NUAV per category.
    Only includes categories where case OR baseline has data above tolerance.
    """
    rows = []
    
    for cat in ASSET_CATEGORIES:
        cat_encode = cat.cat_encode
        var_id = _get_variable_id(cat_encode)
        
        # Case values
        case_row = case_period[case_period['cat_encode'] == cat_encode] if not case_period.empty else pd.DataFrame()
        if not case_row.empty:
            c_ord = case_row['nuav_ord'].iloc[0]
            c_tail = case_row['nuav_tail'].iloc[0]
            c_total = case_row['nuav_total'].iloc[0]
        else:
            c_ord = c_tail = c_total = 0.0
        
        # Baseline values
        base_row = baseline_period[baseline_period['cat_encode'] == cat_encode] if not baseline_period.empty else pd.DataFrame()
        if not base_row.empty:
            b_ord = base_row['nuav_ord'].iloc[0]
            b_tail = base_row['nuav_tail'].iloc[0]
            b_total = base_row['nuav_total'].iloc[0]
        else:
            b_ord = b_tail = b_total = 0.0
        
        # Skip categories where both case and baseline are below tolerance
        if abs(c_total) < TOLERANCE and abs(b_total) < TOLERANCE:
            continue
        
        rows.append({
            'Var-ID': var_id,
            'Category': cat.name,
            'C Ord': c_ord,
            'C Tail': c_tail,
            'C Total': c_total,
            'BL Ord': b_ord,
            'BL Tail': b_tail,
            'BL Total': b_total,
        })
    
    return pd.DataFrame(rows)


def _build_halfyear_table(
    case_hy: pd.DataFrame,
    baseline_hy: pd.DataFrame,
    cat_encode: int
) -> pd.DataFrame:
    """Build half-year NUAV comparison for a single category."""
    rows = []
    
    for time_code, label in TIME_LABELS.items():
        # Case
        case_row = case_hy[(case_hy['cat_encode'] == cat_encode) & (case_hy['time'] == time_code)] if not case_hy.empty else pd.DataFrame()
        if not case_row.empty:
            c_ord = case_row['nuav_ord'].iloc[0]
            c_tail = case_row['nuav_tail'].iloc[0]
            c_total = case_row['nuav_total'].iloc[0]
        else:
            c_ord = c_tail = c_total = 0.0
        
        # Baseline
        base_row = baseline_hy[(baseline_hy['cat_encode'] == cat_encode) & (baseline_hy['time'] == time_code)] if not baseline_hy.empty else pd.DataFrame()
        if not base_row.empty:
            b_ord = base_row['nuav_ord'].iloc[0]
            b_tail = base_row['nuav_tail'].iloc[0]
            b_total = base_row['nuav_total'].iloc[0]
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


def render(
    case: "PipelineResult",
    baseline: "PipelineResult",
    ui_config: Dict[str, Any]
) -> None:
    """Render M1 asset base outputs (NUAV only)."""
    
    user_id_network = getattr(case.pre_dea, 'user_id_network', None)
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
    
    case_period = _aggregate_to_period(case_cat)
    baseline_period = _aggregate_to_period(baseline_cat)
    case_hy = _aggregate_to_half_years(case_cat)
    baseline_hy = _aggregate_to_half_years(baseline_cat)
    
    _render_total_section(case_period, baseline_period)
    st.divider()
    _render_category_section(case_period, baseline_period)
    st.divider()
    _render_halfyear_section(case_hy, baseline_hy)


def _render_total_section(case_period: pd.DataFrame, baseline_period: pd.DataFrame):
    """Render 11.1 Total NUAV values."""
    st.markdown("**11.1 Total Asset Value (NUAV)**")
    
    c_ord = case_period['nuav_ord'].sum() if not case_period.empty else 0
    c_tail = case_period['nuav_tail'].sum() if not case_period.empty else 0
    c_total = c_ord + c_tail
    
    b_ord = baseline_period['nuav_ord'].sum() if not baseline_period.empty else 0
    b_tail = baseline_period['nuav_tail'].sum() if not baseline_period.empty else 0
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


def _render_category_section(case_period: pd.DataFrame, baseline_period: pd.DataFrame):
    """Render 11.2-11.18 NUAV by category."""
    st.markdown("**11.2-11.18 NUAV by Category**")
    
    comparison_df = _build_comparison_table(case_period, baseline_period)
    
    if comparison_df.empty:
        st.info("No category data available for this company.")
        return
    
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


def _render_halfyear_section(case_hy: pd.DataFrame, baseline_hy: pd.DataFrame):
    """Render expandable half-year NUAV breakdown."""
    with st.expander("Per-half-year breakdown by category", expanded=False):
        st.caption("Select a category (values in tkr):")
        
        cat_names = [cat.name for cat in ASSET_CATEGORIES]
        selected_name = st.selectbox(
            "Category",
            options=cat_names,
            key="m1_halfyear_cat_select",
            label_visibility="collapsed"
        )
        
        selected_cat = next((c for c in ASSET_CATEGORIES if c.name == selected_name), None)
        if selected_cat is None:
            return
        
        hy_table = _build_halfyear_table(case_hy, baseline_hy, selected_cat.cat_encode)
        
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
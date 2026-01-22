"""
Module 1: Regulatory Asset Base Valuation

Handles:
- 1.1 General scaling factor (Param 1.1.1) - all companies
- 1.2 Category scaling factors (Param 1.2.1-1.2.17) - all companies
- 1.3 Asset quantities scaling (Var 10.2-10.18) - logged-in company only
- 1.4 KENT upload - logged-in company only (overrides 1.3)

Per User Manual Tables 1-3.

Section-based rendering:
- render_scaling() -> 1.1 + 1.2 (parameters)
- render_quantities() -> 1.3 (variables)
- render_kent() -> 1.4 (KENT upload)
"""

import streamlit as st
import pandas as pd
from typing import Dict, Any, Optional

from frontend.common.asset_categories import (
    ASSET_CATEGORIES,
    CATEGORY_BY_CODE,
    GENERAL_SCALING_FACTOR_BASELINE,
)

MODULE_KEY = "m1_asset_base"

# Time code for period start (2024 H1)
TIMECODE_PERIOD_START = 229


# =============================================================================
# SECTION RENDER FUNCTIONS
# =============================================================================

def render_scaling(user_id_network: Optional[int] = None) -> Dict[str, Any]:
    """
    Render M1 scaling section: 1.1 General + 1.2 Category scaling factors.
    
    These are parameters that affect ALL companies uniformly.
    
    Returns:
        Dict with general_scaling and cat_scaling
    """
    config: Dict[str, Any] = {}
    
    st.markdown("### 1. Regulatory Asset Base - Scaling Factors")
    st.caption("Parameters affecting all companies uniformly.")
    
    # === 1.1 GENERAL SCALING FACTOR ===
    general_scaling = _render_general_scaling()
    if general_scaling != GENERAL_SCALING_FACTOR_BASELINE:
        config["general_scaling"] = general_scaling
    
    # === 1.2 CATEGORY SCALING FACTORS ===
    cat_scaling = _render_category_scaling()
    if cat_scaling:
        config["cat_scaling"] = cat_scaling
    
    return config


def render_quantities(user_id_network: Optional[int] = None) -> Dict[str, Any]:
    """
    Render M1 quantities section: 1.3 Asset quantities (company-specific).
    
    These are variables that affect only the logged-in company.
    
    Returns:
        Dict with var_scaling
    """
    config: Dict[str, Any] = {}
    
    st.markdown("### 1. Regulatory Asset Base - Asset Quantities")
    st.caption("Variables affecting your company only.")
    
    if not user_id_network:
        st.info("Log in to access company-specific asset quantity adjustments.")
        return config
    
    # Check if KENT is uploaded (disables this section)
    existing_kent = st.session_state.get("ui_config", {}).get(MODULE_KEY, {}).get("kent_file_bytes")
    
    var_scaling = _render_variables_scaling(
        user_id_network,
        disabled=(existing_kent is not None)
    )
    if var_scaling:
        config["var_scaling"] = var_scaling
    
    return config


def render_kent(user_id_network: Optional[int] = None) -> Dict[str, Any]:
    """
    Render M1 KENT section: 1.4 KENT file upload.
    
    KENT upload overrides asset quantity scaling (1.3).
    Parameter scaling (1.1, 1.2) still applies.
    
    Returns:
        Dict with kent_file_bytes and kent_file_name
    """
    config: Dict[str, Any] = {}
    
    st.markdown("### 1. Regulatory Asset Base - KENT Upload")
    st.caption("Upload custom capital base data. Overrides quantity scaling.")
    
    if not user_id_network:
        st.info("Log in to upload KENT file.")
        return config
    
    kent_result = _render_kent_upload()
    if kent_result.get("kent_file_bytes") is not None:
        config["kent_file_bytes"] = kent_result["kent_file_bytes"]
        config["kent_file_name"] = kent_result["kent_file_name"]
    
    return config


def render(user_id_network: Optional[int] = None) -> Dict[str, Any]:
    """
    Legacy render function - renders all sections together.
    
    DEPRECATED: Use render_scaling(), render_quantities(), render_kent() instead.
    Kept for backward compatibility.
    """
    config: Dict[str, Any] = {}
    
    st.markdown("### 1. Regulatory Asset Base Valuation")
    
    # === 1.1 GENERAL SCALING FACTOR ===
    general_scaling = _render_general_scaling()
    if general_scaling != GENERAL_SCALING_FACTOR_BASELINE:
        config["general_scaling"] = general_scaling
    
    # === 1.2 CATEGORY SCALING FACTORS ===
    cat_scaling = _render_category_scaling()
    if cat_scaling:
        config["cat_scaling"] = cat_scaling
    
    # === 1.3 & 1.4: Company-specific sections ===
    if user_id_network:
        existing_kent = st.session_state.get("ui_config", {}).get(MODULE_KEY, {}).get("kent_file_bytes")
        
        var_scaling = _render_variables_scaling(
            user_id_network,
            disabled=(existing_kent is not None)
        )
        if var_scaling:
            config["var_scaling"] = var_scaling
        
        kent_result = _render_kent_upload()
        if kent_result.get("kent_file_bytes") is not None:
            config["kent_file_bytes"] = kent_result["kent_file_bytes"]
            config["kent_file_name"] = kent_result["kent_file_name"]
            config.pop("var_scaling", None)
    else:
        st.info("Log in to access company-specific asset quantity adjustments.")
    
    return config


# =============================================================================
# 1.1 GENERAL SCALING FACTOR
# =============================================================================

def _render_general_scaling() -> float:
    """Render general scaling factor input (Param 1.1.1)."""
    with st.expander("1.1 General scaling factor", expanded=False):
        st.caption(
            "Applied multiplicatively to all asset norm values. "
            "Affects all companies ordinarie capital base uniformly. (Parameter-ID: 1.1.1)"
        )
        
        value = st.number_input(
            "General scaling factor",
            min_value=0.5,
            max_value=2.0,
            value=1.0,
            step=0.01,
            format="%.2f",
            key=f"{MODULE_KEY}_general_scaling",
            help="1.0 = no change, 1.2 = +20%, 0.8 = -20%"
        )
        
        if value != 1.0:
            pct = (value - 1) * 100
            st.success(f"General scaling: {value:.2f} ({pct:+.0f}%)")
    
    return value


# =============================================================================
# 1.2 CATEGORY SCALING FACTORS
# =============================================================================

def _render_category_scaling() -> Optional[Dict[int, float]]:
    """Render category-level scaling factors (Param 1.2.1-1.2.17)."""
    with st.expander("1.2 Category scaling factors", expanded=False):
        st.caption(
            "Scaling factors per asset category. Affects all companies ordinarie capital base uniformly."
            "(Parameter-IDs: 1.2.1-1.2.17)"
        )
        
        # Build dataframe for editor
        data = []
        for cat in ASSET_CATEGORIES:
            data.append({
                'cat_encode': cat.cat_encode,
                'Category': cat.name,
                'Param-ID': cat.scaling_param_id,
                'Scaling': 1.0,
            })
        
        df = pd.DataFrame(data)
        
        edited_df = st.data_editor(
            df,
            width='stretch',
            hide_index=True,
            num_rows="fixed",
            disabled=['cat_encode', 'Category', 'Param-ID'],
            column_config={
                'cat_encode': st.column_config.NumberColumn(
                    'Code', format="%d", width="small"
                ),
                'Category': st.column_config.TextColumn(
                    'Category', width="large"
                ),
                'Param-ID': st.column_config.TextColumn(
                    'Param-ID', width="small"
                ),
                'Scaling': st.column_config.NumberColumn(
                    'Scaling',
                    min_value=0.5,
                    max_value=2.0,
                    step=0.01,
                    format="%.2f",
                    width="small",
                    help="1.0 = no change"
                )
            },
            key=f"{MODULE_KEY}_cat_scaling"
        )
        
        # Extract non-default values
        adjustments = {}
        for _, row in edited_df.iterrows():
            if row['Scaling'] != 1.0:
                adjustments[int(row['cat_encode'])] = float(row['Scaling'])
        
        if adjustments:
            st.success(f"{len(adjustments)} category scaling adjustment(s) active")
        
        return adjustments if adjustments else None


# =============================================================================
# 1.3 ASSET QUANTITIES (VARIABLES)
# =============================================================================

def _render_variables_scaling(
    user_id_network: int,
    disabled: bool = False
) -> Optional[Dict[int, float]]:
    """
    Render asset quantities scaling for logged-in company (Var 10.2-10.18).
    
    Shows ordinarie capital base per category with scaling option.
    """
    with st.expander("1.3 Asset quantities (company-specific)", expanded=False):
        if disabled:
            st.warning(
                "KENT file uploaded - asset quantity scaling is disabled. "
                "Remove KENT file to enable manual scaling."
            )
            return None
        
        st.caption(
            "Scale asset quantities per category for your company only. "
            "Only affects ordinaie capital base (tail is unchanged). "
            "(Variable-IDs: 10.2-10.18)"
        )
        
        # Load user's capital base data
        try:
            summary_df = _get_ordinarie_summary(user_id_network)
        except Exception as e:
            st.error(f"Could not load capital base data: {e}")
            return None
        
        if summary_df.empty:
            st.warning("No capital base data found for this company.")
            return None
        
        # Add scaling column
        summary_df['Scaling'] = 1.0
        
        edited_df = st.data_editor(
            summary_df,
            width='stretch',
            hide_index=True,
            num_rows="fixed",
            disabled=['cat_encode', 'Category', 'Var-ID', 'Components', 'NUAV (Mkr)'],
            column_config={
                'cat_encode': st.column_config.NumberColumn(
                    'Code', format="%d", width="small"
                ),
                'Category': st.column_config.TextColumn(
                    'Category', width="medium"
                ),
                'Var-ID': st.column_config.TextColumn(
                    'Var-ID', width="small"
                ),
                'Components': st.column_config.NumberColumn(
                    'Components', format="%d", width="small"
                ),
                'NUAV (Mkr)': st.column_config.NumberColumn(
                    'NUAV (Mkr)', format="%.1f", width="small"
                ),
                'Scaling': st.column_config.NumberColumn(
                    'Scaling',
                    min_value=0.5,
                    max_value=2.0,
                    step=0.01,
                    format="%.2f",
                    width="small",
                    help="1.0 = no change"
                )
            },
            key=f"{MODULE_KEY}_var_scaling"
        )
        
        # Extract non-default values
        adjustments = {}
        for _, row in edited_df.iterrows():
            if row['Scaling'] != 1.0:
                adjustments[int(row['cat_encode'])] = float(row['Scaling'])
        
        if adjustments:
            st.success(f"{len(adjustments)} variable scaling adjustment(s) active")
        
        return adjustments if adjustments else None


def _get_ordinarie_summary(user_id_network: int) -> pd.DataFrame:
    """
    Load user's capital base and return ordinarie summary per category.
    
    Ordinarie = components where age <= ekdep at period start (t=229).
    """
    from data_loaders.rab_data import load_user_capbase
    
    df = load_user_capbase(user_id_network)
    
    if df.empty:
        return pd.DataFrame()
    
    # Classify ordinarie at period start
    df = _classify_ordinarie(df)
    
    # Filter to ordinarie only
    df_ord = df[df['is_ordinarie']].copy()
    
    if df_ord.empty:
        return pd.DataFrame()
    
    # Aggregate per category
    summary = df_ord.groupby('cat_encode').agg(
        Components=('id_component', 'count'),
        NUAV_total=('nuav_2022', 'sum')
    ).reset_index()
    
    # Add category names and Variable-IDs
    summary['Category'] = summary['cat_encode'].map(
        lambda x: CATEGORY_BY_CODE[x].name if x in CATEGORY_BY_CODE else f"Unknown ({x})"
    )
    summary['Var-ID'] = summary['cat_encode'].map(
        lambda x: f"10.{x + 1}"  # 10.2 for cat_encode=1, etc.
    )
    summary['NUAV (Mkr)'] = summary['NUAV_total'] / 1_000_000
    
    # Reorder columns
    summary = summary[['cat_encode', 'Category', 'Var-ID', 'Components', 'NUAV (Mkr)']]
    summary = summary.sort_values('cat_encode').reset_index(drop=True)
    
    return summary


def _classify_ordinarie(df: pd.DataFrame) -> pd.DataFrame:
    """
    Classify components as ordinarie or tail at period start.
    
    Ordinarie: 0 < age <= ekdep (at t=229)
    Tail: ekdep < age <= maxdep
    Expired: age > maxdep
    """
    df = df.copy()
    
    # Calculate age at period start (time code 229 = 2024 H1)
    df['age_229'] = TIMECODE_PERIOD_START - df['time_from']
    
    # Check if capbase_existing column exists
    if 'capbase_existing' in df.columns:
        existing_check = (df['capbase_existing'] == 1)
    else:
        existing_check = True
    
    # Ordinarie: age > 0 and age <= ekdep, and existing asset
    df['is_ordinarie'] = (
        (df['age_229'] > 0) & 
        (df['age_229'] <= df['ekdep']) &
        existing_check
    )
    
    return df


# =============================================================================
# 1.4 KENT UPLOAD
# =============================================================================

def _render_kent_upload() -> Dict[str, Any]:
    """Render KENT file upload UI."""
    result = {
        "kent_file_bytes": None,
        "kent_file_name": None,
    }
    
    with st.expander("1.4 Upload KENT file", expanded=False):
        st.caption(
            "Upload custom capital base data from KENT. "
            "This overrides asset quantity scaling above."
        )
        
        uploaded_file = st.file_uploader(
            "KENT Excel file",
            type=["xlsx", "xls"],
            key=f"{MODULE_KEY}_kent_upload",
            help="Export from KENT regulatory template"
        )
        
        if uploaded_file is not None:
            result["kent_file_bytes"] = uploaded_file.getvalue()
            result["kent_file_name"] = uploaded_file.name
            st.success(f"KENT file loaded: {uploaded_file.name}")
            st.info(
                "KENT file will be used for capital base calculations. "
                "Parameter scaling factors (1.1, 1.2) still apply."
            )
    
    return result


# =============================================================================
# HELPER: Apply variable scaling to capbase
# =============================================================================

def apply_variable_scaling(
    capbase_df: pd.DataFrame,
    var_scaling: Dict[int, float]
) -> pd.DataFrame:
    """
    Apply variable scaling to ordinarie components only.
    
    Used by config_adapter when preparing data for calculations.
    """
    if not var_scaling:
        return capbase_df
    
    df = capbase_df.copy()
    df = _classify_ordinarie(df)
    
    for cat_encode, factor in var_scaling.items():
        mask = (df['cat_encode'] == cat_encode) & (df['is_ordinarie'])
        df.loc[mask, 'nuav_2022'] = df.loc[mask, 'nuav_2022'] * factor
    
    df = df.drop(columns=['is_ordinarie', 'age_229'], errors='ignore')
    
    return df
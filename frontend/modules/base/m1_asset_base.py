"""
Module 1: Regulatory Asset Base Valuation

Handles scaling factor adjustments for asset categories.
Parameter-IDs: 1.1.1 (general), 1.2.1-1.2.17 (per category)

Includes KENT upload for custom capital base data.
"""

import streamlit as st
import pandas as pd
from typing import Dict, Any, Optional

from frontend.common.asset_categories import ASSET_CATEGORIES

MODULE_KEY = "m1_asset_base"


def render(capbase_data: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
    """
    Render Module 1: Regulatory Asset Base Valuation.
    
    Args:
        capbase_data: If available, DataFrame with subcategories for subcat mode
    
    Returns:
        Dict with user selections:
        - normvalue_adjustments: Dict[int, float] or None (multipliers)
        - normvalue_level: 'cat' or 'subcat'
        - kent_file_bytes: bytes or None
        - kent_file_name: str or None
    """
    config: Dict[str, Any] = {}
    
    st.subheader("1. Regulatory Asset Base Valuation")
    
    # KENT upload section
    with st.expander("Upload KENT file", expanded=False):
        st.caption(
            "Custom capital base data. Overrides regulatory baseline."
        )
        kent_result = _render_kent_upload()
        if kent_result["kent_file_bytes"]:
            config["kent_file_bytes"] = kent_result["kent_file_bytes"]
            config["kent_file_name"] = kent_result["kent_file_name"]
    
    # Scaling factor adjustments
    with st.expander("1.2 Scaling factors", expanded=False):
        st.caption(
            "Percentage adjustment to baseline norm values."
        )
        
        # Select level (cat or subcat)
        has_subcat = capbase_data is not None and 'subcat_encode' in capbase_data.columns
        
        if has_subcat:
            level = st.radio(
                "Adjustment level:",
                ["Category level", "Subcategory level"],
                horizontal=True,
                key=f"{MODULE_KEY}_level"
            )
            use_subcat = (level == "Subcategory level")
        else:
            use_subcat = False
        
        if use_subcat and capbase_data is not None:
            adjustments, level_used = _render_subcat_editor(capbase_data)
        else:
            adjustments, level_used = _render_cat_editor()
        
        if adjustments:
            config["normvalue_adjustments"] = adjustments
            config["normvalue_level"] = level_used
            st.success(f"{len(adjustments)} scaling factor adjustment(s) active")
    
    return config


def _render_kent_upload() -> Dict[str, Any]:
    """
    Render KENT file upload UI.
    
    Returns:
        Dict with kent_file_bytes, kent_file_name
    """
    result = {
        "kent_file_bytes": None,
        "kent_file_name": None,
    }
    
    uploaded_file = st.file_uploader(
        "KENT Excel file",
        type=["xlsx", "xls"],
        key=f"{MODULE_KEY}_kent_upload",
        help="Export from KENT and upload here"
    )
    
    if uploaded_file is not None:
        result["kent_file_bytes"] = uploaded_file.getvalue()
        result["kent_file_name"] = uploaded_file.name
        st.success(f"File loaded: {uploaded_file.name}")
    
    return result


def _render_cat_editor() -> tuple[Optional[Dict[int, float]], str]:
    """
    Render editor for category-level adjustments with hardcoded baseline values.
    
    Returns:
        (adjustments dict or None, 'cat')
    """
    data = []
    for cat in ASSET_CATEGORIES:
        data.append({
            'Code': cat.cat_encode,
            'Category': cat.name,
            'Param-ID': cat.scaling_param_id,
            'Adjustment (%)': 0,
        })
    
    baseline_df = pd.DataFrame(data)
    
    edited_df = st.data_editor(
        baseline_df,
        width="stretch",
        hide_index=True,
        num_rows="fixed",
        disabled=['Code', 'Category', 'Param-ID'],
        column_config={
            'Code': st.column_config.NumberColumn('Code', format="%d", width="small"),
            'Category': st.column_config.TextColumn('Category', width="large"),
            'Param-ID': st.column_config.TextColumn('Param-ID', width="small"),
            'Adjustment (%)': st.column_config.NumberColumn(
                'Adjustment (%)',
                min_value=-50,
                max_value=100,
                step=1,
                format="%d",
                width="small"
            )
        },
        key=f"{MODULE_KEY}_cat_editor"
    )
    
    adjustments = _extract_normvalue_changes(edited_df)
    return adjustments, 'cat'


def _render_subcat_editor(capbase_data: pd.DataFrame) -> tuple[Optional[Dict[int, float]], str]:
    """Render editor for subcategory-level adjustments."""
    agg_df = capbase_data.groupby(['subcat_encode', 'subcat']).size().reset_index(name='count')
    
    agg_df = agg_df.rename(columns={
        'subcat_encode': 'Code',
        'subcat': 'Subcategory',
    })
    
    agg_df['Adjustment (%)'] = 0
    agg_df = agg_df[['Code', 'Subcategory', 'Adjustment (%)']].sort_values('Code').reset_index(drop=True)
    
    baseline_df = agg_df.copy()
    
    edited_df = st.data_editor(
        baseline_df,
        width="stretch",
        hide_index=True,
        num_rows="fixed",
        disabled=['Code', 'Subcategory'],
        column_config={
            'Code': st.column_config.NumberColumn('Code', format="%d", width="small"),
            'Subcategory': st.column_config.TextColumn('Subcategory', width="large"),
            'Adjustment (%)': st.column_config.NumberColumn(
                'Adjustment (%)',
                min_value=-50,
                max_value=100,
                step=1,
                format="%d",
                width="small"
            )
        },
        key=f"{MODULE_KEY}_subcat_editor"
    )
    
    adjustments = _extract_normvalue_changes(edited_df)
    return adjustments, 'subcat'


def _extract_normvalue_changes(edited_df: pd.DataFrame) -> Optional[Dict[int, float]]:
    """Extract scaling factor adjustments and convert % to multiplier."""
    adjustments = {}
    
    for _, row in edited_df.iterrows():
        pct = row['Adjustment (%)']
        if pct != 0:
            code = int(row['Code'])
            multiplier = 1 + (pct / 100)
            adjustments[code] = multiplier
    
    return adjustments if adjustments else None
"""
Module 2: Depreciation

Handles lifetime adjustments for asset categories.
Parameter-IDs: 2.X.1 (ordinary lifetime), 2.X.2 (tail lifetime) per category X
"""

import streamlit as st
import pandas as pd
from typing import Dict, Any, Optional

from frontend.common.asset_categories import ASSET_CATEGORIES

MODULE_KEY = "m2_depreciation"


def render(capbase_data: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
    """
    Render Module 2: Depreciation.
    
    Args:
        capbase_data: If available, DataFrame with subcategories for subcat mode
    
    Returns:
        Dict with user selections:
        - lifetime_adjustments: Dict[int, Dict[str, int]] or None
        - lifetime_level: 'cat' or 'subcat'
    """
    config: Dict[str, Any] = {}
    
    st.subheader("2. Depreciation")
    
    with st.expander("2.1-2.17 Asset lifetimes", expanded=False):
        st.caption(
            "Ordinary and tail lifetime by category. Modified values override baseline."
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
            config["lifetime_adjustments"] = adjustments
            config["lifetime_level"] = level_used
            st.success(f"{len(adjustments)} lifetime adjustment(s) active")
    
    return config


def _render_cat_editor() -> tuple[Optional[Dict[int, Dict[str, int]]], str]:
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
            'Param-ID': f"{cat.param_id_ekdep} / {cat.param_id_maxdep}",
            'Ordinary lifetime': cat.ekdep,
            'Tail lifetime': cat.maxdep,
        })
    
    baseline_df = pd.DataFrame(data)
    original_df = baseline_df.copy()
    
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
            'Ordinary lifetime': st.column_config.NumberColumn(
                'Ordinary lifetime',
                min_value=4,
                max_value=120,
                step=1,
                format="%d yrs",
                width="small"
            ),
            'Tail lifetime': st.column_config.NumberColumn(
                'Tail lifetime',
                min_value=4,
                max_value=150,
                step=1,
                format="%d yrs",
                width="small"
            )
        },
        key=f"{MODULE_KEY}_cat_editor"
    )
    
    adjustments = _extract_lifetime_changes(edited_df, original_df)
    return adjustments, 'cat'


def _render_subcat_editor(capbase_data: pd.DataFrame) -> tuple[Optional[Dict[int, Dict[str, int]]], str]:
    """Render editor for subcategory-level adjustments."""
    agg_df = capbase_data.groupby(['subcat_encode', 'subcat']).agg({
        'ekdep': 'first',
        'maxdep': 'first'
    }).reset_index()
    
    agg_df = agg_df.rename(columns={
        'subcat_encode': 'Code',
        'subcat': 'Subcategory',
        'ekdep': 'Ordinary lifetime',
        'maxdep': 'Tail lifetime',
    })
    
    agg_df = agg_df[['Code', 'Subcategory', 'Ordinary lifetime', 'Tail lifetime']].sort_values('Code').reset_index(drop=True)
    
    original_df = agg_df.copy()
    
    edited_df = st.data_editor(
        agg_df,
        width="stretch",
        hide_index=True,
        num_rows="fixed",
        disabled=['Code', 'Subcategory'],
        column_config={
            'Code': st.column_config.NumberColumn('Code', format="%d", width="small"),
            'Subcategory': st.column_config.TextColumn('Subcategory', width="large"),
            'Ordinary lifetime': st.column_config.NumberColumn(
                'Ordinary lifetime',
                min_value=4,
                max_value=120,
                step=1,
                format="%d yrs",
                width="small"
            ),
            'Tail lifetime': st.column_config.NumberColumn(
                'Tail lifetime',
                min_value=4,
                max_value=150,
                step=1,
                format="%d yrs",
                width="small"
            )
        },
        key=f"{MODULE_KEY}_subcat_editor"
    )
    
    adjustments = _extract_lifetime_changes(edited_df, original_df)
    return adjustments, 'subcat'


def _extract_lifetime_changes(
    edited_df: pd.DataFrame, 
    original_df: pd.DataFrame
) -> Optional[Dict[int, Dict[str, int]]]:
    """
    Extract lifetime adjustments by comparing edited vs original.
    
    Returns:
        Dict[code, Dict['ekdep'|'maxdep', new_value]] or None
    """
    adjustments = {}
    
    for idx, edited_row in edited_df.iterrows():
        original_row = original_df.iloc[idx]
        code = int(edited_row['Code'])
        
        changes = {}
        
        if edited_row['Ordinary lifetime'] != original_row['Ordinary lifetime']:
            changes['ekdep'] = int(edited_row['Ordinary lifetime'])
        
        if edited_row['Tail lifetime'] != original_row['Tail lifetime']:
            changes['maxdep'] = int(edited_row['Tail lifetime'])
        
        if changes:
            adjustments[code] = changes
    
    return adjustments if adjustments else None
"""
Module 2: Depreciation

Handles lifetime adjustments for asset categories.
Parameter-IDs: 2.X.1 (ordinary lifetime), 2.X.2 (tail period) per category X

--- NOTE FOR MEETING (kan tas bort efteråt) ---
Tail period vs maxdep:
- User Manual visar "Tail" som en separat period (t.ex. 24 år)
- Internt lagras maxdep som total livslängd (ekdep + tail = 100 + 24 = 124)
- UI visar nu tail period (24), inte maxdep (124)
- Beräkningskedjan får: maxdep = ekdep + tail_period
- Ska tail vara oberoende av ordinary lifetime? Nuvarande beräkningskedja med ex ekdep = 100 och maxdep = 124 innebär att om ekdep ändras till 99 så förblir maxdep 124 fast tail indirekt ökar till 25 då.
--- END NOTE ---
"""

import streamlit as st
import pandas as pd
from typing import Dict, Any, Optional

from frontend.common.asset_categories import ASSET_CATEGORIES

MODULE_KEY = "m2_depreciation"


def render(capbase_data: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
    """
    Render Module 2: Depreciation.
    
    Returns:
        Dict with lifetime_adjustments and lifetime_level
    """
    config: Dict[str, Any] = {}
    
    st.subheader("2. Depreciation")
    
    with st.expander("2.1-2.17 Asset lifetimes", expanded=False):
        st.caption(
            "Ordinary lifetime and tail period by category. Modified values override baseline."
        )
        
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
            adjustments, level_used, validation_error = _render_subcat_editor(capbase_data)
        else:
            adjustments, level_used, validation_error = _render_cat_editor()
        
        if validation_error:
            st.error(validation_error)
        elif adjustments:
            config["lifetime_adjustments"] = adjustments
            config["lifetime_level"] = level_used
            st.success(f"{len(adjustments)} lifetime adjustment(s) active")
    
    return config


def _render_cat_editor() -> tuple[Optional[Dict[int, Dict[str, int]]], str, Optional[str]]:
    """
    Render editor for category-level adjustments.
    
    Returns:
        (adjustments dict or None, 'cat', validation_error or None)
    """
    data = []
    for cat in ASSET_CATEGORIES:
        tail_period = cat.maxdep - cat.ekdep
        data.append({
            'Param-ID': f"{cat.param_id_ekdep} / {cat.param_id_maxdep}",
            'Category': cat.name,
            'Ordinary lifetime': cat.ekdep,
            'Tail period': tail_period,
            '_cat_encode': cat.cat_encode,
            '_baseline_ekdep': cat.ekdep,
            '_baseline_tail': tail_period,
        })
    
    baseline_df = pd.DataFrame(data)
    display_df = baseline_df[['Param-ID', 'Category', 'Ordinary lifetime', 'Tail period']].copy()
    original_display = display_df.copy()
    
    edited_df = st.data_editor(
        display_df,
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        disabled=['Param-ID', 'Category'],
        column_config={
            'Param-ID': st.column_config.TextColumn('Param-ID', width="small"),
            'Category': st.column_config.TextColumn('Category', width="large"),
            'Ordinary lifetime': st.column_config.NumberColumn(
                'Ordinary lifetime',
                min_value=4,
                max_value=120,
                step=1,
                format="%d yrs",
                width="small"
            ),
            'Tail period': st.column_config.NumberColumn(
                'Tail period',
                min_value=1,
                max_value=50,
                step=1,
                format="%d yrs",
                width="small"
            )
        },
        key=f"{MODULE_KEY}_cat_editor"
    )
    
    return _extract_lifetime_changes(edited_df, original_display, baseline_df)


def _render_subcat_editor(capbase_data: pd.DataFrame) -> tuple[Optional[Dict[int, Dict[str, int]]], str, Optional[str]]:
    """Render editor for subcategory-level adjustments."""
    agg_df = capbase_data.groupby(['subcat_encode', 'subcat']).agg({
        'ekdep': 'first',
        'maxdep': 'first'
    }).reset_index()
    
    agg_df['tail_period'] = agg_df['maxdep'] - agg_df['ekdep']
    
    agg_df = agg_df.rename(columns={
        'subcat_encode': '_code',
        'subcat': 'Subcategory',
        'ekdep': 'Ordinary lifetime',
        'tail_period': 'Tail period',
    })
    
    agg_df['_baseline_ekdep'] = agg_df['Ordinary lifetime']
    agg_df['_baseline_tail'] = agg_df['Tail period']
    
    agg_df = agg_df.sort_values('_code').reset_index(drop=True)
    
    display_df = agg_df[['Subcategory', 'Ordinary lifetime', 'Tail period']].copy()
    original_display = display_df.copy()
    
    edited_df = st.data_editor(
        display_df,
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        disabled=['Subcategory'],
        column_config={
            'Subcategory': st.column_config.TextColumn('Subcategory', width="large"),
            'Ordinary lifetime': st.column_config.NumberColumn(
                'Ordinary lifetime',
                min_value=4,
                max_value=120,
                step=1,
                format="%d yrs",
                width="small"
            ),
            'Tail period': st.column_config.NumberColumn(
                'Tail period',
                min_value=1,
                max_value=50,
                step=1,
                format="%d yrs",
                width="small"
            )
        },
        key=f"{MODULE_KEY}_subcat_editor"
    )
    
    return _extract_lifetime_changes_subcat(edited_df, original_display, agg_df)


def _extract_lifetime_changes(
    edited_df: pd.DataFrame, 
    original_df: pd.DataFrame,
    baseline_df: pd.DataFrame
) -> tuple[Optional[Dict[int, Dict[str, int]]], str, Optional[str]]:
    """
    Extract lifetime adjustments for category level.
    
    Returns:
        (adjustments dict, 'cat', validation_error or None)
    """
    adjustments = {}
    validation_errors = []
    
    for idx, edited_row in edited_df.iterrows():
        original_row = original_df.iloc[idx]
        baseline_row = baseline_df.iloc[idx]
        code = int(baseline_row['_cat_encode'])
        
        # Check for empty/NaN values
        if pd.isna(edited_row['Ordinary lifetime']):
            cat_name = baseline_row['Category']
            validation_errors.append(f"Ordinary lifetime cannot be empty ({cat_name})")
            continue
            
        if pd.isna(edited_row['Tail period']):
            cat_name = baseline_row['Category']
            validation_errors.append(f"Tail period cannot be empty ({cat_name})")
            continue
        
        changes = {}
        new_ekdep = int(edited_row['Ordinary lifetime'])
        new_tail = int(edited_row['Tail period'])
        
        if edited_row['Ordinary lifetime'] != original_row['Ordinary lifetime']:
            changes['ekdep'] = new_ekdep
        
        if edited_row['Tail period'] != original_row['Tail period']:
            pass  # Will be handled via maxdep below
        
        # Calculate maxdep from ekdep + tail_period
        baseline_ekdep = int(baseline_row['_baseline_ekdep'])
        baseline_tail = int(baseline_row['_baseline_tail'])
        
        if new_ekdep != baseline_ekdep or new_tail != baseline_tail:
            changes['ekdep'] = new_ekdep
            changes['maxdep'] = new_ekdep + new_tail
        
        if changes:
            adjustments[code] = changes
    
    if validation_errors:
        return None, 'cat', validation_errors[0]
    
    return adjustments if adjustments else None, 'cat', None


def _extract_lifetime_changes_subcat(
    edited_df: pd.DataFrame, 
    original_df: pd.DataFrame,
    baseline_df: pd.DataFrame
) -> tuple[Optional[Dict[int, Dict[str, int]]], str, Optional[str]]:
    """
    Extract lifetime adjustments for subcategory level.
    
    Returns:
        (adjustments dict, 'subcat', validation_error or None)
    """
    adjustments = {}
    validation_errors = []
    
    for idx, edited_row in edited_df.iterrows():
        original_row = original_df.iloc[idx]
        baseline_row = baseline_df.iloc[idx]
        code = int(baseline_row['_code'])
        
        if pd.isna(edited_row['Ordinary lifetime']):
            subcat_name = baseline_row['Subcategory']
            validation_errors.append(f"Ordinary lifetime cannot be empty ({subcat_name})")
            continue
            
        if pd.isna(edited_row['Tail period']):
            subcat_name = baseline_row['Subcategory']
            validation_errors.append(f"Tail period cannot be empty ({subcat_name})")
            continue
        
        new_ekdep = int(edited_row['Ordinary lifetime'])
        new_tail = int(edited_row['Tail period'])
        
        baseline_ekdep = int(baseline_row['_baseline_ekdep'])
        baseline_tail = int(baseline_row['_baseline_tail'])
        
        if new_ekdep != baseline_ekdep or new_tail != baseline_tail:
            adjustments[code] = {
                'ekdep': new_ekdep,
                'maxdep': new_ekdep + new_tail
            }
    
    if validation_errors:
        return None, 'subcat', validation_errors[0]
    
    return adjustments if adjustments else None, 'subcat', None
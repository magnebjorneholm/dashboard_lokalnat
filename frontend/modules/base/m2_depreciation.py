"""
Module 2: Depreciation

Handles lifetime adjustments for asset categories.
Parameter-IDs: 2.X.1 (ordinary lifetime), 2.X.2 (tail period) per category X

Section-based rendering:
- render_lifetimes() -> 2.X Asset lifetimes
"""

import streamlit as st
import pandas as pd
from typing import Dict, Any, Optional

from config.asset_categories import ASSET_CATEGORIES
from frontend.utils.state_manager import get_config_value
from config.glossary import lifetime_ordinary_param_id, lifetime_tail_param_id

MODULE_KEY = "m2_depreciation"


def render_lifetimes(capbase_data: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
    """
    Render M2 lifetimes section: 2.X Asset lifetimes.
    
    Args:
        capbase_data: Optional DataFrame with subcategory info for granular editing
        
    Returns:
        Dict with lifetime_adjustments and lifetime_level
    """
    config: Dict[str, Any] = {}
    
    st.markdown("##### 2.1-2.17 Asset lifetimes")
    st.caption(
        "Modified values override baseline. Changes apply to all companies. "
        f"(Parameters {lifetime_ordinary_param_id(1)}-{lifetime_tail_param_id(17)})"
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
        st.caption(f":orange[Modified] - {len(adjustments)} lifetime adjustment(s)")
    
    return config


# =============================================================================
# EDITOR FUNCTIONS
# =============================================================================

def _render_cat_editor() -> tuple[Optional[Dict[int, Dict[str, int]]], str, Optional[str]]:
    """Render editor for category-level adjustments."""
    editor_key = f"{MODULE_KEY}_cat_editor"
    source_key = f"{editor_key}_source"

    if source_key not in st.session_state or editor_key not in st.session_state:
        lifetime_adj = get_config_value(MODULE_KEY, "lifetime_adjustments", None)
        data = []
        for cat in ASSET_CATEGORIES:
            tail_period = cat.maxdep - cat.ekdep
            initial_ekdep = cat.ekdep
            initial_tail = tail_period
            if isinstance(lifetime_adj, dict) and cat.cat_encode in lifetime_adj:
                adj = lifetime_adj[cat.cat_encode]
                initial_ekdep = int(adj.get('ekdep', initial_ekdep))
                initial_tail = int(adj.get('maxdep', initial_ekdep + initial_tail)) - initial_ekdep
            data.append({
                'Param-ID': f"{cat.param_id_ekdep} / {cat.param_id_maxdep}",
                'Category': cat.name,
                'Ordinary lifetime': initial_ekdep,
                'Tail period': initial_tail,
                '_cat_encode': cat.cat_encode,
                '_baseline_ekdep': cat.ekdep,
                '_baseline_tail': tail_period,
            })
        baseline_df = pd.DataFrame(data)
        st.session_state[source_key] = baseline_df
    else:
        baseline_df = st.session_state[source_key]

    display_df = baseline_df[['Param-ID', 'Category', 'Ordinary lifetime', 'Tail period']].copy()
    original_display = display_df.copy()

    edited_df = st.data_editor(
        display_df,
        width='stretch',
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
    editor_key = f"{MODULE_KEY}_subcat_editor"
    source_key = f"{editor_key}_source"

    if source_key not in st.session_state or editor_key not in st.session_state:
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

        # Prefill from ui_config if present
        lifetime_adj = get_config_value(MODULE_KEY, "lifetime_adjustments", None)
        def _initial_subcat_ekdep(row):
            code = int(row['_code'])
            if isinstance(lifetime_adj, dict) and code in lifetime_adj:
                return int(lifetime_adj[code].get('ekdep', row['Ordinary lifetime']))
            return int(row['Ordinary lifetime'])

        def _initial_subcat_tail(row):
            code = int(row['_code'])
            if isinstance(lifetime_adj, dict) and code in lifetime_adj:
                adj = lifetime_adj[code]
                maxdep = int(adj.get('maxdep', row['Ordinary lifetime'] + row['Tail period']))
                return maxdep - int(adj.get('ekdep', row['Ordinary lifetime']))
            return int(row['Tail period'])

        agg_df['_baseline_ekdep'] = agg_df['Ordinary lifetime']
        agg_df['_baseline_tail'] = agg_df['Tail period']
        agg_df['Ordinary lifetime'] = agg_df.apply(_initial_subcat_ekdep, axis=1)
        agg_df['Tail period'] = agg_df.apply(_initial_subcat_tail, axis=1)

        agg_df = agg_df.sort_values('_code').reset_index(drop=True)
        st.session_state[source_key] = agg_df
    else:
        agg_df = st.session_state[source_key]

    display_df = agg_df[['Subcategory', 'Ordinary lifetime', 'Tail period']].copy()
    original_display = display_df.copy()

    edited_df = st.data_editor(
        display_df,
        width='stretch',
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


# =============================================================================
# EXTRACTION HELPERS
# =============================================================================

def _extract_lifetime_changes(
    edited_df: pd.DataFrame, 
    original_df: pd.DataFrame,
    baseline_df: pd.DataFrame
) -> tuple[Optional[Dict[int, Dict[str, int]]], str, Optional[str]]:
    """Extract lifetime adjustments for category level."""
    adjustments = {}
    validation_errors = []
    
    for idx, edited_row in edited_df.iterrows():
        original_row = original_df.iloc[idx]
        baseline_row = baseline_df.iloc[idx]
        code = int(baseline_row['_cat_encode'])
        
        if pd.isna(edited_row['Ordinary lifetime']):
            cat_name = baseline_row['Category']
            validation_errors.append(f"Ordinary lifetime cannot be empty ({cat_name})")
            continue
            
        if pd.isna(edited_row['Tail period']):
            cat_name = baseline_row['Category']
            validation_errors.append(f"Tail period cannot be empty ({cat_name})")
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
        return None, 'cat', validation_errors[0]
    
    return adjustments if adjustments else None, 'cat', None


def _extract_lifetime_changes_subcat(
    edited_df: pd.DataFrame, 
    original_df: pd.DataFrame,
    baseline_df: pd.DataFrame
) -> tuple[Optional[Dict[int, Dict[str, int]]], str, Optional[str]]:
    """Extract lifetime adjustments for subcategory level."""
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
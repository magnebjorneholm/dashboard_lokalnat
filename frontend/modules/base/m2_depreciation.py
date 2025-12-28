"""
Module 2: Depreciation

Hanterar livslängdsjusteringar för tillgångskategorier.
Parameter-IDs: 2.X.1 (ekdep), 2.X.2 (maxdep) per kategori X
"""

import streamlit as st
import pandas as pd
from typing import Dict, Any, Optional

from frontend.common.asset_categories import ASSET_CATEGORIES

MODULE_KEY = "m2_depreciation"


def render(capbase_data: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
    """
    Renderar Module 2: Depreciation.
    
    Args:
        capbase_data: Om tillgänglig, DataFrame med subkategorier för subcat-läge
    
    Returns:
        Dict med användarens val. Keys:
        - lifetime_adjustments: Dict[int, Dict[str, int]] eller None
        - lifetime_level: 'cat' eller 'subcat'
    """
    config: Dict[str, Any] = {}
    
    st.subheader("2. Depreciation")
    
    with st.expander("Parameters: Livslängder", expanded=False):
        st.markdown("Justera ekonomisk och maximal livslängd per tillgångskategori.")
        st.caption("Ändra värdena direkt i tabellen. Endast ändrade rader påverkar beräkningen.")
        
        # Välj nivå (cat eller subcat)
        has_subcat = capbase_data is not None and 'subcat_encode' in capbase_data.columns
        
        if has_subcat:
            level = st.radio(
                "Justeringsnivå:",
                ["Kategorinivå (cat)", "Subkategorinivå (subcat)"],
                horizontal=True,
                key=f"{MODULE_KEY}_level"
            )
            use_subcat = (level == "Subkategorinivå (subcat)")
        else:
            use_subcat = False
        
        if use_subcat and capbase_data is not None:
            adjustments, level_used = _render_subcat_editor(capbase_data)
        else:
            adjustments, level_used = _render_cat_editor()
        
        if adjustments:
            config["lifetime_adjustments"] = adjustments
            config["lifetime_level"] = level_used
            st.success(f"{len(adjustments)} livslängdsjustering(ar) aktiva")
    
    return config


def _render_cat_editor() -> tuple[Optional[Dict[int, Dict[str, int]]], str]:
    """
    Renderar editor för kategorinivå med hårdkodade baseline-värden.
    
    Returns:
        (adjustments dict eller None, 'cat')
    """
    # Bygg DataFrame från baseline-kategorier
    data = []
    for cat in ASSET_CATEGORIES:
        data.append({
            'Kod': cat.cat_encode,
            'Kategori': cat.name,
            'Ekon. livslängd': cat.ekdep,
            'Max. livslängd': cat.maxdep,
        })
    
    baseline_df = pd.DataFrame(data)
    original_df = baseline_df.copy()
    
    edited_df = st.data_editor(
        baseline_df,
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        disabled=['Kod', 'Kategori'],
        column_config={
            'Kod': st.column_config.NumberColumn('Kod', format="%d"),
            'Kategori': st.column_config.TextColumn('Kategori', width="large"),
            'Ekon. livslängd': st.column_config.NumberColumn(
                'Ekon. livslängd',
                min_value=4,
                max_value=100,
                step=1,
                format="%d år"
            ),
            'Max. livslängd': st.column_config.NumberColumn(
                'Max. livslängd',
                min_value=4,
                max_value=150,
                step=1,
                format="%d år"
            )
        },
        key=f"{MODULE_KEY}_cat_editor"
    )
    
    adjustments = _extract_lifetime_changes(edited_df, original_df)
    return adjustments, 'cat'


def _render_subcat_editor(capbase_data: pd.DataFrame) -> tuple[Optional[Dict[int, Dict[str, int]]], str]:
    """Renderar editor för subkategorinivå."""
    # Aggregera subkategorier från faktisk data
    agg_df = capbase_data.groupby(['subcat_encode', 'subcat']).agg({
        'ekdep': 'first',
        'maxdep': 'first'
    }).reset_index()
    
    agg_df = agg_df.rename(columns={
        'subcat_encode': 'Kod',
        'subcat': 'Subkategori',
        'ekdep': 'Ekon. livslängd',
        'maxdep': 'Max. livslängd',
    })
    
    agg_df = agg_df[['Kod', 'Subkategori', 'Ekon. livslängd', 'Max. livslängd']].sort_values('Kod').reset_index(drop=True)
    
    original_df = agg_df.copy()
    
    edited_df = st.data_editor(
        agg_df,
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        disabled=['Kod', 'Subkategori'],
        column_config={
            'Kod': st.column_config.NumberColumn('Kod', format="%d"),
            'Subkategori': st.column_config.TextColumn('Subkategori', width="large"),
            'Ekon. livslängd': st.column_config.NumberColumn(
                'Ekon. livslängd',
                min_value=4,
                max_value=100,
                step=1,
                format="%d år"
            ),
            'Max. livslängd': st.column_config.NumberColumn(
                'Max. livslängd',
                min_value=4,
                max_value=150,
                step=1,
                format="%d år"
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
    Extraherar livslängdsjusteringar genom att jämföra edited vs original.
    
    Returns:
        Dict[code, Dict['ekdep'|'maxdep', new_value]] eller None
    """
    adjustments = {}
    
    for idx, edited_row in edited_df.iterrows():
        original_row = original_df.iloc[idx]
        code = int(edited_row['Kod'])
        
        changes = {}
        
        if edited_row['Ekon. livslängd'] != original_row['Ekon. livslängd']:
            changes['ekdep'] = int(edited_row['Ekon. livslängd'])
        
        if edited_row['Max. livslängd'] != original_row['Max. livslängd']:
            changes['maxdep'] = int(edited_row['Max. livslängd'])
        
        if changes:
            adjustments[code] = changes
    
    return adjustments if adjustments else None
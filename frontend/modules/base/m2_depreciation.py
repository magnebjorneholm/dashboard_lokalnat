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
            # Subkategori-läge: hämta från data
            adjustments, level_used = _render_subcat_editor(capbase_data)
        else:
            # Kategori-läge: använd hårdkodade baseline-värden
            adjustments, level_used = _render_cat_editor()
        
        if adjustments:
            config["lifetime_adjustments"] = adjustments
            config["lifetime_level"] = level_used
            st.success(f"{len(adjustments)} livslängdsjustering(ar) aktiva")
    
    with st.expander("Variables", expanded=False):
        st.info(
            "Depreciation variables (20.X) beräknas automatiskt.\n\n"
            "Output: Avskrivning per tillgångstyp (ordinarie + svans)"
        )
    
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
    
    # Redigerbar tabell
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
                'Ekon. livslängd (år)',
                min_value=1,
                max_value=200,
                step=1,
                format="%d"
            ),
            'Max. livslängd': st.column_config.NumberColumn(
                'Max. livslängd (år)',
                min_value=1,
                max_value=250,
                step=1,
                format="%d"
            )
        },
        key=f"{MODULE_KEY}_cat_editor"
    )
    
    # Validera och extrahera ändringar
    adjustments = _extract_lifetime_changes(baseline_df, edited_df)
    
    # Validering: maxdep >= ekdep
    invalid = edited_df[edited_df['Max. livslängd'] < edited_df['Ekon. livslängd']]
    if not invalid.empty:
        st.error(f"Fel: {len(invalid)} kategori(er) har max livslängd < ekonomisk livslängd")
        return None, 'cat'
    
    return adjustments, 'cat'


def _render_subcat_editor(capbase_data: pd.DataFrame) -> tuple[Optional[Dict[int, Dict[str, int]]], str]:
    """
    Renderar editor för subkategorinivå baserat på data.
    
    Returns:
        (adjustments dict eller None, 'subcat')
    """
    # Aggregera unika subkategorier
    agg_df = capbase_data.groupby(['subcat_encode', 'subcat']).agg({
        'ekdep': 'first',
        'maxdep': 'first'
    }).reset_index()
    
    agg_df = agg_df.rename(columns={
        'subcat_encode': 'Kod',
        'subcat': 'Subkategori',
        'ekdep': 'Ekon. livslängd',
        'maxdep': 'Max. livslängd'
    })
    
    agg_df = agg_df.sort_values('Kod').reset_index(drop=True)
    baseline_df = agg_df.copy()
    
    # Redigerbar tabell
    edited_df = st.data_editor(
        baseline_df,
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        disabled=['Kod', 'Subkategori'],
        column_config={
            'Kod': st.column_config.NumberColumn('Kod', format="%d"),
            'Subkategori': st.column_config.TextColumn('Subkategori', width="large"),
            'Ekon. livslängd': st.column_config.NumberColumn(
                'Ekon. livslängd (år)',
                min_value=1,
                max_value=200,
                step=1,
                format="%d"
            ),
            'Max. livslängd': st.column_config.NumberColumn(
                'Max. livslängd (år)',
                min_value=1,
                max_value=250,
                step=1,
                format="%d"
            )
        },
        key=f"{MODULE_KEY}_subcat_editor"
    )
    
    # Validera och extrahera ändringar
    adjustments = _extract_lifetime_changes(baseline_df, edited_df)
    
    # Validering
    invalid = edited_df[edited_df['Max. livslängd'] < edited_df['Ekon. livslängd']]
    if not invalid.empty:
        st.error(f"Fel: {len(invalid)} subkategori(er) har max livslängd < ekonomisk livslängd")
        return None, 'subcat'
    
    return adjustments, 'subcat'


def _extract_lifetime_changes(
    baseline_df: pd.DataFrame, 
    edited_df: pd.DataFrame
) -> Optional[Dict[int, Dict[str, int]]]:
    """
    Jämför baseline med edited och returnerar endast ändrade värden.
    
    Returns:
        Dict med {code: {'ekdep': val, 'maxdep': val}} eller None om inga ändringar
    """
    adjustments = {}
    
    for idx in range(len(baseline_df)):
        code = int(baseline_df.iloc[idx]['Kod'])
        
        baseline_ekdep = int(baseline_df.iloc[idx]['Ekon. livslängd'])
        baseline_maxdep = int(baseline_df.iloc[idx]['Max. livslängd'])
        
        edited_ekdep = int(edited_df.iloc[idx]['Ekon. livslängd'])
        edited_maxdep = int(edited_df.iloc[idx]['Max. livslängd'])
        
        changes = {}
        if edited_ekdep != baseline_ekdep:
            changes['ekdep'] = edited_ekdep
        if edited_maxdep != baseline_maxdep:
            changes['maxdep'] = edited_maxdep
        
        if changes:
            adjustments[code] = changes
    
    return adjustments if adjustments else None
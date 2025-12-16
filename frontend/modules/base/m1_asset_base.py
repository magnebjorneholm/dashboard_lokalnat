"""
Module 1: Regulatory Asset Base Valuation

Hanterar normvärdejusteringar för tillgångskategorier.
Parameter-IDs: 1.1.1 (generell), 1.2.1-1.2.17 (per kategori)
"""

import streamlit as st
import pandas as pd
from typing import Dict, Any, Optional

from frontend.common.asset_categories import ASSET_CATEGORIES

MODULE_KEY = "m1_asset_base"


def render(capbase_data: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
    """
    Renderar Module 1: Regulatory Asset Base Valuation.
    
    Args:
        capbase_data: Om tillgänglig, DataFrame med subkategorier för subcat-läge
    
    Returns:
        Dict med användarens val. Keys:
        - normvalue_adjustments: Dict[int, float] eller None (multipliers)
        - normvalue_level: 'cat' eller 'subcat'
    """
    config: Dict[str, Any] = {}
    
    st.subheader("1. Regulatory Asset Base Valuation")
    
    with st.expander("Parameters: Normvärden", expanded=False):
        st.markdown("Justera normvärden procentuellt per tillgångskategori.")
        st.caption("Ange procentuell förändring: +15% ökar normvärdet med 15%, -10% minskar med 10%.")
        
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
            config["normvalue_adjustments"] = adjustments
            config["normvalue_level"] = level_used
            st.success(f"{len(adjustments)} normvärdejustering(ar) aktiva")
    
    with st.expander("Variables", expanded=False):
        st.info(
            "Asset base variables (10.X, 11.X) beräknas automatiskt.\n\n"
            "Output: Tillgångsvärden per kategori baserat på NUAV"
        )
    
    return config


def _render_cat_editor() -> tuple[Optional[Dict[int, float]], str]:
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
            'Justering (%)': 0,
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
            'Justering (%)': st.column_config.NumberColumn(
                'Justering (%)',
                min_value=-50,
                max_value=100,
                step=1,
                format="%d"
            )
        },
        key=f"{MODULE_KEY}_cat_editor"
    )
    
    # Extrahera ändringar (konvertera % till multiplier)
    adjustments = _extract_normvalue_changes(edited_df)
    
    return adjustments, 'cat'


def _render_subcat_editor(capbase_data: pd.DataFrame) -> tuple[Optional[Dict[int, float]], str]:
    """
    Renderar editor för subkategorinivå baserat på data.
    
    Returns:
        (adjustments dict eller None, 'subcat')
    """
    # Aggregera unika subkategorier
    agg_df = capbase_data.groupby(['subcat_encode', 'subcat']).size().reset_index(name='count')
    
    agg_df = agg_df.rename(columns={
        'subcat_encode': 'Kod',
        'subcat': 'Subkategori',
    })
    
    agg_df['Justering (%)'] = 0
    agg_df = agg_df[['Kod', 'Subkategori', 'Justering (%)']].sort_values('Kod').reset_index(drop=True)
    
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
            'Justering (%)': st.column_config.NumberColumn(
                'Justering (%)',
                min_value=-50,
                max_value=100,
                step=1,
                format="%d"
            )
        },
        key=f"{MODULE_KEY}_subcat_editor"
    )
    
    # Extrahera ändringar
    adjustments = _extract_normvalue_changes(edited_df)
    
    return adjustments, 'subcat'


def _extract_normvalue_changes(edited_df: pd.DataFrame) -> Optional[Dict[int, float]]:
    """
    Extraherar normvärdejusteringar och konverterar % till multiplier.
    
    Returns:
        Dict med {code: multiplier} eller None om inga ändringar
        Exempel: +15% -> 1.15, -10% -> 0.90
    """
    adjustments = {}
    
    for _, row in edited_df.iterrows():
        pct = row['Justering (%)']
        if pct != 0:
            code = int(row['Kod'])
            multiplier = 1 + (pct / 100)
            adjustments[code] = multiplier
    
    return adjustments if adjustments else None
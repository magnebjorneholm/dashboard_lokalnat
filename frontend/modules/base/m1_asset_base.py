"""
Module 1: Regulatory Asset Base Valuation

Hanterar normvärdejusteringar för tillgångskategorier.
Parameter-IDs: 1.1.1 (generell), 1.2.1-1.2.17 (per kategori)

Inkluderar KENT-upload för att ladda egen kapitalbas.
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
        - kent_file_bytes: bytes eller None
        - kent_file_name: str eller None
    """
    config: Dict[str, Any] = {}
    
    st.subheader("1. Regulatory Asset Base Valuation")
    
    # KENT-upload sektion
    with st.expander("Ladda upp egen KENT-fil", expanded=False):
        kent_result = _render_kent_upload()
        if kent_result["kent_file_bytes"]:
            config["kent_file_bytes"] = kent_result["kent_file_bytes"]
            config["kent_file_name"] = kent_result["kent_file_name"]
    
    # Normvärde-justeringar
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
            adjustments, level_used = _render_subcat_editor(capbase_data)
        else:
            adjustments, level_used = _render_cat_editor()
        
        if adjustments:
            config["normvalue_adjustments"] = adjustments
            config["normvalue_level"] = level_used
            st.success(f"{len(adjustments)} normvärdejustering(ar) aktiva")
    
    return config


def _render_kent_upload() -> Dict[str, Any]:
    """
    Renderar KENT fil-upload UI.
    
    Returns:
        Dict med kent_file_bytes, kent_file_name
    """
    result = {
        "kent_file_bytes": None,
        "kent_file_name": None,
    }
    
    st.caption(
        "Ladda upp din KENT Excel-fil för att använda egen kapitalbas "
        "istället för regulatorns baseline-data."
    )
    
    uploaded_file = st.file_uploader(
        "KENT Excel-fil",
        type=["xlsx", "xls"],
        key=f"{MODULE_KEY}_kent_upload",
        help="Exportera från KENT och ladda upp här"
    )
    
    if uploaded_file is not None:
        result["kent_file_bytes"] = uploaded_file.getvalue()
        result["kent_file_name"] = uploaded_file.name
        st.success(f"Fil laddad: {uploaded_file.name}")
    
    return result


def _render_cat_editor() -> tuple[Optional[Dict[int, float]], str]:
    """
    Renderar editor för kategorinivå med hårdkodade baseline-värden.
    
    Returns:
        (adjustments dict eller None, 'cat')
    """
    data = []
    for cat in ASSET_CATEGORIES:
        data.append({
            'Kod': cat.cat_encode,
            'Kategori': cat.name,
            'Justering (%)': 0,
        })
    
    baseline_df = pd.DataFrame(data)
    
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
    
    adjustments = _extract_normvalue_changes(edited_df)
    return adjustments, 'cat'


def _render_subcat_editor(capbase_data: pd.DataFrame) -> tuple[Optional[Dict[int, float]], str]:
    """Renderar editor för subkategorinivå."""
    agg_df = capbase_data.groupby(['subcat_encode', 'subcat']).size().reset_index(name='count')
    
    agg_df = agg_df.rename(columns={
        'subcat_encode': 'Kod',
        'subcat': 'Subkategori',
    })
    
    agg_df['Justering (%)'] = 0
    agg_df = agg_df[['Kod', 'Subkategori', 'Justering (%)']].sort_values('Kod').reset_index(drop=True)
    
    baseline_df = agg_df.copy()
    
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
    
    adjustments = _extract_normvalue_changes(edited_df)
    return adjustments, 'subcat'


def _extract_normvalue_changes(edited_df: pd.DataFrame) -> Optional[Dict[int, float]]:
    """Extraherar normvärdejusteringar och konverterar % till multiplier."""
    adjustments = {}
    
    for _, row in edited_df.iterrows():
        pct = row['Justering (%)']
        if pct != 0:
            code = int(row['Kod'])
            multiplier = 1 + (pct / 100)
            adjustments[code] = multiplier
    
    return adjustments if adjustments else None
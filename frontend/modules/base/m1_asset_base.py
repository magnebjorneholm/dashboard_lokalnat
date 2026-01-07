"""
Module 1: Regulatory Asset Base Valuation

Handles:
- RAB-editor för redigering av användarens kapitalbas
- KENT-upload för uppladdning av kapitalbas-fil
- Scaling factor adjustments för normvärden

Parameter-IDs: 1.1.1 (general), 1.2.1-1.2.17 (per category)
"""

import streamlit as st
import pandas as pd
from typing import Dict, Any, Optional

from frontend.common.asset_categories import ASSET_CATEGORIES
from frontend.modules.base import m1_rab_editor

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
        - rab_has_changes: bool
    """
    config: Dict[str, Any] = {}
    
    st.subheader("1. Regulatory Asset Base Valuation")
    
    # === RAB-EDITOR ===
    # Visar info om prioritering om KENT är uppladdad
    current_config = st.session_state.get("ui_config", {}).get(MODULE_KEY, {})
    kent_uploaded = current_config.get("kent_file_bytes") is not None
    
    with st.expander("1.1 Edit capital base (RAB-editor)", expanded=False):
        if kent_uploaded:
            st.warning(
                "KENT-fil är uppladdad och har prioritet. "
                "RAB-editor ändringar ignoreras när KENT-fil finns."
            )
        
        m1_rab_editor.render_info_box()
        rab_config = m1_rab_editor.render()
        
        if rab_config.get("rab_has_changes"):
            config["rab_has_changes"] = True
            if kent_uploaded:
                st.caption(":orange[Ändringar sparade men KENT-fil prioriteras]")
        else:
            config["rab_has_changes"] = False
    
    # === KENT UPLOAD ===
    with st.expander("1.2 Upload KENT file", expanded=False):
        st.caption(
            "Upload custom capital base data from KENT. "
            "This overrides both RAB-editor changes and regulatory baseline."
        )
        kent_result = _render_kent_upload()
        if kent_result["kent_file_bytes"]:
            config["kent_file_bytes"] = kent_result["kent_file_bytes"]
            config["kent_file_name"] = kent_result["kent_file_name"]
            
            # Visa varning om RAB har ändringar
            if config.get("rab_has_changes"):
                st.info("RAB-editor har ändringar som ignoreras pga KENT-fil.")
    
    # === SCALING FACTORS ===
    with st.expander("1.3 Scaling factors", expanded=False):
        st.caption(
            "Percentage adjustment to baseline norm values. "
            "Applies to all companies (parameter change)."
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
        
        # Visa sammanfattning av filen
        try:
            from calculations.kent_capbase_prep import get_kent_upload_summary, build_capbase_a_from_kent
            from frontend.utils.state_manager import get_user_id_network
            from io import BytesIO
            
            user_id = get_user_id_network()
            if user_id:
                kent_file = BytesIO(result["kent_file_bytes"])
                capbase = build_capbase_a_from_kent(kent_file, network_id=user_id)
                summary = get_kent_upload_summary(capbase)
                
                col1, col2, col3 = st.columns(3)
                col1.metric("Komponenter", f"{summary['n_components']:,}")
                col2.metric("Total NUAV", f"{summary['total_nuav_mkr']:.1f} Mkr")
                col3.metric("Investeringar", summary['n_investments'])
        except Exception as e:
            st.caption(f"Kunde inte läsa filsammanfattning: {e}")
    
    # Knapp för att ta bort uppladdad fil
    current_config = st.session_state.get("ui_config", {}).get(MODULE_KEY, {})
    if current_config.get("kent_file_bytes") and uploaded_file is None:
        if st.button("Ta bort KENT-fil", key="remove_kent"):
            # Rensa från config
            st.session_state["ui_config"][MODULE_KEY]["kent_file_bytes"] = None
            st.session_state["ui_config"][MODULE_KEY]["kent_file_name"] = None
            st.rerun()
    
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
    """
    Render editor for subcategory-level adjustments.
    
    Returns:
        (adjustments dict or None, 'subcat')
    """
    # Gruppera per subcat_encode
    subcats = capbase_data.groupby(['cat_encode', 'subcat_encode', 'subcat']).size().reset_index()
    subcats = subcats.rename(columns={0: 'count'})
    
    data = []
    for _, row in subcats.iterrows():
        cat = next((c for c in ASSET_CATEGORIES if c.cat_encode == row['cat_encode']), None)
        cat_name = cat.name if cat else f"Kategori {row['cat_encode']}"
        
        data.append({
            'Cat': row['cat_encode'],
            'Subcat': row['subcat_encode'],
            'Category': cat_name,
            'Subcategory': row['subcat'],
            'Components': row['count'],
            'Adjustment (%)': 0,
        })
    
    baseline_df = pd.DataFrame(data)
    
    edited_df = st.data_editor(
        baseline_df,
        width="stretch",
        hide_index=True,
        num_rows="fixed",
        disabled=['Cat', 'Subcat', 'Category', 'Subcategory', 'Components'],
        column_config={
            'Cat': st.column_config.NumberColumn('Cat', format="%d", width="small"),
            'Subcat': st.column_config.NumberColumn('Subcat', format="%d", width="small"),
            'Category': st.column_config.TextColumn('Category', width="medium"),
            'Subcategory': st.column_config.TextColumn('Subcategory', width="medium"),
            'Components': st.column_config.NumberColumn('N', format="%d", width="small"),
            'Adjustment (%)': st.column_config.NumberColumn(
                'Adj (%)',
                min_value=-50,
                max_value=100,
                step=1,
                format="%d",
                width="small"
            )
        },
        key=f"{MODULE_KEY}_subcat_editor"
    )
    
    adjustments = _extract_subcat_changes(edited_df)
    return adjustments, 'subcat'


def _extract_normvalue_changes(df: pd.DataFrame) -> Optional[Dict[int, float]]:
    """
    Extract non-zero adjustments from category editor.
    
    Returns:
        Dict mapping cat_encode to multiplier (1.0 + adj/100), or None if no changes
    """
    changes = {}
    for _, row in df.iterrows():
        adj = row.get('Adjustment (%)', 0)
        if adj != 0:
            multiplier = 1.0 + (adj / 100.0)
            changes[int(row['Code'])] = multiplier
    
    return changes if changes else None


def _extract_subcat_changes(df: pd.DataFrame) -> Optional[Dict[int, float]]:
    """
    Extract non-zero adjustments from subcategory editor.
    
    Returns:
        Dict mapping subcat_encode to multiplier, or None if no changes
    """
    changes = {}
    for _, row in df.iterrows():
        adj = row.get('Adjustment (%)', 0)
        if adj != 0:
            multiplier = 1.0 + (adj / 100.0)
            changes[int(row['Subcat'])] = multiplier
    
    return changes if changes else None
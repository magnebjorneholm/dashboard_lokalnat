"""
m1_rab_editor.py

RAB editor (Regulatory Asset Base) for editing capital base.

UI structure:
- Three tabs based on vtype (Normvärde, Alternative Methods, Investments)
- Read-only table with clickable rows
- Edit form with dynamic dropdowns
- Bulk actions for scaling
"""

import streamlit as st
import pandas as pd
from typing import Dict, Any, Optional, List, Tuple

from calculations.rab_editor_utils import (
    # Init and data
    initialize_rab_editor,
    get_user_capbase_with_edits,
    get_modified_components,
    get_original_components,
    load_user_components,
    get_current_id_network,
    # Per vtype
    get_normvärderade,
    get_övriga_metoder,
    get_investeringar,
    get_vtype_summary,
    # Changes
    has_changes,
    get_change_summary,
    reset_rab_editor,
    update_component_field,
    update_modified_components,
    update_techspec,
    add_investment,
    add_component_vtype1,
    remove_component,
    restore_component,
    # Scaling
    apply_count_scaling,
    apply_value_scaling,
    # Helpers
    get_category_options,
    get_subcat_options,
    get_techspec_options,
    apply_filters,
    render_summary_metrics,
    time_code_to_year,
    year_to_time_code,
    get_halfyear_options,
)

from frontend.utils.state_manager import get_user_id_network

from calculations.rab_editor_variables import (
    VType,
    VTYPE_NAMN,
    KATEGORIER,
    TIMECODE_PERIOD_START,
    TIMECODE_PERIOD_END,
    HALFYEAR_TO_TIMECODE,
    TIMECODE_TO_HALFYEAR,
)

from data.normvärdelista import (
    list_techspecs_for_category,
    list_typ_anläggning,
    get_normvärde_info,
    NORMVÄRDEN,
)


# =============================================================================
# MAIN FUNCTION
# =============================================================================

def render() -> Dict[str, Any]:
    """Render RAB editor UI."""
    config: Dict[str, Any] = {"rab_has_changes": False}
    
    user_id_network = get_user_id_network()
    
    if not user_id_network:
        st.warning("Select company in sidebar to edit regulatory asset base.")
        return config
    
    # Load and initialize
    try:
        user_components = load_user_components(user_id_network)
        initialize_rab_editor(user_components, user_id_network)
    except Exception as e:
        st.error(f"Failed to load asset base data: {e}")
        return config
    
    # Summary
    _render_header_summary()
    
    st.divider()
    
    # Tabs per vtype
    vtype_stats = get_vtype_summary()

    pct_norm = vtype_stats.get(VType.NORMVÄRDE, {}).get('andel_pct', 0)
    pct_övriga = (
        vtype_stats.get(VType.ANNAT_SKÄLIGT_VÄRDE, {}).get('andel_pct', 0) +
        vtype_stats.get(VType.ANSKAFFNINGSVÄRDE, {}).get('andel_pct', 0)
    )
    pct_inv = vtype_stats.get(VType.INVESTERING, {}).get('andel_pct', 0)

    tab_norm, tab_övriga, tab_invest = st.tabs([
        f"Normvärde ({pct_norm:.1f}%)",
        f"Alternative Methods ({pct_övriga:.1f}%)",
        f"Investments ({pct_inv:.1f}%)",
    ])
    
    with tab_norm:
        _render_normvärderade_tab()
    
    with tab_övriga:
        _render_övriga_metoder_tab()
    
    with tab_invest:
        _render_investeringar_tab()
    
    st.divider()
    
    # Change indicator and reset
    _render_change_indicator()
    config["rab_has_changes"] = has_changes()
    
    return config


# =============================================================================
# SUMMARY
# =============================================================================

def _render_header_summary():
    """Render summary at the top."""
    metrics = render_summary_metrics(show_delta=True)
    vtype_summary = get_vtype_summary()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Components", f"{metrics['n_components']:,}")
    
    with col2:
        st.metric("Total NUAV", f"{metrics['total_nuav_mkr']:.1f} MSEK")
    
    with col3:
        delta = metrics['delta_nuav_mkr']
        delta_str = f"{delta:+.2f} MSEK" if abs(delta) > 0.001 else None
        st.metric("Change", f"{delta:+.2f} MSEK" if delta_str else "0", delta=delta_str)
    
    with col4:
        if st.button("Reset All Changes", type="secondary"):
            reset_rab_editor()
            _clear_edit_state()
            st.rerun()


# =============================================================================
# TAB 1: NORMVÄRDE (vtype=4)
# =============================================================================

def _render_normvärderade_tab():
    """Render tab for normvärde components."""
    st.subheader("Normvärde Components")
    st.caption("Components valued using Ei normvärden. NUAV = normvärde × quantity")
    
    df = get_normvärderade()
    
    if df.empty:
        st.info("No normvärde components.")
        return
    
    # Filters
    col_f1, col_f2 = st.columns(2)
    
    with col_f1:
        kategorier = ["All categories"] + sorted(df['cat'].dropna().unique().tolist())
        selected_cat = st.selectbox(
            "Category",
            kategorier,
            key="norm_filter_cat"
        )
    
    with col_f2:
        if selected_cat != "All categories":
            subcats = ["All subcategories"] + sorted(
                df[df['cat'] == selected_cat]['subcat'].dropna().unique().tolist()
            )
        else:
            subcats = ["All subcategories"]
        
        selected_subcat = st.selectbox(
            "Subcategory",
            subcats,
            key="norm_filter_subcat"
        )
    
    # Filter
    df_filtered = df.copy()
    if selected_cat != "All categories":
        df_filtered = df_filtered[df_filtered['cat'] == selected_cat]
    if selected_subcat != "All subcategories":
        df_filtered = df_filtered[df_filtered['subcat'] == selected_subcat]
    
    st.caption(f"Showing {len(df_filtered)} of {len(df)} components")
    
    # Table and edit form
    _render_normvärderad_table_and_form(df_filtered, selected_cat, selected_subcat)
    
    # Bulk actions
    with st.expander("Bulk Actions: Scale Quantity", expanded=False):
        _render_count_scaling_form(
            vtype=VType.NORMVÄRDE,
            cat_filter=None if selected_cat == "All categories" else selected_cat,
            subcat_filter=None if selected_subcat == "All subcategories" else selected_subcat,
        )


@st.fragment
def _render_normvärderad_table_and_form(df: pd.DataFrame, cat_filter: str, subcat_filter: str):
    """Render table and edit form for normvärde components."""
    
    # Prepare display data
    df_display = df[['id_component', 'cat', 'subcat', 'techspec', 'volt', 'count_comp', 'normvärde', 'nuav_2022', 'time_from']].copy()
    df_display['year'] = df_display['time_from'].apply(time_code_to_year)
    df_display['nuav_mkr'] = df_display['nuav_2022'] / 1_000_000
    df_display['normvärde_kkr'] = df_display['normvärde'] / 1_000
    
    # Format for display
    df_display = df_display.rename(columns={
        'id_component': 'ID',
        'cat': 'Category',
        'subcat': 'Subcategory', 
        'techspec': 'Tech Spec',
        'volt': 'Voltage',
        'count_comp': 'Quantity',
        'normvärde_kkr': 'Normvärde (kSEK)',
        'nuav_mkr': 'NUAV (MSEK)',
        'year': 'Commissioned',
    })
    
    # Select columns to display
    display_cols = ['ID', 'Subcategory', 'Tech Spec', 'Voltage', 'Quantity', 'Normvärde (kSEK)', 'NUAV (MSEK)', 'Commissioned']
    
    # Handle row selection
    edit_key = "norm_selected_id"
    
    # Display table with on_select
    st.markdown("**Click a row to edit:**")
    
    event = st.dataframe(
        df_display[display_cols],
        width='stretch',
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key="norm_table_select",
    )
    
    # Get selected row
    selected_rows = event.selection.rows if event.selection else []
    
    if selected_rows:
        selected_idx = selected_rows[0]
        selected_id = df_display.iloc[selected_idx]['ID']
        
        # Get original data for the component
        original_row = df[df['id_component'] == selected_id].iloc[0]
        
        st.markdown("---")
        st.markdown(f"**Edit Component ID {selected_id}**")
        
        _render_normvärderad_edit_form(original_row, selected_id)


def _render_normvärderad_edit_form(row: pd.Series, component_id: int):
    """Render edit form for a normvärde component."""
    
    kategori = row['cat']
    subkategori = row['subcat']
    current_techspec = row['techspec']
    current_volt = str(row['volt']) if pd.notna(row['volt']) else ""
    current_count = row['count_comp']
    current_year = time_code_to_year(row['time_from'])
    current_normvärde = row['normvärde']
    current_nuav = row['nuav_2022']
    
    # Get available techspecs for this category/subcategory
    techspecs = list_techspecs_for_category(kategori, subkategori)
    
    if not techspecs:
        st.warning(f"No tech specs found for {kategori} / {subkategori}")
        techspec_options = [current_techspec]
        volt_options = [current_volt]
    else:
        # Unique techspecs
        techspec_options = sorted(set(ts for ts, volt, kod, nv in techspecs))
        
        # Ensure current is included
        if current_techspec not in techspec_options:
            techspec_options = [current_techspec] + techspec_options
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Techspec dropdown
        new_techspec = st.selectbox(
            "Technical Specification",
            techspec_options,
            index=techspec_options.index(current_techspec) if current_techspec in techspec_options else 0,
            key=f"edit_techspec_{component_id}",
        )
        
        # Volt dropdown - filtered on selected techspec
        if techspecs:
            volt_for_techspec = sorted(set(
                volt for ts, volt, kod, nv in techspecs 
                if ts == new_techspec
            ))
        else:
            volt_for_techspec = [current_volt] if current_volt else []
        
        if not volt_for_techspec:
            volt_for_techspec = [current_volt] if current_volt else [""]
        
        new_volt = st.selectbox(
            "Voltage",
            volt_for_techspec,
            index=volt_for_techspec.index(current_volt) if current_volt in volt_for_techspec else 0,
            key=f"edit_volt_{component_id}",
        )
        
        # Commissioning year
        new_year = st.number_input(
            "Commissioning Year",
            min_value=1910,
            max_value=2023,
            value=int(current_year) if current_year > 0 else 2000,
            key=f"edit_year_{component_id}",
        )
    
    with col2:
        # Quantity
        new_count = st.number_input(
            "Quantity (km or units)",
            min_value=0.0001,
            value=float(current_count),
            format="%.4f",
            key=f"edit_count_{component_id}",
        )
        
        # Calculate new normvärde based on techspec+volt
        new_normvärde = current_normvärde
        if techspecs:
            for ts, volt, kod, nv in techspecs:
                if ts == new_techspec and volt == new_volt:
                    new_normvärde = nv
                    break
        
        # Display normvärde (read-only)
        st.text_input(
            "Normvärde (SEK/unit)",
            value=f"{new_normvärde:,.0f}",
            disabled=True,
            key=f"edit_normvärde_display_{component_id}",
        )
        
        # Calculate and display new NUAV
        new_nuav = new_normvärde * new_count
        st.text_input(
            "Calculated NUAV (SEK)",
            value=f"{new_nuav:,.0f}",
            disabled=True,
            key=f"edit_nuav_display_{component_id}",
        )
    
    # Display change
    nuav_change = new_nuav - current_nuav
    if abs(nuav_change) > 0.01:
        delta_pct = (nuav_change / current_nuav * 100) if current_nuav != 0 else 0
        st.info(f"NUAV change: {nuav_change:+,.0f} SEK ({delta_pct:+.1f}%)")
    
    # Buttons
    col_save, col_cancel, col_delete = st.columns([1, 1, 1])
    
    with col_save:
        if st.button("Save Changes", type="primary", key=f"save_{component_id}"):
            _save_normvärderad_edit(
                component_id=component_id,
                new_techspec=new_techspec,
                new_volt=new_volt,
                new_count=new_count,
                new_year=new_year,
                new_normvärde=new_normvärde,
            )
            st.success("Changes saved!")
            st.rerun()
    
    with col_cancel:
        if st.button("Cancel", key=f"cancel_{component_id}"):
            st.rerun()
    
    with col_delete:
        if st.button("Remove Component", type="secondary", key=f"delete_{component_id}"):
            remove_component(component_id)
            st.warning("Component marked for removal")
            st.rerun()


def _save_normvärderad_edit(
    component_id: int,
    new_techspec: str,
    new_volt: str,
    new_count: float,
    new_year: int,
    new_normvärde: float,
):
    """Save changes for normvärde component."""
    df = get_modified_components()
    if df is None:
        return
    
    mask = df['id_component'] == component_id
    if not mask.any():
        return
    
    # Update fields
    df.loc[mask, 'techspec'] = new_techspec
    df.loc[mask, 'volt'] = new_volt
    df.loc[mask, 'count_comp'] = new_count
    df.loc[mask, 'time_from'] = year_to_time_code(new_year)
    df.loc[mask, 'normvärde'] = new_normvärde
    
    # NUAV is calculated automatically by prepare_capbase_for_calculations()
    # but we update here for immediate feedback
    df.loc[mask, 'nuav_2022'] = new_normvärde * new_count
    
    # Find and update id_comptype if possible
    for kod, nv in NORMVÄRDEN.items():
        if nv.techspec == new_techspec and nv.volt == new_volt:
            df.loc[mask, 'id_comptype'] = kod
            break
    
    update_modified_components(df)


# =============================================================================
# TAB 2: ALTERNATIVE METHODS (vtype=1,2)
# =============================================================================

def _render_övriga_metoder_tab():
    """Render tab for alternative valuation methods."""
    st.subheader("Alternative Valuation Methods")
    st.caption("Components valued using annat skäligt värde (vtype=1) or anskaffningsvärde (vtype=2)")
    
    df = get_övriga_metoder()
    
    if df.empty:
        st.info("No components with alternative valuation methods.")
        return
    
    # Separate by vtype
    df_vtype1 = df[df['vtype'] == VType.ANNAT_SKÄLIGT_VÄRDE]
    df_vtype2 = df[df['vtype'] == VType.ANSKAFFNINGSVÄRDE]
    
    # Display statistics
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Annat skäligt värde", f"{len(df_vtype1)} components")
    with col2:
        st.metric("Anskaffningsvärde", f"{len(df_vtype2)} components")
    
    # Table for vtype=1
    if not df_vtype1.empty:
        st.markdown("#### Annat skäligt värde (vtype=1)")
        st.caption("NUAV = annat skäligt värde × count")
        _render_vtype1_table_and_form(df_vtype1)
    
    # Table for vtype=2
    if not df_vtype2.empty:
        st.markdown("#### Anskaffningsvärde (vtype=2)")
        st.caption("NUAV = reported NUAV (indexed)")
        _render_vtype2_table_and_form(df_vtype2)
    
    # Add new component
    with st.expander("Add Component (Annat skäligt värde)", expanded=False):
        _render_add_vtype1_form()


@st.fragment
def _render_vtype1_table_and_form(df: pd.DataFrame):
    """Render table for vtype=1 components."""
    df_display = df[['id_component', 'cat', 'subcat', 'annatskäligtvärde', 'count_comp', 'nuav_2022', 'time_from']].copy()
    df_display['year'] = df_display['time_from'].apply(time_code_to_year)
    df_display['nuav_kkr'] = df_display['nuav_2022'] / 1_000
    df_display['värde_kkr'] = df_display['annatskäligtvärde'] / 1_000
    
    df_display = df_display.rename(columns={
        'id_component': 'ID',
        'cat': 'Category',
        'subcat': 'Subcategory',
        'värde_kkr': 'Value/Unit (kSEK)',
        'count_comp': 'Count',
        'nuav_kkr': 'NUAV (kSEK)',
        'year': 'Commissioned',
    })
    
    display_cols = ['ID', 'Category', 'Subcategory', 'Value/Unit (kSEK)', 'Count', 'NUAV (kSEK)', 'Commissioned']
    
    event = st.dataframe(
        df_display[display_cols],
        width='stretch',
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key="vtype1_table_select",
    )
    
    selected_rows = event.selection.rows if event.selection else []
    
    if selected_rows:
        selected_idx = selected_rows[0]
        selected_id = df_display.iloc[selected_idx]['ID']
        original_row = df[df['id_component'] == selected_id].iloc[0]
        
        st.markdown("---")
        _render_vtype1_edit_form(original_row, selected_id)


def _render_vtype1_edit_form(row: pd.Series, component_id: int):
    """Edit form for vtype=1."""
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Category
        cat_options = get_category_options()
        current_cat = int(row['cat_encode'])
        cat_list = list(cat_options.keys())
        
        new_cat = st.selectbox(
            "Category",
            cat_list,
            index=cat_list.index(current_cat) if current_cat in cat_list else 0,
            format_func=lambda x: cat_options[x],
            key=f"edit_cat_v1_{component_id}",
        )
        
        # Subcategory (free text)
        new_subcat = st.text_input(
            "Subcategory",
            value=row['subcat'] if pd.notna(row['subcat']) else "",
            key=f"edit_subcat_v1_{component_id}",
        )
        
        # Commissioning year
        current_year = time_code_to_year(row['time_from'])
        new_year = st.number_input(
            "Commissioning Year",
            min_value=1910,
            max_value=2023,
            value=int(current_year) if current_year > 0 else 2000,
            key=f"edit_year_v1_{component_id}",
        )
    
    with col2:
        # Value per unit
        new_värde = st.number_input(
            "Annat skäligt värde (SEK/unit)",
            min_value=0.0,
            value=float(row['annatskäligtvärde']) if pd.notna(row['annatskäligtvärde']) else 0.0,
            format="%.0f",
            key=f"edit_värde_v1_{component_id}",
        )
        
        # Count
        new_count = st.number_input(
            "Count",
            min_value=0.0001,
            value=float(row['count_comp']),
            format="%.4f",
            key=f"edit_count_v1_{component_id}",
        )
        
        # Calculated NUAV
        new_nuav = new_värde * new_count
        st.text_input(
            "Calculated NUAV (SEK)",
            value=f"{new_nuav:,.0f}",
            disabled=True,
            key=f"edit_nuav_v1_{component_id}",
        )
    
    col_save, col_cancel = st.columns(2)
    
    with col_save:
        if st.button("Save", type="primary", key=f"save_v1_{component_id}"):
            df = get_modified_components()
            mask = df['id_component'] == component_id
            df.loc[mask, 'cat_encode'] = new_cat
            df.loc[mask, 'cat'] = KATEGORIER[new_cat].namn
            df.loc[mask, 'subcat'] = new_subcat
            df.loc[mask, 'annatskäligtvärde'] = new_värde
            df.loc[mask, 'count_comp'] = new_count
            df.loc[mask, 'time_from'] = year_to_time_code(new_year)
            df.loc[mask, 'nuav_2022'] = new_nuav
            update_modified_components(df)
            st.success("Saved!")
            st.rerun()
    
    with col_cancel:
        if st.button("Cancel", key=f"cancel_v1_{component_id}"):
            st.rerun()


@st.fragment
def _render_vtype2_table_and_form(df: pd.DataFrame):
    """Render table for vtype=2 components."""
    df_display = df[['id_component', 'cat', 'subcat', 'anskaffningsvärde', 'rapporteradnuav', 'time_from']].copy()
    df_display['year'] = df_display['time_from'].apply(time_code_to_year)
    df_display['nuav_kkr'] = df_display['rapporteradnuav'] / 1_000
    
    df_display = df_display.rename(columns={
        'id_component': 'ID',
        'cat': 'Category',
        'subcat': 'Subcategory',
        'anskaffningsvärde': 'Anskaffningsvärde',
        'nuav_kkr': 'NUAV (kSEK)',
        'year': 'Acquisition Year',
    })
    
    display_cols = ['ID', 'Category', 'Subcategory', 'Anskaffningsvärde', 'NUAV (kSEK)', 'Acquisition Year']
    
    event = st.dataframe(
        df_display[display_cols],
        width='stretch',
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key="vtype2_table_select",
    )
    
    selected_rows = event.selection.rows if event.selection else []
    
    if selected_rows:
        selected_idx = selected_rows[0]
        selected_id = df_display.iloc[selected_idx]['ID']
        original_row = df[df['id_component'] == selected_id].iloc[0]
        
        st.markdown("---")
        _render_vtype2_edit_form(original_row, selected_id)


def _render_vtype2_edit_form(row: pd.Series, component_id: int):
    """Edit form for vtype=2."""
    
    col1, col2 = st.columns(2)
    
    with col1:
        current_year = time_code_to_year(row['time_from'])
        new_year = st.number_input(
            "Acquisition Year",
            min_value=1910,
            max_value=2023,
            value=int(current_year) if current_year > 0 else 2000,
            key=f"edit_year_v2_{component_id}",
        )
        
        new_anskaffning = st.number_input(
            "Original acquisition value (SEK)",
            min_value=0.0,
            value=float(row['anskaffningsvärde']) if pd.notna(row['anskaffningsvärde']) else 0.0,
            format="%.0f",
            key=f"edit_anskaffning_v2_{component_id}",
        )
    
    with col2:
        new_nuav = st.number_input(
            "Reported NUAV (SEK)",
            min_value=0.0,
            value=float(row['rapporteradnuav']) if pd.notna(row['rapporteradnuav']) else 0.0,
            format="%.0f",
            key=f"edit_nuav_v2_{component_id}",
            help="Acquisition value indexed to 2022 price level using BKI",
        )
    
    col_save, col_cancel = st.columns(2)
    
    with col_save:
        if st.button("Save", type="primary", key=f"save_v2_{component_id}"):
            df = get_modified_components()
            mask = df['id_component'] == component_id
            df.loc[mask, 'anskaffningsvärde'] = new_anskaffning
            df.loc[mask, 'rapporteradnuav'] = new_nuav
            df.loc[mask, 'time_from'] = year_to_time_code(new_year)
            df.loc[mask, 'nuav_2022'] = new_nuav
            update_modified_components(df)
            st.success("Saved!")
            st.rerun()
    
    with col_cancel:
        if st.button("Cancel", key=f"cancel_v2_{component_id}"):
            st.rerun()


@st.fragment
def _render_add_vtype1_form():
    """Form for adding component with annat skäligt värde."""
    
    col1, col2 = st.columns(2)
    
    with col1:
        cat_options = get_category_options()
        new_cat = st.selectbox(
            "Category",
            list(cat_options.keys()),
            format_func=lambda x: cat_options[x],
            key="add_v1_cat",
        )
        
        new_subcat = st.text_input(
            "Subcategory",
            value="",
            key="add_v1_subcat",
        )
        
        new_year = st.number_input(
            "Commissioning Year",
            min_value=1910,
            max_value=2023,
            value=2020,
            key="add_v1_year",
        )
    
    with col2:
        new_värde = st.number_input(
            "Annat skäligt värde (SEK/unit)",
            min_value=0.0,
            value=100000.0,
            format="%.0f",
            key="add_v1_värde",
        )
        
        new_count = st.number_input(
            "Count",
            min_value=0.0001,
            value=1.0,
            format="%.4f",
            key="add_v1_count",
        )
        
        # Display calculated NUAV
        st.text_input(
            "Calculated NUAV",
            value=f"{new_värde * new_count:,.0f} SEK",
            disabled=True,
        )
    
    if st.button("Add Component", type="primary", key="add_v1_submit"):
        if new_subcat.strip() == "":
            st.error("Enter subcategory")
        else:
            new_id = add_component_vtype1(
                cat_encode=new_cat,
                subcat=new_subcat,
                annatskäligtvärde=new_värde,
                count_comp=new_count,
                time_from=year_to_time_code(new_year),
            )
            st.success(f"Component added (ID: {new_id})")
            st.rerun()


# =============================================================================
# TAB 3: INVESTMENTS (vtype=5)
# =============================================================================

def _render_investeringar_tab():
    """Render tab for investments and retirements."""
    st.subheader("Investments and Retirements")
    st.caption("Planned changes during regulatory period 2024-2027")
    
    df = get_investeringar()
    
    # Separate investments and retirements
    if not df.empty:
        df_inv = df[df['invest'] == 1]
        df_utr = df[df['invest'] == -1]
    else:
        df_inv = pd.DataFrame()
        df_utr = pd.DataFrame()
    
    # Statistics
    col1, col2, col3 = st.columns(3)
    with col1:
        inv_sum = df_inv['nuav_2022'].sum() / 1_000_000 if not df_inv.empty else 0
        st.metric("Investments", f"{len(df_inv)} components", f"+{inv_sum:.1f} MSEK")
    with col2:
        utr_sum = abs(df_utr['nuav_2022'].sum()) / 1_000_000 if not df_utr.empty else 0
        st.metric("Retirements", f"{len(df_utr)} components", f"-{utr_sum:.1f} MSEK")
    with col3:
        netto = inv_sum - utr_sum
        st.metric("Net", f"{netto:+.1f} MSEK")
    
    # Table
    if not df.empty:
        _render_investment_table_and_form(df)
    else:
        st.info("No investments or retirements registered.")
    
    st.divider()
    
    # Add new
    col_inv, col_utr = st.columns(2)
    
    with col_inv:
        with st.expander("Add Investment", expanded=False):
            _render_add_investment_form(is_retirement=False)
    
    with col_utr:
        with st.expander("Add Retirement", expanded=False):
            _render_add_investment_form(is_retirement=True)


@st.fragment
def _render_investment_table_and_form(df: pd.DataFrame):
    """Render table for investments/retirements."""
    
    df_display = df[['id_component', 'cat', 'subcat', 'invest', 'value_invest', 'time_invest']].copy()
    df_display['typ'] = df_display['invest'].apply(lambda x: "Investment" if x == 1 else "Retirement")
    df_display['värde_mkr'] = df_display['value_invest'].abs() / 1_000_000
    df_display['halvår'] = df_display['time_invest'].apply(
        lambda x: TIMECODE_TO_HALFYEAR.get(int(x), f"Code {x}") if pd.notna(x) else ""
    )
    
    df_display = df_display.rename(columns={
        'id_component': 'ID',
        'cat': 'Category',
        'subcat': 'Subcategory',
        'typ': 'Type',
        'värde_mkr': 'Value (MSEK)',
        'halvår': 'Half-Year',
    })
    
    display_cols = ['ID', 'Type', 'Category', 'Subcategory', 'Value (MSEK)', 'Half-Year']
    
    event = st.dataframe(
        df_display[display_cols],
        width='stretch',
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key="invest_table_select",
    )
    
    selected_rows = event.selection.rows if event.selection else []
    
    if selected_rows:
        selected_idx = selected_rows[0]
        selected_id = df_display.iloc[selected_idx]['ID']
        original_row = df[df['id_component'] == selected_id].iloc[0]
        
        st.markdown("---")
        _render_investment_edit_form(original_row, selected_id)


def _render_investment_edit_form(row: pd.Series, component_id: int):
    """Edit form for investment/retirement."""
    
    is_retirement = row['invest'] == -1
    typ_label = "Retirement" if is_retirement else "Investment"
    
    st.markdown(f"**Edit {typ_label} ID {component_id}**")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Category
        cat_options = get_category_options()
        current_cat = int(row['cat_encode']) if pd.notna(row['cat_encode']) else 3
        cat_list = list(cat_options.keys())
        
        new_cat = st.selectbox(
            "Category",
            cat_list,
            index=cat_list.index(current_cat) if current_cat in cat_list else 0,
            format_func=lambda x: cat_options[x],
            key=f"edit_cat_inv_{component_id}",
        )
        
        new_subcat = st.text_input(
            "Subcategory",
            value=row['subcat'] if pd.notna(row['subcat']) else "",
            key=f"edit_subcat_inv_{component_id}",
        )
    
    with col2:
        # Half-year
        halfyear_options = list(HALFYEAR_TO_TIMECODE.keys())
        current_halfyear = TIMECODE_TO_HALFYEAR.get(int(row['time_invest']), halfyear_options[0])
        
        new_halfyear = st.selectbox(
            "Half-Year",
            halfyear_options,
            index=halfyear_options.index(current_halfyear) if current_halfyear in halfyear_options else 0,
            key=f"edit_halfyear_inv_{component_id}",
        )
        
        # Value (always positive in input)
        current_value = abs(row['value_invest']) if pd.notna(row['value_invest']) else 0
        new_value = st.number_input(
            "Value (SEK)",
            min_value=0.0,
            value=float(current_value),
            format="%.0f",
            key=f"edit_value_inv_{component_id}",
        )
    
    col_save, col_cancel, col_delete = st.columns(3)
    
    with col_save:
        if st.button("Save", type="primary", key=f"save_inv_{component_id}"):
            df = get_modified_components()
            mask = df['id_component'] == component_id
            
            invest_sign = -1 if is_retirement else 1
            
            df.loc[mask, 'cat_encode'] = new_cat
            df.loc[mask, 'cat'] = KATEGORIER[new_cat].namn
            df.loc[mask, 'subcat'] = new_subcat
            df.loc[mask, 'time_invest'] = HALFYEAR_TO_TIMECODE[new_halfyear]
            df.loc[mask, 'value_invest'] = new_value * invest_sign
            df.loc[mask, 'nuav_2022'] = new_value * invest_sign
            
            update_modified_components(df)
            st.success("Saved!")
            st.rerun()
    
    with col_cancel:
        if st.button("Cancel", key=f"cancel_inv_{component_id}"):
            st.rerun()
    
    with col_delete:
        if st.button("Remove", type="secondary", key=f"delete_inv_{component_id}"):
            remove_component(component_id)
            st.warning("Marked for removal")
            st.rerun()


@st.fragment
def _render_add_investment_form(is_retirement: bool):
    """Form for adding investment or retirement."""
    
    typ_label = "retirement" if is_retirement else "investment"
    
    col1, col2 = st.columns(2)
    
    with col1:
        cat_options = get_category_options()
        new_cat = st.selectbox(
            "Category",
            list(cat_options.keys()),
            format_func=lambda x: cat_options[x],
            key=f"add_{'utr' if is_retirement else 'inv'}_cat",
        )
        
        new_subcat = st.text_input(
            "Subcategory",
            value="",
            key=f"add_{'utr' if is_retirement else 'inv'}_subcat",
        )
    
    with col2:
        halfyear_options = list(HALFYEAR_TO_TIMECODE.keys())
        new_halfyear = st.selectbox(
            "Half-Year",
            halfyear_options,
            key=f"add_{'utr' if is_retirement else 'inv'}_halfyear",
        )
        
        new_value = st.number_input(
            "Value (SEK)",
            min_value=0.0,
            value=1000000.0,
            format="%.0f",
            key=f"add_{'utr' if is_retirement else 'inv'}_value",
        )
    
    if st.button(f"Add {typ_label}", type="primary", key=f"add_{'utr' if is_retirement else 'inv'}_submit"):
        if new_subcat.strip() == "":
            st.error("Enter subcategory")
        else:
            new_id = add_investment(
                cat_encode=new_cat,
                subcat=new_subcat,
                value=new_value,
                time_invest=HALFYEAR_TO_TIMECODE[new_halfyear],
                is_retirement=is_retirement,
            )
            st.success(f"{typ_label.capitalize()} added (ID: {new_id})")
            st.rerun()


# =============================================================================
# BULK ACTIONS
# =============================================================================

@st.fragment
def _render_count_scaling_form(
    vtype: int,
    cat_filter: Optional[str] = None,
    subcat_filter: Optional[str] = None,
):
    """Form for scaling count_comp."""
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        scale_pct = st.number_input(
            "Scaling factor (%)",
            min_value=-99.0,
            max_value=1000.0,
            value=0.0,
            step=5.0,
            format="%.1f",
            key=f"scale_pct_{vtype}",
            help="+10% = increase quantity by 10%",
        )
    
    with col2:
        scope_label = "current filter" if cat_filter else "all"
        st.caption(f"Scope: {scope_label}")
    
    with col3:
        if st.button("Apply", key=f"scale_btn_{vtype}"):
            if abs(scale_pct) > 0.001:
                # Get cat_encode from cat name
                cat_encode = None
                if cat_filter:
                    for ce, kat in KATEGORIER.items():
                        if kat.namn == cat_filter:
                            cat_encode = ce
                            break
                
                n_scaled = apply_count_scaling(
                    multiplier=1 + (scale_pct / 100),
                    cat_encode=cat_encode,
                    subcat=subcat_filter,
                    vtype=vtype,
                )
                st.success(f"Scaled {n_scaled} components by {scale_pct:+.1f}%")
                st.rerun()


# =============================================================================
# CHANGE INDICATOR
# =============================================================================

def _render_change_indicator():
    """Render change indicator at the bottom."""
    
    if has_changes():
        summary = get_change_summary()
        
        msg_parts = []
        if summary['n_modified'] > 0:
            msg_parts.append(f"{summary['n_modified']} modified")
        if summary['n_added'] > 0:
            msg_parts.append(f"{summary['n_added']} added")
        if summary['n_removed'] > 0:
            msg_parts.append(f"{summary['n_removed']} removed")
        
        nuav_str = f"NUAV: {summary['nuav_change_mkr']:+.2f} MSEK"
        
        st.success(f"Changes: {' | '.join(msg_parts)} | {nuav_str}")
    else:
        st.caption("No changes made")


def _clear_edit_state():
    """Clear edit-related session state."""
    keys_to_clear = [k for k in st.session_state.keys() if k.startswith(('edit_', 'add_', 'scale_'))]
    for key in keys_to_clear:
        del st.session_state[key]
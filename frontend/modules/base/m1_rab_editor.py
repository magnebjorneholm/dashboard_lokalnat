"""
m1_rab_editor.py

RAB editor (Regulatory Asset Base) for editing capital base.

UPDATED: Now shows only ordinarie components in UI.
Tail components are hidden but still included in calculations.

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
    # Per vtype (filtered for display)
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
    render_summary_metrics_with_classification,
    render_classification_info,
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
    
    # Summary with classification info
    _render_header_summary()
    
    # Show info about hidden tail components
    render_classification_info()
    
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
# SUMMARY (UPDATED with classification info)
# =============================================================================

def _render_header_summary():
    """Render summary at the top with classification breakdown."""
    metrics = render_summary_metrics_with_classification(show_delta=True)
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric(
            "Ordinarie",
            f"{metrics['n_ordinarie']:,}",
            help="Components within economic lifetime (age <= ekdep)"
        )
    
    with col2:
        st.metric(
            "Investments",
            f"{metrics['n_investments']:,}",
            help="Planned investments and retirements 2024-2027"
        )
    
    with col3:
        st.metric(
            "Total NUAV",
            f"{metrics['total_nuav_mkr']:.1f} MSEK",
            help="Total replacement value including tail components"
        )
    
    with col4:
        delta = metrics['delta_nuav_mkr']
        delta_str = f"{delta:+.2f} MSEK" if abs(delta) > 0.001 else None
        st.metric(
            "Change",
            f"{delta:+.2f} MSEK" if delta_str else "0",
            delta=delta_str
        )
    
    with col5:
        if st.button("Reset All Changes", type="secondary"):
            reset_rab_editor()
            _clear_edit_state()
            st.rerun()
    
    # Show tail info in caption
    if metrics['n_tail'] > 0:
        st.caption(
            f"Hidden: {metrics['n_tail']} tail components "
            f"({metrics['nuav_tail_mkr']:.1f} MSEK) - included in calculations"
        )


# =============================================================================
# TAB 1: NORMVÄRDE (vtype=4)
# =============================================================================

def _render_normvärderade_tab():
    """Render tab for normvärde components."""
    st.subheader("Normvärde Components")
    st.caption("Components valued using Ei normvärden. NUAV = normvärde x quantity. Showing ordinarie only.")
    
    df = get_normvärderade()  # Already filtered to ordinarie
    
    if df.empty:
        st.info("No ordinarie normvärde components.")
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
    
    st.caption(f"Showing {len(df_filtered)} of {len(df)} ordinarie components")
    
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
# TAB 2: ÖVRIGA METODER (vtype=1, 2)
# =============================================================================

def _render_övriga_metoder_tab():
    """Render tab for annat skäligt värde and anskaffningsvärde components."""
    st.subheader("Alternative Valuation Methods")
    st.caption("Components valued using annat skäligt värde or anskaffningsvärde. Showing ordinarie only.")
    
    df = get_övriga_metoder()  # Already filtered to ordinarie
    
    if df.empty:
        st.info("No ordinarie components with alternative valuation methods.")
        return
    
    # Sub-tabs for vtype 1 and 2
    vtype1_df = df[df['vtype'] == VType.ANNAT_SKÄLIGT_VÄRDE]
    vtype2_df = df[df['vtype'] == VType.ANSKAFFNINGSVÄRDE]
    
    sub_tab1, sub_tab2 = st.tabs([
        f"Annat skäligt värde ({len(vtype1_df)})",
        f"Anskaffningsvärde ({len(vtype2_df)})",
    ])
    
    with sub_tab1:
        if vtype1_df.empty:
            st.info("No components")
        else:
            _render_vtype1_table_and_form(vtype1_df)
    
    with sub_tab2:
        if vtype2_df.empty:
            st.info("No components")
        else:
            _render_vtype2_table_and_form(vtype2_df)


@st.fragment
def _render_vtype1_table_and_form(df: pd.DataFrame):
    """Render table and form for annat skäligt värde (vtype=1)."""
    
    df_display = df[['id_component', 'cat', 'subcat', 'annatskäligtvärde', 'count_comp', 'nuav_2022', 'time_from']].copy()
    df_display['year'] = df_display['time_from'].apply(time_code_to_year)
    df_display['nuav_mkr'] = df_display['nuav_2022'] / 1_000_000
    df_display['värde_kkr'] = df_display['annatskäligtvärde'] / 1_000
    
    df_display = df_display.rename(columns={
        'id_component': 'ID',
        'cat': 'Category',
        'subcat': 'Subcategory',
        'värde_kkr': 'Value/unit (kSEK)',
        'count_comp': 'Quantity',
        'nuav_mkr': 'NUAV (MSEK)',
        'year': 'Commissioned',
    })
    
    display_cols = ['ID', 'Category', 'Subcategory', 'Value/unit (kSEK)', 'Quantity', 'NUAV (MSEK)', 'Commissioned']
    
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
    """Edit form for annat skäligt värde."""
    
    st.markdown(f"**Edit Component ID {component_id}**")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Category (read-only display)
        st.text_input(
            "Category",
            value=row['cat'] if pd.notna(row['cat']) else "",
            disabled=True,
            key=f"edit_cat_v1_{component_id}",
        )
        
        st.text_input(
            "Subcategory",
            value=row['subcat'] if pd.notna(row['subcat']) else "",
            disabled=True,
            key=f"edit_subcat_v1_{component_id}",
        )
        
        new_year = st.number_input(
            "Commissioning Year",
            min_value=1910,
            max_value=2023,
            value=int(time_code_to_year(row['time_from'])),
            key=f"edit_year_v1_{component_id}",
        )
    
    with col2:
        new_value = st.number_input(
            "Value per unit (SEK)",
            min_value=0.0,
            value=float(row['annatskäligtvärde']) if pd.notna(row['annatskäligtvärde']) else 0.0,
            format="%.0f",
            key=f"edit_value_v1_{component_id}",
        )
        
        new_count = st.number_input(
            "Quantity",
            min_value=0.0001,
            value=float(row['count_comp']),
            format="%.4f",
            key=f"edit_count_v1_{component_id}",
        )
        
        new_nuav = new_value * new_count
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
            
            df.loc[mask, 'annatskäligtvärde'] = new_value
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
    """Render table and form for anskaffningsvärde (vtype=2)."""
    
    df_display = df[['id_component', 'cat', 'subcat', 'rapporteradnuav', 'nuav_2022', 'time_from']].copy()
    df_display['year'] = df_display['time_from'].apply(time_code_to_year)
    df_display['nuav_mkr'] = df_display['nuav_2022'] / 1_000_000
    
    df_display = df_display.rename(columns={
        'id_component': 'ID',
        'cat': 'Category',
        'subcat': 'Subcategory',
        'rapporteradnuav': 'Reported NUAV',
        'nuav_mkr': 'NUAV (MSEK)',
        'year': 'Commissioned',
    })
    
    display_cols = ['ID', 'Category', 'Subcategory', 'NUAV (MSEK)', 'Commissioned']
    
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
    """Edit form for anskaffningsvärde."""
    
    st.markdown(f"**Edit Component ID {component_id}**")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.text_input(
            "Category",
            value=row['cat'] if pd.notna(row['cat']) else "",
            disabled=True,
            key=f"edit_cat_v2_{component_id}",
        )
        
        st.text_input(
            "Subcategory",
            value=row['subcat'] if pd.notna(row['subcat']) else "",
            disabled=True,
            key=f"edit_subcat_v2_{component_id}",
        )
    
    with col2:
        new_nuav = st.number_input(
            "Reported NUAV (SEK)",
            min_value=0.0,
            value=float(row['rapporteradnuav']) if pd.notna(row['rapporteradnuav']) else 0.0,
            format="%.0f",
            key=f"edit_nuav_v2_{component_id}",
        )
        
        new_year = st.number_input(
            "Commissioning Year",
            min_value=1910,
            max_value=2023,
            value=int(time_code_to_year(row['time_from'])),
            key=f"edit_year_v2_{component_id}",
        )
    
    col_save, col_cancel = st.columns(2)
    
    with col_save:
        if st.button("Save", type="primary", key=f"save_v2_{component_id}"):
            df = get_modified_components()
            mask = df['id_component'] == component_id
            
            df.loc[mask, 'rapporteradnuav'] = new_nuav
            df.loc[mask, 'time_from'] = year_to_time_code(new_year)
            df.loc[mask, 'nuav_2022'] = new_nuav
            
            update_modified_components(df)
            st.success("Saved!")
            st.rerun()
    
    with col_cancel:
        if st.button("Cancel", key=f"cancel_v2_{component_id}"):
            st.rerun()


# =============================================================================
# TAB 3: INVESTERINGAR (vtype=5)
# =============================================================================

def _render_investeringar_tab():
    """Render tab for investments and retirements."""
    st.subheader("Investments and Retirements")
    st.caption("Planned changes during regulatory period 2024-2027")
    
    df = get_investeringar()
    
    # Separate investments and retirements
    if not df.empty:
        inv_df = df[df['invest'] == 1]
        ret_df = df[df['invest'] == -1]
    else:
        inv_df = pd.DataFrame()
        ret_df = pd.DataFrame()
    
    # Statistics metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        inv_sum = inv_df['nuav_2022'].sum() / 1_000_000 if not inv_df.empty else 0
        st.metric("Investments", f"{len(inv_df)} components", f"+{inv_sum:.1f} MSEK")
    with col2:
        ret_sum = abs(ret_df['nuav_2022'].sum()) / 1_000_000 if not ret_df.empty else 0
        st.metric("Retirements", f"{len(ret_df)} components", f"-{ret_sum:.1f} MSEK")
    with col3:
        netto = inv_sum - ret_sum
        st.metric("Net", f"{netto:+.1f} MSEK")
    
    # Tabs for investments and retirements
    if df.empty:
        st.info("No investments or retirements planned.")
    else:
        inv_tab, ret_tab = st.tabs([
            f"Investments ({len(inv_df)})",
            f"Retirements ({len(ret_df)})",
        ])
        
        with inv_tab:
            if inv_df.empty:
                st.info("No investments")
            else:
                _render_investment_table_and_form(inv_df, key_suffix="inv")
        
        with ret_tab:
            if ret_df.empty:
                st.info("No retirements")
            else:
                _render_investment_table_and_form(ret_df, key_suffix="ret")
    
    st.divider()
    
    # Add new - at the bottom
    col_inv, col_ret = st.columns(2)
    
    with col_inv:
        with st.expander("Add Investment", expanded=False):
            _render_add_investment_form(is_retirement=False)
    
    with col_ret:
        with st.expander("Add Retirement", expanded=False):
            _render_add_investment_form(is_retirement=True)


@st.fragment
def _render_investment_table_and_form(df: pd.DataFrame, key_suffix: str = ""):
    """Render table and edit form for investments/retirements."""
    
    df_display = df[['id_component', 'cat', 'subcat', 'value_invest', 'invest', 'time_invest']].copy()
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
        key=f"invest_table_select_{key_suffix}",
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
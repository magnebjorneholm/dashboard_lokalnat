"""
m1_rab_editor.py

RAB-editor (Regulatory Asset Base) för redigering av kapitalbas.

UI-struktur:
- Tre flikar baserat på vtype (Normvärderade, Övriga metoder, Investeringar)
- Read-only tabell med klickbar rad
- Redigeringsformulär med dynamiska dropdowns
- Snabbåtgärder för skalning

Integrerar med:
- rab_editor_utils.py: Session state-hantering
- rab_editor_variables.py: Variabeldefinitioner, validering
- normvärdeslista.py: Techspec-lookup
- prepare_capbase.py: NUAV-beräkning
"""

import streamlit as st
import pandas as pd
from typing import Dict, Any, Optional, List, Tuple

from calculations.rab_editor_utils import (
    # Initiering och data
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
    # Ändringar
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
    # Skalning
    apply_count_scaling,
    apply_value_scaling,
    # Hjälpfunktioner
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
# HUVUDFUNKTION
# =============================================================================

def render() -> Dict[str, Any]:
    """
    Renderar RAB-editor UI.
    
    Args:
        user_id_network: Användarens id_network
    
    Returns:
        Dict med konfiguration och ändringsindikator
    """
    config: Dict[str, Any] = {"rab_has_changes": False}
    
    
    user_id_network = get_user_id_network()
    
    if not user_id_network:
        st.warning("Välj företag i sidopanelen för att redigera kapitalbas.")
        return config
    
    # Ladda och initiera
    try:
        user_components = load_user_components(user_id_network)
        initialize_rab_editor(user_components, user_id_network)
    except Exception as e:
        st.error(f"Kunde inte ladda kapitalbasdata: {e}")
        return config
    
    # Sammanfattning
    _render_header_summary()
    
    st.divider()
    
    # Flikar per vtype
    vtype_stats = get_vtype_summary()

    pct_norm = vtype_stats.get(VType.NORMVÄRDE, {}).get('andel_pct', 0)
    pct_övriga = (
        vtype_stats.get(VType.ANNAT_SKÄLIGT_VÄRDE, {}).get('andel_pct', 0) +
        vtype_stats.get(VType.ANSKAFFNINGSVÄRDE, {}).get('andel_pct', 0)
    )
    pct_inv = vtype_stats.get(VType.INVESTERING, {}).get('andel_pct', 0)

    tab_norm, tab_övriga, tab_invest = st.tabs([
        f"Normvärderade ({pct_norm:.1f}%)",
        f"Övriga metoder ({pct_övriga:.1f}%)",
        f"Investeringar ({pct_inv:.1f}%)",
    ])
    
    with tab_norm:
        _render_normvärderade_tab()
    
    with tab_övriga:
        _render_övriga_metoder_tab()
    
    with tab_invest:
        _render_investeringar_tab()
    
    st.divider()
    
    # Ändringsindikator och återställ
    _render_change_indicator()
    config["rab_has_changes"] = has_changes()
    
    return config


# =============================================================================
# SAMMANFATTNING
# =============================================================================

def _render_header_summary():
    """Renderar sammanfattning högst upp."""
    metrics = render_summary_metrics(show_delta=True)
    vtype_summary = get_vtype_summary()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Komponenter", f"{metrics['n_components']:,}")
    
    with col2:
        st.metric("Total NUAV", f"{metrics['total_nuav_mkr']:.1f} Mkr")
    
    with col3:
        delta = metrics['delta_nuav_mkr']
        delta_str = f"{delta:+.2f} Mkr" if abs(delta) > 0.001 else None
        st.metric("Förändring", f"{delta:+.2f} Mkr" if delta_str else "0", delta=delta_str)
    
    with col4:
        if st.button("Återställ alla ändringar", type="secondary"):
            reset_rab_editor()
            _clear_edit_state()
            st.rerun()


# =============================================================================
# FLIK 1: NORMVÄRDERADE (vtype=4)
# =============================================================================

def _render_normvärderade_tab():
    """Renderar flik för normvärderade komponenter."""
    st.subheader("Normvärderade komponenter")
    st.caption("Komponenter värderade med Ei:s normvärden. NUAV = normvärde × antal/längd")
    
    df = get_normvärderade()
    
    if df.empty:
        st.info("Inga normvärderade komponenter.")
        return
    
    # Filter
    col_f1, col_f2 = st.columns(2)
    
    with col_f1:
        kategorier = ["Alla kategorier"] + sorted(df['cat'].dropna().unique().tolist())
        selected_cat = st.selectbox(
            "Kategori",
            kategorier,
            key="norm_filter_cat"
        )
    
    with col_f2:
        if selected_cat != "Alla kategorier":
            subcats = ["Alla subkategorier"] + sorted(
                df[df['cat'] == selected_cat]['subcat'].dropna().unique().tolist()
            )
        else:
            subcats = ["Alla subkategorier"]
        
        selected_subcat = st.selectbox(
            "Subkategori",
            subcats,
            key="norm_filter_subcat"
        )
    
    # Filtrera
    df_filtered = df.copy()
    if selected_cat != "Alla kategorier":
        df_filtered = df_filtered[df_filtered['cat'] == selected_cat]
    if selected_subcat != "Alla subkategorier":
        df_filtered = df_filtered[df_filtered['subcat'] == selected_subcat]
    
    st.caption(f"Visar {len(df_filtered)} av {len(df)} komponenter")
    
    # Tabell och redigeringsformulär
    _render_normvärderad_table_and_form(df_filtered, selected_cat, selected_subcat)
    
    # Snabbåtgärder
    with st.expander("Snabbåtgärder: Skala antal/längd", expanded=False):
        _render_count_scaling_form(
            vtype=VType.NORMVÄRDE,
            cat_filter=None if selected_cat == "Alla kategorier" else selected_cat,
            subcat_filter=None if selected_subcat == "Alla subkategorier" else selected_subcat,
        )


def _render_normvärderad_table_and_form(df: pd.DataFrame, cat_filter: str, subcat_filter: str):
    """Renderar tabell och redigeringsformulär för normvärderade."""
    
    # Förbered visningsdata
    df_display = df[['id_component', 'cat', 'subcat', 'techspec', 'volt', 'count_comp', 'normvärde', 'nuav_2022', 'time_from']].copy()
    df_display['year'] = df_display['time_from'].apply(time_code_to_year)
    df_display['nuav_mkr'] = df_display['nuav_2022'] / 1_000_000
    df_display['normvärde_kkr'] = df_display['normvärde'] / 1_000
    
    # Formatera för visning
    df_display = df_display.rename(columns={
        'id_component': 'ID',
        'cat': 'Kategori',
        'subcat': 'Subkategori', 
        'techspec': 'Teknisk spec',
        'volt': 'Spänning',
        'count_comp': 'Antal/längd',
        'normvärde_kkr': 'Normvärde (kkr)',
        'nuav_mkr': 'NUAV (Mkr)',
        'year': 'Idrifttagande',
    })
    
    # Välj kolumner att visa
    display_cols = ['ID', 'Subkategori', 'Teknisk spec', 'Spänning', 'Antal/längd', 'Normvärde (kkr)', 'NUAV (Mkr)', 'Idrifttagande']
    
    # Hantera radval
    edit_key = "norm_selected_id"
    
    # Visa tabell med on_select
    st.markdown("**Klicka på en rad för att redigera:**")
    
    event = st.dataframe(
        df_display[display_cols],
        width='stretch',
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key="norm_table_select",
    )
    
    # Hämta vald rad
    selected_rows = event.selection.rows if event.selection else []
    
    if selected_rows:
        selected_idx = selected_rows[0]
        selected_id = df_display.iloc[selected_idx]['ID']
        
        # Hämta originaldata för komponenten
        original_row = df[df['id_component'] == selected_id].iloc[0]
        
        st.markdown("---")
        st.markdown(f"**Redigera komponent ID {selected_id}**")
        
        _render_normvärderad_edit_form(original_row, selected_id)


def _render_normvärderad_edit_form(row: pd.Series, component_id: int):
    """Renderar redigeringsformulär för en normvärderad komponent."""
    
    kategori = row['cat']
    subkategori = row['subcat']
    current_techspec = row['techspec']
    current_volt = str(row['volt']) if pd.notna(row['volt']) else ""
    current_count = row['count_comp']
    current_year = time_code_to_year(row['time_from'])
    current_normvärde = row['normvärde']
    current_nuav = row['nuav_2022']
    
    # Hämta tillgängliga techspecs för denna kategori/subkategori
    techspecs = list_techspecs_for_category(kategori, subkategori)
    
    if not techspecs:
        st.warning(f"Inga techspecs hittades för {kategori} / {subkategori}")
        techspec_options = [current_techspec]
        volt_options = [current_volt]
    else:
        # Unika techspecs
        techspec_options = sorted(set(ts for ts, volt, kod, nv in techspecs))
        
        # Säkerställ att nuvarande finns med
        if current_techspec not in techspec_options:
            techspec_options = [current_techspec] + techspec_options
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Techspec dropdown
        new_techspec = st.selectbox(
            "Teknisk specifikation",
            techspec_options,
            index=techspec_options.index(current_techspec) if current_techspec in techspec_options else 0,
            key=f"edit_techspec_{component_id}",
        )
        
        # Volt dropdown - filtrerat på vald techspec
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
            "Spänning",
            volt_for_techspec,
            index=volt_for_techspec.index(current_volt) if current_volt in volt_for_techspec else 0,
            key=f"edit_volt_{component_id}",
        )
        
        # Idrifttagandeår
        new_year = st.number_input(
            "Idrifttagandeår",
            min_value=1910,
            max_value=2023,
            value=int(current_year) if current_year > 0 else 2000,
            key=f"edit_year_{component_id}",
        )
    
    with col2:
        # Antal/längd
        new_count = st.number_input(
            "Antal/längd (km eller st)",
            min_value=0.0001,
            value=float(current_count),
            format="%.4f",
            key=f"edit_count_{component_id}",
        )
        
        # Beräkna nytt normvärde baserat på techspec+volt
        new_normvärde = current_normvärde
        if techspecs:
            for ts, volt, kod, nv in techspecs:
                if ts == new_techspec and volt == new_volt:
                    new_normvärde = nv
                    break
        
        # Visa normvärde (read-only)
        st.text_input(
            "Normvärde (kr/enhet)",
            value=f"{new_normvärde:,.0f}",
            disabled=True,
            key=f"edit_normvärde_display_{component_id}",
        )
        
        # Beräkna och visa ny NUAV
        new_nuav = new_normvärde * new_count
        st.text_input(
            "Beräknad NUAV (kr)",
            value=f"{new_nuav:,.0f}",
            disabled=True,
            key=f"edit_nuav_display_{component_id}",
        )
    
    # Visa förändring
    nuav_change = new_nuav - current_nuav
    if abs(nuav_change) > 0.01:
        delta_pct = (nuav_change / current_nuav * 100) if current_nuav != 0 else 0
        st.info(f"NUAV-förändring: {nuav_change:+,.0f} kr ({delta_pct:+.1f}%)")
    
    # Knappar
    col_save, col_cancel, col_delete = st.columns([1, 1, 1])
    
    with col_save:
        if st.button("Spara ändringar", type="primary", key=f"save_{component_id}"):
            _save_normvärderad_edit(
                component_id=component_id,
                new_techspec=new_techspec,
                new_volt=new_volt,
                new_count=new_count,
                new_year=new_year,
                new_normvärde=new_normvärde,
            )
            st.success("Ändringar sparade!")
            st.rerun()
    
    with col_cancel:
        if st.button("Avbryt", key=f"cancel_{component_id}"):
            st.rerun()
    
    with col_delete:
        if st.button("Ta bort komponent", type="secondary", key=f"delete_{component_id}"):
            remove_component(component_id)
            st.warning("Komponent markerad för borttagning")
            st.rerun()


def _save_normvärderad_edit(
    component_id: int,
    new_techspec: str,
    new_volt: str,
    new_count: float,
    new_year: int,
    new_normvärde: float,
):
    """Sparar ändringar för normvärderad komponent."""
    df = get_modified_components()
    if df is None:
        return
    
    mask = df['id_component'] == component_id
    if not mask.any():
        return
    
    # Uppdatera fält
    df.loc[mask, 'techspec'] = new_techspec
    df.loc[mask, 'volt'] = new_volt
    df.loc[mask, 'count_comp'] = new_count
    df.loc[mask, 'time_from'] = year_to_time_code(new_year)
    df.loc[mask, 'normvärde'] = new_normvärde
    
    # NUAV beräknas automatiskt av prepare_capbase_for_calculations()
    # men vi uppdaterar här för direkt feedback
    df.loc[mask, 'nuav_2022'] = new_normvärde * new_count
    
    # Hitta och uppdatera id_comptype om möjligt
    for kod, nv in NORMVÄRDEN.items():
        if nv.techspec == new_techspec and nv.volt == new_volt:
            df.loc[mask, 'id_comptype'] = kod
            break
    
    update_modified_components(df)


# =============================================================================
# FLIK 2: ÖVRIGA METODER (vtype=1,2)
# =============================================================================

def _render_övriga_metoder_tab():
    """Renderar flik för övriga värderingsmetoder."""
    st.subheader("Övriga värderingsmetoder")
    st.caption("Komponenter värderade med annat skäligt värde (vtype=1) eller anskaffningsvärde (vtype=2)")
    
    df = get_övriga_metoder()
    
    if df.empty:
        st.info("Inga komponenter med övriga värderingsmetoder.")
        return
    
    # Separera per vtype
    df_vtype1 = df[df['vtype'] == VType.ANNAT_SKÄLIGT_VÄRDE]
    df_vtype2 = df[df['vtype'] == VType.ANSKAFFNINGSVÄRDE]
    
    # Visa statistik
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Annat skäligt värde", f"{len(df_vtype1)} st")
    with col2:
        st.metric("Anskaffningsvärde", f"{len(df_vtype2)} st")
    
    # Tabell för vtype=1
    if not df_vtype1.empty:
        st.markdown("#### Annat skäligt värde (vtype=1)")
        st.caption("NUAV = annat skäligt värde × antal")
        _render_vtype1_table_and_form(df_vtype1)
    
    # Tabell för vtype=2
    if not df_vtype2.empty:
        st.markdown("#### Anskaffningsvärde (vtype=2)")
        st.caption("NUAV = rapporterad NUAV (indexuppräknat)")
        _render_vtype2_table_and_form(df_vtype2)
    
    # Lägg till ny komponent
    with st.expander("Lägg till komponent (annat skäligt värde)", expanded=False):
        _render_add_vtype1_form()


def _render_vtype1_table_and_form(df: pd.DataFrame):
    """Renderar tabell för vtype=1 komponenter."""
    df_display = df[['id_component', 'cat', 'subcat', 'annatskäligtvärde', 'count_comp', 'nuav_2022', 'time_from']].copy()
    df_display['year'] = df_display['time_from'].apply(time_code_to_year)
    df_display['nuav_kkr'] = df_display['nuav_2022'] / 1_000
    df_display['värde_kkr'] = df_display['annatskäligtvärde'] / 1_000
    
    df_display = df_display.rename(columns={
        'id_component': 'ID',
        'cat': 'Kategori',
        'subcat': 'Subkategori',
        'värde_kkr': 'Värde/enhet (kkr)',
        'count_comp': 'Antal',
        'nuav_kkr': 'NUAV (kkr)',
        'year': 'Idrifttagande',
    })
    
    display_cols = ['ID', 'Kategori', 'Subkategori', 'Värde/enhet (kkr)', 'Antal', 'NUAV (kkr)', 'Idrifttagande']
    
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
    """Redigeringsformulär för vtype=1."""
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Kategori
        cat_options = get_category_options()
        current_cat = int(row['cat_encode'])
        cat_list = list(cat_options.keys())
        
        new_cat = st.selectbox(
            "Kategori",
            cat_list,
            index=cat_list.index(current_cat) if current_cat in cat_list else 0,
            format_func=lambda x: cat_options[x],
            key=f"edit_cat_v1_{component_id}",
        )
        
        # Subkategori (fritext)
        new_subcat = st.text_input(
            "Subkategori",
            value=row['subcat'] if pd.notna(row['subcat']) else "",
            key=f"edit_subcat_v1_{component_id}",
        )
        
        # Idrifttagandeår
        current_year = time_code_to_year(row['time_from'])
        new_year = st.number_input(
            "Idrifttagandeår",
            min_value=1910,
            max_value=2023,
            value=int(current_year) if current_year > 0 else 2000,
            key=f"edit_year_v1_{component_id}",
        )
    
    with col2:
        # Värde per enhet
        new_värde = st.number_input(
            "Annat skäligt värde (kr/enhet)",
            min_value=0.0,
            value=float(row['annatskäligtvärde']) if pd.notna(row['annatskäligtvärde']) else 0.0,
            format="%.0f",
            key=f"edit_värde_v1_{component_id}",
        )
        
        # Antal
        new_count = st.number_input(
            "Antal",
            min_value=0.0001,
            value=float(row['count_comp']),
            format="%.4f",
            key=f"edit_count_v1_{component_id}",
        )
        
        # Beräknad NUAV
        new_nuav = new_värde * new_count
        st.text_input(
            "Beräknad NUAV (kr)",
            value=f"{new_nuav:,.0f}",
            disabled=True,
            key=f"edit_nuav_v1_{component_id}",
        )
    
    col_save, col_cancel = st.columns(2)
    
    with col_save:
        if st.button("Spara", type="primary", key=f"save_v1_{component_id}"):
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
            st.success("Sparat!")
            st.rerun()
    
    with col_cancel:
        if st.button("Avbryt", key=f"cancel_v1_{component_id}"):
            st.rerun()


def _render_vtype2_table_and_form(df: pd.DataFrame):
    """Renderar tabell för vtype=2 komponenter."""
    df_display = df[['id_component', 'cat', 'subcat', 'anskaffningsvärde', 'rapporteradnuav', 'time_from']].copy()
    df_display['year'] = df_display['time_from'].apply(time_code_to_year)
    df_display['nuav_kkr'] = df_display['rapporteradnuav'] / 1_000
    
    df_display = df_display.rename(columns={
        'id_component': 'ID',
        'cat': 'Kategori',
        'subcat': 'Subkategori',
        'anskaffningsvärde': 'Anskaffningsvärde',
        'nuav_kkr': 'NUAV (kkr)',
        'year': 'Anskaffningsår',
    })
    
    display_cols = ['ID', 'Kategori', 'Subkategori', 'Anskaffningsvärde', 'NUAV (kkr)', 'Anskaffningsår']
    
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
    """Redigeringsformulär för vtype=2."""
    
    col1, col2 = st.columns(2)
    
    with col1:
        current_year = time_code_to_year(row['time_from'])
        new_year = st.number_input(
            "Anskaffningsår",
            min_value=1910,
            max_value=2023,
            value=int(current_year) if current_year > 0 else 2000,
            key=f"edit_year_v2_{component_id}",
        )
        
        new_anskaffning = st.number_input(
            "Ursprungligt anskaffningsvärde (kr)",
            min_value=0.0,
            value=float(row['anskaffningsvärde']) if pd.notna(row['anskaffningsvärde']) else 0.0,
            format="%.0f",
            key=f"edit_anskaffning_v2_{component_id}",
        )
    
    with col2:
        new_nuav = st.number_input(
            "Rapporterad NUAV (kr)",
            min_value=0.0,
            value=float(row['rapporteradnuav']) if pd.notna(row['rapporteradnuav']) else 0.0,
            format="%.0f",
            key=f"edit_nuav_v2_{component_id}",
            help="Anskaffningsvärde uppräknat till 2022 års prisnivå med BKI",
        )
    
    col_save, col_cancel = st.columns(2)
    
    with col_save:
        if st.button("Spara", type="primary", key=f"save_v2_{component_id}"):
            df = get_modified_components()
            mask = df['id_component'] == component_id
            df.loc[mask, 'anskaffningsvärde'] = new_anskaffning
            df.loc[mask, 'rapporteradnuav'] = new_nuav
            df.loc[mask, 'time_from'] = year_to_time_code(new_year)
            df.loc[mask, 'nuav_2022'] = new_nuav
            update_modified_components(df)
            st.success("Sparat!")
            st.rerun()
    
    with col_cancel:
        if st.button("Avbryt", key=f"cancel_v2_{component_id}"):
            st.rerun()


def _render_add_vtype1_form():
    """Formulär för att lägga till komponent med annat skäligt värde."""
    
    col1, col2 = st.columns(2)
    
    with col1:
        cat_options = get_category_options()
        new_cat = st.selectbox(
            "Kategori",
            list(cat_options.keys()),
            format_func=lambda x: cat_options[x],
            key="add_v1_cat",
        )
        
        new_subcat = st.text_input(
            "Subkategori",
            value="",
            key="add_v1_subcat",
        )
        
        new_year = st.number_input(
            "Idrifttagandeår",
            min_value=1910,
            max_value=2023,
            value=2020,
            key="add_v1_year",
        )
    
    with col2:
        new_värde = st.number_input(
            "Annat skäligt värde (kr/enhet)",
            min_value=0.0,
            value=100000.0,
            format="%.0f",
            key="add_v1_värde",
        )
        
        new_count = st.number_input(
            "Antal",
            min_value=0.0001,
            value=1.0,
            format="%.4f",
            key="add_v1_count",
        )
        
        # Visa beräknad NUAV
        st.text_input(
            "Beräknad NUAV",
            value=f"{new_värde * new_count:,.0f} kr",
            disabled=True,
        )
    
    if st.button("Lägg till komponent", type="primary", key="add_v1_submit"):
        if new_subcat.strip() == "":
            st.error("Ange subkategori")
        else:
            new_id = add_component_vtype1(
                cat_encode=new_cat,
                subcat=new_subcat,
                annatskäligtvärde=new_värde,
                count_comp=new_count,
                time_from=year_to_time_code(new_year),
            )
            st.success(f"Komponent tillagd (ID: {new_id})")
            st.rerun()


# =============================================================================
# FLIK 3: INVESTERINGAR (vtype=5)
# =============================================================================

def _render_investeringar_tab():
    """Renderar flik för investeringar och utrangeringar."""
    st.subheader("Investeringar och utrangeringar")
    st.caption("Planerade förändringar under tillsynsperioden 2024-2027")
    
    df = get_investeringar()
    
    # Separera investeringar och utrangeringar
    if not df.empty:
        df_inv = df[df['invest'] == 1]
        df_utr = df[df['invest'] == -1]
    else:
        df_inv = pd.DataFrame()
        df_utr = pd.DataFrame()
    
    # Statistik
    col1, col2, col3 = st.columns(3)
    with col1:
        inv_sum = df_inv['nuav_2022'].sum() / 1_000_000 if not df_inv.empty else 0
        st.metric("Investeringar", f"{len(df_inv)} st", f"+{inv_sum:.1f} Mkr")
    with col2:
        utr_sum = abs(df_utr['nuav_2022'].sum()) / 1_000_000 if not df_utr.empty else 0
        st.metric("Utrangeringar", f"{len(df_utr)} st", f"-{utr_sum:.1f} Mkr")
    with col3:
        netto = inv_sum - utr_sum
        st.metric("Netto", f"{netto:+.1f} Mkr")
    
    # Tabell
    if not df.empty:
        _render_investment_table_and_form(df)
    else:
        st.info("Inga investeringar eller utrangeringar registrerade.")
    
    st.divider()
    
    # Lägg till nya
    col_inv, col_utr = st.columns(2)
    
    with col_inv:
        with st.expander("Lägg till investering", expanded=False):
            _render_add_investment_form(is_retirement=False)
    
    with col_utr:
        with st.expander("Lägg till utrangering", expanded=False):
            _render_add_investment_form(is_retirement=True)


def _render_investment_table_and_form(df: pd.DataFrame):
    """Renderar tabell för investeringar/utrangeringar."""
    
    df_display = df[['id_component', 'cat', 'subcat', 'invest', 'value_invest', 'time_invest']].copy()
    df_display['typ'] = df_display['invest'].apply(lambda x: "Investering" if x == 1 else "Utrangering")
    df_display['värde_mkr'] = df_display['value_invest'].abs() / 1_000_000
    df_display['halvår'] = df_display['time_invest'].apply(
        lambda x: TIMECODE_TO_HALFYEAR.get(int(x), f"Kod {x}") if pd.notna(x) else ""
    )
    
    df_display = df_display.rename(columns={
        'id_component': 'ID',
        'cat': 'Kategori',
        'subcat': 'Subkategori',
        'typ': 'Typ',
        'värde_mkr': 'Värde (Mkr)',
        'halvår': 'Halvår',
    })
    
    display_cols = ['ID', 'Typ', 'Kategori', 'Subkategori', 'Värde (Mkr)', 'Halvår']
    
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
    """Redigeringsformulär för investering/utrangering."""
    
    is_retirement = row['invest'] == -1
    typ_label = "Utrangering" if is_retirement else "Investering"
    
    st.markdown(f"**Redigera {typ_label} ID {component_id}**")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Kategori
        cat_options = get_category_options()
        current_cat = int(row['cat_encode']) if pd.notna(row['cat_encode']) else 3
        cat_list = list(cat_options.keys())
        
        new_cat = st.selectbox(
            "Kategori",
            cat_list,
            index=cat_list.index(current_cat) if current_cat in cat_list else 0,
            format_func=lambda x: cat_options[x],
            key=f"edit_cat_inv_{component_id}",
        )
        
        new_subcat = st.text_input(
            "Subkategori",
            value=row['subcat'] if pd.notna(row['subcat']) else "",
            key=f"edit_subcat_inv_{component_id}",
        )
    
    with col2:
        # Halvår
        halfyear_options = list(HALFYEAR_TO_TIMECODE.keys())
        current_halfyear = TIMECODE_TO_HALFYEAR.get(int(row['time_invest']), halfyear_options[0])
        
        new_halfyear = st.selectbox(
            "Halvår",
            halfyear_options,
            index=halfyear_options.index(current_halfyear) if current_halfyear in halfyear_options else 0,
            key=f"edit_halfyear_inv_{component_id}",
        )
        
        # Värde (alltid positivt i input)
        current_value = abs(row['value_invest']) if pd.notna(row['value_invest']) else 0
        new_value = st.number_input(
            f"Värde (kr)",
            min_value=0.0,
            value=float(current_value),
            format="%.0f",
            key=f"edit_value_inv_{component_id}",
        )
    
    col_save, col_cancel, col_delete = st.columns(3)
    
    with col_save:
        if st.button("Spara", type="primary", key=f"save_inv_{component_id}"):
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
            st.success("Sparat!")
            st.rerun()
    
    with col_cancel:
        if st.button("Avbryt", key=f"cancel_inv_{component_id}"):
            st.rerun()
    
    with col_delete:
        if st.button("Ta bort", type="secondary", key=f"delete_inv_{component_id}"):
            remove_component(component_id)
            st.warning("Markerad för borttagning")
            st.rerun()


def _render_add_investment_form(is_retirement: bool):
    """Formulär för att lägga till investering eller utrangering."""
    
    typ_label = "utrangering" if is_retirement else "investering"
    
    col1, col2 = st.columns(2)
    
    with col1:
        cat_options = get_category_options()
        new_cat = st.selectbox(
            "Kategori",
            list(cat_options.keys()),
            format_func=lambda x: cat_options[x],
            key=f"add_{'utr' if is_retirement else 'inv'}_cat",
        )
        
        new_subcat = st.text_input(
            "Subkategori",
            value="",
            key=f"add_{'utr' if is_retirement else 'inv'}_subcat",
        )
    
    with col2:
        halfyear_options = list(HALFYEAR_TO_TIMECODE.keys())
        new_halfyear = st.selectbox(
            "Halvår",
            halfyear_options,
            key=f"add_{'utr' if is_retirement else 'inv'}_halfyear",
        )
        
        new_value = st.number_input(
            "Värde (kr)",
            min_value=0.0,
            value=1000000.0,
            format="%.0f",
            key=f"add_{'utr' if is_retirement else 'inv'}_value",
        )
    
    if st.button(f"Lägg till {typ_label}", type="primary", key=f"add_{'utr' if is_retirement else 'inv'}_submit"):
        if new_subcat.strip() == "":
            st.error("Ange subkategori")
        else:
            new_id = add_investment(
                cat_encode=new_cat,
                subcat=new_subcat,
                value=new_value,
                time_invest=HALFYEAR_TO_TIMECODE[new_halfyear],
                is_retirement=is_retirement,
            )
            st.success(f"{typ_label.capitalize()} tillagd (ID: {new_id})")
            st.rerun()


# =============================================================================
# SNABBÅTGÄRDER
# =============================================================================

def _render_count_scaling_form(
    vtype: int,
    cat_filter: Optional[str] = None,
    subcat_filter: Optional[str] = None,
):
    """Formulär för att skala count_comp."""
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        scale_pct = st.number_input(
            "Skalningsfaktor (%)",
            min_value=-99.0,
            max_value=1000.0,
            value=0.0,
            step=5.0,
            format="%.1f",
            key=f"scale_pct_{vtype}",
            help="+10% = öka antal/längd med 10%",
        )
    
    with col2:
        scope_label = "aktuellt filter" if cat_filter else "alla"
        st.caption(f"Omfattning: {scope_label}")
    
    with col3:
        if st.button("Verkställ", key=f"scale_btn_{vtype}"):
            if abs(scale_pct) > 0.001:
                # Hämta cat_encode från cat-namn
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
                st.success(f"Skalade {n_scaled} komponenter med {scale_pct:+.1f}%")
                st.rerun()


# =============================================================================
# ÄNDRINGSINDIKATOR
# =============================================================================

def _render_change_indicator():
    """Renderar ändringsindikator längst ned."""
    
    if has_changes():
        summary = get_change_summary()
        
        msg_parts = []
        if summary['n_modified'] > 0:
            msg_parts.append(f"{summary['n_modified']} modifierade")
        if summary['n_added'] > 0:
            msg_parts.append(f"{summary['n_added']} tillagda")
        if summary['n_removed'] > 0:
            msg_parts.append(f"{summary['n_removed']} borttagna")
        
        nuav_str = f"NUAV: {summary['nuav_change_mkr']:+.2f} Mkr"
        
        st.success(f"Ändringar: {' | '.join(msg_parts)} | {nuav_str}")
    else:
        st.caption("Inga ändringar gjorda")


def _clear_edit_state():
    """Rensar redigeringsrelaterad session state."""
    keys_to_clear = [k for k in st.session_state.keys() if k.startswith(('edit_', 'add_', 'scale_'))]
    for key in keys_to_clear:
        del st.session_state[key]
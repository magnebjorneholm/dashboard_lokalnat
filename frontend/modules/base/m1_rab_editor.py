"""
Module 1: RAB Editor

UI-komponent för redigering av kapitalbas (Regulatory Asset Base).
Anropas från m1_asset_base.py.

Låter användaren:
- Redigera befintliga komponenter (NUAV, idrifttagandeår, kategori)
- Lägga till nya komponenter/investeringar
- Lägga till planerade utrangeringar
- Ta bort komponenter
"""

import streamlit as st
import pandas as pd
from typing import Dict, Any, Optional

from frontend.utils.state_manager import get_user_id_network, get_module_config, set_module_config
from frontend.common.asset_categories import ASSET_CATEGORIES
from calculations.rab_editor_utils import (
    initialize_rab_editor,
    get_user_capbase_with_edits,
    has_changes,
    reset_rab_editor,
    get_modified_components,
    get_original_components,
    update_modified_components,
    add_component,
    remove_component,
    get_change_summary,
    time_code_to_year,
    year_to_time_code,
    load_user_components,
)

MODULE_KEY = "m1_asset_base"

# Kategori-options för SelectboxColumn
CATEGORY_OPTIONS = {
    cat.cat_encode: f"{cat.cat_encode} - {cat.name[:25]}"
    for cat in ASSET_CATEGORIES
}


def render() -> Dict[str, Any]:
    """
    Renderar RAB-editor UI.
    
    Returns:
        Dict med rab_has_changes flagga
    """
    config: Dict[str, Any] = {}
    
    user_id_network = get_user_id_network()
    if not user_id_network:
        st.warning("Välj företag i sidopanelen för att redigera kapitalbas.")
        return config
    
    # Ladda användarens komponenter och initiera RAB-editor
    try:
        user_components = load_user_components(user_id_network)
        initialize_rab_editor(user_components)
    except Exception as e:
        st.error(f"Kunde inte ladda kapitalbasdata: {e}")
        return config
    
    # Hämta data
    df_original = get_original_components()
    df_modified = get_modified_components()
    
    if df_modified is None or df_modified.empty:
        st.info("Inga komponenter hittades för detta företag.")
        return config
    
    # === SAMMANFATTNING ===
    _render_summary(df_modified, df_original)
    
    st.divider()
    
    # === FILTER ===
    col_filter1, col_filter2 = st.columns(2)
    
    with col_filter1:
        cat_options = ["Alla kategorier"] + [
            f"{cat.cat_encode} - {cat.name}" for cat in ASSET_CATEGORIES
        ]
        selected_cat = st.selectbox(
            "Kategori",
            options=cat_options,
            key="rab_filter_cat"
        )
    
    with col_filter2:
        # Subkategori-filter baserat på vald kategori
        if selected_cat != "Alla kategorier":
            cat_encode = int(selected_cat.split(" - ")[0])
            subcats = df_modified[df_modified['cat_encode'] == cat_encode]['subcat'].dropna().unique()
            subcat_options = ["Alla subkategorier"] + list(subcats)
        else:
            cat_encode = None
            subcat_options = ["Alla subkategorier"]
        
        selected_subcat = st.selectbox(
            "Subkategori",
            options=subcat_options,
            key="rab_filter_subcat"
        )
    
    # Applicera filter
    df_filtered = df_modified.copy()
    if cat_encode is not None:
        df_filtered = df_filtered[df_filtered['cat_encode'] == cat_encode]
    if selected_subcat != "Alla subkategorier":
        df_filtered = df_filtered[df_filtered['subcat'] == selected_subcat]
    
    st.caption(f"Visar {len(df_filtered)} av {len(df_modified)} komponenter")
    
    # === EDITOR ===
    df_display = _prepare_for_display(df_filtered)
    
    edited_df = st.data_editor(
        df_display,
        num_rows="fixed",  # Använd separata knappar för add/remove
        hide_index=True,
        width="stretch",
        column_config={
            "id_component": st.column_config.NumberColumn(
                "ID",
                disabled=True,
                width="small",
            ),
            "nuav_2022": st.column_config.NumberColumn(
                "NUAV (kr)",
                min_value=0,
                format="%.0f",
                width="medium",
                required=True,
            ),
            "year": st.column_config.NumberColumn(
                "Idrifttagande",
                min_value=1920,
                max_value=2027,
                format="%d",
                width="small",
                required=True,
                help="År då komponenten togs i bruk",
            ),
            "cat_encode": st.column_config.SelectboxColumn(
                "Kategori",
                options=list(CATEGORY_OPTIONS.keys()),
                width="small",
                required=True,
            ),
            "cat_name": st.column_config.TextColumn(
                "Kategorinamn",
                width="medium",
                disabled=True,
            ),
            "subcat": st.column_config.TextColumn(
                "Subkategori",
                width="medium",
                disabled=True,
            ),
            "antal": st.column_config.NumberColumn(
                "Antal",
                min_value=1,
                format="%d",
                width="small",
            ),
        },
        column_order=["id_component", "nuav_2022", "year", "cat_encode", "cat_name", "subcat", "antal"],
        disabled=["id_component", "cat_name", "subcat"],
        key="rab_data_editor",
    )
    
    # Synka ändringar tillbaka
    _sync_edits_to_session(edited_df, df_filtered)
    
    st.divider()
    
    # === SNABBÅTGÄRDER ===
    _render_quick_actions(cat_encode)
    
    st.divider()
    
    # === LÄGG TILL / ÅTERSTÄLL ===
    col_add, col_reset = st.columns([3, 1])
    
    with col_add:
        with st.expander("Lägg till komponent", expanded=False):
            _render_add_component_form()
        
        with st.expander("Lägg till utrangering", expanded=False):
            _render_add_retirement_form()
    
    with col_reset:
        if st.button("Återställ alla", type="secondary", width="stretch"):
            reset_rab_editor()
            st.rerun()
    
    # === ÄNDRINGSINDIKATOR ===
    if has_changes():
        summary = get_change_summary()
        st.success(
            f"Ändringar: {summary['n_modified']} modifierade | "
            f"{summary['n_added']} tillagda | "
            f"{summary['n_removed']} borttagna | "
            f"NUAV: {summary['nuav_change_mkr']:+.2f} Mkr"
        )
        config["rab_has_changes"] = True
    else:
        st.caption("Inga ändringar")
        config["rab_has_changes"] = False
    
    return config


def _render_summary(df_current: pd.DataFrame, df_original: pd.DataFrame) -> None:
    """Renderar sammanfattnings-metrics."""
    n_components = len(df_current)
    total_nuav = df_current['nuav_2022'].sum() / 1_000_000
    original_nuav = df_original['nuav_2022'].sum() / 1_000_000
    nuav_delta = total_nuav - original_nuav
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Komponenter", f"{n_components:,}")
    
    with col2:
        st.metric("Total NUAV", f"{total_nuav:.1f} Mkr")
    
    with col3:
        delta_str = f"{nuav_delta:+.2f} Mkr" if abs(nuav_delta) > 0.001 else None
        st.metric("Förändring", f"{nuav_delta:+.2f} Mkr" if delta_str else "0", delta=delta_str)


def _prepare_for_display(df: pd.DataFrame) -> pd.DataFrame:
    """Förbereder DataFrame för st.data_editor."""
    df_display = df.copy()
    
    # Konvertera time_from till år för visning
    if 'time_from' in df_display.columns:
        df_display['year'] = df_display['time_from'].apply(time_code_to_year)
    else:
        df_display['year'] = 2000
    
    # Lägg till kategorinamn
    cat_map = {cat.cat_encode: cat.name for cat in ASSET_CATEGORIES}
    df_display['cat_name'] = df_display['cat_encode'].map(cat_map)
    
    # Välj och ordna kolumner
    cols = ['id_component', 'nuav_2022', 'year', 'cat_encode', 'cat_name', 'subcat', 'antal']
    available_cols = [c for c in cols if c in df_display.columns]
    
    return df_display[available_cols]


def _sync_edits_to_session(edited_df: pd.DataFrame, original_filtered: pd.DataFrame) -> None:
    """Synkar ändringar från data_editor tillbaka till session state."""
    df_modified = get_modified_components()
    if df_modified is None:
        return
    
    # Konvertera year tillbaka till time_from
    if 'year' in edited_df.columns:
        edited_df['time_from'] = edited_df['year'].apply(lambda y: year_to_time_code(int(y)))
    
    # Uppdatera ändrade rader i modified_components
    for idx, row in edited_df.iterrows():
        id_comp = row['id_component']
        mask = df_modified['id_component'] == id_comp
        
        if mask.any():
            for col in ['nuav_2022', 'time_from', 'cat_encode', 'antal']:
                if col in row and col in df_modified.columns:
                    df_modified.loc[mask, col] = row[col]
    
    update_modified_components(df_modified)


def _render_quick_actions(cat_encode: Optional[int]) -> None:
    """Renderar snabbåtgärder för skalning etc."""
    st.markdown("**Snabbåtgärder**")
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        scale_pct = st.number_input(
            "Skala NUAV (%)",
            min_value=-100.0,
            max_value=1000.0,
            value=0.0,
            step=5.0,
            format="%.1f",
            key="rab_scale_pct",
            help="Procentuell justering av NUAV"
        )
    
    with col2:
        scope_options = ["Aktuellt filter", "Alla komponenter"]
        scope = st.selectbox("Omfattning", scope_options, key="rab_scale_scope")
    
    with col3:
        st.write("")  # Spacer
        st.write("")
        if st.button("Verkställ", key="rab_scale_btn"):
            if abs(scale_pct) > 0.001:
                _apply_nuav_scaling(scale_pct, scope == "Aktuellt filter", cat_encode)
                st.rerun()


def _apply_nuav_scaling(scale_pct: float, filter_only: bool, cat_encode: Optional[int]) -> None:
    """Applicerar NUAV-skalning."""
    df_modified = get_modified_components()
    if df_modified is None:
        return
    
    multiplier = 1 + (scale_pct / 100)
    
    if filter_only and cat_encode is not None:
        mask = df_modified['cat_encode'] == cat_encode
    else:
        mask = pd.Series([True] * len(df_modified))
    
    df_modified.loc[mask, 'nuav_2022'] = df_modified.loc[mask, 'nuav_2022'] * multiplier
    update_modified_components(df_modified)


def _render_add_component_form() -> None:
    """Renderar formulär för att lägga till ny komponent."""
    with st.form("add_component_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            cat_encode = st.selectbox(
                "Kategori",
                options=list(CATEGORY_OPTIONS.keys()),
                format_func=lambda x: CATEGORY_OPTIONS[x],
                key="add_comp_cat"
            )
            
            nuav = st.number_input(
                "NUAV (kr)",
                min_value=0.0,
                value=100000.0,
                step=10000.0,
                format="%.0f",
                key="add_comp_nuav"
            )
        
        with col2:
            year = st.number_input(
                "Idrifttagandeår",
                min_value=1920,
                max_value=2027,
                value=2020,
                key="add_comp_year"
            )
            
            antal = st.number_input(
                "Antal",
                min_value=1,
                value=1,
                key="add_comp_antal"
            )
        
        submitted = st.form_submit_button("Lägg till", width="stretch")
        
        if submitted:
            # Bestäm capbase_existing baserat på år
            capbase_existing = 1 if year <= 2022 else 0
            time_from = year_to_time_code(year)
            
            component = {
                'cat_encode': cat_encode,
                'nuav_2022': nuav,
                'time_from': time_from,
                'time_invest': time_from if capbase_existing == 0 else None,
                'capbase_existing': capbase_existing,
                'antal': antal,
                'invest': 1.0 if capbase_existing == 0 else None,
                'subcat': 'användardefinierad',
                'metod': 'user_added',
            }
            
            new_id = add_component(component)
            st.success(f"Komponent tillagd (ID: {new_id})")
            st.rerun()


def _render_add_retirement_form() -> None:
    """Renderar formulär för att lägga till utrangering."""
    with st.form("add_retirement_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            cat_encode = st.selectbox(
                "Kategori att utrangera",
                options=list(CATEGORY_OPTIONS.keys()),
                format_func=lambda x: CATEGORY_OPTIONS[x],
                key="retire_cat"
            )
            
            nuav = st.number_input(
                "Belopp att utrangera (kr)",
                min_value=0.0,
                value=100000.0,
                step=10000.0,
                format="%.0f",
                key="retire_nuav",
                help="Positivt värde - blir negativt i beräkningen"
            )
        
        with col2:
            year = st.selectbox(
                "År",
                options=[2023, 2024, 2025, 2026, 2027],
                key="retire_year"
            )
            
            half = st.selectbox(
                "Halvår",
                options=[1, 2],
                format_func=lambda x: f"H{x}",
                key="retire_half"
            )
        
        submitted = st.form_submit_button("Lägg till utrangering", width="stretch")
        
        if submitted:
            time_code = year_to_time_code(year, half)
            
            component = {
                'cat_encode': cat_encode,
                'nuav_2022': nuav,  # Positivt värde
                'time_from': time_code,
                'time_invest': time_code,
                'capbase_existing': 0,
                'invest': -1.0,  # Negativt = utrangering
                'subcat': 'utrangering',
                'metod': 'user_retirement',
            }
            
            new_id = add_component(component)
            st.success(f"Utrangering tillagd (ID: {new_id})")
            st.rerun()


def render_info_box() -> None:
    """Renderar informationsruta om RAB-editorn."""
    st.info(
        """
        **Om RAB-editorn**
        - Alla ändringar beräknas exakt genom KENT-metodiken
        - Inga approximationer används
        - Livslängder (ekdep/maxdep) justeras under "2. Avskrivningar"
        - Ändringar är för scenarioanalys - faktisk inrapportering till Ei sker via KENT-systemet
        """
    )
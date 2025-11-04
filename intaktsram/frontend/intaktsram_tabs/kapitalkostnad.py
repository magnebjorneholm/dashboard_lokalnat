"""
foretag/view/intaktsram_tabs/kapitalkostnad.py
Kapitalkostnad-tab med utökad metadata-visning för justeringar
"""

import streamlit as st
import pandas as pd
from typing import Optional
from pathlib import Path
import json

from intaktsram.backend.scenario_utils import list_available_kapitalbas_scenarios


def show_kapitalkostnad_tab(entity_data: pd.Series, scenario_metadata: Optional[dict] = None):
    """
    Visar kapitalkostnad-tab med status, komponenter och navigation.
    Inkluderar utökad visning av parameterjusteringar.
    
    Args:
        entity_data: Series med data för vald entitet (lokalnät)
        scenario_metadata: Metadata från aktivt kapitalbas-scenario (optional)
    """
    
    st.subheader("Kapitalkostnad")
    
    is_modified = entity_data.get('Uppdaterad_Kapitalkostnad', False)
    källa = entity_data.get('Källa_Kapitalkostnad', 'Baseline')
    
    scenario_data = st.session_state.get('scenario_data', {})
    modifications = scenario_data.get('modifications', {})
    kapital_mod = modifications.get('kapitalkostnad', {})
    
    # Statusmeddelande med utökad information
    if is_modified and kapital_mod.get('source') == 'kapitalbas':
        status_parts = []
        
        # WACC-info
        if scenario_metadata and 'wacc_new' in scenario_metadata:
            wacc_new = scenario_metadata['wacc_new'] * 100
            wacc_old = scenario_metadata.get('wacc_old', 0.0453) * 100
            status_parts.append(f"WACC: {wacc_old:.2f}% → **{wacc_new:.2f}%**")
        
        # Parameterjusteringar
        param_adj = scenario_metadata.get('parameter_adjustments', {}) if scenario_metadata else {}
        
        if param_adj.get('has_normvalue_adjustments'):
            norm_info = param_adj.get('normvalue_adjustments', {})
            count = norm_info.get('count', 0)
            level = norm_info.get('level', 'kategori')
            level_text = 'subkategorinivå' if level == 'subcat' else 'kategorinivå'
            status_parts.append(f"Normvärden: {count} ändringar på {level_text}")
        
        if param_adj.get('has_lifetime_adjustments'):
            life_info = param_adj.get('lifetime_adjustments', {})
            count = life_info.get('count', 0)
            level = life_info.get('level', 'kategori')
            level_text = 'subkategorinivå' if level == 'subcat' else 'kategorinivå'
            status_parts.append(f"Livslängder: {count} ändringar på {level_text}")
        
        # Visa statusinfo
        if status_parts:
            st.info(f"Kapitalkostnad baseras på scenario från Kapitalbas:\n\n" + "\n\n".join(f"• {part}" for part in status_parts))
        else:
            st.info("Kapitalkostnad baseras på scenario från Kapitalbas")
        
        # Visa detaljerad justeringsinformation om den finns
        if param_adj.get('has_normvalue_adjustments') or param_adj.get('has_lifetime_adjustments'):
            with st.expander("Visa detaljerade justeringar"):
                show_detailed_adjustments(param_adj)
        
        if källa and källa != 'Baseline':
            st.caption(f"Källa: {källa}")
    else:
        st.caption("Visar referensperiod (ingen ändring av kapitalkostnad)")
    
    st.markdown("---")
    
    # Hämta värden
    kapitalkostnad_total = entity_data.get('Kapitalkostnad_Total', 0)
    baseline_kapitalkostnad = entity_data.get('Kapitalkostnad_Total_Baseline', kapitalkostnad_total)
    
    avskrivningar = entity_data.get('Avskrivningar', None)
    avkastning = entity_data.get('Avkastning', None)
    
    has_detailed_capital = avskrivningar is not None and avkastning is not None
    
    # METRICS (3 kolumner)
    if has_detailed_capital:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            delta_total = None
            if is_modified and baseline_kapitalkostnad > 0:
                delta_total = kapitalkostnad_total - baseline_kapitalkostnad
                delta_pct = (delta_total / baseline_kapitalkostnad * 100)
            
            st.metric(
                "Total kapitalkostnad",
                f"{kapitalkostnad_total:,.0f} tkr".replace(",", " "),
                delta=f"{delta_pct:+.1f}%" if delta_total else None
            )
        
        with col2:
            if baseline_kapitalkostnad > 0:
                andel = (kapitalkostnad_total / entity_data.get('Intaktsram_Total', 1) * 100)
                st.metric(
                    "Andel av intäktsram",
                    f"{andel:.1f}%"
                )
        
        with col3:
            if is_modified and delta_total:
                st.metric(
                    "Förändring",
                    f"{abs(delta_total):,.0f} tkr".replace(",", " "),
                    delta=f"{delta_total:,.0f} tkr".replace(",", " ")
                )
    else:
        # Fallback om uppdelad kapitalkostnad saknas
        col1, col2 = st.columns(2)
        
        with col1:
            delta_total = None
            if is_modified and baseline_kapitalkostnad > 0:
                delta_total = kapitalkostnad_total - baseline_kapitalkostnad
                delta_pct = (delta_total / baseline_kapitalkostnad * 100)
            
            st.metric(
                "Total kapitalkostnad",
                f"{kapitalkostnad_total:,.0f} tkr".replace(",", " "),
                delta=f"{delta_pct:+.1f}%" if delta_total else None
            )
        
        with col2:
            if baseline_kapitalkostnad > 0:
                andel = (kapitalkostnad_total / entity_data.get('Intaktsram_Total', 1) * 100)
                st.metric(
                    "Andel av intäktsram",
                    f"{andel:.1f}%"
                )
    
    # IMPORTERA FRÅN KAPITALBAS
    st.markdown("---")
    
    available_scenarios = list_available_kapitalbas_scenarios()
    
    if not available_scenarios.empty:
        available_scenarios['display'] = (
            "WACC " + available_scenarios['wacc_tag'] + 
            " - " + 
            available_scenarios['timestamp'].str[:10]
        )
        
        selected_display = st.selectbox(
            "Tillgängliga Kapitalbas-exports",
            options=available_scenarios['display'].tolist(),
            key="kapitalbas_export_selector"
        )
        
        selected_export = available_scenarios[available_scenarios['display'] == selected_display].iloc[0]
    else:
        st.info(
            "Inga Kapitalbas-exports hittades. "
            "Gå till Beräkningskedja för att "
            "beräkna och exportera kapitalkostnader."
        )
        selected_export = None
    
    # KNAPPAR
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Importera från Kapitalbas", use_container_width=True, disabled=available_scenarios.empty):
            if not st.session_state.current_scenario_name:
                st.error("Skapa ett scenario först innan du importerar data")
            elif selected_export is not None:
                success = apply_kapitalbas_scenario(
                    scenario_file=selected_export['filepath'],
                    entity_dmu=int(entity_data.get('DMU'))
                )
                if success:
                    st.success(f"Kapitalkostnad importerad med WACC {selected_export['wacc_tag']}!")
                    st.rerun()
                else:
                    st.error("Kunde inte importera scenario")
    
    with col2:
        if st.button("Till Beräkningskedja", use_container_width=True, type="primary"):
            st.session_state['ir_context'] = {
                'from_page': 'intaktsram_ny',
                'reid': entity_data.get('REId'),
                'dmu': entity_data.get('DMU'),
                'scenario': st.session_state.get('current_scenario_name', ''),
                'fokus': 'kapitalkostnad'
            }
            st.switch_page("pages/foretag/foretag_berakningskedja.py")
    
    # ÅRSVISA KAPITALKOSTNADER
    st.markdown("---")
    show_yearly_kapitalkostnad_breakdown(entity_data, has_detailed_capital, kapital_mod)
    
    # INFO-EXPANDER
    if not is_modified:
        st.markdown("---")
        with st.expander("Om kapitalkostnad"):
            st.write("""
            **Kapitalkostnad** består av två delar:
            
            - **Avskrivningar:** Kostnaden för förslitning/åldrande av anläggningar
            - **Avkastning:** Räntekostnad på kapitalet (WACC × Kapitalbas)
            
            Dessa beräknas utifrån:
            - Nuanskaffningsvärde (NUAV) för varje anläggningstillgång
            - Ekonomiska livslängder enligt Ei:s normvärdeslista
            - WACC-ränta fastställd av Ei för tillsynsperioden
            
            **Processen:**
            1. Gå till Beräkningskedja (knapp ovan)
            2. Beräkna kapitalkostnader med önskade parametrar
            3. Exportera till Intäktsram
            4. Kom tillbaka hit och importera från selectbox ovan
            
            För mer information, se Beräkningskedja.
            """)


def show_detailed_adjustments(param_adj: dict):
    """
    Visar detaljerad information om parameterjusteringar
    
    Args:
        param_adj: Dictionary med justeringsmetadata
    """
    
    # Normvärdejusteringar
    if param_adj.get('has_normvalue_adjustments'):
        st.markdown("#### Normvärdejusteringar")
        norm_info = param_adj.get('normvalue_adjustments', {})
        level = norm_info.get('level', 'kategori')
        level_text = 'Subkategorinivå' if level == 'subcat' else 'Kategorinivå'
        
        st.write(f"**Nivå:** {level_text}")
        st.write(f"**Antal ändringar:** {norm_info.get('count', 0)}")
        
        details = norm_info.get('details', [])
        if details:
            df_details = pd.DataFrame(details)
            
            # Välj relevanta kolumner beroende på vad som finns
            display_cols = []
            for col in ['Kod', 'Beskrivning', 'Justering (%)', 'Ny NUAV (tkr)', 'Förändring (tkr)']:
                if col in df_details.columns:
                    display_cols.append(col)
            
            if display_cols:
                st.dataframe(df_details[display_cols], use_container_width=True, hide_index=True)
    
    # Livslängdsjusteringar
    if param_adj.get('has_lifetime_adjustments'):
        if param_adj.get('has_normvalue_adjustments'):
            st.markdown("---")
        
        st.markdown("#### Livslängdsjusteringar")
        life_info = param_adj.get('lifetime_adjustments', {})
        level = life_info.get('level', 'kategori')
        level_text = 'Subkategorinivå' if level == 'subcat' else 'Kategorinivå'
        
        st.write(f"**Nivå:** {level_text}")
        st.write(f"**Antal ändringar:** {life_info.get('count', 0)}")
        
        details = life_info.get('details', [])
        if details:
            df_details = pd.DataFrame(details)
            
            # Välj relevanta kolumner
            display_cols = []
            for col in ['Kod', 'Beskrivning', 'Ekonomisk livslängd (år)', 'Maximal livslängd (år)']:
                if col in df_details.columns:
                    display_cols.append(col)
            
            if display_cols:
                st.dataframe(df_details[display_cols], use_container_width=True, hide_index=True)


def show_yearly_kapitalkostnad_breakdown(entity_data: pd.Series, has_detailed: bool, kapital_mod: dict):
    """
    Visar breakdown av kapitalkostnader per år.
    """
    if not has_detailed:
        return
    
    # Hämta årsvisa värden om de finns i metadata
    last_calc = kapital_mod.get('metadata') if kapital_mod else None
    
    if last_calc is None:
        # Visa enkel breakdown baserat på totaler
        avskrivningar = entity_data.get('Avskrivningar', 0)
        avkastning = entity_data.get('Avkastning', 0)
        baseline_avskrivningar = entity_data.get('Avskrivningar_Baseline', avskrivningar)
        baseline_avkastning = entity_data.get('Avkastning_Baseline', avkastning)
        
        with st.expander("Komponentspecifikation"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Avskrivningar**")
                breakdown_data = pd.DataFrame({
                    'Komponent': ['Scenario', 'Baseline', 'Skillnad'],
                    'Belopp (tkr)': [
                        f"{avskrivningar:,.0f}".replace(",", " "),
                        f"{baseline_avskrivningar:,.0f}".replace(",", " "),
                        f"{(avskrivningar - baseline_avskrivningar):+,.0f}".replace(",", " ")
                    ]
                })
                st.dataframe(breakdown_data, use_container_width=True, hide_index=True)
            
            with col2:
                st.write("**Avkastning**")
                breakdown_data = pd.DataFrame({
                    'Komponent': ['Scenario', 'Baseline', 'Skillnad'],
                    'Belopp (tkr)': [
                        f"{avkastning:,.0f}".replace(",", " "),
                        f"{baseline_avkastning:,.0f}".replace(",", " "),
                        f"{(avkastning - baseline_avkastning):+,.0f}".replace(",", " ")
                    ]
                })
                st.dataframe(breakdown_data, use_container_width=True, hide_index=True)
    else:
        # Om vi har detaljerad metadata från beräkningskedja
        with st.expander("Detaljerad breakdown från Beräkningskedja"):
            st.caption("Detaljerad information tillgänglig när kapitalkostnad importeras från Beräkningskedja")


def apply_kapitalbas_scenario(scenario_file: str, entity_dmu: int) -> bool:
    """
    Applicerar kapitalbas-scenario på aktivt scenario.
    
    Args:
        scenario_file: Sökväg till parquet-fil
        entity_dmu: DMU för aktuell entitet
        
    Returns:
        True om import lyckades
    """
    try:
        scenario_df = pd.read_parquet(scenario_file)
        
        # Läs metadata från JSON
        json_file = Path(scenario_file).with_suffix('.json')
        metadata = {}
        if json_file.exists():
            with open(json_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
        
        if 'scenario_data' not in st.session_state:
            return False
        
        # Bygg modifications-struktur
        modifications = {}
        for _, row in scenario_df.iterrows():
            if row['DMU'] == entity_dmu:
                dmu_str = str(int(row['DMU']))
                
                modification = {
                    'total': row.get('Kapitalkostnad_Ny', 0)
                }
                
                if 'Avskrivningar_Ny' in row and pd.notna(row['Avskrivningar_Ny']):
                    modification['avskrivningar'] = row['Avskrivningar_Ny']
                if 'Avkastning_Ny' in row and pd.notna(row['Avkastning_Ny']):
                    modification['avkastning'] = row['Avkastning_Ny']
                
                modifications[dmu_str] = modification
        
        if not modifications:
            st.warning(f"Ingen data hittades för DMU {entity_dmu} i exporten")
            return False
        
        # Applicera på session state
        st.session_state.scenario_data['modifications']['kapitalkostnad'] = {
            'values': modifications,
            'source': 'kapitalbas',
            'merge_on': 'DMU',
            'metadata': metadata
        }
        
        st.session_state.scenario_data['component_sources']['kapitalkostnad'] = 'kapitalbas'
        
        return True
        
    except Exception as e:
        st.error(f"Fel vid import: {e}")
        return False
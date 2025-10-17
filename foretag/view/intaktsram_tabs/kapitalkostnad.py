"""
foretag/view/intaktsram_tabs/kapitalkostnad.py
Kapitalkostnad-tab med navigation till beräkningskedja och import från kapitalbas
"""

import streamlit as st
import pandas as pd
from typing import Optional
from pathlib import Path
import json

from foretag.app.scenario_utils import list_available_kapitalbas_scenarios


def show_kapitalkostnad_tab(entity_data: pd.Series, scenario_metadata: Optional[dict] = None):
    """
    Visar kapitalkostnad-tab med status, komponenter, parametrar och navigation.
    KRITISK FIX: Nu tar korrekt parameter scenario_metadata.
    
    Args:
        entity_data: Series med data för vald entitet (lokalnät)
        scenario_metadata: Metadata från aktivt kapitalbas-scenario (optional)
    """
    
    st.subheader("Kapitalkostnad")
    
    is_modified = entity_data.get('Uppdaterad_Kapitalkostnad', False)
    källa = entity_data.get('Källa_Kapitalkostnad', 'Baseline')
    
    if is_modified:
        st.info(f"💡 Kapitalkostnad baseras på scenario från Kapitalbas")
        if källa and källa != 'Baseline':
            st.caption(f"Källa: {källa}")
    else:
        st.caption("Visar baseline-värden från Ei")
    
    st.markdown("---")
    
    # Hämta värden
    kapitalkostnad_total = entity_data.get('Kapitalkostnad_Total', 0)
    baseline_kapitalkostnad = entity_data.get('Kapitalkostnad_Total_Baseline', kapitalkostnad_total)
    
    avskrivningar = entity_data.get('Avskrivningar', None)
    avkastning = entity_data.get('Avkastning', None)
    
    has_detailed_capital = avskrivningar is not None and avkastning is not None
    
    # Visa metrics
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
            baseline_avskrivningar = entity_data.get('Avskrivningar_Baseline', avskrivningar)
            delta_avskr = None
            if is_modified and baseline_avskrivningar and baseline_avskrivningar > 0:
                delta_avskr = avskrivningar - baseline_avskrivningar
                delta_avskr_pct = (delta_avskr / baseline_avskrivningar * 100)
            
            st.metric(
                "Avskrivningar",
                f"{avskrivningar:,.0f} tkr".replace(",", " "),
                delta=f"{delta_avskr_pct:+.1f}%" if delta_avskr else None
            )
        
        with col3:
            baseline_avkastning = entity_data.get('Avkastning_Baseline', avkastning)
            delta_avk = None
            if is_modified and baseline_avkastning and baseline_avkastning > 0:
                delta_avk = avkastning - baseline_avkastning
                delta_avk_pct = (delta_avk / baseline_avkastning * 100)
            
            st.metric(
                "Avkastning (WACC)",
                f"{avkastning:,.0f} tkr".replace(",", " "),
                delta=f"{delta_avk_pct:+.1f}%" if delta_avk else None
            )
    else:
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
            kapitalandel = (kapitalkostnad_total / entity_data.get('Intaktsram_Total', 1) * 100)
            st.metric(
                "Andel av intäktsram",
                f"{kapitalandel:.1f}%"
            )
    
    # Visa parametrar från scenario om applicerat
    if is_modified and scenario_metadata:
        st.markdown("---")
        st.write("**Parametrar från scenario:**")
        
        wacc_old = scenario_metadata.get('wacc_old')
        wacc_new = scenario_metadata.get('wacc_new')
        period = scenario_metadata.get('period', {})
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if wacc_old and wacc_new:
                st.write(f"**WACC baseline:** {wacc_old*100:.2f}%")
                st.write(f"**WACC scenario:** {wacc_new*100:.2f}%")
                
                wacc_change = ((wacc_new - wacc_old) / wacc_old * 100)
                if abs(wacc_change) > 0.01:
                    st.caption(f"Förändring: {wacc_change:+.1f}%")
            elif wacc_new:
                st.write(f"**WACC:** {wacc_new*100:.2f}%")
        
        with col2:
            if period and isinstance(period, dict):
                period_start = period.get('start', 2024)
                period_end = period.get('end', 2027)
                st.write(f"**Period:** {period_start}–{period_end}")
            
            if avkastning and wacc_new:
                implicit_kapitalbas = avkastning / wacc_new
                st.write(f"**~Kapitalbas:** {implicit_kapitalbas:,.0f} tkr".replace(",", " "))
                st.caption("(Beräknad från Avkastning/WACC)")
        
        with col3:
            livslangder_andrade = scenario_metadata.get('livslangder_andrade', False)
            if livslangder_andrade:
                st.write("**Livslängder:** Modifierade")
                st.caption("Se beräkningskedja för detaljer")
    
    # Navigation och import-knappar
    st.markdown("---")
    st.write("**Justera parametrar:**")
    
    col1, col2, col3 = st.columns([3, 2, 2])
    
    with col1:
        st.caption(
            "I beräkningskedjan kan du justera WACC, livslängder och se "
            "fullständig kapitalbas-breakdown med nuanskaffningsvärden."
        )
    
    with col2:
        if st.button("Hämta från Kapitalbas", use_container_width=True):
            if not st.session_state.current_scenario_name:
                st.error("Skapa ett scenario först innan du importerar data")
            else:
                st.session_state.show_kapitalbas_import = True
                st.rerun()
    
    with col3:
        if st.button("Se beräkningskedja", use_container_width=True, type="primary"):
            st.session_state['ir_context'] = {
                'from_page': 'intaktsram_ny',
                'reid': entity_data.get('REId'),
                'dmu': entity_data.get('DMU'),
                'scenario': st.session_state.get('current_scenario_name', ''),
                'fokus': 'kapitalkostnad'
            }
            st.switch_page("pages/foretag/foretag_berakningskedja.py")
    
    # Import-dialog
    if st.session_state.get('show_kapitalbas_import', False):
        show_kapitalbas_import_dialog(entity_data)
    
    # Info-expander för baseline-användare
    if has_detailed_capital and not is_modified:
        st.markdown("---")
        with st.expander("ℹ️ Om kapitalkostnad"):
            st.write("""
            **Kapitalkostnad** består av två delar:
            
            - **Avskrivningar:** Kostnaden för förslitning/åldrande av anläggningar
            - **Avkastning:** Räntekostnad på kapitalet (WACC × Kapitalbas)
            
            Dessa beräknas utifrån:
            - Nuanskaffningsvärde (NUAV) för varje anläggningstillgång
            - Ekonomiska livslängder enligt Ei:s normvärdeslista
            - WACC-ränta fastställd av Ei för tillsynsperioden
            
            För att se fullständig breakdown och justera parametrar, 
            gå till beräkningskedjan.
            """)


def show_kapitalbas_import_dialog(entity_data: pd.Series):
    """
    Visar dialog för att välja och importera kapitalbas-scenario.
    
    Args:
        entity_data: Series med data för aktuell entitet
    """
    with st.expander("📥 Importera från Kapitalbas", expanded=True):
        st.write("Välj kapitalbas-export att importera:")
        
        available_scenarios = list_available_kapitalbas_scenarios()
        
        if available_scenarios.empty:
            st.warning("Inga kapitalbas-exports hittades. Exportera först från Kapitalbas-sektionen.")
            if st.button("Stäng"):
                st.session_state.show_kapitalbas_import = False
                st.rerun()
            return
        
        # Skapa display-namn
        available_scenarios['display'] = (
            available_scenarios['wacc_tag'] + " - " + 
            available_scenarios['timestamp'].str[:10]
        )
        
        selected_display = st.selectbox(
            "Tillgängliga exports",
            options=available_scenarios['display'].tolist(),
            key="kapitalbas_selector"
        )
        
        selected_row = available_scenarios[available_scenarios['display'] == selected_display].iloc[0]
        
        st.caption(f"Fil: {selected_row['filename']}")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Importera", use_container_width=True, type="primary"):
                success = apply_kapitalbas_scenario(
                    scenario_file=selected_row['filepath'],
                    entity_dmu=entity_data.get('DMU')
                )
                
                if success:
                    st.success("✅ Kapitalbas-scenario importerat!")
                    st.session_state.show_kapitalbas_import = False
                    st.rerun()
                else:
                    st.error("❌ Kunde inte importera scenario")
        
        with col2:
            if st.button("Avbryt", use_container_width=True):
                st.session_state.show_kapitalbas_import = False
                st.rerun()


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
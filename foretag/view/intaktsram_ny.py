"""
foretag/view/intaktsram_ny.py
Huvudvy för ny intäktsram-dekomposition med interaktivt diagram och tabs
"""

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from typing import Dict, Optional
from datetime import datetime
from pathlib import Path

from intaktsram.app.data_loader import (
    load_baseline_data,
    calculate_intaktsram
)
from core.session_utils import get_user_role, get_user_dmu, get_user_org
from effektiviseringskrav.backend.ir_calculations import (
    load_ir_paverkbara_baseline,
    calculate_ir_paverkbara_export
)
from foretag.app.diagram_utils import create_interactive_diagram_html
from foretag.view.intaktsram_tabs.oversikt import show_oversikt_tab
from foretag.view.intaktsram_tabs.kapitalkostnad import show_kapitalkostnad_tab
from foretag.view.intaktsram_tabs.effektiviseringskrav import show_effektiviseringskrav_tab
from foretag.app.scenario_utils import (
    create_scenario,
    reset_to_baseline,
    list_saved_scenarios,
    load_scenario_from_file,
    save_scenario_to_file
)


def show_foretag_ir_dekomposition_ny():
    """
    Huvudfunktion för ny intäktsram-dekomposition.
    Hanterar autentisering, data-laddning och tab-struktur.
    """
    
    st.set_page_config(page_title="Din Intäktsram", layout="wide")
    
    if "access_granted" not in st.session_state or not st.session_state.access_granted:
        st.error("Åtkomst nekad")
        st.stop()
    
    if st.session_state.user_role != "company":
        st.error("Denna sida är endast tillgänglig för företagsanvändare")
        st.stop()
    
    user_dmu = get_user_dmu()
    if user_dmu is None:
        st.error("Ingen DMU hittades för ditt konto")
        st.stop()
    
    initialize_session_state()
    
    df_company = load_company_data(user_dmu)
    
    if df_company.empty:
        st.error(f"Ingen data hittades för DMU {user_dmu}")
        st.stop()
    
    show_sidebar_scenario_controls(df_company)
    
    company_name = df_company.iloc[0].get('Företag', f'Företag DMU {user_dmu}')
    st.title(f"Din Intäktsram - {company_name}")
    st.caption(f"DMU {user_dmu} • Interaktiv visualisering med scenario-stöd")
    
    df_working = get_working_dataframe(df_company)
    
    if len(df_working) > 1:
        reid_options = df_working['REId'].tolist()
        selected_reid = st.selectbox("Välj lokalnät", reid_options)
        entity_data = df_working[df_working['REId'] == selected_reid].iloc[0]
    else:
        entity_data = df_working.iloc[0]
        selected_reid = entity_data['REId']
    
    diagram_data = prepare_diagram_data(entity_data, df_company)
    html_content = create_interactive_diagram_html(diagram_data)
    components.html(html_content, height=720, scrolling=False)
    
    st.markdown("---")
    
    tabs = st.tabs([
        "Översikt",
        "Kapitalkostnad",
        "Effektiviseringskrav",
        "Opåverkbara kostnader",
        "Övriga komponenter"
    ])
    
    with tabs[0]:
        show_oversikt_tab(entity_data)
    
    with tabs[1]:
        scenario_metadata = get_scenario_metadata()
        show_kapitalkostnad_tab(entity_data, scenario_metadata)
    
    with tabs[2]:
        show_effektiviseringskrav_tab(entity_data, df_company)
    
    with tabs[3]:
        st.info("Opåverkbara kostnader-tab implementeras i Fas 2")
    
    with tabs[4]:
        st.info("Övriga komponenter-tab implementeras i Fas 2")


def initialize_session_state():
    """Initialiserar session state för scenario-hantering."""
    if 'scenarios' not in st.session_state:
        st.session_state.scenarios = {}
    
    if 'current_scenario_name' not in st.session_state:
        st.session_state.current_scenario_name = ""
    
    if 'scenario_data' not in st.session_state:
        st.session_state.scenario_data = {}
    
    if 'show_scenario_loader' not in st.session_state:
        st.session_state.show_scenario_loader = False
    
    if 'show_kapitalbas_import' not in st.session_state:
        st.session_state.show_kapitalbas_import = False


def load_company_data(user_dmu: int) -> pd.DataFrame:
    """
    Laddar och filtrerar data för företaget.
    
    Args:
        user_dmu: Företagets DMU
        
    Returns:
        DataFrame med företagets lokalnät
    """
    baseline_file = "intaktsram/data/Löpande kostnader från SDF 2024-27.xlsx"
    df_baseline = load_baseline_data(baseline_file)
    
    df_baseline = df_baseline[
        df_baseline['REId'].astype(str).str.startswith('REL') & 
        ~df_baseline['REId'].astype(str).str.startswith('RER')
    ].copy()
    
    df_company = df_baseline[df_baseline['DMU'] == user_dmu]
    
    return df_company


def get_working_dataframe(baseline_df: pd.DataFrame) -> pd.DataFrame:
    """
    Hämtar working dataframe med scenario-modifieringar.
    Applicerar kapitalbas först, sedan effektiviseringskrav.
    
    Args:
        baseline_df: Baseline DataFrame
        
    Returns:
        DataFrame med applicerade scenarier
    """
    if not st.session_state.current_scenario_name or 'scenario_data' not in st.session_state:
        return baseline_df.copy()
    
    working_df = st.session_state.scenario_data['baseline'].copy()
    modifications = st.session_state.scenario_data.get('modifications', {})
    
    # STEG 1: APPLICERA KAPITALBAS-SCENARIO
    if 'kapitalkostnad' in modifications:
        mod_data = modifications['kapitalkostnad']
        if 'values' in mod_data:
            merge_on = mod_data.get('merge_on', 'REId')
            for entity_key, new_values in mod_data['values'].items():
                mask = working_df['DMU'] == float(entity_key) if merge_on == 'DMU' else working_df['REId'] == entity_key
                
                if mask.any():
                    if isinstance(new_values, dict):
                        if 'avskrivningar' in new_values:
                            working_df.loc[mask, 'Avskrivningar'] = new_values['avskrivningar']
                        if 'avkastning' in new_values:
                            working_df.loc[mask, 'Avkastning'] = new_values['avkastning']
                        if 'total' in new_values:
                            working_df.loc[mask, 'Kapitalkostnad_Total'] = new_values['total']
                    else:
                        working_df.loc[mask, 'Kapitalkostnad_Total'] = new_values
                    
                    working_df.loc[mask, 'Källa_Kapitalkostnad'] = f"Scenario ({mod_data.get('source', 'manual')})"
                    working_df.loc[mask, 'Uppdaterad_Kapitalkostnad'] = True
    
    # STEG 2: APPLICERA EFFEKTIVISERINGSKRAV MED AKTUELL CAPEX
    if 'paverkbara' in modifications:
        mod_data = modifications['paverkbara']
        
        if mod_data.get('source') == 'effektiviseringskrav':
            dea_result = mod_data.get('dea_result')
            method = mod_data.get('method', 'OPEX')
            
            if dea_result is not None:
                try:
                    ir_baseline_file = "intaktsram/data/Löpande kostnader från SDF 2024-27.xlsx"
                    ir_baseline = load_ir_paverkbara_baseline(ir_baseline_file)
                    
                    export_data, metadata = calculate_ir_paverkbara_export(
                        dea_result=dea_result,
                        ir_baseline=ir_baseline,
                        working_df=working_df,
                        method=method
                    )
                    
                    if not export_data.empty:
                        for _, row in export_data.iterrows():
                            reid = row['REId']
                            mask = working_df['REId'] == reid
                            
                            if mask.any():
                                working_df.loc[mask, 'Paverkbara_Kostnader'] = row['Paverkbara_Target']
                                working_df.loc[mask, 'Källa_Paverkbara'] = f"Scenario (effektiviseringskrav - {method})"
                                working_df.loc[mask, 'Uppdaterad_Paverkbara'] = True
                        
                        # KRITISK FIX: Spara beräkningsresultat för breakdown
                        mod_data['last_calculation'] = {
                            'export_data': export_data,
                            'metadata': metadata,
                            'timestamp': pd.Timestamp.now().isoformat()
                        }
                    
                except Exception as e:
                    st.error(f"Fel vid beräkning av påverkbara kostnader: {e}")
                    import traceback
                    st.error(traceback.format_exc())
    
    # STEG 3: OMBERÄKNA TOTALER
    working_df = calculate_intaktsram(working_df)
    
    return working_df


def prepare_diagram_data(entity_data: pd.Series, df_baseline: pd.DataFrame) -> Dict[str, float]:
    """
    Förbereder data för diagrammet från entity_data.
    """
    baseline_row = df_baseline[df_baseline['REId'] == entity_data['REId']]
    
    if not baseline_row.empty:
        baseline_paverkbara = float(baseline_row.iloc[0].get('Paverkbara_Kostnader', 0) or 0)
        baseline_kapitalkostnad = float(baseline_row.iloc[0].get('Kapitalkostnad_Total', 0) or 0)
    else:
        baseline_paverkbara = 0
        baseline_kapitalkostnad = 0
    
    paverkbara = float(entity_data.get('Paverkbara_Kostnader', 0) or 0)
    kapitalkostnad_total = float(entity_data.get('Kapitalkostnad_Total', 0) or 0)
    
    effektivisering = paverkbara - baseline_paverkbara
    
    avkastning = float(entity_data.get('Avkastning', 0) or 0)
    
    kapitalbas = 0
    scenario_metadata = get_scenario_metadata()
    if scenario_metadata and avkastning > 0:
        wacc = scenario_metadata.get('wacc_new', 0.0453)
        if wacc > 0:
            kapitalbas = avkastning / wacc
    
    return {
        'paverkbara': baseline_paverkbara,
        'ej_paverkbara': float(entity_data.get('Opaverkbara_Kostnader', 0) or 0),
        'kapitalbas': kapitalbas,
        'effektivisering': effektivisering,
        'avskrivningar': float(entity_data.get('Avskrivningar', 0) or 0),
        'avkastning': avkastning,
        'kvalitet': float(entity_data.get('Flexibilitetstjanster', 0) or 0)
    }


def get_scenario_metadata() -> Optional[dict]:
    """
    Hämtar scenario-metadata för kapitalkostnad från session state.
    """
    if not st.session_state.current_scenario_name or 'scenario_data' not in st.session_state:
        return None
    
    modifications = st.session_state.scenario_data.get('modifications', {})
    
    if 'kapitalkostnad' not in modifications:
        return None
    
    return modifications['kapitalkostnad'].get('metadata', None)


def show_sidebar_scenario_controls(baseline_df: pd.DataFrame):
    """
    Visar scenario-kontroller i sidebar.
    """
    st.sidebar.header("Scenario-hantering")
    
    scenario_name = st.sidebar.text_input(
        "Scenario-namn",
        value=st.session_state.current_scenario_name,
        placeholder="t.ex. WACC 4.75%"
    )
    
    if st.sidebar.button("Skapa nytt scenario", use_container_width=True):
        if create_scenario(scenario_name, baseline_df):
            st.sidebar.success(f"Scenario '{scenario_name}' skapat!")
            st.rerun()
    
    st.sidebar.markdown("---")
    
    saved_scenarios = list_saved_scenarios()
    
    if saved_scenarios:
        if st.sidebar.button("Ladda sparat scenario", use_container_width=True):
            st.session_state.show_scenario_loader = True
        
        if st.session_state.get('show_scenario_loader', False):
            with st.sidebar.expander("Välj scenario att ladda", expanded=True):
                scenario_names = [s[0] for s in saved_scenarios]
                selected_name = st.selectbox(
                    "Sparade scenarier",
                    options=scenario_names,
                    key="scenario_selector"
                )
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Ladda", use_container_width=True):
                        selected_path = next(s[1] for s in saved_scenarios if s[0] == selected_name)
                        df_loaded, metadata = load_scenario_from_file(selected_path)
                        
                        st.session_state.current_scenario_name = selected_name
                        st.session_state.scenario_data = {
                            'baseline': df_loaded,
                            'modifications': metadata.get('modifications', {}),
                            'created': metadata.get('created'),
                            'component_sources': metadata.get('component_sources', {})
                        }
                        st.session_state.show_scenario_loader = False
                        st.sidebar.success(f"Scenario '{selected_name}' laddat!")
                        st.rerun()
                
                with col2:
                    if st.button("Avbryt", use_container_width=True):
                        st.session_state.show_scenario_loader = False
                        st.rerun()
    else:
        st.sidebar.info("Inga sparade scenarier ännu")
    
    if st.session_state.current_scenario_name:
        st.sidebar.markdown("---")
        st.sidebar.write(f"**Aktivt scenario:** {st.session_state.current_scenario_name}")
        
        if st.sidebar.button("Spara scenario", use_container_width=True):
            df_to_save = get_working_dataframe(baseline_df)
            filepath = save_scenario_to_file(st.session_state.current_scenario_name, df_to_save)
            st.sidebar.success(f"Scenario sparat!")
        
        if st.sidebar.button("Återställ till baseline", use_container_width=True):
            reset_to_baseline()
            st.sidebar.success("Återställt till baseline")
            st.rerun()
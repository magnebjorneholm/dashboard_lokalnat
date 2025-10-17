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


def prepare_diagram_data(entity_data: pd.Series, df_baseline: pd.DataFrame) -> Dict[str, dict]:
    """
    Förbereder data för diagrammet med modifieringsinformation.
    
    Returns:
        Dict där varje komponent har struktur:
        {
            'value': float,
            'baseline': float,
            'is_directly_modified': bool,
            'source': str
        }
    """
    baseline_row = df_baseline[df_baseline['REId'] == entity_data['REId']]
    
    # Hämta baseline-värden från Excel (EFTER Ei:s baseline-avdrag)
    if not baseline_row.empty:
        baseline_paverkbara_efter_avdrag = float(baseline_row.iloc[0].get('Paverkbara_Kostnader', 0) or 0)
        baseline_opaverkbara = float(baseline_row.iloc[0].get('Opaverkbara_Kostnader', 0) or 0)
        baseline_avskrivningar = float(baseline_row.iloc[0].get('Avskrivningar', 0) or 0)
        baseline_avkastning = float(baseline_row.iloc[0].get('Avkastning', 0) or 0)
        baseline_flexibilitetstjanster = float(baseline_row.iloc[0].get('Flexibilitetstjanster', 0) or 0)
        baseline_avbrottsersattning = float(baseline_row.iloc[0].get('Avbrottsersattning_12_24h', 0) or 0)
        
        # Läs Ei:s baseline-avdrag direkt från Excel kolumn DZ
        baseline_totalt_avdrag_excel = 0
        try:
            excel_path = "intaktsram/data/Löpande kostnader från SDF 2024-27.xlsx"
            df_avdrag = pd.read_excel(excel_path, sheet_name="Påverkbara", engine="openpyxl")
            # Kolumn DZ är index 129
            if len(df_avdrag.columns) > 129:
                # Hitta rätt rad för detta REId
                reid_col = df_avdrag.iloc[:, 0]  # Kolumn A
                matching_rows = df_avdrag[reid_col == entity_data['REId']]
                if not matching_rows.empty:
                    avdrag_value = matching_rows.iloc[0, 129]
                    baseline_totalt_avdrag_excel = float(avdrag_value) if pd.notna(avdrag_value) else 0
        except Exception as e:
            pass  # Tyst fallback till 0
    else:
        baseline_paverkbara_efter_avdrag = baseline_opaverkbara = 0
        baseline_avskrivningar = baseline_avkastning = 0
        baseline_flexibilitetstjanster = baseline_avbrottsersattning = 0
        baseline_totalt_avdrag_excel = 0
    
    # Hämta aktuella värden (scenario)
    paverkbara_scenario = float(entity_data.get('Paverkbara_Kostnader', 0) or 0)
    ej_paverkbara = float(entity_data.get('Opaverkbara_Kostnader', 0) or 0)
    avskrivningar = float(entity_data.get('Avskrivningar', 0) or 0)
    avkastning = float(entity_data.get('Avkastning', 0) or 0)
    flexibilitetstjanster = float(entity_data.get('Flexibilitetstjanster', 0) or 0)
    avbrottsersattning = float(entity_data.get('Avbrottsersattning_12_24h', 0) or 0)
    
    # Hämta modifieringsflaggor
    is_paverkbara_modified = bool(entity_data.get('Uppdaterad_Paverkbara', False))
    is_kapital_modified = bool(entity_data.get('Uppdaterad_Kapitalkostnad', False))
    
    source_paverkbara = str(entity_data.get('Källa_Paverkbara', 'Baseline'))
    source_kapitalkostnad = str(entity_data.get('Källa_Kapitalkostnad', 'Baseline'))
    
    # === FIX PROBLEM 1 & 2: HÄMTA BASELINE- OCH SCENARIO-AVDRAG ===
    baseline_totalt_avdrag = baseline_totalt_avdrag_excel  # Från Excel kolumn DZ
    scenario_totalt_avdrag = 0
    
    if 'scenario_data' in st.session_state:
        modifications = st.session_state.scenario_data.get('modifications', {})
        effkrav_mod = modifications.get('paverkbara', {})
        last_calc = effkrav_mod.get('last_calculation')
        
        if last_calc:
            export_data = last_calc.get('export_data')
            if export_data is not None and not export_data.empty:
                entity_calc = export_data[export_data['REId'] == entity_data['REId']]
                if not entity_calc.empty:
                    row = entity_calc.iloc[0]
                    
                    # BASELINE-AVDRAG från beräkning (mer exakt än Excel om tillgänglig)
                    baseline_totalt_avdrag = sum([
                        float(row.get('Avdrag_2024_base', 0)),
                        float(row.get('Avdrag_2025_base', 0)),
                        float(row.get('Avdrag_2026_base', 0)),
                        float(row.get('Avdrag_2027_base', 0))
                    ])
                    
                    # SCENARIO-AVDRAG (importerat från DEA)
                    scenario_totalt_avdrag = sum([
                        float(row.get('Avdrag_2024_scn', 0)),
                        float(row.get('Avdrag_2025_scn', 0)),
                        float(row.get('Avdrag_2026_scn', 0)),
                        float(row.get('Avdrag_2027_scn', 0))
                    ])
    
    # FIX PROBLEM 1: Påverkbara kostnader FÖRE alla avdrag
    baseline_paverkbara_fore_avdrag = baseline_paverkbara_efter_avdrag + baseline_totalt_avdrag
    
    # FIX PROBLEM 2: Box 4 visar ALLTID effektiviseringskrav
    # - Baseline-läge: Visa Ei:s baseline-avdrag (blå)
    # - Scenario-läge: Visa scenario-avdrag (orange)
    if is_paverkbara_modified:
        effektivisering_value = scenario_totalt_avdrag
    else:
        effektivisering_value = baseline_totalt_avdrag
    
    # Beräkna kapitalbas
    kapitalbas = 0
    baseline_kapitalbas = 0
    scenario_metadata = get_scenario_metadata()
    
    if avkastning > 0:
        wacc = 0.0453
        if scenario_metadata and scenario_metadata.get('wacc_new'):
            wacc = scenario_metadata.get('wacc_new')
        kapitalbas = avkastning / wacc if wacc > 0 else 0
    
    if baseline_avkastning > 0:
        wacc_baseline = 0.0453
        if scenario_metadata and scenario_metadata.get('wacc_old'):
            wacc_baseline = scenario_metadata.get('wacc_old')
        baseline_kapitalbas = baseline_avkastning / wacc_baseline if wacc_baseline > 0 else 0
    
    TOLERANCE = 1.0
    
    effektivisering_active = is_paverkbara_modified and abs(effektivisering_value) > TOLERANCE
    
    # Endast källor blir orange
    paverkbara_direct = False
    kapitalbas_direct = is_kapital_modified
    effektivisering_direct = effektivisering_active
    avskrivningar_direct = False
    avkastning_direct = False
    
    # Beräkna summor för tooltip och flöde
    lopande_value = baseline_paverkbara_fore_avdrag + ej_paverkbara - abs(effektivisering_value)
    lopande_baseline = baseline_paverkbara_efter_avdrag + baseline_opaverkbara
    
    # Box 9: Kapitalkostnader (endast Avskrivningar + Avkastning)
    kapitalkostnader_value = avskrivningar + avkastning
    kapitalkostnader_baseline = baseline_avskrivningar + baseline_avkastning
    
    # Box 11: Intäktsram inkluderar även Flexibilitetstjänster och Avbrottsersättning
    intaktsram_value = (lopande_value + kapitalkostnader_value + 
                        flexibilitetstjanster + avbrottsersattning)
    intaktsram_baseline = (lopande_baseline + kapitalkostnader_baseline + 
                           baseline_flexibilitetstjanster + baseline_avbrottsersattning)
    
    return {
        # BOX 1: Påverkbara kostnader FÖRE avdrag
        'paverkbara': {
            'value': baseline_paverkbara_fore_avdrag,
            'baseline': baseline_paverkbara_fore_avdrag,
            'is_directly_modified': paverkbara_direct,
            'source': source_paverkbara
        },
        'ej_paverkbara': {
            'value': ej_paverkbara,
            'baseline': baseline_opaverkbara,
            'is_directly_modified': False,
            'source': 'Baseline'
        },
        'kapitalbas': {
            'value': kapitalbas,
            'baseline': baseline_kapitalbas,
            'is_directly_modified': kapitalbas_direct,
            'source': 'Beräknad från avkastning' if kapitalbas_direct else 'Baseline'
        },
        # BOX 4: Totalt kumulativt avdrag från scenario
        'effektivisering': {
            'value': abs(effektivisering_value),
            'baseline': 0,
            'is_directly_modified': effektivisering_direct,
            'source': source_paverkbara if effektivisering_direct else 'Ingen'
        },
        'avskrivningar': {
            'value': avskrivningar,
            'baseline': baseline_avskrivningar,
            'is_directly_modified': avskrivningar_direct,
            'source': source_kapitalkostnad if is_kapital_modified else 'Baseline'
        },
        'avkastning': {
            'value': avkastning,
            'baseline': baseline_avkastning,
            'is_directly_modified': avkastning_direct,
            'source': source_kapitalkostnad if is_kapital_modified else 'Baseline'
        },
        'lopande': {
            'value': lopande_value,
            'baseline': lopande_baseline,
            'is_directly_modified': False,
            'source': 'Beräknad summa'
        },
        'kapitalkostnader': {
            'value': kapitalkostnader_value,
            'baseline': kapitalkostnader_baseline,
            'is_directly_modified': False,
            'source': 'Beräknad summa'
        },
        'intaktsram': {
            'value': intaktsram_value,
            'baseline': intaktsram_baseline,
            'is_directly_modified': False,
            'source': 'Slutlig summa'
        }
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
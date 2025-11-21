"""
Huvudvy för intäktsram-dekomposition UTAN sidebar
All case-hantering är flyttad till Översikt-tabben
"""

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from typing import Dict, Optional
from datetime import datetime
from pathlib import Path

from core.data_loader_intaktsram import (
    load_baseline_data,
    calculate_intaktsram
)
from core.data_loader_base import get_company_display_name
from core.session_utils import get_user_role, get_user_dmu, get_user_org
from effektivitet.backend.ir_calculations import (
    load_ir_paverkbara_baseline,
    calculate_ir_paverkbara_export
)
from återanvändas.diagram_utils import create_interactive_diagram_html
from intaktsram.frontend.intaktsram_tabs.oversikt import show_oversikt_tab
from intaktsram.frontend.intaktsram_tabs.kapitalkostnad import show_kapitalkostnad_tab
from intaktsram.frontend.intaktsram_tabs.effektiviseringskrav import show_effektiviseringskrav_tab


def show_foretag_ir_dekomposition_ny():
    """
    Huvudfunktion för intäktsram-dekomposition.
    INGEN SIDEBAR - all scenario-hantering i Översikt-tab.
    """
    
    st.set_page_config(page_title="Dekomposition intäktsram", layout="wide")
    
    # Autentisering
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
    
    # Initialisera session state
    initialize_session_state()
    
    # Ladda företagsdata
    df_company = load_company_data(user_dmu)
    
    if df_company.empty:
        st.error(f"Ingen data hittades för DMU {user_dmu}")
        st.stop()
    
    # Titel
    base_name = df_company.iloc[0].get('Företag', f'Företag DMU {user_dmu}')
    company_name = get_company_display_name(user_dmu, base_name)
    st.title(f"Intäktsramen för {company_name}")
    
    # Working dataframe med scenario-applicering
    df_working = get_working_dataframe(df_company)
    entity_data = df_working.iloc[0]
    
    # Interaktivt diagram
    diagram_data = prepare_diagram_data(entity_data, df_company)
    html_content = create_interactive_diagram_html(diagram_data)
    components.html(html_content, height=720, scrolling=False)
    
    st.markdown("---")
    
    # Tabs
    tabs = st.tabs([
        "Översikt",
        "Kapitalkostnad",
        "Effektiviseringskrav",
        "Opåverkbara kostnader",
        "Övriga komponenter"
    ])
    
    with tabs[0]:
        show_oversikt_tab(entity_data, df_company)
    
    with tabs[1]:
        scenario_metadata = get_scenario_metadata()
        show_kapitalkostnad_tab(entity_data, scenario_metadata)
    
    with tabs[2]:
        show_effektiviseringskrav_tab(entity_data, df_company)
    
    with tabs[3]:
        st.info("Opåverkbara kostnader-tab implementeras i senare fas")
    
    with tabs[4]:
        st.info("Övriga komponenter-tab implementeras i senare fas")


def initialize_session_state():
    """Initialiserar session state för case-hantering."""
    if 'scenarios' not in st.session_state:
        st.session_state.scenarios = {}
    
    if 'current_scenario_name' not in st.session_state:
        st.session_state.current_scenario_name = ""
    
    if 'scenario_data' not in st.session_state:
        st.session_state.scenario_data = {}
    
    if 'show_scenario_loader' not in st.session_state:
        st.session_state.show_scenario_loader = False


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
    Hämtar working dataframe med applied scenario-modifieringar.
    Använder applied_modifications från pending_changes strukturen.
    
    Args:
        baseline_df: Baseline DataFrame
        
    Returns:
        DataFrame med applicerade scenarier
    """
    if not st.session_state.current_scenario_name or 'scenario_data' not in st.session_state:
        return baseline_df.copy()
    
    working_df = st.session_state.scenario_data['baseline'].copy()
    applied_modifications = st.session_state.scenario_data.get('applied_modifications', {})
    
    # STEG 1: APPLICERA KAPITALBAS-SCENARIO
    if 'kapitalkostnad' in applied_modifications:
        mod_data = applied_modifications['kapitalkostnad']
        
        # Metadata innehåller de faktiska värdena
        metadata = mod_data.get('metadata', {})
        new_avskrivningar = metadata.get('new_avskrivningar')
        new_avkastning = metadata.get('new_avkastning')
        source = mod_data.get('source', 'Scenario')
        
        if new_avskrivningar is not None and new_avkastning is not None:
            for idx in working_df.index:
                working_df.loc[idx, 'Avskrivningar'] = new_avskrivningar
                working_df.loc[idx, 'Avkastning'] = new_avkastning
                working_df.loc[idx, 'Kapitalkostnad_Total'] = new_avskrivningar + new_avkastning
                working_df.loc[idx, 'Uppdaterad_Kapitalkostnad'] = True
                working_df.loc[idx, 'Källa_Kapitalkostnad'] = source
    
    # STEG 2: APPLICERA EFFEKTIVISERINGSKRAV
    if 'paverkbara' in applied_modifications:
        effkrav_mod = applied_modifications['paverkbara']
        dea_result = effkrav_mod.get('dea_result')
        method = effkrav_mod.get('method', 'OPEX')
        
        if dea_result is not None and not dea_result.empty:
            ir_baseline_file = "intaktsram/data/Löpande kostnader från SDF 2024-27.xlsx"
            
            # Använd cached version
            from intaktsram.backend.cached_data_loader import load_ir_paverkbara_baseline_cached
            ir_baseline = load_ir_paverkbara_baseline_cached(ir_baseline_file)
            
            try:
                export_data, metadata = calculate_ir_paverkbara_export(
                    dea_result=dea_result,
                    ir_baseline=ir_baseline,
                    working_df=working_df,
                    method=method
                )

                if export_data is not None:
                    effkrav_mod['last_calculation'] = {
                        'export_data': export_data,
                        'metadata': metadata
                    }

                    for _, row in export_data.iterrows():
                        reid = row['REId']
                        mask = working_df['REId'] == reid

                        if mask.any():
                            working_df.loc[mask, 'Paverkbara_Kostnader'] = row['Paverkbara_Target']
                            working_df.loc[mask, 'Uppdaterad_Paverkbara'] = True
                            working_df.loc[mask, 'Källa_Paverkbara'] = f'DEA ({method})'

            except Exception as e:
                st.error(f"Fel vid applicering av effektiviseringskrav: {e}")
    
    # STEG 3: OMBERÄKNA TOTAL INTÄKTSRAM
    working_df = calculate_intaktsram(working_df)
    
    return working_df


def prepare_diagram_data(entity_data: pd.Series, df_baseline: pd.DataFrame) -> Dict:
    """
    Förbereder data för interaktivt Sankey-diagram.
    Hämtar baseline från Excel och jämför med scenario-värden.
    
    Args:
        entity_data: Series med scenario-data för vald entitet (från working_df)
        df_baseline: Baseline DataFrame (ursprunglig data från Excel)
        
    Returns:
        Dictionary med diagram-data
    """
    baseline_row = df_baseline[df_baseline['REId'] == entity_data['REId']]
    
    # Scenario-värden från entity_data
    paverkbara_efter_avdrag = float(entity_data.get('Paverkbara_Kostnader', 0))
    ej_paverkbara = float(entity_data.get('Opaverkbara_Kostnader', 0))
    avskrivningar = float(entity_data.get('Avskrivningar', 0))
    avkastning = float(entity_data.get('Avkastning', 0))
    
    # Baseline-värden från Excel
    if not baseline_row.empty:
        baseline_paverkbara_efter_avdrag = float(baseline_row.iloc[0].get('Paverkbara_Kostnader', 0) or 0)
        baseline_ej_paverkbara = float(baseline_row.iloc[0].get('Opaverkbara_Kostnader', 0) or 0)
        baseline_avskrivningar = float(baseline_row.iloc[0].get('Avskrivningar', 0) or 0)
        baseline_avkastning = float(baseline_row.iloc[0].get('Avkastning', 0) or 0)
    else:
        baseline_paverkbara_efter_avdrag = paverkbara_efter_avdrag
        baseline_ej_paverkbara = ej_paverkbara
        baseline_avskrivningar = avskrivningar
        baseline_avkastning = avkastning
    
    # Hämta effektiviseringskrav från Excel baseline (kolumn DZ = index 129)
    # Använd cached version
    from intaktsram.backend.cached_data_loader import load_ei_effektiviseringskrav_cached
    
    excel_path = "intaktsram/data/Löpande kostnader från SDF 2024-27.xlsx"
    baseline_totalt_avdrag = load_ei_effektiviseringskrav_cached(excel_path, entity_data['REId'])
    
    # Hämta scenario-effektiviseringskrav
    scenario_data = st.session_state.get('scenario_data', {})
    applied_modifications = scenario_data.get('applied_modifications', {})
    effkrav_mod = applied_modifications.get('paverkbara', {})
    
    scenario_totalt_avdrag = baseline_totalt_avdrag
    if effkrav_mod and effkrav_mod.get('last_calculation'):
        last_calc = effkrav_mod['last_calculation']
        export_data = last_calc.get('export_data')
        if export_data is not None and not export_data.empty:
            entity_calc = export_data[export_data['REId'] == entity_data['REId']]
            if not entity_calc.empty:
                row = entity_calc.iloc[0]
                scenario_totalt_avdrag = sum([
                    float(row.get('Avdrag_2024_scn', 0)),
                    float(row.get('Avdrag_2025_scn', 0)),
                    float(row.get('Avdrag_2026_scn', 0)),
                    float(row.get('Avdrag_2027_scn', 0))
                ])
    
    # Beräkna påverkbara FÖRE avdrag
    baseline_paverkbara_fore_avdrag = baseline_paverkbara_efter_avdrag + baseline_totalt_avdrag
    
    # Beräkna kapitalbas från avkastning/WACC
    scenario_metadata = get_scenario_metadata()
    wacc = 0.0453
    wacc_baseline = 0.0453
    
    if scenario_metadata and scenario_metadata.get('wacc_new'):
        wacc = scenario_metadata.get('wacc_new')
    if scenario_metadata and scenario_metadata.get('wacc_old'):
        wacc_baseline = scenario_metadata.get('wacc_old')
    
    kapitalbas = avkastning / wacc if wacc > 0 and avkastning > 0 else 0
    baseline_kapitalbas = baseline_avkastning / wacc_baseline if wacc_baseline > 0 and baseline_avkastning > 0 else 0
    
    # Modifieringsstatus
    is_kapital_modified = entity_data.get('Uppdaterad_Kapitalkostnad', False)
    is_paverkbara_modified = entity_data.get('Uppdaterad_Paverkbara', False)
    
    source_kapitalkostnad = entity_data.get('Källa_Kapitalkostnad', 'Baseline')
    source_paverkbara = entity_data.get('Källa_Paverkbara', 'Baseline')
    
    # Beräkna summor
    kapitalkostnad_total = avskrivningar + avkastning
    baseline_kapitalkostnad = baseline_avskrivningar + baseline_avkastning
    
    lopande_value = baseline_paverkbara_fore_avdrag + ej_paverkbara - abs(scenario_totalt_avdrag)
    lopande_baseline = baseline_paverkbara_efter_avdrag + baseline_ej_paverkbara
    
    intaktsram_total = lopande_value + kapitalkostnad_total
    baseline_intaktsram = lopande_baseline + baseline_kapitalkostnad
    
    return {
        'paverkbara': {
            'value': baseline_paverkbara_fore_avdrag,
            'baseline': baseline_paverkbara_fore_avdrag,
            'is_directly_modified': False,
            'source': 'Baseline'
        },
        'ej_paverkbara': {
            'value': ej_paverkbara,
            'baseline': baseline_ej_paverkbara,
            'is_directly_modified': False,
            'source': 'Baseline'
        },
        'kapitalbas': {
            'value': kapitalbas,
            'baseline': baseline_kapitalbas,
            'is_directly_modified': is_kapital_modified,
            'source': source_kapitalkostnad if is_kapital_modified else 'Baseline'
        },
        'effektivisering': {
            'value': scenario_totalt_avdrag,
            'baseline': baseline_totalt_avdrag,
            'is_directly_modified': is_paverkbara_modified,
            'source': source_paverkbara if is_paverkbara_modified else 'Baseline'
        },
        'avskrivningar': {
            'value': avskrivningar,
            'baseline': baseline_avskrivningar,
            'is_directly_modified': is_kapital_modified,
            'source': source_kapitalkostnad if is_kapital_modified else 'Baseline'
        },
        'avkastning': {
            'value': avkastning,
            'baseline': baseline_avkastning,
            'is_directly_modified': is_kapital_modified,
            'source': source_kapitalkostnad if is_kapital_modified else 'Baseline'
        },
        'kvalitet': {
            'value': 0,
            'baseline': 0,
            'is_directly_modified': False,
            'source': 'Baseline'
        },
        'lopande': {
            'value': lopande_value,
            'baseline': lopande_baseline,
            'is_directly_modified': False,
            'source': 'Beräknad summa'
        },
        'kapitalkostnader': {
            'value': kapitalkostnad_total,
            'baseline': baseline_kapitalkostnad,
            'is_directly_modified': False,
            'source': 'Beräknad summa'
        },
        'intaktsram': {
            'value': intaktsram_total,
            'baseline': baseline_intaktsram,
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
    scenario_data = st.session_state.scenario_data

    # Försök hämta nya nyckeln 'applied_modifications', fallback till legacy 'modifications'
    applied = scenario_data.get('applied_modifications') or scenario_data.get('modifications') or {}

    if 'kapitalkostnad' not in applied:
        return None

    entry = applied['kapitalkostnad']

    # Om entry är en struktur med 'metadata' returnera det, annars returnera entry (kompatibilitet)
    if isinstance(entry, dict):
        return entry.get('metadata', entry)

    return None
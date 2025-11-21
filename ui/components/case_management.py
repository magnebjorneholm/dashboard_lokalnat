"""
Case management komponenter
Refaktorerad från oversikt.py för ny modulär arkitektur
"""

import streamlit as st
import pandas as pd
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any


def save_case(
    case_name: str,
    case_definition: Dict[str, Any],
    results: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Sparar ett case till disk.
    
    Args:
        case_name: Namn på caset
        case_definition: Case definition från CaseDefinitionManager
        results: Resultat från beräkningar (optional)
        
    Returns:
        True om lyckades, False annars
    """
    try:
        save_dir = Path("saved_cases") / str(st.session_state.user_dmu)
        save_dir.mkdir(parents=True, exist_ok=True)
        
        safe_name = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in case_name)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{safe_name}_{timestamp}.json"
        filepath = save_dir / filename
        
        save_data = {
            'case_name': case_name,
            'created': datetime.now().isoformat(),
            'user_dmu': st.session_state.user_dmu,
            'case_definition': case_definition,
            'results': results
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, indent=2, ensure_ascii=False)
        
        return True
    
    except Exception as e:
        st.error(f"Kunde inte spara case: {e}")
        return False


def load_case(filepath: str) -> Optional[Dict[str, Any]]:
    """
    Laddar ett case från disk.
    
    Args:
        filepath: Sökväg till case-fil
        
    Returns:
        Dict med case-data eller None om misslyckades
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            case_data = json.load(f)
        
        if case_data.get('user_dmu') != st.session_state.user_dmu:
            st.warning("Detta case tillhör ett annat företag")
            return None
        
        return case_data
    
    except Exception as e:
        st.error(f"Kunde inte ladda case: {e}")
        return None


def list_cases() -> List[Dict[str, Any]]:
    """
    Listar alla sparade cases för aktuell användare.
    
    Returns:
        Lista med case-information
    """
    try:
        save_dir = Path("saved_cases") / str(st.session_state.user_dmu)
        
        if not save_dir.exists():
            return []
        
        cases = []
        for filepath in save_dir.glob("*.json"):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    case_data = json.load(f)
                
                cases.append({
                    'filepath': str(filepath),
                    'filename': filepath.name,
                    'case_name': case_data.get('case_name', 'Unnamed'),
                    'created': case_data.get('created', ''),
                    'has_results': case_data.get('results') is not None
                })
            except:
                continue
        
        cases.sort(key=lambda x: x['created'], reverse=True)
        return cases
    
    except Exception as e:
        st.error(f"Kunde inte lista cases: {e}")
        return []


def render_case_selector() -> Optional[Dict[str, Any]]:
    """
    Renderar case selector med spara/ladda funktionalitet.
    
    Returns:
        Valt case data eller None
    """
    st.markdown("### Case-hantering")
    st.caption("Skapa, spara eller ladda cases för olika scenarioanalyser")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        case_name = st.text_input(
            "Case-namn",
            value=st.session_state.get('current_case_name', ''),
            placeholder="t.ex. WACC 4.75%",
            key="case_name_input"
        )
    
    with col2:
        if st.button("Nytt case", type="primary", use_container_width=True):
            if case_name.strip():
                st.session_state.current_case_name = case_name.strip()
                st.session_state.case_definition = {
                    'name': case_name.strip(),
                    'created': datetime.now().isoformat(),
                    'parameters': {},
                    'variables': {},
                    'modules': {}
                }
                st.success(f"Nytt case skapat: {case_name}")
                st.rerun()
            else:
                st.error("Ange ett case-namn")
    
    with col3:
        if st.button("Spara case", use_container_width=True):
            if not st.session_state.get('current_case_name'):
                st.error("Inget aktivt case att spara")
            else:
                case_def = st.session_state.get('case_definition', {})
                results = st.session_state.get('case_results', {})
                
                if save_case(
                    st.session_state.current_case_name,
                    case_def,
                    results
                ):
                    st.success("Case sparat!")
    
    st.markdown("---")
    
    cases = list_cases()
    
    if cases:
        st.markdown("**Sparade cases**")
        
        case_options = {f"{c['case_name']} ({c['created'][:10]})": c for c in cases}
        
        selected = st.selectbox(
            "Välj case att ladda",
            options=[""] + list(case_options.keys()),
            format_func=lambda x: x if x else "-- Välj case --"
        )
        
        if selected and selected != "":
            selected_case = case_options[selected]
            
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.caption(f"**Skapad:** {selected_case['created'][:19]}")
                st.caption(f"**Resultat:** {'Ja' if selected_case['has_results'] else 'Nej'}")
            
            with col2:
                if st.button("Ladda", key=f"load_{selected_case['filename']}"):
                    case_data = load_case(selected_case['filepath'])
                    if case_data:
                        st.session_state.current_case_name = case_data['case_name']
                        st.session_state.case_definition = case_data['case_definition']
                        if case_data.get('results'):
                            st.session_state.case_results = case_data['results']
                        
                        st.success(f"Case laddat: {case_data['case_name']}")
                        st.rerun()
    
    return None


def render_case_status():
    """Visar status för aktivt case"""
    if not st.session_state.get('current_case_name'):
        st.info("Inget aktivt case. Skapa ett nytt case för att börja.")
        return
    
    case_def = st.session_state.get('case_definition', {})
    
    st.markdown(f"**Aktivt case:** {st.session_state.current_case_name}")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        n_params = len(case_def.get('parameters', {}))
        st.metric("Parameters", n_params)
    
    with col2:
        n_vars = len(case_def.get('variables', {}))
        st.metric("Variables", n_vars)
    
    with col3:
        n_modules = len(case_def.get('modules', {}))
        st.metric("Modules", n_modules)
"""
Case Setup Page - Steg 1
Användaren väljer VAD som ska ändras (Parameters/Variables/Modules)
"""

import streamlit as st
from typing import Dict, Any, List


def render_case_setup_page(case_definition: Dict[str, Any]) -> Dict[str, Any]:
    """
    Renderar case setup-sida där användaren väljer komponenter.
    
    Args:
        case_definition: Nuvarande case definition
        
    Returns:
        Uppdaterad case definition med valda komponenter
    """
    st.title("Case Setup")
    st.markdown("Välj vilka komponenter som ska konfigureras i ditt case")
    
    # Use canonical fields in case_definition: 'parameters', 'variables', 'modules'
    # For the setup page we store lists of selected categories under these keys.
    if 'parameters' not in case_definition:
        case_definition['parameters'] = []
    if 'variables' not in case_definition:
        case_definition['variables'] = []
    if 'modules' not in case_definition:
        case_definition['modules'] = []

    selections_params = case_definition['parameters']
    selections_vars = case_definition['variables']
    selections_mods = case_definition['modules']
    
    st.markdown("---")
    
    st.markdown("## Parameters")
    st.caption("Regulatoriska val som är samma för alla nät")
    
    param_options = {
        'wacc_components': {
            'name': 'WACC-komponenter',
            'description': 'Riskfri ränta, marknadens riskpremie, beta, skuldsättning, m.m.'
        },
        'economic_lifetimes': {
            'name': 'Ekonomiska livslängder',
            'description': 'Livslängd per tillgångskategori'
        },
        'norm_values': {
            'name': 'Normvärden',
            'description': 'Normpriser för tillgångskategorier'
        },
        'truncation': {
            'name': 'Trunkering effektiviseringskrav',
            'description': 'Min/max trunkering och outlier-krav'
        }
    }
    
    for key, info in param_options.items():
        checked = key in selections_params
        if st.checkbox(
            info['name'],
            value=checked,
            key=f"param_{key}",
            help=info['description']
        ):
            if key not in selections_params:
                selections_params.append(key)
        else:
            if key in selections_params:
                selections_params.remove(key)
    
    st.markdown("---")
    
    st.markdown("## Variables")
    st.caption("Värden som varierar mellan olika nät")
    
    var_options = {
        'capex': {
            'name': 'CAPEX',
            'description': 'Kapitalkostnader - kan beräknas på flera sätt'
        },
        'opex': {
            'name': 'OPEX',
            'description': 'Påverkbara och opåverkbara löpande kostnader'
        },
        'volumes': {
            'name': 'Volumes',
            'description': 'CU, MW, NS, MWhl, MWhh'
        },
        'quality': {
            'name': 'Kvalitet',
            'description': 'AIT, AIF, CEMI4'
        }
    }
    
    for key, info in var_options.items():
        checked = key in selections_vars
        if st.checkbox(
            info['name'],
            value=checked,
            key=f"var_{key}",
            help=info['description']
        ):
            if key not in selections_vars:
                selections_vars.append(key)
        else:
            if key in selections_vars:
                selections_vars.remove(key)
    
    st.markdown("---")
    
    st.markdown("## Modules")
    st.caption("Analysmetoder som kan väljas")
    
    module_options = {
        'efficiency': {
            'name': 'Efficiency-analys',
            'description': 'DEA-modell för effektivitetsmätning'
        }
    }
    
    for key, info in module_options.items():
        checked = key in selections_mods
        if st.checkbox(
            info['name'],
            value=checked,
            key=f"module_{key}",
            help=info['description']
        ):
            if key not in selections_mods:
                selections_mods.append(key)
        else:
            if key in selections_mods:
                selections_mods.remove(key)
    
    st.markdown("---")
    
    n_selected = (
        len(selections_params) + 
        len(selections_vars) + 
        len(selections_mods)
    )
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        if n_selected > 0:
            st.success(f"Valt {n_selected} komponenter")
        else:
            st.info("Välj minst en komponent för att fortsätta")
    
    with col2:
        if st.button(
            "Nästa: Konfigurera →",
            type="primary",
            disabled=n_selected == 0,
            use_container_width=True
        ):
            st.session_state.page = 'config'
            st.rerun()

    # Persist lists back to case_definition
    case_definition['parameters'] = selections_params
    case_definition['variables'] = selections_vars
    case_definition['modules'] = selections_mods

    return case_definition
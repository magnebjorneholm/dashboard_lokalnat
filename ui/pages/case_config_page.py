"""
Case Config Page - Steg 2
Användaren konfigurerar de valda komponenterna dynamiskt
"""

import streamlit as st
from typing import Dict, Any


def render_case_config_page(case_definition: Dict[str, Any]) -> Dict[str, Any]:
    """
    Renderar case config-sida där användaren konfigurerar valda komponenter.
    
    Args:
        case_definition: Case definition med selections från setup-steget
        
    Returns:
        Uppdaterad case definition med konfigurerade värden
    """
    st.title("Case Configuration")
    st.markdown("Konfigurera de valda komponenterna")
    
    # Read selected categories from canonical fields created in setup
    # These should be lists of keys from the setup page
    selections_params = case_definition.get('parameters', [])
    selections_vars = case_definition.get('variables', [])
    selections_mods = case_definition.get('modules', [])
    
    # Convert to list if dict (for compatibility)
    if isinstance(selections_params, dict):
        selections_params = list(selections_params.keys())
    if isinstance(selections_vars, dict):
        selections_vars = list(selections_vars.keys())
    if isinstance(selections_mods, dict):
        selections_mods = list(selections_mods.keys())
    
    selections = {
        'parameters': selections_params,
        'variables': selections_vars,
        'modules': selections_mods
    }
    
    # Initialize module_configs if not present
    if 'module_configs' not in case_definition:
        case_definition['module_configs'] = {}

    n_selected = (
        len(selections.get('parameters', [])) +
        len(selections.get('variables', [])) +
        len(selections.get('modules', []))
    )
    
    if n_selected == 0:
        st.warning("Inga komponenter valda. Gå tillbaka till Setup.")
        if st.button("← Tillbaka till Setup"):
            st.session_state.page = 'setup'
            st.rerun()
        return case_definition
    
    # Use CaseDefinitionManager to update canonical case fields
    case_manager = st.session_state.case_manager
    case_def = case_definition
    
    st.markdown("---")
    
    if selections.get('parameters'):
        st.markdown("## Parameters")
        
        for param_key in selections['parameters']:
            if param_key == 'wacc_components':
                st.markdown("### WACC-komponenter")
                
                method = st.radio(
                    "Metod",
                    options=['baseline', 'custom'],
                    format_func=lambda x: {
                        'baseline': 'Använd baseline WACC (4.53%)',
                        'custom': 'Anpassa komponenter'
                    }[x],
                    key=f"config_{param_key}_method"
                )
                
                if method == 'custom':
                    from ui.producer_ui.wacc_ui import render_wacc_ui

                    # Handle case_def['parameters'] being list (from setup) or dict (from config)
                    params = case_def.get('parameters', {})
                    current = params.get('wacc_components', {}) if isinstance(params, dict) else {}
                    wacc_config = render_wacc_ui(current_values=current)
                    case_def = case_manager.update_parameter(case_def, 'wacc_components', wacc_config)
                else:
                    case_def = case_manager.update_parameter(case_def, 'wacc_components', {'method': 'baseline'})
                
                st.markdown("---")
            
            elif param_key == 'truncation':
                st.markdown("### Trunkering effektiviseringskrav")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    trunk_min = st.number_input(
                        "Trunkering min",
                        0.0, 0.5, 0.162416,
                        step=0.001,
                        format="%.6f"
                    )
                
                with col2:
                    trunk_max = st.number_input(
                        "Trunkering max",
                        0.0, 1.0, 0.3,
                        step=0.01,
                        format="%.2f"
                    )
                
                with col3:
                    outlier_krav = st.number_input(
                        "Outlier-krav",
                        0.0, 0.1, 0.01,
                        step=0.001,
                        format="%.3f"
                    )
                
                trunc_cfg = {
                    'trunk_min': trunk_min,
                    'trunk_max': trunk_max,
                    'outlier_krav': outlier_krav
                }
                case_def = case_manager.update_parameter(case_def, 'truncation', trunc_cfg)
                
                st.markdown("---")
    
    if selections.get('variables'):
        st.markdown("## Variables")
        
        for var_key in selections['variables']:
            if var_key == 'capex':
                st.markdown("### CAPEX")
                
                method = st.radio(
                    "Metod",
                    options=['baseline', 'wacc_scaling', 'kent_full', 'kent_upload'],
                    format_func=lambda x: {
                        'baseline': 'Baseline',
                        'wacc_scaling': 'Snabb skalning (WACC-ändring)',
                        'kent_full': 'Full pipeline (justera parametrar)',
                        'kent_upload': 'Ladda upp KENT-fil'
                    }[x],
                    key=f"config_{var_key}_method"
                )
                
                # Persist producer selection for this variable
                try:
                    case_def = case_manager.set_module(case_def, 'capex', method)
                except ValueError:
                    # fallback: keep case_def unchanged
                    pass

                if method == 'wacc_scaling':
                    st.info("WACC-skalning använder WACC-komponenter från Parameters-sektionen")

                elif method == 'kent_upload':
                    from ui.producer_ui.kent_upload_ui import render_kent_upload_ui

                    kent_data = render_kent_upload_ui()
                    if kent_data:
                        case_def = case_manager.set_module_config(case_def, 'capex', {'kent_data': kent_data})
                
                st.markdown("---")
    
    if selections.get('modules'):
        st.markdown("## Modules")
        
        for module_key in selections['modules']:
            if module_key == 'efficiency':
                st.markdown("### Efficiency-analys")
                
                method = st.radio(
                    "Metod",
                    options=['baseline', 'dea'],
                    format_func=lambda x: {
                        'baseline': 'Använd baseline efficiency',
                        'dea': 'Kör DEA-analys'
                    }[x],
                    key=f"config_{module_key}_method"
                )
                
                if method == 'dea':
                    try:
                        from core.data_loader_dea import load_data
                        df = load_data("effektivitet/data/Data_modeller.xlsx")

                        from ui.producer_ui.dea_config_ui import render_dea_config_ui

                        current_cfg = case_def.get('module_configs', {}).get(module_key, {})

                        dea_config = render_dea_config_ui(
                            df,
                            current_config=current_cfg
                        )

                        # select DEA producer and set its config
                        try:
                            case_def = case_manager.set_module(case_def, module_key, 'dea')
                        except ValueError:
                            pass

                        case_def = case_manager.set_module_config(case_def, module_key, dea_config)
                    except Exception as e:
                        st.error(f"Kunde inte ladda DEA-data: {e}")
                        try:
                            case_def = case_manager.set_module(case_def, module_key, 'baseline')
                        except ValueError:
                            pass
                else:
                    try:
                        case_def = case_manager.set_module(case_def, module_key, 'baseline')
                    except ValueError:
                        pass
                
                st.markdown("---")
    
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        if st.button("← Tillbaka", use_container_width=True):
            st.session_state.case_definition = case_def
            st.session_state.page = 'setup'
            st.rerun()
    
    with col3:
        if st.button(
            "Kör beräkning →",
            type="primary",
            use_container_width=True
        ):
            st.session_state.case_definition = case_def
            st.session_state.page = 'execution'
            st.rerun()
    
    
    # Persist changes and return updated case definition
    st.session_state.case_definition = case_def
    return case_def
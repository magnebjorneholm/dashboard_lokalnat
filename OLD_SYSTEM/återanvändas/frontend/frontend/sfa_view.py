"""
effektivitet/frontend/sfa_view.py
Huvudvy för SFA-analys (Stochastic Frontier Analysis).
"""

import streamlit as st
import pandas as pd
from datetime import datetime

from effektivitet.backend.sfa_model import (
    run_sfa_model,
    get_sfa_summary_stats,
    extract_beta_coefficients
)
from effektivitet.backend.sfa_export import export_sfa_results_to_ir
from effektivitet.frontend.sfa_components import (
    display_sfa_parameters,
    display_sfa_results_summary,
    display_sfa_parameters_table,
    display_sfa_results_table,
    display_sfa_efficiency_distributions
)
from core.data_loader_dea import merge_capex_scenario, load_data
from core.data_loader_company import get_user_dmu, load_reconciliation_foretag_info
from core.data_loader_base import get_company_display_name


# Autentisering
if "access_granted" not in st.session_state or not st.session_state.access_granted:
    st.stop()

if st.session_state.user_role != "company":
    st.error("Denna sida är endast tillgänglig för företagsanvändare")
    st.stop()


def show_foretag_sfa():
    """Huvudfunktion för SFA-analys"""
    
    user_dmu = get_user_dmu()
    company_info = load_reconciliation_foretag_info()
    
    if user_dmu is None:
        st.error("Ingen DMU hittades för inloggad användare")
        return
    
    company_name = company_info.get('company_name', 'Ditt företag')
    company_display = get_company_display_name(user_dmu, company_name)
    
    # Ladda data
    try:
        data_file = "effektivitet/data/Data_modeller.xlsx"
        df_full = load_data(data_file)
    except Exception as e:
        st.error(f"Kunde inte ladda data: {e}")
        return
    
    if user_dmu not in df_full['DMU'].values:
        st.error(f"DMU {user_dmu} hittades inte i data")
        st.info("Detta kan betyda att ditt företag inte ingår i analysen")
        return
    
    st.title(f"SFA-analys - {company_display}")
    st.markdown("Stochastic Frontier Analysis (SFA) - Parametrisk effektivitetsskattning med separation av ineffektivitet och random noise")
    
    st.markdown("---")
    
    # Merge CAPEX-scenario
    df, scen_info = merge_capex_scenario(df_full)
    
    # Visa parametrar och få användarens val
    params = display_sfa_parameters(df, scen_info)
    
    if params is None:
        return
    
    # Session state key för denna användare
    session_key = f'sfa_runs_{user_dmu}'
    if session_key not in st.session_state:
        st.session_state[session_key] = []
    
    # Kör SFA-analys
    with st.spinner("Kör SFA-skattning..."):
        try:
            result = run_sfa_model(df, **params)
            
            # Spara resultat i session state
            st.session_state[f'latest_sfa_result_{user_dmu}'] = {
                'result': result,
                'sfa_data': df,
                'params': params,
                'scenario_info': scen_info,
                'timestamp': datetime.now().isoformat()
            }
            
            st.success("SFA-analys slutförd")
            
        except Exception as e:
            st.error(f"SFA-analys misslyckades: {e}")
            import traceback
            st.error(traceback.format_exc())
            return
    
    # Visa resultat
    latest_key = f'latest_sfa_result_{user_dmu}'
    if latest_key in st.session_state:
        st.markdown("---")
        show_sfa_results(st.session_state[latest_key], user_dmu, company_display)


def show_sfa_results(latest_result: dict, user_dmu: int, company_name: str):
    """Visar SFA-resultat med alla visualiseringar och export-möjligheter"""
    
    result = latest_result['result']
    params = latest_result['params']
    
    # Beräkna sammanfattande statistik
    stats = get_sfa_summary_stats(result)
    beta_df = extract_beta_coefficients(result)
    
    # Resultatsammanfattning
    display_sfa_results_summary(result, stats)
    
    st.markdown("---")
    
    # Parameterskattningar
    display_sfa_parameters_table(stats, beta_df)
    
    st.markdown("---")
    
    # Fördelningar
    display_sfa_efficiency_distributions(result)
    
    st.markdown("---")
    
    # Resultat-tabell
    st.subheader("Detaljerade resultat")
    display_sfa_results_table(result)
    
    st.markdown("---")
    
    # Export till Intäktsram
    st.subheader("Export till Intäktsram")
    st.markdown("Exportera SFA-resultat för användning i intäktsram-dekomposition")
    
    col_exp1, col_exp2, col_exp3 = st.columns([2, 1, 1])
    
    with col_exp1:
        st.caption(
            f"**Modellspecifikation:** {params['fun'].upper()} | "
            f"Output: {params['output_col']} | "
            f"Inputs: {', '.join(params['input_cols'])} | "
            f"Metod: {params['method']}"
        )
    
    with col_exp2:
        if st.button("Exportera till IR", type="primary", use_container_width=True):
            try:
                data_path, meta_path = export_sfa_results_to_ir(result)
                st.success(f"Exporterat! Gå till Intäktsram-tabben för att importera.")
                
                with st.expander("Export-detaljer"):
                    st.code(f"Data: {data_path}")
                    st.code(f"Metadata: {meta_path}")
                    
            except Exception as e:
                st.error(f"Export misslyckades: {e}")
    
    with col_exp3:
        if st.button("Till Intäktsram", use_container_width=True):
            st.session_state['ir_context'] = {
                'from_page': 'sfa',
                'dmu': user_dmu,
                'fokus': 'effektiviseringskrav'
            }
            st.switch_page("pages/foretag/foretag_intaktsram_ny.py")
    
    # Info om SFA
    st.markdown("---")
    with st.expander("Om SFA-metoden"):
        st.markdown("""
        **Stochastic Frontier Analysis (SFA)** är en parametrisk metod för effektivitetsskattning.
        
        **Fördelar jämfört med DEA:**
        - Separerar ineffektivitet från random noise (mätfel, slumpmässiga variationer)
        - Ger statistisk inferens (standardfel, signifikans)
        - Robust mot outliers och mätfel
        
        **Nackdelar jämfört med DEA:**
        - Kräver antagande om funktionell form (Cobb-Douglas i detta fall)
        - Stödjer endast en output-variabel
        - Mindre flexibel än DEA
        
        **Parametrar:**
        - **λ (lambda):** Kvot mellan σᵤ och σᵥ. Högt värde → ineffektivitet dominerar över noise
        - **σᵤ²:** Varians från ineffektivitet
        - **σᵥ²:** Varians från random noise
        - **β-koefficienter:** Elasticiteter för inputs
        
        **Tolkningsexempel:**
        - Om λ = 3.5 och σᵤ²/σ² = 93%, betyder det att 93% av variansen beror på ineffektivitet
        - β_CAPEX = 0.55 betyder att 1% ökning i CAPEX associeras med 0.55% ökning i output
        """)


if __name__ == "__main__":
    show_foretag_sfa()
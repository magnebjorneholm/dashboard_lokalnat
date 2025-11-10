"""
Översikt-tab med ALL scenario-hantering (ingen sidebar längre)
"""

import streamlit as st
import pandas as pd
import io
from datetime import datetime
from pathlib import Path

from intaktsram.backend.scenario_utils import (
    create_scenario,
    reset_to_baseline,
    list_saved_scenarios,
    load_scenario_from_file,
    save_scenario_to_file
)


def show_oversikt_tab(entity_data: pd.Series, df_company: pd.DataFrame):
    """
    Visar översikt-tab med scenario-hantering och sammanfattning.
    
    Args:
        entity_data: Series med data för vald entitet (lokalnät)
        df_company: DataFrame med alla lokalnät för företaget
    """
    
    st.subheader("Översikt & Scenario-hantering")
    
    # SCENARIO-HANTERING
    show_scenario_management(df_company)
    
    st.markdown("---")
    st.markdown("---")
    
    # Hämta scenario-data
    scenario_data = st.session_state.get('scenario_data', {})
    # Försök läsa nyckeln 'applied_modifications' först, fallback till legacy 'modifications'
    modifications = scenario_data.get('applied_modifications') or scenario_data.get('modifications', {})
    has_active_scenario = bool(st.session_state.get('current_scenario_name'))
    
    # SCENARIO-STATUS
    if has_active_scenario:
        show_scenario_status(modifications)
    else:
        st.info("Inget aktivt scenario. Skapa ett nytt scenario för att börja analysera.")
    
    st.markdown("---")
    
    # EXPORT-FUNKTIONALITET
    show_export_section(entity_data, modifications)


def show_scenario_management(df_company: pd.DataFrame):
    """
    Visar komplett scenario-hantering (flytt från sidebar).
    """
    
    st.markdown("### Scenario-hantering")
    st.caption("Skapa, ladda eller spara scenarier för att analysera olika parameterval")
    
    # Scenario-namn input
    scenario_name = st.text_input(
        "Scenario-namn",
        value=st.session_state.current_scenario_name,
        placeholder="t.ex. WACC 4.75%",
        key="scenario_name_input"
    )
    
    # Knappar för scenario-hantering
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("Skapa nytt scenario", use_container_width=True, type="primary"):
            if create_scenario(scenario_name, df_company):
                st.success(f"Scenario '{scenario_name}' skapat!")
                st.rerun()
            else:
                st.error("Kunde inte skapa scenario")
    
    with col2:
        if st.button(
            "Ladda sparat scenario", 
            use_container_width=True,
            disabled=not list_saved_scenarios()
        ):
            st.session_state.show_scenario_loader = not st.session_state.get('show_scenario_loader', False)
            st.rerun()
    
    with col3:
        if st.button(
            "Spara scenario",
            use_container_width=True,
            disabled=not st.session_state.current_scenario_name
        ):
            if st.session_state.current_scenario_name:
                from intaktsram.frontend.intaktsram_dekomposition import get_working_dataframe
                df_to_save = get_working_dataframe(df_company)
                filepath = save_scenario_to_file(st.session_state.current_scenario_name, df_to_save)
                st.success("Scenario sparat!")
    
    with col4:
        if st.button(
            "Återställ till baseline",
            use_container_width=True,
            disabled=not st.session_state.current_scenario_name
        ):
            reset_to_baseline()
            st.success("Återställt till baseline")
            st.rerun()
    
    # Scenario-loader (expandable)
    if st.session_state.get('show_scenario_loader', False):
        show_scenario_loader_section()
    
    # Aktivt scenario-status
    if st.session_state.current_scenario_name:
        st.info(f"**Aktivt scenario:** {st.session_state.current_scenario_name}")


def show_scenario_loader_section():
    """
    Visar scenario-loader med lista av sparade scenarier.
    """
    st.markdown("---")
    
    with st.expander("Välj scenario att ladda", expanded=True):
        saved_scenarios = list_saved_scenarios()
        
        if not saved_scenarios:
            st.info("Inga sparade scenarier hittades")
            return
        
        scenario_names = [s[0] for s in saved_scenarios]
        
        selected_name = st.selectbox(
            "Sparade scenarier",
            options=scenario_names,
            key="scenario_selector"
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Ladda scenario", use_container_width=True, type="primary"):
                selected_path = next(s[1] for s in saved_scenarios if s[0] == selected_name)
                df_loaded, metadata = load_scenario_from_file(selected_path)
                
                st.session_state.current_scenario_name = selected_name
                # Läs in applied_modifications om det finns i metadata, annars fallback till legacy
                st.session_state.scenario_data = {
                    'baseline': df_loaded,
                    'applied_modifications': metadata.get('applied_modifications', metadata.get('modifications', {})),
                    'created': metadata.get('created'),
                    'component_sources': metadata.get('component_sources', {})
                }
                st.session_state.show_scenario_loader = False
                st.success(f"Scenario '{selected_name}' laddat!")
                st.rerun()
        
        with col2:
            if st.button("Avbryt", use_container_width=True):
                st.session_state.show_scenario_loader = False
                st.rerun()


def show_scenario_status(modifications: dict):
    """
    Visar status för aktivt scenario med modifieringsinformation.
    """
    st.markdown("### Scenario-status")
    
    modified_components = []
    
    # Kapitalkostnad
    if 'kapitalkostnad' in modifications:
        kapital_mod = modifications['kapitalkostnad']
        source = kapital_mod.get('source', 'manuell')
        
        if source == 'wacc_scaling':
            metadata = kapital_mod.get('metadata', {})
            wacc_new = metadata.get('wacc_new', 0) * 100
            wacc_old = metadata.get('wacc_old', 4.53)
            modified_components.append(
                f"**Kapitalkostnad:** WACC-skalning ({wacc_old:.2f}% → {wacc_new:.2f}%)"
            )
        
        elif source == 'kent_pipeline':
            metadata = kapital_mod.get('metadata', {})
            wacc_new = metadata.get('wacc_new', 0) * 100
            info_parts = [f"WACC: {wacc_new:.2f}%"]
            
            param_adj = metadata.get('parameter_adjustments', {})
            if param_adj.get('has_normvalue_adjustments'):
                norm_info = param_adj.get('normvalue_adjustments', {})
                count = norm_info.get('count', 0)
                info_parts.append(f"Normvärden: {count} ändr.")
            
            if param_adj.get('has_lifetime_adjustments'):
                life_info = param_adj.get('lifetime_adjustments', {})
                count = life_info.get('count', 0)
                info_parts.append(f"Livslängder: {count} ändr.")
            
            modified_components.append(
                f"**Kapitalkostnad:** KENT-beräkning ({', '.join(info_parts)})"
            )
    
    # Effektiviseringskrav
    if 'paverkbara' in modifications:
        effkrav_mod = modifications['paverkbara']
        method = effkrav_mod.get('method', 'OPEX')
        dea_result = effkrav_mod.get('dea_result')
        
        if dea_result is not None and not dea_result.empty:
            effkrav_pct = dea_result.iloc[0].get('Effkrav_proc', 0) * 100
            modified_components.append(
                f"**Effektiviseringskrav:** {effkrav_pct:.2f}% (metod: {method})"
            )
        else:
            modified_components.append(
                f"**Effektiviseringskrav:** Aktiv (metod: {method})"
            )
    
    # Visa modifieringar
    if modified_components:
        for comp in modified_components:
            st.markdown(f"- {comp}")
    else:
        st.info("Inga modifieringar i scenario ännu. Använd Kapitalkostnad- och Effektiviseringskrav-tabs.")


# FUNKTION INAKTIVERAD - Fokuserar på diagram istället
# def show_combined_component_table(entity_data: pd.Series, modifications: dict):
#     """
#     Visar kombinerad tabell med alla komponenter och jämförelse baseline vs scenario.
#     """
#     pass


# FUNKTION INAKTIVERAD - Fokuserar på diagram istället
# def show_yearly_paverkbara_table(entity_data: pd.Series, modifications: dict):
#     """
#     Visar tabell med årsvisa påverkbara kostnader.
#     """
#     pass


def show_export_section(entity_data: pd.Series, modifications: dict):
    """
    Visar export-funktionalitet.
    """
    st.markdown("### Export")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Exportera till Excel", use_container_width=True):
            try:
                excel_data = create_excel_export(entity_data, modifications)
                st.download_button(
                    label="Ladda ner Excel-fil",
                    data=excel_data,
                    file_name=f"intaktsram_scenario_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"Export misslyckades: {e}")
    
    with col2:
        st.button("Skapa rapport (PDF)", use_container_width=True, disabled=True)
        st.caption("PDF-rapport implementeras i nästa fas")


def create_excel_export(entity_data: pd.Series, modifications: dict) -> bytes:
    """
    Skapar Excel-export av scenario.
    """
    output = io.BytesIO()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Översikt
        overview_data = pd.DataFrame({
            'Komponent': ['Påverkbara kostnader', 'Opåverkbara kostnader', 'Kapitalkostnad', 'Total intäktsram'],
            'Scenario (tkr)': [
                entity_data.get('Paverkbara_Kostnader', 0),
                entity_data.get('Opaverkbara_Kostnader', 0),
                entity_data.get('Kapitalkostnad_Total', 0),
                entity_data.get('Intaktsram_Total', 0)
            ],
            'Baseline (tkr)': [
                entity_data.get('Paverkbara_Kostnader_Baseline', 0),
                entity_data.get('Opaverkbara_Kostnader_Baseline', 0),
                entity_data.get('Kapitalkostnad_Total_Baseline', 0),
                entity_data.get('Intaktsram_Total_Baseline', 0)
            ]
        })
        overview_data.to_excel(writer, sheet_name='Översikt', index=False)
    
    output.seek(0)
    return output.getvalue()
"""
Översikt-tab med kvalitativ scenario-status och jämförelsetabell
Uppdaterad för att använda applied_modifications från pending_changes_manager
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
    
    # Hämta scenario-data
    scenario_data = st.session_state.get('scenario_data', {})
    applied_modifications = scenario_data.get('applied_modifications', {})
    has_active_scenario = bool(st.session_state.get('current_scenario_name'))
    
    # SCENARIO-STATUS (Kvalitativ metadata)
    if has_active_scenario:
        show_scenario_status(applied_modifications)
    else:
        st.info("Inget aktivt scenario. Skapa ett nytt scenario för att börja analysera.")
    
    st.markdown("---")
    
    # HUVUDKOMPONENTER-TABELL
    show_combined_component_table(entity_data, applied_modifications)
    
    st.markdown("---")
    
    # EXPORT-FUNKTIONALITET
    show_export_section(entity_data, applied_modifications)


def show_scenario_management(df_company: pd.DataFrame):
    """
    Visar komplett scenario-hantering
    """
    st.caption("Skapa, ladda eller spara scenarier för att analysera olika parameterval")
    
    scenario_name = st.text_input(
        "Namn",
        value=st.session_state.current_scenario_name,
        placeholder="t.ex. WACC 4.75%",
        key="scenario_name_input"
    )
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("Skapa nytt scenario", use_container_width=True, type="primary"):
            if create_scenario(scenario_name, df_company):
                st.success(f"Scenario '{scenario_name}' skapat!")
                st.rerun()
    
    with col2:
        if st.button("Återställ till baseline", use_container_width=True):
            if reset_to_baseline(df_company):
                st.success("Återställt till baseline!")
                st.rerun()
    
    with col3:
        if st.button("Ladda scenario", use_container_width=True):
            st.session_state.show_scenario_loader = True
            st.rerun()
    
    with col4:
        if st.session_state.current_scenario_name and st.button("Spara scenario", use_container_width=True):
            try:
                filepath = save_scenario_to_file(
                    st.session_state.current_scenario_name,
                    st.session_state.scenario_data
                )
                st.success(f"Scenario sparat: {filepath}")
            except Exception as e:
                st.error(f"Kunde inte spara: {e}")
    
    # Scenario loader
    if st.session_state.get('show_scenario_loader', False):
        show_scenario_loader()


def show_scenario_loader():
    """
    Visar scenario loader UI
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


def show_scenario_status(applied_modifications: dict):
    """
    Visar KVALITATIV scenario-status med antaganden och metodval.
    Fokuserar på VAD som gjordes, inte resultaten.
    """
    st.markdown("### Antaganden och metodval i aktivt scenario")
    
    has_modifications = False
    
    # KAPITALKOSTNAD
    if 'kapitalkostnad' in applied_modifications:
        has_modifications = True
        kapital_mod = applied_modifications['kapitalkostnad']
        show_kapitalkostnad_status(kapital_mod)
        st.markdown("")
    
    # EFFEKTIVISERINGSKRAV
    if 'paverkbara' in applied_modifications:
        has_modifications = True
        effkrav_mod = applied_modifications['paverkbara']
        show_effektiviseringskrav_status(effkrav_mod)
        st.markdown("")
    
    if not has_modifications:
        st.info("Inga modifieringar applicerade ännu. Gå till Kapitalkostnad eller Effektiviseringskrav för att skapa ett scenario.")


def show_kapitalkostnad_status(kapital_mod: dict):
    """
    Visar kvalitativ status för kapitalkostnad-scenario
    """
    source = kapital_mod.get('source', 'okänd')
    metadata = kapital_mod.get('metadata', {})
    
    st.markdown("#### Kapitalkostnad")
    
    # Grundläggande info
    wacc_new = metadata.get('wacc_new', 0) * 100
    wacc_old = metadata.get('wacc_old', 4.53) * 100
    
    if source == 'wacc_scaling':
        st.markdown(f"""
**Metod:** WACC-skalning från CAPM-komponenter  
**WACC:** {wacc_old:.2f}% → {wacc_new:.2f}% (Δ {wacc_new - wacc_old:+.2f}pp)  
**Tillämpning:** Avkastning skalas proportionellt, avskrivningar oförändrade
        """)
    
    elif source == 'kent_full':
        st.markdown(f"""
**Metod:** Full KENT-pipeline med omberäkning från kapitalbas  
**WACC:** {wacc_new:.2f}% (från CAPM-komponenter)  
**Beräkning:** Fullständig omräkning av avskrivningar och avkastning per period
        """)
        
        # Parameterjusteringar (om de finns)
        param_adj = metadata.get('parameter_adjustments', {})
        
        if param_adj.get('has_normvalue_adjustments') or param_adj.get('has_lifetime_adjustments'):
            st.markdown("**Parameterjusteringar:**")
            
            if param_adj.get('has_normvalue_adjustments'):
                norm_info = param_adj.get('normvalue_adjustments', {})
                count = norm_info.get('count', 0)
                level = norm_info.get('level', 'cat')
                level_text = "subkategorinivå" if level == 'subcat' else "kategorinivå"
                st.markdown(f"• Normvärden: {count} ändringar på {level_text}")
            
            if param_adj.get('has_lifetime_adjustments'):
                life_info = param_adj.get('lifetime_adjustments', {})
                count = life_info.get('count', 0)
                level = life_info.get('level', 'cat')
                level_text = "subkategorinivå" if level == 'subcat' else "kategorinivå"
                st.markdown(f"• Livslängder: {count} ändringar på {level_text}")
    
    else:
        st.markdown(f"**Metod:** {source}")
        st.markdown(f"**WACC:** {wacc_new:.2f}%")


def show_effektiviseringskrav_status(effkrav_mod: dict):
    """
    Visar kvalitativ status för effektiviseringskrav-scenario
    """
    method = effkrav_mod.get('method', 'OPEX')
    metadata = effkrav_mod.get('metadata', {})
    dea_result = effkrav_mod.get('dea_result')
    
    st.markdown("#### Effektiviseringskrav")
    
    # Effektivitetskälla
    efficiency_source = metadata.get('efficiency_source', 'unknown')
    if efficiency_source == 'reference':
        source_text = "Ei:s referens-DEA (2024)"
    elif efficiency_source == 'new_dea':
        source_text = "Egen DEA-analys"
    else:
        source_text = "Okänd källa"
    
    # Årligt effektiviseringskrav
    effkrav_proc = 0.0
    if dea_result is not None and not dea_result.empty:
        effkrav_proc = dea_result.iloc[0].get('Effkrav_proc', 0) * 100
    
    st.markdown(f"""
**Metod:** DEA {method}-metod  
**Effektivitetskälla:** {source_text}  
**Årligt effektiviseringskrav:** {effkrav_proc:.2f}% per år  
**Applicering:** {"Endast påverkbara kostnader (OPEX)" if method == 'OPEX' else "Påverkbara + kapitalkostnad (TOTEX)"}
    """)
    
    # Beräkningsparametrar
    trunk_min = metadata.get('trunk_min', 0.162416) * 100
    trunk_max = metadata.get('trunk_max', 0.3) * 100
    outlier_krav = metadata.get('outlier_krav', 0.01) * 100
    
    st.markdown(f"""
**Beräkningsparametrar:**  
• Trunkering: {trunk_min:.1f}%–{trunk_max:.1f}%  
• Outlier-krav: {outlier_krav:.1f}% per år
    """)
    
    # DEA-parametrar (om ny DEA körts)
    if efficiency_source == 'new_dea' and metadata.get('dea_params'):
        dea_params = metadata['dea_params']
        input_cols = ', '.join(dea_params.get('input_cols', []))
        output_cols = ', '.join(dea_params.get('output_cols', []))
        rts = dea_params.get('rts', 'crs').upper()
        
        st.markdown(f"""
**DEA-specifikation:**  
• Input: {input_cols}  
• Output: {output_cols}  
• Skalavkastning: {rts}
        """)
        
        if dea_params.get('outlier_filter'):
            q_lower = dea_params.get('q_lower', 25)
            q_upper = dea_params.get('q_upper', 75)
            multiplier = dea_params.get('multiplier', 2.0)
            st.markdown(f"• Outlier-filter: Aktiverad (IQR×{multiplier}, Q{q_lower}–Q{q_upper})")


def show_combined_component_table(entity_data: pd.Series, applied_modifications: dict):
    """
    Visar kombinerad tabell med komponenter och jämförelse baseline vs scenario.
    """
    st.markdown("### Komponenter (4-årssumma 2024-2027)")
    
    # Hämta baseline
    baseline_df = st.session_state.scenario_data.get('baseline') if 'scenario_data' in st.session_state else None
    baseline_row = None
    
    if baseline_df is not None and not baseline_df.empty:
        baseline_match = baseline_df[baseline_df['REId'] == entity_data['REId']]
        if not baseline_match.empty:
            baseline_row = baseline_match.iloc[0]
    
    # Komponenter att visa (exkl total - den beräknas sist)
    components = [
        ('Påverkbara kostnader', 'Paverkbara_Kostnader'),
        ('Opåverkbara kostnader', 'Opaverkbara_Kostnader'),
        ('Kapitalkostnad', 'Kapitalkostnad_Total'),
        ('  - varav kapitalförslitning', 'Avskrivningar'),
        ('  - varav kapitalbindning', 'Avkastning'),
        ('Flexibilitetstjänster', 'Flexibilitetstjanster'),
        ('Avbrottsersättning 12-24h', 'Avbrottsersattning_12_24h')
    ]
    
    table_data = []
    total_scenario = 0
    total_baseline = 0
    
    for name, col in components:
        current_val = entity_data.get(col, 0) or 0
        
        if baseline_row is not None:
            ref_val = baseline_row.get(col, 0) or 0
        else:
            ref_val = current_val
        
        diff = current_val - ref_val
        diff_pct = (diff / ref_val * 100) if ref_val > 0 else 0
        
        # Källa med detaljerad information
        source = get_detailed_source(name, col, entity_data, applied_modifications)
        
        table_data.append({
            'Komponent': name,
            'Scenario (MSEK)': f"{current_val/1000:,.1f}".replace(",", " "),
            'Baseline (MSEK)': f"{ref_val/1000:,.1f}".replace(",", " "),
            'Δ (MSEK)': f"{diff/1000:+,.1f}".replace(",", " ") if abs(diff) > 0.5 else "—",
            'Δ (%)': f"{diff_pct:+.1f}%" if abs(diff) > 0.5 else "—",
            'Källa': source
        })
        
        # Summera endast huvudkomponenter (inte delkomponenter som Avskrivningar/Avkastning)
        if not name.startswith('  '):
            total_scenario += current_val
            total_baseline += ref_val
    
    # Lägg till Total intäktsram som beräknad summa
    total_diff = total_scenario - total_baseline
    total_diff_pct = (total_diff / total_baseline * 100) if total_baseline > 0 else 0
    
    table_data.append({
        'Komponent': '**Total intäktsram**',
        'Scenario (MSEK)': f"{total_scenario/1000:,.1f}".replace(",", " "),
        'Baseline (MSEK)': f"{total_baseline/1000:,.1f}".replace(",", " "),
        'Δ (MSEK)': f"{total_diff/1000:+,.1f}".replace(",", " ") if abs(total_diff) > 0.5 else "—",
        'Δ (%)': f"{total_diff_pct:+.1f}%" if abs(total_diff) > 0.5 else "—",
        'Källa': 'Beräknad summa'
    })
    
    df_table = pd.DataFrame(table_data)
    st.dataframe(df_table, use_container_width=True, hide_index=True)


def get_detailed_source(component_name: str, col: str, entity_data: pd.Series, applied_modifications: dict) -> str:
    """
    Returnerar detaljerad källinformation för varje komponent.
    """
    # Påverkbara kostnader
    if col == 'Paverkbara_Kostnader':
        if entity_data.get('Uppdaterad_Paverkbara', False):
            effkrav_mod = applied_modifications.get('paverkbara', {})
            if effkrav_mod.get('source') == 'effektiviseringskrav':
                method = effkrav_mod.get('method', 'OPEX')
                dea_result = effkrav_mod.get('dea_result')
                if dea_result is not None and not dea_result.empty:
                    effkrav_pct = dea_result.iloc[0].get('Effkrav_proc', 0) * 100
                    return f"Eff.krav {effkrav_pct:.2f}%/år på {method}"
                return f"Eff.krav ({method})"
        return "Baseline"
    
    # Kapitalkostnad-komponenter
    if col in ['Kapitalkostnad_Total', 'Avskrivningar', 'Avkastning']:
        if entity_data.get('Uppdaterad_Kapitalkostnad', False):
            kapital_mod = applied_modifications.get('kapitalkostnad', {})
            source = kapital_mod.get('source', 'Scenario')
            metadata = kapital_mod.get('metadata', {})
            wacc = metadata.get('wacc_new')
            
            if wacc:
                wacc_pct = wacc * 100
                if source == 'wacc_scaling':
                    return f"WACC {wacc_pct:.2f}%"
                elif source == 'kent_full':
                    return f"KENT (WACC {wacc_pct:.2f}%)"
            return "Scenario"
        return "Baseline"
    
    # Övriga komponenter
    if entity_data.get(f'Uppdaterad_{col}', False):
        return "Modifierad"
    
    return "Baseline"


def show_export_section(entity_data: pd.Series, applied_modifications: dict):
    """
    Visar export-funktionalitet
    """
    st.markdown("### Exportera scenario")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Exportera till Excel", use_container_width=True):
            try:
                excel_data = create_excel_export(entity_data, applied_modifications)
                st.download_button(
                    label="Ladda ner Excel-fil",
                    data=excel_data,
                    file_name=f"intaktsram_scenario_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"Export misslyckades: {e}")
    
    with col2:
        if st.button("Skapa rapport (PDF)", use_container_width=True, disabled=True):
            st.info("PDF-rapport implementeras i nästa fas")


def create_excel_export(entity_data: pd.Series, applied_modifications: dict) -> bytes:
    """
    Skapar Excel-export av scenario
    """
    output = io.BytesIO()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Översikt-sheet
        overview_data = {
            'Komponent': [],
            'Scenario (tkr)': [],
            'Baseline (tkr)': [],
            'Förändring (tkr)': [],
            'Förändring (%)': []
        }
        
        components = [
            ('Påverkbara kostnader', 'Paverkbara_Kostnader'),
            ('Opåverkbara kostnader', 'Opaverkbara_Kostnader'),
            ('Kapitalkostnad', 'Kapitalkostnad_Total'),
            ('Flexibilitetstjänster', 'Flexibilitetstjanster'),
            ('Avbrottsersättning', 'Avbrottsersattning_12_24h'),
            ('Total intäktsram', 'Intaktsram_Total')
        ]
        
        for name, key in components:
            value = entity_data.get(key, 0)
            baseline = entity_data.get(f'{key}_Baseline', value)
            delta = value - baseline
            delta_pct = (delta / baseline * 100) if baseline != 0 else 0
            
            overview_data['Komponent'].append(name)
            overview_data['Scenario (tkr)'].append(value)
            overview_data['Baseline (tkr)'].append(baseline)
            overview_data['Förändring (tkr)'].append(delta)
            overview_data['Förändring (%)'].append(delta_pct)
        
        df_overview = pd.DataFrame(overview_data)
        df_overview.to_excel(writer, sheet_name='Översikt', index=False)
        
        # Metadata-sheet
        metadata = {
            'Parameter': ['Namn', 'Exportdatum', 'Företag', 'DMU', 'REId'],
            'Värde': [
                st.session_state.get('current_scenario_name', 'Namnlöst'),
                datetime.now().strftime('%Y-%m-%d %H:%M'),
                entity_data.get('Företag', 'N/A'),
                entity_data.get('DMU', 'N/A'),
                entity_data.get('REId', 'N/A')
            ]
        }
        df_metadata = pd.DataFrame(metadata)
        df_metadata.to_excel(writer, sheet_name='Metadata', index=False)
    
    output.seek(0)
    return output.read()
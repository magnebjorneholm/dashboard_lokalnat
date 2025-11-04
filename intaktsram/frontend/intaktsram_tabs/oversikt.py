"""
foretag/view/intaktsram_tabs/oversikt.py
Översikt-tab med utökad modifieringsinformation
"""

import streamlit as st
import pandas as pd
import io
from datetime import datetime


def show_oversikt_tab(entity_data: pd.Series):
    """
    Visar översikt-tab med sammanfattning och komponenter.
    
    Args:
        entity_data: Series med data för vald entitet (lokalnät)
    """
    
    st.subheader("Översikt")
    
    # Hämta scenario-data
    scenario_data = st.session_state.get('scenario_data', {})
    modifications = scenario_data.get('modifications', {})
    has_active_scenario = bool(st.session_state.get('current_scenario_name'))
    
    # SCENARIO-STATUSRUTA
    if has_active_scenario:
        show_scenario_status(modifications)
        st.markdown("---")
    
    # KOMBINERAD KOMPONENTTABELL MED JÄMFÖRELSE
    show_combined_component_table(entity_data, modifications)
    
    st.markdown("---")
    
    # ÅRSVISA PÅVERKBARA KOSTNADER
    show_yearly_paverkbara_table(entity_data, modifications)
    
    st.markdown("---")
    
    # KAPITALKOSTNADER PER PERIOD
    show_yearly_kapitalkostnad_placeholder()
    
    # EXPORT-FUNKTIONALITET
    st.markdown("---")
    show_export_section(entity_data, modifications)


def show_scenario_status(modifications: dict):
    """
    Visar status för aktivt scenario med utökad modifieringsinformation
    """
    scenario_name = st.session_state.get('current_scenario_name', 'Namnlöst scenario')
    
    st.info(f"**Aktivt scenario:** {scenario_name}")
    
    # Lista modifierade komponenter med detaljerad info
    modified_components = []
    
    if 'kapitalkostnad' in modifications:
        kapital_mod = modifications['kapitalkostnad']
        source = kapital_mod.get('source', 'manuell')
        
        if source == 'kapitalbas':
            metadata = kapital_mod.get('metadata', {})
            
            # Bygga kapitalkostnad-info
            info_parts = []
            
            # WACC
            wacc = metadata.get('wacc_new')
            if wacc:
                wacc_old = metadata.get('wacc_old', 0.0453)
                info_parts.append(f"WACC: {wacc_old*100:.2f}% → {wacc*100:.2f}%")
            
            # Parameterjusteringar
            param_adj = metadata.get('parameter_adjustments', {})
            
            if param_adj.get('has_normvalue_adjustments'):
                norm_info = param_adj.get('normvalue_adjustments', {})
                count = norm_info.get('count', 0)
                level = norm_info.get('level', 'kategori')
                level_text = 'subkat' if level == 'subcat' else 'kat'
                info_parts.append(f"Normvärden: {count} ändr. ({level_text})")
            
            if param_adj.get('has_lifetime_adjustments'):
                life_info = param_adj.get('lifetime_adjustments', {})
                count = life_info.get('count', 0)
                level = life_info.get('level', 'kategori')
                level_text = 'subkat' if level == 'subcat' else 'kat'
                info_parts.append(f"Livslängder: {count} ändr. ({level_text})")
            
            if info_parts:
                modified_components.append(f"• Kapitalkostnad: {', '.join(info_parts)}")
            else:
                modified_components.append(f"• Kapitalkostnad")
        else:
            modified_components.append(f"• Kapitalkostnad ({source})")
    
    if 'paverkbara' in modifications:
        effkrav_mod = modifications['paverkbara']
        if effkrav_mod.get('source') == 'effektiviseringskrav':
            method = effkrav_mod.get('method', 'OPEX')
            dea_result = effkrav_mod.get('dea_result')
            if dea_result is not None and not dea_result.empty:
                effkrav_pct = dea_result.iloc[0].get('Effkrav_proc', 0) * 100
                modified_components.append(f"• Påverkbara kostnader: DEA {method}-metod, -{effkrav_pct:.2f}%")
            else:
                modified_components.append(f"• Påverkbara kostnader: DEA {method}-metod")
    
    if modified_components:
        st.write("**Modifieringar:**")
        for comp in modified_components:
            st.caption(comp)
    else:
        st.caption("Inga modifieringar applicerade än")


def show_combined_component_table(entity_data: pd.Series, modifications: dict):
    """
    Visar kombinerad tabell med komponenter och jämförelse.
    Inkluderar specifik modifieringsinformation.
    """
    st.write("**Komponenter (4-årssumma 2024-2027):**")
    
    # Hämta baseline-värden
    baseline_df = st.session_state.scenario_data.get('baseline') if 'scenario_data' in st.session_state else None
    baseline_row = None
    
    if baseline_df is not None and not baseline_df.empty:
        baseline_match = baseline_df[baseline_df['REId'] == entity_data['REId']]
        if not baseline_match.empty:
            baseline_row = baseline_match.iloc[0]
    
    # Definiera komponenter
    components = [
        ('Påverkbara kostnader', 'Paverkbara_Kostnader'),
        ('Opåverkbara kostnader', 'Opaverkbara_Kostnader'),
        ('Kapitalkostnad', 'Kapitalkostnad_Total'),
        ('  - Avskrivningar', 'Avskrivningar'),
        ('  - Avkastning', 'Avkastning'),
        ('Flexibilitetstjänster', 'Flexibilitetstjanster'),
        ('Avbrottsersättning 12-24h', 'Avbrottsersattning_12_24h'),
        ('**Total intäktsram**', 'Intaktsram_Total')
    ]
    
    table_data = []
    
    for name, col in components:
        # Aktuellt värde (scenario eller referens)
        current_val = entity_data.get(col, 0) or 0
        
        # Referensvärde (baseline)
        if baseline_row is not None:
            ref_val = baseline_row.get(col, 0) or 0
        else:
            ref_val = current_val
        
        # Skillnad
        diff = current_val - ref_val
        diff_pct = (diff / ref_val * 100) if ref_val > 0 else 0
        
        # Källa med specifik modifieringsinformation
        source = get_detailed_source(name, col, entity_data, modifications)
        
        # Formatera
        table_data.append({
            'Komponent': name,
            'Aktivt värde (tkr)': f"{current_val:,.0f}".replace(",", " "),
            'Referensvärde (tkr)': f"{ref_val:,.0f}".replace(",", " "),
            'Skillnad (tkr)': f"{diff:+,.0f}".replace(",", " ") if abs(diff) > 0.5 else "—",
            'Δ%': f"{diff_pct:+.1f}%" if abs(diff) > 0.5 else "—",
            'Källa': source
        })
    
    df_table = pd.DataFrame(table_data)
    st.dataframe(df_table, use_container_width=True, hide_index=True)


def get_detailed_source(component_name: str, col: str, entity_data: pd.Series, modifications: dict) -> str:
    """
    Returnerar detaljerad källinformation för varje komponent.
    """
    # Påverkbara kostnader
    if col == 'Paverkbara_Kostnader':
        if entity_data.get('Uppdaterad_Paverkbara', False):
            effkrav_mod = modifications.get('paverkbara', {})
            if effkrav_mod.get('source') == 'effektiviseringskrav':
                method = effkrav_mod.get('method', 'OPEX')
                dea_result = effkrav_mod.get('dea_result')
                if dea_result is not None and not dea_result.empty:
                    effkrav_pct = dea_result.iloc[0].get('Effkrav_proc', 0) * 100
                    return f"Eff. krav {effkrav_pct:.2f}% på {method}"
                return f"Effektiviseringskrav ({method})"
        return "Referens"
    
    # Kapitalkostnad
    if col == 'Kapitalkostnad_Total':
        if entity_data.get('Uppdaterad_Kapitalkostnad', False):
            kapital_mod = modifications.get('kapitalkostnad', {})
            metadata = kapital_mod.get('metadata', {})
            wacc = metadata.get('wacc_new')
            if wacc:
                return f"WACC: {wacc*100:.2f}%"
            return "Kapitalbas"
        return "Referens"
    
    # Avkastning (visa också WACC om modifierad)
    if col == 'Avkastning':
        if entity_data.get('Uppdaterad_Kapitalkostnad', False):
            kapital_mod = modifications.get('kapitalkostnad', {})
            metadata = kapital_mod.get('metadata', {})
            wacc = metadata.get('wacc_new')
            if wacc:
                return f"WACC: {wacc*100:.2f}%"
            return "Kapitalbas"
        return "Referens"
    
    # Övriga komponenter
    if entity_data.get(f'Uppdaterad_{col}', False):
        return "Modifierad"
    
    return "Referens"


def show_yearly_paverkbara_table(entity_data: pd.Series, modifications: dict):
    """
    Visar årsvisa påverkbara kostnader
    """
    st.markdown("### Påverkbara kostnader per år")
    
    # Kontrollera om vi har årsvis data
    has_yearly = all(
        entity_data.get(f'Paverkbara_{year}', None) is not None 
        for year in [2024, 2025, 2026, 2027]
    )
    
    if not has_yearly:
        st.info("Årsvis data för påverkbara kostnader är inte tillgänglig")
        return
    
    years = [2024, 2025, 2026, 2027]
    rows = []
    
    for year in years:
        scenario_val = entity_data.get(f'Paverkbara_{year}', 0)
        baseline_val = entity_data.get(f'Paverkbara_{year}_Baseline', scenario_val)
        delta = scenario_val - baseline_val
        delta_pct = (delta / baseline_val * 100) if baseline_val != 0 else 0
        
        rows.append({
            'År': year,
            'Scenario (tkr)': f"{scenario_val:,.0f}".replace(",", " "),
            'Baseline (tkr)': f"{baseline_val:,.0f}".replace(",", " "),
            'Förändring (tkr)': f"{delta:+,.0f}".replace(",", " ") if abs(delta) > 1 else "—",
            'Förändring (%)': f"{delta_pct:+.1f}%" if abs(delta) > 1 else "—"
        })
    
    df_yearly = pd.DataFrame(rows)
    st.dataframe(df_yearly, use_container_width=True, hide_index=True)


def show_yearly_kapitalkostnad_placeholder():
    """
    Placeholder för årsvisa kapitalkostnader
    """
    st.markdown("### Kapitalkostnad per period")
    st.info("Detaljerad periodvis kapitalkostnad implementeras i nästa fas")


def show_export_section(entity_data: pd.Series, modifications: dict):
    """
    Visar export-funktionalitet
    """
    st.markdown("### Exportera scenario")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Exportera till Excel", use_container_width=True):
            try:
                excel_data = create_excel_export(entity_data, modifications)
                st.download_button(
                    label="Ladda ner Excel-fil",
                    data=excel_data,
                    file_name=f"intaktsram_scenario_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            except Exception as e:
                st.error(f"Export misslyckades: {e}")
    
    with col2:
        if st.button("Skapa rapport (PDF)", use_container_width=True):
            st.info("PDF-rapport implementeras i nästa fas")


def create_excel_export(entity_data: pd.Series, modifications: dict) -> bytes:
    """
    Skapar Excel-export av scenario
    """
    output = io.BytesIO()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Skapa översikt-sheet
        overview_data = {
            'Komponent': [],
            'Scenario (tkr)': [],
            'Baseline (tkr)': [],
            'Förändring (tkr)': [],
            'Förändring (%)': []
        }
        
        components = [
            ('Löpande kostnader', 'Lopande_Total'),
            ('Påverkbara kostnader', 'Paverkbara_Total'),
            ('Ej påverkbara kostnader', 'Opaverkbara_Total'),
            ('Kapitalkostnad', 'Kapitalkostnad_Total'),
            ('Flexibilitetstjänster', 'Flexibilitetstjanster_Total'),
            ('Avbrottsersättning', 'Avbrottsersattning_Total'),
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
        
        # Skapa metadata-sheet
        metadata = {
            'Parameter': ['Scenario-namn', 'Exportdatum', 'Företag', 'DMU'],
            'Värde': [
                st.session_state.get('current_scenario_name', 'Namnlöst'),
                datetime.now().strftime('%Y-%m-%d %H:%M'),
                entity_data.get('Företag', 'N/A'),
                entity_data.get('DMU', 'N/A')
            ]
        }
        df_metadata = pd.DataFrame(metadata)
        df_metadata.to_excel(writer, sheet_name='Metadata', index=False)
    
    output.seek(0)
    return output.read()
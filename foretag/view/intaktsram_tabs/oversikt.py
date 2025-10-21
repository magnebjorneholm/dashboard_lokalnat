"""
foretag/view/intaktsram_tabs/oversikt.py
Översikt-tab för intäktsram-dekomposition med komplett sammanställning
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
    
    # SCENARIO-STATUSRUTA (om aktivt)
    if has_active_scenario:
        show_scenario_status(modifications)
        st.markdown("---")
    
    # KOMBINERAD KOMPONENTTABELL MED JÄMFÖRELSE
    show_combined_component_table(entity_data, modifications)
    
    st.markdown("---")
    
    # ÅRSVISA PÅVERKBARA KOSTNADER (exakt duplicerad från effektiviseringskrav)
    show_yearly_paverkbara_table(entity_data, modifications)
    
    st.markdown("---")
    
    # KAPITALKOSTNADER PER PERIOD (placeholder)
    show_yearly_kapitalkostnad_placeholder()
    
    # EXPORT-FUNKTIONALITET
    st.markdown("---")
    show_export_section(entity_data, modifications)


def show_scenario_status(modifications: dict):
    """Visar status för aktivt scenario."""
    scenario_name = st.session_state.get('current_scenario_name', 'Namnlöst scenario')
    
    st.info(f"**Aktivt scenario:** {scenario_name}")
    
    # Lista modifierade komponenter
    modified_components = []
    
    if 'kapitalkostnad' in modifications:
        kapital_mod = modifications['kapitalkostnad']
        source = kapital_mod.get('source', 'manuell')
        if source == 'kapitalbas':
            metadata = kapital_mod.get('metadata', {})
            wacc = metadata.get('wacc_new')
            if wacc:
                modified_components.append(f"• Kapitalkostnad (WACC: {wacc*100:.2f}%)")
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
                modified_components.append(f"• Påverkbara kostnader (från DEA, {method}-metod, -{effkrav_pct:.2f}%)")
            else:
                modified_components.append(f"• Påverkbara kostnader (från DEA, {method}-metod)")
    
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
                    return f"Effektiviseringskrav {effkrav_pct:.2f}% på {method}"
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
    Visar årsvisa påverkbara kostnader (EXAKT duplicerad från effektiviseringskrav).
    """
    effkrav_mod = modifications.get('paverkbara', {}) if modifications else {}
    last_calc = effkrav_mod.get('last_calculation') if effkrav_mod else None
    
    # Om vi har beräkningsdata från scenario
    if last_calc is not None:
        export_data = last_calc.get('export_data')
        
        if export_data is not None and not export_data.empty:
            reid = entity_data['REId']
            entity_calc = export_data[export_data['REId'] == reid]
            
            if not entity_calc.empty:
                row = entity_calc.iloc[0]
                
                # Hämta årsvisa värden
                y2024_base = row.get('Y2024_baseline', 0)
                y2025_base = row.get('Y2025_baseline', 0)
                y2026_base = row.get('Y2026_baseline', 0)
                y2027_base = row.get('Y2027_baseline', 0)
                
                y2024_scn = row.get('Y2024_scenario', 0)
                y2025_scn = row.get('Y2025_scenario', 0)
                y2026_scn = row.get('Y2026_scenario', 0)
                y2027_scn = row.get('Y2027_scenario', 0)
                
                st.write("**Årsvisa påverkbara kostnader:**")
                
                yearly_data = pd.DataFrame({
                    'År': [2024, 2025, 2026, 2027],
                    'Ei baseline (tkr)': [
                        f"{y2024_base:,.0f}".replace(",", " "),
                        f"{y2025_base:,.0f}".replace(",", " "),
                        f"{y2026_base:,.0f}".replace(",", " "),
                        f"{y2027_base:,.0f}".replace(",", " ")
                    ],
                    'Scenario (tkr)': [
                        f"{y2024_scn:,.0f}".replace(",", " "),
                        f"{y2025_scn:,.0f}".replace(",", " "),
                        f"{y2026_scn:,.0f}".replace(",", " "),
                        f"{y2027_scn:,.0f}".replace(",", " ")
                    ],
                    'Skillnad (tkr)': [
                        f"{(y2024_base - y2024_scn):+,.0f}".replace(",", " "),
                        f"{(y2025_base - y2025_scn):+,.0f}".replace(",", " "),
                        f"{(y2026_base - y2026_scn):+,.0f}".replace(",", " "),
                        f"{(y2027_base - y2027_scn):+,.0f}".replace(",", " ")
                    ],
                    'Inkrement (tkr)': [
                        f"{row.get('Inc_2024_scn', 0):,.0f}".replace(",", " "),
                        f"{row.get('Inc_2025_scn', 0):,.0f}".replace(",", " "),
                        f"{row.get('Inc_2026_scn', 0):,.0f}".replace(",", " "),
                        f"{row.get('Inc_2027_scn', 0):,.0f}".replace(",", " ")
                    ],
                    'Kumulativt avdrag (tkr)': [
                        f"{row.get('Avdrag_2024_scn', 0):,.0f}".replace(",", " "),
                        f"{row.get('Avdrag_2025_scn', 0):,.0f}".replace(",", " "),
                        f"{row.get('Avdrag_2026_scn', 0):,.0f}".replace(",", " "),
                        f"{row.get('Avdrag_2027_scn', 0):,.0f}".replace(",", " ")
                    ]
                })
                
                st.dataframe(yearly_data, use_container_width=True, hide_index=True)
                st.caption("Alla värden är för perioden 2024-2027 (4 år totalt)")
                return
    
    # Om inget scenario: visa info
    st.info("Importera effektiviseringskrav från DEA för att se årsvisa värden")


def show_yearly_kapitalkostnad_placeholder():
    """
    Placeholder för kapitalkostnader per period (kommer snart).
    """
    st.write("**Kapitalkostnader per period:**")
    
    # Visa tom tabell-struktur för att visa hur det kommer se ut
    placeholder_data = pd.DataFrame({
        'År': [2024, 2025, 2026, 2027],
        'Avskrivningar (tkr)': ['—', '—', '—', '—'],
        'Avkastning (tkr)': ['—', '—', '—', '—'],
        'Total kapitalkostnad (tkr)': ['—', '—', '—', '—']
    })
    
    st.dataframe(placeholder_data, use_container_width=True, hide_index=True)
    st.info("Kommer snart")


def show_export_section(entity_data: pd.Series, modifications: dict):
    """Visar export-funktionalitet."""
    st.write("**Export:**")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Excel-export
        buffer = create_comprehensive_excel_export(entity_data, modifications)
        
        scenario_name = st.session_state.get('current_scenario_name', 'baseline')
        reid = entity_data.get('REId', 'unknown')
        filename = f"oversikt_{reid}_{scenario_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
        
        st.download_button(
            label="Ladda ned som Excel",
            data=buffer.getvalue(),
            file_name=filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
    
    with col2:
        st.caption("Exporterar komplett översikt med alla tillgängliga data")


def create_comprehensive_excel_export(entity_data: pd.Series, modifications: dict) -> io.BytesIO:
    """Skapar omfattande Excel-export med all tillgänglig data."""
    buffer = io.BytesIO()
    
    # Hämta baseline för jämförelse
    baseline_df = st.session_state.scenario_data.get('baseline') if 'scenario_data' in st.session_state else None
    baseline_row = None
    
    if baseline_df is not None and not baseline_df.empty:
        baseline_match = baseline_df[baseline_df['REId'] == entity_data['REId']]
        if not baseline_match.empty:
            baseline_row = baseline_match.iloc[0]
    
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        # Sheet 1: Komponenter med full jämförelse
        components = [
            ('Påverkbara kostnader', 'Paverkbara_Kostnader'),
            ('Opåverkbara kostnader', 'Opaverkbara_Kostnader'),
            ('Kapitalkostnad', 'Kapitalkostnad_Total'),
            ('Avskrivningar', 'Avskrivningar'),
            ('Avkastning', 'Avkastning'),
            ('Flexibilitetstjänster', 'Flexibilitetstjanster'),
            ('Avbrottsersättning 12-24h', 'Avbrottsersattning_12_24h'),
            ('Total intäktsram', 'Intaktsram_Total')
        ]
        
        comp_data = []
        for name, col in components:
            current_val = entity_data.get(col, 0) or 0
            ref_val = baseline_row.get(col, 0) if baseline_row is not None else current_val
            diff = current_val - ref_val
            diff_pct = (diff / ref_val * 100) if ref_val > 0 else 0
            source = get_detailed_source(name, col, entity_data, modifications)
            
            comp_data.append({
                'Komponent': name,
                'Aktivt värde (tkr)': current_val,
                'Referensvärde (tkr)': ref_val,
                'Skillnad (tkr)': diff,
                'Skillnad (%)': diff_pct,
                'Källa': source
            })
        
        df_components = pd.DataFrame(comp_data)
        df_components.to_excel(writer, sheet_name='Komponenter', index=False)
        
        # Sheet 2: Årsvisa påverkbara (om tillgängliga)
        effkrav_mod = modifications.get('paverkbara', {}) if modifications else {}
        last_calc = effkrav_mod.get('last_calculation')
        
        if last_calc:
            export_data = last_calc.get('export_data')
            if export_data is not None and not export_data.empty:
                reid = entity_data['REId']
                entity_calc = export_data[export_data['REId'] == reid]
                
                if not entity_calc.empty:
                    row = entity_calc.iloc[0]
                    
                    yearly_data = {
                        'År': [2024, 2025, 2026, 2027],
                        'Ei baseline (tkr)': [
                            row.get('Y2024_baseline', 0),
                            row.get('Y2025_baseline', 0),
                            row.get('Y2026_baseline', 0),
                            row.get('Y2027_baseline', 0)
                        ],
                        'Scenario (tkr)': [
                            row.get('Y2024_scenario', 0),
                            row.get('Y2025_scenario', 0),
                            row.get('Y2026_scenario', 0),
                            row.get('Y2027_scenario', 0)
                        ],
                        'Skillnad (tkr)': [
                            row.get('Y2024_baseline', 0) - row.get('Y2024_scenario', 0),
                            row.get('Y2025_baseline', 0) - row.get('Y2025_scenario', 0),
                            row.get('Y2026_baseline', 0) - row.get('Y2026_scenario', 0),
                            row.get('Y2027_baseline', 0) - row.get('Y2027_scenario', 0)
                        ],
                        'Inkrement (tkr)': [
                            row.get('Inc_2024_scn', 0),
                            row.get('Inc_2025_scn', 0),
                            row.get('Inc_2026_scn', 0),
                            row.get('Inc_2027_scn', 0)
                        ],
                        'Kumulativt avdrag (tkr)': [
                            row.get('Avdrag_2024_scn', 0),
                            row.get('Avdrag_2025_scn', 0),
                            row.get('Avdrag_2026_scn', 0),
                            row.get('Avdrag_2027_scn', 0)
                        ]
                    }
                    
                    df_yearly = pd.DataFrame(yearly_data)
                    df_yearly.to_excel(writer, sheet_name='Årsvisa_påverkbara', index=False)
        
        # Sheet 3: Metadata och scenario-info
        scenario_name = st.session_state.get('current_scenario_name', 'Baseline')
        
        metadata_rows = [
            ('REId', entity_data.get('REId', '')),
            ('DMU', entity_data.get('DMU', '')),
            ('Företag', entity_data.get('Företag', '')),
            ('', ''),
            ('Scenario', scenario_name),
            ('Exportdatum', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
            ('', ''),
        ]
        
        # Lägg till modifieringsinformation
        if 'kapitalkostnad' in modifications:
            kapital_mod = modifications['kapitalkostnad']
            metadata = kapital_mod.get('metadata', {})
            wacc = metadata.get('wacc_new')
            if wacc:
                metadata_rows.append(('Kapitalkostnad WACC', f"{wacc*100:.4f}%"))
            metadata_rows.append(('Kapitalkostnad källa', kapital_mod.get('source', 'okänd')))
        
        if 'paverkbara' in modifications:
            effkrav_mod = modifications['paverkbara']
            if effkrav_mod.get('source') == 'effektiviseringskrav':
                method = effkrav_mod.get('method', 'OPEX')
                metadata_rows.append(('Effektiviseringskrav metod', method))
                dea_result = effkrav_mod.get('dea_result')
                if dea_result is not None and not dea_result.empty:
                    effkrav_pct = dea_result.iloc[0].get('Effkrav_proc', 0) * 100
                    metadata_rows.append(('Effektiviseringskrav %', f"{effkrav_pct:.2f}%"))
        
        df_metadata = pd.DataFrame(metadata_rows, columns=['Parameter', 'Värde'])
        df_metadata.to_excel(writer, sheet_name='Metadata', index=False)
        
        # Sheet 4: Rådata (alla kolumner från entity_data för power users)
        raw_data = pd.DataFrame([entity_data]).T
        raw_data.columns = ['Värde']
        raw_data.to_excel(writer, sheet_name='Rådata')
    
    buffer.seek(0)
    return buffer
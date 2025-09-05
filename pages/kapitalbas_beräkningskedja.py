"""
kapitalbas_berakningslogik.py - Stegvis beräkning av kapitalkostnader för enskild DMU

Implementerar beräkningskedjan 5→6→7→8→9 interaktivt:
5. ages_and_nuav
6. depreciation  
7. returns
8. compile (capcost)
9. jämför med facit
"""

import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional
import plotly.express as px
import plotly.graph_objects as go

# Import befintliga beräkningsfunktioner (refaktoriserade)
from kapitalbas.beräkningsfiler.Beräkningskedja_capcost.beräkningskedja import (
    load_dmu_capbase_a,
    calculate_ages_and_nuav,
    calculate_depreciation_single_dmu,
    calculate_returns_single_dmu,
    compile_capcost_single_dmu,
    load_facit_for_dmu
)

if "access_granted" not in st.session_state or not st.session_state.access_granted:
    st.stop()

st.set_page_config(page_title="Beräkningkedja för kapitalkostnader", layout="wide")
st.title("Beräkningkedja för kapitalkostnader")
st.markdown("Gå igenom beräkningskedjan med möjlighet att (snart) ändra utdata i varje steg.")


def show_kapitalbas_berakningslogik():
    """Huvudvy för stegvis beräkningslogik"""
    
    # === DMU-val ===
    dmu_id = select_dmu()
    if not dmu_id:
        return
        
    # === Ladda grunddata ===
    with st.spinner("Laddar data för DMU..."):
        capbase_data = load_dmu_capbase_a(dmu_id)
        
    if capbase_data.empty:
        st.error(f"Ingen data hittades för DMU {dmu_id}")
        return
    
    st.success(f"Laddade {len(capbase_data)} komponenter för DMU {dmu_id}")
    
    # === Visa grunddata ===
    with st.expander("Grunddata (capbase_a)"):
        st.dataframe(capbase_data, use_container_width=True)
        
        # Enkel statistik
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Antal komponenter", len(capbase_data))
        with col2:
            st.metric("Total NUAV 2022 (MSEK)", f"{capbase_data['nuav_2022'].sum()/1000:.1f}")
        with col3:
            unique_categories = capbase_data['cat_encode'].nunique()
            st.metric("Antal kategorier", unique_categories)
    
    # === Beräkningssteg ===
    st.header("Beräkningssteg")
    
    # Initialisera session state för steg
    if f'dmu_{dmu_id}_steps' not in st.session_state:
        st.session_state[f'dmu_{dmu_id}_steps'] = {
            'current_step': 0,
            'step_data': {},
            'completed_steps': set()
        }
    
    steps_state = st.session_state[f'dmu_{dmu_id}_steps']
    
    # Steg-knappar
    step_tabs = st.tabs([
        "Steg 5: Åldrar & NUAV", 
        "Steg 6: Avskrivningar", 
        "Steg 7: Avkastning",
        "Steg 8: Sammanställning", 
        "Steg 9: Jämför facit"
    ])
    
    with step_tabs[0]:
        run_step_5_ages_nuav(capbase_data, dmu_id, steps_state)
    
    with step_tabs[1]:
        run_step_6_depreciation(dmu_id, steps_state)
    
    with step_tabs[2]:
        run_step_7_returns(dmu_id, steps_state)
    
    with step_tabs[3]:
        run_step_8_compile(dmu_id, steps_state)
        
    with step_tabs[4]:
        run_step_9_compare_facit(dmu_id, steps_state)


def select_dmu() -> Optional[int]:
    """DMU-väljare"""
    
    # Hämta tillgängliga DMU från reconciliation
    try:
        # Läs från new_recon.csv
        recon_path = "effektiviseringskrav/data/new_recon.csv"
        if Path(recon_path).exists():
            recon_df = pd.read_csv(recon_path)
            
            # Skapa dropdown-alternativ med företagsnamn (DMU) - exakt som IR-koden
            entity_options = []
            entity_mapping = {}
            
            # Använd samma logik som IR-dekomposition
            for dmu_float in sorted(recon_df['DMU'].dropna().unique()):
                dmu_int = int(float(dmu_float))  # Konvertera till int för visning
                row = recon_df[recon_df['DMU'] == dmu_float].iloc[0]
                företag = row.get('Företag', 'Okänt företag')
                
                # Format: "Företagsnamn (DMU)" - exakt som IR-koden
                display_name = f"{företag} ({dmu_int})"
                
                entity_options.append(display_name)
                entity_mapping[display_name] = dmu_int  # Spara som int
                
        else:
            st.warning("Reconciliation-fil saknas - använder hårdkodade DMU")
            entity_options = ["Göteborg Energi (30)", "Umeå Energi (115)", "Kraftringen (121)"]
            entity_mapping = {"Göteborg Energi (30)": 30, "Umeå Energi (115)": 115, "Kraftringen (121)": 121}
            
    except Exception as e:
        st.error(f"Fel vid laddning av DMU-lista: {e}")
        return None
    
    # DMU-väljare
    st.sidebar.header("Välj DMU")
    
    if not entity_options:
        st.sidebar.error("Inga DMU hittades")
        return None
    
    selected_display = st.sidebar.selectbox(
        entity_options,
    )
    
    if selected_display:
        return entity_mapping[selected_display]
    
    return None


def run_step_5_ages_nuav(capbase_data: pd.DataFrame, dmu_id: int, steps_state: dict):
    """Steg 5: Beräkna åldrar och NUAV-värden"""
    
    st.subheader("Steg 5: Åldrar och NUAV-värden")
    st.write("Beräknar komponenternas ålder och nuanskaffningsvärden för varje tidsperiod (229-236)")
    
    # Visa indata-sammanfattning
    with st.expander("Indata-översikt"):
        st.write("**Viktiga kolumner från capbase_a:**")
        col1, col2 = st.columns(2)
        with col1:
            st.write("- `time_from`: Komponentens startår")
            st.write("- `time_invest`: Investeringsår (för nya komponenter)")
            st.write("- `capbase_existing`: 1=befintlig, 0=ny investering")
        with col2:
            st.write("- `ekdep`: Ekonomisk livslängd")
            st.write("- `maxdep`: Maximal livslängd") 
            st.write("- `nuav_2022`: Nuanskaffningsvärde 2022")
    
    # Kör beräkning
    if st.button("Kör Steg 5: Åldrar & NUAV", key="step5_button"):
        with st.spinner("Beräknar åldrar och NUAV..."):
            try:
                result_data = calculate_ages_and_nuav(capbase_data)
                steps_state['step_data'][5] = result_data
                steps_state['completed_steps'].add(5)
                steps_state['current_step'] = max(steps_state['current_step'], 5)
                st.success("Steg 5 slutfört!")
                st.rerun()
                
            except Exception as e:
                st.error(f"Fel i steg 5: {e}")
                st.exception(e)
    
    # Visa resultat om steg är slutfört
    if 5 in steps_state['completed_steps']:
        st.success("Steg 5 slutfört")
        result_data = steps_state['step_data'][5]
        
        # Sammanfattning
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Komponenter", len(result_data))
        with col2:
            # Räkna hur många tidsperioder som har data
            time_cols = [col for col in result_data.columns if col.startswith('age_component_')]
            st.metric("Tidsperioder", len(time_cols))
        with col3:
            # Total NUAV för period 229 (2024H1)
            nuav_229 = result_data.get('nuav_ord_229', pd.Series(0)).sum()
            st.metric("NUAV ordinarie 2024H1 (tkr)", f"{nuav_229:,.0f}")
        
        # Detaljerad vy
        with st.expander("Resultat - detaljvy"):
            # Välj vilka kolumner att visa
            display_cols = st.multiselect(
                "Kolumner att visa",
                options=result_data.columns.tolist(),
                default=['id_component', 'cat_encode', 'age_component_229', 'nuav_ord_229', 'nuav_tail_229']
            )
            
            if display_cols:
                st.dataframe(result_data[display_cols], use_container_width=True)
        
        # Visualisering
        with st.expander("Visualisering - Åldersfördelning"):
            if 'age_component_229' in result_data.columns:
                fig = px.histogram(
                    result_data, 
                    x='age_component_229',
                    title='Åldersfördelning komponenter 2024H1',
                    nbins=30
                )
                st.plotly_chart(fig, use_container_width=True)


def run_step_6_depreciation(dmu_id: int, steps_state: dict):
    """Steg 6: Beräkna avskrivningar"""
    
    st.subheader("Steg 6: Avskrivningar")
    st.write("Beräknar ordinarie och svansavskrivningar baserat på åldrar och livslängder")
    
    # Kontrollera att steg 5 är klart
    if 5 not in steps_state['completed_steps']:
        st.warning("Slutför först Steg 5")
        return
    
    # Visa metodik
    with st.expander("Avskrivningsmetodik"):
        st.write("**Ordinarie avskrivning:**")
        st.latex(r"dep\_ord = \frac{nuav\_ord}{ekdep}")
        st.write("**Svansavskrivning:**")  
        st.latex(r"dep\_tail = \frac{nuav\_tail}{age\_reg}")
        st.write("Där age_reg justeras för udda åldrar")
    
    if st.button("Kör Steg 6: Avskrivningar", key="step6_button"):
        with st.spinner("Beräknar avskrivningar..."):
            try:
                input_data = steps_state['step_data'][5]
                result_data = calculate_depreciation_single_dmu(input_data)
                steps_state['step_data'][6] = result_data
                steps_state['completed_steps'].add(6)
                steps_state['current_step'] = max(steps_state['current_step'], 6)
                st.success("Steg 6 slutfört!")
                st.rerun()
                
            except Exception as e:
                st.error(f"Fel i steg 6: {e}")
                st.exception(e)
    
    # Visa resultat
    if 6 in steps_state['completed_steps']:
        st.success("Steg 6 slutfört")
        result_data = steps_state['step_data'][6]
        
        # KPI med full precision
        col1, col2 = st.columns(2)
        with col1:
            dep_ord_total = sum(result_data.get(f'dep_ord_{t}', 0) for t in range(229, 237))
            st.metric("Total ordinarie avskrivning (tkr)", f"{dep_ord_total}")
        with col2:
            dep_tail_total = sum(result_data.get(f'dep_tail_{t}', 0) for t in range(229, 237))
            st.metric("Total svansavskrivning (tkr)", f"{dep_tail_total}")
        
        with st.expander("Resultat per tidsperiod"):
            # Skapa tabell per tidsperiod med full precision
            periods_data = []
            for t in range(229, 237):
                dep_ord = result_data.get(f'dep_ord_{t}', 0)
                dep_tail = result_data.get(f'dep_tail_{t}', 0)
                periods_data.append({
                    'Period': f"{t} ({2024 + (t-229)//2}H{((t-229)%2)+1})",
                    'Ordinarie (tkr)': dep_ord,
                    'Svans (tkr)': dep_tail,
                    'Total (tkr)': dep_ord + dep_tail
                })
            
            st.dataframe(pd.DataFrame(periods_data), use_container_width=True)


def run_step_7_returns(dmu_id: int, steps_state: dict):
    """Steg 7: Beräkna avkastning"""
    
    st.subheader("Steg 7: Avkastning")
    st.write("Beräknar kapitalavkastning baserat på åldersjusterad kapitalbas")
    
    if 6 not in steps_state['completed_steps']:
        st.warning("Slutför först Steg 6")
        return
    
    # WACC-inställning
    current_wacc = st.number_input(
        "Kalkylränta (WACC)",
        min_value=0.0,
        max_value=0.10,
        value=0.0453,
        step=0.0001,
        format="%.4f",
        help="Real kalkylränta före skatt (standard: 4.53%)"
    )
    
    with st.expander("Avkastningsmetodik"):
        st.write("**Ordinarie avkastning:**")
        st.latex(r"capbase\_left\_ord = \frac{(ekdep/2 - age\_return)}{ekdep/2} \times nuav\_ord")
        st.latex(r"return\_ord = WACC \times capbase\_left\_ord / 2")
        st.write("**Svansavkastning:**")
        st.latex(r"capbase\_left\_tail = \frac{nuav\_tail}{age\_return + 1}")
        st.latex(r"return\_tail = WACC \times capbase\_left\_tail / 2")
    
    if st.button("Kör Steg 7: Avkastning", key="step7_button"):
        with st.spinner("Beräknar avkastning..."):
            try:
                input_data = steps_state['step_data'][5]  # Använd data från steg 5
                result_data = calculate_returns_single_dmu(input_data, interest_rate=current_wacc)
                steps_state['step_data'][7] = result_data
                steps_state['completed_steps'].add(7)
                steps_state['current_step'] = max(steps_state['current_step'], 7)
                st.success("Steg 7 slutfört!")
                st.rerun()
                
            except Exception as e:
                st.error(f"Fel i steg 7: {e}")
                st.exception(e)
    
    # Visa resultat
    if 7 in steps_state['completed_steps']:
        st.success("Steg 7 slutfört")
        result_data = steps_state['step_data'][7]
        
        # KPI med höga decimaler
        col1, col2 = st.columns(2)
        with col1:
            ret_ord_total = sum(result_data.get(f'return_ord_{t}', 0) for t in range(229, 237))
            st.metric("Total ordinarie avkastning (tkr)", f"{ret_ord_total:.6f}")
        with col2:
            ret_tail_total = sum(result_data.get(f'return_tail_{t}', 0) for t in range(229, 237))
            st.metric("Total svansavkastning (tkr)", f"{ret_tail_total:.6f}")


def run_step_8_compile(dmu_id: int, steps_state: dict):
    """Steg 8: Sammanställ kapitalkostnad"""
    
    st.subheader("Steg 8: Sammanställning")
    st.write("Kombinerar avskrivningar och avkastning till total kapitalkostnad")
    
    if not (6 in steps_state['completed_steps'] and 7 in steps_state['completed_steps']):
        st.warning("Slutför först Steg 6 och 7")
        return
    
    if st.button("Kör Steg 8: Sammanställning", key="step8_button"):
        with st.spinner("Sammanställer kapitalkostnad..."):
            try:
                dep_data = steps_state['step_data'][6]
                ret_data = steps_state['step_data'][7]
                result_data = compile_capcost_single_dmu(dep_data, ret_data, dmu_id)
                steps_state['step_data'][8] = result_data
                steps_state['completed_steps'].add(8)
                steps_state['current_step'] = max(steps_state['current_step'], 8)
                st.success("Steg 8 slutfört!")
                st.rerun()
                
            except Exception as e:
                st.error(f"Fel i steg 8: {e}")
                st.exception(e)
    
    # Visa resultat
    if 8 in steps_state['completed_steps']:
        st.success("Steg 8 slutfört")
        result_data = steps_state['step_data'][8]
        
        # Beräkna KPI:er med full precision
        total_capcost = result_data['capcost_sum'].sum()
        total_kapitalbindning = result_data['return_ord'].sum() + result_data['return_tail'].sum()
        total_kapitalforslitning = result_data['dep_ord'].sum() + result_data['dep_tail'].sum()
        
        # Huvudresultat - tre KPI:er med hög precision
        st.metric("Total kapitalkostnad (tkr)", f"{total_capcost}")
        st.metric("Total kapitalbindning (tkr)", f"{total_kapitalbindning}")
        st.metric("Total kapitalförslitning (tkr)", f"{total_kapitalforslitning}")

        # Breakdown per period
        with st.expander("Breakdown per tidsperiod"):
            # Formatera för att visa fler decimaler
            display_data = result_data.copy()
            st.dataframe(display_data, use_container_width=True)
        
        # Visualisering
        with st.expander("Visualisering - Kapitalkostnad över tid"):
            # Gruppera per tidsperiod
            period_totals = result_data.groupby('time')['capcost_sum'].sum().reset_index()
            period_totals['period_label'] = period_totals['time'].map(
                {229: '2024H1', 230: '2024H2', 231: '2025H1', 232: '2025H2',
                 233: '2026H1', 234: '2026H2', 235: '2027H1', 236: '2027H2'}
            )
            
            fig = px.bar(
                period_totals,
                x='period_label', 
                y='capcost_sum',
                title='Kapitalkostnad per halvår',
                labels={'capcost_sum': 'Kapitalkostnad (tkr)', 'period_label': 'Period'}
            )
            st.plotly_chart(fig, use_container_width=True)
            
        # Detaljerad uppdelning med full precision
        with st.expander("Detaljerad uppdelning per komponent"):
            breakdown_data = []
            for time in range(229, 237):
                period_data = result_data[result_data['time'] == time].iloc[0]
                breakdown_data.append({
                    'Period': f"{time} ({2024 + (time-229)//2}H{((time-229)%2)+1})",
                    'Ordinarie avskrivning': period_data['dep_ord'],
                    'Svansavskrivning': period_data['dep_tail'],
                    'Ordinarie avkastning': period_data['return_ord'],
                    'Svansavkastning': period_data['return_tail'],
                    'Total kapitalkostnad': period_data['capcost_sum'],
                    'Kapitalförslitning (dep_ord + dep_tail)': period_data['dep_ord'] + period_data['dep_tail'],
                    'Kapitalbindning (return_ord + return_tail)': period_data['return_ord'] + period_data['return_tail']
                })
            
            breakdown_df = pd.DataFrame(breakdown_data)
            st.dataframe(breakdown_df, use_container_width=True)


def run_step_9_compare_facit(dmu_id: int, steps_state: dict):
    """Steg 9: Jämför med facit (begränsat till vissa DMU)"""
    
    st.subheader("Steg 9: Jämför med facit")
    
    if 8 not in steps_state['completed_steps']:
        st.warning("Slutför först Steg 8")
        return
    
    # Kolla om facit finns för denna DMU
    facit_available = check_facit_availability(dmu_id)

    
    if st.button("Ladda och jämför facit", key="step9_button"):
        with st.spinner("Laddar facit och jämför..."):
            try:
                calculated_data = steps_state['step_data'][8]
                facit_data = load_facit_for_dmu(dmu_id)
                
                if facit_data.empty:
                    st.error("Ingen facit-data kunde laddas för denna DMU")
                    return
                
                # Jämför
                comparison = compare_with_facit(calculated_data, facit_data, dmu_id)
                steps_state['step_data'][9] = comparison
                steps_state['completed_steps'].add(9)
                st.success("Steg 9 slutfört!")
                st.rerun()
                
            except Exception as e:
                st.error(f"Fel i steg 9: {e}")
                st.exception(e)
    
    # Visa jämförelse
    if 9 in steps_state['completed_steps']:
        st.success("Steg 9 slutfört")
        comparison = steps_state['step_data'][9]
        
        # Huvudresultat med full precision
        delta = comparison['calculated_total'] - comparison['facit_total']
        delta_pct = (delta / comparison['facit_total'] * 100) if comparison['facit_total'] != 0 else 0

        st.metric("Beräknat total", f"{comparison['calculated_total']} tkr")
        st.metric("Facit total", f"{comparison['facit_total']} tkr")
        st.metric("Differens", f"{delta:+} tkr", delta=f"{delta_pct:+.8f}%")
        
        # Detaljerad jämförelse
        with st.expander("Detaljerad jämförelse"):
            if 'comparison_df' in comparison:
                # Visa med full precision
                display_df = comparison['comparison_df'].copy()
                st.dataframe(display_df, use_container_width=True)
        
        # Toleransanalys med högre precision
        tolerance_tkr = st.number_input("Tolerans (tkr)", min_value=0.0, value=0.1, step=0.01, format="%.6f")
        abs_delta = abs(delta)
        if abs_delta <= tolerance_tkr:
            st.success(f"Beräkning OK! Differens {abs_delta} tkr ligger inom tolerans {tolerance_tkr} tkr")
        else:
            st.warning(f"Differens {abs_delta} tkr överskrider tolerans {tolerance_tkr} tkr")
            
        # Visa exakt differens för debugging
        with st.expander("Exakt differens-analys"):
            st.write(f"**Beräknat värde:** {comparison['calculated_total']}")
            st.write(f"**Facit värde:** {comparison['facit_total']}")
            st.write(f"**Absolut differens:** {abs_delta}")
            st.write(f"**Relativ differens:** {delta_pct}%")
            
          
def check_facit_availability(dmu_id: int) -> bool:
    """Kontrollerar om facit finns för den valda DMU:n"""
    try:
        recon_path = "effektiviseringskrav/data/new_recon.csv"
        if Path(recon_path).exists():
            recon_df = pd.read_csv(recon_path)
            dmu_networks = recon_df[recon_df['DMU'] == dmu_id]['id_network'].tolist()
            
            # Facit finns för id_network 1 och 3035
            return True
    except:
        pass
    
    return False


def compare_with_facit(calculated_data: pd.DataFrame, facit_data: pd.DataFrame, dmu_id: int) -> dict:
    """Jämför beräknade värden med facit"""
    
    # Aggregera till DMU-nivå för jämförelse
    calc_total = calculated_data['capcost_sum'].sum()
    
    # Facit borde vara aggregerat per DMU redan
    facit_total = facit_data['capcost_sum'].sum() if 'capcost_sum' in facit_data.columns else 0
    
    # Detaljerad jämförelse per period om möjligt
    comparison_df = pd.DataFrame({
        'Period': [f"{t} ({2024 + (t-229)//2}H{((t-229)%2)+1})" for t in range(229, 237)],
        'Beräknat': [calculated_data[calculated_data['time']==t]['capcost_sum'].sum() for t in range(229, 237)],
        'Facit': [facit_data[facit_data['time']==t]['capcost_sum'].sum() if 'time' in facit_data.columns else 0 for t in range(229, 237)]
    })
    comparison_df['Differens'] = comparison_df['Beräknat'] - comparison_df['Facit']
    comparison_df['Differens %'] = (comparison_df['Differens'] / comparison_df['Facit'] * 100).round(2)
    
    return {
        'calculated_total': calc_total,
        'facit_total': facit_total,
        'comparison_df': comparison_df,
        'dmu_id': dmu_id
    }


if __name__ == "__main__":
    show_kapitalbas_berakningslogik()
# foretag_berakningskedja.py
# Företagsspecifik stegvis beräkningskedja för kapitalkostnader
# ÅTERANVÄNDER EXAKT samma beräkningslogik från beräkningskedja.py

import streamlit as st
import pandas as pd
import numpy as np
import json
import os
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go

# Import från företagsspecifik data loader
from foretag.app.kapitalbas_data_loader import (
    get_user_dmu,
    get_user_org,
    load_reconciliation_foretag_info,
    validate_company_data
)

# KRITISK: Importera ALLA beräkningsfunktioner från fungerande version
from kapitalbas.beräkningsfiler.Beräkningskedja_capcost.beräkningskedja import (
    load_dmu_capbase_a,
    calculate_ages_and_nuav,
    calculate_depreciation_single_dmu,
    calculate_returns_single_dmu,
    compile_capcost_single_dmu,
    load_facit_for_dmu,
    validate_input_data,
    analyze_component_ages,
    analyze_nuav_distribution
)

# Autentisering
if "access_granted" not in st.session_state or not st.session_state.access_granted:
    st.stop()

if st.session_state.user_role != "company":
    st.error("Denna sida är endast tillgänglig för företagsanvändare")
    st.stop()


def show_foretag_berakningskedja():
    """Huvudfunktion för företagsspecifik beräkningskedja"""
    
    st.set_page_config(page_title="Mitt företag - Beräkningskedja", layout="wide")
    st.title("Mitt företag - Beräkningskedja för kapitalkostnader")
    
    # Hämta företagsinformation
    user_dmu = get_user_dmu()
    company_info = load_reconciliation_foretag_info()
    
    if user_dmu is None:
        st.error("Ingen DMU hittades för inloggad användare")
        return
    
    company_name = company_info.get('company_name', 'Ditt företag')
    
    st.markdown(f"### Stegvis beräkning för {company_name} (DMU {user_dmu})")
    st.markdown("Går igenom beräkningskedjan med exakt samma logik som huvudversionen.")
    
    # Validera data
    validation = validate_company_data()
    if not validation['capcost_data_available']:
        st.error("Kunde inte ladda data för beräkningskedjan")
        with st.expander("Debug-information"):
            st.json(validation)
        return
    
    # Ladda grunddata för DMU - ANVÄNDER SAMMA FUNKTION
    with st.spinner("Laddar komponentdata för ditt företag..."):
        capbase_data = load_dmu_capbase_a(user_dmu)
    
    if capbase_data.empty:
        st.error(f"Ingen komponentdata hittades för DMU {user_dmu}")
        st.info("Detta kan bero på att din DMU inte finns i kapitalbasen eller att data inte är tillgänglig")
        return
    
    st.success(f"Laddade {len(capbase_data)} komponenter för {company_name}")
    
    # Visa grunddata
    with st.expander("Grunddata (capbase_a) för ditt företag"):
        st.dataframe(capbase_data, use_container_width=True)
        
        # Företagsstatistik
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Antal komponenter", len(capbase_data))
        with col2:
            total_nuav = capbase_data['nuav_2022'].sum() if 'nuav_2022' in capbase_data.columns else 0
            st.metric("Total NUAV 2022 (MSEK)", f"{total_nuav/1000:.1f}")
        with col3:
            unique_categories = capbase_data['cat_encode'].nunique() if 'cat_encode' in capbase_data.columns else 0
            st.metric("Antal kategorier", unique_categories)
    
    # Initiera session state för steg
    session_key = f'company_steps_{user_dmu}'
    if session_key not in st.session_state:
        st.session_state[session_key] = {
            'current_step': 0,
            'step_data': {},
            'completed_steps': set()
        }
    
    steps_state = st.session_state[session_key]
    
    # Huvudtabs för beräkningssteg
    st.header("Beräkningssteg")
    
    step_tabs = st.tabs([
        "Steg 5: Åldrar & NUAV",
        "Steg 6: Avskrivningar", 
        "Steg 7: Avkastning",
        "Steg 8: Sammanställning",
        "Steg 9: Jämför facit"
    ])
    
    with step_tabs[0]:
        run_company_step_5_ages_nuav(capbase_data, user_dmu, steps_state, company_name)
    
    with step_tabs[1]:
        run_company_step_6_depreciation(user_dmu, steps_state, company_name)
    
    with step_tabs[2]:
        run_company_step_7_returns(user_dmu, steps_state, company_name)
    
    with step_tabs[3]:
        run_company_step_8_compile(user_dmu, steps_state, company_name)
    
    with step_tabs[4]:
        run_company_step_9_compare_facit(user_dmu, steps_state, company_name)


def run_company_step_5_ages_nuav(capbase_data: pd.DataFrame, dmu_id: int, steps_state: dict, company_name: str):
    """Steg 5: Beräkna åldrar och NUAV-värden för företaget - ANVÄNDER SAMMA LOGIK"""
    
    st.subheader(f"Steg 5: Åldrar och NUAV-värden för {company_name}")
    st.write("Beräknar komponenternas ålder och nuanskaffningsvärden för varje tidsperiod (229-236)")
    
    # Visa indata-sammanfattning
    with st.expander("Indata-översikt för ditt företag"):
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
        
        # Validation av indata - SAMMA FUNKTION
        validation = validate_input_data(capbase_data)
        if not validation['valid']:
            st.warning("Problem med indata:")
            for error in validation['errors']:
                st.error(f"• {error}")
        
        if validation['warnings']:
            for warning in validation['warnings']:
                st.warning(f"• {warning}")
    
    # Kör beräkning - EXAKT SAMMA FUNKTION
    if st.button("Kör Steg 5: Åldrar & NUAV", key=f"step5_button_{dmu_id}"):
        with st.spinner("Beräknar åldrar och NUAV för ditt företag..."):
            try:
                # SAMMA FUNKTION som fungerande version
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
        st.success("✅ Steg 5 slutfört")
        result_data = steps_state['step_data'][5]
        
        # Sammanfattning för företaget
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Komponenter", len(result_data))
        with col2:
            time_cols = [col for col in result_data.columns if col.startswith('age_component_')]
            st.metric("Tidsperioder", len(time_cols))
        with col3:
            nuav_229 = result_data.get('nuav_ord_229', pd.Series(0)).sum()
            st.metric("NUAV ordinarie 2024H1 (tkr)", f"{nuav_229:,.0f}")
        
        # Analys för debugging - SAMMA FUNKTION
        with st.expander("Analys - åldersfördelning för ditt företag"):
            if 'age_component_229' in result_data.columns:
                analysis = analyze_component_ages(result_data, 229)
                
                col_a, col_b = st.columns(2)
                with col_a:
                    st.write("**Åldersstatistik 2024H1:**")
                    stats = analysis['age_stats']
                    st.write(f"• Medel: {stats['mean']:.1f} år")
                    st.write(f"• Median: {stats['median']:.1f} år")
                    st.write(f"• Min: {stats['min']:.0f} år")
                    st.write(f"• Max: {stats['max']:.0f} år")
                
                with col_b:
                    st.write("**Åldersfördelning:**")
                    dist = analysis['age_distribution']
                    st.write(f"• Unga (0-10 år): {dist['young_0_10']} komponenter")
                    st.write(f"• Medelålders (10-30 år): {dist['medium_10_30']} komponenter")
                    st.write(f"• Gamla (30+ år): {dist['old_30_plus']} komponenter")


def run_company_step_6_depreciation(dmu_id: int, steps_state: dict, company_name: str):
    """Steg 6: Beräkna avskrivningar för företaget - ANVÄNDER SAMMA LOGIK"""
    
    st.subheader(f"Steg 6: Avskrivningar för {company_name}")
    st.write("Beräknar ordinarie och svansavskrivningar baserat på åldrar och livslängder")
    
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
    
    # Kör beräkning - EXAKT SAMMA FUNKTION
    if st.button("Kör Steg 6: Avskrivningar", key=f"step6_button_{dmu_id}"):
        with st.spinner(f"Beräknar avskrivningar för {company_name}..."):
            try:
                input_data = steps_state['step_data'][5]
                # SAMMA FUNKTION som fungerande version
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
        st.success("✅ Steg 6 slutfört")
        result_data = steps_state['step_data'][6]
        
        # KPI för företaget
        col1, col2 = st.columns(2)
        with col1:
            dep_ord_total = sum(result_data.get(f'dep_ord_{t}', 0) for t in range(229, 237))
            st.metric("Total ordinarie avskrivning (tkr)", f"{dep_ord_total:,.0f}")
        with col2:
            dep_tail_total = sum(result_data.get(f'dep_tail_{t}', 0) for t in range(229, 237))
            st.metric("Total svansavskrivning (tkr)", f"{dep_tail_total:,.0f}")


def run_company_step_7_returns(dmu_id: int, steps_state: dict, company_name: str):
    """Steg 7: Beräkna avkastning för företaget - ANVÄNDER SAMMA LOGIK"""
    
    st.subheader(f"Steg 7: Avkastning för {company_name}")
    st.write("Beräknar kapitalavkastning baserat på ålderssjusterad kapitalbas")
    
    if 6 not in steps_state['completed_steps']:
        st.warning("Slutför först Steg 6")
        return

    # ENKEL WACC-input (standard Ei-värde för nu)
    current_wacc = st.number_input(
        "Kalkylränta (WACC) - real, före skatt",
        min_value=0.0,
        max_value=0.15,
        value=0.0453,
        step=0.0001,
        format="%.4f",
        help="Real kalkylränta före skatt (Ei-standard: 4.53%)"
    )
    
    # Visa avkastningsmetodik
    with st.expander("Avkastningsmetodik"):
        st.write("**Ordinarie avkastning:**")
        st.latex(r"capbase\_left\_ord = \frac{(ekdep/2 - age\_return)}{ekdep/2} \times nuav\_ord")
        st.latex(r"return\_ord = WACC \times capbase\_left\_ord / 2")
        st.write("**Svansavkastning:**")
        st.latex(r"capbase\_left\_tail = \frac{nuav\_tail}{age\_return + 1}")
        st.latex(r"return\_tail = WACC \times capbase\_left\_tail / 2")
    
    # Kör avkastningsberäkning - EXAKT SAMMA FUNKTION
    if st.button("Kör Steg 7: Avkastning", key=f"step7_button_{dmu_id}"):
        with st.spinner(f"Beräknar avkastning för {company_name} med WACC {current_wacc:.4f}..."):
            try:
                input_data = steps_state['step_data'][5]
                # SAMMA FUNKTION som fungerande version
                result_data = calculate_returns_single_dmu(input_data, interest_rate=current_wacc)
                steps_state['step_data'][7] = result_data
                steps_state['step_data'][7]['used_wacc'] = current_wacc
                steps_state['completed_steps'].add(7)
                steps_state['current_step'] = max(steps_state['current_step'], 7)
                st.success("Steg 7 slutfört!")
                st.rerun()
            except Exception as e:
                st.error(f"Fel i steg 7: {e}")
                st.exception(e)
    
    # Visa resultat
    if 7 in steps_state['completed_steps']:
        st.success("✅ Steg 7 slutfört")
        result_data = steps_state['step_data'][7]
        used_wacc = result_data.get('used_wacc', 0.0453)
        
        # Visa vilken WACC som användes
        st.info(f"Beräkning genomförd med WACC: {used_wacc:.4f}")
        
        # KPI för företaget
        col1, col2 = st.columns(2)
        with col1:
            ret_ord_total = sum(result_data.get(f'return_ord_{t}', 0) for t in range(229, 237))
            st.metric("Total ordinarie avkastning (tkr)", f"{ret_ord_total:,.0f}")
        with col2:
            ret_tail_total = sum(result_data.get(f'return_tail_{t}', 0) for t in range(229, 237))
            st.metric("Total svansavkastning (tkr)", f"{ret_tail_total:,.0f}")


def run_company_step_8_compile(dmu_id: int, steps_state: dict, company_name: str):
    """Steg 8: Sammanställ kapitalkostnad för företaget - ANVÄNDER SAMMA LOGIK"""
    
    st.subheader(f"Steg 8: Sammanställning för {company_name}")
    st.write("Kombinerar avskrivningar och avkastning till total kapitalkostnad")
    
    if not (6 in steps_state['completed_steps'] and 7 in steps_state['completed_steps']):
        st.warning("Slutför först Steg 6 och 7")
        return
    
    # Kör beräkning - EXAKT SAMMA FUNKTION
    if st.button("Kör Steg 8: Sammanställning", key=f"step8_button_{dmu_id}"):
        with st.spinner(f"Sammanställer kapitalkostnad för {company_name}..."):
            try:
                dep_data = steps_state['step_data'][6]
                ret_data = steps_state['step_data'][7]
                # SAMMA FUNKTION som fungerande version
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
        st.success("✅ Steg 8 slutfört")
        result_data = steps_state['step_data'][8]
        
        # Huvudresultat för företaget
        total_capcost = result_data['capcost_sum'].sum()
        total_kapitalbindning = result_data['return_ord'].sum() + result_data['return_tail'].sum()
        total_kapitalforslitning = result_data['dep_ord'].sum() + result_data['dep_tail'].sum()
        
        st.markdown(f"#### Sammanställning för {company_name}")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total kapitalkostnad (tkr)", f"{total_capcost:,.0f}")
        with col2:
            st.metric("Total kapitalbindning (tkr)", f"{total_kapitalbindning:,.0f}")
        with col3:
            st.metric("Total kapitalförslitning (tkr)", f"{total_kapitalforslitning:,.0f}")
        
        # Breakdown per period
        with st.expander("Breakdown per tidsperiod"):
            st.dataframe(result_data, use_container_width=True)


def run_company_step_9_compare_facit(dmu_id: int, steps_state: dict, company_name: str):
    """Steg 9: Jämför med facit för företaget - ANVÄNDER SAMMA LOGIK"""
    
    st.subheader(f"Steg 9: Jämför med facit för {company_name}")
    
    if 8 not in steps_state['completed_steps']:
        st.warning("Slutför först Steg 8")
        return
    
    # Kolla om facit finns för denna DMU - SAMMA FUNKTION
    try:
        facit_data = load_facit_for_dmu(dmu_id)
        facit_available = not facit_data.empty
    except:
        facit_available = False
    
    if not facit_available:
        st.info(f"Facit-data är inte tillgänglig för DMU {dmu_id} i demonstrationsversionen")
        st.write("Detta betyder inte att beräkningarna är felaktiga - bara att vi inte har referensdata att jämföra med.")
        return
    
    if st.button("Ladda och jämför facit", key=f"step9_button_{dmu_id}"):
        with st.spinner("Laddar facit och jämför..."):
            try:
                calculated_data = steps_state['step_data'][8]
                # SAMMA FUNKTION som fungerande version
                facit_data = load_facit_for_dmu(dmu_id)
                
                if facit_data.empty:
                    st.error("Ingen facit-data kunde laddas för ditt företag")
                    return
                
                # Jämför - samma logik
                calc_total = calculated_data['capcost_sum'].sum()
                facit_total = facit_data['capcost_sum'].sum() if 'capcost_sum' in facit_data.columns else 0
                
                comparison = {
                    'calculated_total': calc_total,
                    'facit_total': facit_total,
                    'dmu_id': dmu_id,
                    'company_name': company_name
                }
                
                steps_state['step_data'][9] = comparison
                steps_state['completed_steps'].add(9)
                st.success("Steg 9 slutfört!")
                st.rerun()
            except Exception as e:
                st.error(f"Fel i steg 9: {e}")
                st.exception(e)
    
    # Visa jämförelse
    if 9 in steps_state['completed_steps']:
        st.success("✅ Steg 9 slutfört")
        comparison = steps_state['step_data'][9]
        
        # Huvudresultat för företaget
        delta = comparison['calculated_total'] - comparison['facit_total']
        delta_pct = (delta / comparison['facit_total'] * 100) if comparison['facit_total'] != 0 else 0
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Beräknat total", f"{comparison['calculated_total']:,.0f} tkr")
        with col2:
            st.metric("Facit total", f"{comparison['facit_total']:,.0f} tkr")
        with col3:
            st.metric("Differens", f"{delta:+,.0f} tkr", delta=f"{delta_pct:+.3f}%")
        
        # Toleransanalys
        tolerance_tkr = st.number_input("Tolerans (tkr)", min_value=0.0, value=1.0, step=0.1)
        abs_delta = abs(delta)
        
        if abs_delta <= tolerance_tkr:
            st.success(f"✅ Beräkning OK! Differens {abs_delta:,.1f} tkr ligger inom tolerans {tolerance_tkr} tkr")
        else:
            st.warning(f"⚠️ Differens {abs_delta:,.1f} tkr överskrider tolerans {tolerance_tkr} tkr")


# Huvudfunktion som kallas från pages
if __name__ == "__main__":
    show_foretag_berakningskedja()


# Logga ut
st.sidebar.markdown("---")
if st.button("Logga ut", key="logout_berakningskedja"):
    st.session_state.access_granted = False
    st.session_state.current_user = None
    st.session_state.user_role = None
    st.session_state.user_dmu = None
    st.rerun()
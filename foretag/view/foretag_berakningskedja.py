# foretag_berakningskedja.py
# Företagsspecifik stegvis beräkningskedja för kapitalkostnader
# UPPDATERAD: Använder core-moduler för backend-logik

import streamlit as st
import pandas as pd
import numpy as np
import json
import os
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List
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

from intaktsram.app.data_loader import get_company_display_name

from kapitalbas.beräkningsfiler.Beräkningskedja_capcost.data_upload_validator import (
    get_validated_data_for_berakningskedja, 
    apply_lifetime_scenario
)

# Importera beräkningsfunktioner från beräkningskedja
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

# Importera från core-moduler
from core.calculations import (
    R_OLD, YEAR_TO_CODES,
    EiWaccInputs, ei_wacc_real_pre_tax
)
from core.dmu_aggregation import (
    aggregate_to_dmu,
    check_year_completeness
)
from core.export_builders import (
    build_dea_export_table,
    apply_concession_adjustments
)
from core.export_writers import write_dea_export, write_ir_export

# Behåll UI-funktion från översikt.py
from kapitalbas.visualiseringsfiler.översikt import _render_methodology_info

# Autentisering
if "access_granted" not in st.session_state or not st.session_state.access_granted:
    st.stop()

if st.session_state.user_role != "company":
    st.error("Denna sida är endast tillgänglig för företagsanvändare")
    st.stop()


def show_foretag_berakningskedja():
    """Huvudfunktion för företagsspecifik beräkningskedja"""
    
    # Hämta företagsinformation
    user_dmu = get_user_dmu()
    company_info = load_reconciliation_foretag_info()
    company_name = company_info.get('company_name', 'Ditt företag')
    
    if user_dmu is None:
        st.error("Ingen DMU hittades för inloggad användare")
        return
    
    st.markdown(f"### Beräkningskedja för kapitalkostnader som går in i intäktsramen")
    
    # Validera data
    validation = validate_company_data()
    if not validation['capcost_data_available']:
        st.error("Kunde inte ladda data för beräkningskedjan")
        with st.expander("Debug-information"):
            st.json(validation)
        return
    
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
    step_tabs = st.tabs([
        "Steg 1: Åldrar & NUAV",
        "Steg 2: Avskrivningar", 
        "WACC-kalkylator",
        "Steg 3: Avkastning",
        "Steg 4: Sammanställning",
        "DEA-export"
    ])
    
    with step_tabs[0]:
        run_company_step_1_ages_nuav(user_dmu, steps_state, company_name)

    with step_tabs[1]:
        run_company_step_2_depreciation(user_dmu, steps_state, company_name)
    
    with step_tabs[2]:
        run_company_wacc_calculator(company_name)
    
    with step_tabs[3]:
        run_company_step_3_returns(user_dmu, steps_state, company_name)
    
    with step_tabs[4]:
        run_company_step_4_compile_and_validate(user_dmu, steps_state, company_name)
    
    with step_tabs[5]:
        run_company_dea_export(user_dmu, steps_state, company_name)


def run_company_step_1_ages_nuav(dmu_id: int, steps_state: dict, company_name: str):
    """Steg 1: Beräkna åldrar och NUAV-värden för företaget"""
    st.write("Beräknar komponenternas ålder och nuanskaffningsvärden för varje tidsperiod (229-236)")

    capbase_data, is_custom_data = get_validated_data_for_berakningskedja(
        default_loader_func=lambda: load_dmu_capbase_a(dmu_id)
    )
    if capbase_data is None:
        return

    capbase_data = apply_lifetime_scenario(capbase_data)
    
    # Kör beräkning
    if st.button("Kör Steg 1: Åldrar & NUAV", key=f"step1_button_{dmu_id}"):
        with st.spinner("Beräknar åldrar och NUAV för ditt företag..."):
            try:
                result_data = calculate_ages_and_nuav(capbase_data)
                steps_state['step_data'][1] = result_data
                steps_state['completed_steps'].add(1)
                steps_state['current_step'] = max(steps_state['current_step'], 1)
                st.success("Steg 1 slutfört!")
                st.rerun()
            except Exception as e:
                st.error(f"Fel i steg 1: {e}")
                st.exception(e)
    
    # Visa resultat om steg är slutfört
    if 1 in steps_state['completed_steps']:
        st.success("✓ Steg 1 slutfört")
        result_data = steps_state['step_data'][1]
        
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

def run_company_step_2_depreciation(dmu_id: int, steps_state: dict, company_name: str):
    """Steg 2: Beräkna avskrivningar för företaget"""
    
    st.subheader(f"Steg 2: Avskrivningar för {company_name}")
    st.write("Beräknar ordinarie och svansavskrivningar baserat på åldrar och livslängder")
    
    if 1 not in steps_state['completed_steps']:
        st.warning("Slutför steg 1 först")
        return
    
    # Visa metodik
    with st.expander("Avskrivningsmetodik"):
        st.write("**Ordinarie avskrivning:**")
        st.latex(r"dep\_ord = \frac{nuav\_ord}{ekdep}")
        st.write("**Svansavskrivning:**")
        st.latex(r"dep\_tail = \frac{nuav\_tail}{age\_reg}")
        st.write("Där age_reg justeras för udda åldrar")
    
    # Kör beräkning
    if st.button("Kör Steg 2: Avskrivningar", key=f"step2_button_{dmu_id}"):
        with st.spinner(f"Beräknar avskrivningar för {company_name}..."):
            try:
                input_data = steps_state['step_data'][1]
                result_data = calculate_depreciation_single_dmu(input_data)
                steps_state['step_data'][2] = result_data
                steps_state['completed_steps'].add(2)
                steps_state['current_step'] = max(steps_state['current_step'], 2)
                st.success("Steg 2 slutfört!")
                st.rerun()
            except Exception as e:
                st.error(f"Fel i steg 2: {e}")
                st.exception(e)
    
    # Visa resultat
    if 2 in steps_state['completed_steps']:
        st.success("✓ Steg 2 slutfört")
        result_data = steps_state['step_data'][2]
        
        # KPI för företaget
        col1, col2 = st.columns(2)
        with col1:
            dep_ord_total = sum(result_data.get(f'dep_ord_{t}', 0) for t in range(229, 237))
            st.metric("Total ordinarie avskrivning (tkr)", f"{dep_ord_total:,.0f}")
        with col2:
            dep_tail_total = sum(result_data.get(f'dep_tail_{t}', 0) for t in range(229, 237))
            st.metric("Total svansavskrivning (tkr)", f"{dep_tail_total:,.0f}")


def run_company_wacc_calculator(company_name: str):
    """WACC-kalkylator (importerad från översikt.py)"""
    
    st.subheader(f"WACC-kalkylator för {company_name}")
    st.write("Beräkna kalkylränta från grundparametrar enligt CAPM")
    
    # Använd samma defaults som i översikt.py
    defaults = {
        "rf_nom": 0.0287,
        "mrp": 0.0668,
        "infl": 0.0202,
        "credit": 0.0114,
        "debt_share": 0.36,
        "tax_rate": 0.206,
        "beta_mode": "β_A",
        "beta_a": 0.37,
        "beta_e": 0.54
    }
    
    # Initiera session state
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)
    st.session_state.setdefault("r_new", R_OLD)
    
    # Input-fält i tre kolumner
    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.number_input(
            "Riskfri ränta (nominell) Rf", 
            key="rf_nom", 
            step=0.0001, 
            format="%.4f",
            help="KI:s 9-årsprognos för 10-årig svensk statsobligation (nominell)."
        )
        st.number_input(
            "Marknadsriskpremie (nominell) MRP", 
            key="mrp", 
            step=0.0001, 
            format="%.4f",
            help="Långsiktig aktiemarknadspremie (nominell)."
        )
        st.number_input(
            "Inflation π (KPIF)", 
            key="infl", 
            step=0.0001, 
            format="%.4f",
            help="KPIF enligt KI:s 9-årsprognos."
        )

    with c2:
        st.number_input(
            "Kreditriskpremie (nominell)", 
            key="credit", 
            step=0.0001, 
            format="%.4f",
            help="Spread för lånat kapital."
        )
        st.number_input(
            "Skuldsättningsgrad S = D/(D+E)", 
            key="debt_share", 
            min_value=0.0, 
            max_value=0.95, 
            step=0.01, 
            format="%.2f",
            help="Vikt för skuld i WACC."
        )
        st.number_input(
            "Bolagsskatt T", 
            key="tax_rate", 
            min_value=0.0, 
            max_value=0.99, 
            step=0.001, 
            format="%.3f",
            help="Omräkning från efter skatt till före skatt."
        )

    with c3:
        st.radio(
            "Beta-inmatning", 
            ["β_A", "β_E"], 
            index=0, 
            key="beta_mode",
            help="Välj att ange tillgångsbeta (β_A) eller aktiebeta (β_E) direkt."
        )
        if st.session_state["beta_mode"] == "β_A":
            st.number_input(
                "β_A", 
                key="beta_a", 
                step=0.01, 
                format="%.2f",
                help="Tillgångsbeta (obelanad)."
            )
        else:
            st.number_input(
                "β_E", 
                key="beta_e", 
                step=0.01, 
                format="%.2f",
                help="Aktiebeta (belanad)."
            )

    # Beräkna WACC med core-funktion
    beta_a = st.session_state["beta_a"] if st.session_state["beta_mode"] == "β_A" else None
    beta_e = st.session_state["beta_e"] if st.session_state["beta_mode"] == "β_E" else None
    
    Re, Rd, Wn, Wr = ei_wacc_real_pre_tax(EiWaccInputs(
        rf_nominal=st.session_state["rf_nom"],
        mrp_nominal=st.session_state["mrp"],
        credit_spread=st.session_state["credit"],
        debt_share=st.session_state["debt_share"],
        tax_rate=st.session_state["tax_rate"],
        inflation=st.session_state["infl"],
        beta_asset=beta_a,
        beta_equity=beta_e
    ))

    # Visa resultat
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Re (nominell, efter skatt)", f"{Re*100:.2f} %")
    k2.metric("Rd (nominell, före skatt)", f"{Rd*100:.2f} %")
    k3.metric("WACC (nominell, före skatt)", f"{Wn*100:.2f} %")
    k4.metric("WACC (real, före skatt)", f"{Wr*100:.2f} %", help="Detta värde används i Steg 3")

    # Kontrollknappar
    def _reset_ei_defaults():
        for k, v in defaults.items():
            st.session_state[k] = v
        st.session_state["r_new"] = R_OLD

    cc1, cc2 = st.columns([1, 1])
    with cc1:
        if st.button("Använd denna kalkylränta i Steg 3", type="primary"):
            st.session_state["r_new"] = round(float(Wr), 4)
            st.success(f"Satt r_new = {st.session_state['r_new']:.4f} för användning i Steg 3")
    
    with cc2:
        st.button("Återställ till Ei-standard", on_click=_reset_ei_defaults)

    # Visa nuvarande värde som kommer användas i Steg 3
    current_r_new = st.session_state.get("r_new", R_OLD)
    if abs(current_r_new - Wr) > 1e-6:
        st.info(f"Aktuell WACC för Steg 3: {current_r_new:.4f} (klicka 'Använd denna kalkylränta' för att uppdatera)")
    else:
        st.success(f"✓ Denna WACC ({Wr:.4f}) kommer användas i Steg 3")

    # Metodikruta (importerad från översikt.py)
    _render_methodology_info()


def run_company_step_3_returns(dmu_id: int, steps_state: dict, company_name: str):
    """Steg 3: Beräkna avkastning för företaget"""
    
    st.subheader(f"Steg 3: Avkastning för {company_name}")
    st.write("Beräknar kapitalavkastning baserat på åldersjusterad kapitalbas")
    
    if 2 not in steps_state['completed_steps']:
        st.warning("Slutför steg 2 först")
        return

    # WACC-input
    current_wacc = round(float(st.number_input(
        "WACC (real, före skatt) för scenario",
        value=float(st.session_state.get("r_new", R_OLD)),
        step=0.0001, 
        format="%.4f",
        help="Använd värde från WACC-kalkylatorn eller ange direkt"
    )), 4)
    
    st.session_state["r_new"] = current_wacc
    
    # Visa källa och jämförelse med Ei-standard
    col1, col2 = st.columns(2)
    with col1:
        if abs(current_wacc - R_OLD) < 1e-6:
            st.info("Använder Ei-standard (4.53%)")
        else:
            st.info(f"Använder: {current_wacc*100:.2f}%")
    
    with col2:
        st.caption("Tips: Använd WACC-kalkylator-taben för att beräkna från grundparametrar")
    
    # Visa avkastningsmetodik
    with st.expander("Avkastningsmetodik"):
        st.write("**Ordinarie avkastning:**")
        st.latex(r"capbase\_left\_ord = \frac{(ekdep/2 - age\_return)}{ekdep/2} \times nuav\_ord")
        st.latex(r"return\_ord = WACC \times capbase\_left\_ord / 2")
        st.write("**Svansavkastning:**")
        st.latex(r"capbase\_left\_tail = \frac{nuav\_tail}{age\_return + 1}")
        st.latex(r"return\_tail = WACC \times capbase\_left\_tail / 2")
    
    # Kör avkastningsberäkning
    if st.button("Kör Steg 3: Avkastning", key=f"step3_button_{dmu_id}"):
        with st.spinner(f"Beräknar avkastning för {company_name} med WACC {current_wacc:.4f}..."):
            try:
                input_data = steps_state['step_data'][1]
                result_data = calculate_returns_single_dmu(input_data, interest_rate=current_wacc)
                steps_state['step_data'][3] = result_data
                steps_state['step_data'][3]['used_wacc'] = current_wacc
                steps_state['completed_steps'].add(3)
                steps_state['current_step'] = max(steps_state['current_step'], 3)
                st.success("Steg 3 slutfört!")
                st.rerun()
            except Exception as e:
                st.error(f"Fel i steg 3: {e}")
                st.exception(e)
    
    # Visa resultat
    if 3 in steps_state['completed_steps']:
        st.success("✓ Steg 3 slutfört")
        result_data = steps_state['step_data'][3]
        used_wacc = result_data.get('used_wacc', R_OLD)
        
        st.info(f"Beräkning genomförd med WACC: {used_wacc:.4f}")
        
        # KPI för företaget
        col1, col2 = st.columns(2)
        with col1:
            ret_ord_total = sum(result_data.get(f'return_ord_{t}', 0) for t in range(229, 237))
            st.metric("Total ordinarie avkastning (tkr)", f"{ret_ord_total:,.0f}")
        with col2:
            ret_tail_total = sum(result_data.get(f'return_tail_{t}', 0) for t in range(229, 237))
            st.metric("Total svansavkastning (tkr)", f"{ret_tail_total:,.0f}")


def run_company_step_4_compile_and_validate(dmu_id: int, steps_state: dict, company_name: str):
    """Steg 4: Sammanställ kapitalkostnad och validera mot facit + IR-export"""
    
    st.subheader(f"Steg 4: Sammanställning för {company_name}")
    st.write("Kombinerar avskrivningar och avkastning till total kapitalkostnad")
    
    if not (2 in steps_state['completed_steps'] and 3 in steps_state['completed_steps']):
        st.warning("Slutför steg 1, 2 och 3 först")
        return
    
    # Kör beräkning
    if st.button("Kör Steg 4: Sammanställning", key=f"step4_button_{dmu_id}"):
        with st.spinner(f"Sammanställer kapitalkostnad för {company_name}..."):
            try:
                dep_data = steps_state['step_data'][2]
                ret_data = steps_state['step_data'][3]
                result_data = compile_capcost_single_dmu(dep_data, ret_data, dmu_id)
                steps_state['step_data'][4] = result_data
                steps_state['completed_steps'].add(4)
                steps_state['current_step'] = max(steps_state['current_step'], 4)
                st.success("Steg 4 slutfört!")
                st.rerun()
            except Exception as e:
                st.error(f"Fel i steg 4: {e}")
                st.exception(e)
    
    # Visa resultat
    if 4 in steps_state['completed_steps']:
        st.success("✓ Steg 4 slutfört")
        result_data = steps_state['step_data'][4]
        
        # Beräkna KPIs
        calculated_kpis = {
            'capcost_sum': result_data['capcost_sum'].sum(),
            'dep_ord': result_data['dep_ord'].sum(),
            'dep_tail': result_data['dep_tail'].sum(),
            'return_ord': result_data['return_ord'].sum(),
            'return_tail': result_data['return_tail'].sum()
        }
        
        # Härledda KPIs
        calculated_kpis['total_kapitalforslitning'] = calculated_kpis['dep_ord'] + calculated_kpis['dep_tail']
        calculated_kpis['total_kapitalbindning'] = calculated_kpis['return_ord'] + calculated_kpis['return_tail']
        
        # Kontrollera facit-tillgänglighet
        try:
            facit_data = load_facit_for_dmu(dmu_id)
            facit_available = not facit_data.empty
        except:
            facit_available = False
        
        if not facit_available:
            # Visa resultat utan validering
            st.markdown(f"#### Sammanställning för {company_name}")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total kapitalkostnad (tkr)", f"{calculated_kpis['capcost_sum']:,.0f}")
            with col2:
                st.metric("Total kapitalbindning (tkr)", f"{calculated_kpis['total_kapitalbindning']:,.0f}")
            with col3:
                st.metric("Total kapitalförslitning (tkr)", f"{calculated_kpis['total_kapitalforslitning']:,.0f}")
            
            st.info(f"Hittar inte facit, visar endast beräknade värden för {company_name}")
    
        
        else:
            # Automatisk validering med facit
            with st.spinner("Jämför mot facit..."):
                # Beräkna facit-KPIs
                facit_kpis = {
                    'capcost_sum': facit_data['capcost_sum'].sum() if 'capcost_sum' in facit_data.columns else 0,
                    'dep_ord': facit_data['dep_ord'].sum() if 'dep_ord' in facit_data.columns else 0,
                    'dep_tail': facit_data['dep_tail'].sum() if 'dep_tail' in facit_data.columns else 0,
                    'return_ord': facit_data['return_ord'].sum() if 'return_ord' in facit_data.columns else 0,
                    'return_tail': facit_data['return_tail'].sum() if 'return_tail' in facit_data.columns else 0
                }
                
                # Härledda facit-KPIs
                facit_kpis['total_kapitalforslitning'] = facit_kpis['dep_ord'] + facit_kpis['dep_tail']
                facit_kpis['total_kapitalbindning'] = facit_kpis['return_ord'] + facit_kpis['return_tail']
                
                # KPI-jämförelse med färgkodning
                st.markdown(f"#### Skillnad mot baseline")
                
                kpi_labels = {
                    'capcost_sum': 'Total kapitalkostnad (tkr)',
                    'total_kapitalforslitning': 'Total kapitalförslitning (tkr)',
                    'total_kapitalbindning': 'Total kapitalbindning (tkr)', 
                    'dep_ord': 'Kapitalförslitning - ordinarie (tkr)',
                    'dep_tail': 'Kapitalförslitning - svans (tkr)',
                    'return_ord': 'Kapitalbindning - ordinarie (tkr)',
                    'return_tail': 'Kapitalbindning - svans (tkr)'
                }
                
                # Layout i 4 kolumner för kompakt visning av 7 KPIs
                row1_cols = st.columns(4)
                row2_cols = st.columns(3)
                all_cols = list(row1_cols) + list(row2_cols)
                
                for idx, (kpi, label) in enumerate(kpi_labels.items()):
                    calc_val = calculated_kpis[kpi]
                    facit_val = facit_kpis[kpi]
                    delta = calc_val - facit_val
                    
                    with all_cols[idx]:
                        # Färgkodning: Röd för högre, grön för lägre
                        if abs(delta) <= 1.0:  # Praktiskt noll
                            delta_color = "off"  # Ingen färg
                            delta_str = "≈0"
                        else:
                            delta_color = "inverse"  # Ger: röd↑ för +, grön↓ för -
                            delta_str = f"+{delta:,.0f}" if delta > 0 else f"{delta:,.0f}"
                        
                        st.metric(
                            label,
                            f"{calc_val:,.0f}",
                            delta=delta_str,
                            delta_color=delta_color
                        )
                
                # Spara jämförelse i session state för eventuell framtida användning
                comparison = {
                    'calculated_kpis': calculated_kpis,
                    'facit_kpis': facit_kpis,
                    'dmu_id': dmu_id,
                    'company_name': company_name
                }
                steps_state['step_data'][9] = comparison
                steps_state['completed_steps'].add(9)
        
        # IR-EXPORT SEKTION
        st.markdown("---")
        st.markdown("#### Exportera kapitalkostnader till IR-dekomposition" )
        
        # Export-förhandsvisning
        if st.button("Förhandsgranska IR-export", type="secondary"):
            try:
                ir_preview = prepare_ir_export_from_berakningskedja(steps_state, dmu_id, company_name)
                
                st.markdown("**Förhandsvisning av IR-export:**")
                display_cols = ['DMU', 'Företag', 'Kapitalkostnad_Ny', 'Avskrivningar_Ny', 'Avkastning_Ny', 'r_new']
                st.dataframe(ir_preview[display_cols], use_container_width=True, hide_index=True)
                
            except Exception as e:
                st.error(f"Förhandsvisning misslyckades: {e}")
        
        
        if st.button("Exportera till IR-dekomposition", type="primary"):
            try:
                ir_data = prepare_ir_export_from_berakningskedja(steps_state, dmu_id, company_name)
                ir_path = execute_ir_export(ir_data, company_name)
                st.success("IR-export slutförd!")
                st.caption(f"Exporterat till: {ir_path}")
                    
                with st.expander("Export-detaljer"):
                    st.write("**Exporterad data:**")
                    st.dataframe(ir_data, use_container_width=True, hide_index=True)
                    
            except Exception as e:
                st.error(f"IR-export misslyckades: {e}")
                import traceback
                with st.expander("Teknisk felinfo"):
                    st.code(traceback.format_exc())
        


def run_company_dea_export(dmu_id: int, steps_state: dict, company_name: str):
    """DEA-export för alla företag med metodologisk korrekthet"""
    
    st.subheader(f"DEA-export (alla företag)")
    st.write("Exportera WACC-scenarier för alla företag för att undvika snedvriden DEA")
    
    dea_wacc = st.number_input(
        "Ange WACC (real, före skatt) för DEA-scenario",
        min_value=0.0,
        max_value=0.15,
        value=float(st.session_state.get("r_new", R_OLD)),
        step=0.0001,
        format="%.4f",
    )
    
    # Förhandsvisning
    if st.button("Förhandsgranska DEA-export", type="secondary"):
        with st.spinner("Förbereder förhandsgranskning..."):
            try:
                preview_data = prepare_dea_export_preview(dea_wacc, dmu_id)
                
                st.markdown("**Förhandsvisning av DEA-export:**")
                
                # Visa sammanfattning
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Antal DMU", len(preview_data))
                with col2:
                    st.metric("WACC baseline", f"{R_OLD:.4f}")
                with col3:
                    st.metric("WACC scenario", f"{dea_wacc:.4f}")
                
                # Visa sample data
                if len(preview_data) > 0:
                    st.markdown("**Sample data (första 10 rader):**")
                    st.dataframe(preview_data.head(10), use_container_width=True, hide_index=True)
                
            except Exception as e:
                st.error(f"Förhandsvisning misslyckades: {e}")
    
    # Export-knapp
    st.markdown("---")
    if st.button("Exportera DEA-scenario (alla företag)", type="primary"):
        with st.spinner("Exporterar DEA-scenario för alla företag..."):
            try:
                dea_data, dea_tag = prepare_dea_export_all_companies(dea_wacc, dmu_id)
                dea_path = execute_dea_export(dea_data, dea_wacc)
                
                st.success("DEA-export slutförd!")
                st.caption(f"Exporterat till: {dea_path}")
                
                # Visa statistik
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Exporterade DMU", len(dea_data))
                with col2:
                    st.metric("WACC använd", f"{dea_wacc:.4f}")
                with col3:
                    st.metric("Metod", "WACC-skalning")
                
                
                with st.expander("Export-detaljer"):
                    st.write("**Exporterad data (första 10 rader):**")
                    st.dataframe(dea_data.head(10), use_container_width=True, hide_index=True)
                    
                    if len(dea_data) > 10:
                        st.caption(f"Visar 10 av {len(dea_data)} exporterade rader")
                
            except Exception as e:
                st.error(f"DEA-export misslyckades: {e}")
                import traceback
                with st.expander("Teknisk felinfo"):
                    st.code(traceback.format_exc())


# ========= HJÄLPFUNKTIONER FÖR EXPORT =========

def prepare_ir_export_from_berakningskedja(steps_state: dict, dmu_id: int, company_name: str) -> pd.DataFrame:
    """Förbereder IR-export från beräkningskedjans resultat"""
    
    if 4 not in steps_state['completed_steps']:
        raise ValueError("Steg 4 måste vara slutfört för export")
    
    if 3 not in steps_state['completed_steps']:
        raise ValueError("Steg 3 måste vara slutfört för att få WACC-värde")
    
    result_data = steps_state['step_data'][4]
    used_wacc = steps_state['step_data'][3].get('used_wacc', R_OLD)
    
    # Aggregera över hela perioden 2024-2027
    total_deps_ord = result_data['dep_ord'].sum()
    total_deps_tail = result_data['dep_tail'].sum()
    total_returns_ord = result_data['return_ord'].sum()
    total_returns_tail = result_data['return_tail'].sum()
    total_capcost = result_data['capcost_sum'].sum()
    
    # Formatera för IR
    from core.calculations import format_wacc_tag
    wacc_tag = format_wacc_tag(used_wacc)
    
    ir_export = pd.DataFrame({
        'DMU': [int(dmu_id)],
        'Företag': [str(company_name)],
        'Kapitalkostnad_Baseline': [float(total_capcost)],
        'Kapitalkostnad_Ny': [float(total_capcost)],
        'Avskrivningar_Ny': [float(total_deps_ord + total_deps_tail)],
        'Avkastning_Baseline': [float(total_returns_ord + total_returns_tail)],
        'Avkastning_Ny': [float(total_returns_ord + total_returns_tail)],
        'dep_ord_Ny': [float(total_deps_ord)],
        'dep_tail_Ny': [float(total_deps_tail)],
        'return_ord_Ny': [float(total_returns_ord)],
        'return_tail_Ny': [float(total_returns_tail)],
        'r_old': [float(R_OLD)],
        'r_new': [round(float(used_wacc), 4)],
        'price_year': [2022],
        'scenario_tag': [str(wacc_tag)],
        'source': ['berakningskedja'],
        'export_timestamp': [datetime.now().isoformat()]
    })
    
    # Applicera koncessionsjustering
    ir_export = apply_concession_adjustments(ir_export)
    
    return ir_export


def prepare_dea_export_preview(wacc: float, initiated_by_dmu: int) -> pd.DataFrame:
    """Förbereder förhandsvisning av DEA-export"""
    return prepare_dea_export_all_companies(wacc, initiated_by_dmu)[0]


def prepare_dea_export_all_companies(wacc: float, initiated_by_dmu: int) -> Tuple[pd.DataFrame, str]:
    """Bygger DEA-export för alla företag med core-funktioner"""
    
    try:
        from kapitalbas.datafiler.data_loader import load_capcost_a
        
        # Ladda ALL data
        df_all = load_capcost_a()
        if df_all.empty:
            raise ValueError("Kunde inte ladda kapitalkostnad-data")
        
        # Aggregera till DMU-nivå
        df_all_dmu = aggregate_to_dmu(
            df_all,
            recon_path="effektiviseringskrav/data/reconciliation_id_network_firm_dmu.csv",
            filter_regional=True
        )
        
        if df_all_dmu.empty:
            raise ValueError("DMU-aggregering misslyckades")
        
        # Filtrera till 2024
        df_2024 = df_all_dmu[df_all_dmu["time"].isin(YEAR_TO_CODES[2024])].copy()
        
        if df_2024.empty:
            raise ValueError("Ingen 2024-data för alla företag")
        
        # Kontrollera komplett H1+H2 data
        df_complete, incomplete = check_year_completeness(df_2024, 2024)
        
        if not incomplete.empty:
            st.warning(f"{len(incomplete)} DMU saknar H1 eller H2 för 2024 och exporteras inte.")
            df_2024 = df_complete
        
        if df_2024.empty:
            raise ValueError("Ingen DMU har komplett H1+H2 data för 2024")
        
        # Bygg DEA-export med core-funktion
        df_dea_export, df_dea_excl, dea_tag = build_dea_export_table(
            df_2024, 
            wacc,
            dea_base_path="effektiviseringskrav/data/Data_modeller.xlsx",
            exclude_missing_dmus=True
        )
        
        # Lägg till metadata
        df_dea_export['initiated_by_dmu'] = initiated_by_dmu
        df_dea_export['source'] = 'berakningskedja_wacc_scaling'
        df_dea_export['export_timestamp'] = datetime.now().isoformat()
        
        return df_dea_export, dea_tag
        
    except Exception as e:
        st.error(f"Fel vid byggande av DEA-export: {e}")
        raise


def execute_ir_export(ir_data: pd.DataFrame, company_name: str) -> str:
    """Utför IR-export med core-funktion"""
    
    try:
        org = get_user_org()
        wacc_tag = ir_data['scenario_tag'].iloc[0] if len(ir_data) > 0 else "0453"
        
        # Använd core-funktion
        data_path, meta_path = write_ir_export(ir_data, wacc_tag, org)
        
        return data_path
        
    except Exception as e:
        raise Exception(f"IR-export misslyckades: {e}")


def execute_dea_export(dea_data: pd.DataFrame, wacc: float) -> str:
    """Utför DEA-export med core-funktion"""
    
    try:
        org = get_user_org()
        from core.calculations import format_wacc_tag
        wacc_tag = format_wacc_tag(wacc)
        
        # Använd core-funktion
        data_path, meta_path = write_dea_export(dea_data, wacc_tag, org)
        
        return data_path
        
    except Exception as e:
        raise Exception(f"DEA-export misslyckades: {e}")


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
# foretag_berakningskedja.py
# Företagsspecifik stegvis beräkningskedja för kapitalkostnader
# UPPDATERAD: Med dedikerad WACC-beräkningstab och export-funktionalitet

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

from kapitalbas.beräkningsfiler.Beräkningskedja_capcost.data_upload_validator import (get_validated_data_for_berakningskedja, apply_lifetime_scenario)

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

# NYTT: Importera WACC-funktioner från översikt.py
from kapitalbas.visualiseringsfiler.översikt import (
    R_OLD,
    EiWaccInputs,
    ei_wacc_real_pre_tax,
    _render_methodology_info,
    _aggregate_to_dmu,
    _build_dea_export_table,
    YEAR_TO_CODES,
    apply_concession_adjustments
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
    
    # Initiera session state för steg
    session_key = f'company_steps_{user_dmu}'
    if session_key not in st.session_state:
        st.session_state[session_key] = {
            'current_step': 0,
            'step_data': {},
            'completed_steps': set()
        }
    
    steps_state = st.session_state[session_key]
    
    # Huvudtabs för beräkningssteg - UPPDATERAD: Lagt till DEA-export tab
    st.header("Beräkningssteg")
    
    step_tabs = st.tabs([
        "Steg 5: Åldrar & NUAV",
        "Steg 6: Avskrivningar", 
        "WACC-kalkylator",
        "Steg 7: Avkastning",
        "Steg 8: Sammanställning",
        "DEA-export"  # NY TAB
    ])
    
    with step_tabs[0]:
        run_company_step_5_ages_nuav(user_dmu, steps_state, company_name)

    with step_tabs[1]:
        run_company_step_6_depreciation(user_dmu, steps_state, company_name)
    
    with step_tabs[2]:
        run_company_wacc_calculator(company_name)
    
    with step_tabs[3]:
        run_company_step_7_returns(user_dmu, steps_state, company_name)
    
    with step_tabs[4]:
        run_company_step_8_compile_and_validate(user_dmu, steps_state, company_name)
    
    with step_tabs[5]:  # NY TAB
        run_company_dea_export(user_dmu, steps_state, company_name)

def run_company_step_5_ages_nuav(dmu_id: int, steps_state: dict, company_name: str):
    """Steg 5: Beräkna åldrar och NUAV-värden för företaget - ANVÄNDER SAMMA LOGIK"""
    
    st.subheader(f"Steg 5: Åldrar och NUAV-värden för {company_name}")
    st.write("Beräknar komponenternas ålder och nuanskaffningsvärden för varje tidsperiod (229-236)")

    capbase_data, is_custom_data = get_validated_data_for_berakningskedja(
        default_loader_func=lambda: load_dmu_capbase_a(dmu_id)
    )
    if capbase_data is None:
        return  # Väntar på giltig data

    capbase_data = apply_lifetime_scenario(capbase_data)
    
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
        
        # Förbättrad analys med visualiseringar
        with st.expander("Analys - åldersfördelning för ditt företag"):
            if 'age_component_229' in result_data.columns and 'cat_encode' in result_data.columns:
                
                # Histogram över åldersfördelning per kategori (använder 2024H1 som referens)
                fig_age = px.histogram(
                    result_data, 
                    x='age_component_229', 
                    color='cat_encode',
                    title=f'Åldersfördelning per komponentkategori 2024 - {company_name}',
                    labels={'age_component_229': 'Ålder (år)', 'count': 'Antal komponenter'},
                    nbins=20
                )
                fig_age.update_layout(height=400)
                st.plotly_chart(fig_age, use_container_width=True)
                
                # Andel ordinarie vs svans per kategori (kombinerat för hela 2024)
                if all(col in result_data.columns for col in ['nuav_ord_229', 'nuav_tail_229', 'nuav_ord_230', 'nuav_tail_230']):
                    # Beräkna andelar per kategori för hela 2024 (H1 + H2)
                    share_analysis = result_data.groupby('cat_encode').agg({
                        'nuav_ord_229': 'sum',
                        'nuav_tail_229': 'sum',
                        'nuav_ord_230': 'sum', 
                        'nuav_tail_230': 'sum'
                    }).reset_index()
                    
                    # Summera H1 + H2 för hela 2024
                    share_analysis['nuav_ord_2024'] = share_analysis['nuav_ord_229'] + share_analysis['nuav_ord_230']
                    share_analysis['nuav_tail_2024'] = share_analysis['nuav_tail_229'] + share_analysis['nuav_tail_230']
                    share_analysis['total_nuav_2024'] = share_analysis['nuav_ord_2024'] + share_analysis['nuav_tail_2024']
                    
                    # Filtrera bort kategorier utan NUAV
                    share_analysis = share_analysis[share_analysis['total_nuav_2024'] > 0]
                    
                    if not share_analysis.empty:
                        share_analysis['andel_ordinarie'] = (share_analysis['nuav_ord_2024'] / share_analysis['total_nuav_2024'] * 100).round(1)
                        share_analysis['andel_svans'] = (share_analysis['nuav_tail_2024'] / share_analysis['total_nuav_2024'] * 100).round(1)
                        
                        # Stacked bar chart för andelar
                        fig_share = px.bar(
                            share_analysis,
                            x='cat_encode',
                            y=['andel_ordinarie', 'andel_svans'],
                            title=f'Andel ordinarie vs svans per komponentkategori 2024 - {company_name}',
                            labels={'value': 'Andel (%)', 'cat_encode': 'Komponentkategori'},
                            color_discrete_map={'andel_ordinarie': '#2E8B57', 'andel_svans': '#FF6347'}
                        )
                        fig_share.update_layout(height=400, barmode='stack')
                        st.plotly_chart(fig_share, use_container_width=True)
                        
                        # Förklarande text
                        st.caption("Ordinarie (grön) = komponenter inom ekonomisk livslängd. Svans (röd) = komponenter utanför ekonomisk livslängd men inom maximal livslängd. Data för hela 2024 (H1+H2).")
                
                # Utveckling av andel svans över tid per kategori
                if all(f'nuav_ord_{t}' in result_data.columns and f'nuav_tail_{t}' in result_data.columns for t in range(229, 237)):
                    
                    # Beräkna andel svans för alla tidsperioder
                    trend_data = []
                    for t in range(229, 237):
                        period_data = result_data.groupby('cat_encode').agg({
                            f'nuav_ord_{t}': 'sum',
                            f'nuav_tail_{t}': 'sum'
                        }).reset_index()
                        
                        period_data['total_nuav'] = period_data[f'nuav_ord_{t}'] + period_data[f'nuav_tail_{t}']
                        period_data = period_data[period_data['total_nuav'] > 0]  # Filtrera kategorier utan NUAV
                        
                        if not period_data.empty:
                            period_data['andel_svans'] = (period_data[f'nuav_tail_{t}'] / period_data['total_nuav'] * 100).round(1)
                            period_data['period'] = t
                            period_data['period_label'] = f"{2024 + (t-229)//2}H{((t-229)%2)+1}"
                            
                            trend_data.append(period_data[['cat_encode', 'andel_svans', 'period', 'period_label']])
                    
                    if trend_data:
                        trend_df = pd.concat(trend_data, ignore_index=True)
                        
                        # Linjediagram över utvecklingen
                        fig_trend = px.line(
                            trend_df,
                            x='period_label',
                            y='andel_svans',
                            color='cat_encode',
                            title=f'Utveckling av svansandel över tid per kategori - {company_name}',
                            labels={'andel_svans': 'Svansandel (%)', 'period_label': 'Tidsperiod'},
                            markers=True
                        )
                        fig_trend.update_layout(height=400)
                        st.plotly_chart(fig_trend, use_container_width=True)
                        
                        st.caption("Visar hur stor andel av kapitalet som befinner sig i svansperiod över tiden. Stigande linjer indikerar åldrande komponentportfölj.")
                
                # Kvalitetskontroller
                st.markdown("---")
                st.write("**Kvalitetskontroller:**")
                
                quality_issues = []
                
                # Kontrollera negativa åldrar
                negative_ages = (result_data['age_component_229'] < 0).sum()
                if negative_ages > 0:
                    quality_issues.append(f"⚠️ {negative_ages} komponenter har negativ ålder")
                
                # Kontrollera extremt gamla komponenter
                very_old = (result_data['age_component_229'] > 50).sum()
                if very_old > 0:
                    quality_issues.append(f"ℹ️ {very_old} komponenter är äldre än 50 år")
                
                # Kontrollera komponenter utan NUAV
                zero_nuav = 0
                if 'nuav_ord_229' in result_data.columns and 'nuav_tail_229' in result_data.columns:
                    zero_nuav = ((result_data['nuav_ord_229'] == 0) & (result_data['nuav_tail_229'] == 0)).sum()
                    if zero_nuav > 0:
                        quality_issues.append(f"⚠️ {zero_nuav} komponenter har ingen NUAV-värdering")
                
                # Kontrollera livslängdskonsistens
                if 'ekdep' in result_data.columns and 'maxdep' in result_data.columns:
                    inconsistent_life = (result_data['ekdep'] > result_data['maxdep']).sum()
                    if inconsistent_life > 0:
                        quality_issues.append(f"⚠️ {inconsistent_life} komponenter har ekdep > maxdep")
                
                if quality_issues:
                    for issue in quality_issues:
                        st.write(issue)
                else:
                    st.success("✅ Inga kvalitetsproblem identifierade")


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
        
        # Visualiseringar för avskrivningsanalys
        with st.expander("Analys - avskrivningsfördelning för ditt företag"):
            # Hämta originaldata för kategorianalys
            input_data = steps_state['step_data'][5]
            
            if 'cat_encode' in input_data.columns:
                # 1. Andel ordinarie vs svans avskrivning per kategori (2024)
                if all(f'dep_ord_{t}' in result_data for t in [229, 230]) and all(f'dep_tail_{t}' in result_data for t in [229, 230]):
                    
                    # Skapa mock data per kategori baserat på input_data
                    # Vi behöver beräkna avskrivning per kategori från komponenter
                    dep_by_cat = []
                    for cat in input_data['cat_encode'].unique():
                        cat_data = input_data[input_data['cat_encode'] == cat]
                        
                        # Beräkna totala avskrivningar för denna kategori (2024)
                        dep_ord_2024 = 0
                        dep_tail_2024 = 0
                        
                        for t in [229, 230]:  # 2024H1 + 2024H2
                            if f'nuav_ord_{t}' in cat_data.columns and f'nuav_tail_{t}' in cat_data.columns:
                                # Ordinarie avskrivning
                                if 'ekdep' in cat_data.columns:
                                    dep_ord_2024 += (cat_data[f'nuav_ord_{t}'] / cat_data['ekdep']).sum() / 1000
                                
                                # Svansavskrivning (förenklad beräkning)
                                if f'age_component_{t}' in cat_data.columns:
                                    age_reg = cat_data[f'age_component_{t}'].copy()
                                    # Justera för udda åldrar
                                    mask = (age_reg % 2 == 1)
                                    age_reg.loc[mask] += age_reg.loc[mask].apply(lambda x: 1 if x > 0 else -1)
                                    
                                    # Säker division
                                    valid_age = age_reg != 0
                                    dep_tail_cat = 0
                                    if valid_age.any():
                                        dep_tail_cat = (cat_data.loc[valid_age, f'nuav_tail_{t}'] / age_reg.loc[valid_age]).sum() / 1000
                                    dep_tail_2024 += dep_tail_cat
                        
                        dep_by_cat.append({
                            'cat_encode': cat,
                            'dep_ord_2024': dep_ord_2024,
                            'dep_tail_2024': dep_tail_2024
                        })
                    
                    dep_analysis = pd.DataFrame(dep_by_cat)
                    dep_analysis['total_dep_2024'] = dep_analysis['dep_ord_2024'] + dep_analysis['dep_tail_2024']
                    
                    # Filtrera kategorier utan avskrivning
                    dep_analysis = dep_analysis[dep_analysis['total_dep_2024'] > 0.1]  # Minst 100 kr
                    
                    if not dep_analysis.empty:
                        dep_analysis['andel_ordinarie'] = (dep_analysis['dep_ord_2024'] / dep_analysis['total_dep_2024'] * 100).round(1)
                        dep_analysis['andel_svans'] = (dep_analysis['dep_tail_2024'] / dep_analysis['total_dep_2024'] * 100).round(1)
                        
                        # Stacked bar chart för avskrivningsandelar
                        fig_dep_share = px.bar(
                            dep_analysis,
                            x='cat_encode',
                            y=['andel_ordinarie', 'andel_svans'],
                            title=f'Andel ordinarie vs svans avskrivning per kategori 2024 - {company_name}',
                            labels={'value': 'Andel (%)', 'cat_encode': 'Komponentkategori'},
                            color_discrete_map={'andel_ordinarie': '#4CAF50', 'andel_svans': '#FF9800'}
                        )
                        fig_dep_share.update_layout(height=400, barmode='stack')
                        st.plotly_chart(fig_dep_share, use_container_width=True)
                        
                        st.caption("Ordinarie (grön) = avskrivning av komponenter inom ekonomisk livslängd. Svans (orange) = avskrivning av komponenter utanför ekonomisk livslängd.")
                
                # 2. Avskrivningsutveckling över tid per kategori
                dep_trend_data = []
                for t in range(229, 237):
                    period_label = f"{2024 + (t-229)//2}H{((t-229)%2)+1}"
                    
                    for cat in input_data['cat_encode'].unique():
                        cat_data = input_data[input_data['cat_encode'] == cat]
                        
                        # Beräkna total avskrivning för denna kategori och period
                        total_dep_cat = 0
                        
                        # Ordinarie
                        if f'nuav_ord_{t}' in cat_data.columns and 'ekdep' in cat_data.columns:
                            total_dep_cat += (cat_data[f'nuav_ord_{t}'] / cat_data['ekdep']).sum() / 1000
                        
                        # Svans
                        if f'nuav_tail_{t}' in cat_data.columns and f'age_component_{t}' in cat_data.columns:
                            age_reg = cat_data[f'age_component_{t}'].copy()
                            mask = (age_reg % 2 == 1)
                            age_reg.loc[mask] += age_reg.loc[mask].apply(lambda x: 1 if x > 0 else -1)
                            
                            valid_age = age_reg != 0
                            if valid_age.any():
                                total_dep_cat += (cat_data.loc[valid_age, f'nuav_tail_{t}'] / age_reg.loc[valid_age]).sum() / 1000
                        
                        if total_dep_cat > 0.1:  # Bara kategorier med betydande avskrivning
                            dep_trend_data.append({
                                'cat_encode': cat,
                                'period_label': period_label,
                                'total_dep': total_dep_cat,
                                'period': t
                            })
                
                if dep_trend_data:
                    dep_trend_df = pd.DataFrame(dep_trend_data)
                    
                    # Linjediagram över avskrivningsutveckling
                    fig_dep_trend = px.line(
                        dep_trend_df,
                        x='period_label',
                        y='total_dep',
                        color='cat_encode',
                        title=f'Avskrivningsutveckling över tid per kategori - {company_name}',
                        labels={'total_dep': 'Total avskrivning (tkr)', 'period_label': 'Tidsperiod'},
                        markers=True
                    )
                    fig_dep_trend.update_layout(height=400)
                    st.plotly_chart(fig_dep_trend, use_container_width=True)
                    
                    st.caption("Visar hur total avskrivning (ordinarie + svans) utvecklas över regleringsperioden per komponentkategori.")


def run_company_wacc_calculator(company_name: str):
    """NY FUNKTION: Dedikerad WACC-kalkylator (importerad från översikt.py)"""
    
    st.subheader(f"WACC-kalkylator för {company_name}")
    st.write("Beräkna kalkylränta från grundparametrar enligt Ei:s metodik")
    
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
    
    # Input-fält i tre kolumner (samma layout som översikt.py)
    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.number_input(
            "Riskfri ränta (nominell) Rf", 
            key="rf_nom", 
            step=0.0001, 
            format="%.4f",
            help="KI:s 9-årsprognos för 10-årig svensk statsobligation (nominell). Ingår i både R_E och R_D."
        )
        st.number_input(
            "Marknadsriskpremie (nominell) MRP", 
            key="mrp", 
            step=0.0001, 
            format="%.4f",
            help="Långsiktig aktiemarknadspremie (nominell), baserad på PwC:s riskpremiestudier."
        )
        st.number_input(
            "Inflation π (KPIF)", 
            key="infl", 
            step=0.0001, 
            format="%.4f",
            help="KPIF enligt KI:s 9-årsprognos. Fisher-omräkning till real nivå."
        )

    with c2:
        st.number_input(
            "Kreditriskpremie (nominell)", 
            key="credit", 
            step=0.0001, 
            format="%.4f",
            help="Spread för lånat kapital (typiskt europeiska utilities BBB vs 10-årig Bund)."
        )
        st.number_input(
            "Skuldsättningsgrad S = D/(D+E)", 
            key="debt_share", 
            min_value=0.0, 
            max_value=0.95, 
            step=0.01, 
            format="%.2f",
            help="Vikt för skuld i WACC. Relation: D/E = S/(1−S)."
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
                help="Tillgångsbeta (obelanad). Omvandlas till aktiebeta med Hamada."
            )
        else:
            st.number_input(
                "β_E", 
                key="beta_e", 
                step=0.01, 
                format="%.2f",
                help="Aktiebeta (belanad). Används direkt i CAPM."
            )

    # Beräkna WACC med importerade funktioner
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
    k4.metric("WACC (real, före skatt)", f"{Wr*100:.2f} %", help="Detta värde används i Steg 7")

    # Kontrollknappar
    def _reset_ei_defaults():
        for k, v in defaults.items():
            st.session_state[k] = v
        st.session_state["r_new"] = R_OLD

    cc1, cc2 = st.columns([1, 1])
    with cc1:
        if st.button("Använd denna kalkylränta i Steg 7", type="primary"):
            st.session_state["r_new"] = round(float(Wr), 4)
            st.success(f"Satt r_new = {st.session_state['r_new']:.4f} för användning i Steg 7")
    
    with cc2:
        st.button("Återställ till Ei-standard", on_click=_reset_ei_defaults)

    # Visa nuvarande värde som kommer användas i Steg 7
    current_r_new = st.session_state.get("r_new", R_OLD)
    if abs(current_r_new - Wr) > 1e-6:
        st.info(f"📌 Aktuell WACC för Steg 7: {current_r_new:.4f} (klicka 'Använd denna kalkylränta' för att uppdatera)")
    else:
        st.success(f"✅ Denna WACC ({Wr:.4f}) kommer användas i Steg 7")

    # Metodikruta (importerad från översikt.py)
    _render_methodology_info()


def run_company_step_7_returns(dmu_id: int, steps_state: dict, company_name: str):
    """Steg 7: Beräkna avkastning för företaget - Med flexibel WACC-input som översikt.py"""
    
    st.subheader(f"Steg 7: Avkastning för {company_name}")
    st.write("Beräknar kapitalavkastning baserat på åldersjusterad kapitalbas")
    
    if 6 not in steps_state['completed_steps']:
        st.warning("Slutför först Steg 6")
        return

    # FLEXIBEL WACC-input (samma UI som översikt.py Tab 3)
    current_wacc = round(float(st.number_input(
        "WACC (real, före skatt) för scenario",
        value=float(st.session_state.get("r_new", R_OLD)),
        step=0.0001, 
        format="%.4f",
        help="Använd värde från WACC-kalkylatorn eller ange direkt"
    )), 4)
    
    # Uppdatera session state med det nya värdet
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
        used_wacc = result_data.get('used_wacc', R_OLD)
        
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
        
        # Visualiseringar för avkastningsanalys
        with st.expander("Analys - avkastning och kapitalbindning för ditt företag"):
            # Hämta originaldata för kategorianalys
            input_data = steps_state['step_data'][5]
            
            if 'cat_encode' in input_data.columns:
                # 1. Avkastning per kategori (2024)
                ret_by_cat_2024 = []
                cap_by_cat_all_periods = []
                
                for cat in input_data['cat_encode'].unique():
                    cat_data = input_data[input_data['cat_encode'] == cat]
                    
                    # Beräkna avkastning för 2024 (H1 + H2)
                    ret_ord_2024 = 0
                    ret_tail_2024 = 0
                    
                    # För kapitalbindning över alla perioder
                    for t in range(229, 237):
                        period_label = f"{2024 + (t-229)//2}H{((t-229)%2)+1}"
                        cap_ord_cat = 0
                        cap_tail_cat = 0
                        ret_ord_cat = 0
                        ret_tail_cat = 0
                        
                        if f'age_component_{t}' in cat_data.columns and f'nuav_ord_{t}' in cat_data.columns and f'nuav_tail_{t}' in cat_data.columns:
                            # Beräkna age_return
                            age_return = cat_data[f'age_component_{t}'].copy()
                            mask = (age_return % 2 == 1)
                            age_return.loc[mask] += age_return.loc[mask].apply(lambda x: 1 if x > 0 else -1)
                            age_return = age_return / 2 - 1
                            
                            if 'ekdep' in cat_data.columns:
                                ekdep2 = cat_data['ekdep'] / 2
                                
                                # Ordinarie kapitalbindning och avkastning
                                capbase_left_ord = ((ekdep2 - age_return) / ekdep2) * cat_data[f'nuav_ord_{t}']
                                capbase_left_ord = capbase_left_ord.where(age_return >= 0, 0)  # Sätt till 0 om age_return < 0
                                cap_ord_cat = capbase_left_ord.sum() / 1000
                                ret_ord_cat = (used_wacc * capbase_left_ord / 2).sum() / 1000
                                
                                # Svans kapitalbindning och avkastning
                                capbase_left_tail = cat_data[f'nuav_tail_{t}'] / (age_return + 1)
                                capbase_left_tail = capbase_left_tail.where((age_return + 1) != 0, 0)
                                cap_tail_cat = capbase_left_tail.sum() / 1000
                                ret_tail_cat = (used_wacc * capbase_left_tail / 2).sum() / 1000
                        
                        # Spara för 2024 (H1 + H2)
                        if t in [229, 230]:
                            ret_ord_2024 += ret_ord_cat
                            ret_tail_2024 += ret_tail_cat
                        
                        # Spara för kapitalbindningstrend
                        cap_by_cat_all_periods.append({
                            'cat_encode': cat,
                            'period_label': period_label,
                            'period': t,
                            'cap_bindning': cap_ord_cat + cap_tail_cat,
                            'avkastning': ret_ord_cat + ret_tail_cat
                        })
                    
                    ret_by_cat_2024.append({
                        'cat_encode': cat,
                        'ret_ord_2024': ret_ord_2024,
                        'ret_tail_2024': ret_tail_2024
                    })
                
                # Graf 1: Avkastning per kategori 2024
                ret_analysis = pd.DataFrame(ret_by_cat_2024)
                ret_analysis['total_ret_2024'] = ret_analysis['ret_ord_2024'] + ret_analysis['ret_tail_2024']
                ret_analysis = ret_analysis[ret_analysis['total_ret_2024'] > 0.1]  # Minst 100 kr
                
                if not ret_analysis.empty:
                    ret_analysis['andel_ordinarie'] = (ret_analysis['ret_ord_2024'] / ret_analysis['total_ret_2024'] * 100).round(1)
                    ret_analysis['andel_svans'] = (ret_analysis['ret_tail_2024'] / ret_analysis['total_ret_2024'] * 100).round(1)
                    
                    fig_ret_share = px.bar(
                        ret_analysis,
                        x='cat_encode',
                        y=['andel_ordinarie', 'andel_svans'],
                        title=f'Andel ordinarie vs svans avkastning per kategori 2024 - {company_name}',
                        labels={'value': 'Andel (%)', 'cat_encode': 'Komponentkategori'},
                        color_discrete_map={'andel_ordinarie': '#1E88E5', 'andel_svans': '#FFC107'}
                    )
                    fig_ret_share.update_layout(height=400, barmode='stack')
                    st.plotly_chart(fig_ret_share, use_container_width=True)
                    
                    st.caption("Ordinarie (blå) = avkastning på komponenter inom ekonomisk livslängd. Svans (gul) = avkastning på komponenter utanför ekonomisk livslängd.")
                
                # Graf 2 & 3: Kapitalbindning och avkastning över tid
                if cap_by_cat_all_periods:
                    trend_df = pd.DataFrame(cap_by_cat_all_periods)
                    
                    # Filtrera kategorier med betydande kapitalbindning
                    significant_cats = trend_df.groupby('cat_encode')['cap_bindning'].max()
                    significant_cats = significant_cats[significant_cats > 1.0].index  # Minst 1000 kr
                    trend_df = trend_df[trend_df['cat_encode'].isin(significant_cats)]
                    
                    if not trend_df.empty:
                        # Graf 2: Kapitalbindningsutveckling
                        fig_cap_trend = px.line(
                            trend_df,
                            x='period_label',
                            y='cap_bindning',
                            color='cat_encode',
                            title=f'Kapitalbindningsutveckling över tid per kategori - {company_name}',
                            labels={'cap_bindning': 'Kapitalbindning (tkr)', 'period_label': 'Tidsperiod'},
                            markers=True
                        )
                        fig_cap_trend.update_layout(height=400)
                        st.plotly_chart(fig_cap_trend, use_container_width=True)
                        
                        st.caption("Visar hur mycket kapital som är bundet i varje komponentkategori över tiden. Minskande kapitalbindning = åldrande komponenter.")
                        
                        # Graf 3: Avkastningsutveckling
                        fig_ret_trend = px.line(
                            trend_df,
                            x='period_label',
                            y='avkastning',
                            color='cat_encode',
                            title=f'Avkastningsutveckling över tid per kategori - {company_name}',
                            labels={'avkastning': 'Total avkastning (tkr)', 'period_label': 'Tidsperiod'},
                            markers=True
                        )
                        fig_ret_trend.update_layout(height=400)
                        st.plotly_chart(fig_ret_trend, use_container_width=True)
                        
                        st.caption(f"Visar hur avkastningen utvecklas över regleringsperioden (WACC: {used_wacc:.4f}). Avkastning = WACC × Kapitalbindning ÷ 2.")


def run_company_step_8_compile_and_validate(dmu_id: int, steps_state: dict, company_name: str):
    """Steg 8: Sammanställ kapitalkostnad och validera mot facit för företaget + IR-export"""
    
    st.subheader(f"Steg 8: Sammanställning för {company_name}")
    st.write("Kombinerar avskrivningar och avkastning till total kapitalkostnad och jämför mot facit")
    
    if not (6 in steps_state['completed_steps'] and 7 in steps_state['completed_steps']):
        st.warning("Slutför först Steg 6 och 7")
        return
    
    # Kör beräkning
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
    
    # Visa resultat och automatisk validering
    if 8 in steps_state['completed_steps']:
        st.success("✅ Steg 8 slutfört")
        result_data = steps_state['step_data'][8]
        
        # Beräkna alla KPIs
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
            
            st.info(f"Facit-data är inte tillgänglig för DMU {dmu_id} i demonstrationsversionen")
            
            with st.expander("Breakdown per tidsperiod"):
                st.dataframe(result_data, use_container_width=True)
        
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
        
        # NYT: IR-EXPORT SEKTION (FÖRENKLAD)
        st.markdown("---")
        st.markdown("#### IR-export (endast ditt företag)")
        st.write("Exportera detaljerad kapitalkostnad för IR-dekomposition")
        st.caption("Använder beräknad WACC från Steg 7")
        
        # Export-förhandsvisning (utan WACC-input)
        if st.button("🔍 Förhandsgranska IR-export", type="secondary"):
            try:
                ir_preview = prepare_ir_export_from_berakningskedja(steps_state, dmu_id, company_name)
                
                st.markdown("**Förhandsvisning av IR-export:**")
                display_cols = ['DMU', 'Företag', 'Kapitalkostnad_Ny', 'Avskrivningar_Ny', 'Avkastning_Ny', 'r_new']
                st.dataframe(ir_preview[display_cols], use_container_width=True, hide_index=True)
                
            except Exception as e:
                st.error(f"Förhandsvisning misslyckades: {e}")
        
        # Export-knapp (förenklad)
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📊 Exportera till IR-dekomposition", type="primary"):
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
        
        with col2:
            st.info("💡 Tips: Använd DEA-export tab för att exportera WACC-scenarier för alla företag")


def run_company_dea_export(dmu_id: int, steps_state: dict, company_name: str):
    """NYT: DEA-export för alla företag med metodologisk korrekthet"""
    
    st.subheader(f"DEA-export (alla företag)")
    st.write("Exportera WACC-scenarier för ALLA företag för metodologiskt korrekt effektivitetsanalys")
    
    # Förklaring
    st.info("""
    **Metodologisk viktighet:** DEA-analysen kräver att alla DMU:er justeras med samma WACC 
    för rättvis jämförelse. Om bara ditt företag får ny WACC medan andra behåller 4.53%, 
    blir effektivitetsjämförelsen snedvriden.
    """)
    
    # WACC-input
    st.markdown("#### WACC-scenario för alla företag")
    
    dea_wacc = st.number_input(
        "WACC för DEA-scenario (appliceras på ALLA DMU)",
        min_value=0.0,
        max_value=0.15,
        value=float(st.session_state.get("r_new", R_OLD)),
        step=0.0001,
        format="%.4f",
        help="Denna WACC appliceras på alla DMU:er för rättvis jämförelse"
    )
    
    # Avancerade inställningar
    with st.expander("Avancerade inställningar"):
        full_recalc = st.checkbox(
            "Fullständig omberäkning av alla DMU", 
            value=False,
            help="""
            - ✅ Markerad: Kör hela beräkningskedjan för alla DMU (exakt men långsam)
            - ❌ Ej markerad: Skala bara WACC på befintliga resultat (snabb men approximativ)
            """
        )
        
        if full_recalc:
            st.warning("⚠️ Fullständig omberäkning kan ta flera minuter för alla DMU")
            st.caption("Rekommenderas när andra parametrar än WACC ändrats i framtiden")
        else:
            st.info("ℹ️ Snabb WACC-skalning - avskrivningar förblir oförändrade")
            st.caption("Lämplig för nuvarande läge där bara WACC är justerbar")
    
    # Förhandsvisning
    if st.button("🔍 Förhandsgranska DEA-export", type="secondary"):
        with st.spinner("Förbereder förhandsvisning..."):
            try:
                preview_data = prepare_dea_export_preview(dea_wacc, full_recalc, dmu_id)
                
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
                    display_cols = ['DMU', 'Företag', 'CAPEX_2024_tkr', f'CAPEX_2024_wacc_{int(dea_wacc*10000)}_tkr', 'delta_tkr']
                    available_cols = [col for col in display_cols if col in preview_data.columns]
                    st.dataframe(preview_data[available_cols].head(10), use_container_width=True, hide_index=True)
                
            except Exception as e:
                st.error(f"Förhandsvisning misslyckades: {e}")
    
    # Export-knapp
    st.markdown("---")
    if st.button("📈 Exportera DEA-scenario (alla företag)", type="primary"):
        with st.spinner("Exporterar DEA-scenario för alla företag..."):
            try:
                dea_data = prepare_dea_export_all_companies(
                    dea_wacc, 
                    initiated_by_dmu=dmu_id,
                    full_recalc=full_recalc
                )
                
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
                    method = "Fullständig omberäkning" if full_recalc else "WACC-skalning"
                    st.metric("Metod", method)
                
                st.info("🔬 Nu kan DEA jämföra alla företag under samma WACC-förutsättningar")
                
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


def prepare_ir_export_from_berakningskedja(steps_state: dict, dmu_id: int, company_name: str) -> pd.DataFrame:
    """Förbereder IR-export från beräkningskedjans resultat (använder beräknad WACC från steg 7)"""
    
    if 8 not in steps_state['completed_steps']:
        raise ValueError("Steg 8 måste vara slutfört för export")
    
    if 7 not in steps_state['completed_steps']:
        raise ValueError("Steg 7 måste vara slutfört för att få WACC-värde")
    
    result_data = steps_state['step_data'][8]
    used_wacc = steps_state['step_data'][7].get('used_wacc', R_OLD)
    
    # Aggregera över hela perioden 2024-2027 (använder befintliga värden)
    total_deps_ord = result_data['dep_ord'].sum()
    total_deps_tail = result_data['dep_tail'].sum()
    total_returns_ord = result_data['return_ord'].sum()
    total_returns_tail = result_data['return_tail'].sum()
    total_capcost = result_data['capcost_sum'].sum()
    
    # Formatera för IR (samma struktur som kapital.py för koncessionsjustering)
    wacc_tag = f"{int(used_wacc * 10000)}"
    
    ir_export = pd.DataFrame({
        'DMU': [int(dmu_id)],
        'Företag': [str(company_name)],
        'Kapitalkostnad_Baseline': [(float(total_capcost))],  # Avrundning som kapital.py
        'Kapitalkostnad_Ny': [(float(total_capcost))],  # Samma värde eftersom vi använder beräknad WACC
        'Avskrivningar_Ny': [(float(total_deps_ord + total_deps_tail))],
        'Avkastning_Baseline': [(float(total_returns_ord + total_returns_tail))],
        'Avkastning_Ny': [(float(total_returns_ord + total_returns_tail))],  # Samma värde
        
        # KRITISKT: Lägg till detaljerade ord/tail-delar som apply_concession_adjustments() förväntar sig
        'dep_ord_Ny': [(float(total_deps_ord))],
        'dep_tail_Ny': [(float(total_deps_tail))],
        'return_ord_Ny': [(float(total_returns_ord))],
        'return_tail_Ny': [(float(total_returns_tail))],
        
        'r_old': [float(R_OLD)],
        'r_new': [round(float(used_wacc), 4)],  # Konsistent avrundning
        'price_year': [2022],
        'scenario_tag': [str(wacc_tag)],
        'source': ['berakningskedja'],
        'export_timestamp': [datetime.now().isoformat()]
    })
    
    # KRITISKT: Applicera koncessionsjustering (samma som kapital.py)
    ir_export = apply_concession_adjustments(ir_export)
    
    return ir_export


def prepare_dea_export_preview(wacc: float, full_recalc: bool, initiated_by_dmu: int) -> pd.DataFrame:
    """Förbereder förhandsvisning av DEA-export"""
    
    # För förhandsvisning, kör alltid snabb variant
    return prepare_dea_export_wacc_scaling(wacc, initiated_by_dmu)


def prepare_dea_export_all_companies(wacc: float, initiated_by_dmu: int, full_recalc: bool = False) -> pd.DataFrame:
    """DEA-export med val mellan skalning (snabb) eller fullständig omberäkning (framtidssäker)"""
    
    if full_recalc:
        # FRAMTIDA: Fullständig omberäkning för alla DMU
        return prepare_dea_export_full_recalculation(wacc, initiated_by_dmu)
    else:
        # NUVARANDE: Snabb WACC-skalning (återanvänder kapital.py logik)
        return prepare_dea_export_wacc_scaling(wacc, initiated_by_dmu)


def prepare_dea_export_wacc_scaling(wacc: float, initiated_by_dmu: int) -> pd.DataFrame:
    """Snabb WACC-skalning för nuvarande läge"""
    
    # Samma logik som kapital.py - ladda färdig data och skala
    from kapitalbas.datafiler.data_loader import load_capcost_a
    
    df_all = load_capcost_a()  # Färdiga resultat
    
    if df_all.empty:
        raise ValueError("Kunde inte ladda data för alla företag")
    
    # Aggregera till DMU-nivå
    df_all_dmu = _aggregate_to_dmu(df_all)
    
    # Filtrera till 2024
    df_2024 = df_all_dmu[df_all_dmu["time"].isin(YEAR_TO_CODES[2024])].copy()
    
    if df_2024.empty:
        raise ValueError("Ingen 2024-data för alla företag")
    
    # Kontrollera komplett H1+H2 data
    def _check_completeness(df):
        cnt = df.groupby("DMU")["time"].nunique().reset_index(name="n_halvår")
        incomplete = cnt[cnt["n_halvår"] < 2]
        if not incomplete.empty:
            st.warning(f"{len(incomplete)} DMU saknar H1 eller H2 för 2024")
        # Filtrera till kompletta DMU
        complete_dmus = cnt[cnt["n_halvår"] == 2]["DMU"]
        return df[df["DMU"].isin(complete_dmus)]
    
    df_2024_complete = _check_completeness(df_2024)
    
    # Använd befintlig logik från översikt.py
    df_dea_export, df_dea_excl, dea_tag = _build_dea_export_table(df_2024_complete, wacc)
    
    # Lägg till metadata
    df_dea_export['initiated_by_dmu'] = initiated_by_dmu
    df_dea_export['source'] = 'berakningskedja_wacc_scaling'
    df_dea_export['export_timestamp'] = datetime.now().isoformat()
    
    return df_dea_export


def prepare_dea_export_full_recalculation(wacc: float, initiated_by_dmu: int) -> pd.DataFrame:
    """FRAMTIDA: Fullständig omberäkning för alla DMU"""
    
    # Hämta alla DMU-id:n
    all_dmus = get_all_dmu_ids()
    
    all_results = []
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, dmu in enumerate(all_dmus):
        try:
            status_text.text(f"Beräknar DMU {dmu} ({i+1}/{len(all_dmus)})")
            progress_bar.progress((i + 1) / len(all_dmus))
            
            # Steg 5-8 för varje DMU med nya parametrar
            capbase_data = load_dmu_capbase_a(dmu)
            if capbase_data.empty:
                continue
                
            ages_result = calculate_ages_and_nuav(capbase_data)
            dep_result = calculate_depreciation_single_dmu(ages_result)
            ret_result = calculate_returns_single_dmu(ages_result, wacc)  # NY WACC
            final_result = compile_capcost_single_dmu(dep_result, ret_result, dmu)
            
            # Filtrera till 2024 och aggregera
            result_2024 = final_result[final_result['time'].isin([229, 230])]
            if not result_2024.empty:
                agg_result = {
                    'DMU': dmu,
                    'Företag': f'DMU_{dmu}',  # Placeholder - skulle behöva företagsnamn
                    'CAPEX_2024_baseline': result_2024['capcost_sum'].sum(),  # Skulle behöva baseline
                    'CAPEX_2024_new': result_2024['capcost_sum'].sum(),  # Redan med ny WACC
                    f'CAPEX_2024_wacc_{int(wacc*10000)}_tkr': result_2024['capcost_sum'].sum(),
                    'delta_tkr': 0,  # Skulle behöva baseline för att beräkna
                    'r_old': R_OLD,
                    'r_new': wacc,
                    'initiated_by_dmu': initiated_by_dmu,
                    'source': 'berakningskedja_full_recalc',
                    'export_timestamp': datetime.now().isoformat()
                }
                all_results.append(agg_result)
                
        except Exception as e:
            st.warning(f"Kunde inte beräkna DMU {dmu}: {e}")
            continue
    
    status_text.text("Slutfört!")
    progress_bar.progress(1.0)
    
    return pd.DataFrame(all_results)


def get_all_dmu_ids() -> List[int]:
    """Hämtar alla tillgängliga DMU-id:n"""
    try:
        from kapitalbas.datafiler.data_loader import load_capcost_a
        df_all = load_capcost_a()
        return sorted(df_all['DMU'].unique()) if not df_all.empty else []
    except:
        # Fallback - använd reconciliation data
        try:
            recon_path = "effektiviseringskrav/data/reconciliation_id_network_firm_dmu.csv"
            if Path(recon_path).exists():
                recon_df = pd.read_csv(recon_path)
                return sorted(recon_df['DMU'].unique())
        except:
            pass
        return []


# FIXAD EXPORT-FUNKTION MED RÄTT MAPPAR
def execute_ir_export(ir_data: pd.DataFrame, company_name: str) -> str:
    """Utför IR-export med samma mappstruktur som kapital.py"""
    
    # Använd samma struktur som kapital.py
    base_export_dir = "scenario/kapitalbas/exports_to_ir"
    
    # Skapa organisationsspecifik katalog (samma som kapital.py)
    org = get_user_org()
    export_dir = os.path.join(base_export_dir, org)
    os.makedirs(export_dir, exist_ok=True)
    
    # Filnamn med timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    wacc_tag = ir_data['scenario_tag'].iloc[0] if len(ir_data) > 0 else "0453"
    filename = f"ir_kapkost_wacc_{wacc_tag}_y2024_2027_berakningskedja_{timestamp}.parquet"
    filepath = os.path.join(export_dir, filename)
    
    # Exportera data
    ir_data.to_parquet(filepath, index=False)
    
    # Metadata (konvertera alla värden till JSON-kompatibla typer)
    meta_path = filepath.replace('.parquet', '.json')
    metadata = {
        "description": "IR-export från beräkningskedja",
        "organization": str(org),
        "company": str(company_name),
        "dmu": int(ir_data['DMU'].iloc[0]) if len(ir_data) > 0 else None,
        "wacc_used": float(ir_data['r_new'].iloc[0]) if len(ir_data) > 0 else None,
        "export_timestamp": datetime.now().isoformat(),
        "period": "2024-2027",
        "source": "foretag_berakningskedja",
        "price_year": 2022,
        "unit": "tkr"
    }
    
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    
    return filepath


# FIXAD DEA-EXPORT MED RÄTT MAPPAR
def execute_dea_export(dea_data: pd.DataFrame, wacc: float) -> str:
    """Utför DEA-export med samma mappstruktur som kapital.py"""
    
    # Använd samma struktur som kapital.py  
    base_export_dir = "scenario/kapitalbas/exports_to_dea"
    
    # Skapa organisationsspecifik katalog
    org = get_user_org()
    export_dir = os.path.join(base_export_dir, org)
    os.makedirs(export_dir, exist_ok=True)
    
    # Filnamn
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    wacc_tag = f"{int(wacc * 10000)}"
    filename = f"capex_wacc_{wacc_tag}_y2024_dmu_berakningskedja_{timestamp}.parquet"
    filepath = os.path.join(export_dir, filename)
    
    # Exportera data
    dea_data.to_parquet(filepath, index=False)
    
    # Metadata (konvertera alla värden till JSON-kompatibla typer)
    meta_path = filepath.replace('.parquet', '.json')
    metadata = {
        "description": "DEA-export från beräkningskedja - alla DMU med samma WACC",
        "organization": str(org),
        "initiated_by_dmu": int(get_user_dmu()),
        "total_dmu_count": int(len(dea_data)),
        "wacc_old": float(R_OLD),
        "wacc_new": float(wacc),
        "export_timestamp": datetime.now().isoformat(),
        "period": "2024",
        "source": "foretag_berakningskedja",
        "methodological_note": "Alla DMU får samma WACC-justering för rättvis DEA-jämförelse",
        "price_year": 2022,
        "unit": "tkr"
    }
    
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    
    return filepath


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
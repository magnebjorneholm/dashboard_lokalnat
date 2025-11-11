"""
Kapitalkostnad-tab med kedjestruktur
WACC → KENT (optional) → Applicera
"""

import streamlit as st
import pandas as pd
from datetime import datetime

from kapitalkostnad.backend.capbase_prep import (
    build_capbase_a_from_kent,
    validate_capbase_a
)

from kapitalkostnad.backend.parameter_adjustments import (
    apply_normvalue_adjustments,
    apply_lifetime_adjustments,
    render_normvalue_adjustment_ui,
    render_lifetime_adjustment_ui
)

from kapitalkostnad.backend.beräkningskedja import (
    calculate_ages_and_nuav,
    calculate_depreciation_single_dmu,
    calculate_returns_single_dmu,
    compile_capcost_single_dmu
)

from core.calculations import R_OLD, EiWaccInputs, ei_wacc_real_pre_tax
from core.session_utils import get_user_dmu

from intaktsram.backend.pending_changes_manager import (
    get_staged,
    set_staged,
    get_all_staged,
    has_staged_changes,
    count_staged_changes,
    commit_staged_changes,
    reset_all,
    get_active_value
)


def show_kapitalkostnad_tab(entity_data, scenario_metadata):
    """Huvudfunktion för kapitalkostnad-tab med kedjestruktur"""
    
    st.subheader("Kapitalkostnad")
    
    if not st.session_state.current_scenario_name:
        st.warning("Skapa ett case i Översikt-fliken först")
        return
    
    baseline_wacc = 0.0453
    baseline_avskrivningar = entity_data.get('Avskrivningar_Baseline', entity_data.get('Avskrivningar', 0))
    baseline_avkastning = entity_data.get('Avkastning_Baseline', entity_data.get('Avkastning', 0))
    baseline_kapitalkostnad = entity_data.get('Kapitalkostnad_Total_Baseline', entity_data.get('Kapitalkostnad_Total', 0))
    
    user_dmu = get_user_dmu()
    
    st.markdown("### 1. WACC Parameters (ID: 2.1-2.12)")
    wacc_calculated = render_wacc_section()
    
    st.markdown("---")
    
    st.markdown("### 2. Advanced: Asset Parameters (Variables from KENT)")
    st.caption("För fullständig omberäkning från KENT-inrapportering")
    
    kent_data = render_kent_section(user_dmu)
    
    st.markdown("---")
    
    render_apply_section(
        wacc_calculated=wacc_calculated,
        kent_data=kent_data,
        baseline_avskrivningar=baseline_avskrivningar,
        baseline_avkastning=baseline_avkastning,
        baseline_kapitalkostnad=baseline_kapitalkostnad,
        baseline_wacc=baseline_wacc,
        user_dmu=user_dmu
    )


def render_wacc_section():
    """WACC-beräkning från CAPM-komponenter"""
    
    st.caption("Beräkna WACC från CAPM-komponenter")
    
    defaults = {
        'rf_nom': 0.0287,
        'mrp': 0.0668,
        'infl': 0.0202,
        'credit': 0.0114,
        'debt_share': 0.36,
        'tax_rate': 0.206,
        'beta_mode': 'β_A',
        'beta_a': 0.37,
        'beta_e': 0.54
    }
    
    current_rf = get_active_value('kapitalkostnad', 'rf_nom', defaults['rf_nom'])
    current_mrp = get_active_value('kapitalkostnad', 'mrp', defaults['mrp'])
    current_infl = get_active_value('kapitalkostnad', 'infl', defaults['infl'])
    current_credit = get_active_value('kapitalkostnad', 'credit', defaults['credit'])
    current_debt_share = get_active_value('kapitalkostnad', 'debt_share', defaults['debt_share'])
    current_tax_rate = get_active_value('kapitalkostnad', 'tax_rate', defaults['tax_rate'])
    current_beta_mode = get_active_value('kapitalkostnad', 'beta_mode', defaults['beta_mode'])
    current_beta_a = get_active_value('kapitalkostnad', 'beta_a', defaults['beta_a'])
    current_beta_e = get_active_value('kapitalkostnad', 'beta_e', defaults['beta_e'])
    
    c1, c2, c3 = st.columns(3)
    
    with c1:
        new_rf = st.number_input(
            "Riskfri ränta (nominell) Rf (ID: 2.3)",
            value=float(current_rf),
            step=0.0001,
            format="%.4f",
            help="KI:s 9-årsprognos för 10-årig svensk statsobligation (nominell)",
            key="wacc_input_rf"
        )
        if new_rf != current_rf:
            set_staged('kapitalkostnad', 'rf_nom', new_rf)
        
        new_mrp = st.number_input(
            "Marknadsriskpremie (nominell) MRP (ID: 2.4)",
            value=float(current_mrp),
            step=0.0001,
            format="%.4f",
            help="Långsiktig aktiemarknadspremie (nominell)",
            key="wacc_input_mrp"
        )
        if new_mrp != current_mrp:
            set_staged('kapitalkostnad', 'mrp', new_mrp)
        
        new_infl = st.number_input(
            "Inflation π (KPIF) (ID: 2.7)",
            value=float(current_infl),
            step=0.0001,
            format="%.4f",
            help="KPIF enligt KI:s 9-årsprognos",
            key="wacc_input_infl"
        )
        if new_infl != current_infl:
            set_staged('kapitalkostnad', 'infl', new_infl)
    
    with c2:
        new_credit = st.number_input(
            "Kreditriskpremie (nominell) (ID: 2.5)",
            value=float(current_credit),
            step=0.0001,
            format="%.4f",
            help="Spread för lånat kapital",
            key="wacc_input_credit"
        )
        if new_credit != current_credit:
            set_staged('kapitalkostnad', 'credit', new_credit)
        
        new_debt_share = st.number_input(
            "Skuldsättningsgrad S = D/(D+E) (ID: 2.1)",
            value=float(current_debt_share),
            min_value=0.0,
            max_value=0.95,
            step=0.01,
            format="%.2f",
            help="Vikt för skuld i WACC",
            key="wacc_input_debt_share"
        )
        if new_debt_share != current_debt_share:
            set_staged('kapitalkostnad', 'debt_share', new_debt_share)
        
        new_tax_rate = st.number_input(
            "Bolagsskatt T (ID: 2.6)",
            value=float(current_tax_rate),
            min_value=0.0,
            max_value=0.99,
            step=0.001,
            format="%.3f",
            help="Omräkning från efter skatt till före skatt",
            key="wacc_input_tax_rate"
        )
        if new_tax_rate != current_tax_rate:
            set_staged('kapitalkostnad', 'tax_rate', new_tax_rate)
    
    with c3:
        new_beta_mode = st.radio(
            "Beta-inmatning",
            ["β_A", "β_E"],
            index=0 if current_beta_mode == "β_A" else 1,
            help="Välj att ange tillgångsbeta (β_A) eller aktiebeta (β_E) direkt",
            key="wacc_input_beta_mode"
        )
        if new_beta_mode != current_beta_mode:
            set_staged('kapitalkostnad', 'beta_mode', new_beta_mode)
        
        if new_beta_mode == "β_A":
            new_beta_a = st.number_input(
                "β_A (ID: 2.2)",
                value=float(current_beta_a),
                step=0.01,
                format="%.2f",
                help="Tillgångsbeta (obelanad)",
                key="wacc_input_beta_a"
            )
            if new_beta_a != current_beta_a:
                set_staged('kapitalkostnad', 'beta_a', new_beta_a)
            beta_e_for_calc = None
            beta_a_for_calc = new_beta_a
        else:
            new_beta_e = st.number_input(
                "β_E (ID: 2.8)",
                value=float(current_beta_e),
                step=0.01,
                format="%.2f",
                help="Aktiebeta (belanad)",
                key="wacc_input_beta_e"
            )
            if new_beta_e != current_beta_e:
                set_staged('kapitalkostnad', 'beta_e', new_beta_e)
            beta_a_for_calc = None
            beta_e_for_calc = new_beta_e
    
    Re, Rd, Wn, Wr = ei_wacc_real_pre_tax(EiWaccInputs(
        rf_nominal=new_rf,
        mrp_nominal=new_mrp,
        credit_spread=new_credit,
        debt_share=new_debt_share,
        tax_rate=new_tax_rate,
        inflation=new_infl,
        beta_asset=beta_a_for_calc,
        beta_equity=beta_e_for_calc
    ))
    
    st.markdown("---")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Re (nominell, efter skatt) (ID: 2.9)", f"{Re*100:.2f}%")
    k2.metric("Rd (nominell, före skatt) (ID: 2.10)", f"{Rd*100:.2f}%")
    k3.metric("WACC (nominell, före skatt) (ID: 2.11)", f"{Wn*100:.2f}%")
    k4.metric("WACC (real, före skatt) (ID: 2.12)", f"{Wr*100:.2f}%")
    
    set_staged('kapitalkostnad', 'wacc_calculated', Wr)
    
    return Wr


def render_kent_section(user_dmu):
    """KENT-parametrar sektion"""
    
    kent_file = st.file_uploader(
        "Ladda upp KENT-fil",
        type=['xlsx', 'xls'],
        help="Excel-fil från KENT-inrapportering"
    )
    
    if kent_file is None:
        st.info("Ladda upp KENT-fil för fullständig omberäkning från inrapporterad kapitalbas")
        return None
    
    file_changed = st.session_state.get('current_kent_file') != kent_file.name
    
    if 'capbase_a_processed' not in st.session_state or file_changed:
        with st.spinner("Bearbetar KENT-fil..."):
            try:
                capbase_a = build_capbase_a_from_kent(kent_file, network_id=user_dmu)
                st.session_state.capbase_a_processed = capbase_a
                st.session_state.current_kent_file = kent_file.name
                set_staged('kapitalkostnad', 'kent_file_name', kent_file.name)
            except Exception as e:
                st.error(f"Fel vid bearbetning av KENT-fil: {e}")
                return None
    else:
        capbase_a = st.session_state.capbase_a_processed
    
    st.success(f"KENT-fil bearbetad: {len(capbase_a)} komponenter")
    
    st.markdown("#### Normvärden")
    normvalue_adj = render_normvalue_adjustment_ui(capbase_a)
    if normvalue_adj:
        set_staged('kapitalkostnad', 'normvärden', normvalue_adj)
    
    st.markdown("#### Livslängder")
    lifetime_adj = render_lifetime_adjustment_ui(capbase_a)
    if lifetime_adj:
        set_staged('kapitalkostnad', 'livslängder', lifetime_adj)
    
    return {
        'capbase_a': capbase_a,
        'normvalue_adj': normvalue_adj,
        'lifetime_adj': lifetime_adj
    }


def render_apply_section(wacc_calculated, kent_data, baseline_avskrivningar, 
                         baseline_avkastning, baseline_kapitalkostnad, baseline_wacc, user_dmu):
    """Apply-sektion med intelligent metodval"""
    
    st.markdown("### 3. Applicera ändringar")
    
    staged_count = count_staged_changes('kapitalkostnad')
    
    if staged_count == 0:
        st.info("Inga ändringar att applicera. Justera parametrar ovan för att skapa ändringar.")
        return
    
    st.caption(f"**{staged_count}** osparade ändringar")
    
    method, method_description = determine_method(kent_data)
    
    st.info(f"**Metod:** {method_description}")
    
    if method == "wacc_scaling":
        delta_wacc = wacc_calculated - baseline_wacc
        estimated_change_pct = (delta_wacc / baseline_wacc) * 100
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric(
                "Baseline Kapitalkostnad",
                f"{baseline_kapitalkostnad:,.0f} kr",
                help="Nuvarande värde"
            )
        with col2:
            st.metric(
                "Estimerad förändring",
                f"{estimated_change_pct:+.1f}%",
                help="Baserat på WACC-differens"
            )
    else:
        st.caption("Full omberäkning från KENT-data med justerade parametrar")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Applicera ändringar", type="primary", use_container_width=True, key="apply_kapitalkostnad"):
            apply_changes(method, wacc_calculated, baseline_wacc, kent_data, user_dmu)
    
    with col2:
        if st.button("Återställ alla", use_container_width=True, key="reset_kapitalkostnad"):
            reset_all('kapitalkostnad')
            st.rerun()


def determine_method(kent_data):
    """Bestämmer vilken metod som ska användas baserat på staged changes"""
    
    staged = get_all_staged('kapitalkostnad')
    
    has_kent = kent_data is not None
    has_normvalue = 'normvärden' in staged and staged['normvärden'] is not None
    has_lifetime = 'livslängder' in staged and staged['livslängder'] is not None
    
    if has_kent or has_normvalue or has_lifetime:
        return "kent_full", "Full KENT-pipeline med parameterjusteringar"
    else:
        return "wacc_scaling", "Snabb skalning baserat på WACC-förändring"


def apply_changes(method, wacc_calculated, baseline_wacc, kent_data, user_dmu):
    """Applicerar ändringar baserat på vald metod"""
    
    with st.spinner("Applicerar ändringar..."):
        try:
            if method == "wacc_scaling":
                result = apply_wacc_scaling(wacc_calculated, baseline_wacc, user_dmu)
            else:
                result = apply_kent_calculation(wacc_calculated, kent_data, user_dmu)

            st.session_state.scenario_data['applied_modifications']['kapitalkostnad'] = {
                'source': 'wacc_scaling' if method == "wacc_scaling" else 'kent_full',
                'method': method,
                'metadata': {
                    'new_avskrivningar': result['Avskrivningar'],
                    'new_avkastning': result['Avkastning'],
                    'new_kapitalkostnad': result['Kapitalkostnad_Total'],
                    'scaling_factor': result.get('scaling_factor'),
                    'wacc_new': wacc_calculated,
                    'wacc_old': baseline_wacc,
                    'detailed_result': result.get('detailed_result')
                },
                'timestamp': datetime.now().isoformat()
            }
            
            commit_staged_changes('kapitalkostnad')
            
            st.success("Ändringar applicerade!")
            st.rerun()
            
        except Exception as e:
            st.error(f"Applicering misslyckades: {e}")
            import traceback
            st.error(traceback.format_exc())


def apply_wacc_scaling(new_wacc, baseline_wacc, user_dmu):
    """Snabb skalning av kapitalkostnad baserat på WACC-förändring"""
    
    baseline_df = st.session_state.scenario_data['baseline']
    entity_row = baseline_df[baseline_df['DMU'] == user_dmu].iloc[0]
    
    scaling_factor = new_wacc / baseline_wacc
    
    baseline_avskrivningar = entity_row['Avskrivningar_Baseline']
    baseline_avkastning = entity_row['Avkastning_Baseline']
    
    new_avskrivningar = baseline_avskrivningar
    new_avkastning = baseline_avkastning * scaling_factor
    new_kapitalkostnad = new_avskrivningar + new_avkastning
    
    return {
        'Kapitalkostnad_Total': new_kapitalkostnad,
        'Avskrivningar': new_avskrivningar,
        'Avkastning': new_avkastning,
        'scaling_factor': scaling_factor
    }


def apply_kent_calculation(wacc, kent_data, user_dmu):
    """Full KENT-beräkning med parameterjusteringar"""
    
    capbase_a = kent_data['capbase_a']
    normvalue_adj = kent_data['normvalue_adj']
    lifetime_adj = kent_data['lifetime_adj']
    
    adjusted_data = capbase_a.copy()
    
    if normvalue_adj:
        adjusted_data = apply_normvalue_adjustments(
            adjusted_data,
            normvalue_adj['adjustments'],
            level=normvalue_adj['level']
        )
    
    if lifetime_adj:
        adjusted_data = apply_lifetime_adjustments(
            adjusted_data,
            lifetime_adj['adjustments'],
            level=lifetime_adj['level']
        )
    
    step5_result = calculate_ages_and_nuav(adjusted_data)
    step6_result = calculate_depreciation_single_dmu(step5_result)
    step7_result = calculate_returns_single_dmu(step5_result, interest_rate=wacc)
    final_result = compile_capcost_single_dmu(step6_result, step7_result, user_dmu)
    
    total_capcost = final_result['capcost_sum'].sum()
    total_deps = final_result['dep_ord'].sum() + final_result['dep_tail'].sum()
    total_returns = final_result['return_ord'].sum() + final_result['return_tail'].sum()
    
    return {
        'Kapitalkostnad_Total': total_capcost,
        'Avskrivningar': total_deps,
        'Avkastning': total_returns,
        'detailed_result': final_result
    }
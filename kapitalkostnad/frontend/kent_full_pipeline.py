"""
kent_full_pipeline_ui.py - Komplett UI för KENT-import och beräkningskedja

Funktioner:
1. Ladda upp KENT Excel-fil
2. Justera parametrar (normvärden, livslängder, WACC)
3. Köra hela beräkningskedjan (steg 1-9)
4. Exportera till IR-dekomposition med fullständig metadata
"""

import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime
import json

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
from core.export_writers import write_ir_export
from core.session_utils import get_user_org

from core.data_loader_company import (
    get_user_dmu,
    load_reconciliation_foretag_info,
    validate_company_data
)

# Autentisering
if "access_granted" not in st.session_state or not st.session_state.access_granted:
    st.stop()

if st.session_state.user_role != "company":
    st.error("Denna sida är endast tillgänglig för företagsanvändare")
    st.stop()


def show_kent_full_pipeline():
    """Huvudfunktion för KENT full pipeline UI"""
    
    # Hämta företagsinformation automatiskt
    user_dmu = get_user_dmu()
    company_info = load_reconciliation_foretag_info()
    company_name = company_info.get('company_name', 'Ditt företag')
    
    if user_dmu is None:
        st.error("Ingen DMU hittades för inloggad användare")
        return
    
    # Validera data
    validation = validate_company_data()
    if not validation['capcost_data_available']:
        st.error("Kunde inte ladda data för beräkningskedjan")
        with st.expander("Debug-information"):
            st.json(validation)
        return
    
    st.markdown(f"## Kapitalkostnadsanalys för {company_name}")
    st.markdown("Ladda upp KENT-inrapporteringsmall och kör hela beräkningskedjan med anpassade parametrar.")
    
    # Steg 1: Upload KENT-fil
    st.markdown("### 1. Ladda upp KENT-fil")
    
    kent_file = st.file_uploader(
        "Välj KENT-fil",
        type=['xlsx', 'xls'],
    )
    
    if kent_file is None:
        st.info("Ladda upp en KENT Excel-fil för att börja")
        return
    
    # Steg 2: Generera capbase_a
    if 'capbase_a' not in st.session_state or st.session_state.get('current_file') != kent_file.name:
        with st.spinner("Bearbetar KENT-fil och bygger capbase_a..."):
            try:
                # Använd automatiskt hämtad DMU och företagsinfo
                capbase_a = build_capbase_a_from_kent(kent_file, network_id=user_dmu)
                
                st.session_state.capbase_a = capbase_a
                st.session_state.current_file = kent_file.name
                st.session_state.user_dmu = user_dmu
                st.session_state.company_name = company_name
                
                st.success(f"KENT-fil bearbetad: {len(capbase_a)} komponenter skapade")
                
            except Exception as e:
                st.error(f"Fel vid bearbetning av KENT-fil: {e}")
                with st.expander("Teknisk felinfo"):
                    st.exception(e)
                return
    else:
        capbase_a = st.session_state.capbase_a
        st.success(f"KENT-fil bearbetad: {len(capbase_a)} komponenter")
    
    # Visa preview av capbase_a
    with st.expander("Förhandsgranska capbase_a", expanded=False):
        st.markdown("**Sammanfattning:**")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Komponenter", len(capbase_a))
        with col2:
            st.metric("Kategorier", capbase_a['cat_encode'].nunique())
        with col3:
            total_nuav = capbase_a['nuav_2022'].sum()
            st.metric("Total NUAV (tkr)", f"{total_nuav:,.0f}")
        
        st.markdown("**Data (första 100 rader):**")
        st.dataframe(capbase_a.head(100), use_container_width=True, height=300)
    
    # Steg 3: Parameterjusteringar
    st.markdown("---")
    st.markdown("### 2. Justera parametrar (valfritt)")
    st.caption("Alla justeringar är valfria - lämna tom för att använda originalvärden från KENT")
    
    # Normvärdejustering
    normvalue_adj = render_normvalue_adjustment_ui(capbase_a)
    
    # Livslängdsjustering
    lifetime_adj = render_lifetime_adjustment_ui(capbase_a)
    
    # WACC-justering
    wacc = render_wacc_calculator()
    
    # Steg 4: Kör hela beräkningskedjan
    st.markdown("---")
    st.markdown("### 3. Kör beräkningskedja")
    
    if st.button("Kör hela beräkningskedjan (steg 1-9)", type="primary", use_container_width=True):
        
        with st.spinner("Kör beräkningar..."):
            try:
                adjusted_data = capbase_a.copy()
                
                # Applicera normvärdejusteringar
                if normvalue_adj:
                    st.info(f"Applicerar normvärdejusteringar på {normvalue_adj['level']}-nivå...")
                    adjusted_data = apply_normvalue_adjustments(
                        adjusted_data,
                        normvalue_adj['adjustments'],
                        level=normvalue_adj['level']
                    )
                
                # Applicera livslängdsjusteringar
                if lifetime_adj:
                    st.info(f"Applicerar livslängdsjusteringar på {lifetime_adj['level']}-nivå...")
                    adjusted_data = apply_lifetime_adjustments(
                        adjusted_data,
                        lifetime_adj['adjustments'],
                        level=lifetime_adj['level']
                    )
                
                # Steg 5: Åldrar och NUAV
                st.info("Steg 5: Beräknar åldrar och NUAV för perioder 229-236...")
                step5_result = calculate_ages_and_nuav(adjusted_data)
                
                # Steg 6: Avskrivningar
                st.info("Steg 6: Beräknar avskrivningar...")
                step6_result = calculate_depreciation_single_dmu(step5_result)
                
                # Steg 7: Avkastning
                st.info(f"Steg 7: Beräknar avkastning med WACC={wacc:.4f}...")
                step7_result = calculate_returns_single_dmu(step5_result, interest_rate=wacc)
                
                # Steg 8: Sammanställning
                st.info("Steg 8: Sammanställer kapitalkostnad...")
                dmu_id = st.session_state.user_dmu
                final_result = compile_capcost_single_dmu(step6_result, step7_result, dmu_id)
                
                # Spara resultat i session state
                st.session_state.calculation_result = final_result
                st.session_state.step6_result = step6_result
                st.session_state.step7_result = step7_result
                st.session_state.used_wacc = wacc
                st.session_state.normvalue_adjustments_applied = normvalue_adj
                st.session_state.lifetime_adjustments_applied = lifetime_adj
                
                st.success("Beräkningskedja slutförd!")
                
            except Exception as e:
                st.error(f"Fel under beräkning: {e}")
                with st.expander("Teknisk felinfo"):
                    st.exception(e)
                return
    
    # Visa resultat om beräkning slutförd
    if 'calculation_result' in st.session_state:
        st.markdown("---")
        st.markdown("### 4. Resultat")
        
        result = st.session_state.calculation_result
        
        # Beräkna totaler för perioden 2024-2027
        total_capcost = result['capcost_sum'].sum()
        total_deps = result['dep_ord'].sum() + result['dep_tail'].sum()
        total_returns = result['return_ord'].sum() + result['return_tail'].sum()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total kapitalkostnad (tkr)", f"{total_capcost:,.0f}")
        with col2:
            st.metric("Avskrivningar (tkr)", f"{total_deps:,.0f}")
        with col3:
            st.metric("Avkastning (tkr)", f"{total_returns:,.0f}")
        
        # Visa detaljer om justeringar
        with st.expander("Visa justeringsdetaljer", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**WACC:**")
                st.write(f"- Baseline: {R_OLD*100:.2f}%")
                st.write(f"- Scenario: {st.session_state.used_wacc*100:.2f}%")
            
            with col2:
                norm_adj = st.session_state.get('normvalue_adjustments_applied')
                life_adj = st.session_state.get('lifetime_adjustments_applied')
                
                st.markdown("**Parameterjusteringar:**")
                if norm_adj:
                    st.write(f"- Normvärden: {len(norm_adj['adjustments'])} ändringar på {norm_adj['level']}-nivå")
                else:
                    st.write("- Normvärden: Inga justeringar")
                
                if life_adj:
                    st.write(f"- Livslängder: {len(life_adj['adjustments'])} ändringar på {life_adj['level']}-nivå")
                else:
                    st.write("- Livslängder: Inga justeringar")
        
        # Export-sektion
        st.markdown("---")
        st.markdown("### 5. Exportera till Intäktsram")
        
        if st.button("Förhandsgranska IR-export", type="secondary"):
            try:
                ir_preview = prepare_ir_export_from_kent_pipeline()
                
                st.markdown("**Förhandsvisning av IR-export:**")
                display_cols = ['DMU', 'Företag', 'Kapitalkostnad_Ny', 'Avskrivningar_Ny', 'Avkastning_Ny', 'r_new']
                st.dataframe(ir_preview[display_cols], use_container_width=True, hide_index=True)
                
            except Exception as e:
                st.error(f"Förhandsvisning misslyckades: {e}")
        
        if st.button("Exportera till IR-dekomposition", type="primary"):
            try:
                ir_data = prepare_ir_export_from_kent_pipeline()
                ir_path = execute_ir_export_kent(ir_data)
                st.success("IR-export slutförd!")
                st.info(f"Data exporterad till: {ir_path}")
                st.info("Gå till Intäktsram-sidan för att importera detta scenario")
                
            except Exception as e:
                st.error(f"Export misslyckades: {e}")
                with st.expander("Teknisk felinfo"):
                    st.exception(e)


def render_wacc_calculator() -> float:
    """
    Renderar WACC-kalkylator baserad på CAPM-metodik.
    Returnerar beräknad WACC (real, före skatt).
    """
    
    with st.expander("Justera WACC", expanded=False):
        st.caption("Beräkna kalkylränta från grundparametrar enligt CAPM")
        
        # Ei-defaults enligt regelverket
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
        
        # Initiera session state med unique keys för kent pipeline
        for k, v in defaults.items():
            key = f"kent_wacc_{k}"
            if key not in st.session_state:
                st.session_state[key] = v
        
        # Input-fält i tre kolumner
        c1, c2, c3 = st.columns(3)
        
        with c1:
            rf_nom = st.number_input(
                "Riskfri ränta (nominell) Rf", 
                value=st.session_state["kent_wacc_rf_nom"],
                step=0.0001, 
                format="%.4f",
                help="KI:s 9-årsprognos för 10-årig svensk statsobligation (nominell)",
                key="kent_input_rf_nom"
            )
            st.session_state["kent_wacc_rf_nom"] = rf_nom
            
            mrp = st.number_input(
                "Marknadsriskpremie (nominell) MRP", 
                value=st.session_state["kent_wacc_mrp"],
                step=0.0001, 
                format="%.4f",
                help="Långsiktig aktiemarknadspremie (nominell)",
                key="kent_input_mrp"
            )
            st.session_state["kent_wacc_mrp"] = mrp
            
            infl = st.number_input(
                "Inflation π (KPIF)", 
                value=st.session_state["kent_wacc_infl"],
                step=0.0001, 
                format="%.4f",
                help="KPIF enligt KI:s 9-årsprognos",
                key="kent_input_infl"
            )
            st.session_state["kent_wacc_infl"] = infl

        with c2:
            credit = st.number_input(
                "Kreditriskpremie (nominell)", 
                value=st.session_state["kent_wacc_credit"],
                step=0.0001, 
                format="%.4f",
                help="Spread för lånat kapital",
                key="kent_input_credit"
            )
            st.session_state["kent_wacc_credit"] = credit
            
            debt_share = st.number_input(
                "Skuldsättningsgrad S = D/(D+E)", 
                value=st.session_state["kent_wacc_debt_share"],
                min_value=0.0, 
                max_value=0.95, 
                step=0.01, 
                format="%.2f",
                help="Vikt för skuld i WACC",
                key="kent_input_debt_share"
            )
            st.session_state["kent_wacc_debt_share"] = debt_share
            
            tax_rate = st.number_input(
                "Bolagsskatt T", 
                value=st.session_state["kent_wacc_tax_rate"],
                min_value=0.0, 
                max_value=0.99, 
                step=0.001, 
                format="%.3f",
                help="Omräkning från efter skatt till före skatt",
                key="kent_input_tax_rate"
            )
            st.session_state["kent_wacc_tax_rate"] = tax_rate

        with c3:
            beta_mode = st.radio(
                "Beta-inmatning", 
                ["β_A", "β_E"], 
                index=0 if st.session_state["kent_wacc_beta_mode"] == "β_A" else 1,
                help="Välj att ange tillgångsbeta (β_A) eller aktiebeta (β_E) direkt",
                key="kent_input_beta_mode"
            )
            st.session_state["kent_wacc_beta_mode"] = beta_mode
            
            if beta_mode == "β_A":
                beta_a = st.number_input(
                    "β_A", 
                    value=st.session_state["kent_wacc_beta_a"],
                    step=0.01, 
                    format="%.2f",
                    help="Tillgångsbeta (obelanad)",
                    key="kent_input_beta_a"
                )
                st.session_state["kent_wacc_beta_a"] = beta_a
                beta_e = None
            else:
                beta_e = st.number_input(
                    "β_E", 
                    value=st.session_state["kent_wacc_beta_e"],
                    step=0.01, 
                    format="%.2f",
                    help="Aktiebeta (belanad)",
                    key="kent_input_beta_e"
                )
                st.session_state["kent_wacc_beta_e"] = beta_e
                beta_a = None

        # Beräkna WACC automatiskt
        Re, Rd, Wn, Wr = ei_wacc_real_pre_tax(EiWaccInputs(
            rf_nominal=rf_nom,
            mrp_nominal=mrp,
            credit_spread=credit,
            debt_share=debt_share,
            tax_rate=tax_rate,
            inflation=infl,
            beta_asset=beta_a,
            beta_equity=beta_e
        ))

        # Visa resultat i metrics
        st.markdown("---")
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Re (nominell, efter skatt)", f"{Re*100:.2f}%")
        k2.metric("Rd (nominell, före skatt)", f"{Rd*100:.2f}%")
        k3.metric("WACC (nominell, före skatt)", f"{Wn*100:.2f}%")
        k4.metric("WACC (real, före skatt, används i beräkning)", f"{Wr*100:.2f}%")

        # Återställ-knapp
        def _reset_to_baseline():
            for k, v in defaults.items():
                st.session_state[f"kent_wacc_{k}"] = v
        
        if st.button("Återställ till 4.53%", key="kent_reset_wacc"):
            _reset_to_baseline()
            st.rerun()
    
    return Wr


def prepare_ir_export_from_kent_pipeline() -> pd.DataFrame:
    """
    Förbereder IR-export med fullständig metadata om justeringar
    """
    if 'calculation_result' not in st.session_state:
        raise ValueError("Ingen beräkning slutförd")
    
    result_data = st.session_state.calculation_result
    step6_result = st.session_state.step6_result
    step7_result = st.session_state.step7_result
    used_wacc = st.session_state.used_wacc
    dmu_id = st.session_state.user_dmu
    company_name = st.session_state.company_name
    
    # Aggregera över hela perioden 2024-2027
    total_deps_ord = result_data['dep_ord'].sum()
    total_deps_tail = result_data['dep_tail'].sum()
    total_returns_ord = result_data['return_ord'].sum()
    total_returns_tail = result_data['return_tail'].sum()
    total_capcost = result_data['capcost_sum'].sum()
    
    # Formatera för IR
    from core.calculations import format_wacc_tag
    wacc_tag = format_wacc_tag(used_wacc)
    
    # Bygg export DataFrame
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
        'source': ['kent_full_pipeline'],
        'export_timestamp': [datetime.now().isoformat()]
    })
    
    # Lägg till justeringsmetadata som attribut
    norm_adj = st.session_state.get('normvalue_adjustments_applied')
    life_adj = st.session_state.get('lifetime_adjustments_applied')
    
    adjustments_metadata = {
        'has_normvalue_adjustments': norm_adj is not None,
        'has_lifetime_adjustments': life_adj is not None
    }
    
    if norm_adj:
        adjustments_metadata['normvalue_adjustments'] = {
            'level': norm_adj['level'],
            'count': len(norm_adj['adjustments']),
            'details': norm_adj.get('changes', [])
        }
    
    if life_adj:
        adjustments_metadata['lifetime_adjustments'] = {
            'level': life_adj['level'],
            'count': len(life_adj['adjustments']),
            'details': life_adj.get('changes', [])
        }
    
    ir_export.attrs['adjustments_metadata'] = adjustments_metadata
    
    return ir_export


def execute_ir_export_kent(ir_data: pd.DataFrame) -> str:
    """Utför IR-export med utökad metadata"""
    
    try:
        org = get_user_org()
        wacc_tag = ir_data['scenario_tag'].iloc[0] if len(ir_data) > 0 else "0p0453"
        
        # Använd core-funktion för att skriva parquet och basmetadata
        data_path, meta_path = write_ir_export(ir_data, wacc_tag, org)
        
        # Läs befintlig metadata och utöka den
        with open(meta_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        # Lägg till justeringsmetadata
        adjustments_metadata = ir_data.attrs.get('adjustments_metadata', {})
        metadata['parameter_adjustments'] = adjustments_metadata
        
        # Skriv tillbaka utökad metadata
        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        return data_path
        
    except Exception as e:
        raise Exception(f"IR-export misslyckades: {e}")


if __name__ == "__main__":
    show_kent_full_pipeline()


# Logga ut
st.sidebar.markdown("---")
if st.button("Logga ut", key="logout_kent_pipeline"):
    st.session_state.access_granted = False
    st.session_state.current_user = None
    st.session_state.user_role = None
    st.session_state.user_dmu = None
    st.rerun()
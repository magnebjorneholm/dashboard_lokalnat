"""
kent_full_pipeline_ui.py - Komplett UI för KENT-import och beräkningskedja

Ett enkelt gränssnitt för att:
1. Ladda upp KENT Excel-fil
2. Justera parametrar (normvärden, livslängder, WACC)
3. Köra hela beräkningskedjan (steg 1-9)
4. Visa resultat
"""

import streamlit as st
import pandas as pd
from pathlib import Path

# Importera backend-funktioner
from kapitalbas.beräkningsfiler.Beräkningskedja_capcost.capbase_prep import (
    build_capbase_a_from_kent,
    validate_capbase_a
)

from kapitalbas.beräkningsfiler.Beräkningskedja_capcost.parameter_adjustments import (
    apply_normvalue_adjustments,
    apply_lifetime_adjustments,
    render_normvalue_adjustment_ui,
    render_lifetime_adjustment_ui
)

from kapitalbas.beräkningsfiler.Beräkningskedja_capcost.beräkningskedja import (
    calculate_ages_and_nuav,
    calculate_depreciation_single_dmu,
    calculate_returns_single_dmu,
    compile_capcost_single_dmu
)

from core.calculations import (
    R_OLD, 
    EiWaccInputs, 
    ei_wacc_real_pre_tax
)


def show_kent_full_pipeline():
    """Huvudfunktion för KENT full pipeline UI"""
    
    st.markdown("## Kapitalkostnadsanalys från KENT")
    st.markdown("Ladda upp KENT-inrapporteringsmall och kör hela beräkningskedjan med anpassade parametrar.")
    
    # Steg 1: Upload KENT-fil
    st.markdown("### 1. Ladda upp KENT-fil")
    
    kent_file = st.file_uploader(
        "Välj KENT Excel-fil (Intaktsram_kapitalbas_2024-2027.xlsx)",
        type=['xlsx', 'xls'],
        help="Ladda upp din ifyllda KENT-inrapporteringsmall"
    )
    
    if kent_file is None:
        st.info("👆 Ladda upp en KENT Excel-fil för att börja")
        return
    
    # Steg 2: Generera capbase_a
    if 'capbase_a' not in st.session_state or st.session_state.get('current_file') != kent_file.name:
        with st.spinner("Bearbetar KENT-fil och bygger capbase_a..."):
            try:
                # Be om network_id
                network_id = st.number_input(
                    "Ange nätverks-ID (id_network)",
                    min_value=1,
                    value=1,
                    step=1,
                    help="Numeriskt ID för detta nätverksföretag"
                )
                
                # Bygg capbase_a från KENT
                capbase_a = build_capbase_a_from_kent(kent_file, network_id=network_id)
                
                # Spara i session state
                st.session_state.capbase_a = capbase_a
                st.session_state.current_file = kent_file.name
                st.session_state.network_id = network_id
                
                st.success(f"✓ KENT-fil bearbetad: {len(capbase_a)} komponenter skapade")
                
            except Exception as e:
                st.error(f"Fel vid bearbetning av KENT-fil: {e}")
                with st.expander("Teknisk felinfo"):
                    st.exception(e)
                return
    else:
        capbase_a = st.session_state.capbase_a
        st.success(f"✓ KENT-fil bearbetad: {len(capbase_a)} komponenter")
    
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
    
    if st.button("🚀 Kör hela beräkningskedjan (steg 1-9)", type="primary", use_container_width=True):
        
        with st.spinner("Kör beräkningar..."):
            try:
                # Förbered data med justeringar
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
                network_id = st.session_state.network_id
                final_result = compile_capcost_single_dmu(step6_result, step7_result, network_id)
                
                # Spara resultat i session state
                st.session_state.calculation_result = final_result
                st.session_state.step6_result = step6_result
                st.session_state.step7_result = step7_result
                st.session_state.used_wacc = wacc
                
                st.success("✓ Beräkningskedja slutförd!")
                
            except Exception as e:
                st.error(f"Fel i beräkningskedjan: {e}")
                with st.expander("Teknisk felinfo"):
                    st.exception(e)
                return
    
    # Visa resultat om beräkning körts
    if 'calculation_result' in st.session_state:
        display_results(
            st.session_state.calculation_result,
            st.session_state.step6_result,
            st.session_state.step7_result,
            st.session_state.used_wacc
        )


def render_wacc_calculator() -> float:
    """
    Renderar WACC-kalkylator med CAPM-beräkning.
    Returnerar vald WACC (real, före skatt).
    """
    with st.expander("Justera WACC (kalkylränta)", expanded=False):
        st.markdown("### WACC-kalkylator")
        
        # Initiera session state för WACC
        st.session_state.setdefault("kent_wacc", R_OLD)
        
        # Välj inmatningsmetod
        input_method = st.radio(
            "Välj inmatningsmetod:",
            ["Direkt inmatning", "CAPM-kalkylator"],
            horizontal=True,
            help="Direkt: Ange WACC direkt. CAPM: Bygg upp från grundparametrar."
        )
        
        if input_method == "Direkt inmatning":
            st.write("Ange kalkylränta (WACC) direkt för kapitalbindning.")
            
            wacc_direct = st.number_input(
                "WACC (real, före skatt)",
                min_value=0.0,
                max_value=0.15,
                value=float(st.session_state.get("kent_wacc", R_OLD)),
                step=0.0001,
                format="%.4f",
                help="Weighted Average Cost of Capital - används i avkastningsberäkning",
                key="wacc_direct_input"
            )
            
            st.session_state["kent_wacc"] = round(float(wacc_direct), 4)
            
            if abs(wacc_direct - R_OLD) > 1e-6:
                st.success(f"✓ Använder WACC: {wacc_direct:.4f} ({wacc_direct*100:.2f}%)")
                st.warning("⚠️ Detta är ett scenario för intern analys")
            else:
                st.info(f"Använder Ei-standard: {wacc_direct:.4f} ({wacc_direct*100:.2f}%)")
            
            return wacc_direct
            
        else:  # CAPM-kalkylator
            st.write("Beräkna kalkylränta från grundparametrar enligt CAPM")
            
            # Defaults från Ei
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
            st.markdown("---")
            st.markdown("**Beräknade värden:**")
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Re (nominell, efter skatt)", f"{Re*100:.2f} %")
            k2.metric("Rd (nominell, före skatt)", f"{Rd*100:.2f} %")
            k3.metric("WACC (nominell, före skatt)", f"{Wn*100:.2f} %")
            k4.metric("WACC (real, före skatt)", f"{Wr*100:.2f} %", help="Detta värde används i beräkningen")
            
            # Kontrollknappar
            def _reset_ei_defaults():
                for k, v in defaults.items():
                    st.session_state[k] = v
                st.session_state["kent_wacc"] = R_OLD
            
            cc1, cc2 = st.columns([1, 1])
            with cc1:
                if st.button("Använd denna kalkylränta", type="primary", key="use_wacc_btn"):
                    st.session_state["kent_wacc"] = round(float(Wr), 4)
                    st.success(f"✓ Satt WACC = {st.session_state['kent_wacc']:.4f}")
            
            with cc2:
                st.button("Återställ till Ei-standard", on_click=_reset_ei_defaults, key="reset_wacc_btn")
            
            # Visa nuvarande värde
            current_wacc = st.session_state.get("kent_wacc", R_OLD)
            if abs(current_wacc - Wr) > 1e-6:
                st.info(f"Aktuell WACC för beräkning: {current_wacc:.4f} (klicka 'Använd denna kalkylränta' för att uppdatera)")
            else:
                st.success(f"✓ Denna WACC ({Wr:.4f}) kommer användas i beräkningen")
            
            # Metodikinfo
            with st.expander("Metodikbeskrivning", expanded=False):
                st.markdown("""
                **CAPM-baserad WACC-beräkning:**
                
                1. **Eget kapital-kostnad (Re):**
                   - Re = Rf + β × MRP + Kreditrisk
                   - Omräknas från nominell efter skatt till real före skatt
                
                2. **Lånat kapital-kostnad (Rd):**
                   - Rd = Rf + Kreditrisk
                   - Omräknas från nominell före skatt till real före skatt
                
                3. **WACC:**
                   - WACC = E/(E+D) × Re + D/(E+D) × Rd × (1-T)
                   - Där D/(E+D) = Skuldsättningsgrad
                
                4. **Real före skatt:**
                   - Fisher-ekvationen: (1 + r_real) = (1 + r_nominell) / (1 + inflation)
                   - Före skatt: r_före = r_efter / (1 - T)
                
                **Detta är Ei:s standardmetod för intäktsramereglering.**
                """)
            
            return current_wacc


def display_results(final_result, step6_result, step7_result, wacc):
    """Visar resultat från beräkningskedjan"""
    
    st.markdown("---")
    st.markdown("## 📊 Resultat")
    
    # KPI-sammanfattning
    st.markdown("### Kapitalkostnad per period")
    
    # Beräkna totaler
    total_capcost = final_result['capcost_sum'].sum()
    total_dep_ord = final_result['dep_ord'].sum()
    total_dep_tail = final_result['dep_tail'].sum()
    total_ret_ord = final_result['return_ord'].sum()
    total_ret_tail = final_result['return_tail'].sum()
    
    total_kapitalforslitning = total_dep_ord + total_dep_tail
    total_kapitalbindning = total_ret_ord + total_ret_tail
    
    # Visa KPIs
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total kapitalkostnad (tkr)", f"{total_capcost:,.0f}")
    with col2:
        st.metric("Total kapitalförslitning (tkr)", f"{total_kapitalforslitning:,.0f}")
    with col3:
        st.metric("Total kapitalbindning (tkr)", f"{total_kapitalbindning:,.0f}")
    
    # Detaljerad uppdelning
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Kapitalförslitning:**")
        st.metric("Ordinarie avskrivning", f"{total_dep_ord:,.0f} tkr")
        st.metric("Svansavskrivning", f"{total_dep_tail:,.0f} tkr")
    
    with col2:
        st.markdown("**Kapitalbindning:**")
        st.metric("Ordinarie avkastning", f"{total_ret_ord:,.0f} tkr")
        st.metric("Svansavkastning", f"{total_ret_tail:,.0f} tkr")
    
    st.info(f"Beräknat med WACC: {wacc:.4f} ({wacc*100:.2f}%)")
    
    # Detaljerad tabell per period
    with st.expander("Detaljerad tabell per period", expanded=True):
        st.dataframe(final_result, use_container_width=True, hide_index=True)
    
    # Export-möjlighet
    st.markdown("---")
    st.markdown("### Export")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Export som CSV
        csv = final_result.to_csv(index=False)
        st.download_button(
            label="📥 Ladda ner resultat (CSV)",
            data=csv,
            file_name="kapitalkostnad_resultat.csv",
            mime="text/csv"
        )
    
    with col2:
        # Export som Excel
        import io
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            final_result.to_excel(writer, sheet_name='Kapitalkostnad', index=False)
        
        st.download_button(
            label="📥 Ladda ner resultat (Excel)",
            data=buffer.getvalue(),
            file_name="kapitalkostnad_resultat.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )


if __name__ == "__main__":
    show_kent_full_pipeline()
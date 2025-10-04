# foretag/view/effektivitet.py
# Företagsspecifik vy för effektiviseringsanalys
# Fokus på företagets verkliga behov utan teknisk störning

import streamlit as st
import pandas as pd
import numpy as np
import io
from datetime import datetime
from pathlib import Path

# Backend imports
from effektiviseringskrav.backend.dea_model import run_dea_model
from effektiviseringskrav.backend.data_loader import merge_capex_scenario, load_data
from effektiviseringskrav.backend.ir_calculations import calculate_ir_paverkbara_from_file
from effektiviseringskrav.backend.ir_export import export_ir_paverkbara_scenario
from effektiviseringskrav.backend.spatial_analysis import calculate_company_neighbor_gap

# Frontend imports
from effektiviseringskrav.frontend.components import (
    display_efficiency_histogram,
    display_company_geographic_analysis
)

# Företagsspecifika funktioner
from foretag.app.kapitalbas_data_loader import (
    get_user_dmu,
    load_reconciliation_foretag_info
)

# Autentisering
if "access_granted" not in st.session_state or not st.session_state.access_granted:
    st.stop()

if st.session_state.user_role != "company":
    st.error("Denna sida är endast tillgänglig för företagsanvändare")
    st.stop()


def show_foretag_effektivitet():
    """Huvudfunktion för företagsspecifik effektivitetsanalys"""
    
    # Hämta företagsinformation
    user_dmu = get_user_dmu()
    company_info = load_reconciliation_foretag_info()
    
    if user_dmu is None:
        st.error("Ingen DMU hittades för inloggad användare")
        return
    
    company_name = company_info.get('company_name', 'Ditt företag')
    
    # Ladda DEA-dataset
    try:
        data_file = "effektiviseringskrav/data/Data_modeller.xlsx"
        df_full = load_data(data_file)
    except Exception as e:
        st.error(f"Kunde inte ladda DEA-data: {e}")
        return
    
    # Kontrollera att företaget finns i DEA-data
    if user_dmu not in df_full['DMU'].values:
        st.error(f"DMU {user_dmu} hittades inte i DEA-data")
        st.info("Detta kan betyda att ditt företag inte ingår i den aktuella effektivitetsanalysen")
        return
    
    # === HEADER ===
    st.header(f"Effektivitetsanalys - {company_name}")
    st.caption(f"DMU {user_dmu} • Analysera ditt företags effektivitet och beräkna påverkbara kostnader")
    
    # === DEA-PARAMETRAR ===
    df = df_full  # Använd full dataset för DEA-beräkningar
    
    st.sidebar.subheader("DEA-parametrar")
  
    # Försök merga CAPEX-scenario från Kapitalbas
    df, scen_info = merge_capex_scenario(df)

    if scen_info.get("found"):
        st.sidebar.success(f"WACC-scenario: {scen_info['tag'].replace('p','.')} • täckning {scen_info['coverage']:.0%}")
    else:
        st.sidebar.info("Inget CAPEX-scenario från Kapitalbas")

    # Input/Output val
    base_inputs = ["CAPEX", "OPEXp", "TOTEX"]
    all_inputs = [c for c in base_inputs if c in df.columns]
    all_outputs = ["CU", "MW", "NS", "MWhl", "MWhh"]

    # Lägg till scenario-kolumner
    if scen_info.get("found"):
        capex_wacc_col = scen_info.get("capex_col")
        totex_wacc_col = scen_info.get("totex_col")
        all_inputs += [c for c in [capex_wacc_col, totex_wacc_col] if c and c in df.columns]

    st.sidebar.caption(
        "**Input-alternativ:**\n"
        "• CAPEX + OPEXp: separata kostnadstyper\n"
        "• TOTEX: totalkostnad\n"
        "• _wacc_: scenario från Kapitalbas"
    )

    input_cols = st.sidebar.multiselect(
        "Välj inputvariabler", 
        all_inputs, 
        default=[c for c in ["CAPEX", "OPEXp"] if c in all_inputs]
    )

    # Validering av input-kombinationer
    if not validate_input_combinations(input_cols, scen_info, df):
        return

    output_cols = st.sidebar.multiselect("Välj outputvariabler", all_outputs, default=all_outputs)
    use_outlier_filter = st.sidebar.checkbox("Filtrera bort outliers före beräkning", value=True)

    if not input_cols or not output_cols:
        st.warning("Välj minst en input och en output för att köra modellen.")
        return

    # RTS och trunkering
    st.sidebar.caption("**Skalavkastning (RTS):**")
    dea_rts = st.sidebar.selectbox("RTS", ["crs", "vrs"], index=0, help="crs: Konstant, vrs: Variabel skalavkastning")

    st.sidebar.caption("**Trunkering av intäktsreduktion:**")
    dea_trunk_min = st.sidebar.slider("Minsta trunkering", 0.0, 0.3, 0.162416, step=0.005)
    dea_trunk_max = st.sidebar.slider("Högsta trunkering", 0.1, 0.5, 0.3, step=0.005)

    dea_outlier_krav = st.sidebar.slider(
        "Årligt krav för outliers (%)",
        1.0, 1.82, 1.0, 0.01,
        help="Fast krav för företag som klassas som outliers"
    )

    # === KÖR DEA ===
    run_model = st.sidebar.button("Kör DEA", type="primary")

    # Framtidssäker session state för punkt 3 (jämförelsetabell)
    session_key = f'dea_runs_{user_dmu}'
    if session_key not in st.session_state:
        st.session_state[session_key] = []

    if run_model:
        with st.spinner("Kör DEA-beräkningar..."):
            try:
                result = run_dea_model(
                    df,
                    rts=dea_rts,
                    trunkering_min=dea_trunk_min,
                    trunkering_max=dea_trunk_max,
                    input_cols=input_cols,
                    output_cols=output_cols,
                    outlier_filter=use_outlier_filter,
                    outlier_krav=dea_outlier_krav/100
                )
                
                # Spara senaste körning
                st.session_state[f'latest_dea_result_{user_dmu}'] = {
                    'result': result,
                    'params': {
                        'input_cols': input_cols,
                        'output_cols': output_cols,
                        'rts': dea_rts,
                        'trunk_min': dea_trunk_min,
                        'trunk_max': dea_trunk_max,
                        'outlier_filter': use_outlier_filter,
                        'outlier_krav': dea_outlier_krav,
                        'scenario_info': scen_info
                    },
                    'timestamp': datetime.now().isoformat()
                }
                
                st.success("DEA-analys slutförd!")
                
            except Exception as e:
                st.error(f"DEA-analys misslyckades: {e}")
                return

    # === VISA RESULTAT ===
    latest_key = f'latest_dea_result_{user_dmu}'
    if latest_key in st.session_state:
        show_dea_results(st.session_state[latest_key], user_dmu, company_name)
    else:
        show_waiting_state(df_full, user_dmu, company_name)


def validate_input_combinations(input_cols, scen_info, df):
    """Validerar input-kombinationer enligt DEA-regler"""
    
    # Analysera vald input
    has_capex_std = "CAPEX" in input_cols
    has_capex_scen = any(col.startswith("CAPEX_2024_wacc_") for col in input_cols)
    has_opexp = "OPEXp" in input_cols
    has_totex_std = "TOTEX" in input_cols
    has_totex_scen = any(col.startswith("TOTEX_wacc_") for col in input_cols)

    capex_any = has_capex_std or has_capex_scen
    totex_any = has_totex_std or has_totex_scen

    # Exklusivitetsregler
    if totex_any and (capex_any or has_opexp):
        st.error("Välj antingen TOTEX ELLER CAPEX/OPEXp, inte båda.")
        return False

    if (has_capex_std and has_capex_scen) or (has_totex_std and has_totex_scen):
        st.error("Välj antingen baseline- ELLER scenario-variant inom samma familj.")
        return False

    # Kontrollera scenario-fullständighet
    if scen_info.get("found"):
        capex_wacc_col = scen_info.get("capex_col")
        totex_wacc_col = scen_info.get("totex_col")
        chosen_scen_cols = [c for c in [capex_wacc_col, totex_wacc_col] if c and c in input_cols]
        
        if chosen_scen_cols:
            missing = [c for c in chosen_scen_cols if df[c].isna().any()]
            if missing:
                st.error(
                    "Scenario-kolumn saknar värden:\n"
                    f"- {', '.join(missing)}\n\n"
                    "Kontrollera exporten från Kapitalbas."
                )
                return False
    
    return True


def show_dea_results(latest_result, user_dmu, company_name):
    """Visar DEA-resultat med fokus på företaget"""
    
    result = latest_result['result']
    params = latest_result['params']
    
    # Filtrera till företaget
    company_result = result[result['DMU'] == user_dmu]
    if company_result.empty:
        st.error("Ditt företag hittades inte i DEA-resultatet")
        return
    
    company_row = company_result.iloc[0]
    
    # BERÄKNA GRANNGAP (för metric)
    neighbor_gap = calculate_company_neighbor_gap(result, user_dmu)
    
    # === PUNKT 2: FÖRETAGETS RESULTAT (5 METRICS) ===
    st.subheader("Ditt företags resultat")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        eff_val = company_row['Effektivitet']
        st.metric("Effektivitet", f"{eff_val:.3f}" if not pd.isna(eff_val) else "N/A")
    
    with col2:
        krav_val = company_row['Effkrav_proc']
        st.metric("Årligt krav", f"{krav_val*100:.2f}%" if not pd.isna(krav_val) else "N/A")
    
    with col3:
        is_outlier = company_row['is_outlier']
        st.metric("Outlier", "Ja" if is_outlier else "Nej")
    
    with col4:
        # Ranking
        valid_results = result[result['Effektivitet'].notna() & ~result['is_outlier']]
        if not valid_results.empty and not pd.isna(eff_val) and not company_row['is_outlier']:
            ranked = valid_results.sort_values('Effektivitet', ascending=False).reset_index(drop=True)
            company_rank = ranked[ranked['DMU'] == user_dmu].index[0] + 1
            total_ranked = len(ranked)
            st.metric("Ranking", f"{company_rank} / {total_ranked}")
        else:
            st.metric("Ranking", "N/A")
    
    with col5:
        # NYA METRIKEN: vs Grannar
        if neighbor_gap is not None:
            st.metric(
                "vs grannar",
                f"{neighbor_gap:+.3f}",
                delta=f"{neighbor_gap:+.3f}",
                help="Skillnad mot 4 närmaste grannar (KNN). Positivt = bättre än grannar."
            )
        else:
            st.metric("vs grannar", "N/A", help="Geografisk data saknas")
    
    # === PÅVERKBARA KOSTNADER ===
    company_paverkbara = calculate_company_paverkbara_costs(company_result)
    
    if company_paverkbara is not None:
        col1, col2, col3 = st.columns(3)
        with col1:
            baseline = company_paverkbara.get('baseline_4yr', 0) / 1000
            st.metric("Baseline 4-år", f"{baseline:.1f} MSEK")
        with col2:
            target = company_paverkbara.get('target_4yr', 0) / 1000  
            st.metric("Efter effektiviseringskrav", f"{target:.1f} MSEK")
        with col3:
            reduction = company_paverkbara.get('reduction_4yr', 0) / 1000
            reduction_pct = (reduction / baseline * 100) if baseline > 0 else 0
            st.metric("Delta", f"{reduction:.1f} MSEK ({reduction_pct:.1f}%)")
    else:
        st.info("Påverkbara kostnader kunde inte beräknas för ditt företag")

    # === PUNKT 4: BRANSCHKONTEXT ===
    st.markdown("---")
    st.subheader("Branschkontext")
    
    # Enkel statistik
    n_total = len(result)
    n_outliers = result['is_outlier'].sum()
    avg_eff = result[~result["is_outlier"]]["Effektivitet"].mean()
    avg_krav = result["Effkrav_proc"].mean() * 100
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Totalt antal företag", n_total)
    col2.metric("Outliers", n_outliers)
    col3.metric("Medeleffektivitet", f"{avg_eff:.3f}")
    col4.metric("Genomsnittligt krav", f"{avg_krav:.2f}%")

    # Enkla histogram
    st.markdown("#### Fördelningar")
    col_hist1, col_hist2 = st.columns(2)
    
    df_plot = result[result["is_outlier"] == False]
    
    with col_hist1:
        display_efficiency_histogram(df_plot["Effektivitet"], title="Effektivitet (exkl. outliers)")
    with col_hist2:
        display_efficiency_histogram(df_plot["Effkrav_proc"] * 100, title="Årligt effektiviseringskrav (%)")

    # Visa outliers om det finns
    if n_outliers > 0:
        with st.expander(f"Visa outliers ({n_outliers} företag)"):
            df_outliers = result[result["is_outlier"] == True][["Företag", "DMU", "Effektivitet", "Effkrav_proc"]]
            df_outliers["Effkrav_proc"] = (df_outliers["Effkrav_proc"] * 100).round(2)
            df_outliers = df_outliers.rename(columns={"Effkrav_proc": "Årligt krav (%)"})
            st.dataframe(df_outliers, use_container_width=True)

    # === GEOGRAFISK ANALYS (NYTT) ===
    st.markdown("---")
    st.header("Geografisk analys")
    display_company_geographic_analysis(result, user_dmu, company_name)

    # === PUNKT 5 & 6: EXPORT ===
    st.markdown("---")
    st.subheader("Export")
    
    col_excel, col_ir = st.columns(2)
    
    # Excel-export (Punkt 5)
    with col_excel:
        st.markdown("**DEA-resultat**")
        buffer = create_excel_export(result, company_result, company_name)
        st.download_button(
            label="Ladda ned som Excel",
            data=buffer.getvalue(),
            file_name=f"dea_resultat_{company_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    
    # IR-export (Punkt 6) 
    with col_ir:
        st.markdown("**Påverkbara kostnader**")
        if company_paverkbara is not None:
            export_name = st.text_input(
                "Export-namn", 
                value=f"DEA_{company_name.replace(' ', '_')}", 
                key="ir_export_name"
            )
            
            if st.button("Exportera till IR-dekomposition"):
                try:
                    export_path = export_paverkbara_to_ir(company_result, export_name)
                    st.success("Export till IR klar!")
                    st.caption(f"Fil: {export_path}")
                    st.info("Nu tillgängligt i IR-dekompositionen")
                except Exception as e:
                    st.error(f"Export misslyckades: {e}")
        else:
            st.info("Inga påverkbara kostnader att exportera")


def show_waiting_state(df_full, user_dmu, company_name):
    """Visar info medan användaren inte kört DEA än"""
    
    st.info("Välj parametrar och klicka på 'Kör DEA' för att analysera ditt företags effektivitet")
    
    # Visa företagsinformation
    with st.expander("Företagsinformation"):
        company_data = df_full[df_full['DMU'] == user_dmu]
        if not company_data.empty:
            company_row = company_data.iloc[0]
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("DMU", user_dmu)
            with col2:
                st.metric("CAPEX (tkr)", f"{company_row['CAPEX']:,.0f}")
            with col3:
                st.metric("OPEXp (tkr)", f"{company_row['OPEXp']:,.0f}")
            with col4:
                st.metric("Totalt i analys", len(df_full))


def calculate_company_paverkbara_costs(company_result):
    """Beräknar påverkbara kostnader för företaget"""
    
    try:
        ir_baseline_file = "intaktsram/data/Löpande kostnader från SDF 2024-27.xlsx"
        if not Path(ir_baseline_file).exists():
            return None
        
        export_data, metadata = calculate_ir_paverkbara_from_file(company_result, ir_baseline_file)
        
        if export_data is None or export_data.empty:
            return None
        
        return {
            'baseline_4yr': export_data['Paverkbara_Baseline_4yr'].sum(),
            'target_4yr': export_data['Paverkbara_Target'].sum(),
            'reduction_4yr': export_data['Total_Reduction_tkr'].sum(),
            'reid_count': len(export_data),
            'detailed_data': export_data
        }
        
    except Exception as e:
        st.error(f"Fel vid beräkning av påverkbara kostnader: {e}")
        return None


def export_paverkbara_to_ir(company_result, scenario_name):
    """Exporterar påverkbara kostnader till IR"""
    
    try:
        ir_baseline_file = "intaktsram/data/Löpande kostnader från SDF 2024-27.xlsx"
        export_data, metadata = calculate_ir_paverkbara_from_file(company_result, ir_baseline_file)
        
        if export_data is None or export_data.empty:
            raise Exception("Ingen export-data kunde beräknas")
        
        data_path, meta_path, summary = export_ir_paverkbara_scenario(
            export_data, 
            scenario_name,
            st.session_state  # Session state för org-identifiering
        )
        
        return data_path
        
    except Exception as e:
        raise Exception(f"Export misslyckades: {e}")


def create_excel_export(result, company_result, company_name):
    """Skapar Excel-export med företagsfokus"""
    
    buffer = io.BytesIO()
    
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        # Företagets resultat först
        company_export = company_result.copy()
        company_export.to_excel(writer, sheet_name="Mitt_företag", index=False)
        
        # Alla företag för kontext
        all_results = result.copy() 
        all_results['Mitt_företag'] = all_results['DMU'].isin(company_result['DMU'])
        all_results.to_excel(writer, sheet_name="Alla_företag", index=False)
        
        # Enkel sammanfattning
        summary_data = {
            'Mått': ['Företag totalt', 'Mitt företags ranking', 'Medeleffektivitet', 'Mitt företags effektivitet'],
            'Värde': [
                len(result),
                "N/A",  # Behöver beräknas från ranking-logiken
                f"{result[~result['is_outlier']]['Effektivitet'].mean():.3f}",
                f"{company_result.iloc[0]['Effektivitet']:.3f}"
            ]
        }
        pd.DataFrame(summary_data).to_excel(writer, sheet_name="Sammanfattning", index=False)
    
    return buffer


# Huvudfunktion som kallas från pages
if __name__ == "__main__":
    show_foretag_effektivitet()

# Logga ut
st.markdown("---")
if st.button("Logga ut", key="logout_effektivitet"):
    st.session_state.access_granted = False
    st.session_state.current_user = None
    st.session_state.user_role = None
    st.session_state.user_dmu = None
    st.rerun()
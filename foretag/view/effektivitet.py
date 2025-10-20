# foretag/view/effektivitet.py
# Företagsspecifik vy för effektiviseringsanalys
# UI-VERSION: Parametrar i huvudskärmen, professionell mörkblå profil

import streamlit as st
import pandas as pd
import numpy as np
import io
from datetime import datetime
from pathlib import Path

from effektiviseringskrav.backend.dea_model import run_dea_model
from effektiviseringskrav.backend.data_loader import merge_capex_scenario, load_data
from effektiviseringskrav.backend.ir_export import export_effektiviseringskrav_scenario
from effektiviseringskrav.backend.spatial_analysis import calculate_company_neighbor_gap
from effektiviseringskrav.frontend.components import (
    display_efficiency_histogram,
    display_company_geographic_analysis
)
from foretag.app.kapitalbas_data_loader import (
    get_user_dmu,
    load_reconciliation_foretag_info
)
from intaktsram.app.data_loader import get_company_display_name

# Autentisering
if "access_granted" not in st.session_state or not st.session_state.access_granted:
    st.stop()

if st.session_state.user_role != "company":
    st.error("Denna sida är endast tillgänglig för företagsanvändare")
    st.stop()


def show_foretag_effektivitet():
    """Huvudfunktion för företagsspecifik effektivitetsanalys"""
    
    # FLYTTA TILLBAKA HIT
    user_dmu = get_user_dmu()
    company_info = load_reconciliation_foretag_info()
    
    if user_dmu is None:
        st.error("Ingen DMU hittades för inloggad användare")
        return
    
    company_name = company_info.get('company_name', 'Ditt företag')
    company_display = get_company_display_name(user_dmu, company_name)
    
    # Ladda DEA-dataset
    try:
        data_file = "effektiviseringskrav/data/Data_modeller.xlsx"
        df_full = load_data(data_file)
    except Exception as e:
        st.error(f"Kunde inte ladda DEA-data: {e}")
        return
    
    if user_dmu not in df_full['DMU'].values:
        st.error(f"DMU {user_dmu} hittades inte i DEA-data")
        st.info("Detta kan betyda att ditt företag inte ingår i den aktuella effektivitetsanalysen")
        return
    
    st.title(f"DEA och effektiviseringskrav - {company_display}")
    st.markdown("Välj parametrar för DEA-analys och beräkna effektiviseringskrav för export till Intäktsram")
    
    st.markdown("---")
    
    # === DEA-PARAMETRAR I HUVUDSKÄRMEN ===
    df = df_full
    
    st.subheader("DEA-parametrar")
    
    # Försök merga CAPEX-scenario från Kapitalbas
    df, scen_info = merge_capex_scenario(df)

    if scen_info.get("found"):
        st.success(f"WACC-scenario aktivt: {scen_info['tag'].replace('p','.')} - täckning {scen_info['coverage']:.0%} - Se inputs för scenario-variabler")
    else:
        st.info("Inget CAPEX-scenario från Kapitalbas")

    # Input/Output val
    base_inputs = ["CAPEX", "OPEXp", "TOTEX"]
    all_inputs = [c for c in base_inputs if c in df.columns]
    all_outputs = ["CU", "MW", "NS", "MWhl", "MWhh"]

    # Lägg till scenario-kolumner
    if scen_info.get("found"):
        capex_wacc_col = scen_info.get("capex_col")
        totex_wacc_col = scen_info.get("totex_col")
        all_inputs += [c for c in [capex_wacc_col, totex_wacc_col] if c and c in df.columns]

    # Layout: Två kolumner för parametrar
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Variabler**")
        input_cols = st.multiselect(
            "Inputvariabler", 
            all_inputs, 
            default=[c for c in ["CAPEX", "OPEXp"] if c in all_inputs],
            help="Välj kostnadsvariabler som ska ingå i analysen"
        )
        
        output_cols = st.multiselect(
            "Outputvariabler", 
            all_outputs, 
            default=all_outputs,
            help="Välj outputvariabler som beskriver nätets storlek och aktivitet"
        )
    
    with col2:
        st.markdown("**Modellinställningar**")
        dea_rts = st.selectbox(
            "Skalavkastning", 
            ["crs", "vrs"], 
            index=0,
            help="CRS = Constant Returns to Scale, VRS = Variable Returns to Scale"
        )
        
        use_outlier_filter = st.checkbox(
            "Filtrera bort outliers före beräkning", 
            value=True,
            help="Exkluderar extremvärden från analysen"
        )

    if not validate_input_combinations(input_cols, scen_info, df):
        return

    if not input_cols or not output_cols:
        st.warning("Välj minst en input och en output för att köra modellen.")
        return

    # Trunkering och krav för outliers i en egen sektion
    st.markdown("**Trunkering och krav för outliers**")
    col3, col4, col5 = st.columns(3)
    
    with col3:
        dea_trunk_min = st.slider(
            "Minsta trunkering", 
            0.0, 0.3, 0.162416, 
            step=0.005,
            help="Lägsta effektivitetsgräns för trunkeringsintervallet"
        )
    
    with col4:
        dea_trunk_max = st.slider(
            "Högsta trunkering", 
            0.1, 0.5, 0.3, 
            step=0.005,
            help="Högsta effektivitetsgräns för trunkeringsintervallet"
        )
    
    with col5:
        dea_outlier_krav = st.slider(
            "Årligt krav för outliers (%)",
            1.0, 1.82, 1.0, 0.01,
            help="Fast effektiviseringskrav för företag klassade som outliers"
        )

    # Körknapp centrerad
    st.markdown("")
    col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 1])
    with col_btn1:
        run_model = st.button("Kör DEA-analys", type="primary", use_container_width=True)

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
                
                # Spara DEA-resultat för senare användning
                st.session_state[f'latest_dea_result_{user_dmu}'] = {
                    'result': result,
                    'dea_data': df,
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
                
                st.success("DEA-analys slutförd")
                
            except Exception as e:
                st.error(f"DEA-analys misslyckades: {e}")
                return

    # === VISA RESULTAT ===
    latest_key = f'latest_dea_result_{user_dmu}'
    if latest_key in st.session_state:
        st.markdown("---")
        show_dea_results(st.session_state[latest_key], user_dmu, company_display)  # FIXAT: använd company_display


def validate_input_combinations(input_cols, scen_info, df):
    """Validerar input-kombinationer enligt DEA-regler"""
    
    has_capex_std = "CAPEX" in input_cols
    has_capex_scen = any(col.startswith("CAPEX_2024_wacc_") for col in input_cols)
    has_opexp = "OPEXp" in input_cols
    has_totex_std = "TOTEX" in input_cols
    has_totex_scen = any(col.startswith("TOTEX_wacc_") for col in input_cols)

    capex_any = has_capex_std or has_capex_scen
    totex_any = has_totex_std or has_totex_scen

    if totex_any and (capex_any or has_opexp):
        st.error("Välj antingen TOTEX ELLER CAPEX/OPEXp, inte båda.")
        return False

    if (has_capex_std and has_capex_scen) or (has_totex_std and has_totex_scen):
        st.error("Välj antingen baseline- ELLER scenario-variant inom samma familj.")
        return False

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


def show_dea_results(latest_result, user_dmu, company_name):  # company_name innehåller nu company_display!
    """Visar DEA-resultat med fokus på företaget"""
    
    result = latest_result['result']
    params = latest_result['params']
    
    # Filtrera till företaget (DMU-nivå)
    company_result_dmu = result[result['DMU'] == user_dmu]
    if company_result_dmu.empty:
        st.error("Ditt företag hittades inte i DEA-resultatet")
        return
    
    company_row = company_result_dmu.iloc[0]
    
    # Beräkna granngap
    neighbor_gap = calculate_company_neighbor_gap(result, user_dmu)
    
    # === FÖRETAGETS RESULTAT ===
    st.subheader(f"Outputs för {company_name}")  # FIXAT: använd f-string och company_name
    
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
        valid_results = result[result['Effektivitet'].notna() & ~result['is_outlier']]
        if not valid_results.empty and not pd.isna(eff_val) and not company_row['is_outlier']:
            ranked = valid_results.sort_values('Effektivitet', ascending=False).reset_index(drop=True)
            company_rank = ranked[ranked['DMU'] == user_dmu].index[0] + 1
            total_ranked = len(ranked)
            st.metric("Ranking", f"{company_rank} / {total_ranked}")
        else:
            st.metric("Ranking", "N/A")
    
    with col5:
        if neighbor_gap is not None:
            st.metric(
                "vs grannar",
                 f"{neighbor_gap*100:+.2f}%",
                help="Skillnad (procentenhet) mot 4 närmaste grannar (KNN). Positivt = bättre än grannar."
            )
        else:
            st.metric("vs grannar", "N/A", help="Geografisk data saknas")
    
    # === ÖVERGRIPANDE STATISTIK OCH FÖRDELNINGAR ===
    n_total = len(result)
    n_outliers = result['is_outlier'].sum()
    avg_eff = result[~result["is_outlier"]]["Effektivitet"].mean()
    avg_krav = result["Effkrav_proc"].mean() * 100
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Totalt antal företag", n_total)
    col2.metric("Outliers", n_outliers)
    col3.metric("Medeleffektivitet", f"{avg_eff:.3f}")
    col4.metric("Genomsnittligt krav", f"{avg_krav:.2f}%")

    st.markdown("#### Fördelningar")
    col_hist1, col_hist2 = st.columns(2)
    
    df_plot = result[result["is_outlier"] == False]
    
    with col_hist1:
        display_efficiency_histogram(df_plot["Effektivitet"], title="Effektivitet (exkl. outliers)")
    with col_hist2:
        display_efficiency_histogram(df_plot["Effkrav_proc"] * 100, title="Årligt effektiviseringskrav (%)")

    # === GEOGRAFISK ANALYS ===
    st.markdown("---")
    st.subheader("Geografisk analys")
    value_choice = st.radio(
        "Välj värde för kartvisualisering",
        ["Effektivitet", "Supereffektivitet"],
        index=0,
        horizontal=True,
        help="Supereffektivitet ger större spridning mellan företag")

    display_company_geographic_analysis(result, user_dmu, company_name, value_column=value_choice)

    # === EXPORT ===
    st.markdown("---")
    st.subheader("Export")
    
    col_excel, col_ir = st.columns(2)
    
    # Excel-export
    with col_excel:
        st.markdown("**DEA-resultat**")
        st.caption("Ladda ned som Excel för egen analys")
        buffer = create_excel_export(result, company_result_dmu, company_name)
        st.download_button(
            label="Ladda ned som Excel",
            data=buffer.getvalue(),
            file_name=f"dea_resultat_{company_name.replace(' ', '_').replace('(', '').replace(')', '')}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
    
    # IR-export
    with col_ir:
        st.markdown("**Export till Intäktsram**")
        st.caption("Exporterar effektiviseringskrav för användning i Intäktsram-dekomposition")
        
        # Ta bort user_dmu från key eftersom det kan vara utanför scope
        if st.button("Exportera till Intäktsram", key=f"export_ir_{user_dmu}", use_container_width=True):
            try:
                success, message = export_to_ir(company_result_dmu)
                
                if success:
                    st.success(message)
                    st.info(
                        "Nu tillgängligt i Intäktsram → Effektiviseringskrav-tab → Importera från DEA. "
                        "Välj OPEX eller TOTEX vid import."
                    )
                else:
                    st.error(message)
                    
            except Exception as e:
                st.error(f"Export misslyckades: {e}")
                import traceback
                st.error(traceback.format_exc())


def export_to_ir(company_result):
    """
    Exporterar effektiviseringskrav till Intäktsram.
    """
    try:
        required_cols = ['DMU', 'REId', 'Effkrav_proc']
        missing_cols = [col for col in required_cols if col not in company_result.columns]
        
        if missing_cols:
            return False, f"DEA-resultat saknar kolumner: {missing_cols}"
        
        if company_result['REId'].isna().all():
            return False, "Alla REId är None i DEA-resultat"
        
        data_path, meta_path = export_effektiviseringskrav_scenario(
            dea_result=company_result
        )
        
        filename = Path(data_path).name
        return True, f"Export klar - Fil: {filename}"
        
    except Exception as e:
        return False, f"Export misslyckades: {str(e)}"


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
        
        # Sammanfattning
        summary_data = {
            'Mått': ['Företag totalt', 'Medeleffektivitet', 'Mitt företags effektivitet', 'Mitt företags krav'],
            'Värde': [
                len(result),
                f"{result[~result['is_outlier']]['Effektivitet'].mean():.3f}",
                f"{company_result.iloc[0]['Effektivitet']:.3f}",
                f"{company_result.iloc[0]['Effkrav_proc']*100:.2f}%"
            ]
        }
        pd.DataFrame(summary_data).to_excel(writer, sheet_name="Sammanfattning", index=False)
    
    return buffer


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
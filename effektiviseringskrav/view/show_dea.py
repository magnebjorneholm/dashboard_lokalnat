import streamlit as st
import pandas as pd
import numpy as np
import io
from datetime import datetime
from pathlib import Path
from typing import Tuple, Optional

from effektiviseringskrav.app.dea_model import run_dea_model
from effektiviseringskrav.app.plots import (
    plot_efficiency_histogram,
)
# NYTT: scenariomerge från data_loader
from effektiviseringskrav.app.data_loader import merge_capex_scenario


def show_dea_view(df):
    st.header("DEA-modell")
    st.sidebar.subheader("DEA-parametrar")
  
    # --- Försök merga CAPEX-scenario från Kapitalbas (DMU) -------------------
    df, scen_info = merge_capex_scenario(df)

    if scen_info.get("found"):
        capex_col = scen_info.get("capex_col")
        missing_scenario = df[df[capex_col].isna()]
        
        if not missing_scenario.empty:
            st.warning(f"CAPEX-scenario saknas för {len(missing_scenario)} DMU:")
            st.dataframe(missing_scenario[['DMU', 'Företag']])
            
            # Visa vilka DMU som finns i kapitalbas-exporten
            with st.expander("Debug: Jämför DMU mellan DEA och Kapitalbas"):
                # Läs kapitalbas-export direkt
                from effektiviseringskrav.app.data_loader import _latest_capex_scenario_path
                latest_path, _ = _latest_capex_scenario_path()
                if latest_path:
                    kapbas_df = pd.read_parquet(latest_path)
                    
                    dea_dmus = set(df['DMU'].unique())
                    kapbas_dmus = set(kapbas_df['DMU'].unique())
                    
                    st.write(f"DEA har {len(dea_dmus)} DMU")
                    st.write(f"Kapitalbas-export har {len(kapbas_dmus)} DMU")
                    st.write(f"Endast i DEA: {sorted(dea_dmus - kapbas_dmus)}")
                    st.write(f"Endast i Kapitalbas: {sorted(kapbas_dmus - dea_dmus)}")

    # --- Kolumnval (bas) ----------------------------------------------------
    base_inputs = ["CAPEX", "OPEXp", "TOTEX"]
    all_inputs = [c for c in base_inputs if c in df.columns]
    all_outputs = ["CU", "MW", "NS", "MWhl", "MWhh"]

    # --- Scenariokolumner in i listan (endast om hittat) --------------------
    capex_wacc_col = None
    totex_wacc_col = None
    if scen_info.get("found"):
        capex_wacc_col = scen_info.get("capex_col")
        totex_wacc_col = scen_info.get("totex_col")
        # Lägg bara in de kolumner som faktiskt finns i df
        all_inputs += [c for c in [capex_wacc_col, totex_wacc_col] if c and c in df.columns]
        st.sidebar.success(f"WACC-scenario aktiv: {scen_info['tag'].replace('p','.')} • täckning {scen_info['coverage']:.0%}")
    else:
        st.sidebar.info("Inget CAPEX-scenario laddat från Kapitalbas")

    st.sidebar.caption(
        "**Input-alternativ**\n"
        "• CAPEX + OPEXp: separata poster för analys av kostnadstyper\n"
        "• TOTEX: totalkostnad utan uppdelning\n"
        "• _wacc_: scenario från Kapitalbas med justerad kalkylränta"
    )

    # Default: CAPEX + OPEXp
    input_cols = st.sidebar.multiselect("Välj inputvariabler", all_inputs, default=[c for c in ["CAPEX", "OPEXp"] if c in all_inputs])

    # --- Exklusivitetsregler ------------------------------------------------
    has_capex_std  = "CAPEX" in input_cols
    has_capex_scen = any(col.startswith("CAPEX_2024_wacc_") for col in input_cols)
    has_opexp      = "OPEXp" in input_cols
    has_totex_std  = "TOTEX" in input_cols
    has_totex_scen = any(col.startswith("TOTEX_wacc_") for col in input_cols)

    capex_any = has_capex_std or has_capex_scen
    totex_any = has_totex_std or has_totex_scen

    # (1) TOTEX får inte kombineras med OPEXp/CAPEX eller scenario
    if (totex_any and (capex_any or has_opexp)):
        st.error("Välj antingen bara TOTEX (baseline/scenario) ELLER CAPEX (baseline/scenario) och/eller OPEXp.")
        st.stop()

    # (2) Samma familj: baseline & scenario samtidigt är inte tillåtet
    if (has_capex_std and has_capex_scen) or (has_totex_std and has_totex_scen):
        st.error("Välj antingen baseline- ELLER scenario-variant inom samma familj (CAPEX/TOTEX).")
        st.stop()

    # (3) Om scenario-kolumn valts, kontrollera att kolumnen är komplett (inga NaN)
    if scen_info.get("found"):
        chosen_scen_cols = [c for c in [capex_wacc_col, totex_wacc_col] if c and c in input_cols]
        if chosen_scen_cols:
            missing = [c for c in chosen_scen_cols if df[c].isna().any()]
            if missing:
                st.error(
                    "Scenario-kolumn saknar värden för alla DMU och kan inte användas:\n"
                    f"- {', '.join(missing)}\n\n"
                    "Kontrollera exporten från Kapitalbas (nät utan DMU-match exkluderas)."
                )
                st.stop()

    output_cols = st.sidebar.multiselect("Välj outputvariabler", all_outputs, default=all_outputs)
    use_outlier_filter = st.sidebar.checkbox("Filtrera bort outliers före beräkning", value=True)

    if not input_cols or not output_cols:
        st.warning("Välj minst en input och en output för att köra modellen.")
        st.stop()

    # --- RTS och trunkering ---
    st.sidebar.caption("**Skalavkastning (RTS)**\n• crs: Konstant skalavkastning\n• vrs: Variabel skalavkastning")
    dea_rts = st.sidebar.selectbox("Skalavkastning (RTS)", ["crs", "vrs"], index=0)

    st.sidebar.caption("**Trunkering av intäktsreduktion**\nBegränsar hur mycket ineffektivitet får påverka kraven.")
    dea_trunk_min = st.sidebar.slider("Minsta trunkering", 0.0, 0.3, 0.162416, step=0.005)
    dea_trunk_max = st.sidebar.slider("Högsta trunkering", 0.1, 0.5, 0.3, step=0.005)

    dea_outlier_krav = st.sidebar.slider(
        "Årligt krav för outliers (%)",
        1.0, 1.82, 1.0, 0.01,
        help="Vilket fast krav (i procent) ska ges till företag som klassas som outliers?"
    )

    # --- Körmodellknapp ---
    run_model = st.sidebar.button("Kör DEA", type="primary")

    # Lagra DEA-resultat i session state för att bevara mellan reruns
    if run_model:
        with st.spinner("Kör DEA-beräkningar..."):
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
        # Lagra i session state
        st.session_state['dea_result'] = result
        st.session_state['dea_params'] = {
            'input_cols': input_cols,
            'output_cols': output_cols,
            'rts': dea_rts,
            'trunkering_min': dea_trunk_min,
            'trunkering_max': dea_trunk_max
        }

    # Visa resultat om de finns (antingen just körda eller från session state)
    if 'dea_result' in st.session_state:
        result = st.session_state['dea_result']

        # --- Resultatvisning ---
        st.subheader("DEA-resultat")
        
        # Outlier-sammanfattning
        df_outliers = result[result["is_outlier"] == True][["Företag", "Effektivitet", "Supereffektivitet", "Effkrav_proc"]]
        df_outliers["Effkrav_proc"] = df_outliers["Effkrav_proc"].round(4)

        n_outliers = len(df_outliers)
        n_total = len(result)
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Totalt antal DMU", n_total)
        with col2:
            st.metric("Outliers", n_outliers)
        with col3:
            avg_eff = result[~result["is_outlier"]]["Effektivitet"].mean()
            st.metric("Medeleffektivitet", f"{avg_eff:.3f}")
        with col4:
            avg_krav = result["Effkrav_proc"].mean() * 100
            st.metric("Medelkrav (%)", f"{avg_krav:.2f}%")

        if n_outliers > 0:
            st.warning(f"{n_outliers} företag klassificerade som outliers (fast krav {dea_outlier_krav:.1f}%)")
            with st.expander("Visa outliers"):
                st.dataframe(df_outliers, use_container_width=True)

        # Huvudresultat-tabell
        display_result = result[["DMU", "Företag", "Effektivitet", "Supereffektivitet", "Effkrav_proc", "is_outlier"]].copy()
        display_result["Effkrav_proc"] = (display_result["Effkrav_proc"] * 100).round(2)
        display_result = display_result.rename(columns={
            "Effkrav_proc": "Årligt krav (%)",
            "is_outlier": "Outlier"
        })
        
        st.dataframe(display_result, use_container_width=True)

        # Histogram-plots
        st.subheader("Fördelningar")
        col1, col2 = st.columns(2)
        
        df_plot = result[result["is_outlier"] == False]
        
        with col1:
            plot_efficiency_histogram(df_plot["Effektivitet"], title="Effektivitet (exkl. outliers)")
        with col2:
            plot_efficiency_histogram(df_plot["Effkrav_proc"] * 100, title="Årligt effektiviseringskrav (%) (exkl. outliers)")

        # --- IR-EXPORT SEKTION ---
        st.markdown("---")
        st.subheader("Export till Intäktsram-dekomposition")
        st.caption("Beräknar påverkbara kostnader för 2024-2027 perioden baserat på Ei:s verkliga beräkningsmetod")
        
        # Kontrollera att vi har nödvändiga kolumner
        if 'Effkrav_proc' not in result.columns:
            st.error("Export kräver Effkrav_proc. Kontrollera DEA-modellens output.")
        else:
            # Ladda IR-baseline data för korrekt beräkning
            ir_baseline_file = st.text_input(
                "Sökväg till IR baseline Excel-fil",
                value="intaktsram/data/Löpande kostnader från SDF 2024-27.xlsx",
                help="Excel-fil med 'Påverkbara' ark som innehåller baseline-data per REId"
            )
            
            if Path(ir_baseline_file).exists():
                try:
                    # Beräkna påverkbara kostnader enligt Ei:s metod
                    export_data = calculate_ir_paverkbara_export_correct(result, ir_baseline_file)
                    
                    if export_data is not None and not export_data.empty:
                        # Visa sammanfattning av exporten
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            total_baseline = export_data['Paverkbara_Baseline_4yr'].sum() / 1000  # MSEK
                            st.metric("Baseline 4-år totalt", f"{total_baseline:.1f} MSEK")
                        with col2:
                            total_target = export_data['Paverkbara_Target'].sum() / 1000  # MSEK
                            st.metric("Efter effektiviseringskrav", f"{total_target:.1f} MSEK")
                        with col3:
                            total_reduction = export_data['Total_Reduction_tkr'].sum() / 1000  # MSEK
                            reduction_pct = (total_reduction / total_baseline) * 100 if total_baseline > 0 else 0
                            st.metric("Total reduktion", f"{total_reduction:.1f} MSEK ({reduction_pct:.1f}%)")
                        
                        # Test: jämför mot Ei:s baseline för sanity check
                        with st.expander("🔍 Sanity check - Ei baseline vs vårt scenario"):
                            # Beräkna vad som händer om vi applicerar Ei:s egna krav
                            ei_test = export_data.copy()
                            ei_test['Test_Target'] = (
                                ei_test['Y2024_baseline'] + 
                                ei_test['Y2025_baseline'] + 
                                ei_test['Y2026_baseline'] + 
                                ei_test['Y2027_baseline']
                            )
                            ei_test['Test_Delta'] = ei_test['Test_Target'] - ei_test['Paverkbara_Baseline_4yr']
                            
                            test_delta_total = ei_test['Test_Delta'].sum()
                            test_delta_pct = (test_delta_total / ei_test['Paverkbara_Baseline_4yr'].sum() * 100) if ei_test['Paverkbara_Baseline_4yr'].sum() > 0 else 0
                            
                            col_a, col_b = st.columns(2)
                            with col_a:
                                st.metric("Ei baseline total", f"{ei_test['Test_Target'].sum()/1000:.1f} MSEK")
                            with col_b:
                                st.metric("Delta mot IR baseline", f"{test_delta_total/1000:+.1f} MSEK ({test_delta_pct:+.2f}%)")
                            
                            if abs(test_delta_pct) < 0.1:
                                st.success("✅ Sanity check OK - mindre än 0,1% skillnad mellan Ei baseline och IR baseline")
                            else:
                                st.warning(f"⚠️ Sanity check: {test_delta_pct:.2f}% skillnad - kontrollera baseline-mappning")
                        
                        # Visa preview av export-data
                        with st.expander("Förhandsvisning av export-data"):
                            preview_data = export_data[['DMU', 'REId', 'Företag', 'Paverkbara_Baseline_4yr', 'Effektiviseringskrav', 'Paverkbara_Target', 'Total_Reduction_tkr']].copy()
                            preview_data['Effektiviseringskrav'] = (preview_data['Effektiviseringskrav'] * 100).round(2)
                            preview_data = preview_data.rename(columns={'Effektiviseringskrav': 'Årligt krav (%)'})
                            st.dataframe(preview_data, use_container_width=True)
                        
                        # Export-knapp
                        export_name = st.text_input("Export-namn (valfritt)", placeholder="t.ex. 'DEA_CRS_2024'")
                        
                        col_export1, col_export2 = st.columns(2)
                        with col_export1:
                            if st.button("Exportera till IR-dekomposition", type="primary"):
                                try:
                                    data_path, meta_path = export_ir_paverkbara_scenario(export_data, export_name or "DEA")
                                    st.success("Export klar!")
                                    st.caption(f"Data: {data_path}")
                                    st.caption(f"Metadata: {meta_path}")
                                    st.info("Scenariot är nu tillgängligt i IR-dekompositionen under 'Hämta från Effektiviseringskrav'")
                                except Exception as e:
                                    st.error(f"Export misslyckades: {e}")
                                    import traceback
                                    st.code(traceback.format_exc())
                        
                except Exception as e:
                    st.error(f"Fel vid läsning av IR baseline: {e}")
                    import traceback
                    st.code(traceback.format_exc())
            else:
                st.warning(f"IR baseline-fil hittades inte: {ir_baseline_file}")
                st.info("Kontrollera sökvägen till Excel-filen med 'Påverkbara' ark")

        # --- Standard Excel-export för DEA-resultat ---
        st.markdown("---")
        st.subheader("Export av DEA-resultat")
        
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            result.to_excel(writer, sheet_name="Resultat", index=False)

        st.download_button(
            label="Ladda ned DEA-resultat som Excel",
            data=buffer.getvalue(),
            file_name=f"dea_resultat_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
    else:
        st.info("Välj modellspecifikationer och klicka på 'Kör DEA' för att se resultat och export-alternativ.")
        
        # Lägg till knapp för att rensa lagrade resultat
        if 'dea_result' in st.session_state:
            if st.button("Rensa lagrade DEA-resultat"):
                del st.session_state['dea_result']
                if 'dea_params' in st.session_state:
                    del st.session_state['dea_params']
                st.rerun()

def calculate_ir_paverkbara_export_correct(dea_result: pd.DataFrame, ir_baseline_file: str) -> Optional[pd.DataFrame]:
    """
    Korrekt beräkning av påverkbara kostnader enligt Ei:s exakta metod.
    
    Metod enligt Excel-formler:
    1. Börja från DT (medelvärde 2018-2021) - den rena basen
    2. Applicera scenario-krav direkt: Y_t = DT - t·e_scn·DT + DU/4
    3. NeonAndringar (DU) fördelas lika över 2024-2027 som +DU/4 per år
    4. Totalsumma = 4·DT - 10·e_scn·DT + DU
    """
    
    # Ladda IR baseline-data
    ir_baseline = load_ir_paverkbara_baseline(ir_baseline_file)
    if ir_baseline is None:
        return None
    
    # Robust kolumnhantering för DEA-resultat (hanterar encoding-problem)
    available_cols = list(dea_result.columns)
    
    # Leta efter företagskolumn med olika möjliga namn
    foretag_col = None
    for col in available_cols:
        if any(variant in col.lower() for variant in ['företag', 'foretag', 'företag', 'fÃ¶retag']):
            foretag_col = col
            break
    
    if foretag_col is None:
        st.warning("Hittar inte företagskolumn - använder endast DMU och REId")
        required_cols = ['DMU', 'REId', 'Effkrav_proc']
        export_cols = required_cols
    else:
        required_cols = ['DMU', 'REId', foretag_col, 'Effkrav_proc']
        export_cols = required_cols
    
    # Kontrollera att alla nödvändiga kolumner finns
    missing_cols = [col for col in required_cols if col not in available_cols]
    if missing_cols:
        st.error(f"DEA-resultat saknar kolumner: {missing_cols}")
        st.write(f"Tillgängliga kolumner: {available_cols}")
        return None
    
    # Skapa export-data med robusta kolumnnamn
    export_data = dea_result[export_cols].copy()
    
    # Normalisera kolumnnamn
    if foretag_col and foretag_col != 'Företag':
        export_data = export_data.rename(columns={foretag_col: 'Företag'})
    
    # Merge med IR baseline per REId
    export_data = export_data.merge(ir_baseline, on='REId', how='left')
    
    # Filtrera till endast rader där vi har komplett baseline-data
    required_cols = ['B_raw', 'e_base']  # Vi behöver inte y2024_base längre för återställning
    complete_mask = export_data[required_cols].notna().all(axis=1)
    incomplete_count = (~complete_mask).sum()
    
    if incomplete_count > 0:
        st.warning(f"{incomplete_count} REId saknar komplett baseline-data och exkluderas från export")
        # Visa vilka REId som saknas för debugging - hantera om Företag-kolumn saknas
        display_cols = ['REId'] + required_cols
        if 'Företag' in export_data.columns:
            display_cols.insert(1, 'Företag')
        missing_data = export_data[~complete_mask][display_cols]
        with st.expander("Visa REId med saknade data"):
            st.dataframe(missing_data)
    
    export_data = export_data[complete_mask].copy()
    
    if export_data.empty:
        st.error("Ingen REId har komplett baseline-data")
        return None
    
    # Hämta värden enligt korrekt logik
    DT = export_data['B_raw'].astype(float)           # Medelvärde 2018-2021 (ren bas)
    DU = export_data.get('Adj', 0).astype(float).fillna(0)  # NeonAndringar (total justering)
    e_base = export_data['e_base'].astype(float)      # Ei:s originalkriterier för sanity check
    e_scn = export_data['Effkrav_proc'].astype(float)  # Era DEA-krav (scenario)
    
    # Årlig fördelning av NeonAndringar
    Delta = DU / 4  # Fördelat lika över 4 år
    
    # Hjälpfunktion för Excel "half-up" avrundning
    def round_half_up(x):
        import math
        return int(math.floor(float(x) + 0.5))
    
    # Hjälpfunktion för Excel-korrekt avdragsberäkning
    def avdrag_kumulativ_vectorized(DT_series, DU_series, e_series):
        """Beräknar Excel-korrekta kumulativa avdrag för alla rader samtidigt."""
        results = []
        
        for i, (dt_val, du_val, e_val) in enumerate(zip(DT_series, DU_series, e_series)):
            # B = DT + DU/4 (årlig bas att ta procent på)
            B = float(dt_val) + float(du_val)/4.0
            
            # Årliga inkrement med tillväxtfaktor: inc_t = round_half_up(e * B * (1+e)^(t-1))
            inc = [round_half_up(e_val * B * ((1.0 + e_val) ** k)) for k in range(4)]
            
            # Kumulativa avdrag: Avdrag_t = sum(inc_1 till inc_t)
            cum = [inc[0], 
                   inc[0] + inc[1], 
                   inc[0] + inc[1] + inc[2], 
                   sum(inc)]
            
            results.append({
                'inc': inc,
                'avdrag': cum,
                'B': B
            })
        
        return results
    
    # === SCENARIO-BERÄKNING med Excel-korrekt tillväxtfaktor ===
    scn_results = avdrag_kumulativ_vectorized(DT, DU, e_scn)
    
    # Extrahera avdrag och beräkna årsnivåer
    avdrag_2024_scn = np.array([r['avdrag'][0] for r in scn_results])
    avdrag_2025_scn = np.array([r['avdrag'][1] for r in scn_results])
    avdrag_2026_scn = np.array([r['avdrag'][2] for r in scn_results])
    avdrag_2027_scn = np.array([r['avdrag'][3] for r in scn_results])
    
    # Beräkna årsnivåer: Y_t = DT - Avdrag_t + Δ
    y2024_scn = np.array([round_half_up(dt - av + dlt) for dt, av, dlt in zip(DT, avdrag_2024_scn, Delta)])
    y2025_scn = np.array([round_half_up(dt - av + dlt) for dt, av, dlt in zip(DT, avdrag_2025_scn, Delta)])
    y2026_scn = np.array([round_half_up(dt - av + dlt) for dt, av, dlt in zip(DT, avdrag_2026_scn, Delta)])
    y2027_scn = np.array([round_half_up(dt - av + dlt) for dt, av, dlt in zip(DT, avdrag_2027_scn, Delta)])
    
    # Totalsumma scenario
    total_4yr_scn = y2024_scn + y2025_scn + y2026_scn + y2027_scn
    
    # Spara inkrement för debug
    inc_2024_scn = np.array([r['inc'][0] for r in scn_results])
    inc_2025_scn = np.array([r['inc'][1] for r in scn_results])
    inc_2026_scn = np.array([r['inc'][2] for r in scn_results])
    inc_2027_scn = np.array([r['inc'][3] for r in scn_results])
    B_scn = np.array([r['B'] for r in scn_results])
    
    # === BASELINE-BERÄKNING med Excel-korrekt tillväxtfaktor ===
    base_results = avdrag_kumulativ_vectorized(DT, DU, e_base)
    
    # Extrahera avdrag och beräkna årsnivåer för baseline
    avdrag_2024_base = np.array([r['avdrag'][0] for r in base_results])
    avdrag_2025_base = np.array([r['avdrag'][1] for r in base_results])
    avdrag_2026_base = np.array([r['avdrag'][2] for r in base_results])
    avdrag_2027_base = np.array([r['avdrag'][3] for r in base_results])
    
    # Beräkna årsnivåer för baseline: Y_t = DT - Avdrag_t + Δ
    y2024_base_calc = np.array([round_half_up(dt - av + dlt) for dt, av, dlt in zip(DT, avdrag_2024_base, Delta)])
    y2025_base_calc = np.array([round_half_up(dt - av + dlt) for dt, av, dlt in zip(DT, avdrag_2025_base, Delta)])
    y2026_base_calc = np.array([round_half_up(dt - av + dlt) for dt, av, dlt in zip(DT, avdrag_2026_base, Delta)])
    y2027_base_calc = np.array([round_half_up(dt - av + dlt) for dt, av, dlt in zip(DT, avdrag_2027_base, Delta)])
    
    # Totalsumma baseline
    total_4yr_base = y2024_base_calc + y2025_base_calc + y2026_base_calc + y2027_base_calc
    
    # Spara inkrement för baseline (för debug)
    inc_2024_base = np.array([r['inc'][0] for r in base_results])
    inc_2025_base = np.array([r['inc'][1] for r in base_results])
    inc_2026_base = np.array([r['inc'][2] for r in base_results])
    inc_2027_base = np.array([r['inc'][3] for r in base_results])
    B_base = np.array([r['B'] for r in base_results])
    
    # === SANITY CHECK ===
    # Kontrollera mot verkliga Excel-värden om de finns
    sanity_check_data = {}
    if 'y2024_base' in export_data.columns:
        y2024_excel = export_data['y2024_base'].astype(float)
        diff_2024 = np.abs(y2024_base_calc - y2024_excel)
        sanity_check_data['2024_diff'] = diff_2024
    
    if 'ir_totalsumma' in export_data.columns:
        total_excel = export_data['ir_totalsumma'].astype(float)
        diff_total = np.abs(total_4yr_base - total_excel)
        sanity_check_data['total_diff'] = diff_total
    
    # Avrunda resultat till heltal (tkr)
    y2024_scn = np.round(y2024_scn).astype(int)
    y2025_scn = np.round(y2025_scn).astype(int)
    y2026_scn = np.round(y2026_scn).astype(int)
    y2027_scn = np.round(y2027_scn).astype(int)
    total_4yr_scn = np.round(total_4yr_scn).astype(int)
    total_4yr_base = np.round(total_4yr_base).astype(int)
    
    y2024_base_calc = np.round(y2024_base_calc).astype(int)
    y2025_base_calc = np.round(y2025_base_calc).astype(int)
    y2026_base_calc = np.round(y2026_base_calc).astype(int)
    y2027_base_calc = np.round(y2027_base_calc).astype(int)
    
    # === SKAPA EXPORT-DATAFRAME ===
    export_data['Paverkbara_Baseline_4yr'] = total_4yr_base
    export_data['Paverkbara_Target'] = total_4yr_scn
    export_data['Total_Reduction_tkr'] = (total_4yr_base - total_4yr_scn).astype(int)
    export_data['Effektiviseringskrav'] = e_scn  # Behåll som decimal för referens
    
    # Lägg till årsvisa komponenter för debugging/validering
    export_data['Y2024_scenario'] = y2024_scn
    export_data['Y2025_scenario'] = y2025_scn
    export_data['Y2026_scenario'] = y2026_scn
    export_data['Y2027_scenario'] = y2027_scn
    
    export_data['Y2024_baseline'] = y2024_base_calc
    export_data['Y2025_baseline'] = y2025_base_calc
    export_data['Y2026_baseline'] = y2026_base_calc
    export_data['Y2027_baseline'] = y2027_base_calc
    
    # Lägg till beräkningsparametrar för transparens
    export_data['DT_medelvarde'] = np.round(DT).astype(int)
    export_data['DU_neonandringar'] = np.round(DU).astype(int)
    export_data['Delta_per_ar'] = np.round(Delta).astype(int)
    export_data['B_bas_scn'] = np.round(B_scn).astype(int)
    export_data['Ei_arligt_krav'] = np.round(e_base, 6)
    export_data['DEA_arligt_krav'] = np.round(e_scn, 6)
    
    # Lägg till Excel-korrekta inkrement och avdrag
    export_data['Inc_2024_scn'] = inc_2024_scn
    export_data['Inc_2025_scn'] = inc_2025_scn  
    export_data['Inc_2026_scn'] = inc_2026_scn
    export_data['Inc_2027_scn'] = inc_2027_scn
    export_data['Avdrag_2024_scn'] = avdrag_2024_scn
    export_data['Avdrag_2025_scn'] = avdrag_2025_scn  
    export_data['Avdrag_2026_scn'] = avdrag_2026_scn
    export_data['Avdrag_2027_scn'] = avdrag_2027_scn
    
    # Sanity check-resultat mot Excel-värden
    if 'y2024_excel' in export_data.columns:
        export_data['Sanity_2024_diff'] = np.abs(y2024_base_calc - export_data['y2024_excel'].astype(float))
    if 'total_excel' in export_data.columns:
        export_data['Sanity_total_diff'] = np.abs(total_4yr_base - export_data['total_excel'].astype(float))
    
    export_data['Analysis_Method'] = 'DEA_corrected_DT_excel_growth_factor'
    export_data['Export_Timestamp'] = datetime.now().isoformat()
    
    # === DEBUG-SEKTION med tillväxtfaktor-analys ===
    # Visa detaljerad beräkning för en utvald REId
    debug_reids = ['REL00015', 'REL00001']  # Prova företag med NeonAndringar först
    debug_reid = None
    debug_mask = None
    
    for reid in debug_reids:
        mask = export_data['REId'] == reid
        if mask.any():
            debug_reid = reid
            debug_mask = mask
            break
    
    if debug_reid and debug_mask.any():
        debug_row = export_data[debug_mask].iloc[0]
        
        with st.expander(f"Debug: Excel-korrekt tillväxtfaktor för {debug_reid}"):
            st.write("**Input-värden:**")
            st.write(f"- DT (medelvärde 2018-2021): {debug_row['DT_medelvarde']:,} tkr")
            st.write(f"- DU (NeonAndringar): {debug_row['DU_neonandringar']:,} tkr") 
            st.write(f"- Δ (per år): {debug_row['Delta_per_ar']:,} tkr")
            st.write(f"- **B (bas för procent)**: DT + Δ = {debug_row['DT_medelvarde']:,} + {debug_row['Delta_per_ar']:,} = {debug_row['B_bas_scn']:,} tkr")
            st.write(f"- e_base (Ei:s krav): {debug_row['Ei_arligt_krav']:.6f} ({debug_row['Ei_arligt_krav']*100:.3f}%)")
            st.write(f"- e_scn (DEA-krav): {debug_row['DEA_arligt_krav']:.6f} ({debug_row['DEA_arligt_krav']*100:.2f}%)")
            
            st.write("**KORREKT Excel-formel med tillväxtfaktor:**")
            st.code("inc_t = round_half_up(e × B × (1+e)^(t-1))")
            st.code("Avdrag_t = Σ(inc_1 till inc_t)")
            st.code("Y_t = DT - Avdrag_t + Δ")
            
            st.write("**Scenario-beräkning (årliga inkrement):**")
            B_val = debug_row['B_bas_scn']
            e_scn_val = debug_row['DEA_arligt_krav']
            
            for t, year in enumerate([2024, 2025, 2026, 2027], 1):
                growth_factor = (1.0 + e_scn_val) ** (t-1)
                teoretisk_inc = e_scn_val * B_val * growth_factor
                faktisk_inc = debug_row[f'Inc_{year}_scn']
                avdrag_kum = debug_row[f'Avdrag_{year}_scn']
                
                st.write(f"- **{year} (t={t})**: inc = {e_scn_val:.6f} × {B_val:,} × {growth_factor:.6f} = {teoretisk_inc:.1f} → {faktisk_inc} tkr")
                st.caption(f"  Kumulativt avdrag: {avdrag_kum:,} tkr")
            
            st.write("**Årsnivåer efter avdrag:**")
            DT_val = debug_row['DT_medelvarde']
            Delta_val = debug_row['Delta_per_ar']
            
            for year in [2024, 2025, 2026, 2027]:
                avdrag_val = debug_row[f'Avdrag_{year}_scn']
                resultat_val = debug_row[f'Y{year}_scenario']
                beraknad = DT_val - avdrag_val + Delta_val
                
                st.write(f"- **{year}**: {DT_val:,} - {avdrag_val:,} + {Delta_val:,} = {beraknad:,} → {resultat_val:,} tkr")
            
            st.write(f"**Total scenario:** {debug_row['Paverkbara_Target']:,} tkr")
            st.write(f"**Total baseline:** {debug_row['Paverkbara_Baseline_4yr']:,} tkr")
            st.write(f"**Total reduktion:** {debug_row['Total_Reduction_tkr']:,} tkr")
            
            # Sanity check mot Excel-värden om de finns
            sanity_cols = [col for col in debug_row.index if col.startswith('Sanity_')]
            if sanity_cols:
                st.write("**Sanity check mot Excel:**")
                for col in sanity_cols:
                    diff_val = debug_row[col]
                    if abs(diff_val) < 0.5:
                        st.write(f"✅ {col.replace('Sanity_', '').replace('_', ' ')}: skillnad {diff_val:.1f} tkr (PERFEKT)")
                    elif abs(diff_val) < 2:
                        st.write(f"✅ {col.replace('Sanity_', '').replace('_', ' ')}: skillnad {diff_val:.1f} tkr (OK)")
                    else:
                        st.write(f"⚠️ {col.replace('Sanity_', '').replace('_', ' ')}: skillnad {diff_val:.1f} tkr")
            
            st.write("**Metod:** Excel-exakt med tillväxtfaktor (1+e)^(t-1) och half-up avrundning")
    
    return export_data


def load_ir_paverkbara_baseline(filepath: str) -> Optional[pd.DataFrame]:
    """
    Läser baseline-data från 'Påverkbara' arket för korrekt IR-beräkning.
    Använder exakta kolumnpositioner enligt användarspecifikation.

    Kolumnpositioner:
    - REid (A) 
    - Medelvärde 2018-2021 påverkbara kostnader (DT) - DEN RENA BASEN
    - NeonAndringar total justering (DU) - fördelas lika över 2024-2027
    - Parametrar OPEX Årligt eff.krav procent (EG) - Ei:s originalkrav
    - 2024-2027 (EA-ED) - används endast för sanity check
    - Totalsumma (EE) - används för sanity check
    """
    try:
        # Läs Excel-fil med header på rad 1
        df_pav = pd.read_excel(filepath, sheet_name="Påverkbara", 
                              header=1, engine="openpyxl")
        
        if df_pav.empty:
            st.error("Påverkbara-arket är tomt")
            return None

        def excel_col_to_index(col_str: str) -> int:
            """Konverterar Excel-kolumnnamn (t.ex. 'DT') till 0-baserat index"""
            result = 0
            for char in col_str:
                result = result * 26 + (ord(char) - ord('A') + 1)
            return result - 1

        # Kolumnpositioner enligt korrigerad metod
        col_positions = {
            'REId': 'A',           # REid
            'B_raw': 'DT',         # Medelvärde 2018-2021 (REN BAS)
            'Adj': 'DU',           # NeonAndringar (total justering, inte DD)
            'e_base': 'EG',        # Ei:s årliga effektiviseringskrav
            'mu_factor': 'EF',     # Omvandlingsränta (används ej i nya metoden)
            # Dessa används endast för sanity check:
            'y2024_excel': 'EA',   # Excel-beräknat 2024-värde
            'y2025_excel': 'EB',   # Excel-beräknat 2025-värde
            'y2026_excel': 'EC',   # Excel-beräknat 2026-värde 
            'y2027_excel': 'ED',   # Excel-beräknat 2027-värde
            'total_excel': 'EE'    # Excel-beräknad totalsumma
        }
        
        # Konvertera till kolumnindex
        col_indices = {field: excel_col_to_index(col) for field, col in col_positions.items()}
        
        # Kontrollera att vi har tillräckligt många kolumner
        max_col_index = max(col_indices.values())
        if len(df_pav.columns) <= max_col_index:
            st.error(f"Excel-filen har endast {len(df_pav.columns)} kolumner, behöver minst {max_col_index + 1}")
            return None

        # Bygg DataFrame med våra kolumnnamn
        df_out = pd.DataFrame()
        
        for field, col_index in col_indices.items():
            if col_index < len(df_pav.columns):
                df_out[field] = df_pav.iloc[:, col_index]
            else:
                st.warning(f"Kolumn {field} på position {col_positions[field]} (index {col_index}) finns inte i filen")
                # För obligatoriska kolumner, sätt som NaN
                if field in ['REId', 'B_raw', 'e_base']:
                    df_out[field] = pd.Series([np.nan] * len(df_pav))

        # Kontrollera att vi har kritiska kolumner
        if 'REId' not in df_out.columns or df_out['REId'].isna().all():
            st.error("REId-kolumn hittades inte på position A eller är tom")
            return None

        # Typning och rensning för numeriska kolumner
        numeric_cols = ['B_raw', 'Adj', 'e_base', 'y2024_excel', 'y2025_excel', 
                       'y2026_excel', 'y2027_excel', 'total_excel', 'mu_factor']
        
        for col in numeric_cols:
            if col in df_out.columns:
                # Konvertera till numerisk - e_base är redan i decimal format (0.01 = 1%)
                df_out[col] = pd.to_numeric(df_out[col], errors='coerce')

        # Hantera Adj-kolumn (NeonAndringar kan saknas eller vara NaN)
        if 'Adj' not in df_out.columns:
            df_out['Adj'] = 0.0
        else:
            df_out['Adj'] = df_out['Adj'].fillna(0.0)

        # Filtrera till giltiga REId och ta bort tomma rader
        df_out = df_out.dropna(subset=['REId'])
        df_out = df_out[df_out['REId'].astype(str).str.startswith('REL')].reset_index(drop=True)

        # Validering av kritiska data
        critical_missing = df_out[['B_raw', 'e_base']].isna().any(axis=1).sum()
        if critical_missing > 0:
            st.warning(f"{critical_missing} REId saknar kritiska baseline-värden (B_raw eller e_base)")

        # Debug-info
        found_cols = [col for col in numeric_cols + ['REId'] if col in df_out.columns]
        missing_cols = [col for col in numeric_cols if col not in df_out.columns]
        
        st.success(f"Läste {len(df_out)} REId från Påverkbara-arket (korrigerad metod - DT som bas)")
        
        with st.expander("Debug: Kolumnmapping och sampel-data"):
            st.write("**Kolumnpositioner som användes:**")
            for field, pos in col_positions.items():
                index = col_indices[field]
                status = "✓" if field in found_cols else "✗"
                importance = "🔥" if field in ['B_raw', 'Adj', 'e_base'] else "📊" if 'excel' in field else ""
                st.write(f"{status} {importance} {field}: {pos} (index {index})")
            
            if missing_cols:
                st.write(f"**Saknade kolumner:** {missing_cols}")
            
            st.write("**KRITISK FÖRÄNDRING:** Använder nu DT (B_raw) som ren bas istället för att återställa från EA (y2024_base)")
            
            # Visa sampel av inläst data
            st.write("**Sampel av inlästa data:**")
            sample_cols = ['REId', 'B_raw', 'Adj', 'e_base', 'y2024_excel', 'total_excel']
            available_sample_cols = [c for c in sample_cols if c in df_out.columns]
            st.dataframe(df_out[available_sample_cols].head(3))

        return df_out

    except Exception as e:
        st.error(f"Fel vid läsning av Påverkbara-arket: {e}")
        import traceback
        st.code(traceback.format_exc())
        return None

def export_ir_paverkbara_scenario(export_data: pd.DataFrame, scenario_name: str) -> Tuple[str, str]:
    """Exporterar påverkbara kostnader till IR-dekompositionen. Returnerar (data_path, meta_path)."""
    
    # Skapa export-katalog - rätt sökväg enligt din specifikation
    export_dir = Path("scenario/effektiviseringskrav/exports_to_ir")
    export_dir.mkdir(parents=True, exist_ok=True)
    
    # Skapa filnamn med timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    safe_name = "".join(c for c in scenario_name if c.isalnum() or c in ['_', '-']).lower()
    filename = f"ir_paverkbara_{safe_name}_{timestamp}.parquet"
    filepath = export_dir / filename
    
    # Förbered final export-data (endast nödvändiga kolumner för IR)
    final_export = export_data[[
        'DMU', 'REId', 'Företag', 
        'Paverkbara_Baseline_4yr', 'Paverkbara_Target', 
        'Effektiviseringskrav', 'Total_Reduction_tkr',
        'Analysis_Method', 'Export_Timestamp'
    ]].copy()
    
    # Exportera som parquet
    final_export.to_parquet(filepath, index=False)
    
    # Skapa metadata-fil
    metadata = {
        "description": "Påverkbara kostnader baserat på DEA-effektiviseringskrav för IR-dekomposition (Ei-korrekt metod)",
        "scenario_name": scenario_name,
        "analysis_method": "DEA_corrected_exact_columns",
        "export_timestamp": datetime.now().isoformat(),
        "price_year": 2022,
        "unit": "tkr",
        "level": "REId",
        "period": "2024-2027",
        "formula": "Ei-korrekt: B_eff återställd från baseline, μ-faktor från 2024/2025-förhållande",
        "reid_count": len(final_export),
        "total_baseline_tkr": int(final_export['Paverkbara_Baseline_4yr'].sum()),
        "total_target_tkr": int(final_export['Paverkbara_Target'].sum()),
        "total_reduction_tkr": int(final_export['Total_Reduction_tkr'].sum()),
        "method_details": {
            "step1": "B_eff = y2024_base / (1 - e_base)",
            "step2": "μ = 1 - e_base - (y2025_base / y2024_base)",
            "step3": "y_t_scn = y_{t-1}_scn * (1 - e_scn - μ) for t > 2024",
            "step4": "Totalsumma_scn = sum(y2024_scn + y2025_scn + y2026_scn + y2027_scn)"
        }
    }
    
    metadata_path = filepath.with_suffix('.json')
    with open(metadata_path, 'w', encoding='utf-8') as f:
        import json
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    
    return str(filepath), str(metadata_path)

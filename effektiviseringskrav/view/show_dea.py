import streamlit as st
import pandas as pd
import numpy as np
import io, json, os
from datetime import datetime
from pathlib import Path
from typing import Tuple, Optional

from effektiviseringskrav.app.dea_model import run_dea_model
from effektiviseringskrav.app.plots import (
    plot_efficiency_histogram,
)
# NYTT: scenariomerge från data_loader
from effektiviseringskrav.app.data_loader import merge_capex_scenario
from core.session_utils import get_user_org, ensure_org_dir

def show_dea_view(df):
    st.header("DEA-modell")
    st.sidebar.subheader("DEA-parametrar")
    st.warning("NOTERA: Om man kör Ei:s standard-DEA så får man exakt samma påverkbara kostnader för alla företag förutom LKAB nät (delta -23 tkr) och Jukkasjärvi (delta -238 tkr). Anledningen är att vi får små skillnader i uppskattade krav (1,75% hos Ei vs. 1,82% här för LKAB och 1,50% hos Ei vs. 1,62% här Jukkasjärvi), oklart varför.")
  
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
                    export_data = calculate_ir_paverkbara_export_fixed(result, ir_baseline_file)
                    
                    if export_data is not None and not export_data.empty:
                        # TVINGA float64 för alla kritiska kolumner
                        float_cols = [
                            'Paverkbara_Baseline_4yr', 'Paverkbara_Target', 'Total_Reduction_tkr',
                            'Y2024_scenario', 'Y2025_scenario', 'Y2026_scenario', 'Y2027_scenario',
                            'Y2024_baseline', 'Y2025_baseline', 'Y2026_baseline', 'Y2027_baseline'
                        ]
                        
                        for col in float_cols:
                            if col in export_data.columns:
                                export_data[col] = export_data[col].astype(np.float64)
                        
                        st.write("**FORCE-KONVERTERING TILLÄMPAT**")
                        st.write("Nya datatyper:")
                        for col in float_cols:
                            if col in export_data.columns:
                                st.write(f"- {col}: {export_data[col].dtype}")

                    if export_data is not None and not export_data.empty:
                        debug_precision_step_by_step(export_data, "REL00015")
                    
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

def calculate_ir_paverkbara_export_fixed(dea_result: pd.DataFrame, ir_baseline_file: str) -> Optional[pd.DataFrame]:
    """
    KORRIGERAD beräkning av påverkbara kostnader med Excel-exakt precision.
    
    Huvudändringar:
    1. Behåll FULLSTÄNDIG precision genom hela beräkningen
    2. Avrunda ENDAST slutresultatet för varje år
    3. Använd exakta värden från Excel, inte föravrundade
    """
    
    # Ladda IR baseline-data
    ir_baseline = load_ir_paverkbara_baseline(ir_baseline_file)
    if ir_baseline is None:
        return None
    
    # Robust kolumnhantering för DEA-resultat
    available_cols = list(dea_result.columns)
    
    # Leta efter företagskolumn
    foretag_col = None
    for col in available_cols:
        if any(variant in col.lower() for variant in ['företag', 'foretag', 'företag', 'fÃƒÂ¶retag']):
            foretag_col = col
            break
    
    required_cols = ['DMU', 'REId', 'Effkrav_proc']
    if foretag_col:
        required_cols.append(foretag_col)
    
    # Kontrollera kolumner
    missing_cols = [col for col in required_cols if col not in available_cols]
    if missing_cols:
        st.error(f"DEA-resultat saknar kolumner: {missing_cols}")
        return None
    
    # Skapa export-data
    export_data = dea_result[required_cols].copy()
    if foretag_col and foretag_col != 'Företag':
        export_data = export_data.rename(columns={foretag_col: 'Företag'})
    
    # Merge med IR baseline
    export_data = export_data.merge(ir_baseline, on='REId', how='left')
    
    # Filtrera till kompletta data
    required_baseline_cols = ['B_raw', 'e_base']
    complete_mask = export_data[required_baseline_cols].notna().all(axis=1)
    
    if (~complete_mask).sum() > 0:
        st.warning(f"{(~complete_mask).sum()} REId saknar baseline-data och exkluderas")
    
    export_data = export_data[complete_mask].copy()
    if export_data.empty:
        st.error("Ingen REId har komplett baseline-data")
        return None
    
    # === KRITISK FIX: Använd EXAKT precision från Excel ===
    # Konvertera till float64 för maximal precision
    DT = export_data['B_raw'].astype(np.float64)
    DU = export_data.get('Adj', 0).astype(np.float64).fillna(0.0)
    e_base = export_data['e_base'].astype(np.float64)
    e_scn = export_data['Effkrav_proc'].astype(np.float64)
    
    # Årlig fördelning av NeonAndringar med full precision
    Delta = DU / 4.0
    
    # Bas för procentberäkning med full precision
    B = DT + Delta
    
    def excel_half_up_round(x):
        """Excel-exakt half-up avrundning"""
        import math
        return int(math.floor(float(x) + 0.5))
    
    def calculate_exact_yearly_values(DT_series, DU_series, e_series):
        """Beräknar årsvärden med Excel-exakt precision och avrundning"""
        results = []
        
        for dt_val, du_val, e_val in zip(DT_series, DU_series, e_series):
            # Konvertera till float64 för maximal precision
            dt = np.float64(dt_val)
            du = np.float64(du_val)
            e = np.float64(e_val)
            delta = du / 4.0
            B_val = dt + delta
            
            # Beräkna årliga inkrement med FULLSTÄNDIG precision
            # NYTT: Behåll både exakta och avrundade värden separat
            inc_exact_vals = []
            inc_rounded_vals = []
            avdrag_vals = []

            for t in range(1, 5):  # t = 1,2,3,4 för åren 2024-2027
                # Beräkna inkrement med full precision
                growth_factor = (1.0 + e) ** (t - 1)
                inc_exact = e * B_val * growth_factor
                
                # Spara exakt värde för kumulativ summa
                inc_exact_vals.append(inc_exact)
                
                # Avrunda för kompatibilitet (används vid rapportering)
                inc_rounded = excel_half_up_round(inc_exact)
                inc_rounded_vals.append(inc_rounded)
                
                # KRITISK FIX: Kumulativt avdrag baserat på EXAKTA värden
                avdrag_kum = sum(inc_exact_vals)
                avdrag_vals.append(avdrag_kum)
            
            # Beräkna årsvärden: Y_t = DT - Avdrag_t + Δ
            # VIKTIGT: Avrunda slutresultatet, inte mellanstegen
            year_vals = []
            for avdrag in avdrag_vals:
                y_exact = dt - avdrag + delta
                year_vals.append(y_exact)  # Behåll decimaler!

            
            results.append({
                'inc': inc_rounded_vals,      # Avrundade för visning
                'inc_exact': inc_exact_vals,  # Exakta för beräkning
                'avdrag': avdrag_vals,        # Baserat på exakta värden
                'years': year_vals,
                'B': B_val,
                'total': sum(year_vals)
            })
        
        return results
    
    # === SCENARIO-BERÄKNING ===
    scn_results = calculate_exact_yearly_values(DT, DU, e_scn)
    
    # === BASELINE-BERÄKNING ===
    base_results = calculate_exact_yearly_values(DT, DU, e_base)
    
    # === EXTRAHERA RESULTAT ===
    # Scenario-värden
    y2024_scn = np.array([r['years'][0] for r in scn_results])
    y2025_scn = np.array([r['years'][1] for r in scn_results])
    y2026_scn = np.array([r['years'][2] for r in scn_results])
    y2027_scn = np.array([r['years'][3] for r in scn_results])
    total_4yr_scn = np.array([r['total'] for r in scn_results])
    
    # Baseline-värden
    y2024_base = np.array([r['years'][0] for r in base_results])
    y2025_base = np.array([r['years'][1] for r in base_results])
    y2026_base = np.array([r['years'][2] for r in base_results])
    y2027_base = np.array([r['years'][3] for r in base_results])
    total_4yr_base = np.array([r['total'] for r in base_results])
    
    # === SKAPA EXPORT-DATAFRAME ===
    # Behåll decimaler för att matcha Excel exakt
    export_data['Paverkbara_Baseline_4yr'] = total_4yr_base
    export_data['Paverkbara_Target'] = total_4yr_scn
    export_data['Total_Reduction_tkr'] = total_4yr_base - total_4yr_scn
    export_data['Effektiviseringskrav'] = e_scn
    
    # Lägg till årsvisa värden för debugging
    export_data['Y2024_scenario'] = y2024_scn
    export_data['Y2025_scenario'] = y2025_scn
    export_data['Y2026_scenario'] = y2026_scn
    export_data['Y2027_scenario'] = y2027_scn
    
    export_data['Y2024_baseline'] = y2024_base
    export_data['Y2025_baseline'] = y2025_base
    export_data['Y2026_baseline'] = y2026_base
    export_data['Y2027_baseline'] = y2027_base
    
    # Debug-information med full precision
    export_data['DT_exact'] = DT
    export_data['DU_exact'] = DU
    export_data['Delta_exact'] = Delta
    export_data['B_exact'] = B
    export_data['e_base_exact'] = e_base
    export_data['e_scn_exact'] = e_scn
    
    # Lägg till inkrement för transparens
    for i, year in enumerate([2024, 2025, 2026, 2027]):
        export_data[f'Inc_{year}_scn'] = [r['inc'][i] for r in scn_results]
        export_data[f'Avdrag_{year}_scn'] = [r['avdrag'][i] for r in scn_results]
        export_data[f'Inc_{year}_base'] = [r['inc'][i] for r in base_results]
        export_data[f'Avdrag_{year}_base'] = [r['avdrag'][i] for r in base_results]
    
    # Sanity check mot Excel-värden om de finns
    if 'y2024_excel' in export_data.columns:
        y2024_excel = export_data['y2024_excel'].astype(float)
        diff_2024 = np.abs(y2024_base - y2024_excel)
        export_data['Sanity_2024_diff'] = diff_2024
        
        # Rapportera sanity check
        max_diff = diff_2024.max()
        avg_diff = diff_2024.mean()
        st.info(f"Sanity check 2024: Max avvikelse {max_diff:.1f} tkr, Medel {avg_diff:.2f} tkr")
    
    if 'total_excel' in export_data.columns:
        total_excel = export_data['total_excel'].astype(float)
        diff_total = np.abs(total_4yr_base - total_excel)
        export_data['Sanity_total_diff'] = diff_total
        
        max_diff = diff_total.max()
        avg_diff = diff_total.mean()
        st.info(f"Sanity check total: Max avvikelse {max_diff:.1f} tkr, Medel {avg_diff:.2f} tkr")
    
    export_data['Analysis_Method'] = 'Excel_exact_precision_fixed'
    export_data['Export_Timestamp'] = datetime.now().isoformat()
    
    # === ENHANCED DEBUG för specifik REId ===
    debug_reid = 'REL00015'
    debug_mask = export_data['REId'] == debug_reid
    if debug_mask.any():
        debug_row = export_data[debug_mask].iloc[0]
        
        with st.expander(f"🔧 KORRIGERAD debug för {debug_reid}"):
            st.write("**FÖRE FIX vs EFTER FIX:**")
            
            # Visa exakta input-värden
            st.write(f"- DT (exakt): {debug_row['DT_exact']:,.6f} tkr")
            st.write(f"- DU (exakt): {debug_row['DU_exact']:,.6f} tkr")
            st.write(f"- Δ (exakt): {debug_row['Delta_exact']:,.6f} tkr")
            st.write(f"- B (exakt): {debug_row['B_exact']:,.6f} tkr")
            st.write(f"- e_scn (exakt): {debug_row['e_scn_exact']:.10f}")
            
            st.write("**KORRIGERADE årliga inkrement (scenario):**")
            for i, year in enumerate([2024, 2025, 2026, 2027]):
                inc_val = debug_row[f'Inc_{year}_scn']
                avdrag_val = debug_row[f'Avdrag_{year}_scn']
                
                # Beräkna teoretiskt värde för jämförelse
                t = i + 1
                growth = (1.0 + debug_row['e_scn_exact']) ** (t - 1)
                teoretisk = debug_row['e_scn_exact'] * debug_row['B_exact'] * growth
                
                st.write(f"- **{year} (t={t})**: {teoretisk:.3f} → {inc_val:,} tkr (kum: {avdrag_val:,})")
            
            st.write("**KORRIGERADE årsnivåer:**")
            for year in [2024, 2025, 2026, 2027]:
                val_scn = debug_row[f'Y{year}_scenario']
                val_base = debug_row[f'Y{year}_baseline']
                st.write(f"- **{year}**: Scenario {val_scn:,} tkr, Baseline {val_base:,} tkr")
            
            st.write(f"**RESULTAT:**")
            st.write(f"- Total scenario: {debug_row['Paverkbara_Target']:,} tkr")
            st.write(f"- Total baseline: {debug_row['Paverkbara_Baseline_4yr']:,} tkr")
            st.write(f"- **Total reduktion: {debug_row['Total_Reduction_tkr']:,} tkr**")
            
            # Visa sanity check om tillgänglig
            if 'Sanity_total_diff' in debug_row.index:
                diff = debug_row['Sanity_total_diff']
                if abs(diff) < 1:
                    st.success(f"✅ Excel-match: {diff:.2f} tkr skillnad (PERFEKT)")
                elif abs(diff) < 5:
                    st.info(f"✅ Excel-match: {diff:.1f} tkr skillnad (OK)")
                else:
                    st.warning(f"⚠️ Excel-avvikelse: {diff:.1f} tkr")
    
    return export_data

def debug_precision_step_by_step(export_data: pd.DataFrame, debug_reid: str = 'REL00015'):
    """
    Detaljerad debug som spårar exakt var precision förloras i beräkningarna.
    """
    
    # Hitta debug-raden
    debug_mask = export_data['REId'] == debug_reid
    if not debug_mask.any():
        st.error(f"Debug REId {debug_reid} hittades inte")
        return
    
    debug_row = export_data[debug_mask].iloc[0]
    
    with st.expander(f"🔬 STEG-FÖR-STEG PRECISION DEBUG för {debug_reid}"):
        st.write("**SPÅRNING AV DATATYPER OCH VÄRDEN**")
        
        # === STEG 1: INPUT-VÄRDEN ===
        st.write("### STEG 1: Input-värden från Excel")
        dt_raw = debug_row.get('DT_exact', debug_row.get('B_raw', 0))
        du_raw = debug_row.get('DU_exact', debug_row.get('Adj', 0))
        e_scn_raw = debug_row.get('e_scn_exact', debug_row.get('Effkrav_proc', 0))
        
        st.code(f"""
DT_raw = {dt_raw} (type: {type(dt_raw)})
DU_raw = {du_raw} (type: {type(du_raw)})
e_scn_raw = {e_scn_raw} (type: {type(e_scn_raw)})
        """)
        
        # === STEG 2: KONVERTERING TILL NUMPY ===
        st.write("### STEG 2: Konvertering till beräkningsformat")
        import numpy as np
        
        dt_calc = np.float64(dt_raw)
        du_calc = np.float64(du_raw)
        e_calc = np.float64(e_scn_raw)
        delta_calc = du_calc / 4.0
        b_calc = dt_calc + delta_calc
        
        st.code(f"""
dt_calc = np.float64({dt_raw}) = {dt_calc} (type: {type(dt_calc)})
du_calc = np.float64({du_raw}) = {du_calc} (type: {type(du_calc)})
e_calc = np.float64({e_scn_raw}) = {e_calc} (type: {type(e_calc)})
delta_calc = {du_calc} / 4.0 = {delta_calc} (type: {type(delta_calc)})
b_calc = {dt_calc} + {delta_calc} = {b_calc} (type: {type(b_calc)})
        """)
        
        # === STEG 3: BERÄKNING AV INKREMENT ===
        st.write("### STEG 3: Årliga inkrement (med Excel half-up avrundning)")
        
        def excel_half_up_round(x):
            import math
            return int(math.floor(float(x) + 0.5))
        
        inc_exact = []
        inc_rounded = []
        avdrag_kum = []
        
        for t in range(1, 5):
            growth_factor = (1.0 + e_calc) ** (t - 1)
            inc_exact_val = e_calc * b_calc * growth_factor
            inc_rounded_val = excel_half_up_round(inc_exact_val)
            
            inc_exact.append(inc_exact_val)
            inc_rounded.append(inc_rounded_val)
            
            # Kumulativt avdrag
            avdrag_val = sum(inc_rounded[:t])
            avdrag_kum.append(avdrag_val)
            
            st.code(f"""
År {2023+t} (t={t}):
  growth_factor = (1 + {e_calc})^({t}-1) = {growth_factor}
  inc_exact = {e_calc} × {b_calc} × {growth_factor} = {inc_exact_val}
  inc_rounded = excel_half_up({inc_exact_val}) = {inc_rounded_val}
  avdrag_kumulativt = {avdrag_val} (type: {type(avdrag_val)})
            """)
        
        # === STEG 4: BERÄKNING AV ÅRSVÄRDEN ===
        st.write("### STEG 4: Årsvärden (Y_t = DT - Avdrag_t + Δ)")
        
        year_values_exact = []
        year_values_stored = []
        
        for i, avdrag in enumerate(avdrag_kum):
            year = 2024 + i
            
            # Exakt beräkning
            y_exact = dt_calc - avdrag + delta_calc
            year_values_exact.append(y_exact)
            
            # Vad som faktiskt lagras i export_data
            stored_val = debug_row.get(f'Y{year}_scenario', 'SAKNAS')
            year_values_stored.append(stored_val)
            
            st.code(f"""
År {year}:
  y_exact = {dt_calc} - {avdrag} + {delta_calc} = {y_exact}
  type(y_exact) = {type(y_exact)}
  LAGRAD I export_data = {stored_val} (type: {type(stored_val)})
  PRECISION FÖRLUST = {abs(float(y_exact) - float(stored_val)) if stored_val != 'SAKNAS' else 'N/A'}
            """)
        
        # === STEG 5: TOTALSUMMA ===
        st.write("### STEG 5: Totalsumma")
        
        total_exact = sum(year_values_exact)
        total_stored = debug_row.get('Paverkbara_Target', 'SAKNAS')
        
        st.code(f"""
total_exact = sum({[round(y, 3) for y in year_values_exact]}) = {total_exact}
type(total_exact) = {type(total_exact)}
LAGRAD total = {total_stored} (type: {type(total_stored)})
TOTAL PRECISION FÖRLUST = {abs(float(total_exact) - float(total_stored)) if total_stored != 'SAKNAS' else 'N/A'}
        """)
        
        # === STEG 6: DATAFRAME KOLUMNTYPER ===
        st.write("### STEG 6: DataFrame kolumntyper")
        
        relevant_cols = [col for col in export_data.columns if any(x in col for x in ['Y202', 'Paverkbara', 'Target', 'scenario'])]
        
        st.write("**Datatyper i export_data:**")
        for col in relevant_cols:
            if col in export_data.columns:
                dtype = export_data[col].dtype
                sample_val = debug_row[col] if col in debug_row.index else 'SAKNAS'
                st.code(f"{col}: {dtype} (värde: {sample_val})")
        
        # === STEG 7: JÄMFÖRELSE MED EXCEL ===
        st.write("### STEG 7: Jämförelse med Excel-referens")
        
        excel_values = {
            2024: 46192.839,
            2025: 45721.579, 
            2026: 45245.606,
            2027: 44764.874
        }
        excel_total = sum(excel_values.values())
        
        st.write("**Excel vs Beräknat vs Lagrat:**")
        for i, year in enumerate([2024, 2025, 2026, 2027]):
            excel_val = excel_values[year]
            calc_val = year_values_exact[i]
            stored_val = year_values_stored[i]
            
            calc_diff = abs(excel_val - calc_val) if calc_val else float('inf')
            stored_diff = abs(excel_val - float(stored_val)) if stored_val != 'SAKNAS' else float('inf')
            
            st.code(f"""
{year}: Excel={excel_val}, Beräknat={calc_val:.3f}, Lagrat={stored_val}
       Calc diff={calc_diff:.6f}, Stored diff={stored_diff:.6f}
            """)
        
        st.code(f"""
TOTALER:
Excel total = {excel_total}
Beräknad total = {total_exact}
Lagrad total = {total_stored}
Skillnad Excel vs Beräknad = {abs(excel_total - total_exact):.6f}
Skillnad Excel vs Lagrad = {abs(excel_total - float(total_stored)) if total_stored != 'SAKNAS' else 'N/A'}
        """)
        
        # === SLUTSATS ===
        st.write("### 🎯 SLUTSATS")
        
        if total_stored != 'SAKNAS':
            precision_loss = abs(total_exact - float(total_stored))
            if precision_loss > 0.001:
                st.error(f"❌ PRECISION FÖRLUST UPPTÄCKT: {precision_loss:.3f} tkr förlorades mellan beräkning och lagring")
                st.write("**Trolig orsak:** Konvertering till integer eller float32 någonstans i koden")
            else:
                st.success("✅ Beräkning till lagring: OK (minimal precision förlust)")
        
        excel_diff = abs(excel_total - float(total_stored)) if total_stored != 'SAKNAS' else float('inf')
        if excel_diff < 0.1:
            st.success("✅ Excel-matchning: PERFEKT")
        elif excel_diff < 1.0:
            st.info(f"✅ Excel-matchning: BRA ({excel_diff:.3f} tkr skillnad)")
        else:
            st.warning(f"⚠️ Excel-matchning: Problem ({excel_diff:.3f} tkr skillnad)")

# Använd denna funktion i show_dea_view efter export_data skapas:
# debug_precision_step_by_step(export_data, "REL00015")


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
    """
    UPPDATERAD: Exporterar påverkbara kostnader till organisationsspecifik katalog.
    Returnerar (data_path, meta_path).
    """
    
    # Skapa organisationsspecifik export-katalog
    base_export_dir = "scenario/effektiviseringskrav/exports_to_ir"
    export_dir = Path(ensure_org_dir(base_export_dir))
    
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
        "description": "Påverkbara kostnader baserat på DEA-effektiviseringskrav för IR-dekomposition",
        "scenario_name": scenario_name,
        "organization": get_user_org(),
        "analysis_method": "DEA_corrected_exact_columns",
        "export_timestamp": datetime.now().isoformat(),
        "price_year": 2022,
        "unit": "tkr",
        "level": "REId",
        "period": "2024-2027",
        "reid_count": len(final_export),
        "total_baseline_tkr": int(final_export['Paverkbara_Baseline_4yr'].sum()),
        "total_target_tkr": int(final_export['Paverkbara_Target'].sum()),
        "total_reduction_tkr": int(final_export['Total_Reduction_tkr'].sum()),
    }
    
    metadata_path = filepath.with_suffix('.json')
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    
    return str(filepath), str(metadata_path)
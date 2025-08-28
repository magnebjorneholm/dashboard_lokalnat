import streamlit as st
import pandas as pd
import numpy as np
import io
from datetime import datetime
from pathlib import Path
from typing import Tuple

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
        st.caption("Beräknar påverkbara kostnader för 2024-2027 perioden baserat på effektiviseringskraven")
        
        # Kontrollera att vi har nödvändiga kolumner
        if 'OPEXp' not in result.columns or 'Effkrav_proc' not in result.columns:
            st.error("Export kräver både OPEXp och Effkrav_proc. Kontrollera att DEA-modellen inkluderar OPEXp som input.")
        else:
            # Beräkna påverkbara kostnader enligt 4-årsformeln
            export_data = calculate_ir_paverkbara_export(result)
            
            # Visa sammanfattning av exporten
            col1, col2, col3 = st.columns(3)
            with col1:
                total_baseline = export_data['Paverkbara_Baseline'].sum() / 1000  # MSEK
                st.metric("Baseline OPEX totalt", f"{total_baseline:.1f} MSEK")
            with col2:
                total_target = export_data['Paverkbara_Target'].sum() / 1000  # MSEK
                st.metric("Efter effektiviseringskrav", f"{total_target:.1f} MSEK")
            with col3:
                total_reduction = export_data['Total_Reduction_tkr'].sum() / 1000  # MSEK
                reduction_pct = (total_reduction / total_baseline) * 100
                st.metric("Total reduktion", f"{total_reduction:.1f} MSEK ({reduction_pct:.1f}%)")
            
            # Visa preview av export-data
            with st.expander("Förhandsvisning av export-data"):
                preview_data = export_data[['DMU', 'Företag', 'Paverkbara_Baseline', 'Effektiviseringskrav', 'Paverkbara_Target', 'Total_Reduction_tkr']].copy()
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
            
            with col_export2:
                # Alternativ Excel-download
                buffer = create_ir_export_excel(export_data)
                st.download_button(
                    label="Ladda ned som Excel",
                    data=buffer.getvalue(),
                    file_name=f"ir_paverkbara_export_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

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


def calculate_ir_paverkbara_export(dea_result: pd.DataFrame) -> pd.DataFrame:
    """
    Beräknar påverkbara kostnader för IR-export baserat på 4-årsformeln.
    
    Formel: Sum_OPEX_2024_27 = B × (1-e) × (1-(1-e)^4) / e
    där B = OPEXp (baseline) och e = Effkrav_proc (årligt krav)
    """
    export_data = dea_result[['DMU', 'REId', 'Företag', 'OPEXp', 'Effkrav_proc']].copy()
    
    # Säkerhetscheck
    export_data = export_data.dropna(subset=['OPEXp', 'Effkrav_proc'])
    
    B = export_data['OPEXp'].astype(float)  # Baseline OPEX (tkr)
    e = export_data['Effkrav_proc'].astype(float)  # Årligt krav (decimal)
    
    # Beräkna enligt 4-årsformeln (closed form)
    # Sum_OPEX_2024_27 = B × (1-e) × (1-(1-e)^4) / e
    # Men för e=0 behövs specialbehandling
    r = 1 - e  # (1-e)
    
    # Använd formeln där e > 0, annars baseline × 4
    sum_opex = np.where(
        e > 0,
        B * r * (1 - r**4) / e,
        B * 4  # Om inget krav (e=0) blir summan 4×baseline
    )
    
    # Avrunda till heltal (tkr)
    sum_opex = np.round(sum_opex).astype(int)
    
    # Beräkna totalt avdrag
    total_reduction = (B * 4) - sum_opex
    
    # Skapa export-dataframe
    export_data['Paverkbara_Baseline'] = B.astype(int)
    export_data['Paverkbara_Target'] = sum_opex
    export_data['Total_Reduction_tkr'] = total_reduction.astype(int)
    export_data['Effektiviseringskrav'] = e  # Behåll som decimal för referens
    export_data['Analysis_Method'] = 'DEA'
    export_data['Export_Timestamp'] = datetime.now().isoformat()
    
    return export_data


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
        'Paverkbara_Baseline', 'Paverkbara_Target', 
        'Effektiviseringskrav', 'Total_Reduction_tkr',
        'Analysis_Method', 'Export_Timestamp'
    ]].copy()
    
    # Exportera som parquet
    final_export.to_parquet(filepath, index=False)
    
    # Skapa metadata-fil
    metadata = {
        "description": "Påverkbara kostnader baserat på DEA-effektiviseringskrav för IR-dekomposition",
        "scenario_name": scenario_name,
        "analysis_method": "DEA",
        "export_timestamp": datetime.now().isoformat(),
        "price_year": 2022,
        "unit": "tkr",
        "level": "DMU",
        "period": "2024-2027",
        "formula": "4-års ackumulerat krav: Sum = B × (1-e) × (1-(1-e)^4) / e",
        "dmu_count": len(final_export),
        "total_baseline_tkr": int(final_export['Paverkbara_Baseline'].sum()),
        "total_target_tkr": int(final_export['Paverkbara_Target'].sum()),
        "total_reduction_tkr": int(final_export['Total_Reduction_tkr'].sum())
    }
    
    metadata_path = filepath.with_suffix('.json')
    with open(metadata_path, 'w', encoding='utf-8') as f:
        import json
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    
    return str(filepath), str(metadata_path)


def create_ir_export_excel(export_data: pd.DataFrame) -> io.BytesIO:
    """Skapar Excel-export av IR påverkbara kostnader data."""
    buffer = io.BytesIO()
    
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        # Huvuddata
        main_data = export_data[[
            'DMU', 'REId', 'Företag', 'Paverkbara_Baseline', 
            'Paverkbara_Target', 'Total_Reduction_tkr', 'Effektiviseringskrav'
        ]].copy()
        
        main_data['Effektiviseringskrav'] = (main_data['Effektiviseringskrav'] * 100).round(2)
        main_data = main_data.rename(columns={'Effektiviseringskrav': 'Årligt krav (%)'})
        
        main_data.to_excel(writer, sheet_name='IR_Påverkbara_Export', index=False)
        
        # Sammanfattning
        summary_data = [
            ['Total baseline OPEX (tkr)', export_data['Paverkbara_Baseline'].sum()],
            ['Total efter krav (tkr)', export_data['Paverkbara_Target'].sum()],
            ['Total reduktion (tkr)', export_data['Total_Reduction_tkr'].sum()],
            ['Antal DMU', len(export_data)],
            ['Medel årligt krav (%)', (export_data['Effektiviseringskrav'].mean() * 100).round(2)],
            ['Export-datum', datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
        ]
        
        summary_df = pd.DataFrame(summary_data, columns=['Metrik', 'Värde'])
        summary_df.to_excel(writer, sheet_name='Sammanfattning', index=False)
    
    return buffer
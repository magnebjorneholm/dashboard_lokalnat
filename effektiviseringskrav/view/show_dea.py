import streamlit as st
import pandas as pd
import io

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
        st.sidebar.info(f"WACC-scenario hittat: {scen_info['tag'].replace('p','.')}  •  täckning {scen_info['coverage']:.0%}")
    else:
        st.sidebar.caption("Ingen CAPEX-scenariofil hittad under scenario/kapitalbas/exports_to_dea/ ännu.")

    st.sidebar.caption(
        "**Inputs**\n"
        "- `CAPEX + OPEXp`: separata poster – kan visa om ineffektivitet ligger i kapital eller drift.\n"
        "- `TOTEX`: summererar kostnader – totalbedömning, bortser från kostnadsstruktur.\n"
        "- `…_wacc_…`: scenario exporterat från Kapitalbas (2024, tkr, prisår 2022)."
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
    st.sidebar.caption("**Skalavkastning (RTS)**\n- `crs`: Konstant skalavkastning.\n- `vrs`: Variabel skalavkastning.")
    dea_rts = st.sidebar.selectbox("Skalavkastning (RTS)", ["crs", "vrs"], index=0)

    st.sidebar.caption("**Trunkering av intäktsreduktion**\nAnger hur mycket ineffektivitet (1 − effektivitet) får påverka kraven.")
    dea_trunk_min = st.sidebar.slider("Minsta trunkering", 0.0, 0.3, 0.162416, step=0.005)
    dea_trunk_max = st.sidebar.slider("Högsta trunkering", 0.1, 0.5, 0.3, step=0.005)

    dea_outlier_krav = st.sidebar.slider(
        "Årligt krav för outliers (%)",
        1.0, 1.82, 1.0, 0.01,
        help="Vilket fast krav (i procent) ska ges till företag som klassas som outliers?"
    )

    # --- Körmodellknapp ---
    run_model = st.sidebar.button("Kör DEA")

    if run_model:
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

        df_outliers = result[result["is_outlier"] == True][["Företag", "Effektivitet", "Supereffektivitet", "Effkrav_proc"]]
        df_outliers["Effkrav_proc"] = df_outliers["Effkrav_proc"].round(4)

        n_outliers = len(df_outliers)
        if n_outliers > 0:
            st.warning(f"{n_outliers} företag har identifierats som outliers, exkluderats från fronten och tilldelats ett fast årligt effektiviseringskrav på {dea_outlier_krav:.1f} %.")
            st.dataframe(df_outliers)
        else:
            st.info("Inga outliers identifierades i denna körning.")

        st.dataframe(result[["Företag", "Effektivitet", "Supereffektivitet", "Effkrav_proc"]])
        df_plot = result[result["is_outlier"] == False]
        plot_efficiency_histogram(df_plot["Effektivitet"], title="DEA: Effektivitet (utan outliers)")
        plot_efficiency_histogram(df_plot["Supereffektivitet"], title="DEA: Supereffektivitet (utan outliers)")
        plot_efficiency_histogram(df_plot["Effkrav_proc"] * 100, title="DEA: Årligt effektiviseringskrav (%) (utan outliers)")

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            result.to_excel(writer, sheet_name="Resultat", index=False)

        st.download_button(
            label="Ladda ned resultat för DEA-modellen som Excel",
            data=buffer.getvalue(),
            file_name="resultat_dea.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("Välj modellspecifikationer och klicka på 'Kör DEA-modellen' för att se resultat.")
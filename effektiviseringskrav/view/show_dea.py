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

    # --- Försök merga CAPEX-scenario från dea_exports/ (om fil finns) ---
    df_merged, scen_info = merge_capex_scenario(df)
    df = df_merged

    # --- Kolumnval ---
    all_inputs = ["CAPEX", "OPEXp", "TOTEX"]
    all_outputs = ["CU", "MW", "NS", "MWhl", "MWhh"]

    # Lägg till scenariokolumner (om upptäckta)
    if scen_info is not None:
        capex_wacc_col = scen_info["capex_col"]  # t.ex. CAPEX_2024_wacc_0p0475_tkr
        totex_wacc_col = scen_info["totex_col"]  # t.ex. TOTEX_wacc_0p0475
        all_inputs.extend([capex_wacc_col, totex_wacc_col])
        st.sidebar.info(f"Scenario\nupptäckt: WACC = {scen_info['tag'].replace('p','.')}")
    else:
        capex_wacc_col = None
        totex_wacc_col = None

    st.sidebar.caption(
        "**Inputs**\n"
        "- `CAPEX + OPEXp`: separata poster – kan visa om ineffektivitet ligger i kapital eller drift.\n"
        "- `TOTEX`: summerar kostnader – totalbedömning, bortser från kostnadsstruktur.\n"
        "- `…_wacc_…`: scenario exporterat från kapitalbasens Tab 3 (2024, tkr)."
    )

    # Default: CAPEX + OPEXp (som tidigare)
    input_cols = st.sidebar.multiselect("Välj inputvariabler", all_inputs, default=["CAPEX", "OPEXp"])

    # Exklusivitetsregler (uppdaterad logik för att undvika dubbelräkning)
    has_capex_std  = "CAPEX" in input_cols
    has_capex_scen = any(col.startswith("CAPEX_2024_wacc_") for col in input_cols)
    has_opexp      = "OPEXp" in input_cols
    has_totex_std  = "TOTEX" in input_cols
    has_totex_scen = any(col.startswith("TOTEX_wacc_") for col in input_cols)

    capex_any = has_capex_std or has_capex_scen
    totex_any = has_totex_std or has_totex_scen

    # Ogiltiga kombinationer (mer tillåtande UX):
    # (1) TOTEX i kombination med något annat (CAPEX eller OPEXp)
    # (2) Både standard- och scenariokolumn inom samma familj samtidigt
    # (3) Inga inputs valda
    if (totex_any and (capex_any or has_opexp)) \
       or ((has_capex_std and has_capex_scen) or (has_totex_std and has_totex_scen)):
        st.warning("Välj antingen enbart TOTEX, eller valfritt ur CAPEX (standard/scenario) och/eller OPEXp — men inte båda CAPEX-varianterna samtidigt, och kombinera aldrig TOTEX med andra.")
        st.stop()

    # Om scenario-input valts, säkerställ full täckning (inga NaN i valda scenariokolumner)
    if scen_info is not None and (
        (capex_wacc_col is not None and capex_wacc_col in input_cols) or
        (totex_wacc_col is not None and totex_wacc_col in input_cols)
        ):
        missing_cols = []
        for col in input_cols:
            if col in df.columns and df[col].isna().any():
                missing_cols.append(col)
        if missing_cols:
            st.error(
                "Scenario-kolumn saknar värden för alla DMU och kan inte användas:\n"
                f"- {', '.join(missing_cols)}\n\n"
                "Kontrollera exporten från kapitalbasen (nät utan DMU-match exkluderas)."
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
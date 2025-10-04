import streamlit as st
import pandas as pd
import io

from effektiviseringskrav.app.pystoned_model import run_pystoned_model
from effektiviseringskrav.app.plots import plot_efficiency_histogram

def show_pystoned_view(df):
    st.header("PyStoned-modell")
    st.sidebar.subheader("PyStoned-parametrar")

    all_inputs = ["CAPEX", "OPEXp", "TOTEX"]
    all_outputs = ["CU", "MW", "NS", "MWhl", "MWhh"]

    st.sidebar.caption("**Inputs**\n"
        "- `CAPEX + OPEXp`: Separata poster för investeringar och drift – visar om ineffektivitet ligger i kapital eller drift.\n"
        "- `TOTEX`: Summerar kostnaderna – ger en totalbedömning och bortser från kostnadsstruktur.")

    input_cols = st.sidebar.multiselect("Välj inputvariabler", all_inputs, default=["CAPEX", "OPEXp"])

    if "TOTEX" in input_cols and ("CAPEX" in input_cols or "OPEXp" in input_cols):
        st.warning("Välj antingen TOTEX eller CAPEX+OPEXp, inte båda samtidigt.")
        st.stop()

    output_cols = st.sidebar.multiselect("Välj outputvariabler", all_outputs, default=["CU"])
    use_outlier_filter = st.sidebar.checkbox("Filtrera bort outliers före beräkning", value=True)

    if not input_cols or not output_cols:
        st.warning("Välj minst en input och en output för att köra modellen.")
        st.stop()

    st.sidebar.caption("**Skalavkastning (RTS)**\n"
                       "- `crs`: Konstant skalavkastning – output ökar proportionellt med input.\n"
                       "- `vrs`: Variabel skalavkastning – tillåter t.ex. stordriftsfördelar.")
    rts_val = st.sidebar.selectbox("Skalavkastning (RTS)", ["crs", "vrs"], index=0)

    st.sidebar.caption("**Funktionstyp**\n"
                       "- `prod`: Produktionsfunktion – ineffektivitet tolkas som outputförlust.\n"
                       "- `cost`: Kostnadsfunktion – ineffektivitet tolkas som överskott i kostnader.")
    fun_val = st.sidebar.selectbox("Funktionstyp", ["prod", "cost"], index=0)

    st.sidebar.caption("**Teknologi (CET)**\n"
                       "- `addi`: Additiv teknologi – tillåter absoluta skillnader i ineffektivitet.\n"
                       "- `mult`: Multiplikativ teknologi – kräver särskild solver (`ipopt`) och används sällan i prototyper.")
    cet_val = st.sidebar.selectbox("Teknologi (CET)", ["addi", "mult"], index=0)

    kravmetod = st.sidebar.radio(
        "Metod för att beräkna effektivitetskrav (endast för PyStoned):",
        options=["absolut", "percentilbaserat"],
        index=0,
        help="Välj om kravet ska baseras direkt på ineffektivitet (1 - effektivitet) eller anpassas efter fördelningen av ineffektivitet."
    )

    st.sidebar.caption("**Trunkering av intäktsreduktion**\n"
                       "Anger hur mycket ineffektivitet (1 − effektivitet) får påverka kraven.\n"
                       "- Högre max → större möjliga krav\n"
                       "- Lägre min → fler företag får krav även vid låg ineffektivitet")
    trunk_min = st.sidebar.slider("Minsta trunkering", 0.0, 0.3, 0.162416, step=0.005)
    trunk_max = st.sidebar.slider("Högsta trunkering", 0.1, 0.5, 0.3, step=0.005)

    run_model = st.sidebar.button("Kör PyStoned")

    if cet_val == "mult":
        st.warning("Teknologin 'mult' kräver solvern 'ipopt', som inte är tillgänglig i din miljö. Välj 'addi' istället.")
        st.stop()

    if run_model:
        result = run_pystoned_model(
            df,
            rts=rts_val,
            fun=fun_val,
            cet=cet_val,
            trunkering_min=trunk_min,
            trunkering_max=trunk_max,
            input_cols=input_cols,
            output_cols=output_cols,
            outlier_filter=use_outlier_filter,
            kravmetod=kravmetod,
        )

        n_outliers = result["is_outlier"].sum()
        if n_outliers > 0:
            st.warning(f"{n_outliers} företag har identifierats som outliers och exkluderats från modellberäkning.")
            st.dataframe(result[result["is_outlier"]][["Företag", "Effektivitet"]])
        else:
            st.info("Inga outliers identifierades i denna körning.")

        st.dataframe(result[["Företag", "Effektivitet", "Effkrav_proc"]])
        plot_efficiency_histogram(result["Effektivitet"], title="PyStoned: Effektivitet")
        plot_efficiency_histogram(result["Effkrav_proc"] * 100, title="PyStoned: Årligt effektiviseringskrav (%)")

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            result.to_excel(writer, sheet_name="Resultat", index=False)
        st.download_button(
            label=f"Ladda ned resultat för PyStoned-modellen som Excel",
            data=buffer.getvalue(),
            file_name="resultat_pystoned.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("Välj modellspecifikationer och klicka på 'Kör PyStoned-modellen' för att se resultat.")

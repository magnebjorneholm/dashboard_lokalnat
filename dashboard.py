# dashboard.py

import streamlit as st
import pandas as pd
import io

from app.data_loader import load_data
from app.dea_model import run_dea_model
from app.sfa_model import run_sfa_model
from app.pystoned_model import run_pystoned_model
from app.plots import (
    plot_efficiency_histogram,
    plot_efficiency_boxplot,
    plot_efficiency_vs_size,
)
from app.run_logger import list_runs, load_run

from app.model_compare import generate_summary_table

#Lösenordsskydd
if "access_granted" not in st.session_state:
    st.session_state.access_granted = False

if not st.session_state.access_granted:
    password_input = st.text_input("Ange lösenord", type="password")
    if password_input == st.secrets["password"]:
        st.session_state.access_granted = True
        st.rerun()
    elif password_input != "":
        st.warning("Fel lösenord. Försök igen.")
    st.stop()


st.set_page_config(page_title="Effektiviseringsdashboard", layout="wide")
st.title("Effektiviseringsdashboard för lokalnätsföretag")
st.markdown("Välj modell och se effektivitet, krav och utfall för olika företag.")

# --- Ladda data ---
data_file = "data/Data_modeller.xlsx"
df = load_data(data_file)

# --- Modellval ---
modellval = st.sidebar.selectbox(
    "Välj modell",
    ["DEA", "SFA", "PyStoned", "Jämför körningar", "Effektivitetsjämförelse", "Företagsanalys"]
)


if modellval == "DEA":
    st.header("DEA-modell")

    st.sidebar.subheader("DEA-parametrar")

    # --- Kolumnval ---
    all_inputs = ["CAPEX", "OPEXp"]
    all_outputs = ["CU", "MW", "NS", "MWhl", "MWhh"]

    input_cols = st.sidebar.multiselect("Välj inputvariabler", all_inputs, default=all_inputs)
    output_cols = st.sidebar.multiselect("Välj outputvariabler", all_outputs, default=all_outputs)

    if not input_cols or not output_cols:
        st.warning("Välj minst en input och en output för att köra modellen.")
        st.stop()

    # --- RTS och trunkering ---
    st.sidebar.caption("**Skalavkastning (RTS)**\n"
                       "- `crs`: Konstant skalavkastning – output ökar proportionellt med input.\n"
                       "- `vrs`: Variabel skalavkastning – tillåter t.ex. stordriftsfördelar.")
    dea_rts = st.sidebar.selectbox("Skalavkastning (RTS)", ["crs", "vrs"], index=0)

    st.sidebar.caption("**Trunkering av intäktsreduktion**\n"
                       "Anger hur mycket ineffektivitet (1 − effektivitet) får påverka kraven.\n"
                       "- Högre max → större möjliga krav\n"
                       "- Lägre min → fler företag får krav även vid låg ineffektivitet")
    dea_trunk_min = st.sidebar.slider("Minsta trunkering", 0.0, 0.3, 0.162416, step=0.005)
    dea_trunk_max = st.sidebar.slider("Högsta trunkering", 0.1, 0.5, 0.3, step=0.005)

    # --- Körmodellknapp ---
    run_model = st.sidebar.button("🔁 Kör DEA-modellen")

    if run_model:
        result = run_dea_model(
            df,
            rts=dea_rts,
            trunkering_min=dea_trunk_min,
            trunkering_max=dea_trunk_max,
            input_cols=input_cols,
            output_cols=output_cols
        )

        st.dataframe(result[["Företag", "Effektivitet", "Supereffektivitet", "Effkrav_proc"]])
        plot_efficiency_histogram(result["Effektivitet"], title="DEA: Effektivitet")
        plot_efficiency_histogram(result["Supereffektivitet"], title="DEA: Supereffektivitet")
        plot_efficiency_histogram(result["Effkrav_proc"] * 100, title="DEA: Årligt effektiviseringskrav (%)")
        plot_efficiency_boxplot(result["Effektivitet"], title="DEA: Effektivitet (boxplot)")
        plot_efficiency_vs_size(result, size_col="MWhl", eff_col="Effektivitet")
    else:
        st.info("⚙️ Välj modellspecifikationer och klicka på 'Kör DEA-modellen' för att se resultat.")


elif modellval == "SFA":
    st.header("SFA-modell")
    result = run_sfa_model(df)
    st.dataframe(result[["Företag", "Effektivitet", "Effkrav_proc"]])
    plot_efficiency_histogram(result["Effektivitet"], title="SFA: Effektivitet")
    plot_efficiency_histogram(result["Effkrav_proc"] * 100, title="SFA: Årligt effektiviseringskrav (%)")
    plot_efficiency_boxplot(result["Effektivitet"], title="SFA: Effektivitet (boxplot)")
    plot_efficiency_vs_size(result, size_col="MWhl", eff_col="Effektivitet")


elif modellval == "PyStoned":
    st.header("PyStoned-modell")

    st.sidebar.subheader("PyStoned-parametrar")

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

    st.sidebar.caption("**Trunkering av intäktsreduktion**\n"
                       "Anger hur mycket ineffektivitet (1 − effektivitet) får påverka kraven.\n"
                       "- Högre max → större möjliga krav\n"
                       "- Lägre min → fler företag får krav även vid låg ineffektivitet")
    trunk_min = st.sidebar.slider("Minsta trunkering", 0.0, 0.3, 0.162416, step=0.005)
    trunk_max = st.sidebar.slider("Högsta trunkering", 0.1, 0.5, 0.3, step=0.005)

    # Kör endast om användaren klickar på knappen
    run_model = st.sidebar.button("🔁 Kör PyStoned-modellen")

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
            trunkering_max=trunk_max
        )

        # --- Spara körningen som YAML + Feather ---
        from app.run_logger import save_run
        save_run("PyStoned", {
            "rts": rts_val,
            "fun": fun_val,
            "cet": cet_val,
            "trunkering_min": trunk_min,
            "trunkering_max": trunk_max
        }, result)

        st.dataframe(result[["Företag", "Effektivitet", "Effkrav_proc"]])
        plot_efficiency_histogram(result["Effektivitet"], title="PyStoned: Effektivitet")
        plot_efficiency_histogram(result["Effkrav_proc"] * 100, title="PyStoned: Årligt effektiviseringskrav (%)")
        plot_efficiency_boxplot(result["Effektivitet"], title="PyStoned: Effektivitet (boxplot)")
        plot_efficiency_vs_size(result, size_col="MWhl", eff_col="Effektivitet")

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            result.to_excel(writer, sheet_name="Resultat", index=False)
        st.download_button(
            label=f"📄 Ladda ned resultat för {modellval}-modellen som Excel",
            data=buffer.getvalue(),
            file_name=f"resultat_{modellval.lower()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("⚙️ Välj modellspecifikationer och klicka på 'Kör PyStoned-modellen' för att se resultat.")


elif modellval == "Jämför körningar":
    st.header("Jämför två modellkörningar")

    from app.run_logger import list_runs, load_run
    import matplotlib.pyplot as plt

    runs = list_runs()
    if len(runs) < 2:
        st.warning("Minst två körningar krävs för att göra en jämförelse.")
        st.stop()

    run_id_a = st.selectbox("Välj körning A", runs, index=0)
    run_id_b = st.selectbox("Välj körning B", runs, index=1)

    if run_id_a == run_id_b:
        st.warning("Välj två olika körningar.")
        st.stop()

    params_a, df_a = load_run(run_id_a)
    params_b, df_b = load_run(run_id_b)

    merged = df_a[["Företag", "Effektivitet"]].rename(columns={"Effektivitet": "Eff_A"}).merge(
        df_b[["Företag", "Effektivitet"]].rename(columns={"Effektivitet": "Eff_B"}),
        on="Företag",
        how="inner"
    )

    if merged.empty:
        st.error("Inga gemensamma företag hittades.")
        st.stop()

    merged["Diff"] = merged["Eff_B"] - merged["Eff_A"]
    corr = merged["Eff_A"].corr(merged["Eff_B"])

    st.subheader("Korrelation")
    st.write(f"Pearson-korrelation mellan effektivitet A och B: **{corr:.4f}**")

    st.subheader("Största skillnader (Eff_B − Eff_A)")
    st.dataframe(merged.sort_values("Diff", key=abs, ascending=False).head())

    st.subheader("Scatterplot: Effektivitet A vs B")
    fig, ax = plt.subplots(figsize=(5, 5))
    ax.scatter(merged["Eff_A"], merged["Eff_B"], alpha=0.7)
    ax.plot([0, 1], [0, 1], color="gray", linestyle="--")
    ax.set_xlabel("Effektivitet – Körning A")
    ax.set_ylabel("Effektivitet – Körning B")
    ax.set_title("Effektivitet A vs B")
    ax.grid(True)

    col1, col2 = st.columns([2, 2])
    with col1:
        st.pyplot(fig, use_container_width=False)


elif modellval == "Effektivitetsjämförelse":
    st.header("Effektivitetsjämförelse")

    from app.run_logger import list_runs, load_run

    runs = list_runs()
    run_id = st.selectbox("Välj tidigare körning", runs)
    params, df = load_run(run_id)

    kr_bas_col = st.selectbox("Bas för krav i kr", ["OPEXp", "TOTEX"])
    trunk_min = st.slider("Min trunkering", 0.0, 0.3, 0.162416)
    trunk_max = st.slider("Max trunkering", 0.1, 0.5, 0.3)


    table = generate_summary_table(df, trunk_min, trunk_max, kr_bas_col)
    st.subheader("Effektivitet och krav")
    st.dataframe(table)

    # Förbered data för diagram – ta bort företag med icke-finit värde
    chart_data = table[["Företag", "Effkrav_kr"]].copy()
    chart_data["Effkrav_kr"] = pd.to_numeric(chart_data["Effkrav_kr"], errors="coerce")
    filtered = chart_data.dropna(subset=["Effkrav_kr"])

    removed_firms = set(chart_data["Företag"]) - set(filtered["Företag"])
    if removed_firms:
        st.warning(f"Följande företag har filtrerats bort från diagrammet p.g.a. ogiltiga värden: {', '.join(removed_firms)}")

    if not filtered.empty:
        st.bar_chart(filtered.set_index("Företag"))
    else:
        st.info("Inga giltiga värden att visa i diagrammet.")

elif modellval == "Företagsanalys":
    st.header("Företagsanalys")

    from app.run_logger import list_runs, load_run

    runs = list_runs()
    run_id = st.selectbox("Välj tidigare körning", runs)
    params, df = load_run(run_id)

    selected_firm = st.selectbox("Välj företag", df["Företag"].unique())

    if "last_firm" not in st.session_state:
        st.session_state["last_firm"] = selected_firm
    elif selected_firm != st.session_state["last_firm"]:
            st.session_state["sim_history"] = []
            st.session_state["sim_inputs"] = []
            st.session_state["last_firm"] = selected_firm
            st.rerun()

    row = df[df["Företag"] == selected_firm].iloc[0]

    st.write("Redigera indata:")
    edited_row = {}
    for col in ["OPEXp", "CAPEX", "CU", "MW", "NS", "MWhl", "MWhh"]:
        edited_row[col] = st.number_input(f"{col}", value=float(row[col]))

    modelltyp = st.selectbox("Modell", ["DEA", "PyStoned"])
    rts_val = st.selectbox("RTS", ["crs", "vrs"])
    output_cols = st.multiselect("Outputvariabler", ["CU", "MW", "NS", "MWhl", "MWhh"], default=["CU"])
    trunk_min = st.slider("Min trunkering", 0.0, 0.3, 0.162416)
    trunk_max = st.slider("Max trunkering", 0.1, 0.5, 0.3)
    kr_bas_col = st.selectbox("Bas för krav i kr", ["OPEXp", "TOTEX"])

    # Initiera historik om det inte finns
    if "sim_history" not in st.session_state:
        st.session_state["sim_history"] = []
    if "sim_inputs" not in st.session_state:
        st.session_state["sim_inputs"] = []

    # Kör ny simulering
    if st.button("Kör simulering"):
        df_sim = pd.DataFrame([edited_row])
        df_sim["Företag"] = selected_firm


        df_ref = df[df["Företag"] != selected_firm].copy()
        df_combined = pd.concat([df_ref, df_sim], ignore_index=True)

        if modelltyp == "DEA":
            result = run_dea_model(
                df_combined,
                rts=rts_val,
                trunkering_min=trunk_min,
                trunkering_max=trunk_max,
                input_cols=["CAPEX", "OPEXp"],
                output_cols=output_cols
            )
        elif modelltyp == "PyStoned":
            result = run_pystoned_model(
                df_combined,
                rts=rts_val,
                fun="cost",
                cet="addi",
                trunkering_min=trunk_min,
                trunkering_max=trunk_max
            )

        res_firm = result[result["Företag"] == selected_firm].copy()
        effkrav_kr = res_firm["Effkrav_proc"].values[0] * res_firm[kr_bas_col].values[0]
        sim_index = len([r for r in st.session_state["sim_history"] if r["Scenario"].startswith("Simulering")])

        # Lägg till resultat
        st.session_state["sim_history"].append({
            "Scenario": f"Simulering {sim_index + 1}",
            "Företag": selected_firm,
            "Effektivitet": res_firm["Effektivitet"].values[0],
            "Effkrav (%)": res_firm["Effkrav_proc"].values[0] * 100,
            "Effkrav (kr)": effkrav_kr
        })

        # Lägg till antaganden
        input_record = {
            "Scenario": f"Simulering {sim_index + 1}",
            "Företag": selected_firm,
            "RTS": rts_val,
            "Outputval": ", ".join(output_cols),
            "Trunk min": trunk_min,
            "Trunk max": trunk_max,
            "Kr-bas": kr_bas_col
        }
        input_record.update({k: v for k, v in edited_row.items()})
        st.session_state["sim_inputs"].append(input_record)

    # Ursprungligt resultat
    if not any(row["Scenario"] == "Ursprungligt" for row in st.session_state["sim_history"]):
        original_row = df[df["Företag"] == selected_firm].iloc[0]
        effkrav_kr_orig = original_row["Effkrav_proc"] * original_row[kr_bas_col]
        st.session_state["sim_history"].insert(0, {
            "Scenario": "Ursprungligt",
            "Företag": selected_firm,
            "Effektivitet": original_row["Effektivitet"],
            "Effkrav (%)": original_row["Effkrav_proc"] * 100,
            "Effkrav (kr)": effkrav_kr_orig
        })
        st.session_state["sim_inputs"].insert(0, {
            "Scenario": "Ursprungligt",
            "Företag": selected_firm,
            "RTS": params.get("rts", ""),
            "Outputval": ", ".join(params.get("output_cols", [])),
            "Trunk min": float(params.get("trunkering_min", 0.0) or 0.0),
            "Trunk max": float(params.get("trunkering_max", 0.0) or 0.0),
            "Kr-bas": kr_bas_col,
            **{k: original_row[k] for k in ["OPEXp", "CAPEX", "CU", "MW", "NS", "MWhl", "MWhh"]}
        })

    # Rensningsknapp
    if st.button("🧹 Rensa simuleringar"):
        st.session_state["sim_history"] = []
        st.session_state["sim_inputs"] = []

    # Visa resultat
    st.subheader("Resultatöversikt")
    hist_df = pd.DataFrame(st.session_state["sim_history"])
    st.dataframe(hist_df)

    st.subheader("Körningsantaganden")
    input_df = pd.DataFrame(st.session_state["sim_inputs"])
    st.dataframe(input_df)

    # Export till Excel
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        hist_df.to_excel(writer, sheet_name="Resultat", index=False)
        input_df.to_excel(writer, sheet_name="Antaganden", index=False)
    st.download_button(
        label="📄 Ladda ned resultatöversikt som Excel",
        data=buffer.getvalue(),
        file_name=f"simulering_{selected_firm}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

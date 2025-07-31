# dashboard.py

import streamlit as st
import pandas as pd
import io
import numpy as np
import geopandas as gpd

from app.data_loader import load_data
from app.dea_model import run_dea_model
from Gammalt.sfa_model import run_sfa_model
from app.pystoned_model import run_pystoned_model
from app.plots import (
    plot_efficiency_histogram,
    plot_efficiency_boxplot,
    plot_efficiency_vs_size,
)
from app.run_logger import list_runs, load_run
from spatial_analysis import lägg_till_grannsnitt

if "access_granted" not in st.session_state or not st.session_state.access_granted:
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
    ["DEA", "SFA", "PyStoned", "PyStoned (färdig körning)" ,"Jämför körningar", "Företagsanalys", "Geografisk karta"]
)


if modellval == "DEA":
    st.header("DEA-modell")

    st.sidebar.subheader("DEA-parametrar")

    # --- Kolumnval ---
    all_inputs = ["CAPEX", "OPEXp", "TOTEX"]
    all_outputs = ["CU", "MW", "NS", "MWhl", "MWhh"]

    st.sidebar.caption("**Inputs**\n"
                       "- `CAPEX + OPEXp`: Separata poster för investeringar och drift – visar om ineffektivitet ligger i kapital eller drift.\n"
                       "- `TOTEX`: Summerar kostnaderna – ger en totalbedömning och bortser från kostnadsstruktur.")
    
    input_cols = st.sidebar.multiselect("Välj inputvariabler", all_inputs, default=["CAPEX", "OPEXp"])

    if "TOTEX" in input_cols and ("CAPEX" in input_cols or "OPEXp" in input_cols):
        st.warning("Välj antingen TOTEX eller CAPEX+OPEXp, inte båda samtidigt.")
        st.stop()

    output_cols = st.sidebar.multiselect("Välj outputvariabler", all_outputs, default=all_outputs)
    use_outlier_filter = st.sidebar.checkbox("Filtrera bort outliers före beräkning", value=True)

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


elif modellval == "SFA":
    st.header("SFA-modell")
    st.warning("Tekniska problem")
    st.stop()

    result = run_sfa_model(df)
    st.dataframe(result[["Företag", "Effektivitet", "Effkrav_proc"]])
    plot_efficiency_histogram(result["Effektivitet"], title="SFA: Effektivitet")
    plot_efficiency_histogram(result["Effkrav_proc"] * 100, title="SFA: Årligt effektiviseringskrav (%)")
    plot_efficiency_boxplot(result["Effektivitet"], title="SFA: Effektivitet (boxplot)")
    plot_efficiency_vs_size(result, size_col="MWhl", eff_col="Effektivitet")


elif modellval == "PyStoned":
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

    # Kör endast om användaren klickar på knappen
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
            label=f"Ladda ned resultat för {modellval}-modellen som Excel",
            data=buffer.getvalue(),
            file_name=f"resultat_{modellval.lower()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("Välj modellspecifikationer och klicka på 'Kör PyStoned-modellen' för att se resultat.")


elif modellval == "PyStoned (färdig körning)":
    st.header("PyStoned: Färdig körning med dynamiskt krav")

    import os
    import yaml
    import pandas as pd
    from datetime import datetime
    from app.plots import plot_efficiency_histogram, plot_efficiency_boxplot

    BASE_DIR = "runs_pystoned"  # Härifrån hämtas alla färdiga körningar
    SAVE_DIR = "runs"           # Här ska nya justerade versioner sparas
    os.makedirs(BASE_DIR, exist_ok=True)
    os.makedirs(SAVE_DIR, exist_ok=True)

    # --- Hämta alla färdiga körningar ---
    runs = sorted(os.listdir(BASE_DIR))
    if not runs:
        st.warning("Inga färdiga PyStoned-körningar hittades i 'runs_pystoned/'.")
        st.stop()

    # --- Välj körning ---
    run_id = st.selectbox("Välj en körning", runs)

    # --- Läs in params.yaml och result.feather ---
    params_path = os.path.join(BASE_DIR, run_id, "params.yaml")
    result_path = os.path.join(BASE_DIR, run_id, "result.feather")

    with open(params_path) as f:
        params = yaml.safe_load(f)
    df = pd.read_feather(result_path)

    if "Effektivitet" not in df.columns:
        st.error("Ingen 'Effektivitet'-kolumn hittades i körningen.")
        st.stop()

    # --- Visa modellspecifikation ---
    st.subheader("Modellspecifikation")
    p = params.get("parametrar", {})

    visade_keys = {
        "input_cols": "Inputs",
        "output_cols": "Outputs",
        "outlier_filter": "Outlierfilter",
        "rts": "RTS",
        "cet": "Teknologi (CET)",
        "fun": "Funktionstyp"
    }
    rows = []
    for key, label in visade_keys.items():
        val = p.get(key, "-")
        if isinstance(val, list):
            val = ", ".join(val)
        rows.append((label, val))

    df_spec = pd.DataFrame(rows, columns=["Parameter", "Värde"])
    df_spec["Värde"] = df_spec["Värde"].astype(str)
    st.table(df_spec)

    # --- Visa outliers om de finns ---
    if "is_outlier" in df.columns:
        df_outliers = df[df["is_outlier"] == True][["Företag", "Effektivitet"]]
        if not df_outliers.empty:
            st.warning(f"{len(df_outliers)} företag har identifierats som outliers och exkluderats från fronten.")
            st.dataframe(df_outliers)
        else:
            st.info("Inga outliers identifierades i denna körning.")
    else:
        st.info("Ingen outlier-information finns sparad för denna körning.")

    # Visa tabell och histogram
    st.dataframe(df[["Företag", "Effektivitet"]])
    plot_efficiency_histogram(df["Effektivitet"], title="PyStoned: Effektivitet") 

    # --- Policyval ---
    st.sidebar.subheader("Omberäkna effektivitetskrav")
    kravmetod = st.sidebar.radio("Ny metod för krav", ["absolut", "percentilbaserad"], index=0)
    trunk_min = st.sidebar.slider("Minsta trunkering", 0.0, 0.3, 0.162, step=0.005)
    trunk_max = st.sidebar.slider("Högsta trunkering", 0.1, 0.5, 0.3, step=0.005)

    # --- Beräkna nytt krav ---
    if st.button("Beräkna nytt effektivitetskrav"):
        import numpy as np
        t = 1 - df["Effektivitet"].astype(float)

        if kravmetod == "absolut":
            revred_compress = np.clip(t, trunk_min, trunk_max)
            krav = ((1 + revred_compress / 4) ** 0.25) - 1

        elif kravmetod == "percentilbaserad":
            if "is_outlier" in df.columns:
                revred_all = t[df["is_outlier"] == False]
            else:
                revred_all = t

            r10, r90 = np.percentile(revred_all.values, [10, 90])

            krav_list = []
            for ineff in t:
                revred_scaled = (ineff - r10) / (r90 - r10)
                revred_scaled = np.clip(revred_scaled, 0, 1)
                revred_compress = revred_scaled * (trunk_max - trunk_min) + trunk_min
                krav_val = ((1 + revred_compress / 4) ** 0.25) - 1
                krav_list.append(krav_val)

            krav = pd.Series(krav_list, index=df.index)

        else:
            st.error("Ogiltig kravmetod.")
            st.stop()

        # Uppdatera df i minnet
        df = df.copy()
        df["Effkrav_proc"] = krav
        st.session_state["justerat_df"] = df.copy()
        st.session_state["justerade_params"] = {
            "kravmetod": kravmetod,
            "trunkering_min": trunk_min,
            "trunkering_max": trunk_max,
        }

        st.success("Nytt effektivitetskrav har beräknats.")
        

        # Plotta grafer
        plot_efficiency_histogram(df["Effkrav_proc"] * 100, title="Effektiviseringskrav (%)")

        # Exportera Excel
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            df[["Företag", "Effektivitet", "Effkrav_proc"]].to_excel(writer, sheet_name="Resultat", index=False)
        st.download_button(
            "Ladda ned resultat som Excel",
            data=buffer.getvalue(),
            file_name=f"krav_{run_id}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        # --- Möjlighet att spara som ny körning ---
    if "justerat_df" in st.session_state:
        if st.button("Spara denna version"):
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            new_run_id = f"Pystoned_{run_id}_{timestamp}"
            new_path = os.path.join(SAVE_DIR, new_run_id)
            os.makedirs(new_path, exist_ok=True)

            nya_params = params.copy()
            nya_params.update(st.session_state["justerade_params"])

            with open(os.path.join(new_path, "params.yaml"), "w") as f:
                yaml.dump(nya_params, f)

            st.session_state["justerat_df"].to_feather(os.path.join(new_path, "result.feather"))
            st.success(f"Ny version sparad i {new_path}")  


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

    # --- Visa modellspecifikationer i två tabeller ---
    st.subheader("Modellspecifikationer")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### Körning A")
        df_a_spec = pd.DataFrame(params_a.items(), columns=["Parameter", "Värde"])
        st.table(df_a_spec)
    with col2:
        st.markdown("### Körning B")
        df_b_spec = pd.DataFrame(params_b.items(), columns=["Parameter", "Värde"])
        st.table(df_b_spec)

    # --- Sammanfoga gemensamma företag ---
    merged = df_a[["Företag", "Effektivitet"]].rename(columns={"Effektivitet": "Eff_A"}).merge(
        df_b[["Företag", "Effektivitet"]].rename(columns={"Effektivitet": "Eff_B"}),
        on="Företag",
        how="inner"
    ).dropna()

    if merged.empty:
        st.info("Inga gemensamma företag att jämföra.")
        st.stop()

    merged["Diff"] = merged["Eff_B"] - merged["Eff_A"]
    corr = merged["Eff_A"].corr(merged["Eff_B"])

    st.subheader("Effektivitetsjämförelse")
    st.markdown(f"**Pearson-korrelation mellan effektivitet A och B:** `{corr:.4f}`")
    st.markdown("#### Största skillnader (Eff_B − Eff_A)")
    st.dataframe(merged.sort_values("Diff", key=abs, ascending=False).head(10))
    st.markdown("#### Samtliga gemensamma företag")
    st.dataframe(merged.sort_values("Företag"))

    # --- Lägg till effektivitetskrav för scatterplot ---
    if "Effkrav_proc" in df_a.columns and "Effkrav_proc" in df_b.columns:
        merged["Krav_A"] = df_a.set_index("Företag").loc[merged["Företag"], "Effkrav_proc"].values * 100
        merged["Krav_B"] = df_b.set_index("Företag").loc[merged["Företag"], "Effkrav_proc"].values * 100
    else:
        st.warning("Effektivitetskrav saknas i en eller båda körningarna – scatterplot för krav kan inte visas.")
        st.stop()

    # --- Två scatterplots ---
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Scatterplot: Effektivitet – A vs B")
        fig, ax = plt.subplots(figsize=(5, 5))
        ax.scatter(merged["Eff_A"], merged["Eff_B"], alpha=0.7)
        ax.plot([0, 1], [0, 1], color="gray", linestyle="--")
        ax.set_xlabel("Effektivitet – Körning A")
        ax.set_ylabel("Effektivitet – Körning B")
        ax.set_title("Effektivitet A vs B")
        ax.grid(True)
        st.pyplot(fig, use_container_width=False)

    with col2:
        st.subheader("Scatterplot: Effektivitetskrav (%) – A vs B")
        fig_k, ax_k = plt.subplots(figsize=(5, 5))
        ax_k.scatter(merged["Krav_A"], merged["Krav_B"], alpha=0.7)
        ax_k.plot([1, 2], [1, 2], color="gray", linestyle="--")
        ax_k.set_xlim(1.0, 2.0)
        ax_k.set_ylim(1.0, 2.0)
        ax_k.set_xlabel("Effektiviseringskrav (%) – Körning A")
        ax_k.set_ylabel("Effektiviseringskrav (%) – Körning B")
        ax_k.set_title("Effektiviseringskrav A vs B")
        ax_k.grid(True)
        st.pyplot(fig_k, use_container_width=False)


elif modellval == "Företagsanalys":
    st.header("Företagsanalys")
    st.info(
        "Testa olika scenarier för ett företag med valfria specifikationer. "
        "Första körningen i denna flik sparas som referens. "
        "Senare körningar numreras som Simulering 1, 2, 3... och jämförs med referensen. "
        "Körningar sparas inte mellan sessioner – du börjar från noll varje gång du öppnar fliken eller klickar 'Rensa'."
    )

    df = load_data("data/Data_modeller.xlsx")
    df["TOTEX"] = df["OPEXp"] + df["CAPEX"]
    företag_namn = df["Företag"].unique()
    selected_firm = st.selectbox("Välj företag", företag_namn)

    row = df[df["Företag"] == selected_firm].iloc[0]

    st.subheader("Redigera företagets data")
    edited_row = {}
    for col in ["OPEXp", "CAPEX", "TOTEX", "CU", "MW", "NS", "MWhl", "MWhh"]:
        edited_row[col] = st.number_input(f"{col}", value=float(row[col]))

    st.subheader("Välj modellspecifikation")
    modelltyp = st.selectbox("Modell", ["DEA", "PyStoned"])
    rts_val = st.selectbox("RTS", ["crs", "vrs"])

    if modelltyp == "PyStoned":
        fun_val = st.selectbox("Funktionstyp", ["prod", "cost"], index=1)
        cet_val = st.selectbox("Teknologi (CET)", ["addi", "mult"], index=0)
        kravmetod_val = st.selectbox("Effektivitetskrav – metod", ["absolut", "percentilbaserat"], index=0)
        if cet_val == "mult":
            st.warning("Teknologin 'mult' kräver solvern 'ipopt', som inte stöds i din miljö.")
            st.stop()
    else:
        fun_val = None
        cet_val = None
        kravmetod_val = None

    möjliga_inputs = ["CAPEX", "OPEXp"]
    möjliga_outputs = ["CU", "MW", "NS", "MWhl", "MWhh"]
    input_cols = st.multiselect("Inputvariabler", möjliga_inputs, default=["CAPEX", "OPEXp"])
    output_cols = st.multiselect("Outputvariabler", möjliga_outputs, default=["CU"])
    use_outlier_filter = st.checkbox("Filtrera bort outliers", value=True)
    trunk_min = st.slider("Min trunkering", 0.0, 0.3, 0.162416)
    trunk_max = st.slider("Max trunkering", 0.1, 0.5, 0.3)
    kr_bas_col = st.selectbox("Bas för krav i kr", ["OPEXp", "TOTEX"])

    if "sim_history" not in st.session_state:
        st.session_state["sim_history"] = []
        st.session_state["sim_inputs"] = []

    if st.button("Kör modell"):
        df_mod = df.copy()
        mask = df_mod["Företag"] == selected_firm
        for col in edited_row:
            df_mod.loc[mask, col] = edited_row[col]

        # Kör vald modell
        if modelltyp == "DEA":
            result = run_dea_model(
                df_mod,
                rts=rts_val,
                trunkering_min=trunk_min,
                trunkering_max=trunk_max,
                input_cols=input_cols,
                output_cols=output_cols,
                outlier_filter=use_outlier_filter
            )
        elif modelltyp == "PyStoned":
            result = run_pystoned_model(
                df_mod,
                rts=rts_val,
                fun=fun_val,
                cet=cet_val,
                trunkering_min=trunk_min,
                trunkering_max=trunk_max,
                input_cols=input_cols,
                output_cols=output_cols,
                outlier_filter=use_outlier_filter,
                kravmetod=kravmetod_val
            )

        res_firm = result[result["Företag"] == selected_firm].copy()
        effkrav_kr = res_firm["Effkrav_proc"].values[0] * res_firm[kr_bas_col].values[0]

        # Namnge scenario
        scen_namn = (
            "Referens" if len(st.session_state["sim_history"]) == 0
            else f"Simulering {len(st.session_state['sim_history'])}"
        )

        st.session_state["sim_history"].append({
            "Scenario": scen_namn,
            "Företag": selected_firm,
            "Effektivitet": res_firm["Effektivitet"].values[0],
            "Effkrav (%)": res_firm["Effkrav_proc"].values[0] * 100,
            "Effkrav (kr)": effkrav_kr,
            "Funktion": fun_val,
            "Teknologi": cet_val,
            "Kravmetod": kravmetod_val
        })

        st.session_state["sim_inputs"].append({
            "Scenario": scen_namn,
            "Företag": selected_firm,
            "RTS": rts_val,
            "Inputval": ", ".join(input_cols),
            "Outputval": ", ".join(output_cols),
            "Trunk min": trunk_min,
            "Trunk max": trunk_max,
            "Kr-bas": kr_bas_col,
            "Outlierfilter": use_outlier_filter,
            "Kravmetod": kravmetod_val,
            "Funktion": fun_val,
            "Teknologi": cet_val,
            **edited_row
        })

    if st.button("Rensa körningar"):
        st.session_state["sim_history"] = []
        st.session_state["sim_inputs"] = []
        st.rerun()

    st.subheader("Resultatöversikt")
    hist_df = pd.DataFrame(st.session_state["sim_history"])
    st.dataframe(hist_df)

    st.subheader("Körningsantaganden")
    input_df = pd.DataFrame(st.session_state["sim_inputs"])
    st.dataframe(input_df)

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        hist_df.to_excel(writer, sheet_name="Resultat", index=False)
        input_df.to_excel(writer, sheet_name="Antaganden", index=False)
    st.download_button(
        label="Ladda ned resultatöversikt som Excel",
        data=buffer.getvalue(),
        file_name=f"simulering_{selected_firm}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


elif modellval == "Geografisk karta":
    from app.run_logger import list_runs, load_run
    from heatmap_view import show_heatmap, load_shapes
    from spatial_analysis import lägg_till_grannsnitt

    runs = list_runs()
    if not runs:
        st.warning("Inga modellkörningar hittades.")
        st.stop()

    run_id = st.selectbox("Välj körning", runs, index=0)
    _, df_resultat = load_run(run_id)

    karttyp = st.selectbox("Välj karttyp", ["Statisk", "Dynamisk"])

    möjliga_indikatorer = ["Effektivitet"]
    if "Supereffektivitet" in df_resultat.columns:
        möjliga_indikatorer.append("Supereffektivitet")

    indikator = st.selectbox("Välj indikator", möjliga_indikatorer)
    if "visa_karta" not in st.session_state:
        st.session_state.visa_karta = False

    if st.button("Visa karta", key="visa_karta_button"):
        st.session_state.visa_karta = True

    if st.session_state.visa_karta:
        # Visa heatmap
        show_heatmap(df_resultat, karttyp=karttyp, indikator=indikator)

        # Grannsnittsanalys
        st.subheader("Jämför med grannar")

        gdf_shapes = load_shapes()
        df_merge = df_resultat[["REId", "Företag", indikator]].copy()
        gdf_shapes = gdf_shapes.merge(df_merge, on="REId", how="left")

        # Sätt geometri aktiv om den tappats
        gdf_shapes = gpd.GeoDataFrame(gdf_shapes, geometry="geometry", crs=gdf_shapes.crs)

        # Val av metod för grannanalys
        st.subheader("Parametrar")
        metod = st.selectbox("Metod", ["knn", "distanceband"], index=0)
        avståndsviktning = st.checkbox("Använd avståndsviktning", value=False)

        if metod == "knn":
            k_val = st.slider("Antal närmaste grannar (k)", 1, 10, 4)
        else:
            d_val = st.slider("Maximalt avstånd (meter)", 1000, 100000, 50000, step=1000)

        # --- Session state ---
        if "visa_grannanalys" not in st.session_state:
            st.session_state.visa_grannanalys = False
            st.session_state.gdf_analys = None
            st.session_state.metodtext = None

        # --- Knapp för att köra analys ---
        if st.button("Kör grannskapsanalys", key="run_neighbour_analysis"):
            st.session_state.visa_grannanalys = True
            st.session_state.metod_val = metod
            st.session_state.avståndsviktning_val = avståndsviktning

            if metod == "knn":
                st.session_state.k_val = k_val
                gdf_analys = lägg_till_grannsnitt(
                    gdf_shapes,
                    indikator=indikator,
                    method="knn",
                    k=k_val,
                    avståndsviktning=avståndsviktning
                )
                st.session_state.gdf_analys = gdf_analys
                st.session_state.metodtext = f"{k_val} närmaste grannar (centroid-baserat)"

            else:
                st.session_state.d_val = d_val
                gdf_analys = lägg_till_grannsnitt(
                    gdf_shapes,
                    indikator=indikator,
                    method="distanceband",
                    distance_threshold=d_val,
                    avståndsviktning=avståndsviktning
                )
                st.session_state.gdf_analys = gdf_analys
                st.session_state.metodtext = f"alla grannar inom {d_val} meter (centroid-baserat)"

        # --- Visa analys endast om knapp tryckts och resultat finns ---
        if st.session_state.visa_grannanalys and st.session_state.gdf_analys is not None:
            with st.expander("Visa analys"):
                st.markdown("**Relativ effektivitet jämfört med geografiska grannar**")
                vikttext = "med avståndsviktning" if st.session_state.avståndsviktning_val else "utan avståndsviktning"
                st.markdown(f"_Baseras på {indikator.lower()} och {st.session_state.metodtext}, {vikttext}._")

                df_grann = st.session_state.gdf_analys[["REId", "Företag", indikator, "grannsnitt", "eff_gap"]].dropna().copy()
                df_grann = df_grann.sort_values("eff_gap")

                st.dataframe(df_grann.style
                            .background_gradient(cmap="RdYlGn", subset=["eff_gap"]),
                            use_container_width=True)

                
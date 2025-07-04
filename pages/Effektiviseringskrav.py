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
    ["DEA", "SFA", "PyStoned", "Jämför körningar", "Företagsanalys", "Geografisk karta"]
)


if modellval == "DEA":
    st.header("DEA-modell")

    st.sidebar.subheader("DEA-parametrar")

    # --- Kolumnval ---
    all_inputs = ["CAPEX", "OPEXp"]
    all_outputs = ["CU", "MW", "NS", "MWhl", "MWhh"]

    input_cols = st.sidebar.multiselect("Välj inputvariabler", all_inputs, default=all_inputs)
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

    # --- Körmodellknapp ---
    run_model = st.sidebar.button("🔁 Kör DEA-modellen")

    if run_model:
        result = run_dea_model(
            df,
            rts=dea_rts,
            trunkering_min=dea_trunk_min,
            trunkering_max=dea_trunk_max,
            input_cols=input_cols,
            output_cols=output_cols,
            outlier_filter=use_outlier_filter
        )

        df_outliers = result[result["is_outlier"] == True][["Företag", "Effektivitet", "Supereffektivitet", "Effkrav_proc"]]
        df_outliers["Effkrav_proc"] = df_outliers["Effkrav_proc"].round(4)

        n_outliers = len(df_outliers)
        if n_outliers > 0:
            st.warning(f"{n_outliers} företag har identifierats som outliers, exkluderats från fronten och tilldelats ett fast årligt effektiviseringskrav på 1 %.")
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
            label="📥 Ladda ned resultat för DEA-modellen som Excel",
            data=buffer.getvalue(),
            file_name="resultat_dea.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
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

    all_inputs = ["CAPEX", "OPEXp"]
    all_outputs = ["CU", "MW", "NS", "MWhl", "MWhh"]

    input_cols = st.sidebar.multiselect("Välj inputvariabler", all_inputs, default=["CAPEX", "OPEXp"])
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
        "Denna vy tillåter analys och simulering även för företag som identifierats som outliers i tidigare modellkörning. "
        "Effektivitetsmåtten för sådana företag kan saknas (NaN), men deras data kan ändras och testas i nya scenarier. "
        "Simuleringar bygger alltid en ny front baserat på de ändrade värdena för detta företag. "
        "Detta innebär att resultatet inte är direkt jämförbart med den ursprungliga modellkörningen."
    )

    from app.run_logger import list_runs, load_run

    runs = list_runs()
    run_id = st.selectbox("Välj tidigare körning", runs)
    params, df = load_run(run_id)

    if "TOTEX" not in df.columns and "OPEXp" in df.columns and "CAPEX" in df.columns:
        df["TOTEX"] = df["OPEXp"] + df["CAPEX"]

    selected_firm = st.selectbox("Välj företag", df["Företag"].unique())

    if "last_firm" not in st.session_state:
        st.session_state["last_firm"] = selected_firm
    elif selected_firm != st.session_state["last_firm"]:
        st.session_state["sim_history"] = []
        st.session_state["sim_inputs"] = []
        st.session_state["last_firm"] = selected_firm
        st.rerun()

    row = df[df["Företag"] == selected_firm].iloc[0]

    if "is_outlier" in df.columns and row["is_outlier"]:
        st.warning("⚠️ Det här företaget identifierades som outlier i vald modellkörning och exkluderades från beräkning.")

    st.write("Redigera indata:")
    edited_row = {}
    for col in ["OPEXp", "CAPEX", "TOTEX", "CU", "MW", "NS", "MWhl", "MWhh"]:
        edited_row[col] = st.number_input(f"{col}", value=float(row[col]))

    modelltyp = st.selectbox("Modell", ["DEA", "PyStoned"])
    rts_val = st.selectbox("RTS", ["crs", "vrs"])
        
    if modelltyp == "PyStoned":
        fun_val = st.selectbox("Funktionstyp", ["prod", "cost"], index=1)
        cet_val = st.selectbox("Teknologi (CET)", ["addi", "mult"], index=0)
        kravmetod_val = st.selectbox("Effektivitetskrav – metod", ["absolut", "percentilbaserat"], index=0)
        
        if cet_val == "mult":
            st.warning("Teknologin 'mult' kräver solvern 'ipopt', som inte är tillgänglig i din miljö. Välj 'addi' istället.")
            st.stop()
    else:
        fun_val = None
        cet_val = None
        kravmetod_val = None

    if cet_val == "mult":
        st.warning("Teknologin 'mult' kräver solvern 'ipopt', som inte är tillgänglig i din miljö. Välj 'addi' istället.")
        st.stop()
    
    output_cols = st.multiselect("Outputvariabler", ["CU", "MW", "NS", "MWhl", "MWhh"], default=["CU"])
    input_cols = ["CAPEX", "OPEXp"]
    use_outlier_filter = st.checkbox("Filtrera bort outliers", value=True)
    trunk_min = st.slider("Min trunkering", 0.0, 0.3, 0.162416)
    trunk_max = st.slider("Max trunkering", 0.1, 0.5, 0.3)
    kr_bas_col = st.selectbox("Bas för krav i kr", ["OPEXp", "TOTEX"])

    if "sim_history" not in st.session_state:
        st.session_state["sim_history"] = []
    if "sim_inputs" not in st.session_state:
        st.session_state["sim_inputs"] = []

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
                input_cols=input_cols,
                output_cols=output_cols,
                outlier_filter=use_outlier_filter
            )
        elif modelltyp == "PyStoned":
            result = run_pystoned_model(
                df_combined,
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
        sim_index = len([r for r in st.session_state["sim_history"] if r["Scenario"].startswith("Simulering")])

        st.session_state["sim_history"].append({
            "Scenario": f"Simulering {sim_index + 1}",
            "Företag": selected_firm,
            "Effektivitet": res_firm["Effektivitet"].values[0],
            "Effkrav (%)": res_firm["Effkrav_proc"].values[0] * 100,
            "Effkrav (kr)": effkrav_kr,
            "Funktion": fun_val,
            "Teknologi": cet_val,
            "Kravmetod": kravmetod_val
        })

        input_record = {
            "Scenario": f"Simulering {sim_index + 1}",
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
        }
        input_record.update({k: v for k, v in edited_row.items()})
        st.session_state["sim_inputs"].append(input_record)

    if not any(row["Scenario"] == "Ursprungligt" for row in st.session_state["sim_history"]):
        original_row = df[df["Företag"] == selected_firm].iloc[0]
        if pd.notnull(original_row["Effkrav_proc"]) and pd.notnull(original_row["Effektivitet"]):
            effkrav_kr_orig = original_row["Effkrav_proc"] * original_row[kr_bas_col]
            st.session_state["sim_history"].insert(0, {
                "Scenario": "Ursprungligt",
                "Företag": selected_firm,
                "Effektivitet": original_row["Effektivitet"],
                "Effkrav (%)": original_row["Effkrav_proc"] * 100,
                "Effkrav (kr)": effkrav_kr_orig,
                "Kravmetod": params.get("kravmetod", kravmetod_val),
            })
            st.session_state["sim_inputs"].insert(0, {
                "Scenario": "Ursprungligt",
                "Företag": selected_firm,
                "RTS": params.get("rts", ""),
                "Inputval": ", ".join(params.get("input_cols", input_cols)),
                "Outputval": ", ".join(params.get("output_cols", output_cols)),
                "Trunk min": float(params.get("trunkering_min", trunk_min) or trunk_min),
                "Trunk max": float(params.get("trunkering_max", trunk_max) or trunk_max),
                "Kr-bas": kr_bas_col,
                "Outlierfilter": params.get("outlier_filter", True),
                "Kravmetod": kravmetod_val,
                **{k: original_row[k] for k in ["OPEXp", "CAPEX", "CU", "MW", "NS", "MWhl", "MWhh"]}
            })

    if st.button("🧹 Rensa simuleringar"):
        st.session_state["sim_history"] = []
        st.session_state["sim_inputs"] = []
        st.session_state["last_firm"] = selected_firm
        st.rerun()

    st.subheader("Resultatöversikt")
    hist_df = pd.DataFrame(st.session_state["sim_history"])
    if "is_outlier" not in hist_df.columns and "is_outlier" in df.columns:
        hist_df["is_outlier"] = hist_df["Företag"].map(df.set_index("Företag")["is_outlier"])
    st.dataframe(hist_df)

    st.subheader("Körningsantaganden")
    input_df = pd.DataFrame(st.session_state["sim_inputs"])
    st.dataframe(input_df)

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
    visa_karta = st.checkbox("Visa karta", value=True)

    if visa_karta:
        # Visa heatmap
        show_heatmap(df_resultat, karttyp=karttyp, indikator=indikator)

        # Grannsnittsanalys
        st.subheader("🔍 Relativ effektivitet: Grannanalys")

        gdf_shapes = load_shapes()
        df_merge = df_resultat[["REId", indikator]].copy()
        gdf_shapes = gdf_shapes.merge(df_merge, on="REId", how="left")

        # Sätt geometri aktiv om den tappats
        gdf_shapes = gpd.GeoDataFrame(gdf_shapes, geometry="geometry", crs=gdf_shapes.crs)

        # Val av metod för grannanalys
        st.subheader("Parametrar för grannanalys")
        metod = st.selectbox("Metod för grannanalys", ["knn", "distanceband"], index=0)
        avståndsviktning = st.checkbox("Använd avståndsviktning", value=False)

        if metod == "knn":
            k_val = st.slider("Antal närmaste grannar (k)", 1, 10, 4)
            gdf_analys = lägg_till_grannsnitt(
                gdf_shapes,
                indikator=indikator,
                method="knn",
                k=k_val,
                avståndsviktning=avståndsviktning
            )
            metodtext = f"{k_val} närmaste grannar (centroid-baserat)"
        else:
            d_val = st.slider("Maximalt avstånd (meter)", 1000, 100000, 50000, step=1000)
            gdf_analys = lägg_till_grannsnitt(
                gdf_shapes,
                indikator=indikator,
                method="distanceband",
                distance_threshold=d_val,
                avståndsviktning=avståndsviktning
            )
            metodtext = f"alla grannar inom {d_val} meter (centroid-baserat)"

        # Visa tabell
        with st.expander("Visa grannsnittsanalys"):
            st.markdown("**Relativ effektivitet jämfört med geografiska grannar**")
            vikttext = "med avståndsviktning" if avståndsviktning else "utan avståndsviktning"
            st.markdown(f"_Baseras på {indikator.lower()} och {metodtext}, {vikttext}._")

            df_grann = gdf_analys[["REId", indikator, "grannsnitt", "eff_gap"]].dropna().copy()
            df_grann = df_grann.sort_values("eff_gap")

            st.dataframe(df_grann.style
                        .background_gradient(cmap="RdYlGn", subset=["eff_gap"]),
                        use_container_width=True)

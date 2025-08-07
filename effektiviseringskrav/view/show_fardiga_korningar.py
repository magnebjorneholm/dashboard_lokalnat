import streamlit as st
import os
import yaml
import pandas as pd
import numpy as np
import io
from datetime import datetime
from effektiviseringskrav.app.plots import plot_efficiency_histogram

BASE_DIR = "effektiviseringskrav/runs_fardiga"
SAVE_DIR = "effektiviseringskrav/runs"
os.makedirs(BASE_DIR, exist_ok=True)
os.makedirs(SAVE_DIR, exist_ok=True)

def show_fardiga_korningar_view():
    st.header("Färdiga körningar med dynamiska krav")

    runs = sorted(os.listdir(BASE_DIR))
    if not runs:
        st.warning("Inga färdiga körningar hittades.")
        st.stop()

    run_id = st.selectbox("Välj en körning", runs)
    params_path = os.path.join(BASE_DIR, run_id, "params.yaml")
    result_path = os.path.join(BASE_DIR, run_id, "result.feather")

    with open(params_path) as f:
        params = yaml.safe_load(f)
    df = pd.read_feather(result_path)

    if "Effektivitet" not in df.columns:
        st.error("Ingen 'Effektivitet'-kolumn hittades i körningen.")
        st.stop()

    st.subheader("Modellspecifikation")
    spec = params.get("parametrar", params)
    if isinstance(spec, dict) and "obs" in spec:
        spec = {k: v for k, v in spec.items() if k != "obs"}
    st.json(spec)

    if "is_outlier" in df.columns:
        df_outliers = df[df["is_outlier"] == True][["Företag", "Effektivitet"]]
        if not df_outliers.empty:
            st.warning(f"{len(df_outliers)} företag har identifierats som outliers och exkluderats från fronten.")
            st.dataframe(df_outliers)
        else:
            st.info("Inga outliers identifierades i denna körning.")
    else:
        st.info("Ingen outlier-information finns sparad för denna körning.")

    st.dataframe(df[["Företag", "Effektivitet"]])
    plot_efficiency_histogram(df["Effektivitet"], title="Effektivitet")

    st.sidebar.subheader("Omberäkna effektivitetskrav")
    kravmetod = st.sidebar.radio("Ny metod för krav", ["absolut", "percentilbaserat"], index=0)
    trunk_min = st.sidebar.slider("Minsta trunkering", 0.0, 0.3, 0.162, step=0.005)
    trunk_max = st.sidebar.slider("Högsta trunkering", 0.1, 0.5, 0.3, step=0.005)

    if st.button("Beräkna nytt effektivitetskrav"):
        t = 1 - df["Effektivitet"].astype(float)

        if kravmetod == "absolut":
            revred_compress = np.clip(t, trunk_min, trunk_max)
            krav = ((1 + revred_compress / 4) ** 0.25) - 1

        elif kravmetod == "percentilbaserat":
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

        df = df.copy()
        df["Effkrav_proc"] = krav
        st.session_state["justerat_df"] = df.copy()
        st.session_state["justerade_params"] = {
            "kravmetod": kravmetod,
            "trunkering_min": trunk_min,
            "trunkering_max": trunk_max,
        }

        st.success("Nytt effektivitetskrav har beräknats.")
        plot_efficiency_histogram(df["Effkrav_proc"] * 100, title="Effektiviseringskrav (%)")

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            df[["Företag", "Effektivitet", "Effkrav_proc"]].to_excel(writer, sheet_name="Resultat", index=False)

        st.download_button(
            "Ladda ned resultat som Excel",
            data=buffer.getvalue(),
            file_name=f"krav_{run_id}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    if "justerat_df" in st.session_state:
        if st.button("Spara denna version"):
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            new_run_id = f"{run_id}_{timestamp}"
            new_path = os.path.join(SAVE_DIR, new_run_id)
            os.makedirs(new_path, exist_ok=True)

            nya_params = params.copy()
            nya_params.update(st.session_state["justerade_params"])

            with open(os.path.join(new_path, "params.yaml"), "w") as f:
                yaml.dump(nya_params, f)

            st.session_state["justerat_df"].to_feather(os.path.join(new_path, "result.feather"))
            st.success(f"Ny version sparad i {new_path}")

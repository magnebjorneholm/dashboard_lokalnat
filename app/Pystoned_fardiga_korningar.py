# pages/10_PyStoned_färdiga_körningar.py
import streamlit as st
import pandas as pd
from run_logger import list_runs, load_run
from app.plots import (
    plot_efficiency_histogram,
    plot_efficiency_boxplot
)

st.title("PyStoned: Visa färdiga körningar och beräkna krav")

# --- Filtrera fram endast PyStoned-körningar ---
runs = list_runs()
pystoned_runs = [r for r in runs if r.lower().startswith("pystoned")]

if not pystoned_runs:
    st.warning("Inga färdiga PyStoned-körningar hittades i 'runs/'-mappen.")
    st.stop()

# --- Användarval av run-id ---
run_id = st.selectbox("Välj en PyStoned-körning", pystoned_runs)
params, df = load_run(run_id)

if "Effektivitet" not in df.columns:
    st.error("Körningen innehåller inte någon kolumn 'Effektivitet'.")
    st.stop()

# --- Användarval av policyparametrar ---
st.sidebar.header("Beräkna krav")
kravmetod = st.sidebar.radio("Metod för effektivitetskrav", ["absolut", "percentilbaserad"], index=0)
trunk_min = st.sidebar.slider("Minsta trunkering", 0.0, 0.3, 0.162, step=0.005)
trunk_max = st.sidebar.slider("Högsta trunkering", 0.1, 0.5, 0.3, step=0.005)

# --- Funktion för kravberäkning ---
def beräkna_effkrav(eff, metod, t_min, t_max):
    ineff = 1 - eff
    if metod == "absolut":
        krav = ineff.clip(lower=t_min, upper=t_max)
    elif metod == "percentilbaserad":
        gräns = ineff.quantile(0.9)  # t.ex. 90e percentilen
        krav = ineff.clip(upper=gräns).clip(lower=t_min, upper=t_max)
    else:
        krav = ineff
    return krav

# --- Beräkna nytt krav och uppdatera dataframe ---
df = df.copy()
df["Effkrav_proc"] = beräkna_effkrav(df["Effektivitet"].astype(float), kravmetod, trunk_min, trunk_max)

# --- Visa resultat ---
st.subheader("Resultat")
st.dataframe(df[["Företag", "Effektivitet", "Effkrav_proc"]])

plot_efficiency_histogram(df["Effektivitet"], title="Effektivitet")
plot_efficiency_boxplot(df["Effektivitet"], title="Effektivitet (boxplot)")
plot_efficiency_histogram(df["Effkrav_proc"] * 100, title="Effektiviseringskrav (%)")

# --- Export ---
buffer = df[["Företag", "Effektivitet", "Effkrav_proc"]].copy()
st.download_button(
    "Ladda ned som Excel",
    data=buffer.to_excel(index=False, engine="xlsxwriter"),
    file_name=f"krav_{run_id}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

if st.button("Använd denna körning i 'Jämför körning'"):
    st.session_state["valda_run_id"] = run_id
    st.success("Körningen är nu förvald i fliken 'Jämför körning'")

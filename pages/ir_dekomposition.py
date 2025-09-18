import streamlit as st
from pathlib import Path

from intaktsram.app.data_loader import load_baseline_data
from intaktsram.view.ir_view import show_ir_dekomposition_view

if "access_granted" not in st.session_state or not st.session_state.access_granted:
    st.stop()

st.set_page_config(page_title="Dekomposition av intäktsram", layout="wide")
st.title("Dekomposition av intäktsram")
st.markdown("Visa och analysera intäktsramens komponenter med möjlighet att uppdatera från andra sektioner.")

# --- Ladda baseline-data ---
possible_paths = [
    "intaktsram/data/Löpande kostnader från SDF 2024-27.xlsx",
    "Löpande kostnader från SDF 2024-27.xlsx", 
    "data/Löpande kostnader från SDF 2024-27.xlsx",
    "intaktsram/Löpande kostnader från SDF 2024-27.xlsx"
]

data_file = None
for path in possible_paths:
    if Path(path).exists():
        data_file = path
        break

if not data_file:
    st.error(f"Kunde inte hitta Excel-filen. Sök efter: {possible_paths[0]}")
    st.info("Kontrollera att filen ligger på rätt plats eller uppdatera sökvägen i koden.")
    st.stop()

try:
    df_baseline = load_baseline_data(data_file)
    st.success(f"Baseline-data laddad från: {data_file} ({len(df_baseline)} företag)")
except Exception as e:
    st.error(f"Kunde inte ladda baseline-data: {e}")
    st.stop()

# --- Visa huvudvyn ---
show_ir_dekomposition_view(df_baseline)

st.sidebar.markdown("---")
if st.sidebar.button("Logga ut"):
    st.session_state.access_granted = False
    st.session_state.current_user = None
    st.session_state.user_role = None
    st.session_state.user_dmu = None
    st.rerun()
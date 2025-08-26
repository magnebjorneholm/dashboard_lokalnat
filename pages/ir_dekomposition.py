import streamlit as st

from intaktsram.app.ir_data_loader import load_baseline_data
from intaktsram.view.ir_view import show_ir_dekomposition_view
if "access_granted" not in st.session_state or not st.session_state.access_granted:
    st.stop()

st.set_page_config(page_title="Intäktsram Dekomposition", layout="wide")
st.title("Intäktsram Dekomposition")
st.markdown("Visa och analysera intäktsramens komponenter med möjlighet att uppdatera från andra sektioner.")

# --- Ladda baseline-data ---
data_file = "intaktsram/data/Löpande kostnader från SDF 2024-27.xlsx"

try:
    df_baseline = load_baseline_data(data_file)
    st.success(f"Baseline-data laddad: {len(df_baseline)} företag")
except Exception as e:
    st.error(f"Kunde inte ladda baseline-data: {e}")
    st.stop()

# --- Visa huvudvyn ---
show_ir_dekomposition_view(df_baseline)
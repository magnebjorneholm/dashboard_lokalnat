"""
Effektiviseringskrav - Regulator View
======================================

Minimal entry point för DEA-analys (regulatoranvändare).
Delegerar all logik till frontend/streamlit/dea_view.py
"""

import streamlit as st
from effektiviseringskrav.backend.data_loader import load_data
from effektiviseringskrav.frontend.dea_view import show_dea_view


# Access control
if "access_granted" not in st.session_state or not st.session_state.access_granted:
    st.error("Du måste logga in för att komma åt denna sida.")
    st.stop()

if st.session_state.user_role != "regulator":
    st.error("Denna sida är endast tillgänglig för regulatorer.")
    st.stop()


# Page config
st.set_page_config(
    page_title="Effektiviseringskrav - DEA", 
    layout="wide"
)

st.title("Effektiviseringskrav")
st.markdown("Beräkna effektiviseringskrav och påverkbara kostnader och exportera till intäktsramen.")


# Load data
DATA_FILE = "effektiviseringskrav/data/Data_modeller.xlsx"

try:
    df = load_data(DATA_FILE)
except Exception as e:
    st.error(f"Kunde inte ladda data: {e}")
    st.stop()


# Show DEA view
show_dea_view(df)


# Logout button
st.sidebar.markdown("---")
if st.sidebar.button("Logga ut"):
    st.session_state.access_granted = False
    st.session_state.current_user = None
    st.session_state.user_role = None
    st.session_state.user_dmu = None
    st.rerun()
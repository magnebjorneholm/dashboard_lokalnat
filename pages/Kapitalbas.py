import streamlit as st

if "access_granted" not in st.session_state or not st.session_state.access_granted:
    st.stop()

st.set_page_config(page_title="Kapitalbas – Dashboard", layout="wide")
st.title("Kapitalbas är under utveckling:)")
st.info("Denna del utvecklas senare.")

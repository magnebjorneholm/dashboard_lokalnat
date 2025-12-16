"""
Results Page - Raw Debug Version.

Dumpar all rådata utan formatering för att se strukturen.
"""

import streamlit as st
from frontend.utils.state_manager import init_session_state, reset_case, get_user_reid
from frontend.utils.export_button import render_export_button

init_session_state()

st.title("Resultat (Raw Debug)")

if not st.session_state.get("calculation_done"):
    st.warning("Ingen beräkning gjord ännu.")
    if st.button("Gå till Case Config"):
        st.switch_page("pages/1_case_config.py")
    st.stop()

baseline = st.session_state.get("baseline_result")
case = st.session_state.get("case_result")
user_reid = get_user_reid()

st.subheader(f"Företag: {user_reid}")

# --- Dump varje stage som rådata ---

st.subheader("Case Result")

with st.expander("case.extraction", expanded=True):
    st.write(vars(case.extraction))

with st.expander("case.pre_dea", expanded=True):
    st.write(vars(case.pre_dea))

with st.expander("case.dea", expanded=True):
    st.write(vars(case.dea))

with st.expander("case.post_dea", expanded=True):
    st.write(vars(case.post_dea))

st.divider()

st.subheader("Baseline Result")

with st.expander("baseline.extraction", expanded=False):
    st.write(vars(baseline.extraction))

with st.expander("baseline.pre_dea", expanded=False):
    st.write(vars(baseline.pre_dea))

with st.expander("baseline.dea", expanded=False):
    st.write(vars(baseline.dea))

with st.expander("baseline.post_dea", expanded=False):
    st.write(vars(baseline.post_dea))

st.divider()

# UI Config
with st.expander("UI Config (session_state)", expanded=False):
    st.json(st.session_state.get("ui_config", {}))

# Knappar
st.divider()
col1, col2 = st.columns(2)

with col1:
    if st.button("NYTT CASE", use_container_width=True):
        reset_case()
        st.switch_page("pages/1_case_config.py")

with col2:
    if st.button("ÄNDRA CASE", use_container_width=True):
        st.session_state["calculation_done"] = False
        st.switch_page("pages/1_case_config.py")

# Export-knapp
st.divider()
render_export_button(
    user_reid=user_reid,
    foretag=case.extraction.foretag,
    baseline_result=baseline,
    case_result=case,
    ui_config=st.session_state.get("ui_config", {})
)
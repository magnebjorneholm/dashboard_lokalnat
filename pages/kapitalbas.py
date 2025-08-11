# kapitalbas_ny.py

import streamlit as st
from kapitalbas.kapitalbas_app.data_loader import load_main_data
from kapitalbas.kapitalbas_app.data_loader import load_component_sample
from kapitalbas.kapitalbas_app.översikt_view import show_översikt
from kapitalbas.kapitalbas_app.tidsserie_view import show_tidsserie
from kapitalbas.kapitalbas_app.komponent_view import show_komponenter
from kapitalbas.kapitalbas_app.policy_playground_view import show_policy_playground
from kapitalbas.kapitalbas_app.qa_view import show_qa

st.title("Kapitalbas")

# === Ladda data ===
capbase, capcost = load_main_data()
st.session_state["final_capbase_sample"] = load_component_sample()

# === Välj sektion ===
sektion = st.sidebar.selectbox(
    "Välj del av kapitalbasen",
    ["Översikt", "Tidsserie", "QA", "Komponenter", "Policy Playground"]
)

# === Visa vald sektion ===
if sektion == "Översikt":
    show_översikt(capbase, capcost)


elif sektion == "Tidsserie":
    show_tidsserie(capcost)


elif sektion == "Komponenter":
    show_komponenter()


elif sektion == "Policy Playground":
    show_policy_playground(capcost)

elif sektion == "QA":
    show_qa()

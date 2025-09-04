# kapitalbas.py - UPPDATERAD med age_reg sektion

import streamlit as st
from kapitalbas.kapitalbas_app.data_loader import (
    load_main_data,
    load_component_sample,
    load_tail_full,
)
from kapitalbas.datafiler.data_loader import (
    ##load_capbase_b_sample,
    ##load_capbase_compress_tail_sample, load_capbase_compress_tail,
    load_capbase_compress, load_depreciation_compress_sample,
    load_depreciation_compress, load_depreciation,
    load_returns_compress_sample, load_returns_compress,
    load_capbase_a_sample, load_capbase_a,
    load_capcost_a_sample, load_capcost_a,
    load_dmu_volymer, load_reconciliation
)
from kapitalbas.visualiseringsfiler.tidsserie_view import show_tidsserie
from kapitalbas.kapitalbas_app.komponent_view import show_komponent_view
from kapitalbas.kapitalbas_app.policy_playground_view import show_policy_playground
from kapitalbas.kapitalbas_app.qa_view import show_qa
from kapitalbas.kapitalbas_app.livslangd_view import show_livslangd_view
# KORRIGERAD IMPORT för age_reg sektion
from kapitalbas.visualiseringsfiler.age_reg_view import show_age_reg_view

from kapitalbas.visualiseringsfiler.intensitet_view import show_intensity_analysis
from kapitalbas.visualiseringsfiler.översikt import show_capcost


st.title("Kapitalbas")

# === Ladda data ===
st.session_state["capbase_compress"] = load_capbase_compress()
st.session_state["depreciation_compress_sample"] = load_depreciation_compress_sample()
st.session_state["depreciation_compress"] = load_depreciation_compress()
st.session_state["returns_compress"] = load_returns_compress()
st.session_state["capbase_a_sample"] = load_capbase_a_sample()
st.session_state["capcost_a_sample"] = load_capcost_a_sample()
st.session_state["capcost_a"] = load_capcost_a()

# === Ladda volymdata för intensitetsanalys ===
st.session_state["dmu_volymer"] = load_dmu_volymer()
st.session_state["reconciliation"] = load_reconciliation()

capbase, capcost = load_main_data()
st.session_state["final_capbase_sample"] = load_component_sample()
st.session_state["capbase_compress_tail"] = load_tail_full()
st.session_state["capcost_python"] = capcost


# === Välj sektion ===
sektion = st.sidebar.selectbox(
    "Välj del av kapitalbasen", 
    [
        "Översikt", 
        "Tidsserie", 
        "Intensitetsanalys", 
        "QA", 
        "Komponenter", 
        "Policy Playground", 
        "Livslängdssimulering",
        "Age_reg Parametrisering"  # NY SEKTION
    ]
)

# === Visa vald sektion ===
if sektion == "Översikt":
    show_capcost(st.session_state["capcost_a"])

elif sektion == "Tidsserie":
    show_tidsserie(st.session_state["capcost_a"])

elif sektion == "Intensitetsanalys":
    show_intensity_analysis(
        st.session_state["capcost_a"],
        st.session_state["dmu_volymer"], 
        st.session_state["reconciliation"]
    )

elif sektion == "Komponenter":
    show_komponent_view(st.session_state["final_capbase_sample"])

elif sektion == "Policy Playground":
    show_policy_playground(capcost)

elif sektion == "QA":
    show_qa()

elif sektion == "Livslängdssimulering":
    show_livslangd_view()

# NY SEKTION för age_reg parametrisering
elif sektion == "Age_reg Parametrisering":
    show_age_reg_view()
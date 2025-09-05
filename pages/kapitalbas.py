# kapitalbas.py - UPPDATERAD med age_reg sektion

import streamlit as st

from kapitalbas.datafiler.data_loader import load_capcost_a, load_dmu_volymer, load_reconciliation
from kapitalbas.visualiseringsfiler.tidsserie_view import show_tidsserie
from kapitalbas.visualiseringsfiler.intensitet_view import show_intensity_analysis
from kapitalbas.visualiseringsfiler.översikt import show_capcost


st.set_page_config(page_title="Kapitalkostnader", layout="wide")
st.title("Kapitalkostnader")
st.markdown("Se över kapitalkostnader, beräkna nya kapitalkapitalkostnader, och exportera till intäktsramen eller DEA.")

# === Ladda data ===
st.session_state["capcost_a"] = load_capcost_a()
st.session_state["dmu_volymer"] = load_dmu_volymer()
st.session_state["reconciliation"] = load_reconciliation()


# === Välj sektion ===
sektion = st.sidebar.selectbox(
    "Välj del av kapitalbasen", 
    [
        "Kapitalkostnader", 
        "Tidsserie", 
        "Intensitetsanalys", 
    ]
)

# === Visa vald sektion ===
if sektion == "Kapitalkostnader":
    show_capcost(st.session_state["capcost_a"])

elif sektion == "Tidsserie":
    show_tidsserie(st.session_state["capcost_a"])

elif sektion == "Intensitetsanalys":
    show_intensity_analysis(
        st.session_state["capcost_a"],
        st.session_state["dmu_volymer"], 
        st.session_state["reconciliation"]
    )

# elif sektion == "Komponenter":
#    show_komponent_view(st.session_state["final_capbase_sample"])

# elif sektion == "Policy Playground":
#    show_policy_playground(capcost)


# elif sektion == "Livslängdssimulering":
#    show_livslangd_view()

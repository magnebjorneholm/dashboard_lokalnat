# kapitalbas.py

import streamlit as st
from kapitalbas.kapitalbas_app.data_loader import (
    load_main_data,
    load_component_sample,
    load_tail_full,
)
from kapitalbas.datafiler.data_loader import (
    load_capbase_b_sample,
    load_capbase_compress_tail_sample, load_capbase_compress_tail,
    load_capbase_compress, load_depreciation_compress_sample,
    load_depreciation_compress, load_depreciation,
    load_returns_compress_sample, load_returns_compress,
    load_capbase_a_sample, load_capbase_a,
    load_capcost_a_sample, load_capcost_a
)
from kapitalbas.kapitalbas_app.översikt_view import show_översikt
from kapitalbas.kapitalbas_app.tidsserie_view import show_tidsserie
from kapitalbas.kapitalbas_app.komponent_view import show_komponent_view
from kapitalbas.kapitalbas_app.policy_playground_view import show_policy_playground
from kapitalbas.kapitalbas_app.qa_view import show_qa
from kapitalbas.kapitalbas_app.livslangd_view import show_livslangd_view

from kapitalbas.visualiseringsfiler.översikt import show_capcost


st.title("Kapitalbas")

# === Ladda data ===
### st.session_state["capbase_b_sample"] = load_capbase_b_sample()
st.session_state["capbase_compress_tail_sample"] = load_capbase_compress_tail_sample()
st.session_state["capbase_compress_tail"] = load_capbase_compress_tail()
st.session_state["capbase_compress"] = load_capbase_compress()
st.session_state["depreciation_compress_sample"] = load_depreciation_compress_sample()
st.session_state["depreciation_compress"] = load_depreciation_compress()
### st.session_state["depreciation"] = load_depreciation()
st.session_state["returns_compress_sample"] = load_returns_compress_sample()
st.session_state["returns_compress"] = load_returns_compress()
st.session_state["capbase_a_sample"] = load_capbase_a_sample()
### st.session_state["capbase_a"] = load_capbase_a()
st.session_state["capcost_a_sample"] = load_capcost_a_sample()
st.session_state["capcost_a"] = load_capcost_a()


capbase, capcost = load_main_data()
st.session_state["final_capbase_sample"] = load_component_sample()
st.session_state["capbase_compress_tail"] = load_tail_full()
st.session_state["capcost_python"] = capcost


# === Välj sektion ===
sektion = st.sidebar.selectbox(
    "Välj del av kapitalbasen", ["Översikt", "Tidsserie", "QA", "Komponenter", "Policy Playground", "Livslängdssimulering", "Ny översikt"]
)

# === Visa vald sektion ===
if sektion == "Översikt":
    show_översikt(capbase)

elif sektion == "Tidsserie":
    show_tidsserie(capcost)

elif sektion == "Komponenter":
    show_komponent_view(st.session_state["final_capbase_sample"])

elif sektion == "Policy Playground":
    show_policy_playground(capcost)

elif sektion == "QA":
    show_qa()

elif sektion == "Livslängdssimulering":
    show_livslangd_view()

elif sektion == "Ny översikt":
    show_capcost(st.session_state["capcost_a"])
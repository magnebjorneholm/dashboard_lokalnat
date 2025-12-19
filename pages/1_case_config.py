"""
Case Configuration Page.

Huvudsida för att konfigurera ett case.
"""

import streamlit as st

from frontend.utils.state_manager import init_session_state, set_module_config, get_user_reid
from frontend.utils.config_adapter import build_case_definition, get_changed_parameters

from frontend.modules.base import (
    m1_asset_base,
    m2_depreciation,
    m3_cost_of_capital,
    m4_operating_exp,
    m5_efficiency,
)
from frontend.modules.addons import benchmarking

# Initialisera state
init_session_state()


# --- Cachade funktioner (måste definieras före användning) ---

@st.cache_data(ttl=3600, show_spinner="Laddar baseline data...")
def get_baseline_data():
    """Cachad baseline-data."""
    from data_loaders.baseline_data import load_baseline_data
    return load_baseline_data()


@st.cache_data(ttl=3600, show_spinner="Beräknar baseline...")
def get_baseline_result(_baseline_data, user_reid: str):
    """Cachad baseline-result per företag."""
    from config.case_definition import get_baseline_config
    from pipeline.core import run_pipeline
    
    baseline_config = get_baseline_config(user_reid)
    return run_pipeline(_baseline_data, baseline_config)


# --- Sidinnehåll ---

st.title("Regumetrica - Case Configuration")

# Kontrollera att företag är valt
user_reid = get_user_reid()
if user_reid is None:
    st.warning("Välj företag i sidopanelen för att fortsätta.")
    st.stop()

# Visa valt företag
st.info(f"Företag: **{user_reid}**")

# Visa ändrade parametrar i sidebar
if "ui_config" in st.session_state:
    changed = get_changed_parameters(st.session_state["ui_config"])
    if changed:
        with st.sidebar:
            st.markdown("### Ändrade parametrar")
            for param in changed:
                st.markdown(f"- {param}")
    else:
        with st.sidebar:
            st.caption("Alla parametrar = baseline")

# Tabs för modules
tab1, tab2, tab3, tab4, tab5, tab_addons = st.tabs([
    "1. Asset Base",
    "2. Depreciation",
    "3. Cost of Capital",
    "4. OPEX",
    "5. Efficiency",
    "Add-ons"
])

with tab1:
    config = m1_asset_base.render()
    set_module_config("m1_asset_base", config)

with tab2:
    config = m2_depreciation.render()
    set_module_config("m2_depreciation", config)

with tab3:
    # WACC-konfiguration
    config = m3_cost_of_capital.render()
    set_module_config("m3_cost_of_capital", config)
    
    st.divider()
    
    # Incitamentjusteringar (3.3-3.6)
    qa_config = m3_cost_of_capital.render_quality_adjustments()
    set_module_config("m3_quality_adjustments", qa_config)

with tab4:
    config = m4_operating_exp.render()
    set_module_config("m4_operating_exp", config)

with tab5:
    config = m5_efficiency.render()
    set_module_config("m5_efficiency", config)

with tab_addons:
    config = benchmarking.render()
    set_module_config("addon_benchmarking", config)

# Beräkna-knapp
st.divider()

if st.button("BERÄKNA INTÄKTSRAM", type="primary", use_container_width=True):
    
    with st.status("Kör beräkning...", expanded=True) as status:
        
        try:
            # Ladda baseline data (cachad)
            st.write("Laddar baseline data...")
            baseline_data = get_baseline_data()
            
            # Hämta baseline-resultat (cachad per företag)
            st.write("Hämtar baseline...")
            baseline_result = get_baseline_result(baseline_data, user_reid)
            st.session_state["baseline_result"] = baseline_result
            
            # Bygg case definition
            st.write("Bygger case...")
            case_definition = build_case_definition(
                user_reid,
                st.session_state["ui_config"]
            )
            
            # Kör pipeline
            st.write("Beräknar intäktsram...")
            from pipeline.core import run_pipeline
            case_result = run_pipeline(baseline_data, case_definition)
            st.session_state["case_result"] = case_result
            
            st.session_state["calculation_done"] = True
            status.update(label="Beräkning klar!", state="complete")
            
        except ValueError as e:
            st.error(f"Konfigurationsfel: {e}")
            status.update(label="Fel!", state="error")
            st.stop()
        except Exception as e:
            st.error(f"Beräkningsfel: {e}")
            with st.expander("Teknisk information"):
                st.exception(e)
            status.update(label="Fel!", state="error")
            st.stop()
    
    # Navigera till resultat
    st.switch_page("pages/2_results.py")
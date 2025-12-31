"""
Case Configuration Page.

Main page for configuring a regulatory case.
"""

import streamlit as st

from frontend.utils.state_manager import init_session_state, set_module_config, get_user_reid
from frontend.utils.config_adapter import build_case_definition, get_changed_parameters

from frontend.modules.base import (
    m1_asset_base,
    m2_depreciation,
    m3_cost_of_capital,
    m3_incentive_variables,
    m4_operating_exp,
    m5_efficiency,
)
from frontend.modules.addons import benchmarking

# Initialize state
init_session_state()


# --- Cached functions (must be defined before use) ---

@st.cache_data(ttl=3600, show_spinner="Loading baseline data...")
def get_baseline_data():
    """Cached baseline data."""
    from data_loaders.baseline_data import load_baseline_data
    return load_baseline_data()


@st.cache_data(ttl=3600, show_spinner="Calculating baseline...")
def get_baseline_result(_baseline_data, user_reid: str):
    """Cached baseline result per company."""
    from config.case_definition import get_baseline_config
    from pipeline.core import run_pipeline
    
    baseline_config = get_baseline_config(user_reid)
    return run_pipeline(_baseline_data, baseline_config)


# --- Page content ---

st.title("Regumetrica - Case Configuration")

# Check that company is selected
user_reid = get_user_reid()
if user_reid is None:
    st.warning("Select a company in the sidebar to continue.")
    st.stop()

# Show selected company
st.info(f"Company: **{user_reid}**")

# Show changed parameters in sidebar
if "ui_config" in st.session_state:
    changed = get_changed_parameters(st.session_state["ui_config"])
    if changed:
        with st.sidebar:
            st.markdown("### Modified Parameters")
            for param in changed:
                st.markdown(f"- {param}")
    else:
        with st.sidebar:
            st.caption("All parameters at baseline")

# Tabs for modules
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
    # WACC parameters
    config = m3_cost_of_capital.render()
    set_module_config("m3_cost_of_capital", config)
    
    st.divider()
    
    # Quality adjustments (parameters affecting all companies)
    qa_config = m3_cost_of_capital.render_quality_adjustments()
    set_module_config("m3_quality_adjustments", qa_config)
    
    st.divider()
    
    # Incentive variables (company-specific observed/norm values)
    var_config = m3_incentive_variables.render()
    set_module_config("m3_incentive_variables", var_config)

with tab4:
    config = m4_operating_exp.render()
    set_module_config("m4_operating_exp", config)

with tab5:
    config = m5_efficiency.render()
    set_module_config("m5_efficiency", config)

with tab_addons:
    config = benchmarking.render()
    set_module_config("addon_benchmarking", config)

# Calculate button
st.divider()

if st.button("CALCULATE REVENUE FRAME", type="primary", use_container_width=True):
    
    with st.status("Running calculation...", expanded=True) as status:
        
        try:
            # Load baseline data (cached)
            st.write("Loading baseline data...")
            baseline_data = get_baseline_data()
            
            # Retrieve baseline result (cached per company)
            st.write("Retrieving baseline...")
            baseline_result = get_baseline_result(baseline_data, user_reid)
            st.session_state["baseline_result"] = baseline_result
            
            # Build case definition
            st.write("Building case...")
            case_definition = build_case_definition(
                user_reid,
                st.session_state["ui_config"]
            )
            
            # Run pipeline
            st.write("Calculating revenue frame...")
            from pipeline.core import run_pipeline
            case_result = run_pipeline(baseline_data, case_definition)
            st.session_state["case_result"] = case_result
            
            st.session_state["calculation_done"] = True
            status.update(label="Calculation complete", state="complete")
            
        except ValueError as e:
            st.error(f"Configuration error: {e}")
            status.update(label="Error", state="error")
            st.stop()
        except Exception as e:
            st.error(f"Calculation error: {e}")
            with st.expander("Technical Details"):
                st.exception(e)
            status.update(label="Error", state="error")
            st.stop()
    
    # Navigate to results
    st.switch_page("pages/2_results.py")
"""
Case Configuration Page.

Main page for configuring a regulatory case.
"""

import streamlit as st

from frontend.utils.state_manager import init_session_state, set_module_config, get_user_reid
from frontend.utils.config_adapter import get_changed_parameters

from frontend.modules.base import (
    m1_asset_base,
    m1_rab_editor,
    m2_depreciation,
    m3_cost_of_capital,
    m3_incentive_variables,
    m4_operating_exp,
    m5_efficiency,
    case_summary,
)
from frontend.modules.addons import benchmarking

# Initialize state
init_session_state()


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
tab1, tab2, tab3, tab4, tab5, tab_addons, tab_summary = st.tabs([
    "1. Regulatory asset base valuation",
    "2. Depreciation",
    "3. Cost of capital",
    "4. Operating expenditures",
    "5. Efficiency incentive",
    "7. Add-on modules",
    "Case summary"
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

with tab_summary:
    case_summary.render()
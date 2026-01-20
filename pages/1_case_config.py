"""
Case Configuration Page.

Main page for configuring a regulatory case.
Renders only selected modules as scrollable sections.
"""

import streamlit as st

from frontend.utils.state_manager import (
    init_session_state,
    set_module_config,
    get_user_reid,
    get_user_id_network,
    get_case_name,
    get_selected_modules,
    is_module_selected,
)
from frontend.utils.config_adapter import get_changed_parameters

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


# =============================================================================
# PAGE HEADER
# =============================================================================

st.title("Regumetrica")

# Show case name
case_name = get_case_name()
if case_name:
    st.subheader(f"Configure: {case_name}")
else:
    st.subheader("Configure")

# Check that company is selected
user_reid = get_user_reid()
if user_reid is None:
    st.warning("Select a company in the sidebar to continue.")
    st.stop()

# Get user_id_network for company-specific sections
user_id_network = get_user_id_network()

# Check which modules are selected
selected_modules = get_selected_modules()
has_selection = len(selected_modules) > 0

if has_selection:
    st.caption(f"Configuring {len(selected_modules)} selected module(s). Other modules use baseline values.")
else:
    st.caption("No modules selected - running baseline simulation.")


# =============================================================================
# SIDEBAR: MODIFIED PARAMETERS
# =============================================================================

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


# =============================================================================
# MODULE SECTIONS (Conditional rendering)
# =============================================================================

def render_module_section(
    module_key: str,
    title: str,
    render_func,
    config_key: str,
    **render_kwargs
) -> None:
    """
    Render a module section if selected.
    
    Args:
        module_key: Module key (e.g., "m1")
        title: Section title
        render_func: Function to render the module
        config_key: Key for set_module_config
        **render_kwargs: Additional kwargs passed to render_func
    """
    if not is_module_selected(module_key):
        return
    
    st.divider()
    
    with st.container():
        config = render_func(**render_kwargs)
        set_module_config(config_key, config)


# --- Module 1: Regulatory asset base valuation ---
if is_module_selected("m1"):
    st.divider()
    config = m1_asset_base.render(user_id_network=user_id_network)
    set_module_config("m1_asset_base", config)


# --- Module 2: Depreciation ---
if is_module_selected("m2"):
    st.divider()
    config = m2_depreciation.render()
    set_module_config("m2_depreciation", config)


# --- Module 3: Cost of capital ---
if is_module_selected("m3"):
    st.divider()
    
    # WACC parameters
    config = m3_cost_of_capital.render()
    set_module_config("m3_cost_of_capital", config)
    
    st.markdown("")
    
    # Quality adjustments (parameters affecting all companies)
    qa_config = m3_cost_of_capital.render_quality_adjustments()
    set_module_config("m3_quality_adjustments", qa_config)
    
    st.markdown("")
    
    # Incentive variables (company-specific observed/norm values)
    var_config = m3_incentive_variables.render()
    set_module_config("m3_incentive_variables", var_config)


# --- Module 4: Operating expenditures ---
if is_module_selected("m4"):
    st.divider()
    config = m4_operating_exp.render()
    set_module_config("m4_operating_exp", config)


# --- Module 5: Efficiency incentive ---
if is_module_selected("m5"):
    st.divider()
    config = m5_efficiency.render()
    set_module_config("m5_efficiency", config)


# --- Module 7: Add-on modules (Benchmarking) ---
if is_module_selected("m7"):
    st.divider()
    config = benchmarking.render()
    set_module_config("addon_benchmarking", config)


# =============================================================================
# END OF CONFIGURATION
# =============================================================================
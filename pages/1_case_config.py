"""
Case Configuration Page.

Main page for configuring a regulatory case.
Renders only selected modules/sections as scrollable sections.
"""

import streamlit as st

from frontend.utils.state_manager import (
    init_session_state,
    set_module_config,
    get_user_reid,
    get_user_id_network,
    get_case_name,
    get_selected_modules,
    is_section_selected,
)

from frontend.modules.base import (
    m1_asset_base,
    m2_depreciation,
    m3_cost_of_capital,
    m3_incentive_variables,
    m4_operating_exp,
    m5_efficiency,
)
from frontend.modules.addons import benchmarking

init_session_state()


# =============================================================================
# PAGE HEADER
# =============================================================================

st.title("Regumetrica")

case_name = get_case_name()
if case_name:
    st.subheader(f"Configure: {case_name}")
else:
    st.subheader("Configure")

user_reid = get_user_reid()
if user_reid is None:
    st.warning("Select a company in the sidebar to continue.")
    st.stop()

user_id_network = get_user_id_network()

selected_modules = get_selected_modules()
has_selection = len(selected_modules) > 0

if has_selection:
    st.caption(f"Configuring {len(selected_modules)} selected item(s). Unselected items use baseline values.")
else:
    st.caption("No modules selected - running baseline simulation.")


# =============================================================================
# MODULE SECTIONS (Conditional rendering based on section selection)
# =============================================================================

# --- Module 1: Regulatory asset base valuation ---

if is_section_selected("m1", "scaling"):
    st.divider()
    scaling_config = m1_asset_base.render_scaling(user_id_network=user_id_network)
    current_config = st.session_state.get("ui_config", {}).get("m1_asset_base", {})
    current_config.update(scaling_config)
    set_module_config("m1_asset_base", current_config)

if is_section_selected("m1", "quantities"):
    st.divider()
    quantities_config = m1_asset_base.render_quantities(user_id_network=user_id_network)
    current_config = st.session_state.get("ui_config", {}).get("m1_asset_base", {})
    current_config.update(quantities_config)
    set_module_config("m1_asset_base", current_config)

if is_section_selected("m1", "kent"):
    st.divider()
    kent_config = m1_asset_base.render_kent(user_id_network=user_id_network)
    current_config = st.session_state.get("ui_config", {}).get("m1_asset_base", {})
    current_config.update(kent_config)
    if kent_config.get("kent_file_bytes"):
        current_config.pop("var_scaling", None)
    set_module_config("m1_asset_base", current_config)


# --- Module 2: Depreciation ---

if is_section_selected("m2", "lifetimes"):
    st.divider()
    config = m2_depreciation.render_lifetimes()
    set_module_config("m2_depreciation", config)


# --- Module 3: Cost of capital ---

if is_section_selected("m3", "wacc"):
    st.divider()
    config = m3_cost_of_capital.render_wacc()
    set_module_config("m3_cost_of_capital", config)

if is_section_selected("m3", "incentive_params"):
    st.divider()
    qa_config = m3_cost_of_capital.render_incentive_params()
    set_module_config("m3_quality_adjustments", qa_config)

if is_section_selected("m3", "incentive_vars"):
    st.divider()
    var_config = m3_incentive_variables.render_incentive_vars()
    set_module_config("m3_incentive_variables", var_config)


# --- Module 4: Operating expenditures ---

if is_section_selected("m4", "scaling"):
    st.divider()
    config = m4_operating_exp.render_scaling()
    set_module_config("m4_operating_exp", config)

if is_section_selected("m4", "opex_vars"):
    st.divider()
    var_config = m4_operating_exp.render_opex_vars()
    current_config = st.session_state.get("ui_config", {}).get("m4_operating_exp", {})
    current_config.update(var_config)
    set_module_config("m4_operating_exp", current_config)


# --- Module 5: Efficiency incentive ---

if is_section_selected("m5", "efficiency_params"):
    st.divider()
    config = m5_efficiency.render_efficiency_params()
    set_module_config("m5_efficiency", config)


# --- Module 7: Add-on modules (Benchmarking) ---

if is_section_selected("m7", "dea_spec"):
    st.divider()
    config = benchmarking.render_dea_spec()
    set_module_config("addon_benchmarking", config)


# =============================================================================
# END OF CONFIGURATION
# =============================================================================

if not has_selection:
    st.info(
        "No modules are selected. Go to the **Define** page to select "
        "which modules you want to configure, or proceed with baseline values."
    )
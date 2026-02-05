"""
Case Configuration Page.

Main page for configuring a regulatory case.
Renders modules in tabs - only selected modules are active.
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
    is_module_selected,
    has_main_config,
    restore_main_config,
    is_snapshot_calculation,
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

# Restore main config if navigating back from a snapshot calculation
# Only triggers when case_result differs from main (i.e. a snapshot calc was run)
# Does NOT trigger on normal reruns, allowing the user to edit freely
if has_main_config() and is_snapshot_calculation():
    restore_main_config()


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
# TAB CONFIGURATION
# =============================================================================

def _tab_label(module_key: str, name: str) -> str:
    """Return tab label with gray color if module not selected."""
    if not is_module_selected(module_key):
        return f":gray[{name}]"
    return name


def _render_not_selected_message():
    """Render message for non-selected modules."""
    st.info(
        "This module is not selected for configuration. "
        "Go to **Define** to enable it, or proceed with baseline values."
    )


tab_labels = [
    _tab_label("m1", "M1 Regulatory asset base valuation"),
    _tab_label("m2", "M2 Depreciation"),
    _tab_label("m3", "M3 Cost of Capital"),
    _tab_label("m4", "M4 Operating expenditures"),
    _tab_label("m5", "M5 Efficiency incentive"),
    _tab_label("m7", "M7 Benchmarking"),
]

tabs = st.tabs(tab_labels)


# =============================================================================
# TAB 1: REGULATORY ASSET BASE
# =============================================================================

with tabs[0]:
    if not is_module_selected("m1"):
        _render_not_selected_message()
    else:
        st.markdown("#### 1. Regulatory Asset Base")
        
        # Section: Scaling factors (1.1, 1.2)
        if is_section_selected("m1", "scaling"):
            scaling_config = m1_asset_base.render_scaling(user_id_network=user_id_network)
            current_config = st.session_state.get("ui_config", {}).get("m1_asset_base", {})
            current_config.update(scaling_config)
            set_module_config("m1_asset_base", current_config)
        
        # Section: Asset quantities (1.3)
        if is_section_selected("m1", "quantities"):
            if is_section_selected("m1", "scaling"):
                st.divider()
            quantities_config = m1_asset_base.render_quantities(user_id_network=user_id_network)
            current_config = st.session_state.get("ui_config", {}).get("m1_asset_base", {})
            current_config.update(quantities_config)
            set_module_config("m1_asset_base", current_config)
        
        # Section: KENT upload (1.4)
        if is_section_selected("m1", "kent"):
            if is_section_selected("m1", "scaling") or is_section_selected("m1", "quantities"):
                st.divider()
            kent_config = m1_asset_base.render_kent(user_id_network=user_id_network)
            current_config = st.session_state.get("ui_config", {}).get("m1_asset_base", {})
            current_config.update(kent_config)
            if kent_config.get("kent_file_bytes"):
                current_config.pop("var_scaling", None)
            set_module_config("m1_asset_base", current_config)


# =============================================================================
# TAB 2: DEPRECIATION
# =============================================================================

with tabs[1]:
    if not is_module_selected("m2"):
        _render_not_selected_message()
    else:
        st.markdown("#### 2. Depreciation")
        
        if is_section_selected("m2", "lifetimes"):
            config = m2_depreciation.render_lifetimes()
            set_module_config("m2_depreciation", config)


# =============================================================================
# TAB 3: COST OF CAPITAL
# =============================================================================

with tabs[2]:
    if not is_module_selected("m3"):
        _render_not_selected_message()
    else:
        st.markdown("#### 3. Cost of Capital")
        
        # Section: WACC (3.1-3.2)
        if is_section_selected("m3", "wacc"):
            config = m3_cost_of_capital.render_wacc()
            set_module_config("m3_cost_of_capital", config)
        
        # Section: Incentive parameters (3.3-3.6)
        if is_section_selected("m3", "incentive_params"):
            if is_section_selected("m3", "wacc"):
                st.divider()
            qa_config = m3_cost_of_capital.render_incentive_params()
            set_module_config("m3_quality_adjustments", qa_config)
        
        # Section: Incentive variables (30.X)
        if is_section_selected("m3", "incentive_vars"):
            if is_section_selected("m3", "wacc") or is_section_selected("m3", "incentive_params"):
                st.divider()
            var_config = m3_incentive_variables.render_incentive_vars()
            set_module_config("m3_incentive_variables", var_config)


# =============================================================================
# TAB 4: OPERATING EXPENDITURES
# =============================================================================

with tabs[3]:
    if not is_module_selected("m4"):
        _render_not_selected_message()
    else:
        st.markdown("#### 4. Operating Expenditures")
        
        # Section: OPEX scaling (4.1)
        if is_section_selected("m4", "scaling"):
            config = m4_operating_exp.render_scaling()
            set_module_config("m4_operating_exp", config)
        
        # Section: OPEX variables (40.X)
        if is_section_selected("m4", "opex_vars"):
            if is_section_selected("m4", "scaling"):
                st.divider()
            var_config = m4_operating_exp.render_opex_vars()
            current_config = st.session_state.get("ui_config", {}).get("m4_operating_exp", {})
            current_config.update(var_config)
            set_module_config("m4_operating_exp", current_config)


# =============================================================================
# TAB 5: EFFICIENCY INCENTIVE
# =============================================================================

with tabs[4]:
    if not is_module_selected("m5"):
        _render_not_selected_message()
    else:
        st.markdown("#### 5. Efficiency Incentive")
        
        if is_section_selected("m5", "efficiency_params"):
            config = m5_efficiency.render_efficiency_params()
            set_module_config("m5_efficiency", config)


# =============================================================================
# TAB 6: BENCHMARKING (ADD-ON)
# =============================================================================

with tabs[5]:
    if not is_module_selected("m7"):
        _render_not_selected_message()
    else:
        st.markdown("#### 7. Benchmarking")
        
        if is_section_selected("m7", "dea_spec"):
            config = benchmarking.render_dea_spec()
            set_module_config("addon_benchmarking", config)
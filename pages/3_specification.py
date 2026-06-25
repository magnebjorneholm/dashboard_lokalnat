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
from frontend.common.manuals import module_manual_panel
from config.module_registry import get_module

init_session_state()


# =============================================================================
# PAGE HEADER
# =============================================================================

case_name = get_case_name()
st.subheader("3. Configure selected modules")
if case_name:
    st.caption(f"Active case: {case_name}")

from frontend.common.save_bar import render_save_bar
render_save_bar()

user_reid = get_user_reid()
if user_reid is None:
    st.warning("Select a company in the sidebar to continue.")
    st.stop()

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
        "Go to **Case Setup** to enable it, or proceed with baseline values."
    )


tab_labels = [
    _tab_label(key, get_module(key).title)
    for key in ("m1", "m2", "m3", "m4", "m5")
]

tabs = st.tabs(tab_labels)


# =============================================================================
# FRAGMENT FUNCTIONS — one per tab
# Each fragment isolates widget reruns: changing a parameter in one tab
# does not re-render the other tabs.
# =============================================================================

@st.fragment
def _render_m1_tab():
    if not is_module_selected("m1"):
        _render_not_selected_message()
        return

    user_id_network = get_user_id_network()
    st.markdown(f"#### {get_module('m1').title}")
    module_manual_panel("m1")

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
        # Warn only if case had KENT but neither raw bytes nor saved capbase exists
        m1_cfg = st.session_state.get("ui_config", {}).get("m1_asset_base", {})
        if (m1_cfg.get("kent_file_name")
                and not m1_cfg.get("kent_file_bytes")
                and not m1_cfg.get("kent_capbase_parquet")):
            st.warning(
                f"This case originally used a KENT file "
                f"(**{m1_cfg['kent_file_name']}**) which was not saved. "
                f"Re-upload the file below to restore KENT-based calculations."
            )
        kent_config = m1_asset_base.render_kent(user_id_network=user_id_network)
        current_config = st.session_state.get("ui_config", {}).get("m1_asset_base", {})
        current_config.update(kent_config)
        if kent_config.get("kent_file_bytes"):
            current_config.pop("var_scaling", None)
        set_module_config("m1_asset_base", current_config)


@st.fragment
def _render_m2_tab():
    if not is_module_selected("m2"):
        _render_not_selected_message()
        return

    user_id_network = get_user_id_network()
    st.markdown(f"#### {get_module('m2').title}")
    module_manual_panel("m2")

    if is_section_selected("m2", "lifetimes"):
        config = m2_depreciation.render_lifetimes(user_id_network=user_id_network)
        set_module_config("m2_depreciation", config)


@st.fragment
def _render_m3_tab():
    if not is_module_selected("m3"):
        _render_not_selected_message()
        return

    st.markdown(f"#### {get_module('m3').title}")
    module_manual_panel("m3")

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


@st.fragment
def _render_m4_tab():
    if not is_module_selected("m4"):
        _render_not_selected_message()
        return

    st.markdown(f"#### {get_module('m4').title}")
    module_manual_panel("m4")

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


@st.fragment
def _render_m5_tab():
    if not is_module_selected("m5"):
        _render_not_selected_message()
        return

    st.markdown(f"#### {get_module('m5').title}")
    module_manual_panel("m5")

    # Section: Benchmarking (DEA specification) — measures relative efficiency
    if is_section_selected("m5", "benchmarking"):
        config = benchmarking.render_dea_spec()
        set_module_config("m5_benchmarking", config)

    # Section: Efficiency requirement — applies the measured efficiency to the frame
    if is_section_selected("m5", "efficiency_params"):
        if is_section_selected("m5", "benchmarking"):
            st.divider()
        config = m5_efficiency.render_efficiency_params()
        set_module_config("m5_efficiency", config)


# =============================================================================
# RENDER TABS — each fragment is called inside its tab context
# =============================================================================

with tabs[0]:
    _render_m1_tab()

with tabs[1]:
    _render_m2_tab()

with tabs[2]:
    _render_m3_tab()

with tabs[3]:
    _render_m4_tab()

with tabs[4]:
    _render_m5_tab()
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
        # Warn if case originally had KENT file that wasn't restored
        m1_cfg = st.session_state.get("ui_config", {}).get("m1_asset_base", {})
        if m1_cfg.get("kent_file_name") and not m1_cfg.get("kent_file_bytes"):
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

    st.markdown("#### 2. Depreciation")

    if is_section_selected("m2", "lifetimes"):
        config = m2_depreciation.render_lifetimes()
        set_module_config("m2_depreciation", config)


@st.fragment
def _render_m3_tab():
    if not is_module_selected("m3"):
        _render_not_selected_message()
        return

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


@st.fragment
def _render_m4_tab():
    if not is_module_selected("m4"):
        _render_not_selected_message()
        return

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


@st.fragment
def _render_m5_tab():
    if not is_module_selected("m5"):
        _render_not_selected_message()
        return

    st.markdown("#### 5. Efficiency Incentive")

    if is_section_selected("m5", "efficiency_params"):
        config = m5_efficiency.render_efficiency_params()
        set_module_config("m5_efficiency", config)


@st.fragment
def _render_m7_tab():
    if not is_module_selected("m7"):
        _render_not_selected_message()
        return

    st.markdown("#### 7. Benchmarking")

    if is_section_selected("m7", "dea_spec"):
        config = benchmarking.render_dea_spec()
        set_module_config("addon_benchmarking", config)

        # --- Mini-run ---
        if st.button("Run DEA", type="secondary", key="mini_run_dea_btn"):
            _execute_dea_mini_run(config)

        _render_mini_run_stale_indicator()

        mini_result = st.session_state.get("mini_run_result")
        mini_baseline = st.session_state.get("mini_run_baseline")
        if mini_result is not None and mini_baseline is not None:
            from frontend.results.m7_mini_run_output import render_mini_results
            render_mini_results(mini_result, mini_baseline)


def _build_eff_req_params() -> dict:
    """Read current M5 parameters from ui_config for efficiency requirement calc."""
    m5 = st.session_state.get("ui_config", {}).get("m5_efficiency", {})
    params = {}

    v = m5.get("trunkering_max")
    if v is not None:
        params["truncation_max"] = v

    v = m5.get("trunkering_min")
    if v is not None:
        params["truncation_min"] = v

    v = m5.get("outlier_krav")
    if v is not None:
        params["outlier_req"] = v

    v = m5.get("kunddelning")
    if v is not None:
        params["customer_sharing"] = v

    v = m5.get("realiseringstid")
    if v is not None:
        params["realization_time"] = v

    v = m5.get("tillsynsperiod")
    if v is not None:
        params["supervision_period"] = v

    return params


def _execute_dea_mini_run(addon_config: dict) -> None:
    """Run DEA mini-run and store results in session state."""
    import copy

    user_reid = get_user_reid()
    if not user_reid:
        st.error("Select a company first.")
        return

    with st.spinner("Running DEA analysis..."):
        try:
            from data_loaders.baseline_data import load_baseline_data
            from pipeline.mini_run import run_dea_mini
            from config.config_adapter import build_dea_config
            from config.case_definition import DeaConfig

            baseline_data = load_baseline_data()

            # Build DEA config from current M7 settings
            ui_config = st.session_state.get("ui_config", {})
            dea_config = build_dea_config(ui_config)

            # Current M5 params for efficiency requirement
            eff_req_params = _build_eff_req_params()

            # Case mini-run: current DEA spec + current M5
            case_result = run_dea_mini(
                baseline_data, dea_config, user_reid, eff_req_params or None
            )

            # Baseline mini-run: baseline DEA + baseline M5 (defaults)
            bl = st.session_state.get("mini_run_baseline")
            if bl is None or bl.user_reid != user_reid:
                baseline_result = run_dea_mini(
                    baseline_data, DeaConfig(), user_reid
                )
            else:
                baseline_result = bl

            st.session_state["mini_run_result"] = case_result
            st.session_state["mini_run_baseline"] = baseline_result
            st.session_state["mini_run_config_snapshot"] = {
                "addon_benchmarking": copy.deepcopy(addon_config),
                "m5_efficiency": copy.deepcopy(
                    ui_config.get("m5_efficiency", {})
                ),
            }
        except Exception as e:
            st.error(f"DEA mini-run failed: {e}")


def _render_mini_run_stale_indicator() -> None:
    """Show warning if M7/M5 config changed since last mini-run."""
    snapshot = st.session_state.get("mini_run_config_snapshot")
    if snapshot is None:
        return

    ui_config = st.session_state.get("ui_config", {})
    current_m7 = ui_config.get("addon_benchmarking", {})
    current_m5 = ui_config.get("m5_efficiency", {})

    if current_m7 != snapshot.get("addon_benchmarking") or current_m5 != snapshot.get("m5_efficiency"):
        st.caption(":orange[Config changed since last run]")


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

with tabs[5]:
    _render_m7_tab()
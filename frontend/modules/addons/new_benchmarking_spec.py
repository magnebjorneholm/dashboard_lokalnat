"""
new_benchmarking_spec.py — fine-tuning controls for the new benchmarking model add-on.

Renders the (few) parameters a user may adjust on top of the fixed "main model" and
returns a fully-formed NewBenchmarkingConfig. Everything not exposed here — TOTEX
composition, outputs, returns to scale — is fixed at the main-model reference reading
(see calculations/new_benchmarking/config.py).

This add-on is standalone (its own page) and does NOT flow through the case/ui_config
system, so it builds the config object directly rather than a ui_config dict.
"""

from __future__ import annotations

import streamlit as st

from calculations.new_benchmarking.config import NewBenchmarkingConfig
from calculations.new_benchmarking.cable_length import C as cable_C
from calculations.new_benchmarking.environment_capex_adjustment import config as env_C
from calculations.new_benchmarking.station_capex_adjustment import config as st_C
from config.incentive_parameters import K_NF

# Common loss price (kr/MWh) at the main-model reference reading. Derived from the
# single source of truth K_NF so the panel default never drifts from the model.
BASELINE_K_NF = float(next(iter(K_NF.values())))

# Human-readable labels + per-method explanations for the placement-environment methods.
_CABLE_METHOD_LABELS = {
    env_C.METHOD_EXACT: "Exact",
    env_C.METHOD_SCHABLON_PER_KM: "Schablon (kr/km)",
    env_C.METHOD_SCHABLON_PERCENT: "Schablon (%)",
}
_CABLE_METHOD_HELP = {
    env_C.METHOD_EXACT:
        "Re-prices each cable type down to the landsbygd-normal level. Most precise of the "
        "three methods. Types without a reference price fall back to the per-km schablon.",
    env_C.METHOD_SCHABLON_PER_KM:
        "Deducts a flat premium (kr/km) per placement environment.",
    env_C.METHOD_SCHABLON_PERCENT:
        "Deducts a flat percentage of value per placement environment (Ei's schablon).",
}
_STATION_METHOD_LABELS = {
    st_C.METHOD_EXACT: "Exact",
    st_C.METHOD_SCHABLON_PERCENT: "Schablon (%)",
}
_STATION_METHOD_HELP = {
    st_C.METHOD_EXACT:
        "Removes the City/tätort station surcharge in full. Exact, per company.",
    st_C.METHOD_SCHABLON_PERCENT:
        "Deducts a flat percentage across the whole station base (Ei's schablon).",
}


def render_config_panel() -> NewBenchmarkingConfig:
    """Render the fine-tuning controls and return the *active* NewBenchmarkingConfig.

    Only three things are adjustable on top of the fixed main model: the common loss
    price, the placement-environment methods (cable + station), and which line types
    feed the cable-length output. All other fields keep their main-model defaults.

    The DEA run is heavy, so it must not fire on every widget edit. The returned config
    therefore reflects the last config the user committed via the "Run experiment" button
    (or the main model before any run) — not the live widget values. Editing widgets only
    marks pending changes; nothing recomputes until the button is clicked.
    """
    st.caption(
        "These settings adjust the main model. Everything else is fixed at the main-model "
        "specification: TOTEX composition, outputs and returns to scale."
    )

    # ── Common loss price (price-area correction) ───────────────────────────
    k_nf = st.number_input(
        "Common loss price (kr/MWh)",
        min_value=0.0, value=BASELINE_K_NF, step=10.0,
        help=f"Network losses are valued as nf_obs · price · e_in. Main model: {BASELINE_K_NF:g} kr/MWh.",
        key="nb_k_nf",
    )

    # ── Placement-environment methods (capex levelling) ─────────────────────
    col_cable, col_station = st.columns(2)
    with col_cable:
        cable_method = st.selectbox(
            "Cable method",
            options=list(env_C.METHODS),
            index=list(env_C.METHODS).index(env_C.METHOD_EXACT),
            format_func=lambda m: _CABLE_METHOD_LABELS.get(m, m),
            key="nb_cable_method",
        )
        st.caption(_CABLE_METHOD_HELP[cable_method])
    with col_station:
        station_method = st.selectbox(
            "Station method",
            options=list(st_C.METHODS),
            index=list(st_C.METHODS).index(st_C.METHOD_EXACT),
            format_func=lambda m: _STATION_METHOD_LABELS.get(m, m),
            key="nb_station_method",
        )
        st.caption(_STATION_METHOD_HELP[station_method])

    # ── Line types in the cable-length output ───────────────────────────────
    cable_types = st.multiselect(
        "Line types in cable length",
        options=list(cable_C.ALL_TYPES),
        default=list(cable_C.ELECTRICAL_TYPES),
        format_func=lambda t: cable_C.TYPE_LABELS.get(t, t),
        help="Physical line length (km) used as a structural output. "
             "Default excludes optical fibre (optokabel).",
        key="nb_cable_types",
    )

    pending = NewBenchmarkingConfig(
        k_nf={2024: k_nf, 2025: k_nf, 2026: k_nf, 2027: k_nf},
        cable_method=cable_method,
        station_method=station_method,
        cable_types=tuple(cable_types),
    )

    # Active config = the last one the user ran (or the main model). Widgets above only
    # build `pending`; the heavy DEA run fires only when the button commits it.
    committed = st.session_state.get("nb_committed_cfg")
    if committed is None:
        committed = NewBenchmarkingConfig()

    st.divider()
    if pending.signature() != committed.signature():
        st.caption("⚠ Pending changes. Click **Run experiment** to apply them.")

    main_cfg = NewBenchmarkingConfig()
    experiment_active = committed.signature() != main_cfg.signature()

    col_run, col_reset = st.columns(2)
    with col_run:
        if st.button("Run experiment", type="primary", key="nb_run_experiment"):
            st.session_state["nb_committed_cfg"] = pending
            committed = pending
    with col_reset:
        # Clears the committed config and the widget keys so the panel falls back to
        # the main-model defaults on rerun. Disabled when already on the main model.
        if st.button("Reset to main model", key="nb_reset", disabled=not experiment_active):
            for k in ("nb_committed_cfg", "nb_k_nf", "nb_cable_method",
                      "nb_station_method", "nb_cable_types"):
                st.session_state.pop(k, None)
            st.rerun()

    return committed

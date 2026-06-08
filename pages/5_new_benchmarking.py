"""
Page 5 — New benchmarking model (isolated add-on).

Standalone analysis of Ei's proposed new benchmarking model: builds a new TOTEX for all
148 companies and shows how the selected company's efficiency and — above all —
efficiency requirement would change versus its current published values (EIs_DEA).

This page is decoupled from the case/revenue-frame pipeline: it calls
run_new_benchmarking() directly with its own config and does not produce a CaseDefinition.
"""

from __future__ import annotations

import streamlit as st

from frontend.utils.state_manager import init_session_state, get_user_reid
from frontend.modules.addons.new_benchmarking_spec import render_config_panel
from frontend.results.new_benchmarking_output import render_company_view
from calculations.new_benchmarking import run_new_benchmarking, NewBenchmarkingConfig

init_session_state()


# ---------------------------------------------------------------------------
# Cached run — keyed on a config signature; baseline data is loaded internally
# (and itself cached). The actual cfg is passed underscore-prefixed so Streamlit
# does not try to hash it.
# ---------------------------------------------------------------------------

def _signature(cfg: NewBenchmarkingConfig) -> tuple:
    def _od(d):  # ordered, hashable view of an optional dict
        return tuple(sorted(d.items())) if d else None
    return (
        _od(cfg.resolved_k_nf()),
        cfg.include_controllable, cfg.include_losses, cfg.include_capex,
        tuple(cfg.non_controllable_categories),
        cfg.cable_method, _od(cfg.cable_override_percent),
        cfg.station_method, _od(cfg.station_override_percent),
        cfg.include_cable_length, tuple(cfg.cable_types), cfg.split_by_voltage,
        cfg.rts, tuple(cfg.new_base_outputs),
        tuple(sorted(cfg.eff_req_params.items())),
    )


@st.cache_data(show_spinner="Kör den nya benchmarking-modellen för alla 148 företag…")
def _run_cached(signature: tuple, _cfg: NewBenchmarkingConfig):
    return run_new_benchmarking(_cfg)


@st.cache_data(ttl=3600)
def _company_name(reid: str) -> str:
    try:
        from data_loaders.baseline_data import load_baseline_data
        from config.column_names import COL_COMPANY_NAME
        df = load_baseline_data().df_all_companies
        m = df[df["REId"] == reid]
        return str(m.iloc[0][COL_COMPANY_NAME]) if not m.empty else reid
    except Exception:
        return reid


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

st.title("Regumetrica")
st.subheader("Ny benchmarking-modell")
st.caption(
    "Hur påverkas företaget av enbart Ei:s föreslagna nya benchmarking-modell "
    "(TOTEX-baserad DEA), allt annat lika? Fristående analys, skild från intäktsramen."
)

user_reid = get_user_reid()
if user_reid is None:
    st.warning("Välj ett företag i sidofältet för att fortsätta.")
    st.stop()

st.markdown(f"**Företag:** {_company_name(user_reid)} ({user_reid})")

cfg = render_config_panel()

if st.button("Kör analys", type="primary"):
    st.session_state["nb_signature"] = _signature(cfg)
    st.session_state["nb_cfg"] = cfg

sig = st.session_state.get("nb_signature")
if sig is None:
    st.info("Ställ in parametrarna ovan och klicka **Kör analys**.")
    st.stop()

# Re-run is instant when the signature is unchanged (cache hit).
result = _run_cached(sig, st.session_state["nb_cfg"])

# Staleness hint if the panel was changed after the last run.
if _signature(cfg) != sig:
    st.warning("Konfigurationen har ändrats sedan senaste körningen — klicka **Kör analys** igen för att uppdatera.")

st.divider()
render_company_view(result, user_reid, st.session_state["nb_cfg"])

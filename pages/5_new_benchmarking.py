"""
Page 5 — New benchmarking model (isolated add-on).

Standalone analysis of Ei's proposed new benchmarking model. The main model runs
immediately on load (no run button); an optional "Experiment" panel lets the user
fine-tune it, in which case the visualisations update and a secondary indicator shows
how far the tweak moved the efficiency requirement versus the main model.

Decoupled from the case/revenue-frame pipeline: calls run_new_benchmarking() directly
with its own config and does not produce a CaseDefinition.
"""

from __future__ import annotations

import streamlit as st

from frontend.utils.state_manager import init_session_state, get_user_reid
from frontend.modules.addons.new_benchmarking_spec import render_config_panel
from frontend.results.new_benchmarking_output import render_company_view
from calculations.new_benchmarking import run_new_benchmarking, NewBenchmarkingConfig
from calculations.new_benchmarking.model import NewBenchmarkingResult
from data_loaders.new_benchmarking_data import load_precomputed_main
from config.column_names import (
    COL_REID, COL_EFF_REQ_ANNUAL, COL_COMPANY_NAME, COL_COMPANY_NAME_SHORT,
)
from config.formatting import format_pp

init_session_state()


# ---------------------------------------------------------------------------
# Cached run — keyed on a config signature; baseline data is loaded internally
# (and itself cached). The cfg is passed underscore-prefixed so Streamlit does not
# try to hash it.
# ---------------------------------------------------------------------------

def _signature(cfg: NewBenchmarkingConfig) -> tuple:
    return cfg.signature()


@st.cache_data(show_spinner="Running the new benchmarking model for all 148 companies…")
def _run_cached(signature: tuple, _cfg: NewBenchmarkingConfig) -> NewBenchmarkingResult:
    return run_new_benchmarking(_cfg)


@st.cache_data(ttl=3600)
def _company_name(reid: str) -> str:
    try:
        from data_loaders.baseline_data import load_baseline_data
        df = load_baseline_data().df_all_companies
        m = df[df[COL_REID] == reid]
        return str(m.iloc[0][COL_COMPANY_NAME]) if not m.empty else reid
    except Exception:
        return reid


@st.cache_data(ttl=3600)
def _company_short(reid: str) -> str:
    """Curated short name for tight chart markers; falls back to the REId."""
    try:
        from data_loaders.baseline_data import load_baseline_data
        df = load_baseline_data().df_all_companies
        m = df[df[COL_REID] == reid]
        return str(m.iloc[0][COL_COMPANY_NAME_SHORT]) if not m.empty else reid
    except Exception:
        return reid


def _user_eff_req(result: NewBenchmarkingResult, reid: str):
    """User company's annual efficiency requirement under the new model, or None."""
    df = result.dea_new
    m = df[df[COL_REID] == reid]
    if m.empty or COL_EFF_REQ_ANNUAL not in df.columns:
        return None
    v = m.iloc[0][COL_EFF_REQ_ANNUAL]
    return None if v is None else float(v)


def _render_model_diff() -> None:
    """Short, factual summary of what the new model changes vs. the current one.

    Always shown at the top of the page. Placeholder — the final description is
    authored by the project owner.
    """
    st.markdown("**What this model changes vs. the current one**")
    st.caption("_Placeholder — a short, factual description of the model changes goes here._")


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

st.title("Regumetrica")
st.subheader("New benchmarking model")
st.caption(
    "How would the company be affected by Ei's proposed new benchmarking model "
    "(TOTEX-based DEA) alone, all else equal? A standalone analysis, separate from the revenue frame."
)

user_reid = get_user_reid()
if user_reid is None:
    st.warning("Select a company in the sidebar to continue.")
    st.stop()

st.markdown(f"**Company:** {_company_name(user_reid)} ({user_reid})")

# Model-diff (top).
_render_model_diff()

# Reserve the results area; it is filled below, after the experiment panel is evaluated,
# so the controls execute last but still display beneath the results.
results_area = st.container()

# Experiment panel (bottom): fine-tuning of the main model.
with st.expander("Experiment — fine-tune the model", expanded=False):
    active_cfg = render_config_panel()
    indicator_area = st.container()

# Main model = reference reading; active model = main model unless the user tweaked it.
main_cfg = NewBenchmarkingConfig()
main_sig = _signature(main_cfg)
active_sig = _signature(active_cfg)

# The main spec is fixed, so prefer the committed pre-computed bundle (instant, survives
# redeploys); fall back to a live run only if it is missing or its signature has drifted.
main_result = load_precomputed_main() or _run_cached(main_sig, main_cfg)
active_result = main_result if active_sig == main_sig else _run_cached(active_sig, active_cfg)

# Secondary indicator: how far the tweak moved the requirement vs. the main model.
if active_sig != main_sig:
    a = _user_eff_req(active_result, user_reid)
    m = _user_eff_req(main_result, user_reid)
    if a is not None and m is not None:
        with indicator_area:
            st.caption(f"ⓘ Your tweak changed the requirement by {format_pp(a - m)} vs. the main model.")

# Render the results (active model vs. current) in their reserved spot above the panel.
with results_area:
    render_company_view(active_result, user_reid, active_result.config, _company_short(user_reid))

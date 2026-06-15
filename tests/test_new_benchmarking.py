"""
tests/test_new_benchmarking.py

Tests for the new benchmarking model add-on (new_benchmarking_model):
- opex_components: loss valuation + non-controllable selection (synthetic, fast)
- capex_environment: förläggningsmiljö correction only lowers capital cost
- model: end-to-end run, schema, and parameter propagation

The full run is expensive (KENT + two DEA passes on 148 companies); it is computed
once per session via the `nb_result` fixture.
"""

import numpy as np
import pandas as pd
import pytest

from config.column_names import (
    COL_REID, COL_LOSS_VALUED, COL_NONCTRL_SELECTED, COL_TOTEX_NEW, COL_OPEX_NEW,
    COL_CAPITAL_COST_ENV_ADJ, COL_CABLE_LENGTH_KM, COL_CAPITAL_COST_2024,
    COL_EFF_REQ_NEW, COL_EFF_REQ_CURRENT, COL_EFF_REQ_DELTA,
)
from new_benchmarking_model import run_new_benchmarking, NewBenchmarkingConfig
from new_benchmarking_model.totex.opex_components import (
    compute_loss_valued, compute_non_controllable_selected,
)
from calculations.efficiency.efficiency_requirement import get_max_eff_req
from new_benchmarking_model.efficiency.efficiency_requirement_two_sided import (
    two_sided_requirement_from_gap,
)


# ---------------------------------------------------------------------------
# opex_components — synthetic, fast
# ---------------------------------------------------------------------------

def _incentive_stub():
    rows = []
    for yr in (2024, 2025, 2026, 2027):
        rows.append({"REId": "REL00001", "year": yr, "nf_obs": 0.04, "e_in": 1_000_000.0})
        rows.append({"REId": "REL00002", "year": yr, "nf_obs": 0.00, "e_in": 0.0})
    return pd.DataFrame(rows)


def test_loss_valued_formula_and_units():
    k_nf = {2024: 700.0, 2025: 700.0, 2026: 700.0, 2027: 700.0}
    out = compute_loss_valued(_incentive_stub(), k_nf)
    # 0.04 * 700 * 1_000_000 / 1000 = 28_000 tkr, constant across years → mean 28_000
    val = out.loc[out[COL_REID] == "REL00001", COL_LOSS_VALUED].iloc[0]
    assert val == pytest.approx(28_000.0)
    assert out.loc[out[COL_REID] == "REL00002", COL_LOSS_VALUED].iloc[0] == pytest.approx(0.0)


def test_loss_valued_scales_with_k_nf():
    base = compute_loss_valued(_incentive_stub(), {y: 700.0 for y in (2024, 2025, 2026, 2027)})
    dbl = compute_loss_valued(_incentive_stub(), {y: 1400.0 for y in (2024, 2025, 2026, 2027)})
    b = base.loc[base[COL_REID] == "REL00001", COL_LOSS_VALUED].iloc[0]
    d = dbl.loc[dbl[COL_REID] == "REL00001", COL_LOSS_VALUED].iloc[0]
    assert d == pytest.approx(2 * b)


def test_non_controllable_selection_excludes_fees_and_losses():
    detail = pd.DataFrame([
        {"REId": "REL00001", "kent_category": "grid_subscription", "year": 2024, "amount": -100.0},
        {"REId": "REL00001", "kent_category": "regulatory_fees", "year": 2024, "amount": -999.0},
        {"REId": "REL00001", "kent_category": "network_loss_purchased", "year": 2024, "amount": -50.0},
        {"REId": "REL00001", "kent_category": "grid_connection", "year": 2024, "amount": -20.0},
    ])
    out = compute_non_controllable_selected(
        detail, ("grid_subscription", "grid_connection", "feed_in_compensation", "capacity_reserve")
    )
    # only grid_subscription + grid_connection, negated, single year → 120
    assert out.loc[out[COL_REID] == "REL00001", COL_NONCTRL_SELECTED].iloc[0] == pytest.approx(120.0)


# ---------------------------------------------------------------------------
# Full run fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def nb_result(baseline_data):
    return run_new_benchmarking(NewBenchmarkingConfig(), baseline_data=baseline_data)


@pytest.fixture(scope="session")
def unadjusted_capital_cost(baseline_data):
    """capital_cost_2024 from KENT on the *unmodified* capbase, for comparison."""
    from data_loaders.rab_data import load_capbase_a
    from calculations.capex.kent_calculations import run_kent_calculations_batch
    _, df_network, _ = run_kent_calculations_batch(
        load_capbase_a(), wacc=baseline_data.wacc, return_detailed=False
    )
    return pd.DataFrame({
        COL_REID: df_network["id_network"].apply(lambda x: f"REL{int(x):05d}"),
        "capital_cost_unadjusted": df_network["capital_cost_2024"].to_numpy(),
    })


# ---------------------------------------------------------------------------
# capex_environment
# ---------------------------------------------------------------------------

def test_env_capex_all_companies_positive(nb_result):
    cc = nb_result.env_capex.capital_cost
    assert len(cc) == 148
    assert (cc[COL_CAPITAL_COST_ENV_ADJ] > 0).all()


def test_env_correction_only_lowers_capital_cost(nb_result, unadjusted_capital_cost):
    merged = nb_result.env_capex.capital_cost.merge(unadjusted_capital_cost, on=COL_REID)
    adj = merged[COL_CAPITAL_COST_ENV_ADJ]
    base = merged["capital_cost_unadjusted"]
    # förläggningsmiljö correction never increases capital cost (per firm, small tol)
    assert (adj <= base * (1 + 1e-9) + 1e-6).all()
    # and it strictly lowers the sector total (city/tätort premiums removed)
    assert adj.sum() < base.sum()


def test_env_deductions_positive(nb_result):
    assert nb_result.env_capex.cable_adjustment.per_company["deduction"].sum() > 0
    assert nb_result.env_capex.station_adjustment.per_company["deduction"].sum() > 0


# ---------------------------------------------------------------------------
# model — schema, bounds, propagation
# ---------------------------------------------------------------------------

def test_comparison_schema_and_no_nan(nb_result):
    c = nb_result.comparison
    assert len(c) == 148
    for col in (COL_EFF_REQ_NEW, COL_EFF_REQ_CURRENT, COL_EFF_REQ_DELTA):
        assert c[col].notna().all()


def test_totex_components_present_and_consistent(nb_result):
    t = nb_result.totex
    assert len(t) == 148
    # totex_new = opex_new + capital_cost (default cfg includes capex)
    recomputed = t[COL_OPEX_NEW] + t[COL_CAPITAL_COST_ENV_ADJ]
    assert np.allclose(t[COL_TOTEX_NEW], recomputed)
    assert (t[COL_TOTEX_NEW] > 0).all()


def test_eff_req_within_bounds(nb_result):
    c = nb_result.comparison
    cfg = nb_result.config
    # New model: signed two-sided requirement, bounded by the gap cap — a deduction up to
    # +1.82 %/yr and (since the gap is clipped symmetrically) a reward floor at the negative
    # of that band. Rewards (negative values) are expected, not floored at +1%.
    bound_kwargs = dict(
        gap_cap=cfg.gap_cap, sharing=cfg.sharing,
        realization_time=cfg.realization_time, supervision_period=cfg.supervision_period,
    )
    lo = two_sided_requirement_from_gap(-cfg.gap_cap, **bound_kwargs)
    hi = two_sided_requirement_from_gap(cfg.gap_cap, **bound_kwargs)
    assert (c[COL_EFF_REQ_NEW] >= lo - 1e-9).all()
    assert (c[COL_EFF_REQ_NEW] <= hi + 1e-9).all()
    # The whole point of the change: at least some efficient firms cross into a reward.
    assert (c[COL_EFF_REQ_NEW] < 0).any()
    # Current model: read straight from EIs_DEA (Ei's published Effkrav_proc) → within [0, max].
    cur_hi = get_max_eff_req()
    assert (c[COL_EFF_REQ_CURRENT] >= -1e-9).all()
    assert (c[COL_EFF_REQ_CURRENT] <= cur_hi + 1e-9).all()


def test_model_change_has_effect(nb_result):
    # The new model should differ from the current model for at least some firms.
    assert (nb_result.comparison[COL_EFF_REQ_DELTA].abs() > 1e-6).any()


def test_cable_length_is_a_new_output(nb_result):
    # default config includes cable length among the DEA outputs used
    assert COL_CABLE_LENGTH_KM in nb_result.new_model_outputs
    assert COL_CABLE_LENGTH_KM in nb_result.new_model_inputs.columns
    assert (nb_result.new_model_inputs[COL_CABLE_LENGTH_KM] >= 0).all()


def test_k_nf_override_raises_totex(nb_result, baseline_data):
    """Doubling the common loss price raises loss valuation and hence TOTEX."""
    k_nf_dbl = {y: 2 * 753.44 for y in (2024, 2025, 2026, 2027)}
    hi = run_new_benchmarking(NewBenchmarkingConfig(k_nf=k_nf_dbl), baseline_data=baseline_data)
    # firms with losses see higher loss valuation and higher TOTEX
    b = nb_result.totex.set_index(COL_REID)
    h = hi.totex.set_index(COL_REID)
    has_loss = b[COL_LOSS_VALUED] > 0
    assert (h.loc[has_loss, COL_LOSS_VALUED] > b.loc[has_loss, COL_LOSS_VALUED]).all()
    assert (h.loc[has_loss, COL_TOTEX_NEW] > b.loc[has_loss, COL_TOTEX_NEW]).all()


def test_component_toggle_excludes_losses(baseline_data):
    """Turning losses off removes them from opex_new."""
    off = run_new_benchmarking(
        NewBenchmarkingConfig(include_losses=False), baseline_data=baseline_data
    )
    t = off.totex
    # loss column still computed for transparency, but not in opex_new
    expected_opex = t["controllable_cost_average"] + t[COL_NONCTRL_SELECTED]
    assert np.allclose(t[COL_OPEX_NEW], expected_opex)

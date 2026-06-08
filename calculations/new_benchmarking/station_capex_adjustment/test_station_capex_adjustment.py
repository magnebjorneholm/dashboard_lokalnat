"""
Correctness tests for the station capex adjustment.

Run:
    ./venv/Scripts/python.exe -m pytest calculations/new_benchmarking/station_capex_adjustment/test_station_capex_adjustment.py -v
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from calculations.new_benchmarking.station_capex_adjustment import (
    load_station_components,
    calibrate,
    apply_environment_adjustment,
    classify_env,
    C,
)


@pytest.fixture(scope="module")
def components():
    return load_station_components()


@pytest.fixture(scope="module")
def calib(components):
    return calibrate(components)


# ── data model ──────────────────────────────────────────────────────────────

def test_value_identity(components):
    """nuav_2022 == normvärde × count_comp on rows that carry a unit price."""
    priced = components[(components[C.COL_UNIT_PRICE] > 0) & (components[C.COL_VALUE] != 0)]
    pred = priced[C.COL_UNIT_PRICE] * priced[C.COL_COUNT]
    rel = ((priced[C.COL_VALUE] - pred) / priced[C.COL_VALUE]).abs()
    assert (rel < 0.01).mean() > 0.999


def test_classify_env():
    assert classify_env("City- och tätortstillägg nätstation") == C.TATORT
    assert classify_env("Nätstation 800 kVA, betong") == C.BASE
    assert classify_env("Tillägg extra linjefack, per fack.") == C.BASE
    assert classify_env("Tillägg inhyst nätstation") == C.BASE
    assert classify_env("Kopplingsstation") == C.BASE


def test_only_tatort_surcharge_is_environment(components):
    """The only TATORT rows are the City-/tätort surcharge; nothing else leaks in."""
    tat = components[components[C.COL_ENV] == C.TATORT]
    assert tat[C.COL_TECHSPEC].str.lower().str.contains("city- och").all()


# ── calibration ─────────────────────────────────────────────────────────────

def test_surcharge_unit_price_matches_official_list(components):
    """The tätort surcharge unit price must equal Ei's list value (126 861 SEK/st)."""
    tat = components[(components[C.COL_ENV] == C.TATORT) & (components[C.COL_UNIT_PRICE] > 0)]
    assert not tat.empty
    assert tat[C.COL_UNIT_PRICE].mode().iloc[0] == pytest.approx(126861, rel=1e-4)


def test_calibration_premium_positive(calib):
    cov = calib.coverage.iloc[0]
    assert 0 < cov["percent"] < 1
    assert cov["premium_value"] > 0
    assert calib.sek_per_station == pytest.approx(126861, rel=0.05)


# ── adjustment invariants ───────────────────────────────────────────────────

@pytest.mark.parametrize("method", list(C.METHODS))
def test_conservation(components, calib, method):
    res = apply_environment_adjustment(components, calib, method=method)
    comp = res.components
    value = comp[C.COL_VALUE]
    ded = comp[C.COL_DEDUCTION]
    adj = comp[C.COL_ADJ_VALUE]
    # magnitude of deduction never exceeds the component's own value (handles disposals)
    assert (ded.abs() <= value.abs() + 1e-6).all()
    # the correction shrinks magnitude and never flips sign
    assert (adj.abs() <= value.abs() + 1e-6).all()
    assert (value * adj >= -1e-6).all()


def test_itemized_zeroes_surcharge_and_keeps_base(components, calib):
    """itemized removes the surcharge rows in full and leaves base rows untouched."""
    res = apply_environment_adjustment(components, calib, method=C.METHOD_ITEMIZED)
    comp = res.components
    tat = comp[comp[C.COL_ENV] == C.TATORT]
    base = comp[comp[C.COL_ENV] == C.BASE]
    assert tat[C.COL_ADJ_VALUE].abs().max() == pytest.approx(0.0, abs=1e-6)
    assert base[C.COL_DEDUCTION].abs().max() == pytest.approx(0.0, abs=1e-6)


def test_methods_agree_at_sector_level(components, calib):
    """The schablon % should reproduce the itemized total sector-wide (it is calibrated to)."""
    totals = {}
    for method in C.METHODS:
        res = apply_environment_adjustment(components, calib, method=method)
        totals[method] = res.per_company[C.COL_DEDUCTION].sum()
    base = totals[C.METHOD_ITEMIZED]
    for method, t in totals.items():
        assert abs(t - base) / base < 0.01


def test_override_percent(components, calib):
    res = apply_environment_adjustment(
        components, calib, method=C.METHOD_PERCENT, override_percent={C.TATORT: 0.0}
    )
    assert res.components[C.COL_DEDUCTION].abs().max() == pytest.approx(0.0, abs=1e-6)


def test_reduction_factor_consistent(components, calib):
    res = apply_environment_adjustment(components, calib, method=C.METHOD_ITEMIZED)
    pc = res.per_company
    recomputed = pc[C.COL_ADJ_VALUE] / pc[C.COL_VALUE]
    assert np.allclose(pc[C.COL_REDUCTION_FACTOR], recomputed, atol=1e-9)

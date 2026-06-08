"""
Correctness tests for the environment capex adjustment.

Run:
    ./venv/Scripts/python.exe -m pytest calculations/new_benchmarking/environment_capex_adjustment/test_environment_capex_adjustment.py -v
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from calculations.new_benchmarking.environment_capex_adjustment import (
    load_jordkabel_components,
    calibrate,
    apply_environment_adjustment,
    classify_env,
    C,
)


@pytest.fixture(scope="module")
def components():
    return load_jordkabel_components()


@pytest.fixture(scope="module")
def calib(components):
    return calibrate(components)


# ── data model ──────────────────────────────────────────────────────────────

def test_value_identity(components):
    """nuav_2022 == normvärde × count_comp (the basis the whole module relies on)."""
    pred = components[C.COL_UNIT_PRICE] * components[C.COL_KM]
    rel = ((components[C.COL_VALUE] - pred) / components[C.COL_VALUE]).abs()
    assert (rel < 0.01).mean() > 0.999


def test_classify_env():
    assert classify_env("jordkabel city") == C.CITY
    assert classify_env("jordkabel landsbygd normal") == C.LB_NORMAL
    assert classify_env("jordkabel landsbygd svår") == C.LB_SVAR
    assert classify_env("jordkabel tätort") == C.TATORT
    assert classify_env("sjökabel") == C.OTHER


def test_reference_price_matches_official_list(components):
    """Landsbygd-normal price for PEX 3x1x95 mm², 12 kV must equal Ei's list (441 285)."""
    ref = components[
        (components[C.COL_ENV] == C.LB_NORMAL)
        & (components[C.COL_TECHSPEC].str.replace(" ", "") == "PEX3x1x95mm²".replace(" ", ""))
        & (components[C.COL_VOLT] == "12")
    ]
    assert not ref.empty
    assert ref[C.COL_UNIT_PRICE].mode().iloc[0] == pytest.approx(441285, rel=1e-4)


# ── calibration ─────────────────────────────────────────────────────────────

def test_premium_ordering(calib):
    """city > tätort > landsbygd svår > 0, both in SEK/km and percent."""
    s = calib.sek_per_km
    assert s[C.CITY] > s[C.TATORT] > s[C.LB_SVAR] > 0
    p = calib.percent
    assert p[C.CITY] > p[C.TATORT] > p[C.LB_SVAR] > 0


def test_coverage_complete(calib):
    cov = calib.coverage.set_index(C.COL_ENV)
    assert (cov["km_matched_share"] > 0.85).all()


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


@pytest.mark.parametrize("method", list(C.METHODS))
def test_reference_and_other_untouched(components, calib, method):
    res = apply_environment_adjustment(components, calib, method=method)
    untouched = res.components[res.components[C.COL_ENV].isin([C.LB_NORMAL, C.OTHER])]
    assert untouched[C.COL_DEDUCTION].abs().max() == pytest.approx(0.0, abs=1e-6)


def test_methods_agree_at_sector_level(components, calib):
    """Well-calibrated schablons should land within ~2% of exact per-type, sector-wide."""
    totals = {}
    for method in C.METHODS:
        res = apply_environment_adjustment(components, calib, method=method)
        totals[method] = res.per_company[C.COL_DEDUCTION].sum()
    base = totals[C.METHOD_PER_TYPE]
    for method, t in totals.items():
        assert abs(t - base) / base < 0.02


def test_override_percent(components, calib):
    res = apply_environment_adjustment(
        components, calib, method=C.METHOD_PERCENT, override_percent={C.CITY: 0.0}
    )
    city = res.components[res.components[C.COL_ENV] == C.CITY]
    assert city[C.COL_DEDUCTION].abs().max() == pytest.approx(0.0, abs=1e-6)


def test_reduction_factor_consistent(components, calib):
    res = apply_environment_adjustment(components, calib, method=C.METHOD_PER_TYPE)
    pc = res.per_company
    recomputed = pc[C.COL_ADJ_VALUE] / pc[C.COL_VALUE]
    assert np.allclose(pc[C.COL_REDUCTION_FACTOR], recomputed, atol=1e-9)

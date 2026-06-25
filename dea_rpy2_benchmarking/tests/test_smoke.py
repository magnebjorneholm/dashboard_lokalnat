"""Smoke tests for the rpy2 <-> Benchmarking bridge on mock data.

Run from the package root:
    cd dea_rpy2_benchmarking && uv run pytest tests/ -v

These tests are skipped (not failed) if R or the Benchmarking package is not
installed, so they don't break a CI run that lacks the R toolchain.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "src"))
sys.path.insert(0, str(_ROOT))


def _require_r():
    try:
        from dea_benchmarking import get_benchmarking

        get_benchmarking()
    except Exception as exc:  # R missing, Benchmarking missing, etc.
        pytest.skip(f"R/Benchmarking not available: {exc}")


def test_import_is_clean():
    """Importing the package must not raise."""
    import dea_benchmarking  # noqa: F401


def test_textbook_dea():
    """Known 5-firm VRS example: 4 efficient, firm_4 dominated at 0.5."""
    _require_r()
    from dea_benchmarking import dea
    from examples.mock_data import textbook_example

    X, Y, names = textbook_example()
    res = dea(X, Y, rts="vrs", orientation="in", dmu_names=names)

    assert res.n_dmu == 5
    assert res.eff.shape == (5,)
    np.testing.assert_allclose(res.eff[3], 0.5, atol=1e-6)  # firm_4
    assert int(res.efficient().sum()) == 4


def test_efficiency_bounds_input_oriented():
    """Input-oriented DEA scores must lie in (0, 1]."""
    _require_r()
    from dea_benchmarking import dea
    from examples.mock_data import random_dmus

    X, Y, names = random_dmus(n_dmu=12, seed=1)
    res = dea(X, Y, rts="crs", orientation="in", dmu_names=names)

    assert np.all(res.eff > 0)
    assert np.all(res.eff <= 1 + 1e-9)


def test_lambda_matrix_shape():
    """The peer (lambda) matrix is square: n_dmu x n_dmu."""
    _require_r()
    from dea_benchmarking import dea
    from examples.mock_data import random_dmus

    X, Y, _ = random_dmus(n_dmu=10, seed=3)
    res = dea(X, Y, rts="vrs")
    assert res.lambdas.shape == (10, 10)


def test_slack_computed_when_requested():
    """SLACK=True must populate result.slack with one value per DMU."""
    _require_r()
    from dea_benchmarking import dea
    from examples.mock_data import random_dmus

    X, Y, _ = random_dmus(n_dmu=8, seed=5)
    res = dea(X, Y, rts="crs", orientation="in", slack=True)
    assert res.slack is not None
    assert res.slack.shape == (8,)
    assert np.all(res.slack >= -1e-9)


def test_superefficiency_can_exceed_one():
    """Super-efficiency lets at least one efficient unit score above 1."""
    _require_r()
    from dea_benchmarking import dea, sdea
    from examples.mock_data import random_dmus

    X, Y, _ = random_dmus(n_dmu=15, seed=7)
    base = dea(X, Y, rts="crs", orientation="in")
    sres = sdea(X, Y, rts="crs", orientation="in")

    assert sres.eff.shape == base.eff.shape
    assert np.any(sres.eff[base.efficient()] > 1.0 + 1e-6)


def test_raw_package_access():
    """The full Benchmarking R API is reachable via package()."""
    _require_r()
    from dea_benchmarking import package

    bench = package()
    # dea and sdea (R's dotted names map to underscores) must be present.
    assert hasattr(bench, "dea")
    assert hasattr(bench, "sdea")


def test_input_validation():
    """Mismatched X/Y row counts and bad options raise cleanly."""
    _require_r()
    from dea_benchmarking import dea

    with pytest.raises(ValueError):
        dea(np.ones((3, 1)), np.ones((4, 1)))  # row mismatch
    with pytest.raises(ValueError):
        dea(np.ones((3, 1)), np.ones((3, 1)), rts="nope")  # bad rts

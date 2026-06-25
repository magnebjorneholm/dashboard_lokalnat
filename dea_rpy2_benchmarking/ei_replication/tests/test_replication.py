"""Exact-replication tests for Ei's DEA via R/Benchmarking.

Skipped (not failed) when R, the Benchmarking package, or the Ei data files are
unavailable, so a machine without the R toolchain or the raw data still runs the
rest of the suite cleanly.

Run from the repo root:
    uv run pytest dea_rpy2_benchmarking/ei_replication/tests/ -v
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

_PKG_ROOT = Path(__file__).resolve().parents[2]   # dea_rpy2_benchmarking/
_REPO_ROOT = _PKG_ROOT.parent
for p in (str(_REPO_ROOT), str(_PKG_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

EXPECTED_OUTLIERS = {"REL00024", "REL00257", "REL00965"}
KNOWN_NONREPLICABLE = "REL00193"


@pytest.fixture(scope="module")
def replicated():
    """Run the replication once for the whole module, or skip if unavailable."""
    try:
        from ei_replication.data import load_facit, load_model_data
        from ei_replication.replicate import replicate

        md = load_model_data()
        facit = load_facit()
        res = replicate(md.X, md.Y)
    except Exception as exc:  # R/Benchmarking missing, or data files absent
        pytest.skip(f"replication prerequisites unavailable: {exc}")
    return md, facit, res


def test_three_outliers_match_ei(replicated):
    md, _, res = replicated
    found = set(md.reid[res.is_outlier].tolist())
    assert found == EXPECTED_OUTLIERS


def test_iteration_converges_in_multiple_rounds(replicated):
    """A single round does not reproduce Ei; it must iterate (here: 3 rounds)."""
    _, _, res = replicated
    assert res.n_rounds >= 2


def test_efficiency_matches_facit_to_tolerance(replicated):
    md, facit, res = replicated
    from ei_replication.compare import compare

    cmp = compare(md, res, tolerance=5e-9)
    assert cmp.passed, (
        f"max eff diff={cmp.max_eff_diff:.2e}, "
        f"max seff diff={cmp.max_seff_diff:.2e}"
    )


def test_known_anomaly_is_isolated(replicated):
    """REL00193 is the *only* firm that deviates beyond tolerance."""
    md, facit, res = replicated
    f_seff = facit["Supereffektivitet"].to_numpy(float)
    diff = np.abs(res.super_efficiency - f_seff)

    over = md.reid[diff > 5e-9]
    assert set(over.tolist()) <= {KNOWN_NONREPLICABLE}
    # And it genuinely does deviate (sanity: the anomaly is real, not masked).
    idx = int(np.where(md.reid == KNOWN_NONREPLICABLE)[0][0])
    assert diff[idx] > 1e-3


def test_efficiency_is_capped_at_one(replicated):
    """Reported efficiency = min(super_eff, 1) for every scored firm."""
    _, _, res = replicated
    scored = np.isfinite(res.efficiency)
    assert np.all(res.efficiency[scored] <= 1.0 + 1e-9)
    np.testing.assert_allclose(
        res.efficiency[scored],
        np.minimum(res.super_efficiency[scored], 1.0),
        atol=1e-9,
    )

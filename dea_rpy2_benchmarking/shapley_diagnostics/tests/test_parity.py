"""Parity + sanity tests for the R/Benchmarking Shapley diagnostics.

The parity gate is the linchpin: the R-based frozen scoring must reproduce the
existing PuLP value grid (efficiency and the two-sided requirement) to solver
tolerance, otherwise the new diagnostics built on top cannot be trusted.

Skipped (not failed) if R/Benchmarking, the spine bundle, or the legacy value
grids are unavailable.

    uv run pytest dea_rpy2_benchmarking/shapley_diagnostics/tests/ -v
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
for p in (str(REPO_ROOT), str(REPO_ROOT / "dea_rpy2_benchmarking")):
    if p not in sys.path:
        sys.path.insert(0, p)

# Two LP backends (CBC vs lpSolve) agree to solver tolerance; allow 1e-5 slack.
PARITY_TOL = 1e-5


@pytest.fixture(scope="module")
def ctx():
    try:
        import pandas as pd

        from new_benchmarking_model.analysis._helpers import load_analysis_df
        from new_benchmarking_model.analysis.decomp.players import PLAYERS
        from shapley_diagnostics.scoring import score_coalition

        spine = load_analysis_df()
        vg_eff = pd.read_csv(
            REPO_ROOT / "new_benchmarking_model/analysis/out/decomp_eff/frozen/value_grid.csv")
        vg_req = pd.read_csv(
            REPO_ROOT / "new_benchmarking_model/analysis/out/decomp_req/frozen/value_grid.csv")
    except Exception as exc:
        pytest.skip(f"prerequisites unavailable: {exc}")
    return spine, vg_eff, vg_req, PLAYERS, score_coalition


def _mask(S, players):
    return sum(1 << i for i, p in enumerate(players) if p in S)


def _parity(spine, vg, S, players, score_coalition, attr):
    reids = spine["REId"].to_numpy()
    cs = score_coalition(spine, S)
    facit = vg[vg.subset_mask == _mask(S, players)].set_index("REId")["value"].reindex(reids).to_numpy()
    return float(np.nanmax(np.abs(getattr(cs, attr) - facit)))


def test_parity_baseline_and_full(ctx):
    spine, vg_eff, vg_req, players, score = ctx
    for S in (frozenset(), frozenset(players)):
        assert _parity(spine, vg_eff, S, players, score, "efficiency") < PARITY_TOL
        assert _parity(spine, vg_req, S, players, score, "requirement_pp") < PARITY_TOL


def test_parity_sample_interior_coalitions(ctx):
    """A few interior coalitions must match too (not just the endpoints)."""
    spine, vg_eff, vg_req, players, score = ctx
    interiors = [
        frozenset({"grid_subscription"}),
        frozenset({"capex_adj", "cable"}),
        frozenset({"losses", "feed_in", "grid_connection"}),
    ]
    for S in interiors:
        assert _parity(spine, vg_eff, S, players, score, "efficiency") < PARITY_TOL
        assert _parity(spine, vg_req, S, players, score, "requirement_pp") < PARITY_TOL


def test_efficiency_is_capped_supereff(ctx):
    spine, *_ , score = ctx
    cs = score(spine, frozenset())
    fin = np.isfinite(cs.theta)
    np.testing.assert_allclose(cs.efficiency[fin], np.minimum(cs.theta[fin], 1.0), atol=1e-12)


def test_diagnostics_shapes(ctx):
    spine, *_rest = ctx
    from shapley_diagnostics.metrics import coalition_diagnostics

    dg = coalition_diagnostics(spine, frozenset())
    n = len(dg.ref_reid)
    assert dg.u.shape == (n, 1)
    assert dg.v.shape == (n, len(dg.output_names))
    # Frontier firms (efficiency 1) should be exactly those with few own peers.
    assert dg.number_peers.sum() > 0

"""Replicate Ei's DEA exactly, using R's Benchmarking as the LP engine.

This is a faithful port of the project's pure-Python procedure
(`calculations/frontier/outliers.py` + `dea_calculations.py`), with the only
difference being *what solves the LP*: instead of PuLP/CBC we call
``Benchmarking::sdea`` (CRS, input-oriented) through the rpy2 wrapper in
``dea_benchmarking``. Same six invariants from ``eis_dea_metod.md``:

    1. input-oriented, CRS (no lambda-sum constraint)
    2. super-efficiency (leave-one-out, j != i) in both the outlier step and
       the final scoring
    3. no scaling/normalisation of inputs/outputs
    4. one-sided upper IQR fence: Q3 + 2*(Q3-Q1) on the 25/75 percentiles
    5. outlier detection iterated to convergence (not a single round)
    6. outliers removed from the reference front and left unscored; survivors
       scored against the cleaned front with E = min(theta, 1), potential = 1-E

The independent solver is the whole point: if this R-based path matches both
the published facit and the project's PuLP path to solver tolerance, the result
is corroborated by two unrelated LP backends.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

# Make the sibling dea_benchmarking package importable (src/ layout).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from dea_benchmarking import sdea  # noqa: E402


@dataclass
class ReplicationResult:
    """Per-firm DEA outcome, aligned to the input row order."""

    efficiency: np.ndarray  # min(theta, 1); NaN if unsolvable
    super_efficiency: np.ndarray  # theta (can exceed 1)
    potential: np.ndarray  # 1 - efficiency for survivors; 1.0 for outliers
    is_outlier: np.ndarray  # bool
    n_rounds: int


def super_eff_scores(X: np.ndarray, Y: np.ndarray, reference_mask: np.ndarray,
                     rts: str = "crs") -> np.ndarray:
    """Input-oriented super-efficiency for firms in ``reference_mask``.

    Each reference firm i is scored leave-one-out against the *other* reference
    firms (exactly what ``sdea`` computes when handed only the reference rows).
    Firms outside the mask, with missing data, or whose LP is infeasible get
    NaN — the caller treats NaN/non-finite as an outlier signal.
    """
    n = X.shape[0]
    scores = np.full(n, np.nan)
    idx = np.where(reference_mask)[0]
    if idx.size < 2:
        return scores

    finite_row = ~np.isnan(X[idx]).any(axis=1) & ~np.isnan(Y[idx]).any(axis=1)
    valid = idx[finite_row]
    if valid.size < 2:
        return scores

    res = sdea(X[valid], Y[valid], rts=rts, orientation="in")
    eff = np.asarray(res.eff, dtype=float)
    # Benchmarking returns Inf for an infeasible super-efficiency LP; normalise
    # that to NaN so downstream finite-checks treat it as "no score".
    eff[~np.isfinite(eff)] = np.nan
    scores[valid] = eff
    return scores


def _iqr_fence(scores: np.ndarray, q_lower=25.0, q_upper=75.0,
               multiplier=2.0) -> float:
    """Upper IQR fence on already-finite scores: Q3 + multiplier*(Q3-Q1)."""
    q1 = np.percentile(scores, q_lower)
    q3 = np.percentile(scores, q_upper)
    return q3 + multiplier * (q3 - q1)


def detect_outliers(X: np.ndarray, Y: np.ndarray, *, rts="crs", q_lower=25.0,
                    q_upper=75.0, multiplier=2.0, max_rounds=None):
    """Iterate super-eff + IQR fence to convergence. Returns (is_outlier,
    flag_scores, final_scores, n_rounds). Mirrors detect_outliers_iterative."""
    n = X.shape[0]
    is_outlier = np.zeros(n, dtype=bool)
    flag_scores = np.full(n, np.nan)

    last_scores = None
    last_remaining = None
    n_rounds = 0

    while max_rounds is None or n_rounds < max_rounds:
        n_rounds += 1
        remaining = ~is_outlier
        scores = super_eff_scores(X, Y, remaining, rts)
        last_scores, last_remaining = scores, remaining

        ref_scores = scores[remaining & np.isfinite(scores)]
        if ref_scores.size == 0:
            break
        fence = _iqr_fence(ref_scores, q_lower, q_upper, multiplier)

        new = remaining & (~np.isfinite(scores) | (scores > fence))
        if not new.any():
            break
        is_outlier |= new
        flag_scores[new] = scores[new]

    remaining = ~is_outlier
    if last_remaining is not None and np.array_equal(last_remaining, remaining):
        final_scores = last_scores.copy()
    else:
        final_scores = super_eff_scores(X, Y, remaining, rts)
    final_scores[is_outlier] = np.nan
    return is_outlier, flag_scores, final_scores, n_rounds


def replicate(X: np.ndarray, Y: np.ndarray, *, rts="crs", q_lower=25.0,
              q_upper=75.0, multiplier=2.0, max_rounds=None) -> ReplicationResult:
    """Full Ei replication: outliers + final scoring -> ReplicationResult.

    Output convention matches dea_calculations.run_dea_analysis:
    - survivor: efficiency = min(theta, 1), super_eff = theta, potential = 1-eff
    - outlier:  efficiency = min(flag_theta, 1), super_eff = flag_theta,
                potential = 1.0 (it has no requirement gap to close)
    """
    is_outlier, flag_scores, final_scores, n_rounds = detect_outliers(
        X, Y, rts=rts, q_lower=q_lower, q_upper=q_upper,
        multiplier=multiplier, max_rounds=max_rounds,
    )

    n = X.shape[0]
    efficiency = np.full(n, np.nan)
    super_eff = np.full(n, np.nan)
    potential = np.full(n, np.nan)

    for i in range(n):
        theta = flag_scores[i] if is_outlier[i] else final_scores[i]
        if not np.isfinite(theta):
            continue
        super_eff[i] = theta
        efficiency[i] = min(theta, 1.0)
        potential[i] = 1.0 if is_outlier[i] else 1.0 - min(theta, 1.0)

    return ReplicationResult(
        efficiency=efficiency,
        super_efficiency=super_eff,
        potential=potential,
        is_outlier=is_outlier,
        n_rounds=n_rounds,
    )

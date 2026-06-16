"""
calculations/frontier/outliers.py

Shared outlier detection for DEA: super-efficiency + IQR, iterated to
convergence. Pure logic, no UI imports.

Super-efficiency is used here *only* to identify outliers (leave-one-out scores
that exceed an IQR fence). The reported efficiency of the surviving firms comes
from a final super-efficiency solve against the cleaned reference set.

This module is the single source of truth for the outlier step. Both the
revenue-cap pipeline (calculations/frontier/dea_calculations.py) and the
standalone DEA-diagnostics tool import from here, so the two never drift.

Removing the diagnostics tool leaves this module untouched: the dependency
points tool -> frontier, never the reverse.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pulp


@dataclass
class OutlierResult:
    """Outcome of iterative outlier detection.

    is_outlier    (n,) bool   firms flagged as outliers
    flag_scores   (n,) float  super-eff score of each outlier at the round it was
                              flagged; NaN for non-outliers (and for outliers whose
                              LP failed / had missing data)
    final_scores  (n,) float  super-eff score of each surviving firm against the
                              final cleaned reference set; NaN for outliers
    n_rounds      int         number of identification rounds actually run
    """

    is_outlier: np.ndarray
    flag_scores: np.ndarray
    final_scores: np.ndarray
    n_rounds: int


def _iqr_threshold(
    scores: np.ndarray, q_lower: float, q_upper: float, multiplier: float
) -> float:
    """Upper IQR fence: q_upper + multiplier * (q_upper - q_lower).

    `scores` must already be filtered to finite reference-set values.
    """
    q_low = np.percentile(scores, q_lower)
    q_high = np.percentile(scores, q_upper)
    return q_high + multiplier * (q_high - q_low)


def super_eff_scores(
    inputs: np.ndarray,
    outputs: np.ndarray,
    rts: str,
    reference_mask: np.ndarray,
) -> np.ndarray:
    """Input-oriented super-efficiency scores, reference = `reference_mask`.

    For each firm i in the reference set, solve the leave-one-out LP

        min theta
        s.t.  sum_{j in ref, j != i} lam_j * y_jk >= y_ik     for each output k
              sum_{j in ref, j != i} lam_j * x_jl <= theta*x_il for each input l
              sum_{j in ref, j != i} lam_j = 1                  (VRS only)
              lam_j, theta >= 0

    Returns an (n,) array; entries for firms outside `reference_mask`, with
    missing data, or whose LP does not solve are NaN. No column scaling is
    applied (kept identical to Ei's reference implementation).
    """
    n = len(inputs)
    n_out = outputs.shape[1]
    n_in = inputs.shape[1]
    scores = np.full(n, np.nan)
    ref_idx = np.where(reference_mask)[0]

    for i in ref_idx:
        if np.any(np.isnan(inputs[i])) or np.any(np.isnan(outputs[i])):
            continue  # leave NaN -> caller treats as outlier

        model = pulp.LpProblem(name=f"DEA_SUPER_{i}", sense=pulp.LpMinimize)
        theta = pulp.LpVariable("theta", lowBound=0)
        lam = {j: pulp.LpVariable(f"lambda_{j}", lowBound=0)
               for j in ref_idx if j != i}

        model += theta

        for k in range(n_out):
            model += pulp.lpSum(lam[j] * outputs[j][k] for j in lam) >= outputs[i][k]
        for l in range(n_in):
            model += pulp.lpSum(lam[j] * inputs[j][l] for j in lam) <= theta * inputs[i][l]
        if rts == "vrs":
            model += pulp.lpSum(lam[j] for j in lam) == 1

        try:
            model.solve(pulp.PULP_CBC_CMD(msg=0))
            score = pulp.value(theta)
            if score is not None and not np.isnan(score):
                scores[i] = score
        except Exception:
            pass  # leave NaN

    return scores


def detect_outliers_iterative(
    inputs: np.ndarray,
    outputs: np.ndarray,
    rts: str = "crs",
    *,
    q_lower: float = 25.0,
    q_upper: float = 75.0,
    multiplier: float = 2.0,
    max_rounds: int | None = None,
    forced_outliers: np.ndarray | None = None,
) -> OutlierResult:
    """Identify outliers by iterating the super-eff + IQR fence to convergence.

    Each round: solve super-efficiency on the firms still in the reference set,
    compute the IQR fence on those scores, and flag any firm above the fence (or
    with missing/failed data). Flagged firms are removed from the reference set
    permanently and keep the score they had when flagged. The loop stops when a
    round flags nothing new, or after `max_rounds` rounds.

    `max_rounds`:
        None -> iterate until no new outliers appear (the general behaviour).
        1    -> a single identification round, i.e. Ei's reference method
                (flag once on the full-set scores, then one cleaned re-solve).

    A final super-efficiency solve on the surviving firms always produces
    `final_scores`, regardless of how the loop terminated.

    `forced_outliers`: optional (n,) bool mask of firms removed from the reference
        set up front (e.g. firms Ei deems structurally unsuitable for DEA). They are
        excluded from the frontier and the IQR fence that score everyone else, and
        are themselves left unscored (NaN efficiency) rather than assigned a score —
        scoring them against the full set would only reflect the very anomalies that
        got them excluded. This mirrors how Ei reports them (no published efficiency).
    """
    n = len(inputs)
    is_outlier = (
        np.zeros(n, dtype=bool) if forced_outliers is None
        else np.asarray(forced_outliers, dtype=bool).copy()
    )
    flag_scores = np.full(n, np.nan)  # forced firms keep NaN here -> reported unscored

    last_scores: np.ndarray | None = None
    last_remaining: np.ndarray | None = None
    n_rounds = 0

    while max_rounds is None or n_rounds < max_rounds:
        n_rounds += 1
        remaining = ~is_outlier
        scores = super_eff_scores(inputs, outputs, rts, remaining)
        last_scores, last_remaining = scores, remaining

        ref_scores = scores[remaining & np.isfinite(scores)]
        if ref_scores.size == 0:
            break
        threshold = _iqr_threshold(ref_scores, q_lower, q_upper, multiplier)

        new = remaining & (~np.isfinite(scores) | (scores > threshold))
        if not new.any():
            break
        is_outlier |= new
        flag_scores[new] = scores[new]

    # Final scoring solve on the surviving reference set. Reuse the last solve
    # when its reference set already matches (convergence case); otherwise the
    # loop was capped by max_rounds with fresh flags, so re-solve.
    remaining = ~is_outlier
    if last_remaining is not None and np.array_equal(last_remaining, remaining):
        final_scores = last_scores.copy()
    else:
        final_scores = super_eff_scores(inputs, outputs, rts, remaining)
    final_scores[is_outlier] = np.nan

    return OutlierResult(
        is_outlier=is_outlier,
        flag_scores=flag_scores,
        final_scores=final_scores,
        n_rounds=n_rounds,
    )

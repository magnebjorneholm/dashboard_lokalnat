"""
efficiency_requirement_two_sided.py — Ei's proposed two-sided efficiency mechanic.

Converts a cross-section of DEA efficiency scores into a *signed* annual efficiency
requirement. This is the new-benchmarking add-on's replacement for the current
front-reference / deduction-only method — and it lives here, inside the isolated add-on
package, precisely so the revenue-cap pipeline keeps using the legacy method untouched
(calculations/efficiency/efficiency_requirement.py models the *current* regulation, which
is correct and must not change).

The change vs. the legacy method
(new_benchmarking_model/docs/tolkning-overgang-effektiviseringsincitament.md §3, §7):

    Legacy:  potential = 1 − E_i        gap to the frontier (≥ 0) → deduction only
    New:     gap       = E75 − E_i      gap to the third quartile → signed

E75 is the 75th percentile of the efficiency distribution, computed *excluding outliers*.
A firm below E75 is less efficient than the threshold and gets a deduction (positive
requirement); a firm above E75 gets an addition (negative requirement = reward); a firm
exactly at E75 gets full cost coverage (zero).

Locked specification (decided with the project owner):

    E_i    = min(θ, 1)                                 # capped DEA efficiency (COL_DEA_EFFICIENCY)
    E75    = percentile(E_i over non-outliers, 75)
    gap    = E75 − E_i
    gap̃   = clip(gap, −gap_cap, +gap_cap)             # gap_cap = 0.30; symmetric, but only
                                                       #   the deduction side actually binds
    period = gap̃ × sharing × (supervision_period / realization_time)
    annual = (1 + period) ** (1 / supervision_period) − 1   # >0 deduction, <0 reward

There is no floor and no fixed outlier requirement: "full coverage" at the third quartile
replaces the legacy floor, and outliers (capped to E_i = 1.0 like every other frontier
firm) receive the same reward as the rest of the frontier — they are only excluded from
the percentile that sets the threshold.

With gap_cap = 0.30 and the locked defaults, the maximum deduction is +1.82 %/yr — the
same ceiling as the legacy method — so the two stay numerically anchored.

All requirements are signed decimals (e.g. 0.0182 = +1.82 %/yr deduction,
−0.0047 = −0.47 %/yr reward).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from config.column_names import (
    COL_DEA_EFFICIENCY,
    COL_IS_OUTLIER,
    COL_EFF_REQ_ANNUAL,
    COL_DEA_REFERENCE,
)


# Locked defaults (see module docstring). sharing × supervision/realization = 0.50 × 4/8 = 0.25.
DEFAULT_TWO_SIDED_PARAMS = {
    "reference_percentile": 75.0,   # third quartile
    "gap_cap": 0.30,                # symmetric cap on the signed gap (matches legacy 0.30)
    "sharing": 0.50,                # customer sharing
    "realization_time": 8,          # years to realise the full gap
    "supervision_period": 4,        # years in the supervision period
}


def reference_efficiency(
    efficiency: pd.Series,
    is_outlier: pd.Series,
    reference_percentile: float = 75.0,
) -> float:
    """E75 — the reference efficiency (third quartile), computed *excluding outliers*.

    Outliers are dropped from the cross-section that sets the threshold (they sit above it
    by construction and would only bias it upward); NaN scores are ignored. Returns NaN if
    no non-outlier scores remain.
    """
    mask = ~is_outlier.astype(bool)
    scores = pd.to_numeric(efficiency[mask], errors="coerce").dropna()
    if scores.empty:
        return float("nan")
    return float(np.percentile(scores, reference_percentile))


def two_sided_requirement_from_gap(
    signed_gap: float,
    gap_cap: float = 0.30,
    sharing: float = 0.50,
    realization_time: int = 8,
    supervision_period: int = 4,
) -> float:
    """Annual signed requirement from one firm's signed gap (E75 − E_i).

    Positive gap (firm below the threshold) → positive requirement (deduction); negative
    gap (firm above) → negative requirement (reward); zero gap → zero. NaN in → NaN out.
    """
    if pd.isna(signed_gap):
        return float("nan")
    gap_clipped = float(np.clip(signed_gap, -gap_cap, gap_cap))
    period = gap_clipped * sharing * (supervision_period / realization_time)
    return (1 + period) ** (1 / supervision_period) - 1


def calculate_two_sided_requirement(
    df: pd.DataFrame,
    efficiency_col: str = COL_DEA_EFFICIENCY,
    outlier_col: str = COL_IS_OUTLIER,
    reference_percentile: float = 75.0,
    gap_cap: float = 0.30,
    sharing: float = 0.50,
    realization_time: int = 8,
    supervision_period: int = 4,
) -> pd.DataFrame:
    """Add the two-sided annual efficiency requirement for every firm in the cross-section.

    Unlike the legacy per-row method, this is inherently cross-sectional: the reference E75
    is read from the whole (non-outlier) distribution before any firm's requirement can be
    set.

    Args:
        df: cross-section, one row per firm, holding efficiency_col and outlier_col.
        efficiency_col: capped DEA efficiency E_i = min(θ, 1).
        outlier_col: bool flag; outliers are excluded from the percentile but still scored.
        reference_percentile / gap_cap / sharing / realization_time / supervision_period:
            see module docstring (locked defaults).

    Returns:
        A copy of df with two new columns:
          - COL_DEA_REFERENCE: E75, the reference efficiency (constant across rows).
          - COL_EFF_REQ_ANNUAL: signed annual requirement (>0 deduction, <0 reward).
    """
    if efficiency_col not in df.columns:
        raise ValueError(f"Column '{efficiency_col}' missing from DataFrame")
    if outlier_col not in df.columns:
        raise ValueError(f"Column '{outlier_col}' missing from DataFrame")

    result = df.copy()

    e75 = reference_efficiency(
        result[efficiency_col], result[outlier_col], reference_percentile
    )
    result[COL_DEA_REFERENCE] = e75

    eff = pd.to_numeric(result[efficiency_col], errors="coerce")
    result[COL_EFF_REQ_ANNUAL] = (e75 - eff).map(
        lambda gap: two_sided_requirement_from_gap(
            gap,
            gap_cap=gap_cap,
            sharing=sharing,
            realization_time=realization_time,
            supervision_period=supervision_period,
        )
    )
    return result

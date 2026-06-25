"""R/Benchmarking scoring of one DEA coalition in *frozen* outlier mode.

This is the new scoring layer for the Shapley diagnostics. It replaces the PuLP
solve in `new_benchmarking_model/analysis/decomp/engine.py` (`_score`,
`_frozen_efficiency`) with R's Benchmarking, while reproducing the SAME frozen
semantics so the efficiency/requirement numbers are bit-comparable (the parity
gate). On top of the efficiency it also yields the extra diagnostics Benchmarking
gives natively (super-efficiency, peers, dual multipliers) — see metrics.py.

Frozen semantics (mirrors engine.py):
    R           = reference set = firms NOT in the frozen set (e.g. 144 firms)
    scored      = firms NOT Ei-excluded (e.g. 145 firms) = R plus any frozen-but-
                  scored firm (REL03016)
    - reference firms: leave-one-out super-efficiency within R   (R's sdea)
    - a frozen-but-scored firm i (i not in R): efficiency of i against the fixed
      reference R                                                 (R's dea + XREF/YREF)
    - Ei-excluded firms: left unscored (NaN)
    eff_i = min(theta_i, 1);  E75 = pct75 of eff over non-frozen firms.

The frontier payable post is opexp_dea; the requirement base is on the kr side
and untouched (same as the legacy engine).
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import FrozenSet

import numpy as np
import pandas as pd

# Sibling dea_benchmarking package (src/ layout) for the rpy2 bridge.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from rpy2.robjects.conversion import get_conversion  # noqa: E402

from dea_benchmarking.r_session import get_benchmarking, np_converter  # noqa: E402

from config.column_names import (  # noqa: E402
    COL_REID, COL_DEA_EFFICIENCY, COL_DEA_SUPER_EFF, COL_DEA_POTENTIAL,
    COL_IS_OUTLIER, COL_EFF_REQ_ANNUAL,
)
from new_benchmarking_model.analysis.decomp.players import (  # noqa: E402
    subset_input, subset_outputs,
)
from new_benchmarking_model.efficiency.efficiency_requirement_two_sided import (  # noqa: E402
    calculate_two_sided_requirement, reference_efficiency,
)
from new_benchmarking_model.config import NewBenchmarkingConfig  # noqa: E402

# The full-model frozen outlier set (what 'frozen' mode freezes; from the
# analysis manifest). The first three are also Ei's structural exclusions.
FROZEN_REIDS = ("REL00024", "REL00257", "REL00965", "REL03016")
EI_EXCLUDED_REIDS = ("REL00024", "REL00257", "REL00965")


def _np2r(arr: np.ndarray):
    with np_converter.context():
        return get_conversion().py2rpy(np.ascontiguousarray(arr, dtype=float))


def _r2np(robj) -> np.ndarray:
    with np_converter.context():
        out = np.asarray(get_conversion().rpy2py(robj))
    return out


@dataclass
class CoalitionScore:
    """Per-firm scoring of one coalition (aligned to the spine row order)."""

    reid: np.ndarray
    theta: np.ndarray        # super-efficiency (uncapped); NaN if unscored
    efficiency: np.ndarray   # min(theta, 1); NaN if unscored
    is_outlier: np.ndarray   # frozen mask
    e75: float
    requirement_pp: np.ndarray  # signed two-sided requirement, percentage points


def _theta_frozen(X: np.ndarray, Y: np.ndarray, ref_mask: np.ndarray,
                  scored_mask: np.ndarray, rts: str) -> np.ndarray:
    """Super-efficiency theta under frozen semantics (see module docstring)."""
    bench = get_benchmarking()
    n = X.shape[0]
    theta = np.full(n, np.nan)

    ref_idx = np.where(ref_mask)[0]
    # Reference firms: leave-one-out super-efficiency within R (sdea on R rows).
    far = bench.sdea(_np2r(X[ref_idx]), _np2r(Y[ref_idx]), RTS=rts, ORIENTATION="in")
    eff_ref = _r2np(far.rx2("eff")).ravel()
    eff_ref[~np.isfinite(eff_ref)] = np.nan
    theta[ref_idx] = eff_ref

    # Frozen-but-scored firms (scored, not in R): efficiency against fixed R.
    extra_idx = np.where(scored_mask & ~ref_mask)[0]
    if extra_idx.size:
        Xref = _np2r(X[ref_idx])
        Yref = _np2r(Y[ref_idx])
        far_e = bench.dea(_np2r(X[extra_idx]), _np2r(Y[extra_idx]),
                          RTS=rts, ORIENTATION="in", XREF=Xref, YREF=Yref)
        eff_e = _r2np(far_e.rx2("eff")).ravel()
        eff_e[~np.isfinite(eff_e)] = np.nan
        theta[extra_idx] = eff_e

    return theta


def score_coalition(spine: pd.DataFrame, S: FrozenSet[str], *,
                    cfg: NewBenchmarkingConfig | None = None) -> CoalitionScore:
    """Score coalition S (a set of players) in frozen mode via R/Benchmarking."""
    cfg = cfg or NewBenchmarkingConfig()
    reids = spine[COL_REID].to_numpy()

    frozen_mask = np.isin(reids, FROZEN_REIDS)
    ei_mask = np.isin(reids, EI_EXCLUDED_REIDS)
    ref_mask = ~frozen_mask
    scored_mask = ~ei_mask

    out_cols = subset_outputs(S)
    X = subset_input(spine, S).to_numpy(dtype=float).reshape(-1, 1)
    Y = spine[out_cols].to_numpy(dtype=float)

    theta = _theta_frozen(X, Y, ref_mask, scored_mask, cfg.rts)
    theta[~scored_mask] = np.nan
    eff = np.where(np.isfinite(theta), np.minimum(theta, 1.0), np.nan)

    scored = pd.DataFrame({
        COL_REID: reids,
        COL_DEA_EFFICIENCY: eff,
        COL_IS_OUTLIER: frozen_mask,
    })
    e75 = reference_efficiency(scored[COL_DEA_EFFICIENCY], scored[COL_IS_OUTLIER],
                               cfg.reference_percentile)
    req = calculate_two_sided_requirement(
        scored, reference_percentile=cfg.reference_percentile, gap_cap=cfg.gap_cap,
        sharing=cfg.sharing, realization_time=cfg.realization_time,
        supervision_period=cfg.supervision_period,
    )[COL_EFF_REQ_ANNUAL].to_numpy() * 100.0

    return CoalitionScore(
        reid=reids, theta=theta, efficiency=eff, is_outlier=frozen_mask,
        e75=e75, requirement_pp=req,
    )

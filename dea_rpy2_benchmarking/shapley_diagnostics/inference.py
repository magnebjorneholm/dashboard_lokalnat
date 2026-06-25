"""Bootstrap inference for DEA efficiency (Simar & Wilson), via Benchmarking::dea.boot.

DEA efficiency is a point estimate of a boundary; it is biased (the sample frontier
sits inside the true one) and has no closed-form standard error. dea.boot resamples
the firms, re-estimates the frontier each time, and returns the bias, variance,
bias-corrected score and a per-firm confidence interval.

Per the agreed scope this runs ONLY on the two endpoint coalitions (baseline v(∅)
and full v(N)) — the inference question is "how solid is each firm's efficiency in
the model we actually use", which the endpoints answer; the interior coalitions are
covered by the (cheaper) peers/shadow-price diagnostics instead.

The frontier is the fixed frozen reference set R (144 firms), consistent with the
scoring and the other diagnostics.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from config.column_names import COL_REID
from new_benchmarking_model.analysis.decomp.players import subset_input, subset_outputs
from new_benchmarking_model.config import NewBenchmarkingConfig

from .scoring import FROZEN_REIDS, _np2r, _r2np
from dea_benchmarking.r_session import get_benchmarking, r

DEFAULT_NREP = 2000
_BOOT_SEED = 42  # fixed so the bootstrap CI is reproducible run to run


@dataclass
class CoalitionInference:
    """Bootstrap inference for one coalition's efficiency, indexed by reference firms."""

    ref_reid: np.ndarray
    eff: np.ndarray        # original DEA efficiency
    eff_bc: np.ndarray     # bias-corrected efficiency
    bias: np.ndarray
    var: np.ndarray
    ci_low: np.ndarray     # lower confidence bound
    ci_high: np.ndarray    # upper confidence bound
    nrep: int

    def to_frame(self) -> pd.DataFrame:
        return pd.DataFrame({
            COL_REID: self.ref_reid, "eff": self.eff, "eff_bc": self.eff_bc,
            "bias": self.bias, "var": self.var,
            "ci_low": self.ci_low, "ci_high": self.ci_high,
        })


def coalition_inference(spine: pd.DataFrame, S, *, nrep: int = DEFAULT_NREP,
                        cfg: NewBenchmarkingConfig | None = None) -> CoalitionInference:
    """Bootstrap CI for coalition S's efficiency on the frozen reference frontier."""
    cfg = cfg or NewBenchmarkingConfig()
    bench = get_benchmarking()
    reids = spine[COL_REID].to_numpy()
    ref_idx = np.where(~np.isin(reids, FROZEN_REIDS))[0]

    out_cols = subset_outputs(S)
    X = subset_input(spine, S).to_numpy(dtype=float).reshape(-1, 1)[ref_idx]
    Y = spine[out_cols].to_numpy(dtype=float)[ref_idx]

    r["set.seed"](_BOOT_SEED)
    b = bench.dea_boot(_np2r(X), _np2r(Y), NREP=nrep, RTS=cfg.rts, ORIENTATION="in")
    ci = _r2np(b.rx2("conf.int"))
    if ci.ndim == 1:
        ci = ci.reshape(-1, 2)
    # Benchmarking labels the two columns "97.5%"/"2.5%", and for input-oriented
    # efficiency the lower bound lands in the "97.5%" column — so assign by value,
    # not by column position, to be convention-proof.
    lo = np.minimum(ci[:, 0], ci[:, 1])
    hi = np.maximum(ci[:, 0], ci[:, 1])

    return CoalitionInference(
        ref_reid=reids[ref_idx],
        eff=_r2np(b.rx2("eff")).ravel(),
        eff_bc=_r2np(b.rx2("eff.bc")).ravel(),
        bias=_r2np(b.rx2("bias")).ravel(),
        var=_r2np(b.rx2("var")).ravel(),
        ci_low=lo, ci_high=hi, nrep=nrep,
    )

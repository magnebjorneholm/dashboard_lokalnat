"""
s3_inference.py — DEA-aware resampling inference for the channel slopes (step 3).

The naive homoskedastic t-CI in s3 ignores the cross-sectional dependence that DEA
induces (shared frontier + the E75 reference is a sample percentile). This recomputes
the WHOLE pipeline (full / channel-A-off / channel-B-off + the two-sided requirement +
E75) on each resample, so frontier and reference dependence propagate into the CI.

The OLS slope stays the point estimate; only the interval is replaced. Coupled by
construction: each resample recomputes all three specs, so beta_A = beta_full - beta_offA
is exact per replicate.

Scheme: SUBSAMPLING without replacement is primary (m<n) — it re-estimates the frontier
on a subset and, unlike n-of-n with replacement, creates no duplicate DMUs (duplicates
would spuriously inflate efficiency). n-of-n is kept only as a caveated contrast.
Subsampling CI uses the sqrt(m) rescaling (working rate for the second-stage slope).

    .venv/bin/python new_benchmarking_model/analysis/s3_inference.py          # full run (~15 min, parallel)
    .venv/bin/python new_benchmarking_model/analysis/s3_inference.py smoke     # tiny B sanity run
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _helpers import load_analysis_df, add_urban_proxies, OUT_DIR, NEW_MODEL_BASE_OUTPUTS  # noqa: E402
from config.column_names import COL_REID, COL_CABLE_LENGTH_KM, COL_EFF_REQ_ANNUAL  # noqa: E402
from new_benchmarking_model.config import NewBenchmarkingConfig  # noqa: E402
from calculations.frontier.dea_calculations import run_dea_analysis  # noqa: E402
from new_benchmarking_model.efficiency.efficiency_requirement_two_sided import (  # noqa: E402
    calculate_two_sided_requirement,
)

CFG = NewBenchmarkingConfig()
BASE = list(NEW_MODEL_BASE_OUTPUTS)
FULL = BASE + [COL_CABLE_LENGTH_KM]
TS = dict(reference_percentile=CFG.reference_percentile, gap_cap=CFG.gap_cap,
          sharing=CFG.sharing, realization_time=CFG.realization_time,
          supervision_period=CFG.supervision_period)
SLOPES = ["beta_net", "beta_A", "beta_B"]

_SPINE = None  # set per worker via initializer


def _init(spine):
    global _SPINE
    _SPINE = spine


def _req(frame, inp, outs):
    forced = frame[COL_REID].isin(CFG.exclude_reids).to_numpy()
    d = run_dea_analysis(frame, {"inputs": [inp], "outputs": outs, "rts": CFG.rts,
                                 "forced_outliers": forced})
    d = calculate_two_sided_requirement(d, **TS)
    return d[COL_EFF_REQ_ANNUAL].to_numpy() * 100.0   # pp


def _slope(x, y):
    m = np.isfinite(x) & np.isfinite(y)
    if m.sum() < 3:
        return np.nan
    x, y = x[m], y[m]
    xb = x.mean()
    return float(((x - xb) * (y - y.mean())).sum() / ((x - xb) ** 2).sum())


def _slopes(frame):
    rf = _req(frame, "totex_new", FULL)
    ra = _req(frame, "totex_unadj", FULL)
    rb = _req(frame, "totex_new", BASE)
    urb = frame["urbanity_index"].to_numpy()
    return _slope(urb, rf), _slope(urb, rf - ra), _slope(urb, rf - rb)


def _worker(idx):
    return _slopes(_SPINE.iloc[idx])


def run_scheme(spine, scheme, B, m, seed, workers):
    n = len(spine)
    rng = np.random.default_rng(seed)
    if scheme == "subsample":
        idxs = [rng.choice(n, m, replace=False) for _ in range(B)]
    else:  # n-of-n with replacement (contrast)
        idxs = [rng.choice(n, n, replace=True) for _ in range(B)]
    with Pool(workers, initializer=_init, initargs=(spine,)) as p:
        res = p.map(_worker, idxs)
    return np.asarray(res)  # B x 3


def _ci(arr, j, scheme, m, n, bhat):
    col = arr[:, j]
    col = col[np.isfinite(col)]
    if scheme == "subsample":
        resc = np.sqrt(m) * (col - bhat[j])
        qlo, qhi = np.percentile(resc, [2.5, 97.5])
        return bhat[j] - qhi / np.sqrt(n), bhat[j] - qlo / np.sqrt(n), col.std(ddof=1), len(col)
    lo, hi = np.percentile(col, [2.5, 97.5])
    return lo, hi, col.std(ddof=1), len(col)


if __name__ == "__main__":
    smoke = len(sys.argv) > 1 and sys.argv[1] == "smoke"
    spine = add_urban_proxies(load_analysis_df())
    n = len(spine)
    bhat = np.array(_slopes(spine))   # OLS point estimate on the full sample
    print(f"point estimates: beta_net={bhat[0]:+.4f} beta_A={bhat[1]:+.4f} beta_B={bhat[2]:+.4f}")

    WORKERS = 9
    configs = ([("subsample", 75, 6)] if smoke
               else [("subsample", 75, 300), ("subsample", 110, 300), ("nofn", None, 120)])

    rows = []
    for scheme, m, B in configs:
        t = time.time()
        arr = run_scheme(spine, scheme, B, m, seed=42, workers=WORKERS)
        for j, nm in enumerate(SLOPES):
            lo, hi, se, nb = _ci(arr, j, scheme, m, n, bhat)
            rows.append({"scheme": scheme, "m": m or n, "B": nb, "slope": nm,
                         "point": round(bhat[j], 4), "ci_low": round(lo, 4),
                         "ci_high": round(hi, 4), "boot_se": round(se, 4)})
        print(f"  {scheme} m={m} B={B}: {time.time() - t:.0f}s")

    rob = pd.DataFrame(rows)
    print("\n" + rob.to_string(index=False))
    if not smoke:
        rob.to_csv(OUT_DIR / "s3_slopes_robustness.csv", index=False)
        # augment s3_slopes.csv with the primary (subsample m=75) bootstrap CI
        prim = rob[(rob.scheme == "subsample") & (rob.m == 75)].set_index("slope")
        chan_to_slope = {"A: capex-adj (phi pp)": "beta_A",
                         "B: cable-length (phi pp)": "beta_B",
                         "net: full model (req level, pp/urb)": "beta_net"}
        s3 = pd.read_csv(OUT_DIR / "s3_slopes.csv")
        s3["boot_ci_low"] = [prim.loc[chan_to_slope[c], "ci_low"] for c in s3["channel"]]
        s3["boot_ci_high"] = [prim.loc[chan_to_slope[c], "ci_high"] for c in s3["channel"]]
        s3["boot_se"] = [prim.loc[chan_to_slope[c], "boot_se"] for c in s3["channel"]]
        s3.to_csv(OUT_DIR / "s3_slopes.csv", index=False)
        print(f"\nsaved: s3_slopes_robustness.csv; augmented s3_slopes.csv (primary = subsample m=75)")

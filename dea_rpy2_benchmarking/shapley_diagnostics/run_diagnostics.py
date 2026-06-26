"""Sweep all 128 coalitions (frozen mode) and write the R/Benchmarking diagnostics.

For every coalition S (subset of the 7 cost-component players) this computes, on the
fixed frozen reference frontier:

    - efficiency + signed two-sided requirement   (scoring.py)  -> validated against
      the existing PuLP analysis (the parity gate),
    - super-efficiency theta                        (scoring.py),
    - number.peers / n_peers_per_firm               (metrics.py),
    - shadow prices u, v                            (metrics.py).

For the two endpoint coalitions (baseline v(0) and full v(N)) it also runs the
Simar-Wilson bootstrap (inference.py).

Outputs land in shapley_diagnostics/out/ (see README). The parity table is written
for ALL 128 coalitions so the whole sweep is provably equivalent to the legacy
value grid, not just the endpoints.

    uv run python -m dea_rpy2_benchmarking.shapley_diagnostics.run_diagnostics
    uv run python -m dea_rpy2_benchmarking.shapley_diagnostics.run_diagnostics --nrep 200   # faster boot
    uv run python -m dea_rpy2_benchmarking.shapley_diagnostics.run_diagnostics --smoke      # 1 coalition, tiny boot
"""

from __future__ import annotations

import argparse
import json
import sys
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
for p in (str(REPO_ROOT), str(REPO_ROOT / "dea_rpy2_benchmarking")):
    if p not in sys.path:
        sys.path.insert(0, p)

from new_benchmarking_model.analysis._helpers import load_analysis_df  # noqa: E402
from new_benchmarking_model.analysis.decomp.players import PLAYERS  # noqa: E402
from new_benchmarking_model.config import NewBenchmarkingConfig  # noqa: E402
from shapley_diagnostics.scoring import score_coalition, FROZEN_REIDS  # noqa: E402
from shapley_diagnostics.metrics import coalition_diagnostics  # noqa: E402
from shapley_diagnostics.inference import coalition_inference, DEFAULT_NREP  # noqa: E402

OUT_DIR = Path(__file__).resolve().parent / "out"
# Parity tolerances vs the legacy PuLP value grid. 127/128 coalitions agree to ~5e-9;
# a single degenerate coalition (different optimal LP vertex between CBC and lpSolve)
# sits at ~1e-6 eff / ~5e-6 pp req — still negligible, so the gate allows solver-level
# slack rather than demanding bit-identity across two different LP backends.
EFF_TOL = 1e-5       # efficiency is 0-1; 1e-5 = 0.001 %
REQ_TOL_PP = 1e-4    # requirement in pp
_FROZEN_VG = REPO_ROOT / "new_benchmarking_model/analysis/out"


def subset_mask(S) -> int:
    """Bitmask over PLAYERS order — same encoding as the legacy analysis."""
    return sum(1 << i for i, p in enumerate(PLAYERS) if p in S)


def players_csv(S) -> str:
    return "+".join(p for p in PLAYERS if p in S) or "(baseline)"


def all_subsets():
    for r in range(len(PLAYERS) + 1):
        for c in combinations(PLAYERS, r):
            yield frozenset(c)


def _load_facit():
    """Existing frozen value grids (eff + req) for the parity gate."""
    eff = pd.read_csv(_FROZEN_VG / "decomp_eff/frozen/value_grid.csv")
    req = pd.read_csv(_FROZEN_VG / "decomp_req/frozen/value_grid.csv")
    return eff, req


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--nrep", type=int, default=DEFAULT_NREP, help="dea.boot replications")
    ap.add_argument("--smoke", action="store_true", help="1 coalition, tiny bootstrap")
    args = ap.parse_args()

    cfg = NewBenchmarkingConfig()
    spine = load_analysis_df()
    reids = spine["REId"].to_numpy()
    vg_eff, vg_req = _load_facit()
    eff_by_mask = {m: g.set_index("REId")["value"] for m, g in vg_eff.groupby("subset_mask")}
    req_by_mask = {m: g.set_index("REId")["value"] for m, g in vg_req.groupby("subset_mask")}

    subsets = [frozenset()] if args.smoke else list(all_subsets())
    nrep = 20 if args.smoke else args.nrep
    print(f"spine: {len(spine)} firms; sweeping {len(subsets)} coalitions (frozen); "
          f"frozen set {list(FROZEN_REIDS)}")

    se_rows, peer_rows, sp_rows, par_rows, peerlink_rows = [], [], [], [], []
    max_eff_d = max_req_d = 0.0

    for k, S in enumerate(subsets):
        mask = subset_mask(S)
        pcsv = players_csv(S)

        cs = score_coalition(spine, S, cfg=cfg)
        dg = coalition_diagnostics(spine, S, cfg=cfg)

        # Parity vs the legacy value grid (eff + req), per coalition.
        fe = eff_by_mask[mask].reindex(reids).to_numpy()
        fr = req_by_mask[mask].reindex(reids).to_numpy()
        d_eff = float(np.nanmax(np.abs(cs.efficiency - fe)))
        d_req = float(np.nanmax(np.abs(cs.requirement_pp - fr)))
        max_eff_d = max(max_eff_d, d_eff)
        max_req_d = max(max_req_d, d_req)
        par_rows.append({"subset_mask": mask, "players": pcsv, "e75": cs.e75,
                         "max_abs_d_eff": d_eff, "max_abs_d_req": d_req})

        # Per-firm coalition scores (all scored firms): super-eff, capped eff, and the
        # signed two-sided requirement. requirement_pp is aligned to `reids` just like
        # theta/efficiency, so reusing the same finite-theta filter is exact: a scored
        # firm has finite theta and a finite requirement; the Ei-excluded have NaN for both.
        for i in range(len(reids)):
            if np.isfinite(cs.theta[i]):
                se_rows.append({"subset_mask": mask, "players": pcsv, "REId": reids[i],
                                "super_eff": cs.theta[i], "eff": cs.efficiency[i],
                                "requirement_pp": cs.requirement_pp[i]})

        # Peers + shadow prices (reference firms).
        for j, rid in enumerate(dg.ref_reid):
            peer_rows.append({"subset_mask": mask, "players": pcsv, "REId": rid,
                              "number_peers": dg.number_peers[j],
                              "n_peers_per_firm": dg.n_peers_per_firm[j],
                              "eff_standard": dg.eff_standard[j]})
            sp_rows.append({"subset_mask": mask, "players": pcsv, "REId": rid,
                            "kind": "u", "variable": "totex", "value": float(dg.u[j, 0])})
            for c, name in enumerate(dg.output_names):
                sp_rows.append({"subset_mask": mask, "players": pcsv, "REId": rid,
                                "kind": "v", "variable": name, "value": float(dg.v[j, c])})

        # Peer identities + weights (sparse lambda): who each firm leans on.
        ref = dg.ref_reid
        for fi, pj, w in zip(dg.peer_firm_idx, dg.peer_ref_idx, dg.peer_weight):
            peerlink_rows.append({"subset_mask": mask, "players": pcsv,
                                  "REId": ref[fi], "peer_REId": ref[pj],
                                  "is_self": bool(fi == pj), "lambda_weight": float(w)})

        if (k + 1) % 16 == 0 or k + 1 == len(subsets):
            print(f"  {k + 1}/{len(subsets)} coalitions  (running max|Δeff|={max_eff_d:.1e}, "
                  f"max|Δreq|={max_req_d:.1e})")

    # Inference on the endpoints only.
    inf_rows = []
    endpoints = [("baseline", frozenset())] if args.smoke else \
        [("baseline", frozenset()), ("full", frozenset(PLAYERS))]
    for label, S in endpoints:
        print(f"  bootstrap [{label}] NREP={nrep} ...")
        inf = coalition_inference(spine, S, nrep=nrep, cfg=cfg)
        df = inf.to_frame()
        df.insert(0, "coalition", label)
        df.insert(1, "subset_mask", subset_mask(S))
        inf_rows.append(df)

    peerlinks = pd.DataFrame(peerlink_rows)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(se_rows).to_csv(OUT_DIR / "coalition_scores.csv", index=False)
    pd.DataFrame(peer_rows).to_csv(OUT_DIR / "number_peers.csv", index=False)
    peerlinks.to_csv(OUT_DIR / "peers.csv", index=False)
    pd.DataFrame(sp_rows).to_csv(OUT_DIR / "shadow_prices.csv", index=False)
    pd.DataFrame(par_rows).to_csv(OUT_DIR / "parity.csv", index=False)
    pd.concat(inf_rows, ignore_index=True).to_csv(OUT_DIR / "inference.csv", index=False)

    manifest = {
        "outlier_mode": "frozen",
        "frozen_reids": list(FROZEN_REIDS),
        "n_coalitions": len(subsets),
        "n_reference_firms": int((~np.isin(reids, FROZEN_REIDS)).sum()),
        "rts": cfg.rts,
        "dual_frontier": "standard (dea.dual)",
        "bootstrap_nrep": nrep,
        "bootstrap_endpoints": [lbl for lbl, _ in endpoints],
        "shadow_price_nan": int(pd.DataFrame(sp_rows)["value"].isna().sum()),
        "n_peer_links": int(len(peerlinks)),
        "parity": {"max_abs_d_eff": max_eff_d, "max_abs_d_req_pp": max_req_d,
                   "eff_tol": EFF_TOL, "req_tol_pp": REQ_TOL_PP,
                   "passed": bool(max_eff_d < EFF_TOL and max_req_d < REQ_TOL_PP)},
    }
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2))

    status = "PASS" if manifest["parity"]["passed"] else "FAIL"
    print(f"\nparity gate: {status}  (max|Δeff|={max_eff_d:.2e}, max|Δreq|={max_req_d:.2e} pp)")
    print(f"saved → {OUT_DIR.relative_to(REPO_ROOT)}")
    return 0 if manifest["parity"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

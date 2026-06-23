"""
run_decomposition.py — the parametrised cost-component decomposition (replaces s4 + s5).

Runs the Shapley decomposition of the new-benchmarking outcome over the parameter grid

    outcome      ∈ {"req", "eff"}
    outlier_mode ∈ {"dynamic", "frozen"}

For each outlier mode the 128 DEA subsets are solved ONCE and reused for both outcomes
(efficiency and requirement share the same DEA solve), so a full sweep is 128 × 2 = 256
DEA solves, not 512. Each (outcome, mode) result is written under

    out/decomp_<outcome>/<outlier_mode>/   (see decomp/io.py)

Players (7): losses, grid_subscription, grid_connection, feed_in, capacity_reserve,
capex_adj, cable. The frontier payable post is opexp_dea (NOT controllable_cost_average).

Usage:
    .venv/bin/python new_benchmarking_model/analysis/run_decomposition.py                  # all 4
    .venv/bin/python new_benchmarking_model/analysis/run_decomposition.py --outcomes req   # req only
    .venv/bin/python new_benchmarking_model/analysis/run_decomposition.py --modes frozen   # frozen only
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from new_benchmarking_model.analysis._helpers import load_analysis_df          # noqa: E402
from new_benchmarking_model.analysis.decomp.engine import compute_grids, decompose  # noqa: E402
from new_benchmarking_model.analysis.decomp.io import write_run                 # noqa: E402
from new_benchmarking_model.config import NewBenchmarkingConfig                 # noqa: E402

OUTCOMES = ("req", "eff")
MODES = ("dynamic", "frozen")


def main() -> None:
    ap = argparse.ArgumentParser(description="Parametrised Shapley decomposition.")
    ap.add_argument("--outcomes", nargs="+", choices=OUTCOMES, default=list(OUTCOMES))
    ap.add_argument("--modes", nargs="+", choices=MODES, default=list(MODES))
    args = ap.parse_args()

    cfg = NewBenchmarkingConfig()
    spine = load_analysis_df()
    print(f"spine: {len(spine)} firms; players=7 → {2**7} subsets per outlier mode")

    for mode in args.modes:
        print(f"\n=== outlier_mode = {mode} :: solving {2**7} DEA subsets (once for both outcomes) ===")
        grid = compute_grids(spine, mode, cfg)
        if grid.frozen_reids:
            print(f"  frozen outlier set: {grid.frozen_reids}")
        for outcome in args.outcomes:
            res = decompose(spine, grid, outcome, cfg)
            d = write_run(res)
            ident = res.checks.get("shapley_identity_max_resid", float("nan"))
            print(f"  [{outcome}/{mode}] Shapley identity max|resid| = {ident:.2e}")
            for k, v in res.checks.items():
                if k != "shapley_identity_max_resid":
                    print(f"      {k}: {v:.2e}")
            print(f"      top players: "
                  + ", ".join(f"{r.player} {r.mean_abs_phi:.4f}"
                              for r in res.summary.head(3).itertuples()))
            print(f"      saved → {d.relative_to(REPO_ROOT)}")

    print("\nDone.")


if __name__ == "__main__":
    main()

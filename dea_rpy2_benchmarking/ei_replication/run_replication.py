"""CLI: replicate Ei's DEA and report the match against the published facit.

Run from the repo root (so the project's config/ is importable):
    uv run python -m dea_rpy2_benchmarking.ei_replication.run_replication
or:
    cd dea_rpy2_benchmarking && uv run python ei_replication/run_replication.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make both the repo root (for config.data_paths) and this package importable.
_PKG_ROOT = Path(__file__).resolve().parent.parent       # dea_rpy2_benchmarking/
_REPO_ROOT = _PKG_ROOT.parent                            # project root
for p in (str(_REPO_ROOT), str(_PKG_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

from ei_replication.compare import compare  # noqa: E402
from ei_replication.data import KNOWN_NONREPLICABLE, load_model_data  # noqa: E402
from ei_replication.replicate import replicate  # noqa: E402


def main() -> int:
    md = load_model_data()
    print(f"Loaded {md.n} firms; inputs={md.X.shape[1]}, outputs={md.Y.shape[1]}")

    res = replicate(md.X, md.Y)
    print(f"Outlier rounds: {res.n_rounds}   outliers: {int(res.is_outlier.sum())}")
    print(f"Outlier firms : {', '.join(md.reid[res.is_outlier].tolist())}")

    cmp = compare(md, res)
    print(f"\nComparison vs facit (excluding {', '.join(cmp.excluded)}):")
    print(f"  tolerance         : {cmp.tolerance:.1e}")
    print(f"  max |eff  diff|   : {cmp.max_eff_diff:.3e}")
    print(f"  max |seff diff|   : {cmp.max_seff_diff:.3e}")
    print(f"  firms over tol    : eff={cmp.n_eff_exceeding}, seff={cmp.n_seff_exceeding}")
    print(f"  RESULT            : {'PASS' if cmp.passed else 'FAIL'}")

    # Always show the known anomaly explicitly so it is never mistaken for a bug.
    row = cmp.table[cmp.table["REId"] == KNOWN_NONREPLICABLE]
    if not row.empty:
        r = row.iloc[0]
        print(f"\nKnown non-replicable row {KNOWN_NONREPLICABLE} (data anomaly, expected):")
        print(f"  super-eff replicated={r.seff_repl:.6f}  facit={r.seff_facit:.6f}")

    return 0 if cmp.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

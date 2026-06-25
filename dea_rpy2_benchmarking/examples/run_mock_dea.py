"""End-to-end smoke demo: mock data -> DEA + super-efficiency -> printed results.

Run from the package root:
    uv run python -m examples.run_mock_dea
or:
    cd dea_rpy2_benchmarking && uv run python examples/run_mock_dea.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make ``src/`` and the package root importable when run as a plain script.
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "src"))
sys.path.insert(0, str(_ROOT))

import numpy as np  # noqa: E402

from dea_benchmarking import dea, r_version, sdea  # noqa: E402
from examples.mock_data import random_dmus, textbook_example  # noqa: E402


def _print_result(title, res, names):
    print(f"\n=== {title} ===")
    print(res)
    for name, e in zip(names, res.eff):
        flag = "  <- efficient" if abs(e - 1.0) <= 1e-6 else ""
        print(f"  {name:10s} eff = {e:7.4f}{flag}")


def main() -> None:
    print(f"Active R: {r_version()}")

    # 1) Textbook single-input/single-output example.
    X, Y, names = textbook_example()
    res = dea(X, Y, rts="vrs", orientation="in", dmu_names=names)
    _print_result("Textbook VRS input-oriented DEA", res, names)

    # 2) Larger random set: standard DEA then super-efficiency ranking.
    X, Y, names = random_dmus(n_dmu=15, n_inputs=2, n_outputs=2, seed=7)
    res = dea(X, Y, rts="crs", orientation="in", slack=True, dmu_names=names)
    _print_result("Random 15-DMU CRS DEA (with slack)", res, names)
    print(f"  mean efficiency: {res.eff.mean():.4f}")
    if res.slack is not None:
        print(f"  total slack (sum): {res.slack.sum():.4f}")

    sres = sdea(X, Y, rts="crs", orientation="in", dmu_names=names)
    print("\n  super-efficiency (efficient units only, ranked):")
    eff_mask = res.efficient()
    ranking = sorted(
        (np.array(names)[eff_mask].tolist()),
        key=lambda n: -sres.eff[names.index(n)],
    )
    for n in ranking:
        print(f"    {n:10s} sdea = {sres.eff[names.index(n)]:.4f}")

    print("\nOK — DEA pipeline runs end to end on mock data.")


if __name__ == "__main__":
    main()

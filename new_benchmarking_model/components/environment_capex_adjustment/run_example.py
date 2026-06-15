"""
run_example.py — demonstrate and sanity-check the environment capex adjustment.

Run directly from anywhere:
    ./venv/Scripts/python.exe new_benchmarking_model/components/environment_capex_adjustment/run_example.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import pandas as pd  # noqa: E402

from new_benchmarking_model.components.environment_capex_adjustment import (  # noqa: E402
    run_environment_adjustment,
    load_jordkabel_components,
    calibrate,
    apply_environment_adjustment,
    C,
)

pd.set_option("display.width", 200)
pd.set_option("display.float_format", lambda x: f"{x:,.3f}")


def main() -> None:
    components = load_jordkabel_components()
    calib = calibrate(components)

    print("=" * 78)
    print("CALIBRATION — premium per förläggningsmiljö (reference = landsbygd normal)")
    print("=" * 78)
    cov = calib.coverage.copy()
    cov["sek_per_km"] = cov["sek_per_km"].map(lambda x: f"{x:,.0f}")
    cov["percent"] = cov["percent"].map(lambda x: f"{x:.1%}")
    cov["km_matched_share"] = cov["km_matched_share"].map(lambda x: f"{x:.1%}")
    cov["value_total"] = (cov["value_total"] / 1e9).map(lambda x: f"{x:,.1f} bn")
    print(cov[[C.COL_ENV, "n_types_matched", "km_matched_share",
               "value_total", "sek_per_km", "percent"]].to_string(index=False))

    # Compare the three methods at the sector level
    print("\n" + "=" * 78)
    print("METHOD COMPARISON — total jordkabel value vs adjusted (all companies)")
    print("=" * 78)
    for method in C.METHODS:
        res = apply_environment_adjustment(components, calib, method=method)
        orig = res.per_company[C.COL_VALUE].sum()
        adj = res.per_company[C.COL_ADJ_VALUE].sum()
        ded = res.per_company[C.COL_DEDUCTION].sum()
        print(f"  {method:11s}: original {orig/1e9:6.1f} bn  ->  adjusted {adj/1e9:6.1f} bn"
              f"   (deduction {ded/1e9:5.1f} bn, {ded/orig:.1%})")

    # Per-company effect under the precise method
    print("\n" + "=" * 78)
    print("TOP 10 companies by effective deduction (method = exact)")
    print("=" * 78)
    res = run_environment_adjustment(method=C.METHOD_EXACT)
    pc = res.per_company.sort_values(C.COL_EFFECTIVE_PCT, ascending=False).head(10).copy()
    pc["value_mn"] = (pc[C.COL_VALUE] / 1e6).map(lambda x: f"{x:,.0f}")
    pc["deduction_mn"] = (pc[C.COL_DEDUCTION] / 1e6).map(lambda x: f"{x:,.0f}")
    pc["effective_pct"] = pc[C.COL_EFFECTIVE_PCT].map(lambda x: f"{x:.1%}")
    print(pc[[C.COL_REID, "value_mn", "deduction_mn", "effective_pct"]].to_string(index=False))

    print("\nDone.")


if __name__ == "__main__":
    main()

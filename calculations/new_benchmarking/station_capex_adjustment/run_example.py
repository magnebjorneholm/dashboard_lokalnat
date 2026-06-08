"""
run_example.py — demonstrate and sanity-check the station capex adjustment.

Run directly from anywhere:
    ./venv/Scripts/python.exe calculations/new_benchmarking/station_capex_adjustment/run_example.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import pandas as pd  # noqa: E402

from calculations.new_benchmarking.station_capex_adjustment import (  # noqa: E402
    run_station_adjustment,
    load_station_components,
    calibrate,
    apply_environment_adjustment,
    C,
)

pd.set_option("display.width", 200)
pd.set_option("display.float_format", lambda x: f"{x:,.3f}")


def main() -> None:
    components = load_station_components()
    calib = calibrate(components)

    print("=" * 78)
    print("CALIBRATION — tätort station premium (reference = outside tätort)")
    print("=" * 78)
    cov = calib.coverage.iloc[0]
    print(f"  surcharge rows          : {int(cov['n_components']):,}")
    print(f"  stations with surcharge : {cov['n_stations']:,.0f}")
    print(f"  companies with surcharge: {int(cov['companies_with_surcharge'])} / {int(cov['companies_total'])}")
    print(f"  premium value           : {cov['premium_value']/1e9:,.2f} bn SEK")
    print(f"  total station base       : {cov['station_value_total']/1e9:,.2f} bn SEK")
    print(f"  premium share of base    : {cov['percent']:.1%}")
    print(f"  SEK / station (list price): {cov['sek_per_station']:,.0f}")

    # Compare the two methods at the sector level
    print("\n" + "=" * 78)
    print("METHOD COMPARISON — total station value vs adjusted (all companies)")
    print("=" * 78)
    for method in C.METHODS:
        res = apply_environment_adjustment(components, calib, method=method)
        orig = res.per_company[C.COL_VALUE].sum()
        adj = res.per_company[C.COL_ADJ_VALUE].sum()
        ded = res.per_company[C.COL_DEDUCTION].sum()
        print(f"  {method:9s}: original {orig/1e9:6.1f} bn  ->  adjusted {adj/1e9:6.1f} bn"
              f"   (deduction {ded/1e9:5.1f} bn, {ded/orig:.1%})")

    # Per-company effect under the exact method
    print("\n" + "=" * 78)
    print("TOP 10 companies by effective deduction (method = itemized)")
    print("=" * 78)
    res = run_station_adjustment(method=C.METHOD_ITEMIZED)
    pc = res.per_company.sort_values(C.COL_EFFECTIVE_PCT, ascending=False).head(10).copy()
    pc["value_mn"] = (pc[C.COL_VALUE] / 1e6).map(lambda x: f"{x:,.0f}")
    pc["deduction_mn"] = (pc[C.COL_DEDUCTION] / 1e6).map(lambda x: f"{x:,.0f}")
    pc["effective_pct"] = pc[C.COL_EFFECTIVE_PCT].map(lambda x: f"{x:.1%}")
    pc["reduction_factor"] = pc[C.COL_REDUCTION_FACTOR].map(lambda x: f"{x:.3f}")
    print(pc[[C.COL_REID, "value_mn", "deduction_mn", "effective_pct",
              "reduction_factor"]].to_string(index=False))

    # Distribution of the per-company deduction (itemized)
    print("\n" + "=" * 78)
    print("DISTRIBUTION of per-company effective deduction (method = itemized)")
    print("=" * 78)
    print((res.per_company[C.COL_EFFECTIVE_PCT] * 100).describe().round(2).to_string())
    zero = (res.per_company[C.COL_EFFECTIVE_PCT] == 0).mean()
    print(f"\n  companies with no tätort surcharge (0% deduction): {zero:.1%}")

    print("\nDone.")


if __name__ == "__main__":
    main()

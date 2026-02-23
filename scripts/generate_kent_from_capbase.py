"""
scripts/generate_kent_from_capbase.py

Reverse-engineers a KENT Excel file from capbase_a.parquet for company 886
(Kraftringen Nat AB). The generated file, when processed through
build_capbase_a_from_kent() -> run_kent_calculations_batch(), should produce
identical capital cost results as the baseline.

Usage:
    cd dashboard_lokalnat
    ./venv/Scripts/python.exe scripts/generate_kent_from_capbase.py
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pandas as pd
import numpy as np
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
OUTPUT_PATH = DATA_DIR / "generated_kent_886.xlsx"
NETWORK_ID = 886
WACC = 0.0453

# Reverse mapping: cat_encode -> KENT anl_kat text that round-trips through
# CATEGORY_MAPPING in kent_capbase_prep.py (substring match, case-insensitive)
REVERSE_CAT = {
    1: "Markarbeten, LK",
    2: "Annan ledning, LK",
    3: "Kabel",
    4: "Luftledning, LK",
    5: "IT-system",
    6: "Kabelskåp",
    7: "Kabel 220kV+",
    8: "Luftledning 220kV+",
    9: "Luftledning, OK",
    10: "Markarbeten 220kV+",
    11: "Markarbeten, OK",
    12: "Mätare",
    13: "Nätstation",
    14: "Shuntreaktor",
    15: "Styr/kontroll",
    16: "Ställverk",
    17: "Transformator",
}


def time_from_to_year(tf: float) -> float:
    """Reverse of year_to_time_code: time_code -> year (float, supports H2)."""
    if pd.isna(tf):
        return np.nan
    return (tf - 1) / 2 + 1910


def time_invest_to_halvar(ti: float) -> str:
    """Reverse of halvar_to_time_code: time_code -> '2024 H1' format."""
    if pd.isna(ti):
        return ""
    ti = int(ti)
    year = (ti - 1) // 2 + 1910
    half = "H1" if (ti % 2) == 1 else "H2"
    return f"{year} {half}"


def load_company_capbase(network_id: int) -> pd.DataFrame:
    """Load capbase_a rows for a single company."""
    path = DATA_DIR / "capbase_a.parquet"
    df = pd.read_parquet(path)
    company = df[df["id_network"] == network_id].copy()
    print(f"Loaded {len(company)} rows for id_network={network_id}")
    print(f"  Existing: {(company['capbase_existing'] == 1).sum()}")
    print(f"  Future:   {(company['capbase_existing'] == 0).sum()}")
    return company


def build_normvarde_sheet(existing: pd.DataFrame) -> pd.DataFrame:
    """Build Sheet 1 'Normvarde' from existing assets."""
    rows = []
    for _, r in existing.iterrows():
        rows.append({
            "Anl.-kategori": REVERSE_CAT.get(r["cat_encode"], "Transformator"),
            "Kod": int(r["cat_encode"]),
            "Typ av anläggning": r.get("subcat", ""),
            "Antal": r.get("count_comp", 1),
            "Rådighet": "ägd" if r.get("owned", 1) == 1 else "ej ägd",
            "Ursprungligen tagen i bruk": time_from_to_year(r["time_from"]),
            "Tidsperiod för ursprunglig tagen i bruk Från": "",
            "Till": "",
            "År saknas": "",
            "NUAV": r["nuav_2022"],
        })
    return pd.DataFrame(rows)


def build_ovriga_sheet() -> pd.DataFrame:
    """Build empty Sheet 2 'Ovriga varderingsmetoder' with correct headers."""
    cols = [
        "Ansk", "Bokf", "Annat", "Anl.kategori",
        "Typ av anläggning", "Antal", "Ursprungligen tagen i bruk",
        "Rådighet", "NUAV 2022",
    ]
    return pd.DataFrame(columns=cols)


def build_investeringar_sheet(future: pd.DataFrame) -> pd.DataFrame:
    """Build Sheet 3 'Investeringar_Utrangeringar' from future investments."""
    rows = []
    for _, r in future.iterrows():
        invest_sign = r.get("invest", 1.0)
        if pd.isna(invest_sign):
            invest_sign = 1.0
        typ = "Investering" if invest_sign > 0 else "Utrangering"

        rows.append({
            "Investering / Utrangering": typ,
            "Halvår": time_invest_to_halvar(r["time_invest"]),
            "Anl.kategori": REVERSE_CAT.get(r["cat_encode"], "Transformator"),
            "Typ av anläggning": r.get("subcat", ""),
            "Antal": r.get("count_comp", 1),
            "Totalt i kronor": abs(r["nuav_2022"]),
            "Ursprungligen tagen i bruk": time_from_to_year(r["time_from"]),
        })
    return pd.DataFrame(rows)


def generate_kent_excel(network_id: int = NETWORK_ID) -> Path:
    """Generate KENT Excel file from capbase_a data."""
    capbase = load_company_capbase(network_id)

    existing = capbase[capbase["capbase_existing"] == 1].copy()
    future = capbase[capbase["capbase_existing"] == 0].copy()

    sheet1 = build_normvarde_sheet(existing)
    sheet2 = build_ovriga_sheet()
    sheet3 = build_investeringar_sheet(future)

    print(f"\nBuilding KENT Excel:")
    print(f"  Sheet 'Normvärde':                    {len(sheet1)} rows")
    print(f"  Sheet 'Övriga värderingsmetoder':      {len(sheet2)} rows")
    print(f"  Sheet 'Investeringar_Utrangeringar':   {len(sheet3)} rows")

    with pd.ExcelWriter(OUTPUT_PATH, engine="openpyxl") as writer:
        # header=1 means read_kent_excel expects the header on row index 1
        # so we write a title row first, then the data with headers
        for sheet_name, df in [
            ("Normvärde", sheet1),
            ("Övriga värderingsmetoder", sheet2),
            ("Investeringar_Utrangeringar", sheet3),
        ]:
            # Write title row + data starting at row 1
            df.to_excel(writer, sheet_name=sheet_name, index=False, startrow=1)
            ws = writer.sheets[sheet_name]
            ws.cell(row=1, column=1, value=sheet_name)

    print(f"\nSaved to: {OUTPUT_PATH}")
    return OUTPUT_PATH


def verify_roundtrip(kent_path: Path, network_id: int = NETWORK_ID):
    """Verify that generated KENT file produces correct capital costs."""
    from calculations.capex.kent_capbase_prep import build_capbase_a_from_kent
    from calculations.capex.kent_calculations import run_kent_calculations_batch

    print("\n=== Round-trip verification ===")
    print(f"Reading KENT file: {kent_path}")

    capbase_from_kent = build_capbase_a_from_kent(str(kent_path), network_id)
    print(f"capbase_a from KENT: {len(capbase_from_kent)} rows")

    _, df_network, _ = run_kent_calculations_batch(capbase_from_kent, wacc=WACC)
    row = df_network[df_network["id_network"] == network_id].iloc[0]

    EXPECTED = {
        "capital_cost_2024": 421294.7929530114,
        "capital_cost_2025": 426379.45313688926,
        "capital_cost_2026": 430758.4156895735,
        "capital_cost_2027": 435833.0997066046,
        "capital_cost_period": 1714265.7614860786,
        "depreciation_2024": 231034.10364999977,
        "depreciation_2025": 234623.28254953108,
        "depreciation_2026": 237620.61005355237,
        "depreciation_2027": 241392.8488825707,
        "depreciation_period": 944670.8451356539,
        "return_on_assets_2024": 190260.68930301163,
        "return_on_assets_2025": 191756.1705873582,
        "return_on_assets_2026": 193137.80563602116,
        "return_on_assets_2027": 194440.25082403392,
        "return_on_assets_period": 769594.916350425,
    }

    all_pass = True
    for metric, expected in EXPECTED.items():
        actual = row[metric]
        diff_pct = abs(actual - expected) / expected * 100
        status = "PASS" if diff_pct < 0.01 else "FAIL"
        if status == "FAIL":
            all_pass = False
        print(f"  {metric}: {actual:>14,.2f}  (expected {expected:>14,.2f}, diff {diff_pct:.6f}%) [{status}]")

    if all_pass:
        print("\n>>> ALL CHECKS PASSED - KENT file is a valid round-trip! <<<")
    else:
        print("\n>>> SOME CHECKS FAILED - see details above <<<")

    return all_pass


if __name__ == "__main__":
    path = generate_kent_excel()
    verify_roundtrip(path)

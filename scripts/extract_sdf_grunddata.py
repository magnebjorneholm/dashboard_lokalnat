"""
scripts/extract_sdf_grunddata.py

Extract detailed controllable and non-controllable cost data from the SDF Excel file
into clean parquet files (grunddata) for use in the pipeline.

Outputs:
    data/controllable_a.parquet       - Tidy: company × category × year
    data/controllable_meta.parquet    - One row per company: index, neo, eff_req
    data/non_controllable_a.parquet   - Tidy: company × kent_category × year

Run: ./venv/Scripts/python.exe scripts/extract_sdf_grunddata.py
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SDF_FILE = Path("data/Löpande kostnader från SDF 2024-27.xlsx")

# Column positions in the Påverkbara sheet (0-indexed, data starts at row 2)
# Each group spans 4 columns for years 2018, 2019, 2020, 2021
EXPENSE_GROUPS = {
    "RR7320_power_purchase":       3,   # RR7320 Transitering och inköp av kraft
    "RR73120_materials":           7,   # RR73120 Råvaror och förnödenheter
    "RR73130_external_services":  11,   # RR73130 Övriga externa kostnader
    "RR73140_personnel":          15,   # RR73140 Personalkostnader
    "RR73180_other_operating":    19,   # RR73180 Övriga rörelsekostnader
}

ADJUSTMENT_GROUPS = {
    "RR71120_inventory_change":   27,   # RR71120 Förändring av varulager
    "RR71140_capitalized_work":   31,   # RR71140 Aktiverat arbete för egen räkning
}

# 13 TN/KENT deduction lines (cols 35-86, step 4)
DEDUCTION_COL_STARTS = list(range(35, 84, 4))  # 35, 39, 43, ..., 83

# Verification / derived columns
COL_SUMMA_KOSTNADER = 23   # |sum of 5 RR expense categories|
COL_SUMMA_AVGAR = 87       # Summa avgår
COL_PAVERKBARA = 91        # Påverkbara kostnader
COL_KAP_EJ_KAPBAS = 103    # Kapitalkostnad ej kapitalbasen
COL_NEO_PER_YEAR = 107     # NeoÄndringar per year
COL_TOTALA_PAVERKBARA = 111 # Totala påverkbara kostnader
COL_INDEX = 115             # Index L/R
COL_SUMMA_2022 = 119       # Summa påverkbara i 2022 prisnivå
COL_MEDELVARDE = 123        # Medelvärde 2018-2021
COL_NEO_UNSEPARATED = 124   # Unseparated NeoÄndringar (period sum, 2022 price level)
COL_EFF_REQ_PCT = 136       # Årligt eff.krav procent

YEARS = [2018, 2019, 2020, 2021]

# Non-controllable KENT categories (Opåverkbara sheet)
NON_CTRL_CATEGORIES = {
    "network_loss_purchased":       3,   # KENT - Nätförluster, inköp
    "network_loss_own_production":  7,   # KENT - Nätförluster, egen produktion
    "grid_subscription":           11,   # KENT - Abonnemang till överliggande nät
    "grid_connection":             15,   # KENT - Anslutning till överliggande nät
    "feed_in_compensation":        19,   # KENT - Nätnytta-ersättning (inmatning)
    "regulatory_fees":             23,   # KENT - Myndighetsavgifter
    "capacity_reserve":            27,   # KENT - Nätkapacitetsreserv
}

NON_CTRL_TOTAL_PER_YEAR = 31  # Totala opåverkbara per år
NON_CTRL_TOTAL_PERIOD = 35    # Totala opåverkbara per period
NON_CTRL_YEARS = [2024, 2025, 2026, 2027]


# ---------------------------------------------------------------------------
# Extraction: Controllable (Påverkbara)
# ---------------------------------------------------------------------------

def extract_controllable(sdf_file: Path):
    """
    Parse the Påverkbara sheet and return 3 DataFrames:
    - detail: tidy format (company × category × year)
    - meta: one row per company
    - raw_verification: per-company verification values from the sheet
    """
    df_raw = pd.read_excel(sdf_file, sheet_name="Påverkbara", engine="openpyxl", header=None)

    # Data rows start at row 2 (0=header, 1=year labels)
    data = df_raw.iloc[2:].copy().reset_index(drop=True)

    # Filter to local networks only
    data = data[data.iloc[:, 1] == "L"].reset_index(drop=True)
    data = data[data.iloc[:, 0].astype(str).str.startswith("REL")].reset_index(drop=True)
    n_companies = len(data)
    print(f"  Påverkbara: {n_companies} local companies after filtering")

    detail_rows = []
    meta_rows = []
    verif_rows = []

    for _, row in data.iterrows():
        reid = str(row.iloc[0])

        for yr_offset, year in enumerate(YEARS):
            # 5 RR expense categories (stored POSITIVE = costs)
            for cat_name, col_start in EXPENSE_GROUPS.items():
                raw_val = _to_float(row.iloc[col_start + yr_offset])
                # Sheet values are negative (costs); negate to store as positive
                detail_rows.append({
                    "REId": reid,
                    "category": cat_name,
                    "year": year,
                    "amount_nominal": -raw_val,
                })

            # RR71 adjustments → net contribution = -(RR71140 + RR71120)
            rr71120 = _to_float(row.iloc[ADJUSTMENT_GROUPS["RR71120_inventory_change"] + yr_offset])
            rr71140 = _to_float(row.iloc[ADJUSTMENT_GROUPS["RR71140_capitalized_work"] + yr_offset])
            detail_rows.append({
                "REId": reid,
                "category": "RR71_adjustments",
                "year": year,
                "amount_nominal": -(rr71140 + rr71120),
            })

            # KENT deductions → sum of 13 TN/KENT lines (already negative in sheet)
            tn_kent_sum = sum(
                _to_float(row.iloc[c + yr_offset]) for c in DEDUCTION_COL_STARTS
            )
            detail_rows.append({
                "REId": reid,
                "category": "KENT_deductions",
                "year": year,
                "amount_nominal": tn_kent_sum,  # negative = reduces total
            })

            # Kap ej kapbas (capital cost outside base)
            kap_ej = _to_float(row.iloc[COL_KAP_EJ_KAPBAS + yr_offset])
            detail_rows.append({
                "REId": reid,
                "category": "capital_cost_outside_base",
                "year": year,
                "amount_nominal": kap_ej,
            })

            # Neo adjustments per year (separated by company)
            neo_yr = _to_float(row.iloc[COL_NEO_PER_YEAR + yr_offset])
            detail_rows.append({
                "REId": reid,
                "category": "neo_adjustments_per_year",
                "year": year,
                "amount_nominal": neo_yr,
            })

        # Meta data (per company)
        meta_rows.append({
            "REId": reid,
            "index_2018": _to_float(row.iloc[COL_INDEX + 0]),
            "index_2019": _to_float(row.iloc[COL_INDEX + 1]),
            "index_2020": _to_float(row.iloc[COL_INDEX + 2]),
            "index_2021": _to_float(row.iloc[COL_INDEX + 3]),
            "neo_adjustment": _to_float(row.iloc[COL_NEO_UNSEPARATED]),
            "eff_req_pct": _to_float(row.iloc[COL_EFF_REQ_PCT]),
        })

        # Verification values
        verif_rows.append({
            "REId": reid,
            **{f"paverkbara_{y}": _to_float(row.iloc[COL_PAVERKBARA + off])
               for off, y in enumerate(YEARS)},
            **{f"totala_paverkbara_{y}": _to_float(row.iloc[COL_TOTALA_PAVERKBARA + off])
               for off, y in enumerate(YEARS)},
            **{f"summa_2022_{y}": _to_float(row.iloc[COL_SUMMA_2022 + off])
               for off, y in enumerate(YEARS)},
            "medelvarde": _to_float(row.iloc[COL_MEDELVARDE]),
        })

    detail = pd.DataFrame(detail_rows)
    meta = pd.DataFrame(meta_rows)
    verif = pd.DataFrame(verif_rows)

    return detail, meta, verif


# ---------------------------------------------------------------------------
# Extraction: Non-controllable (Opåverkbara)
# ---------------------------------------------------------------------------

def extract_non_controllable(sdf_file: Path):
    """
    Parse the Opåverkbara sheet and return:
    - detail: tidy format (company × kent_category × year)
    - verif: per-company verification values
    """
    df_raw = pd.read_excel(sdf_file, sheet_name="Opåverkbara", engine="openpyxl", header=None)

    # Data starts at row 2 (0=header, 1=year/region labels)
    data = df_raw.iloc[2:].copy().reset_index(drop=True)

    # Filter to local networks (col 1 = Lokal/Region)
    data = data[data.iloc[:, 1] == "L"].reset_index(drop=True)
    data = data[data.iloc[:, 0].astype(str).str.startswith("REL")].reset_index(drop=True)
    n_companies = len(data)
    print(f"  Opåverkbara: {n_companies} local companies after filtering")

    detail_rows = []
    verif_rows = []

    for _, row in data.iterrows():
        reid = str(row.iloc[0])

        for yr_offset, year in enumerate(NON_CTRL_YEARS):
            for cat_name, col_start in NON_CTRL_CATEGORIES.items():
                val = _to_float(row.iloc[col_start + yr_offset])
                detail_rows.append({
                    "REId": reid,
                    "kent_category": cat_name,
                    "year": year,
                    "amount": val,
                })

        # Verification: per-year totals and period total
        verif_rows.append({
            "REId": reid,
            **{f"total_{y}": _to_float(row.iloc[NON_CTRL_TOTAL_PER_YEAR + off])
               for off, y in enumerate(NON_CTRL_YEARS)},
            "total_period": _to_float(row.iloc[NON_CTRL_TOTAL_PERIOD]),
        })

    detail = pd.DataFrame(detail_rows)
    verif = pd.DataFrame(verif_rows)

    return detail, verif


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------

def verify_controllable(detail: pd.DataFrame, meta: pd.DataFrame, verif: pd.DataFrame):
    """Verify controllable data against SDF facit values."""
    print("\n=== Controllable Verification ===")

    # Check 1: Sum of categories per year = Totala påverkbara (col 111)
    cat_sums = detail.groupby(["REId", "year"])["amount_nominal"].sum().reset_index()
    cat_sums.columns = ["REId", "year", "cat_sum"]

    max_diff_totala = 0
    fail_count = 0

    for _, vrow in verif.iterrows():
        reid = vrow["REId"]
        for yr in YEARS:
            expected = vrow[f"totala_paverkbara_{yr}"]
            actual_rows = cat_sums[(cat_sums["REId"] == reid) & (cat_sums["year"] == yr)]
            if actual_rows.empty:
                print(f"  MISSING: {reid} year {yr}")
                fail_count += 1
                continue
            actual = actual_rows["cat_sum"].iloc[0]
            diff = abs(actual - expected)
            max_diff_totala = max(max_diff_totala, diff)
            if diff > 1.0:
                print(f"  FAIL: {reid} {yr}: sum={actual:.2f}, expected={expected:.2f}, diff={diff:.2f}")
                fail_count += 1

    n_checks = len(verif) * 4
    print(f"  Check 1 (sum = Totala påverkbara): {n_checks - fail_count}/{n_checks} pass, max diff = {max_diff_totala:.4f} tkr")

    # Check 2: sum × index → average ≈ Medelvärde (col 123)
    cat_sums_pivot = cat_sums.pivot(index="REId", columns="year", values="cat_sum")

    merged = meta.merge(verif[["REId", "medelvarde"]], on="REId")
    max_diff_avg = 0
    avg_fail = 0

    for _, mrow in merged.iterrows():
        reid = mrow["REId"]
        if reid not in cat_sums_pivot.index:
            continue

        yearly_2022 = []
        for yr in YEARS:
            nominal = cat_sums_pivot.loc[reid, yr]
            idx = mrow[f"index_{yr}"]
            yearly_2022.append(nominal * idx)

        computed_avg = np.mean(yearly_2022)
        expected_avg = mrow["medelvarde"]
        diff = abs(computed_avg - expected_avg)
        max_diff_avg = max(max_diff_avg, diff)
        if diff > 1.0:
            print(f"  AVG FAIL: {reid}: computed={computed_avg:.2f}, expected={expected_avg:.2f}, diff={diff:.2f}")
            avg_fail += 1

    print(f"  Check 2 (average = Medelvärde): {len(merged) - avg_fail}/{len(merged)} pass, max diff = {max_diff_avg:.4f} tkr")

    # Check 3: Show specific companies
    for reid in ["REL00001", "REL00886", "REL03035"]:
        mrow = merged[merged["REId"] == reid]
        if mrow.empty:
            continue
        mrow = mrow.iloc[0]
        if reid in cat_sums_pivot.index:
            yearly_2022 = []
            for yr in YEARS:
                nominal = cat_sums_pivot.loc[reid, yr]
                idx = mrow[f"index_{yr}"]
                yearly_2022.append(nominal * idx)
            computed_avg = np.mean(yearly_2022)
            neo = mrow["neo_adjustment"]
            print(f"  {reid}: avg={computed_avg:.2f}, medelvärde={mrow['medelvarde']:.2f}, "
                  f"diff={abs(computed_avg - mrow['medelvarde']):.4f}, neo_unsep={neo:.0f}")


def verify_non_controllable(detail: pd.DataFrame, verif: pd.DataFrame):
    """Verify non-controllable data against SDF facit values."""
    print("\n=== Non-Controllable Verification ===")

    # Check 1: Sum per company per year = sheet total per year
    cat_sums = detail.groupby(["REId", "year"])["amount"].sum().reset_index()
    cat_sums.columns = ["REId", "year", "cat_sum"]

    max_diff = 0
    fail_count = 0

    for _, vrow in verif.iterrows():
        reid = vrow["REId"]
        for yr in NON_CTRL_YEARS:
            expected = vrow[f"total_{yr}"]
            actual_rows = cat_sums[(cat_sums["REId"] == reid) & (cat_sums["year"] == yr)]
            if actual_rows.empty:
                fail_count += 1
                continue
            actual = actual_rows["cat_sum"].iloc[0]
            diff = abs(actual - expected)
            max_diff = max(max_diff, diff)
            if diff > 1.0:
                print(f"  FAIL: {reid} {yr}: sum={actual:.2f}, expected={expected:.2f}")
                fail_count += 1

    n_checks = len(verif) * 4
    print(f"  Check 1 (sum per year = total): {n_checks - fail_count}/{n_checks} pass, max diff = {max_diff:.4f} tkr")

    # Check 2: Period sum
    period_sums = detail.groupby("REId")["amount"].sum().reset_index()
    period_sums.columns = ["REId", "computed_period"]
    period_sums = period_sums.merge(verif[["REId", "total_period"]], on="REId")

    max_period_diff = abs(period_sums["computed_period"] - period_sums["total_period"]).max()
    period_pass = (abs(period_sums["computed_period"] - period_sums["total_period"]) <= 1.0).sum()
    print(f"  Check 2 (period sum): {period_pass}/{len(period_sums)} pass, max diff = {max_period_diff:.4f} tkr")

    # Specific companies
    for reid in ["REL00001", "REL00886", "REL03035"]:
        row = period_sums[period_sums["REId"] == reid]
        if not row.empty:
            row = row.iloc[0]
            print(f"  {reid}: computed={row['computed_period']:.0f}, expected={row['total_period']:.0f}, "
                  f"diff={abs(row['computed_period'] - row['total_period']):.2f}")


# Also verify against SDF IR sheet
def verify_non_controllable_vs_ir(detail: pd.DataFrame, sdf_file: Path):
    """Cross-check non-controllable period totals against SDF IR sheet."""
    print("\n=== Non-Controllable vs IR Sheet ===")
    df_ir = pd.read_excel(sdf_file, sheet_name="IR 2024-2027", engine="openpyxl")

    # Find the non-controllable column
    reid_col = "REid" if "REid" in df_ir.columns else "REId"
    nonctrl_col = None
    for col in df_ir.columns:
        if "opåverkbara" in col.lower() or "opaverkbara" in col.lower():
            nonctrl_col = col
            break

    if nonctrl_col is None:
        print("  WARNING: Could not find non-controllable column in IR sheet")
        return

    # Filter to local REL* companies
    ir_local = df_ir[df_ir[reid_col].astype(str).str.startswith("REL")].copy()
    ir_local = ir_local.rename(columns={reid_col: "REId"})

    # Compare period sums
    period_sums = detail.groupby("REId")["amount"].sum().reset_index()
    period_sums.columns = ["REId", "computed_period"]

    merged = period_sums.merge(ir_local[["REId", nonctrl_col]], on="REId")
    merged["ir_value"] = pd.to_numeric(merged[nonctrl_col], errors="coerce")
    # Opåverkbara sheet stores costs as negative; IR stores as positive
    merged["diff"] = abs(merged["computed_period"] + merged["ir_value"])  # sign-flipped comparison

    max_diff = merged["diff"].max()
    n_pass = (merged["diff"] <= 1.0).sum()
    print(f"  Match vs IR: {n_pass}/{len(merged)} pass, max diff = {max_diff:.2f} tkr")

    if max_diff > 1.0:
        fails = merged[merged["diff"] > 1.0].head(5)
        for _, r in fails.iterrows():
            print(f"  DIFF: {r['REId']}: computed={r['computed_period']:.0f}, IR={r['ir_value']:.0f}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _to_float(val) -> float:
    """Convert a value to float, treating NaN/None as 0."""
    try:
        f = float(val)
        return 0.0 if np.isnan(f) else f
    except (ValueError, TypeError):
        return 0.0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if not SDF_FILE.exists():
        print(f"ERROR: SDF file not found: {SDF_FILE}")
        sys.exit(1)

    print(f"Reading {SDF_FILE}...")

    # --- Controllable ---
    print("\nExtracting controllable costs...")
    ctrl_detail, ctrl_meta, ctrl_verif = extract_controllable(SDF_FILE)
    verify_controllable(ctrl_detail, ctrl_meta, ctrl_verif)

    # --- Non-controllable ---
    print("\nExtracting non-controllable costs...")
    nonctrl_detail, nonctrl_verif = extract_non_controllable(SDF_FILE)
    verify_non_controllable(nonctrl_detail, nonctrl_verif)
    verify_non_controllable_vs_ir(nonctrl_detail, SDF_FILE)

    # --- Save parquets ---
    out_dir = Path("data")

    ctrl_detail.to_parquet(out_dir / "controllable_a.parquet", index=False)
    print(f"\nSaved: {out_dir / 'controllable_a.parquet'} ({len(ctrl_detail)} rows)")

    ctrl_meta.to_parquet(out_dir / "controllable_meta.parquet", index=False)
    print(f"Saved: {out_dir / 'controllable_meta.parquet'} ({len(ctrl_meta)} rows)")

    nonctrl_detail.to_parquet(out_dir / "non_controllable_a.parquet", index=False)
    print(f"Saved: {out_dir / 'non_controllable_a.parquet'} ({len(nonctrl_detail)} rows)")

    # Summary
    print(f"\n=== Summary ===")
    print(f"Controllable: {ctrl_detail['REId'].nunique()} companies, "
          f"{ctrl_detail['category'].nunique()} categories, "
          f"{ctrl_detail['year'].nunique()} years")
    print(f"Controllable meta: {len(ctrl_meta)} companies")
    print(f"Non-controllable: {nonctrl_detail['REId'].nunique()} companies, "
          f"{nonctrl_detail['kent_category'].nunique()} categories, "
          f"{nonctrl_detail['year'].nunique()} years")

    # Show category list
    print(f"\nControllable categories:")
    for cat in ctrl_detail["category"].unique():
        n_nonzero = (ctrl_detail[ctrl_detail["category"] == cat]["amount_nominal"].abs() > 0.01).sum()
        print(f"  {cat}: {n_nonzero} non-zero values")

    print(f"\nNon-controllable categories:")
    for cat in nonctrl_detail["kent_category"].unique():
        n_nonzero = (nonctrl_detail[nonctrl_detail["kent_category"] == cat]["amount"].abs() > 0.01).sum()
        print(f"  {cat}: {n_nonzero} non-zero values")


if __name__ == "__main__":
    main()

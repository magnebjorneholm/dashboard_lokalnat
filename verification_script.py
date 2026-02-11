"""
verification_script.py

Test-driven variable specification & canonical naming.
Cross-references data sources to prove what each variable represents.

Uses capbase_a_mini.parquet (3 test companies) for speed.

NOTE: All data sources now use English canonical column names.
See config/column_names.py for the full mapping.
"""

import pandas as pd
import numpy as np
import sys
import os

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from calculations.kent_calculations import run_kent_calculations_batch
from calculations.controllable_cost_calculations import (
    get_controllable_from_sdf,
    calculate_controllable_with_eff_req,
)
from calculations.efficiency_requirement import (
    calculate_eff_req_for_dataframe,
    calculate_truncation_min_from_outlier_req,
)
from calculations.revenue_frame_assembly import assemble_revenue_frame
from data_loaders.baseline_data import load_baseline_data

# ============================================================================
# Configuration
# ============================================================================

TEST_COMPANIES = {
    1: {"REId": "REL00001", "name": "Ale El ek. for.", "has_neo": False},
    886: {"REId": "REL00886", "name": "Kraftringen Nat AB", "has_neo": True},
    3035: {"REId": "REL03035", "name": "(large company)", "has_neo": False},
}

TOLERANCE_PCT = 0.1  # 0.1% relative tolerance for "equal"
WACC = 0.0453


def fmt(val, unit="tkr"):
    """Format value for display."""
    if pd.isna(val):
        return "NaN"
    if unit == "tkr":
        return f"{val:,.1f} tkr"
    if unit == "pct":
        return f"{val:.4%}"
    return f"{val}"


def compare(label, val_a, val_b, source_a="KENT", source_b="DM"):
    """Compare two values and report difference."""
    if pd.isna(val_a) or pd.isna(val_b):
        print(f"  {label}: {source_a}={fmt(val_a)} | {source_b}={fmt(val_b)} | CANNOT COMPARE (NaN)")
        return None

    abs_diff = val_a - val_b
    rel_diff = abs_diff / val_b if val_b != 0 else float("inf")

    match = abs(rel_diff) < TOLERANCE_PCT / 100
    status = "OK" if match else "MISMATCH"

    print(
        f"  {label}: {source_a}={fmt(val_a)} | {source_b}={fmt(val_b)} | "
        f"diff={abs_diff:+,.1f} tkr ({rel_diff:+.4%}) [{status}]"
    )
    return {"label": label, "val_a": val_a, "val_b": val_b,
            "abs_diff": abs_diff, "rel_diff": rel_diff, "match": match}


# ============================================================================
# Load all data
# ============================================================================

def load_all_data():
    """Load all data sources needed for verification."""
    print("=" * 80)
    print("LOADING DATA")
    print("=" * 80)

    # 1. Mini capbase (3 test companies)
    print("\n1. Loading capbase_a_mini.parquet...")
    capbase = pd.read_parquet("data/capbase_a_mini.parquet")
    print(f"   {len(capbase)} rows, {capbase['id_network'].nunique()} companies: "
          f"{sorted(capbase['id_network'].unique())}")

    # 2. Baseline data (all 148 companies)
    print("\n2. Loading baseline data (Data_modeller, EIs_DEA, SDF)...")
    baseline = load_baseline_data()
    dm = baseline.df_all_companies
    print(f"   Data_modeller: {len(dm)} companies")
    print(f"   Columns: {list(dm.columns)}")

    # 3. capcost_a (pre-aggregated capital costs)
    print("\n3. Loading capcost_a.parquet...")
    capcost_a = pd.read_parquet("data/capcost_a.parquet")
    print(f"   {len(capcost_a)} rows, {capcost_a['id_network'].nunique()} companies")
    print(f"   Columns: {list(capcost_a.columns)}")

    # 4. SDF IR columns
    print("\n4. SDF IR sheet columns:")
    print(f"   {list(baseline.sdf_ir.columns)}")

    # 5. SDF Controllable columns
    print("\n5. SDF Controllable sheet columns:")
    print(f"   {list(baseline.sdf_controllable.columns)}")

    # 6. SDF Non-controllable columns
    print("\n6. SDF Non-controllable sheet columns:")
    print(f"   {list(baseline.sdf_non_controllable.columns)}")

    # 7. DEA results
    print("\n7. EIs_DEA results:")
    print(f"   {len(baseline.dea_results)} companies")
    print(f"   Columns: {list(baseline.dea_results.columns)}")

    return capbase, baseline, capcost_a


# ============================================================================
# Run KENT calculations
# ============================================================================

def run_kent(capbase):
    """Run KENT calculations on mini capbase."""
    print("\n" + "=" * 80)
    print("RUNNING KENT CALCULATIONS (3 test companies)")
    print("=" * 80)

    df_detailed, df_network, df_category = run_kent_calculations_batch(
        capbase, wacc=WACC
    )

    print(f"\ndf_network: {len(df_network)} rows")
    print(f"  Columns: {list(df_network.columns)}")
    print(f"\ndf_category: {len(df_category)} rows")

    return df_detailed, df_network, df_category


# ============================================================================
# GROUP 1: Capital Cost Variables
# ============================================================================

def group1_capital_costs(df_network, df_category, baseline, capcost_a):
    """Verify capital cost variables across sources."""
    print("\n" + "=" * 80)
    print("GROUP 1: CAPITAL COST VARIABLES")
    print("=" * 80)

    dm = baseline.df_all_companies
    sdf_ir = baseline.sdf_ir
    results = []

    # -------------------------------------------------------------------
    # 1a. KENT vs Data_modeller (first-year values)
    # -------------------------------------------------------------------
    print("\n--- 1a. KENT vs Data_modeller (first-year / 2024 values) ---")

    for id_net, info in TEST_COMPANIES.items():
        reid = info["REId"]
        print(f"\n  Company: {reid} (id_network={id_net})")

        kent_row = df_network[df_network["id_network"] == id_net]
        dm_row = dm[dm["REId"] == reid]

        if kent_row.empty:
            print(f"    NOT FOUND in KENT output")
            continue
        if dm_row.empty:
            print(f"    NOT FOUND in Data_modeller")
            continue

        kent_row = kent_row.iloc[0]
        dm_row = dm_row.iloc[0]

        # capital_cost_2024 (KENT) vs capital_cost_2024 (DM, was CAPEX)
        r = compare("capital_cost_2024",
                     kent_row["capital_cost_2024"], dm_row["capital_cost_2024"],
                     "KENT", "DM")
        if r:
            results.append(r)

        # depreciation_2024 (KENT) vs depreciation_2024 (DM, was Avskrivning)
        r = compare("depreciation_2024",
                     kent_row["depreciation_2024"], dm_row["depreciation_2024"],
                     "KENT", "DM")
        if r:
            results.append(r)

        # return_on_assets_2024 (KENT) vs return_on_assets_2024 (DM, was Avkastning)
        # Note: DM aggregate "Avkastning" was DROPPED; only per-year exist.
        # DM now has return_on_assets_2024 from the per-year rename.
        r = compare("return_on_assets_2024",
                     kent_row["return_on_assets_2024"], dm_row["return_on_assets_2024"],
                     "KENT", "DM")
        if r:
            results.append(r)

    # -------------------------------------------------------------------
    # 1b. KENT vs Data_modeller (per-year returns)
    # -------------------------------------------------------------------
    print("\n--- 1b. KENT vs Data_modeller (per-year returns) ---")

    for id_net, info in TEST_COMPANIES.items():
        reid = info["REId"]
        print(f"\n  Company: {reid}")

        kent_row = df_network[df_network["id_network"] == id_net]
        dm_row = dm[dm["REId"] == reid]
        if kent_row.empty or dm_row.empty:
            continue

        kent_row = kent_row.iloc[0]
        dm_row = dm_row.iloc[0]

        for year in [2024, 2025, 2026, 2027]:
            col = f"return_on_assets_{year}"
            if col in dm_row.index:
                r = compare(col, kent_row[col], dm_row[col], "KENT", "DM")
                if r:
                    results.append(r)

        # Period sum
        r = compare("return_on_assets_period",
                     kent_row["return_on_assets_period"], dm_row["return_on_assets_period"],
                     "KENT", "DM")
        if r:
            results.append(r)

    # -------------------------------------------------------------------
    # 1c. KENT vs SDF IR (period sums)
    # -------------------------------------------------------------------
    print("\n--- 1c. KENT vs SDF IR (period sums) ---")

    # Discover REId column in SDF IR
    sdf_reid_col = None
    for c in sdf_ir.columns:
        if c.lower() in ("reid", "re-id", "re id", "reid"):
            sdf_reid_col = c
            break
    if sdf_reid_col is None:
        # Try to find any column with 'REL' values
        for c in sdf_ir.columns:
            sample = sdf_ir[c].astype(str).head(5)
            if sample.str.startswith("REL").any():
                sdf_reid_col = c
                break

    if sdf_reid_col:
        print(f"  SDF IR REId column: '{sdf_reid_col}'")
    else:
        print(f"  WARNING: Could not find REId column in SDF IR")
        print(f"  Available columns: {list(sdf_ir.columns)}")

    # Discover capital cost columns in SDF IR
    # After SDF_IR_RENAME, renamed columns are English; unrenamed stay Swedish.
    # Search for BOTH English (renamed) and Swedish (unrenamed) patterns.
    sdf_capcost_col = None
    sdf_dep_col = None
    sdf_return_col = None

    for c in sdf_ir.columns:
        cl = c.lower().strip()
        # English renamed patterns
        if c == "capital_cost_period":
            sdf_capcost_col = c
        elif c == "depreciation_period":
            sdf_dep_col = c
        elif c == "return_on_assets_period":
            sdf_return_col = c
        # Swedish fallback patterns (in case SDF IR rename was not applied)
        elif sdf_capcost_col is None and "kapitalkostnad" in cl and "varav" not in cl:
            sdf_capcost_col = c
        elif sdf_dep_col is None and ("kapitalforslitning" in cl or "kapital-forslitning" in cl
                or "kapitalförslitning" in cl or "kapital-förslitning" in cl):
            sdf_dep_col = c
        elif sdf_return_col is None and ("kapitalbindning" in cl or "kapital-bindning" in cl):
            sdf_return_col = c

    print(f"  SDF IR capital cost col: '{sdf_capcost_col}'")
    print(f"  SDF IR depreciation col: '{sdf_dep_col}'")
    print(f"  SDF IR return col: '{sdf_return_col}'")

    if sdf_reid_col and sdf_capcost_col:
        for id_net, info in TEST_COMPANIES.items():
            reid = info["REId"]
            print(f"\n  Company: {reid}")

            kent_row = df_network[df_network["id_network"] == id_net]
            sdf_row = sdf_ir[sdf_ir[sdf_reid_col] == reid]

            if kent_row.empty or sdf_row.empty:
                print(f"    Skipped (not found)")
                continue

            kent_row = kent_row.iloc[0]
            sdf_row = sdf_row.iloc[0]

            # capital_cost_period (KENT) vs SDF capital cost
            if sdf_capcost_col:
                r = compare("capital_cost_period vs SDF",
                            kent_row["capital_cost_period"],
                            sdf_row[sdf_capcost_col],
                            "KENT", "SDF_IR")
                if r:
                    results.append(r)

            # depreciation_period (KENT) vs SDF depreciation
            if sdf_dep_col:
                r = compare("depreciation_period vs SDF",
                            kent_row["depreciation_period"],
                            sdf_row[sdf_dep_col],
                            "KENT", "SDF_IR")
                if r:
                    results.append(r)

            # return_on_assets_period (KENT) vs SDF return
            if sdf_return_col:
                r = compare("return_on_assets_period vs SDF",
                            kent_row["return_on_assets_period"],
                            sdf_row[sdf_return_col],
                            "KENT", "SDF_IR")
                if r:
                    results.append(r)

    # -------------------------------------------------------------------
    # 1d. KENT vs capcost_a (category-level)
    # -------------------------------------------------------------------
    print("\n--- 1d. KENT vs capcost_a (category-level) ---")

    for id_net, info in TEST_COMPANIES.items():
        reid = info["REId"]
        print(f"\n  Company: {reid}")

        kent_cat = df_category[df_category["id_network"] == id_net].copy()
        capcost_cat = capcost_a[capcost_a["id_network"] == id_net].copy()

        if kent_cat.empty:
            print(f"    NOT FOUND in KENT category output")
            continue
        if capcost_cat.empty:
            print(f"    NOT FOUND in capcost_a")
            continue

        # Merge on (cat_encode, time) and compare
        merged = kent_cat.merge(
            capcost_cat,
            on=["id_network", "cat_encode", "time"],
            suffixes=("_kent", "_capcost")
        )

        if merged.empty:
            print(f"    No matching (cat_encode, time) pairs")
            continue

        # Compare capcost_sum
        value_cols = ["nuav_ord", "nuav_tail", "dep_ord", "dep_tail",
                      "return_ord", "return_tail", "capcost_sum"]

        for col in value_cols:
            kent_col = f"{col}_kent"
            capcost_col = f"{col}_capcost"

            if kent_col in merged.columns and capcost_col in merged.columns:
                max_abs_diff = (merged[kent_col] - merged[capcost_col]).abs().max()
                max_rel_diff = (
                    (merged[kent_col] - merged[capcost_col]).abs() /
                    merged[capcost_col].abs().clip(lower=1e-6)
                ).max()

                n_rows = len(merged)
                n_match = (
                    (merged[kent_col] - merged[capcost_col]).abs() <
                    merged[capcost_col].abs() * TOLERANCE_PCT / 100 + 0.01
                ).sum()

                status = "OK" if n_match == n_rows else "MISMATCH"
                print(
                    f"    {col}: {n_match}/{n_rows} match | "
                    f"max_abs_diff={max_abs_diff:.2f} tkr | "
                    f"max_rel_diff={max_rel_diff:.4%} [{status}]"
                )

    return results


# ============================================================================
# GROUP 2: Controllable Cost Variables (OPEXp)
# ============================================================================

def group2_controllable_costs(baseline):
    """Verify controllable cost variables."""
    print("\n" + "=" * 80)
    print("GROUP 2: CONTROLLABLE COST VARIABLES (controllable_cost_average)")
    print("=" * 80)

    dm = baseline.df_all_companies
    sdf_ir = baseline.sdf_ir
    sdf_ctrl = baseline.sdf_controllable
    results = []

    # -------------------------------------------------------------------
    # 2a. SDF controllable (average) vs Data_modeller
    # -------------------------------------------------------------------
    print("\n--- 2a. SDF controllable (average) vs Data_modeller controllable_cost_average ---")

    # Get controllable baseline from SDF
    try:
        sdf_baseline = get_controllable_from_sdf(sdf_ir, sdf_ctrl)
        print(f"  SDF baseline loaded: {len(sdf_baseline)} companies")
        print(f"  Columns: {list(sdf_baseline.columns)}")
    except Exception as e:
        print(f"  ERROR loading SDF baseline: {e}")
        return results

    # Merge with Data_modeller — BOTH have "controllable_cost_average" after rename,
    # so we use suffixes to disambiguate.
    merged = sdf_baseline.merge(
        dm[["REId", "controllable_cost_average"]],
        on="REId",
        how="inner",
        suffixes=("_sdf", "_dm")
    )
    print(f"  Merged: {len(merged)} companies")

    # Separate companies with and without Neo adjustments
    merged["has_neo"] = merged["neo_adjustments_period"].abs() > 0.01
    no_neo = merged[~merged["has_neo"]]
    with_neo = merged[merged["has_neo"]]

    print(f"\n  Companies WITHOUT neo adjustments: {len(no_neo)}")
    print(f"  Companies WITH neo adjustments: {len(with_neo)}")

    # For companies WITHOUT neo adjustments: are controllable_cost_average_sdf == controllable_cost_average_dm?
    if len(no_neo) > 0:
        no_neo = no_neo.copy()
        no_neo["diff"] = no_neo["controllable_cost_average_sdf"] - no_neo["controllable_cost_average_dm"]
        no_neo["rel_diff"] = no_neo["diff"] / no_neo["controllable_cost_average_dm"].clip(lower=1e-6)
        n_match = (no_neo["rel_diff"].abs() < TOLERANCE_PCT / 100).sum()
        max_diff = no_neo["diff"].abs().max()
        max_rel = no_neo["rel_diff"].abs().max()

        print(f"\n  WITHOUT neo adjustments: {n_match}/{len(no_neo)} exact matches")
        print(f"    Max abs diff: {max_diff:.2f} tkr")
        print(f"    Max rel diff: {max_rel:.4%}")

        # Show test companies
        for id_net, info in TEST_COMPANIES.items():
            reid = info["REId"]
            row = no_neo[no_neo["REId"] == reid]
            if not row.empty:
                row = row.iloc[0]
                print(f"    {reid}: SDF={row['controllable_cost_average_sdf']:.1f} | "
                      f"DM={row['controllable_cost_average_dm']:.1f} | diff={row['diff']:.1f}")

    # For companies WITH neo adjustments: what is the relationship?
    if len(with_neo) > 0:
        with_neo = with_neo.copy()
        with_neo["diff_raw"] = with_neo["controllable_cost_average_sdf"] - with_neo["controllable_cost_average_dm"]
        with_neo["diff_adjusted"] = (
            with_neo["controllable_cost_average_sdf"] +
            with_neo["neo_adjustments_period"] / 4 -
            with_neo["controllable_cost_average_dm"]
        )
        print(f"\n  WITH neo adjustments:")
        print(f"    Hypothesis: DM = SDF_avg + neo_adjustments_period/4 ?")
        n_match_adj = (with_neo["diff_adjusted"].abs() < 1.0).sum()
        print(f"    {n_match_adj}/{len(with_neo)} match (within 1 tkr)")

        # Show test companies with Neo
        for id_net, info in TEST_COMPANIES.items():
            reid = info["REId"]
            if not info["has_neo"]:
                continue
            row = with_neo[with_neo["REId"] == reid]
            if not row.empty:
                row = row.iloc[0]
                print(
                    f"    {reid}: SDF_avg={row['controllable_cost_average_sdf']:.1f} | "
                    f"Neo={row['neo_adjustments_period']:.1f} | "
                    f"SDF_avg+Neo/4={row['controllable_cost_average_sdf'] + row['neo_adjustments_period'] / 4:.1f} | "
                    f"DM={row['controllable_cost_average_dm']:.1f} | "
                    f"diff_adjusted={row['diff_adjusted']:.1f}"
                )

    # -------------------------------------------------------------------
    # 2b. Define controllable_cost_average precisely
    # -------------------------------------------------------------------
    print("\n--- 2b. controllable_cost_average definition analysis ---")

    # Check if values have .25 remainders (4-year mean of integers)
    remainder_25 = ((dm["controllable_cost_average"] * 4) % 1).abs()
    n_integer_sum = (remainder_25 < 0.01).sum()
    print(f"  controllable_cost_average * 4 is integer for {n_integer_sum}/{len(dm)} companies")
    print(f"  -> Suggests controllable_cost_average is likely a 4-year mean")

    # Check SDF Controllable sheet for "Antal ar" column
    print(f"\n  SDF Controllable sheet columns (looking for year count):")
    for col in sdf_ctrl.columns:
        col_lower = col.lower()
        if "antal" in col_lower or "ar" in col_lower or "year" in col_lower:
            print(f"    Found: '{col}'")
            vals = sdf_ctrl[col].dropna().unique()
            print(f"      Unique values: {sorted(vals)[:20]}")

    return results


# ============================================================================
# GROUP 3: Volume Variables
# ============================================================================

def group3_volume_variables(baseline):
    """Analyze volume variables (CU, MW, NS, MWhl, MWhh)."""
    print("\n" + "=" * 80)
    print("GROUP 3: VOLUME VARIABLES (CU, MW, NS, MWhl, MWhh)")
    print("=" * 80)

    dm = baseline.df_all_companies
    sdf_ir = baseline.sdf_ir
    results = []

    # -------------------------------------------------------------------
    # 3a. Source identification
    # -------------------------------------------------------------------
    print("\n--- 3a. Source identification ---")

    volume_cols = ["CU", "MW", "NS", "MWhl", "MWhh"]

    for col in volume_cols:
        vals = dm[col].dropna()
        print(f"\n  {col}:")
        print(f"    Count: {len(vals)}, Min: {vals.min():.2f}, Max: {vals.max():.2f}, "
              f"Mean: {vals.mean():.2f}")

        # Check for .25 remainders (4-year mean)
        remainder_25 = ((vals * 4) % 1).abs()
        n_int4 = (remainder_25 < 0.01).sum()
        pct_int4 = n_int4 / len(vals) * 100

        # Check for .5 remainders (2-value average)
        remainder_50 = ((vals * 2) % 1).abs()
        n_int2 = (remainder_50 < 0.01).sum()

        # Check if already integers
        remainder_1 = (vals % 1).abs()
        n_int1 = (remainder_1 < 0.01).sum()

        print(f"    Integer: {n_int1}/{len(vals)} ({n_int1 / len(vals) * 100:.0f}%)")
        print(f"    x4 is integer: {n_int4}/{len(vals)} ({pct_int4:.0f}%) -> 4-year mean?")
        print(f"    x2 is integer: {n_int2}/{len(vals)} ({n_int2 / len(vals) * 100:.0f}%) -> 2-year mean?")

    # Check SDF IR for per-year volume breakdowns
    print("\n  Searching SDF IR for volume-related columns:")
    for col in sdf_ir.columns:
        cl = col.lower()
        if any(kw in cl for kw in ["abonnent", "kund", "customer", "cu",
                                     "effekt", "mw", "natstation", "ns",
                                     "energi", "mwh", "leveran"]):
            print(f"    '{col}'")

    # Search SDF Controllable for volume info
    print("\n  Searching SDF Controllable for volume-related columns:")
    sdf_ctrl = baseline.sdf_controllable
    for col in sdf_ctrl.columns:
        cl = col.lower()
        if any(kw in cl for kw in ["abonnent", "kund", "cu", "effekt", "mw",
                                     "natstation", "ns", "energi", "mwh"]):
            print(f"    '{col}'")

    return results


# ============================================================================
# GROUP 4: DEA and Efficiency Variables
# ============================================================================

def group4_dea_efficiency(df_network, baseline):
    """Verify DEA and efficiency variables."""
    print("\n" + "=" * 80)
    print("GROUP 4: DEA AND EFFICIENCY VARIABLES")
    print("=" * 80)

    dm = baseline.df_all_companies
    dea = baseline.dea_results
    results = []

    # -------------------------------------------------------------------
    # 4a. DEA inputs
    # -------------------------------------------------------------------
    print("\n--- 4a. DEA inputs in Data_modeller ---")
    print("  Variables used as DEA inputs/outputs:")
    print(f"    capital_cost_2024 (was CAPEX): total capital cost for 2024")
    print(f"    controllable_cost_average (was OPEXp): controllable operating cost (historical average)")
    print(f"    CU, MW, NS, MWhl, MWhh: volume variables (outputs)")

    # Show summary stats
    for col in ["capital_cost_2024", "controllable_cost_average", "CU", "MW", "NS", "MWhl", "MWhh"]:
        if col in dm.columns:
            vals = dm[col].dropna()
            print(f"    {col}: mean={vals.mean():.1f}, sum={vals.sum():.1f}")

    # -------------------------------------------------------------------
    # 4b. Efficiency requirement from EIs_DEA
    # -------------------------------------------------------------------
    print("\n--- 4b. EIs_DEA Efficiency requirement ---")

    print(f"  Total companies: {len(dea)}")
    n_outlier = dea["is_outlier"].sum()
    print(f"  Outliers: {n_outlier}")

    if "efficiency_requirement_annual" in dea.columns:
        eff = dea[~dea["is_outlier"]]["efficiency_requirement_annual"]
        print(f"  efficiency_requirement_annual (non-outliers): min={eff.min():.4f}, "
              f"max={eff.max():.4f}, mean={eff.mean():.4f}")

        # Replicate efficiency requirement calculation
        print("\n  Replicating efficiency_requirement_annual from 'potential' column...")
        try:
            dea_with_eff = calculate_eff_req_for_dataframe(
                dea[["REId", "potential", "is_outlier"]].copy()
            )

            # Compare
            merged = dea[["REId", "efficiency_requirement_annual"]].merge(
                dea_with_eff[["REId", "efficiency_requirement_annual"]],
                on="REId",
                suffixes=("_eis", "_calc")
            )

            merged["diff"] = merged["efficiency_requirement_annual_calc"] - merged["efficiency_requirement_annual_eis"]
            max_diff = merged["diff"].abs().max()
            n_match = (merged["diff"].abs() < 1e-6).sum()

            print(f"  {n_match}/{len(merged)} exact matches")
            print(f"  Max difference: {max_diff:.8f}")

            if max_diff > 1e-4:
                worst = merged.loc[merged["diff"].abs().idxmax()]
                print(f"  Worst case: {worst['REId']} "
                      f"(EIs={worst['efficiency_requirement_annual_eis']:.6f}, "
                      f"Calc={worst['efficiency_requirement_annual_calc']:.6f})")

            # Show test companies
            for id_net, info in TEST_COMPANIES.items():
                reid = info["REId"]
                row = merged[merged["REId"] == reid]
                if not row.empty:
                    row = row.iloc[0]
                    print(f"  {reid}: EIs={row['efficiency_requirement_annual_eis']:.6f} | "
                          f"Calc={row['efficiency_requirement_annual_calc']:.6f} | "
                          f"diff={row['diff']:.8f}")
        except Exception as e:
            print(f"  ERROR replicating: {e}")

    return results


# ============================================================================
# GROUP 5: Revenue Frame Assembly
# ============================================================================

def group5_revenue_frame(df_network, baseline):
    """Verify revenue frame assembly matches SDF IR."""
    print("\n" + "=" * 80)
    print("GROUP 5: REVENUE FRAME ASSEMBLY")
    print("=" * 80)

    dm = baseline.df_all_companies
    sdf_ir = baseline.sdf_ir
    dea = baseline.dea_results
    results = []

    # -------------------------------------------------------------------
    # 5a. SDF IR verification: identify revenue frame column
    # -------------------------------------------------------------------
    print("\n--- 5a. SDF IR revenue frame verification ---")

    # Find revenue frame column — search for BOTH English (renamed) and Swedish patterns
    ir_col = None
    for c in sdf_ir.columns:
        cl = c.lower()
        # English patterns (after potential rename)
        if "revenue_frame" in cl:
            ir_col = c
            break
        # Swedish patterns (original SDF IR column names that may not be renamed)
        if "intaktsram" in cl or "intäktsram" in cl:
            ir_col = c
            break

    if ir_col:
        print(f"  Revenue frame column: '{ir_col}'")
    else:
        print(f"  WARNING: Could not find revenue frame column in SDF IR")

    # List all SDF IR columns with their sample values
    print("\n  SDF IR column inventory:")

    # Find REId column
    sdf_reid_col = None
    for c in sdf_ir.columns:
        if "reid" in c.lower() or "re-id" in c.lower():
            sdf_reid_col = c
            break
        sample = sdf_ir[c].astype(str).head(5)
        if sample.str.startswith("REL").any():
            sdf_reid_col = c
            break

    for i, c in enumerate(sdf_ir.columns):
        sample = sdf_ir[c].dropna()
        if len(sample) > 0:
            if pd.api.types.is_numeric_dtype(sample):
                print(f"  [{i}] '{c}' - numeric, mean={sample.mean():.1f}, sum={sample.sum():.1f}")
            else:
                print(f"  [{i}] '{c}' - {sample.dtype}, examples: {list(sample.head(3))}")
        else:
            print(f"  [{i}] '{c}' - all NaN")

    # Identify revenue frame components
    # Search for BOTH English (renamed) and Swedish (unrenamed) patterns
    print("\n  Looking for revenue frame components in SDF IR:")
    component_patterns = {
        # (English pattern, Swedish pattern, description)
        "capital_cost": ("capital_cost_period", "kapitalkostnad", "Capital cost (period sum)"),
        "controllable": ("controllable_cost_period", "påverkbara", "Controllable costs"),
        "non_controllable": ("non_controllable_cost_period", "opåverkbara", "Non-controllable costs"),
        "flexibility": ("flexibility_services_period", "flexibilitet", "Flexibility services"),
        "interruption": ("interruption_compensation_period", "avbrottsersättning", "Interruption compensation"),
        "state_deduction": ("state_subsidy_deduction_period", "statligt", "State subsidy deduction"),
        "revenue_frame": ("revenue_frame", "intäktsram", "Revenue frame total"),
    }

    for key, (eng_pattern, swe_pattern, desc) in component_patterns.items():
        matches = []
        for c in sdf_ir.columns:
            cl = c.lower()
            if eng_pattern in cl or swe_pattern in cl:
                matches.append(c)
        if matches:
            for m in matches:
                val = sdf_ir[m].dropna()
                if pd.api.types.is_numeric_dtype(val) and len(val) > 0:
                    print(f"    {desc}: '{m}' (sum={val.sum():.0f} tkr)")
                else:
                    print(f"    {desc}: '{m}'")
        else:
            print(f"    {desc}: NOT FOUND")

    # -------------------------------------------------------------------
    # 5b. Verify revenue frame = sum of components
    # -------------------------------------------------------------------
    if sdf_reid_col and ir_col:
        print(f"\n--- 5b. Verify revenue frame = sum of components ---")

        # Find component columns
        # Search for BOTH English (renamed) and Swedish (unrenamed) patterns
        comp_cols = {}
        for c in sdf_ir.columns:
            cl = c.lower()

            # Capital cost — English or Swedish
            if c == "capital_cost_period" or (
                "kapitalkostnad" in cl and "varav" not in cl and "avdrag" not in cl
                and "capital_cost" not in comp_cols
            ):
                comp_cols["capital_cost"] = c

            # Non-controllable — check BEFORE controllable (English or Swedish)
            elif c == "non_controllable_cost_period" or (
                ("opåverkbara" in cl or "opaverkbara" in cl)
                and "non_controllable" not in comp_cols
            ):
                comp_cols["non_controllable"] = c

            # Controllable — English or Swedish
            elif c == "controllable_cost_period" or (
                ("påverkbara" in cl or "paverkbara" in cl)
                and "varav" not in cl and "medel" not in cl
                and "controllable" not in comp_cols
                and "non_controllable" not in cl
            ):
                comp_cols["controllable"] = c

            # Flexibility — English or Swedish
            elif c == "flexibility_services_period" or (
                "flexibilitet" in cl and "flexibility" not in comp_cols
            ):
                comp_cols["flexibility"] = c

            # Interruption — English or Swedish
            elif c == "interruption_compensation_period" or (
                ("avbrottsersättning" in cl or "avbrottsersattning" in cl)
                and "interruption" not in comp_cols
            ):
                comp_cols["interruption"] = c

            # State deduction — English or Swedish
            elif c == "state_subsidy_deduction_period" or (
                "avdrag" in cl and ("statlig" in cl or "statligt" in cl)
                and "state_deduction" not in comp_cols
            ):
                comp_cols["state_deduction"] = c

        print(f"  Component columns found: {comp_cols}")

        # For test companies, try to verify sum
        for id_net, info in TEST_COMPANIES.items():
            reid = info["REId"]
            row = sdf_ir[sdf_ir[sdf_reid_col] == reid]
            if row.empty:
                continue
            row = row.iloc[0]

            total_ir = row[ir_col] if ir_col in row.index else None
            if pd.isna(total_ir):
                continue

            component_sum = 0
            detail_str = []
            for name, col in comp_cols.items():
                val = row[col]
                if pd.isna(val):
                    val = 0
                if name == "state_deduction":
                    component_sum += val  # already negative in data
                    detail_str.append(f"+{name}={val:.0f}")
                else:
                    component_sum += val
                    detail_str.append(f"+{name}={val:.0f}")

            diff = total_ir - component_sum
            print(f"\n  {reid}: IR_total={total_ir:.0f} | "
                  f"Sum_components={component_sum:.0f} | "
                  f"Residual={diff:.0f} tkr")
            print(f"    Components: {', '.join(detail_str)}")
            if abs(diff) > 1:
                print(f"    -> Residual likely = incentive adjustments ({diff:.0f} tkr)")

    return results


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("=" * 80)
    print("VARIABLE SPECIFICATION VERIFICATION SCRIPT")
    print("=" * 80)
    print(f"Tolerance: {TOLERANCE_PCT}% relative difference")
    print(f"WACC: {WACC}")
    print(f"Test companies: {list(TEST_COMPANIES.keys())}")

    # Load data
    capbase, baseline, capcost_a = load_all_data()

    # Run KENT
    df_detailed, df_network, df_category = run_kent(capbase)

    # Run all groups
    r1 = group1_capital_costs(df_network, df_category, baseline, capcost_a)
    r2 = group2_controllable_costs(baseline)
    r3 = group3_volume_variables(baseline)
    r4 = group4_dea_efficiency(df_network, baseline)
    r5 = group5_revenue_frame(df_network, baseline)

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    all_results = r1 + r2 + r3 + r4 + r5
    if all_results:
        n_ok = sum(1 for r in all_results if r.get("match", False))
        n_total = len(all_results)
        print(f"\n  Comparisons: {n_ok}/{n_total} within tolerance ({TOLERANCE_PCT}%)")

        mismatches = [r for r in all_results if not r.get("match", True)]
        if mismatches:
            print(f"\n  MISMATCHES ({len(mismatches)}):")
            for r in mismatches:
                print(f"    {r['label']}: diff={r['abs_diff']:+,.1f} tkr "
                      f"({r['rel_diff']:+.4%})")
    else:
        print("\n  (No numeric comparisons collected - check output above)")

    print("\n" + "=" * 80)
    print("DONE")
    print("=" * 80)


if __name__ == "__main__":
    main()

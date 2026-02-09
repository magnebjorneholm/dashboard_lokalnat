"""
verification_script.py

Test-driven variable specification & canonical naming.
Cross-references data sources to prove what each variable represents.

Uses capbase_a_mini.parquet (3 test companies) for speed.
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
    1: {"REId": "REL00001", "name": "Ale El ek. för.", "has_neo": False},
    886: {"REId": "REL00886", "name": "Kraftringen Nät AB", "has_neo": True},
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

        # Kapitalkostnad_2024 vs CAPEX
        r = compare("Kapitalkostnad_2024 vs CAPEX",
                     kent_row["Kapitalkostnad_2024"], dm_row["CAPEX"],
                     "KENT", "DM")
        if r:
            results.append(r)

        # Avskrivning_2024 vs Avskrivning
        r = compare("Avskrivning_2024 vs Avskrivning",
                     kent_row["Avskrivning_2024"], dm_row["Avskrivning"],
                     "KENT", "DM")
        if r:
            results.append(r)

        # Avkastning_2024 vs Avkastning
        r = compare("Avkastning_2024 vs Avkastning",
                     kent_row["Avkastning_2024"], dm_row["Avkastning"],
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
            col = f"Avkastning_{year}"
            if col in dm_row.index:
                r = compare(col, kent_row[col], dm_row[col], "KENT", "DM")
                if r:
                    results.append(r)

        # Period sum
        r = compare("Avkastning_Period",
                     kent_row["Avkastning_Period"], dm_row["Avkastning_Period"],
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
    sdf_capcost_col = None
    sdf_dep_col = None
    sdf_return_col = None

    for c in sdf_ir.columns:
        cl = c.lower().strip()
        if "kapitalkostnad" in cl and "varav" not in cl:
            sdf_capcost_col = c
        if ("kapitalförslitning" in cl or "kapital-förslitning" in cl or
                "kapitalforslitning" in cl):
            sdf_dep_col = c
        if ("kapitalbindning" in cl or "kapital-bindning" in cl):
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

            # Kapitalkostnad_Period vs SDF Kapitalkostnad
            if sdf_capcost_col:
                r = compare("Kapitalkostnad_Period vs SDF",
                            kent_row["Kapitalkostnad_Period"],
                            sdf_row[sdf_capcost_col],
                            "KENT", "SDF_IR")
                if r:
                    results.append(r)

            # Avskrivning_Period vs SDF depreciation
            if sdf_dep_col:
                r = compare("Avskrivning_Period vs SDF",
                            kent_row["Avskrivning_Period"],
                            sdf_row[sdf_dep_col],
                            "KENT", "SDF_IR")
                if r:
                    results.append(r)

            # Avkastning_Period vs SDF return
            if sdf_return_col:
                r = compare("Avkastning_Period vs SDF",
                            kent_row["Avkastning_Period"],
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
    print("GROUP 2: CONTROLLABLE COST VARIABLES (OPEXp)")
    print("=" * 80)

    dm = baseline.df_all_companies
    sdf_ir = baseline.sdf_ir
    sdf_ctrl = baseline.sdf_controllable
    results = []

    # -------------------------------------------------------------------
    # 2a. SDF Påverkbara vs Data_modeller
    # -------------------------------------------------------------------
    print("\n--- 2a. SDF Påverkbara (average) vs Data_modeller OPEXp ---")

    # Get controllable baseline from SDF
    try:
        sdf_baseline = get_controllable_from_sdf(sdf_ir, sdf_ctrl)
        print(f"  SDF baseline loaded: {len(sdf_baseline)} companies")
        print(f"  Columns: {list(sdf_baseline.columns)}")
    except Exception as e:
        print(f"  ERROR loading SDF baseline: {e}")
        return results

    # Merge with Data_modeller
    merged = sdf_baseline.merge(dm[["REId", "OPEXp"]], on="REId", how="inner")
    print(f"  Merged: {len(merged)} companies")

    # Separate companies with and without NeoÄndringar
    merged["has_neo"] = merged["Neonjusteringar"].abs() > 0.01
    no_neo = merged[~merged["has_neo"]]
    with_neo = merged[merged["has_neo"]]

    print(f"\n  Companies WITHOUT NeoÄndringar: {len(no_neo)}")
    print(f"  Companies WITH NeoÄndringar: {len(with_neo)}")

    # For companies WITHOUT NeoÄndringar: are Paverkbara_Medelvarde == OPEXp?
    if len(no_neo) > 0:
        no_neo = no_neo.copy()
        no_neo["diff"] = no_neo["Paverkbara_Medelvarde"] - no_neo["OPEXp"]
        no_neo["rel_diff"] = no_neo["diff"] / no_neo["OPEXp"].clip(lower=1e-6)
        n_match = (no_neo["rel_diff"].abs() < TOLERANCE_PCT / 100).sum()
        max_diff = no_neo["diff"].abs().max()
        max_rel = no_neo["rel_diff"].abs().max()

        print(f"\n  WITHOUT NeoÄndringar: {n_match}/{len(no_neo)} exact matches")
        print(f"    Max abs diff: {max_diff:.2f} tkr")
        print(f"    Max rel diff: {max_rel:.4%}")

        # Show test companies
        for id_net, info in TEST_COMPANIES.items():
            reid = info["REId"]
            row = no_neo[no_neo["REId"] == reid]
            if not row.empty:
                row = row.iloc[0]
                print(f"    {reid}: SDF={row['Paverkbara_Medelvarde']:.1f} | "
                      f"DM_OPEXp={row['OPEXp']:.1f} | diff={row['diff']:.1f}")

    # For companies WITH NeoÄndringar: what is the relationship?
    if len(with_neo) > 0:
        with_neo = with_neo.copy()
        with_neo["diff_raw"] = with_neo["Paverkbara_Medelvarde"] - with_neo["OPEXp"]
        with_neo["diff_adjusted"] = (
            with_neo["Paverkbara_Medelvarde"] +
            with_neo["Neonjusteringar"] / 4 -
            with_neo["OPEXp"]
        )
        print(f"\n  WITH NeoÄndringar:")
        print(f"    Hypothesis: OPEXp = Paverkbara_Medelvarde + NeoÄndringar/4 ?")
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
                    f"    {reid}: SDF_avg={row['Paverkbara_Medelvarde']:.1f} | "
                    f"Neo={row['Neonjusteringar']:.1f} | "
                    f"SDF_avg+Neo/4={row['Paverkbara_Medelvarde'] + row['Neonjusteringar'] / 4:.1f} | "
                    f"DM_OPEXp={row['OPEXp']:.1f} | "
                    f"diff_adjusted={row['diff_adjusted']:.1f}"
                )

    # -------------------------------------------------------------------
    # 2b. Define OPEXp precisely
    # -------------------------------------------------------------------
    print("\n--- 2b. OPEXp definition analysis ---")

    # Check if values have .25 remainders (4-year mean of integers)
    remainder_25 = ((dm["OPEXp"] * 4) % 1).abs()
    n_integer_sum = (remainder_25 < 0.01).sum()
    print(f"  OPEXp * 4 is integer for {n_integer_sum}/{len(dm)} companies")
    print(f"  -> Suggests OPEXp is likely a 4-year mean")

    # Check SDF Påverkbara sheet for "Antal år" column
    print(f"\n  SDF Controllable sheet columns (looking for year count):")
    for col in sdf_ctrl.columns:
        col_lower = col.lower()
        if "antal" in col_lower or "år" in col_lower or "year" in col_lower:
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
                                     "effekt", "mw", "nätstation", "ns",
                                     "energi", "mwh", "leveran"]):
            print(f"    '{col}'")

    # Search SDF Controllable for volume info
    print("\n  Searching SDF Controllable for volume-related columns:")
    sdf_ctrl = baseline.sdf_controllable
    for col in sdf_ctrl.columns:
        cl = col.lower()
        if any(kw in cl for kw in ["abonnent", "kund", "cu", "effekt", "mw",
                                     "nätstation", "ns", "energi", "mwh"]):
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
    print(f"    CAPEX (= Kapitalkostnad_2024): total capital cost for 2024")
    print(f"    OPEXp: controllable operating cost (historical average)")
    print(f"    CU, MW, NS, MWhl, MWhh: volume variables (outputs)")

    # Show summary stats
    for col in ["CAPEX", "OPEXp", "CU", "MW", "NS", "MWhl", "MWhh"]:
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

    if "Effkrav_proc" in dea.columns:
        eff = dea[~dea["is_outlier"]]["Effkrav_proc"]
        print(f"  Effkrav_proc (non-outliers): min={eff.min():.4f}, "
              f"max={eff.max():.4f}, mean={eff.mean():.4f}")

        # Replicate efficiency requirement calculation
        print("\n  Replicating Effkrav_proc from 'potential' column...")
        try:
            dea_with_eff = calculate_eff_req_for_dataframe(
                dea[["REId", "potential", "is_outlier"]].copy()
            )

            # Compare
            merged = dea[["REId", "Effkrav_proc"]].merge(
                dea_with_eff[["REId", "Effkrav_proc"]],
                on="REId",
                suffixes=("_eis", "_calc")
            )

            merged["diff"] = merged["Effkrav_proc_calc"] - merged["Effkrav_proc_eis"]
            max_diff = merged["diff"].abs().max()
            n_match = (merged["diff"].abs() < 1e-6).sum()

            print(f"  {n_match}/{len(merged)} exact matches")
            print(f"  Max difference: {max_diff:.8f}")

            if max_diff > 1e-4:
                worst = merged.loc[merged["diff"].abs().idxmax()]
                print(f"  Worst case: {worst['REId']} "
                      f"(EIs={worst['Effkrav_proc_eis']:.6f}, "
                      f"Calc={worst['Effkrav_proc_calc']:.6f})")

            # Show test companies
            for id_net, info in TEST_COMPANIES.items():
                reid = info["REId"]
                row = merged[merged["REId"] == reid]
                if not row.empty:
                    row = row.iloc[0]
                    print(f"  {reid}: EIs={row['Effkrav_proc_eis']:.6f} | "
                          f"Calc={row['Effkrav_proc_calc']:.6f} | "
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
    # 5a. SDF IR verification: identify intäktsram column
    # -------------------------------------------------------------------
    print("\n--- 5a. SDF IR revenue frame verification ---")

    # Find intäktsram column
    ir_col = None
    for c in sdf_ir.columns:
        if "intäktsram" in c.lower() or "intaktsram" in c.lower():
            ir_col = c
            break

    if ir_col:
        print(f"  Revenue frame column: '{ir_col}'")
    else:
        print(f"  WARNING: Could not find intäktsram column in SDF IR")

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
    print("\n  Looking for revenue frame components in SDF IR:")
    component_patterns = {
        "Kapitalkostnad": "Capital cost (period sum)",
        "Påverkbara": "Controllable costs",
        "Opåverkbara": "Non-controllable costs",
        "Flexibilitet": "Flexibility services",
        "Avbrottsersättning": "Interruption compensation",
        "Statligt": "State subsidy deduction",
        "Intäktsram": "Revenue frame total",
    }

    for pattern, desc in component_patterns.items():
        matches = [c for c in sdf_ir.columns if pattern.lower() in c.lower()]
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
    # 5b. Verify Intäktsram = sum of components
    # -------------------------------------------------------------------
    if sdf_reid_col and ir_col:
        print(f"\n--- 5b. Verify Intäktsram = sum of components ---")

        # Find component columns (order matters: check opåverkbara BEFORE påverkbara)
        comp_cols = {}
        for c in sdf_ir.columns:
            cl = c.lower()
            if "kapitalkostnad" in cl and "varav" not in cl and "avdrag" not in cl:
                comp_cols["capital_cost"] = c
            elif "opåverkbara" in cl or "opaverkbara" in cl:
                comp_cols["non_controllable"] = c
            elif ("påverkbara" in cl or "paverkbara" in cl) and "varav" not in cl and "medel" not in cl:
                comp_cols["controllable"] = c
            elif "flexibilitet" in cl:
                comp_cols["flexibility"] = c
            elif "avbrottsersättning" in cl or "avbrottsersattning" in cl:
                comp_cols["interruption"] = c
            elif "avdrag" in cl and ("statlig" in cl or "statligt" in cl):
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

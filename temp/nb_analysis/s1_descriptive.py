"""
s1_descriptive.py — Step 1 (bundle, instant): build and validate the analysis spine.

Per temp/PLAN.md step 1. Builds `analysis_df` (one row per REId) and persists it.
No scatters, no figures — output is the table only; validation prints to stdout.

Run cell-by-cell in VSCode (# %%), or as a script:
    .venv/bin/python temp/nb_analysis/s1_descriptive.py
"""

# %% build the spine
from _helpers import load_analysis_df, OUT_DIR
from new_benchmarking_model.config import EI_DEA_EXCLUDED_REIDS

df = load_analysis_df()

# %% validate (definition of done: 148 rows, NaN only where meaningful)
OUT_DIR.mkdir(parents=True, exist_ok=True)
df.to_csv(OUT_DIR / "analysis_df.csv", index=False)

print(f"analysis_df: {len(df)} rows, {len(df.columns)} cols")
print(f"  REId unique: {df['REId'].is_unique}")
print(f"  saved: {OUT_DIR / 'analysis_df.csv'}")

# Row-aware NaN check. Every NaN must be explained by one of three known causes:
#   1. REId in EI_DEA_EXCLUDED_REIDS — excluded from the DEA (both models), so ALL
#      outcome columns (eff/req/kr/rank/gap/kind/deltas) are NaN by design.
#   2. cable_*/station_* — company has no förläggningsmiljö adjustment of that kind.
#   3. capex_cut_pct — REL00024 has capex_unadj=0 (source anomaly), pct set NaN not -inf.
# A NaN that fits none of these is a real defect.
excluded = set(EI_DEA_EXCLUDED_REIDS)
env_cols = {"cable_ded", "cable_eff_pct", "station_ded", "station_eff_pct"}

unexplained = []
for col in df.columns:
    for _, row in df[df[col].isna()].iterrows():
        if row["REId"] in excluded:
            continue                                  # cause 1
        if col in env_cols:
            continue                                  # cause 2
        if col == "capex_cut_pct" and row["capex_unadj"] == 0:
            continue                                  # cause 3
        unexplained.append((col, row["REId"]))

nan_counts = df.isna().sum()
print("\nNaN by column:")
for col, n in nan_counts[nan_counts > 0].items():
    print(f"  {col:16s} {n:3d}")
print(f"\nexcluded firms (NaN outcomes by design): {sorted(excluded)}")
print(f"DoD NaN check: {'PASS — all NaN explained' if not unexplained else 'FAIL: ' + str(unexplained)}")

# Cheap sanity checks on the key reconstructed quantities.
print("\nsanity:")
print(f"  cable_length_km > 0 for all: {(df['cable_length_km'] > 0).all()}")
# capex_cut >= 0 everywhere EXCEPT REL00024 (capex_unadj=0, capex_adj>0 source anomaly).
_capex_cut_neg = df[df['capex_cut'] < -1e-6]['REId'].tolist()
print(f"  capex_cut < 0 only at:       {_capex_cut_neg}  (expected: REL00024 anomaly)")
print(f"  e75 constant across rows:    {df['e75'].nunique() == 1}  (E75 = {df['e75'].iloc[0]:.4f})")
print(f"  kind ∈ reward/deduction/coverage: {set(df['kind'].dropna().unique())}")
print(f"  total cable_length_km: {df['cable_length_km'].sum():,.0f} km")

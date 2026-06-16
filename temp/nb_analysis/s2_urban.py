"""
s2_urban.py — Step 2 (light live): urban proxies + validation.

Per temp/PLAN.md step 2. Builds three urban measures on the analysis spine and runs
two independent validation tests of the "luftledning = landsbygd" assumption. No DEA,
no KENT — only capbase reads + the jordkabel calibration. Output is tables only.

    .venv/bin/python temp/nb_analysis/s2_urban.py
"""

# %% build spine + urban proxies
import pandas as pd

from _helpers import load_analysis_df, add_urban_proxies, urban_weights, OUT_DIR

df = add_urban_proxies(load_analysis_df(), basis="percent")
OUT_DIR.mkdir(parents=True, exist_ok=True)
df.to_csv(OUT_DIR / "analysis_df.csv", index=False)

w_city, w_tatort = urban_weights("percent")
w_city_s, w_tatort_s = urban_weights("sek_per_km")
print(f"urban weights — percent:    w_city={w_city:.3f}  w_tatort={w_tatort:.3f}")
print(f"urban weights — sek_per_km: w_city={w_city_s:.3f}  w_tatort={w_tatort_s:.3f}  (sensitivity)")

for col in ["density_cu_km", "jordkabel_share", "urbanity_index"]:
    s = df[col]
    print(f"  {col:18s} min {s.min():.3f}  median {s.median():.3f}  max {s.max():.3f}")

# %% correlation matrix: 3 measures + the dose (capex_cut_pct, cable_eff_pct)
corr_cols = ["density_cu_km", "jordkabel_share", "urbanity_index", "capex_cut_pct", "cable_eff_pct"]
pearson = df[corr_cols].corr(method="pearson")
spearman = df[corr_cols].corr(method="spearman")
pearson.to_csv(OUT_DIR / "s2_urban_corr.csv")
spearman.to_csv(OUT_DIR / "s2_urban_corr_spearman.csv")
print("\nPearson correlation (3 measures + dose):")
print(pearson.round(3).to_string())

# %% validation — two independent triangulations of luftledning = rural
#   A: does luftledning-share covary with the jordkabel landsbygd-share? (expect +)
#   B: do luftledning-heavy companies have low CU density?              (expect -)
def _corr(a, b, method):
    pair = df[[a, b]].dropna()
    return pair[a].corr(pair[b], method=method), len(pair)

rows = []
for name, a, b, expect in [
    ("A: luftledning_share vs jordkabel_landsbygd_share", "luftledning_share", "jordkabel_landsbygd_share", "positive"),
    ("B: luftledning_share vs density_cu_km", "luftledning_share", "density_cu_km", "negative"),
]:
    pe, n = _corr(a, b, "pearson")
    sp, _ = _corr(a, b, "spearman")
    consistent = (pe > 0) == (expect == "positive")
    rows.append({
        "test": name, "expect": expect, "pearson": round(pe, 3),
        "spearman": round(sp, 3), "n": n, "consistent_with_expectation": consistent,
    })

validation = pd.DataFrame(rows)
validation.to_csv(OUT_DIR / "s2_validation.csv", index=False)
print("\nValidation (luftledning = rural):")
print(validation.to_string(index=False))

print(f"\nsaved: analysis_df.csv, s2_urban_corr.csv, s2_urban_corr_spearman.csv, s2_validation.csv")

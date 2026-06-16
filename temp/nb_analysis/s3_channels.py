"""
s3_channels.py — Step 3 (heavy live, ~2 DEA): two-channel isolation.

Per temp/PLAN.md step 3. Isolates the two opposing channels and projects each on the
urban axis. The full model is read from the bundle (it IS the default spec); only the
two channel-off variants are run live.

  Channel A — capex env-adjustment OFF: input = totex_unadj (opex_new + capex_unadj).
  Channel B — cable-length output OFF:  outputs = base only (drop cable_length_km).

Per-firm channel contribution phi = req(WITH channel) − req(WITHOUT) [convention (a)]:
"with" = full model, "without" = the channel-off variant. phi < 0 means the channel
lowers that firm's requirement, i.e. FAVOURS it. Slope vs urbanity: expect channel A
negative (favours urban → more negative as urbanity rises), channel B positive (favours
rural), and the full-model req level near-flat if the two cancel.

NOTE: the OLS slope is the point estimate; its naive t-CI is anti-conservative because it
ignores DEA-induced cross-sectional dependence. The valid CI comes from s3_inference.py
(DEA-aware subsampling), which augments s3_slopes.csv with boot_ci_low/high. Read those.

    .venv/bin/python temp/nb_analysis/s3_channels.py
"""

# %% setup — spine (full model from bundle) + the two variants
import pandas as pd
from scipy import stats

from _helpers import (
    load_analysis_df, add_urban_proxies, run_variant, OUT_DIR,
    NEW_MODEL_BASE_OUTPUTS,
)
from config.column_names import COL_CABLE_LENGTH_KM

spine = add_urban_proxies(load_analysis_df(), basis="percent")

base_outputs = list(NEW_MODEL_BASE_OUTPUTS)
full_outputs = base_outputs + [COL_CABLE_LENGTH_KM]

# Full model = bundle (req_new_pct, kr_new already on the spine).
full = spine[["REId", "name_short", "urbanity_index", "req_new_pct", "kr_new"]].rename(
    columns={"req_new_pct": "req_full", "kr_new": "kr_full"})

# Channel A off: env-unadjusted capex input, cable output kept.
offA = run_variant(spine, "totex_unadj", full_outputs).rename(
    columns={"eff": "eff_offA", "req": "req_offA", "kr": "kr_offA"})
# Channel B off: env-adjusted TOTEX input, cable output dropped.
offB = run_variant(spine, "totex_new", base_outputs).rename(
    columns={"eff": "eff_offB", "req": "req_offB", "kr": "kr_offB"})

# %% per-firm channel contribution phi = req(with) − req(without)  [convention (a)]
# phi < 0  ->  channel lowers the requirement  ->  favours that firm.
ch = full.merge(offA, on="REId").merge(offB, on="REId")
ch["dA_pp"] = (ch["req_full"] - ch["req_offA"]) * 100.0
ch["dB_pp"] = (ch["req_full"] - ch["req_offB"]) * 100.0
ch["dA_kr"] = ch["kr_full"] - ch["kr_offA"]
ch["dB_kr"] = ch["kr_full"] - ch["kr_offB"]
ch["req_full_pp"] = ch["req_full"] * 100.0   # net level, same pp units as the channel deltas

OUT_DIR.mkdir(parents=True, exist_ok=True)
ch.to_csv(OUT_DIR / "s3_channels.csv", index=False)

# %% OLS slopes vs urbanity (indicative CI; see open-question note)
def ols(y_col, x_col="urbanity_index"):
    pair = ch[[x_col, y_col]].dropna()
    r = stats.linregress(pair[x_col], pair[y_col])
    tcrit = stats.t.ppf(0.975, len(pair) - 2)
    return {
        "slope": r.slope, "ci_low": r.slope - tcrit * r.stderr,
        "ci_high": r.slope + tcrit * r.stderr, "r2": r.rvalue ** 2,
        "p": r.pvalue, "n": len(pair),
    }

# Slopes are on the requirement in percentage points only. The kr versions are dropped
# from the regression: kr scales with firm size, so regressing Δkr on urbanity is
# heteroskedastic and uninformative. Per-firm Δkr stays in s3_channels.csv as raw data.
slopes = []
for label, y, expect in [
    ("A: capex-adj (phi pp)", "dA_pp", "negative"),     # favours urban -> more negative as urbanity rises
    ("B: cable-length (phi pp)", "dB_pp", "positive"),  # favours rural -> less negative as urbanity rises
    ("net: full model (req level, pp/urb)", "req_full_pp", "≈ flat"),
]:
    res = ols(y)
    direction = "positive" if res["slope"] > 0 else "negative"
    consistent = (expect == direction) if expect in ("positive", "negative") else "—"
    slopes.append({"channel": label, "expect": expect, **{k: round(v, 4) for k, v in res.items()}, "consistent": consistent})

slopes_df = pd.DataFrame(slopes)
slopes_df.to_csv(OUT_DIR / "s3_slopes.csv", index=False)

# %% report
print("=== aggregate channel contribution (tkr, 4-yr period; with − without) ===")
print(f"  Σ dA_kr (capex-adj):    {ch['dA_kr'].sum():>14,.0f}  (<0 = lowers aggregate req)")
print(f"  Σ dB_kr (cable-length): {ch['dB_kr'].sum():>14,.0f}")
print(f"  median |dA_pp| {ch['dA_pp'].abs().median():.3f}   median |dB_pp| {ch['dB_pp'].abs().median():.3f}")

print("\n=== OLS slopes vs urbanity_index (indicative) ===")
print(slopes_df.to_string(index=False))
print(f"\nsaved: s3_channels.csv, s3_slopes.csv")

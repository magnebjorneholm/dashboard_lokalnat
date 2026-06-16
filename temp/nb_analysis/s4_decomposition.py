"""
s4_decomposition.py — Step 4 (heavy live, ~9 DEA): leave-one-out + add-one-in.

Per temp/PLAN.md step 4. Ranks the four cost-component players by their marginal effect
on the two-sided requirement, from both ends:

  Players: losses@common-price, selected non-controllable, förläggningsmiljö capex
           adjustment, cable-length output. (The two-sided vs legacy mechanic is held
           out — see PLAN open question.)

  full TOTEX input = controllable + losses + nonctrl + capex_adj   (+ cable output)
  bare baseline    = controllable + capex_unadj                    (all players off)

  LOO(player) = req(full) − req(full without player)      marginal at the full context
  AOI(player) = req(baseline + player) − req(baseline)    marginal at the empty context

DEA is non-linear, so LOO and AOI do NOT sum to the full−baseline total — they are the
two endpoints that bracket each player's effect, and their gap is the interaction signal
that motivates Shapley (step 5). Analysis is in percentage points; per-firm Δkr is kept
as raw data only (kr scales with size — no regression on it).

    .venv/bin/python temp/nb_analysis/s4_decomposition.py
"""

# %% setup — spine + composed input columns
import pandas as pd

from _helpers import load_analysis_df, run_variant, OUT_DIR, NEW_MODEL_BASE_OUTPUTS
from config.column_names import COL_CABLE_LENGTH_KM
from new_benchmarking_model.ui.charts import outcome_kind

s = load_analysis_df()

# Composed DEA inputs (pure arithmetic on the spine; totex_new = controllable + losses
# + nonctrl + capex_adj, totex_unadj swaps capex_adj -> capex_unadj).
s["in_full"] = s["totex_new"]
s["in_loo_losses"] = s["totex_new"] - s["loss_valued"]
s["in_loo_nonctrl"] = s["totex_new"] - s["nonctrl_selected"]
s["in_loo_capex"] = s["totex_unadj"]                          # = opex_new + capex_unadj
s["in_base"] = s["controllable"] + s["capex_unadj"]          # all players off
s["in_aoi_losses"] = s["in_base"] + s["loss_valued"]
s["in_aoi_nonctrl"] = s["in_base"] + s["nonctrl_selected"]
s["in_aoi_capex"] = s["controllable"] + s["capex_adj"]        # baseline w/ capex adjusted

base_out = list(NEW_MODEL_BASE_OUTPUTS)
full_out = base_out + [COL_CABLE_LENGTH_KM]

PLAYERS = ["losses", "nonctrl", "capex_adj", "cable"]

# full model = bundle; bare baseline = one live run.
full = s[["REId", "req_new_pct", "kr_new"]].rename(columns={"req_new_pct": "req", "kr_new": "kr"})
base = run_variant(s, "in_base", base_out)

# %% leave-one-out: full minus each player
loo_spec = {
    "losses": ("in_loo_losses", full_out),
    "nonctrl": ("in_loo_nonctrl", full_out),
    "capex_adj": ("in_loo_capex", full_out),
    "cable": ("in_full", base_out),
}
loo = s[["REId", "name_short"]].copy()
loo["req_full_pp"] = full["req"] * 100.0
for p, (incol, outs) in loo_spec.items():
    v = run_variant(s, incol, outs).set_index("REId")
    loo[f"dpp_{p}"] = (full.set_index("REId")["req"] - v["req"]).reindex(loo["REId"]).values * 100.0
    loo[f"dkr_{p}"] = (full.set_index("REId")["kr"] - v["kr"]).reindex(loo["REId"]).values
    loo[f"kind_{p}"] = v["req"].reindex(loo["REId"]).map(outcome_kind).values

# %% add-one-in: baseline plus each player
aoi_spec = {
    "losses": ("in_aoi_losses", base_out),
    "nonctrl": ("in_aoi_nonctrl", base_out),
    "capex_adj": ("in_aoi_capex", base_out),
    "cable": ("in_base", full_out),
}
aoi = s[["REId", "name_short"]].copy()
aoi["req_base_pp"] = base.set_index("REId")["req"].reindex(aoi["REId"]).values * 100.0
for p, (incol, outs) in aoi_spec.items():
    v = run_variant(s, incol, outs).set_index("REId")
    aoi[f"dpp_{p}"] = (v["req"] - base.set_index("REId")["req"]).reindex(aoi["REId"]).values * 100.0
    aoi[f"dkr_{p}"] = (v["kr"] - base.set_index("REId")["kr"]).reindex(aoi["REId"]).values

OUT_DIR.mkdir(parents=True, exist_ok=True)
loo.to_csv(OUT_DIR / "s4_loo.csv", index=False)
aoi.to_csv(OUT_DIR / "s4_aoi.csv", index=False)

# %% ranking — median |Δ pp| (primary), kind-flip share, Σ|Δ kr| (descriptive)
kind_full = full.set_index("REId")["req"].map(outcome_kind)
rows = []
for p in PLAYERS:
    loo_flip = (loo.set_index("REId")[f"kind_{p}"] != kind_full).reindex(loo["REId"]).values
    valid = loo[f"dpp_{p}"].notna().values
    rows.append({
        "player": p,
        "loo_median_abs_pp": round(loo[f"dpp_{p}"].abs().median(), 4),
        "aoi_median_abs_pp": round(aoi[f"dpp_{p}"].abs().median(), 4),
        "loo_kind_flip_share": round((pd.Series(loo_flip) & pd.Series(valid)).sum() / valid.sum(), 3),
        "loo_sum_abs_kr": round(loo[f"dkr_{p}"].abs().sum(), 0),   # descriptive only
        "aoi_sum_abs_kr": round(aoi[f"dkr_{p}"].abs().sum(), 0),
    })
ranking = pd.DataFrame(rows).sort_values("loo_median_abs_pp", ascending=False).reset_index(drop=True)
ranking.to_csv(OUT_DIR / "s4_ranking.csv", index=False)

# %% report
print("Player ranking by marginal effect on the requirement (pp):")
print(ranking.to_string(index=False))
print("\nLOO vs AOI median |Δ pp| (gap = interaction signal → motivates Shapley):")
for p in PLAYERS:
    lo = loo[f"dpp_{p}"].abs().median()
    ai = aoi[f"dpp_{p}"].abs().median()
    print(f"  {p:10s} LOO {lo:6.3f}   AOI {ai:6.3f}   gap {abs(lo-ai):6.3f}")
print(f"\nsaved: s4_loo.csv, s4_aoi.csv, s4_ranking.csv")

"""
s5_shapley.py — Step 5 (heavy live, 16 DEA): Shapley attribution.

Per temp/PLAN.md step 5. The watertight additive split of the requirement across the
four cost-component players, exact despite DEA non-linearity:

    phi_k = Σ_{S ⊆ N\\{k}} w(|S|) · [ v(S ∪ k) − v(S) ]          (convention (a))
    w(s)  = s!·(n−s−1)! / n!
    Σ_k phi_k = v(N) − v(∅)   exactly, per company.

v(S) = the firm's signed annual requirement (pp) when only the players in S are on.
Convention (a): phi_k = req(with k) − req(without k); phi_k < 0 means player k LOWERS
the requirement, i.e. FAVOURS the firm. Players: losses, nonctrl, capex_adj, cable.

The mechanic switch (two-sided E75 vs legacy front-reference) is held OUT of the players
and surfaced separately as the residual v(∅) − req_current (structural + mechanic).

    .venv/bin/python new_benchmarking_model/analysis/s5_shapley.py
"""

# %% setup
from itertools import combinations
from math import factorial

import pandas as pd

from _helpers import load_analysis_df, run_variant, OUT_DIR, NEW_MODEL_BASE_OUTPUTS
from config.column_names import COL_CABLE_LENGTH_KM

s = load_analysis_df()
base_out = list(NEW_MODEL_BASE_OUTPUTS)
PLAYERS = ["losses", "nonctrl", "capex_adj", "cable"]
N = len(PLAYERS)


def subset_input(spine, S):
    """DEA input column for player-subset S (pure arithmetic on the spine)."""
    inp = spine["controllable"].copy()
    if "losses" in S:
        inp = inp + spine["loss_valued"]
    if "nonctrl" in S:
        inp = inp + spine["nonctrl_selected"]
    inp = inp + (spine["capex_adj"] if "capex_adj" in S else spine["capex_unadj"])
    return inp


def all_subsets(items):
    for r in range(len(items) + 1):
        for c in combinations(items, r):
            yield frozenset(c)


# %% value function: req (pp) for every one of the 2^4 subsets
V = {}
for S in all_subsets(PLAYERS):
    frame = s.copy()
    frame["_inp"] = subset_input(s, S)
    outs = base_out + ([COL_CABLE_LENGTH_KM] if "cable" in S else [])
    v = run_variant(frame, "_inp", outs).set_index("REId")
    V[S] = v["req"] * 100.0   # pp

empty, full = frozenset(), frozenset(PLAYERS)
idx = V[empty].index

# cross-checks: V(full) == bundle new model, V(∅) == bare baseline
chk_full = (V[full] - s.set_index("REId")["req_new_pct"] * 100.0).abs().max()
print(f"cross-check V(full) vs bundle req_new: max |Δ pp| = {chk_full:.2e}")

# %% Shapley values per company
w = {ssize: factorial(ssize) * factorial(N - ssize - 1) / factorial(N) for ssize in range(N)}
phi = {p: pd.Series(0.0, index=idx) for p in PLAYERS}
for p in PLAYERS:
    for S in all_subsets([x for x in PLAYERS if x != p]):
        phi[p] = phi[p] + w[len(S)] * (V[S | {p}] - V[S])

sum_phi = sum(phi.values())
total = V[full] - V[empty]
identity_err = (sum_phi - total).abs().max()
print(f"Shapley identity  Σφ == v(N)−v(∅):  max |residual pp| = {identity_err:.2e}")

# %% per-company table + residual vs the actual current model
per = s[["REId", "name_short"]].copy().set_index("REId")
per["v_empty_pp"] = V[empty]
per["v_full_pp"] = V[full]
for p in PLAYERS:
    per[f"phi_{p}"] = phi[p]
per["sum_phi"] = sum_phi
# residual = our two-sided baseline minus Ei's published current (mechanic + structural)
per["residual_vs_current_pp"] = V[empty] - s.set_index("REId")["req_cur_pct"] * 100.0
per = per.reset_index()
OUT_DIR.mkdir(parents=True, exist_ok=True)
per.to_csv(OUT_DIR / "s5_shapley_percompany.csv", index=False)

# %% sector synthesis: mean signed phi, mean |phi|, dominance share
phi_df = pd.DataFrame({p: phi[p] for p in PLAYERS}).dropna()
dominant = phi_df.abs().idxmax(axis=1)
rows = []
for p in PLAYERS:
    rows.append({
        "player": p,
        "mean_phi_pp": round(phi_df[p].mean(), 4),       # signed: <0 favours firms on average
        "mean_abs_phi_pp": round(phi_df[p].abs().mean(), 4),
        "share_dominant": round((dominant == p).mean(), 3),
        "n_favoured(phi<0)": int((phi_df[p] < 0).sum()),
        "n_penalised(phi>0)": int((phi_df[p] > 0).sum()),
    })
summary = pd.DataFrame(rows).sort_values("mean_abs_phi_pp", ascending=False).reset_index(drop=True)
summary.to_csv(OUT_DIR / "s5_shapley_summary.csv", index=False)

# %% report
print("\nSector synthesis (phi in pp; phi<0 = player lowers requirement = favours firm):")
print(summary.to_string(index=False))
print(f"\nresidual v(∅) − current: median {per['residual_vs_current_pp'].median():.3f} pp"
      f"  (mechanic switch + structural; held out of the players)")
print(f"\nsaved: s5_shapley_percompany.csv, s5_shapley_summary.csv")


# %% ===========================================================================
# Residual decomposition: split v(∅) − current into mechanic vs input structure.
#
# The residual mixes two changes plus a publication gap. A 2x2 over
#   mechanic: legacy front-reference (calculate_eff_req_for_dataframe) vs two-sided
#   input:    2 separate DEA inputs [capex, controllable] vs 1 summed TOTEX
# gives a 2-factor Shapley (exact: average of the two orderings), and the remaining
# gap C1 - published is the reconciliation of our recomputed legacy against Ei's
# published current. Consistent forced exclusion across all four corners.
#
#   C1 = 2-input, legacy    (≈ current)        C2 = 2-input, two-sided
#   C3 = 1-input, legacy                        C4 = 1-input, two-sided  (= v(∅))
#   phi_mechanic = ½[(C2-C1)+(C4-C3)]   phi_input = ½[(C3-C1)+(C4-C2)]
#   phi_mechanic + phi_input = C4 - C1 ;  + (C1 - published) = residual
# ============================================================================
import numpy as np
from calculations.frontier.dea_calculations import run_dea_analysis
from new_benchmarking_model.efficiency.efficiency_requirement_two_sided import (
    calculate_two_sided_requirement,
)
from calculations.efficiency.efficiency_requirement import calculate_eff_req_for_dataframe
from new_benchmarking_model.config import NewBenchmarkingConfig
from config.column_names import COL_EFF_REQ_ANNUAL, COL_REID

CFG = NewBenchmarkingConfig()
s = s.copy()
s["totex_base"] = s["controllable"] + s["capex_unadj"]   # 1-input TOTEX (= v(∅) input)


def _dea(inputs):
    forced = s[COL_REID].isin(CFG.exclude_reids).to_numpy()
    return run_dea_analysis(s, {"inputs": inputs, "outputs": base_out, "rts": CFG.rts,
                                "forced_outliers": forced})


def _legacy(dea):   # front-reference: truncation 16.24-30 %, 1 % outlier floor, 50/50, t=8
    return calculate_eff_req_for_dataframe(dea)[COL_EFF_REQ_ANNUAL].to_numpy() * 100.0


def _twosided(dea):
    d = calculate_two_sided_requirement(
        dea, reference_percentile=CFG.reference_percentile, gap_cap=CFG.gap_cap,
        sharing=CFG.sharing, realization_time=CFG.realization_time,
        supervision_period=CFG.supervision_period)
    return d[COL_EFF_REQ_ANNUAL].to_numpy() * 100.0


dea2 = _dea(["capex_unadj", "controllable"])   # 2 separate inputs (legacy Ei DEA spec)
dea1 = _dea(["totex_base"])                    # 1 summed TOTEX input
C1, C2 = _legacy(dea2), _twosided(dea2)
C3, C4 = _legacy(dea1), _twosided(dea1)
published = s["req_cur_pct"].to_numpy() * 100.0

phi_mech = 0.5 * ((C2 - C1) + (C4 - C3))       # legacy front-ref -> two-sided
phi_inp = 0.5 * ((C3 - C1) + (C4 - C2))        # 2 inputs -> 1 TOTEX
recon = C1 - published                          # recomputed legacy vs Ei published
interaction = (C4 - C3) - (C2 - C1)             # diagnostic: mechanic effect (1-in minus 2-in)

decomp = pd.DataFrame({
    "REId": s[COL_REID].to_numpy(), "name_short": s["name_short"].to_numpy(),
    "phi_mechanic": phi_mech, "phi_input": phi_inp, "reconciliation": recon,
    "interaction": interaction, "residual_total": C4 - published,
    "C1_legacy_2in": C1, "C4_twosided_1in": C4, "published": published,
})
decomp.to_csv(OUT_DIR / "s5_residual_decomp.csv", index=False)

# cross-checks: C4 must equal v(∅) from the main Shapley; exact additivity
v0 = per.set_index("REId")["v_empty_pp"].reindex(s[COL_REID]).to_numpy()
chk_v0 = np.nanmax(np.abs(C4 - v0))
chk_add = np.nanmax(np.abs((phi_mech + phi_inp) - (C4 - C1)))
chk_tot = np.nanmax(np.abs((phi_mech + phi_inp + recon) - (C4 - published)))

print("\n=== residual decomposition (pp; <0 = lowers requirement) ===")
print(f"  check C4 == v(∅):                    max |Δ| = {chk_v0:.2e}")
print(f"  check phi_mech+phi_inp == C4−C1:     max |Δ| = {chk_add:.2e}")
print(f"  check sum + recon == residual:       max |Δ| = {chk_tot:.2e}")
print(f"  reconciliation (C1 vs Ei published): median {np.nanmedian(recon):+.3f}  median|.| {np.nanmedian(np.abs(recon)):.3f}")
print(f"  phi_mechanic (legacy -> two-sided):  median {np.nanmedian(phi_mech):+.3f}  mean {np.nanmean(phi_mech):+.3f}")
print(f"  phi_input    (2 inputs -> 1 TOTEX):  median {np.nanmedian(phi_inp):+.3f}  mean {np.nanmean(phi_inp):+.3f}")
print(f"  residual_total v(∅) − published:     median {np.nanmedian(C4 - published):+.3f}")
print(f"\nsaved: s5_residual_decomp.csv")

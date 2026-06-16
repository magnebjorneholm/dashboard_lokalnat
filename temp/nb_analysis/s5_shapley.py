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

    .venv/bin/python temp/nb_analysis/s5_shapley.py
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

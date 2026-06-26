# shapley_diagnostics

Re-run the new-benchmarking decomposition's per-coalition DEA on **R's Benchmarking**
(via the parent `dea_rpy2_benchmarking` rpy2 bridge) to obtain, for **every** Shapley
coalition, the structural diagnostics that PuLP does not expose — plus bootstrap
inference on the endpoints. The point is **fragility analysis**: because DEA is
relative, the peer structure and shadow prices shift as cost components enter the
model, and that shift is the brittleness signal.

> **For future Claude sessions:** read this first. The linchpin is the *parity gate*
> (below). The new diagnostics are only trustworthy because the R-based scoring
> reproduces the existing PuLP value grid to solver tolerance. Don't touch the
> scoring without re-checking parity. Background:
> `new_benchmarking_model/analysis/README.md` (the Shapley analysis) and
> `../ei_replication/` (R reproduces Ei's DEA exactly).

---

## What it produces

For each of the **128 coalitions** (subsets of the 7 cost-component players), in the
**frozen** outlier mode (the only mode used — see "Why only frozen"):

| Output | What it is |
|--------|-----------|
| **super-efficiency** θ (uncapped) | leave-one-out super-efficiency per scored firm (`sdea`). |
| **efficiency** (capped) + **requirement_pp** | `min(θ, 1)` and the signed two-sided requirement (percentage points) per scored firm — the per-firm scores that roll up to E75. |
| **number.peers** | how many firms each frontier firm benchmarks — its "load-bearing" weight. A frontier defined by one firm everyone leans on is fragile. |
| **n_peers_per_firm** | how many peers each firm leans on. |
| **peer identities + weights** | *who* each firm is benchmarked against and with what λ weight (the sparse active lambda) — the finest-level input for custom relativity/fragility analyses (e.g. does my benchmark set churn as cost posts enter?). |
| **shadow prices** u, v | input/output multipliers on the **standard frontier** (`dea.dual`) — how much each input/output "counts". Matrix form: u is n_ref×1, v is n_ref×(5 or 6). |

And for the **two endpoint coalitions** (baseline `v(∅)` and full `v(N)`):

| Output | What it is |
|--------|-----------|
| **bootstrap inference** | Simar-Wilson `dea.boot`: per-firm `eff`, bias-corrected `eff_bc`, `bias`, `var`, and a confidence interval `[ci_low, ci_high]`. DEA efficiency is a biased boundary estimate with no closed-form SE; this is the proper interval. |

Scope was agreed with Erik: super-eff/peers/shadow-prices for **all** coalitions
(the fragility question is inherently cross-coalition); inference only for the two
endpoints (the "how solid is the model we actually use" question).

---

## The parity gate (linchpin)

Before any new diagnostic is trusted, the R scoring must reproduce the existing PuLP
value grid (`new_benchmarking_model/analysis/out/decomp_{eff,req}/frozen/value_grid.csv`)
for **efficiency** and the **two-sided requirement**, coalition by coalition. The
runner writes `parity.csv` for all 128 coalitions and a pass/fail to `manifest.json`.

Result: **127/128 coalitions agree to ~5·10⁻⁹**. One coalition
(`losses+grid_subscription+cable`) sits at ~9·10⁻⁷ eff / ~5·10⁻⁶ pp req — a degenerate
LP where CBC (PuLP) and lpSolve (R) pick different optimal vertices with the same θ.
That is solver noise, not a method difference, so the gate allows solver-level slack
(`EFF_TOL=1e-5`, `REQ_TOL_PP=1e-4`) rather than demanding bit-identity across two
unrelated LP backends. Two independent solvers agreeing this closely *corroborates*
both, exactly as `../ei_replication/` does against Ei's facit.

---

## Why only frozen (not dynamic)

The two outlier modes give an **identical** outcome at the full coalition (max|Δ|=0)
and barely differ in the interior (Erik's comparison: mean |Δφ| ≈ 0.003 eff / 0.024 pp
req, ranking unchanged). For the **new** diagnostics, frozen is not just sufficient but
*better*: it holds the same 144-firm reference and the same 145 scored firms in every
coalition, so peers and shadow prices are **apples-to-apples across coalitions**. It
isolates "a cost post was added to the frontier" from "the outlier set was re-detected"
— dynamic would confound the two. Frozen set: `{REL00024, REL00257, REL00965, REL03016}`
(the first three are Ei's structural exclusions, left unscored; REL03016 is scored
against the fixed reference).

---

## Design: scoped replacement, not a rewrite

Only the **scoring layer** is new. Everything stable is reused by import from
`new_benchmarking_model`:
- the spine (`analysis._helpers.load_analysis_df`),
- the 7 players and subset composition (`analysis.decomp.players`),
- the two-sided E75 requirement (`efficiency.efficiency_requirement_two_sided`),
- the config (`NewBenchmarkingConfig`).

The Shapley/LOO/AOI attribution machinery in `analysis/decomp/engine.py` is **not**
touched — these diagnostics are the raw per-coalition matrices Erik wants for the
fragility study, not a Shapley decomposition of the new metrics. (Shapley of eff/req
already exists in the analysis package.)

---

## Files

```
shapley_diagnostics/
├── README.md            ← you are here
├── scoring.py           ← frozen-mode eff + two-sided req + super-eff θ (sdea + dea/XREF)
├── metrics.py           ← number.peers, n_peers_per_firm, shadow prices u/v (dea + dea.dual)
├── inference.py         ← Simar-Wilson bootstrap CI (dea.boot), endpoints only
├── run_diagnostics.py   ← sweep 128 coalitions, parity gate, write out/
├── out/                 ← CSV outputs + manifest.json (regenerated by the runner)
└── tests/test_parity.py ← parity gate + sanity (skips if R / data missing)
```

### out/

```
out/
  coalition_scores.csv   per coalition × scored firm: subset_mask, players, REId, super_eff, eff, requirement_pp
  number_peers.csv       per coalition × ref firm:    subset_mask, players, REId, number_peers, n_peers_per_firm, eff_standard
  peers.csv              LONG (active lambda): subset_mask, players, REId, peer_REId, is_self, lambda_weight
  shadow_prices.csv      LONG: subset_mask, players, REId, kind(u/v), variable(totex/CU/…), value
  inference.csv          endpoints × ref firm:        coalition, subset_mask, REId, eff, eff_bc, bias, var, ci_low, ci_high
  parity.csv             per coalition:               subset_mask, players, e75, max_abs_d_eff, max_abs_d_req
  manifest.json          frozen set, nrep, dual frontier, parity pass/fail, NaN count
```

`subset_mask` = bitmask over the player order in `analysis/decomp/players.py` (same
encoding as the legacy value grid, so the two join directly).

`peers.csv` is the finest level: per-firm peer-set stability, churn, weight-aware
benchmark concentration, etc. are all custom roll-ups of it — group by `REId` across
`subset_mask` (drop the `is_self` links first) and cut however the analysis needs. No
stability table is shipped; the runner writes only `peers.csv`.

### Granularity & firm coverage

All grids are **complete** (no gaps), but the level differs by metric because of the
frozen design — there are three firm tiers out of the 148:

| Tier | Firms | Appears in |
|------|-------|------------|
| reference frontier | **144** | everything (super-eff, peers, duals, inference) |
| scored | **145** = 144 + `REL03016` | super-eff / efficiency / requirement only — `REL03016` is frozen *out of the reference* so it gets a score but is never a peer and has no frontier shadow price |
| Ei-excluded | **3** (`REL00024`, `REL00257`, `REL00965`) | nowhere — unscored by Ei's own method |

| Output | Rows | = |
|--------|------|---|
| `coalition_scores.csv` | 18 560 | 128 coalitions × 145 scored firms |
| `number_peers.csv` | 18 432 | 128 × 144 reference firms |
| `peers.csv` | ~64 000 | 128 × the active λ links that coalition (one row per firm→peer) |
| `shadow_prices.csv` | 119 808 | 128 × 144 × (1 input u + 5 or 6 output v); 73 NaN from Status=5 |
| `inference.csv` | 288 | **2 endpoint coalitions** × 144 reference firms |
| `parity.csv` | 128 | one row per coalition |

So super-efficiency, number.peers and shadow prices cover **all 128 coalitions**;
the bootstrap inference covers **only the two endpoints** (baseline + full) by the
agreed scope — extending it to all 128 is a one-line change (128×2 `dea.boot`) but
much heavier.

---

## Run

```bash
# from the repo root
uv run python -m dea_rpy2_benchmarking.shapley_diagnostics.run_diagnostics            # full (NREP=2000)
uv run python -m dea_rpy2_benchmarking.shapley_diagnostics.run_diagnostics --nrep 200 # faster bootstrap
uv run python -m dea_rpy2_benchmarking.shapley_diagnostics.run_diagnostics --smoke    # 1 coalition, tiny boot
uv run pytest dea_rpy2_benchmarking/shapley_diagnostics/tests/ -v
```

Exit code 0 iff the parity gate passes. A full sweep is a few minutes (128 coalitions
+ two NREP=2000 bootstraps); the bootstrap seed is fixed (`set.seed(42)`) so the CI is
reproducible.

---

## Notes / gotchas

- **Standard frontier for duals** (per Erik): `dea.dual` gives shadow prices on the
  ordinary envelopment frontier, not the super-efficiency LP. Super-efficiency θ is a
  separate output (from `sdea`).
- **Non-uniqueness.** Under degeneracy, λ (peers) and the multipliers (u, v) are not
  unique — different solvers/vertices can give different peer sets and shadow prices at
  the same θ. That is itself part of the fragility signal, but read peers/duals as
  solver-convention-dependent, not exact. Using Benchmarking's documented convention
  (the DEA-literature reference) is deliberate here.
- **Status = 5.** lpSolve occasionally reports a numerical problem for a few firms in a
  few coalitions; it surfaces as a small number of NaN **dual** values
  (~0.06 % of shadow-price cells; super-eff and peers are unaffected). They are left NaN
  rather than papered over. If this ever grows, scale X/Y or pass `CONTROL` to the LP
  (see Benchmarking's `dea` notes).
- **rpy2 dependency.** This is an offline analysis; running it needs R + the
  Benchmarking package present (same as the rest of `dea_rpy2_benchmarking/`).

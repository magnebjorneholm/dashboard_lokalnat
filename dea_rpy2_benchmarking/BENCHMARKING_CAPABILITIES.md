# What you can get out of `Benchmarking` (beyond a bare efficiency score)

A catalogue of every metric, diagnostic, intermediate and side-analysis the R
`Benchmarking` package (Bogetoft & Otto, v0.33) exposes. Grounded in actually
running each function and inspecting the returned objects — not from memory.

> **Reading this from Python.** Our `dea()`/`sdea()` wrappers surface `eff`,
> `lambdas` and (optionally) total `slack`, and keep the raw R object on
> `result.raw`. Everything below is reachable either through `result.raw.rx2("…")`
> or through `package()` (the full R package; R's dotted names map to underscores,
> e.g. `dea.boot` → `bench.dea_boot`). See `README.md`.

---

## 1. Intermediates already inside one `dea()` solve

A single `dea(X, Y, RTS, ORIENTATION, SLACK=TRUE, DUAL=TRUE)` returns a "Farrell"
object — a named list with **16 fields**. You get all of these from *one* solve:

| Field | What it is |
|-------|-----------|
| `eff` | The efficiency score (θ). The headline number. |
| `lambda` | **Intensity weights** — the (n×n) matrix saying which frontier units, and in what proportions, each DMU is benchmarked against. Row i's non-zeros are i's "recipe". |
| `objval` | LP objective value (= `eff` for radial models; = slack sum for additive). |
| `sx`, `sy` | **Input slacks / output slacks** (with `SLACK=TRUE`): the *non-radial* leftover after the radial move — extra input reducible / output expandable beyond θ. |
| `slack` (bool), `sum` | Per-DMU "has slack?" flag and the **total slack** Σ(sx+sy). |
| `ux`, `vy` | **Optimal multipliers** (with `DUAL=TRUE`): the input weights u and output weights v — i.e. the DMU's own most-favourable shadow prices. |
| `gamma` | Dual variable(s) on the convexity/RTS constraints — carries scale information. |
| `primal`, `dual` | The full primal and dual LP solution matrices (every variable, for audit). |
| `RTS`, `ORIENTATION`, `TRANSPOSE`, `param`, `direct` | Metadata recording exactly how it was solved. |

So even "just running DEA" already hands you peers, slacks, and shadow prices.

---

## 2. Peer / benchmark diagnostics (who you're compared to)

Accessor functions on a Farrell object:

- **`peers(e)`** — for each DMU, the indices of its benchmark units (the frontier
  units with λ>0). The concrete "look at firms 3 and 4" answer.
- **`get.peers.lambda(e)`** — the same, but with the λ weight on each peer.
- **`get.number.peers(e)`** — how many times each frontier unit *serves as* a peer
  for others: a **benchmark-influence / robustness** measure (a frontier defined by
  one firm that everyone leans on is fragile).
- **`get.which.peers(e)`** — which DMUs have a given unit in their peer set.
- **`lambda(e)` / `lambda.print(e)`** — the full intensity matrix, printed readably.

---

## 3. Slacks & excess (the improvement *plan*, in real units)

- **`slack(X, Y, e)`** — runs the second-phase slack-maximising LP and returns
  `sx`, `sy`, `sum`, plus the `slack` flag. This is the non-radial part: after
  shrinking inputs by θ, what *else* is wasted.
- **`excess(e, X)`** — the improvement target expressed in **original units**:
  how much of each input to cut (and/or output to add) to reach the frontier
  point. The actionable "reduce input 2 by 1.5" number.

---

## 4. Shadow prices / multipliers (`dea.dual`)

- **`dea.dual(X, Y, RTS)`** — returns `u` (input weights) and `v` (output weights)
  for every DMU. These are the **marginal values / shadow prices**: how much each
  input and output "counts" in the weighting that makes the DMU look best. Useful
  for spotting outputs a unit puts zero weight on (effectively ignored), and for
  imposing weight restrictions.

---

## 5. Returns-to-scale analysis

Run the same data under different `RTS` and combine:

- `RTS ∈ {fdh, vrs, drs, irs, irs2, crs, add, fdh+}`.
- **Scale efficiency** = θ_CRS / θ_VRS per DMU (how much of inefficiency is pure
  scale vs. pure technical).
- The sign/pattern of `gamma` and the VRS-vs-DRS-vs-IRS comparison classify each
  DMU's local returns to scale (operating below / at / above optimal size).

---

## 6. Economic efficiency — needs prices (`cost/revenue/profit.opt`)

| Function | Inputs | Returns | Gives you |
|----------|--------|---------|-----------|
| `cost.opt(X,Y,W,RTS)` | input prices W | `xopt`, `cost`, `lambda` | The cost-minimising input mix and minimum cost → **cost efficiency** CE = min cost / actual cost. |
| `revenue.opt(X,Y,P,RTS)` | output prices P | `yopt`, `rev`, `lambda` | Revenue-maximising output mix → **revenue efficiency**. |
| `profit.opt(X,Y,W,P,RTS)` | W and P | `xopt`, `yopt`, `profit`, `lambda` | Profit-maximising plan → **profit efficiency**. |

**Allocative efficiency** falls out: AE = CE / TE (cost efficiency divided by the
technical efficiency from `dea`). I.e. the part of cost waste due to the *wrong
input mix* given prices, separate from pure technical waste. (Verified: e.g. a
unit with TE=0.75 but CE=0.68 → AE=0.91.)

---

## 7. Directional & multidirectional models

- **`dea.direct(X,Y,DIRECT=…)`** — directional distance function: instead of a
  radial (proportional) move, you specify a **direction** g and get the additive
  improvement along it. Lets inputs and outputs improve simultaneously, or a
  chosen subset.
- **`mea(X,Y,RTS)`** — Multidirectional Efficiency Analysis: a **per-dimension**
  potential. Its `direct` matrix gives each DMU's improvement potential separately
  for *every individual input and output* (e.g. "input 1 can fall by 6, input 2 by
  4"), rather than one scalar. Good for asymmetric, variable-by-variable targets.

---

## 8. Additive / slack-based model

- **`dea.add(X,Y,RTS)`** — the additive DEA model. Efficiency is measured purely
  as the **sum of slacks** (`sum`, with `sx`/`sy`), units-invariant variants
  exist. Flags any unit with *any* slack as inefficient even when radially
  efficient — stricter than radial DEA.

---

## 9. Productivity change over time (Malmquist)

- **`malmq(...)` / `malmquist(...)`** with two periods (X0,Y0) and (X1,Y1) returns
  a full decomposition:
  - **`m`** — the Malmquist productivity index (total productivity change).
  - **`tc`** — **technical change**: how much the frontier itself shifted (sector
    moving forward/back).
  - **`ec`** — **efficiency change** ("catch-up"): the unit moving toward/away from
    the frontier.
  - **`mq`**, and the four cross-period distances **`e00, e10, e11, e01`** (each
    period's data scored against each period's frontier) used to build them.
  - `m = tc · ec`. Decomposes "did we get more productive?" into innovation vs.
    catch-up. (Needs two aligned periods with an `ID`.)

---

## 10. Statistical inference — bootstrap (`dea.boot`, `boot.fear`)

DEA scores are point estimates with no built-in standard error. The bootstrap
fixes that:

- **`dea.boot(X,Y,NREP,…)`** returns:
  - **`eff`** — original scores; **`eff.bc`** — **bias-corrected** scores.
  - **`bias`** — estimated bias of the DEA estimator per DMU.
  - **`var`** — variance of each score.
  - **`conf.int`** — per-DMU **confidence interval** (e.g. 2.5%/97.5%).
  - **`boot`** — the full matrix of bootstrap replicate scores (n × NREP).
- **`boot.fear(...)`** — same idea via the faster FEAR backend.
- **`critValue(...)` / `typeIerror(...)`** — turn bootstrap replicates into a
  hypothesis test (critical value for a statistic; type-I error / p-value for an
  observed value). Used e.g. to test constant returns to scale.

---

## 11. Outlier & influence diagnostics

- **`outlier.ap(X,Y,NDEL)` / `outlierC.ap(...)`** — the Wilson (1993)
  super-efficiency / min-ratio method. Returns `ratio` (the R_min statistic as you
  delete 1,2,…,NDEL firms), `imat` (which firms are jointly the most influential
  at each deletion order), and `r0`. Flags units whose removal most changes the
  frontier — *this is the package-native sibling of the IQR procedure in
  `ei_replication/`.*
- **`eladder(i, X, Y, RTS)` / `eladder.plot` / `eladder2`** — the **efficiency
  ladder** for a chosen DMU i: repeatedly remove i's most influential peer and
  record how i's efficiency moves. Returns `eff` (the sequence of scores), `peer`
  (the order peers were removed), `lastp`. Shows how dependent one firm's score is
  on a single benchmark.

---

## 12. Parametric & semi-parametric frontiers

Alternatives to DEA's deterministic frontier:

- **`sfa(x, y)`** — **Stochastic Frontier Analysis**. Separates inefficiency from
  noise. Returns a lot: `coef`/`beta` (frontier slope coefficients), `residuals`,
  `fitted.values`, **`lambda`** (= σu/σv, the inefficiency-to-noise ratio),
  **`sigma2`** (total), `loglik`, `vcov`, `std.err`, `t.value`, plus
  `summary()` with a coefficient table. Helpers `sigma2u`/`sigma2v`/`sigma2`
  split the variance.
  - Technical-efficiency estimators per firm: **`te.sfa`** (Battese–Coelli
    conditional mean), **`teBC.sfa`**, **`teJ.sfa`** (Jondrow et al.),
    **`teMode.sfa`** (conditional mode), and `te.add.sfa`.
- **`sfa.cost(...)`** — the cost-function version (inefficiency raises cost).
- **`stoned(X,Y,RTS)`** — **StoNED** (convex nonparametric least squares + a
  stochastic frontier). Returns `eff`, `front` (fitted frontier), `yhat`,
  `residuals`, `coef`, **`sigma_u`**, `SSR`. A middle ground: DEA's shape-freedom
  with SFA's noise handling.

---

## 13. Distribution of efficiency

- **`eff.dens(scores)` / `eff.dens.plot(...)`** — a boundary-corrected **kernel
  density** of the efficiency scores (`x`, `y`, bandwidth `bw`). For seeing the
  shape of the efficiency distribution (bimodal? mass at 1?) rather than just a
  mean.

---

## 14. Merger analysis (`dea.merge`, `make.merge`)

For "what if these firms merged?" (very relevant to a regulator):

- **`dea.merge(X,Y,M,RTS)`** decomposes the potential gain of each merger group M:
  - **`Eff`** — overall efficiency of the merged unit; **`Estar`** — its
    efficiency net of the partners' own pre-merger inefficiency.
  - **`learning`** — gain available just from each partner reaching its own
    frontier first.
  - **`harmony`** (a.k.a. scope) — gain from a better *mix* of the combined
    inputs/outputs.
  - **`size`** (scale) — gain/loss from the merged entity's size.
  - `Eff = learning · harmony · size`. Separates "merge to fix bad management"
    from "merge for genuine scope/scale synergy".
- **`make.merge(...)`** — helper to build the merge-grouping matrix M.

---

## 15. Visual diagnostics (`dea.plot` family)

`dea.plot`, `dea.plot.frontier`, `dea.plot.isoquant`, `dea.plot.transform`,
`mea.lines`, `eladder.plot`, `eff.dens.plot` — draw the production frontier,
isoquants, the transformation curve, MEA paths, etc. (These render in R graphics;
from Python you'd typically recompute the geometry and plot with Plotly instead.)

---

## Quick map: which call gives which extra output

| You want… | Call |
|-----------|------|
| Who am I benchmarked against | `peers`, `get.peers.lambda`, `lambda` |
| How influential is each frontier firm | `get.number.peers` |
| Concrete units to cut/add | `excess`, `slack` (`sx`/`sy`) |
| Shadow prices / weights | `dea.dual` (or `DUAL=TRUE`) |
| Scale vs. technical inefficiency | DEA at CRS and VRS, ratio |
| Cost / allocative efficiency | `cost.opt` (+ prices) |
| Revenue / profit efficiency | `revenue.opt` / `profit.opt` |
| Per-variable improvement potential | `mea` |
| Productivity change over years | `malmq` (`m`, `tc`, `ec`) |
| Confidence intervals / bias | `dea.boot` (`eff.bc`, `bias`, `conf.int`) |
| Test (e.g. CRS vs VRS) | `dea.boot` + `critValue`/`typeIerror` |
| Outlier / influence screening | `outlier.ap`, `eladder` |
| Noise-robust frontier | `sfa`, `sfa.cost`, `stoned` |
| Efficiency distribution shape | `eff.dens` |
| Merger synergies | `dea.merge` |

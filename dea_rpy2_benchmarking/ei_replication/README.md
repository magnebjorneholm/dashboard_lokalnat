# ei_replication

Reproduce **Ei's published DEA results** (`data/raw/ei/EIs_DEA.xlsx`) exactly,
using **R's Benchmarking** package as the LP engine (via the parent
`dea_benchmarking` rpy2 bridge). This is **step 3** of the parent project — see
`../README.md`.

> **For future Claude sessions:** this folder is self-contained. It ports the
> project's pure-Python DEA procedure onto R/Benchmarking and checks the output
> against Ei's facit. If a change here ever stops matching, read
> `../../eis_dea_metod.md` (the authoritative method) before touching anything.

## Result (verified)

Running `run_replication.py` reproduces Ei's facit **to ~8·10⁻¹¹** (well inside
the 5·10⁻⁹ solver tolerance) for **all 148 firms except REL00193**:

```
Loaded 148 firms; inputs=2, outputs=5
Outlier rounds: 3   outliers: 3
Outlier firms : REL00024, REL00257, REL00965
Comparison vs facit (excluding REL00193):
  max |eff  diff|   : 1.290e-11
  max |seff diff|   : 8.213e-11
  RESULT            : PASS
Known non-replicable row REL00193: super-eff replicated=0.757065  facit=0.582885
```

Two unrelated LP backends — the project's PuLP/CBC path and R/Benchmarking here —
agree, which corroborates both. REL00193 is a known **data** anomaly (its facit
0.5829 is below what any reference set yields), not a method error; see
`eis_dea_metod.md`.

## What it does

Faithful port of `calculations/frontier/outliers.py` +
`calculations/frontier/dea_calculations.py`, swapping the solver:

1. **Super-efficiency LP** — input-oriented, **CRS**, leave-one-out (`j ≠ i`).
   Computed by `Benchmarking::sdea` on the current reference rows (passing only
   the reference rows makes `sdea`'s leave-one-out = "scored against the rest of
   the reference set").
2. **Iterated IQR outlier fence** — `Q3 + 2·(Q3−Q1)` on the 25/75 percentiles of
   the finite reference scores, one-sided (upper). Flag → remove → re-solve,
   **until no new outliers appear** (here: 3 rounds). A single round does *not*
   reproduce Ei.
3. **Final scoring** — survivors scored against the cleaned reference set:
   `efficiency = min(θ, 1)`, `super_eff = θ`, `potential = 1 − efficiency`.
   Outliers are reported with their flag-time score and `potential = 1.0`.

### Specification (Ei's locked baseline)

| Role | Columns (raw, from `Data_modeller.xlsx`) |
|------|------------------------------------------|
| inputs  X | `CAPEX`, `OPEXp` (raw OPEXp — **not** the SDF `controllable_cost_average`) |
| outputs Y | `CU`, `MW`, `NS`, `MWhl`, `MWhh` |
| model | CRS, input-oriented, super-efficiency, no scaling |
| fence | q_lower=25, q_upper=75, multiplier=2.0, iterated to convergence |

The "raw OPEXp vs SDF" distinction matters: the app's pipeline swaps OPEXp for an
SDF-derived cost and so does **not** reproduce this facit (it re-runs the same
method on a revised cost base). For Ei's published numbers, use raw OPEXp — which
is what `data.py` loads. See `eis_dea_metod.md` §"Inputkravet".

## Files

```
ei_replication/
├── README.md            ← you are here
├── data.py              ← load Data_modeller + facit via config/data_paths.py
├── replicate.py         ← super_eff_scores / detect_outliers / replicate()  (uses sdea)
├── compare.py           ← compare() replicated vs facit, excluding REL00193
├── run_replication.py   ← CLI: run + report PASS/FAIL
└── tests/
    └── test_replication.py   ← 5 tests; skip cleanly if R / data missing
```

## Run

```bash
# from the repo root (so the project's config/ is importable)
uv run python -m dea_rpy2_benchmarking.ei_replication.run_replication
uv run pytest dea_rpy2_benchmarking/ei_replication/tests/ -v
```

`run_replication.py` exits 0 on PASS, 1 on FAIL.

## Notes / gotchas

- **Data dependency.** Reads `data_modeller` and `eis_dea` through the project
  registry `config/data_paths.py` (logical names → `data/raw/ei/*.xlsx`). The CLI
  and tests add the repo root to `sys.path` so that import resolves. If the raw
  files are absent the tests skip rather than fail.
- **Infeasible / missing.** `sdea` returns `Inf` for an infeasible
  super-efficiency LP; `replicate.py` normalises that to `NaN`, and any
  non-finite score is treated as an outlier signal (matching the PuLP path).
  There are no NaNs in the current data, but the handling is kept for parity.
- **Identifiers.** `Data_modeller.xlsx` and `EIs_DEA.xlsx` are row-aligned on
  `REId`/`DMU` (verified), so comparison is a straight row-wise join.
- **Don't "fix" REL00193.** Its deviation is expected and the tests assert it is
  the *only* deviation. If more firms start deviating, the method changed —
  investigate `replicate.py` against `eis_dea_metod.md`, don't relax the tolerance.

# dea_rpy2_benchmarking

Run **DEA (Data Envelopment Analysis)** from Python using the R package
**Benchmarking** (Bogetoft & Otto), bridged via **rpy2**. The goal is to make the
*entire* Benchmarking toolbox callable from Python while offering clean,
typed wrappers for the common cases.

> **For future Claude sessions:** this README is the source of truth for this
> isolated sub-project. Read it first. It explains the rpy2 setup gotchas, what
> works today, and the planned next steps. Keep it updated as the project grows.

---

## Status (step 1 — mock data ✅)

| Piece | State |
|-------|-------|
| R 4.6 + `Benchmarking` 0.33 installed | ✅ |
| `rpy2` 3.6 bridge, clean import (no API-mode warning) | ✅ |
| `dea()` / `sdea()` Python wrappers | ✅ |
| Mock-data demo runs end to end | ✅ |
| Smoke test suite (8 tests, all green) | ✅ |
| **Replicating Ei's DEA exactly** (`ei_replication/`) | ✅ matches facit to ~8e-11 |
| Real Regumetrica (SDF) data | ⏳ optional next |

**The current milestone is deliberately limited to synthetic data** so we can
trust the plumbing before pointing it at real regulatory inputs.

---

## Prerequisites

These are **not** pip-installable and must exist on the machine:

1. **R** (>= 4.x) on `PATH`. Here: Homebrew R 4.6 (`brew install r`).
2. **Benchmarking** R package:
   ```bash
   Rscript -e 'install.packages("Benchmarking", repos="https://cloud.r-project.org")'
   ```
   (Pulls in `lpSolveAPI`, `ucminf`, `quadprog`, `Matrix`.)

Python deps (into the project `.venv`):
```bash
uv pip install -r dea_rpy2_benchmarking/requirements.txt
```

Sanity check the whole stack:
```bash
cd dea_rpy2_benchmarking
uv run python examples/run_mock_dea.py     # prints efficiency scores
uv run pytest tests/ -v                     # 8 passing / skipped if R absent
```

---

## Layout

```
dea_rpy2_benchmarking/
├── README.md                     ← you are here
├── requirements.txt
├── src/dea_benchmarking/
│   ├── __init__.py               ← public API: dea, sdea, package, DEAResult
│   ├── r_session.py              ← rpy2 bootstrap: R_HOME detect, ABI mode, package import
│   ├── conversions.py            ← coerce inputs to clean (n_dmu, n_dim) float matrices
│   ├── dea.py                    ← dea()/sdea() wrappers + raw package() access
│   └── results.py                ← DEAResult dataclass (eff, lambdas, slack, raw)
├── examples/
│   ├── mock_data.py              ← textbook + random synthetic DMUs
│   └── run_mock_dea.py           ← end-to-end demo
└── tests/
    └── test_smoke.py             ← skips cleanly if R/Benchmarking missing
```

The package lives under `src/` and is not pip-installed; scripts/tests add
`src/` (and the package root) to `sys.path`. If this graduates into the main
app later, give it a real install or wire it into `config/data_paths.py`
conventions — but for now it stays self-contained.

---

## Usage

```python
import numpy as np
from dea_benchmarking import dea, sdea, package

X = np.array([[1.], [2.], [3.], [4.], [5.]])   # inputs:  (n_dmu, n_inputs)
Y = np.array([[1.], [3.], [4.], [3.], [5.]])   # outputs: (n_dmu, n_outputs)

res = dea(X, Y, rts="vrs", orientation="in", slack=True,
          dmu_names=["a", "b", "c", "d", "e"])

res.eff            # np.ndarray of efficiency scores, one per DMU
res.lambdas        # (n_dmu, n_dmu) peer-intensity matrix
res.slack          # total slack per DMU (because slack=True)
res.efficient()    # boolean mask of frontier units
res.as_dataframe() # tidy pandas table (needs pandas)
res.raw            # the underlying rpy2 "Farrell" object

# Super-efficiency (efficient units can score > 1 — outlier screening, ranking)
sres = sdea(X, Y, rts="crs", orientation="in")
```

### Options

- `rts` (returns to scale): `"fdh" | "vrs" | "drs" | "crs" | "irs" | "irs2" | "add" | "fdh+"`
- `orientation`: `"in" | "out" | "graph" | "in-out"`

> **What can you get out of Benchmarking besides a bare efficiency score?**
> See [`BENCHMARKING_CAPABILITIES.md`](BENCHMARKING_CAPABILITIES.md) — a full
> catalogue of every metric/diagnostic/intermediate (peers, slacks, shadow
> prices, allocative/cost/profit efficiency, Malmquist, bootstrap CIs, outlier
> diagnostics, SFA/StoNED, merger analysis, …), each verified by running it.

### The full Benchmarking API ("everything is available")

The wrappers cover `dea`/`sdea`. For anything else, reach the raw R package
object — every exported function is an attribute (R's dotted names become
underscores, e.g. `dea.boot` → `dea_boot`):

```python
bench = package()
bench.dea_boot(...)     # bootstrap confidence intervals
bench.malmquist(...)    # Malmquist productivity index
bench.cost_opt(...)     # cost-minimising input mix
bench.sfa(...)          # stochastic frontier analysis
bench.outlier_ap(...)   # outlier detection
```

Available functions in Benchmarking 0.33 include:
`dea, sdea, dea.add, dea.boot, dea.direct, dea.dual, dea.merge, dea.plot,
cost.opt, revenue.opt, profit.opt, malmquist, malmq, mea, sfa, slack, eff,
peers, lambda, eladder, outlier.ap, outlierC.ap, stoned, boot.fear, …`
(full list: `Rscript -e 'library(Benchmarking); ls("package:Benchmarking")'`).

---

## How the bridge works (and why it's fiddly)

`r_session.py` owns every fragile bit. Three things matter:

1. **Environment before import.** rpy2 reads `R_HOME` and `RPY2_CFFI_MODE` at
   import time. `r_session` sets them *before* importing rpy2, so **any module
   that needs rpy2 must import `r_session` first**. (Bug we already hit:
   importing `rpy2.robjects.conversion` at the top of `dea.py` before
   `r_session` re-triggered an API-mode dlopen warning. Fixed by ordering.)

2. **ABI mode + dynamic R_HOME.** The prebuilt rpy2 wheel was linked against a
   *different* R (a CRAN framework R 4.5) than the Homebrew R 4.6 we run. Forcing
   `RPY2_CFFI_MODE=ABI` and pinning `R_HOME` to `R RHOME` makes the binding load
   the correct `libR`. Without this you get a noisy
   `Library not loaded: .../4.5-arm64/.../libRblas.dylib` warning.

3. **Scoped numpy conversion.** rpy2 ≥ 3.5 deprecated the global
   `numpy2ri.activate()`. We use a merged converter
   (`default_converter + numpy2ri.converter`) only where needed:
   - numpy → R: convert the X/Y matrices *inside* the converter context.
   - R → numpy: convert `eff`/`lambda`/slacks back inside the context.
   - The Farrell result object itself is **not** auto-converted (so it keeps its
     `.rx2(...)` accessors) — we pull fields out explicitly.

If `Benchmarking` is missing, `get_benchmarking()` raises with the exact install
command. Tests `pytest.skip` rather than fail when R is unavailable.

---

## Sub-projects

- **`ei_replication/`** — reproduces Ei's published DEA (`EIs_DEA.xlsx`) exactly
  using R/Benchmarking. Matches the facit to ~8·10⁻¹¹ for all 148 firms except
  the known anomaly REL00193; finds the same 3 outliers in 3 iteration rounds.
  See `ei_replication/README.md`. **This is the realised "step 3".**

## Roadmap

- **Step 1 — mock data (done).** Plumbing + wrappers + smoke tests.
- **Step 3 — replicate Ei (done).** See `ei_replication/`.
- **Possible next — real (SDF) data.** Re-run the same method on the app's
  SDF-derived cost base (`controllable_cost_average` instead of raw OPEXp). Per
  `eis_dea_metod.md` this is *not* a facit replication but a re-run; outlier set
  shifts 3 → 5. Resolve datasets through `config/data_paths.py`.
- **Possible later:** bootstrap CIs (`dea.boot`), Malmquist over years, expose a
  thin result→pandas layer aligned with the app's `COL_*` conventions.

---

## Conventions reminder (from project CLAUDE.md)

- Code/identifiers in English; conversation in Swedish.
- Don't hardcode `data/` paths — use the `config/data_paths.py` registry when
  step 2 starts.
- This sub-project is isolated: it does **not** import from `calculations/`,
  `pipeline/`, etc., and nothing in the main app imports it yet.

# Backend Rebuild Evaluation

**Purpose.** A pre-migration evaluation of Regumetrica's backend, data flow, pipeline,
naming, file formats and documentation, written to set up the correct building blocks for
the planned move to **React + Next.js + Tailwind frontend over a Python (FastAPI) API
backend**. All future backend work is done by AI coding agents overseen by the owner, so
this document optimizes for unambiguous structure and machine-readable context.

**Status.** Produced 2026-06-12 by a multi-agent audit: 7 parallel deep-dives, each finding
independently re-checked by an adversarial verifier, plus a completeness-critic pass that
added 4 gap dimensions. 105 findings total; **0 were refuted**, ~45% were *adjusted*
(evidence or severity corrected) by the verifier — i.e. the verification did real work, and
what remains is calibrated. The run hit a session limit at the very end, so **17 findings
(deployment/runtime + most of the test-coverage gap) carry evidence but were not
independently verified** — they are marked `unverified` in the appendix and flagged inline.
The two auto-generated target-architecture drafts also died at the cutoff; the *Target
building blocks* section below is written by hand from the verified findings.

> This document is independent of, and does not draw on, `MIGRATION_PRINCIPER.md`.

**Legend.** Severity = impact on the rebuild / future development. `H` high, `M` medium,
`L` low. Status: `✓` confirmed, `±` adjusted (corrected, see appendix), `?` unverified.

---

## Executive summary

The codebase is **fundamentally sound but built as accretion around a Streamlit runtime,
not as a data backend.** The pure calculation core (`calculations/`, ~3,600 LOC of real
domain math) is good and largely survives. The problems cluster in the layers the migration
must replace anyway — the pipeline orchestration, the data-loading/caching story, the
config/state contract, and naming — plus a serious authorization hole found along the way.

The owner's two intuitions are both correct and now quantified:

1. **The pipeline is overengineered.** The 5 "stages" wrap a computation that is genuinely a
   **3-node DAG** on 148-row DataFrames: (1) capital costs, (2) efficiency scores, (3)
   revenue-frame assembly. Stage 1 is a deep-copy repack of the input; stage 4 ("extraction")
   is a two-row lookup that belongs at the API/serialization layer; and **`stage_dea`
   provably ignores its `pre_dea` input** — so the linear 5-step narrative actively
   *misdescribes* the dependency structure. Orchestration is **2,047 LOC today; a clean
   implementation is ~550–650 LOC**, calling the existing `calculations/` functions
   unchanged.

2. **Much was done inefficiently in ways that impair future work.** The same regulatory rule
   is encoded in two stages (OPEX scaling), defaults for the same parameter live in up to
   six places, the revenue-frame decomposition is derived three independent times, the
   REId↔id_network conversion is reimplemented 8 times, and 20+ year-suffixed column
   constants hard-code the 2024–2027 period into identifier names. None of this is fatal at
   148-company scale; all of it is exactly the ambiguity that derails AI coding agents.

Three things are **urgent regardless of the migration**:

- **Security (H).** Open registration writes the user's chosen `role`/`REId` straight into
  Firebase custom claims — **anyone can self-provision "Regulator" access** and read/write/
  delete any company's saved cases (which include uploaded KENT capital-base data). Cases are
  scoped by REId string, not user identity. See [Security](#8-security--authorization-gap-h--found-along-the-way).
- **A latent crash (H?).** The `PARAMETER_CHANGE` + direct-WACC path already throws under the
  installed `pandas 3.0.3` (`float32` setitem at `calculations/capex/data_mapping.py:122`),
  masked in production only because the surrounding code swallows it and silently returns
  *baseline* numbers to a user who asked for a change.
- **Firestore size limit (H?).** Computed capbase parquet is base64-inlined into the case
  document; the largest company's blob can exceed Firestore's 1 MiB document limit.

The single highest-leverage decisions for the rebuild: **(a)** collapse the pipeline to three
pure functions + one composer; **(b)** introduce a `raw → staging → derived` data layer built
by scripts, so the API serves fixed parquet instead of re-parsing three Excel workbooks per
process; **(c)** replace the untyped `ui_config` dict (and the 673-LOC adapter that renames
it) with **one pydantic `CaseConfig`** that is simultaneously the API request body, the
Firestore document, and the validation boundary; **(d)** make `config/glossary.py` the single
`ParameterSpec` registry (metadata + bounds + defaults); **(e)** standardize on **one company
key (REId)** and **tidy long format** (year as a column). The 275-test facit suite is the
golden master that proves the rebuilt core is equivalent — but it must first be made
Streamlit-free.

---

## 1. The pipeline is overengineered (the central finding)

**What the computation actually is.** From inputs to revenue cap, the real graph is a diamond,
not a chain:

```
BaselineData (static, 148 rows) ──┬──> capital_costs(baseline, capex_cfg) ─┐
        + CaseConfig              │                                        ├─> revenue_frame(...) ─> 148 frames
                                  └──> efficiency(baseline, eff_cfg) ───────┘
                                       (DEA / published table / StoNED)
   per-company view = a query over the 148 frames  (NOT a compute step)
```

`capital_costs` and `efficiency` are **mutually independent**; only `revenue_frame` depends on
both. Verified facts behind this:

- `pipeline/stages/dea.py:33` declares `pre_dea: Optional[...] = None` and the body never
  reads it; `dea.py:12-16` and `mini_run.py:77` ("stage_dea never uses pre_dea") confirm DEA
  depends only on baseline data. `core.py:118-122` threads the unused parameter through anyway.
- `pipeline/stages/baseline.py:41-51` is a near-verbatim repack of `BaselineData` with 8
  `.copy()` calls and **zero computation** (and the copies are redundant — the loader is
  already cached).
- `pipeline/stages/extraction.py` (81 LOC) does two `df[df.REId == reid]` lookups into an
  11-field dataclass; production reads **4 of 11** fields, and `cu/mw/ns` are read nowhere.
  `stage_post_dea` never consumes it (`core.py:142-150`). `mini_run.py:87-113` re-implements
  its own extraction rather than reusing the stage.
- A full baseline-config run measures **~0.05 s**; two runs produce byte-identical outputs.

**Why it matters for the rebuild.** The 5-step linear story in `core.py` teaches a false
dependency structure that AI agents will copy into the new backend (and keep threading the
unused `pre_dea`). The frozen-dataclass "stage outputs" layer (5 classes, 42 fields, **8+
never read**) buys no type safety — consumers reach into `.df` attributes and re-merge by REId
30+ times — only copy overhead and a second vocabulary.

**Quantified.** Orchestration today: `core.py` 212 + `stages/` 1,130 + `debug_logger.py` 363
+ `post_dea_capex_helpers.py` 163 + `mini_run.py` 128 + `__init__` 51 = **2,047 LOC**
(`export_excel.py` 1,349 and `result_helpers.py` 343 are misplaced *presentation* code inside
`pipeline/`, counted separately). A clean rebuild — three pure functions + a ~30-line composer
+ one result container — is **~550–650 LOC** calling the existing, sound `calculations/`
entry points unchanged. **Heuristic for the rebuild: if the new orchestration exceeds ~700
LOC, ceremony is creeping back.**

Other pipeline-layer findings:
- **OPEX scaling (4.1.1/40.1.1) is implemented twice** — `pre_dea.py:75-112` on
  `df_all_companies` and `post_dea.py:99-109` on `sdf_controllable` — and the two encodings
  have **already diverged in scope** (post_dea also scales `neo_adjustments`). Only the
  post_dea copy affects the revenue cap; the pre_dea copy feeds dead extraction fields. Apply
  each user adjustment **once**, in the step where it has effect.
- **`debug_logger` (363 LOC, 51 `print()`s)** runs by default in production, printing ~2.9 KB
  to stdout per calculation; it is larger than the orchestrator it instruments. Replace with
  standard `logging` + a small `validate(result)` for the genuine invariants (148 companies,
  TOTEX = CAPEX + OPEX).
- **Silent `except Exception` fallbacks** (`pre_dea.py:347-349, 417-418`; `post_dea.py:246-249`)
  convert real errors into plausible-but-wrong results (baseline shown as the user's scenario;
  incentives silently omitted) — poison for an API whose clients can't see stdout. Let errors
  propagate to typed HTTP responses.

---

## 2. Data management & file formats

**The core defect: there is no `raw → staging` build step.** Every cold start re-parses three
Excel workbooks, re-derives controllable-cost averages, re-merges curated names, re-aggregates
returns, and reconciles three overlapping sources of OPEXp — i.e. **the "baseline data" is the
output of load-time computation, not a readable dataset** (`data_loaders/baseline_data.py:324-435`).
No script in `scripts/` builds `capbase_a.parquet`, `capcost_a.parquet`, `controllable_a.parquet`
or `all_adjust_vars.csv`; their provenance is undocumented. An agent cannot tell which source
is authoritative for any number.

- **Runtime xlsx parsing is fragile more than slow.** Measured cold `load_baseline_data()` =
  ~289 ms (xlsx ≈ 150 ms of it). The cost is not speed; it is the **sheet-name guessing**
  (`baseline_data.py:94` tries `["Körning","Sheet1",0]`, first always fails and is swallowed),
  the **opening of the SDF workbook three times**, and **silent empty-frame substitution** that
  defers crashes deep into the pipeline.
- **The Swedish→English boundary leaks.** The rule "Swedish columns only in `data_loaders/`"
  is violated in ≥5 places: `calculations/opex/controllable_cost_calculations.py:217-244`
  substring-sniffs `'medelvärde'`/`'2018-2021'`; `capbase_a.parquet` has a raw `normvärde`
  column resolved by fuzzy `_resolve(cols,"normv")` **duplicated in 3 modules**;
  `calculations/capex/data_mapping.py:191-196` probes Swedish fallbacks "because the frame may
  be English or Swedish depending on load order". Fuzzy header matching can silently bind the
  wrong column — the top failure mode for AI-driven backend work.
- **Streamlit caching IS the data layer.** All 6 `data_loaders/` modules `import streamlit`
  solely for **22 `@st.cache_data`/`@st.cache_resource`** decorators that vanish in an API.
  The precompute scripts already document the weakness ("wiped on each Render redeploy").
- **The `capbase_a` memory problem (H?).** 17 MB on disk → **153 MB** deep memory (79 MB of it
  string columns), and `@st.cache_data` **deep-copies it on every access**. Measured peaks: 512
  MB idle, ~1 GB on the heavy path. Re-encoding the 7 string columns as categorical → ~80 MB.
- **Four ad-hoc path-resolution schemes** (incl. a dead `/mnt/project` fallback from a previous
  host) instead of one data root — everything silently assumes the process starts at repo root.
- **Format choice is accretion, not policy.** Reference tables are split csv/parquet with no
  rule; `all_adjust_vars.csv` (371 KB, 66 numeric cols) is dtype-lossy CSV with unknown origin.
- **The precompute-bundle pattern is the best idea in the layer** (manifest + config-signature
  guard + drift test, `data/new_benchmarking/`) — generalize it into one derived-data
  convention. StoNED (`data/stoned/`) is the unguarded one: no signature, no hashes, no test,
  and live recompute is impossible (remote solver, `pystoned` not even in requirements).
- **Stray/dead data:** `Normvärdeslista-2024-2027.xlsx` sits git-tracked in repo root (it is
  the raw source for `normvärde` unit prices, referenced only in prose); `data/examples/` (1.3
  MB) is referenced by no code; `data/reference/avg_norm_value_by_category.parquet` has **no
  generating script** (provenance gap).

---

## 3. Naming & identifiers

- **Year-suffixed wide columns hard-code the regulatory period (H).** 20 per-year constants
  (`COL_CAPITAL_COST_2024..2027`, etc.) plus PID_CPI_2024..2027. The source data is already
  **tidy long** (`capcost_a` is `(id_network, cat_encode, time)`); the code pivots long→wide
  then re-sums named columns by hand in ≥5 places (`~80` grep hits for `_2024/.../_2027`). This
  is *why the calculations look more complex than they are* — most per-year code collapses to a
  `groupby('year')`. A JSON API returning `capital_cost_2024..2027` fields is period-bound and
  hostile to a React frontend that wants to iterate years.
- **Three drifting naming layers for the same parameter (H).** Swedish `ui_config` key
  (`trunkering_max`) → English dataclass field (`truncation_max`) → registry selection key
  (`m3.incentive_params` vs ui_config `m3_quality_adjustments`; module `m7` vs `addon_benchmarking`;
  there is no `m6`). `DEFAULT_UI_CONFIG` declares 3 m5 keys while the adapter reads 7 — the
  schema is implicit and has drifted. These Swedish keys are the **persisted Firestore format**.
- **User-manual PID numbers as code keys, with live collisions (M).** `'3.6.1'` is bound to two
  different parameters in two files; `'3.7.X'` is cited but doesn't exist; `PID_TRUNC_MIN = ''`
  is an empty-string sentinel. Manual numbers are a genuine regulator-facing convention — keep
  them as **display metadata**, not keys. (The collisions sit in two dead functions, so they're
  latent, not active — but exactly the trap to remove before they become an API contract.)
- **Four company-ID systems where one suffices (M).** REId / id_network / DMU / id_firm. **DMU
  is dead** (0 uses outside passthrough). The mechanical REL-conversion is reimplemented **8
  times** (`f"REL{x:05d}"` in 5 sites + `int(x.replace("REL",""))` etc.). Caveat: one company
  in the reference table uses a `RET` prefix, which every inline `REL`-formatter would corrupt
  (currently inert — excluded from the active set).
- **Swedish leaks past the boundary into `calculations/` (M)** — function names
  (`read_normvarde`, `halvar_to_time_code`), an internal `metod` column, Swedish docstrings.
- **Ei encodings are correct to keep but under-documented (M).** Half-year timecodes 229–236
  have the formula written **twice with different anchors** (`time_codes.py` uses `2024+...`;
  `kent_capbase_prep.py:232` uses a `1910` epoch that appears nowhere else). `get_category_encode`
  **silently returns 17 (Transformator)** for any unrecognized KENT text — a data-correctness
  trap hiding behind an encoding.
- **`kpi` is a Swedish false-friend** — it means **CPI** (consumer price index), not
  key-performance-indicator. To an English-trained model `df['kpi']` reads as the wrong thing.

**Swedish/Ei keep-list (document, don't translate):** `REId`/`REL`, `KENT`, `NUAV`,
`cat_encode`, `ekdep`/`maxdep`, the half-year timecodes, the Bilaga-4 variable names
(`nf_norm`, `ug_obs`, `cemi4_*`, `ait_*`, `aif_*`, `ame_*`), `sni` (customer-type code),
`normvärde`, `anskaffningsvärde`, `förläggningsmiljö`, `jordkabel`/`nätstation`, and the
statutory Swedish asset-category names (as canonical labels). **Translate/retire:**
`trunkering`, `paverkbara`, `outlier_krav`, `kunddelning`, `realiseringstid`, `tillsynsperiod`,
`halvar`, `metod`, `grunddata` (→ "source data"). **Rename `kpi` → `cpi_factor`** in the new
schema (with a metadata note "Ei name: KPI") — but not in place, because it is a persisted key.

---

## 4. State, config & API readiness

- **`ui_config` is an untyped `Dict` with an implicit, drifted schema (H).** Modules write keys
  the declared `DEFAULT_UI_CONFIG` doesn't contain; the **None-means-baseline convention is
  already broken** by widget-persistence blocks that copy unchanged baseline values back into
  the config (`m5_efficiency.py:167-177`, `m3_cost_of_capital.py:114-138`), causing spurious
  "modified/unsaved" states and type instability (`8` vs `8.0`).
- **A pipeline artifact is stored inside the config (H).** After compute,
  `case_result.pre_dea.user_capbase_a` is serialized to parquet and written **back into**
  `ui_config["m1_asset_base"]["kent_capbase_parquet"]` (`case_actions.py:125-132`), then
  base64-inlined into the Firestore doc — output flowing backwards into user input, breaking
  the config-hash cache key and risking the 1 MiB doc limit.
- **Saved cases are unversioned with heuristic deserializers (M).** No `schema_version`;
  `_convert_numeric_keys` converts *every* digit-string key to int (lossy); tuple-keyed
  incentive dicts can't survive JSON. There is no migration path.
- **The 673-LOC `config_adapter` is "the only bridge" — and the claim mostly holds** (verified:
  `CaseDefinition` is constructed only there, in the baseline factory, and in tests), but two
  side-channels duplicate the mapping, and the adapter is essentially a **renaming layer**
  (Swedish keys → English fields) that disappears once the config is typed.
- **The three-level config model (working/computed/saved) is the right design** and largely
  extractable; `compute_config_hash` is the portable kernel — but it is **not type-stable** for
  values a JSON API sends (`8` vs `8.0`, numpy scalars, set vs list all hash differently), and
  **every save/load round-trip changes the hash** (a `None` key is dropped on save), so the
  planned cache key is broken from day one.
- **Auth keepers vs discards.** Keep: the custom-claims `{role, reid}` model, `verify_id_token`
  claim extraction, admin claim management, the Firestore wrapper. Discard: `pyrebase4`
  (unmaintained, forces pinned `urllib3`), the JS-set cookie session, the dialog flow, and all
  `st.*` coupling. Extract a UI-free `verify_token(id_token) -> AuthContext` as FastAPI
  middleware.

---

## 5. Calculations core (the part that survives)

The legacy core (`capex/`, `opex/`, `frontier/`, `incentive/`, `efficiency/`,
`revenue_frame_assembly.py` — ~3,600 LOC) is **genuinely sound**: KENT steps 5–8 process the
full 496,077-row capbase in 0.51 s, the math is mostly vectorized, and mass is roughly
proportional to domain complexity. The real issues are concentrated:

- **The only true performance bottleneck is the DEA solver, not problem size (H).**
  `dea_calculations.py:166-214` solves one LP per company via `pulp.PULP_CBC_CMD` (a
  **subprocess + LP file per solve**), 296 LPs/run = **6.5 s measured**. An equivalent
  `scipy.optimize.linprog(method='highs')` formulation measured **~0.18 s (≈16× faster)** — and
  scipy is already installed. **The precompute-bundle and caching machinery largely exists to
  work around this self-inflicted cost.** Also replace the `"OUTLIER"` *string sentinel* in a
  numeric column with `np.nan` + a status column.
- **`new_benchmarking` breaks the pure-calculations contract (H).** `import
  calculations.new_benchmarking.capex_environment` pulls in **streamlit** (via a top-level
  `from data_loaders.rab_data import ...`). Make calculation entry points take DataFrames as
  required parameters; move the in-package `data.py` loaders to `data_loaders/`.
- **A second architecture is growing inside `calculations/new_benchmarking/` (H).** The three
  subpackages each carry `config.py` + `data.py` + `calibration.py` + `test_*.py` +
  `run_example.py` **inside the package** (411 LOC of tests that `pytest` doesn't even collect,
  since `testpaths = tests`). ~230 lines are duplicated between `environment_capex_adjustment`
  and `station_capex_adjustment` (two frozen dataclasses with the *same name*). Flatten to one
  convention: I/O in `data_loaders/`, tests in `tests/`, one parametrized adjustment module.
- **Regulatory constants restated in 10+ sites (M)** — `0.30 / 0.50 / 8 / 4` appear as literals
  across `efficiency_requirement.py`, `case_definition.py`, `config_adapter.py` (twice),
  `new_benchmarking/config.py`. One `regulatory_constants` source; functions take required
  params.
- **KENT Excel parsing lives in `calculations/` (M)** — it is *parsing*, not calculation; move
  to the load/upload boundary.
- Minor: `print()`-based logging contradicts the repo's own convention; a handful of dead
  functions; per-row `iterrows`/`apply(axis=1)` over 148 rows (readability cost, not perf);
  `range(229, 237)` hardcoded 8× despite an existing time-code config.

---

## 6. Frontend ↔ backend boundary (logic that must move below the API line)

Better than typical Streamlit apps — `calculations/` is pure, `export_excel.py` and
`result_snapshot.py` are already Streamlit-free — but a consistent band of **business logic
sits above the future API line** and would be silently lost or re-invented in a React rewrite:

- **The revenue-frame decomposition is derived three independent times (H)** —
  `visualization/diagram_data.py:33-276`, `pages/4_revenue_frame.py:243-255`, and
  `export_excel.py` — with no canonical pipeline output. Make it a first-class result object
  (`RevenueFrameDecomposition`, English keys) computed once server-side and consumed by the API,
  the Excel export, and React.
- **A regulatory formula is re-implemented in a frontend chart helper (H)** —
  `_efficiency_charts.py:50-54` duplicates the truncation-min formula from
  `efficiency_requirement.py:25-56`. Emit it from stage 5 instead.
- **`pipeline/result_helpers.py` mixes all three target layers (M)** — server-side aggregation
  + client-side string formatting (`fmt_tkr`) + Plotly trace construction, in one module inside
  `pipeline/`. Split: aggregation stays server-side; formatting moves to React `Intl`; chart
  construction is throwaway.
- **Output modules bypass `PipelineResult` and read `capcost_a.parquet` directly (M)** for
  baseline category data, with `getattr(case.pre_dea, 'df_by_category', None)` probing of frozen
  dataclasses. Make per-category detail an explicit result field.
- **`m3_cost_of_capital_output.py` is 651 LOC of superseded, still-wired code (M)** — delete.
- **Sector statistics (rank, peer, percentiles) computed independently in four places (M).**
- **`result_snapshot.py` is already the results-summary endpoint payload (L)** — pure, tested —
  just filed in `frontend/` with a flat key scheme. Move it below the line.
- **`pages/4` embeds business rules (M)** — per-module "modified" predicates re-hardcoding
  regulatory defaults inline (`abs(trunkering_max - 0.30) > 1e-9`, etc.).
- `visualization/geo_data.py` is **not** Streamlit-free (contradicts ARCHITECTURE.md) and
  computes per-customer KPIs in the visualization layer.

---

## 7. Documentation & repo hygiene

- **No per-directory READMEs except 3 leaf subpackages; no root `README.md` (H).** Ten
  top-level packages (~30k LOC) and every `data/` subdirectory are undocumented — the **opposite**
  of the per-directory, machine-friendly structure the rebuild needs. (The 3 that exist, under
  `new_benchmarking/`, are high-quality but contain **stale import paths and Windows commands**.)
- **ARCHITECTURE.md has materially drifted on ≥8 verifiable claims (H)** — Python 3.11 vs actual
  3.12; `venv/`+pip vs `uv`+`.venv/`; a `secrets.toml.example` that doesn't exist; a documented
  `@st.cache_resource` session store that **no longer exists in code**; a `data/updated_shapefiles/`
  directory that isn't on disk; wrong `asset_categories.py` field names. **AI agents treat this
  doc as ground truth** — drift is costly. Shrink it to what can't be derived from code; push
  trees/tables into per-directory READMEs; add a CI check for mechanically-verifiable claims.
- **The 275-test facit suite is a strong rewrite spec — but transitively requires Streamlit**
  via `data_loaders` (H). Strip `@st.cache_data` out of the loaders (plain functions; cache at
  the Streamlit edge) so the spec runs Streamlit-free, and add `pure`/`data`/`integration`
  pytest markers.
- **`new_benchmarking_model/` at repo root** holds docs for `calculations/new_benchmarking/`
  (confusing split; includes a 0-byte committed file). Working notes, finished plans, and
  meeting scratch are interleaved with importable code (`landing_pages/tankar.md`,
  `efter_möte.md`, `plans/`). Move to a `notes/` area.
- **Five deleted-but-still-tracked files** (incl. a 3 MB stray PDF) sit uncommitted; commit the
  cleanup. The `.git` is ~113 MB — consider a fresh history when carving out the new repo.
- **`requirements.txt` is unpinned, has no lockfile, and lists 4 never-imported heavy deps**
  (`folium`, `streamlit-folium`, `matplotlib`, `libpysal`). `docs/ei_to_markdown/` (regulatory
  primary sources with excellent frontmatter) is the **right pattern** — just add an index.

---

## 8. Security & authorization gap (H — found along the way)

Not part of the original brief, surfaced by the completeness critic, and **the weakest
dimension of the app.** Most of it cannot be carried into the rebuild, and several items are
exploitable today:

- **Anyone can self-provision regulator access.** `auth_dialog.py:114-135` lets an
  unauthenticated visitor pick `role` ∈ {company, regulator} and any company's REId; these are
  written **straight into Firebase custom claims** at sign-up (`firebase_auth.py:152-157`) with
  no approval. → In the rebuild, registration creates users with **no role**; claims are set
  only by a server-side admin endpoint after approval / via invite token.
- **Saved cases are scoped by REId string, not user uid** (`case_storage.py:287`), so a
  regulator and a company user share/leak case lists, including uploaded KENT data. → Key case
  docs by `owner_uid`; enforce ownership in API middleware.
- **A 30-day Firebase refresh token is stored in a JS-set, non-HttpOnly cookie**
  (`cookie_session.py:34-52`). → Browser should never hold a raw refresh token; use the Firebase
  JS SDK + short-lived ID-token verification, or an HttpOnly session cookie minted server-side.
- **All authorization is application-code-only; the admin SDK bypasses Firestore rules and no
  rules files exist in the repo.** → Commit `firestore.rules` (`allow read, write: if false;`
  if all access goes through the API) + `firebase.json`, deployed via CI.
- **Production auth can be disabled by a single `skip_auth` secrets flag with no environment
  guard**; `showErrorDetails = true` ships full stack traces to end users; the devcontainer
  disables CORS/XSRF.

---

## 9. Deployment & runtime (mostly `unverified` — cutoff)

> Evidence gathered but not independently re-checked; treat as strong leads.

- **No deploy-as-code:** no `render.yaml`, `Dockerfile`, `Procfile`, lockfile, or pinned Python
  version anywhere — the entire production contract lives in the Render dashboard, traced in-repo
  only by a hardcoded `/etc/secrets/secrets.toml` path.
- **Single-process runtime model:** `st.session_state` for all working state, cache singletons,
  module globals, and per-call deep copies of the 153 MB capbase — all break or multiply under a
  multi-worker uvicorn/gunicorn API. Design the new API as **stateless workers** (clients in a
  FastAPI lifespan hook; immutable reference data loaded once at startup; per-case state in
  Firestore).
- **Unpinned deps already bite:** the installed `pandas 3.0.3` crashes the `PARAMETER_CHANGE`
  path. Pin Python 3.12 everywhere; adopt `pyproject.toml` + committed `uv.lock`;
  `uv sync --frozen` in Docker; a CI job that runs the full pipeline (incl. the KENT-batch path)
  on the locked set.

---

## Target building blocks

This is the opinionated target. Assumes **FastAPI + pydantic v2**. Optimized for AI-agent
development: unambiguous structure, one source of truth per concept, a README in every
directory.

### Target directory layout

```
backend/                              # the new Python API (own repo or top-level dir)
├── README.md                         # entrypoint context for agents: layers, how to run
├── pyproject.toml  uv.lock  .python-version(3.12)  Dockerfile  render.yaml
├── api/                              # FastAPI: routers, request/response pydantic models, deps
│   ├── README.md
│   ├── main.py                       # app factory + lifespan (load reference data once)
│   ├── deps.py                       # auth middleware: verify_token -> AuthContext
│   ├── routers/ {companies, cases, compute, benchmarking, results, geo, parameters}.py
│   ├── schemas/ case_config.py result.py decomposition.py   # the API contract (= the models)
│   └── serializers/                  # per-company view, decomposition, sector stats (was "extraction")
├── compute/                          # the ~600-LOC orchestration (replaces pipeline/)
│   ├── README.md                     # the 3-node DAG, the composer, the result container
│   ├── capital_costs.py  efficiency.py  revenue_frame.py  compose.py  result.py
│   └── validate.py                   # the genuine invariants (148 companies, TOTEX=CAPEX+OPEX)
├── calculations/                     # PURE math, ported ~as-is (the survivors)
│   ├── README.md                     # the layer rule: no I/O, no streamlit, English only
│   ├── capex/ opex/ frontier/ incentive/ efficiency/ revenue_frame_assembly.py
│   └── new_benchmarking/             # flattened: no in-package data.py/tests/run_example
├── data_access/                      # the load layer (was data_loaders/, streamlit-free)
│   ├── README.md
│   ├── catalog.py                    # eager load of staging parquet at startup -> immutable frames
│   └── paths.py                      # ONE data root from env; no search lists
├── auth/                             # UI-free: verify_token, claim management, firestore client
├── domain/                          # config/ renamed: pure constants & the registry
│   ├── README.md
│   ├── parameters.py                 # the ParameterSpec registry (was glossary.py)
│   ├── companies.py  asset_categories.py  time_codes.py  regulatory_constants.py
│   └── columns.py / schemas.py       # per-dataset column schemas (pandera/typed)
├── scripts/                          # ALL offline builds (raw->staging->derived)
│   ├── README.md
│   └── build_staging.py  build_derived.py  build_geo.py  precompute_*.py
├── data/
│   ├── README.md                     # provenance of EVERY file: source, columns, dtypes, script
│   ├── raw/                          # immutable Ei/SDF sources (xlsx, the root Normvärdeslista, shapefiles)
│   ├── staging/                      # all parquet, English columns, REId key, tidy long (built)
│   └── derived/                      # stoned/, new_benchmarking/, geo/ — each with manifest.json
├── tests/                            # the facit suite, made streamlit-free; markers: pure/data/integration
└── docs/
    ├── README.md (index)
    ├── ei_sources/                   # the ei_to_markdown library + an index table
    └── domain/                       # dependency_graph.md, the two-sided interpretation note
```

### Data store design (`raw → staging → derived`)

- **`data/raw/`** — immutable regulatory sources in their native format (the 3 xlsx workbooks,
  `Normvärdeslista-2024-2027.xlsx` moved here, shapefiles). Never parsed at request time.
- **`scripts/build_staging.py`** — does **all** reconciliation once: name override, OPEXp
  replacement, return aggregation, Swedish→English rename, `normvärde → norm_value`, flatten the
  SDF controllable sheet to named columns, standardize **every table on REId**. Writes
  `data/staging/*.parquet` + a `manifest.json` (`{input_file_hashes, generated_at, code_version}`)
  and **fails loudly** on any schema surprise (no sheet-fallback, no `except: continue`).
- **`data/staging/`** — typed parquet, English columns, **tidy long format** (year as a column),
  validated by explicit schema asserts. The API reads these as **dumb `pd.read_parquet`**.
- **`scripts/build_derived.py` + `data/derived/`** — one uniform bundle convention for stoned,
  new_benchmarking, geo: every directory has `manifest.json` with `{config_signature,
  input_file_hashes, code_version, generated_at}`; the loader **verifies and raises** (or returns
  a 503-able state) instead of silently recomputing live. Re-encode `capbase_a` string columns
  as categorical at write time (~153 MB → ~80 MB).
- **Loading at runtime:** a `data_access/catalog.py` that eagerly loads the small staging frames
  into **immutable module-level singletons in the FastAPI lifespan hook** (total staging ≈ 25 MB),
  with `functools.lru_cache` for per-company slices. No TTLs, no `@st.cache_data`.

### Compute core design

Three pure functions + one composer, calling the existing `calculations/` entry points
unchanged:

```python
# compute/capital_costs.py
def capital_costs(baseline: BaselineData, cfg: CapexConfig) -> CapitalCostResult:
    """KENT recompute or baseline passthrough. Returns df + method metadata
       (capbase_source/capex_method) — post_dea branches on these."""

# compute/efficiency.py     (independent of capital_costs)
def efficiency(baseline: BaselineData, cfg: EfficiencyConfig) -> EfficiencyResult:
    """DEA (scipy/HiGHS) | published table | StoNED file. 148-row frame."""

# compute/revenue_frame.py
def revenue_frame(cap: CapitalCostResult, eff: EfficiencyResult,
                  baseline: BaselineData, cfg: FrameConfig) -> RevenueFrameResult:
    """Eff-req + incentives + assembly. Apply each user adjustment ONCE here."""

# compute/compose.py  (~30 lines)
def run(baseline, case: CaseConfig) -> ComputeResult:
    cap = capital_costs(baseline, case.capex)
    eff = efficiency(baseline, case.efficiency)
    return ComputeResult(cap, eff, revenue_frame(cap, eff, baseline, case.frame))
```

- **Precompute the baseline result once globally** (it is a pure function of static data —
  verified identical across all users/sessions). The case endpoint computes only the case run
  and returns case + delta. This deletes `result_snapshot.py`'s reason to exist.
- **Per-company extraction is a serializer**, not a stage: `result.for_company(reid)` /
  `api/serializers/`.
- **One result container** with the few frames the API serializes — no 42-field frozen-dataclass
  layer; use pydantic models at the API boundary where validation/serialization pays.

### Config model (the contract)

**One pydantic `CaseConfig`** = the API request body = the Firestore document = the validation
boundary = the adapter (the 673-LOC adapter and `DEFAULT_UI_CONFIG` are deleted):

```python
class M5EfficiencyConfig(BaseModel):
    truncation_max: float = 0.30          # English names, from ParameterSpec
    outlier_requirement: float = 0.01
    realization_time: int = 8
    customer_sharing: float = 0.50
    supervision_period: int = 4
    controllable_method: Literal["OPEX","TOTEX"] = "OPEX"
    @model_validator(...)                 # cross-field invariants live here

class CaseConfig(BaseModel):
    schema_version: int = 2               # <-- versioned from day one; migrations on read
    user_reid: str
    capex: CapexConfig; efficiency: EfficiencyConfig; frame: FrameConfig
```

- Uploaded files go to **object storage** (GCS/Firebase Storage); the case doc holds
  `kent_upload_id` / `capbase_artifact_id`, never inlined bytes.
- `compute_config_hash` becomes a hash of the validated model (type-stable, artifact IDs not
  bytes-length); "stale results" = `response.config_hash != working.hash`.

### API surface (FastAPI)

```
GET  /companies                          -> [{reid, name, name_short}]
GET  /companies/{reid}/baseline          -> baseline frames (cacheable, deterministic)
GET/POST /cases   GET/PUT/DELETE /cases/{id}   POST /cases/{id}/duplicate
POST /uploads/kent  (file)               -> {upload_id, capbase_artifact_id}
POST /compute       {case_config}        -> {result_id, config_hash}
GET  /results/{result_id}                -> {case, baseline, delta, decomposition, sector_stats}
GET  /results/{result_id}/export.xlsx    -> server-side openpyxl render
POST /benchmarking/mini-run {eff_config} -> fast DEA-only feedback (= efficiency() directly)
GET  /benchmarking/new                   -> precomputed new-benchmarking bundle
GET  /geo/areas.geojson                  -> static simplified GeoJSON (built offline)
GET  /parameters                         -> the ParameterSpec registry (drives React inputs + validation)
GET  /glossary                           -> PID/label/unit metadata for the UI
```

Auth: `verify_token(Authorization: Bearer)` middleware → `AuthContext(uid, email, role, reid)`;
reject `email_verified is False`; ownership enforced per-route.

### Naming & conventions

- **One company key: REId (string)** everywhere below the load boundary. `id_network`/`name` are
  attributes in a single `companies` dimension table. **Delete DMU.** One pair of conversion
  functions in one module.
- **Tidy long format** for per-company/per-year measures (`company_id, year, measure, value`) or
  `{year: value}` maps in API responses. Wide only at the presentation edge. `REGULATORY_PERIOD
  = range(2024, 2028)` named once.
- **Semantic parameter keys**; user-manual PIDs are metadata served by `/glossary`. Forbid PID
  literals outside the registry.
- **`ParameterSpec` registry** (evolve `glossary.py`): `key, manual_id, label, help, unit,
  value_type, ge, le, ui_step, ui_format, default, scope, stage, provenance`
  (`hard` | `regulatory_baseline` | `ui_hint`). Single source for the metadata endpoint, the
  request-validation models, and defaults.
- **English everywhere below the API** except the documented Swedish/Ei keep-list (§3). Rename
  `kpi → cpi_factor` in the new schema.
- **Per-dataset column schemas** (pandera/typed) validated at function boundaries, so misspelled
  columns fail loudly — replaces the bypassed `COL_*` string constants.

### What survives from the current repo as-is (or nearly)

- **`calculations/capex/`, `opex/`, `frontier/` (re-solver only), `incentive/`, `efficiency/`,
  `revenue_frame_assembly.py`** — the math. Port with minimal change; remove `print()`, the
  KENT-Excel parsing (→ load boundary), and embedded constants.
- **`config/case_definition.py`** (enums + dataclasses) — becomes the pydantic models.
- **`config/glossary.py`, `asset_categories.py`, `time_codes.py`, `colors.py`, `formatting.py`,
  `incentive_parameters.py`** — domain constants, mostly intact.
- **The 275-test facit suite** — the golden master. Make it streamlit-free first; it then proves
  the rebuilt core equivalent.
- **`result_snapshot.py`, `export_excel.py`** — already Streamlit-free; move below the line.
- **The precompute pattern**, the auth claims/role model, the `docs/ei_to_markdown/` library.

### Migration order (each step independently shippable; Streamlit stays runnable until cutover)

1. **Hygiene + safety now (no rewrite):** commit pending deletions; pin `pandas<3` (or fix the
   `float32` setitem); delete the 4 unused deps; fix `showErrorDetails`; **close the
   self-provisioning auth hole** (server-side claim assignment) — this is exploitable today.
2. **Make the test suite streamlit-free** — strip `@st.cache_data` from `data_loaders/` (cache at
   the Streamlit edge). Now the facit suite is a portable spec.
3. **Build the `raw → staging` layer** — `scripts/build_staging.py` + `data/staging/*.parquet` +
   `data/README.md` provenance. Point the *existing* loaders at staging (behavior unchanged,
   tests green). This de-risks everything downstream.
4. **Add per-directory READMEs + shrink ARCHITECTURE.md** — cheap, high-leverage for the agents
   doing the rest.
5. **Swap DEA to scipy/HiGHS** behind the existing interface; re-validate against facit; then
   re-evaluate whether the precompute machinery is still needed.
6. **Collapse the pipeline** to `compute/` (3 functions + composer) behind the current
   `run_pipeline` signature; golden-master against the current `PipelineResult` (the facit suite
   + a snapshot diff). Delete stages 1 & 4, `debug_logger`, `mini_run` duplication.
7. **Type the config** — pydantic `CaseConfig` + `ParameterSpec` registry; write the one-time
   Firestore migration; delete the adapter and Swedish keys.
8. **Stand up FastAPI** over the now-clean core (endpoints above; auth middleware; object storage
   for uploads). Run it alongside Streamlit.
9. **Build the React/Next.js frontend** against the API; cut over; retire Streamlit.

---

## Appendix A: complete findings index

All 105 findings, grouped by dimension. Severity is the **verifier-calibrated** value where it
differs from the original. Status: `✓` confirmed · `±` adjusted · `?` unverified (session
cutoff). The titles below already reflect the corrected claim where it changed.

> **Full evidence archive:** the complete per-finding detail — evidence with `file:line`
> references, rationale, recommendation, and the adversarial verifier's correction for every
> one of the 105 findings — is preserved in
> [backend_rebuild_findings.md](backend_rebuild_findings.md). This appendix is the
> index; that file is the deep reference.

### 1. Pipeline (overengineering)

| Sev | Status | Finding |
|:---:|:------:|---------|
| H | ± | 2 of 5 stages are ceremony; pipeline is a linear chain over what is actually a 3-node DAG |
| H | ± | Baseline result is recomputed per session although it is a pure function of static data |
| H | ± | OPEX scaling/override (4.1.1/40.1.1) is implemented twice, in two different stages, on two different tables |
| M | ± | Extraction stage is a per-company view masquerading as a pipeline stage |
| M | ✓ | debug_logger is 363 LOC of print-based scaffolding, enabled by default in production |
| M | ± | Frozen-dataclass layer (42 fields) provides fake immutability and carries dead fields |
| M | ✓ | mini_run.py duplicates the pipeline path with separately-maintained defaults |
| M | ✓ | pipeline/ package contains 1,692 LOC of UI/reporting code, inverting the layer boundary |
| M | ✓ | Silent except-Exception fallbacks mask failures while the unguarded path actually crashes |
| L | ✓ | Clean-rebuild sizing: ~2,050 LOC of orchestration collapses to ~550-650 LOC |

### 2. Data management & formats

| Sev | Status | Finding |
|:---:|:------:|---------|
| H | ± | No raw→staging build step: loader re-derives and reconciles three overlapping sources at every cold start |
| H | ✓ | Swedish-column boundary leaks: raw SDF sheets and 'normvärde' force fuzzy header sniffing inside calculations/ |
| H | ± | Streamlit caching is the de facto data layer — 24 @st.cache decorators, all of which disappear in the API backend |
| M | ✓ | Runtime xlsx parsing with sheet-name guessing and silent failure — fragile more than slow |
| M | ✓ | Four ad-hoc, CWD-relative path-resolution schemes (incl. dead /mnt/project fallback) instead of one data root |
| M | ✓ | Three company-key systems (REId, id_network, DMU) with REL-string formatting re-implemented in four places |
| M | ± | Precompute-bundle pattern (manifest + signature guard + drift test) is sound — generalize it, and harden its failure mode |
| L | ✓ | csv/parquet/xlsx format choice is accretion, not policy |
| L | ± | 2-second runtime shapefile processing should be a precomputed derived artifact |
| L | ± | Stray and dead data files: tracked root xlsx, 1.3 MB unused examples, stale doc entries |

### 3. Naming & identifiers

| Sev | Status | Finding |
|:---:|:------:|---------|
| H | ✓ | Year-suffixed wide columns hard-code the 2024-2027 regulatory period into identifier names |
| H | ± | Three drifting naming layers for the same parameters (Swedish ui_config keys, English dataclass fields, registry selection keys) |
| M | ± | User-manual PID/VID numbers used as string keys, with internal collisions and drift — demote to display metadata |
| M | ± | Four company-ID systems where one suffices; DMU is dead and REId↔id_network conversion is reimplemented 8 times |
| M | ✓ | Swedish leaks past the stated load boundary into calculations/ |
| M | ✓ | Ei encodings (cat_encode 1-17, timecodes 229-236) are correct to keep but their definitions are duplicated and under-documented, with a silent default to category 17 |
| M | ± | Canonical column constants exist but are bypassed by raw strings ~30 times in calculations/pipeline |
| L | ± | Explicit keep-list for Swedish/Ei domain terms (and a KPI/CPI false-friend to fix) |
| L | ✓ | Misleading file-path headers and mojibake in backend files actively misdirect AI agents |

### 4. State, config & API readiness

| Sev | Status | Finding |
|:---:|:------:|---------|
| H | ✓ | ui_config schema is implicit and has drifted from DEFAULT_UI_CONFIG in at least 4 modules |
| H | ± | None-means-baseline convention already broken by widget-persistence workarounds; type-unstable values cause spurious 'modified/unsaved' states |
| H | ± | Pipeline artifact stored inside config and base64-inlined into the case document — exceeds Firestore's 1 MiB doc limit; uploads never durably persisted |
| M | ± | Saved-case Firestore schema is unversioned; deserialization relies on lossy heuristics; no migration path |
| M | ✓ | Case ownership keyed by company REId, not user identity — regulator and company users share/leak case lists |
| M | ✓ | Three-level config (working/computed/saved) is the right model and largely extractable; compute_config_hash is the portable kernel |
| M | ± | Persistence layer writes Streamlit widget keys — storage coupled to widget naming conventions |
| M | ✓ | Auth: claims/role model and admin verification are keepers; pyrebase4 client, JS cookie sessions, and st.* coupling are not |
| M | ± | The 'only bridge' claim mostly holds, but two side-channels duplicate the ui_config→pipeline mapping |
| M | ± | Swedish and ID-cryptic key names are persisted in case documents and will freeze into the API contract unless migrated |
| L | ✓ | Implied API surface is derivable and small; three current flows have no clean server-side equivalent |

### 5. Calculations core

| Sev | Status | Finding |
|:---:|:------:|---------|
| H | ✓ | DEA bottleneck is the PuLP+CBC solver, not the problem size — 16x speedup available with scipy already installed |
| H | ✓ | new_benchmarking breaks the pure-calculations contract: importing it loads streamlit |
| H | ± | A second architecture is growing inside calculations/new_benchmarking (in-package configs, loaders, tests, example runners) |
| M | ± | ~230 lines duplicated between environment_capex_adjustment and station_capex_adjustment, with a third copy of the loaders in capex_environment.py |
| M | ✓ | Regulatory constants (0.30 truncation, 0.50 sharing, 8-year realization, 4-year supervision) restated in 10+ code sites |
| M | ✓ | KENT Excel parsing with Swedish identifiers lives inside calculations/ (load-boundary violation) |
| M | ✓ | print()-based logging inside calculations contradicts the repo's own no-print convention |
| L | ± | Dead and vestigial code in the compute core |
| L | ± | Per-row Python over 148-row frames — a readability cost, not a performance one |
| L | ± | Presentation logic embedded in the calculations layer |
| L | ± | Half-year time codes 229-236 hardcoded throughout kent_calculations.py despite an existing time-code config |

### 7. Docs & repo hygiene

| Sev | Status | Finding |
|:---:|:------:|---------|
| H | ✓ | No per-directory READMEs anywhere except three leaf subpackages; no root README.md |
| H | ✓ | ARCHITECTURE.md has materially drifted from the code on at least 8 verifiable claims |
| H | ± | Test suite is a strong rewrite spec, but transitively requires Streamlit via data_loaders |
| M | ✓ | All three new_benchmarking subpackage READMEs contain stale, non-working import paths and Windows commands |
| M | ± | Docs for calculations/new_benchmarking/ split into root directory new_benchmarking_model/ that looks like a package, including a committed empty file |
| M | ± | Five deleted-but-uncommitted tracked files, including a 3 MB stray PDF, plus an orphan root xlsx |
| M | ± | Meeting notes, finished plans, and superseded specs interleaved with importable code |
| M | ± | requirements.txt: unpinned, carries four never-imported heavy dependencies, no lock file despite uv workflow |
| L | ± | docs/ei_to_markdown/ is the right primary-source pattern but has no index and is referenced nowhere |

### 6. Frontend↔backend boundary

| Sev | Status | Finding |
|:---:|:------:|---------|
| H | ✓ | Revenue-frame decomposition is derived three times above/at the boundary, with no canonical pipeline output |
| H | ✓ | Regulatory truncation formula re-implemented in a frontend chart helper |
| M | ± | pipeline/result_helpers.py mixes all three target layers (aggregation, string formatting, Plotly traces) inside the pipeline layer |
| M | ± | Output modules bypass PipelineResult and read capcost_a.parquet directly for baseline category data |
| M | ✓ | m3_cost_of_capital_output.py is 651 LOC of superseded code still wired into the package |
| M | ✓ | Incentive waterfall decomposition and cap-binding rule computed inside render code |
| M | ± | Sector statistics (rank, peer, outcome counts, percentiles) computed independently in four places above the line |
| M | ± | pages/4 embeds business rules: per-module 'modified' predicates with re-hardcoded regulatory defaults |
| L | ± | geo_data.py is not Streamlit-free (contradicts ARCHITECTURE.md) and computes per-customer KPIs in the visualization layer |
| L | ✓ | result_snapshot.py is already the results-summary endpoint payload — but filed in frontend/ with a flat key scheme |
| L | ✓ | export_excel.py is correctly server-side but inlines design-system constants |

### 8. Security & authorization

| Sev | Status | Finding |
|:---:|:------:|---------|
| H | ✓ | Anyone can self-provision regulator-level access (open registration writes role/REId straight into custom claims) |
| H | ✓ | Saved cases (including uploaded KENT capital-base data) are scoped by REId string, not by user uid |
| H | ✓ | 30-day Firebase refresh token stored in a JavaScript-set, non-HttpOnly cookie |
| H | ✓ | All authorization is application-code-only; admin SDK bypasses Firestore rules and no rules files exist in the repo |
| M | ± | Email verification — the only registration gate — is bypassable via the cookie-restore path |
| M | ± | Production auth can be disabled by a single secrets-file flag with no environment guard |
| M | ± | showErrorDetails = true ships full stack traces to end users in production |
| L | ✓ | Devcontainer launches Streamlit with CORS and XSRF protection disabled |

### 9. Deployment & runtime

| Sev | Status | Finding |
|:---:|:------:|---------|
| H | ? | No deploy-as-code: production configuration exists only in the Render dashboard |
| H | ? | Unpinned dependencies, no lockfile — and the heavy pipeline path already crashes under today's resolution (pandas 3.0.3) |
| H | ? | Runtime model is hard-wired to one process: session_state, cache singletons, and module globals all break or multiply under a multi-worker API |
| H | ? | capbase_a dominates memory: 17 MB parquet inflates to 153 MB and @st.cache_data deep-copies it on every access; measured peaks 512 MB idle / 1,029 MB on the heavy path |
| M | ? | Secrets contract is implicit, dual-path, and includes an auth-bypass flag on the same channel |
| M | ? | Python version drift across four sources of truth; production version unrecorded |
| M | ? | ARCHITECTURE.md documents a per-user @st.cache_resource session store that no longer exists in code |
| M | ? | Deploy image carries dead heavy dependencies and an unnecessary system-GDAL step; the entire runtime geo stack is eliminable |
| M | ? | Data file resolution depends on CWD and contains a dead /mnt/project fallback from a previous host |

### 10. Server-side validation & parameter registry

| Sev | Status | Finding |
|:---:|:------:|---------|
| H | ✓ | No server-side validation: widgets are the only guard, and the case-load path already bypasses them |
| H | ± | Parameter metadata (min/max/step/default/help/unit) exists only as widget kwargs, duplicated per render site |
| H | ± | Defaults re-declared in up to six places per parameter |
| H | ± | Cross-parameter invariants enforced only in the widget layer — or silently violated |
| M | ± | Regulatory vs ergonomic constraints are indistinguishable and undocumented |
| M | ± | ui_config keys are Swedish and shaped by Streamlit widget names; the adapter is a 673-LOC renaming layer |
| M | ± | Constraint derived by substring-matching a unit label string |
| L | ✓ | config/glossary.py is already 90% of the target registry — extend it rather than building parallel metadata |

### 11. Test coverage of the bridge/persistence layers

| Sev | Status | Finding |
|:---:|:------:|---------|
| H | ✓ | config_adapter.py (673 LOC, the only ui_config -> CaseDefinition bridge) has zero test coverage across all mapping branches |
| H | ? | Every save/load round trip changes compute_config_hash — the planned cache key is broken from day one (measured) |
| H | ? | compute_config_hash is not type-stable for values a JSON API will send (8 vs 8.0, numpy scalars, set vs list) |
| H | ? | Firestore deserialization is heuristic type-guessing with zero tests; tuple-keyed incentive dicts cannot survive any JSON layer |
| H | ? | Base64-inlined KENT parquet can exceed Firestore's 1 MiB document limit for large companies (measured) |
| M | ? | ui_config schema is implicit and contradictory: DEFAULT_UI_CONFIG misses keys the adapter reads, and baseline defaults are triplicated |
| M | ? | Timestamp encoding is inconsistent between Firestore and local paths, sorted by raw string comparison, untested |
| M | ? | _configs_equal is type-strict (8 != 8.0, list != tuple) with zero tests — porting it as the API staleness check inherits the trap |
| L | ? | Duplicated Firestore/local save-load implementations double the surface the characterization tests must pin |

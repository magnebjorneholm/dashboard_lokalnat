# Regumetrica - Architecture Document

## 1. Project Overview

**App name:** Regumetrica
**Domain:** Regulatory analysis of Swedish electricity distribution companies (revenue cap calculation)
**Target users:** Distribution companies and the regulator (Energimarknadsinspektionen / Ei)
**Entrypoint:** `streamlit_app.py`

The application calculates revenue caps for 148 Swedish electricity distribution companies
according to Ei's regulatory model. Users can adjust parameters (affecting all companies)
and variables (company-specific), run the calculation pipeline, and compare results
against a baseline.

> **Valuation principle (read for any värdering question):** when a question concerns the
> asset/capital-base valuation principle — kapacitetsbevarande vs förmögenhetsbevarande, the
> värdekonsistent transition for 2028–2031, or whether the pipeline / new_benchmarking_model
> data is a valid basis for a given analysis — see
> [kapitalbas_vardering_och_dashboard.md](kapitalbas_vardering_och_dashboard.md) (repo root).
> It summarises Ei's switch of valuation principle and its consequences for the dashboard
> data, with cited references to the Ei source doc
> ([docs/ei_to_markdown/outputs/inriktning-reglering-intaktsramar-2028-2031.md](docs/ei_to_markdown/outputs/inriktning-reglering-intaktsramar-2028-2031.md)).


## 2. Tech Stack

| Layer          | Technology                                        |
|----------------|---------------------------------------------------|
| Framework      | Python 3.11, Streamlit                            |
| Data           | Pandas, NumPy, PyArrow (parquet)                  |
| Visualization  | Plotly, Folium (maps), Matplotlib                 |
| Optimization   | PuLP (DEA / linear programming)                   |
| Geo            | Geopandas, Shapely, Libpysal                      |
| Auth           | Firebase Admin SDK (server), Pyrebase4 (client)   |
| Persistence    | Firestore (cases), Parquet/Excel (base data)      |
| Deploy         | Render.com, DevContainer (Python 3.11 Bullseye)   |


## Getting Started

### Prerequisites

- **Python 3.11** (check with `python --version`)
- **Git**
- **Docker Desktop** (only if using Dev Container)

### Option A: Local setup (recommended)

```bash
# 1. Clone the repo
git clone <repo-url>
cd dashboard_lokalnat

# 2. Create virtual environment
python -m venv venv

# 3. Activate it
# Windows (PowerShell):
./venv/Scripts/Activate.ps1
# Windows (CMD):
venv\Scripts\activate.bat
# Linux/Mac:
source venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Set up secrets (see below)

# 6. Run the app
streamlit run streamlit_app.py

# 7. Run tests
python -m pytest tests/ -v
```

### Option B: Dev Container

1. Install **Docker Desktop** and the VS Code extension **Dev Containers**
2. Open the repo folder in VS Code
3. Click "Reopen in Container" (or Ctrl+Shift+P → "Dev Containers: Reopen in Container")
4. Wait for the container to build and install dependencies
5. Set up secrets (see below)
6. The app starts automatically on port 8501

### Firebase Secrets

The app requires Firebase credentials in `.streamlit/secrets.toml` (gitignored).
Copy the template and fill in real values:

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

For local development **without Firebase**, use dev mode instead:

```toml
# .streamlit/secrets.toml
[dev]
skip_auth = true
```

This bypasses authentication and lets you use the app freely.


## 3. Directory Structure

```
dashboard_lokalnat/
|
|-- streamlit_app.py              # Entrypoint: two-zone controller (public landing vs authenticated tool)
|-- requirements.txt              # Python dependencies
|-- .streamlit/config.toml        # Streamlit config (theme, port 8501)
|-- static/                       # Statically served assets (enableStaticServing; served at app/static/)
|   |-- manuals/<slug>.pdf            # Per-tool manual PDFs (published by user_manual_latex/build.sh)
|   |-- manual_reader/                # Framework-agnostic in-page manual reader (reader.css + reader.js)
|   |-- login_pic.jpg                 # Landing background photo (served as app/static/login_pic.jpg)
|
|-- landing_pages/                # ZON 1: public landing (no sidebar, own top bar)
|   |-- landing.py                # Single page, three anchored sections: #home (hero),
|   |                             #   #tools (registry-driven index), #team (profiles)
|
|-- pages/                        # ZON 2: authenticated tool pages (sidebar nav, two groups)
|   |-- 1_create_and_select_case.py  # Create/load/delete/duplicate/compare cases
|   |-- 2_case_setup.py           # Case Setup: select modules/sections
|   |-- 3_specification.py        # Specification: configure parameters (tabs M1-M7)
|   |-- 4_revenue_frame.py        # Revenue Frame: display results, export
|   |-- 5_new_benchmarking.py     # New benchmarking model (standalone add-on analysis)
|   |-- 6_placeholder.py          # Placeholder stub (exists, but not registered in the sidebar nav)
|
|-- config/                       # Constants, metadata, domain configuration (no Streamlit)
|   |-- case_definition.py        # Dataclasses: CaseDefinition, PreDeaConfig, DeaConfig, etc.
|   |-- column_names.py           # COL_* constants, rename dicts (single source of truth)
|   |-- glossary.py               # Parameter-IDs (PID_*), Variable-IDs (VID_*), glossary
|   |-- module_registry.py        # Module definitions (M1-M7), sections, selection logic
|   |-- asset_categories.py       # 17 asset categories (codes, names, lifetimes)
|   |-- colors.py                 # COLORS, CHART_COLORS, get_plotly_template()
|   |-- formatting.py             # Formatting: tkr, percent, delta (European conventions)
|   |-- time_codes.py             # Half-year timecodes (229=2024H1, etc.)
|   |-- incentive_parameters.py   # KPI, K_NF, AIT/AIF costs, caps, SNI labels
|   |-- tools_registry.py         # ToolSpec + TOOLS: single source of truth for the tools (drives the landing index)
|   |-- config_adapter.py         # UI config -> CaseDefinition (only bridge frontend->backend)
|
|-- frontend/                     # Streamlit-dependent UI code ONLY
|   |-- common/                   # Shared Streamlit components
|   |   |-- parameter_input.py    # Reusable input component with baseline comparison
|   |   |-- styling.py            # apply_base_styling() (both zones) + apply_tool_chrome() (tool sidebar); re-exports colors
|   |   |-- auth_page.py          # Full-page sign-in gate (login/register/reset/verify) for the tool zone
|   |   |-- landing_shell.py      # Landing theme (faded bg) + frozen top bar (brand + anchor nav + auth-aware CTA: Sign in / Open tool) + shared helpers (landing_anchor/cards/heading/profile/footer)
|   |   |-- manuals.py            # Host seam for per-tool manuals: published PDF (static/manuals/<slug>.pdf) + builds the in-page reader doc (manual_reader_html) from the Markdown twin (user_manual_latex/manuals/<slug>/main.md)
|   |   |-- save_bar.py           # Save button (update only, on pages 3-4)
|   |   |-- case_comparison.py    # Side-by-side KPI comparison table for cases
|   |
|   |-- modules/                  # Input renderers per module
|   |   |-- base/
|   |   |   |-- m1_asset_base.py          # render_scaling(), render_quantities(), render_kent()
|   |   |   |-- m2_depreciation.py        # render_lifetimes()
|   |   |   |-- m3_cost_of_capital.py     # render_wacc()
|   |   |   |-- m3_incentive_variables.py # render_incentive_vars()
|   |   |   |-- m4_operating_exp.py       # render_scaling(), render_opex_vars()
|   |   |   |-- m5_efficiency.py          # render_efficiency_params()
|   |   |-- addons/
|   |       |-- benchmarking.py           # render_dea_spec()
|   |
|   |-- results/                  # Output renderers per module
|   |   |-- m1_asset_base_output.py       # NUAV, category breakdown
|   |   |-- m2_depreciation_output.py     # Depreciation values
|   |   |-- m3_cost_of_capital_output.py  # (imports m3_return_output)
|   |   |-- m3_return_output.py           # WACC, return on assets
|   |   |-- m3_incentive_output.py        # Quality/incentive adjustments
|   |   |-- m5_efficiency_output.py       # Efficiency requirements
|   |   |-- _efficiency_charts.py        # Shared efficiency chart helpers
|   |
|   |-- utils/                    # Streamlit-dependent frontend utilities
|       |-- state_manager.py      # Session state: init, get/set, config references
|       |-- company_directory.py  # Company list / name lookups (sidebar selectors + registration)
|       |-- case_storage.py       # Save/load cases (Firestore/local JSON)
|       |-- case_actions.py       # Extracted do_save_case(), run_calculation()
|       |-- result_snapshot.py    # Lightweight KPI extraction for case comparison
|       |-- export_button.py      # Export button component
|
|-- pipeline/
|   |-- core.py                   # run_pipeline(): orchestrates 5 stages -> PipelineResult
|   |-- debug_logger.py           # Structured logging per stage
|   |-- post_dea_capex_helpers.py # Helper functions for post-DEA
|   |-- result_helpers.py         # Shared formatting/aggregation for result output modules
|   |-- export_excel.py           # Excel generation from PipelineResult
|   |-- stages/
|       |-- stage_outputs.py      # Frozen dataclasses per stage
|       |-- baseline.py           # Stage 1: Convert BaselineData
|       |-- pre_dea.py            # Stage 2: CAPEX/WACC calculation
|       |-- dea.py                # Stage 3: DEA efficiency analysis
|       |-- extraction.py         # Stage 4: Extract user's company
|       |-- post_dea.py           # Stage 5: Efficiency requirement + revenue cap
|
|-- calculations/                 # Pure calculation logic (no UI dependencies)
|   |-- capex/                    # M1+M2+M3: Capital base, depreciation, WACC
|   |   |-- kent_calculations.py          # KENT steps 5-8, capital cost
|   |   |-- kent_capbase_prep.py          # KENT steps 1-4, capbase_a format
|   |   |-- wacc_calculations.py          # CAPM -> WACC
|   |   |-- data_mapping.py               # KENT-baseline merge, id_network mapping
|   |
|   |-- opex/                     # M4: Operating expenditure
|   |   |-- controllable_cost_calculations.py # Controllable costs (OPEX/TOTEX methods)
|   |   |-- cost_aggregation.py              # Grunddata aggregation (controllable + non-controllable)
|   |
|   |-- frontier/                 # M7: DEA / frontier estimation
|   |   |-- dea_calculations.py              # DEA via PuLP
|   |
|   |-- incentive/                # M3 incentive: Quality/loss/load adjustments
|   |   |-- incentive_calculations.py        # Interruption, netloss, utilization
|   |
|   |-- efficiency/               # M5: Efficiency requirement
|   |   |-- efficiency_requirement.py        # DEA potential -> annual requirement
|   |
|   |   (the new benchmarking add-on is its own vertical module: new_benchmarking_model/)
|   |
|   |-- revenue_frame_assembly.py            # Cross-cutting: final revenue frame assembly
|
|-- visualization/                # Streamlit-free visualization (Plotly, HTML, geodata)
|   |-- diagram_data.py           # Revenue frame decomposition data
|   |-- diagram_utils.py          # Interactive HTML/CSS diagram generation
|   |-- geo_data.py               # Shapefile loading, geodata preparation
|   |-- geo_visualization.py      # Choropleth map visualization (Plotly)
|
|-- data_loaders/                 # Data loading (load boundary; Swedish->English rename here)
|   |-- _cache.py                 # cached(): st.cache_data when Streamlit present, else memo
|   |-- schemas.py                # non-mutating column contracts (require_columns)
|   |-- baseline_data.py          # BaselineData; reads frozen snapshots, else parses Excel
|   |-- cost_data.py              # Grunddata parquet loaders (used by baseline_data)
|   |-- rab_data.py               # RAB data (capbase_a.parquet, capcost_a.parquet)
|   |-- incentive_data.py         # Incentive data loader (load_incentive_data + UI baseline)
|   |   (paths resolve via config/data_paths.py; prep logic in calculations/incentive/;
|   |    variable metadata in config/incentive_variables.py;
|   |    new-benchmarking loading lives in new_benchmarking_model/data/)
|
|-- new_benchmarking_model/       # Vertical feature module: Ei's proposed new benchmarking
|   |                             # model (TOTEX-based DEA), self-contained across layers
|   |-- __init__.py               # Public API: run_new_benchmarking, NewBenchmarkingConfig
|   |-- config.py                 # NewBenchmarkingConfig (parameters); cfg.signature()
|   |-- model.py                  # run_new_benchmarking(): new vs current (EIs_DEA)
|   |-- totex/                    # TOTEX build (pure calc, Streamlit-free)
|   |   |-- totex.py                          # build new TOTEX (opex + adjusted capex)
|   |   |-- opex_components.py                # losses@common price + selected non-controllable
|   |   |-- capex_environment.py              # consolidated förläggningsmiljö + KENT rerun
|   |-- efficiency/               # efficiency requirement + kr impact (pure calc)
|   |   |-- efficiency_requirement_two_sided.py  # signed gap to E75 -> two-sided annual outcome
|   |   |-- cost_impact.py                    # efficiency requirement -> tkr (current OPEX vs new TOTEX base)
|   |-- components/               # parametrised DEA-input builders (pure calc)
|   |   |-- cable_length/                     # ledningslängd per firm (new DEA output)
|   |   |-- environment_capex_adjustment/     # jordkabel förläggningsmiljö correction
|   |   |-- station_capex_adjustment/         # nätstation förläggningsmiljö correction
|   |-- data/                     # feature IO + committed precomputed bundle
|   |   |-- loader.py                         # load_precomputed_main() (runtime)
|   |   |-- precompute.py                     # offline bundle builder (run manually)
|   |   |-- precomputed/                      # *.parquet + manifest.json (committed)
|   |-- ui/                       # ONLY Streamlit-dependent part of the module
|   |   |-- page.py                           # render_page() (pages/5 is a thin shim)
|   |   |-- company_view.py                   # per-company view (firm-first)
|   |   |-- charts.py                         # two-sided position/bridge/scatter graph drawers
|   |   |-- chart_panel.py                    # stacks the thematic chart groups (layout seam)
|   |   |-- config_panel.py                   # render_config_panel() (Experiment panel)
|   |-- docs/                     # dependency_graph.md + interpretation notes
|
|-- scripts/                     # Utility scripts (offline data preparation)
|   |-- generate_kent_from_capbase.py        # Generate KENT data from capbase
|   |-- generate_company_names.py            # Build data/reference/company_names.csv
|
|-- auth/
|   |-- firebase_auth.py          # Firebase auth: login, registration, claims, dev mode
|   |-- firebase_firestore.py     # Firestore client (singleton)
|   |-- cookie_session.py         # Cookie-based session persistence (refresh token)
|
|-- data/                         # Data files, organised by PROVENANCE (see data/README.md)
|   |                             # Access via config/data_paths.py registry, never hardcode.
|   |                             # Root overridable with env REGUMETRICA_DATA_DIR.
|   |-- raw/                      # External sources, exactly as delivered (DO NOT EDIT)
|   |   |-- ei/                   # Ei source files
|   |   |   |-- Data_modeller.xlsx    # 148 companies, CAPEX/OPEX/volumes/returns
|   |   |   |-- EIs_DEA.xlsx          # Ei's baseline DEA results
|   |   |   |-- Löpande kostnader från SDF 2024-27.xlsx  # SDF regulatory submissions
|   |   |-- adjustments/all_adjust_vars.csv          # Incentive variables
|   |   |-- shapefiles/all_network_operator_areas.*  # Network areas (geo)
|   |-- derived/                  # Generated by scripts/ (DO NOT EDIT — regenerate)
|   |   |-- rab_and_capex/        # capbase_a.parquet (18 MB), capcost_a.parquet
|   |   |-- opex/                 # controllable_a, controllable_meta, non_controllable_a
|   |   |-- snapshots/            # frozen Excel output (scripts/freeze_raw_sources.py)
|   |   |   |-- data_modeller.parquet, eis_dea.parquet  # read at runtime instead of .xlsx
|   |-- reference/                # Curated lookups
|   |   |-- reconciliation_id_network_firm_dmu.csv  # ID mapping (REId <-> id_network <-> DMU)
|   |   |-- avg_norm_value_by_category.parquet      # Per-category average normvalue
|   |   |-- company_names.csv     # Curated names (REId, name_full, name_short)
|   |   (the new-benchmarking bundle now lives in new_benchmarking_model/data/precomputed/)
|   |-- fixtures/                 # Mini parquet for unit tests (3 companies; REGUMETRICA_TEST_MODE=1)
|   |   |-- capbase_a_mini.parquet, controllable_a_mini.parquet,
|   |   |-- controllable_meta_mini.parquet, non_controllable_a_mini.parquet
|   |-- examples/                 # Example uploads (KENT, paverkbara)
|   |   |-- capbase_a_exempel.xlsx, exempel_paverkbara.xlsx, generated_kent_886.xlsx
|
|-- tests/                        # pytest test suite (~260 tests, ~70s)
|   |-- conftest.py               # Session-scoped fixtures
|   |-- test_baseline_replication.py
|   |-- test_kent_calculations.py
|   |-- test_wacc.py
|   |-- test_dea.py
|   |-- test_efficiency_requirement.py
|   |-- test_controllable_costs.py
|   |-- test_cost_aggregation.py     # Grunddata aggregation verification
|   |-- test_incentive_calculations.py
|   |-- test_revenue_frame.py
|   |-- test_pipeline_integration.py
|   |-- test_override_cascades.py    # Category override cascade tests
|   |-- test_result_snapshot.py      # Result snapshot extraction tests
|   |-- test_new_benchmarking_precompute.py  # New-benchmarking bundle + freshness guard
|   |-- test_new_benchmarking_cost_impact.py # kr quantification: pipeline-match + base/sign sanity
|   |-- test_tools_registry.py       # Tool registry <-> published-manual consistency
|
|-- user_manual_latex/            # LaTeX sources for the per-tool manual PDFs (see Section 19)
    |-- build.sh                      # Build all (or one) manual(s) -> publish to static/manuals/<slug>.pdf
    |-- latexmkrc                     # latexmk config: $out_dir=build
    |-- LATEX_VSCODE_SETUP.md         # Setup guide (MacTeX + LaTeX Workshop)
    |-- shared/                       # preamble.tex + references.bib shared by every manual
    |-- manuals/                      # One folder per tool; folder name == manual slug
        |-- _template/main.tex            # Starting point for a new tool's manual (skipped by build.sh)
        |-- regumetrica_user_manual/main.tex  # Revenue cap tool
        |-- new_benchmarking_model/main.tex   # New benchmarking model
        |-- placeholder/main.tex              # Placeholder
        |-- <slug>/build/main.pdf             # Build artifacts per manual (gitignored)
```


## 4. Architecture Layers (dependency flow)

Dependencies flow strictly downward. Lower layers NEVER import from higher layers.
`calculations/` has no UI dependencies. `config/` knows nothing about Streamlit.

```
Layer 1: PAGES (top)
    streamlit_app.py (two-zone controller),
    landing_pages/landing.py,
    pages/1_create_and_select_case.py .. pages/5_new_benchmarking.py
        |
        | imports
        v
Layer 2: FRONTEND (Streamlit-dependent only)
    Left side: FRONTEND UTILS
        state_manager.py, company_directory.py, case_storage.py,
        case_actions.py, result_snapshot.py, export_button.py
    Right side: FRONTEND COMMON + MODULES
        parameter_input.py, styling.py, auth_page.py, landing_shell.py,
        manuals.py, save_bar.py, case_comparison.py,
        m1_asset_base.py .. m5_efficiency.py, benchmarking.py
        |
        | imports
        v
Layer 2b: VISUALIZATION (Streamlit-free)
    diagram_data.py, diagram_utils.py, geo_data.py, geo_visualization.py
        |
        | imports
        v
Layer 3: CONFIG (constants, metadata, domain configuration)
    case_definition.py, column_names.py, glossary.py,
    module_registry.py, asset_categories.py, colors.py, formatting.py,
    time_codes.py, incentive_parameters.py, tools_registry.py, config_adapter.py
        |
        | imports
        v
Layer 4: PIPELINE
    core.py -> stages/baseline -> pre_dea -> dea -> extraction -> post_dea
    stage_outputs.py, result_helpers.py, export_excel.py
        |
        | imports
        v
Layer 5: CALCULATIONS + DATA LOADERS (bottom)
    Left side: CALCULATIONS
        capex/ (kent, wacc, data_mapping)
        opex/ (controllable, cost_aggregation)
        frontier/ (dea)
        incentive/ (incentive_calculations)
        efficiency/ (efficiency_requirement)
        revenue_frame_assembly.py
    Right side: DATA LOADERS
        baseline_data.py, cost_data.py, rab_data.py, incentive_data.py
        |
        | imports
        v
Layer 6: AUTH / FIRESTORE
    firebase_auth.py, firebase_firestore.py
```

**Vertical exception — `new_benchmarking_model/`:** the new benchmarking add-on is a
self-contained feature module that spans layers internally instead of being split across
them (see Section 20). It depends downward on config/, pipeline pieces it reuses
(calculations.frontier.dea, data_loaders.baseline_data) and the same lower layers; nothing
else imports *into* it except its thin page shim (`pages/5_new_benchmarking.py`). The
horizontal-layer rule still holds inside it: everything outside `new_benchmarking_model/ui/`
is Streamlit-free.


## 5. Page Flow & Navigation

Two zones, but the **route** decides the zone, not auth. All pages live in ONE
`st.navigation` so Streamlit resolves the requested page from the real URL
(reliable — the controller never parses the URL itself); the controller then
branches on the *returned* page, and auth only gates the tool pages. This lets a
logged-in user keep the public landing open in one window and a tool in another at
the same time.

```
ZON 1 — Landing (public)             ZON 2 — Tool (auth-gated)
------------------------             -------------------------
landing_pages/landing.py             sidebar nav, two groups:
(hidden DEFAULT page, root "/")
  #home / #tools / #team             group "Main module":
  (in-page anchor nav)                 pages/1_create_and_select_case.py  (Create & Select)
        |                                    |
  [Open tool] (all visitors,             v
   new tab; landing stays open) ──►   pages/2_case_setup.py              (Case Setup)
        |                                    |
  opens the tool window; if logged          v
  out, that window shows the          pages/3_specification.py          (Specification)
  sign-in gate -> render_auth_gate()        |
  in place, then renders the tool     [Compute] (on page 4)
                                            |
  ◄─── [Back to Home] (sidebar,          v
       new tab; tool stays open)      pages/4_revenue_frame.py          (Revenue Frame)

                                     group "Add-on modules":  (decoupled, not part of 1 → 4)
                                       pages/5_new_benchmarking.py        (New benchmarking model)
```

**Window-target policy.** Zone navigation (Open tool, Back to Home), manuals and
external links open the destination in its own window (new tab), so a user can
keep the landing — with its manuals — open beside the tool. Sign-in / log-out
(identity events) and forced redirects act in the current window. A logged-in
user can therefore have the public landing in one window and a tool in another at
the same time; window reuse is intentionally not managed (closing windows is the
user's job). The new-tab links are plain buttons with no visual new-tab marker.

**Entrypoint:** `streamlit_app.py` — a route-based two-zone controller.
- Configures page (`st.set_page_config`); `apply_base_styling()` (fonts +
  branding) applies to both zones. Initializes state; restores auth/case from
  cookies on refresh.
- One navigation for everything:
  `st.navigation({"Main module": [landing_main, *REVENUE_CAP_PAGES],
  "Add-on modules": STANDALONE_PAGES})`. `landing_main` is the **hidden default**
  page — it owns the root URL but never shows in the tool sidebar nav. The returned
  page `pg` decides the zone: `pg in TOOL_PAGES` → Zon 2, else → Zon 1.
  - **Zon 1 (landing):** `pg.run()` runs `landing.py`, which calls
    `apply_landing_shell()` (theme + a frozen top bar: brand + in-page anchor nav,
    the native menu hidden via CSS). The right-hand CTA is a single **Open tool**
    link (new tab) for everyone — no auth branching; the landing is a purely public
    surface. Sign-in happens in the tool window it opens (see below).
  - **Zon 2 (tool):** gated by `check_auth()`. A tool window opened while logged
    out renders the **full-page sign-in gate in place** (`render_auth_gate()`,
    frontend/common/auth_page.py: a glass-card login/register over the faded
    login_pic backdrop), not a bounce back to the landing — so the landing (and
    its manuals) can stay open beside it. Once authed: `apply_tool_chrome()`
    (locked sidebar + Nordic Energy refinements) + `render_sidebar()` (company
    selector, **Back to Home** new-tab link, logout), then `pg.run()`.
- **Launch / login (Option B):** the landing's **Open tool** link opens the tool
  window with one reliable click (a link gesture is never popup-blocked). If logged
  out, the user signs in *in that window* on the full-page gate
  (`render_auth_gate()`); a verified login reruns the app and the same window
  renders the tool (the controller writes the deferred auth cookie once auth
  passes). No `_login_redirect` flag and no
  cross-zone `switch_page` are involved — those were removed with this flow.
- **Logout:** clears auth + deletes the cookie and reruns → the (now logged-out)
  tool window falls back to the sign-in gate in place. *Caveat:* logout is
  per-window — other open tool windows keep their in-memory session until reloaded
  (cookie reads are a connection-time snapshot). Cross-window "global logout" is a
  known post-V1 item.


## 6. Module Architecture (M1-M7)

Modules are defined centrally in `config/module_registry.py`.
Each module has sections for fine-grained control.

| Module        | Purpose                     | Input file                  | Output file                   | Config key               |
|---------------|-----------------------------|-----------------------------|-------------------------------|--------------------------|
| M1            | Asset base valuation        | m1_asset_base.py            | m1_asset_base_output.py       | m1_asset_base            |
| M2            | Depreciation                | m2_depreciation.py          | m2_depreciation_output.py     | m2_depreciation          |
| M3 WACC       | Cost of capital (CAPM)      | m3_cost_of_capital.py       | m3_return_output.py           | m3_cost_of_capital       |
| M3 Incentive  | Quality/incentive adj.      | m3_incentive_variables.py   | m3_incentive_output.py        | m3_quality_adjustments   |
| M4            | Operating expenditure       | m4_operating_exp.py         | _(no dedicated output module)_ | m4_operating_exp         |
| M5            | Efficiency requirement      | m5_efficiency.py            | m5_efficiency_output.py       | m5_efficiency            |
| M7            | Benchmarking (DEA)          | benchmarking.py             | _(results shown in M5)_       | addon_benchmarking       |

**Sections (example M1):**
- `m1.scaling` -- Scaling factors (param 1.1-1.2, all companies)
- `m1.quantities` -- Quantity adjustment (var 10.X, own company)
- `m1.kent` -- KENT file upload (override)

**Selection keys:** `"m1"`, `"m1.scaling"`, `"m3.wacc"`, `"m3.incentive_params"`, etc.


## 7. Data Flow

The data flows through 3 major phases: UI Configuration, Pipeline Execution, Results Display.

### Phase 1: UI Configuration -> CaseDefinition

```
Step 1: User adjusts parameters in pages/3_specification.py
Step 2: Values stored in st.session_state["ui_config"] (Dict)
Step 3: User clicks "Compute Revenue Frame"
Step 4: config_adapter.build_case_definition(user_reid, ui_config) is called
Step 5: Returns a CaseDefinition containing PreDeaConfig + DeaConfig + PostDeaConfig
```

`config_adapter.build_case_definition()` is the ONLY bridge between frontend and backend.

### Phase 2: Pipeline Execution

```
Input:  BaselineData (cached, 148 companies) + CaseDefinition
Call:   pipeline.core.run_pipeline(baseline_data, case_config)

  Stage 1: baseline    -- BaselineData      -->  BaselineStageOutput
  Stage 2: pre_dea     -- Stage1 + PreDea   -->  PreDeaStageOutput
  Stage 3: dea         -- Stage2 + DeaCfg   -->  DeaStageOutput
  Stage 4: extraction  -- Stage2+3 + REId   -->  ExtractionStageOutput
  Stage 5: post_dea    -- Stage1-4 + Post   -->  PostDeaStageOutput

Output: PipelineResult (frozen dataclass containing all 5 stage outputs)
```

### Phase 3: Results Display

```
pages/4_revenue_frame.py receives PipelineResult
Each output module calls: render(case_result, baseline_result, ui_config)
Results shown with case-vs-baseline comparison (orange = modified)
```


## 8. State Management

**Mechanism:** Streamlit `st.session_state` via `frontend/utils/state_manager.py`

### Core Session Variables

| Key                      | Type            | Description                                      |
|--------------------------|-----------------|--------------------------------------------------|
| user_reid                | str             | Selected company's REId (sole authoritative ID)  |
| ui_config                | Dict[str, Dict] | Module configurations (8 top-level keys)        |
| selected_modules         | Set[str]        | Selected modules/sections                        |
| baseline_result          | PipelineResult  | Baseline calculation                             |
| case_result              | PipelineResult  | User's case calculation                          |
| calculation_done         | bool            | Flag: calculation completed                      |
| case_id                  | str/None        | UUID if saved, None if new                       |
| case_name                | str             | Case name (edited via sidebar)                   |
| case_notes               | str             | Notes (edited via sidebar)                       |
| computed_ui_config       | Dict/None       | Frozen config from last pipeline run             |
| computed_selected_modules| Set/None        | Frozen modules from last pipeline run            |
| saved_ui_config          | Dict/None       | Frozen config as last persisted to DB            |
| saved_selected_modules   | Set/None        | Frozen modules as last persisted to DB           |
| auth_*                   | various         | Firebase auth state (email, role, reid, uid)     |

### ui_config Structure (8 module keys)

```python
DEFAULT_UI_CONFIG = {
    "m1_asset_base":          {general_scaling, cat_scaling, var_scaling, kent_file_*},
    "m2_depreciation":        {lifetime_adjustments},
    "m3_cost_of_capital":     {wacc_override},
    "m3_quality_adjustments": {enable_quality/netloss/load, adj_max_*, sharing_*, k_nf},
    "m3_incentive_variables": {nf_norm/obs, ug_norm/obs, cemi4_norm/obs, ...},
    "m4_operating_exp":       {opex_scaling, flex_scaling, non_adj_scaling,
                                opex_override, flex_override, non_controllable_override},
    "m5_efficiency":          {trunkering_max/min, efficiency_override},
    "addon_benchmarking":     {dea_method, dea_inputs/outputs, dea_rts},
}
```

**Pattern:** All values = `None` means "use baseline". Non-None = user adjustment.

### Config Reference System (Change Detection)

Three levels of config exist for tracking changes:
1. **Working state** (`ui_config`, `selected_modules`) — live, editable
2. **Computed reference** (`computed_ui_config`, `computed_selected_modules`) — frozen at last pipeline run
3. **Saved reference** (`saved_ui_config`, `saved_selected_modules`) — frozen at last DB save/load

- `has_unsaved_changes()`: working differs from saved (guards save button)
- `has_config_changed_since_compute()`: working differs from computed (stale results warning on page 4)

### Case Management

See `docs/case_system_framework.md` for the full conceptual framework.

- **Create**: Page 1. User names a case, it is saved to DB immediately with default config.
  A `case_id` is always present on pages 2-4.
- **Save (update)**: Single "Save" button on pages 3-4. Always updates the existing case.
  Saves the current working config regardless of computation state. Includes a KPI snapshot
  only when working config matches the last computed config.
- **Result snapshot**: Lightweight KPI snapshot (~15 aggregated values + baseline equivalents)
  persisted alongside the config. Enables instant case comparison on page 1.
- **Load case**: Page 1. Clears widget keys so inputs reinitialize on rerun.
- **Delete case**: Page 1, modal confirmation.
- **Duplicate case**: Page 1, modal dialog with new name. No fork from save bar.
- **Compare cases**: Page 1. Multiselect of cases with snapshots, side-by-side KPI table.
- **Revert to saved**: Page 4 button, restores working state to last saved/loaded config.

### data_editor Widget Caching

Source DataFrames are cached in `st.session_state["{key}_source"]` so `data_editor`
input is constant between reruns (prevents widget reset on rerun feedback loop).
Rebuilt when widget key is lost (page navigation) or `_clear_config_widget_keys()` fires
(case load, reset, revert).


## 9. Pipeline Architecture

**File:** `pipeline/core.py`
**Signature:** `run_pipeline(baseline_data, case_config) -> PipelineResult`

| Stage | Function             | Input                    | Output                  | Description                              |
|-------|----------------------|--------------------------|-------------------------|------------------------------------------|
| 1     | stage_baseline()     | BaselineData             | BaselineStageOutput     | Converts raw data to stage format        |
| 2     | stage_pre_dea()      | Stage 1 + PreDeaConfig   | PreDeaStageOutput       | CAPEX calculation (KENT 1-8), WACC       |
| 3     | stage_dea()          | Stage 1 + DeaConfig      | DeaStageOutput          | DEA efficiency (always baseline data)    |
| 4     | stage_extraction()   | Stage 2+3 + REId         | ExtractionStageOutput   | Extracts data for user's company         |
| 5     | stage_post_dea()     | Stage 1-4 + PostDeaConfig| PostDeaStageOutput      | Eff. req + incentives + revenue cap      |

**All stage outputs:** Frozen dataclasses in `pipeline/stages/stage_outputs.py`
**Logging:** `PipelineDebugLogger` logs each stage in structured format

### PipelineResult

```python
@dataclass(frozen=True)
class PipelineResult:
    baseline: BaselineStageOutput
    pre_dea: PreDeaStageOutput
    dea: DeaStageOutput
    extraction: ExtractionStageOutput
    post_dea: PostDeaStageOutput
    case_name: str
    user_reid: str
```


## 10. Column Names and the Rename Boundary

**Single source of truth:** `config/column_names.py`

All DataFrame columns use English names throughout the codebase. Swedish column names
from external data files are renamed at the load boundary in `data_loaders/`.

### Key COL_* Constants

```
Identifiers:     COL_REID, COL_ID_NETWORK, COL_DMU, COL_COMPANY_NAME
Capital costs:   COL_CAPITAL_COST_2024 .. 2027, COL_CAPITAL_COST_PERIOD
Depreciation:    COL_DEPRECIATION_2024 .. 2027, COL_DEPRECIATION_PERIOD
Returns:         COL_RETURN_2024 .. 2027, COL_RETURN_PERIOD
Controllable:    COL_CONTROLLABLE_AVG (SDF, requirement base), COL_CONTROLLABLE_2024 .. 2027, COL_CONTROLLABLE_PERIOD
DEA frontier:    COL_OPEXP_DEA (raw OPEXp), COL_TOTEX_DEA (= opexp_dea + capital_cost_2024)
OPEX/CAPEX:      COL_OPEX_BEFORE/AFTER, COL_CAPEX_BEFORE/AFTER, COL_OPEX/CAPEX_EFF_DEDUCTION
DEA:             COL_DEA_EFFICIENCY, COL_DEA_SUPER_EFF, COL_DEA_POTENTIAL, COL_IS_OUTLIER
Efficiency:      COL_EFF_REQ_ANNUAL
Revenue frame:   COL_CAPITAL_COST_IN_RF, COL_CONTROLLABLE_IN_RF, COL_NON_CONTROLLABLE,
                 COL_FLEXIBILITY, COL_INTERRUPTION, COL_STATE_DEDUCTION, COL_REVENUE_FRAME
Incentives:      COL_QUALITY_INCENTIVE, COL_NETLOSS_INCENTIVE, COL_LOAD_INCENTIVE,
                 COL_INCENTIVE_TOTAL, COL_MISSING_INCENTIVE
Volumes:         COL_CU, COL_MW, COL_NS, COL_MWH_LOW, COL_MWH_HIGH
TOTEX:           COL_TOTEX
```

### Rename Dictionaries (in config/column_names.py, used by data_loaders/)

- `DATA_MODELLER_RENAME` -- Maps Swedish columns in Data_modeller.xlsx to English
- `EIS_DEA_RENAME` -- Maps Swedish columns in EIs_DEA.xlsx to English
- `SDF_IR_RENAME` -- Maps Swedish columns in SDF "IR 2024-2027" sheet to English

**Pattern:** Swedish column names appear ONLY in `data_loaders/` (the load boundary).
All downstream code (calculations, pipeline, frontend) uses `COL_*` constants exclusively.


## 11. Authentication & Roles

**File:** `auth/firebase_auth.py`

| Role      | Description              | Company selection                        |
|-----------|--------------------------|------------------------------------------|
| company   | Distribution company     | Locked to their REId (custom claim)      |
| regulator | Ei staff                 | Can select any of 148 companies          |
| Dev mode  | skip_auth=true in secrets| Free selection (dropdown)                |

**Flow:**
1. `streamlit_app.py` -> `try_restore_auth_from_cookie()` -> `check_auth()` -> dev mode OR Firebase
2. Login via the full-page sign-in gate (`frontend/common/auth_page.py`, email/password)
3. Custom claims: `{REId: "REL00886", role: "company"}`
4. Session state: `auth_email`, `auth_role`, `auth_reid`, `auth_uid`, `auth_token`

### Session Persistence (cookie_session.py)

Authentication survives page refreshes via a browser cookie storing the Firebase refresh token.

**Files:** `auth/cookie_session.py` (helpers), `streamlit_app.py` (restore + deferred save),
`frontend/common/auth_page.py` (defers the token on login)

**Flow on login:**
1. Firebase `sign_in` → returns `refreshToken`
2. The sign-in dialog stashes it in `st.session_state["_pending_auth_cookie"]` and
   reruns; `streamlit_app.py` then calls `set_auth_cookie(refreshToken)` once the
   auth check passes (so the JS cookie component renders cleanly) →
   sets cookie (`regumetrica_auth`, 30-day expiry)

**Flow on page refresh:**
1. `st.session_state` is wiped (new websocket)
2. `try_restore_auth_from_cookie()` reads cookie via `st.context.cookies`
3. Exchanges refresh token for new ID token via `auth.refresh()`
4. Verifies claims via admin SDK → restores session state
5. User stays logged in on the same page

**Flow on logout:**
1. `delete_auth_cookie()` → expires the cookie
2. `auth_manager.sign_out()` → clears session state

### Session Store (state_manager.py)

Working state (ui_config, selected_modules, results, case metadata) is persisted across
page refreshes via a server-side `@st.cache_resource` dict keyed by `auth_uid`.

**Save points:** after compute, after case save, after case load, after revert.
**Clear points:** on reset ("New case"), on logout.

**Limitations:** Store is cleared on server restart (Render redeploy). Config changes
made after compute but before a new compute are not persisted. Users should save their
case to Firestore to preserve work across sessions.


## 12. Config Dataclasses (config/case_definition.py)

### Enums

- `CapbaseSource`: BASELINE, VAR_SCALED, KENT_UPLOAD
- `CapexMethod`: BASELINE, PARAMETER_CHANGE
- `EfficiencyMethod`: BASELINE, DEA
- `ControllableMethod`: OPEX, TOTEX

### Config Dataclasses

**PreDeaConfig** (Stage 2):
- capbase_source, user_capbase_scaled, kent_file_bytes, kent_user_id_network,
  kent_capbase_df (pre-parsed capbase for saved cases)
- method (CapexMethod), wacc, normvalue_adjustments, lifetime_adjustments
- wacc_input_method ("capm"/"derived"/"direct"/"baseline"),
  wacc_capm_inputs (3.1.X), wacc_derived_inputs (3.2.X)
- opex_scaling (4.1.1) -- float multiplier for user's company controllable OPEX only
- opex_override (40.1.1) -- absolute controllable cost (requirement base) in tkr for user's company (trumps scaling)

**DeaConfig** (Stage 3):
- method (EfficiencyMethod), inputs, outputs, rts ("crs"/"vrs")
- orientation ("input"), q_lower (25.0), q_upper (75.0), multiplier (2.0)

**IncentiveConfig** (nested in PostDeaConfig):
- kpi, k_nf, sharing_netloss (0.75), adj_max_agg (1/3), adj_max_cemi4 (0.25)
- ait_costs, aif_costs, enable_quality/netloss/load, variable_overrides

**PostDeaConfig** (Stage 5):
- truncation_min (None = auto-derive from outlier_req), truncation_max (0.30), outlier_req (0.01)
- customer_sharing (0.50), realization_time (8), supervision_period (4)
- controllable_method (OPEX/TOTEX), incentive (IncentiveConfig)
- flex_scaling (4.1.2) -- float multiplier for all companies' flexibility costs
- non_adj_scaling (4.1.3) -- float multiplier for all companies' non-controllable costs
- flex_override (40.1.2) -- absolute flexibility in tkr for user's company (trumps scaling)
- non_controllable_override (40.2.1) -- absolute non-controllable in tkr for user (trumps scaling)

**CaseDefinition** (top-level):
- name, user_reid, pre_dea (PreDeaConfig), dea (DeaConfig), post_dea (PostDeaConfig)

**Factory functions:**
- `get_baseline_config(user_reid)` -> default CaseDefinition
- `create_var_scaled_config(...)`, `create_kent_upload_config(...)`,
  `create_parameter_change_config(...)`


## 13. Calculations Module (Pure Logic)

All files in `calculations/` are pure functions with no UI dependencies.

| File                                        | Purpose                                    |
|---------------------------------------------|--------------------------------------------|
| capex/kent_calculations.py                  | KENT steps 5-8: capital cost calculation   |
| capex/kent_capbase_prep.py                  | KENT steps 1-4: capbase_a conversion       |
| capex/wacc_calculations.py                  | CAPM -> WACC (baseline: 4.53%)             |
| capex/data_mapping.py                       | KENT-baseline merge, id_network mapping    |
| opex/controllable_cost_calculations.py      | Controllable costs (OPEX/TOTEX methods)    |
| opex/cost_aggregation.py                    | Grunddata aggregation (controllable + non-controllable) |
| frontier/dea_calculations.py                | DEA via PuLP (input-oriented, CRS)         |
| incentive/incentive_calculations.py         | Quality/netloss/load incentive adjustments |
| efficiency/efficiency_requirement.py        | DEA potential -> annual efficiency req      |
| revenue_frame_assembly.py                   | Assemble revenue frame from all components |

The new benchmarking add-on is no longer under `calculations/`; it is its own vertical
module, `new_benchmarking_model/` (see Section 20).

### Key Calculation Details

**KENT:** Steps 1-4 (capbase prep) then 5-8 (depreciation, returns, capital cost).
Uses half-year timecodes: 229=2024H1, 230=2024H2, 231=2025H1, ..., 236=2027H2.

**DEA:** Input-oriented CRS. Default (locked) inputs: [capital_cost_2024, opexp_dea]
(raw OPEXp), or their sum totex_dea in TOTEX mode. The requirement-side
controllable_cost_average is NEVER a DEA input (config_adapter guards this).
Default outputs: [CU, MW, NS, MWhl, MWhh]. Outlier detection via IQR method.
DEA always uses baseline (historical) cost data — user changes to OPEX/CAPEX/WACC
do NOT affect DEA inputs. Only the model specification (cost-input mode, outputs, RTS,
outlier params) can be changed. The default spec is served from EIs_DEA.xlsx as a cache;
any non-default spec recomputes live on opexp_dea. See the two-track split note below.

> **Replicating Ei's baseline DEA results** (`data/raw/ei/EIs_DEA.xlsx`): the exact,
> data-agnostic procedure that reproduces Ei's effektivitet/supereffektivitet to solver
> tolerance is written up in [eis_dea_metod.md](eis_dea_metod.md) (repo root). Key point:
> the IQR outlier fence must be **iterated to convergence** (not a single round) to match
> Ei's outlier set. One row (REL00193) is not replicable from the published data. Note the
> pipeline default is `outlier_max_rounds=1`; matching EIs_DEA exactly needs iteration.

**Efficiency requirement:** Converts DEA potential via truncation, customer sharing (50%),
realization time (8 years), supervision period (4 years).

**Incentives:** 3 types -- quality (CEMI4), network loss (NF), load (UG).
Per-year calculations with individual and aggregate caps.
Baseline: KPI ~1.1546/year, k_nf ~753.44 kr/MWh, sharing_netloss=0.75.
Column format: `ait_{ann}_{sni}_{norm/obs}`, `ame_{sni}`, output `_a` suffix = before capping.


## 14. Data Loaders (Load Boundary)

All data loading is cached with `@cached(ttl=3600)` (`data_loaders/_cache.py`):
`st.cache_data` when Streamlit is present, else a plain process memo (so the
pipeline/tests don't hard-depend on Streamlit). Paths resolve via the
`config/data_paths.py` registry; each load asserts a non-mutating column contract
(`data_loaders/schemas.py`).
Swedish column names from files are renamed to English here using rename dicts.

### baseline_data.py

`load_baseline_data() -> BaselineData` (frozen dataclass):
- `df_all_companies` -- 148 rows from Data_modeller.xlsx. Two cost tracks kept separate:
  the FRONTIER track `opexp_dea` (raw OPEXp) + `totex_dea` (= opexp_dea + capex), used only
  as locked DEA inputs; and the REQUIREMENT track `controllable_cost_average` (SDF-derived
  pure average, merged in at load) + `totex_first_year` (= controllable + capex), the base
  the efficiency requirement is applied to. The two never mix (see eis_dea_metod.md and the
  two-track DEA note). Company names overridden by the curated list, see below.
- `dea_results` -- Baseline DEA from EIs_DEA.xlsx
- `sdf_ir` -- Revenue frame baseline from SDF file
- `sdf_controllable` -- Controllable costs from SDF file (raw sheet, used for verification)
- `reconciliation` -- REId <-> id_network mapping
- `wacc` -- float, default 0.0453
- `controllable_detail` -- Per-category controllable grunddata (from controllable_a.parquet)
- `controllable_meta` -- Controllable meta with index/neo (from controllable_meta.parquet)
- `non_controllable_detail` -- Per-category non-controllable grunddata (from non_controllable_a.parquet)

#### Company names

Names come from the curated list `data/reference/company_names.csv`
(`REId, name_full, name_short`), **not** from the Excel `Företag` column. The list
is regenerated by `scripts/generate_company_names.py` (full names from the
reconciliation file, short names from a hand-curated mapping). Editing existing
names only requires editing the CSV -- the loader reads it on every load.

At the load boundary (`baseline_data.py`, step 1b) the list is merged onto
`df_all_companies` by `REId`, overriding the Excel name and adding two columns
(falls back to the Excel name if a `REId` is missing from the list):

| Column (constant)          | Example                          | Use                                      |
|----------------------------|----------------------------------|------------------------------------------|
| `COL_COMPANY_NAME`         | `Ellevio AB`                     | Full name -- reports, export, tooltips   |
| `COL_COMPANY_NAME_SHORT`   | `Ellevio`                        | Short name -- tight space, chart axes    |
| `COL_DISPLAY_NAME`         | `Ellevio (REId)` -> `Ellevio (REL03035)` | Default label -- selectboxes, table rows, headings |

Standard display pattern is `COL_DISPLAY_NAME` = `Kortnamn (REId)`; `REId` keeps it
unambiguous even for look-alike names (e.g. the two `Näckåns Elnät`, where REL03050
is curated as `Näckåns Elnät (Viggafors)`).

**How to use names in a new module:**
- **Calculations layer** -- pure, no UI imports. Operate on `REId`; the name columns
  ride along on `df_all_companies`, or merge them onto your result by `REId`.
- **UI layer** (`pages/`, `streamlit_app.py`) -- use `get_company_display(reid)`
  (-> `Kortnamn (REId)`, safe REId fallback), `get_company_name_lookup()`
  (-> `REId -> kortnamn`), or `_get_company_list()` for a sorted selectbox source.

### cost_data.py

Grunddata parquet loaders (used internally by `baseline_data.py`):
- `load_controllable_detail()` -> controllable_a.parquet (company x category x year)
- `load_controllable_meta()` -> controllable_meta.parquet (one row per company)
- `load_non_controllable_detail()` -> non_controllable_a.parquet (company x kent_category x year)

### rab_data.py

- `load_capbase_a()` -> capbase_a.parquet (full or mini in test mode)
- `load_capcost_a()` -> capcost_a.parquet (category-level capital costs)
- `load_user_capbase(id_network)` -> filtered capbase for one company
- `load_user_capcost(id_network)` -> filtered capcost for one company

### incentive_data.py

- `load_incentive_data()` -> all_adjust_vars.csv (48 incentive variable columns)
- `prepare_incentive_input()` -- Merge incentive data with return per year
- `apply_variable_overrides()` -- Apply company-specific changes
- `get_user_baseline_variables(reid, year)` -- Baseline values for one company
- `get_variable_metadata()` -- Metadata for UI (label, unit, format)

**Variable columns:** nf_norm, nf_obs, e_in, ug_norm, ug_obs, k_upstream,
cemi4_norm, cemi4_obs, aif_{a,o}_{1-6}_{norm,obs}, ait_{a,o}_{1-6}_{norm,obs}, ame_{1-6}

### new_benchmarking_model/data/loader.py

The new-benchmarking add-on loads its own data inside its module (not via `data_loaders/`).
`load_precomputed_main() -> NewBenchmarkingResult | None` loads the committed
new-benchmarking main-spec bundle (`new_benchmarking_model/data/precomputed/`, built by
`new_benchmarking_model/data/precompute.py`) and reconstructs the result page 5 reads, so
the fixed main model skips its live KENT+DEA run on cold start. Returns `None` (caller runs
live) if the bundle is missing or its config signature no longer matches the current
default. See Section 20.


## 15. File Dependencies (Import Map)

```
streamlit_app.py
    |-- frontend.utils.state_manager      (init, get/set functions)
    |-- frontend.utils.company_directory  (get_company_records, get_company_display)
    |-- frontend.common.styling           (apply_base_styling, apply_tool_chrome)
    |-- frontend.common.auth_page         (render_auth_gate: full-page sign-in gate)
    |     |-- frontend.common.landing_shell    (apply_auth_backdrop)
    |     |-- frontend.utils.company_directory  (get_company_options)
    |     |-- frontend.utils.state_manager      (set_user_reid)
    |     |-- auth.firebase_auth                (initialize_firebase_auth)
    |-- auth.firebase_auth                (is_dev_mode, initialize_firebase_auth)
    |-- auth.cookie_session               (auth + case cookie helpers)

landing_pages/landing.py                  (ZON 1 — single page)
    |-- frontend.common.landing_shell     (apply_landing_shell, landing_anchor, landing_cards,
    |                                       landing_heading, landing_profile, landing_footer)
    |-- config.tools_registry             (#tools section: tools_for, ToolSpec)
    |-- frontend.common.manuals           (#tools cards: manual_path for the PDF link,
    |                                       manual_reader_html for the in-page reader dialog)

pages/1_create_and_select_case.py
    |-- frontend.utils.state_manager     (init, get/set, reset_case)
    |-- frontend.utils.case_storage      (list/load/delete/save, apply_case_to_session)
    |-- frontend.common.case_comparison  (render_comparison_table)
    |-- pipeline.result_helpers          (fmt_tkr)

pages/2_case_setup.py
    |-- frontend.utils.state_manager     (init, module selection)

pages/3_specification.py
    |-- frontend.modules.base.m1-m5      (render_* functions)
    |-- frontend.modules.addons.benchmarking
    |-- frontend.utils.state_manager     (is_section_selected)
    |-- frontend.common.save_bar         (render_save_bar)

pages/4_revenue_frame.py
    |-- frontend.results.m1-m5_output    (render functions)
    |-- visualization.diagram_data, diagram_utils
    |-- visualization.geo_data, geo_visualization
    |-- frontend.utils.export_button
    |-- frontend.common.save_bar         (render_save_bar)
    |-- pipeline.result_helpers          (formatting/aggregation helpers)

frontend.utils.case_actions
    |-- frontend.utils.case_storage      (save_case)
    |-- frontend.utils.state_manager     (get/set config, compute_config_hash)
    |-- frontend.utils.result_snapshot   (extract_result_snapshot)
    |-- config.config_adapter            (build_case_definition)
    |-- pipeline.core                    (run_pipeline)
    |-- data_loaders.baseline_data       (load_baseline_data)

config.config_adapter
    |-- config.case_definition           (CaseDefinition, enums)

pipeline.core
    |-- config.case_definition           (CaseDefinition)
    |-- data_loaders.baseline_data       (BaselineData)
    |-- pipeline.stages.*                (stage functions)
    |-- pipeline.debug_logger

pipeline.stages.*
    |-- calculations.capex.*             (kent, wacc, data_mapping)
    |-- calculations.opex.*              (controllable, cost_aggregation)
    |-- calculations.frontier.*          (dea)
    |-- calculations.incentive.*         (incentive_calculations)
    |-- calculations.efficiency.*        (efficiency_requirement)
    |-- calculations.revenue_frame_assembly

config.module_registry
    |-- (no external dependencies, defines dataclasses)

frontend.utils.state_manager
    |-- config.module_registry           (parse/build selection keys)
```

**Lazy imports:** `streamlit_app.py` uses lazy imports (inside functions) for heavy
dependencies like `data_loaders` and `pipeline` for faster initial rendering.


## 16. Data Files

Paths resolve via the `config/data_paths.py` registry (logical name in the last
column); organised by provenance (see `data/README.md`). Never hardcode paths.

| File                                                 | Format  | Registry name | Contents                                        |
|------------------------------------------------------|---------|---------------|-------------------------------------------------|
| data/raw/ei/Data_modeller.xlsx                       | Excel   | data_modeller | 148 companies: CAPEX, OPEX, volumes, returns    |
| data/raw/ei/EIs_DEA.xlsx                             | Excel   | eis_dea       | Ei's baseline DEA results                       |
| data/raw/ei/Löpande kostnader från SDF 2024-27.xlsx  | Excel   | sdf_running_costs | SDF submissions: revenue cap, controllable, etc. |
| data/raw/adjustments/all_adjust_vars.csv             | CSV     | adjustment_vars | All adjustable variables                      |
| data/raw/shapefiles/all_network_operator_areas.*     | SHP     | network_areas_shapefile | Network operator areas (geo)          |
| data/derived/rab_and_capex/capbase_a.parquet         | Parquet | capbase_a     | Capital base per company/category/time (18 MB)  |
| data/derived/rab_and_capex/capcost_a.parquet         | Parquet | capcost_a     | Capital costs per category                      |
| data/derived/opex/controllable_a.parquet             | Parquet | controllable_a | Controllable grunddata: REId, category, year, amount |
| data/derived/opex/controllable_meta.parquet          | Parquet | controllable_meta | Controllable meta: index factors, neo_adjustment |
| data/derived/opex/non_controllable_a.parquet         | Parquet | non_controllable_a | Non-controllable grunddata: REId, kent_category, year, amount |
| data/derived/snapshots/data_modeller.parquet         | Parquet | snap_data_modeller | Frozen Data_modeller (read at runtime; built by scripts/freeze_raw_sources.py) |
| data/derived/snapshots/eis_dea.parquet               | Parquet | snap_eis_dea  | Frozen EIs_DEA (read at runtime)                |
| data/fixtures/*_mini.parquet                         | Parquet | *_mini        | Mini versions (3 test companies) for unit tests |
| data/reference/reconciliation_id_network_firm_dmu.csv | CSV    | reconciliation | ID mapping: REId <-> id_network <-> DMU        |
| data/reference/company_names.csv                     | CSV     | company_names | Curated names: REId, name_full, name_short      |
| data/reference/avg_norm_value_by_category.parquet    | Parquet | avg_norm_value | Per-category average normvalue                  |
| new_benchmarking_model/data/precomputed/*.parquet, manifest.json | Parquet | — | Pre-computed new-benchmarking main-spec bundle (lives in its feature module) |
| data/examples/                                       | Excel   | —             | Example KENT / paverkbara upload files          |
| data/updated_shapefiles/                             | SHP     | Network operator area shapefiles                |

**Note:** The SDF file has a Swedish filename with diacritics
(`Löpande kostnader från SDF 2024-27.xlsx`). In code it is loaded from
`data_loaders/baseline_data.py` via a path constant.

**REId format:** `"REL00886"` -> `id_network: 886` (conversion via `reid_to_id_network()`)
**148 companies** with REId format `REL00XXX` (not all numeric IDs in sequence).


## 17. Key Conventions

### Render Pattern (input modules)

```python
def render_scaling() -> Dict[str, Any]:
    """Render inputs, return config dict."""
    config = {}
    val = parameter_input(label, baseline, key)
    if val != baseline:
        config["key"] = val
    return config
```

### Render Pattern (output modules)

```python
def render(case: PipelineResult, baseline: PipelineResult, ui_config: dict):
    """Render results with case vs baseline comparison."""
    # Load data from pipeline
    # Calculate delta
    # Display metrics/charts with color coding (orange = modified)
```

### parameter_input Pattern

- Each input shows "Modified" label if value != baseline
- Baseline value shown as reference
- `parameter_input()`, `parameter_select()`, `parameter_header()` in `parameter_input.py`

### None = Baseline Convention

- In `ui_config`: `None` -> "use baseline value"
- Non-None -> user adjustment to be applied
- `get_filtered_ui_config()` filters out unselected modules

### Naming

- Module prefix: `m1_`, `m2_`, `m3_`, `m4_`, `m5_`, `addon_`
- Parameters: `"1.1.1"`, `"3.2.5"` (User Manual reference)
- Variables: `"10.X"`, `"30.2"`, `"40.1"`
- Files: `m{N}_{name}.py` (input), `m{N}_{name}_output.py` (output)

### Dataclasses

- Pipeline outputs: `@dataclass(frozen=True)` (immutable)
- Config: Regular dataclasses with defaults
- Module registry: `@dataclass(frozen=True)` (ModuleDefinition, ModuleSection)

### Language in Code

- **Python identifiers** (functions, variables, classes): English
- **DataFrame column names**: English (via COL_* constants from config/column_names.py)
- **Data files**: Swedish column names (external regulatory sources, renamed at load boundary)
- **UI text**: English
- **Domain terms**: Swedish regulatory terms preserved where appropriate (intaktsram, pavekrbara, KENT, NUAV)

### Asset Categories

17 asset categories (cat_encode 1-17) defined in `config/asset_categories.py`.
Each has: cat_encode, name_sv, name_en, ek_dep (economic depreciation years),
max_dep (max depreciation years).

### Half-Year Time Codes

```
229 = 2024H1,  230 = 2024H2
231 = 2025H1,  232 = 2025H2
233 = 2026H1,  234 = 2026H2
235 = 2027H1,  236 = 2027H2
```


## 18. Testing

**Run:** `./venv/Scripts/python.exe -m pytest tests/ -v`
**Coverage:** `./venv/Scripts/python.exe -m pytest tests/ -v --cov=calculations --cov=pipeline`
**~260 tests**, all green, ~70s total runtime.

**Session-scoped fixtures** (loaded once in `tests/conftest.py`):
- `baseline_data` -- Full BaselineData (all 148 companies)
- `capbase_mini` -- Mini capbase (3 companies)
- `controllable_detail_mini`, `controllable_meta_mini`, `non_controllable_detail_mini` -- Grunddata minis
- `kent_results_mini` -- KENT calculation output
- `pipeline_result_886` -- Full pipeline for company 886

**Key tests:**
- `test_baseline_replication.py` -- Replicates facit values with hardcoded expected values
- `test_cost_aggregation.py` -- Verifies grunddata aggregation matches SDF sheets
- `test_override_cascades.py` -- OPEX/flex/non-adj scaling and override cascade through pipeline
- `test_result_snapshot.py` -- Result snapshot extraction tests
- `test_new_benchmarking_precompute.py` -- New-benchmarking bundle shape + freshness guard
  (recomputes the main spec live and asserts it matches the committed bundle, incl. the kr columns)
- `test_new_benchmarking_cost_impact.py` -- kr quantification: `period_efficiency_amount`
  matches the revenue-cap pipeline's compounding exactly; application-base and sign sanity

**Known:** Company 886 has ~354 tkr rounding difference in capital_cost_2024 (KENT vs DM).


## 19. User Manuals (LaTeX) & the tool registry

Each tool ships its own manual, authored in LaTeX and independent of the Python
application. The tools themselves are described centrally by the **tool registry**.

### Tool registry (`config/tools_registry.py`)

`ToolSpec` (frozen dataclass) + the `TOOLS` list are the Streamlit-free single
source of truth for the tools: `key`, `name`, `branch` (`revenue_cap` /
`standalone`), `summary`, `icon`, `status` (`available` / `beta` / `coming_soon`),
`manual_slug`, `public`, `page_path`. `tools_for(branch)` drives the `#tools`
section of the landing ([landing_pages/landing.py](landing_pages/landing.py));
being pure data it ports directly to the future React landing.

### Manuals: source -> published

| Location | Role |
|----------|------|
| `user_manual_latex/manuals/<slug>/main.tex` | **Source** for the PDF (one folder per tool; `shared/` holds the common preamble + `references.bib`) |
| `user_manual_latex/manuals/<slug>/main.md` | **Content store** for the in-page reader: a Markdown twin with YAML frontmatter (`title`, `subtitle`, `version`, `status`, `date`, `url`). Committed |
| `user_manual_latex/manuals/<slug>/build/main.pdf` | Build artifact (gitignored) |
| `static/manuals/<slug>.pdf` | **Published** PDF the app serves (committed) |
| `static/manual_reader/{reader.css,reader.js}` | The framework-agnostic in-page reader (Streamlit-free; committed) |

`main.tex` and `main.md` are **separate twins, not auto-converted**: build.sh only
touches the PDF, and the in-page reader only reads `main.md`. To change the in-page
manual, edit `main.md` (no build step). To change the downloadable PDF, edit
`main.tex` and rebuild. `user_manual_latex/build.sh` is the PDF bridge: `./build.sh`
builds every manual (or `./build.sh <slug>` just one), runs `latexmk -r latexmkrc`,
and copies `build/main.pdf` -> `static/manuals/<slug>.pdf`.

Each tool card on the landing offers the manual two ways: **"User manual (PDF)"**
opens the published PDF in a new window (a static `<a
href="app/static/manuals/<slug>.pdf">` link), and **"User manual (inline)"** opens
the **manual reader** in a wide `@st.dialog` (widened past "large" via CSS in
`landing_shell.py`). The reader is a self-contained, framework-agnostic HTML
document (`static/manual_reader/reader.css` + `reader.js`): a two-pane layout
(sticky table of contents + scrolling content) with click-to-scroll and a
scroll-spy that bolds the section in view. It auto-builds the TOC from the
markdown's `h2`-`h4` headings (shared `slugify`, so anchors/deep links are stable)
and renders math/tables client-side (`markdown-it` + `markdown-it-anchor` +
`markdown-it-texmath`/KaTeX, pinned CDN). The iframe is required, not cosmetic:
scroll-spy and smooth in-pane scrolling need client-side JS, which `st.markdown`
cannot run.

`frontend/common/manuals.py` is the thin host seam (the only Streamlit-aware part;
a future React/Next.js landing reuses the `static/manual_reader/` bundle and drops
it): `manual_bytes` / `manual_path` for the PDF; `manual_reader_html` builds the
reader document from `main.md` (inlining the reader bundle, loading the libs from
CDN, injecting the markdown + the Nordic-Energy theme tokens); `manual_markdown` /
`manual_markdown_path` read the raw `main.md`. The cards are built natively
(`landing.py` `_render_tool_cards`, a keyed `st.container`) rather than as an HTML
string, because the inline action is a real `st.button` and a Streamlit widget
cannot live inside an HTML blob (and a plain `<a>` link can't stay in the same
window — Streamlit opens markdown links in a new tab).

**Naming rule:** the LaTeX folder name, the `main.md` twin, the published
`static/manuals/<slug>.pdf` filename, and the registry's `manual_slug` must all be
the same `<slug>`, or a manual link silently disappears. build.sh couples the tex
folder and the PDF; the registry is guarded by `tests/test_tools_registry.py`
(every `available` tool has a published PDF *and* a `main.md`; no orphan PDFs). The
one deliberate divergence is `revenue_cap` (key) -> `regumetrica_user_manual`
(manual_slug).

Requires a LaTeX toolchain (MacTeX/BasicTeX) on PATH; VS Code uses the
`James-Yu.latex-workshop` extension. See `user_manual_latex/LATEX_VSCODE_SETUP.md`.


## 20. New Benchmarking Add-on (page 5)

A standalone analysis of Ei's proposed new benchmarking model (TOTEX-based DEA),
**decoupled** from the case/revenue-frame pipeline. It answers: "how would the company be
affected by the new model alone, all else equal?" It calls `run_new_benchmarking()`
directly and never builds a `CaseDefinition`.

It is packaged as a **self-contained vertical module** at the repo root,
`new_benchmarking_model/`, rather than split across `calculations/`, `frontend/`,
`data_loaders/` and `scripts/`. Layout: `config.py` + `model.py` (entry point), `totex/`
(TOTEX build), `efficiency/` (two-sided requirement + kr impact), `components/` (DEA-input
builders: cable_length, environment/station capex adjustments), `data/` (precompute builder,
runtime loader, committed parquet bundle), `ui/` (the only Streamlit-dependent part: page +
graph drawers), and `docs/`. The pure-calc rule still holds inside it: everything outside
`ui/` is Streamlit-free.

> **Dependency map:** `new_benchmarking_model/docs/dependency_graph.md` is a README-style,
> Claude-readable walkthrough of the whole chain (capbase -> capital cost -> TOTEX -> DEA
> -> efficiency requirement): a Mermaid graph plus step-by-step prose with file/line refs,
> data sources, config switches and gotchas. Point new conversations there before touching
> `new_benchmarking_model/`.

### Backend (`new_benchmarking_model/`, `model.py` orchestrating `totex/` + `efficiency/` + `components/`)

`run_new_benchmarking(cfg) -> NewBenchmarkingResult` builds a new TOTEX per company and
runs one DEA pass, comparing against the current model (read directly from EIs_DEA, not
recomputed — the firm's actual "föregående värden"):

- **TOTEX** = `controllable_cost_average` (reused from baseline, apples-to-apples)
  + network losses valued at a common price (`nf_obs · k_nf · e_in`)
  + selected non-controllable categories (grid subscription/connection, feed-in, capacity
  reserve) + förläggningsmiljö-adjusted `capital_cost_2024`. The adjusted capital cost
  re-runs KENT on a capbase whose jordkabel (cat 3) and nätstation (cat 13) NUAV is
  levelled to a reference environment (cable + station sub-packages).
- **DEA**: single TOTEX input + base outputs (CU, MW, NS, MWhl, MWhh) + cable length.
- **Efficiency requirement** (`efficiency/efficiency_requirement_two_sided.py`): the firm's annual
  outcome is a *signed* gap to the third quartile, replacing the legacy front-reference /
  deduction-only mechanic (which still drives the revenue-cap pipeline, M5, untouched).
  `E75` = the 75th-percentile efficiency over non-outliers; `outcome = annualize(clip(E75 −
  E_i, ±0.30) × 0.50 × 4/8)` → a deduction below the benchmark (>0), full coverage at it, a
  reward above (<0). No floor, no fixed outlier requirement; outliers are excluded from the
  percentile but still scored. See
  `new_benchmarking_model/docs/tolkning-overgang-effektiviseringsincitament.md` for the interpretation.
- **Cost impact in kronor** (`efficiency/cost_impact.py`): the efficiency requirement is a percentage;
  the kronor impact applies it to a cost base over the 4-year supervision period. Per Ei the
  two models apply their % to *different* bases (the point of the reform, see
  `docs/ei_to_markdown/outputs/tillampningsmetod-effektiviseringsincitament.md`): the current
  model on **OPEX** (controllable + neon), the new model on the full **uncorrected TOTEX**
  (controllable + neon + actual losses + selected non-controllable + unadjusted capital cost).
  The benchmarking corrections (common-price losses, förläggningsmiljö capex) set the % but
  never the kronor base. `period_efficiency_amount()` reuses the revenue-cap pipeline's
  compounding mechanic exactly (asserted in tests), so the current figure matches the
  pipeline. The bases and the two period-sum kr figures are merged onto the `totex` frame
  (`COL_OPEX_BASE_CURRENT`, `COL_APPLICATION_BASE_NEW`, `COL_KR_CURRENT`, `COL_KR_NEW`).
  Because the new % applies to a much larger base, an outcome can fall in % yet rise in
  kronor - true for ~52% of companies, the model's headline insight.
- `NewBenchmarkingConfig` holds every choice; `cfg.signature()` is its stable identity,
  used both as the @st.cache_data key and as the pre-compute bundle's validity token.

### Pre-computed main spec

The fixed main spec (`NewBenchmarkingConfig()`) is expensive (148-company KENT re-run +
DEA) yet identical for every user, and `@st.cache_data` is wiped on each redeploy. So it
is pre-computed offline (`new_benchmarking_model/data/precompute.py`) into
`new_benchmarking_model/data/precomputed/` and loaded at runtime
(`new_benchmarking_model/data/loader.py`, `load_precomputed_main()`), which reconstructs the
`NewBenchmarkingResult`. Guarded by the
config-signature token plus `test_new_benchmarking_precompute.py`, which recomputes the
spec live and fails if the committed bundle has drifted. Only the default spec is
pre-computed; Experiment-panel tweaks still run live (cached per signature).
**Re-run the script whenever the main spec, the calculation code, or the source data
changes.**

### Frontend (`new_benchmarking_model/ui/`)

- `pages/5_new_benchmarking.py` -- a thin Streamlit shim; it just calls
  `new_benchmarking_model.ui.page.render_page()` (the file stays under `pages/` for
  Streamlit's navigation, registered in `streamlit_app.py`).
- `ui/page.py` -- `render_page()`: a company subheader (`get_company_display`), the model
  description, the results, then the Experiment expander. The Experiment panel's "Run
  experiment" button commits a config to session state; the heavy DEA fires only on click
  (editing widgets just marks pending changes).
- `ui/config_panel.py` -- `render_config_panel()`: the few
  adjustable fields (common loss price defaulted from `K_NF`, cable/station method, line
  types), a "Run experiment" button, and a "Reset to main model" button that clears the
  committed config and widget keys.
- `ui/company_view.py` -- per-company view, firm-first. Every figure is framed as the impact
  on the firm's **revenue frame** (positive = the cap is raised), flipped from the regulatory
  deduction-positive convention at a single display seam (`revenue_frame_impact` in
  `ui/charts.py`); the model, comparison and kr data keep the regulatory sign untouched. The
  verdict is pinned on top, then the thematic groups are stacked vertically (no tabs):
  - **Your company** (verdict): a from/to transition (how the new model raises or lowers the
    cap *relative to the current model*, coloured by the kronor swing - raises green, lowers
    amber - with a plain-language note when % and kronor diverge); plus KPI cards (Current
    model, New model, change in kronor, efficiency + rank), all in revenue-frame terms.
  - **Efficiency & outcome**: the position chart (efficiency histogram with the E75 pivot
    splitting the lower-cap / higher-cap zones, the transfer curve and a clear 0-impact line,
    the firm marked), the diverging revenue-frame-impact distribution (raises right/green,
    lowers left/amber), the lower-cap / full-coverage / higher-cap counts, and three
    new-vs-current scatters (rank, efficiency, revenue-frame impact; points green where the
    new model favours the firm, amber where not, with a prominent no-change diagonal).
  - **TOTEX bridge**: the waterfall (current -> new TOTEX: additions red, the förläggningsmiljö
    capex cut green, totals blue).
  A fourth group, **Outcome decomposition** (sector-level channel / Shapley analysis read from
  the committed `analysis/out/` tables), is built and wired but hidden for V1 as too technical
  (`HIDDEN_CHART_GROUPS`; re-enabling is a one-line move). The groups are stacked by
  `ui/chart_panel.py` (`render_chart_panel`), which owns the layout so a horizontal switcher
  can be restored in one place. The two-sided visuals live in `ui/charts.py` (not the
  M5-shared `frontend/results/_efficiency_charts.py`).

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
|-- streamlit_app.py              # Entrypoint: auth guard, sidebar, navigation
|-- requirements.txt              # Python dependencies
|-- .streamlit/config.toml        # Streamlit config (theme, port 8501)
|
|-- pages/                        # Streamlit multi-page app
|   |-- login.py                  # Authentication (Firebase)
|   |-- 1_create_and_select_case.py  # Create/load/delete/duplicate/compare cases
|   |-- 2_case_setup.py           # Case Setup: select modules/sections
|   |-- 3_specification.py        # Specification: configure parameters (tabs M1-M7)
|   |-- 4_revenue_frame.py        # Revenue Frame: display results, export
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
|   |-- config_adapter.py         # UI config -> CaseDefinition (only bridge frontend->backend)
|
|-- frontend/                     # Streamlit-dependent UI code ONLY
|   |-- common/                   # Shared Streamlit components
|   |   |-- parameter_input.py    # Reusable input component with baseline comparison
|   |   |-- styling.py            # CSS injection, font loading (re-exports from config.colors)
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
|   |       |-- mini_run_output.py        # Inline DEA/StoNED mini-run results in Configure
|   |
|   |-- results/                  # Output renderers per module
|   |   |-- m1_asset_base_output.py       # NUAV, category breakdown
|   |   |-- m2_depreciation_output.py     # Depreciation values
|   |   |-- m3_cost_of_capital_output.py  # (imports m3_return_output)
|   |   |-- m3_return_output.py           # WACC, return on assets
|   |   |-- m3_incentive_output.py        # Quality/incentive adjustments
|   |   |-- m4_operating_exp_output.py    # OPEX results
|   |   |-- m5_efficiency_output.py       # Efficiency requirements
|   |
|   |-- utils/                    # Streamlit-dependent frontend utilities
|       |-- state_manager.py      # Session state: init, get/set, config references
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
|   |-- revenue_frame_assembly.py            # Cross-cutting: final revenue frame assembly
|
|-- visualization/                # Streamlit-free visualization (Plotly, HTML, geodata)
|   |-- diagram_data.py           # Revenue frame decomposition data
|   |-- diagram_utils.py          # Interactive HTML/CSS diagram generation
|   |-- geo_data.py               # Shapefile loading, geodata preparation
|   |-- geo_visualization.py      # Choropleth map visualization (Plotly)
|
|-- data_loaders/                 # Data loading (cached with @st.cache_data)
|   |-- baseline_data.py          # BaselineData: Data_modeller.xlsx (148 companies)
|   |-- cost_data.py              # Grunddata parquet loaders (used by baseline_data)
|   |-- rab_data.py               # RAB data (capbase_a.parquet, capcost_a.parquet)
|   |-- incentive_data.py         # Incentive parameters
|
|-- auth/
|   |-- firebase_auth.py          # Firebase auth: login, registration, claims, dev mode
|   |-- firebase_firestore.py     # Firestore client (singleton)
|   |-- cookie_session.py         # Cookie-based session persistence (refresh token)
|
|-- data/                         # Data files (external/regulatory sources, DO NOT RENAME)
|   |-- Data_modeller.xlsx        # Main data: 148 companies, CAPEX/OPEX/volumes/returns
|   |-- EIs_DEA.xlsx              # Ei's baseline DEA results
|   |-- [SDF running costs].xlsx  # SDF regulatory submissions (Swedish filename w/ diacritics)
|   |-- capbase_a.parquet         # Capital base per company/category/time (18 MB)
|   |-- capbase_a_mini.parquet    # Mini version for testing (3 companies)
|   |-- capcost_a.parquet         # Capital costs per category
|   |-- controllable_a.parquet    # Controllable cost grunddata (detail per category/year)
|   |-- controllable_a_mini.parquet # Mini version for testing (3 companies)
|   |-- controllable_meta.parquet # Controllable cost meta (index, neo_adjustment, eff_req_pct)
|   |-- controllable_meta_mini.parquet # Mini version for testing (3 companies)
|   |-- non_controllable_a.parquet # Non-controllable cost grunddata (per category/year)
|   |-- non_controllable_a_mini.parquet # Mini version for testing (3 companies)
|   |-- reconciliation_id_network_firm_dmu.csv  # ID mapping (REId <-> id_network <-> DMU)
|   |-- adjustment_final (1).csv  # Adjustment variables
|   |-- all_adjust_vars.csv       # All adjustable variables
|   |-- shapefiles/               # Geographic shapefiles (municipality/county)
|
|-- tests/                        # pytest test suite (205 tests, ~85s)
    |-- conftest.py               # Session-scoped fixtures
    |-- test_baseline_replication.py
    |-- test_kent_calculations.py
    |-- test_wacc.py
    |-- test_dea.py
    |-- test_efficiency_requirement.py
    |-- test_controllable_costs.py
    |-- test_cost_aggregation.py     # Grunddata aggregation verification
    |-- test_incentive_calculations.py
    |-- test_revenue_frame.py
    |-- test_pipeline_integration.py
    |-- test_override_cascades.py    # Category override cascade tests
```


## 4. Architecture Layers (dependency flow)

Dependencies flow strictly downward. Lower layers NEVER import from higher layers.
`calculations/` has no UI dependencies. `config/` knows nothing about Streamlit.

```
Layer 1: PAGES (top)
    streamlit_app.py, pages/login.py,
    pages/1_create_and_select_case.py, pages/2_case_setup.py,
    pages/3_specification.py, pages/4_revenue_frame.py
        |
        | imports
        v
Layer 2: FRONTEND (Streamlit-dependent only)
    Left side: FRONTEND UTILS
        state_manager.py, case_storage.py, case_actions.py,
        result_snapshot.py, export_button.py
    Right side: FRONTEND COMMON + MODULES
        parameter_input.py, styling.py, save_bar.py, case_comparison.py,
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
    time_codes.py, incentive_parameters.py, config_adapter.py
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


## 5. Page Flow & Navigation

```
Unauthenticated                Authenticated
---------------                -------------
pages/login.py    --auth-->    pages/1_create_and_select_case.py  (Create & Select)
                                       |
                                       v
                               pages/2_case_setup.py              (Case Setup)
                                       |
                                       v
                               pages/3_specification.py           (Specification)
                                       |
                                  [Compute] (on page 4)
                                       |
                                       v
                               pages/4_revenue_frame.py           (Revenue Frame)
```

**Entrypoint:** `streamlit_app.py`
- Configures page (`st.set_page_config`)
- Applies styling
- Initializes session state
- Auth guard: `check_auth()` -> shows login OR app navigation
- Sidebar: Company selector + Compute + Revert/New case + stale results indicator


## 6. Module Architecture (M1-M7)

Modules are defined centrally in `config/module_registry.py`.
Each module has sections for fine-grained control.

| Module        | Purpose                     | Input file                  | Output file                   | Config key               |
|---------------|-----------------------------|-----------------------------|-------------------------------|--------------------------|
| M1            | Asset base valuation        | m1_asset_base.py            | m1_asset_base_output.py       | m1_asset_base            |
| M2            | Depreciation                | m2_depreciation.py          | m2_depreciation_output.py     | m2_depreciation          |
| M3 WACC       | Cost of capital (CAPM)      | m3_cost_of_capital.py       | m3_return_output.py           | m3_cost_of_capital       |
| M3 Incentive  | Quality/incentive adj.      | m3_incentive_variables.py   | m3_incentive_output.py        | m3_quality_adjustments   |
| M4            | Operating expenditure       | m4_operating_exp.py         | m4_operating_exp_output.py    | m4_operating_exp         |
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
Step 1: User adjusts parameters in pages/1_case_config.py
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
pages/2_results.py receives PipelineResult
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
Controllable:    COL_CONTROLLABLE_AVG, COL_CONTROLLABLE_2024 .. 2027, COL_CONTROLLABLE_PERIOD
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
2. Login via `pages/login.py` (email/password)
3. Custom claims: `{REId: "REL00886", role: "company"}`
4. Session state: `auth_email`, `auth_role`, `auth_reid`, `auth_uid`, `auth_token`

### Session Persistence (cookie_session.py)

Authentication survives page refreshes via a browser cookie storing the Firebase refresh token.

**Files:** `auth/cookie_session.py` (helpers), `streamlit_app.py` (restore), `pages/login.py` (save)

**Flow on login:**
1. Firebase `sign_in` → returns `refreshToken`
2. `set_auth_cookie(refreshToken)` → JavaScript sets cookie (`regumetrica_auth`, 30-day expiry)

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
- capbase_source, user_capbase_scaled, kent_file_bytes, kent_user_id_network
- method (CapexMethod), wacc, normvalue_adjustments, lifetime_adjustments
- wacc_input_method ("capm"/"derived"/"direct"/"baseline"), wacc_capm_inputs
- opex_scaling (4.1.1) -- float multiplier for user's company controllable OPEX only
- opex_override (40.1.1) -- absolute OPEXp in tkr for user's company (trumps scaling)

**DeaConfig** (Stage 3):
- method (EfficiencyMethod), inputs, outputs, rts ("crs"/"vrs")
- orientation ("input"), q_lower (25.0), q_upper (75.0), multiplier (2.0)

**IncentiveConfig** (nested in PostDeaConfig):
- kpi, k_nf, sharing_netloss (0.75), adj_max_agg (1/3), adj_max_cemi4 (0.25)
- ait_costs, aif_costs, enable_quality/netloss/load, variable_overrides

**PostDeaConfig** (Stage 5):
- truncation_min (0.01), truncation_max (0.30), outlier_req (0.01)
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

### Key Calculation Details

**KENT:** Steps 1-4 (capbase prep) then 5-8 (depreciation, returns, capital cost).
Uses half-year timecodes: 229=2024H1, 230=2024H2, 231=2025H1, ..., 236=2027H2.

**DEA:** Input-oriented CRS. Default inputs: [capital_cost_2024, controllable_cost_average].
Default outputs: [CU, MW, NS, MWhl, MWhh]. Outlier detection via IQR method.
DEA always uses baseline (historical) cost data — user changes to OPEX/CAPEX/WACC
do NOT affect DEA inputs. Only the model specification (inputs, outputs, RTS) can be changed.

**Efficiency requirement:** Converts DEA potential via truncation, customer sharing (50%),
realization time (8 years), supervision period (4 years).

**Incentives:** 3 types -- quality (CEMI4), network loss (NF), load (UG).
Per-year calculations with individual and aggregate caps.
Baseline: KPI ~1.1546/year, k_nf ~753.44 kr/MWh, sharing_netloss=0.75.
Column format: `ait_{ann}_{sni}_{norm/obs}`, `ame_{sni}`, output `_a` suffix = before capping.


## 14. Data Loaders (Load Boundary)

All data loading is cached with `@st.cache_data(ttl=3600)`.
Swedish column names from files are renamed to English here using rename dicts.

### baseline_data.py

`load_baseline_data() -> BaselineData` (frozen dataclass):
- `df_all_companies` -- 148 rows from Data_modeller.xlsx (OPEXp replaced with SDF-derived values)
- `dea_results` -- Baseline DEA from EIs_DEA.xlsx
- `sdf_ir` -- Revenue frame baseline from SDF file
- `sdf_controllable` -- Controllable costs from SDF file (raw sheet, used for verification)
- `reconciliation` -- REId <-> id_network mapping
- `wacc` -- float, default 0.0453
- `controllable_detail` -- Per-category controllable grunddata (from controllable_a.parquet)
- `controllable_meta` -- Controllable meta with index/neo (from controllable_meta.parquet)
- `non_controllable_detail` -- Per-category non-controllable grunddata (from non_controllable_a.parquet)

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


## 15. File Dependencies (Import Map)

```
streamlit_app.py
    |-- frontend.utils.state_manager      (init, get/set functions)
    |-- frontend.common.styling           (apply_styling)
    |-- auth.firebase_auth                (is_dev_mode, initialize_firebase_auth)

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

| File                                          | Format  | Contents                                        |
|-----------------------------------------------|---------|-------------------------------------------------|
| data/Data_modeller.xlsx                       | Excel   | 148 companies: CAPEX, OPEX, volumes, returns    |
| data/EIs_DEA.xlsx                             | Excel   | Ei's baseline DEA results                       |
| data/[SDF running costs].xlsx                 | Excel   | SDF submissions: revenue cap, controllable, etc. |
| data/capbase_a.parquet                        | Parquet | Capital base per company/category/time (18 MB)  |
| data/capbase_a_mini.parquet                   | Parquet | Mini capbase for testing (3 companies)          |
| data/capcost_a.parquet                        | Parquet | Capital costs per category                      |
| data/controllable_a.parquet                   | Parquet | Controllable grunddata: REId, category, year, amount |
| data/controllable_meta.parquet                | Parquet | Controllable meta: index factors, neo_adjustment |
| data/non_controllable_a.parquet               | Parquet | Non-controllable grunddata: REId, kent_category, year, amount |
| data/*_mini.parquet                           | Parquet | Mini versions (3 test companies) for unit tests |
| data/reconciliation_id_network_firm_dmu.csv   | CSV     | ID mapping: REId <-> id_network <-> DMU         |
| data/adjustment_final (1).csv                 | CSV     | Adjustment variables                            |
| data/all_adjust_vars.csv                      | CSV     | All adjustable variables (48 cols)              |
| data/shapefiles/                              | SHP     | Geographic boundaries (municipality/county)     |

**Note:** The SDF file has a Swedish filename with diacritics. In code it is loaded from
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
**205 tests**, all green, ~65s total runtime.

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

**Known:** Company 886 has ~354 tkr rounding difference in capital_cost_2024 (KENT vs DM).

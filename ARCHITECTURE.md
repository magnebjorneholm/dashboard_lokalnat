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
|   |-- 0_case_definition.py      # Step 1: Select modules/sections, name case
|   |-- 1_case_config.py          # Step 2: Configure parameters (tabs M1-M7)
|   |-- 2_results.py              # Step 3: Display results, snapshots, export
|
|-- frontend/
|   |-- common/                   # Shared UI components & data
|   |   |-- module_registry.py    # Module definitions (M1-M7), sections, selection logic
|   |   |-- parameter_input.py    # Reusable input component with baseline comparison
|   |   |-- asset_categories.py   # 17 asset categories (codes, names, lifetimes)
|   |   |-- styling.py            # Colors, fonts (Inter, IBM Plex Mono), CSS
|   |   |-- formatting.py         # Formatting: tkr, percent, delta
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
|   |   |-- m4_operating_exp_output.py    # OPEX results
|   |   |-- m5_efficiency_output.py       # Efficiency requirements
|   |   |-- m7_benchmarking_output.py     # DEA results, rankings
|   |
|   |-- utils/                    # Frontend utilities
|       |-- state_manager.py      # Session state: init, get/set, snapshots
|       |-- config_adapter.py     # UI config -> CaseDefinition (only bridge frontend->backend)
|       |-- case_storage.py       # Save/load cases (Firestore/local JSON)
|       |-- firebase_firestore.py # Firestore client (singleton)
|       |-- export_button.py      # Export button component
|       |-- export_excel.py       # Excel generation
|       |-- diagram_data.py       # Waterfall diagram data
|       |-- diagram_utils.py      # SVG/HTML diagrams
|       |-- geo_data.py           # Geodata preparation
|       |-- geo_visualization.py  # Map visualization
|
|-- config/
|   |-- case_definition.py        # Dataclasses: CaseDefinition, PreDeaConfig, DeaConfig, etc.
|   |                              # Enums: CapbaseSource, CapexMethod, EfficiencyMethod
|   |-- column_names.py           # COL_* constants, rename dicts (single source of truth)
|
|-- pipeline/
|   |-- core.py                   # run_pipeline(): orchestrates 5 stages -> PipelineResult
|   |-- debug_logger.py           # Structured logging per stage
|   |-- post_dea_capex_helpers.py # Helper functions for post-DEA
|   |-- stages/
|       |-- stage_outputs.py      # Frozen dataclasses per stage
|       |-- baseline.py           # Stage 1: Convert BaselineData
|       |-- pre_dea.py            # Stage 2: CAPEX/WACC calculation
|       |-- dea.py                # Stage 3: DEA efficiency analysis
|       |-- extraction.py         # Stage 4: Extract user's company
|       |-- post_dea.py           # Stage 5: Efficiency requirement + revenue cap
|
|-- calculations/                 # Pure calculation logic (no UI dependencies)
|   |-- wacc_calculations.py              # CAPM -> WACC
|   |-- kent_calculations.py              # KENT processing (steps 5-8)
|   |-- kent_capbase_prep.py              # KENT steps 1-4, capbase_a format
|   |-- dea_calculations.py               # DEA via PuLP
|   |-- incentive_calculations.py         # Quality/loss/load adjustments
|   |-- incentive_parameters.py           # KPI factors, k_nf constants
|   |-- revenue_frame_assembly.py         # Revenue frame assembly
|   |-- efficiency_requirement.py         # Efficiency requirement calculation
|   |-- controllable_cost_calculations.py # Controllable cost calculations
|   |-- data_mapping.py                   # Asset category mapping
|   |-- time_codes.py                     # Half-year period coding
|
|-- data_loaders/                 # Data loading (cached with @st.cache_data)
|   |-- baseline_data.py          # BaselineData: Data_modeller.xlsx (148 companies)
|   |-- rab_data.py               # RAB data (capbase_a.parquet, capcost_a.parquet)
|   |-- incentive_data.py         # Incentive parameters
|
|-- auth/
|   |-- firebase_auth.py          # Firebase auth: login, registration, claims, dev mode
|
|-- data/                         # Data files (external/regulatory sources, DO NOT RENAME)
|   |-- Data_modeller.xlsx        # Main data: 148 companies, CAPEX/OPEX/volumes/returns
|   |-- EIs_DEA.xlsx              # Ei's baseline DEA results
|   |-- [SDF running costs].xlsx  # SDF regulatory submissions (Swedish filename w/ diacritics)
|   |-- capbase_a.parquet         # Capital base per company/category/time (18 MB)
|   |-- capbase_a_mini.parquet    # Mini version for testing
|   |-- capcost_a.parquet         # Capital costs per category
|   |-- reconciliation_id_network_firm_dmu.csv  # ID mapping (REId <-> id_network <-> DMU)
|   |-- adjustment_final (1).csv  # Adjustment variables
|   |-- all_adjust_vars.csv       # All adjustable variables
|   |-- shapefiles/               # Geographic shapefiles (municipality/county)
|
|-- tests/                        # pytest test suite (136 tests, ~50s)
    |-- conftest.py               # Session-scoped fixtures
    |-- test_baseline_replication.py
    |-- test_kent_calculations.py
    |-- test_wacc.py
    |-- test_dea.py
    |-- test_efficiency_requirement.py
    |-- test_controllable_costs.py
    |-- test_incentive_calculations.py
    |-- test_revenue_frame.py
    |-- test_pipeline_integration.py
```


## 4. Architecture Layers (dependency flow)

Dependencies flow strictly downward. Lower layers NEVER import from higher layers.
`calculations/` has no UI dependencies. `config/` knows nothing about Streamlit.

```
Layer 1: PAGES (top)
    streamlit_app.py, pages/login.py,
    pages/0_case_definition.py, pages/1_case_config.py,
    pages/2_results.py
        |
        | imports
        v
Layer 2: FRONTEND
    Left side: FRONTEND UTILS
        state_manager.py, config_adapter.py,
        case_storage.py, export_*.py, diagram_*.py, geo_*.py
    Right side: FRONTEND COMMON + MODULES
        module_registry.py, parameter_input.py, asset_categories.py,
        styling.py, formatting.py,
        m1_asset_base.py .. m5_efficiency.py, benchmarking.py
        |
        | imports
        v
Layer 3: CONFIG
    case_definition.py (CaseDefinition, enums)
    column_names.py (COL_* constants)
        |
        | imports
        v
Layer 4: PIPELINE
    core.py -> stages/baseline -> pre_dea -> dea -> extraction -> post_dea
    stage_outputs.py (frozen dataclasses)
        |
        | imports
        v
Layer 5: CALCULATIONS + DATA LOADERS (bottom)
    Left side: CALCULATIONS
        wacc, kent, dea, incentive,
        revenue_frame_assembly, efficiency_requirement,
        controllable_cost
    Right side: DATA LOADERS
        baseline_data.py, rab_data.py, incentive_data.py
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
pages/login.py    --auth-->    pages/0_case_definition.py  (Define)
                                       |
                                       v
                               pages/1_case_config.py      (Configure)
                                       |
                                  [Compute] (sidebar button)
                                       |
                                       v
                               pages/2_results.py          (Results)
```

**Entrypoint:** `streamlit_app.py`
- Configures page (`st.set_page_config`)
- Applies styling
- Initializes session state
- Auth guard: `check_auth()` -> shows login OR app navigation
- Sidebar: Company selector + "Compute Revenue Frame" + "Save case"


## 6. Module Architecture (M1-M7)

Modules are defined centrally in `frontend/common/module_registry.py`.
Each module has sections for fine-grained control.

| Module        | Purpose                     | Input file                  | Output file                   | Config key               |
|---------------|-----------------------------|-----------------------------|-------------------------------|--------------------------|
| M1            | Asset base valuation        | m1_asset_base.py            | m1_asset_base_output.py       | m1_asset_base            |
| M2            | Depreciation                | m2_depreciation.py          | m2_depreciation_output.py     | m2_depreciation          |
| M3 WACC       | Cost of capital (CAPM)      | m3_cost_of_capital.py       | m3_return_output.py           | m3_cost_of_capital       |
| M3 Incentive  | Quality/incentive adj.      | m3_incentive_variables.py   | m3_incentive_output.py        | m3_quality_adjustments   |
| M4            | Operating expenditure       | m4_operating_exp.py         | m4_operating_exp_output.py    | m4_operating_exp         |
| M5            | Efficiency requirement      | m5_efficiency.py            | m5_efficiency_output.py       | m5_efficiency            |
| M7            | Benchmarking (DEA)          | benchmarking.py             | m7_benchmarking_output.py     | addon_benchmarking       |

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

| Key                    | Type            | Description                                      |
|------------------------|-----------------|--------------------------------------------------|
| user_reid              | str             | Selected company's REId (sole authoritative ID)  |
| ui_config              | Dict[str, Dict] | Module configurations (8 top-level keys)        |
| selected_modules       | Set[str]        | Selected modules/sections                        |
| baseline_result        | PipelineResult  | Baseline calculation                             |
| case_result            | PipelineResult  | User's case calculation                          |
| calculation_done       | bool            | Flag: calculation completed                      |
| case_id                | str/None        | UUID if saved, None if new                       |
| case_name              | str             | Case name                                        |
| case_notes             | str             | Notes                                            |
| main_ui_config         | Dict            | Snapshot: frozen config after first calculation  |
| main_selected_modules  | Set             | Snapshot: frozen selections                      |
| main_case_result       | PipelineResult  | Snapshot: main result                            |
| result_snapshots       | List[Dict]      | Max 5 saved snapshots per session                |
| auth_*                 | various         | Firebase auth state (email, role, reid, uid)     |

### ui_config Structure (8 module keys)

```python
DEFAULT_UI_CONFIG = {
    "m1_asset_base":          {general_scaling, cat_scaling, var_scaling, kent_file_*},
    "m2_depreciation":        {lifetime_adjustments, lifetime_level},
    "m3_cost_of_capital":     {wacc_override},
    "m3_quality_adjustments": {enable_quality/netloss/load, adj_max_*, sharing_*, k_nf},
    "m3_incentive_variables": {nf_norm/obs, ug_norm/obs, cemi4_norm/obs, ...},
    "m4_operating_exp":       {opex_override},
    "m5_efficiency":          {trunkering_max/min, efficiency_override},
    "addon_benchmarking":     {dea_method, dea_inputs/outputs, dea_rts},
}
```

**Pattern:** All values = `None` means "use baseline". Non-None = user adjustment.

### Snapshot System

1. First calculation -> saved as `main_*`
2. Subsequent calculations -> marked as `_is_snapshot_candidate`
3. User can save as snapshot (max 5) or promote snapshot to main


## 9. Pipeline Architecture

**File:** `pipeline/core.py`
**Signature:** `run_pipeline(baseline_data, case_config) -> PipelineResult`

| Stage | Function             | Input                    | Output                  | Description                              |
|-------|----------------------|--------------------------|-------------------------|------------------------------------------|
| 1     | stage_baseline()     | BaselineData             | BaselineStageOutput     | Converts raw data to stage format        |
| 2     | stage_pre_dea()      | Stage 1 + PreDeaConfig   | PreDeaStageOutput       | CAPEX calculation (KENT 1-8), WACC       |
| 3     | stage_dea()          | Stage 2 + DeaConfig      | DeaStageOutput          | DEA efficiency analysis (148 companies)  |
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
1. `streamlit_app.py` -> `check_auth()` -> dev mode OR Firebase
2. Login via `pages/login.py` (email/password)
3. Custom claims: `{REId: "REL00886", role: "company"}`
4. Session state: `auth_email`, `auth_role`, `auth_reid`, `auth_uid`, `auth_token`


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

**CaseDefinition** (top-level):
- name, user_reid, pre_dea (PreDeaConfig), dea (DeaConfig), post_dea (PostDeaConfig)

**Factory functions:**
- `get_baseline_config(user_reid)` -> default CaseDefinition
- `create_var_scaled_config(...)`, `create_kent_upload_config(...)`,
  `create_parameter_change_config(...)`


## 13. Calculations Module (Pure Logic)

All files in `calculations/` are pure functions with no UI dependencies.

| File                              | Purpose                                    |
|-----------------------------------|--------------------------------------------|
| kent_calculations.py              | KENT steps 5-8: capital cost calculation   |
| kent_capbase_prep.py              | KENT steps 1-4: capbase_a conversion       |
| wacc_calculations.py              | CAPM -> WACC (baseline: 4.53%)             |
| dea_calculations.py               | DEA via PuLP (input-oriented, CRS)         |
| efficiency_requirement.py         | DEA potential -> annual efficiency req      |
| controllable_cost_calculations.py | Controllable costs (OPEX/TOTEX methods)    |
| revenue_frame_assembly.py         | Assemble revenue frame from all components |
| incentive_calculations.py         | Quality/netloss/load incentive adjustments |
| incentive_parameters.py           | Baseline KPI, k_nf, AIT/AIF cost constants |
| data_mapping.py                   | KENT-baseline merge, id_network mapping    |
| time_codes.py                     | Half-year timecodes (229=2024H1, etc.)     |

### Key Calculation Details

**KENT:** Steps 1-4 (capbase prep) then 5-8 (depreciation, returns, capital cost).
Uses half-year timecodes: 229=2024H1, 230=2024H2, 231=2025H1, ..., 236=2027H2.

**DEA:** Input-oriented CRS. Default inputs: [capital_cost_2024, controllable_cost_average].
Default outputs: [CU, MW, NS, MWhl, MWhh]. Outlier detection via IQR method.

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
- `df_all_companies` -- 148 rows from Data_modeller.xlsx
- `dea_results` -- Baseline DEA from EIs_DEA.xlsx
- `sdf_ir` -- Revenue frame baseline from SDF file
- `sdf_controllable` -- Controllable costs from SDF file
- `sdf_non_controllable` -- Non-controllable costs from SDF file
- `reconciliation` -- REId <-> id_network mapping
- `wacc` -- float, default 0.0453

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
    |-- [lazy] data_loaders.baseline_data (load_baseline_data)
    |-- [lazy] frontend.utils.config_adapter (build_case_definition)
    |-- [lazy] pipeline.core              (run_pipeline)
    |-- [lazy] frontend.utils.case_storage (save_case)

pages/1_case_config.py
    |-- frontend.modules.base.m1-m5      (render_* functions)
    |-- frontend.modules.addons.benchmarking
    |-- frontend.utils.state_manager     (is_section_selected)

pages/2_results.py
    |-- frontend.results.m1-m7_output    (render functions)
    |-- frontend.utils.diagram_data, diagram_utils
    |-- frontend.utils.geo_visualization
    |-- frontend.utils.export_button

frontend.utils.config_adapter
    |-- config.case_definition           (CaseDefinition, enums)

pipeline.core
    |-- config.case_definition           (CaseDefinition)
    |-- data_loaders.baseline_data       (BaselineData)
    |-- pipeline.stages.*                (stage functions)
    |-- pipeline.debug_logger

pipeline.stages.*
    |-- calculations.*                   (wacc, kent, dea, incentive, etc.)

frontend.common.module_registry
    |-- (no external dependencies, defines dataclasses)

frontend.utils.state_manager
    |-- frontend.common.module_registry  (parse/build selection keys)
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
| data/capbase_a_mini.parquet                   | Parquet | Mini version for testing (3 companies)          |
| data/capcost_a.parquet                        | Parquet | Capital costs per category                      |
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

17 asset categories (cat_encode 1-17) defined in `frontend/common/asset_categories.py`.
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
**136 tests**, all green, ~50s total runtime.

**Session-scoped fixtures** (loaded once in `tests/conftest.py`):
- `baseline_data` -- Full BaselineData (all 148 companies)
- `capbase_mini` -- Mini capbase (3 companies)
- `kent_results_mini` -- KENT calculation output
- `pipeline_result_886` -- Full pipeline for company 886

**Key test:** `test_baseline_replication.py` replicates facit values with hardcoded
expected values (no Excel loading). Compares KENT vs DM, eff_req vs EIs_DEA, RF vs SDF.

**Known:** Company 886 has ~354 tkr rounding difference in capital_cost_2024 (KENT vs DM).

# Column Rename: Swedish to English

## Overview

All ~88 Swedish DataFrame column names across the Regumetrica codebase were renamed to English canonical names. The rename follows a **boundary pattern**: Swedish names appear only in `data_loaders/` where they map from Excel/parquet file columns to English. All downstream code (calculations, pipeline, frontend, pages) uses English names via `COL_*` constants from `config/column_names.py`.

## Central Constants File

**`config/column_names.py`** is the single source of truth for all column names. It contains:

- ~50 `COL_*` constants (e.g., `COL_CAPITAL_COST_2024 = "capital_cost_2024"`)
- 3 rename dictionaries used by data loaders:
  - `DATA_MODELLER_RENAME` — maps Data_modeller.xlsx Swedish columns to English
  - `EIS_DEA_RENAME` — maps EIs_DEA.xlsx Swedish columns to English
  - `SDF_IR_RENAME` — maps SDF IR sheet Swedish columns to English

## Phases

### Phase 1: Data Loaders

**Files modified:** `data_loaders/baseline_data.py`, `data_loaders/incentive_data.py`

Rename happens at the load boundary. Each loader reads the Excel/parquet file with its original Swedish column names, then applies a rename dictionary before returning the DataFrame. Downstream code never sees Swedish names.

Key renames in `baseline_data.py`:
- `_load_data_modeller()`: applies `DATA_MODELLER_RENAME` after loading (CAPEX -> capital_cost_2024, OPEXp -> controllable_cost_average, etc.)
- `_load_eis_dea()`: applies `EIS_DEA_RENAME` (Effektivitet -> dea_efficiency, Effkrav_proc -> efficiency_requirement_annual, etc.)
- `_load_sdf_running_costs()`: applies `SDF_IR_RENAME` (Kapitalkostnad -> capital_cost_period, etc.)

### Phase 2: Calculations

**Files modified:**
- `calculations/kent_calculations.py` — KENT output columns (Kapitalkostnad_2024 -> capital_cost_2024, Avskrivning_* -> depreciation_*, Avkastning_* -> return_on_assets_*)
- `calculations/controllable_cost_calculations.py` — controllable cost output (Paverkbara_Medelvarde -> controllable_cost_average, Neonjusteringar -> neo_adjustments_period)
- `calculations/revenue_frame_assembly.py` — revenue frame columns (Intaktsram_Total -> revenue_frame_total, Paverkbara_Periodsumma -> controllable_cost_period, etc.)
- `calculations/efficiency_requirement.py` — efficiency requirement output (Effkrav_proc -> efficiency_requirement_annual)
- `calculations/data_mapping.py` — column references in mapping logic
- `calculations/dea_calculations.py` — DEA input/output columns
- `calculations/incentive_calculations.py` — incentive output columns (Kvalitetsjustering_Total -> quality_incentive_total, etc.)

### Phase 3: Pipeline

**Files modified:**
- `pipeline/stages/*.py` — all 5 pipeline stage files updated to use COL_* constants
- `pipeline/helpers.py` — helper functions updated
- `pipeline/debug_logger.py` — debug output references updated

### Phase 4: Frontend and Pages

**Files modified:**
- `frontend/utils/config_adapter.py` — DEA input option constants
- `frontend/utils/diagram_data.py` — revenue frame decomposition data (complete rewrite)
- `frontend/utils/geo_data.py` — geodata for map visualization (complete rewrite)
- `frontend/utils/geo_visualization.py` — map visualization column references (complete rewrite)
- `frontend/results/m3_cost_of_capital_output.py` — incentive column refs
- `frontend/results/m3_incentive_output.py` — incentive column refs
- `frontend/results/m4_operating_exp_output.py` — controllable/non-controllable refs
- `frontend/results/m5_efficiency_output.py` — efficiency output display (complete rewrite)
- `frontend/modules/addons/benchmarking.py` — DEA input/baseline constants
- `pages/2_results.py` — revenue frame and capital cost summary metrics

### Phase 5: Verification

**File modified:** `verification_script.py`

Updated all column references to English names. Added dual English/Swedish pattern matching for SDF column discovery (defensive fallback). Handled merge conflict where both SDF and Data_modeller now output `controllable_cost_average` by using merge suffixes.

## Verification Results

```
Comparisons: 32/33 within tolerance (0.1%)

MISMATCHES (1):
  depreciation_period vs SDF: diff=-1,013.4 tkr (-0.1072%)
```

- **32/33 OK** — all comparisons pass except one pre-existing rounding difference
- **148/148** efficiency requirement exact matches
- **Revenue frame = sum of components** verified for all 3 test companies (residual = 0)
- The single mismatch (depreciation_period, -0.1072%) is a known rounding difference between KENT calculations and the SDF source file, not caused by the rename

## Column Name Reference

| English Name | Swedish Name(s) | Source |
|---|---|---|
| `capital_cost_2024` | CAPEX, Kapitalkostnad_2024 | Data_modeller, KENT |
| `capital_cost_period` | Kapitalkostnad_Period, Kapitalkostnad_Total | KENT, SDF IR |
| `depreciation_2024` | Avskrivning, Avskrivning_2024 | Data_modeller, KENT |
| `depreciation_period` | Avskrivning_Period | KENT, SDF IR |
| `return_on_assets_2024` | Avkastning_2024 | Data_modeller, KENT |
| `return_on_assets_period` | Avkastning_Period | Data_modeller, KENT, SDF IR |
| `controllable_cost_average` | OPEXp, Paverkbara_Medelvarde | Data_modeller, SDF |
| `controllable_cost_period` | Paverkbara_Periodsumma | Pipeline, SDF IR |
| `controllable_cost_before_period` | Paverkbara_Fore_Periodsumma | Pipeline |
| `non_controllable_cost_period` | Opaverkbara_Kostnader | SDF IR |
| `dea_efficiency` | Effektivitet | EIs_DEA |
| `dea_super_efficiency` | Supereffektivitet | EIs_DEA |
| `efficiency_requirement_annual` | Effkrav_proc | EIs_DEA, Pipeline |
| `revenue_frame_total` | Intaktsram_Total | Pipeline, SDF IR |
| `incentive_adjustment_total` | Incitamentjustering_Total | Pipeline |
| `quality_incentive_total` | Kvalitetsjustering_Total | Pipeline |
| `network_loss_incentive_total` | Natforlustjustering_Total | Pipeline |
| `load_incentive_total` | Belastningsjustering_Total | Pipeline |
| `flexibility_services_period` | Flexibilitetstjanster | SDF IR |
| `interruption_compensation_period` | Avbrottsersattning_12_24h | SDF IR |
| `state_subsidy_deduction_period` | Avdrag_Statligt_Stod | SDF IR |
| `method_used` | Method_used | Pipeline |
| `company_name` | Foretag | Data_modeller, EIs_DEA |
| `neo_adjustments_period` | Neonjusteringar | SDF |
| `totex_first_year` | TOTEX | Data_modeller |
| `opex_before` | OPEX_Fore | Pipeline (TOTEX method) |
| `opex_after` | OPEX_Efter | Pipeline (TOTEX method) |
| `opex_efficiency_deduction` | OPEX_Effektivisering | Pipeline (TOTEX method) |
| `capex_efficiency_deduction` | CAPEX_Effektivisering | Pipeline (TOTEX method) |

## Files Not Modified

- **`data_loaders/rab_data.py`** — loads parquet files that already use English column names (nuav_ord, dep_ord, return_ord, etc.)
- **`pages/login.py`** — reads Data_modeller.xlsx directly for company dropdown; uses original file columns (REId, Foretag) at the data boundary
- **`calculations/data_mapping.py`** — contains a defensive fallback list that checks for both English and Swedish column names; English is checked first
- **`calculations/wacc_calculations.py`** — uses only numeric parameters, no DataFrame column names

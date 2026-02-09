# Task: Test-Driven Variable Specification & Canonical Naming

## Context

The codebase currently pulls overlapping data from multiple sources. Many variables (capital costs, depreciation, returns, controllable costs) exist under different names depending on which file they come from and where in the pipeline they are used. The same economic quantity may appear as `CAPEX`, `Kapitalkostnad_2024`, or `Kapitalkostnad_Period` depending on scope (first year vs period sum) and source.

**Current state of the codebase:** Python function names and file names are in English. DataFrame column names are still in Swedish (from data files and calculation outputs). The goal is to establish a definitive specification that enables consolidation to ONE canonical English name per variable.

## Goal

Produce:
1. A **verification script** that cross-references data sources to prove what each variable represents
2. A **specification document** mapping every variable to its exact definition and canonical English name

## Primary Data Sources

| File | Path | Role |
|------|------|------|
| capbase_a.parquet | `data/capbase_a.parquet` | Component-level capital base (~510k rows, 148 companies) |
| capcost_a.parquet | `data/capcost_a.parquet` | Pre-aggregated capital costs per (network, category, time) |
| Data_modeller.xlsx | `data/Data_modeller.xlsx` | 148 companies, DEA input/output data |
| SDF file | `data/Löpande kostnader från SDF 2024-27.xlsx` | Regulatory submission data (sheets: IR 2024-2027, Påverkbara, Opåverkbara) |
| EIs_DEA.xlsx | `data/EIs_DEA.xlsx` | Ei's baseline DEA results |
| all_adjust_vars.csv | `data/all_adjust_vars.csv` | Incentive adjustment variables |
| adjustment_final (1).csv | `data/adjustment_final (1).csv` | Final adjustment variables |

## Key Calculation Functions

All calculation functions are in `calculations/`. Use these -- do NOT reimplement.

| Function | File | Purpose |
|----------|------|---------|
| `run_kent_calculations_batch(capbase_data, wacc=0.0453)` | `calculations/kent_calculations.py` | KENT steps 5-8 for all companies. Returns (df_detailed, df_network, df_category) |
| `calculate_controllable_with_eff_req(...)` | `calculations/controllable_cost_calculations.py` | Controllable costs with efficiency requirement |
| `get_controllable_from_sdf(sdf_ir, sdf_controllable)` | `calculations/controllable_cost_calculations.py` | Extract controllable baseline from SDF |
| `calculate_wacc(...)` | `calculations/wacc_calculations.py` | CAPM -> WACC |
| `calculate_efficiency_requirement(...)` | `calculations/efficiency_requirement.py` | Efficiency requirement calculation |
| `assemble_revenue_frame(...)` | `calculations/revenue_frame_assembly.py` | Revenue frame assembly |

Data loaders are in `data_loaders/`:
- `baseline_data.py` -- loads Data_modeller.xlsx, EIs_DEA.xlsx, SDF file
- `rab_data.py` -- loads capbase_a.parquet, capcost_a.parquet
- `incentive_data.py` -- loads adjustment variables

Time codes: `calculations/time_codes.py` -- 229=2024H1, 230=2024H2, ..., 236=2027H2

## Test Companies

Use the 3 companies already present in `data/capbase_a_mini.parquet` (~52k rows instead of ~510k):

| REId | id_network | Company | Characteristics |
|------|-----------|---------|-----------------|
| REL00001 | 1 | Ale El ek. för. | Small/medium, NO NeoÄndringar adjustments |
| REL00886 | 886 | Kraftringen Nät AB | Large, WITH NeoÄndringar (73,097 tkr) |
| REL03035 | 3035 | (large company) | Very large (~42k components), scale edge case |

**Use `capbase_a_mini.parquet` instead of the full `capbase_a.parquet` for all KENT calculations in this task.** This is ~10x faster while containing exactly the 3 test companies we need.

## Task: Verification Script

Create a Python script (or set of test functions) that systematically verifies variable definitions. The approach is: derive each variable from the primary source (capbase_a) and compare against secondary sources (Data_modeller, SDF) to confirm what each variable actually represents.

### Group 1: Capital Cost Variables (capbase_a -> KENT -> compare)

```python
import pandas as pd
from calculations.kent_calculations import run_kent_calculations_batch
from data_loaders.baseline_data import load_baseline_data

# Use mini file for speed (~52k rows, 3 companies instead of ~510k)
capbase = pd.read_parquet("data/capbase_a_mini.parquet")
baseline = load_baseline_data()
df_detailed, df_network, df_category = run_kent_calculations_batch(capbase, wacc=0.0453)
dm = baseline.df_all_companies  # Data_modeller DataFrame (still all 148 companies)
```

For each test company, verify:

**1a. KENT vs Data_modeller (first-year values)**
- Is `df_network['Kapitalkostnad_2024']` == `dm['CAPEX']`?
- Is `df_network['Avskrivning_2024']` == `dm['Avskrivning']`?
- Is `df_network['Avkastning_2024']` == `dm['Avkastning']`?
- Report: absolute diff, relative diff (%)

**1b. KENT vs Data_modeller (per-year returns)**
- Is `df_network['Avkastning_2024']` == `dm['Avkastning_2024']`?
- Is `df_network['Avkastning_2025']` == `dm['Avkastning_2025']`?
- Same for 2026, 2027
- Is `df_network['Avkastning_Period']` == `dm['Avkastning_Period']`?

**1c. KENT vs SDF IR (period sums)**
- Load SDF: `sdf_data = _load_sdf_data()` (from baseline_data.py)
- Is `df_network['Kapitalkostnad_Period']` == SDF IR `Kapitalkostnad`?
- Is `df_network['Avskrivning_Period']` == SDF IR `-varav Kapital-förslitning`?
- Is `df_network['Avkastning_Period']` == SDF IR `varav Kapital-bindning`?

**1d. KENT vs capcost_a (category-level)**
- For each (id_network, cat_encode, time): does `df_category` match `capcost_a`?
- This verifies that capcost_a is simply a pre-computed version of KENT output

### Group 2: Controllable Cost Variables (OPEXp)

**2a. SDF Påverkbara vs Data_modeller**
- Load SDF controllable data via `get_controllable_from_sdf()`
- Compare `Paverkbara_Medelvarde` against `dm['OPEXp']`
- For companies WITHOUT NeoÄndringar: are they equal?
- For companies WITH NeoÄndringar: what is the relationship?

**2b. Define OPEXp precisely**
- Is it the mean of 2018-2021 historical controllable costs?
- Check SDF "Påverkbara Halvnya" sheet for "Antal år medräknat i historiken" column
- Do some companies use 3 years instead of 4? Does this explain discrepancies?

### Group 3: Volume Variables (CU, MW, NS, MWhl, MWhh)

**3a. Source identification**
- These CANNOT be derived from capbase_a
- Determine: are they 4-year means? Single-year values? Period totals?
- Check if values have .25 remainders (suggesting 4-year means of integers)
- Check if any SDF sheet contains per-year volume breakdowns

### Group 4: DEA and Efficiency Variables

**4a. DEA inputs**
- Verify what `dm['CAPEX']`, `dm['OPEXp']`, `dm['CU']`, etc. represent as DEA inputs
- Compare against `EIs_DEA.xlsx` baseline results

**4b. Efficiency requirement**
- `dm['Effkrav_proc']` from EIs_DEA.xlsx -- what does it represent?
- Cross-reference with `calculate_efficiency_requirement()` output

### Group 5: Revenue Frame Assembly

**5a. SDF IR verification**
- Verify: `Intäktsram = Påverkbara + Opåverkbara + Kapitalkostnad + adjustments`
- Trace each component to its source

## Output: Specification Document

Based on verification results, produce a specification with this format for EVERY variable:

```markdown
## capital_cost_first_year

- **Definition**: Total capital cost (depreciation + return) for first year of regulation period (2024)
- **Unit**: tkr, 2022 price level
- **Time scope**: Annual (first year, sum of H1+H2)
- **Formula**: sum(dep_ord_t + dep_tail_t + return_ord_t + return_tail_t) for t in [229, 230]
- **Primary source**: capbase_a -> KENT step 5-8 -> aggregate to network
- **Also found in**: Data_modeller.xlsx col 'CAPEX', aliased as 'Kapitalkostnad_2024'
- **Verification**: KENT vs DM: max diff X tkr (Y%) across 148 companies
- **Can be derived from capbase_a**: Yes
- **Current names in codebase**: CAPEX, Kapitalkostnad_2024
- **Canonical name**: `capital_cost_first_year` (or `capital_cost_2024`)
```

## Output: Data Source Classification

Classify each data file:

| Classification | Meaning | Example |
|---|---|---|
| **PRIMARY** | Cannot be derived, must be loaded | capbase_a (component-level assets) |
| **DERIVED** | Can be regenerated from primary sources | Data_modeller capital cost columns |
| **INDEPENDENT** | Contains unique data not in other sources | Volume data, incentive variables |
| **MIXED** | Some columns primary, some derived | Data_modeller (volumes=independent, CAPEX=derived) |

## Naming Convention for Canonical Names

Use this pattern for canonical English names:

```
{metric}_{scope}_{qualifier}

Metrics:     capital_cost, depreciation, return_on_assets, controllable_cost,
             non_controllable_cost, efficiency, revenue_frame
Scopes:      first_year, 2024, 2025, 2026, 2027, period (=sum 2024-2027),
             average (=mean over period), h1_2024, h2_2024, ...
Qualifiers:  ord (ordinarie), tail (svanskomponent), total, per_category
```

Examples:
- `capital_cost_2024` -- total capital cost for 2024 (= sum of H1+H2)
- `depreciation_period` -- total depreciation over 2024-2027
- `return_on_assets_ord_h1_2024` -- return on ordinarie components, 2024 H1
- `controllable_cost_average` -- mean of historical controllable costs (2018-2021)

## Important Notes

- All monetary values in tkr (thousands SEK) at 2022 price level unless noted
- WACC baseline: 4.53% (real, before tax)
- Small differences (<0.1%) between KENT and DM/SDF are expected (Ei runs their own KENT)
- If differences are larger, investigate why (different capbase_a version? rounding? different WACC?)
- Use existing functions from `calculations/` -- do not reimplement
- Run on the 3 test companies in `capbase_a_mini.parquet` first, then validate pattern holds for all 148 using full `capbase_a.parquet` if needed

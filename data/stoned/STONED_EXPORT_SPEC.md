# StoNED Export Specification

Specification for pre-computed StoNED efficiency results consumed by Regumetrica.
Use this as reference when producing models in an external repo.


## Overview

Regumetrica loads StoNED results from `data/stoned/`. Each model consists of:

1. **A parquet file** — `{model_id}.parquet` with per-company efficiency scores
2. **A registry entry** — in `models.json` with model metadata and diagnostics

The results slot into the pipeline at Stage 3 (efficiency estimation) and must
match the same column structure as DEA results so downstream stages work unchanged.


## Parquet file (`{model_id}.parquet`)

### Columns

| Column               | Type      | Description                                              |
|----------------------|-----------|----------------------------------------------------------|
| `REId`               | `str`     | Company ID, format `"REL00XXX"`                          |
| `dea_efficiency`     | `float64` | Efficiency score (0–1 range for valid models)            |
| `dea_super_efficiency` | `float64` | Always `NaN` (StoNED has no super-efficiency concept)  |
| `potential`          | `float64` | Inefficiency = `1 - dea_efficiency`                      |
| `is_outlier`         | `bool`    | `True` for companies excluded ex ante from estimation    |

### Row rules

- **Exactly 148 rows** — one per company in Data_modeller.xlsx
- **Estimated companies:** `is_outlier = False`, valid `dea_efficiency`, `potential = 1 - dea_efficiency`
- **Outliers** (excluded from estimation): `is_outlier = True`, `dea_efficiency = NaN`, `potential = 1.0`
- Sort order does not matter — the pipeline matches on `REId`

### Outlier companies (current ex ante exclusions)

The first three are Ei's official DEA outliers (identified via IQR method).
REL00193 is not an Ei outlier but was manually excluded in the StoNED script
(efficiency 0.58 in Ei's DEA — may distort CNLS estimation).

| REId       | Company                            | Ei DEA outlier? |
|------------|------------------------------------|:---------------:|
| REL00024   | Carlfors Bruk E Björklund & Co KB  | Yes             |
| REL00257   | Övik Energi Nät AB                 | Yes             |
| REL00965   | Sörbylunds Elnät HB                | Yes             |
| REL00193   | Tåre Energi ek. för.               | No              |

### Example rows

```
REId        dea_efficiency  dea_super_efficiency  potential   is_outlier
REL00001    0.9634          NaN                   0.0366      False
REL00006    0.9598          NaN                   0.0402      False
...
REL00024    NaN             NaN                   1.0000      True
REL00257    NaN             NaN                   1.0000      True
```

### Creating the parquet in Python

```python
import pandas as pd
import numpy as np

# After estimation — efficiency and outlier_flags are arrays of length 148
df = pd.DataFrame({
    "REId": reid_list,                        # list[str], 148 entries
    "dea_efficiency": efficiency_values,       # float, NaN for outliers
    "dea_super_efficiency": np.nan,            # always NaN
    "potential": potential_values,             # 1 - efficiency, 1.0 for outliers
    "is_outlier": outlier_flags,              # bool
})

df.to_parquet(f"{model_id}.parquet", index=False)
```


## Metadata registry (`models.json`)

A single JSON object where each key is a `model_id` mapping to its metadata.

### Schema per model

```json
{
  "M1": {
    "model_id": "M1",
    "label": "StoNED TOTEX (VRS, QLE)",
    "description": "Cost: totex, Outputs: CU, MW, NS, MWhl, MWhh, Decomp: QLE",
    "cost_variable": "totex_first_year",
    "output_variables": ["CU", "MW", "NS", "MWhl", "MWhh"],
    "rts": "vrs",
    "cet": "mult",
    "fun": "cost",
    "decomposition": "QLE",
    "sigma_u": 0.047898,
    "sigma_v": 0.118879,
    "mu": 0.038217,
    "lambda_ratio": 0.4029,
    "n_firms": 144,
    "n_excluded_ex_ante": 4,
    "eff_min": 0.9443,
    "eff_median": 0.9633,
    "eff_max": 0.9749,
    "computed_at": "2026-03-03T09:30:55"
  }
}
```

### Field reference

| Field                  | Type         | Required | Description                                                      |
|------------------------|--------------|:--------:|------------------------------------------------------------------|
| `model_id`             | `str`        | Yes      | Unique ID, must match parquet filename (`{model_id}.parquet`)    |
| `label`                | `str`        | Yes      | Shown in UI radio button. Format: `"StoNED {cost} ({RTS}, {decomp})"` |
| `description`          | `str`        | Yes      | Free-text description shown as info in UI                        |
| `cost_variable`        | `str`        | Yes      | Cost variable column name (see Cost variables below)             |
| `output_variables`     | `list[str]`  | Yes      | Output variable column names                                     |
| `rts`                  | `str`        | Yes      | `"vrs"` or `"crs"`                                               |
| `cet`                  | `str`        | Yes      | `"mult"` (multiplicative) or `"addi"` (additive)                |
| `fun`                  | `str`        | Yes      | `"cost"` or `"prod"`                                             |
| `decomposition`        | `str`        | Yes      | `"QLE"`, `"MoM"`, or `"KDE"`                                    |
| `sigma_u`              | `float`      | Yes      | Inefficiency std dev (should be > 0 for meaningful model)        |
| `sigma_v`              | `float`      | Yes      | Noise std dev                                                    |
| `mu`                   | `float`      | Yes      | Mean inefficiency                                                |
| `lambda_ratio`         | `float`      | Yes      | `sigma_u / sigma_v` (signal-to-noise ratio)                     |
| `n_firms`              | `int`        | Yes      | Firms in estimation sample (excluding outliers)                  |
| `n_excluded_ex_ante`   | `int`        | Yes      | Number of excluded outliers                                      |
| `eff_min`              | `float`      | Yes      | Minimum efficiency in estimation sample                          |
| `eff_median`           | `float`      | Yes      | Median efficiency                                                |
| `eff_max`              | `float`      | Yes      | Maximum efficiency                                               |
| `computed_at`          | `str`        | Yes      | ISO-8601 timestamp (`YYYY-MM-DDTHH:MM:SS`)                      |

### Cost variables

The `cost_variable` field should use the English column name from `config/column_names.py`:

| Column name               | Description                                        |
|---------------------------|----------------------------------------------------|
| `totex_first_year`        | TOTEX = controllable avg + capital cost 2024       |
| `controllable_cost_average` | Controllable operating costs (SDF-derived)       |
| `capital_cost_2024`       | Capital cost first year                            |

### Output variables

Standard outputs available in Data_modeller.xlsx:

| Column  | Description                         |
|---------|-------------------------------------|
| `CU`    | Number of customers                 |
| `MW`    | Subscribed capacity                 |
| `NS`    | Network length                      |
| `MWhl`  | Energy delivered, low voltage       |
| `MWhh`  | Energy delivered, high/medium voltage |


## Naming convention

No hard constraint on `model_id`, but keep it short. Suggestions:

```
M1, M2, M3, ...               # Sequential (current convention)
totex_vrs_qle                  # Descriptive
opex_crs_mom_v2                # With versioning
```


## Validation checklist

Before copying files to `data/stoned/`:

- [ ] Parquet has exactly 5 columns with correct names and types
- [ ] Exactly 148 rows with valid `REId` values
- [ ] Outliers: `is_outlier=True`, `potential=1.0`, `dea_efficiency=NaN`
- [ ] Estimated firms: `is_outlier=False`, `0 < dea_efficiency <= 1`, `potential = 1 - dea_efficiency`
- [ ] `sigma_u > 0` (negative sigma_u means no inefficiency signal — model is unusable)
- [ ] `lambda_ratio > 0` (same implication as above)
- [ ] `models.json` has an entry for every parquet file with all required fields
- [ ] Parquet filename matches `model_id` in registry
- [ ] `computed_at` is a valid ISO-8601 timestamp


## How Regumetrica loads the data

```
User selects "StoNED" + model in UI
    → config_adapter sets DeaConfig(method=STONED, stoned_model_id="M1")
    → Stage 3 (pipeline/stages/dea.py) calls load_stoned_results("M1")
    → data_loaders/stoned_data.py reads data/stoned/M1.parquet
    → Returns DataFrame with same structure as DEA results
    → Stage 5 (post_dea) calculates efficiency requirement from potential column
    → Downstream is identical to DEA path
```

No runtime validation is performed on the parquet contents. If columns are
missing or types are wrong, the pipeline will raise an error at Stage 5 when
it tries to access `potential` and `is_outlier`.

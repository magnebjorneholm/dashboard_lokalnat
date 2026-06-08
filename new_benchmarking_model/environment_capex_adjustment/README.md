# Environment capex adjustment (förläggningsmiljö, jordkabel)

Levels every company's **jordkabel** capital base down to the **landsbygd-normal** cost
level, so that a company is not penalised in the new benchmarking model for a placement
environment it cannot control. This is a **benchmarking (DEA/TOTEX) input adjustment**, not
a change to the intäktsram. See Ei's *ny-modell-benchmarking-elnätsreglering* §"Korrigering
görs för dyrare förläggningsmiljö".

## What it does, exactly

### 1. Data model (verified, not assumed)
In `capbase_a.parquet`, for cables (`cat_encode == 3`), the identity

```
nuav_2022  ==  normvärde × count_comp        (holds for 100% of rows, 0.00% median error)
```

holds because:
- **`normvärde`** is the per-km unit price `[SEK/km]` from Ei's `Normvärdeslista-2024-2027.xlsx`
  for the component's **exact cable type** (`techspec × volt`) **and** its placement environment;
- **`count_comp`** is the physical cable length `[km]`;
- **`nuav_2022`** is the component's capital-base value `[SEK]` (NUAV 2022, before depreciation).

Cross-checked against the official list, e.g. `PEX 3x1x95 mm², 12 kV`:
`landsbygd normal = 441 285`, `landsbygd svår = 596 153`, `tätort = 1 179 781`,
`city = 1 610 809` SEK/km — capbase reproduces these exactly.

Because the environment premium is *already embedded in each component's unit price*, the
correction is a **re-pricing** problem: replace each cable's price with the landsbygd-normal
price for the **same cable type**.

### 2. Placement environments (from `subcat`)
`city`, `tatort`, `lb_normal` (**reference**), `lb_svar`, and `other`
(sjökabel / optokabel / övriga / unlabelled "jordkabel"). Reference and `other` are
**never adjusted**.

### 3. Calibration (`calibration.py`)
For each adjustable environment, measure how much more expensive the *same* cable type is
vs landsbygd normal, matched on `techspec × volt`, volume-weighted by the actual installed
km mix, and summarise two ways:

| env       | premium `[SEK/km]` | premium `[% of value]` | km matched | per-type spread |
|-----------|-------------------:|-----------------------:|-----------:|-----------------|
| city      |          1 002 107 |                  71.0 % |     88.1 % | SEK/km CV 4.3 %, ratio 3.55× CV 14.6 % |
| tatort    |            614 259 |                  61.9 % |     94.1 % | SEK/km CV 13.0 %, ratio 2.79× CV 21.3 % |
| lb_svar   |            146 016 |                  27.7 % |    100.0 % | SEK/km CV 29.1 %, ratio 1.39× CV  5.3 % |

(Numbers from the current `capbase_a.parquet`; regenerate with `run_example.py`.)

The form that is "cleaner" is **environment-dependent**: for **city/tätort** the premium is
close to a fixed `SEK/km` (urban ground works ≈ constant per km, CV 4–13 %), so the additive
form is the more faithful schablon; for **landsbygd svår** the *ratio* is more stable
(CV 5.3 %), i.e. the difficult-terrain surcharge scales with the cable value. Per-type
re-pricing avoids having to choose.

### 4. Adjustment (`adjustment.py`) — three methods + override
- **`per_type`** (default, most precise): re-price each component at the landsbygd-normal
  unit price for its own `techspec × volt`. Types without a landsbygd-normal reference
  (≈6–12 % of city/tätort km) fall back to the `sek_per_km` schablon.
- **`sek_per_km`**: `deduction = km × sek_per_km[env]`.
- **`percent`**: `deduction = value × percent[env]`. Matches Ei's wording. Pass
  `override_percent={"city": 0.6, ...}` to substitute Ei's official figures when published.

Deductions are clipped to `[0, value]`: the correction only levels expensive environments
**down**; it never adds value (a cable type that is cheaper than landsbygd normal is left
unchanged).

## Output
`run_environment_adjustment(method=...)` returns an `EnvironmentAdjustmentResult`:
- `per_company` — per `REId`: original / adjusted jordkabel value, `effective_pct`,
  `reduction_factor`;
- `per_company_env` — same split by environment;
- `components` — per-component detail;
- `calibration.coverage` — the premium + reliability diagnostics above.

### Integrating into benchmarking
The adjustment produces a per-company jordkabel **capital-base value**. Since KENT capital
cost is linear in the base value, multiply the jordkabel capital-cost component that enters
the DEA/TOTEX input by `reduction_factor` (= `adjusted_value / value`). The intäktsram itself
is unchanged.

## Scope & caveats
- **Jordkabel only.** Stations (nätstation etc.) are *not* split by environment in `subcat`,
  so no station correction is possible from this data (Ei flags station correction as future
  work).
- **Normvärde as proxy for anskaffningsvärde.** Ei's method targets anskaffningsvärde, which
  is 98.5 % missing in `capbase_a`. We use the normvärde-embedded environment ratios instead;
  this assumes the inter-environment price *ratio* is the same in anskaffningsvärde as in
  normvärde — reasonable but not verifiable from this data.
- **Ei's official schablon % is not yet published**, so the calibrated figures are a
  data-grounded reconstruction, not Ei's numbers. Use `override_percent` once they exist.

## Usage
```python
from new_benchmarking_model.environment_capex_adjustment import run_environment_adjustment

res = run_environment_adjustment(method="per_type")
res.per_company            # one row per company
res.calibration.coverage   # premium + reliability per environment
```
Demo / sanity check:
```
./venv/Scripts/python.exe new_benchmarking_model/environment_capex_adjustment/run_example.py
```

## Files
| File | Role |
|------|------|
| `config.py`      | constants: paths, environment codes, method names, column names |
| `data.py`        | load + normalise jordkabel components; `classify_env()` |
| `calibration.py` | derive per-environment premium (SEK/km + percent) + diagnostics |
| `adjustment.py`  | apply a method per company; aggregate; `reduction_factor` |
| `run_example.py` | end-to-end demo and sector/company summaries |
| `test_environment_capex_adjustment.py` | correctness tests (identity, conservation, cross-check vs official list) |

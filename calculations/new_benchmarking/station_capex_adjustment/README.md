# Station capex adjustment (förläggningsmiljö, nätstation)

Levels every company's **nätstation** capital base down to the **outside-tätort** cost
level, so that a company is not penalised in the new benchmarking model for a placement
environment it cannot control. This is a **benchmarking (DEA/TOTEX) input adjustment**, not
a change to the intäktsram. Parallel to [`environment_capex_adjustment`](../environment_capex_adjustment/README.md)
(jordkabel). See Ei's *ny-modell-benchmarking-elnätsreglering* §"Korrigering görs för dyrare
förläggningsmiljö": *"Även värdet på nätstationer skiljer sig mellan olika förläggningsmiljöer …
kommer en liknande korrigering att kunna göras som för jordkablar."*

## How the data model differs from jordkabel

This is the crux, and it makes the station case **simpler** than cables:

| | Jordkabel | Nätstation |
|---|---|---|
| Where the premium lives | **embedded** in each component's per-km price (same type, 4 prices) | a **separate itemised line**: `City- och tätortstillägg nätstation` |
| Environment levels | 4 (city / tätort / lb-normal / lb-svår), in `subcat` | **1 binary** (inside/outside SCB tätort boundary), in `techspec` |
| Reference | landsbygd normal (a price to *re-price to*) | outside tätort (= the station **without** the surcharge) |
| Correction | re-price each component per `techspec × volt` | **remove the surcharge rows** — exact, no lookup |

For stations the premium is therefore *directly observed*, not reconstructed. There is no
per-type reference price list to build and no schablon needed for precision.

## What it does, exactly

### 1. Data model (verified, not assumed)
In `capbase_a.parquet`, for stations (`cat_encode == 13`), the identity

```
nuav_2022  ==  normvärde × count_comp        (holds for 100% of priced rows, 0.00% median error)
```

holds because:
- **`normvärde`** is the per-station unit price `[SEK/st]` from Ei's `Normvärdeslista-2024-2027.xlsx`;
- **`count_comp`** is the number of stations `[st]`;
- **`nuav_2022`** is the row's capital-base value `[SEK]` (NUAV 2022, before depreciation).

The placement-environment premium is the surcharge code `City- och tätortstillägg nätstation`
(Ei list codes `NG15171` / `NG15271`), **126 861 SEK/st**, booked for stations inside the
tätort boundary of Statistiska Centralbyrån's tätort map. capbase reproduces this exactly.

### 2. Placement environments (from `techspec`)
- **`tatort`** — the `City- och tätortstillägg nätstation` rows (the **adjustable** premium);
- **`base`** (**reference**) — base stations, kopplingsstation, and the *functional*
  tillägg (linjefack, effektbrytare, inhyst, inomhusbetjänad, nedbyggd). **Never adjusted.**

`classify_env` reads `techspec`, not `subcat`: `subcat == "tillägg nätstation"` covers all
six surcharge types, so only `techspec` isolates the environment one.

### 3. Calibration (`calibration.py`)
The premium is observed, so calibration just summarises it:

| metric | value (current capbase) |
|--------|------------------------:|
| premium value (Σ surcharge) | 6.30 bn SEK |
| total station base | 57.29 bn SEK |
| premium share of base (`percent`) | 11.0 % |
| unit price (`sek_per_station`) | 126 861 SEK/st |
| companies with surcharge | 136 / 146 |

(Regenerate with `run_example.py`.)

### 4. Adjustment (`adjustment.py`) — two methods + override
- **`itemized`** (default, exact, per-company): remove the `City- och tätortstillägg` rows
  in full (`deduction = their value`); base rows untouched. `reduction_factor` varies by
  company (here 0.77–1.00).
- **`percent`** (schablon, Ei-style): `deduction = value × percent[tatort]`, a flat haircut
  across the whole station base. Matches Ei's "schablonavdrag i procent" wording and reproduces
  the `itemized` total sector-wide; per company it discards the company-specific tätort share.
  Pass `override_percent={"tatort": 0.10}` to substitute Ei's official figure when published.

Deductions are clipped to `[0, value]` in magnitude, sign-preserving, so a disposal
(negative value) is never flipped or over-credited.

## Output
`run_station_adjustment(method=...)` returns an `EnvironmentAdjustmentResult` (same shape as
the cable module):
- `per_company` — per `REId`: original / adjusted station value, `effective_pct`, `reduction_factor`;
- `per_company_env` — same split by environment (`tatort` / `base`);
- `components` — per-component detail;
- `calibration.coverage` — the premium + reliability diagnostics above.

### Integrating into benchmarking
Multiply the station capital-cost component that enters the DEA/TOTEX input by
`reduction_factor` (= `adjusted_value / value`). The intäktsram itself is unchanged.
(Integration is out of scope for this module — backend only.)

## Scope & caveats
- **Nätstation only** (`cat_encode == 13`). Jordkabel is handled by the sibling module;
  kabelskåp is *intentionally not corrected* — Ei deems the price differences negligible.
- **Binary environment.** Unlike cables there is no city-vs-tätort split and no landsbygd-svår
  level for stations: the list defines a single tätort surcharge, so the correction is
  inside/outside tätort only.
- **Normvärde as proxy for anskaffningsvärde.** Ei's method targets anskaffningsvärde, which
  is ~98 % missing in `capbase_a`. The surcharge value is the normvärde-based premium; this
  assumes the tätort premium is the same share of anskaffningsvärde as of normvärde —
  reasonable but not verifiable from this data.
- **Ei's official schablon % is not yet published**, so `percent` is a data-grounded
  reconstruction. Prefer `itemized` (exact); use `override_percent` once Ei's number exists.

## Usage
```python
from new_benchmarking_model.station_capex_adjustment import run_station_adjustment

res = run_station_adjustment(method="itemized")
res.per_company            # one row per company
res.calibration.coverage   # premium + reliability diagnostics
```
Demo / sanity check:
```
./venv/Scripts/python.exe new_benchmarking_model/station_capex_adjustment/run_example.py
```

## Files
| File | Role |
|------|------|
| `config.py`      | constants: paths, environment codes, method names, column names |
| `data.py`        | load + normalise station components; `classify_env()` |
| `calibration.py` | summarise the tätort premium (percent + SEK/st) + diagnostics |
| `adjustment.py`  | apply a method per company; aggregate; `reduction_factor` |
| `run_example.py` | end-to-end demo and sector/company summaries |
| `test_station_capex_adjustment.py` | correctness tests (identity, conservation, cross-check vs official list) |

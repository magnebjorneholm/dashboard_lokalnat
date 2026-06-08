# cable_length — ledningslängd per företag

Computes physical line length (**ledningslängd**, km) per company from
`capbase_a`, for use as a benchmarking variable in the new regulatory model.

In `capbase_a`, `count_comp` is the quantity field: **kilometres for line
components**, but a plain *count* for point components (mätare, nätstationer,
transformatorer, kabelskåp). This module therefore filters strictly to line
components before summing.

## Two parametrisable axes

1. **`ledningstyp`** — which line types to include:
   `jordkabel`, `luftledning`, `hsp_hangkabel`, `sjokabel`, `optokabel`,
   `ovriga` (Övriga ledningar / annan ledning).
2. **`voltage_level`** — optional split: `lsp` (0,4 kV), `hsp` (> 0,4 kV),
   `unknown` (volt not reported — a genuine mix, ≈12 % of line km, surfaced
   rather than guessed).

## Usage

```python
from new_benchmarking_model.cable_length import (
    load_cable_components, aggregate_cable_length_per_firm, C,
)

comp = load_cable_components()                 # one row per line component

# one total km per company (electrical lines, optical fibre excluded)
km = aggregate_cable_length_per_firm(comp, include_types=C.ELECTRICAL_TYPES)
#   columns: id_firm, km_total

# broken down by voltage level
km_v = aggregate_cable_length_per_firm(
    comp, include_types=C.ELECTRICAL_TYPES, split_by_voltage=True
)
#   columns: id_firm, voltage_level, km_total
```

`include_types=None` includes all line types; `C.ALL_TYPES` and
`C.ELECTRICAL_TYPES` (= all except `optokabel`) are provided as convenient
presets.

## Classification decisions

- **`tillägg` rows excluded** — `jordkabel tillägg` / `luftledning tillägg`
  are capital-base cost supplements (often no `normvärde`, sometimes negative
  value); their `count_comp` is a placeholder, not real length (~24 km total).
- **`optokabel` is optical fibre** — included as a selectable type but excluded
  from the `ELECTRICAL_TYPES` default.
- **`alus` and other point components excluded** — not measured in km.
- `subcat` / `volt` are referenced by exact column name (a substring lookup
  would wrongly hit `subcat_encode`).

## Test

```
./venv/Scripts/python.exe -m pytest new_benchmarking_model/cable_length/test_cable_length.py -v
```

Tests cross-check the module total against an independent recomputation off the
raw parquet, and verify that the voltage split exactly partitions each company's
total.

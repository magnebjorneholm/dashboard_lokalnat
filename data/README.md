# `data/` — datakatalog

All data åtkomms via det centrala registret i
[config/data_paths.py](../config/data_paths.py) — använd `dataset_path(name)` /
`require_dataset(name)`, aldrig hårdkodade sökvägar. Mappstrukturen speglar
varje datasets **ursprung**:

| Mapp | Ursprung | Får redigeras? |
|---|---|---|
| `raw/` | Externa källor (Ei, regulatoriska) — exakt som levererade. | Nej (oföränderlig källa) |
| `derived/` | Genererat av `scripts/` (KENT-output, grunddata, frysta snapshots). | Nej (regenereras) |
| `reference/` | Kurerade uppslagstabeller. | Ja (för hand / via skript) |
| `fixtures/` | Mini-dataset (3 bolag) för enhetstester. | Nej (genereras) |
| `examples/` | Exempel-/demofiler (t.ex. KENT-uppladdning). | — |

Datarot kan flyttas utanför trädet med miljövariabeln `REGUMETRICA_DATA_DIR`.

## Innehåll

### `raw/` — externa källor
| Fil | Registry-namn | Beskrivning |
|---|---|---|
| `ei/Data_modeller.xlsx` | `data_modeller` | 148 bolag: CAPEX/OPEX, volymer, identiteter. |
| `ei/EIs_DEA.xlsx` | `eis_dea` | Ei:s referens-DEA (effektivitet, supereffektivitet, outliers). |
| `ei/Löpande kostnader från SDF 2024-27.xlsx` | `sdf_running_costs` | SDF: IR + påverkbara/opåverkbara kostnader. |
| `adjustments/all_adjust_vars.csv` | `adjustment_vars` | Incitamentvariabler per bolag/år. |
| `shapefiles/all_network_operator_areas.*` | `network_areas_shapefile` | Nätområden (geodata). |

### `derived/` — genererat
| Fil | Registry-namn | Genereras av |
|---|---|---|
| `rab_and_capex/capbase_a.parquet` | `capbase_a` | KENT-pipeline (kapitalbas per komponent). |
| `rab_and_capex/capcost_a.parquet` | `capcost_a` | KENT (kapitalkostnad per kategori/tid). |
| `opex/controllable_a.parquet` | `controllable_a` | Grunddata (påverkbara kostnader). |
| `opex/controllable_meta.parquet` | `controllable_meta` | Grunddata (index, neo, eff-krav). |
| `opex/non_controllable_a.parquet` | `non_controllable_a` | Grunddata (opåverkbara kostnader). |
| `snapshots/data_modeller.parquet` | `snap_data_modeller` | `scripts/freeze_raw_sources.py` |
| `snapshots/eis_dea.parquet` | `snap_eis_dea` | `scripts/freeze_raw_sources.py` |

**Frysta snapshots:** runtime-loaderna läser dessa parquet-snapshots i stället
för de långsamma Excel-filerna. Varje snapshot är den *exakta transformerade
loader-outputen*, så beräkningarna är oförändrade — bara snabbare och
deterministiska. Kör om när en rå Excel-källa uppdateras:

```bash
uv run python scripts/freeze_raw_sources.py
```

SDF-arken fryses **inte** (de innehåller heterogena Excel-kolumner som inte
round-trippar säkert via parquet) — de läses fortfarande från `raw/`.

### `reference/` — kurerade uppslag
| Fil | Registry-namn |
|---|---|
| `company_names.csv` | `company_names` |
| `reconciliation_id_network_firm_dmu.csv` | `reconciliation` |
| `avg_norm_value_by_category.parquet` | `avg_norm_value` |

### `fixtures/` — testdata (3 bolag)
`capbase_a_mini`, `controllable_a_mini`, `controllable_meta_mini`,
`non_controllable_a_mini` — aktiveras med `REGUMETRICA_TEST_MODE=1`.

## Schemakontrakt

Varje dataset har ett **icke-muterande** kolumnkontrakt i
[data_loaders/schemas.py](../data_loaders/schemas.py). Loadern kontrollerar att
nödvändiga kolumner finns och felar tydligt annars — den ändrar aldrig data.

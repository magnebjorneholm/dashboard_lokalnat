# Teknisk implementationsplan: Case System Redesign

## Context

Nuvarande case-system har 3 sidor (Define → Configure → Results) där sparande
kräver beräkning och save-dialogen lever i sidopanelen. Designdokumentet
(`docs/case_system_redesign.md`) specificerar en ny 4-sidig arkitektur med
Case Manager som landing page, persistent save bar, result snapshots för
jämförelse, och sparande frikopplat från beräkning.

---

## Fas 1: Datalager — result snapshot + config hash ✅ DONE

- `compute_config_hash()` tillagd i `frontend/utils/state_manager.py`
- `frontend/utils/result_snapshot.py` skapad med `extract_result_snapshot()`
- `SavedCase.result_snapshot` fält tillagt i `frontend/utils/case_storage.py`
- 14 tester i `tests/test_result_snapshot.py` — alla gröna

## Fas 2: Frikoppla sparande från beräkning ✅ DONE

- `_do_save_case()` i `streamlit_app.py` sparar alltid working state + snapshot vid match
- Save-knapp i sidebar kräver inte längre `calculation_done`
- `has_unsaved_changes()` jämför nu working state vs saved reference
- Status-text uppdaterad ("results may be outdated" istället för "save will use computed config")

---

## Fas 3: Sidstruktur ✅ DONE

### 3a. Ny Case Manager-sida

**Ny fil:** `pages/0_case_manager.py`

Innehåll extraherat från `pages/0_case_definition.py`:
- Case-identitet (namn, notes input)
- Ladda sparade case (med snapshot-info i listan)
- Ta bort case
- "New case"-knapp
- Case comparison (fas 5)

Case-listan visar per rad: namn, revenue_frame från snapshot (eller
"(ej beräknad)"), updated_at, [Load]-knapp.

### 3b. Byt namn och refaktorisera

| Gammal | Ny | Ändring |
|--------|----|---------|
| `pages/0_case_definition.py` | `pages/1_case_setup.py` | Ta bort case-identitet, load/delete. Behåll modulval. |
| `pages/1_case_config.py` | `pages/2_specification.py` | Bara namnbyte. |
| `pages/2_results.py` | `pages/3_revenue_frame.py` | Bara namnbyte. |

### 3c. Uppdatera navigation i `streamlit_app.py`

```python
case_manager = st.Page("pages/0_case_manager.py", title="Case Manager")
case_setup = st.Page("pages/1_case_setup.py", title="Case Setup")
specification = st.Page("pages/2_specification.py", title="Specification")
revenue_frame = st.Page("pages/3_revenue_frame.py", title="Revenue Frame")
pg = st.navigation([case_manager, case_setup, specification, revenue_frame])
```

Uppdatera `st.switch_page()` efter beräkning → `pages/3_revenue_frame.py`.

---

## Fas 4: Persistent save bar ✅ DONE

- `frontend/utils/case_actions.py` skapad med `do_save_case()` och `run_calculation()`
- `frontend/common/save_bar.py` skapad med `render_save_bar()` (tre lägen: saved/unsaved/new)
- Save bar integrerad i `pages/1_case_setup.py`, `pages/2_specification.py`, `pages/3_revenue_frame.py`
- Sidebar rensad: save-knapp, save-dialog och "Saved cases: N/10" borttagna
- Sidebar behåller: case info, compute-knapp, revert/new case, stale results-varning

---

## Fas 5: Case-jämförelse ✅ DONE

- `frontend/common/case_comparison.py` skapad med `render_comparison_table()`
- HTML-tabell med baseline + delta-färgning (grön/röd), 11 KPI:er
- Case Manager omskriven: selectbox → checkbox-lista med Load/Delete per rad
- "Compare selected (N)"-knapp → inline jämförelsetabell
- Checkboxar disabled för cases utan snapshot
- `from_dict()` backward compat fix: `data.setdefault("result_snapshot", None)`

---

## Fas 6: Slutförande ✅ DONE

- `ARCHITECTURE.md` uppdaterad: ny sidstruktur, nya filer, save-modell, import map
- Backward compat säkrad via `from_dict` och `from_firestore` (båda hanterar saknade fält)

---

## Filöversikt

### Nya filer (5)

| Fil | Syfte |
|-----|-------|
| `frontend/utils/result_snapshot.py` | `extract_result_snapshot()` ✅ |
| `frontend/utils/case_actions.py` | Extraherade `do_save_case()`, `run_calculation()` ✅ |
| `frontend/common/save_bar.py` | Save bar-komponent ✅ |
| `frontend/common/case_comparison.py` | Jämförelsetabell |
| `pages/0_case_manager.py` | Case Manager landing page |

### Modifierade filer (4)

| Fil | Ändringar |
|-----|-----------|
| `streamlit_app.py` | Navigation (4 sidor), sidebar cleanup, extrahera case actions ✅ |
| `frontend/utils/case_storage.py` | `result_snapshot`-fält ✅ |
| `frontend/utils/state_manager.py` | `has_unsaved_changes()` semantik ✅, `compute_config_hash()` ✅ |
| `pages/1_case_setup.py` (f.d. 0_case_definition) | Ta bort case-identitet/load/delete, behåll modulval, lägg till save bar ✅ |

### Omdöpta filer (2)

| Gammal | Ny |
|--------|----|
| `pages/1_case_config.py` | `pages/2_specification.py` |
| `pages/2_results.py` | `pages/3_revenue_frame.py` |

### Oförändrade filer

- `config/case_definition.py` (CaseDefinition dataclasses)
- `config/config_adapter.py` (UI → pipeline bridge)
- `pipeline/` (all pipeline/calculation logic)
- `frontend/modules/` (alla modulrenderers)
- `frontend/results/` (alla resultatrenderers)

---

## Verifiering

1. **Enhetstester:** `./venv/Scripts/python.exe -m pytest tests/test_result_snapshot.py -v`
2. **Manuell genomgång:**
   - Starta appen, verifiera 4-sidig navigation
   - Skapa nytt case → konfigurera → spara utan beräkning → ladda om → verifiera config bevarad
   - Beräkna → spara → verifiera snapshot finns i Firestore
   - Ladda case → ändra config → save bar visar "Unsaved"
   - Fork case → verifiera nytt UUID, original orört
   - Jämför 2 cases på Case Manager → verifiera KPI-tabell med baseline
3. **Backward compat:** Ladda befintligt sparat case (saknar snapshot) → ska fungera, snapshot=None

---

## Commit-strategi

| Commit | Innehåll |
|--------|----------|
| 1 | Fas 1-2: Datalager + frikopplat sparande ✅ (ej committat ännu) |
| 2 | Fas 3: Sidstruktur (file renames + ny Case Manager) |
| 3 | Fas 4: Save bar + sidebar cleanup |
| 4 | Fas 5: Case-jämförelse |
| 5 | Fas 6: ARCHITECTURE.md + slutpolering |

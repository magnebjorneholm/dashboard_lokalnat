# Case System Redesign — Conceptual Design

## 1. Background

The current system uses 3 pages (Define → Configure → Results) with case saving
tightly coupled to computed results. Saving requires a completed pipeline run,
cases are stored as UI widget state, and the save dialog lives in the sidebar.

This document proposes a redesigned case system with clearer separation of concerns,
a dedicated case management page, and a more flexible persistence model.


## 2. Core Design Decision: What Is a Case?

**A case is a configuration — results are a derived property.**

A case represents a set of regulatory assumptions (parameter and variable adjustments).
Results are deterministic given a configuration and can always be recomputed.
This means:

- Cases can be saved without running a computation first
- A "stale results" indicator shows when config has changed since last compute
- When saving a case that has computed results, a lightweight **result snapshot**
  (aggregated KPIs) is persisted alongside the config — enabling instant
  cross-case comparison without re-running the pipeline (see Section 7)


## 3. Page Structure

```
Page 1              Page 2             Page 3               Page 4
Case Manager   →   Case Setup    →   Specification    →   Revenue Frame
(hub)              (select modules)   (configure values)   (results)
```

### Page 1: Case Manager

The landing page and entry point after login. Purpose:

- **Create** a new case (blank config with default name)
- **Load** a previously saved case
- **Delete** saved cases
- **Compare** saved cases side-by-side (see Section 7)
- **Name and describe** a case (name, notes)

This is where the user decides *what* to work on before diving into configuration.

### Page 2: Case Setup

Select which modules and sections to configure. Functionally equivalent to
the current `0_case_definition.py` module selection, minus the case identity
fields and load/save controls (those now live on Page 1).

### Page 3: Detailed Specification

Configure parameter and variable values per module. Functionally equivalent
to the current `1_case_config.py`. No changes to module renderers needed.

> **Open question:** Pages 2 and 3 could be consolidated into a single page
> using tabs per module with inline checkboxes for section activation.
> This is a UX decision that can be made independently — it does not affect
> the case management architecture.

### Page 4: Revenue Frame (Results)

Display computed results with case-vs-baseline comparison. Functionally
equivalent to the current `2_results.py`. The "Compute" action stays here
(or in sidebar — TBD). Save is also accessible here via the persistent save bar.


## 4. Save Model

### What gets saved

Always the **working state** (latest configuration), regardless of whether
results have been computed.

```
SavedCase:
    id:                str (UUID)
    name:              str
    notes:             str
    user_reid:         str
    created_at:        timestamp
    updated_at:        timestamp
    ui_config:         dict               # Working state — always the latest
    selected_modules:  list[str]          # Active modules/sections
    has_kent_file:     bool               # Metadata flag
    kent_file_name:    str | null
    result_snapshot:   dict | null        # Lightweight KPIs (see Section 7)
```

Full pipeline results (DataFrames) are NOT persisted. They are cached in-session
and marked stale when the config changes. The `result_snapshot` is a small
summary written at save time if results exist — see Section 7 for details.

### Three save operations

| Operation       | Intent                              | Behavior                                          |
|-----------------|-------------------------------------|---------------------------------------------------|
| **Create**      | Start a new scenario                | New UUID, blank config or duplicated from existing |
| **Update**      | Refine the current scenario         | Overwrite config on existing UUID                  |
| **Fork**        | Branch into an alternative scenario | New UUID with copied config, original untouched    |


## 5. Persistent Save Bar

Since saving is decoupled from computation, the save action should be accessible
from any page where the user edits configuration (Pages 2, 3, 4).

A persistent strip (not in the sidebar) displays case status and save actions:

```
Loaded case, no changes:
┌──────────────────────────────────────────────────┐
│  Case: "Scenario A"                       [Saved]│
└──────────────────────────────────────────────────┘

Loaded case, unsaved changes:
┌──────────────────────────────────────────────────┐
│  Case: "Scenario A"  ● Unsaved   [Save] [Save as new...] │
└──────────────────────────────────────────────────┘

New case, never saved:
┌──────────────────────────────────────────────────┐
│  New case (unsaved)              [Save as...]    │
└──────────────────────────────────────────────────┘
```

This replaces the current sidebar save dialog. The sidebar is freed up for
company selection and the compute action only.


## 6. Change Detection

The current three-level reference system (working / computed / saved) remains
relevant but with adjusted semantics:

| Reference             | Purpose                                                  |
|-----------------------|----------------------------------------------------------|
| **Working state**     | Live `ui_config` + `selected_modules` in session         |
| **Computed reference**| Config snapshot from last pipeline run (stale detection)  |
| **Saved reference**   | Config snapshot from last DB save/load (unsaved detection)|

- **"Unsaved changes"** = working state differs from saved reference
- **"Stale results"** = working state differs from computed reference

Both indicators can coexist. A case can have unsaved changes AND valid results
(if computed but not yet saved), or unsaved changes AND stale results (if
config was edited after compute but before save).


## 7. Result Snapshots and Case Comparison

### Result snapshot

When a case is saved and computed results exist in-session, a lightweight
**result snapshot** is persisted alongside the configuration. This is NOT the
full PipelineResult — it is a small dict of ~10-15 aggregated KPIs sufficient
for comparison.

```
result_snapshot:
    computed_at:              timestamp   # When the pipeline ran
    config_hash:              str         # Hash of ui_config + selected_modules
    revenue_frame:            float       # Total intäktsram (tkr)
    capital_cost_period:      float       # Capital costs, period total
    controllable_period:      float       # Controllable costs, period total
    non_controllable_period:  float       # Non-controllable costs, period total
    flexibility_period:       float       # Flexibility costs, period total
    depreciation_period:      float       # Depreciation, period total
    return_period:            float       # Return on assets, period total
    dea_efficiency:           float       # DEA efficiency score
    efficiency_req_annual:    float       # Annual efficiency requirement
    incentive_total:          float       # Total incentive adjustment
    ...                                   # Extend as needed
```

**Staleness:** The `config_hash` is computed from the saved config at save time.
If the user later loads the case and modifies config without recomputing,
the snapshot is still present but can be marked "outdated" by comparing the
hash against the current working config.

**Lifecycle:**
- **Save with results:** Snapshot is written from the in-session PipelineResult
- **Save without results:** `result_snapshot` is `null`
- **Update with new results:** Snapshot is overwritten
- **Update config only (no recompute):** Snapshot is cleared (set to `null`)
  because it no longer matches the saved config

### Case comparison on the Case Manager page

Cases with a valid `result_snapshot` can be selected for side-by-side comparison
directly on the Case Manager page — no computation required.

```
┌─ Saved Cases ──────────────────────────────────────────────────────────┐
│                                                                         │
│  ☑ Scenario A         Revenue frame: 45 230 tkr    2h ago       [Load] │
│  ☑ Higher WACC        Revenue frame: 47 102 tkr    1d ago       [Load] │
│  ☐ OPEX sensitivity   (not computed)               3d ago       [Load] │
│                                                                         │
│  [Compare selected (2)]                                                 │
└─────────────────────────────────────────────────────────────────────────┘
```

**Rules:**
- All cases appear in the same list — no split between "computed" and "not computed"
- Cases without a snapshot show "(not computed)" and their checkbox is disabled
- Cases with an outdated snapshot (config changed since compute) show a warning icon
- "Compare selected" opens an inline comparison view (table or chart)

**Comparison view** shows the selected cases' KPIs side-by-side, with baseline
as implicit reference column:

```
┌─ Comparison ──────────────────────────────────────────────────┐
│                     Baseline    Scenario A    Higher WACC     │
│  Revenue frame      44 500      45 230        47 102    tkr  │
│  Capital costs      28 100      28 100        30 200    tkr  │
│  Controllable       12 400      13 130        12 400    tkr  │
│  DEA efficiency     0.92        0.92          0.92           │
│  Eff. req (annual)  2.1%        2.1%          2.1%           │
│  Incentive total    +1 200      +1 200        +1 200    tkr  │
│  ...                                                          │
└───────────────────────────────────────────────────────────────┘
```

Deltas from baseline can be shown as color-coded values (green/red) consistent
with the existing visual identity.


## 8. User Flows

### Flow A: New case from scratch

```
1. Case Manager  → Click "New case"
2. Case Setup    → Select M1, M3.wacc, M5
3. Specification → Adjust WACC to 5.0%, truncation max to 25%
4. Save bar      → Click "Save as..." → Enter name "Higher WACC" → Saved
5. Revenue Frame → Click "Compute" → View results
6. Save bar      → Shows "Saved" (config unchanged since save)
```

### Flow B: Load and modify existing case

```
1. Case Manager  → Select "Higher WACC" → Click "Load"
2. Specification → Change WACC to 5.5%
3. Save bar      → Shows "● Unsaved" → Click "Save" (updates existing)
4. Revenue Frame → Shows "Stale results" → Click "Compute" → Fresh results
```

### Flow C: Fork a case for comparison

```
1. Case Manager  → Load "Higher WACC"
2. Specification → Change truncation max to 20%
3. Save bar      → Click "Save as new..." → Name "Higher WACC + lower trunc"
4. (Original "Higher WACC" is untouched)
```

### Flow D: Save without computing

```
1. Case Manager  → "New case"
2. Case Setup    → Select M1, M4
3. Specification → Adjust OPEX scaling to 1.10
4. Save bar      → "Save as..." → "OPEX sensitivity" → Saved
5. (User closes browser — config is persisted, no results needed)
```

### Flow E: Compare saved cases

```
1. Case Manager  → Three saved cases listed, two have result snapshots
2. Case Manager  → Check "Scenario A" and "Higher WACC"
3. Case Manager  → Click "Compare selected (2)"
4. Comparison    → Table shows KPIs side-by-side with baseline as reference
5. (No computation needed — snapshots provide all data)
```


## 9. Migration Path

The current `SavedCase` structure is almost identical to the proposed one.
Key changes:

1. **Remove compute requirement for save** — decouple `_do_save_case()` from
   `calculation_done` flag
2. **Always save working state** — remove preference for `computed_ui_config`
   over live `ui_config`
3. **Move case identity (name/notes)** from Define page to Case Manager
4. **Move load/delete** from Define page to Case Manager
5. **Add save bar component** — shared across Pages 2-4
6. **Remove sidebar save dialog** — replaced by save bar

7. **Add result snapshot extraction** — helper function that extracts ~15 KPIs
   from PipelineResult into a plain dict at save time
8. **Add config hashing** — deterministic hash of ui_config + selected_modules
   for snapshot staleness detection
9. **Add comparison view component** — table/chart rendering for Case Manager

No changes needed to:
- `CaseDefinition` dataclasses
- `config_adapter.py` (bridge to pipeline)
- Pipeline or calculation logic
- Module renderers (input or output)

Firestore schema change: one new optional field (`result_snapshot`) added to
the `saved_cases` collection. Backward compatible — existing cases load with
`result_snapshot: null`.


## 10. Open Questions

1. **Pages 2+3 consolidation:** Single page with tabs, or keep separate?
   Pure UX decision, no architectural impact.

2. **Compute trigger location:** Keep in sidebar? Move to Page 4? Both?

3. **Max cases limit:** Currently 10 per user. Sufficient?

4. **Save bar implementation:** Streamlit `st.container` with custom CSS,
   or native `st.columns` at top of each page? Needs prototyping.

5. **Comparison view scope:** Table only, or also charts (bar chart of
   revenue frame components)? MVP vs full version.

6. **Snapshot KPI selection:** Which ~10-15 KPIs to include? Should be
   sufficient for meaningful comparison without bloating the Firestore document.

7. **Snapshot on config-only update:** Current proposal clears snapshot when
   config is updated without recompute. Alternative: keep stale snapshot with
   warning. Which is less confusing for users?

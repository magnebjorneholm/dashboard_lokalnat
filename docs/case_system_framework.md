# Case System Framework

Conceptual framework for how case management works in Regumetrica.
Agreed upon 2026-03-19.

---

## Core principle

**A case is a configuration.** Results are deterministic from a specification,
so only the configuration is persisted. A lightweight KPI snapshot is included
when computed results exist and match the saved configuration.

---

## What is saved per case

| Field               | Description                                              |
|---------------------|----------------------------------------------------------|
| `case_id`           | UUID, assigned at creation                               |
| `name`              | User-provided name                                       |
| `notes`             | Optional description                                     |
| `user_reid`         | Company the case belongs to                              |
| `ui_config`         | Full module configuration dict                           |
| `selected_modules`  | Set of enabled modules/sections                          |
| `created_at`        | Timestamp                                                |
| `updated_at`        | Timestamp                                                |
| `result_snapshot`   | Aggregated KPIs if results matched config at save time   |

**Result snapshot rule:** Included only when `working config == computed config`
at the moment of saving. Otherwise the case is saved without a snapshot.

---

## Page flow and responsibilities

```
Page 1: Create & Select Case     — case management (create, load, duplicate, delete, compare)
Page 2: Case Setup               — module selection (no save)
Page 3: Specification            — parameter configuration (save available)
Page 4: Revenue Frame            — results display (save available)
```

### Page 1 — Create & Select Case

- **Create:** User names a case. It is saved to DB immediately with default
  (empty) configuration. A `case_id` is assigned. The user can delete empty
  cases if they were just testing.
- **Load:** Select a saved case. Config is applied to session state.
- **Duplicate:** Copy an existing case with a new name/ID.
- **Delete:** Remove a case from DB. Confirmation required.
- **Compare:** Side-by-side KPI comparison of cases that have result snapshots.

### Page 2 — Case Setup

- Select which modules/sections to configure.
- No save button. Module selection is always followed by specification (page 3)
  or computation (page 4), both of which have save.

### Page 3 — Specification

- Configure parameters and variables per module.
- **Save button available.** Always an update (case already exists in DB).

### Page 4 — Revenue Frame

- View computed results.
- **Save button available.** Always an update.
- Stale results warning shown when config has changed since last computation.

---

## Save behavior

Since the case is created on page 1, a `case_id` always exists on pages 2-4.
Save is always **update**, never "save as new".

- **One button:** "Save" (updates the existing case in DB).
- **Guard:** If working config is identical to the saved version, show a
  message like "No changes since last save" instead of saving.
- **No fork from save bar.** Duplicating a case is done from page 1 only.
- **What is saved:** Always the current working configuration, regardless of
  whether it has been computed. If the user modifies config after a computation,
  the latest working config is saved — not the previously computed one.

---

## Change detection

Two concepts, each with a specific purpose:

### 1. Working != Saved (unsaved changes)

Compares current `ui_config` + `selected_modules` against what is stored in DB.

- **Purpose:** Determines whether the save button does anything.
- **Visible to user:** Only as a guard on the save button (warning when no
  changes exist). No persistent "unsaved" badge.

### 2. Working != Computed (stale results)

Compares current `ui_config` + `selected_modules` against what was used in the
last pipeline run.

- **Purpose:** (a) Show stale results warning on page 4.
  (b) Decide whether to include a KPI snapshot when saving.
- **Visible to user:** Warning on page 4 when results may be outdated.

---

## State model (simplified)

| State level        | What it tracks                  | When it's set                |
|--------------------|---------------------------------|------------------------------|
| Working state      | `ui_config`, `selected_modules` | Continuously as user edits   |
| Saved reference    | Last DB-persisted config        | On create (page 1) and save  |
| Computed reference | Config used in last pipeline run| After computation completes  |

The session store (`@st.cache_resource`) continues to serve as a safety net
for page refreshes. It is not part of the conceptual case model — it is an
implementation detail for Streamlit's stateless reruns.

---

## What this eliminates

- "Save as new case" dialog on pages 3-4
- Fork logic from save bar
- Special-casing for "new unsaved case" (case always has an ID)
- Three-variant save button (was: save as / update / save as new)
- Save on page 2

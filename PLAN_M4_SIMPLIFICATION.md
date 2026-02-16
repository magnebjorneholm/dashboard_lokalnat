# Plan: Simplify M4 to Match User Manual

## Context
The current M4 implementation has 16 per-category cost overrides (9 controllable + 7 non-controllable) with parameter IDs that **conflict** with the User Manual. The glossary (`config/glossary.py`) correctly defines the manual's IDs, but the UI renders entirely different controls. This plan replaces the category-level override machinery with the 3 parameters + 3 variables specified in the User Manual (Tables 11-12).

## What the User Manual specifies

| ID | Description | Type | Pipeline effect |
|----|-------------|------|-----------------|
| **4.1.1** | Scaling factor adjustable OPEX | Parameter (all 148 cos) | DEA input changes → DEA re-runs → eff_req → RF |
| **4.1.2** | Scaling factor flexibility services | Parameter (all 148 cos) | RF only (not DEA, not efficiency) |
| **4.1.3** | Scaling factor non-adjustable OPEX | Parameter (all 148 cos) | RF only (not DEA, not efficiency) |
| **40.1.1** | Adjusted OPEX (OPEXp) | Variable (user's company) | Same as 4.1.1 but only user's co |
| **40.1.2** | Flexibility service cost | Variable (user's company) | RF only for user's company |
| **40.2.1** | Total non-adjustable costs | Variable (user's company) | RF only for user's company |

**Interaction rule:** Variable overrides trump parameter scaling for user's company.

## Pipeline flow per item

### 4.1.1 — Scale adjustable OPEX (all companies)
- **Pre-DEA** (stage 2): `df_all_companies[COL_CONTROLLABLE_AVG] *= scaling` + recalc `COL_TOTEX`
- **Post-DEA** (stage 5): After `aggregate_controllable()`, scale `controllable_cost_average` and `neo_adjustments_period` → feeds into `calculate_controllable_with_eff_req()`
- Sets `opex_modified=True` → DEA re-runs

### 4.1.2 — Scale flexibility services (all companies)
- **Post-DEA** (stage 5): Copy `sdf_ir`, scale `COL_FLEXIBILITY`, pass modified copy to `assemble_revenue_frame()`

### 4.1.3 — Scale non-adjustable OPEX (all companies)
- **Post-DEA** (stage 5): After `aggregate_non_controllable()`, scale `COL_NON_CONTROLLABLE` (+ per-year cols)

### 40.1.1 — Override user's OPEXp (after parameter scaling applied)
- **Pre-DEA**: Replace user's row `COL_CONTROLLABLE_AVG` with override value, recalc `COL_TOTEX`
- **Post-DEA**: Replace user's `controllable_cost_average` in aggregated result, set `neo_adjustments_period=0`
- Sets `opex_modified=True` → DEA re-runs

### 40.1.2 — Override user's flexibility
- **Post-DEA**: Replace user's `COL_FLEXIBILITY` in sdf copy before assembly

### 40.2.1 — Override user's non-adjustable costs
- **Post-DEA**: Replace user's `COL_NON_CONTROLLABLE` in aggregated result before assembly

## Files to modify (8 files)

### 1. `config/case_definition.py`
- **PreDeaConfig**: Remove `controllable_category_overrides`. Add:
  - `opex_scaling: Optional[float] = None` (4.1.1, None = 1.0)
  - `opex_override: Optional[float] = None` (40.1.1, annual OPEXp in tkr)
- **PostDeaConfig**: Remove `non_controllable_category_overrides`. Add:
  - `flex_scaling: Optional[float] = None` (4.1.2)
  - `non_adj_scaling: Optional[float] = None` (4.1.3)
  - `flex_override: Optional[float] = None` (40.1.2, period total in tkr)
  - `non_controllable_override: Optional[float] = None` (40.2.1, period total in tkr)

### 2. `frontend/modules/base/m4_operating_exp.py` — Major rewrite
- **Remove**: `CONTROLLABLE_CATEGORIES`, `NON_CONTROLLABLE_CATEGORIES`, `_render_controllable_scaling()`, `_render_non_controllable_scaling()`
- **Rewrite `render_scaling()`**: 3 `parameter_input()` calls for 4.1.1, 4.1.2, 4.1.3 (baseline=1.0, range 0.5-2.0, step 0.01). Pattern: copy from `m5_efficiency.py:render_efficiency_params()`.
  - Returns: `{"opex_scaling": 1.10, "flex_scaling": 1.05, ...}` (only non-default values)
- **Rewrite `render_opex_vars()`**: 3 `number_input()` calls for 40.1.1, 40.1.2, 40.2.1
  - Load user's baseline values via cached loader (pattern: `m3_incentive_variables.py:_load_baseline_cached`)
  - Need helper to extract: OPEXp from `df_all_companies`, flexibility from `sdf_ir`, non-controllable from aggregation
  - Returns: `{"opex_override": 250000, ...}` (only overridden values)

### 3. `frontend/utils/config_adapter.py`
- **`_build_pre_dea_config()`** (~line 162-164): Replace `controllable_category_overrides = m4.get(...)` with:
  ```python
  opex_scaling = m4.get("opex_scaling") or None
  opex_override = m4.get("opex_override") or None
  ```
- **`_build_post_dea_config()`** (~line 473-475): Replace `non_controllable_category_overrides = m4.get(...)` with:
  ```python
  flex_scaling = m4.get("flex_scaling") or None
  non_adj_scaling = m4.get("non_adj_scaling") or None
  flex_override = m4.get("flex_override") or None
  non_controllable_override = m4.get("non_controllable_override") or None
  ```
- **`get_changed_parameters()`**: Add M4 parameter change detection
- **`infer_selected_from_ui_config()`** (in module_registry.py line 464-466): Update M4 detection

### 4. `pipeline/stages/pre_dea.py`
- **Remove**: `_apply_controllable_overrides()` (lines 401-462, ~60 lines)
- **Replace** STEP 3 (lines 73-81) with new logic:
  ```python
  # STEP 3: Apply OPEX parameter scaling and variable override
  opex_modified = False
  if config.opex_scaling is not None:
      df[COL_CONTROLLABLE_AVG] *= config.opex_scaling
      df[COL_TOTEX] = df[COL_CONTROLLABLE_AVG] + df[COL_CAPITAL_COST_2024]
      opex_modified = True
  if config.opex_override is not None:
      user_reid = f"REL{user_id_network:05d}"
      mask = df["REId"] == user_reid
      df.loc[mask, COL_CONTROLLABLE_AVG] = config.opex_override
      df.loc[mask, COL_TOTEX] = config.opex_override + df.loc[mask, COL_CAPITAL_COST_2024].values[0]
      opex_modified = True
  ```
- Note: `stage_pre_dea()` currently receives `user_id_network` but not `user_reid`. Derive as shown above.

### 5. `pipeline/stages/post_dea.py`
- **Remove**: `controllable_category_overrides` parameter from `stage_post_dea()` signature (line 48)
- **Remove**: Controllable category override block (lines 91-107)
- **Remove**: Non-controllable category override block (lines 143-155)
- **Add** `opex_scaling` and `opex_override` as explicit arguments (same pattern as current `controllable_category_overrides`).

  After `aggregate_controllable()` (line 86-89):
  ```python
  # Apply opex parameter scaling (all companies)
  if opex_scaling is not None:
      sdf_controllable[COL_CONTROLLABLE_AVG] *= opex_scaling
      sdf_controllable["neo_adjustments_period"] *= opex_scaling
  # Apply opex variable override (user's company, trumps scaling)
  if opex_override is not None:
      mask = sdf_controllable["REId"] == user_reid
      sdf_controllable.loc[mask, COL_CONTROLLABLE_AVG] = opex_override
      sdf_controllable.loc[mask, "neo_adjustments_period"] = 0
  ```

  After `aggregate_non_controllable()` (line 139-141):
  ```python
  # Apply non-adjustable scaling (all companies)
  if config.non_adj_scaling is not None:
      for col in [COL_NON_CONTROLLABLE, COL_NON_CONTROLLABLE_2024, ...per-year...]:
          if col in non_controllable_result.columns:
              non_controllable_result[col] *= config.non_adj_scaling
  # Apply variable override (user's company)
  if config.non_controllable_override is not None:
      mask = non_controllable_result["REId"] == user_reid
      non_controllable_result.loc[mask, COL_NON_CONTROLLABLE] = config.non_controllable_override
  ```

  Before `assemble_revenue_frame()`:
  ```python
  # Apply flexibility scaling and override
  sdf_for_assembly = baseline.sdf_ir.copy()
  if config.flex_scaling is not None:
      sdf_for_assembly[COL_FLEXIBILITY] *= config.flex_scaling
  if config.flex_override is not None:
      mask = sdf_for_assembly["REId"] == user_reid
      sdf_for_assembly.loc[mask, COL_FLEXIBILITY] = config.flex_override
  ```
  Then pass `sdf_for_assembly` instead of `baseline.sdf_ir` to `assemble_revenue_frame()`.

### 6. `pipeline/core.py`
- Line 148: Replace `controllable_category_overrides=case_config.pre_dea.controllable_category_overrides` with:
  ```python
  opex_scaling=case_config.pre_dea.opex_scaling,
  opex_override=case_config.pre_dea.opex_override,
  ```

### 7. `calculations/cost_aggregation.py`
- `aggregate_controllable()`: Remove `category_overrides` parameter and its application logic (lines 29, 44, 53-57)
- `aggregate_non_controllable()`: Remove `category_overrides` parameter and its application logic (lines 92, 99, 108-112)
- Functions themselves stay — still used for baseline aggregation

### 8. `tests/test_override_cascades.py` — Rewrite
- Remove `CONTROLLABLE_OVERRIDE` and `NON_CONTROLLABLE_OVERRIDE` dicts
- Replace with: `OPEX_SCALING = 1.10`, `NON_ADJ_SCALING = 1.10`, `FLEX_SCALING = 1.10`
- Rewrite fixtures to use new config fields
- Test cases:
  1. `opex_scaling=1.10` → OPEXp +10% all cos → DEA re-runs → eff_req changes → RF changes
  2. `non_adj_scaling=1.10` → non-controllable +10% → RF changes, DEA unchanged
  3. `flex_scaling=1.10` → flexibility +10% → RF changes, DEA unchanged
  4. `opex_override=X` → user's OPEXp replaced → DEA may change
  5. `opex_scaling + opex_override` → variable trumps for user's co

### Also update (minor)
- `tests/test_cost_aggregation.py`: Remove tests for `category_overrides` parameter
- `frontend/common/module_registry.py`: Update `infer_selected_from_ui_config()` M4 detection (line 464-467)
- `ARCHITECTURE.md`: Update Override flow section and case_definition description

## Files NOT changed
- `config/glossary.py` — already correct (4.1.1-4.1.3, 40.1.1-40.2.1 defined per manual)
- `calculations/revenue_frame_assembly.py` — unchanged (scaling applied before calling it)
- `calculations/controllable_cost_calculations.py` — unchanged
- All other modules, data files, other tests

## Verification
1. Run full test suite: `./venv/Scripts/python.exe -m pytest tests/ -v`
2. All 197 tests should pass (minus removed override tests, plus new parameter tests)
3. Baseline pipeline (all scaling = 1.0, no overrides) must reproduce facit values exactly:
   - Company 886: controllable_cost_average ≈ 219,438.70 tkr
   - Company 886: revenue_frame_total ≈ 3,986,194.49 tkr
4. Parameter test: opex_scaling=1.10 should change DEA results for all companies
5. Variable test: opex_override should only change user's company, and trump parameter scaling

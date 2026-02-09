# Regumetrica: Swedish to English Glossary

This document maps all Swedish terms in the codebase to their English equivalents.
Use this as the authoritative reference when refactoring.

---

## 1. File Names (3 files)

| Current | New | Notes |
|---------|-----|-------|
| `effektiviseringskrav.py` | `efficiency_requirement.py` | Main efficiency calculation module |
| `intaktsram_assembly.py` | `revenue_frame_assembly.py` | Revenue frame assembly |
| `paverkbara_calculations.py` | `controllable_cost_calculations.py` | Controllable/adjustable costs |

---

## 2. Core Domain Terms

### 2.1 Revenue Frame (Intäktsram)

| Swedish | English | Context |
|---------|---------|---------|
| intäktsram | revenue_frame | The complete revenue allowance |
| intaktsram (in code) | revenue_frame | Variable naming |
| ir (abbreviation) | rf | Short form in variables |
| user_intaktsram | user_revenue_frame | User's complete revenue frame |
| all_intaktsram | all_revenue_frames | All 148 companies |
| Intaktsram_Total | RevenueFrame_Total | DataFrame column |
| assemble_intaktsram() | assemble_revenue_frame() | Function |
| extract_user_intaktsram() | extract_user_revenue_frame() | Function |
| create_intaktsram_breakdown() | create_revenue_frame_breakdown() | Function |
| intaktsram_assembly | revenue_frame_assembly | Module import |

### 2.2 Efficiency Requirement (Effektiviseringskrav)

| Swedish | English | Context |
|---------|---------|---------|
| effektiviseringskrav | efficiency_requirement | Annual efficiency target |
| effkrav | eff_req | Short form |
| effkrav_proc | eff_req_pct | Percentage form |
| user_effkrav_proc | user_eff_req_pct | User's requirement |
| all_effkrav | all_eff_reqs | All companies |
| effkrav_arligt | eff_req_annual | Annual requirement |
| calculate_effkrav_from_potential() | calculate_eff_req_from_potential() | Function |
| calculate_effkrav_for_dataframe() | calculate_eff_req_for_dataframe() | Function |
| get_max_effkrav() | get_max_eff_req() | Function |
| get_min_effkrav() | get_min_eff_req() | Function |
| _is_effkrav_modified() | _is_eff_req_modified() | Function |
| Effektivisering_Total | Efficiency_Total | DataFrame column |

### 2.3 Controllable Costs (Påverkbara kostnader)

| Swedish | English | Context |
|---------|---------|---------|
| påverkbara (kostnader) | controllable (costs) | Costs affected by efficiency |
| paverkbara | controllable | Variable naming |
| pav (abbreviation) | ctrl | Short form |
| opåverkbara | non_controllable | Non-controllable costs |
| opaverkbara | non_controllable | Variable naming |
| opav (abbreviation) | non_ctrl | Short form |
| sdf_paverkbara | sdf_controllable | SDF data source |
| sdf_opaverkbara | sdf_non_controllable | SDF data source |
| paverkbara_method | controllable_method | Config parameter |
| PaverkbaraMethod | ControllableMethod | Enum class |
| Paverkbara_Periodsumma | Controllable_PeriodSum | DataFrame column |
| Paverkbara_Medelvarde | Controllable_Average | DataFrame column |
| Paverkbara_I_Intaktsram | Controllable_In_RevenueFrame | DataFrame column |
| Opaverkbara_Kostnader | NonControllable_Costs | DataFrame column |
| ej_paverkbara | non_controllable | "Not controllable" |
| paverkbara_fore | controllable_before | Before adjustment |
| paverkbara_efter | controllable_after | After adjustment |
| paverkbara_result | controllable_result | Result variable |
| paverkbara_total | controllable_total | Total |
| paverkbara_per_ar | controllable_per_year | Per year |
| calculate_paverkbara_with_effkrav() | calculate_controllable_with_eff_req() | Function |
| get_paverkbara_from_sdf() | get_controllable_from_sdf() | Function |
| _calculate_paverkbara_single_company() | _calculate_controllable_single_company() | Function |
| _get_paverkbara_components() | _get_controllable_components() | Function |

### 2.4 Efficiency Parameters (Post-DEA Config)

| Swedish | English | Context |
|---------|---------|---------|
| trunkering_min | truncation_min | Lower efficiency bound |
| trunkering_max | truncation_max | Upper efficiency bound |
| trunkering | truncation | General term |
| outlier_krav | outlier_req | Outlier requirement |
| kunddelning | customer_sharing | Sharing with customers |
| realiseringstid | realization_time | Years to realize savings |
| tillsynsperiod | supervision_period | Regulatory period (4 years) |
| calculate_trunkering_min_from_outlier_krav() | calculate_truncation_min_from_outlier_req() | Function |

### 2.5 Capital Base (KENT terms)

| Swedish | English | Decision |
|---------|---------|----------|
| nuav | pv (present_value) | **KEEP AS-IS** - Ei regulatory term |
| ekdep | econ_dep | **KEEP AS-IS** - Ei regulatory term |
| maxdep | max_dep | **KEEP AS-IS** - Ei regulatory term |
| ordinarie | standard | Standard assets (vs tail) |
| svans | tail | Tail depreciation |
| normvärde | norm_value | Standard replacement value |
| normvarde | norm_value | Variable naming |
| livslängd | lifetime | Asset lifetime |
| livslangd | lifetime | Variable naming |
| avkastning | return | Return on capital |
| avskrivning | depreciation | Depreciation |
| kapitalbas | capital_base | Capital base |
| kapitalkostnad | capital_cost | Capital cost |

**Note:** `nuav`, `ekdep`, `maxdep` are kept as-is because they are official Ei terminology used in KENT files and regulatory documents.

### 2.6 Incentive Adjustments

| Swedish | English | Context |
|---------|---------|---------|
| Kvalitetsjustering_Total | QualityAdjustment_Total | DataFrame column |
| Belastningsjustering_Total | LoadAdjustment_Total | DataFrame column |
| Natforlustjustering_Total | NetworkLossAdjustment_Total | DataFrame column |
| Incitamentjustering_Total | IncentiveAdjustment_Total | DataFrame column |
| Flexibilitetstjanster | FlexibilityServices | DataFrame column |
| Avbrottsersattning_12_24h | InterruptionCompensation_12_24h | DataFrame column |

### 2.7 Company/Entity Terms

| Swedish | English | Context |
|---------|---------|---------|
| foretag | company | Company name |
| företag | company | In comments |
| nätföretag | network_company | DSO |

---

## 3. DataFrame Column Mapping

These columns come from Swedish Excel files (SDF) and need mapping at load time.

### 3.1 Revenue Frame Columns

| Swedish (SDF) | English (Internal) |
|---------------|-------------------|
| Kapitalkostnad_Total | CapitalCost_Total |
| Kapitalkostnad_Period | CapitalCost_Period |
| Kapitalkostnad_I_Intaktsram | CapitalCost_In_RevenueFrame |
| Avkastning_Period | Return_Period |
| Avskrivning_Period | Depreciation_Period |
| Paverkbara_Periodsumma | Controllable_PeriodSum |
| Paverkbara_Medelvarde | Controllable_Average |
| Paverkbara_I_Intaktsram | Controllable_In_RevenueFrame |
| Opaverkbara_Kostnader | NonControllable_Costs |
| Effektivisering_Total | Efficiency_Total |
| Intaktsram_Total | RevenueFrame_Total |
| Investeringar_Utrangeringar | Investments_Disposals |

### 3.2 Incentive Columns

| Swedish (SDF) | English (Internal) |
|---------------|-------------------|
| Kvalitetsjustering_Total | QualityAdjustment_Total |
| Belastningsjustering_Total | LoadAdjustment_Total |
| Natforlustjustering_Total | NetworkLossAdjustment_Total |
| Incitamentjustering_Total | IncentiveAdjustment_Total |
| Flexibilitetstjanster | FlexibilityServices |
| Avbrottsersattning_12_24h | InterruptionCompensation_12_24h |

---

## 4. Enum Classes

| Current | New |
|---------|-----|
| `PaverkbaraMethod` | `ControllableMethod` |
| `PaverkbaraMethod.OPEX` | `ControllableMethod.OPEX` |
| `PaverkbaraMethod.TOTEX` | `ControllableMethod.TOTEX` |

---

## 5. Config Keys (ui_config)

These are already English but reference Swedish concepts:

| Key | Current Value | New Value |
|-----|---------------|-----------|
| `m5_efficiency.paverkbara_method` | `"OPEX"/"TOTEX"` | Keep values, rename key to `controllable_method` |

---

## 6. Files Requiring Changes

### High Impact (many changes)
1. `effektiviseringskrav.py` → `efficiency_requirement.py`
2. `intaktsram_assembly.py` → `revenue_frame_assembly.py`
3. `paverkbara_calculations.py` → `controllable_cost_calculations.py`
4. `post_dea.py`
5. `case_definition.py`
6. `stage_outputs.py`
7. `config_adapter.py`
8. `baseline_data.py`

### Medium Impact
9. `2_results.py`
10. `diagram_data.py`
11. `debug_logger.py`
12. `incentive_calculations.py`
13. `m5_efficiency.py`
14. `m5_efficiency_output.py`
15. `export_excel.py`

### Low Impact (few changes)
16. `baseline.py`
17. `extraction.py`
18. `state_manager.py`
19. `formulas.py`
20. `m3_cost_of_capital_output.py`
21. `m4_operating_exp_output.py`
22. `module_registry.py`
23. `case_summary.py`
24. `data_mapping.py`
25. `kent_calculations.py`
26. `wacc_scaling.py`
27. `incentive_data.py`
28. `incentive_parameters.py`
29. `post_dea_capex_helpers.py`
30. `time_codes.py`
31. `export_button.py`

---

## 7. Migration Strategy

### Phase 1: Core Data Structures
1. Update `case_definition.py` (enums, config classes)
2. Update `stage_outputs.py` (output dataclasses)
3. Update `baseline_data.py` (add column mapping at load)

### Phase 2: Calculation Modules
4. Rename and update `effektiviseringskrav.py`
5. Rename and update `intaktsram_assembly.py`
6. Rename and update `paverkbara_calculations.py`
7. Update `post_dea.py`

### Phase 3: Pipeline & Config
8. Update `config_adapter.py`
9. Update `baseline.py`
10. Update remaining pipeline files

### Phase 4: Frontend & Output
11. Update result output modules
12. Update `2_results.py`
13. Update `diagram_data.py`
14. Update export modules

### Phase 5: Cleanup
15. Update comments/docstrings
16. Update state_manager defaults
17. Final testing

---

## 8. Decisions & Notes

### Keep Swedish
- `nuav`, `ekdep`, `maxdep` - Official KENT/Ei terminology
- Category names in `asset_categories.py` - Regulatory terms
- Sheet names in Excel files - External data source

### Column Mapping Approach
Create a `COLUMN_MAPPING` dict in `baseline_data.py`:
```python
COLUMN_MAPPING = {
    'Kapitalkostnad_Total': 'CapitalCost_Total',
    'Paverkbara_Periodsumma': 'Controllable_PeriodSum',
    # ... etc
}
```
Apply with `df.rename(columns=COLUMN_MAPPING)` at load time.

### Backwards Compatibility
- Saved cases in Firestore may have old key names
- Consider migration or dual-key support

---

## 9. Statistics

- **Files to modify:** 31
- **Variables/functions to rename:** ~80 unique terms
- **DataFrame columns to map:** ~18
- **Estimated str_replace operations:** 150-200
- **Risk level:** Medium (DataFrame columns are sensitive)

---

*Document created: 2025-02-03*
*For use in Regumetrica refactoring sessions*

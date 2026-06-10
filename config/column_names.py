"""
config/column_names.py

Canonical English column names for all DataFrames in the pipeline.
Single source of truth — import from here, never hardcode column names.

Swedish column names should ONLY appear in data_loaders/ where they map
from file columns to these English names.
"""

# =============================================================================
# Identifiers (kept as-is — domain abbreviations)
# =============================================================================
COL_REID = "REId"
COL_DMU = "DMU"
COL_ID_NETWORK = "id_network"
COL_COMPANY_NAME = "company_name"  # was: Företag
COL_COMPANY_NAME_SHORT = "company_name_short"  # curated short name, from data/reference/company_names.csv
COL_DISPLAY_NAME = "display_name"  # "Kortnamn (REId)" — built at the load boundary

# =============================================================================
# Capital costs (from capcost_a.parquet / KENT calculations)
# =============================================================================
COL_CAPITAL_COST_2024 = "capital_cost_2024"  # was: CAPEX, Kapitalkostnad_2024
COL_CAPITAL_COST_2025 = "capital_cost_2025"
COL_CAPITAL_COST_2026 = "capital_cost_2026"
COL_CAPITAL_COST_2027 = "capital_cost_2027"
COL_CAPITAL_COST_PERIOD = "capital_cost_period"  # was: Kapitalkostnad_Period, Kapitalkostnad_Total

# =============================================================================
# Depreciation (from capcost_a.parquet / KENT)
# =============================================================================
COL_DEPRECIATION_2024 = "depreciation_2024"  # was: Avskrivning, Avskrivning_2024
COL_DEPRECIATION_2025 = "depreciation_2025"
COL_DEPRECIATION_2026 = "depreciation_2026"
COL_DEPRECIATION_2027 = "depreciation_2027"
COL_DEPRECIATION_PERIOD = "depreciation_period"  # was: Avskrivning_Period

# =============================================================================
# Return on assets (from capcost_a.parquet / KENT)
# =============================================================================
COL_RETURN_2024 = "return_on_assets_2024"  # was: Avkastning, Avkastning_2024
COL_RETURN_2025 = "return_on_assets_2025"
COL_RETURN_2026 = "return_on_assets_2026"
COL_RETURN_2027 = "return_on_assets_2027"
COL_RETURN_PERIOD = "return_on_assets_period"  # was: Avkastning_Period

# =============================================================================
# Controllable costs
# =============================================================================
COL_CONTROLLABLE_AVG = "controllable_cost_average"  # was: OPEXp, Paverkbara_Medelvarde
COL_NEO_ADJUSTMENTS = "neo_adjustments_period"  # was: Neonjusteringar
COL_CONTROLLABLE_2024 = "controllable_cost_2024"  # was: Paverkbara_2024
COL_CONTROLLABLE_2025 = "controllable_cost_2025"
COL_CONTROLLABLE_2026 = "controllable_cost_2026"
COL_CONTROLLABLE_2027 = "controllable_cost_2027"
COL_CONTROLLABLE_PERIOD = "controllable_cost_period"  # was: Paverkbara_Periodsumma
COL_CONTROLLABLE_BEFORE = "controllable_cost_before_period"  # was: Paverkbara_Fore_Periodsumma
COL_EFFICIENCY_DEDUCTION = "efficiency_deduction_total"  # was: Effektivisering_Total

# OPEX/CAPEX breakdown (from TOTEX method)
COL_OPEX_BEFORE = "opex_before"  # was: OPEX_Fore
COL_OPEX_AFTER = "opex_after"  # was: OPEX_Efter
COL_OPEX_EFF_DEDUCTION = "opex_efficiency_deduction"  # was: OPEX_Effektivisering
COL_OPEX_SHARE = "opex_share"  # was: OPEX_Andel
COL_CAPEX_BEFORE = "capex_before"  # was: CAPEX_Fore
COL_CAPEX_AFTER = "capex_after"  # was: CAPEX_Efter
COL_CAPEX_EFF_DEDUCTION = "capex_efficiency_deduction"  # was: CAPEX_Effektivisering
COL_CAPEX_SHARE = "capex_share"  # was: CAPEX_Andel

# =============================================================================
# TOTEX
# =============================================================================
COL_TOTEX = "totex_first_year"  # was: TOTEX

# =============================================================================
# DEA and efficiency
# =============================================================================
COL_DEA_EFFICIENCY = "dea_efficiency"  # was: Effektivitet
COL_DEA_SUPER_EFF = "dea_super_efficiency"  # was: Supereffektivitet
COL_DEA_POTENTIAL = "potential"  # already English
COL_IS_OUTLIER = "is_outlier"  # already English
COL_EFF_REQ_ANNUAL = "efficiency_requirement_annual"  # was: Effkrav_proc

# =============================================================================
# Revenue frame
# =============================================================================
COL_CAPITAL_COST_AFTER_EFF = "capital_cost_after_efficiency"  # was: Kapitalkostnad_Efter_Effektivisering
COL_CAPITAL_COST_IN_RF = "capital_cost_in_revenue_frame"  # was: Kapitalkostnad_I_Intaktsram
COL_CONTROLLABLE_IN_RF = "controllable_cost_in_revenue_frame"  # was: Paverkbara_I_Intaktsram
COL_NON_CONTROLLABLE = "non_controllable_cost_period"  # was: Opaverkbara_Kostnader
COL_FLEXIBILITY = "flexibility_services_period"  # was: Flexibilitetstjanster
COL_INTERRUPTION = "interruption_compensation_period"  # was: Avbrottsersattning_12_24h
COL_STATE_DEDUCTION = "state_subsidy_deduction_period"  # was: Avdrag_Statligt_Stod
COL_REVENUE_FRAME = "revenue_frame_total"  # was: Intaktsram_Total

# =============================================================================
# Incentive adjustments
# =============================================================================
COL_QUALITY_INCENTIVE = "quality_incentive_total"  # was: Kvalitetsjustering_Total
COL_NETLOSS_INCENTIVE = "network_loss_incentive_total"  # was: Natforlustjustering_Total
COL_LOAD_INCENTIVE = "load_incentive_total"  # was: Belastningsjustering_Total
COL_INCENTIVE_TOTAL = "incentive_adjustment_total"  # was: Incitamentjustering_Total
COL_MISSING_INCENTIVE = "Missing_Incentive_Data"  # already English

# =============================================================================
# Method metadata
# =============================================================================
COL_METHOD_USED = "method_used"  # was: Method_used

# =============================================================================
# Cost detail (grunddata parquet files)
# =============================================================================
COL_CTRL_CATEGORY = "category"  # Controllable cost category name
COL_CTRL_AMOUNT_NOMINAL = "amount_nominal"  # Nominal cost (before index)
COL_NONCTRL_KENT_CATEGORY = "kent_category"  # Non-controllable KENT category name
COL_NONCTRL_AMOUNT = "amount"  # Non-controllable cost amount

# Per-year non-controllable (from grunddata aggregation)
COL_NON_CONTROLLABLE_2024 = "non_controllable_cost_2024"
COL_NON_CONTROLLABLE_2025 = "non_controllable_cost_2025"
COL_NON_CONTROLLABLE_2026 = "non_controllable_cost_2026"
COL_NON_CONTROLLABLE_2027 = "non_controllable_cost_2027"

# =============================================================================
# Volume variables (kept as-is — well-understood abbreviations)
# =============================================================================
COL_CU = "CU"
COL_MW = "MW"
COL_NS = "NS"
COL_MWH_LOW = "MWhl"
COL_MWH_HIGH = "MWhh"

# =============================================================================
# New benchmarking model (calculations/new_benchmarking) — add-on, isolated
# =============================================================================
# TOTEX building blocks (all annual, tkr, to mirror the current TOTEX definition
# controllable_cost_average + capital_cost_2024).
COL_TOTEX_NEW = "totex_new"                              # single DEA input in the new model
COL_OPEX_NEW = "opex_new"                                # controllable + losses@common price + selected non-ctrl
COL_LOSS_VALUED = "loss_valued_common_price"            # nf_obs · k_nf · e_in, annual avg (tkr)
COL_NONCTRL_SELECTED = "non_controllable_selected"      # grid sub/conn + feed-in + capacity reserve, annual avg (tkr)
COL_CAPITAL_COST_ENV_ADJ = "capital_cost_2024_env_adjusted"  # capital_cost_2024 after förläggningsmiljö correction
COL_CABLE_LENGTH_KM = "cable_length_km"                  # physical line length per company (new DEA output)
COL_DEA_REFERENCE = "dea_reference_e75"                  # E75 reference (third quartile, excl. outliers) — two-sided model

# Per-model DEA / efficiency results (new model vs current model, compared side by side).
COL_DEA_EFFICIENCY_NEW = "dea_efficiency_new"
COL_DEA_EFFICIENCY_CURRENT = "dea_efficiency_current"
COL_POTENTIAL_NEW = "potential_new"
COL_POTENTIAL_CURRENT = "potential_current"
COL_IS_OUTLIER_NEW = "is_outlier_new"
COL_IS_OUTLIER_CURRENT = "is_outlier_current"
COL_EFF_REQ_NEW = "efficiency_requirement_annual_new"
COL_EFF_REQ_CURRENT = "efficiency_requirement_annual_current"
COL_EFF_REQ_DELTA = "efficiency_requirement_annual_delta"   # new − current
COL_EFFICIENCY_DELTA = "dea_efficiency_delta"               # new − current

# =============================================================================
# Rename dictionaries for data_loaders/
# Swedish file column → English canonical name
# =============================================================================

DATA_MODELLER_RENAME = {
    "Företag": COL_COMPANY_NAME,
    "CAPEX": COL_CAPITAL_COST_2024,
    "OPEXp": COL_CONTROLLABLE_AVG,
    # Note: "Kapitalkostnad_2024" alias is not created; CAPEX maps directly
    # Note: Avkastning columns removed from DM; return sourced from capcost_a.parquet
    "TOTEX": COL_TOTEX,
}

EIS_DEA_RENAME = {
    "Företag": COL_COMPANY_NAME,
    "Effektivitet": COL_DEA_EFFICIENCY,
    "Supereffektivitet": COL_DEA_SUPER_EFF,
    "Effkrav_proc": COL_EFF_REQ_ANNUAL,
}

# SDF IR sheet column rename (long Swedish names → English)
SDF_IR_RENAME = {
    "Påverkbara kostnader": COL_CONTROLLABLE_PERIOD,
    "Opåverkbara kostnader": COL_NON_CONTROLLABLE,
    "Kostnader för flexibilitetstjänster": COL_FLEXIBILITY,
    "Avbrottsersättning 12-24 timmar": COL_INTERRUPTION,
    "Avdrag av kapitalkostnader pga anläggningar med statligt stöd": COL_STATE_DEDUCTION,
    "Avdrag av kapitalkostnader pga. anläggningar som finansierats med statlig stöd": COL_STATE_DEDUCTION,
    "Kapitalkostnad": COL_CAPITAL_COST_PERIOD,
    "-varav Kapital-förslitning": COL_DEPRECIATION_PERIOD,
    "varav Kapital-bindning": COL_RETURN_PERIOD,
}

# SDF IR revenue frame total column (varies by file version)
SDF_IR_REVENUE_FRAME_PATTERNS = [
    "BERÄKNAD INTÄKTSRAM",
    "intäktsram",
]

"""
config/glossary.py

Centralized glossary for all Parameter-IDs and Variable-IDs
from the Regumetrica User Manual (Tables 1-15).

Single source of truth. All frontend modules import from here.
Pipeline/calculations do NOT use these IDs.

Design:
- Named constants (PID_*, VID_*) for direct reference
- Generator functions for systematic asset-category IDs
- INCENTIVE_VARIABLE_META for m3 incentive variable metadata
- GlossaryEntry + GLOSSARY dict for programmatic lookups

Note on capital-cost output IDs (Table 7): The User Manual assigns
30.2-30.18 to per-category capital costs, which conflicts with
Table 9 (30.2.X = network loss variables). The code resolves this
by using a four-level scheme under the 30.1 block: totals at
30.1.1.{component} and per-category at 30.1.{cat+1}.{component}.
This keeps 30.1.1 (totals) and 30.1.2-30.1.18 (categories) as
distinct parent nodes, so no ID is both a leaf and a parent. The
glossary follows the code convention.
"""

from typing import NamedTuple, Dict, List, Tuple, Optional


# =============================================================================
# GLOSSARY ENTRY
# =============================================================================

class GlossaryEntry(NamedTuple):
    """Metadata for one parameter or variable ID."""
    id: str              # e.g. "1.1.1", "10.2", "30.2.1"
    description: str     # English description from User Manual
    module: str          # "m1", "m2", "m3", "m4", "m5"
    kind: str            # "parameter", "input_var", "output_var"
    unit: str = ""       # "kr", "share", "years", "MWh", etc.


# =============================================================================
# ASSET CATEGORY NAMES  (17 categories, cat_encode 1-17)
# Used by generator functions below
# =============================================================================

ASSET_CATEGORY_NAMES: Dict[int, str] = {
    1: "Andra markarbeten och byggnader, linjekoncession",
    2: "Annan ledning, linjekoncession",
    3: "Annan ledning, områdeskoncession",
    4: "Annan luftledning, linjekoncession",
    5: "It-system",
    6: "Kabelskåp",
    7: "Ledning med en spänning om 220 kV eller mer, med undantag för luftledning, linjekoncession",
    8: "Luftledning med en spänning om 220 kV eller mer, linjekoncession",
    9: "Luftledning, områdeskoncession",
    10: "Markarbeten och byggnader med anknytning till ett ledningsnät med en spänning om 220 kV eller mer, linjekoncession",
    11: "Markarbeten och byggnader, områdeskoncession",
    12: "Mätare",
    13: "Nätstation",
    14: "Shuntreaktor",
    15: "Styr- och kontrollutrustning",
    16: "Ställverk utan sekundärapparater",
    17: "Transformator",
}

# Customer type names (SNI codes) for incentive variables
CUSTOMER_TYPE_NAMES: Dict[int, str] = {
    5: "Household",
    1: "Agriculture",
    3: "Trade/Services",
    2: "Industry",
    4: "Public sector",
    6: "Boundary points",
}

# Display order for customer types (User Manual Table 9)
CUSTOMER_TYPES_ORDERED: List[Tuple[int, int, str]] = [
    (1, 5, "Household"),
    (2, 1, "Agriculture"),
    (3, 3, "Trade/Services"),
    (4, 2, "Industry"),
    (5, 4, "Public sector"),
    (6, 6, "Boundary points"),
]


# =============================================================================
# MODULE 1: REGULATORY ASSET BASE VALUATION (User Manual Tables 1-3)
# =============================================================================

# --- 1.1 General asset valuation parameters ---
PID_GENERAL_SCALING = "1.1.1"

# --- 1.2 Category scaling factors ---
def scaling_param_id(cat_encode: int) -> str:
    """Parameter-ID for category scaling factor. Table 1: 1.2.1-1.2.17"""
    return f"1.2.{cat_encode}"

# --- 10.X Input variables: asset quantities ---
def asset_qty_var_id(cat_encode: int) -> str:
    """Variable-ID for asset quantity by type. Table 2: 10.2-10.18"""
    return f"10.{cat_encode + 1}"

# --- 11.X Output variables: asset values ---
VID_TOTAL_ASSET_VALUE = "11.1"

def asset_value_var_id(cat_encode: int) -> str:
    """Variable-ID for asset value by type. Table 3: 11.2-11.18"""
    return f"11.{cat_encode + 1}"


# =============================================================================
# MODULE 2: DEPRECIATION (User Manual Tables 4-5)
# =============================================================================

# --- 2.X.1 / 2.X.2 Lifetime parameters ---
def lifetime_ordinary_param_id(cat_encode: int) -> str:
    """Parameter-ID for ordinary lifetime. Table 4: 2.1.1-2.17.1"""
    return f"2.{cat_encode}.1"

def lifetime_tail_param_id(cat_encode: int) -> str:
    """Parameter-ID for tail lifetime. Table 4: 2.1.2-2.17.2"""
    return f"2.{cat_encode}.2"

# --- 20.X Output variables: depreciation cost ---
VID_TOTAL_DEPRECIATION_ORD = "20.1.1"
VID_TOTAL_DEPRECIATION_TAIL = "20.1.2"

def depreciation_var_id(cat_encode: int) -> str:
    """Variable-ID for depreciation by type (combined). Table 5: 20.2-20.18"""
    return f"20.{cat_encode + 1}"

def depreciation_ord_var_id(cat_encode: int) -> str:
    """Variable-ID for ordinary depreciation by type. Table 5: 20.X.1"""
    return f"20.{cat_encode + 1}.1"

def depreciation_tail_var_id(cat_encode: int) -> str:
    """Variable-ID for tail depreciation by type. Table 5: 20.X.2"""
    return f"20.{cat_encode + 1}.2"

def depreciation_components_var_id(cat_encode: int) -> str:
    """Combined Variable-ID string 'ord / tail' for display. Table 5."""
    base = cat_encode + 1
    return f"20.{base}.1; 20.{base}.2"


# =============================================================================
# MODULE 3: COST OF CAPITAL (User Manual Tables 6-10)
# =============================================================================

# --- 3.1 Base WACC parameters (Table 6) ---
PID_DEBT_RATIO = "3.1.1"
PID_ASSET_BETA = "3.1.2"
PID_RISK_FREE_RATE = "3.1.3"
PID_MARKET_RISK_PREMIUM = "3.1.4"
PID_CREDIT_RISK_PREMIUM = "3.1.5"
PID_TAX_RATE = "3.1.6"
PID_INFLATION = "3.1.7"

# --- 3.2 Endogenously determined parameters (Table 6) ---
PID_EQUITY_BETA = "3.2.1"
PID_COST_OF_EQUITY = "3.2.2"
PID_COST_OF_DEBT = "3.2.3"
PID_WACC_NOMINAL = "3.2.4"
PID_WACC_REAL = "3.2.5"

# --- 30.1 Capital cost output (Table 7) ---
# Totals live at 30.1.1.{component}; per-category at 30.1.{cat+1}.{component}.
# This keeps totals (30.1.1) and categories (30.1.2-30.1.18) as distinct
# parent nodes, avoiding any leaf/parent clash, and sidesteps the Table 9
# conflict (30.2.X = network loss variables).
VID_TOTAL_CAPITAL_COST_ORD = "30.1.1.1"
VID_TOTAL_CAPITAL_COST_TAIL = "30.1.1.2"

def capital_cost_var_id(cat_encode: int, component: str = "combined") -> str:
    """
    Variable-ID for capital cost by category. Table 7.

    Code uses 30.1.{cat+1}.{suffix} to avoid numbering conflict with
    incentive variables in Table 9.

    Args:
        cat_encode: 1-17
        component: "ord", "tail", or "combined"
    """
    base = cat_encode + 1
    if component == "ord":
        return f"30.1.{base}.1"
    elif component == "tail":
        return f"30.1.{base}.2"
    else:
        return f"30.1.{base}.1/.2"

# --- 3.3 Overall adjustment cap (Table 8) ---
PID_MAX_TOTAL_ADJUSTMENT = "3.3.1"

# --- 3.4 Network loss parameters (Table 8) ---
PID_LOSS_SCALING = "3.4.1"
PID_LOSS_SHARING = "3.4.2"
PID_LOSS_COST_AVG = "3.4.3"

# --- 3.5 Utilization rate parameters (Table 8) ---
PID_UTIL_SCALING = "3.5.1"

# --- 3.6 Interruption parameters (Table 8) ---
PID_INTER_COST_SCALING = "3.6.1"
PID_CPI_2024 = "3.6.2"
PID_CPI_2025 = "3.6.3"
PID_CPI_2026 = "3.6.4"
PID_CPI_2027 = "3.6.5"
PID_CEMI4_CORRECTION = "3.6.6"

# ILE (interruption energy cost) Parameter-IDs (Table 8: 3.6.7-3.6.18)
# Keys: (sni, plan_type) where plan_type is "unplanned"/"planned"
PID_ILE: Dict[Tuple[int, str], str] = {
    (5, "unplanned"): "3.6.7",  (5, "planned"): "3.6.8",    # Household
    (1, "unplanned"): "3.6.9",  (1, "planned"): "3.6.10",   # Agriculture
    (3, "unplanned"): "3.6.11", (3, "planned"): "3.6.12",   # Trade/Services
    (2, "unplanned"): "3.6.13", (2, "planned"): "3.6.14",   # Industry
    (4, "unplanned"): "3.6.15", (4, "planned"): "3.6.16",   # Public sector
    (6, "unplanned"): "3.6.17", (6, "planned"): "3.6.18",   # Boundary points
}

# ILEffekt (interruption power cost) Parameter-IDs (Table 8: 3.6.19-3.6.30)
PID_ILEFFEKT: Dict[Tuple[int, str], str] = {
    (5, "unplanned"): "3.6.19", (5, "planned"): "3.6.20",   # Household
    (1, "unplanned"): "3.6.21", (1, "planned"): "3.6.22",   # Agriculture
    (3, "unplanned"): "3.6.23", (3, "planned"): "3.6.24",   # Trade/Services
    (2, "unplanned"): "3.6.25", (2, "planned"): "3.6.26",   # Industry
    (4, "unplanned"): "3.6.27", (4, "planned"): "3.6.28",   # Public sector
    (6, "unplanned"): "3.6.29", (6, "planned"): "3.6.30",   # Boundary points
}

# --- 3.7 KPI indexation factors (per year) ---
# KPI factors used to index interruption costs to the reference price level.
# The User Manual refers to these factors without numbering them; the code and
# UI carry them under 3.7.X (one per year), distinct from the CPI factors (3.6.2-3.6.5).
PID_KPI: Dict[int, str] = {
    2024: "3.7.1", 2025: "3.7.2", 2026: "3.7.3", 2027: "3.7.4",
}

# --- 30.2 Network loss input variables (Table 9) ---
VID_NF_NORM = "30.2.1"
VID_NF_OBS = "30.2.2"
VID_E_IN = "30.2.3"

# --- 30.3 Utilization rate input variables (Table 9) ---
VID_UG_NORM = "30.3.1"
VID_UG_OBS = "30.3.2"
VID_K_UPSTREAM = "30.3.3"

# --- 30.4 Interruption input variables (Table 9) ---
VID_CEMI4_NORM = "30.4.1"
VID_CEMI4_OBS = "30.4.2"

# AME Variable-IDs: annual average power per customer type (Table 9: 30.4.3-30.4.8)
VID_AME: Dict[int, str] = {
    5: "30.4.3",   # Household
    1: "30.4.4",   # Agriculture
    3: "30.4.5",   # Trade/Services
    2: "30.4.6",   # Industry
    4: "30.4.7",   # Public sector
    6: "30.4.8",   # Boundary points
}

# AIT Variable-IDs: average interruption time (Table 9: 30.4.9-30.4.32)
# Key: (sni, plan_type, measurement) where plan_type is 'o'(unplanned)/'a'(planned),
# measurement is 'norm'/'obs'
VID_AIT: Dict[Tuple[int, str, str], str] = {
    # Household (SNI 5)
    (5, "o", "norm"): "30.4.9",  (5, "a", "norm"): "30.4.10",
    (5, "o", "obs"):  "30.4.11", (5, "a", "obs"):  "30.4.12",
    # Agriculture (SNI 1)
    (1, "o", "norm"): "30.4.13", (1, "a", "norm"): "30.4.14",
    (1, "o", "obs"):  "30.4.15", (1, "a", "obs"):  "30.4.16",
    # Trade/Services (SNI 3)
    (3, "o", "norm"): "30.4.17", (3, "a", "norm"): "30.4.18",
    (3, "o", "obs"):  "30.4.19", (3, "a", "obs"):  "30.4.20",
    # Industry (SNI 2)
    (2, "o", "norm"): "30.4.21", (2, "a", "norm"): "30.4.22",
    (2, "o", "obs"):  "30.4.23", (2, "a", "obs"):  "30.4.24",
    # Public sector (SNI 4)
    (4, "o", "norm"): "30.4.25", (4, "a", "norm"): "30.4.26",
    (4, "o", "obs"):  "30.4.27", (4, "a", "obs"):  "30.4.28",
    # Boundary points (SNI 6)
    (6, "o", "norm"): "30.4.29", (6, "a", "norm"): "30.4.30",
    (6, "o", "obs"):  "30.4.31", (6, "a", "obs"):  "30.4.32",
}

# AIF Variable-IDs: average interruption frequency (Table 9: 30.4.33-30.4.56)
VID_AIF: Dict[Tuple[int, str, str], str] = {
    # Household (SNI 5)
    (5, "o", "norm"): "30.4.33", (5, "a", "norm"): "30.4.34",
    (5, "o", "obs"):  "30.4.35", (5, "a", "obs"):  "30.4.36",
    # Agriculture (SNI 1)
    (1, "o", "norm"): "30.4.37", (1, "a", "norm"): "30.4.38",
    (1, "o", "obs"):  "30.4.39", (1, "a", "obs"):  "30.4.40",
    # Trade/Services (SNI 3)
    (3, "o", "norm"): "30.4.41", (3, "a", "norm"): "30.4.42",
    (3, "o", "obs"):  "30.4.43", (3, "a", "obs"):  "30.4.44",
    # Industry (SNI 2)
    (2, "o", "norm"): "30.4.45", (2, "a", "norm"): "30.4.46",
    (2, "o", "obs"):  "30.4.47", (2, "a", "obs"):  "30.4.48",
    # Public sector (SNI 4)
    (4, "o", "norm"): "30.4.49", (4, "a", "norm"): "30.4.50",
    (4, "o", "obs"):  "30.4.51", (4, "a", "obs"):  "30.4.52",
    # Boundary points (SNI 6)
    (6, "o", "norm"): "30.4.53", (6, "a", "norm"): "30.4.54",
    (6, "o", "obs"):  "30.4.55", (6, "a", "obs"):  "30.4.56",
}

# --- 30.2-30.5 Incentive output variables (Table 10) ---
VID_LOSS_BEFORE_CAP = "30.2.4"
VID_LOSS_AFTER_CAP = "30.2.5"
VID_UTIL_BEFORE_CAP = "30.3.4"
VID_UTIL_AFTER_CAP = "30.3.5"
VID_INTER_BEFORE_CEMI4 = "30.4.57"
VID_INTER_AFTER_CEMI4 = "30.4.58"
VID_INTER_AFTER_CAP = "30.4.59"
VID_TOTAL_BEFORE_AGG_CAP = "30.5.1"
VID_TOTAL_AFTER_AGG_CAP = "30.5.2"

# Incentive output: internal column name -> Variable-ID (for m3_incentive_output)
INCENTIVE_OUTPUT_VAR_IDS: Dict[str, str] = {
    "loss_incentive_a":    VID_LOSS_BEFORE_CAP,
    "loss_incentive":      VID_LOSS_AFTER_CAP,
    "util_incentive_a":    VID_UTIL_BEFORE_CAP,
    "util_incentive":      VID_UTIL_AFTER_CAP,
    "inc_inter":           VID_INTER_BEFORE_CEMI4,
    "inter_incentive_a":   VID_INTER_AFTER_CEMI4,
    "inter_incentive":     VID_INTER_AFTER_CAP,
    "total_before_agg_cap": VID_TOTAL_BEFORE_AGG_CAP,
    "incentive_total_year": VID_TOTAL_AFTER_AGG_CAP,
}

# Incentive input: internal column name -> (Variable-ID, label, unit, format_str)
# Used by m3_incentive_variables.py for rendering
INCENTIVE_VARIABLE_META: Dict[str, Tuple[str, str, str, str]] = {
    # 30.2 Network loss
    "nf_norm":    (VID_NF_NORM,    "Network loss norm",         "share", "%.4f"),
    "nf_obs":     (VID_NF_OBS,     "Network loss observed",     "share", "%.4f"),
    "e_in":       (VID_E_IN,       "Energy input",              "MWh",   "%.0f"),
    # 30.3 Utilization rate
    "ug_norm":    (VID_UG_NORM,    "Utilization rate norm",     "share", "%.4f"),
    "ug_obs":     (VID_UG_OBS,     "Utilization rate observed", "share", "%.4f"),
    "k_upstream": (VID_K_UPSTREAM, "Cost for upstream network", "kr",    "%.0f"),
    # 30.4 Interruption - CEMI4
    "cemi4_norm": (VID_CEMI4_NORM, "CEMI4 norm",               "share", "%.4f"),
    "cemi4_obs":  (VID_CEMI4_OBS,  "CEMI4 observed",           "share", "%.4f"),
}


# =============================================================================
# MODULE 4: OPERATING EXPENDITURES (User Manual Tables 11-12)
# =============================================================================

# --- 4.1 Parameters (Table 11) ---
PID_OPEX_SCALING = "4.1.1"
PID_FLEX_SCALING = "4.1.2"
PID_NON_ADJ_SCALING = "4.1.3"

# --- 40.X Input variables (Table 12) ---
VID_OPEX_ADJUSTABLE = "40.1.1"
VID_FLEX_SERVICE = "40.1.2"
VID_NON_ADJUSTABLE = "40.2.1"


# =============================================================================
# MODULE 5: EFFICIENCY INCENTIVE (User Manual Tables 13-15)
# =============================================================================

# --- 5.1-5.4 Parameters (Table 13) ---
PID_OUTLIER_THRESHOLD = "5.1.1"
PID_MAX_POTENTIAL_CAP = "5.2.1"
PID_REALIZATION_TIME = "5.2.2"
PID_CUSTOMER_SHARING = "5.2.3"
PID_MIN_ANNUAL_REQ = "5.3.1"
PID_TRUNC_MIN = ""                 # Derived internally; not in User Manual
PID_COST_BASE = "5.4.1"

# --- 50.2 Input variables (Table 14) ---
VID_SUBSCRIPTIONS = "50.2.1"
VID_SUBSTATIONS = "50.2.2"
VID_ENERGY_LOW = "50.2.3"
VID_ENERGY_HIGH = "50.2.4"
VID_PMAX = "50.2.5"

# --- 50.3 Output: derived efficiency measures (Table 15) ---
VID_EFFICIENCY_SCORE = "50.3.1"
VID_SUPER_EFFICIENCY = "50.3.2"
VID_EFFICIENCY_POTENTIAL = "50.3.3"
VID_APPLIED_POTENTIAL = "50.3.4"

# --- 50.4 Output: efficiency-adjusted costs (Table 15) ---
VID_OPEX_EFF_ADJUSTMENT = "50.4.1"
VID_CAPEX_EFF_ADJUSTMENT = "50.4.2"
VID_OPEX_AFTER_EFF = "50.4.3"
VID_CAPEX_AFTER_EFF = "50.4.4"


# =============================================================================
# FULL GLOSSARY DICT  (built at module load)
# =============================================================================

def _build_glossary() -> Dict[str, GlossaryEntry]:
    """Build complete glossary from all constants above."""
    g: Dict[str, GlossaryEntry] = {}

    # --- M1 Parameters ---
    g[PID_GENERAL_SCALING] = GlossaryEntry(
        PID_GENERAL_SCALING, "General scaling factor for asset valuation",
        "m1", "parameter")
    for ce in range(1, 18):
        pid = scaling_param_id(ce)
        g[pid] = GlossaryEntry(
            pid, f"Scaling factor for {ASSET_CATEGORY_NAMES[ce]}",
            "m1", "parameter")

    # --- M1 Input variables ---
    for ce in range(1, 18):
        vid = asset_qty_var_id(ce)
        g[vid] = GlossaryEntry(
            vid, f"Asset quantity: {ASSET_CATEGORY_NAMES[ce]}",
            "m1", "input_var")

    # --- M1 Output variables ---
    g[VID_TOTAL_ASSET_VALUE] = GlossaryEntry(
        VID_TOTAL_ASSET_VALUE, "Total asset value for all asset types",
        "m1", "output_var", "kr")
    for ce in range(1, 18):
        vid = asset_value_var_id(ce)
        g[vid] = GlossaryEntry(
            vid, f"Asset value: {ASSET_CATEGORY_NAMES[ce]}",
            "m1", "output_var", "kr")

    # --- M2 Parameters ---
    for ce in range(1, 18):
        pid_o = lifetime_ordinary_param_id(ce)
        pid_t = lifetime_tail_param_id(ce)
        g[pid_o] = GlossaryEntry(
            pid_o, f"Ordinary lifetime: {ASSET_CATEGORY_NAMES[ce]}",
            "m2", "parameter", "years")
        g[pid_t] = GlossaryEntry(
            pid_t, f"Tail lifetime: {ASSET_CATEGORY_NAMES[ce]}",
            "m2", "parameter", "years")

    # --- M2 Output variables ---
    g[VID_TOTAL_DEPRECIATION_ORD] = GlossaryEntry(
        VID_TOTAL_DEPRECIATION_ORD, "Total depreciation cost (ordinary)",
        "m2", "output_var", "kr")
    g[VID_TOTAL_DEPRECIATION_TAIL] = GlossaryEntry(
        VID_TOTAL_DEPRECIATION_TAIL, "Total depreciation cost (tail)",
        "m2", "output_var", "kr")
    for ce in range(1, 18):
        g[depreciation_ord_var_id(ce)] = GlossaryEntry(
            depreciation_ord_var_id(ce),
            f"Depreciation (ordinary): {ASSET_CATEGORY_NAMES[ce]}",
            "m2", "output_var", "kr")
        g[depreciation_tail_var_id(ce)] = GlossaryEntry(
            depreciation_tail_var_id(ce),
            f"Depreciation (tail): {ASSET_CATEGORY_NAMES[ce]}",
            "m2", "output_var", "kr")

    # --- M3 WACC parameters ---
    wacc_params = [
        (PID_DEBT_RATIO, "Debt ratio"),
        (PID_ASSET_BETA, "Asset beta"),
        (PID_RISK_FREE_RATE, "Risk-free rate"),
        (PID_MARKET_RISK_PREMIUM, "Market risk premium"),
        (PID_CREDIT_RISK_PREMIUM, "Credit risk premium"),
        (PID_TAX_RATE, "Tax rate"),
        (PID_INFLATION, "Inflation, CPIF forecast"),
        (PID_EQUITY_BETA, "Equity beta"),
        (PID_COST_OF_EQUITY, "Nominal cost of equity after tax"),
        (PID_COST_OF_DEBT, "Nominal cost of debt after tax"),
        (PID_WACC_NOMINAL, "Nominal WACC before tax"),
        (PID_WACC_REAL, "Real WACC before tax"),
    ]
    for pid, desc in wacc_params:
        g[pid] = GlossaryEntry(pid, desc, "m3", "parameter")

    # --- M3 Capital cost output ---
    g[VID_TOTAL_CAPITAL_COST_ORD] = GlossaryEntry(
        VID_TOTAL_CAPITAL_COST_ORD, "Total capital cost (ordinary)",
        "m3", "output_var", "kr")
    g[VID_TOTAL_CAPITAL_COST_TAIL] = GlossaryEntry(
        VID_TOTAL_CAPITAL_COST_TAIL, "Total capital cost (tail)",
        "m3", "output_var", "kr")
    for ce in range(1, 18):
        for comp, suffix in [("ord", "ordinary"), ("tail", "tail")]:
            vid = capital_cost_var_id(ce, comp)
            g[vid] = GlossaryEntry(
                vid, f"Capital cost ({suffix}): {ASSET_CATEGORY_NAMES[ce]}",
                "m3", "output_var", "kr")

    # --- M3 Incentive parameters ---
    g[PID_MAX_TOTAL_ADJUSTMENT] = GlossaryEntry(
        PID_MAX_TOTAL_ADJUSTMENT, "Max total adjustment (share of WACC)",
        "m3", "parameter")
    g[PID_LOSS_SCALING] = GlossaryEntry(
        PID_LOSS_SCALING, "Loss incentive scaling parameter",
        "m3", "parameter")
    g[PID_LOSS_SHARING] = GlossaryEntry(
        PID_LOSS_SHARING, "Network loss incentive sharing factor",
        "m3", "parameter")
    g[PID_LOSS_COST_AVG] = GlossaryEntry(
        PID_LOSS_COST_AVG, "Average network loss cost",
        "m3", "parameter", "kr/MWh")
    g[PID_UTIL_SCALING] = GlossaryEntry(
        PID_UTIL_SCALING, "Utilization rate incentive scaling parameter",
        "m3", "parameter")
    g[PID_INTER_COST_SCALING] = GlossaryEntry(
        PID_INTER_COST_SCALING, "Cost scaling parameter (ILE/ILEffekt)",
        "m3", "parameter")
    for year_id, year in [(PID_CPI_2024, 2024), (PID_CPI_2025, 2025),
                          (PID_CPI_2026, 2026), (PID_CPI_2027, 2027)]:
        g[year_id] = GlossaryEntry(year_id, f"CPI {year}", "m3", "parameter")
    g[PID_CEMI4_CORRECTION] = GlossaryEntry(
        PID_CEMI4_CORRECTION, "CEMI4 correction factor",
        "m3", "parameter")
    for year, pid in PID_KPI.items():
        g[pid] = GlossaryEntry(pid, f"KPI indexation factor {year}", "m3", "parameter")
    for key, pid in PID_ILE.items():
        sni, pt = key
        g[pid] = GlossaryEntry(
            pid, f"ILE ({pt}): {CUSTOMER_TYPE_NAMES[sni]}",
            "m3", "parameter", "kr/kWh")
    for key, pid in PID_ILEFFEKT.items():
        sni, pt = key
        g[pid] = GlossaryEntry(
            pid, f"ILEffekt ({pt}): {CUSTOMER_TYPE_NAMES[sni]}",
            "m3", "parameter", "kr/kW")

    # --- M3 Incentive input variables ---
    for col_name, (vid, desc, unit, _fmt) in INCENTIVE_VARIABLE_META.items():
        g[vid] = GlossaryEntry(vid, desc, "m3", "input_var", unit)
    for sni, vid in VID_AME.items():
        g[vid] = GlossaryEntry(
            vid, f"Annual average power: {CUSTOMER_TYPE_NAMES[sni]}",
            "m3", "input_var", "kW")
    for key, vid in VID_AIT.items():
        sni, pt, meas = key
        pt_label = "unplanned" if pt == "o" else "planned"
        g[vid] = GlossaryEntry(
            vid, f"AIT ({pt_label}, {meas}): {CUSTOMER_TYPE_NAMES[sni]}",
            "m3", "input_var", "hours")
    for key, vid in VID_AIF.items():
        sni, pt, meas = key
        pt_label = "unplanned" if pt == "o" else "planned"
        g[vid] = GlossaryEntry(
            vid, f"AIF ({pt_label}, {meas}): {CUSTOMER_TYPE_NAMES[sni]}",
            "m3", "input_var", "count")

    # --- M3 Incentive output variables ---
    incentive_outputs = [
        (VID_LOSS_BEFORE_CAP, "Network loss adjustment before cap"),
        (VID_LOSS_AFTER_CAP, "Network loss adjustment after cap"),
        (VID_UTIL_BEFORE_CAP, "Utilization rate incentive before cap"),
        (VID_UTIL_AFTER_CAP, "Utilization rate incentive after cap"),
        (VID_INTER_BEFORE_CEMI4, "Interruption adjustment before CEMI4 correction"),
        (VID_INTER_AFTER_CEMI4, "Interruption adjustment after CEMI4 correction"),
        (VID_INTER_AFTER_CAP, "Interruption adjustment after CEMI4 correction and cap"),
        (VID_TOTAL_BEFORE_AGG_CAP, "Total adjustment before aggregate cap"),
        (VID_TOTAL_AFTER_AGG_CAP, "Total adjustment after aggregate cap"),
    ]
    for vid, desc in incentive_outputs:
        g[vid] = GlossaryEntry(vid, desc, "m3", "output_var", "kr")

    # --- M4 Parameters ---
    g[PID_OPEX_SCALING] = GlossaryEntry(
        PID_OPEX_SCALING, "Scaling factor adjustable OPEX",
        "m4", "parameter")
    g[PID_FLEX_SCALING] = GlossaryEntry(
        PID_FLEX_SCALING, "Scaling factor flexibility services",
        "m4", "parameter")
    g[PID_NON_ADJ_SCALING] = GlossaryEntry(
        PID_NON_ADJ_SCALING, "Scaling factor non-adjustable OPEX",
        "m4", "parameter")

    # --- M4 Input variables ---
    g[VID_OPEX_ADJUSTABLE] = GlossaryEntry(
        VID_OPEX_ADJUSTABLE, "Adjusted OPEX",
        "m4", "input_var", "kr")
    g[VID_FLEX_SERVICE] = GlossaryEntry(
        VID_FLEX_SERVICE, "Flexibility service cost",
        "m4", "input_var", "kr")
    g[VID_NON_ADJUSTABLE] = GlossaryEntry(
        VID_NON_ADJUSTABLE, "Total non-adjustable costs (prognosis)",
        "m4", "input_var", "kr")

    # --- M5 Parameters ---
    m5_params = [
        (PID_OUTLIER_THRESHOLD, "Outlier threshold (IQRs above Q3)"),
        (PID_MAX_POTENTIAL_CAP, "Maximum efficiency potential cap"),
        (PID_REALIZATION_TIME, "Realization time", "years"),
        (PID_CUSTOMER_SHARING, "Customer sharing factor"),
        (PID_MIN_ANNUAL_REQ, "Minimum annual efficiency requirement"),
        (PID_COST_BASE, "Apply efficiency requirement on TOTEX"),
    ]
    for item in m5_params:
        pid, desc = item[0], item[1]
        unit = item[2] if len(item) > 2 else ""
        g[pid] = GlossaryEntry(pid, desc, "m5", "parameter", unit)

    # --- M5 Input variables ---
    m5_inputs = [
        (VID_SUBSCRIPTIONS, "Number of subscriptions"),
        (VID_SUBSTATIONS, "Number of substations"),
        (VID_ENERGY_LOW, "Energy delivered, low voltage", "MWh"),
        (VID_ENERGY_HIGH, "Energy delivered, high voltage", "MWh"),
        (VID_PMAX, "Maximum power from upstream network", "MW"),
    ]
    for item in m5_inputs:
        vid, desc = item[0], item[1]
        unit = item[2] if len(item) > 2 else ""
        g[vid] = GlossaryEntry(vid, desc, "m5", "input_var", unit)

    # --- M5 Output variables ---
    m5_outputs = [
        (VID_EFFICIENCY_SCORE, "Efficiency score"),
        (VID_SUPER_EFFICIENCY, "Super-efficiency score"),
        (VID_EFFICIENCY_POTENTIAL, "Efficiency potential"),
        (VID_APPLIED_POTENTIAL, "Applied efficiency potential"),
        (VID_OPEX_EFF_ADJUSTMENT, "OPEX efficiency adjustment", "kr"),
        (VID_CAPEX_EFF_ADJUSTMENT, "CAPEX efficiency adjustment", "kr"),
        (VID_OPEX_AFTER_EFF, "OPEX after efficiency adjustment", "kr"),
        (VID_CAPEX_AFTER_EFF, "CAPEX after efficiency adjustment", "kr"),
    ]
    for item in m5_outputs:
        vid, desc = item[0], item[1]
        unit = item[2] if len(item) > 2 else ""
        g[vid] = GlossaryEntry(vid, desc, "m5", "output_var", unit)

    return g


GLOSSARY: Dict[str, GlossaryEntry] = _build_glossary()


# =============================================================================
# LOOKUP HELPERS
# =============================================================================

def get_entry(id: str) -> Optional[GlossaryEntry]:
    """Look up a glossary entry by ID. Returns None if not found."""
    return GLOSSARY.get(id)


def get_description(id: str) -> str:
    """Get description for an ID. Returns the ID itself if not found."""
    entry = GLOSSARY.get(id)
    return entry.description if entry else id


def get_ids_by_module(module: str) -> List[str]:
    """Get all IDs belonging to a module (e.g., 'm1', 'm3')."""
    return [e.id for e in GLOSSARY.values() if e.module == module]


def get_ids_by_kind(kind: str) -> List[str]:
    """Get all IDs of a given kind ('parameter', 'input_var', 'output_var')."""
    return [e.id for e in GLOSSARY.values() if e.kind == kind]

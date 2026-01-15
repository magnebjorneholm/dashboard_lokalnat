"""
Module Registry for Regumetrica.

Defines the structure and metadata for all regulatory modules
according to the Regumetrica User Manual.

Used by:
- 0_case_definition.py for module selection display
- 1_case_config.py for conditional rendering
- case_storage.py for inferring selected modules from saved cases
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Set, Dict, Any


@dataclass(frozen=True)
class ModuleParameter:
    """A parameter within a module."""
    param_id: str
    label: str
    description: str = ""


@dataclass(frozen=True)
class ModuleVariable:
    """A variable within a module."""
    var_id: str
    label: str
    description: str = ""


@dataclass(frozen=True)
class ModuleDefinition:
    """Complete definition of a regulatory module."""
    key: str
    title: str
    description: str
    parameters: Tuple[ModuleParameter, ...]
    variables: Tuple[ModuleVariable, ...]
    ui_config_keys: Tuple[str, ...]
    is_addon: bool = False


# =============================================================================
# MODULE DEFINITIONS (User Manual order)
# =============================================================================

M1_ASSET_BASE = ModuleDefinition(
    key="m1",
    title="1. Regulatory asset base valuation",
    description="Asset valuation using norm values or KENT upload",
    parameters=(
        ModuleParameter("1.1.1", "General scaling factor", 
                       "Multiplicative factor applied to all asset norm values"),
        ModuleParameter("1.2.X", "Asset type scaling factors", 
                       "Category-specific scaling factors (17 categories)"),
    ),
    variables=(
        ModuleVariable("10.X", "Asset quantities", 
                      "Asset quantities by type (17 categories)"),
        ModuleVariable("KENT", "KENT file upload", 
                      "Upload KENT Excel template to override asset data"),
    ),
    ui_config_keys=("m1_asset_base",),
)

M2_DEPRECIATION = ModuleDefinition(
    key="m2",
    title="2. Depreciation",
    description="Asset lifetimes for depreciation calculation",
    parameters=(
        ModuleParameter("2.X.1", "Ordinary lifetimes", 
                       "Economic lifetime for assets not yet fully depreciated (17 categories)"),
        ModuleParameter("2.X.2", "Tail lifetimes", 
                       "Lifetime for assets beyond ordinary economic life (17 categories)"),
    ),
    variables=(),
    ui_config_keys=("m2_depreciation",),
)

M3_COST_OF_CAPITAL = ModuleDefinition(
    key="m3",
    title="3. Cost of capital",
    description="WACC and quality/incentive adjustments",
    parameters=(
        ModuleParameter("3.1", "Base WACC parameters", 
                       "Debt ratio, asset beta, risk-free rate, market risk premium, etc."),
        ModuleParameter("3.2", "Derived WACC", 
                       "Real WACC before tax (endogenously determined)"),
        ModuleParameter("3.3", "Overall adjustment cap", 
                       "Maximum total adjustment as share of WACC"),
        ModuleParameter("3.4", "Network loss parameters", 
                       "Loss incentive scaling, sharing factor, average cost"),
        ModuleParameter("3.5", "Utilization rate parameters", 
                       "Utilization rate incentive scaling"),
        ModuleParameter("3.6", "Interruption parameters", 
                       "CPI factors, CEMI4 correction, ILE/ILEffekt costs"),
    ),
    variables=(
        ModuleVariable("30.2", "Network loss adjustment", 
                      "Norm level, observed level, energy input"),
        ModuleVariable("30.3", "Utilization rate adjustment", 
                      "Norm level, observed level, upstream network cost"),
        ModuleVariable("30.4", "Interruption adjustment", 
                      "CEMI4, AME, AIT, AIF per customer type"),
    ),
    ui_config_keys=("m3_cost_of_capital", "m3_quality_adjustments", "m3_incentive_variables"),
)

M4_OPERATING_EXP = ModuleDefinition(
    key="m4",
    title="4. Operating expenditures",
    description="OPEX scaling and adjustable cost method",
    parameters=(
        ModuleParameter("4.1.1", "Scaling factor adjustable OPEX", 
                       "Applied to OPEX subject to efficiency requirements"),
        ModuleParameter("4.1.2", "Scaling factor flexibility services", 
                       "Applied to flexibility service costs"),
        ModuleParameter("4.1.3", "Scaling factor non-adjustable OPEX", 
                       "Applied to costs outside operator's direct control"),
    ),
    variables=(
        ModuleVariable("40.1", "Adjustable OPEX", 
                      "OPEXp and flexibility service cost"),
        ModuleVariable("40.2", "Non-adjustable OPEX", 
                      "Total non-adjustable costs (prognosis)"),
    ),
    ui_config_keys=("m4_operating_exp",),
)

M5_EFFICIENCY = ModuleDefinition(
    key="m5",
    title="5. Efficiency incentive",
    description="DEA efficiency requirements and bounds",
    parameters=(
        ModuleParameter("5.1", "Outlier identification", 
                       "Outlier threshold (IQRs above Q3)"),
        ModuleParameter("5.2", "Efficiency requirement conversion", 
                       "Maximum potential cap, realization time, customer sharing"),
        ModuleParameter("5.3", "Efficiency requirement bounds", 
                       "Minimum annual efficiency requirement"),
        ModuleParameter("5.4", "Cost base application", 
                       "Apply efficiency requirement on TOTEX or OPEX only"),
    ),
    variables=(),
    ui_config_keys=("m5_efficiency",),
)

M7_BENCHMARKING = ModuleDefinition(
    key="m7",
    title="7. Benchmarking module",
    description="Custom DEA specification",
    parameters=(
        ModuleParameter("DEA", "DEA model specification", 
                       "Input/output selection, RTS assumption, outlier detection"),
    ),
    variables=(),
    ui_config_keys=("addon_benchmarking",),
    is_addon=True,
)


# =============================================================================
# REGISTRY
# =============================================================================

# Ordered list of all modules (User Manual order)
ALL_MODULES: Tuple[ModuleDefinition, ...] = (
    M1_ASSET_BASE,
    M2_DEPRECIATION,
    M3_COST_OF_CAPITAL,
    M4_OPERATING_EXP,
    M5_EFFICIENCY,
    M7_BENCHMARKING,
)

# Base modules only (exclude add-ons)
BASE_MODULES: Tuple[ModuleDefinition, ...] = tuple(
    m for m in ALL_MODULES if not m.is_addon
)

# Add-on modules only
ADDON_MODULES: Tuple[ModuleDefinition, ...] = tuple(
    m for m in ALL_MODULES if m.is_addon
)

# Lookup by key
MODULE_BY_KEY: Dict[str, ModuleDefinition] = {m.key: m for m in ALL_MODULES}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_module(key: str) -> ModuleDefinition:
    """Get module definition by key."""
    if key not in MODULE_BY_KEY:
        raise KeyError(f"Unknown module key: {key}")
    return MODULE_BY_KEY[key]


def get_all_ui_config_keys() -> Set[str]:
    """Get set of all ui_config keys across all modules."""
    keys = set()
    for module in ALL_MODULES:
        keys.update(module.ui_config_keys)
    return keys


def infer_selected_modules(ui_config: Dict[str, Any]) -> Set[str]:
    """
    Infer which modules have modifications based on ui_config.
    
    Used when loading a saved case to determine which modules
    should be pre-selected in Case Definition.
    
    Args:
        ui_config: The saved ui_config dict
        
    Returns:
        Set of module keys that have non-default values
    """
    selected = set()
    
    # Module 1: Asset base
    m1 = ui_config.get("m1_asset_base", {})
    if any([
        m1.get("general_scaling") is not None,
        m1.get("cat_scaling"),
        m1.get("var_scaling"),
        m1.get("kent_file_bytes"),
    ]):
        selected.add("m1")
    
    # Module 2: Depreciation
    m2 = ui_config.get("m2_depreciation", {})
    if m2.get("lifetime_adjustments"):
        selected.add("m2")
    
    # Module 3: Cost of capital
    m3 = ui_config.get("m3_cost_of_capital", {})
    m3q = ui_config.get("m3_quality_adjustments", {})
    m3v = ui_config.get("m3_incentive_variables", {})
    
    if any([
        m3.get("wacc_override") is not None,
        m3q.get("kpi"),
        m3q.get("k_nf"),
        m3q.get("sharing_netloss") is not None,
        m3q.get("adj_max_agg") is not None,
        m3q.get("adj_max_cemi4") is not None,
        not m3q.get("enable_quality", True),
        not m3q.get("enable_netloss", True),
        not m3q.get("enable_load", True),
        any(v is not None for v in m3v.values()),
    ]):
        selected.add("m3")
    
    # Module 4: Operating expenditures
    m4 = ui_config.get("m4_operating_exp", {})
    if m4.get("paverkbara_method") != "OPEX":
        selected.add("m4")
    
    # Module 5: Efficiency
    m5 = ui_config.get("m5_efficiency", {})
    if any([
        m5.get("trunkering_max") is not None,
        m5.get("trunkering_min") is not None,
        m5.get("outlier_krav") is not None,
        m5.get("kunddelning") is not None,
        m5.get("realiseringstid") is not None,
    ]):
        selected.add("m5")
    
    # Module 7: Benchmarking
    m7 = ui_config.get("addon_benchmarking", {})
    if m7.get("dea_method") == "custom":
        selected.add("m7")
    
    return selected


def module_has_variables(key: str) -> bool:
    """Check if a module has variables (company-specific data)."""
    module = get_module(key)
    return len(module.variables) > 0
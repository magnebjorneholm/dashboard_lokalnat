"""
Module Registry for Regumetrica.

Defines the structure and metadata for all regulatory modules
according to the Regumetrica User Manual.

Supports section-level granularity for modules with multiple
distinct configuration areas (e.g., M3 with WACC, incentive params, variables).

Used by:
- 1_case_setup.py for module/section selection display
- 2_specification.py for conditional rendering
- state_manager.py for filtering config by selection
- case_storage.py for inferring selected sections from saved cases
"""

from dataclasses import dataclass
from typing import Tuple, Set, Dict, Any, Optional

from config.glossary import (
    PID_GENERAL_SCALING, PID_DEBT_RATIO, PID_WACC_REAL,
    PID_MAX_TOTAL_ADJUSTMENT, PID_LOSS_SCALING, PID_UTIL_SCALING,
    PID_INTER_COST_SCALING, PID_OPEX_SCALING, PID_FLEX_SCALING,
    PID_NON_ADJ_SCALING, PID_OUTLIER_THRESHOLD, PID_MAX_POTENTIAL_CAP,
    PID_MIN_ANNUAL_REQ, PID_COST_BASE,
    VID_NF_NORM, VID_UG_NORM, VID_CEMI4_NORM,
    VID_OPEX_ADJUSTABLE, VID_NON_ADJUSTABLE,
    get_description,
)


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
class ModuleSection:
    """
    A configurable section within a module.
    
    Sections allow fine-grained control over which parts of a module
    are rendered and applied.
    """
    key: str                        # e.g., "wacc", "incentive_params"
    label: str                      # Display label for checkbox
    ui_config_keys: Tuple[str, ...]  # Keys in DEFAULT_UI_CONFIG
    default_enabled: bool = True
    help_text: str = ""             # Tooltip text (User Manual reference)


@dataclass(frozen=True)
class ModuleDefinition:
    """
    Complete definition of a regulatory module.
    
    Modules can have optional sections for fine-grained selection.
    If sections is empty, the entire module is treated as one unit.
    """
    key: str
    title: str
    description: str
    parameters: Tuple[ModuleParameter, ...]
    variables: Tuple[ModuleVariable, ...]
    sections: Tuple[ModuleSection, ...] = ()
    is_addon: bool = False
    _ui_config_keys: Tuple[str, ...] = ()
    
    @property
    def ui_config_keys(self) -> Tuple[str, ...]:
        """Get all ui_config keys for this module."""
        if self.sections:
            return tuple(k for s in self.sections for k in s.ui_config_keys)
        return self._ui_config_keys
    
    @property
    def has_sections(self) -> bool:
        """Check if module has configurable sections."""
        return len(self.sections) > 0
    
    def get_section(self, section_key: str) -> Optional[ModuleSection]:
        """Get a section by key."""
        for section in self.sections:
            if section.key == section_key:
                return section
        return None


# =============================================================================
# MODULE DEFINITIONS (User Manual order)
# =============================================================================

M1_ASSET_BASE = ModuleDefinition(
    key="m1",
    title="1. Regulatory asset base valuation",
    description="Asset valuation using norm values or KENT upload",
    parameters=(
        ModuleParameter(PID_GENERAL_SCALING, get_description(PID_GENERAL_SCALING),
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
    sections=(
        ModuleSection(
            key="scaling",
            label="1.1-1.2 General and norm value scaling factors",
            ui_config_keys=("m1_asset_base",),
            default_enabled=True,
            help_text="Parameters 1.1.1 (general), 1.2.X (per category). Affects all companies.",
        ),
        ModuleSection(
            key="quantities",
            label="10.X Asset quantity adjustments",
            ui_config_keys=("m1_asset_base",),
            default_enabled=False,
            help_text="Variable 10.X. Adjust quantities per asset category for your company.",
        ),
        ModuleSection(
            key="kent",
            label="KENT file upload (overrides quantity adjustments)",
            ui_config_keys=("m1_asset_base",),
            default_enabled=False,
            help_text="Upload KENT Excel template. Overrides manual quantity adjustments.",
        ),
    ),
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
    sections=(
        ModuleSection(
            key="lifetimes",
            label="2.X Economic and tail lifetime parameters",
            ui_config_keys=("m2_depreciation",),
            default_enabled=True,
            help_text="Parameters 2.X.1 (ordinary) and 2.X.2 (tail) per asset category.",
        ),
    ),
)

M3_COST_OF_CAPITAL = ModuleDefinition(
    key="m3",
    title="3. Cost of capital",
    description="WACC and quality/incentive adjustments",
    parameters=(
        ModuleParameter(f"{PID_DEBT_RATIO}-3.1.7", "Base WACC parameters",
                       "Debt ratio, asset beta, risk-free rate, market risk premium, etc."),
        ModuleParameter(f"3.2.1-{PID_WACC_REAL}", "Derived WACC",
                       "Real WACC before tax (endogenously determined)"),
        ModuleParameter(PID_MAX_TOTAL_ADJUSTMENT, get_description(PID_MAX_TOTAL_ADJUSTMENT),
                       "Maximum total adjustment as share of WACC"),
        ModuleParameter(PID_LOSS_SCALING, "Network loss parameters",
                       "Loss incentive scaling, sharing factor, average cost"),
        ModuleParameter(PID_UTIL_SCALING, "Utilization rate parameters",
                       "Utilization rate incentive scaling"),
        ModuleParameter(PID_INTER_COST_SCALING, "Interruption parameters",
                       "CPI factors, CEMI4 correction, ILE/ILEffekt costs"),
    ),
    variables=(
        ModuleVariable(VID_NF_NORM, "Network loss adjustment",
                      "Norm level, observed level, energy input"),
        ModuleVariable(VID_UG_NORM, "Utilization rate adjustment",
                      "Norm level, observed level, upstream network cost"),
        ModuleVariable(VID_CEMI4_NORM, "Interruption adjustment",
                      "CEMI4, AME, AIT, AIF per customer type"),
    ),
    sections=(
        ModuleSection(
            key="wacc",
            label="3.1-3.2 WACC calculation (CAPM parameters)",
            ui_config_keys=("m3_cost_of_capital",),
            default_enabled=True,
            help_text="Risk-free rate, market risk premium, beta, debt ratio, tax rate, inflation.",
        ),
        ModuleSection(
            key="incentive_params",
            label="3.3-3.6 Quality and incentive adjustment parameters",
            ui_config_keys=("m3_quality_adjustments",),
            default_enabled=True,
            help_text="Adjustment caps, network loss sharing, interruption cost parameters.",
        ),
        ModuleSection(
            key="incentive_vars",
            label="30.X Incentive adjustment variables (company-specific)",
            ui_config_keys=("m3_incentive_variables",),
            default_enabled=False,
            help_text="Network loss, utilization, CEMI4 values for your company.",
        ),
    ),
)

M4_OPERATING_EXP = ModuleDefinition(
    key="m4",
    title="4. Operating expenditures",
    description="OPEX scaling and adjustable cost method",
    parameters=(
        ModuleParameter(PID_OPEX_SCALING, get_description(PID_OPEX_SCALING),
                       "Applied to OPEX subject to efficiency requirements"),
        ModuleParameter(PID_FLEX_SCALING, get_description(PID_FLEX_SCALING),
                       "Applied to flexibility service costs"),
        ModuleParameter(PID_NON_ADJ_SCALING, get_description(PID_NON_ADJ_SCALING),
                       "Applied to costs outside operator's direct control"),
    ),
    variables=(
        ModuleVariable(VID_OPEX_ADJUSTABLE, "Adjustable OPEX",
                      "OPEXp and flexibility service cost"),
        ModuleVariable(VID_NON_ADJUSTABLE, "Non-adjustable OPEX",
                      "Total non-adjustable costs (prognosis)"),
    ),
    sections=(
        ModuleSection(
            key="scaling",
            label="4.1 OPEX scaling factors (adjustable, flexibility, non-adjustable)",
            ui_config_keys=("m4_operating_exp",),
            default_enabled=True,
            help_text="Parameters 4.1.1-4.1.3. Scale operating expenditure components.",
        ),
        ModuleSection(
            key="opex_vars",
            label="40.X OPEX variables (company-specific cost data)",
            ui_config_keys=("m4_operating_exp",),
            default_enabled=False,
            help_text="Variables 40.1-40.2. Override OPEX values for your company.",
        ),
    ),
)

M5_EFFICIENCY = ModuleDefinition(
    key="m5",
    title="5. Efficiency incentive",
    description="DEA efficiency requirements and bounds",
    parameters=(
        ModuleParameter(PID_OUTLIER_THRESHOLD, "Outlier identification",
                       "Outlier threshold (IQRs above Q3)"),
        ModuleParameter(PID_MAX_POTENTIAL_CAP, "Efficiency requirement conversion",
                       "Maximum potential cap, realization time, customer sharing"),
        ModuleParameter(PID_MIN_ANNUAL_REQ, "Efficiency requirement bounds",
                       "Minimum annual efficiency requirement"),
        ModuleParameter(PID_COST_BASE, "Cost base application",
                       "Apply efficiency requirement on TOTEX or OPEX only"),
    ),
    variables=(),
    sections=(
        ModuleSection(
            key="efficiency_params",
            label="5.1-5.4 Efficiency requirement parameters (bounds, outliers, cost base)",
            ui_config_keys=("m5_efficiency",),
            default_enabled=True,
            help_text="Truncation bounds, outlier treatment, TOTEX vs OPEX application.",
        ),
    ),
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
    sections=(
        ModuleSection(
            key="dea_spec",
            label="DEA model specification (inputs, outputs, RTS)",
            ui_config_keys=("addon_benchmarking",),
            default_enabled=True,
            help_text="Define custom DEA model with different inputs/outputs than Ei baseline.",
        ),
    ),
    is_addon=True,
)


# =============================================================================
# REGISTRY
# =============================================================================

ALL_MODULES: Tuple[ModuleDefinition, ...] = (
    M1_ASSET_BASE,
    M2_DEPRECIATION,
    M3_COST_OF_CAPITAL,
    M4_OPERATING_EXP,
    M5_EFFICIENCY,
    M7_BENCHMARKING,
)

BASE_MODULES: Tuple[ModuleDefinition, ...] = tuple(
    m for m in ALL_MODULES if not m.is_addon
)

ADDON_MODULES: Tuple[ModuleDefinition, ...] = tuple(
    m for m in ALL_MODULES if m.is_addon
)

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


def parse_selection_key(key: str) -> Tuple[str, Optional[str]]:
    """
    Parse a selection key into module_key and optional section_key.
    
    Examples:
        "m1" -> ("m1", None)
        "m3.wacc" -> ("m3", "wacc")
    """
    if "." in key:
        parts = key.split(".", 1)
        return parts[0], parts[1]
    return key, None


def build_selection_key(module_key: str, section_key: Optional[str] = None) -> str:
    """
    Build a selection key from module and section keys.
    
    Examples:
        ("m1", None) -> "m1"
        ("m3", "wacc") -> "m3.wacc"
    """
    if section_key:
        return f"{module_key}.{section_key}"
    return module_key


def get_default_sections_for_module(module_key: str) -> Set[str]:
    """
    Get default section keys for a module (where default_enabled=True).
    For modules without sections, returns empty set.
    """
    module = get_module(module_key)
    if not module.has_sections:
        return set()
    return {s.key for s in module.sections if s.default_enabled}


def expand_module_to_sections(module_key: str) -> Set[str]:
    """
    Expand a module key to all its section keys.
    
    For modules without sections, returns {module_key}.
    For modules with sections, returns {module_key.section1, ...}.
    """
    module = get_module(module_key)
    if not module.has_sections:
        return {module_key}
    return {build_selection_key(module_key, s.key) for s in module.sections}


def get_ui_config_keys_for_selection(selection_key: str) -> Tuple[str, ...]:
    """
    Get ui_config keys for a selection key.
    
    Args:
        selection_key: "m1" or "m3.wacc"
        
    Returns:
        Tuple of ui_config keys
    """
    module_key, section_key = parse_selection_key(selection_key)
    module = get_module(module_key)
    
    if section_key:
        section = module.get_section(section_key)
        if section:
            return section.ui_config_keys
        return ()
    
    return module.ui_config_keys


def infer_selected_from_ui_config(ui_config: Dict[str, Any]) -> Set[str]:
    """
    Infer selected modules/sections from ui_config values.
    
    Used when loading saved cases to determine pre-selection.
    Returns selection keys (e.g., {"m1.scaling", "m3.wacc", "m3.incentive_params"}).
    """
    selected = set()
    
    # Module 1: Asset base (3 sections)
    m1 = ui_config.get("m1_asset_base", {})
    if any([m1.get("general_scaling") is not None, m1.get("cat_scaling")]):
        selected.add("m1.scaling")
    if m1.get("var_scaling"):
        selected.add("m1.quantities")
    if m1.get("kent_file_bytes"):
        selected.add("m1.kent")
    
    # Module 2: Depreciation (1 section)
    m2 = ui_config.get("m2_depreciation", {})
    if m2.get("lifetime_adjustments"):
        selected.add("m2.lifetimes")
    
    # Module 3: Cost of capital (3 sections)
    m3_wacc = ui_config.get("m3_cost_of_capital", {})
    if m3_wacc.get("wacc_override") is not None:
        selected.add("m3.wacc")
    
    m3_qual = ui_config.get("m3_quality_adjustments", {})
    if any([
        m3_qual.get("kpi"),
        m3_qual.get("k_nf"),
        m3_qual.get("sharing_netloss") is not None,
        m3_qual.get("adj_max_agg") is not None,
        m3_qual.get("adj_max_cemi4") is not None,
        not m3_qual.get("enable_quality", True),
        not m3_qual.get("enable_netloss", True),
        not m3_qual.get("enable_load", True),
    ]):
        selected.add("m3.incentive_params")
    
    m3_vars = ui_config.get("m3_incentive_variables", {})
    if any(v is not None for v in m3_vars.values()):
        selected.add("m3.incentive_vars")
    
    # Module 4: Operating expenditures (2 sections)
    m4 = ui_config.get("m4_operating_exp", {})
    if any([
        m4.get("opex_scaling") is not None,
        m4.get("flex_scaling") is not None,
        m4.get("non_adj_scaling") is not None,
    ]):
        selected.add("m4.scaling")
    if any([
        m4.get("opex_override") is not None,
        m4.get("flex_override") is not None,
        m4.get("non_controllable_override") is not None,
    ]):
        selected.add("m4.opex_vars")
    
    # Module 5: Efficiency (1 section)
    m5 = ui_config.get("m5_efficiency", {})
    if any([
        m5.get("trunkering_max") is not None,
        m5.get("trunkering_min") is not None,
        m5.get("efficiency_override") is not None,
    ]):
        selected.add("m5.efficiency_params")
    
    # Module 7: Benchmarking (1 section)
    m7 = ui_config.get("addon_benchmarking", {})
    if m7.get("dea_method") == "custom":
        selected.add("m7.dea_spec")
    
    return selected


def module_has_variables(key: str) -> bool:
    """Check if a module has variables (company-specific data)."""
    module = get_module(key)
    return len(module.variables) > 0


def get_selected_module_keys(selected: Set[str]) -> Set[str]:
    """
    Extract unique module keys from selection set.
    
    {"m1", "m3.wacc", "m3.incentive_params"} -> {"m1", "m3"}
    """
    module_keys = set()
    for key in selected:
        module_key, _ = parse_selection_key(key)
        module_keys.add(module_key)
    return module_keys


def is_any_section_selected(module_key: str, selected: Set[str]) -> bool:
    """Check if any section of a module is selected."""
    module = get_module(module_key)
    
    if not module.has_sections:
        return module_key in selected
    
    for section in module.sections:
        if build_selection_key(module_key, section.key) in selected:
            return True
    return False
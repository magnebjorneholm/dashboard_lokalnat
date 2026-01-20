"""Common components for Regumetrica UI."""

from .module_registry import (
    # Dataclasses
    ModuleParameter,
    ModuleVariable,
    ModuleSection,
    ModuleDefinition,
    # Module definitions
    M1_ASSET_BASE,
    M2_DEPRECIATION,
    M3_COST_OF_CAPITAL,
    M4_OPERATING_EXP,
    M5_EFFICIENCY,
    M7_BENCHMARKING,
    # Collections
    ALL_MODULES,
    BASE_MODULES,
    ADDON_MODULES,
    MODULE_BY_KEY,
    # Functions
    get_module,
    get_all_ui_config_keys,
    parse_selection_key,
    build_selection_key,
    get_default_sections_for_module,
    expand_module_to_sections,
    get_ui_config_keys_for_selection,
    infer_selected_from_ui_config,
    module_has_variables,
    get_selected_module_keys,
    is_any_section_selected,
)

__all__ = [
    # Dataclasses
    "ModuleParameter",
    "ModuleVariable",
    "ModuleSection",
    "ModuleDefinition",
    # Module definitions
    "M1_ASSET_BASE",
    "M2_DEPRECIATION",
    "M3_COST_OF_CAPITAL",
    "M4_OPERATING_EXP",
    "M5_EFFICIENCY",
    "M7_BENCHMARKING",
    # Collections
    "ALL_MODULES",
    "BASE_MODULES",
    "ADDON_MODULES",
    "MODULE_BY_KEY",
    # Functions
    "get_module",
    "get_all_ui_config_keys",
    "parse_selection_key",
    "build_selection_key",
    "get_default_sections_for_module",
    "expand_module_to_sections",
    "get_ui_config_keys_for_selection",
    "infer_selected_from_ui_config",
    "module_has_variables",
    "get_selected_module_keys",
    "is_any_section_selected",
]
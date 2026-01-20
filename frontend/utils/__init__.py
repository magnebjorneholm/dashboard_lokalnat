"""Utils package for Regumetrica UI."""

from .state_manager import (
    init_session_state,
    reset_case,
    get_module_config,
    set_module_config,
    get_user_reid,
    set_user_reid,
    get_user_id_network,
    get_case_name,
    set_case_name,
    get_case_notes,
    set_case_notes,
    get_case_id,
    set_case_id,
    mark_case_saved,
    is_case_saved,
    get_default_case_name,
    increment_saved_cases_count,
    set_saved_cases_count,
    get_selected_modules,
    set_selected_modules,
    is_module_selected,
    is_section_selected,
    is_selection_key_selected,
    get_filtered_ui_config,
    is_authenticated,
    get_auth_role,
    get_auth_reid,
    get_auth_email,
    is_regulator,
    DEFAULT_UI_CONFIG,
)

from .config_adapter import (
    build_case_definition,
    get_changed_parameters,
    get_baseline_value,
    PARAM_TO_CONFIG,
    DEA_INPUT_OPTIONS,
    DEA_OUTPUT_OPTIONS,
)

from .export_excel import (
    create_case_export,
    get_export_filename,
)

from .export_button import (
    render_export_button,
)

__all__ = [
    # State management
    "init_session_state",
    "reset_case",
    "get_module_config",
    "set_module_config",
    "get_user_reid",
    "set_user_reid",
    "get_user_id_network",
    "get_case_name",
    "set_case_name",
    "get_case_notes",
    "set_case_notes",
    "get_case_id",
    "set_case_id",
    "mark_case_saved",
    "is_case_saved",
    "get_default_case_name",
    "increment_saved_cases_count",
    "set_saved_cases_count",
    "get_selected_modules",
    "set_selected_modules",
    "is_module_selected",
    "is_section_selected",
    "is_selection_key_selected",
    "get_filtered_ui_config",
    "is_authenticated",
    "get_auth_role",
    "get_auth_reid",
    "get_auth_email",
    "is_regulator",
    "DEFAULT_UI_CONFIG",
    # Config adapter
    "build_case_definition",
    "get_changed_parameters",
    "get_baseline_value",
    "PARAM_TO_CONFIG",
    "DEA_INPUT_OPTIONS",
    "DEA_OUTPUT_OPTIONS",
    # Export
    "create_case_export",
    "get_export_filename",
    "render_export_button",
]
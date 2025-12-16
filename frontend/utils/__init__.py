"""Utils package för Regumetrica UI."""

from .state_manager import (
    init_session_state,
    reset_case,
    get_module_config,
    set_module_config,
    get_user_reid,
    set_user_reid,
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
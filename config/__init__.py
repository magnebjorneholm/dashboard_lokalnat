"""
config module

Configuration structures and utilities for Regumetrica pipeline.
"""

from .case_definition import (
    CaseDefinition,
    PreDeaConfig,
    DeaConfig,
    PostDeaConfig,
    CapexMethod,
    EfficiencyMethod,
    PaverkbaraMethod,
    get_baseline_config,
    create_wacc_scaling_config,
    create_parameter_change_config,
    create_kent_upload_config,
)

__all__ = [
    'CaseDefinition',
    'PreDeaConfig',
    'DeaConfig',
    'PostDeaConfig',
    'CapexMethod',
    'EfficiencyMethod',
    'PaverkbaraMethod',
    'get_baseline_config',
    'create_wacc_scaling_config',
    'create_parameter_change_config',
    'create_kent_upload_config'
]
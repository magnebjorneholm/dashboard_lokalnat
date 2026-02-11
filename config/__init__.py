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
    ControllableMethod,
    get_baseline_config,
)

__all__ = [
    'CaseDefinition',
    'PreDeaConfig',
    'DeaConfig',
    'PostDeaConfig',
    'CapexMethod',
    'EfficiencyMethod',
    'ControllableMethod',
    'get_baseline_config',
]
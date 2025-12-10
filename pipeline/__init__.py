"""
pipeline module

Pipeline execution and orchestration.
"""

from .core import (
    PipelineResult,
    run_pipeline,
    validate_pipeline_result
)

__all__ = [
    'PipelineResult',
    'run_pipeline',
    'validate_pipeline_result'
]
"""
pipeline module

Main pipeline runner and stage definitions.
"""

from .core import (
    PipelineResult,
    run_pipeline,
    validate_pipeline_result,
    get_pipeline_summary
)

from .debug_logger import (
    PipelineDebugLogger,
    create_logger
)

from .stages import (
    BaselineStageOutput,
    PreDeaStageOutput,
    DeaStageOutput,
    ExtractionStageOutput,
    PostDeaStageOutput,
    stage_baseline,
    stage_pre_dea,
    stage_dea,
    stage_extraction,
    stage_post_dea
)

__all__ = [
    # Core
    'PipelineResult',
    'run_pipeline',
    'validate_pipeline_result',
    'get_pipeline_summary',
    
    # Debug logger
    'PipelineDebugLogger',
    'create_logger',
    
    # Stage outputs
    'BaselineStageOutput',
    'PreDeaStageOutput',
    'DeaStageOutput',
    'ExtractionStageOutput',
    'PostDeaStageOutput',
    
    # Stage functions
    'stage_baseline',
    'stage_pre_dea',
    'stage_dea',
    'stage_extraction',
    'stage_post_dea'
]
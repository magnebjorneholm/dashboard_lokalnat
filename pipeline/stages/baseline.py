"""
pipeline/stages/baseline.py

Stage 1: Baseline
Converts BaselineData to BaselineStageOutput.

No print statements - logging handled by PipelineDebugLogger.
"""

import pandas as pd
from data_loaders import BaselineData
from pipeline.stages.stage_outputs import BaselineStageOutput


def stage_baseline(baseline: BaselineData) -> BaselineStageOutput:
    """
    Stage 1: Convert BaselineData to stage output format.
    
    Args:
        baseline: BaselineData from data_loaders
        
    Returns:
        BaselineStageOutput with all baseline data
        
    Raises:
        AttributeError: If BaselineData missing required attributes
    """
    # Validate baseline structure
    if not hasattr(baseline, 'sdf_ir'):
        raise AttributeError(
            "BaselineData missing 'sdf_ir' attribute. "
            "Check that load_baseline_data() returns correct structure."
        )
    
    if not hasattr(baseline, 'sdf_controllable'):
        raise AttributeError(
            "BaselineData missing 'sdf_controllable' attribute. "
            "Check that load_baseline_data() returns correct structure."
        )

    return BaselineStageOutput(
        df_all_companies=baseline.df_all_companies.copy(),
        dea_baseline=baseline.dea_results.copy(),
        reconciliation=baseline.reconciliation.copy(),
        wacc=baseline.wacc,
        sdf_ir=baseline.sdf_ir.copy(),
        sdf_controllable=baseline.sdf_controllable.copy()
    )
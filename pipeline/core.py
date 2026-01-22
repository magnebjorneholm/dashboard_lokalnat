"""
pipeline/core.py

Main pipeline runner.
Orchestrates all stages and returns complete result.

UPDATED: Integrated PipelineDebugLogger for comprehensive debugging.
Old print statements replaced with structured logging.
"""

from dataclasses import dataclass
from typing import Optional

from config.case_definition import CaseDefinition
from data_loaders.baseline_data import BaselineData
from pipeline.stages.stage_outputs import (
    BaselineStageOutput,
    PreDeaStageOutput,
    DeaStageOutput,
    ExtractionStageOutput,
    PostDeaStageOutput
)
from pipeline.stages import (
    stage_baseline,
    stage_pre_dea,
    stage_dea,
    stage_extraction,
    stage_post_dea
)
from pipeline.debug_logger import PipelineDebugLogger


@dataclass(frozen=True)
class PipelineResult:
    """Complete pipeline result with outputs from all stages."""
    baseline: BaselineStageOutput
    pre_dea: PreDeaStageOutput
    dea: DeaStageOutput
    extraction: ExtractionStageOutput
    post_dea: PostDeaStageOutput
    
    case_name: str
    user_reid: str


def run_pipeline(
    baseline_data: BaselineData,
    case_config: CaseDefinition,
    debug: bool = True,
    validate: bool = True
) -> PipelineResult:
    """
    Run complete pipeline from start to finish.
    
    Pipeline flow:
    1. Baseline -> Convert BaselineData to stage output
    2. Pre-DEA -> Prepare CAPEX/OPEX (with CapbaseSource + CapexMethod)
    3. DEA -> Run efficiency analysis
    4. Extraction -> Extract results for user's company
    5. Post-DEA -> Calculate efficiency requirements and revenue frame
    
    Args:
        baseline_data: Baseline data (immutable)
        case_config: Case definition with all settings
        debug: If True, print debug output (default True)
        validate: If True, validate results (raises on error)
        
    Returns:
        PipelineResult with all stage outputs
        
    Raises:
        ValueError: If invalid configuration or validation fails
        RuntimeError: If stage execution fails
    """
    
    user_reid = case_config.user_reid
    
    # Validate REId format
    if not user_reid.startswith('REL'):
        raise ValueError(f"Invalid user_reid format: {user_reid} (must start with 'REL')")
    
    # Get user_id_network for Pre-DEA
    user_id_network = _reid_to_id_network(user_reid)
    
    # Initialize logger
    logger = PipelineDebugLogger(case_config, user_reid)
    
    if debug:
        logger.log_config()
    
    # =========================================================================
    # Stage 1: Baseline
    # =========================================================================
    baseline_output = stage_baseline(baseline_data)
    
    # Validate REId exists
    if user_reid not in baseline_output.df_all_companies['REId'].values:
        raise ValueError(f"user_reid {user_reid} not found in baseline data")
    
    if debug:
        logger.log_baseline(baseline_output)
    
    # =========================================================================
    # Stage 2: Pre-DEA
    # =========================================================================
    pre_dea_output = stage_pre_dea(
        baseline_output, 
        case_config.pre_dea,
        user_id_network
    )
    
    if debug:
        logger.log_pre_dea(pre_dea_output, baseline_output)
    
    # =========================================================================
    # Stage 3: DEA
    # =========================================================================
    dea_output = stage_dea(
        pre_dea_output,
        case_config.dea,
        baseline_output
    )
    
    if debug:
        logger.log_dea(dea_output, baseline_output)
    
    # =========================================================================
    # Stage 4: Extraction
    # =========================================================================
    extraction_output = stage_extraction(
        pre_dea_output,
        dea_output,
        user_reid
    )
    
    if debug:
        logger.log_extraction(extraction_output)
    
    # =========================================================================
    # Stage 5: Post-DEA
    # =========================================================================
    post_dea_output = stage_post_dea(
        dea=dea_output,
        pre_dea=pre_dea_output,
        baseline=baseline_output,
        config=case_config.post_dea,
        user_reid=user_reid
    )
    
    if debug:
        logger.log_post_dea(post_dea_output)
    
    # =========================================================================
    # Final report and validation
    # =========================================================================
    if debug:
        logger.print_report()
    
    if validate:
        logger.validate()
    
    return PipelineResult(
        baseline=baseline_output,
        pre_dea=pre_dea_output,
        dea=dea_output,
        extraction=extraction_output,
        post_dea=post_dea_output,
        case_name=case_config.name,
        user_reid=user_reid
    )


def _reid_to_id_network(reid: str) -> int:
    """
    Convert REId to id_network.
    Ex: "REL00886" -> 886
    """
    try:
        numeric_part = reid.replace("REL", "").lstrip("0")
        if not numeric_part:
            return 0
        return int(numeric_part)
    except (ValueError, AttributeError):
        raise ValueError(f"Could not convert REId to id_network: {reid}")


def validate_pipeline_result(result: PipelineResult) -> bool:
    """
    Validate that pipeline result is complete and consistent.
    
    Args:
        result: PipelineResult to validate
        
    Returns:
        True if valid, otherwise raises exception
    """
    errors = []
    
    # Check all stages have data
    if result.baseline is None:
        errors.append("baseline is None")
    if result.pre_dea is None:
        errors.append("pre_dea is None")
    if result.dea is None:
        errors.append("dea is None")
    if result.extraction is None:
        errors.append("extraction is None")
    if result.post_dea is None:
        errors.append("post_dea is None")
    
    # Check consistency
    if result.pre_dea and result.baseline:
        n_baseline = len(result.baseline.df_all_companies)
        n_pre_dea = len(result.pre_dea.df_all_companies)
        if n_baseline != n_pre_dea:
            errors.append(f"Inconsistent company count: baseline={n_baseline}, pre_dea={n_pre_dea}")
    
    if result.extraction:
        if result.extraction.user_reid != result.user_reid:
            errors.append(f"Inconsistent REId: result={result.user_reid}, extraction={result.extraction.user_reid}")
    
    if errors:
        raise ValueError(f"Pipeline validation failed: {', '.join(errors)}")
    
    return True


def get_pipeline_summary(result: PipelineResult) -> dict:
    """
    Generate pipeline result summary for UI/logging.
    
    Args:
        result: PipelineResult
        
    Returns:
        Dict with summary
    """
    return {
        "case_name": result.case_name,
        "user_reid": result.user_reid,
        "pre_dea": {
            "capbase_source": result.pre_dea.capbase_source,
            "capex_method": result.pre_dea.capex_method,
            "capex_modified": result.pre_dea.capex_modified,
            "wacc_used": result.pre_dea.wacc_used,
        },
        "dea": {
            "method": result.dea.dea_method,
            "executed": result.dea.dea_executed,
        },
        "extraction": {
            "efficiency": result.extraction.efficiency,
            "potential": result.extraction.potential,
            "is_outlier": result.extraction.is_outlier,
            "capex": result.extraction.capex,
            "opex": result.extraction.opex,
        },
        "post_dea": {
            "user_reid": result.post_dea.user_reid,
        }
    }
"""
pipeline/core.py

Main pipeline runner.
Orchestrerar alla stages och returnerar komplett resultat.
"""

from dataclasses import dataclass
from typing import Optional

from config import CaseDefinition
from data_loaders import BaselineData
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


@dataclass(frozen=True)
class PipelineResult:
    """
    Komplett resultat från pipeline.
    Innehåller outputs från alla stages.
    """
    baseline: BaselineStageOutput
    pre_dea: PreDeaStageOutput
    dea: DeaStageOutput
    extraction: ExtractionStageOutput
    post_dea: PostDeaStageOutput
    
    # Metadata
    case_name: str
    user_reid: str  # REId för användarens företag (ex: "REL00001")


def run_pipeline(
    baseline: BaselineData,
    case_config: CaseDefinition
) -> PipelineResult:
    """
    Kör hela pipeline från början till slut.
    
    Pipeline flow:
    1. Baseline → Konvertera BaselineData till stage output
    2. Pre-DEA → Förbereda CAPEX/OPEX (baseline, WACC-scaling, parameter change, KENT)
    3. DEA → Kör effektivitetsanalys (baseline eller ny DEA)
    4. Extraction → Extrahera resultat för användarens företag
    5. Post-DEA → Beräkna effektiviseringskrav och påverkbara kostnader
    
    Args:
        baseline: Baseline data (immutable)
        case_config: Case definition med alla inställningar
        
    Returns:
        PipelineResult med alla outputs från varje stage
        
    Raises:
        ValueError: Om invalid configuration
        RuntimeError: Om stage execution misslyckas
    """
    
    # Validera config - kontrollera att user_reid är giltigt format
    user_reid = case_config.user_reid
    if not user_reid.startswith('REL'):
        raise ValueError(f"Invalid user_reid format: {user_reid} (måste börja med 'REL')")
    
    # Validera att REId finns i baseline
    if user_reid not in baseline.df_all_companies['REId'].values:
        raise ValueError(f"user_reid {user_reid} finns inte i baseline data")
    
    # Stage 1: Baseline
    baseline_output = stage_baseline(baseline)
    
    # Stage 2: Pre-DEA
    pre_dea_output = stage_pre_dea(
        baseline_output, 
        case_config.pre_dea
    )
    
    # Stage 3: DEA
    dea_output = stage_dea(
        pre_dea_output,
        case_config.dea,
        baseline_output  # Behövs för baseline-metod
    )
    
    # Stage 4: Extraction
    extraction_output = stage_extraction(
        pre_dea_output,
        dea_output,
        case_config.user_reid
    )
    
    # Stage 5: Post-DEA
    post_dea_output = stage_post_dea(
        dea=dea_output,
        pre_dea=pre_dea_output,
        baseline=baseline_output,
        config=case_config.post_dea,
        user_reid=case_config.user_reid
    )

    
    return PipelineResult(
        baseline=baseline_output,
        pre_dea=pre_dea_output,
        dea=dea_output,
        extraction=extraction_output,
        post_dea=post_dea_output,
        case_name=case_config.name,
        user_reid=case_config.user_reid
    )


def validate_pipeline_result(result: PipelineResult) -> bool:
    """
    Validera att pipeline result är komplett och konsekvent.
    
    Args:
        result: PipelineResult att validera
        
    Returns:
        True om valid
        
    Raises:
        ValueError: Om validation misslyckas
    """
    
    # Testa att alla stages har output
    if result.baseline is None:
        raise ValueError("Baseline output saknas")
    if result.pre_dea is None:
        raise ValueError("Pre-DEA output saknas")
    if result.dea is None:
        raise ValueError("DEA output saknas")
    if result.extraction is None:
        raise ValueError("Extraction output saknas")
    if result.post_dea is None:
        raise ValueError("Post-DEA output saknas")
    
    # Testa att user_reid är konsekvent
    if result.extraction.user_reid != result.user_reid:
        raise ValueError(
            f"Inconsistent user_reid: extraction={result.extraction.user_reid}, "
            f"result={result.user_reid}"
        )
    
    if result.post_dea.user_reid != result.user_reid:
        raise ValueError(
            f"Inconsistent user_reid: post_dea={result.post_dea.user_reid}, "
            f"result={result.user_reid}"
        )
    
    # Testa att DataFrames har rätt antal rader
    n_companies = len(result.baseline.df_all_companies)
    if n_companies < 140:  # Allow some tolerance
        raise ValueError(f"För få företag: {n_companies} (förväntar ~148)")
    
    n_pre_dea = len(result.pre_dea.df_all_companies)
    if n_pre_dea != n_companies:
        raise ValueError(
            f"Pre-DEA har {n_pre_dea} företag men baseline har {n_companies}"
        )
    
    n_dea = len(result.dea.dea_results)
    if n_dea != n_companies:
        raise ValueError(
            f"DEA har {n_dea} företag men baseline har {n_companies}"
        )
    
    return True
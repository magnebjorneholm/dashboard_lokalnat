"""
pipeline/core.py

Main pipeline runner.
Orchestrerar alla stages och returnerar komplett resultat.

REFAKTORISERAD: Skickar user_id_network till Pre-DEA stage för
korrekt hantering av CapbaseSource.
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
    user_reid: str


def run_pipeline(
    baseline_data: BaselineData,
    case_config: CaseDefinition
) -> PipelineResult:
    """
    Kör hela pipeline från början till slut.
    
    Pipeline flow:
    1. Baseline → Konvertera BaselineData till stage output
    2. Pre-DEA → Förbered CAPEX/OPEX (med CapbaseSource + CapexMethod)
    3. DEA → Kör effektivitetsanalys
    4. Extraction → Extrahera resultat för användarens företag
    5. Post-DEA → Beräkna effektiviseringskrav och intäktsram
    
    Args:
        baseline_data: Baseline data (immutable)
        case_config: Case definition med alla inställningar
        
    Returns:
        PipelineResult med alla outputs från varje stage
        
    Raises:
        ValueError: Om invalid configuration
        RuntimeError: Om stage execution misslyckas
    """
    
    user_reid = case_config.user_reid
    
    # Validera REId format
    if not user_reid.startswith('REL'):
        raise ValueError(f"Invalid user_reid format: {user_reid} (måste börja med 'REL')")
    
    # Hämta user_id_network för Pre-DEA
    user_id_network = _reid_to_id_network(user_reid)
    
    print(f"\n{'='*60}")
    print(f"Pipeline: {case_config.name}")
    print(f"Företag: {user_reid} (id_network: {user_id_network})")
    print(f"{'='*60}")
    
    # Stage 1: Baseline
    print("\n--- Stage 1: Baseline ---")
    baseline_output = stage_baseline(baseline_data)
    
    # Validera att REId finns i baseline
    if user_reid not in baseline_output.df_all_companies['REId'].values:
        raise ValueError(f"user_reid {user_reid} finns inte i baseline data")
    
    # Stage 2: Pre-DEA
    print("\n--- Stage 2: Pre-DEA ---")
    pre_dea_output = stage_pre_dea(
        baseline_output, 
        case_config.pre_dea,
        user_id_network  # Skicka med för CapbaseSource-hantering
    )
    
    # Stage 3: DEA
    print("\n--- Stage 3: DEA ---")
    dea_output = stage_dea(
        pre_dea_output,
        case_config.dea,
        baseline_output
    )
    
    # Stage 4: Extraction
    print("\n--- Stage 4: Extraction ---")
    extraction_output = stage_extraction(
        pre_dea_output,
        dea_output,
        user_reid
    )
    
    # Stage 5: Post-DEA
    print("\n--- Stage 5: Post-DEA ---")
    post_dea_output = stage_post_dea(
        dea=dea_output,
        pre_dea=pre_dea_output,
        baseline=baseline_output,
        config=case_config.post_dea,
        user_reid=user_reid
    )
    
    print(f"\n{'='*60}")
    print(f"Pipeline klar: {case_config.name}")
    print(f"{'='*60}\n")
    
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
    Konverterar REId till id_network.
    
    Ex: "REL00886" -> 886
    """
    try:
        numeric_part = reid.replace("REL", "").lstrip("0")
        if not numeric_part:
            return 0
        return int(numeric_part)
    except (ValueError, AttributeError):
        raise ValueError(f"Kunde inte konvertera REId till id_network: {reid}")


def validate_pipeline_result(result: PipelineResult) -> bool:
    """
    Validera att pipeline result är komplett och konsekvent.
    
    Args:
        result: PipelineResult att validera
        
    Returns:
        True om valid, annars raises exception
    """
    errors = []
    
    # Kontrollera att alla stages har data
    if result.baseline is None:
        errors.append("baseline saknas")
    if result.pre_dea is None:
        errors.append("pre_dea saknas")
    if result.dea is None:
        errors.append("dea saknas")
    if result.extraction is None:
        errors.append("extraction saknas")
    if result.post_dea is None:
        errors.append("post_dea saknas")
    
    # Kontrollera konsistens
    if result.pre_dea and result.baseline:
        n_baseline = len(result.baseline.df_all_companies)
        n_pre_dea = len(result.pre_dea.df_all_companies)
        if n_baseline != n_pre_dea:
            errors.append(f"Inkonsistent antal företag: baseline={n_baseline}, pre_dea={n_pre_dea}")
    
    if result.extraction:
        if result.extraction.user_reid != result.user_reid:
            errors.append(f"Inkonsistent REId: result={result.user_reid}, extraction={result.extraction.user_reid}")
    
    if errors:
        raise ValueError(f"Pipeline validation failed: {', '.join(errors)}")
    
    return True


def get_pipeline_summary(result: PipelineResult) -> dict:
    """
    Genererar sammanfattning av pipeline-resultat för UI/logging.
    
    Args:
        result: PipelineResult
        
    Returns:
        Dict med sammanfattning
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
            # Lägg till intäktsram-komponenter vid behov
        }
    }
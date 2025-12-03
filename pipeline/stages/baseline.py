"""
pipeline/stages/baseline.py

Stage 1: Baseline
Konverterar BaselineData till BaselineStageOutput.
"""

import pandas as pd
from data_loaders import BaselineData
from pipeline.stages.stage_outputs import BaselineStageOutput


def stage_baseline(baseline: BaselineData) -> BaselineStageOutput:
    """
    Stage 1: Konvertera BaselineData till stage output format.
    """
    # Validera att baseline har korrekt struktur
    if not hasattr(baseline, 'sdf_ir'):
        raise AttributeError(
            "BaselineData saknar 'sdf_ir' attribut. "
            "Kontrollera att load_baseline_data() returnerar korrekt struktur."
        )
    
    if not hasattr(baseline, 'sdf_paverkbara'):
        raise AttributeError(
            "BaselineData saknar 'sdf_paverkbara' attribut. "
            "Kontrollera att load_baseline_data() returnerar korrekt struktur."
        )
    
    return BaselineStageOutput(
        df_all_companies=baseline.df_all_companies.copy(),
        dea_baseline=baseline.dea_results.copy(),
        reconciliation=baseline.reconciliation.copy(),
        wacc=baseline.wacc,
        sdf_ir=baseline.sdf_ir.copy(),
        sdf_paverkbara=baseline.sdf_paverkbara.copy()
    )
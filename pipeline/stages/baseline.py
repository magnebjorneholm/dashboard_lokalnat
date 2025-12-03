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
    
    Denna stage är enkel - den bara ompaketerar data från BaselineData
    till det format som pipeline förväntar sig.
    
    Args:
        baseline: BaselineData (immutable)
        
    Returns:
        BaselineStageOutput med:
        - df_all_companies: 148 företag med CAPEX, OPEX, volumes
        - dea_baseline: Baseline DEA-resultat från Ei
        - reconciliation: REId/id_network mapping (har även DMU för kompatibilitet)
        - wacc: Baseline WACC (0.0453)
        - sdf_ir: SDF sheet "IR 2024-2027"
        - sdf_paverkbara: SDF sheet "Påverkbara"
    """
    
    return BaselineStageOutput(
        df_all_companies=baseline.df_all_companies.copy(),
        dea_baseline=baseline.dea_results.copy(),
        reconciliation=baseline.reconciliation.copy(),
        wacc=baseline.wacc,
        sdf_ir=baseline.sdf_ir.copy() if hasattr(baseline, 'sdf_ir') else pd.DataFrame(),
        sdf_paverkbara=baseline.sdf_paverkbara.copy() if hasattr(baseline, 'sdf_paverkbara') else pd.DataFrame()
    )
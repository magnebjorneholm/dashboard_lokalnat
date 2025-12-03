"""
pipeline/stages/dea.py

Stage 3: DEA
Kör Data Envelopment Analysis för effektivitetsmätning.

Stöder 2 metoder:
1. baseline - Använd Ei's baseline DEA-resultat
2. dea - Kör ny DEA-modell med custom inputs/outputs
"""

from config import DeaConfig, EfficiencyMethod
from pipeline.stages.stage_outputs import PreDeaStageOutput, DeaStageOutput, BaselineStageOutput
from calculations import run_dea_analysis


def stage_dea(
    pre_dea: PreDeaStageOutput,
    config: DeaConfig,
    baseline: BaselineStageOutput = None
) -> DeaStageOutput:
    """
    Stage 3: Kör DEA-analys.
    
    Args:
        pre_dea: Output från Pre-DEA stage
        config: DeaConfig med metod och parametrar
        baseline: BaselineStageOutput (behövs för baseline-metod)
        
    Returns:
        DeaStageOutput med:
        - dea_results: 148 rows med efficiency, potential, is_outlier
        - dea_method: Metod som användes
        - dea_executed: True om ny DEA kördes
    """
    
    if config.method == EfficiencyMethod.BASELINE:
        # Använd baseline DEA-resultat från Ei
        if baseline is None:
            raise ValueError("Baseline krävs för baseline DEA-metod")
        
        print("\n" + "="*60)
        print("STAGE 3: DEA (Baseline)")
        print("="*60)
        print("✓ Använder Ei's baseline DEA-resultat")
        
        return DeaStageOutput(
            dea_results=baseline.dea_baseline.copy(),
            dea_method="baseline",
            dea_executed=False
        )
    
    elif config.method == EfficiencyMethod.DEA:
        # Kör ny DEA-analys
        print("\n" + "="*60)
        print("STAGE 3: DEA (Custom)")
        print("="*60)
        
        # Extrahera modellspecifikation från config
        model_spec = {
            'inputs': config.inputs,
            'outputs': config.outputs,
            'rts': config.rts,
            'orientation': config.orientation,
            'outlier_params': {
                'q_lower': config.q_lower,
                'q_upper': config.q_upper,
                'multiplier': config.multiplier
            }
        }
        
        # Kör DEA
        dea_results = run_dea_analysis(
            df=pre_dea.df_all_companies,
            model_spec=model_spec
        )
        
        print("="*60 + "\n")
        
        return DeaStageOutput(
            dea_results=dea_results,
            dea_method="dea",
            dea_executed=True
        )
    
    else:
        raise ValueError(f"Okänd DEA-metod: {config.method}")
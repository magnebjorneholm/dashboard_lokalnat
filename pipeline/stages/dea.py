"""
pipeline/stages/dea.py

Stage 3: DEA
Kör Data Envelopment Analysis för effektivitetsmätning.

Stöder 2 metoder:
1. baseline - Använd Ei's baseline DEA-resultat
2. dea - Kör ny DEA-modell med custom inputs/outputs

OBS: Om CAPEX modifierats i Pre-DEA körs alltid ny DEA för metodisk konsistens,
även om användaren valt "baseline". Detta eftersom baseline-DEA beräknades med
ursprunglig CAPEX och inte är giltig för modifierad data.
"""

from config import DeaConfig, EfficiencyMethod
from pipeline.stages.stage_outputs import PreDeaStageOutput, DeaStageOutput, BaselineStageOutput
from calculations import run_dea_analysis

# Baseline DEA-specifikation (matchar Ei's metodik)
BASELINE_DEA_SPEC = {
    'inputs': ['CAPEX', 'OPEXp'],
    'outputs': ['CU', 'MW', 'NS', 'MWhl', 'MWhh'],
    'rts': 'crs',
    'orientation': 'input',
    'outlier_params': {
        'q_lower': 25.0,
        'q_upper': 75.0,
        'multiplier': 2.0
    }
}


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
    
    capex_modified = pre_dea.capex_modified
    
    # =========================================================================
    # SCENARIO 1: Baseline DEA (ingen CAPEX-modifikation)
    # =========================================================================
    if config.method == EfficiencyMethod.BASELINE and not capex_modified:
        
        if baseline is None:
            raise ValueError("Baseline krävs för baseline DEA-metod")
        
        print("\n" + "="*60)
        print("STAGE 3: DEA")
        print(f"  Metod: baseline (Ei's officiella resultat)")
        print("="*60)
        
        print("\n  Steg 1/1: Laddar baseline DEA-resultat...")
        print(f"    Källa: EIs_DEA.xlsx")
        print(f"    Företag: {len(baseline.dea_baseline)}")
        print("    [OK] Använder Ei's baseline DEA-resultat (ingen omberäkning)")
        
        # Statistik
        df = baseline.dea_baseline
        mean_eff = df['Effektivitet'].mean()
        n_efficient = (df['Effektivitet'] >= 1.0).sum()
        n_outliers = df['is_outlier'].sum() if 'is_outlier' in df.columns else 0
        
        print(f"\n  Statistik:")
        print(f"    Medel-effektivitet: {mean_eff:.3f}")
        print(f"    Effektiva (>=100%): {n_efficient} företag")
        print(f"    Outliers: {n_outliers} företag")
        
        print("\n" + "-"*60)
        print("  Resultat: dea_executed=False, dea_method='baseline'")
        print("="*60 + "\n")
        
        return DeaStageOutput(
            dea_results=baseline.dea_baseline.copy(),
            dea_method="baseline",
            dea_executed=False
        )
    
    # =========================================================================
    # SCENARIO 2: Baseline spec med modifierad CAPEX (kör ny DEA)
    # =========================================================================
    elif config.method == EfficiencyMethod.BASELINE and capex_modified:
        
        print("\n" + "="*60)
        print("STAGE 3: DEA")
        print(f"  Metod: baseline_recalculated")
        print(f"  OBS: CAPEX modifierad via '{pre_dea.capex_method}' - kör ny DEA")
        print("="*60)
        
        print("\n  Steg 1/2: Förbereder DEA-input...")
        print(f"    Källa: Pre-DEA output ({len(pre_dea.df_all_companies)} företag)")
        print(f"    CAPEX-metod: {pre_dea.capex_method}")
        if pre_dea.wacc_used:
            print(f"    WACC: {pre_dea.wacc_used:.4f}")
        
        print("\n  Steg 2/2: Kör DEA med baseline-specifikation...")
        print(f"    Inputs: {BASELINE_DEA_SPEC['inputs']}")
        print(f"    Outputs: {BASELINE_DEA_SPEC['outputs']}")
        print(f"    RTS: {BASELINE_DEA_SPEC['rts']}, Orientation: {BASELINE_DEA_SPEC['orientation']}")
        
        dea_results = run_dea_analysis(
            df=pre_dea.df_all_companies,
            model_spec=BASELINE_DEA_SPEC
        )
        
        # Statistik
        mean_eff = dea_results['Effektivitet'].mean()
        n_efficient = (dea_results['Effektivitet'] >= 1.0).sum()
        n_outliers = dea_results['is_outlier'].sum() if 'is_outlier' in dea_results.columns else 0
        
        print(f"\n  Resultat:")
        print(f"    Företag: {len(dea_results)}")
        print(f"    Medel-effektivitet: {mean_eff:.3f}")
        print(f"    Effektiva (>=100%): {n_efficient} företag")
        print(f"    Outliers: {n_outliers} företag")
        
        print("\n" + "-"*60)
        print("  Resultat: dea_executed=True, dea_method='baseline_recalculated'")
        print("="*60 + "\n")
        
        return DeaStageOutput(
            dea_results=dea_results,
            dea_method="baseline_recalculated",
            dea_executed=True
        )
    
    # =========================================================================
    # SCENARIO 3: Custom DEA
    # =========================================================================
    elif config.method == EfficiencyMethod.DEA:
        
        print("\n" + "="*60)
        print("STAGE 3: DEA")
        print(f"  Metod: custom (användardefinierad)")
        print("="*60)
        
        print("\n  Steg 1/2: Förbereder DEA-input...")
        print(f"    Källa: Pre-DEA output ({len(pre_dea.df_all_companies)} företag)")
        
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
        
        print("\n  Steg 2/2: Kör custom DEA...")
        print(f"    Inputs: {model_spec['inputs']}")
        print(f"    Outputs: {model_spec['outputs']}")
        print(f"    RTS: {model_spec['rts']}, Orientation: {model_spec['orientation']}")
        print(f"    Outlier-params: q=[{config.q_lower}, {config.q_upper}], mult={config.multiplier}")
        
        dea_results = run_dea_analysis(
            df=pre_dea.df_all_companies,
            model_spec=model_spec
        )
        
        # Statistik
        mean_eff = dea_results['Effektivitet'].mean()
        n_efficient = (dea_results['Effektivitet'] >= 1.0).sum()
        n_outliers = dea_results['is_outlier'].sum() if 'is_outlier' in dea_results.columns else 0
        
        print(f"\n  Resultat:")
        print(f"    Företag: {len(dea_results)}")
        print(f"    Medel-effektivitet: {mean_eff:.3f}")
        print(f"    Effektiva (>=100%): {n_efficient} företag")
        print(f"    Outliers: {n_outliers} företag")
        
        print("\n" + "-"*60)
        print("  Resultat: dea_executed=True, dea_method='dea'")
        print("="*60 + "\n")
        
        return DeaStageOutput(
            dea_results=dea_results,
            dea_method="dea",
            dea_executed=True
        )
    
    else:
        raise ValueError(f"Okänd DEA metod: {config.method}")
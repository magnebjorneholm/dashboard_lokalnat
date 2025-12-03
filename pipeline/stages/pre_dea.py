"""
pipeline/stages/pre_dea.py

Stage 2: Pre-DEA
Förbereder CAPEX/OPEX data för DEA-analys.

Stöder 4 metoder:
1. baseline - Ingen ändring, använd baseline-värden
2. wacc_scaling - Skala avkastning med ny WACC
3. parameter_change - Ändra normvärden/livslängder och kör KENT-beräkningar
4. kent_upload - Ladda ny KENT-fil och kör beräkningar (skelett)
"""

from config import PreDeaConfig, CapexMethod
from pipeline.stages.stage_outputs import BaselineStageOutput, PreDeaStageOutput
from calculations import (
    calculate_wacc_scaled_capex,
    load_capbase_a,
    run_kent_calculations_batch,
    merge_kent_with_baseline
)


def stage_pre_dea(
    baseline: BaselineStageOutput,
    config: PreDeaConfig
) -> PreDeaStageOutput:
    """
    Stage 2: Förbereda data för DEA-analys.
    
    Args:
        baseline: Output från Baseline stage
        config: PreDeaConfig med metod och parametrar
        
    Returns:
        PreDeaStageOutput med:
        - df_all_companies: 148 rows, potentially modified CAPEX/OPEX
        - capex_method: Metod som användes
        - capex_modified: True om CAPEX ändrades
    """
    
    if config.method == CapexMethod.BASELINE:
        return _pre_dea_baseline(baseline)
    
    elif config.method == CapexMethod.WACC_SCALING:
        return _pre_dea_wacc_scaling(baseline, config)
    
    elif config.method == CapexMethod.PARAMETER_CHANGE:
        return _pre_dea_parameter_change(baseline, config)
    
    elif config.method == CapexMethod.KENT_UPLOAD:
        return _pre_dea_kent_upload(baseline, config)
    
    else:
        raise ValueError(f"Okänd CAPEX-metod: {config.method}")


def _pre_dea_baseline(baseline: BaselineStageOutput) -> PreDeaStageOutput:
    """
    Metod 1: Baseline - ingen ändring.
    """
    return PreDeaStageOutput(
        df_all_companies=baseline.df_all_companies.copy(),
        capex_method="baseline",
        capex_modified=False
    )


def _pre_dea_wacc_scaling(
    baseline: BaselineStageOutput,
    config: PreDeaConfig
) -> PreDeaStageOutput:
    """
    Metod 2: WACC-scaling - skala avkastning med ny WACC.
    
    Formel:
        Ny Avkastning = Baseline Avkastning × (ny_WACC / baseline_WACC)
        Ny CAPEX = Avskrivning + Ny Avkastning
        Ny TOTEX = OPEXp + Ny CAPEX
    """
    
    if config.wacc is None:
        raise ValueError("WACC måste anges för wacc_scaling metod")
    
    print(f"🔧 WACC-scaling: {baseline.wacc:.4f} → {config.wacc:.4f}")
    
    # Kör WACC-skalning
    df_scaled = calculate_wacc_scaled_capex(
        baseline.df_all_companies,
        new_wacc=config.wacc,
        baseline_wacc=baseline.wacc
    )
    
    print(f"✓ CAPEX skalad för alla {len(df_scaled)} företag")
    
    return PreDeaStageOutput(
        df_all_companies=df_scaled,
        capex_method="wacc_scaling",
        capex_modified=True
    )


def _pre_dea_parameter_change(
    baseline: BaselineStageOutput,
    config: PreDeaConfig
) -> PreDeaStageOutput:
    """
    Metod 3: Parameter-ändringar - ändra normvärden/livslängder.
    
    Process:
    1. Ladda capbase_a (~510k komponenter)
    2. Applicera parameterjusteringar
    3. Kör KENT steg 5-8 för alla företag
    4. Aggregera till id_network nivå
    5. Merge med baseline för övrig data
    """
    
    print("🔧 Parameter-ändringar: Kör KENT-beräkningar...")
    
    # Ladda capbase_a
    try:
        capbase_data = load_capbase_a()
        print(f"  ✓ Laddade capbase_a: {len(capbase_data):,} komponenter")
    except FileNotFoundError as e:
        print(f"  ⚠️ {e}")
        print("  → Använder baseline CAPEX")
        return _pre_dea_baseline(baseline)
    
    # Kör KENT-beräkningar med justeringar
    try:
        df_detailed, df_network = run_kent_calculations_batch(
            capbase_data,
            wacc=config.wacc if config.wacc else baseline.wacc,
            normvalue_adjustments=config.normvalue_adjustments,
            lifetime_adjustments=config.lifetime_adjustments
        )
        print(f"  ✓ KENT-beräkningar klara: {len(df_network)} nätverk")
        
        # Mappa tillbaka till företagsnivå med REId
        df_result = merge_kent_with_baseline(
            df_network,
            baseline.df_all_companies
        )
        print(f"  ✓ Mergat med baseline: {len(df_result)} företag")
        
        return PreDeaStageOutput(
            df_all_companies=df_result,
            capex_method="parameter_change",
            capex_modified=True
        )
        
    except Exception as e:
        print(f"  ⚠️ Fel i KENT-beräkningar: {e}")
        print("  → Använder baseline CAPEX")
        return _pre_dea_baseline(baseline)


def _pre_dea_kent_upload(
    baseline: BaselineStageOutput,
    config: PreDeaConfig
) -> PreDeaStageOutput:
    """
    Metod 4: KENT-upload - ladda ny KENT-fil och kör beräkningar.
    
    TODO: Implementera full KENT-pipeline (steg 1-8)
    För nu: använd baseline
    """
    print("⚠️ KENT-upload inte implementerat än - använder baseline")
    
    return PreDeaStageOutput(
        df_all_companies=baseline.df_all_companies.copy(),
        capex_method="kent_upload",
        capex_modified=False
    )
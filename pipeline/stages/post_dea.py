"""
pipeline/stages/post_dea.py

Stage 4: Post-DEA
Beräknar effektiviseringskrav, påverkbara kostnader, och assemblerar intäktsram.
"""

from config import PostDeaConfig
from pipeline.stages.stage_outputs import (
    DeaStageOutput, 
    PreDeaStageOutput, 
    BaselineStageOutput,
    PostDeaStageOutput
)
from calculations import (
    calculate_effkrav_for_dataframe,
    calculate_paverkbara_with_effkrav,
    assemble_intaktsram,
    extract_user_intaktsram,
    get_paverkbara_from_sdf
)
import pandas as pd


def stage_post_dea(
    dea: DeaStageOutput,
    pre_dea: PreDeaStageOutput,
    baseline: BaselineStageOutput,
    config: PostDeaConfig,
    user_reid: str
) -> PostDeaStageOutput:
    """
    Stage 4: Beräkna effektiviseringskrav, påverkbara, och intäktsram.
    
    Process:
    1. Beräkna effektiviseringskrav för alla 148 företag
    2. Beräkna påverkbara kostnader (OPEX eller TOTEX)
    3. Assemblera intäktsram med alla komponenter
    4. Extrahera användarens specifika intäktsram
    
    Args:
        dea: Output från DEA stage (effektivitet, potential för alla 148)
        pre_dea: Output från Pre-DEA stage (CAPEX-data)
        baseline: Output från Baseline stage (SDF-data)
        config: PostDeaConfig med trunkering och metod
        user_reid: REId för användarens företag
        
    Returns:
        PostDeaStageOutput med:
        - user_intaktsram: Series med alla komponenter för användaren
        - user_effkrav_proc: Årligt effektiviseringskrav för användaren
        - all_intaktsram: DataFrame med alla 148 företags intäktsramar
        - all_effkrav: DataFrame med alla 148 företags effektiviseringskrav
    """
    
    print("\n" + "="*60)
    print("STAGE 4: POST-DEA")
    print("="*60)
    
    # STEG 1: Beräkna effektiviseringskrav för alla 148 företag
    print("\n  Steg 1/4: Beräknar effektiviseringskrav...")
    
    all_effkrav = calculate_effkrav_for_dataframe(
        df=dea.dea_results,
        potential_col='potential',
        outlier_col='is_outlier',
        trunkering_min=config.effkrav_truncation_min,
        trunkering_max=config.effkrav_truncation_max,
        outlier_krav=config.outlier_krav
    )
    
    print(f"    ✓ Effektiviseringskrav beräknat för {len(all_effkrav)} företag")
    
    # STEG 2: Förbered påverkbara baseline-data från SDF
    print("\n  Steg 2/4: Laddar påverkbara baseline från SDF...")
    
    # SDF data finns i baseline.sdf
    # Vi behöver extrahera Påverkbara_Medelvärde och Neonjusteringar
    sdf_paverkbara = get_paverkbara_from_sdf(
        sdf_ir=baseline.sdf_ir,
        sdf_paverkbara=baseline.sdf_paverkbara
    )
    
    print(f"    ✓ Påverkbara baseline laddad för {len(sdf_paverkbara)} företag")
    
    # STEG 3: Beräkna påverkbara kostnader med effektiviseringskrav
    print(f"\n  Steg 3/4: Beräknar påverkbara kostnader ({config.paverkbara_method})...")
    
    all_paverkbara = calculate_paverkbara_with_effkrav(
        effkrav_data=all_effkrav,
        sdf_baseline=sdf_paverkbara,
        capex_data=pre_dea.df_all_companies,
        method=config.paverkbara_method.value
    )
    
    print(f"    ✓ Påverkbara beräknat för {len(all_paverkbara)} företag")
    
    # STEG 4: Assemblera intäktsram
    print("\n  Steg 4/4: Assemblerar intäktsram...")
    
    all_intaktsram = assemble_intaktsram(
        capex_result=pre_dea.df_all_companies,
        paverkbara_result=all_paverkbara,
        sdf_baseline=baseline.sdf_ir
    )
    
    print(f"    ✓ Intäktsram assemblerad för {len(all_intaktsram)} företag")
    
    # STEG 5: Extrahera användarens specifika data
    print(f"\n  Extraherar data för användare ({user_reid})...")
    
    user_intaktsram = extract_user_intaktsram(all_intaktsram, user_reid)
    user_effkrav_proc = all_effkrav[all_effkrav['REId'] == user_reid]['Effkrav_proc'].iloc[0]
    
    print(f"    ✓ Intäktsram: {user_intaktsram['Intaktsram_Total']:,.0f} tkr")
    print(f"    ✓ Effektiviseringskrav: {user_effkrav_proc*100:.2f}% per år")
    
    print("="*60 + "\n")
    
    # Returnera output
    return PostDeaStageOutput(
        user_reid=user_reid,
        user_intaktsram=user_intaktsram,
        user_effkrav_proc=user_effkrav_proc,
        all_intaktsram=all_intaktsram,
        all_effkrav=all_effkrav
    )
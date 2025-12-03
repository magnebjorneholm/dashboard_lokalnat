"""
pipeline/stages/post_dea.py

Stage 4: Post-DEA
Beräknar effektiviseringskrav, påverkbara kostnader, och assemblerar intäktsram.
"""

import pandas as pd
from config import PostDeaConfig
from config.case_definition import PaverkbaraMethod
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
    3. Förbered kapitalkostnad baserat på Pre-DEA metod
    4. Assemblera intäktsram med alla komponenter
    5. Extrahera användarens specifika intäktsram
    
    Args:
        dea: Output från DEA stage (effektivitet, potential för alla 148)
        pre_dea: Output från Pre-DEA stage (CAPEX-data + metadata)
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
    print("\n  Steg 1/5: Beräknar effektiviseringskrav...")
    
    all_effkrav = calculate_effkrav_for_dataframe(
        df=dea.dea_results,
        potential_col='potential',
        outlier_col='is_outlier',
        trunkering_min=config.trunkering_min,
        trunkering_max=config.trunkering_max,
        outlier_krav=config.outlier_krav
    )
    
    print(f"    ✓ Effektiviseringskrav beräknat för {len(all_effkrav)} företag")
    
    # STEG 2: Förbered påverkbara baseline-data från SDF
    print("\n  Steg 2/5: Laddar påverkbara baseline från SDF...")
    
    sdf_paverkbara = get_paverkbara_from_sdf(
        sdf_ir=baseline.sdf_ir,
        sdf_paverkbara=baseline.sdf_paverkbara
    )
    
    print(f"    ✓ Påverkbara baseline laddad för {len(sdf_paverkbara)} företag")
    
    # STEG 3: Beräkna påverkbara kostnader med effektiviseringskrav
    print(f"\n  Steg 3/5: Beräknar påverkbara kostnader ({config.paverkbara_method})...")
    
    # För TOTEX behöver vi kapitalkostnad
    if config.paverkbara_method == PaverkbaraMethod.TOTEX:
        capex_for_paverkbara = _prepare_capex_for_intaktsram(pre_dea, baseline)
    else:
        # För OPEX behövs ingen CAPEX-data
        capex_for_paverkbara = pd.DataFrame({'REId': pre_dea.df_all_companies['REId']})
    
    all_paverkbara = calculate_paverkbara_with_effkrav(
        effkrav_data=all_effkrav,
        sdf_baseline=sdf_paverkbara,
        capex_data=capex_for_paverkbara,
        method=config.paverkbara_method.value
    )
    
    print(f"    ✓ Påverkbara beräknat för {len(all_paverkbara)} företag")
    
    # STEG 4: Förbered kapitalkostnad för intäktsram (baserat på Pre-DEA metod)
    print(f"\n  Steg 4/5: Förbereder kapitalkostnad (källa: {pre_dea.capex_method})...")
    
    capex_for_intaktsram = _prepare_capex_for_intaktsram(
        pre_dea=pre_dea,
        baseline=baseline
    )
    
    print(f"    ✓ Kapitalkostnad förberedd för {len(capex_for_intaktsram)} företag")
    
    # STEG 5: Assemblera intäktsram
    print("\n  Steg 5/5: Assemblerar intäktsram...")
    
    all_intaktsram = assemble_intaktsram(
        capex_result=capex_for_intaktsram,
        paverkbara_result=all_paverkbara,
        sdf_baseline=baseline.sdf_ir
    )
    
    print(f"    ✓ Intäktsram assemblerad för {len(all_intaktsram)} företag")
    
    # STEG 6: Extrahera användarens specifika data
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


def _prepare_capex_for_intaktsram(
    pre_dea: PreDeaStageOutput,
    baseline: BaselineStageOutput
) -> pd.DataFrame:
    """
    Förbereder kapitalkostnad-data för intäktsram assembly.
    
    Använder rätt källa baserat på Pre-DEA metod:
    - 'baseline' → SDF IR (periodsummor från Ei)
    - 'wacc_scaling' → Approximera från skalad CAPEX (år * 4)
    - 'parameter_change' eller 'kent_upload' → Pre-DEA output (har redan periodsummor)
    
    Args:
        pre_dea: Output från Pre-DEA stage (innehåller capex_method)
        baseline: Output från Baseline stage (innehåller SDF IR)
    
    Returns:
        DataFrame med: REId, Kapitalkostnad_Total (periodsummor)
        
    Raises:
        ValueError: Om capex_method är okänd eller periodsummor saknas för KENT-metoder
    """
    
    method = pre_dea.capex_method
    
    if method == 'baseline':
        # Metod 1: Hämta periodsummor från SDF IR (Ei's baseline)
        return baseline.sdf_ir[['REId', 'Kapitalkostnad']].rename(
            columns={'Kapitalkostnad': 'Kapitalkostnad_Total'}
        ).copy()
    
    elif method == 'wacc_scaling':
        # Metod 2: Beräkna periodsummor från skalad CAPEX
        df = pre_dea.df_all_companies[['REId', 'CAPEX']].copy()
        
        return pd.DataFrame({
            'REId': df['REId'],
            'Kapitalkostnad_Total': df['CAPEX'] * 4
        })
    
    elif method in ['parameter_change', 'kent_upload']:
        # Metod 3-4: Periodsummor ska finnas i Pre-DEA output från KENT pipeline
        if 'Kapitalkostnad_Total' in pre_dea.df_all_companies.columns:
            # KENT har körts → har redan periodsummor
            return pre_dea.df_all_companies[['REId', 'Kapitalkostnad_Total']].copy()
        else:
            # Fallback om KENT inte producerat periodsummor (borde inte hända)
            print(f"    ⚠️ Varning: KENT-metod '{method}' saknar periodsummor, använder SDF baseline")
            return baseline.sdf_ir[['REId', 'Kapitalkostnad']].rename(
                columns={'Kapitalkostnad': 'Kapitalkostnad_Total'}
            ).copy()
    
    else:
        raise ValueError(
            f"Okänd capex_method: '{method}'. "
            f"Förväntade värden: 'baseline', 'wacc_scaling', 'parameter_change', 'kent_upload'"
        )
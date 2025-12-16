"""
pipeline/stages/post_dea.py

Stage 5: Post-DEA
Beraknar effektiviseringskrav, paverkbara kostnader, och assemblerar intaktsram.
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
    Stage 5: Berakna effektiviseringskrav, paverkbara, och intaktsram.
    
    Process:
    1. Berakna effektiviseringskrav for alla 148 foretag
    2. Berakna paverkbara kostnader (OPEX eller TOTEX)
    3. Forbered kapitalkostnad baserat pa Pre-DEA metod
    4. Assemblera intaktsram med alla komponenter
    5. Extrahera anvandarens specifika intaktsram
    
    Args:
        dea: Output fran DEA stage (effektivitet, potential for alla 148)
        pre_dea: Output fran Pre-DEA stage (CAPEX-data + metadata)
        baseline: Output fran Baseline stage (SDF-data)
        config: PostDeaConfig med trunkering, kunddelning, realiseringstid, etc.
        user_reid: REId for anvandarens foretag
        
    Returns:
        PostDeaStageOutput med:
        - user_intaktsram: Series med alla komponenter for anvandaren
        - user_effkrav_proc: Arligt effektiviseringskrav for anvandaren
        - all_intaktsram: DataFrame med alla 148 foretags intaktsramar
        - all_effkrav: DataFrame med alla 148 foretags effektiviseringskrav
    """
    
    print("\n" + "="*60)
    print("STAGE 5: POST-DEA")
    print("="*60)
    
    # STEG 1: Berakna effektiviseringskrav for alla 148 foretag
    print("\n  Steg 1/5: Beraknar effektiviseringskrav...")
    print(f"    Parametrar: trunkering=[{config.trunkering_min:.1%}, {config.trunkering_max:.1%}], "
          f"kunddelning={config.kunddelning:.0%}, realiseringstid={config.realiseringstid} ar")
    
    all_effkrav = calculate_effkrav_for_dataframe(
        df=dea.dea_results,
        potential_col='potential',
        outlier_col='is_outlier',
        trunkering_min=config.trunkering_min,
        trunkering_max=config.trunkering_max,
        outlier_krav=config.outlier_krav,
        kunddelning=config.kunddelning,
        realiseringstid=config.realiseringstid,
        tillsynsperiod=config.tillsynsperiod
    )
    
    print(f"    [OK] Effektiviseringskrav beraknat for {len(all_effkrav)} foretag")
    
    # STEG 2: Forbered paverkbara baseline-data fran SDF
    print("\n  Steg 2/5: Laddar paverkbara baseline fran SDF...")
    
    sdf_paverkbara = get_paverkbara_from_sdf(
        sdf_ir=baseline.sdf_ir,
        sdf_paverkbara=baseline.sdf_paverkbara
    )
    
    print(f"    [OK] Paverkbara baseline laddad for {len(sdf_paverkbara)} foretag")
    
    # STEG 3: Berakna paverkbara kostnader med effektiviseringskrav
    print(f"\n  Steg 3/5: Beraknar paverkbara kostnader ({config.paverkbara_method})...")
    
    # For TOTEX behovs kapitalkostnad
    if config.paverkbara_method == PaverkbaraMethod.TOTEX:
        capex_for_paverkbara = _prepare_capex_for_intaktsram(pre_dea, baseline)
    else:
        # For OPEX behovs ingen CAPEX-data
        capex_for_paverkbara = pd.DataFrame({'REId': pre_dea.df_all_companies['REId']})
    
    all_paverkbara = calculate_paverkbara_with_effkrav(
        effkrav_data=all_effkrav,
        sdf_baseline=sdf_paverkbara,
        capex_data=capex_for_paverkbara,
        method=config.paverkbara_method.value
    )
    
    print(f"    [OK] Paverkbara beraknat for {len(all_paverkbara)} foretag")
    
    # STEG 4: Forbered kapitalkostnad for intaktsram (baserat pa Pre-DEA metod)
    print(f"\n  Steg 4/5: Forbereder kapitalkostnad (kalla: {pre_dea.capex_method})...")
    
    capex_for_intaktsram = _prepare_capex_for_intaktsram(
        pre_dea=pre_dea,
        baseline=baseline
    )
    
    print(f"    [OK] Kapitalkostnad forberedd for {len(capex_for_intaktsram)} foretag")
    
    # STEG 5: Assemblera intaktsram
    print("\n  Steg 5/5: Assemblerar intaktsram...")
    
    all_intaktsram = assemble_intaktsram(
        capex_result=capex_for_intaktsram,
        paverkbara_result=all_paverkbara,
        sdf_baseline=baseline.sdf_ir
    )
    
    print(f"    [OK] Intaktsram assemblerad for {len(all_intaktsram)} foretag")
    
    # STEG 6: Extrahera anvandarens specifika data
    print(f"\n  Extraherar data for anvandare ({user_reid})...")
    
    user_intaktsram = extract_user_intaktsram(all_intaktsram, user_reid)
    user_effkrav_proc = all_effkrav[all_effkrav['REId'] == user_reid]['Effkrav_proc'].iloc[0]
    
    print(f"    [OK] Intaktsram: {user_intaktsram['Intaktsram_Total']:,.0f} tkr")
    print(f"    [OK] Effektiviseringskrav: {user_effkrav_proc*100:.2f}% per ar")
    
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
    Forbereder kapitalkostnad-data for intaktsram assembly.
    
    Kritiskt: Returnerar PERIODSUMMA (4 ar), INTE arsvarde!
    
    Anvander ratt kalla baserat pa Pre-DEA metod:
    - 'baseline' -> SDF IR (periodsummor fran Ei)
    - 'wacc_scaling' -> Approximera fran skalad CAPEX (ar * 4)
    - 'parameter_change' eller 'kent_upload' -> Kapitalkostnad_Period fran KENT
    
    Args:
        pre_dea: Output fran Pre-DEA stage (innehaller capex_method)
        baseline: Output fran Baseline stage (innehaller SDF IR)
    
    Returns:
        DataFrame med: REId, Kapitalkostnad_Total (periodsummor i tkr)
        
    Raises:
        ValueError: Om capex_method ar okand
    """
    
    method = pre_dea.capex_method
    
    if method == 'baseline':
        # Metod 1: Hamta periodsummor fran SDF IR (Ei's baseline)
        return baseline.sdf_ir[['REId', 'Kapitalkostnad']].rename(
            columns={'Kapitalkostnad': 'Kapitalkostnad_Total'}
        ).copy()
    
    elif method == 'wacc_scaling':
        # Metod 2: Berakna periodsummor fran skalad Kapitalkostnad_2024 (arsvarde * 4)
        df = pre_dea.df_all_companies[['REId', 'Kapitalkostnad_2024']].copy()

        return pd.DataFrame({
            'REId': df['REId'],
            'Kapitalkostnad_Total': df['Kapitalkostnad_2024'] * 4
        })
    
    elif method in ['parameter_change', 'kent_upload']:
        # Metod 3-4: Hamta periodsumma fran KENT output
        
        # Forst: kolla om Kapitalkostnad_Period finns (ny namnkonvention)
        if 'Kapitalkostnad_Period' in pre_dea.df_all_companies.columns:
            return pre_dea.df_all_companies[['REId', 'Kapitalkostnad_Period']].rename(
                columns={'Kapitalkostnad_Period': 'Kapitalkostnad_Total'}
            ).copy()
        
        # Bakatkompabilitet: kolla om Kapitalkostnad_Total finns
        elif 'Kapitalkostnad_Total' in pre_dea.df_all_companies.columns:
            return pre_dea.df_all_companies[['REId', 'Kapitalkostnad_Total']].copy()
        
        else:
            # If user requested a KENT-based method we should not silently fall back.
            raise ValueError(
                f"Kapitalkostnad periodsummor saknas i Pre-DEA resultat for metod '{method}'. "
                "Forvantade kolumner: 'Kapitalkostnad_Period' eller 'Kapitalkostnad_Total'. "
                "Kontrollera KENT-output och kor om pre-dea-steget."
            )
    
    else:
        raise ValueError(
            f"Okand capex_method: '{method}'. "
            f"Forvantade varden: 'baseline', 'wacc_scaling', 'parameter_change', 'kent_upload'"
        )
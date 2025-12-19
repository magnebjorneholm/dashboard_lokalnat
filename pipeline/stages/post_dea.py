"""
pipeline/stages/post_dea.py

Stage 5: Post-DEA
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


# Kolumnnamn i SDF IR-sheet för periodsummor
SDF_COL_KAPITALFORSLITNING = '-varav Kapital-förslitning'
SDF_COL_KAPITALBINDNING = 'varav Kapital-bindning'
SDF_COL_KAPITALKOSTNAD = 'Kapitalkostnad'


def stage_post_dea(
    dea: DeaStageOutput,
    pre_dea: PreDeaStageOutput,
    baseline: BaselineStageOutput,
    config: PostDeaConfig,
    user_reid: str
) -> PostDeaStageOutput:
    """
    Stage 5: Beräkna effektiviseringskrav, påverkbara, och intäktsram.
    
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
        config: PostDeaConfig med trunkering, kunddelning, realiseringstid, etc.
        user_reid: REId för användarens företag
        
    Returns:
        PostDeaStageOutput med:
        - user_intaktsram: Series med alla komponenter för användaren
        - user_effkrav_proc: Årligt effektiviseringskrav för användaren
        - all_intaktsram: DataFrame med alla 148 företags intäktsramar
        - all_effkrav: DataFrame med alla 148 företags effektiviseringskrav
    """
    
    print("\n" + "="*60)
    print("STAGE 5: POST-DEA")
    print("="*60)
    
    # STEG 1: Beräkna effektiviseringskrav för alla 148 företag
    print("\n  Steg 1/5: Beräknar effektiviseringskrav...")
    print(f"    Parametrar: trunkering=[{config.trunkering_min:.1%}, {config.trunkering_max:.1%}], "
          f"kunddelning={config.kunddelning:.0%}, realiseringstid={config.realiseringstid} år")
    
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
    
    print(f"    [OK] Effektiviseringskrav beräknat för {len(all_effkrav)} företag")
    
    # STEG 2: Förbered påverkbara baseline-data från SDF
    print("\n  Steg 2/5: Laddar påverkbara baseline från SDF...")
    
    sdf_paverkbara = get_paverkbara_from_sdf(
        sdf_ir=baseline.sdf_ir,
        sdf_paverkbara=baseline.sdf_paverkbara
    )
    
    print(f"    [OK] Påverkbara baseline laddad för {len(sdf_paverkbara)} företag")
    
    # STEG 3: Beräkna påverkbara kostnader med effektiviseringskrav
    print(f"\n  Steg 3/5: Beräknar påverkbara kostnader ({config.paverkbara_method})...")
    
    # För TOTEX behövs kapitalkostnad
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
    
    print(f"    [OK] Påverkbara beräknat för {len(all_paverkbara)} företag")
    
    # STEG 4: Förbered kapitalkostnad för intäktsram (baserat på Pre-DEA metod)
    print(f"\n  Steg 4/5: Förbereder kapitalkostnad (källa: {pre_dea.capex_method})...")
    
    capex_for_intaktsram = _prepare_capex_for_intaktsram(
        pre_dea=pre_dea,
        baseline=baseline
    )
    
    print(f"    [OK] Kapitalkostnad förberedd för {len(capex_for_intaktsram)} företag")
    
    # STEG 5: Assemblera intäktsram
    print("\n  Steg 5/5: Assemblerar intäktsram...")
    
    all_intaktsram = assemble_intaktsram(
        capex_result=capex_for_intaktsram,
        paverkbara_result=all_paverkbara,
        sdf_baseline=baseline.sdf_ir
    )
    
    print(f"    [OK] Intäktsram assemblerad för {len(all_intaktsram)} företag")
    
    # STEG 6: Extrahera användarens specifika data
    print(f"\n  Extraherar data för användare ({user_reid})...")
    
    user_intaktsram = extract_user_intaktsram(all_intaktsram, user_reid)
    user_effkrav_proc = all_effkrav[all_effkrav['REId'] == user_reid]['Effkrav_proc'].iloc[0]
    
    print(f"    [OK] Intäktsram: {user_intaktsram['Intaktsram_Total']:,.0f} tkr")
    print(f"    [OK] Effektiviseringskrav: {user_effkrav_proc*100:.2f}% per år")
    
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
    
    KRITISKT: Returnerar PERIODSUMMA (4 år), INTE årsvärde!
    
    Använder rätt källa baserat på Pre-DEA metod:
    - 'baseline' -> SDF IR (periodsummor från Ei)
    - 'wacc_scaling' -> Skala periodsummor från SDF med WACC-kvot
    - 'parameter_change' eller 'kent_upload' -> Kapitalkostnad_Period från KENT
    
    Args:
        pre_dea: Output från Pre-DEA stage (innehåller capex_method och wacc_used)
        baseline: Output från Baseline stage (innehåller SDF IR)
    
    Returns:
        DataFrame med: REId, Kapitalkostnad_Total (periodsummor i tkr)
        
    Raises:
        ValueError: Om capex_method är okänd eller data saknas
    """
    
    method = pre_dea.capex_method
    
    if method == 'baseline':
        # Metod 1: Hämta periodsummor från SDF IR (Ei's baseline)
        return baseline.sdf_ir[['REId', SDF_COL_KAPITALKOSTNAD]].rename(
            columns={SDF_COL_KAPITALKOSTNAD: 'Kapitalkostnad_Total'}
        ).copy()
    
    elif method == 'wacc_scaling':
        # Metod 2: Skala periodsummor från SDF med WACC-kvot
        # 
        # KORREKT METOD:
        # - Kapitalförslitning (avskrivning) är oförändrad
        # - Kapitalbindning (avkastning) skalas med (ny_WACC / baseline_WACC)
        # - Ny periodsumma = Kapitalförslitning + Skalad Kapitalbindning
        #
        # FELAKTIG (tidigare) METOD:
        # - Kapitalkostnad_2024 * 4 (ignorerar att kapitalbindningen avtar över tid)
        
        return _calculate_wacc_scaled_period_capex(pre_dea, baseline)
    
    elif method in ['parameter_change', 'kent_upload']:
        # Metod 3-4: Hämta periodsumma från KENT output
        
        # Först: kolla om Kapitalkostnad_Period finns (ny namnkonvention)
        if 'Kapitalkostnad_Period' in pre_dea.df_all_companies.columns:
            return pre_dea.df_all_companies[['REId', 'Kapitalkostnad_Period']].rename(
                columns={'Kapitalkostnad_Period': 'Kapitalkostnad_Total'}
            ).copy()
        
        # Bakåtkompatibilitet: kolla om Kapitalkostnad_Total finns
        elif 'Kapitalkostnad_Total' in pre_dea.df_all_companies.columns:
            return pre_dea.df_all_companies[['REId', 'Kapitalkostnad_Total']].copy()
        
        else:
            # Om användaren valde KENT-baserad metod ska vi inte falla tillbaka tyst
            raise ValueError(
                f"Kapitalkostnad periodsummor saknas i Pre-DEA resultat för metod '{method}'. "
                "Förväntade kolumner: 'Kapitalkostnad_Period' eller 'Kapitalkostnad_Total'. "
                "Kontrollera KENT-output och kör om pre-dea-steget."
            )
    
    else:
        raise ValueError(
            f"Okänd capex_method: '{method}'. "
            f"Förväntade värden: 'baseline', 'wacc_scaling', 'parameter_change', 'kent_upload'"
        )


def _calculate_wacc_scaled_period_capex(
    pre_dea: PreDeaStageOutput,
    baseline: BaselineStageOutput
) -> pd.DataFrame:
    """
    Beräknar korrekt WACC-skalad periodsumma för kapitalkostnad.
    
    Metod:
    1. Hämta periodsummor för kapitalförslitning och kapitalbindning från SDF
    2. Beräkna skalningsfaktor: ny_WACC / baseline_WACC
    3. Skala ENDAST kapitalbindningen (avkastning avtar med WACC)
    4. Ny periodsumma = Kapitalförslitning + Skalad Kapitalbindning
    
    Varför detta är korrekt:
    - Kapitalförslitning (avskrivning) beror på NUAV och livslängd, inte på WACC
    - Kapitalbindning (avkastning) = kapitalbas × WACC, proportionell mot WACC
    - Att ta årsvärde × 4 är FEL eftersom kapitalbindningen avtar varje halvår
      när tillgångarna åldras
    
    Args:
        pre_dea: Output från Pre-DEA stage (innehåller wacc_used)
        baseline: Output från Baseline stage (innehåller SDF IR med periodsummor)
    
    Returns:
        DataFrame med: REId, Kapitalkostnad_Total (korrekt skalad periodsumma)
    """
    
    # Validera att vi har WACC
    if pre_dea.wacc_used is None:
        raise ValueError(
            "wacc_used saknas i PreDeaStageOutput för wacc_scaling metod. "
            "Kontrollera att pre_dea.py sätter wacc_used korrekt."
        )
    
    new_wacc = pre_dea.wacc_used
    baseline_wacc = baseline.wacc
    
    # Validera SDF-kolumner
    sdf = baseline.sdf_ir.copy()
    
    if SDF_COL_KAPITALFORSLITNING not in sdf.columns:
        raise ValueError(
            f"Kolumn '{SDF_COL_KAPITALFORSLITNING}' saknas i SDF IR. "
            f"Tillgängliga kolumner: {list(sdf.columns)}"
        )
    
    if SDF_COL_KAPITALBINDNING not in sdf.columns:
        raise ValueError(
            f"Kolumn '{SDF_COL_KAPITALBINDNING}' saknas i SDF IR. "
            f"Tillgängliga kolumner: {list(sdf.columns)}"
        )
    
    # Extrahera periodsummor
    df = sdf[['REId', SDF_COL_KAPITALFORSLITNING, SDF_COL_KAPITALBINDNING]].copy()
    df.columns = ['REId', 'Kapitalforslitning_Period', 'Kapitalbindning_Period']
    
    # Konvertera till numeriska värden
    df['Kapitalforslitning_Period'] = pd.to_numeric(
        df['Kapitalforslitning_Period'], errors='coerce'
    ).fillna(0)
    df['Kapitalbindning_Period'] = pd.to_numeric(
        df['Kapitalbindning_Period'], errors='coerce'
    ).fillna(0)
    
    # Beräkna skalningsfaktor
    scaling_factor = new_wacc / baseline_wacc
    
    print(f"    WACC-skalning av periodsummor:")
    print(f"      Baseline WACC: {baseline_wacc:.4f} ({baseline_wacc*100:.2f}%)")
    print(f"      Ny WACC: {new_wacc:.4f} ({new_wacc*100:.2f}%)")
    print(f"      Skalningsfaktor: {scaling_factor:.4f}")
    
    # Skala endast kapitalbindningen
    df['Kapitalbindning_Skalad'] = df['Kapitalbindning_Period'] * scaling_factor
    
    # Ny periodsumma = Kapitalförslitning (oförändrad) + Kapitalbindning (skalad)
    df['Kapitalkostnad_Total'] = df['Kapitalforslitning_Period'] + df['Kapitalbindning_Skalad']
    
    # Logga förändring för verifiering
    total_baseline = df['Kapitalforslitning_Period'].sum() + df['Kapitalbindning_Period'].sum()
    total_scaled = df['Kapitalkostnad_Total'].sum()
    delta_pct = (total_scaled / total_baseline - 1) * 100
    
    print(f"      Baseline periodsumma (alla): {total_baseline:,.0f} tkr")
    print(f"      Skalad periodsumma (alla): {total_scaled:,.0f} tkr")
    print(f"      Förändring: {delta_pct:+.2f}%")
    
    return df[['REId', 'Kapitalkostnad_Total']]


def get_return_per_year(
    pre_dea: PreDeaStageOutput,
    baseline: BaselineStageOutput
) -> pd.DataFrame:
    """
    Hämtar avkastning per år för alla företag, baserat på capex_method.
    
    Används för incitamentjusteringens 1/3-cap som appliceras per år.
    
    Källor beroende på capex_method:
    - 'baseline': SDF "varav Kapital-bindning" / 4
    - 'wacc_scaling': SDF "varav Kapital-bindning" × (ny_WACC / baseline_WACC) / 4
    - 'kent_upload': KENT-output Avkastning_{year}
    - 'parameter_change': KENT-output Avkastning_{year}
    
    Args:
        pre_dea: Output från Pre-DEA stage
        baseline: Output från Baseline stage
    
    Returns:
        DataFrame med: REId, Avkastning_2024, Avkastning_2025, 
                       Avkastning_2026, Avkastning_2027 (alla i tkr)
    """
    
    method = pre_dea.capex_method
    years = [2024, 2025, 2026, 2027]
    
    if method == 'baseline':
        # Hämta periodsumma från SDF och dela med 4
        return _get_return_from_sdf(baseline, scaling_factor=1.0)
    
    elif method == 'wacc_scaling':
        # Skala periodsumma med WACC-kvot och dela med 4
        if pre_dea.wacc_used is None:
            raise ValueError(
                "wacc_used saknas i PreDeaStageOutput för wacc_scaling metod."
            )
        scaling_factor = pre_dea.wacc_used / baseline.wacc
        return _get_return_from_sdf(baseline, scaling_factor=scaling_factor)
    
    elif method in ['kent_upload', 'parameter_change']:
        # Hämta per-år avkastning från KENT-output
        return _get_return_from_kent(pre_dea, years)
    
    else:
        raise ValueError(
            f"Okänd capex_method: '{method}'. "
            f"Förväntade: 'baseline', 'wacc_scaling', 'parameter_change', 'kent_upload'"
        )


def _get_return_from_sdf(
    baseline: BaselineStageOutput,
    scaling_factor: float = 1.0
) -> pd.DataFrame:
    """
    Hämtar avkastning per år från SDF (för baseline och wacc_scaling).
    
    Approximerar per-år genom att ta periodsumma / 4.
    """
    sdf = baseline.sdf_ir.copy()
    
    if SDF_COL_KAPITALBINDNING not in sdf.columns:
        raise ValueError(
            f"Kolumn '{SDF_COL_KAPITALBINDNING}' saknas i SDF IR."
        )
    
    df = sdf[['REId']].copy()
    
    # Hämta periodsumma och skala
    kapitalbindning_period = pd.to_numeric(
        sdf[SDF_COL_KAPITALBINDNING], errors='coerce'
    ).fillna(0)
    
    kapitalbindning_skalad = kapitalbindning_period * scaling_factor
    
    # Approximera per år (periodsumma / 4)
    avkastning_per_year = kapitalbindning_skalad / 4
    
    # Sätt samma värde för alla år (approximation)
    for year in [2024, 2025, 2026, 2027]:
        df[f'Avkastning_{year}'] = avkastning_per_year
    
    return df


def _get_return_from_kent(
    pre_dea: PreDeaStageOutput,
    years: list
) -> pd.DataFrame:
    """
    Hämtar avkastning per år från KENT-output (för kent_upload och parameter_change).
    """
    df_kent = pre_dea.df_all_companies
    
    # Verifiera att per-år kolumner finns
    missing_years = []
    for year in years:
        col = f'Avkastning_{year}'
        if col not in df_kent.columns:
            missing_years.append(year)
    
    if missing_years:
        raise ValueError(
            f"Avkastning per år saknas i KENT-output för år: {missing_years}. "
            "Förväntade kolumner: Avkastning_2024, Avkastning_2025, etc. "
            "Kontrollera att kent_calculations.py genererar dessa kolumner."
        )
    
    # Extrahera relevanta kolumner
    cols = ['REId'] + [f'Avkastning_{year}' for year in years]
    return df_kent[cols].copy()
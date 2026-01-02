"""
pipeline/stages/pre_dea.py

Stage 2: Pre-DEA
Förbereder CAPEX/OPEX data för DEA-analys.

Stöder 4 metoder:
1. baseline - Ingen ändring, använd baseline-värden
2. wacc_scaling - Skala avkastning med ny WACC
3. parameter_change - Ändra normvärden/livslängder och kör KENT-beräkningar
4. kent_upload - Ladda ny KENT-fil och kör beräkningar
"""

import pandas as pd
from io import BytesIO
from typing import Optional

from config.case_definition import PreDeaConfig, CapexMethod
from pipeline.stages.stage_outputs import BaselineStageOutput, PreDeaStageOutput
from calculations.wacc_scaling import calculate_wacc_scaled_capex
from calculations.kent_calculations import (
    load_capbase_a,
    run_kent_calculations_batch,
)
from calculations.data_mapping import merge_kent_with_baseline


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
        - wacc_used: WACC som användes (för wacc_scaling)
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
    """Metod 1: Baseline - ingen ändring."""
    return PreDeaStageOutput(
        df_all_companies=baseline.df_all_companies.copy(),
        capex_method="baseline",
        capex_modified=False,
        wacc_used=None
    )


def _pre_dea_wacc_scaling(
    baseline: BaselineStageOutput,
    config: PreDeaConfig
) -> PreDeaStageOutput:
    """
    Metod 2: WACC-scaling - skala avkastning med ny WACC.
    
    Producerar Kapitalkostnad_2024 (årsvärde) för DEA.
    Post-DEA använder wacc_used för att skala periodsummor från SDF.
    
    Formel för DEA (årsvärde):
        Ny Avkastning = Baseline Avkastning * (ny_WACC / baseline_WACC)
        Ny CAPEX = Avskrivning + Ny Avkastning
        Ny TOTEX = OPEXp + Ny CAPEX
    """
    
    if config.wacc is None:
        raise ValueError("WACC måste anges för wacc_scaling metod")
    
    print(f"WACC-scaling: {baseline.wacc:.4f} -> {config.wacc:.4f}")
    
    df_scaled = calculate_wacc_scaled_capex(
        baseline.df_all_companies,
        new_wacc=config.wacc,
        baseline_wacc=baseline.wacc
    )
    
    print(f"CAPEX skalad för alla {len(df_scaled)} företag")
    
    return PreDeaStageOutput(
        df_all_companies=df_scaled,
        capex_method="wacc_scaling",
        capex_modified=True,
        wacc_used=config.wacc  # Spara för post_dea periodsumme-beräkning
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
    
    print("Parameter-ändringar: Kör KENT-beräkningar...")
    
    try:
        capbase_data = load_capbase_a()
        print(f"  Laddade capbase_a: {len(capbase_data):,} komponenter")
    except FileNotFoundError as e:
        print(f"  {e}")
        print("  Använder baseline CAPEX")
        return _pre_dea_baseline(baseline)
    
    try:
        df_detailed, df_network = run_kent_calculations_batch(
            capbase_data,
            wacc=config.wacc if config.wacc else baseline.wacc,
            normvalue_adjustments=config.normvalue_adjustments,
            lifetime_adjustments=config.lifetime_adjustments
        )
        print(f"  KENT-beräkningar klara: {len(df_network)} nätverk")
        
        # Skicka med sdf_ir för DEV FALLBACK av Kapitalkostnad_Period
        df_result = merge_kent_with_baseline(
            df_network,
            baseline.df_all_companies,
            sdf_ir=baseline.sdf_ir  # Fallback för företag utan KENT-data
        )
        print(f"  Mergat med baseline: {len(df_result)} företag")
        
        return PreDeaStageOutput(
            df_all_companies=df_result,
            capex_method="parameter_change",
            capex_modified=True,
            wacc_used=config.wacc if config.wacc else baseline.wacc
        )
        
    except Exception as e:
        print(f"  Fel i KENT-beräkningar: {e}")
        print("  Använder baseline CAPEX")
        return _pre_dea_baseline(baseline)


def _pre_dea_kent_upload(
    baseline: BaselineStageOutput,
    config: PreDeaConfig
) -> PreDeaStageOutput:
    """
    Metod 4: KENT-upload - ladda ny KENT-fil och kör beräkningar.
    
    Två scenarion:
    1. KENT-only (inga parametrar ändrade):
       - Kör steg 1-4 + 5-8 för användarens företag
       - Använd baseline för övriga 147 företag
       
    2. KENT + parametrar (normvärden/livslängder ändrade):
       - Kör steg 1-4 för användarens företag
       - Ersätt användarens data i capbase_a
       - Kör steg 5-8 för ALLA 148 företag
    """
    
    # Importera kent_capbase_prep här för att undvika cirkulära imports
    try:
        from calculations.kent_capbase_prep import (
            build_capbase_a_from_kent,
            get_kent_upload_summary
        )
    except ImportError as e:
        print(f"  Kunde inte importera kent_capbase_prep: {e}")
        print("  Använder baseline CAPEX")
        return _pre_dea_baseline(baseline)
    
    # Validera input
    if config.kent_file_bytes is None:
        raise ValueError("kent_file_bytes måste anges för kent_upload metod")
    
    if config.kent_user_id_network is None:
        raise ValueError("kent_user_id_network måste anges för kent_upload metod")
    
    print("KENT-upload: Processar uppladdad fil...")
    
    # Steg 1-4: Konvertera KENT Excel till capbase_a format
    try:
        kent_file = BytesIO(config.kent_file_bytes)
        
        user_capbase_a = build_capbase_a_from_kent(
            kent_file,
            network_id=config.kent_user_id_network,
            lifetime_adjustments=config.lifetime_adjustments
        )
        
        summary = get_kent_upload_summary(user_capbase_a)
        print(f"  KENT steg 1-4 klara:")
        print(f"    - {summary['n_components']} komponenter")
        print(f"    - {summary['n_existing']} befintliga, {summary['n_investments']} investeringar")
        print(f"    - Total NUAV: {summary['total_nuav_mkr']:.1f} Mkr")
        
    except Exception as e:
        print(f"  Fel vid KENT-processning: {e}")
        print("  Använder baseline CAPEX")
        return _pre_dea_baseline(baseline)
    
    # Bestäm scenario baserat på parametrar
    has_parameter_changes = (
        config.normvalue_adjustments is not None or
        config.lifetime_adjustments is not None
    )
    
    if has_parameter_changes:
        return _kent_upload_with_parameters(
            baseline, config, user_capbase_a
        )
    else:
        return _kent_upload_only(
            baseline, config, user_capbase_a
        )


def _kent_upload_only(
    baseline: BaselineStageOutput,
    config: PreDeaConfig,
    user_capbase_a: pd.DataFrame
) -> PreDeaStageOutput:
    """
    Scenario 1: KENT-only
    
    Kör steg 5-8 för ENDAST användarens företag.
    Övriga 147 företag använder baseline CAPEX.
    
    Kritiskt: Både Kapitalkostnad_2024 (för DEA) och Kapitalkostnad_Period 
    (för intäktsram) måste hämtas från KENT-output.
    """
    print("  Scenario: KENT-only (inget annat ändrat)")
    
    wacc_to_use = config.wacc if config.wacc else baseline.wacc
    
    # Kör steg 5-8 för användarens data
    try:
        _, df_user_network = run_kent_calculations_batch(
            user_capbase_a,
            wacc=wacc_to_use,
            normvalue_adjustments=None,
            lifetime_adjustments=None
        )
        
        if len(df_user_network) == 0:
            raise ValueError("Inga nätverk beräknades från KENT-data")
        
        user_capex = df_user_network.iloc[0]['Kapitalkostnad_2024']
        print(f"  Användarens nya CAPEX: {user_capex:,.0f} tkr")
        
        # Hämta periodsumma från KENT-output
        if 'Kapitalkostnad_Period' in df_user_network.columns:
            user_period = df_user_network.iloc[0]['Kapitalkostnad_Period']
            print(f"  Användarens periodsumma: {user_period:,.0f} tkr")
        else:
            raise ValueError(
                "Kapitalkostnad_Period saknas i KENT-output. "
                "Kontrollera att kent_calculations.py producerar periodsummor korrekt.")
        
    except Exception as e:
        print(f"  Fel vid KENT steg 5-8: {e}")
        print("  Använder baseline CAPEX")
        return _pre_dea_baseline(baseline)
    
    # Kopiera baseline och berika med periodsummor från SDF
    df_result = baseline.df_all_companies.copy()
    
    # Lägg till periodsummor från SDF för alla 148 företag (baseline-värden)
    # sdf_ir innehåller 'Kapitalkostnad' som är periodsumman
    if 'Kapitalkostnad_Period' not in df_result.columns:
        sdf_period = baseline.sdf_ir[['REId', 'Kapitalkostnad']].rename(
            columns={'Kapitalkostnad': 'Kapitalkostnad_Period'}
        )
        df_result = df_result.merge(sdf_period, on='REId', how='left')
        print(f"  Lade till baseline periodsummor för {len(df_result)} företag")
    
    # Hitta användarens rad via id_network
    user_id_network = config.kent_user_id_network
    
    # Skapa REId från id_network
    user_reid = f"REL{user_id_network:05d}"
    
    mask = df_result['REId'] == user_reid
    if mask.sum() == 0:
        # Försök med id_network direkt
        if 'id_network' in df_result.columns:
            mask = df_result['id_network'] == user_id_network
    
    if mask.sum() == 0:
        print(f"  Kunde inte hitta företag {user_reid} i baseline")
        print("  Använder baseline CAPEX")
        return _pre_dea_baseline(baseline)
    
    # Uppdatera CAPEX-relaterade kolumner för användaren
    old_capex = df_result.loc[mask, 'Kapitalkostnad_2024'].values[0]
    old_period = df_result.loc[mask, 'Kapitalkostnad_Period'].values[0] if 'Kapitalkostnad_Period' in df_result.columns else None
    
    # Kapitalkostnad_2024 (för DEA)
    df_result.loc[mask, 'Kapitalkostnad_2024'] = user_capex
    
    # Kapitalkostnad_Period (för intäktsram)
    df_result.loc[mask, 'Kapitalkostnad_Period'] = user_period
    
    # Uppdatera CAPEX alias om det finns
    if 'CAPEX' in df_result.columns:
        df_result.loc[mask, 'CAPEX'] = user_capex
    
    # Uppdatera TOTEX om det finns
    if 'TOTEX' in df_result.columns and 'OPEXp' in df_result.columns:
        opex = df_result.loc[mask, 'OPEXp'].values[0]
        df_result.loc[mask, 'TOTEX'] = opex + user_capex
    
    # Uppdatera Avskrivning och Avkastning om de finns i df_user_network
    if 'Avskrivning' in df_user_network.columns:
        avskriv = df_user_network.iloc[0].get('Avskrivning', 0)
        if 'Avskrivning' in df_result.columns:
            df_result.loc[mask, 'Avskrivning'] = avskriv
    
    if 'Avkastning' in df_user_network.columns:
        avkast = df_user_network.iloc[0].get('Avkastning', 0)
        if 'Avkastning' in df_result.columns:
            df_result.loc[mask, 'Avkastning'] = avkast
    
    # Uppdatera årsvisa kapitalkostnader om de finns
    for year in [2025, 2026, 2027]:
        col = f'Kapitalkostnad_{year}'
        if col in df_user_network.columns and col in df_result.columns:
            df_result.loc[mask, col] = df_user_network.iloc[0][col]
    
    print(f"  Ersatte för {user_reid}:")
    print(f"    - Kapitalkostnad_2024: {old_capex:,.0f} -> {user_capex:,.0f} tkr")
    if old_period is not None:
        print(f"    - Kapitalkostnad_Period: {old_period:,.0f} -> {user_period:,.0f} tkr")
    
    return PreDeaStageOutput(
        df_all_companies=df_result,
        capex_method="kent_upload",
        capex_modified=True,
        wacc_used=wacc_to_use
    )


def _kent_upload_with_parameters(
    baseline: BaselineStageOutput,
    config: PreDeaConfig,
    user_capbase_a: pd.DataFrame
) -> PreDeaStageOutput:
    """
    Scenario 2: KENT + parametrar
    
    Ersätter användarens data i capbase_a och kör steg 5-8
    för ALLA 148 företag (eftersom parametrar ändrats).
    
    merge_kent_with_baseline() hanterar Kapitalkostnad_Period automatiskt.
    """
    print("  Scenario: KENT + parametrar (alla företag omberäknas)")
    
    wacc_to_use = config.wacc if config.wacc else baseline.wacc
    
    # Ladda baseline capbase_a
    try:
        capbase_data = load_capbase_a()
        print(f"  Laddade capbase_a: {len(capbase_data):,} komponenter")
    except FileNotFoundError as e:
        print(f"  {e}")
        # Fallback: Kör bara för användarens företag
        return _kent_upload_only(baseline, config, user_capbase_a)
    
    # Ersätt användarens komponenter i capbase_a
    user_id_network = config.kent_user_id_network
    
    # Ta bort användarens befintliga komponenter
    mask_not_user = capbase_data['id_network'] != user_id_network
    capbase_without_user = capbase_data[mask_not_user].copy()
    
    n_removed = len(capbase_data) - len(capbase_without_user)
    print(f"  Tog bort {n_removed} komponenter för id_network={user_id_network}")
    
    # Lägg till användarens nya komponenter
    capbase_combined = pd.concat([capbase_without_user, user_capbase_a], ignore_index=True)
    print(f"  Lade till {len(user_capbase_a)} nya komponenter")
    print(f"  Total capbase_a: {len(capbase_combined):,} komponenter")
    
    # Kör steg 5-8 för alla företag med parameterjusteringar
    try:
        df_detailed, df_network = run_kent_calculations_batch(
            capbase_combined,
            wacc=wacc_to_use,
            normvalue_adjustments=config.normvalue_adjustments,
            lifetime_adjustments=config.lifetime_adjustments
        )
        print(f"  KENT-beräkningar klara: {len(df_network)} nätverk")
        
    except Exception as e:
        print(f"  Fel i KENT-beräkningar: {e}")
        print("  Använder baseline CAPEX")
        return _pre_dea_baseline(baseline)
    
    # Merge med baseline för övrig data
    # Skicka med sdf_ir för DEV FALLBACK av Kapitalkostnad_Period
    df_result = merge_kent_with_baseline(
        df_network,
        baseline.df_all_companies,
        sdf_ir=baseline.sdf_ir  # Fallback för företag utan KENT-data
    )
    print(f"  Mergat med baseline: {len(df_result)} företag")
    
    return PreDeaStageOutput(
        df_all_companies=df_result,
        capex_method="kent_upload",
        capex_modified=True,
        wacc_used=wacc_to_use
    )
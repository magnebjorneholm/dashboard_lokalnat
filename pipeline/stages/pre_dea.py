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


# =============================================================================
# HUVUDFUNKTION
# =============================================================================

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
    
    # Stage header
    print("\n" + "="*60)
    print("STAGE 2: PRE-DEA")
    print(f"  Metod: {config.method.value}")
    print("="*60)
    
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


# =============================================================================
# METOD 1: BASELINE
# =============================================================================

def _pre_dea_baseline(baseline: BaselineStageOutput) -> PreDeaStageOutput:
    """Metod 1: Baseline - ingen ändring, använd befintliga värden."""
    
    print("\n  Steg 1/1: Kopierar baseline-data...")
    print(f"    Källa: Data_modeller.xlsx ({len(baseline.df_all_companies)} företag)")
    print(f"    WACC: {baseline.wacc:.4f} (baseline)")
    print("    [OK] Ingen CAPEX-modifikation")
    
    print("\n" + "-"*60)
    print("  Resultat: capex_modified=False, capex_method='baseline'")
    print("="*60 + "\n")
    
    return PreDeaStageOutput(
        df_all_companies=baseline.df_all_companies.copy(),
        capex_method="baseline",
        capex_modified=False,
        wacc_used=None
    )


# =============================================================================
# METOD 2: WACC-SCALING
# =============================================================================

def _pre_dea_wacc_scaling(
    baseline: BaselineStageOutput,
    config: PreDeaConfig
) -> PreDeaStageOutput:
    """
    Metod 2: WACC-scaling - skala avkastning med ny WACC.
    
    Producerar Kapitalkostnad_2024 (årsvärde) för DEA.
    Post-DEA använder wacc_used för att skala periodsummor från SDF.
    """
    
    if config.wacc is None:
        raise ValueError("WACC måste anges för wacc_scaling metod")
    
    print("\n  Steg 1/2: Beräknar skalningsfaktor...")
    scaling_factor = config.wacc / baseline.wacc
    print(f"    Baseline WACC: {baseline.wacc:.4f}")
    print(f"    Ny WACC:       {config.wacc:.4f}")
    print(f"    Skalningsfaktor: {scaling_factor:.4f}")
    
    print("\n  Steg 2/2: Skalar avkastning för alla företag...")
    print(f"    Källa: Data_modeller.xlsx ({len(baseline.df_all_companies)} företag)")
    
    df_scaled = calculate_wacc_scaled_capex(
        baseline.df_all_companies,
        new_wacc=config.wacc,
        baseline_wacc=baseline.wacc
    )
    
    print(f"    [OK] CAPEX skalad för {len(df_scaled)} företag")
    
    # Visa exempel på förändring
    sample_reid = df_scaled['REId'].iloc[0]
    old_capex = baseline.df_all_companies[
        baseline.df_all_companies['REId'] == sample_reid
    ]['Kapitalkostnad_2024'].iloc[0]
    new_capex = df_scaled[df_scaled['REId'] == sample_reid]['Kapitalkostnad_2024'].iloc[0]
    print(f"    Exempel ({sample_reid}): {old_capex:,.0f} -> {new_capex:,.0f} tkr")
    
    print("\n" + "-"*60)
    print(f"  Resultat: capex_modified=True, capex_method='wacc_scaling'")
    print(f"            wacc_used={config.wacc:.4f}")
    print("="*60 + "\n")
    
    return PreDeaStageOutput(
        df_all_companies=df_scaled,
        capex_method="wacc_scaling",
        capex_modified=True,
        wacc_used=config.wacc
    )


# =============================================================================
# METOD 3: PARAMETER_CHANGE
# =============================================================================

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
    
    wacc_to_use = config.wacc if config.wacc else baseline.wacc
    
    # Steg 1: Ladda capbase_a
    print("\n  Steg 1/4: Laddar kapitalbas...")
    try:
        capbase_data = load_capbase_a()
        n_components = len(capbase_data)
        n_networks = capbase_data['id_network'].nunique()
        print(f"    Källa: capbase_a.parquet")
        print(f"    Komponenter: {n_components:,}")
        print(f"    Nätverk: {n_networks}")
    except FileNotFoundError as e:
        print(f"    [FALLBACK: BASELINE] {e}")
        print("    Kunde inte ladda capbase_a, använder baseline CAPEX")
        return _pre_dea_baseline(baseline)
    
    # Steg 2: Logga parameterjusteringar
    print("\n  Steg 2/4: Applicerar parameterjusteringar...")
    if config.normvalue_adjustments:
        print(f"    Normvärde-justeringar: {len(config.normvalue_adjustments)} kategorier")
        for cat_id, factor in config.normvalue_adjustments.items():
            print(f"      - Kategori {cat_id}: x{factor:.2f}")
    else:
        print("    Normvärde-justeringar: Inga")
    
    if config.lifetime_adjustments:
        print(f"    Livslängd-justeringar: {len(config.lifetime_adjustments)} kategorier")
    else:
        print("    Livslängd-justeringar: Inga")
    
    print(f"    WACC: {wacc_to_use:.4f}")
    
    # Steg 3: Kör KENT-beräkningar
    print("\n  Steg 3/4: Kör KENT-beräkningar (steg 5-8)...")
    try:
        df_detailed, df_network = run_kent_calculations_batch(
            capbase_data,
            wacc=wacc_to_use,
            normvalue_adjustments=config.normvalue_adjustments,
            lifetime_adjustments=config.lifetime_adjustments
        )
        print(f"    [OK] Beräknade {len(df_network)} nätverk")
        
    except Exception as e:
        print(f"    [FALLBACK: BASELINE] KENT-beräkning misslyckades: {e}")
        print("    Använder baseline CAPEX")
        return _pre_dea_baseline(baseline)
    
    # Steg 4: Merge med baseline
    print("\n  Steg 4/4: Mergar KENT-resultat med baseline...")
    df_result = merge_kent_with_baseline(
        df_network,
        baseline.df_all_companies,
        sdf_ir=baseline.sdf_ir
    )
    
    print("\n" + "-"*60)
    print(f"  Resultat: capex_modified=True, capex_method='parameter_change'")
    print(f"            {len(df_result)} företag, wacc_used={wacc_to_use:.4f}")
    print("="*60 + "\n")
    
    return PreDeaStageOutput(
        df_all_companies=df_result,
        capex_method="parameter_change",
        capex_modified=True,
        wacc_used=wacc_to_use
    )


# =============================================================================
# METOD 4: KENT_UPLOAD
# =============================================================================

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
        print(f"  [FALLBACK: BASELINE] Kunde inte importera kent_capbase_prep: {e}")
        return _pre_dea_baseline(baseline)
    
    # Validera input
    if config.kent_file_bytes is None:
        raise ValueError("kent_file_bytes måste anges för kent_upload metod")
    
    if config.kent_user_id_network is None:
        raise ValueError("kent_user_id_network måste anges för kent_upload metod")
    
    # Steg 1: Konvertera KENT Excel till capbase_a format
    print("\n  Steg 1/3: Processar uppladdad KENT-fil...")
    print(f"    id_network: {config.kent_user_id_network}")
    print(f"    Filstorlek: {len(config.kent_file_bytes):,} bytes")
    
    try:
        kent_file = BytesIO(config.kent_file_bytes)
        
        user_capbase_a = build_capbase_a_from_kent(
            kent_file,
            network_id=config.kent_user_id_network,
            lifetime_adjustments=config.lifetime_adjustments
        )
        
        summary = get_kent_upload_summary(user_capbase_a)
        print(f"    [OK] KENT steg 1-4 klara:")
        print(f"         - {summary['n_components']} komponenter")
        print(f"         - {summary['n_existing']} befintliga, {summary['n_investments']} investeringar")
        print(f"         - Total NUAV: {summary['total_nuav_mkr']:.1f} Mkr")
        
    except Exception as e:
        print(f"    [FALLBACK: BASELINE] KENT-processning misslyckades: {e}")
        return _pre_dea_baseline(baseline)
    
    # Bestäm scenario baserat på parametrar
    has_parameter_changes = (
        config.normvalue_adjustments is not None or
        config.lifetime_adjustments is not None
    )
    
    if has_parameter_changes:
        print("\n  Scenario: KENT + parametrar (alla företag omberäknas)")
        return _kent_upload_with_parameters(baseline, config, user_capbase_a)
    else:
        print("\n  Scenario: KENT-only (endast användarens företag)")
        return _kent_upload_only(baseline, config, user_capbase_a)


def _kent_upload_only(
    baseline: BaselineStageOutput,
    config: PreDeaConfig,
    user_capbase_a: pd.DataFrame
) -> PreDeaStageOutput:
    """
    Scenario 1: KENT-only
    
    Kör steg 5-8 för ENDAST användarens företag.
    Övriga 147 företag använder baseline CAPEX med SDF periodsummor.
    """
    
    wacc_to_use = config.wacc if config.wacc else baseline.wacc
    
    # Steg 2: Kör KENT steg 5-8 för användaren
    print("\n  Steg 2/3: Kör KENT steg 5-8 för användaren...")
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
        print(f"    [OK] Kapitalkostnad_2024: {user_capex:,.0f} tkr")
        
        if 'Kapitalkostnad_Period' in df_user_network.columns:
            user_period = df_user_network.iloc[0]['Kapitalkostnad_Period']
            print(f"    [OK] Kapitalkostnad_Period: {user_period:,.0f} tkr")
        else:
            raise ValueError("Kapitalkostnad_Period saknas i KENT-output")
        
    except Exception as e:
        print(f"    [FALLBACK: BASELINE] KENT steg 5-8 misslyckades: {e}")
        return _pre_dea_baseline(baseline)
    
    # Steg 3: Bygg resultat-DataFrame
    print("\n  Steg 3/3: Bygger resultat...")
    df_result = baseline.df_all_companies.copy()
    
    # Lägg till periodsummor från SDF för alla företag (baseline)
    if 'Kapitalkostnad_Period' not in df_result.columns:
        sdf_period = baseline.sdf_ir[['REId', 'Kapitalkostnad']].rename(
            columns={'Kapitalkostnad': 'Kapitalkostnad_Period'}
        )
        df_result = df_result.merge(sdf_period, on='REId', how='left')
        print(f"    [FALLBACK: SDF] Periodsummor för {len(df_result)} företag från SDF")
    
    # Hitta och uppdatera användarens rad
    user_id_network = config.kent_user_id_network
    user_reid = f"REL{user_id_network:05d}"
    
    mask = df_result['REId'] == user_reid
    if mask.sum() == 0:
        if 'id_network' in df_result.columns:
            mask = df_result['id_network'] == user_id_network
    
    if mask.sum() == 0:
        print(f"    [FALLBACK: BASELINE] Kunde inte hitta {user_reid} i baseline")
        return _pre_dea_baseline(baseline)
    
    # Spara gamla värden för loggning
    old_capex = df_result.loc[mask, 'Kapitalkostnad_2024'].values[0]
    old_period = df_result.loc[mask, 'Kapitalkostnad_Period'].values[0] if 'Kapitalkostnad_Period' in df_result.columns else None
    
    # Uppdatera CAPEX-relaterade kolumner för användaren
    df_result.loc[mask, 'Kapitalkostnad_2024'] = user_capex
    df_result.loc[mask, 'Kapitalkostnad_Period'] = user_period
    
    if 'CAPEX' in df_result.columns:
        df_result.loc[mask, 'CAPEX'] = user_capex
    
    if 'TOTEX' in df_result.columns and 'OPEXp' in df_result.columns:
        opex = df_result.loc[mask, 'OPEXp'].values[0]
        df_result.loc[mask, 'TOTEX'] = opex + user_capex
    
    # Uppdatera övriga kolumner om de finns
    if 'Avskrivning' in df_user_network.columns and 'Avskrivning' in df_result.columns:
        df_result.loc[mask, 'Avskrivning'] = df_user_network.iloc[0]['Avskrivning']
    
    if 'Avkastning' in df_user_network.columns and 'Avkastning' in df_result.columns:
        df_result.loc[mask, 'Avkastning'] = df_user_network.iloc[0]['Avkastning']
    
    for year in [2025, 2026, 2027]:
        col = f'Kapitalkostnad_{year}'
        if col in df_user_network.columns and col in df_result.columns:
            df_result.loc[mask, col] = df_user_network.iloc[0][col]
    
    print(f"    Uppdaterade {user_reid}:")
    print(f"      Kapitalkostnad_2024: {old_capex:,.0f} -> {user_capex:,.0f} tkr")
    if old_period is not None:
        print(f"      Kapitalkostnad_Period: {old_period:,.0f} -> {user_period:,.0f} tkr")
    
    print("\n" + "-"*60)
    print(f"  Resultat: capex_modified=True, capex_method='kent_upload'")
    print(f"            KENT: 1 företag ({user_reid}), SDF-baseline: {len(df_result)-1} företag")
    print("="*60 + "\n")
    
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
    """
    
    wacc_to_use = config.wacc if config.wacc else baseline.wacc
    
    # Steg 2: Ladda baseline capbase_a
    print("\n  Steg 2/4: Laddar baseline kapitalbas...")
    try:
        capbase_data = load_capbase_a()
        n_components = len(capbase_data)
        print(f"    [OK] capbase_a.parquet: {n_components:,} komponenter")
    except FileNotFoundError as e:
        print(f"    [FALLBACK: KENT-ONLY] {e}")
        return _kent_upload_only(baseline, config, user_capbase_a)
    
    # Steg 3: Ersätt användarens komponenter
    print("\n  Steg 3/4: Ersätter användarens komponenter...")
    user_id_network = config.kent_user_id_network
    
    mask_not_user = capbase_data['id_network'] != user_id_network
    capbase_without_user = capbase_data[mask_not_user].copy()
    
    n_removed = len(capbase_data) - len(capbase_without_user)
    print(f"    Tog bort: {n_removed} komponenter (id_network={user_id_network})")
    
    capbase_combined = pd.concat([capbase_without_user, user_capbase_a], ignore_index=True)
    print(f"    Lade till: {len(user_capbase_a)} nya komponenter")
    print(f"    Total: {len(capbase_combined):,} komponenter")
    
    # Steg 4: Kör KENT för alla
    print("\n  Steg 4/4: Kör KENT steg 5-8 för alla företag...")
    if config.normvalue_adjustments:
        print(f"    Normvärde-justeringar: {len(config.normvalue_adjustments)} kategorier")
    if config.lifetime_adjustments:
        print(f"    Livslängd-justeringar: {len(config.lifetime_adjustments)} kategorier")
    print(f"    WACC: {wacc_to_use:.4f}")
    
    try:
        df_detailed, df_network = run_kent_calculations_batch(
            capbase_combined,
            wacc=wacc_to_use,
            normvalue_adjustments=config.normvalue_adjustments,
            lifetime_adjustments=config.lifetime_adjustments
        )
        print(f"    [OK] Beräknade {len(df_network)} nätverk")
        
    except Exception as e:
        print(f"    [FALLBACK: BASELINE] KENT-beräkning misslyckades: {e}")
        return _pre_dea_baseline(baseline)
    
    # Merge med baseline (inkl. SDF-fallback för periodsummor)
    print("\n  Mergar KENT-resultat med baseline...")
    df_result = merge_kent_with_baseline(
        df_network,
        baseline.df_all_companies,
        sdf_ir=baseline.sdf_ir
    )
    
    print("\n" + "-"*60)
    print(f"  Resultat: capex_modified=True, capex_method='kent_upload'")
    print(f"            {len(df_result)} företag, wacc_used={wacc_to_use:.4f}")
    print("="*60 + "\n")
    
    return PreDeaStageOutput(
        df_all_companies=df_result,
        capex_method="kent_upload",
        capex_modified=True,
        wacc_used=wacc_to_use
    )
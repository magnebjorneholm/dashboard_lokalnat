"""
pipeline/stages/pre_dea.py

Stage 2: Pre-DEA
Förbereder CAPEX/OPEX data för DEA-analys.

REFAKTORISERAD ARKITEKTUR:
- Steg 1: Bestäm användarens capbase_a (CapbaseSource)
- Steg 2: Applicera beräkningsmetod (CapexMethod)

Denna separation möjliggör alla kombinationer av:
- Datakälla: baseline / kent_upload
- Metod: baseline / wacc_scaling / parameter_change

Kombinationsmatris (6 kombinationer):
┌─────────────────┬──────────────┬────────────────┬───────────────────┐
│ Source \ Method │ BASELINE     │ WACC_SCALING   │ PARAMETER_CHANGE  │
├─────────────────┼──────────────┼────────────────┼───────────────────┤
│ BASELINE        │ Direkt       │ Skala alla     │ KENT 5-8 alla     │
│ KENT_UPLOAD     │ KENT för usr │ KENT+skala     │ Ersätt+KENT alla  │
└─────────────────┴──────────────┴────────────────┴───────────────────┘
"""

import pandas as pd
from io import BytesIO
from typing import Optional, Tuple

from config.case_definition import PreDeaConfig, CapbaseSource, CapexMethod
from pipeline.stages.stage_outputs import BaselineStageOutput, PreDeaStageOutput
from calculations.wacc_scaling import calculate_wacc_scaled_capex
from calculations.kent_calculations import load_capbase_a, run_kent_calculations_batch
from calculations.data_mapping import merge_kent_with_baseline


# =============================================================================
# HUVUDFUNKTION
# =============================================================================

def stage_pre_dea(
    baseline: BaselineStageOutput,
    config: PreDeaConfig,
    user_id_network: int
) -> PreDeaStageOutput:
    """
    Stage 2: Förbered data för DEA-analys.
    
    Tvåstegsprocess:
    1. Hämta användarens capbase_a baserat på CapbaseSource
    2. Applicera beräkningsmetod baserat på CapexMethod
    
    Args:
        baseline: Output från Baseline stage
        config: PreDeaConfig med source och method
        user_id_network: Användarens id_network
        
    Returns:
        PreDeaStageOutput med:
        - df_all_companies: 148 rows, potentiellt modifierad CAPEX/OPEX
        - capbase_source: Källa som användes
        - capex_method: Metod som användes
        - capex_modified: True om CAPEX ändrades
        - wacc_used: WACC som användes
    """
    print(f"\n=== Pre-DEA Stage ===")
    print(f"  CapbaseSource: {config.capbase_source.value}")
    print(f"  CapexMethod: {config.method.value}")
    
    # STEG 1: Hämta användarens capbase_a
    user_capbase, source_used = _get_user_capbase(config, user_id_network)
    
    # STEG 2: Applicera beräkningsmetod
    result = _apply_capex_method(
        baseline=baseline,
        config=config,
        user_capbase=user_capbase,
        user_id_network=user_id_network,
        source_used=source_used
    )
    
    print(f"  Resultat: capex_modified={result.capex_modified}")
    if result.wacc_used:
        print(f"  WACC använd: {result.wacc_used:.4f}")
    
    return result


# =============================================================================
# STEG 1: CAPBASE SOURCE - Hämta användarens capbase_a
# =============================================================================

def _get_user_capbase(
    config: PreDeaConfig,
    user_id_network: int
) -> Tuple[Optional[pd.DataFrame], str]:
    """
    Hämtar användarens capbase_a baserat på CapbaseSource.
    
    VIKTIGT: Denna funktion returnerar data i capbase_a format.
    - BASELINE: Returnerar None (baseline data används direkt i method-steget)
    - KENT_UPLOAD: Konverteras via kent_capbase_prep.py (steg 1-4)
    
    Steg 5-8 (KENT-beräkningar) körs sedan i _apply_capex_method().
    
    Args:
        config: PreDeaConfig med source-inställningar
        user_id_network: Användarens id_network
        
    Returns:
        Tuple av (user_capbase DataFrame eller None, source_used sträng)
    """
    
    if config.capbase_source == CapbaseSource.BASELINE:
        # Baseline: Ingen custom capbase, använd befintlig data
        print("  Source: Baseline (ingen custom capbase)")
        return None, "baseline"
    
    elif config.capbase_source == CapbaseSource.KENT_UPLOAD:
        # KENT-upload: Kräver konvertering via steg 1-4
        print("  Source: KENT-upload (konverterar fil...)")
        user_capbase = _load_kent_upload(config, user_id_network)
        return user_capbase, "kent_upload"
    
    else:
        raise ValueError(f"Okänd CapbaseSource: {config.capbase_source}")


def _load_kent_upload(config: PreDeaConfig, user_id_network: int) -> pd.DataFrame:
    """
    Konverterar uppladdad KENT-fil till capbase_a format.
    
    Detta är ENDAST steg 1-4 (konvertering från Ei:s Excel-mall).
    Steg 5-8 (beräkning av kapitalkostnader) körs senare i _apply_capex_method()
    beroende på vald CapexMethod.
    
    Args:
        config: PreDeaConfig med kent_file_bytes
        user_id_network: Användarens id_network
        
    Returns:
        DataFrame i capbase_a format
    """
    from calculations.kent_capbase_prep import build_capbase_a_from_kent, get_kent_upload_summary
    
    if config.kent_file_bytes is None:
        raise ValueError("kent_file_bytes måste anges för KENT_UPLOAD source")
    
    print("    Konverterar KENT-fil till capbase_a format (steg 1-4)...")
    
    kent_file = BytesIO(config.kent_file_bytes)
    user_capbase = build_capbase_a_from_kent(
        kent_file,
        network_id=user_id_network,
        lifetime_adjustments=None  # Livslängder appliceras i steg 5-8, inte här
    )
    
    summary = get_kent_upload_summary(user_capbase)
    print(f"    KENT steg 1-4 klara:")
    print(f"      - {summary['n_components']} komponenter")
    print(f"      - {summary['n_existing']} befintliga, {summary['n_investments']} investeringar")
    print(f"      - Total NUAV: {summary['total_nuav_mkr']:.1f} Mkr")
    
    return user_capbase


# =============================================================================
# STEG 2: CAPEX METHOD - Applicera beräkningsmetod
# =============================================================================

def _apply_capex_method(
    baseline: BaselineStageOutput,
    config: PreDeaConfig,
    user_capbase: Optional[pd.DataFrame],
    user_id_network: int,
    source_used: str
) -> PreDeaStageOutput:
    """
    Applicerar beräkningsmetod på data.
    
    Logik:
    - BASELINE method + baseline source → Direkt från baseline
    - BASELINE method + custom source → KENT 5-8 för användaren, baseline för övriga
    - WACC_SCALING → Skala avkastning för alla (efter ev. KENT för användaren)
    - PARAMETER_CHANGE → KENT 5-8 för alla (med ev. ersättning av användaren)
    
    Args:
        baseline: Output från Baseline stage
        config: PreDeaConfig med method-inställningar
        user_capbase: Användarens capbase_a (None om baseline source)
        user_id_network: Användarens id_network
        source_used: Sträng som beskriver källan
        
    Returns:
        PreDeaStageOutput med resultat
    """
    
    method = config.method
    has_custom_source = (source_used != "baseline")
    
    print(f"  Method: {method.value}" + (f" (med custom source: {source_used})" if has_custom_source else ""))
    
    # === BASELINE method ===
    if method == CapexMethod.BASELINE:
        if has_custom_source:
            return _method_baseline_with_custom_source(
                baseline, user_capbase, user_id_network, source_used
            )
        else:
            return _method_baseline_pure(baseline, user_id_network)
    
    # === WACC_SCALING method ===
    elif method == CapexMethod.WACC_SCALING:
        return _method_wacc_scaling(
            baseline, user_capbase, user_id_network, source_used, config
        )
    
    # === PARAMETER_CHANGE method ===
    elif method == CapexMethod.PARAMETER_CHANGE:
        return _method_parameter_change(
            baseline, user_capbase, user_id_network, source_used, config
        )
    
    else:
        raise ValueError(f"Okänd CapexMethod: {method}")


# =============================================================================
# METHOD IMPLEMENTATIONS
# =============================================================================

def _method_baseline_pure(
    baseline: BaselineStageOutput,
    user_id_network: int
) -> PreDeaStageOutput:
    """
    BASELINE method med BASELINE source.
    
    Enklaste fallet: returnera baseline direkt utan modifiering.
    """
    print("    → Direkt baseline (ingen beräkning)")
    
    return PreDeaStageOutput(
        df_all_companies=baseline.df_all_companies.copy(),
        capbase_source="baseline",
        capex_method="baseline",
        capex_modified=False,
        wacc_used=None,
        user_id_network=user_id_network
    )


def _method_baseline_with_custom_source(
    baseline: BaselineStageOutput,
    user_capbase: pd.DataFrame,
    user_id_network: int,
    source_used: str
) -> PreDeaStageOutput:
    """
    BASELINE method med custom source (KENT_UPLOAD).
    
    Kör KENT steg 5-8 för ENDAST användarens företag med baseline parametrar.
    Övriga 147 företag använder baseline direkt (ingen omberäkning).
    
    Detta är scenariot där användaren har laddat upp sin KENT-fil men
    inte vill ändra några parametrar - bara se resultatet med sin egen data.
    """
    print("    → KENT steg 5-8 för användaren (baseline WACC och parametrar)")
    print("    → Baseline för övriga 147 företag")
    
    # Kör KENT steg 5-8 för användarens komponenter med baseline WACC
    _, df_user_network = run_kent_calculations_batch(
        user_capbase,
        wacc=baseline.wacc,  # Baseline WACC (0.0453)
        normvalue_adjustments=None,  # Baseline normvärden
        lifetime_adjustments=None    # Baseline livslängder
    )
    
    # Merge: ersätt användarens rad, behåll baseline för övriga
    df_result = merge_kent_with_baseline(
        df_user_network,
        baseline.df_all_companies,
        sdf_ir=baseline.sdf_ir
    )
    
    return PreDeaStageOutput(
        df_all_companies=df_result,
        capbase_source=source_used,
        capex_method="baseline",
        capex_modified=True,  # Användarens CAPEX ändrades (pga ny capbase_a)
        wacc_used=baseline.wacc,
        user_id_network=user_id_network
    )


def _method_wacc_scaling(
    baseline: BaselineStageOutput,
    user_capbase: Optional[pd.DataFrame],
    user_id_network: int,
    source_used: str,
    config: PreDeaConfig
) -> PreDeaStageOutput:
    """
    WACC_SCALING method.
    
    Implementerar Alternativ A (enklast):
    1. Om custom source: Kör KENT 5-8 för användaren med BASELINE WACC
    2. Merge med baseline för övriga 147
    3. Skala ALLA 148 företag med ny WACC
    
    Detta ger samma resultat som att köra KENT med ny WACC för användaren
    och skala övriga, men är enklare att implementera.
    """
    if config.wacc is None:
        raise ValueError("WACC måste anges för WACC_SCALING method")
    
    print(f"    WACC-scaling: {baseline.wacc:.4f} → {config.wacc:.4f}")
    
    if user_capbase is not None:
        # Custom source: Kör KENT för användaren med BASELINE WACC först
        print("    → Steg 1: KENT 5-8 för användaren (baseline WACC)")
        
        _, df_user_network = run_kent_calculations_batch(
            user_capbase,
            wacc=baseline.wacc,  # Baseline WACC - skalas sedan
            normvalue_adjustments=None,
            lifetime_adjustments=None
        )
        
        # Merge användarens resultat med baseline
        print("    → Steg 2: Merge med baseline")
        df_merged = merge_kent_with_baseline(
            df_user_network,
            baseline.df_all_companies,
            sdf_ir=baseline.sdf_ir
        )
        
        # Skala ALLA 148 företag med ny WACC
        print("    → Steg 3: Skala alla 148 med WACC-kvot")
        df_result = calculate_wacc_scaled_capex(
            df_merged,
            new_wacc=config.wacc,
            baseline_wacc=baseline.wacc
        )
    else:
        # Baseline source: Endast WACC-skalning av befintlig data
        print("    → Skala alla 148 med WACC-kvot")
        df_result = calculate_wacc_scaled_capex(
            baseline.df_all_companies,
            new_wacc=config.wacc,
            baseline_wacc=baseline.wacc
        )
    
    return PreDeaStageOutput(
        df_all_companies=df_result,
        capbase_source=source_used,
        capex_method="wacc_scaling",
        capex_modified=True,
        wacc_used=config.wacc,
        user_id_network=user_id_network
    )


def _method_parameter_change(
    baseline: BaselineStageOutput,
    user_capbase: Optional[pd.DataFrame],
    user_id_network: int,
    source_used: str,
    config: PreDeaConfig
) -> PreDeaStageOutput:
    """
    PARAMETER_CHANGE method.
    
    Kör KENT steg 5-8 för ALLA 148 företag med nya parametrar.
    Om custom source: Ersätt användarens komponenter i capbase_a först.
    
    VIKTIGT: Normvärden och livslängder appliceras här i steg 5-8,
    INTE i steg 1-4 (KENT-konvertering). Detta säkerställer att
    parameterändringar gäller för ALLA företag, inte bara det uppladdade.
    """
    print("    Parameter-ändringar: Kör KENT steg 5-8 för alla 148 företag")
    if config.normvalue_adjustments:
        print(f"      - {len(config.normvalue_adjustments)} normvärdesjusteringar")
    if config.lifetime_adjustments:
        print(f"      - {len(config.lifetime_adjustments)} livslängdsjusteringar")
    
    wacc_to_use = config.wacc if config.wacc else baseline.wacc
    
    # Ladda baseline capbase_a
    try:
        capbase_data = load_capbase_a()
        print(f"    Laddade capbase_a: {len(capbase_data):,} komponenter")
    except FileNotFoundError as e:
        print(f"    FEL: {e}")
        print("    → Fallback till baseline")
        return _method_baseline_pure(baseline, user_id_network)
    
    # Om custom source: ersätt användarens komponenter
    if user_capbase is not None:
        n_user_original = (capbase_data['id_network'] == user_id_network).sum()
        print(f"    Ersätter användarens komponenter: {n_user_original} → {len(user_capbase)}")
        
        # Ta bort befintliga komponenter för användaren
        mask_not_user = capbase_data['id_network'] != user_id_network
        capbase_without_user = capbase_data[mask_not_user].copy()
        
        # Lägg till användarens nya/modifierade komponenter
        capbase_data = pd.concat([capbase_without_user, user_capbase], ignore_index=True)
        print(f"    Total capbase_a: {len(capbase_data):,} komponenter")
    
    # Kör KENT steg 5-8 för alla med nya parametrar
    try:
        _, df_network = run_kent_calculations_batch(
            capbase_data,
            wacc=wacc_to_use,
            normvalue_adjustments=config.normvalue_adjustments,
            lifetime_adjustments=config.lifetime_adjustments
        )
        print(f"    KENT-beräkningar klara: {len(df_network)} nätverk")
    except Exception as e:
        print(f"    FEL i KENT-beräkningar: {e}")
        print("    → Fallback till baseline")
        return _method_baseline_pure(baseline, user_id_network)
    
    # Merge med baseline för övrig data (volymer, DEA-outputs etc.)
    df_result = merge_kent_with_baseline(
        df_network,
        baseline.df_all_companies,
        sdf_ir=baseline.sdf_ir
    )
    
    return PreDeaStageOutput(
        df_all_companies=df_result,
        capbase_source=source_used,
        capex_method="parameter_change",
        capex_modified=True,
        wacc_used=wacc_to_use,
        user_id_network=user_id_network
    )
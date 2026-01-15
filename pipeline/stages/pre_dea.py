"""
pipeline/stages/pre_dea.py

Stage 2: Pre-DEA
Prepares CAPEX/OPEX data for DEA analysis.

REFACTORED ARCHITECTURE:
- Step 1: Determine user's capbase_a (CapbaseSource)
- Step 2: Apply calculation method (CapexMethod)

This separation enables all combinations of:
- Data source: baseline / var_scaled / kent_upload
- Method: baseline / wacc_scaling / parameter_change

Combination matrix (9 combinations):
+------------------+--------------+----------------+-------------------+
| Source \ Method  | BASELINE     | WACC_SCALING   | PARAMETER_CHANGE  |
+------------------+--------------+----------------+-------------------+
| BASELINE         | Direct       | Scale all      | KENT 5-8 all      |
| VAR_SCALED       | KENT for usr | KENT+scale     | Replace+KENT all  |
| KENT_UPLOAD      | KENT for usr | KENT+scale     | Replace+KENT all  |
+------------------+--------------+----------------+-------------------+
"""

import pandas as pd
from io import BytesIO
from typing import Optional, Tuple

from config.case_definition import PreDeaConfig, CapbaseSource, CapexMethod
from pipeline.stages.stage_outputs import BaselineStageOutput, PreDeaStageOutput
from calculations.wacc_scaling import calculate_wacc_scaled_capex
from calculations.kent_calculations import run_kent_calculations_batch
from calculations.data_mapping import merge_kent_with_baseline
from data_loaders.rab_data import load_capbase_a  


# =============================================================================
# MAIN FUNCTION
# =============================================================================

def stage_pre_dea(
    baseline: BaselineStageOutput,
    config: PreDeaConfig,
    user_id_network: int
) -> PreDeaStageOutput:
    """
    Stage 2: Prepare data for DEA analysis.
    
    Two-step process:
    1. Get user's capbase_a based on CapbaseSource
    2. Apply calculation method based on CapexMethod
    
    Args:
        baseline: Output from Baseline stage
        config: PreDeaConfig with source and method
        user_id_network: User's id_network
        
    Returns:
        PreDeaStageOutput with:
        - df_all_companies: 148 rows, potentially modified CAPEX/OPEX
        - capbase_source: Source that was used
        - capex_method: Method that was used
        - capex_modified: True if CAPEX was changed
        - wacc_used: WACC that was used
    """
    print(f"\n=== Pre-DEA Stage ===")
    print(f"  CapbaseSource: {config.capbase_source.value}")
    print(f"  CapexMethod: {config.method.value}")
    
    # STEP 1: Get user's capbase_a
    user_capbase, source_used = _get_user_capbase(config, user_id_network)
    
    # STEP 2: Apply calculation method
    result = _apply_capex_method(
        baseline=baseline,
        config=config,
        user_capbase=user_capbase,
        user_id_network=user_id_network,
        source_used=source_used
    )
    
    print(f"  Result: capex_modified={result.capex_modified}")
    if result.wacc_used:
        print(f"  WACC used: {result.wacc_used:.4f}")
    
    return result


# =============================================================================
# STEP 1: CAPBASE SOURCE - Get user's capbase_a
# =============================================================================

def _get_user_capbase(
    config: PreDeaConfig,
    user_id_network: int
) -> Tuple[Optional[pd.DataFrame], str]:
    """
    Get user's capbase_a based on CapbaseSource.
    
    IMPORTANT: This function returns data in capbase_a format.
    - BASELINE: Returns None (baseline data used directly in method step)
    - VAR_SCALED: Returns DataFrame from config (already capbase_a format with scaling applied)
    - KENT_UPLOAD: Converted via kent_capbase_prep.py (steps 1-4)
    
    Steps 5-8 (KENT calculations) are then run in _apply_capex_method().
    
    Args:
        config: PreDeaConfig with source settings
        user_id_network: User's id_network
        
    Returns:
        Tuple of (user_capbase DataFrame or None, source_used string)
    """
    
    if config.capbase_source == CapbaseSource.BASELINE:
        # Baseline: No custom capbase, use existing data
        print("  Source: Baseline (no custom capbase)")
        return None, "baseline"
    
    elif config.capbase_source == CapbaseSource.VAR_SCALED:
        # Variable scaled: Already in capbase_a format with scaling applied
        print("  Source: Variable scaled (from config)")
        user_capbase = _load_var_scaled(config, user_id_network)
        return user_capbase, "var_scaled"
    
    elif config.capbase_source == CapbaseSource.KENT_UPLOAD:
        # KENT upload: Requires conversion via steps 1-4
        print("  Source: KENT upload (converting file...)")
        user_capbase = _load_kent_upload(config, user_id_network)
        return user_capbase, "kent_upload"
    
    else:
        raise ValueError(f"Unknown CapbaseSource: {config.capbase_source}")


def _load_var_scaled(config: PreDeaConfig, user_id_network: int) -> pd.DataFrame:
    """
    Get variable-scaled capbase from config.
    
    Variable-scaled data is already in capbase_a format with scaling applied
    to ordinarie components - no conversion needed.
    
    Args:
        config: PreDeaConfig with user_capbase_scaled
        user_id_network: User's id_network
        
    Returns:
        DataFrame in capbase_a format
    """
    if config.user_capbase_scaled is None:
        raise ValueError("CapbaseSource=VAR_SCALED but user_capbase_scaled=None")
    
    user_capbase = config.user_capbase_scaled.copy()
    
    # Ensure id_network is correct
    user_capbase['id_network'] = user_id_network
    
    n_components = len(user_capbase)
    if 'capbase_existing' in user_capbase.columns:
        n_existing = (user_capbase['capbase_existing'] == 1).sum()
    else:
        n_existing = n_components
    total_nuav = user_capbase['nuav_2022'].sum() / 1e6
    
    print(f"    Variable-scaled data:")
    print(f"      - {n_components} components")
    print(f"      - {n_existing} existing, {n_components - n_existing} investments/retirements")
    print(f"      - Total NUAV: {total_nuav:.1f} Mkr")
    
    return user_capbase


def _load_kent_upload(config: PreDeaConfig, user_id_network: int) -> pd.DataFrame:
    """
    Convert uploaded KENT file to capbase_a format.
    
    This is ONLY steps 1-4 (conversion from Ei's Excel template).
    Steps 5-8 (capital cost calculation) are run later in _apply_capex_method()
    depending on selected CapexMethod.
    
    Args:
        config: PreDeaConfig with kent_file_bytes
        user_id_network: User's id_network
        
    Returns:
        DataFrame in capbase_a format
    """
    from calculations.kent_capbase_prep import build_capbase_a_from_kent, get_kent_upload_summary
    
    if config.kent_file_bytes is None:
        raise ValueError("kent_file_bytes must be provided for KENT_UPLOAD source")
    
    print("    Converting KENT file to capbase_a format (steps 1-4)...")
    
    kent_file = BytesIO(config.kent_file_bytes)
    user_capbase = build_capbase_a_from_kent(
        kent_file,
        network_id=user_id_network,
        lifetime_adjustments=None  # Lifetimes applied in steps 5-8, not here
    )
    
    summary = get_kent_upload_summary(user_capbase)
    print(f"    KENT steps 1-4 complete:")
    print(f"      - {summary['n_components']} components")
    print(f"      - {summary['n_existing']} existing, {summary['n_investments']} investments")
    print(f"      - Total NUAV: {summary['total_nuav_mkr']:.1f} Mkr")
    
    return user_capbase


# =============================================================================
# STEP 2: CAPEX METHOD - Apply calculation method
# =============================================================================

def _apply_capex_method(
    baseline: BaselineStageOutput,
    config: PreDeaConfig,
    user_capbase: Optional[pd.DataFrame],
    user_id_network: int,
    source_used: str
) -> PreDeaStageOutput:
    """
    Apply calculation method to data.
    
    Logic:
    - BASELINE method + baseline source -> Direct from baseline
    - BASELINE method + custom source -> KENT 5-8 for user, baseline for others
    - WACC_SCALING -> Scale return for all (after optional KENT for user)
    - PARAMETER_CHANGE -> KENT 5-8 for all with new parameters
    """
    method = config.method
    
    # === BASELINE method ===
    if method == CapexMethod.BASELINE:
        if user_capbase is None:
            # Pure baseline - no custom source
            return _method_baseline_pure(baseline, user_id_network)
        else:
            # Custom source with baseline parameters
            return _method_baseline_with_custom_source(
                baseline, user_capbase, user_id_network, source_used
            )
    
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
        raise ValueError(f"Unknown CapexMethod: {method}")


# =============================================================================
# METHOD IMPLEMENTATIONS
# =============================================================================

def _method_baseline_pure(
    baseline: BaselineStageOutput,
    user_id_network: int
) -> PreDeaStageOutput:
    """
    BASELINE method with BASELINE source.
    
    Simplest case: return baseline directly without modification.
    """
    print("    -> Direct baseline (no calculation)")
    
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
    BASELINE method with custom source (VAR_SCALED or KENT_UPLOAD).
    
    Run KENT steps 5-8 for ONLY user's company with baseline parameters.
    Other 147 companies use baseline directly (no recalculation).
    
    This is the scenario where user has modified their capbase but
    doesn't want to change any parameters - just see result with their own data.
    """
    print("    -> KENT steps 5-8 for user, baseline for others")
    
    wacc_to_use = baseline.wacc
    
    # Run KENT steps 5-8 for user's capbase
    try:
        _, df_network = run_kent_calculations_batch(
            user_capbase,
            wacc=wacc_to_use,
            normvalue_adjustments=None,
            lifetime_adjustments=None
        )
        print(f"    KENT calculations complete for user")
    except Exception as e:
        print(f"    ERROR in KENT calculations: {e}")
        print("    -> Fallback to baseline")
        return _method_baseline_pure(baseline, user_id_network)
    
    # Merge with baseline for other 147 companies
    df_result = merge_kent_with_baseline(
        df_network,
        baseline.df_all_companies,
        sdf_ir=baseline.sdf_ir
    )
    
    return PreDeaStageOutput(
        df_all_companies=df_result,
        capbase_source=source_used,
        capex_method="baseline",
        capex_modified=True,
        wacc_used=wacc_to_use,
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
    
    If custom source: Run KENT steps 5-8 for user first (with baseline WACC),
    then scale ALL 148 companies with WACC ratio.
    
    If baseline source: Scale directly from baseline.
    """
    print("    -> WACC scaling for all 148 companies")
    
    new_wacc = config.wacc
    if new_wacc is None:
        print("    WARNING: WACC_SCALING without wacc, using baseline")
        new_wacc = baseline.wacc
    
    print(f"    WACC: {baseline.wacc:.4f} -> {new_wacc:.4f}")
    
    # Step 1: If custom source, run KENT for user with baseline WACC
    if user_capbase is not None:
        print("    Step 1: KENT for user with baseline WACC...")
        try:
            _, df_network = run_kent_calculations_batch(
                user_capbase,
                wacc=baseline.wacc,
                normvalue_adjustments=None,
                lifetime_adjustments=None
            )
            df_base = merge_kent_with_baseline(
                df_network,
                baseline.df_all_companies,
                sdf_ir=baseline.sdf_ir
            )
        except Exception as e:
            print(f"    ERROR in KENT calculations: {e}")
            df_base = baseline.df_all_companies.copy()
    else:
        df_base = baseline.df_all_companies.copy()
    
    # Step 2: Scale all 148 with WACC ratio
    print("    Step 2: Scale all with WACC ratio...")
    df_result = calculate_wacc_scaled_capex(
        df_base,
        baseline_wacc=baseline.wacc,
        new_wacc=new_wacc
    )
    
    return PreDeaStageOutput(
        df_all_companies=df_result,
        capbase_source=source_used,
        capex_method="wacc_scaling",
        capex_modified=True,
        wacc_used=new_wacc,
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
    
    Run KENT steps 5-8 for ALL 148 companies with new parameters.
    If custom source: Replace user's components in capbase_a first.
    
    IMPORTANT: Normvalues and lifetimes are applied here in steps 5-8,
    NOT in steps 1-4 (KENT conversion). This ensures that parameter
    changes apply to ALL companies, not just the uploaded one.
    """
    print("    Parameter changes: Run KENT steps 5-8 for all 148 companies")
    if config.normvalue_adjustments:
        print(f"      - {len(config.normvalue_adjustments)} normvalue adjustments")
    if config.lifetime_adjustments:
        print(f"      - {len(config.lifetime_adjustments)} lifetime adjustments")
    
    wacc_to_use = config.wacc if config.wacc else baseline.wacc
    
    # Load baseline capbase_a
    try:
        capbase_data = load_capbase_a()
        print(f"    Loaded capbase_a: {len(capbase_data):,} components")
    except FileNotFoundError as e:
        print(f"    ERROR: {e}")
        print("    -> Fallback to baseline")
        return _method_baseline_pure(baseline, user_id_network)
    
    # If custom source: replace user's components
    if user_capbase is not None:
        n_user_original = (capbase_data['id_network'] == user_id_network).sum()
        print(f"    Replacing user's components: {n_user_original} -> {len(user_capbase)}")
        
        # Remove existing components for user
        mask_not_user = capbase_data['id_network'] != user_id_network
        capbase_without_user = capbase_data[mask_not_user].copy()
        
        # Add user's new/modified components
        capbase_data = pd.concat([capbase_without_user, user_capbase], ignore_index=True)
        print(f"    Total capbase_a: {len(capbase_data):,} components")
    
    # Run KENT steps 5-8 for all with new parameters
    try:
        _, df_network = run_kent_calculations_batch(
            capbase_data,
            wacc=wacc_to_use,
            normvalue_adjustments=config.normvalue_adjustments,
            lifetime_adjustments=config.lifetime_adjustments
        )
        print(f"    KENT calculations complete: {len(df_network)} networks")
    except Exception as e:
        print(f"    ERROR in KENT calculations: {e}")
        print("    -> Fallback to baseline")
        return _method_baseline_pure(baseline, user_id_network)
    
    # Merge with baseline for other data (volumes, DEA outputs, etc.)
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
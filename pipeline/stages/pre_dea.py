"""
pipeline/stages/pre_dea.py

Stage 2: Pre-DEA
Prepares CAPEX/OPEX data for DEA analysis.

REFACTORED ARCHITECTURE:
- Step 1: Determine user's capbase_a (CapbaseSource)
- Step 2: Apply calculation method (CapexMethod)

This separation enables all combinations of:
- Data source: baseline / var_scaled / kent_upload
- Method: baseline / parameter_change

No print statements - logging handled by PipelineDebugLogger.
"""

import pandas as pd
from io import BytesIO
from typing import Optional, Tuple

from config.case_definition import PreDeaConfig, CapbaseSource, CapexMethod
from pipeline.stages.stage_outputs import BaselineStageOutput, PreDeaStageOutput
from calculations.capex.wacc_calculations import CAPMInputs, WACCResult, calculate_wacc, BASELINE_WACC, BASELINE_CAPM, BASELINE_DERIVED
from calculations.capex.kent_calculations import run_kent_calculations_batch
from calculations.capex.data_mapping import merge_kent_with_baseline
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

    Three-step process:
    1. Get user's capbase_a based on CapbaseSource
    2. Apply calculation method based on CapexMethod
    3. Apply OPEX scaling (4.1.1) and override (40.1.1)

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
        - opex_modified: True if OPEX scaling/override applied
        - wacc_used: WACC that was used
    """
    from config.column_names import COL_CONTROLLABLE_AVG, COL_TOTEX, COL_CAPITAL_COST_2024

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

    # STEP 3: Apply OPEX parameter scaling (4.1.1) and variable override (40.1.1)
    opex_modified = False
    if config.opex_scaling is not None or config.opex_override is not None:
        df = result.df_all_companies.copy()

        # 4.1.1 — Scale adjustable OPEX for all 148 companies
        if config.opex_scaling is not None:
            df[COL_CONTROLLABLE_AVG] *= config.opex_scaling
            df[COL_TOTEX] = df[COL_CONTROLLABLE_AVG] + df[COL_CAPITAL_COST_2024]
            opex_modified = True

        # 40.1.1 — Override user's OPEXp (trumps scaling for that company)
        if config.opex_override is not None:
            user_reid = f"REL{user_id_network:05d}"
            mask = df["REId"] == user_reid
            df.loc[mask, COL_CONTROLLABLE_AVG] = config.opex_override
            df.loc[mask, COL_TOTEX] = (
                config.opex_override + df.loc[mask, COL_CAPITAL_COST_2024].values[0]
            )
            opex_modified = True

        result = PreDeaStageOutput(
            df_all_companies=df,
            capbase_source=result.capbase_source,
            capex_method=result.capex_method,
            capex_modified=result.capex_modified,
            opex_modified=opex_modified,
            wacc_used=result.wacc_used,
            user_id_network=result.user_id_network,
            wacc_input_method=result.wacc_input_method,
            wacc_inputs=result.wacc_inputs,
            wacc_derived=result.wacc_derived,
            df_by_category=result.df_by_category,
        )

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
    
    Returns:
        Tuple of (capbase_a DataFrame or None, source string)
    """
    source = config.capbase_source
    
    if source == CapbaseSource.BASELINE:
        return None, "baseline"
    
    elif source == CapbaseSource.VAR_SCALED:
        if config.user_capbase_scaled is None:
            raise ValueError("VAR_SCALED source requires user_capbase_scaled")
        return config.user_capbase_scaled.copy(), "var_scaled"
    
    elif source == CapbaseSource.KENT_UPLOAD:
        if config.kent_file_bytes is None:
            raise ValueError("KENT_UPLOAD source requires kent_file_bytes")
        
        # Convert KENT Excel to capbase_a format (steps 1-4)
        from calculations.capex.kent_capbase_prep import convert_kent_to_capbase
        
        kent_capbase = convert_kent_to_capbase(
            BytesIO(config.kent_file_bytes),
            config.kent_user_id_network or user_id_network
        )
        return kent_capbase, "kent_upload"
    
    else:
        raise ValueError(f"Unknown CapbaseSource: {source}")


# =============================================================================
# STEP 2: CAPEX METHOD - Apply calculation method
# =============================================================================

def _calculate_wacc_chain(config: PreDeaConfig, baseline_wacc: float) -> dict:
    """
    Calculate WACC chain based on input method.
    
    Returns dict with:
    - wacc_used: Final WACC value
    - wacc_input_method: "capm", "derived", "direct", or "baseline"
    - wacc_inputs: 3.1.X parameters (if capm)
    - wacc_derived: 3.2.X derived values (if capm or derived)
    """
    wacc_input_method = config.wacc_input_method
    
    if wacc_input_method == "capm" and config.wacc_capm_inputs:
        # Calculate full WACC chain from CAPM inputs
        inputs = CAPMInputs(
            debt_ratio=config.wacc_capm_inputs.get("debt_ratio", BASELINE_CAPM["debt_ratio"]),
            asset_beta=config.wacc_capm_inputs.get("asset_beta", BASELINE_CAPM["asset_beta"]),
            risk_free_rate=config.wacc_capm_inputs.get("risk_free_rate", BASELINE_CAPM["risk_free_rate"]),
            market_risk_premium=config.wacc_capm_inputs.get("market_risk_premium", BASELINE_CAPM["market_risk_premium"]),
            credit_risk_premium=config.wacc_capm_inputs.get("credit_risk_premium", BASELINE_CAPM["credit_risk_premium"]),
            tax_rate=config.wacc_capm_inputs.get("tax_rate", BASELINE_CAPM["tax_rate"]),
            inflation=config.wacc_capm_inputs.get("inflation", BASELINE_CAPM["inflation"]),
        )
        result = calculate_wacc(inputs)
        
        return {
            "wacc_used": result.wacc_real_pre_tax,
            "wacc_input_method": "capm",
            "wacc_inputs": config.wacc_capm_inputs,
            "wacc_derived": {
                "equity_beta": result.equity_beta,
                "cost_of_equity_nominal": result.cost_of_equity_nominal,
                "cost_of_debt_nominal": result.cost_of_debt_nominal,
                "wacc_nominal_pre_tax": result.wacc_nominal_pre_tax,
                "wacc_real_pre_tax": result.wacc_real_pre_tax,
            }
        }
    
    elif wacc_input_method == "derived" and config.wacc_derived_inputs:
        # Calculate WACC from derived parameters
        di = config.wacc_derived_inputs
        cost_of_equity = di.get("cost_of_equity", BASELINE_DERIVED["cost_of_equity_nominal"])
        cost_of_debt = di.get("cost_of_debt", BASELINE_DERIVED["cost_of_debt_nominal"])
        debt_ratio = di.get("debt_ratio", BASELINE_CAPM["debt_ratio"])
        tax_rate = di.get("tax_rate", BASELINE_CAPM["tax_rate"])
        inflation = di.get("inflation", BASELINE_CAPM["inflation"])
        
        # WACC calculation from derived
        wacc_nominal_after_tax = (
            (1 - debt_ratio) * cost_of_equity + 
            debt_ratio * cost_of_debt * (1 - tax_rate)
        )
        wacc_nominal_pre_tax = wacc_nominal_after_tax / (1 - tax_rate)
        wacc_real_pre_tax = (1 + wacc_nominal_pre_tax) / (1 + inflation) - 1
        
        return {
            "wacc_used": wacc_real_pre_tax,
            "wacc_input_method": "derived",
            "wacc_inputs": None,
            "wacc_derived": {
                "cost_of_equity_nominal": cost_of_equity,
                "cost_of_debt_nominal": cost_of_debt,
                "debt_ratio": debt_ratio,
                "tax_rate": tax_rate,
                "inflation": inflation,
                "wacc_nominal_pre_tax": wacc_nominal_pre_tax,
                "wacc_real_pre_tax": wacc_real_pre_tax,
            }
        }
    
    elif wacc_input_method == "direct" and config.wacc is not None:
        # Direct input - only final WACC
        return {
            "wacc_used": config.wacc,
            "wacc_input_method": "direct",
            "wacc_inputs": None,
            "wacc_derived": None,
        }
    
    else:
        # Baseline
        return {
            "wacc_used": baseline_wacc,
            "wacc_input_method": "baseline",
            "wacc_inputs": None,
            "wacc_derived": None,
        }


def _apply_capex_method(
    baseline: BaselineStageOutput,
    config: PreDeaConfig,
    user_capbase: Optional[pd.DataFrame],
    user_id_network: int,
    source_used: str
) -> PreDeaStageOutput:
    """
    Apply calculation method to get final CAPEX/OPEX values.
    
    Logic:
    - BASELINE method + baseline source -> Direct from baseline
    - BASELINE method + custom source -> KENT 5-8 for user, baseline for others
    - PARAMETER_CHANGE -> KENT 5-8 for all with new parameters (incl WACC changes)
    """
    method = config.method
    
    # Calculate WACC chain
    wacc_chain = _calculate_wacc_chain(config, baseline.wacc)
    
    # === BASELINE method ===
    if method == CapexMethod.BASELINE:
        if user_capbase is None:
            return _method_baseline_pure(baseline, user_id_network, wacc_chain)
        else:
            return _method_baseline_with_custom_source(
                baseline, user_capbase, user_id_network, source_used, wacc_chain
            )
    
    # === PARAMETER_CHANGE method (includes WACC-only changes) ===
    elif method == CapexMethod.PARAMETER_CHANGE:
        return _method_parameter_change(
            baseline, user_capbase, user_id_network, source_used, config, wacc_chain
        )
    
    else:
        raise ValueError(f"Unknown CapexMethod: {method}")


# =============================================================================
# METHOD IMPLEMENTATIONS
# =============================================================================

def _method_baseline_pure(
    baseline: BaselineStageOutput,
    user_id_network: int,
    wacc_chain: dict
) -> PreDeaStageOutput:
    """BASELINE method with BASELINE source. Return baseline directly."""
    
    # Load baseline category data for M1/M2 output
    from data_loaders.rab_data import load_capcost_a
    try:
        df_by_category = load_capcost_a()
    except FileNotFoundError:
        df_by_category = None
    
    return PreDeaStageOutput(
        df_all_companies=baseline.df_all_companies.copy(),
        capbase_source="baseline",
        capex_method="baseline",
        capex_modified=False,
        wacc_used=wacc_chain["wacc_used"],
        user_id_network=user_id_network,
        wacc_input_method=wacc_chain["wacc_input_method"],
        wacc_inputs=wacc_chain["wacc_inputs"],
        wacc_derived=wacc_chain["wacc_derived"],
        df_by_category=df_by_category,
    )


def _method_baseline_with_custom_source(
    baseline: BaselineStageOutput,
    user_capbase: pd.DataFrame,
    user_id_network: int,
    source_used: str,
    wacc_chain: dict
) -> PreDeaStageOutput:
    """
    BASELINE method with custom source (VAR_SCALED or KENT_UPLOAD).
    Run KENT steps 5-8 for ONLY user's company with baseline parameters.
    """
    wacc_to_use = wacc_chain["wacc_used"]
    
    try:
        _, df_network, df_category_user = run_kent_calculations_batch(
            user_capbase,
            wacc=wacc_to_use,
            normvalue_adjustments=None,
            lifetime_adjustments=None,
            return_detailed=False
        )
    except Exception as e:
        # Fallback to baseline on error
        return _method_baseline_pure(baseline, user_id_network, wacc_chain)
    
    df_result = merge_kent_with_baseline(
        df_network,
        baseline.df_all_companies,
        sdf_ir=baseline.sdf_ir
    )
    
    # Combine user's category data with baseline for other companies
    from data_loaders.rab_data import load_capcost_a
    try:
        df_cat_baseline = load_capcost_a()
        # Replace user's data with calculated
        df_cat_others = df_cat_baseline[df_cat_baseline['id_network'] != user_id_network]
        df_by_category = pd.concat([df_cat_others, df_category_user], ignore_index=True)
    except FileNotFoundError:
        df_by_category = df_category_user
    
    return PreDeaStageOutput(
        df_all_companies=df_result,
        capbase_source=source_used,
        capex_method="baseline",
        capex_modified=True,
        wacc_used=wacc_to_use,
        user_id_network=user_id_network,
        wacc_input_method=wacc_chain["wacc_input_method"],
        wacc_inputs=wacc_chain["wacc_inputs"],
        wacc_derived=wacc_chain["wacc_derived"],
        df_by_category=df_by_category,
    )


def _method_parameter_change(
    baseline: BaselineStageOutput,
    user_capbase: Optional[pd.DataFrame],
    user_id_network: int,
    source_used: str,
    config: PreDeaConfig,
    wacc_chain: dict
) -> PreDeaStageOutput:
    """
    PARAMETER_CHANGE method.
    Run KENT steps 5-8 for ALL 148 companies with new parameters.
    """
    wacc_to_use = wacc_chain["wacc_used"]
    
    # Load baseline capbase_a
    try:
        capbase_data = load_capbase_a()
    except FileNotFoundError:
        return _method_baseline_pure(baseline, user_id_network, wacc_chain)
    
    # If custom source: replace user's components
    if user_capbase is not None:
        mask_not_user = capbase_data['id_network'] != user_id_network
        capbase_without_user = capbase_data[mask_not_user].copy()
        capbase_data = pd.concat([capbase_without_user, user_capbase], ignore_index=True)
    
    # Run KENT steps 5-8 for all with new parameters
    try:
        _, df_network, df_by_category = run_kent_calculations_batch(
            capbase_data,
            wacc=wacc_to_use,
            normvalue_adjustments=config.normvalue_adjustments,
            lifetime_adjustments=config.lifetime_adjustments,
            return_detailed=False
        )
    except Exception:
        return _method_baseline_pure(baseline, user_id_network, wacc_chain)
    
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
        user_id_network=user_id_network,
        wacc_input_method=wacc_chain["wacc_input_method"],
        wacc_inputs=wacc_chain["wacc_inputs"],
        wacc_derived=wacc_chain["wacc_derived"],
        df_by_category=df_by_category,
    )



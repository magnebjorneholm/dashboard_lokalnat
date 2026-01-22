"""
pipeline/stages/post_dea.py

Stage 5: Post-DEA
Calculates efficiency requirements, incentive adjustments, adjustable costs,
and assembles revenue frame.

No print statements - logging handled by PipelineDebugLogger.
"""

import pandas as pd
from typing import Optional

from config import PostDeaConfig
from config.case_definition import PaverkbaraMethod
from pipeline.stages.stage_outputs import (
    DeaStageOutput,
    PreDeaStageOutput,
    BaselineStageOutput,
    PostDeaStageOutput,
)
from calculations.effektiviseringskrav import calculate_effkrav_for_dataframe
from calculations.paverkbara_calculations import calculate_paverkbara_with_effkrav, get_paverkbara_from_sdf
from calculations.intaktsram_assembly import assemble_intaktsram, extract_user_intaktsram
from calculations.incentive_calculations import calculate_all_incentives
from data_loaders.incentive_data import (
    load_incentive_data,
    prepare_incentive_input,
    get_incentive_summary_by_reid,
    apply_variable_overrides,
)

from pipeline.post_dea_capex_helpers import get_return_per_year, get_capex_period_sum


# =============================================================================
# MAIN FUNCTION
# =============================================================================

def stage_post_dea(
    dea: DeaStageOutput,
    pre_dea: PreDeaStageOutput,
    baseline: BaselineStageOutput,
    config: PostDeaConfig,
    user_reid: str
) -> PostDeaStageOutput:
    """
    Stage 5: Calculate efficiency requirements, incentives, adjustable costs, and revenue frame.
    
    Process:
    1. Calculate efficiency requirements for all 148 companies
    2. Calculate adjustable costs (OPEX or TOTEX)
    3. Prepare capital costs based on Pre-DEA method
    4. Calculate incentive adjustments (quality, network loss, load)
    5. Assemble revenue frame with all components incl. incentives
    6. Extract user's specific revenue frame
    
    Args:
        dea: Output from DEA stage (efficiency, potential for all 148)
        pre_dea: Output from Pre-DEA stage (CAPEX data + metadata)
        baseline: Output from Baseline stage (SDF data)
        config: PostDeaConfig with truncation, customer sharing, realization time, etc.
        user_reid: REId for user's company
        
    Returns:
        PostDeaStageOutput with all calculated components
    """
    
    # STEP 1: Calculate efficiency requirements for all 148 companies
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
    
    # STEP 2: Prepare adjustable costs baseline from SDF
    sdf_paverkbara = get_paverkbara_from_sdf(
        sdf_ir=baseline.sdf_ir,
        sdf_paverkbara=baseline.sdf_paverkbara
    )
    
    # STEP 3: Calculate adjustable costs with efficiency requirements
    if config.paverkbara_method == PaverkbaraMethod.TOTEX:
        capex_for_paverkbara = get_capex_period_sum(pre_dea, baseline)
    else:
        capex_for_paverkbara = pd.DataFrame({'REId': pre_dea.df_all_companies['REId']})
    
    all_paverkbara = calculate_paverkbara_with_effkrav(
        effkrav_data=all_effkrav,
        sdf_baseline=sdf_paverkbara,
        capex_data=capex_for_paverkbara,
        method=config.paverkbara_method.value
    )
    
    # STEP 4: Prepare capital cost for revenue frame
    capex_for_intaktsram = get_capex_period_sum(pre_dea, baseline)
    
    # STEP 5: Calculate incentive adjustments
    all_incentives = _calculate_incentive_adjustments(
        pre_dea=pre_dea,
        baseline=baseline,
        config=config,
        user_reid=user_reid
    )
    
    # STEP 6: Assemble revenue frame
    all_intaktsram = assemble_intaktsram(
        capex_result=capex_for_intaktsram,
        paverkbara_result=all_paverkbara,
        sdf_baseline=baseline.sdf_ir,
        incentive_result=all_incentives
    )
    
    # Extract user's specific data
    user_intaktsram = extract_user_intaktsram(all_intaktsram, user_reid)
    user_effkrav_proc = all_effkrav[all_effkrav['REId'] == user_reid]['Effkrav_proc'].iloc[0]
    
    return PostDeaStageOutput(
        user_reid=user_reid,
        user_intaktsram=user_intaktsram,
        user_effkrav_proc=user_effkrav_proc,
        all_intaktsram=all_intaktsram,
        all_effkrav=all_effkrav,
        all_incentives=all_incentives
    )


# =============================================================================
# INCENTIVE ADJUSTMENTS
# =============================================================================

def _calculate_incentive_adjustments(
    pre_dea: PreDeaStageOutput,
    baseline: BaselineStageOutput,
    config: PostDeaConfig,
    user_reid: str
) -> Optional[pd.DataFrame]:
    """
    Calculate incentive adjustments for all companies.
    
    Three types of incentives:
    1. Quality incentive (AIT/AIF)
    2. Network loss incentive
    3. Load incentive
    
    Each incentive is capped at +/-1/3 of return per year (configurable).
    """
    try:
        incentive_data = load_incentive_data()
        
        # Get return per year
        return_per_year = get_return_per_year(pre_dea, baseline)
        
        df_input = prepare_incentive_input(incentive_data, return_per_year)
        
        # Apply variable_overrides if present
        incentive_config = getattr(config, 'incentive', None)
        if incentive_config:
            variable_overrides = getattr(incentive_config, 'variable_overrides', None)
            if variable_overrides and user_reid:
                df_input = apply_variable_overrides(df_input, user_reid, variable_overrides)
        
        incentive_params = _extract_incentive_params(config)
        
        df_calc = calculate_all_incentives(
            df_input, 
            ret_period_col='ret_period', 
            **incentive_params
        )
        
        df_summary = get_incentive_summary_by_reid(df_calc)
        
        return df_summary
        
    except FileNotFoundError:
        return None
    except Exception:
        return None


def _extract_incentive_params(config: Optional[PostDeaConfig]) -> dict:
    """Extract incentive parameters from PostDeaConfig."""
    params = {}
    
    if config is None:
        return params
    
    incentive_config = getattr(config, 'incentive', None)
    if incentive_config is None:
        return params
    
    param_mapping = {
        'kpi': 'kpi',
        'k_nf': 'k_nf',
        'sharing_netloss': 'sharing_netloss',
        'adj_max_agg': 'adj_max_agg',
        'adj_max_cemi4': 'adj_max_cemi4',
        'ait_costs': 'ait_costs',
        'aif_costs': 'aif_costs',
        'enable_quality': 'enable_quality',
        'enable_netloss': 'enable_netloss',
        'enable_load': 'enable_load',
    }
    
    for config_attr, param_name in param_mapping.items():
        if hasattr(incentive_config, config_attr):
            value = getattr(incentive_config, config_attr)
            if value is not None:
                params[param_name] = value
    
    return params
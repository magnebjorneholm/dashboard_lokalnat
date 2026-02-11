"""
pipeline/stages/post_dea.py

Stage 5: Post-DEA
Calculates efficiency requirements, incentive adjustments, adjustable costs,
and assembles revenue frame.

No print statements - logging handled by PipelineDebugLogger.
"""

import pandas as pd
from typing import Optional, Tuple

from config import PostDeaConfig
from config.case_definition import ControllableMethod
from pipeline.stages.stage_outputs import (
    DeaStageOutput,
    PreDeaStageOutput,
    BaselineStageOutput,
    PostDeaStageOutput,
)
from calculations.efficiency_requirement import calculate_eff_req_for_dataframe
from calculations.controllable_cost_calculations import calculate_controllable_with_eff_req, get_controllable_from_sdf
from calculations.revenue_frame_assembly import assemble_revenue_frame, extract_user_revenue_frame
from calculations.incentive_calculations import calculate_all_incentives
from data_loaders.incentive_data import (
    load_incentive_data,
    prepare_incentive_input,
    get_incentive_summary_by_reid,
    get_incentive_detailed_by_reid,
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
    all_eff_reqs = calculate_eff_req_for_dataframe(
        df=dea.dea_results,
        potential_col='potential',
        outlier_col='is_outlier',
        truncation_min=config.truncation_min,
        truncation_max=config.truncation_max,
        outlier_req=config.outlier_req,
        customer_sharing=config.customer_sharing,
        realization_time=config.realization_time,
        supervision_period=config.supervision_period
    )

    # STEP 2: Prepare controllable costs baseline from SDF
    sdf_controllable = get_controllable_from_sdf(
        sdf_ir=baseline.sdf_ir,
        sdf_controllable=baseline.sdf_controllable
    )

    # STEP 3: Calculate controllable costs with efficiency requirements
    if config.controllable_method == ControllableMethod.TOTEX:
        capex_for_controllable = get_capex_period_sum(pre_dea, baseline)
    else:
        capex_for_controllable = pd.DataFrame({'REId': pre_dea.df_all_companies['REId']})

    all_controllable = calculate_controllable_with_eff_req(
        eff_req_data=all_eff_reqs,
        sdf_baseline=sdf_controllable,
        capex_data=capex_for_controllable,
        method=config.controllable_method.value
    )

    # STEP 4: Prepare capital cost for revenue frame
    capex_for_revenue_frame = get_capex_period_sum(pre_dea, baseline)
    
    # STEP 5: Calculate incentive adjustments
    all_incentives, all_incentives_full = _calculate_incentive_adjustments(
        pre_dea=pre_dea,
        baseline=baseline,
        config=config,
        user_reid=user_reid
    )
    
    # Extract user's detailed incentive data (per-year breakdown)
    user_incentive_details = None
    if all_incentives_full is not None:
        user_incentive_details = get_incentive_detailed_by_reid(all_incentives_full, user_reid)
    
    # STEP 6: Assemble revenue frame
    all_revenue_frames = assemble_revenue_frame(
        capex_result=capex_for_revenue_frame,
        controllable_result=all_controllable,
        sdf_baseline=baseline.sdf_ir,
        incentive_result=all_incentives
    )

    # Extract user's specific data
    user_revenue_frame = extract_user_revenue_frame(all_revenue_frames, user_reid)
    from config.column_names import COL_EFF_REQ_ANNUAL
    user_eff_req_pct = all_eff_reqs[all_eff_reqs['REId'] == user_reid][COL_EFF_REQ_ANNUAL].iloc[0]

    return PostDeaStageOutput(
        user_reid=user_reid,
        user_revenue_frame=user_revenue_frame,
        user_eff_req_pct=user_eff_req_pct,
        all_revenue_frames=all_revenue_frames,
        all_eff_reqs=all_eff_reqs,
        all_incentives=all_incentives,
        user_incentive_details=user_incentive_details
    )


# =============================================================================
# INCENTIVE ADJUSTMENTS
# =============================================================================

def _calculate_incentive_adjustments(
    pre_dea: PreDeaStageOutput,
    baseline: BaselineStageOutput,
    config: PostDeaConfig,
    user_reid: str
) -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame]]:
    """
    Calculate incentive adjustments for all companies.
    
    Three types of incentives:
    1. Quality incentive (AIT/AIF)
    2. Network loss incentive
    3. Load incentive
    
    Each incentive is capped at +/-1/3 of return per year (configurable).
    
    Returns:
        Tuple of (summary_df, full_calc_df):
        - summary_df: Aggregated per-company totals for intaktsram assembly
        - full_calc_df: Complete per-year data with all intermediate values
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
        
        return df_summary, df_calc
        
    except FileNotFoundError:
        return None, None
    except Exception:
        return None, None


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
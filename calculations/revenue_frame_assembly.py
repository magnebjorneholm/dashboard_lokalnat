"""
calculations/revenue_frame_assembly.py

Assembly of revenue frame from all components.
Sums capital cost, controllable costs, non-controllable costs, incentives, and other components.

For TOTEX method: CAPEX is reduced separately with its share of the efficiency requirement.
"""

import pandas as pd
from typing import Optional

from config.column_names import (
    COL_CAPITAL_COST_PERIOD, COL_CONTROLLABLE_PERIOD, COL_METHOD_USED,
    COL_CONTROLLABLE_BEFORE, COL_EFFICIENCY_DEDUCTION,
    COL_OPEX_BEFORE, COL_OPEX_AFTER, COL_OPEX_EFF_DEDUCTION,
    COL_CAPEX_BEFORE, COL_CAPEX_AFTER, COL_CAPEX_EFF_DEDUCTION,
    COL_OPEX_SHARE, COL_CAPEX_SHARE,
    COL_NON_CONTROLLABLE, COL_FLEXIBILITY, COL_INTERRUPTION, COL_STATE_DEDUCTION,
    COL_QUALITY_INCENTIVE, COL_NETLOSS_INCENTIVE, COL_LOAD_INCENTIVE,
    COL_INCENTIVE_TOTAL, COL_MISSING_INCENTIVE,
    COL_CAPITAL_COST_AFTER_EFF, COL_CAPITAL_COST_IN_RF,
    COL_CONTROLLABLE_IN_RF, COL_REVENUE_FRAME,
)


def assemble_revenue_frame(
    capex_result: pd.DataFrame,
    controllable_result: pd.DataFrame,
    sdf_baseline: pd.DataFrame,
    incentive_result: Optional[pd.DataFrame] = None
) -> pd.DataFrame:
    """
    Assemble complete revenue frame for all companies.

    Formula (OPEX method):
    RevenueFrame_Total = CapitalCost_Total
                       + Controllable_PeriodSum (after OPEX efficiency)
                       + NonControllable_Costs
                       + FlexibilityServices
                       + InterruptionCompensation_12_24h
                       - Deduction_StateSubsidy
                       + IncentiveAdjustment_Total

    Formula (TOTEX method):
    RevenueFrame_Total = CapitalCost_After_Efficiency (CAPEX - CAPEX_Efficiency)
                       + OPEX_After (OPEX share of controllable after efficiency)
                       + NonControllable_Costs
                       + FlexibilityServices
                       + InterruptionCompensation_12_24h
                       - Deduction_StateSubsidy
                       + IncentiveAdjustment_Total

    Args:
        capex_result: DataFrame with REId, capital_cost_period
        controllable_result: DataFrame with REId, controllable_cost_period, OPEX/CAPEX fields
        sdf_baseline: DataFrame from SDF Excel with non-controllable and other components
        incentive_result: Optional DataFrame with incentive adjustments per REId

    Returns:
        DataFrame with all components and revenue_frame_total
    """
    # Start with CAPEX
    df = capex_result[['REId', COL_CAPITAL_COST_PERIOD]].copy()

    # Merge controllable costs - include all relevant fields
    controllable_cols = ['REId', COL_CONTROLLABLE_PERIOD, COL_METHOD_USED]

    # Efficiency fields
    for col in [COL_CONTROLLABLE_BEFORE, COL_EFFICIENCY_DEDUCTION]:
        if col in controllable_result.columns:
            controllable_cols.append(col)

    # Separated OPEX/CAPEX fields
    for col in [COL_OPEX_BEFORE, COL_OPEX_AFTER, COL_OPEX_EFF_DEDUCTION,
                COL_CAPEX_BEFORE, COL_CAPEX_AFTER, COL_CAPEX_EFF_DEDUCTION,
                COL_OPEX_SHARE, COL_CAPEX_SHARE]:
        if col in controllable_result.columns:
            controllable_cols.append(col)

    df = df.merge(
        controllable_result[controllable_cols],
        on='REId',
        how='left'
    )

    # Apply CAPEX efficiency reduction for TOTEX method
    if COL_CAPEX_EFF_DEDUCTION in df.columns:
        df[COL_CAPEX_EFF_DEDUCTION] = df[COL_CAPEX_EFF_DEDUCTION].fillna(0)
        df[COL_CAPITAL_COST_AFTER_EFF] = (
            df[COL_CAPITAL_COST_PERIOD] - df[COL_CAPEX_EFF_DEDUCTION]
        )
    else:
        df[COL_CAPEX_EFF_DEDUCTION] = 0
        df[COL_CAPITAL_COST_AFTER_EFF] = df[COL_CAPITAL_COST_PERIOD]

    # Merge SDF baseline components (already renamed to English in data_loaders)
    sdf_component_cols = [COL_NON_CONTROLLABLE, COL_FLEXIBILITY, COL_INTERRUPTION, COL_STATE_DEDUCTION]

    available_sdf_cols = ['REId'] + [c for c in sdf_component_cols if c in sdf_baseline.columns]
    sdf_subset = sdf_baseline[available_sdf_cols].copy()

    df = df.merge(sdf_subset, on='REId', how='left')

    # Fill NaN with 0 for missing components
    for col in sdf_component_cols:
        if col in df.columns:
            df[col] = df[col].fillna(0)
        else:
            df[col] = 0

    # Merge incentive adjustments if available
    if incentive_result is not None and not incentive_result.empty:
        incentive_cols = [
            'REId',
            COL_QUALITY_INCENTIVE,
            COL_NETLOSS_INCENTIVE,
            COL_LOAD_INCENTIVE,
            COL_INCENTIVE_TOTAL,
            COL_MISSING_INCENTIVE
        ]
        available_inc_cols = [c for c in incentive_cols if c in incentive_result.columns]

        df = df.merge(
            incentive_result[available_inc_cols],
            on='REId',
            how='left'
        )

        for col in [COL_QUALITY_INCENTIVE, COL_NETLOSS_INCENTIVE,
                    COL_LOAD_INCENTIVE, COL_INCENTIVE_TOTAL]:
            if col in df.columns:
                df[col] = df[col].fillna(0)
            else:
                df[col] = 0

        if COL_MISSING_INCENTIVE not in df.columns:
            df[COL_MISSING_INCENTIVE] = False
    else:
        df[COL_QUALITY_INCENTIVE] = 0
        df[COL_NETLOSS_INCENTIVE] = 0
        df[COL_LOAD_INCENTIVE] = 0
        df[COL_INCENTIVE_TOTAL] = 0
        df[COL_MISSING_INCENTIVE] = True

    # Determine which CAPEX value to use based on method
    df[COL_CAPITAL_COST_IN_RF] = df.apply(
        lambda row: row[COL_CAPITAL_COST_AFTER_EFF]
                    if row[COL_METHOD_USED] == 'TOTEX'
                    else row[COL_CAPITAL_COST_PERIOD],
        axis=1
    )

    # For TOTEX, use opex_after; for OPEX, use controllable_cost_period
    if COL_OPEX_AFTER in df.columns:
        df[COL_CONTROLLABLE_IN_RF] = df.apply(
            lambda row: row.get(COL_OPEX_AFTER, row[COL_CONTROLLABLE_PERIOD])
                        if pd.notna(row.get(COL_OPEX_AFTER))
                        else row[COL_CONTROLLABLE_PERIOD],
            axis=1
        )
    else:
        df[COL_CONTROLLABLE_IN_RF] = df[COL_CONTROLLABLE_PERIOD]

    # Calculate total revenue frame incl. incentives
    df[COL_REVENUE_FRAME] = (
        df[COL_CAPITAL_COST_IN_RF]
        + df[COL_CONTROLLABLE_IN_RF]
        + df[COL_NON_CONTROLLABLE]
        + df[COL_FLEXIBILITY]
        + df[COL_INTERRUPTION]
        - df[COL_STATE_DEDUCTION]
        + df[COL_INCENTIVE_TOTAL]
    )

    return df


def extract_user_revenue_frame(
    revenue_frame_df: pd.DataFrame,
    user_reid: str
) -> pd.Series:
    """
    Extract revenue frame for a specific company.

    Args:
        revenue_frame_df: DataFrame with all companies' revenue frames
        user_reid: REId for the user's company

    Returns:
        Series with all components for this company

    Raises:
        ValueError: If REId is not found in data
    """
    result = revenue_frame_df[revenue_frame_df['REId'] == user_reid]

    if result.empty:
        raise ValueError(f"REId '{user_reid}' not found in revenue frame data")

    return result.iloc[0]


def create_revenue_frame_breakdown(
    user_revenue_frame: pd.Series
) -> pd.DataFrame:
    """
    Create breakdown table for visualization.

    Args:
        user_revenue_frame: Series with all components

    Returns:
        DataFrame with columns: Component, Value (tkr)
    """
    method = user_revenue_frame.get(COL_METHOD_USED, 'OPEX')

    capex_value = user_revenue_frame.get(COL_CAPITAL_COST_IN_RF,
                                          user_revenue_frame.get(COL_CAPITAL_COST_PERIOD, 0))
    controllable_value = user_revenue_frame.get(COL_CONTROLLABLE_IN_RF,
                                                 user_revenue_frame.get(COL_CONTROLLABLE_PERIOD, 0))

    breakdown = [
        ('Capital cost', capex_value),
        ('Controllable costs', controllable_value),
        ('Non-controllable costs', user_revenue_frame.get(COL_NON_CONTROLLABLE, 0)),
        ('Flexibility services', user_revenue_frame.get(COL_FLEXIBILITY, 0)),
        ('Interruption compensation 12-24h', user_revenue_frame.get(COL_INTERRUPTION, 0)),
        ('State subsidy deduction', -user_revenue_frame.get(COL_STATE_DEDUCTION, 0)),
    ]

    # Show efficiency breakdown for TOTEX
    if method == 'TOTEX':
        capex_eff = user_revenue_frame.get(COL_CAPEX_EFF_DEDUCTION, 0)
        opex_eff = user_revenue_frame.get(COL_OPEX_EFF_DEDUCTION, 0)
        if capex_eff != 0 or opex_eff != 0:
            breakdown.append(('', ''))
            breakdown.append(('Efficiency (TOTEX):', ''))
            if opex_eff != 0:
                breakdown.append(('  - OPEX reduction', -opex_eff))
            if capex_eff != 0:
                breakdown.append(('  - CAPEX reduction', -capex_eff))

    # Add incentive adjustments if present
    if COL_INCENTIVE_TOTAL in user_revenue_frame.index:
        inc_total = user_revenue_frame.get(COL_INCENTIVE_TOTAL, 0)
        if inc_total != 0:
            breakdown.append(('', ''))
            breakdown.append(('Incentive adjustments:', ''))

            qual = user_revenue_frame.get(COL_QUALITY_INCENTIVE, 0)
            loss = user_revenue_frame.get(COL_NETLOSS_INCENTIVE, 0)
            util = user_revenue_frame.get(COL_LOAD_INCENTIVE, 0)

            if qual != 0:
                breakdown.append(('  - Quality incentive', qual))
            if loss != 0:
                breakdown.append(('  - Network loss incentive', loss))
            if util != 0:
                breakdown.append(('  - Load incentive', util))

            breakdown.append(('Incentive adjustment total', inc_total))

    breakdown.append(('', ''))
    breakdown.append(('TOTAL REVENUE FRAME', user_revenue_frame.get(COL_REVENUE_FRAME, 0)))

    df = pd.DataFrame(breakdown, columns=['Component', 'Value (tkr)'])

    return df

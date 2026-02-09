"""
calculations/revenue_frame_assembly.py

Assembly of revenue frame from all components.
Sums capital cost, controllable costs, non-controllable costs, incentives, and other components.

For TOTEX method: CAPEX is reduced separately with its share of the efficiency requirement.
"""

import pandas as pd
from typing import Optional


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
        capex_result: DataFrame with REId, Kapitalkostnad_Total
        controllable_result: DataFrame with REId, Paverkbara_Periodsumma, OPEX/CAPEX fields
        sdf_baseline: DataFrame from SDF Excel with non-controllable and other components
        incentive_result: Optional DataFrame with incentive adjustments per REId

    Returns:
        DataFrame with all components and Intaktsram_Total
    """
    # Start with CAPEX
    df = capex_result[['REId', 'Kapitalkostnad_Total']].copy()

    # Merge controllable costs - include all relevant fields
    controllable_cols = ['REId', 'Paverkbara_Periodsumma', 'Method_used']

    # Legacy efficiency fields
    for col in ['Paverkbara_Fore_Periodsumma', 'Effektivisering_Total']:
        if col in controllable_result.columns:
            controllable_cols.append(col)

    # Separated OPEX/CAPEX fields
    for col in ['OPEX_Fore', 'OPEX_Efter', 'OPEX_Effektivisering',
                'CAPEX_Fore', 'CAPEX_Efter', 'CAPEX_Effektivisering',
                'OPEX_Andel', 'CAPEX_Andel']:
        if col in controllable_result.columns:
            controllable_cols.append(col)

    df = df.merge(
        controllable_result[controllable_cols],
        on='REId',
        how='left'
    )

    # Apply CAPEX efficiency reduction for TOTEX method
    if 'CAPEX_Effektivisering' in df.columns:
        df['CAPEX_Effektivisering'] = df['CAPEX_Effektivisering'].fillna(0)
        df['Kapitalkostnad_Efter_Effektivisering'] = (
            df['Kapitalkostnad_Total'] - df['CAPEX_Effektivisering']
        )
    else:
        df['CAPEX_Effektivisering'] = 0
        df['Kapitalkostnad_Efter_Effektivisering'] = df['Kapitalkostnad_Total']

    # Merge SDF baseline components
    sdf_cols = [
        'REId',
        'Opåverkbara kostnader',
        'Kostnader för flexibilitetstjänster',
        'Avbrottsersättning 12-24 timmar',
        'Avdrag av kapitalkostnader pga anläggningar med statligt stöd'
    ]

    available_cols = ['REId']
    col_mapping = {
        'Opåverkbara kostnader': 'Opaverkbara_Kostnader',
        'Kostnader för flexibilitetstjänster': 'Flexibilitetstjanster',
        'Avbrottsersättning 12-24 timmar': 'Avbrottsersattning_12_24h',
        'Avdrag av kapitalkostnader pga anläggningar med statligt stöd': 'Avdrag_Statligt_Stod'
    }

    for col in sdf_cols[1:]:
        if col in sdf_baseline.columns:
            available_cols.append(col)

    sdf_subset = sdf_baseline[available_cols].copy()

    # Rename columns
    rename_dict = {k: v for k, v in col_mapping.items() if k in sdf_subset.columns}
    sdf_subset = sdf_subset.rename(columns=rename_dict)

    df = df.merge(sdf_subset, on='REId', how='left')

    # Fill NaN with 0 for missing components
    for col in col_mapping.values():
        if col in df.columns:
            df[col] = df[col].fillna(0)
        else:
            df[col] = 0

    # Merge incentive adjustments if available
    if incentive_result is not None and not incentive_result.empty:
        incentive_cols = [
            'REId',
            'Kvalitetsjustering_Total',
            'Natforlustjustering_Total',
            'Belastningsjustering_Total',
            'Incitamentjustering_Total',
            'Missing_Incentive_Data'
        ]
        available_inc_cols = [c for c in incentive_cols if c in incentive_result.columns]

        df = df.merge(
            incentive_result[available_inc_cols],
            on='REId',
            how='left'
        )

        for col in ['Kvalitetsjustering_Total', 'Natforlustjustering_Total',
                    'Belastningsjustering_Total', 'Incitamentjustering_Total']:
            if col in df.columns:
                df[col] = df[col].fillna(0)
            else:
                df[col] = 0

        if 'Missing_Incentive_Data' not in df.columns:
            df['Missing_Incentive_Data'] = False
    else:
        df['Kvalitetsjustering_Total'] = 0
        df['Natforlustjustering_Total'] = 0
        df['Belastningsjustering_Total'] = 0
        df['Incitamentjustering_Total'] = 0
        df['Missing_Incentive_Data'] = True

    # Determine which CAPEX value to use based on method
    df['Kapitalkostnad_I_Intaktsram'] = df.apply(
        lambda row: row['Kapitalkostnad_Efter_Effektivisering']
                    if row['Method_used'] == 'TOTEX'
                    else row['Kapitalkostnad_Total'],
        axis=1
    )

    # For TOTEX, use OPEX_Efter; for OPEX, use Paverkbara_Periodsumma
    if 'OPEX_Efter' in df.columns:
        df['Paverkbara_I_Intaktsram'] = df.apply(
            lambda row: row.get('OPEX_Efter', row['Paverkbara_Periodsumma'])
                        if pd.notna(row.get('OPEX_Efter'))
                        else row['Paverkbara_Periodsumma'],
            axis=1
        )
    else:
        df['Paverkbara_I_Intaktsram'] = df['Paverkbara_Periodsumma']

    # Calculate total revenue frame incl. incentives
    df['Intaktsram_Total'] = (
        df['Kapitalkostnad_I_Intaktsram']
        + df['Paverkbara_I_Intaktsram']
        + df['Opaverkbara_Kostnader']
        + df['Flexibilitetstjanster']
        + df['Avbrottsersattning_12_24h']
        - df['Avdrag_Statligt_Stod']
        + df['Incitamentjustering_Total']
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
    method = user_revenue_frame.get('Method_used', 'OPEX')

    capex_value = user_revenue_frame.get('Kapitalkostnad_I_Intaktsram',
                                          user_revenue_frame.get('Kapitalkostnad_Total', 0))
    controllable_value = user_revenue_frame.get('Paverkbara_I_Intaktsram',
                                                 user_revenue_frame.get('Paverkbara_Periodsumma', 0))

    breakdown = [
        ('Capital cost', capex_value),
        ('Controllable costs', controllable_value),
        ('Non-controllable costs', user_revenue_frame.get('Opaverkbara_Kostnader', 0)),
        ('Flexibility services', user_revenue_frame.get('Flexibilitetstjanster', 0)),
        ('Interruption compensation 12-24h', user_revenue_frame.get('Avbrottsersattning_12_24h', 0)),
        ('State subsidy deduction', -user_revenue_frame.get('Avdrag_Statligt_Stod', 0)),
    ]

    # Show efficiency breakdown for TOTEX
    if method == 'TOTEX':
        capex_eff = user_revenue_frame.get('CAPEX_Effektivisering', 0)
        opex_eff = user_revenue_frame.get('OPEX_Effektivisering', 0)
        if capex_eff != 0 or opex_eff != 0:
            breakdown.append(('', ''))
            breakdown.append(('Efficiency (TOTEX):', ''))
            if opex_eff != 0:
                breakdown.append(('  - OPEX reduction', -opex_eff))
            if capex_eff != 0:
                breakdown.append(('  - CAPEX reduction', -capex_eff))

    # Add incentive adjustments if present
    if 'Incitamentjustering_Total' in user_revenue_frame.index:
        inc_total = user_revenue_frame.get('Incitamentjustering_Total', 0)
        if inc_total != 0:
            breakdown.append(('', ''))
            breakdown.append(('Incentive adjustments:', ''))

            qual = user_revenue_frame.get('Kvalitetsjustering_Total', 0)
            loss = user_revenue_frame.get('Natforlustjustering_Total', 0)
            util = user_revenue_frame.get('Belastningsjustering_Total', 0)

            if qual != 0:
                breakdown.append(('  - Quality incentive', qual))
            if loss != 0:
                breakdown.append(('  - Network loss incentive', loss))
            if util != 0:
                breakdown.append(('  - Load incentive', util))

            breakdown.append(('Incentive adjustment total', inc_total))

    breakdown.append(('', ''))
    breakdown.append(('TOTAL REVENUE FRAME', user_revenue_frame.get('Intaktsram_Total', 0)))

    df = pd.DataFrame(breakdown, columns=['Component', 'Value (tkr)'])

    return df


def create_detailed_breakdown(
    user_revenue_frame: pd.Series,
    show_incentive_details: bool = True
) -> pd.DataFrame:
    """
    Create detailed breakdown with all incentive components.

    Args:
        user_revenue_frame: Series with all components
        show_incentive_details: If True, show quality/network loss/load separately

    Returns:
        DataFrame with columns: Component, Value (tkr), Share (%)
    """
    total = user_revenue_frame.get('Intaktsram_Total', 0)
    method = user_revenue_frame.get('Method_used', 'OPEX')

    components = []

    capex_value = user_revenue_frame.get('Kapitalkostnad_I_Intaktsram',
                                          user_revenue_frame.get('Kapitalkostnad_Total', 0))
    controllable_value = user_revenue_frame.get('Paverkbara_I_Intaktsram',
                                                 user_revenue_frame.get('Paverkbara_Periodsumma', 0))

    main = [
        ('Capital cost', capex_value),
        ('Controllable costs', controllable_value),
        ('Non-controllable costs', user_revenue_frame.get('Opaverkbara_Kostnader', 0)),
        ('Flexibility services', user_revenue_frame.get('Flexibilitetstjanster', 0)),
        ('Interruption compensation 12-24h', user_revenue_frame.get('Avbrottsersattning_12_24h', 0)),
    ]

    for label, val in main:
        pct = (val / total * 100) if total != 0 else 0
        components.append((label, val, pct))

    # Deduction (negative)
    deduction = user_revenue_frame.get('Avdrag_Statligt_Stod', 0)
    if deduction != 0:
        pct = (-deduction / total * 100) if total != 0 else 0
        components.append(('State subsidy deduction', -deduction, pct))

    # Incentive adjustments
    inc_total = user_revenue_frame.get('Incitamentjustering_Total', 0)

    if show_incentive_details and inc_total != 0:
        qual = user_revenue_frame.get('Kvalitetsjustering_Total', 0)
        loss = user_revenue_frame.get('Natforlustjustering_Total', 0)
        util = user_revenue_frame.get('Belastningsjustering_Total', 0)

        if qual != 0:
            pct = (qual / total * 100) if total != 0 else 0
            components.append(('Quality incentive', qual, pct))
        if loss != 0:
            pct = (loss / total * 100) if total != 0 else 0
            components.append(('Network loss incentive', loss, pct))
        if util != 0:
            pct = (util / total * 100) if total != 0 else 0
            components.append(('Load incentive', util, pct))
    elif inc_total != 0:
        pct = (inc_total / total * 100) if total != 0 else 0
        components.append(('Incentive adjustment', inc_total, pct))

    df = pd.DataFrame(components, columns=['Component', 'Value (tkr)', 'Share (%)'])

    return df

"""
calculations/controllable_cost_calculations.py

Calculations for controllable costs with efficiency requirements.
Supports both OPEX method (traditional) and TOTEX method (Ei 2020).

TOTEX method: The efficiency requirement is applied to OPEX + CAPEX, but the reduction
is allocated proportionally and applied separately to each cost component.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple


def calculate_controllable_with_eff_req(
    eff_req_data: pd.DataFrame,
    sdf_baseline: pd.DataFrame,
    capex_data: pd.DataFrame,
    method: str = 'OPEX'
) -> pd.DataFrame:
    """
    Calculate controllable costs with efficiency requirements for all companies.

    Implements Ei's method:
    1. Define starting value (OPEX: only controllable, TOTEX: controllable + CAPEX/4)
    2. Calculate annual deductions with compound growth
    3. Calculate controllable per year (2024-2027)
    4. Sum period total
    5. For TOTEX: Allocate efficiency proportionally between OPEX and CAPEX

    Args:
        eff_req_data: DataFrame with REId, Effkrav_proc (from efficiency requirement stage)
        sdf_baseline: DataFrame with REId, Paverkbara_Medelvarde, Neonjusteringar
        capex_data: DataFrame with REId, Kapitalkostnad_Total (period sum 2024-2027)
        method: 'OPEX' or 'TOTEX'

    Returns:
        DataFrame with columns:
        - REId
        - Paverkbara_2024, Paverkbara_2025, Paverkbara_2026, Paverkbara_2027
        - Paverkbara_Periodsumma
        - Method_used
        - OPEX_Fore, OPEX_Efter, OPEX_Effektivisering
        - CAPEX_Fore, CAPEX_Efter, CAPEX_Effektivisering
    """
    if method not in ['OPEX', 'TOTEX']:
        raise ValueError(f"Method must be 'OPEX' or 'TOTEX', got '{method}'")

    # Merge all datasets on REId
    df = eff_req_data[['REId', 'Effkrav_proc']].copy()

    # Merge with SDF baseline
    df = df.merge(
        sdf_baseline[['REId', 'Paverkbara_Medelvarde', 'Neonjusteringar']],
        on='REId',
        how='left'
    )

    # Merge with CAPEX data (needed for TOTEX, and for CAPEX_Fore even in OPEX mode)
    if 'Kapitalkostnad_Total' in capex_data.columns:
        df = df.merge(
            capex_data[['REId', 'Kapitalkostnad_Total']],
            on='REId',
            how='left'
        )
        df['Kapitalkostnad_Total'] = df['Kapitalkostnad_Total'].fillna(0)
    else:
        df['Kapitalkostnad_Total'] = 0

    # Validate that we have data
    required_cols = ['REId', 'Effkrav_proc', 'Paverkbara_Medelvarde', 'Neonjusteringar']
    missing = [col for col in required_cols if col not in df.columns or df[col].isna().all()]
    if missing:
        raise ValueError(f"Missing or empty columns: {missing}")

    # Calculate for each company
    results = []

    for _, row in df.iterrows():
        result = _calculate_controllable_single_company(
            reid=row['REId'],
            eff_req_pct=row['Effkrav_proc'],
            controllable_average=row['Paverkbara_Medelvarde'],
            neon_adjustments=row['Neonjusteringar'],
            capital_cost_total=row.get('Kapitalkostnad_Total', 0),
            method=method
        )
        results.append(result)

    return pd.DataFrame(results)


def _calculate_controllable_single_company(
    reid: str,
    eff_req_pct: float,
    controllable_average: float,
    neon_adjustments: float,
    capital_cost_total: float,
    method: str
) -> Dict[str, Any]:
    """
    Calculate controllable costs for a single company.

    Calculation chain (according to Ei's method):
    1. Starting value = Controllable_Average (OPEX) or + CAPEX/4 (TOTEX)
    2. Annual_Adjustment = Neon_Adjustments / 4
    3. Annual_Base_EffReq = Starting_Value + Annual_Adjustment
    4. For each year t:
       - Growth_Factor_t = (1 + eff_req)^(t-1)
       - Annual_Deduction_t = eff_req * Annual_Base * Growth_Factor_t
       - Cumulative_Deduction_t = sum(Annual_Deduction[1:t+1])
       - Controllable_t = Starting_Value - Cumulative_Deduction_t + Annual_Adjustment
    5. Period_Sum = sum(Controllable[2024:2028])
    6. For TOTEX: Allocate efficiency proportionally between OPEX and CAPEX

    Args:
        reid: REId for the company
        eff_req_pct: Annual efficiency requirement (decimal)
        controllable_average: Average controllable costs 2018-2021 (tkr, annual)
        neon_adjustments: Neon adjustments (tkr, 4-year period sum)
        capital_cost_total: Total capital cost 2024-2027 (tkr, 4-year period sum)
        method: 'OPEX' or 'TOTEX'

    Returns:
        Dict with results for this company
    """
    annual_adjustment = neon_adjustments / 4

    # OPEX base (annual)
    opex_base_annual = controllable_average + annual_adjustment

    # CAPEX base (annual) - only relevant for TOTEX
    capex_base_annual = capital_cost_total / 4

    # Define starting value for efficiency calculation
    if method == 'OPEX':
        starting_value = controllable_average
        total_base_annual = opex_base_annual
    else:  # TOTEX
        starting_value = controllable_average + capex_base_annual
        total_base_annual = opex_base_annual + capex_base_annual

    annual_base_eff_req = starting_value + annual_adjustment

    # Calculate annual values and total efficiency
    controllable_per_year = {}
    cumulative_deduction = 0

    for t in range(1, 5):  # t = 1,2,3,4 for 2024,2025,2026,2027
        growth_factor = (1 + eff_req_pct) ** (t - 1)
        annual_deduction = eff_req_pct * annual_base_eff_req * growth_factor
        cumulative_deduction += annual_deduction
        controllable_after_deduction = starting_value - cumulative_deduction + annual_adjustment
        year = 2023 + t
        controllable_per_year[f'Paverkbara_{year}'] = controllable_after_deduction

    # Total efficiency (period sum)
    total_before = (starting_value + annual_adjustment) * 4
    total_after = sum(controllable_per_year.values())
    efficiency_total = total_before - total_after

    # Calculate OPEX/CAPEX shares and allocate efficiency
    if method == 'OPEX' or total_base_annual == 0:
        opex_share = 1.0
        capex_share = 0.0
    else:  # TOTEX
        opex_share = opex_base_annual / total_base_annual
        capex_share = capex_base_annual / total_base_annual

    # OPEX before/after (period sum)
    opex_before = opex_base_annual * 4
    opex_efficiency = efficiency_total * opex_share
    opex_after = opex_before - opex_efficiency

    # CAPEX before/after (period sum)
    if method == 'TOTEX':
        capex_before = capital_cost_total
        capex_efficiency = efficiency_total * capex_share
        capex_after = capex_before - capex_efficiency
    else:
        capex_before = capital_cost_total
        capex_efficiency = 0.0
        capex_after = capex_before

    # Return results
    result = {
        'REId': reid,
        'Method_used': method,

        # Legacy fields (backwards compatibility)
        'Paverkbara_Fore_Periodsumma': total_before,
        'Paverkbara_Periodsumma': total_after,
        'Effektivisering_Total': efficiency_total,

        # Separated OPEX fields
        'OPEX_Fore': opex_before,
        'OPEX_Efter': opex_after,
        'OPEX_Effektivisering': opex_efficiency,

        # Separated CAPEX fields
        'CAPEX_Fore': capex_before,
        'CAPEX_Efter': capex_after,
        'CAPEX_Effektivisering': capex_efficiency,

        # Shares (for transparency)
        'OPEX_Andel': opex_share,
        'CAPEX_Andel': capex_share,
    }
    result.update(controllable_per_year)

    return result


def get_controllable_from_sdf(
    sdf_ir: pd.DataFrame,
    sdf_controllable: pd.DataFrame
) -> pd.DataFrame:
    """
    Extract controllable baseline data from SDF Excel.

    CRITICAL: Uses AVERAGE 2018-2021 from Controllable sheet,
    NOT the period sum from IR sheet!

    Args:
        sdf_ir: DataFrame from sheet "IR 2024-2027" (no longer used for average)
        sdf_controllable: DataFrame from sheet "Påverkbara"

    Returns:
        DataFrame with REId, Paverkbara_Medelvarde, Neonjusteringar
    """
    # REId column may be named 'REid' or 'REId' in the sheet
    reid_col = 'REid' if 'REid' in sdf_controllable.columns else 'REId'

    # Column 123: "Medelvärde 2018-2021 påverkbara kostnader"
    average_col = None
    for col in sdf_controllable.columns:
        col_lower = col.lower()
        if ('medelvärde' in col_lower or 'medelvarde' in col_lower) and '2018-2021' in col_lower:
            average_col = col
            break

    if average_col is None:
        raise ValueError(
            "Could not find column 'Medelvärde 2018-2021 påverkbara kostnader' "
            "in controllable costs sheet. Check Excel file structure."
        )

    # Column 124: Neon adjustments (separerat yrkandet)
    neojust_col = None
    for col in sdf_controllable.columns:
        if 'separerat yrkandet' in col.lower():
            neojust_col = col
            break

    if neojust_col is None:
        for col in sdf_controllable.columns:
            if 'neojust' in col.lower() or ('neo' in col.lower() and 'andr' in col.lower()):
                neojust_col = col
                break

    # Extract data
    result = sdf_controllable[[reid_col, average_col]].copy()
    result.columns = ['REId', 'Paverkbara_Medelvarde']

    # Add neon adjustments
    if neojust_col:
        result['Neonjusteringar'] = sdf_controllable[neojust_col]
    else:
        result['Neonjusteringar'] = 0

    # Fill NaN with 0
    result['Neonjusteringar'] = result['Neonjusteringar'].fillna(0)
    result['Paverkbara_Medelvarde'] = result['Paverkbara_Medelvarde'].fillna(0)

    return result


# Default method
DEFAULT_CONTROLLABLE_METHOD = 'OPEX'

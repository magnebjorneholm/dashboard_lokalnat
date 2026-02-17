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

from config.column_names import (
    COL_EFF_REQ_ANNUAL, COL_CONTROLLABLE_AVG, COL_NEO_ADJUSTMENTS,
    COL_CAPITAL_COST_PERIOD, COL_CONTROLLABLE_PERIOD,
    COL_CONTROLLABLE_BEFORE, COL_EFFICIENCY_DEDUCTION,
    COL_METHOD_USED, COL_OPEX_BEFORE, COL_OPEX_AFTER,
    COL_OPEX_EFF_DEDUCTION, COL_OPEX_SHARE,
    COL_CAPEX_BEFORE, COL_CAPEX_AFTER,
    COL_CAPEX_EFF_DEDUCTION, COL_CAPEX_SHARE,
)


def calculate_controllable_with_eff_req(
    eff_req_data: pd.DataFrame,
    sdf_baseline: pd.DataFrame,
    capex_data: pd.DataFrame,
    method: str = 'OPEX'
) -> pd.DataFrame:
    """
    Calculate controllable costs with efficiency requirements for all companies.

    Args:
        eff_req_data: DataFrame with REId, efficiency_requirement_annual
        sdf_baseline: DataFrame with REId, controllable_cost_average, neo_adjustments_period
        capex_data: DataFrame with REId, capital_cost_period (period sum 2024-2027)
        method: 'OPEX' or 'TOTEX'

    Returns:
        DataFrame with English column names for all controllable cost fields
    """
    if method not in ['OPEX', 'TOTEX']:
        raise ValueError(f"Method must be 'OPEX' or 'TOTEX', got '{method}'")

    # Merge all datasets on REId
    df = eff_req_data[['REId', COL_EFF_REQ_ANNUAL]].copy()

    # Merge with SDF baseline
    df = df.merge(
        sdf_baseline[['REId', COL_CONTROLLABLE_AVG, COL_NEO_ADJUSTMENTS]],
        on='REId',
        how='left'
    )

    # Merge with CAPEX data (needed for TOTEX, and for capex_before even in OPEX mode)
    if COL_CAPITAL_COST_PERIOD in capex_data.columns:
        df = df.merge(
            capex_data[['REId', COL_CAPITAL_COST_PERIOD]],
            on='REId',
            how='left'
        )
        df[COL_CAPITAL_COST_PERIOD] = df[COL_CAPITAL_COST_PERIOD].fillna(0)
    else:
        df[COL_CAPITAL_COST_PERIOD] = 0

    # Validate that we have data
    required_cols = ['REId', COL_EFF_REQ_ANNUAL, COL_CONTROLLABLE_AVG, COL_NEO_ADJUSTMENTS]
    missing = [col for col in required_cols if col not in df.columns or df[col].isna().all()]
    if missing:
        raise ValueError(f"Missing or empty columns: {missing}")

    # Calculate for each company
    results = []

    for _, row in df.iterrows():
        result = _calculate_controllable_single_company(
            reid=row['REId'],
            eff_req_pct=row[COL_EFF_REQ_ANNUAL],
            controllable_average=row[COL_CONTROLLABLE_AVG],
            neon_adjustments=row[COL_NEO_ADJUSTMENTS],
            capital_cost_total=row.get(COL_CAPITAL_COST_PERIOD, 0),
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

    Args:
        reid: REId for the company
        eff_req_pct: Annual efficiency requirement (decimal)
        controllable_average: Average controllable costs 2018-2021 (tkr, annual)
        neon_adjustments: Neon adjustments (tkr, 4-year period sum)
        capital_cost_total: Total capital cost 2024-2027 (tkr, 4-year period sum)
        method: 'OPEX' or 'TOTEX'

    Returns:
        Dict with results for this company using English column names
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
        controllable_per_year[f'controllable_cost_{year}'] = controllable_after_deduction

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

    # Return results with English column names
    result = {
        'REId': reid,
        COL_METHOD_USED: method,

        # Controllable cost totals
        COL_CONTROLLABLE_BEFORE: total_before,
        COL_CONTROLLABLE_PERIOD: total_after,
        COL_EFFICIENCY_DEDUCTION: efficiency_total,

        # Separated OPEX fields
        COL_OPEX_BEFORE: opex_before,
        COL_OPEX_AFTER: opex_after,
        COL_OPEX_EFF_DEDUCTION: opex_efficiency,

        # Separated CAPEX fields
        COL_CAPEX_BEFORE: capex_before,
        COL_CAPEX_AFTER: capex_after,
        COL_CAPEX_EFF_DEDUCTION: capex_efficiency,

        # Shares (for transparency)
        COL_OPEX_SHARE: opex_share,
        COL_CAPEX_SHARE: capex_share,
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
        DataFrame with REId, controllable_cost_average, neo_adjustments_period
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

    # Extract data with English column names
    result = sdf_controllable[[reid_col, average_col]].copy()
    result.columns = ['REId', COL_CONTROLLABLE_AVG]

    # Add neon adjustments
    if neojust_col:
        result[COL_NEO_ADJUSTMENTS] = sdf_controllable[neojust_col]
    else:
        result[COL_NEO_ADJUSTMENTS] = 0

    # Fill NaN with 0
    result[COL_NEO_ADJUSTMENTS] = result[COL_NEO_ADJUSTMENTS].fillna(0)
    result[COL_CONTROLLABLE_AVG] = result[COL_CONTROLLABLE_AVG].fillna(0)

    return result


# Default method
DEFAULT_CONTROLLABLE_METHOD = 'OPEX'

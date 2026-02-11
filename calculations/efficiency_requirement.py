"""
calculations/efficiency_requirement.py

Calculation functions for efficiency requirements.
Converts DEA potential to annual efficiency requirement according to Ei's method.
"""

import numpy as np
import pandas as pd
from typing import Optional

from config.column_names import COL_EFF_REQ_ANNUAL


# Default parameters from Ei's method for supervision period 2024-2027
DEFAULT_EFF_REQ_PARAMS = {
    'truncation_max': 0.30,        # Max potential for truncation (30%)
    'outlier_req': 0.01,           # Fixed annual requirement for outliers (1%)
    'customer_sharing': 0.50,      # Share allocated to customers (50%)
    'realization_time': 8,         # Years to achieve full efficiency
    'supervision_period': 4,       # Length of supervision period in years
}


def calculate_truncation_min_from_outlier_req(
    outlier_req: float = 0.01,
    customer_sharing: float = 0.50,
    realization_time: int = 8,
    supervision_period: int = 4
) -> float:
    """
    Calculate truncation_min that gives the same annual requirement as outlier_req.

    This ensures that non-outliers with low potential get the same
    minimum requirement as outliers, consistent with Ei's method.

    Inverse calculation of the formula:
        annual_req = (1 + potential * customer_sharing * supervision_period/realization_time)^(1/supervision_period) - 1

    Gives:
        potential = ((1 + annual_req)^supervision_period - 1) / (customer_sharing * supervision_period/realization_time)

    With default parameters (outlier_req=1%) this gives truncation_min ~ 16.24%

    Args:
        outlier_req: Fixed annual requirement for outliers (default 1%)
        customer_sharing: Share of efficiency allocated to customers (default 50%)
        realization_time: Number of years to achieve full efficiency (default 8)
        supervision_period: Length of supervision period in years (default 4)

    Returns:
        truncation_min that gives the same annual requirement as outlier_req
    """
    total_eff = (1 + outlier_req) ** supervision_period - 1
    realization_factor = supervision_period / realization_time
    potential = total_eff / (customer_sharing * realization_factor)
    return potential


def calculate_eff_req_from_potential(
    potential: float,
    is_outlier: bool,
    truncation_min: float = 0.162416,
    truncation_max: float = 0.30,
    outlier_req: float = 0.01,
    customer_sharing: float = 0.50,
    realization_time: int = 8,
    supervision_period: int = 4
) -> float:
    """
    Calculate annual efficiency requirement from potential.

    Implements Ei's complete formula:

    1. If outlier: use fixed requirement (default 1%)
    2. Truncate potential between min/max
    3. Calculate total efficiency: potential * customer_sharing * (supervision_period/realization_time)
    4. Distribute over supervision period: (1 + total_eff)^(1/supervision_period) - 1

    For supervision period 2024-2027 with default parameters:
    - Max annual requirement: 1.82%
    - Min annual requirement: 1.0% (outlier_req)

    Args:
        potential: Inefficiency (1 - efficiency), 0-1 range
        is_outlier: Whether the company is an outlier
        truncation_min: Minimum potential for truncation (calculated from outlier_req)
        truncation_max: Maximum potential for truncation (default 30%)
        outlier_req: Fixed annual requirement for outliers (default 1%)
        customer_sharing: Share of efficiency allocated to customers (default 50%)
        realization_time: Number of years to achieve full efficiency (default 8)
        supervision_period: Length of supervision period in years (default 4)

    Returns:
        Annual efficiency requirement (decimal, e.g. 0.0182 = 1.82% per year)
    """
    if is_outlier:
        return outlier_req

    # Truncate potential
    potential_truncated = np.clip(potential, truncation_min, truncation_max)

    # Calculate total efficiency during supervision period
    total_efficiency = potential_truncated * customer_sharing * (supervision_period / realization_time)

    # Distribute over supervision period with compound growth
    eff_req_yearly = (1 + total_efficiency) ** (1 / supervision_period) - 1

    return eff_req_yearly


def calculate_eff_req_for_dataframe(
    df: pd.DataFrame,
    potential_col: str = 'potential',
    outlier_col: str = 'is_outlier',
    truncation_min: Optional[float] = None,
    truncation_max: float = 0.30,
    outlier_req: float = 0.01,
    customer_sharing: float = 0.50,
    realization_time: int = 8,
    supervision_period: int = 4
) -> pd.DataFrame:
    """
    Calculate efficiency requirements for all companies in DataFrame.

    Args:
        df: DataFrame with potential and outlier flag from DEA
        potential_col: Column name for potential (default 'potential')
        outlier_col: Column name for outlier flag (default 'is_outlier')
        truncation_min: Minimum potential for truncation (calculated from outlier_req if None)
        truncation_max: Maximum potential for truncation
        outlier_req: Fixed annual requirement for outliers
        customer_sharing: Share of efficiency allocated to customers
        realization_time: Number of years to achieve full efficiency
        supervision_period: Length of supervision period in years

    Returns:
        DataFrame with new column 'efficiency_requirement_annual'
    """
    result = df.copy()

    if potential_col not in result.columns:
        raise ValueError(f"Column '{potential_col}' missing from DataFrame")
    if outlier_col not in result.columns:
        raise ValueError(f"Column '{outlier_col}' missing from DataFrame")

    # Calculate truncation_min from outlier_req if not specified
    if truncation_min is None:
        truncation_min = calculate_truncation_min_from_outlier_req(
            outlier_req=outlier_req,
            customer_sharing=customer_sharing,
            realization_time=realization_time,
            supervision_period=supervision_period
        )

    # Calculate efficiency requirement for each row
    result[COL_EFF_REQ_ANNUAL] = result.apply(
        lambda row: calculate_eff_req_from_potential(
            potential=row[potential_col],
            is_outlier=row[outlier_col],
            truncation_min=truncation_min,
            truncation_max=truncation_max,
            outlier_req=outlier_req,
            customer_sharing=customer_sharing,
            realization_time=realization_time,
            supervision_period=supervision_period
        ),
        axis=1
    )

    return result


def get_max_eff_req(
    truncation_max: float = 0.30,
    customer_sharing: float = 0.50,
    realization_time: int = 8,
    supervision_period: int = 4
) -> float:
    """
    Calculate maximum annual efficiency requirement given the parameters.

    Useful for validation and UI display.

    Returns:
        Max annual efficiency requirement (e.g. 0.0182 = 1.82%)
    """
    return calculate_eff_req_from_potential(
        potential=truncation_max,
        is_outlier=False,
        truncation_min=0.0,
        truncation_max=truncation_max,
        customer_sharing=customer_sharing,
        realization_time=realization_time,
        supervision_period=supervision_period
    )


def get_min_eff_req(
    outlier_req: float = 0.01
) -> float:
    """
    Return minimum annual efficiency requirement.

    This is the same as outlier_req since truncation_min
    is calculated to give the same result.

    Args:
        outlier_req: Fixed annual requirement for outliers

    Returns:
        Min annual efficiency requirement (same as outlier_req)
    """
    return outlier_req

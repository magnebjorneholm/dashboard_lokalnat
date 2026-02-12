"""
calculations/cost_aggregation.py

Pure calculation functions that aggregate grunddata (parquet) into pipeline-ready values.
No UI dependencies — only pandas/numpy.

Controllable: detail × meta → controllable_cost_average + neo_adjustments_period
Non-controllable: detail → per-company period total + per-year breakdown
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict

from config.column_names import (
    COL_CONTROLLABLE_AVG, COL_NEO_ADJUSTMENTS,
    COL_NON_CONTROLLABLE,
    COL_NON_CONTROLLABLE_2024, COL_NON_CONTROLLABLE_2025,
    COL_NON_CONTROLLABLE_2026, COL_NON_CONTROLLABLE_2027,
)

YEARS = [2018, 2019, 2020, 2021]
INDEX_COLS = {2018: "index_2018", 2019: "index_2019", 2020: "index_2020", 2021: "index_2021"}


def aggregate_controllable(
    detail: pd.DataFrame,
    meta: pd.DataFrame,
    category_overrides: Optional[Dict[str, float]] = None,
) -> pd.DataFrame:
    """
    Aggregate per-category detail to per-company controllable_cost_average.

    Steps:
    1. Apply category overrides (multiplicative scaling) if provided
    2. Sum categories per company per year → nominal yearly total
    3. Multiply by index factor per year → 2022-level yearly total
    4. Average the 4 yearly totals → controllable_cost_average
    5. Attach neo_adjustments from meta

    Args:
        detail: From controllable_a.parquet (REId, category, year, amount_nominal)
        meta: From controllable_meta.parquet (REId, index_2018..2021, neo_adjustment, eff_req_pct)
        category_overrides: Optional {category_name: multiplier} for scaling

    Returns:
        DataFrame with REId, controllable_cost_average, neo_adjustments_period
        (Same output shape as current get_controllable_from_sdf())
    """
    df = detail.copy()

    # Step 1: Apply category overrides
    if category_overrides:
        for cat_name, multiplier in category_overrides.items():
            mask = df["category"] == cat_name
            if mask.any():
                df.loc[mask, "amount_nominal"] = df.loc[mask, "amount_nominal"] * multiplier

    # Step 2: Sum categories per company per year
    yearly_sums = df.groupby(["REId", "year"])["amount_nominal"].sum().reset_index()
    yearly_sums.columns = ["REId", "year", "nominal_total"]

    # Step 3: Pivot to wide format and multiply by index
    yearly_pivot = yearly_sums.pivot(index="REId", columns="year", values="nominal_total").reset_index()

    # Merge with meta to get index values
    yearly_pivot = yearly_pivot.merge(meta[["REId"] + list(INDEX_COLS.values())], on="REId", how="left")

    # Compute 2022-level totals per year
    for yr in YEARS:
        idx_col = INDEX_COLS[yr]
        yearly_pivot[f"total_2022_{yr}"] = yearly_pivot[yr] * yearly_pivot[idx_col]

    # Step 4: Average of 4 yearly totals
    total_cols = [f"total_2022_{yr}" for yr in YEARS]
    yearly_pivot[COL_CONTROLLABLE_AVG] = yearly_pivot[total_cols].mean(axis=1)

    # Step 5: Attach neo_adjustments from meta
    result = yearly_pivot[["REId", COL_CONTROLLABLE_AVG]].merge(
        meta[["REId", "neo_adjustment"]],
        on="REId",
        how="left",
    )
    result = result.rename(columns={"neo_adjustment": COL_NEO_ADJUSTMENTS})
    result[COL_NEO_ADJUSTMENTS] = result[COL_NEO_ADJUSTMENTS].fillna(0)

    return result


def aggregate_non_controllable(
    detail: pd.DataFrame,
    category_overrides: Optional[Dict[str, float]] = None,
) -> pd.DataFrame:
    """
    Aggregate per-category non-controllable detail to per-company totals.

    Args:
        detail: From non_controllable_a.parquet (REId, kent_category, year, amount)
        category_overrides: Optional {kent_category: multiplier} for scaling

    Returns:
        DataFrame with REId, non_controllable_cost_period,
        non_controllable_cost_2024..2027
    """
    df = detail.copy()

    # Apply category overrides
    if category_overrides:
        for cat_name, multiplier in category_overrides.items():
            mask = df["kent_category"] == cat_name
            if mask.any():
                df.loc[mask, "amount"] = df.loc[mask, "amount"] * multiplier

    # Sum per company per year
    yearly_sums = df.groupby(["REId", "year"])["amount"].sum().reset_index()
    yearly_sums.columns = ["REId", "year", "total"]

    # Pivot to wide format
    yearly_pivot = yearly_sums.pivot(index="REId", columns="year", values="total").reset_index()

    # Non-controllable values are negative in the parquet (costs).
    # The pipeline expects positive values (matching IR sheet convention).
    # Negate here to match the convention used by revenue_frame_assembly.
    year_col_map = {
        2024: COL_NON_CONTROLLABLE_2024,
        2025: COL_NON_CONTROLLABLE_2025,
        2026: COL_NON_CONTROLLABLE_2026,
        2027: COL_NON_CONTROLLABLE_2027,
    }

    result = yearly_pivot[["REId"]].copy()
    for yr, col_name in year_col_map.items():
        if yr in yearly_pivot.columns:
            result[col_name] = -yearly_pivot[yr]  # Negate: negative costs → positive
        else:
            result[col_name] = 0.0

    # Period total
    result[COL_NON_CONTROLLABLE] = (
        result[COL_NON_CONTROLLABLE_2024]
        + result[COL_NON_CONTROLLABLE_2025]
        + result[COL_NON_CONTROLLABLE_2026]
        + result[COL_NON_CONTROLLABLE_2027]
    )

    return result

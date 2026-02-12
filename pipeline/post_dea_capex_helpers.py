"""
pipeline/post_dea_capex_helpers.py

Helper functions for fetching capital cost and return data in post_dea.

SIMPLIFIED: With wacc_scaling removed, logic is now:
- baseline + baseline: Use baseline df / SDF
- Any other combination: Use KENT output from pre_dea.df_all_companies
"""

import pandas as pd
from typing import List

from config.column_names import (
    COL_CAPITAL_COST_PERIOD, COL_CAPITAL_COST_2024, COL_CAPITAL_COST_2025,
    COL_CAPITAL_COST_2026, COL_CAPITAL_COST_2027,
    COL_RETURN_2024, COL_RETURN_2025, COL_RETURN_2026, COL_RETURN_2027,
    COL_RETURN_PERIOD,
)
from pipeline.stages.stage_outputs import PreDeaStageOutput, BaselineStageOutput


def get_return_per_year(
    pre_dea: PreDeaStageOutput,
    baseline: BaselineStageOutput
) -> pd.DataFrame:
    """
    Get return per year for all 148 companies.

    Used for incentive adjustment 1/3-cap applied per year.

    Logic:
    - baseline + baseline: From baseline df_all_companies
    - Any other: From pre_dea.df_all_companies (KENT output)

    Returns:
        DataFrame with: REId, return_on_assets_2024-2027 (all in tkr)
    """
    source = pre_dea.capbase_source
    method = pre_dea.capex_method
    yearly_cols = [COL_RETURN_2024, COL_RETURN_2025, COL_RETURN_2026, COL_RETURN_2027]

    if method == 'baseline' and source == 'baseline':
        return _get_return_from_baseline(baseline, yearly_cols)
    else:
        # KENT output in pre_dea.df_all_companies
        return _get_return_from_pre_dea(pre_dea, yearly_cols)


def _get_return_from_baseline(
    baseline: BaselineStageOutput,
    yearly_cols: List[str]
) -> pd.DataFrame:
    """Get return per year from baseline df_all_companies."""
    df = baseline.df_all_companies

    missing_cols = [col for col in yearly_cols if col not in df.columns]

    if missing_cols:
        result = df[['REId']].copy()
        for col in yearly_cols:
            result[col] = 0
        return result

    return df[['REId'] + yearly_cols].copy()


def _get_return_from_pre_dea(
    pre_dea: PreDeaStageOutput,
    yearly_cols: List[str]
) -> pd.DataFrame:
    """Get return per year from pre_dea.df_all_companies (KENT output)."""
    df = pre_dea.df_all_companies

    missing_cols = [col for col in yearly_cols if col not in df.columns]

    if missing_cols:
        # Fallback: use return_on_assets_period / 4
        if COL_RETURN_PERIOD in df.columns:
            result = df[['REId']].copy()
            avg_return = df[COL_RETURN_PERIOD] / 4
            for col in yearly_cols:
                result[col] = avg_return
            return result

        # Last fallback: 0
        result = df[['REId']].copy()
        for col in yearly_cols:
            result[col] = 0
        return result

    return df[['REId'] + yearly_cols].copy()


def get_capex_period_sum(
    pre_dea: PreDeaStageOutput,
    baseline: BaselineStageOutput
) -> pd.DataFrame:
    """
    Get capital cost period sum (4 years) for all 148 companies.

    CRITICAL: Returns PERIOD SUM (4 years), NOT annual value!

    Logic:
    - baseline + baseline: SDF capital_cost_period (period sum)
    - Any other: KENT output capital_cost_period

    Returns:
        DataFrame with: REId, capital_cost_period (period sum in tkr)
    """
    source = pre_dea.capbase_source
    method = pre_dea.capex_method

    if method == 'baseline' and source == 'baseline':
        return _get_capex_from_sdf(baseline)
    else:
        # KENT output in pre_dea.df_all_companies
        return _get_capex_from_pre_dea(pre_dea, baseline)


def _get_capex_from_sdf(baseline: BaselineStageOutput) -> pd.DataFrame:
    """Get capital cost period sum from SDF (local networks only)."""
    sdf = baseline.sdf_ir.copy()

    # Filter to local networks only (REL*), excluding regional (RER*)
    sdf = sdf[sdf['REId'].str.startswith('REL')]

    if COL_CAPITAL_COST_PERIOD not in sdf.columns:
        raise ValueError(f"Column '{COL_CAPITAL_COST_PERIOD}' missing in SDF IR")

    df = sdf[['REId', COL_CAPITAL_COST_PERIOD]].copy()
    df[COL_CAPITAL_COST_PERIOD] = pd.to_numeric(
        df[COL_CAPITAL_COST_PERIOD], errors='coerce'
    ).fillna(0)

    return df


def _get_capex_from_pre_dea(
    pre_dea: PreDeaStageOutput,
    baseline: BaselineStageOutput
) -> pd.DataFrame:
    """Get capital cost period sum from pre_dea.df_all_companies."""
    df = pre_dea.df_all_companies

    if COL_CAPITAL_COST_PERIOD in df.columns:
        return df[['REId', COL_CAPITAL_COST_PERIOD]].copy()

    else:
        # Try summing per-year columns
        yearly_cols = [COL_CAPITAL_COST_2024, COL_CAPITAL_COST_2025,
                      COL_CAPITAL_COST_2026, COL_CAPITAL_COST_2027]

        if all(col in df.columns for col in yearly_cols):
            result = df[['REId']].copy()
            result[COL_CAPITAL_COST_PERIOD] = (
                df[COL_CAPITAL_COST_2024] + df[COL_CAPITAL_COST_2025] +
                df[COL_CAPITAL_COST_2026] + df[COL_CAPITAL_COST_2027]
            )
            return result

        # Last fallback: use SDF
        return _get_capex_from_sdf(baseline)

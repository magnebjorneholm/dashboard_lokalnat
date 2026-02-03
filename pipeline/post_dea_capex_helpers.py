"""
pipeline/post_dea_capex_helpers.py

Helper functions for fetching capital cost and return data in post_dea.

SIMPLIFIED: With wacc_scaling removed, logic is now:
- baseline + baseline: Use baseline df / SDF
- Any other combination: Use KENT output from pre_dea.df_all_companies
"""

import pandas as pd
from typing import List

from pipeline.stages.stage_outputs import PreDeaStageOutput, BaselineStageOutput


SDF_COL_KAPITALKOSTNAD = 'Kapitalkostnad'


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
        DataFrame with: REId, Avkastning_2024-2027 (all in tkr)
    """
    source = pre_dea.capbase_source
    method = pre_dea.capex_method
    yearly_cols = [f'Avkastning_{year}' for year in [2024, 2025, 2026, 2027]]
    
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
            if 'Avkastning' in df.columns:
                result[col] = df['Avkastning']
            else:
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
        # Fallback: use Avkastning_Period / 4
        if 'Avkastning_Period' in df.columns:
            result = df[['REId']].copy()
            avg_return = df['Avkastning_Period'] / 4
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
    - baseline + baseline: SDF "Kapitalkostnad" (period sum)
    - Any other: KENT output Kapitalkostnad_Period
    
    Returns:
        DataFrame with: REId, Kapitalkostnad_Total (period sum in tkr)
    """
    source = pre_dea.capbase_source
    method = pre_dea.capex_method
    
    if method == 'baseline' and source == 'baseline':
        return _get_capex_from_sdf(baseline)
    else:
        # KENT output in pre_dea.df_all_companies
        return _get_capex_from_pre_dea(pre_dea, baseline)


def _get_capex_from_sdf(baseline: BaselineStageOutput) -> pd.DataFrame:
    """Get capital cost period sum from SDF."""
    sdf = baseline.sdf_ir.copy()
    
    if SDF_COL_KAPITALKOSTNAD not in sdf.columns:
        raise ValueError(f"Column '{SDF_COL_KAPITALKOSTNAD}' missing in SDF IR")
    
    df = sdf[['REId', SDF_COL_KAPITALKOSTNAD]].copy()
    df.columns = ['REId', 'Kapitalkostnad_Total']
    df['Kapitalkostnad_Total'] = pd.to_numeric(
        df['Kapitalkostnad_Total'], errors='coerce'
    ).fillna(0)
    
    return df


def _get_capex_from_pre_dea(
    pre_dea: PreDeaStageOutput,
    baseline: BaselineStageOutput
) -> pd.DataFrame:
    """Get capital cost period sum from pre_dea.df_all_companies."""
    df = pre_dea.df_all_companies
    
    if 'Kapitalkostnad_Period' in df.columns:
        result = df[['REId', 'Kapitalkostnad_Period']].copy()
        result.columns = ['REId', 'Kapitalkostnad_Total']
        return result
    
    elif 'Kapitalkostnad_Total' in df.columns:
        return df[['REId', 'Kapitalkostnad_Total']].copy()
    
    else:
        # Try summing per-year columns
        yearly_cols = ['Kapitalkostnad_2024', 'Kapitalkostnad_2025',
                      'Kapitalkostnad_2026', 'Kapitalkostnad_2027']
        
        if all(col in df.columns for col in yearly_cols):
            result = df[['REId']].copy()
            result['Kapitalkostnad_Total'] = (
                df['Kapitalkostnad_2024'] + df['Kapitalkostnad_2025'] +
                df['Kapitalkostnad_2026'] + df['Kapitalkostnad_2027']
            )
            return result
        
        # Last fallback: use SDF
        return _get_capex_from_sdf(baseline)
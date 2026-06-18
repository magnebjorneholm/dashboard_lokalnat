"""
calculations/incentive/incentive_prep.py

Pure preparation / aggregation helpers around the incentive calculation.

These were previously in ``data_loaders/incentive_data.py`` but they perform no
I/O — they only transform DataFrames — so they belong in the calculations layer.
The actual file loading stays in ``data_loaders/incentive_data.py``.
"""
from __future__ import annotations

from typing import Optional, Dict

import pandas as pd


def prepare_incentive_input(
    incentive_data: pd.DataFrame,
    return_per_year: pd.DataFrame,
) -> pd.DataFrame:
    """
    Prepare complete input for incentive calculation by merging
    incentive data with return per year.

    Args:
        incentive_data: DataFrame from load_incentive_data()
        return_per_year: DataFrame with REId, return_on_assets_2024..2027 (tkr)

    Returns:
        DataFrame with all variables ready for calculate_all_incentives().
        Contains column 'ret_period' (return in kr for each year).
    """
    df = incentive_data.copy()

    # Merge with return per year
    df = df.merge(return_per_year, on='REId', how='left')

    # Create ret_period based on year (convert tkr -> kr)
    df['ret_period'] = df.apply(
        lambda row: row.get(f"return_on_assets_{int(row['year'])}", 0) * 1000,
        axis=1
    )

    return df


def get_incentive_summary_by_reid(
    incentive_results: pd.DataFrame
) -> pd.DataFrame:
    """
    Aggregate incentive results to one row per REId (period sum).

    Args:
        incentive_results: Output from calculate_all_incentives()

    Returns:
        DataFrame with one row per REId:
        - REId
        - quality_incentive_total (tkr)
        - network_loss_incentive_total (tkr)
        - load_incentive_total (tkr)
        - incentive_adjustment_total (tkr)
        - Missing_Incentive_Data (bool)
    """
    from config.incentive_parameters import MISSING_DATA_IDS
    from config.column_names import (
        COL_QUALITY_INCENTIVE, COL_NETLOSS_INCENTIVE,
        COL_LOAD_INCENTIVE, COL_INCENTIVE_TOTAL, COL_MISSING_INCENTIVE,
    )

    # Period sums are already on all rows (aggregate_period_totals)
    # Extract one row per REId
    df_summary = incentive_results.groupby('REId').first().reset_index()

    # Select relevant columns
    cols_to_keep = ['REId']
    rename_map = {}

    # Period sums (from aggregate_period_totals)
    if 'inter_incentive_sum' in df_summary.columns:
        cols_to_keep.append('inter_incentive_sum')
        rename_map['inter_incentive_sum'] = COL_QUALITY_INCENTIVE
    if 'loss_incentive_sum' in df_summary.columns:
        cols_to_keep.append('loss_incentive_sum')
        rename_map['loss_incentive_sum'] = COL_NETLOSS_INCENTIVE
    if 'util_incentive_sum' in df_summary.columns:
        cols_to_keep.append('util_incentive_sum')
        rename_map['util_incentive_sum'] = COL_LOAD_INCENTIVE
    if 'incentive_total' in df_summary.columns:
        cols_to_keep.append('incentive_total')
        rename_map['incentive_total'] = COL_INCENTIVE_TOTAL

    df_summary = df_summary[cols_to_keep].copy()

    # Convert from kr to tkr
    for col in cols_to_keep[1:]:  # Skip REId
        df_summary[col] = df_summary[col] / 1000

    # Rename to English
    df_summary = df_summary.rename(columns=rename_map)

    # Flag for missing data (based on numeric reid in MISSING_DATA_IDS)
    df_summary[COL_MISSING_INCENTIVE] = df_summary['REId'].apply(
        lambda x: int(x.replace('REL', '')) in MISSING_DATA_IDS
    )

    return df_summary


def get_incentive_detailed_by_reid(
    incentive_results: pd.DataFrame,
    user_reid: str
) -> Optional[pd.DataFrame]:
    """
    Extract detailed per-year incentive data for a specific company.

    Returns all intermediate values needed for User Manual Table 10 display:
    - 30.2.4/30.2.5: Network loss before/after cap
    - 30.3.4/30.3.5: Utilization before/after cap
    - 30.4.57/58/59: Quality before CEMI4, after CEMI4, after cap
    - 30.5.1/30.5.2: Total before/after aggregate cap
    - AIT/AIF per customer type (no Variable-ID)

    Args:
        incentive_results: Full output from calculate_all_incentives()
        user_reid: REId for the company (e.g., "REL00886")

    Returns:
        DataFrame with one row per year (2024-2027) plus period totals,
        or None if user not found.
    """
    if incentive_results is None or incentive_results.empty:
        return None

    # Filter to user's rows
    df_user = incentive_results[incentive_results['REId'] == user_reid].copy()

    if df_user.empty:
        return None

    # Columns to extract (User Manual Table 10 outputs)
    output_columns = [
        'year',
        # 30.2 Network loss
        'loss_incentive_a',      # 30.2.4 before cap
        'loss_incentive',        # 30.2.5 after cap
        # 30.3 Utilization
        'util_incentive_a',      # 30.3.4 before cap
        'util_incentive',        # 30.3.5 after cap
        # 30.4 Quality/Interruption
        'inc_inter',             # 30.4.57 before CEMI4
        'inter_incentive_a',     # 30.4.58 after CEMI4
        'inter_incentive',       # 30.4.59 after CEMI4 + cap
        # 30.5 Total
        'incentive_total_year',  # 30.5.2 after aggregate cap
        # Cap reference
        'max_adj',               # Max adjustment (1/3 of return)
        'ret_period',            # Return used for cap calculation
    ]

    # AIT/AIF per customer type columns (no Variable-ID in User Manual)
    ait_aif_columns = []
    for ind_type in ['ait', 'aif']:
        for ann in ['a', 'o']:
            for sni in range(1, 7):
                col = f'inc_{ind_type}_{ann}_{sni}'
                if col in df_user.columns:
                    ait_aif_columns.append(col)

    # Build column list with available columns only
    available_cols = [c for c in output_columns if c in df_user.columns]
    available_cols.extend(ait_aif_columns)

    # Select and sort by year
    df_detail = df_user[available_cols].copy()
    df_detail = df_detail.sort_values('year').reset_index(drop=True)

    # Calculate 30.5.1: Total after individual caps but before aggregate cap
    # This is the sum of individually capped values (not _a values)
    if all(c in df_detail.columns for c in ['inter_incentive', 'loss_incentive', 'util_incentive']):
        df_detail['total_before_agg_cap'] = (
            df_detail['inter_incentive'] +
            df_detail['loss_incentive'] +
            df_detail['util_incentive']
        )

    # Add period totals row
    period_totals = {'year': 'Total'}
    for col in df_detail.columns:
        if col == 'year':
            continue
        if col in ['ret_period', 'max_adj']:
            # Sum these for period total
            period_totals[col] = df_detail[col].sum()
        elif df_detail[col].dtype in ['float64', 'int64']:
            period_totals[col] = df_detail[col].sum()

    df_detail = pd.concat([df_detail, pd.DataFrame([period_totals])], ignore_index=True)

    return df_detail


def apply_variable_overrides(
    df: pd.DataFrame,
    user_reid: str,
    variable_overrides: Optional[Dict[str, float]]
) -> pd.DataFrame:
    """
    Apply variable overrides for a specific company.

    Overrides are applied to ALL years (2024-2027) for the given company.
    Other companies are unaffected.

    Args:
        df: DataFrame with incentive data (output from prepare_incentive_input)
        user_reid: REId for the company whose variables to change (e.g. "REL00886")
        variable_overrides: Dict of column name -> new value.
                           E.g. {"nf_obs": 0.045, "ug_obs": 0.65}
                           If None or empty -> no change

    Returns:
        DataFrame with overrides applied.
    """
    if not variable_overrides:
        return df

    df = df.copy()

    # Mask for the user's rows
    mask = df['REId'] == user_reid

    if not mask.any():
        print(f"    [VARNING] Företag {user_reid} hittades inte i incitamentdata")
        return df

    # Apply each override (filter out invalid values)
    applied = []
    for col, value in variable_overrides.items():
        # Skip None, "NULL", "null" and other invalid values
        if value is None or value == "NULL" or value == "null":
            continue

        if col in df.columns:
            try:
                df.loc[mask, col] = float(value)
                applied.append(col)
            except (ValueError, TypeError) as e:
                print(f"    [VARNING] Kunde inte konvertera '{col}'={value}: {e}")
        else:
            print(f"    [VARNING] Okänd variabel '{col}' ignorerades")

    if applied:
        print(f"    Variabel-overrides för {user_reid}: {len(applied)} st ({', '.join(applied[:5])}{'...' if len(applied) > 5 else ''})")

    return df

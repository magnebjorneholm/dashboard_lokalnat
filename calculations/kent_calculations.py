"""
calculations/kent_calculations.py

KENT-beräkningar för kapitalkostnader (Steg 5-8).

UPDATED: Normvalue adjustments now applied AFTER step 5, only to ordinarie
capital base (nuav_ord_{time} columns), not to tail. This matches the
regulatory intent where parameter scaling (1.1-1.2) affects ordinary assets.

OPTIMIZED: Replaced pd.concat with direct column assignment and kept
intermediate arrays as local variables to reduce peak memory by ~67%.
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple

from calculations.wacc_calculations import BASELINE_WACC
from calculations.time_codes import YEAR_TO_TIMECODES


def run_kent_calculations_batch(
    capbase_data: pd.DataFrame,
    wacc: float = BASELINE_WACC,
    normvalue_adjustments: Optional[Dict[int, float]] = None,
    lifetime_adjustments: Optional[Dict[int, Dict[str, int]]] = None,
    return_detailed: bool = True
) -> Tuple[Optional[pd.DataFrame], pd.DataFrame, pd.DataFrame]:
    """
    Run KENT steps 5-8 for all companies.

    Args:
        capbase_data: DataFrame with all components (capbase_a format)
        wacc: WACC to use
        normvalue_adjustments: {cat_encode: multiplier} - applied to ordinarie only
        lifetime_adjustments: {cat_encode: {'ekdep': X, 'maxdep': Y}}
        return_detailed: If False, return None instead of detailed DataFrame
                        to save memory. Pipeline callers should use False.

    Returns:
        Tuple of:
        - df_detailed: Detailed data per component (None if return_detailed=False)
        - df_network: Aggregated per network with per-year columns (for DEA)
        - df_category: Aggregated per (network, category, time) for M1/M2 output
    """
    df = capbase_data.copy()

    # Apply lifetime adjustments BEFORE step 5 (affects ord/tail classification)
    if lifetime_adjustments:
        for cat_encode, adjustments in lifetime_adjustments.items():
            mask = df['cat_encode'] == cat_encode
            if 'ekdep' in adjustments:
                df.loc[mask, 'ekdep'] = adjustments['ekdep']
            if 'maxdep' in adjustments:
                df.loc[mask, 'maxdep'] = adjustments['maxdep']
        print(f"  Applied lifetime adjustments for {len(lifetime_adjustments)} categories")

    # Step 5: Calculate ages and NUAV
    df = calculate_ages_and_nuav_batch(df)

    # Apply normvalue adjustments AFTER step 5, only on ordinarie
    if normvalue_adjustments:
        df = _apply_normvalue_to_ordinarie(df, normvalue_adjustments)
        print(f"  Applied normvalue adjustments to ordinarie for {len(normvalue_adjustments)} categories")

    # Step 6: Calculate depreciation
    df = calculate_depreciation_batch(df)

    # Step 7: Calculate returns
    df = calculate_returns_batch(df, wacc=wacc)

    # Drop age_component columns (no longer needed after step 7)
    age_cols = [f'age_component_{t}' for t in range(229, 237) if f'age_component_{t}' in df.columns]
    if age_cols:
        df.drop(columns=age_cols, inplace=True)

    # Step 8a: Aggregate to network level (for DEA)
    df_network = aggregate_to_network_level(df)
    df_network = calculate_capex_outputs(df_network)

    # Step 8b: Aggregate to category level (for M1/M2 output)
    df_category = aggregate_to_category_level(df)

    df_detailed = df if return_detailed else None
    return df_detailed, df_network, df_category


def _apply_normvalue_to_ordinarie(
    df: pd.DataFrame,
    normvalue_adjustments: Dict[int, float]
) -> pd.DataFrame:
    """
    Apply normvalue adjustments to ordinarie capital base only.

    Applied AFTER step 5 has created nuav_ord_{time} columns.
    Does NOT affect nuav_tail_{time} columns.

    Args:
        df: DataFrame with nuav_ord_{time} columns from step 5
        normvalue_adjustments: {cat_encode: multiplier}

    Returns:
        DataFrame with adjusted nuav_ord_{time} values
    """
    for cat_encode, multiplier in normvalue_adjustments.items():
        mask = df['cat_encode'] == cat_encode

        # Apply to all nuav_ord_{time} columns (229-236)
        for time in range(229, 237):
            col = f'nuav_ord_{time}'
            if col in df.columns:
                df.loc[mask, col] = df.loc[mask, col] * multiplier

    return df


def calculate_ages_and_nuav_batch(df: pd.DataFrame) -> pd.DataFrame:
    """
    Steg 5: Beräkna ålder och NUAV för alla komponenter och tidsperioder.

    Klassificerar komponenter som ordinarie eller tail baserat på ålder vs ekdep/maxdep.
    Skapar age_component_{time}, nuav_ord_{time} och nuav_tail_{time} kolumner.

    Intermediate arrays (base_ord, base_tail, age_component_invest) are kept as
    local numpy variables to avoid storing them on the DataFrame.
    """
    # Pre-extract numpy arrays for faster access in loop
    time_from = df['time_from'].to_numpy()
    time_invest = df['time_invest'].to_numpy()
    capbase_existing = df['capbase_existing'].to_numpy()
    ekdep = df['ekdep'].to_numpy()
    maxdep = df['maxdep'].to_numpy()
    nuav_2022 = df['nuav_2022'].to_numpy()
    invest_isna = df['invest'].isna().to_numpy()
    n = len(df)

    for time in range(229, 237):
        # Age on components — kept on df (needed by steps 6, 7)
        age_component = time - time_from
        df[f'age_component_{time}'] = age_component

        # Age on investments — LOCAL ONLY (only used within this iteration)
        age_component_invest = np.where(capbase_existing == 0, time - time_invest, np.nan)

        # Ordinary capital base classification — LOCAL ONLY
        base_ord = np.zeros(n, dtype='int8')
        base_ord[
            (age_component <= ekdep) & (age_component > 0) & (capbase_existing == 1)
        ] = 1
        base_ord[
            (age_component <= ekdep) & (age_component_invest > 0) & (capbase_existing == 0)
        ] = 1
        base_ord[
            (age_component > ekdep) & (capbase_existing == 0)
        ] = 0

        # NUAV ordinary — kept on df (needed by steps 6, 7, aggregation)
        nuav_ord = nuav_2022 * base_ord
        df[f'nuav_ord_{time}'] = nuav_ord

        # Tail capital base classification — LOCAL ONLY
        base_tail = np.zeros(n, dtype='int8')
        base_tail[
            (age_component <= maxdep) & (age_component > ekdep) & (capbase_existing == 1)
        ] = 1
        base_tail[
            (age_component <= maxdep) & (age_component > ekdep) &
            (time_invest < time) & (~invest_isna)
        ] = 1

        # NUAV tail — kept on df (needed by steps 6, 7, aggregation)
        df[f'nuav_tail_{time}'] = nuav_2022 * base_tail

    return df


def calculate_depreciation_batch(df: pd.DataFrame) -> pd.DataFrame:
    """
    Steg 6: Beräkna avskrivningar för alla komponenter och tidsperioder.

    Intermediate array (age_reg) is kept as local variable.
    """
    ekdep = df['ekdep'].to_numpy(dtype='float64')

    for t in range(229, 237):
        nuav_col = f'nuav_ord_{t}'
        if nuav_col not in df.columns:
            continue

        # Ordinary depreciation — kept on df (needed for aggregation)
        df[f'comp_dep_{t}'] = df[nuav_col].to_numpy() / ekdep

        # Tail depreciation
        age_component = df[f'age_component_{t}'].to_numpy(dtype='float64')

        # age_reg — LOCAL ONLY (only used to compute comp_dep_tail)
        adjustment = np.where(
            (age_component % 2 == 1),
            np.where(age_component > 0, 1, -1),
            0
        )
        age_reg = (age_component + adjustment).astype('float64')

        tail_col = f'nuav_tail_{t}'
        if tail_col in df.columns:
            nuav_tail = df[tail_col].to_numpy(dtype='float64')
            comp_dep_tail = np.divide(
                nuav_tail,
                age_reg,
                out=np.zeros(len(df), dtype='float64'),
                where=(age_reg != 0)
            )
            # kept on df (needed for aggregation)
            df[f'comp_dep_tail_{t}'] = comp_dep_tail

    return df


def calculate_returns_batch(df: pd.DataFrame, wacc: float = BASELINE_WACC) -> pd.DataFrame:
    """
    Steg 7: Beräkna avkastning för alla komponenter och tidsperioder.

    Intermediate arrays (ekdep2, age_return, capbase_left_ord, capbase_left_tail)
    are kept as local variables.
    """
    # ekdep2 as local numpy array (not stored on df)
    ekdep2 = df['ekdep'].to_numpy(dtype='float64') / 2
    n = len(df)

    for time in range(229, 237):
        age_col = f'age_component_{time}'
        if age_col not in df.columns:
            continue

        # age_return — LOCAL ONLY
        age_return = df[age_col].to_numpy(dtype='float64').copy()
        mask_odd = (age_return % 2 == 1)
        adjustment = np.where(age_return > 0, 1, -1)
        age_return = np.where(mask_odd, age_return + adjustment, age_return)
        age_return = age_return / 2 - 1

        # Ordinary returns
        nuav_ord_col = f'nuav_ord_{time}'
        if nuav_ord_col in df.columns:
            nuav_ord = df[nuav_ord_col].to_numpy()
            # capbase_left_ord — LOCAL ONLY
            capbase_left_ord = ((ekdep2 - age_return) / ekdep2) * nuav_ord
            capbase_left_ord = np.where(age_return < 0, 0, capbase_left_ord)

            # return_ord — kept on df (needed for aggregation)
            df[f'return_ord_{time}'] = wacc * capbase_left_ord / 2

        # Tail returns
        nuav_tail_col = f'nuav_tail_{time}'
        if nuav_tail_col in df.columns:
            denominator = age_return + 1
            # capbase_left_tail — LOCAL ONLY
            capbase_left_tail = np.divide(
                df[nuav_tail_col].to_numpy(dtype='float64'),
                denominator,
                out=np.zeros(n, dtype='float64'),
                where=(denominator != 0)
            )

            # return_tail — kept on df (needed for aggregation)
            df[f'return_tail_{time}'] = wacc * capbase_left_tail / 2

    return df


def aggregate_to_network_level(df: pd.DataFrame) -> pd.DataFrame:
    """
    Steg 8: Aggregerar kapitalkostnader till id_network nivå (företagsnivå).

    Summerar dep_ord, dep_tail, return_ord, return_tail per id_network för varje tidsperiod.
    Lägger också till REId för direct joining.
    """
    aggregation_dict = {}

    for t in range(229, 237):
        dep_ord_col = f'comp_dep_{t}'
        dep_tail_col = f'comp_dep_tail_{t}'
        ret_ord_col = f'return_ord_{t}'
        ret_tail_col = f'return_tail_{t}'

        if dep_ord_col in df.columns:
            aggregation_dict[dep_ord_col] = 'sum'
        if dep_tail_col in df.columns:
            aggregation_dict[dep_tail_col] = 'sum'
        if ret_ord_col in df.columns:
            aggregation_dict[ret_ord_col] = 'sum'
        if ret_tail_col in df.columns:
            aggregation_dict[ret_tail_col] = 'sum'

    df_agg = df.groupby('id_network').agg(aggregation_dict).reset_index()

    # Lägg till REId
    df_agg['REId'] = 'REL' + df_agg['id_network'].astype(str).str.zfill(5)

    # Konvertera till tkr
    for col in df_agg.columns:
        if col not in ['id_network', 'REId']:
            df_agg[col] = df_agg[col] / 1000

    # Byt namn på kolumner
    rename_dict = {}
    for t in range(229, 237):
        if f'comp_dep_{t}' in df_agg.columns:
            rename_dict[f'comp_dep_{t}'] = f'dep_ord_{t}'
        if f'comp_dep_tail_{t}' in df_agg.columns:
            rename_dict[f'comp_dep_tail_{t}'] = f'dep_tail_{t}'

    df_agg = df_agg.rename(columns=rename_dict)

    # Beräkna total kapitalkostnad per halvår
    for t in range(229, 237):
        dep_ord = f'dep_ord_{t}'
        dep_tail = f'dep_tail_{t}'
        ret_ord = f'return_ord_{t}'
        ret_tail = f'return_tail_{t}'

        for col in [dep_ord, dep_tail, ret_ord, ret_tail]:
            if col not in df_agg.columns:
                df_agg[col] = 0.0

        df_agg[f'capcost_{t}'] = (
            df_agg[dep_ord] +
            df_agg[dep_tail] +
            df_agg[ret_ord] +
            df_agg[ret_tail]
        )

    return df_agg


def aggregate_to_category_level(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate KENT results to (id_network, cat_encode, time) level.

    Parallel to aggregate_to_network_level() but retains category breakdown.
    Used for M1/M2 output display.

    Args:
        df: DataFrame from calculate_returns_batch() with columns:
            - id_network, cat_encode
            - nuav_ord_{time}, nuav_tail_{time}
            - comp_dep_{time}, comp_dep_tail_{time}
            - return_ord_{time}, return_tail_{time}

    Returns:
        DataFrame with columns (all monetary values in tkr):
            - id_network, cat_encode, time (229-236)
            - nuav_ord, nuav_tail (tkr)
            - dep_ord, dep_tail (tkr)
            - return_ord, return_tail (tkr)
            - capcost_sum (tkr)
    """
    rows = []

    for time in range(229, 237):
        # Build aggregation dict for this time period
        agg_dict = {}
        col_mapping = {}

        # NUAV columns
        nuav_ord_col = f'nuav_ord_{time}'
        nuav_tail_col = f'nuav_tail_{time}'
        if nuav_ord_col in df.columns:
            agg_dict[nuav_ord_col] = 'sum'
            col_mapping[nuav_ord_col] = 'nuav_ord'
        if nuav_tail_col in df.columns:
            agg_dict[nuav_tail_col] = 'sum'
            col_mapping[nuav_tail_col] = 'nuav_tail'

        # Depreciation columns
        dep_ord_col = f'comp_dep_{time}'
        dep_tail_col = f'comp_dep_tail_{time}'
        if dep_ord_col in df.columns:
            agg_dict[dep_ord_col] = 'sum'
            col_mapping[dep_ord_col] = 'dep_ord'
        if dep_tail_col in df.columns:
            agg_dict[dep_tail_col] = 'sum'
            col_mapping[dep_tail_col] = 'dep_tail'

        # Return columns
        ret_ord_col = f'return_ord_{time}'
        ret_tail_col = f'return_tail_{time}'
        if ret_ord_col in df.columns:
            agg_dict[ret_ord_col] = 'sum'
            col_mapping[ret_ord_col] = 'return_ord'
        if ret_tail_col in df.columns:
            agg_dict[ret_tail_col] = 'sum'
            col_mapping[ret_tail_col] = 'return_tail'

        if not agg_dict:
            continue

        # Aggregate per (id_network, cat_encode) for this time
        df_time = df.groupby(['id_network', 'cat_encode']).agg(agg_dict).reset_index()
        df_time['time'] = time

        # Rename to standard names
        df_time = df_time.rename(columns=col_mapping)

        rows.append(df_time)

    if not rows:
        return pd.DataFrame(columns=[
            'id_network', 'cat_encode', 'time',
            'nuav_ord', 'nuav_tail', 'dep_ord', 'dep_tail',
            'return_ord', 'return_tail', 'capcost_sum'
        ])

    result = pd.concat(rows, ignore_index=True)

    # Fill missing columns with 0
    for col in ['nuav_ord', 'nuav_tail', 'dep_ord', 'dep_tail', 'return_ord', 'return_tail']:
        if col not in result.columns:
            result[col] = 0.0

    # Calculate total capital cost per category/time
    result['capcost_sum'] = (
        result['dep_ord'] + result['dep_tail'] +
        result['return_ord'] + result['return_tail']
    )

    # Convert to tkr (matching capcost_a.parquet format and aggregate_to_network_level)
    value_cols = ['nuav_ord', 'nuav_tail', 'dep_ord', 'dep_tail',
                  'return_ord', 'return_tail', 'capcost_sum']
    for col in value_cols:
        if col in result.columns:
            result[col] = result[col] / 1000

    return result


def calculate_capex_outputs(df_network: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate capital cost outputs with correct half-year mapping.

    Timecodes are HALF-YEARS: 229=2024H1, 230=2024H2, 231=2025H1, etc.

    Generates English column names:
    - capital_cost_2024-2027 and capital_cost_period
    - return_on_assets_2024-2027 and return_on_assets_period
    - depreciation_2024-2027 and depreciation_period
    """
    df = df_network.copy()

    for year, timecodes in YEAR_TO_TIMECODES.items():
        t1, t2 = timecodes

        # Capital cost per year
        capcost_cols = [f'capcost_{t}' for t in [t1, t2] if f'capcost_{t}' in df.columns]
        if capcost_cols:
            df[f'capital_cost_{year}'] = df[capcost_cols].sum(axis=1)
        else:
            df[f'capital_cost_{year}'] = 0.0

        # Return on assets per year
        return_cols = []
        for t in [t1, t2]:
            if f'return_ord_{t}' in df.columns:
                return_cols.append(f'return_ord_{t}')
            if f'return_tail_{t}' in df.columns:
                return_cols.append(f'return_tail_{t}')

        if return_cols:
            df[f'return_on_assets_{year}'] = df[return_cols].sum(axis=1)
        else:
            df[f'return_on_assets_{year}'] = 0.0

        # Depreciation per year
        dep_cols = []
        for t in [t1, t2]:
            if f'dep_ord_{t}' in df.columns:
                dep_cols.append(f'dep_ord_{t}')
            if f'dep_tail_{t}' in df.columns:
                dep_cols.append(f'dep_tail_{t}')

        if dep_cols:
            df[f'depreciation_{year}'] = df[dep_cols].sum(axis=1)
        else:
            df[f'depreciation_{year}'] = 0.0

    # Period sums
    df['capital_cost_period'] = df[[f'capital_cost_{y}' for y in [2024, 2025, 2026, 2027]]].sum(axis=1)
    df['return_on_assets_period'] = df[[f'return_on_assets_{y}' for y in [2024, 2025, 2026, 2027]]].sum(axis=1)
    df['depreciation_period'] = df[[f'depreciation_{y}' for y in [2024, 2025, 2026, 2027]]].sum(axis=1)

    return df

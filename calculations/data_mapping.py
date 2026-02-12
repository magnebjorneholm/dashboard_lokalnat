"""
calculations/data_mapping.py

Functions for mapping between id_network, REId and company data.
After RER filtering we have 1:1 mapping: id_network <-> REId.

Merge strategy:
- Baseline has return_on_assets_2024-2027, return_on_assets_period
- KENT updates ONLY companies that were actually recalculated
- Other companies keep their baseline values intact
- SDF fallback for companies without capital_cost_period
"""

import pandas as pd
from typing import Dict, List, Optional, Tuple

from calculations.time_codes import YEAR_TO_TIMECODES

TEST_MODE = True  # Flag for test mode (mini-dataset)


def merge_kent_with_baseline(
    df_network: pd.DataFrame,
    df_all_companies: pd.DataFrame,
    sdf_ir: Optional[pd.DataFrame] = None,
    verbose: bool = True
) -> pd.DataFrame:
    """
    Merge KENT-calculated CAPEX with baseline company data.

    Strategy:
    - Baseline already has return_on_assets_2024-2027, return_on_assets_period
    - KENT updates ONLY companies that were actually recalculated
    - Other companies keep their baseline values intact
    - If sdf_ir is provided: SDF data used as fallback for companies
      missing capital_cost_period (partial KENT coverage)

    Args:
        df_network: DataFrame with capital costs per REId from KENT
        df_all_companies: Baseline company data with controllable_cost_average, volumes, per-year return
        sdf_ir: (Optional) SDF revenue frame data for fallback
        verbose: If True, print detailed debug info

    Returns:
        DataFrame with 148 companies and updated capital costs for KENT-calculated companies
    """

    def log(msg: str, indent: int = 0):
        if verbose:
            prefix = "  " * indent
            print(f"{prefix}{msg}")

    log("── merge_kent_with_baseline() ──", indent=1)

    # 1. Verify REId exists in KENT output
    if 'REId' not in df_network.columns:
        raise ValueError(
            "df_network missing REId column! "
            "Run aggregate_to_network_level first."
        )

    # 2. Start with a copy of baseline
    df_result = df_all_companies.copy()

    # 3. Identify which REIds KENT has recalculated
    kent_reids = set(df_network['REId'].unique())
    baseline_reids = set(df_all_companies['REId'].unique())

    n_kent = len(kent_reids)
    n_baseline = len(baseline_reids)

    log(f"Input: KENT={n_kent} companies, Baseline={n_baseline} companies", indent=2)

    missing_in_kent = baseline_reids - kent_reids
    if missing_in_kent:
        log(f"KENT coverage: {n_kent}/{n_baseline} ({100*n_kent/n_baseline:.1f}%)", indent=2)
        log(f"Without KENT data: {len(missing_in_kent)} companies keep baseline values", indent=2)
    else:
        log(f"KENT coverage: Complete ({n_kent}/{n_baseline})", indent=2)

    # 4. Define columns to update from KENT (all English names)
    update_cols = [
        # Capital costs
        'capital_cost_2024', 'capital_cost_2025',
        'capital_cost_2026', 'capital_cost_2027',
        'capital_cost_period',
        # Return on assets
        'return_on_assets_2024', 'return_on_assets_2025',
        'return_on_assets_2026', 'return_on_assets_2027',
        'return_on_assets_period',
        # Depreciation
        'depreciation_2024', 'depreciation_2025',
        'depreciation_2026', 'depreciation_2027',
        'depreciation_period',
    ]

    # Filter to columns that actually exist in KENT output
    available_update_cols = [col for col in update_cols if col in df_network.columns]

    if not available_update_cols:
        log("[WARNING] KENT output missing updatable columns!", indent=2)
        return df_result

    log(f"Columns from KENT: {len(available_update_cols)}", indent=2)

    # 5. Ensure all update columns exist in result
    for col in available_update_cols:
        if col not in df_result.columns:
            df_result[col] = pd.NA

    # 6. Update ONLY the rows that exist in KENT output
    df_network_indexed = df_network.set_index('REId')

    updated_count = 0
    for reid in kent_reids:
        if reid in df_result['REId'].values:
            mask = df_result['REId'] == reid

            for col in available_update_cols:
                if col in df_network_indexed.columns:
                    value = df_network_indexed.loc[reid, col]
                    df_result.loc[mask, col] = value

            updated_count += 1

    log(f"Updated: {updated_count} companies with KENT values", indent=2)

    # 7. Recalculate TOTEX for all
    df_result['totex_first_year'] = df_result['controllable_cost_average'] + df_result['capital_cost_2024']

    # 8. Fill in capital_cost_period from SDF for companies without KENT data
    df_result, fallback_stats = _apply_capital_cost_period_fallback(
        df_result, sdf_ir, kent_reids, verbose
    )

    # 9. Verify result
    n_result = len(df_result)
    if n_result != n_baseline:
        log(f"[WARNING] Result has {n_result} rows, expected {n_baseline}", indent=2)

    log("── Result ──", indent=1)
    log(f"capital_cost_2024: {(~df_result['capital_cost_2024'].isna()).sum()}/{n_result} companies", indent=2)

    if 'capital_cost_period' in df_result.columns:
        n_period = (~df_result['capital_cost_period'].isna()).sum()
        log(f"capital_cost_period: {n_period}/{n_result} companies "
            f"(KENT: {fallback_stats['from_kent']}, SDF-fallback: {fallback_stats['from_sdf']})", indent=2)

    return df_result


def _apply_capital_cost_period_fallback(
    df_result: pd.DataFrame,
    sdf_ir: Optional[pd.DataFrame],
    kent_reids: set,
    verbose: bool = True
) -> Tuple[pd.DataFrame, Dict]:
    """
    Fill in capital_cost_period from SDF for companies missing KENT data.

    Returns:
        Tuple: (DataFrame with filled capital_cost_period, stats dict)
    """

    def log(msg: str, indent: int = 0):
        if verbose:
            prefix = "  " * indent
            print(f"{prefix}{msg}")

    stats = {
        'from_kent': len(kent_reids),
        'from_sdf': 0,
        'still_missing': 0
    }

    if 'capital_cost_period' not in df_result.columns:
        df_result['capital_cost_period'] = pd.NA

    missing_period_mask = df_result['capital_cost_period'].isna()
    n_missing = missing_period_mask.sum()

    if n_missing == 0:
        log("capital_cost_period: Complete coverage, no fallback needed", indent=2)
        return df_result, stats

    if sdf_ir is None:
        log(f"[WARNING] {n_missing} companies missing capital_cost_period, no SDF available", indent=2)
        stats['still_missing'] = n_missing
        return df_result, stats

    # Find capital cost column in SDF (may be English or Swedish depending on load order)
    sdf_capex_col = None
    for col_name in ['capital_cost_period', 'Kapitalkostnad', 'Kapitalkostnad_Total', 'Kapitalkostnad_Period']:
        if col_name in sdf_ir.columns:
            sdf_capex_col = col_name
            break

    if sdf_capex_col is None:
        log(f"[WARNING] No capital cost column in SDF. Columns: {list(sdf_ir.columns)[:5]}...", indent=2)
        stats['still_missing'] = n_missing
        return df_result, stats

    sdf_lookup = sdf_ir.set_index('REId')[sdf_capex_col].to_dict()

    filled_count = 0
    for idx, row in df_result[missing_period_mask].iterrows():
        reid = row['REId']
        if reid in sdf_lookup:
            sdf_value = sdf_lookup[reid]
            if pd.notna(sdf_value):
                df_result.loc[idx, 'capital_cost_period'] = sdf_value
                filled_count += 1

    stats['from_sdf'] = filled_count

    still_missing = df_result['capital_cost_period'].isna().sum()
    stats['still_missing'] = still_missing

    n_total = len(df_result)
    log(f"[FALLBACK: SDF] {n_missing}/{n_total} companies missing capital_cost_period from KENT", indent=2)
    log(f"                Filled {filled_count} from SDF (column: '{sdf_capex_col}')", indent=2)

    if still_missing > 0:
        log(f"[WARNING] {still_missing} companies still missing capital_cost_period", indent=2)

    return df_result, stats

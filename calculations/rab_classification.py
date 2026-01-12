"""
calculations/rab_classification.py

Classification of capital base components as ordinarie vs. tail.
The classification is DYNAMIC - depends on component age at a specific time point.

Ordinarie: age <= ekdep (within economic lifetime)
Tail: ekdep < age <= maxdep (past economic, within maximum lifetime)
Expired: age > maxdep (fully depreciated)

Key insight: capbase_existing=1 does NOT mean "ordinarie"!
It means "existing component at base year" (vs. new investment during period).
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional


TIMECODE_PERIOD_START = 229  # 2024H1


def calculate_component_age(
    df: pd.DataFrame,
    time: int = TIMECODE_PERIOD_START,
) -> pd.Series:
    """
    Calculate component age at given time point.
    
    Args:
        df: DataFrame with 'time_from' column
        time: Time code (default 229 = 2024H1)
    
    Returns:
        Series with age in half-years
    """
    return time - df['time_from']


def classify_components(
    df: pd.DataFrame,
    time: int = TIMECODE_PERIOD_START,
) -> pd.DataFrame:
    """
    Add classification columns to DataFrame.
    
    Adds columns:
    - age_at_time: Component age at the specified time
    - is_ordinarie: True if age <= ekdep (within economic lifetime)
    - is_tail: True if ekdep < age <= maxdep
    - is_expired: True if age > maxdep
    
    Args:
        df: DataFrame with time_from, ekdep, maxdep, capbase_existing
        time: Time code to evaluate at (default 229 = 2024H1)
    
    Returns:
        DataFrame with classification columns added
    """
    result = df.copy()
    
    # Calculate age
    result['age_at_time'] = time - result['time_from']
    
    # Classify based on age vs lifetimes
    result['is_ordinarie'] = (
        (result['age_at_time'] > 0) &
        (result['age_at_time'] <= result['ekdep'])
    )
    
    result['is_tail'] = (
        (result['age_at_time'] > result['ekdep']) &
        (result['age_at_time'] <= result['maxdep'])
    )
    
    result['is_expired'] = result['age_at_time'] > result['maxdep']
    
    return result


def filter_for_display(
    df: pd.DataFrame,
    vtype_filter: Optional[int] = None,
    time: int = TIMECODE_PERIOD_START,
) -> pd.DataFrame:
    """
    Filter components for UI display.
    
    Shows:
    - Ordinarie components (age <= ekdep at period start)
    - All investments/retirements (capbase_existing=0)
    
    Does NOT show:
    - Tail components (ekdep < age <= maxdep)
    - Expired components (age > maxdep)
    
    Args:
        df: DataFrame with all components
        vtype_filter: Optional vtype to filter by
        time: Time code to evaluate at
        
    Returns:
        Filtered DataFrame for display
    """
    if df is None or df.empty:
        return pd.DataFrame()
    
    # Apply vtype filter first if specified
    if vtype_filter is not None:
        df = df[df['vtype'] == vtype_filter]
    
    if df.empty:
        return df
    
    # Classify components
    classified = classify_components(df, time)
    
    # Filter: ordinarie existing OR any investment
    is_existing = classified['capbase_existing'] == 1
    is_investment = classified['capbase_existing'] == 0
    
    mask = (is_existing & classified['is_ordinarie']) | is_investment
    
    return df[mask].copy()


def get_classification_summary(
    df: pd.DataFrame,
    time: int = TIMECODE_PERIOD_START,
) -> Dict[str, Any]:
    """
    Get summary statistics of classification.
    
    Returns:
        Dict with counts and NUAV per classification
    """
    if df is None or df.empty:
        return {
            'existing_components': {
                'ordinarie': {'count': 0, 'nuav_mkr': 0},
                'tail': {'count': 0, 'nuav_mkr': 0},
                'expired': {'count': 0, 'nuav_mkr': 0},
            },
            'investments': {'count': 0, 'nuav_mkr': 0},
            'total_components': 0,
            'time_evaluated': time,
        }
    
    classified = classify_components(df, time)
    
    # Only count existing components (capbase_existing=1)
    existing = classified[classified['capbase_existing'] == 1]
    investments = classified[classified['capbase_existing'] == 0]
    
    ordinarie = existing[existing['is_ordinarie']]
    tail = existing[existing['is_tail']]
    expired = existing[existing['is_expired']]
    
    return {
        'existing_components': {
            'ordinarie': {
                'count': len(ordinarie),
                'nuav_mkr': ordinarie['nuav_2022'].sum() / 1_000_000 if len(ordinarie) > 0 else 0,
            },
            'tail': {
                'count': len(tail),
                'nuav_mkr': tail['nuav_2022'].sum() / 1_000_000 if len(tail) > 0 else 0,
            },
            'expired': {
                'count': len(expired),
                'nuav_mkr': expired['nuav_2022'].sum() / 1_000_000 if len(expired) > 0 else 0,
            },
        },
        'investments': {
            'count': len(investments),
            'nuav_mkr': investments['nuav_2022'].sum() / 1_000_000 if len(investments) > 0 else 0,
        },
        'total_components': len(df),
        'time_evaluated': time,
    }


def get_tail_summary(df: pd.DataFrame, time: int = TIMECODE_PERIOD_START) -> Dict[str, Any]:
    """
    Get summary of tail components (hidden from UI but included in calculations).
    
    Returns:
        Dict with count and NUAV of tail components
    """
    if df is None or df.empty:
        return {'count': 0, 'nuav_mkr': 0}
    
    classified = classify_components(df, time)
    
    # Tail = existing and is_tail
    is_existing = classified['capbase_existing'] == 1
    tail_mask = is_existing & classified['is_tail']
    
    tail_df = df[tail_mask]
    
    return {
        'count': len(tail_df),
        'nuav_mkr': tail_df['nuav_2022'].sum() / 1_000_000 if len(tail_df) > 0 else 0,
    }
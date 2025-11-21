"""
parameter_adjustments.py - Parameterjusteringar
===============================================

Återanvänd från parameter_adjustments.py (utan UI-delar).
"""

import pandas as pd
from typing import Dict


def apply_normvalue_adjustments(
    capbase_data: pd.DataFrame, 
    adjustments: Dict[int, float],
    level: str = 'cat'
) -> pd.DataFrame:
    """
    Applicerar procentuella normvärdejusteringar.
    
    Args:
        capbase_data: DataFrame med nuav_2022, cat_encode, subcat_encode
        adjustments: Dict med {code: multiplier}, ex: {5: 1.15, 7: 0.90}
        level: 'cat' eller 'subcat'
    
    Returns:
        DataFrame med justerade nuav_2022-värden
    """
    df = capbase_data.copy()
    encode_col = f'{level}_encode'
    
    if encode_col not in df.columns:
        raise ValueError(f"Kolumn '{encode_col}' saknas i data")
    
    for code, multiplier in adjustments.items():
        mask = df[encode_col] == code
        df.loc[mask, 'nuav_2022'] *= multiplier
    
    return df


def apply_lifetime_adjustments(
    capbase_data: pd.DataFrame,
    adjustments: Dict[int, Dict[str, int]],
    level: str = 'cat'
) -> pd.DataFrame:
    """
    Applicerar livslängdsjusteringar.
    
    Args:
        capbase_data: DataFrame med ekdep, maxdep, cat_encode, subcat_encode
        adjustments: Dict med {code: {'ekdep': X, 'maxdep': Y}}
        level: 'cat' eller 'subcat'
    
    Returns:
        DataFrame med justerade ekdep/maxdep-värden
    """
    df = capbase_data.copy()
    encode_col = f'{level}_encode'
    
    if encode_col not in df.columns:
        raise ValueError(f"Kolumn '{encode_col}' saknas i data")
    
    for code, params in adjustments.items():
        mask = df[encode_col] == code
        if 'ekdep' in params:
            df.loc[mask, 'ekdep'] = params['ekdep'] * 2
        if 'maxdep' in params:
            df.loc[mask, 'maxdep'] = params['maxdep'] * 2
    
    return df
"""
Effektiviseringskrav producer
Beräknar effektiviseringskrav från efficiency scores
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional


def calculate_effkrav_from_potential(
    potential: float,
    is_outlier: bool,
    trunkering_min: float = 0.162416,
    trunkering_max: float = 0.3,
    outlier_krav: float = 0.01
) -> float:
    """
    Beräknar årligt effektiviseringskrav från potential.
    
    Implementerar Ei:s metod:
    1. Trunkera potential mellan min/max
    2. Konvertera till årligt krav med 4-årsperiod
    3. För outliers: använd fast krav
    """
    if is_outlier:
        return outlier_krav
    
    revred_compress = np.clip(potential, trunkering_min, trunkering_max)
    revred_compress_yearly = ((1 + revred_compress / 4) ** 0.25) - 1
    return revred_compress_yearly


def calculate_effkrav_for_dataframe(
    df: pd.DataFrame,
    potential_col: str = 'potential',
    outlier_col: str = 'is_outlier',
    trunkering_min: float = 0.162416,
    trunkering_max: float = 0.3,
    outlier_krav: float = 0.01
) -> pd.DataFrame:
    """
    Beräknar effektiviseringskrav för alla företag i DataFrame.
    Använder outlier-flagga från DEA.
    """
    result = df.copy()
    
    result['Effkrav_proc'] = result.apply(
        lambda row: calculate_effkrav_from_potential(
            potential=row[potential_col],
            is_outlier=row[outlier_col],
            trunkering_min=trunkering_min,
            trunkering_max=trunkering_max,
            outlier_krav=outlier_krav
        ),
        axis=1
    )
    
    return result


def produce_effektiviseringskrav(
    efficiency_data: pd.DataFrame,
    trunkering_min: float = 0.162416,
    trunkering_max: float = 0.3,
    outlier_krav: float = 0.01,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Producer för effektiviseringskrav från efficiency scores.
    
    Args:
        efficiency_data: DataFrame med efficiency-resultat, måste innehålla:
            - DMU
            - REId
            - potential (ineffektivitet, 1 - effektivitet)
            - is_outlier (bool)
            - Företag (optional)
        trunkering_min: Minsta trunkering (default Ei-värde)
        trunkering_max: Högsta trunkering (default Ei-värde)
        outlier_krav: Fast årligt krav för outliers
        metadata: Extra metadata att inkludera
        
    Returns:
        Dict med:
            - data: DataFrame med Effkrav_proc-kolumn tillagd
            - metadata: Dict med beräkningsinformation
    """
    if efficiency_data.empty:
        raise ValueError("efficiency_data är tom")
    
    required_cols = ['DMU', 'REId', 'potential', 'is_outlier']
    missing_cols = [col for col in required_cols if col not in efficiency_data.columns]
    if missing_cols:
        raise ValueError(f"Saknade kolumner i efficiency_data: {missing_cols}")
    
    result_df = calculate_effkrav_for_dataframe(
        efficiency_data,
        potential_col='potential',
        outlier_col='is_outlier',
        trunkering_min=trunkering_min,
        trunkering_max=trunkering_max,
        outlier_krav=outlier_krav
    )
    
    n_outliers = result_df['is_outlier'].sum()
    n_total = len(result_df)
    mean_krav = result_df['Effkrav_proc'].mean()
    
    result_metadata = {
        'source': 'calculated',
        'method': 'truncated_potential',
        'n_companies': n_total,
        'n_outliers': int(n_outliers),
        'n_regular': n_total - n_outliers,
        'trunkering_min': trunkering_min,
        'trunkering_max': trunkering_max,
        'outlier_krav': outlier_krav,
        'mean_effkrav_pct': float(mean_krav * 100),
        'min_effkrav_pct': float(result_df['Effkrav_proc'].min() * 100),
        'max_effkrav_pct': float(result_df['Effkrav_proc'].max() * 100)
    }
    
    if metadata:
        result_metadata['input_metadata'] = metadata
    
    return {
        'data': result_df,
        'metadata': result_metadata
    }
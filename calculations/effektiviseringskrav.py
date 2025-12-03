"""
calculations/effektiviseringskrav.py

Beräkningsfunktioner för effektiviseringskrav.
Konverterar DEA-potential till årligt effektiviseringskrav enligt Ei's metod.
"""

import numpy as np
import pandas as pd
from typing import Optional


def calculate_effkrav_from_potential(
    potential: float,
    is_outlier: bool,
    trunkering_min: float = 0.162416,
    trunkering_max: float = 0.3,
    outlier_krav: float = 0.01
) -> float:
    """
    Beräknar årligt effektiviseringskrav från potential.
    
    Implementerar Ei's metod:
    1. Om outlier: använd fast krav (default 1%)
    2. Trunkera potential mellan min/max
    3. Konvertera till årligt krav med 4-årsperiod: ((1 + p/4)^0.25) - 1
    
    Args:
        potential: Ineffektivitet (1 - effektivitet), 0-1 range
        is_outlier: Om företaget är outlier
        trunkering_min: Minsta trunkering (default 0.162416 = 16.24%)
        trunkering_max: Högsta trunkering (default 0.3 = 30%)
        outlier_krav: Fast årligt krav för outliers (default 0.01 = 1%)
        
    Returns:
        Årligt effektiviseringskrav (decimal, t.ex. 0.015 = 1.5% per år)
    """
    if is_outlier:
        return outlier_krav
    
    # Trunkera potential
    potential_trunkerad = np.clip(potential, trunkering_min, trunkering_max)
    
    # Konvertera till årligt krav
    # Formula: ((1 + potential/4)^(1/4)) - 1
    effkrav_yearly = ((1 + potential_trunkerad / 4) ** 0.25) - 1
    
    return effkrav_yearly


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
    
    Args:
        df: DataFrame med potential och outlier-flagga från DEA
        potential_col: Kolumnnamn för potential (default 'potential')
        outlier_col: Kolumnnamn för outlier-flagga (default 'is_outlier')
        trunkering_min: Minsta trunkering
        trunkering_max: Högsta trunkering
        outlier_krav: Fast årligt krav för outliers
        
    Returns:
        DataFrame med ny kolumn 'Effkrav_proc' (årligt effektiviseringskrav)
    """
    result = df.copy()
    
    # Validera att kolumner finns
    if potential_col not in result.columns:
        raise ValueError(f"Kolumn '{potential_col}' saknas i DataFrame")
    if outlier_col not in result.columns:
        raise ValueError(f"Kolumn '{outlier_col}' saknas i DataFrame")
    
    # Beräkna effektiviseringskrav för varje rad
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


# Default parametrar från Ei's metod
DEFAULT_EFFKRAV_PARAMS = {
    'trunkering_min': 0.162416,
    'trunkering_max': 0.3,
    'outlier_krav': 0.01
}
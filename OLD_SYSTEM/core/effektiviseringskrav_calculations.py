"""
Beräkningsfunktioner för effektiviseringskrav i intäktsram-tabben.
Flyttat från DEA-modulen för att ge användaren kontroll över parametrar.
"""

import numpy as np
import pandas as pd


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
    
    Args:
        potential: Ineffektivitet (1 - effektivitet)
        is_outlier: Om företaget är outlier
        trunkering_min: Minsta trunkering
        trunkering_max: Högsta trunkering
        outlier_krav: Fast årligt krav för outliers
        
    Returns:
        Årligt effektiviseringskrav (decimal)
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
    Använder outlier-flagga från DEA (omberäknar inte outliers).
    
    Args:
        df: DataFrame med potential och outlier-flagga från DEA
        potential_col: Kolumnnamn för potential
        outlier_col: Kolumnnamn för outlier-flagga
        trunkering_min: Minsta trunkering
        trunkering_max: Högsta trunkering
        outlier_krav: Fast årligt krav för outliers
        
    Returns:
        DataFrame med ny kolumn 'Effkrav_proc'
    """
    result = df.copy()
    
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
"""
calculations/effektiviseringskrav.py

Beräkningsfunktioner för effektiviseringskrav.
Konverterar DEA-potential till årligt effektiviseringskrav enligt Ei's metod.
"""

import numpy as np
import pandas as pd
from typing import Optional


# Default parametrar från Ei's metod för tillsynsperiod 2024-2027
DEFAULT_EFFKRAV_PARAMS = {
    'trunkering_min': 0.162416,   # Min potential för trunkering (16.24%)
    'trunkering_max': 0.30,       # Max potential för trunkering (30%)
    'outlier_krav': 0.01,         # Fast årligt krav för outliers (1%)
    'kunddelning': 0.50,          # Andel som tillfaller kunder (50%)
    'realiseringstid': 8,         # År för att uppnå full effektivisering
    'tillsynsperiod': 4,          # Längd på tillsynsperiod i år
}


def calculate_effkrav_from_potential(
    potential: float,
    is_outlier: bool,
    trunkering_min: float = 0.162416,
    trunkering_max: float = 0.30,
    outlier_krav: float = 0.01,
    kunddelning: float = 0.50,
    realiseringstid: int = 8,
    tillsynsperiod: int = 4
) -> float:
    """
    Beräknar årligt effektiviseringskrav från potential.
    
    Implementerar Ei's fullständiga formel:
    
    1. Om outlier: använd fast krav (default 1%)
    2. Trunkera potential mellan min/max
    3. Beräkna total effektivisering: potential * kunddelning * (tillsynsperiod/realiseringstid)
    4. Fördela över tillsynsperioden: (1 + total_eff)^(1/tillsynsperiod) - 1
    
    För tillsynsperiod 2024-2027 med default-parametrar:
    - Max årligt krav: 1.82%
    - Min årligt krav: 1.0% (outlier_krav)
    
    Args:
        potential: Ineffektivitet (1 - effektivitet), 0-1 range
        is_outlier: Om företaget är outlier
        trunkering_min: Minsta potential för trunkering (default 16.24%)
        trunkering_max: Högsta potential för trunkering (default 30%)
        outlier_krav: Fast årligt krav för outliers (default 1%)
        kunddelning: Andel av effektivisering som tillfaller kunder (default 50%)
        realiseringstid: Antal år för att uppnå full effektivisering (default 8)
        tillsynsperiod: Längd på tillsynsperiod i år (default 4)
        
    Returns:
        Årligt effektiviseringskrav (decimal, t.ex. 0.0182 = 1.82% per år)
    """
    if is_outlier:
        return outlier_krav
    
    # Trunkera potential
    potential_trunkerad = np.clip(potential, trunkering_min, trunkering_max)
    
    # Beräkna total effektivisering under tillsynsperioden
    # = potential * kunddelning * (tillsynsperiod / realiseringstid)
    total_effektivisering = potential_trunkerad * kunddelning * (tillsynsperiod / realiseringstid)
    
    # Fördela över tillsynsperioden med ränta-på-ränta
    # Årligt krav = (1 + total)^(1/period) - 1
    effkrav_yearly = (1 + total_effektivisering) ** (1 / tillsynsperiod) - 1
    
    return effkrav_yearly


def calculate_effkrav_for_dataframe(
    df: pd.DataFrame,
    potential_col: str = 'potential',
    outlier_col: str = 'is_outlier',
    trunkering_min: float = 0.162416,
    trunkering_max: float = 0.30,
    outlier_krav: float = 0.01,
    kunddelning: float = 0.50,
    realiseringstid: int = 8,
    tillsynsperiod: int = 4
) -> pd.DataFrame:
    """
    Beräknar effektiviseringskrav för alla företag i DataFrame.
    
    Args:
        df: DataFrame med potential och outlier-flagga från DEA
        potential_col: Kolumnnamn för potential (default 'potential')
        outlier_col: Kolumnnamn för outlier-flagga (default 'is_outlier')
        trunkering_min: Minsta potential för trunkering
        trunkering_max: Högsta potential för trunkering
        outlier_krav: Fast årligt krav för outliers
        kunddelning: Andel av effektivisering som tillfaller kunder
        realiseringstid: Antal år för att uppnå full effektivisering
        tillsynsperiod: Längd på tillsynsperiod i år
        
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
            outlier_krav=outlier_krav,
            kunddelning=kunddelning,
            realiseringstid=realiseringstid,
            tillsynsperiod=tillsynsperiod
        ),
        axis=1
    )
    
    return result


def get_max_effkrav(
    trunkering_max: float = 0.30,
    kunddelning: float = 0.50,
    realiseringstid: int = 8,
    tillsynsperiod: int = 4
) -> float:
    """
    Beräknar maximalt årligt effektiviseringskrav givet parametrarna.
    
    Användbart för validering och UI-visning.
    
    Returns:
        Max årligt effektiviseringskrav (t.ex. 0.0182 = 1.82%)
    """
    return calculate_effkrav_from_potential(
        potential=trunkering_max,
        is_outlier=False,
        trunkering_min=0.0,
        trunkering_max=trunkering_max,
        kunddelning=kunddelning,
        realiseringstid=realiseringstid,
        tillsynsperiod=tillsynsperiod
    )
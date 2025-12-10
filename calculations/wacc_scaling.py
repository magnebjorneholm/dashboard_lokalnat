"""
calculations/wacc_scaling.py

WACC-skalning: Skalar avkastning med ny WACC medan avskrivning halls konstant.

Formel:
    Kapitalkostnad_2024 = Avskrivning + Avkastning
    Ny Avkastning = Baseline Avkastning * (ny_WACC / baseline_WACC)
    Ny Kapitalkostnad_2024 = Avskrivning + Ny Avkastning

Producerar:
    - Kapitalkostnad_2024: Årsvärde för 2024 (för DEA)
    - Avskrivning: Oförändrad från baseline
    - Avkastning: Skalad med WACC-kvot
"""

import pandas as pd
from typing import Optional


def calculate_wacc_scaled_capex(
    df_all_companies: pd.DataFrame,
    new_wacc: float,
    baseline_wacc: float = 0.0453
) -> pd.DataFrame:
    """
    Skalar CAPEX for alla foretag med ny WACC.
    
    Metod:
    - Avskrivning halls konstant
    - Avkastning skalas med (ny_WACC / baseline_WACC)
    - CAPEX = Avskrivning + Ny Avkastning
    - TOTEX = OPEXp + CAPEX (uppdateras)
    
    Args:
        df_all_companies: DataFrame med alla 148 foretag
            Maste innehalla: CAPEX, Avskrivning, Avkastning, OPEXp
        new_wacc: Ny WACC (real fore skatt)
        baseline_wacc: Baseline WACC (default 0.0453)
        
    Returns:
        DataFrame med uppdaterad CAPEX, Kapitalkostnad_2024, och TOTEX
        
    Example:
        >>> df_scaled = calculate_wacc_scaled_capex(
        ...     df_all_companies, 
        ...     new_wacc=0.05,
        ...     baseline_wacc=0.0453
        ... )
        >>> # CAPEX och TOTEX ar nu uppdaterade
    """
    
    # Validera input
    required_cols = ['Kapitalkostnad_2024', 'Avskrivning', 'Avkastning', 'OPEXp']
    missing = [col for col in required_cols if col not in df_all_companies.columns]
    if missing:
        raise ValueError(f"Saknar obligatoriska kolumner: {missing}")
    
    if new_wacc <= 0:
        raise ValueError(f"WACC maste vara positiv: {new_wacc}")
    
    if baseline_wacc <= 0:
        raise ValueError(f"Baseline WACC maste vara positiv: {baseline_wacc}")
    
    # Kopiera for att inte modifiera original
    df = df_all_companies.copy()
    
    # Berakna skalningsfaktor
    scaling_factor = new_wacc / baseline_wacc
    
    # Ny avkastning = baseline avkastning * skalningsfaktor
    df['Avkastning'] = df['Avkastning'] * scaling_factor
    
    # Ny Kapitalkostnad_2024 = Avskrivning + Ny Avkastning (Årsvärde)
    df['Kapitalkostnad_2024'] = df['Avskrivning'] + df['Avkastning']

    # Uppdatera TOTEX = OPEXp + Kapitalkostnad_2024
    df['TOTEX'] = df['OPEXp'] + df['Kapitalkostnad_2024']
    
    return df


def get_wacc_scaling_summary(
    df_baseline: pd.DataFrame,
    df_scaled: pd.DataFrame,
    new_wacc: float,
    baseline_wacc: float
) -> dict:
    """
    Sammanfattar effekten av WACC-skalning.
    
    Args:
        df_baseline: Baseline DataFrame
        df_scaled: Skalad DataFrame
        new_wacc: Ny WACC
        baseline_wacc: Baseline WACC
        
    Returns:
        Dict med sammanfattning
    """
    
    baseline_capex = df_baseline['Kapitalkostnad_2024'].sum()
    scaled_capex = df_scaled['Kapitalkostnad_2024'].sum()
    
    baseline_avkastning = df_baseline['Avkastning'].sum()
    scaled_avkastning = df_scaled['Avkastning'].sum()
    
    return {
        'baseline_wacc': baseline_wacc,
        'new_wacc': new_wacc,
        'scaling_factor': new_wacc / baseline_wacc,
        'baseline_capex_total': baseline_capex,
        'scaled_capex_total': scaled_capex,
        'capex_change': scaled_capex - baseline_capex,
        'capex_change_pct': (scaled_capex / baseline_capex - 1) * 100,
        'baseline_avkastning_total': baseline_avkastning,
        'scaled_avkastning_total': scaled_avkastning,
        'avkastning_change': scaled_avkastning - baseline_avkastning,
        'avkastning_change_pct': (scaled_avkastning / baseline_avkastning - 1) * 100,
        'n_companies': len(df_scaled)
    }
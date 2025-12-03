"""
calculations/wacc_scaling.py

WACC-skalning: Skalar avkastning med ny WACC medan avskrivning hålls konstant.

Formel:
    CAPEX = Avskrivning + Avkastning
    Ny Avkastning = Baseline Avkastning × (ny_WACC / baseline_WACC)
    Ny CAPEX = Avskrivning + Ny Avkastning
"""

import pandas as pd
from typing import Optional


def calculate_wacc_scaled_capex(
    df_all_companies: pd.DataFrame,
    new_wacc: float,
    baseline_wacc: float = 0.0453
) -> pd.DataFrame:
    """
    Skalar CAPEX för alla företag med ny WACC.
    
    Metod:
    - Avskrivning hålls konstant
    - Avkastning skalas med (ny_WACC / baseline_WACC)
    - CAPEX = Avskrivning + Ny Avkastning
    - TOTEX = OPEXp + CAPEX (uppdateras)
    
    Args:
        df_all_companies: DataFrame med alla 148 företag
            Måste innehålla: CAPEX, Avskrivning, Avkastning, OPEXp
        new_wacc: Ny WACC (real före skatt)
        baseline_wacc: Baseline WACC (default 0.0453)
        
    Returns:
        DataFrame med uppdaterad CAPEX och TOTEX
        
    Example:
        >>> df_scaled = calculate_wacc_scaled_capex(
        ...     df_all_companies, 
        ...     new_wacc=0.05,
        ...     baseline_wacc=0.0453
        ... )
        >>> # CAPEX och TOTEX är nu uppdaterade
    """
    
    # Validera input
    required_cols = ['CAPEX', 'Avskrivning', 'Avkastning', 'OPEXp']
    missing = [col for col in required_cols if col not in df_all_companies.columns]
    if missing:
        raise ValueError(f"Saknar obligatoriska kolumner: {missing}")
    
    if new_wacc <= 0:
        raise ValueError(f"WACC måste vara positiv: {new_wacc}")
    
    if baseline_wacc <= 0:
        raise ValueError(f"Baseline WACC måste vara positiv: {baseline_wacc}")
    
    # Kopiera för att inte modifiera original
    df = df_all_companies.copy()
    
    # Beräkna skalningsfaktor
    scaling_factor = new_wacc / baseline_wacc
    
    # Ny avkastning = baseline avkastning × skalningsfaktor
    df['Avkastning'] = df['Avkastning'] * scaling_factor
    
    # Ny CAPEX = Avskrivning + Ny Avkastning
    df['CAPEX'] = df['Avskrivning'] + df['Avkastning']
    
    # Uppdatera TOTEX = OPEXp + CAPEX
    df['TOTEX'] = df['OPEXp'] + df['CAPEX']
    
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
    
    baseline_capex = df_baseline['CAPEX'].sum()
    scaled_capex = df_scaled['CAPEX'].sum()
    
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
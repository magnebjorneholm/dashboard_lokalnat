"""
calculations/wacc_scaling.py

WACC-skalning: Skalar avkastning med ny WACC medan avskrivning hålls konstant.

Formel:
    Kapitalkostnad_2024 = Avskrivning + Avkastning
    Ny Avkastning = Baseline Avkastning * (ny_WACC / baseline_WACC)
    Ny Kapitalkostnad_2024 = Avskrivning + Ny Avkastning

UPPDATERAD med stöd för per-år avkastning:
- Kan nu skala Avkastning_2024-2027 individuellt
- Bevarar årlig variation istället för att använda ett genomsnitt
- Beräknar Avkastning_Period från skalade per-år värden
"""

import pandas as pd
from typing import Dict, List, Optional


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
    
    UPPDATERAD: Skalar nu även per-år avkastning om kolumnerna finns.
    
    Args:
        df_all_companies: DataFrame med alla 148 företag
            Måste innehålla: CAPEX, Avskrivning, Avkastning, OPEXp
            Kan innehålla: Avkastning_2024-2027, Avkastning_Period
        new_wacc: Ny WACC (real före skatt)
        baseline_wacc: Baseline WACC (default 0.0453)
        
    Returns:
        DataFrame med uppdaterad CAPEX, Kapitalkostnad_2024, och TOTEX
    """
    
    # Validera input
    required_cols = ['Kapitalkostnad_2024', 'Avskrivning', 'Avkastning', 'OPEXp']
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
    
    # Skala aggregerad avkastning
    df['Avkastning'] = df['Avkastning'] * scaling_factor
    
    # Skala per-år avkastning om kolumnerna finns
    yearly_cols = ['Avkastning_2024', 'Avkastning_2025', 
                   'Avkastning_2026', 'Avkastning_2027']
    
    has_yearly = all(col in df.columns for col in yearly_cols)
    
    if has_yearly:
        for col in yearly_cols:
            df[col] = df[col] * scaling_factor
        
        # Beräkna ny periodsumma från skalade per-år värden
        df['Avkastning_Period'] = (
            df['Avkastning_2024'] + df['Avkastning_2025'] +
            df['Avkastning_2026'] + df['Avkastning_2027']
        )
    elif 'Avkastning_Period' in df.columns:
        # Skala periodsumma om per-år saknas
        df['Avkastning_Period'] = df['Avkastning_Period'] * scaling_factor
    
    # Ny Kapitalkostnad_2024 = Avskrivning + Ny Avkastning (Årsvärde)
    df['Kapitalkostnad_2024'] = df['Avskrivning'] + df['Avkastning']

    # Uppdatera TOTEX = OPEXp + Kapitalkostnad_2024
    df['TOTEX'] = df['OPEXp'] + df['Kapitalkostnad_2024']
    
    return df


def calculate_wacc_scaled_yearly_returns(
    df_all_companies: pd.DataFrame,
    new_wacc: float,
    baseline_wacc: float = 0.0453
) -> pd.DataFrame:
    """
    Skalar per-år avkastning med ny WACC.
    
    Returnerar endast REId och skalade per-år avkastningskolumner.
    Används av get_return_per_year() i post_dea.py.
    
    Args:
        df_all_companies: DataFrame med per-år avkastningskolumner
        new_wacc: Ny WACC
        baseline_wacc: Baseline WACC
        
    Returns:
        DataFrame med REId och Avkastning_2024-2027 (skalade)
    """
    yearly_cols = ['Avkastning_2024', 'Avkastning_2025', 
                   'Avkastning_2026', 'Avkastning_2027']
    
    # Validera att per-år kolumner finns
    missing = [col for col in yearly_cols if col not in df_all_companies.columns]
    if missing:
        raise ValueError(
            f"Kan inte skala per-år avkastning - saknar kolumner: {missing}. "
            "Använd baseline som har dessa kolumner."
        )
    
    scaling_factor = new_wacc / baseline_wacc
    
    # Skapa resultat
    df_result = df_all_companies[['REId']].copy()
    
    for col in yearly_cols:
        df_result[col] = df_all_companies[col] * scaling_factor
    
    return df_result


def get_wacc_scaling_summary(
    df_baseline: pd.DataFrame,
    df_scaled: pd.DataFrame,
    new_wacc: float,
    baseline_wacc: float
) -> Dict:
    """
    Sammanfattar effekten av WACC-skalning.
    
    UPPDATERAD: Inkluderar nu per-år statistik om tillgänglig.
    
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
    
    summary = {
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
    
    # Lägg till per-år statistik om tillgänglig
    yearly_cols = ['Avkastning_2024', 'Avkastning_2025', 
                   'Avkastning_2026', 'Avkastning_2027']
    
    if all(col in df_baseline.columns for col in yearly_cols):
        summary['has_yearly_returns'] = True
        
        for year in [2024, 2025, 2026, 2027]:
            col = f'Avkastning_{year}'
            summary[f'baseline_avkastning_{year}'] = float(df_baseline[col].sum())
            summary[f'scaled_avkastning_{year}'] = float(df_scaled[col].sum())
    else:
        summary['has_yearly_returns'] = False
    
    return summary


def validate_wacc_scaling_inputs(
    df: pd.DataFrame,
    require_yearly: bool = False
) -> Dict:
    """
    Validerar att DataFrame har nödvändiga kolumner för WACC-skalning.
    
    Args:
        df: DataFrame att validera
        require_yearly: Om True, kräv per-år avkastningskolumner
        
    Returns:
        Dict med valideringsresultat
    """
    result = {
        'valid': True,
        'errors': [],
        'warnings': [],
        'available_columns': list(df.columns)
    }
    
    # Obligatoriska kolumner
    required = ['Kapitalkostnad_2024', 'Avskrivning', 'Avkastning', 'OPEXp', 'REId']
    missing = [col for col in required if col not in df.columns]
    
    if missing:
        result['valid'] = False
        result['errors'].append(f"Saknar obligatoriska kolumner: {missing}")
    
    # Per-år kolumner
    yearly = ['Avkastning_2024', 'Avkastning_2025', 
              'Avkastning_2026', 'Avkastning_2027']
    missing_yearly = [col for col in yearly if col not in df.columns]
    
    if missing_yearly:
        if require_yearly:
            result['valid'] = False
            result['errors'].append(f"Saknar per-år avkastningskolumner: {missing_yearly}")
        else:
            result['warnings'].append(
                f"Per-år avkastning saknas ({missing_yearly}). "
                "WACC-skalning använder approximation."
            )
    else:
        result['has_yearly_returns'] = True
    
    # Validera numeriska värden
    if result['valid']:
        for col in required[:-1]:  # Exkludera REId
            if col in df.columns:
                if df[col].isna().any():
                    result['warnings'].append(f"Kolumn {col} innehåller NaN-värden")
                if (df[col] < 0).any():
                    result['warnings'].append(f"Kolumn {col} innehåller negativa värden")
    
    return result
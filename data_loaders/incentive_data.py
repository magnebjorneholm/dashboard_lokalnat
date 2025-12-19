"""
incentive_data.py

Laddar och förbereder incitamentdata från all_adjust_vars.csv.
Mappar numerisk reid till REId-format (REL00001, etc.).
"""

import pandas as pd
from pathlib import Path
from typing import Optional


def load_incentive_data(filepath: Optional[str] = None) -> pd.DataFrame:
    """
    Laddar incitamentdata och förbereder den för beräkning.
    
    Args:
        filepath: Sökväg till all_adjust_vars.csv. Om None, använd default.
    
    Returns:
        DataFrame med alla incitamentvariabler, REId i korrekt format.
        Kolumnen 'capcost' tas bort (placeholder som ersätts med faktisk avkastning).
    """
    if filepath is None:
        # Default sökväg relativt till projektrot
        # Prova flera möjliga platser
        possible_paths = [
            Path(__file__).parent / "data" / "all_adjust_vars.csv",
            Path(__file__).parent.parent / "data" / "all_adjust_vars.csv",
            Path("data") / "all_adjust_vars.csv",
        ]
        for path in possible_paths:
            if path.exists():
                filepath = path
                break
        else:
            raise FileNotFoundError(
                f"Kunde inte hitta all_adjust_vars.csv. Prövade: {possible_paths}"
            )
    
    df = pd.read_csv(filepath)
    
    # Mappa numerisk reid till REId-format (REL00001, REL00886, etc.)
    df['REId'] = df['reid'].apply(lambda x: f"REL{int(x):05d}")
    
    # Ta bort placeholder capcost - ersätts med faktisk avkastning i pipeline
    if 'capcost' in df.columns:
        df = df.drop(columns=['capcost'])
    
    return df


def prepare_incentive_input(
    incentive_data: pd.DataFrame,
    return_per_year: pd.DataFrame
) -> pd.DataFrame:
    """
    Förbereder komplett input för incitamentberäkning genom att
    slå ihop incitamentdata med avkastning per år.
    
    Args:
        incentive_data: DataFrame från load_incentive_data()
        return_per_year: DataFrame med REId, Avkastning_2024..2027 (tkr)
    
    Returns:
        DataFrame med alla variabler redo för calculate_all_incentives().
        Innehåller kolumnen 'ret_period' (avkastning i kr för respektive år).
    """
    df = incentive_data.copy()
    
    # Slå ihop med avkastning per år
    df = df.merge(return_per_year, on='REId', how='left')
    
    # Skapa ret_period baserat på år (konvertera tkr -> kr)
    df['ret_period'] = df.apply(
        lambda row: row.get(f"Avkastning_{int(row['year'])}", 0) * 1000,
        axis=1
    )
    
    return df


def get_incentive_summary_by_reid(
    incentive_results: pd.DataFrame
) -> pd.DataFrame:
    """
    Aggregerar incitamentresultat till en rad per REId (periodsumma).
    
    Args:
        incentive_results: Output från calculate_all_incentives()
    
    Returns:
        DataFrame med en rad per REId:
        - REId
        - Kvalitetsjustering_Total (tkr)
        - Natforlustjustering_Total (tkr)
        - Belastningsjustering_Total (tkr)
        - Incitamentjustering_Total (tkr)
        - Missing_Incentive_Data (bool)
    """
    from calculations.incentive_parameters import MISSING_DATA_IDS
    
    # Periodsummorna finns redan på alla rader (aggregate_period_totals)
    # Extrahera en rad per REId
    df_summary = incentive_results.groupby('REId').first().reset_index()
    
    # Välj relevanta kolumner
    cols_to_keep = ['REId']
    rename_map = {}
    
    # Periodsummor (från aggregate_period_totals)
    if 'inter_incentive_sum' in df_summary.columns:
        cols_to_keep.append('inter_incentive_sum')
        rename_map['inter_incentive_sum'] = 'Kvalitetsjustering_Total'
    if 'loss_incentive_sum' in df_summary.columns:
        cols_to_keep.append('loss_incentive_sum')
        rename_map['loss_incentive_sum'] = 'Natforlustjustering_Total'
    if 'util_incentive_sum' in df_summary.columns:
        cols_to_keep.append('util_incentive_sum')
        rename_map['util_incentive_sum'] = 'Belastningsjustering_Total'
    if 'incentive_total' in df_summary.columns:
        cols_to_keep.append('incentive_total')
        rename_map['incentive_total'] = 'Incitamentjustering_Total'
    
    df_summary = df_summary[cols_to_keep].copy()
    
    # Konvertera från kr till tkr
    for col in cols_to_keep[1:]:  # Skippa REId
        df_summary[col] = df_summary[col] / 1000
    
    # Byt namn
    df_summary = df_summary.rename(columns=rename_map)
    
    # Flagga för saknad data (baserat på numerisk reid i MISSING_DATA_IDS)
    df_summary['Missing_Incentive_Data'] = df_summary['REId'].apply(
        lambda x: int(x.replace('REL', '')) in MISSING_DATA_IDS
    )
    
    return df_summary
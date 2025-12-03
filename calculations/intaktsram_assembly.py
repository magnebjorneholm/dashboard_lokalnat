"""
calculations/intaktsram_assembly.py

Assemblering av intäktsram från alla komponenter.
Summerar kapitalkostnad, påverkbara, opåverkbara, och övriga komponenter.
"""

import pandas as pd
from typing import Optional


def assemble_intaktsram(
    capex_result: pd.DataFrame,
    paverkbara_result: pd.DataFrame,
    sdf_baseline: pd.DataFrame
) -> pd.DataFrame:
    """
    Assemblerar komplett intäktsram för alla företag.
    
    Formel:
    Intäktsram_Total = Kapitalkostnad_Total
                     + Påverkbara_Periodsumma
                     + Opåverkbara_Kostnader
                     + Flexibilitetstjänster
                     + Avbrottsersättning_12_24h
                     - Avdrag_Statligt_Stöd
    
    Args:
        capex_result: DataFrame med REId, Avskrivningar, Avkastning, Kapitalkostnad_Total
        paverkbara_result: DataFrame med REId, Paverkbara_Periodsumma
        sdf_baseline: DataFrame från SDF Excel med opåverkbara och övriga komponenter
        
    Returns:
        DataFrame med alla komponenter och Intaktsram_Total
    """
    # Start med CAPEX
    df = capex_result[['REId', 'Avskrivningar', 'Avkastning', 'Kapitalkostnad_Total']].copy()
    
    # Merge påverkbara
    df = df.merge(
        paverkbara_result[['REId', 'Paverkbara_Periodsumma', 'Method_used']],
        on='REId',
        how='left'
    )
    
    # Merge SDF baseline komponenter
    sdf_cols = [
        'REId',
        'Opåverkbara kostnader',
        'Kostnader för flexibilitetstjänster',
        'Avbrottsersättning 12-24 timmar',
        'Avdrag av kapitalkostnader pga anläggningar med statligt stöd'
    ]
    
    # Validera att kolumner finns i SDF
    available_cols = ['REId']
    col_mapping = {
        'Opåverkbara kostnader': 'Opaverkbara_Kostnader',
        'Kostnader för flexibilitetstjänster': 'Flexibilitetstjanster',
        'Avbrottsersättning 12-24 timmar': 'Avbrottsersattning_12_24h',
        'Avdrag av kapitalkostnader pga anläggningar med statligt stöd': 'Avdrag_Statligt_Stod'
    }
    
    for col in sdf_cols[1:]:  # Skip REId
        if col in sdf_baseline.columns:
            available_cols.append(col)
    
    sdf_subset = sdf_baseline[available_cols].copy()
    
    # Rename kolumner
    rename_dict = {k: v for k, v in col_mapping.items() if k in sdf_subset.columns}
    sdf_subset = sdf_subset.rename(columns=rename_dict)
    
    # Merge med main dataframe
    df = df.merge(sdf_subset, on='REId', how='left')
    
    # Fyll NaN med 0 för komponenter som saknas
    for col in col_mapping.values():
        if col in df.columns:
            df[col] = df[col].fillna(0)
        else:
            df[col] = 0
    
    # Beräkna total intäktsram
    df['Intaktsram_Total'] = (
        df['Kapitalkostnad_Total']
        + df['Paverkbara_Periodsumma']
        + df['Opaverkbara_Kostnader']
        + df['Flexibilitetstjanster']
        + df['Avbrottsersattning_12_24h']
        - df['Avdrag_Statligt_Stod']
    )
    
    return df


def extract_user_intaktsram(
    intaktsram_df: pd.DataFrame,
    user_reid: str
) -> pd.Series:
    """
    Extraherar intäktsram för ett specifikt företag.
    
    Args:
        intaktsram_df: DataFrame med alla företags intäktsramar
        user_reid: REId för användarens företag
        
    Returns:
        Series med alla komponenter för detta företag
        
    Raises:
        ValueError: Om REId inte finns i data
    """
    result = intaktsram_df[intaktsram_df['REId'] == user_reid]
    
    if result.empty:
        raise ValueError(f"REId '{user_reid}' finns inte i intäktsram-data")
    
    return result.iloc[0]


def create_intaktsram_breakdown(
    user_intaktsram: pd.Series
) -> pd.DataFrame:
    """
    Skapar breakdown-tabell för visualisering.
    
    Args:
        user_intaktsram: Series med alla komponenter
        
    Returns:
        DataFrame med kolumner: Komponent, Värde (tkr)
    """
    breakdown = [
        ('Kapitalkostnad', user_intaktsram['Kapitalkostnad_Total']),
        ('  - varav Avskrivningar', user_intaktsram['Avskrivningar']),
        ('  - varav Avkastning', user_intaktsram['Avkastning']),
        ('Påverkbara kostnader', user_intaktsram['Paverkbara_Periodsumma']),
        ('Opåverkbara kostnader', user_intaktsram['Opaverkbara_Kostnader']),
        ('Flexibilitetstjänster', user_intaktsram['Flexibilitetstjanster']),
        ('Avbrottsersättning 12-24h', user_intaktsram['Avbrottsersattning_12_24h']),
        ('Avdrag statligt stöd', -user_intaktsram['Avdrag_Statligt_Stod']),
        ('', ''),  # Blank rad
        ('TOTAL INTÄKTSRAM', user_intaktsram['Intaktsram_Total'])
    ]
    
    df = pd.DataFrame(breakdown, columns=['Komponent', 'Värde (tkr)'])
    
    return df
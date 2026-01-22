"""
calculations/kent_calculations.py

KENT-beräkningar för kapitalkostnader (Steg 5-8).

UPDATED: Normvalue adjustments now applied AFTER step 5, only to ordinarie
capital base (nuav_ord_{time} columns), not to tail. This matches the
regulatory intent where parameter scaling (1.1-1.2) affects ordinary assets.
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple

# Halvårsmappning till år
YEAR_TO_TIMECODES = {
    2024: [229, 230],  # H1 + H2
    2025: [231, 232],
    2026: [233, 234],
    2027: [235, 236],
}


def run_kent_calculations_batch(
    capbase_data: pd.DataFrame,
    wacc: float = 0.0453,
    normvalue_adjustments: Optional[Dict[int, float]] = None,
    lifetime_adjustments: Optional[Dict[int, Dict[str, int]]] = None
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Kör KENT steg 5-8 för alla företag.
    
    Args:
        capbase_data: DataFrame med alla komponenter (capbase_a format)
        wacc: WACC att använda
        normvalue_adjustments: {cat_encode: multiplier} - applied to ordinarie only
        lifetime_adjustments: {cat_encode: {'ekdep': X, 'maxdep': Y}}
        
    Returns:
        Tuple av:
        - df_detailed: Detaljerad data per komponent
        - df_network: Aggregerad data per nätverk med per-år kolumner
    """
    df = capbase_data.copy()
    
    # Applicera livslängdsjusteringar FÖRE steg 5 (påverkar ord/tail klassificering)
    if lifetime_adjustments:
        for cat_encode, adjustments in lifetime_adjustments.items():
            mask = df['cat_encode'] == cat_encode
            if 'ekdep' in adjustments:
                df.loc[mask, 'ekdep'] = adjustments['ekdep']
            if 'maxdep' in adjustments:
                df.loc[mask, 'maxdep'] = adjustments['maxdep']
        print(f"  Applied lifetime adjustments for {len(lifetime_adjustments)} categories")
    
    # Steg 5: Beräkna ålder och NUAV (skapar base_ord/base_tail, nuav_ord/nuav_tail)
    df = calculate_ages_and_nuav_batch(df)
    
    # Applicera normvärdejusteringar EFTER steg 5, endast på ordinarie
    if normvalue_adjustments:
        df = _apply_normvalue_to_ordinarie(df, normvalue_adjustments)
        print(f"  Applied normvalue adjustments to ordinarie for {len(normvalue_adjustments)} categories")
    
    # Steg 6: Beräkna avskrivningar
    df = calculate_depreciation_batch(df)
    
    # Steg 7: Beräkna avkastning
    df = calculate_returns_batch(df, wacc=wacc)
    
    # Steg 8: Aggregera till nätverksnivå
    df_network = aggregate_to_network_level(df)
    
    # Beräkna per-år kolumner (Avkastning_2024, etc.)
    df_network = calculate_capex_outputs(df_network)
    
    return df, df_network


def _apply_normvalue_to_ordinarie(
    df: pd.DataFrame,
    normvalue_adjustments: Dict[int, float]
) -> pd.DataFrame:
    """
    Apply normvalue adjustments to ordinarie capital base only.
    
    Applied AFTER step 5 has created nuav_ord_{time} columns.
    Does NOT affect nuav_tail_{time} columns.
    
    Args:
        df: DataFrame with nuav_ord_{time} columns from step 5
        normvalue_adjustments: {cat_encode: multiplier}
        
    Returns:
        DataFrame with adjusted nuav_ord_{time} values
    """
    for cat_encode, multiplier in normvalue_adjustments.items():
        mask = df['cat_encode'] == cat_encode
        
        # Apply to all nuav_ord_{time} columns (229-236)
        for time in range(229, 237):
            col = f'nuav_ord_{time}'
            if col in df.columns:
                df.loc[mask, col] = df.loc[mask, col] * multiplier
    
    return df


def calculate_ages_and_nuav_batch(df: pd.DataFrame) -> pd.DataFrame:
    """
    Steg 5: Beräkna ålder och NUAV för alla komponenter och tidsperioder.
    
    Klassificerar komponenter som ordinarie eller tail baserat på ålder vs ekdep/maxdep.
    Skapar nuav_ord_{time} och nuav_tail_{time} kolumner.
    """
    new_cols = {}
    
    for time in range(229, 237):
        # Age on components
        new_cols[f'age_component_{time}'] = time - df['time_from']
        new_cols[f'age_component_{time}_invest'] = np.where(
            df['capbase_existing'] == 0, 
            time - df['time_invest'], 
            np.nan
        )
        
        # Initial capital base ordinary
        base_ord = np.zeros(len(df), dtype='int64')
        mask = (
            (new_cols[f'age_component_{time}'] <= df['ekdep']) & 
            (new_cols[f'age_component_{time}'] > 0) & 
            (df['capbase_existing'] == 1)
        )
        base_ord[mask] = 1
        
        # Investments and retirements ordinary
        mask = (
            (new_cols[f'age_component_{time}'] <= df['ekdep']) & 
            (new_cols[f'age_component_{time}_invest'] > 0) & 
            (df['capbase_existing'] == 0)
        )
        base_ord[mask] = 1
        
        mask = (
            (new_cols[f'age_component_{time}'] > df['ekdep']) & 
            (df['capbase_existing'] == 0)
        )
        base_ord[mask] = 0
        
        new_cols[f'base_ord_{time}'] = base_ord
        
        # Calculate nuav_ord
        nuav_ord = np.zeros(len(df), dtype='float64')
        mask = base_ord == 1
        nuav_ord[mask] = (df['nuav_2022'] * base_ord)[mask]
        new_cols[f'nuav_ord_{time}'] = nuav_ord
        
        # Initial capital base tail
        base_tail = np.zeros(len(df), dtype='int64')
        mask = (
            (new_cols[f'age_component_{time}'] <= df['maxdep']) & 
            (new_cols[f'age_component_{time}'] > df['ekdep']) & 
            (df['capbase_existing'] == 1)
        )
        base_tail[mask] = 1
        
        # Investments and retirements tail
        mask = (
            (new_cols[f'age_component_{time}'] <= df['maxdep']) & 
            (new_cols[f'age_component_{time}'] > df['ekdep']) & 
            (df['time_invest'] < time) & 
            (~df['invest'].isna())
        )
        base_tail[mask] = 1
        
        new_cols[f'base_tail_{time}'] = base_tail
        new_cols[f'nuav_tail_{time}'] = df['nuav_2022'] * base_tail
    
    df = pd.concat([df, pd.DataFrame(new_cols, index=df.index)], axis=1)
    
    return df


def calculate_depreciation_batch(df: pd.DataFrame) -> pd.DataFrame:
    """
    Steg 6: Beräkna avskrivningar för alla komponenter och tidsperioder.
    """
    new_cols = {}
    
    for t in range(229, 237):
        nuav_col = f'nuav_ord_{t}'
        if nuav_col not in df.columns:
            continue
        
        # Ordinary depreciation
        comp_dep = df[nuav_col] / df['ekdep']
        new_cols[f'comp_dep_{t}'] = comp_dep
        
        # Tail depreciation
        age_comp = f'age_component_{t}'
        age_component_numeric = pd.to_numeric(df[age_comp], errors='coerce')
        
        adjustment = np.where(
            (age_component_numeric % 2 == 1), 
            np.where(age_component_numeric > 0, 1, -1), 
            0
        )
        age_reg_values = age_component_numeric + adjustment
        age_reg_values = pd.to_numeric(age_reg_values, errors='coerce')
        new_cols[f'age_reg_{t}'] = age_reg_values
        
        tail_col = f'nuav_tail_{t}'
        if tail_col in df.columns:
            nuav_tail_numeric = pd.to_numeric(df[tail_col], errors='coerce')
            denominator = age_reg_values.to_numpy().astype(float)
            numerator = nuav_tail_numeric.to_numpy().astype(float)
            comp_dep_tail = np.divide(
                numerator, 
                denominator, 
                out=np.zeros_like(denominator, dtype=float), 
                where=(denominator != 0)
            )
            new_cols[f'comp_dep_tail_{t}'] = comp_dep_tail
    
    if new_cols:
        df = pd.concat([df, pd.DataFrame(new_cols, index=df.index)], axis=1)
    
    return df


def calculate_returns_batch(df: pd.DataFrame, wacc: float = 0.0453) -> pd.DataFrame:
    """
    Steg 7: Beräkna avkastning för alla komponenter och tidsperioder.
    """
    df['ekdep2'] = df['ekdep'] / 2
    df['maxdep2'] = df['maxdep'] / 2
    
    new_cols = {}
    
    for time in range(229, 237):
        age_col = f'age_component_{time}'
        if age_col not in df.columns:
            continue
        
        age_return_values = pd.to_numeric(df[age_col], errors='coerce').copy()
        
        mask_odd = (age_return_values % 2 == 1)
        adjustment = np.where(age_return_values > 0, 1, -1)
        age_return_values = np.where(mask_odd, age_return_values + adjustment, age_return_values)
        age_return_values = age_return_values / 2
        age_return_values = age_return_values - 1
        
        new_cols[f'age_return_{time}'] = age_return_values
        
        # Ordinary returns
        nuav_ord_col = f'nuav_ord_{time}'
        if nuav_ord_col in df.columns:
            capbase_left_ord = ((df['ekdep2'] - age_return_values) / df['ekdep2']) * df[nuav_ord_col]
            capbase_left_ord = np.where(age_return_values < 0, 0, capbase_left_ord)
            new_cols[f'capbase_left_ord_{time}'] = capbase_left_ord
            
            return_ord = wacc * capbase_left_ord / 2
            new_cols[f'return_ord_{time}'] = return_ord
        
        # Tail returns
        nuav_tail_col = f'nuav_tail_{time}'
        if nuav_tail_col in df.columns:
            denominator = age_return_values + 1
            capbase_left_tail = np.divide(
                df[nuav_tail_col].to_numpy().astype(float),
                denominator,
                out=np.zeros(len(df), dtype=float),
                where=(denominator != 0)
            )
            new_cols[f'capbase_left_tail_{time}'] = capbase_left_tail
            
            return_tail = wacc * capbase_left_tail / 2
            new_cols[f'return_tail_{time}'] = return_tail
    
    if new_cols:
        df = pd.concat([df, pd.DataFrame(new_cols, index=df.index)], axis=1)
    
    return df


def aggregate_to_network_level(df: pd.DataFrame) -> pd.DataFrame:
    """
    Steg 8: Aggregerar kapitalkostnader till id_network nivå (företagsnivå).
    
    Summerar dep_ord, dep_tail, return_ord, return_tail per id_network för varje tidsperiod.
    Lägger också till REId för direct joining.
    """
    aggregation_dict = {}
    
    for t in range(229, 237):
        dep_ord_col = f'comp_dep_{t}'
        dep_tail_col = f'comp_dep_tail_{t}'
        ret_ord_col = f'return_ord_{t}'
        ret_tail_col = f'return_tail_{t}'
        
        if dep_ord_col in df.columns:
            aggregation_dict[dep_ord_col] = 'sum'
        if dep_tail_col in df.columns:
            aggregation_dict[dep_tail_col] = 'sum'
        if ret_ord_col in df.columns:
            aggregation_dict[ret_ord_col] = 'sum'
        if ret_tail_col in df.columns:
            aggregation_dict[ret_tail_col] = 'sum'
    
    df_agg = df.groupby('id_network').agg(aggregation_dict).reset_index()
    
    # Lägg till REId
    df_agg['REId'] = 'REL' + df_agg['id_network'].astype(str).str.zfill(5)
    
    # Konvertera till tkr
    for col in df_agg.columns:
        if col not in ['id_network', 'REId']:
            df_agg[col] = df_agg[col] / 1000
    
    # Byt namn på kolumner
    rename_dict = {}
    for t in range(229, 237):
        if f'comp_dep_{t}' in df_agg.columns:
            rename_dict[f'comp_dep_{t}'] = f'dep_ord_{t}'
        if f'comp_dep_tail_{t}' in df_agg.columns:
            rename_dict[f'comp_dep_tail_{t}'] = f'dep_tail_{t}'
    
    df_agg = df_agg.rename(columns=rename_dict)
    
    # Beräkna total kapitalkostnad per halvår
    for t in range(229, 237):
        dep_ord = f'dep_ord_{t}'
        dep_tail = f'dep_tail_{t}'
        ret_ord = f'return_ord_{t}'
        ret_tail = f'return_tail_{t}'
        
        for col in [dep_ord, dep_tail, ret_ord, ret_tail]:
            if col not in df_agg.columns:
                df_agg[col] = 0.0
        
        df_agg[f'capcost_{t}'] = (
            df_agg[dep_ord] + 
            df_agg[dep_tail] + 
            df_agg[ret_ord] + 
            df_agg[ret_tail]
        )
    
    return df_agg


def calculate_capex_outputs(df_network: pd.DataFrame) -> pd.DataFrame:
    """
    Beräknar kapitalkostnads-outputs med KORREKT halvårsmappning.
    
    Tidskoder är HALVÅR: 229=2024H1, 230=2024H2, 231=2025H1, etc.
    
    Genererar:
    - Kapitalkostnad_2024-2027 och Kapitalkostnad_Period
    - Avkastning_2024-2027 och Avkastning_Period
    - Avskrivning_2024-2027 och Avskrivning_Period
    """
    df = df_network.copy()
    
    # Beräkna per-år värden genom att summera halvåren
    for year, timecodes in YEAR_TO_TIMECODES.items():
        t1, t2 = timecodes
        
        # Kapitalkostnad per år
        capcost_cols = [f'capcost_{t}' for t in [t1, t2] if f'capcost_{t}' in df.columns]
        if capcost_cols:
            df[f'Kapitalkostnad_{year}'] = df[capcost_cols].sum(axis=1)
        else:
            df[f'Kapitalkostnad_{year}'] = 0.0
        
        # Avkastning per år (return_ord + return_tail för båda halvåren)
        return_cols = []
        for t in [t1, t2]:
            if f'return_ord_{t}' in df.columns:
                return_cols.append(f'return_ord_{t}')
            if f'return_tail_{t}' in df.columns:
                return_cols.append(f'return_tail_{t}')
        
        if return_cols:
            df[f'Avkastning_{year}'] = df[return_cols].sum(axis=1)
        else:
            df[f'Avkastning_{year}'] = 0.0
        
        # Avskrivning per år (dep_ord + dep_tail för båda halvåren)
        dep_cols = []
        for t in [t1, t2]:
            if f'dep_ord_{t}' in df.columns:
                dep_cols.append(f'dep_ord_{t}')
            if f'dep_tail_{t}' in df.columns:
                dep_cols.append(f'dep_tail_{t}')
        
        if dep_cols:
            df[f'Avskrivning_{year}'] = df[dep_cols].sum(axis=1)
        else:
            df[f'Avskrivning_{year}'] = 0.0
    
    # Beräkna periodsummor
    yearly_capcost = [f'Kapitalkostnad_{year}' for year in [2024, 2025, 2026, 2027]]
    df['Kapitalkostnad_Period'] = df[yearly_capcost].sum(axis=1)
    
    yearly_return = [f'Avkastning_{year}' for year in [2024, 2025, 2026, 2027]]
    df['Avkastning_Period'] = df[yearly_return].sum(axis=1)
    
    yearly_dep = [f'Avskrivning_{year}' for year in [2024, 2025, 2026, 2027]]
    df['Avskrivning_Period'] = df[yearly_dep].sum(axis=1)
    
    # Sätt standardkolumner för kompatibilitet med baseline
    if 'Kapitalkostnad_2024' in df.columns:
        df['CAPEX'] = df['Kapitalkostnad_2024']
    
    if 'Avkastning_2024' in df.columns:
        df['Avkastning'] = df['Avkastning_2024']
    
    if 'Avskrivning_2024' in df.columns:
        df['Avskrivning'] = df['Avskrivning_2024']
    
    return df


def get_capex_summary(df_network: pd.DataFrame) -> Dict:
    """
    Skapar sammanfattning av kapitalkostnader.
    """
    summary = {
        'total_companies': len(df_network),
        'total_capex_2024': df_network['Kapitalkostnad_2024'].sum() if 'Kapitalkostnad_2024' in df_network.columns else 0,
        'total_capex_period': df_network['Kapitalkostnad_Period'].sum() if 'Kapitalkostnad_Period' in df_network.columns else 0,
    }
    return summary
"""
kent_pipeline.py - KENT-beräkningspipeline (steg 5-9)
======================================================

Återanvänd från beräkningskedja.py.
Beräknar åldrar, NUAV, avskrivningar och avkastning.
"""

import pandas as pd
import numpy as np
from typing import Dict


def calculate_ages_and_nuav(df: pd.DataFrame) -> pd.DataFrame:
    """Beräknar åldrar och NUAV för alla tidsperioder (229-236)."""
    result_df = df.copy()
    for time in range(229, 237):
        result_df = _process_time_period(result_df, time)
    return result_df.copy()


def _process_time_period(df: pd.DataFrame, time: int) -> pd.DataFrame:
    """Bearbetar en tidsperiod."""
    new_cols = {}
    
    new_cols[f'age_component_{time}'] = time - df['time_from']
    new_cols[f'age_component_{time}_invest'] = np.where(
        df['capbase_existing'] == 0, 
        time - df['time_invest'], 
        np.nan
    )
    
    base_ord = np.zeros(len(df), dtype='int64')
    mask = (new_cols[f'age_component_{time}'] <= df['ekdep']) & \
           (new_cols[f'age_component_{time}'] > 0) & \
           (df['capbase_existing'] == 1)
    base_ord[mask] = 1
    
    mask = (new_cols[f'age_component_{time}'] <= df['ekdep']) & \
           (new_cols[f'age_component_{time}_invest'] > 0) & \
           (df['capbase_existing'] == 0)
    base_ord[mask] = 1
    
    mask = (new_cols[f'age_component_{time}'] > df['ekdep']) & \
           (df['capbase_existing'] == 0)
    base_ord[mask] = 0
    
    new_cols[f'base_ord_{time}'] = base_ord
    
    nuav_ord = np.zeros(len(df), dtype='float64')
    mask = base_ord == 1
    nuav_ord[mask] = (df['nuav_2022'] * base_ord)[mask]
    new_cols[f'nuav_ord_{time}'] = nuav_ord

    base_tail = np.zeros(len(df), dtype='int64')
    mask = (new_cols[f'age_component_{time}'] <= df['maxdep']) & \
           (new_cols[f'age_component_{time}'] > df['ekdep']) & \
           (df['capbase_existing'] == 1)
    base_tail[mask] = 1
    
    mask = (new_cols[f'age_component_{time}'] <= df['maxdep']) & \
           (new_cols[f'age_component_{time}'] > df['ekdep']) & \
           (df['time_invest'] < time) & (~df['invest'].isna())
    base_tail[mask] = 1
    
    new_cols[f'base_tail_{time}'] = base_tail
    new_cols[f'nuav_tail_{time}'] = df['nuav_2022'] * base_tail
    
    df = pd.concat([df, pd.DataFrame(new_cols, index=df.index)], axis=1)
    
    sum_nuav_ord = df.groupby(['cat_encode', 'id_network'])[f'nuav_ord_{time}'].sum().reset_index(name=f'sum_nuav_ord_{time}')
    df = df.merge(sum_nuav_ord, on=['cat_encode', 'id_network'], how='left')
    df[f'sum_nuav_ord_{time}'] = df[f'sum_nuav_ord_{time}'] / 1000
    
    sum_nuav_tail = df.groupby(['cat_encode', 'id_network'])[f'nuav_tail_{time}'].sum().reset_index(name=f'sum_nuav_tail_{time}')
    df = df.merge(sum_nuav_tail, on=['cat_encode', 'id_network'], how='left')
    df[f'sum_nuav_tail_{time}'] = df[f'sum_nuav_tail_{time}'] / 1000
    
    return df.copy()


def calculate_depreciation(df: pd.DataFrame) -> Dict[str, float]:
    """Beräknar avskrivningar."""
    results = {}
    new_cols = {}
    
    for t in range(229, 237):
        nuav_col = f'nuav_ord_{t}'
        if nuav_col not in df.columns:
            continue
            
        comp_dep = df[nuav_col] / df['ekdep']
        new_cols[f'comp_dep_{t}'] = comp_dep
        
        age_comp = f'age_component_{t}'
        age_reg = f'age_reg_{t}'
        
        age_component_numeric = pd.to_numeric(df[age_comp], errors='coerce')
        
        adjustment = np.where((age_component_numeric % 2 == 1), 
                            np.where(age_component_numeric > 0, 1, -1), 
                            0)
        age_reg_values = age_component_numeric + adjustment
        age_reg_values = pd.to_numeric(age_reg_values, errors='coerce')
        new_cols[age_reg] = age_reg_values
        
        tail_col = f'nuav_tail_{t}'
        if tail_col in df.columns:
            nuav_tail_numeric = pd.to_numeric(df[tail_col], errors='coerce')
            denominator = age_reg_values.to_numpy().astype(float)
            numerator = nuav_tail_numeric.to_numpy().astype(float)
            comp_dep_tail = np.divide(numerator, denominator, 
                                    out=np.zeros_like(denominator, dtype=float), 
                                    where=(denominator != 0))
            new_cols[f'comp_dep_tail_{t}'] = comp_dep_tail
    
    if new_cols:
        df = pd.concat([df, pd.DataFrame(new_cols, index=df.index)], axis=1)
    
    for t in range(229, 237):
        if f'comp_dep_{t}' in df.columns:
            aggr_ord = df.groupby(['cat_encode', 'id_network'])[f'comp_dep_{t}'].sum().reset_index()
            dep_ord_total = aggr_ord[f'comp_dep_{t}'].sum() / 1000
            results[f'dep_ord_{t}'] = dep_ord_total
        
        if f'comp_dep_tail_{t}' in df.columns:
            aggr_tail = df.groupby(['cat_encode', 'id_network'])[f'comp_dep_tail_{t}'].sum().reset_index()
            dep_tail_total = aggr_tail[f'comp_dep_tail_{t}'].sum() / 1000
            results[f'dep_tail_{t}'] = dep_tail_total
        else:
            results[f'dep_tail_{t}'] = 0
    
    return results


def calculate_returns(df: pd.DataFrame, interest_rate: float = 0.0453) -> Dict[str, float]:
    """Beräknar avkastning."""
    results = {}
    df['ekdep2'] = df['ekdep'] / 2
    df['maxdep2'] = df['maxdep'] / 2
    
    new_cols = {}
    
    for time in range(229, 237):
        age_col = f'age_component_{time}'
        if age_col not in df.columns:
            continue
            
        ret_col = f'age_return_{time}'
        age_return_values = df[age_col].copy()
        
        mask = (age_return_values % 2 == 1)
        age_return_values[mask] += age_return_values[mask].apply(lambda x: 1 if x > 0 else -1)
        age_return_values = age_return_values / 2
        age_return_values = age_return_values - 1
        new_cols[ret_col] = age_return_values

        nuav_ord_col = f'nuav_ord_{time}'
        if nuav_ord_col in df.columns:
            cap_ord = f'capbase_left_ord_{time}'
            capbase_left_ord_values = ((df['ekdep2'] - age_return_values) / df['ekdep2']) * df[nuav_ord_col]
            capbase_left_ord_values[age_return_values < 0] = 0
            new_cols[cap_ord] = capbase_left_ord_values
            
            ret_ord = f'return_ord_{time}'
            new_cols[ret_ord] = interest_rate * capbase_left_ord_values / 2

        nuav_tail_col = f'nuav_tail_{time}'
        if nuav_tail_col in df.columns:
            cap_tail = f'capbase_left_tail_{time}'
            new_cols[cap_tail] = (1 / (age_return_values + 1)) * df[nuav_tail_col]
            
            ret_tail = f'return_tail_{time}'
            new_cols[ret_tail] = interest_rate * new_cols[cap_tail] / 2
    
    if new_cols:
        df = pd.concat([df, pd.DataFrame(new_cols, index=df.index)], axis=1)
    
    for time in range(229, 237):
        ret_ord = f'return_ord_{time}'
        if ret_ord in df.columns:
            ret_ord_total = df.groupby(['cat_encode', 'id_network'])[ret_ord].sum().sum() / 1000
            results[ret_ord] = ret_ord_total
        
        ret_tail = f'return_tail_{time}'
        if ret_tail in df.columns:
            ret_tail_total = df.groupby(['cat_encode', 'id_network'])[ret_tail].sum().sum() / 1000
            results[ret_tail] = ret_tail_total
    
    return results


def compile_capcost(dep_data: Dict[str, float], ret_data: Dict[str, float]) -> pd.DataFrame:
    """Sammanställer kapitalkostnad."""
    rows = []
    for time in range(229, 237):
        dep_ord = dep_data.get(f'dep_ord_{time}', 0)
        dep_tail = dep_data.get(f'dep_tail_{time}', 0)
        ret_ord = ret_data.get(f'return_ord_{time}', 0)
        ret_tail = ret_data.get(f'return_tail_{time}', 0)
        
        rows.append({
            'time': time,
            'dep_ord': dep_ord,
            'dep_tail': dep_tail,
            'return_ord': ret_ord,
            'return_tail': ret_tail,
            'capcost_sum': dep_ord + dep_tail + ret_ord + ret_tail
        })
    
    return pd.DataFrame(rows)
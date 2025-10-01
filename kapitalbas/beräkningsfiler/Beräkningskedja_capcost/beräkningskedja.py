"""
beräkningskedja.py - Refaktoriserade beräkningsfunktioner för enskilda DMU

Extraherar beräkningslogiken från scripts 5-9 och gör dem återanvändbara
för interaktiv användning per DMU.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional, Dict, Any
from pandas.api.types import is_categorical_dtype
import psutil
import os


def get_memory_usage():
    """Returnerar minnesanvändning i MB"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024


def load_dmu_capbase_a(dmu_id: int) -> pd.DataFrame:
    """
    Laddar capbase_a data för en specifik DMU.
    Filtrerar på id_network som mappas till den DMU:n.
    """
    try:
        # Först behöver vi hitta vilka id_network som hör till denna DMU
        recon_path = "effektiviseringskrav/data/reconciliation_id_network_firm_dmu.csv"
        if not Path(recon_path).exists():
            raise FileNotFoundError(f"Reconciliation-fil saknas: {recon_path}")
        
        recon_df = pd.read_csv(recon_path)
        
        # Hitta id_network för denna DMU
        dmu_networks = recon_df[recon_df['DMU'] == dmu_id]['id_network'].tolist()
        
        if not dmu_networks:
            return pd.DataFrame()  # Tom dataframe om DMU inte hittas
        
        # Ladda capbase_a och filtrera
        capbase_path = "kapitalbas/datafiler/rådata/capbase_a.parquet"
        if not Path(capbase_path).exists():
            raise FileNotFoundError(f"Capbase_a saknas: {capbase_path}")
        
        df_full = pd.read_parquet(capbase_path)
        
        # Filtrera för denna DMU:s nätverk
        df_dmu = df_full[df_full['id_network'].isin(dmu_networks)].copy()
        
        return df_dmu
        
    except Exception as e:
        print(f"Fel vid laddning av DMU {dmu_id}: {e}")
        return pd.DataFrame()


def calculate_ages_and_nuav(df: pd.DataFrame) -> pd.DataFrame:
    """
    Beräknar åldrar och NUAV för alla tidsperioder (229-236).
    Refaktoriserad version av 5_ages_and_nuav.py
    """
    mem_start = get_memory_usage()
    print(f"[MINNE] Före ages_and_nuav: {mem_start:.1f} MB")
    
    result_df = df.copy()
    
    # Bearbeta varje tidsperiod
    for time in range(229, 237):
        result_df = process_time_period(result_df, time)
    
    result_df = result_df.copy()
    
    mem_end = get_memory_usage()
    print(f"[MINNE] Efter ages_and_nuav: {mem_end:.1f} MB (Δ: {mem_end-mem_start:+.1f} MB)")
    
    return result_df


def process_time_period(df: pd.DataFrame, time: int) -> pd.DataFrame:
    """
    Bearbetar en tidsperiod - extraherat från 5_ages_and_nuav.py
    FIXAD: Använder batch-tillägg för kolumner och explicit float64-konvertering
    """
    
    # Samla alla nya kolumner i dictionary för effektiv tillägg
    new_cols = {}
    
    # Age on components
    new_cols[f'age_component_{time}'] = time - df['time_from']
    new_cols[f'age_component_{time}_invest'] = np.where(df['capbase_existing'] == 0, 
                                                 time - df['time_invest'], 
                                                 np.nan)
    
    # Initial capital base ordinary - FIX: Create as array not scalar
    base_ord = np.zeros(len(df), dtype='int64')
    mask = (new_cols[f'age_component_{time}'] <= df['ekdep']) & (new_cols[f'age_component_{time}'] > 0) & (df['capbase_existing'] == 1)
    base_ord[mask] = 1
    
    # Investments and retirements ordinary
    mask = (new_cols[f'age_component_{time}'] <= df['ekdep']) & (new_cols[f'age_component_{time}_invest'] > 0) & (df['capbase_existing'] == 0)
    base_ord[mask] = 1
    
    mask = (new_cols[f'age_component_{time}'] > df['ekdep']) & (df['capbase_existing'] == 0)
    base_ord[mask] = 0
    
    new_cols[f'base_ord_{time}'] = base_ord
    
    # Calculate nuav_ord - FIX: Explicit float64 conversion
    nuav_ord = np.zeros(len(df), dtype='float64')
    mask = base_ord == 1
    nuav_ord[mask] = (df['nuav_2022'] * base_ord)[mask]
    new_cols[f'nuav_ord_{time}'] = nuav_ord

    # Initial capital base tail - FIX: Create as array not scalar
    base_tail = np.zeros(len(df), dtype='int64')
    mask = (new_cols[f'age_component_{time}'] <= df['maxdep']) & (new_cols[f'age_component_{time}'] > df['ekdep']) & (df['capbase_existing'] == 1)
    base_tail[mask] = 1
    
    # Investments and retirements tail
    mask = (new_cols[f'age_component_{time}'] <= df['maxdep']) & (new_cols[f'age_component_{time}'] > df['ekdep']) & (df['time_invest'] < time) & (~df['invest'].isna())
    base_tail[mask] = 1
    
    new_cols[f'base_tail_{time}'] = base_tail
    
    # Calculate nuav_tail
    new_cols[f'nuav_tail_{time}'] = df['nuav_2022'] * base_tail
    
    # FIX: Lägg till alla nya kolumner på en gång för bättre prestanda
    df = pd.concat([df, pd.DataFrame(new_cols, index=df.index)], axis=1)
    
    # Summarize - ordinary capital base
    sum_nuav_ord = df.groupby(['cat_encode', 'id_network'])[f'nuav_ord_{time}'].sum().reset_index(name=f'sum_nuav_ord_{time}')
    df = df.merge(sum_nuav_ord, on=['cat_encode', 'id_network'], how='left')
    df[f'sum_nuav_ord_{time}'] = df[f'sum_nuav_ord_{time}'] / 1000  # Convert to thousands
    
    # Summarize - tail
    sum_nuav_tail = df.groupby(['cat_encode', 'id_network'])[f'nuav_tail_{time}'].sum().reset_index(name=f'sum_nuav_tail_{time}')
    df = df.merge(sum_nuav_tail, on=['cat_encode', 'id_network'], how='left')
    df[f'sum_nuav_tail_{time}'] = df[f'sum_nuav_tail_{time}'] / 1000  # Convert to thousands
    
    df = df.copy() 
    return df


def calculate_depreciation_single_dmu(df: pd.DataFrame) -> Dict[str, float]:
    """
    Beräknar avskrivningar för en DMU.
    Refaktoriserad version av 6_deprecation.py
    OPTIMERAD: Batch-tillägg av kolumner för bättre prestanda
    """
    mem_start = get_memory_usage()
    print(f"[MINNE] Före depreciation: {mem_start:.1f} MB")
    
    results = {}
    new_cols = {}  # Samla alla nya kolumner här
    
    # Bearbeta alla tidsperioder
    for t in range(229, 237):
        # 1. Compute dep_ord
        nuav_col = f'nuav_ord_{t}'
        if nuav_col not in df.columns:
            continue
            
        comp_dep = df[nuav_col] / df['ekdep']
        new_cols[f'comp_dep_{t}'] = comp_dep
        
        # 2. Compute dep_tail
        age_comp = f'age_component_{t}'
        age_reg = f'age_reg_{t}'
        
        # Convert age_component to numeric (already exists in df)
        age_component_numeric = pd.to_numeric(df[age_comp], errors='coerce')
        
        # Compute age_reg
        adjustment = np.where((age_component_numeric % 2 == 1), 
                            np.where(age_component_numeric > 0, 1, -1), 
                            0)
        age_reg_values = age_component_numeric + adjustment
        age_reg_values = pd.to_numeric(age_reg_values, errors='coerce')
        new_cols[age_reg] = age_reg_values
        
        # Compute comp_dep_tail using safe division
        tail_col = f'nuav_tail_{t}'
        if tail_col in df.columns:
            nuav_tail_numeric = pd.to_numeric(df[tail_col], errors='coerce')
            denominator = age_reg_values.to_numpy().astype(float)
            numerator = nuav_tail_numeric.to_numpy().astype(float)
            comp_dep_tail = np.divide(numerator, denominator, 
                                    out=np.zeros_like(denominator, dtype=float), 
                                    where=(denominator != 0))
            new_cols[f'comp_dep_tail_{t}'] = comp_dep_tail
    
    # Lägg till alla nya kolumner på en gång - OPTIMERING
    if new_cols:
        df = pd.concat([df, pd.DataFrame(new_cols, index=df.index)], axis=1)
    
    # Nu aggregera med alla kolumner på plats
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
    
    mem_end = get_memory_usage()
    print(f"[MINNE] Efter depreciation: {mem_end:.1f} MB (Δ: {mem_end-mem_start:+.1f} MB)")
    
    return results


def calculate_returns_single_dmu(df: pd.DataFrame, interest_rate: float = 0.0453) -> Dict[str, float]:
    """
    Beräknar avkastning för en DMU.
    Refaktoriserad version av 7_returns.py
    OPTIMERAD: Batch-tillägg av kolumner för bättre prestanda
    """
    mem_start = get_memory_usage()
    print(f"[MINNE] Före returns: {mem_start:.1f} MB")
    
    results = {}
    
    # Calculate ekdep2 and maxdep2 - dessa behövs före loop
    df['ekdep2'] = df['ekdep'] / 2
    df['maxdep2'] = df['maxdep'] / 2
    
    new_cols = {}  # Samla alla nya kolumner här
    
    # Bearbeta för varje tidsperiod (229 to 236 inclusive)
    for time in range(229, 237):
        # Calculate age_return
        age_col = f'age_component_{time}'
        if age_col not in df.columns:
            continue
            
        ret_col = f'age_return_{time}'
        age_return_values = df[age_col].copy()
        
        # For rows where the value is odd, adjust by 1 in the proper direction
        mask = (age_return_values % 2 == 1)
        age_return_values[mask] += age_return_values[mask].apply(lambda x: 1 if x > 0 else -1)
        age_return_values = age_return_values / 2
        age_return_values = age_return_values - 1
        new_cols[ret_col] = age_return_values

        # Ordinary returns calculations
        nuav_ord_col = f'nuav_ord_{time}'
        if nuav_ord_col in df.columns:
            cap_ord = f'capbase_left_ord_{time}'
            capbase_left_ord_values = ((df['ekdep2'] - age_return_values) / df['ekdep2']) * df[nuav_ord_col]
            capbase_left_ord_values[age_return_values < 0] = 0
            new_cols[cap_ord] = capbase_left_ord_values
            
            ret_ord = f'return_ord_{time}'
            new_cols[ret_ord] = interest_rate * capbase_left_ord_values / 2

        # Tail returns calculations
        nuav_tail_col = f'nuav_tail_{time}'
        if nuav_tail_col in df.columns:
            cap_tail = f'capbase_left_tail_{time}'
            new_cols[cap_tail] = (1 / (age_return_values + 1)) * df[nuav_tail_col]
            
            ret_tail = f'return_tail_{time}'
            new_cols[ret_tail] = interest_rate * new_cols[cap_tail] / 2
    
    # Lägg till alla nya kolumner på en gång - OPTIMERING
    if new_cols:
        df = pd.concat([df, pd.DataFrame(new_cols, index=df.index)], axis=1)
    
    # Nu aggregera med alla kolumner på plats
    for time in range(229, 237):
        ret_ord = f'return_ord_{time}'
        if ret_ord in df.columns:
            ret_ord_total = df.groupby(['cat_encode', 'id_network'])[ret_ord].sum().sum() / 1000
            results[ret_ord] = ret_ord_total
        
        ret_tail = f'return_tail_{time}'
        if ret_tail in df.columns:
            ret_tail_total = df.groupby(['cat_encode', 'id_network'])[ret_tail].sum().sum() / 1000
            results[ret_tail] = ret_tail_total

    mem_end = get_memory_usage()
    print(f"[MINNE] Efter returns: {mem_end:.1f} MB (Δ: {mem_end-mem_start:+.1f} MB)")
    
    return results


def compile_capcost_single_dmu(dep_data: Dict[str, float], ret_data: Dict[str, float], dmu_id: int) -> pd.DataFrame:
    """
    Sammanställer kapitalkostnad från avskrivningar och avkastning.
    Refaktoriserad version av 8_capcost_compile.py
    """
    
    # Skapa dataframe med alla tidsperioder
    periods_data = []
    
    for time in range(229, 237):
        dep_ord = dep_data.get(f'dep_ord_{time}', 0)
        dep_tail = dep_data.get(f'dep_tail_{time}', 0) 
        ret_ord = ret_data.get(f'return_ord_{time}', 0)
        ret_tail = ret_data.get(f'return_tail_{time}', 0)
        
        capcost_sum = dep_ord + dep_tail + ret_ord + ret_tail
        
        periods_data.append({
            'id_network': dmu_id,  # Använd DMU som surrogate för id_network
            'cat_encode': 'aggregated',  # Placeholder
            'time': time,
            'dep_ord': dep_ord,
            'dep_tail': dep_tail,
            'return_ord': ret_ord,
            'return_tail': ret_tail,
            'capcost_sum': capcost_sum
        })
    
    df_result = pd.DataFrame(periods_data)
    return df_result


def load_facit_for_dmu(dmu_id: int) -> pd.DataFrame:
    """
    Laddar facit-data för jämförelse för en specifik DMU.
    """
    try:
        facit_path = "kapitalbas/datafiler/slutdata/capcost_a_3_Sheet1.parquet"
        if not Path(facit_path).exists():
            return pd.DataFrame()
        
        df_facit = pd.read_parquet(facit_path)

        # Hitta id_network för denna DMU från reconciliation_id_network_firm_dmu.csv
        recon_path = "effektiviseringskrav/data/reconciliation_id_network_firm_dmu.csv"
        if Path(recon_path).exists():
            recon_df = pd.read_csv(recon_path)
            dmu_networks = recon_df[recon_df['DMU'] == dmu_id]['id_network'].tolist()
            
            if dmu_networks:
                # Filtrera facit för denna DMU:s nätverk
                available_networks = df_facit['id_network'].unique()
                valid_networks = [net for net in dmu_networks if net in available_networks]
                
                if not valid_networks:
                    return pd.DataFrame()
                    
                df_dmu_facit = df_facit[df_facit['id_network'].isin(valid_networks)]
                
                # Aggregera till DMU-nivå
                aggregated = df_dmu_facit.groupby('time').agg({
                    'capcost_sum': 'sum',
                    'dep_ord': 'sum',
                    'dep_tail': 'sum', 
                    'return_ord': 'sum',
                    'return_tail': 'sum'
                }).reset_index()
                
                return aggregated
        
        return pd.DataFrame()
        
    except Exception as e:
        print(f"Fel vid laddning av facit för DMU {dmu_id}: {e}")
        return pd.DataFrame()


def validate_input_data(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Validerar indata och returnerar valideringsresultat.
    """
    validation = {
        'valid': True,
        'errors': [],
        'warnings': [],
        'stats': {}
    }
    
    # Kolla obligatoriska kolumner
    required_cols = ['id_component', 'cat_encode', 'id_network', 'nuav_2022', 
                     'ekdep', 'maxdep', 'time_from', 'capbase_existing']
    
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        validation['valid'] = False
        validation['errors'].append(f"Saknar obligatoriska kolumner: {missing_cols}")
    
    # Statistik
    validation['stats'] = {
        'total_components': len(df),
        'total_nuav_2022': df['nuav_2022'].sum() if 'nuav_2022' in df.columns else 0,
        'categories': df['cat_encode'].nunique() if 'cat_encode' in df.columns else 0,
        'networks': df['id_network'].nunique() if 'id_network' in df.columns else 0
    }
    
    # Varningar
    if 'nuav_2022' in df.columns:
        zero_nuav = (df['nuav_2022'] == 0).sum()
        if zero_nuav > 0:
            validation['warnings'].append(f"{zero_nuav} komponenter har NUAV = 0")
    
    if 'ekdep' in df.columns:
        invalid_ekdep = (df['ekdep'] <= 0).sum()
        if invalid_ekdep > 0:
            validation['warnings'].append(f"{invalid_ekdep} komponenter har ekdep <= 0")
    
    return validation


def export_step_result(step_data: Dict[str, Any], step_number: int, dmu_id: int, export_dir: str = "exports/") -> str:
    """
    Exporterar steg-resultat till fil för senare användning.
    """
    import json
    from datetime import datetime
    
    Path(export_dir).mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"dmu_{dmu_id}_step_{step_number}_{timestamp}.json"
    filepath = Path(export_dir) / filename
    
    export_data = {
        'dmu_id': dmu_id,
        'step_number': step_number,
        'timestamp': timestamp,
        'data': step_data
    }
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, ensure_ascii=False, indent=2, default=str)
    
    return str(filepath)


def import_step_result(filepath: str) -> Dict[str, Any]:
    """
    Importerar tidigare exporterat steg-resultat.
    """
    import json
    
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


# Hjälpfunktioner för debugging och analys
def analyze_component_ages(df: pd.DataFrame, time: int = 229) -> Dict[str, Any]:
    """
    Analyserar komponentålders-fördelning för debugging.
    """
    age_col = f'age_component_{time}'
    if age_col not in df.columns:
        return {'error': f'Kolumn {age_col} saknas'}
    
    ages = df[age_col]
    
    analysis = {
        'period': time,
        'total_components': len(ages),
        'age_stats': {
            'mean': ages.mean(),
            'median': ages.median(),
            'min': ages.min(),
            'max': ages.max(),
            'std': ages.std()
        },
        'age_distribution': {
            'negative_ages': (ages < 0).sum(),
            'zero_age': (ages == 0).sum(),
            'young_0_10': ((ages > 0) & (ages <= 10)).sum(),
            'medium_10_30': ((ages > 10) & (ages <= 30)).sum(),
            'old_30_plus': (ages > 30).sum()
        }
    }
    
    return analysis


def analyze_nuav_distribution(df: pd.DataFrame, time: int = 229) -> Dict[str, Any]:
    """
    Analyserar NUAV-fördelning för debugging.
    """
    ord_col = f'nuav_ord_{time}'
    tail_col = f'nuav_tail_{time}'
    
    analysis = {'period': time}
    
    if ord_col in df.columns:
        ord_nuav = df[ord_col]
        analysis['ordinary'] = {
            'total': ord_nuav.sum(),
            'components_with_value': (ord_nuav > 0).sum(),
            'max_component': ord_nuav.max(),
            'mean_per_component': ord_nuav[ord_nuav > 0].mean() if (ord_nuav > 0).any() else 0
        }
    
    if tail_col in df.columns:
        tail_nuav = df[tail_col]
        analysis['tail'] = {
            'total': tail_nuav.sum(),
            'components_with_value': (tail_nuav > 0).sum(),
            'max_component': tail_nuav.max(),
            'mean_per_component': tail_nuav[tail_nuav > 0].mean() if (tail_nuav > 0).any() else 0
        }
    
    return analysis
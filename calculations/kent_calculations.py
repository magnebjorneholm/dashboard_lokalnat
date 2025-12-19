"""
calculations/kent_calculations.py

KENT beräkningskedja steg 5-8 för batch-processing av alla 148 företag.

Steg 5: Åldersberäkning och NUAV
Steg 6: Avskrivningar
Steg 7: Avkastning
Steg 8: Sammanställning

Optimerad för att processa alla företag samtidigt genom capbase_a.
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple
from pathlib import Path


def load_capbase_a(data_path: Optional[str] = None) -> pd.DataFrame:
    """
    Laddar capbase_a_mini.parquet.
    
    Args:
        data_path: Sökväg till data-mapp
        
    Returns:
        DataFrame med ~510k komponenter
    """
    search_paths = []
    if data_path:
        search_paths.append(Path(data_path) / "capbase_a_mini.parquet")
    
    search_paths.extend([
        Path("capbase_a_mini.parquet"),
        Path("data/capbase_a_mini.parquet"),
    ])
    
    for path in search_paths:
        if path.exists():
            return pd.read_parquet(path)
    
    raise FileNotFoundError(
        "capbase_a.parquet hittades inte. Sökvägar försökt: " + 
        ", ".join(str(p) for p in search_paths)
    )


def apply_parameter_adjustments(
    df: pd.DataFrame,
    normvalue_adjustments: Optional[Dict[int, float]] = None,
    lifetime_adjustments: Optional[Dict[int, Dict[str, int]]] = None
) -> pd.DataFrame:
    """
    Applicerar parameterjusteringar på capbase_a data.
    
    Args:
        df: capbase_a DataFrame
        normvalue_adjustments: {cat_encode: multiplier}, ex {5: 1.15, 7: 0.90}
        lifetime_adjustments: {cat_encode: {'ekdep': 120, 'maxdep': 150}}
        
    Returns:
        DataFrame med justerade värden
    """
    df = df.copy()
    
    # Normvärdejusteringar (procentuella)
    if normvalue_adjustments:
        for cat_encode, multiplier in normvalue_adjustments.items():
            mask = df['cat_encode'] == cat_encode
            df.loc[mask, 'nuav_2022'] *= multiplier
    
    # Livslängdsjusteringar (absoluta värden)
    if lifetime_adjustments:
        for cat_encode, adjustments in lifetime_adjustments.items():
            mask = df['cat_encode'] == cat_encode
            
            if 'ekdep' in adjustments:
                df.loc[mask, 'ekdep'] = adjustments['ekdep']
            
            if 'maxdep' in adjustments:
                df.loc[mask, 'maxdep'] = adjustments['maxdep']
    
    return df


def calculate_ages_and_nuav_batch(df: pd.DataFrame) -> pd.DataFrame:
    """
    Steg 5: Beräkna åldrar och NUAV för alla tidsperioder (229-236).
    
    Optimerad för batch-processing - bearbetar alla komponenter samtidigt.
    
    Args:
        df: capbase_a DataFrame med komponenter
        
    Returns:
        DataFrame med nya kolumner:
        - age_component_{time}
        - age_component_{time}_invest
        - base_ord_{time}
        - nuav_ord_{time}
        - base_tail_{time}
        - nuav_tail_{time}
        - sum_nuav_ord_{time}
        - sum_nuav_tail_{time}
    """
    result_df = df.copy()
    
    # Bearbeta varje tidsperiod
    for time in range(229, 237):
        result_df = _process_time_period(result_df, time)
    
    return result_df


def _process_time_period(df: pd.DataFrame, time: int) -> pd.DataFrame:
    """
    Bearbetar en tidsperiod - KENT steg 5.
    """
    # Samla alla nya kolumner i dictionary
    new_cols = {}
    
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
    
    # Calculate nuav_tail
    new_cols[f'nuav_tail_{time}'] = df['nuav_2022'] * base_tail
    
    # Lägg till alla nya kolumner
    df = pd.concat([df, pd.DataFrame(new_cols, index=df.index)], axis=1)
    
    # Summarize - ordinary capital base
    sum_nuav_ord = df.groupby(['cat_encode', 'id_network'])[f'nuav_ord_{time}'].sum().reset_index(
        name=f'sum_nuav_ord_{time}'
    )
    df = df.merge(sum_nuav_ord, on=['cat_encode', 'id_network'], how='left')
    df[f'sum_nuav_ord_{time}'] = df[f'sum_nuav_ord_{time}'] / 1000  # Convert to tkr
    
    # Summarize - tail
    sum_nuav_tail = df.groupby(['cat_encode', 'id_network'])[f'nuav_tail_{time}'].sum().reset_index(
        name=f'sum_nuav_tail_{time}'
    )
    df = df.merge(sum_nuav_tail, on=['cat_encode', 'id_network'], how='left')
    df[f'sum_nuav_tail_{time}'] = df[f'sum_nuav_tail_{time}'] / 1000  # Convert to tkr
    
    return df


def calculate_depreciation_batch(df: pd.DataFrame) -> pd.DataFrame:
    """
    Steg 6: Beräkna avskrivningar för alla komponenter och tidsperioder.
    
    Args:
        df: DataFrame från steg 5 med age och nuav kolumner
        
    Returns:
        DataFrame med nya kolumner:
        - comp_dep_{time}
        - age_reg_{time}
        - comp_dep_tail_{time}
    """
    new_cols = {}
    
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
        
        # Convert age_component to numeric
        age_component_numeric = pd.to_numeric(df[age_comp], errors='coerce')
        
        # Compute age_reg
        adjustment = np.where(
            (age_component_numeric % 2 == 1), 
            np.where(age_component_numeric > 0, 1, -1), 
            0
        )
        age_reg_values = age_component_numeric + adjustment
        age_reg_values = pd.to_numeric(age_reg_values, errors='coerce')
        new_cols[age_reg] = age_reg_values
        
        # Compute comp_dep_tail using safe division
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
    
    # Lägg till alla nya kolumner
    if new_cols:
        df = pd.concat([df, pd.DataFrame(new_cols, index=df.index)], axis=1)
    
    return df


def calculate_returns_batch(df: pd.DataFrame, wacc: float = 0.0453) -> pd.DataFrame:
    """
    Steg 7: Beräkna avkastning för alla komponenter och tidsperioder.
    
    Använder Ei's metod med halvårsbaserad åldersberäkning och linjär
    avskrivning av kvarvarande kapitalbas.
    
    Args:
        df: DataFrame från steg 6 med depreciation kolumner
        wacc: WACC att använda (default 0.0453)
        
    Returns:
        DataFrame med nya kolumner:
        - age_return_{time}
        - capbase_left_ord_{time}
        - return_ord_{time}
        - capbase_left_tail_{time}
        - return_tail_{time}
    """
    # Beräkna ekdep2 och maxdep2 (halvår)
    df['ekdep2'] = df['ekdep'] / 2
    df['maxdep2'] = df['maxdep'] / 2
    
    new_cols = {}
    
    for time in range(229, 237):
        age_col = f'age_component_{time}'
        if age_col not in df.columns:
            continue
        
        # Konvertera ålder till halvårsbaserat age_return enligt Ei's metod:
        # 1. Avrunda udda åldrar uppåt (om positiv) eller nedåt (om negativ)
        # 2. Dividera med 2 för att få halvår
        # 3. Subtrahera 1 för att få "ålder vid periodens slut"
        age_return_values = pd.to_numeric(df[age_col], errors='coerce').copy()
        
        mask_odd = (age_return_values % 2 == 1)
        adjustment = np.where(age_return_values > 0, 1, -1)
        age_return_values = np.where(mask_odd, age_return_values + adjustment, age_return_values)
        age_return_values = age_return_values / 2
        age_return_values = age_return_values - 1
        
        new_cols[f'age_return_{time}'] = age_return_values
        
        # Ordinary returns: linjär avskrivning av kvarvarande kapitalbas
        nuav_ord_col = f'nuav_ord_{time}'
        if nuav_ord_col in df.columns:
            # Kvarvarande kapitalbas (linjär avskrivning)
            # capbase_left = ((ekdep/2 - age_return) / (ekdep/2)) * nuav
            capbase_left_ord = ((df['ekdep2'] - age_return_values) / df['ekdep2']) * df[nuav_ord_col]
            
            # Sätt till 0 där age_return < 0 (ännu ej i drift)
            capbase_left_ord = np.where(age_return_values < 0, 0, capbase_left_ord)
            new_cols[f'capbase_left_ord_{time}'] = capbase_left_ord
            
            # Avkastning = wacc * kvarvarande_kapitalbas / 2 (halvårsränta)
            return_ord = wacc * capbase_left_ord / 2
            new_cols[f'return_ord_{time}'] = return_ord
        
        # Tail returns: hyperbolisk avskrivning
        nuav_tail_col = f'nuav_tail_{time}'
        if nuav_tail_col in df.columns:
            # Kvarvarande kapitalbas för tail (hyperbolisk)
            # capbase_left_tail = (1 / (age_return + 1)) * nuav_tail
            denominator = age_return_values + 1
            capbase_left_tail = np.divide(
                df[nuav_tail_col].to_numpy().astype(float),
                denominator,
                out=np.zeros(len(df), dtype=float),
                where=(denominator != 0)
            )
            new_cols[f'capbase_left_tail_{time}'] = capbase_left_tail
            
            # Avkastning = wacc * kvarvarande_kapitalbas / 2 (halvårsränta)
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
    
    Args:
        df: DataFrame från steg 7 med alla beräkningar
        
    Returns:
        DataFrame med aggregerade värden per id_network:
        - id_network
        - REId (ex: "REL00001")
        - dep_ord_{time}
        - dep_tail_{time}
        - return_ord_{time}
        - return_tail_{time}
        - capcost_{time} (summa av alla fyra)
    """
    
    aggregation_dict = {}
    
    # Samla alla kolumner som ska aggregeras
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
    
    # Aggregera per id_network
    df_agg = df.groupby('id_network').agg(aggregation_dict).reset_index()
    
    # Lägg till REId: "REL" + padded id_network
    df_agg['REId'] = 'REL' + df_agg['id_network'].astype(str).str.zfill(5)
    
    # Konvertera till tkr (divide by 1000)
    for col in df_agg.columns:
        if col not in ['id_network', 'REId']:
            df_agg[col] = df_agg[col] / 1000
    
    # Byt namn på kolumner för tydlighet
    rename_dict = {}
    for t in range(229, 237):
        if f'comp_dep_{t}' in df_agg.columns:
            rename_dict[f'comp_dep_{t}'] = f'dep_ord_{t}'
        if f'comp_dep_tail_{t}' in df_agg.columns:
            rename_dict[f'comp_dep_tail_{t}'] = f'dep_tail_{t}'
    
    df_agg = df_agg.rename(columns=rename_dict)
    
    # Beräkna total kapitalkostnad per tidsperiod
    for t in range(229, 237):
        dep_ord = f'dep_ord_{t}'
        dep_tail = f'dep_tail_{t}'
        ret_ord = f'return_ord_{t}'
        ret_tail = f'return_tail_{t}'
        
        # Sätt 0 för kolumner som saknas
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
    
    Producerar:
    - Kapitalkostnad_2024: Årsvärde för 2024 (H1+H2) - används för DEA
    - Kapitalkostnad_Period: Periodsumma 2024-2027 (8 halvår) - används för intäktsram
    - Avkastning_{year}: Avkastning per år - används för incitament 1/3-cap
    
    Args:
        df_network: DataFrame med capcost_{time} kolumner per id_network
        
    Returns:
        DataFrame med nya kolumner för kapitalkostnad och avkastning
    """
    df = df_network.copy()
    
    # Säkerställ att alla capcost-kolumner finns (229-236 = 8 halvår)
    for t in range(229, 237):
        col = f'capcost_{t}'
        if col not in df.columns:
            df[col] = 0.0
    
    # Årsvärde för 2024: summa av H1 (229) + H2 (230)
    df['Kapitalkostnad_2024'] = df['capcost_229'] + df['capcost_230']
    
    # Periodsumma för 2024-2027: alla 8 halvår (229-236)
    period_cols = [f'capcost_{t}' for t in range(229, 237)]
    df['Kapitalkostnad_Period'] = df[period_cols].sum(axis=1)
    
    # Årsvärden per år (för breakdown/analys)
    year_to_codes = {
        2024: [229, 230],
        2025: [231, 232],
        2026: [233, 234],
        2027: [235, 236],
    }
    for year, codes in year_to_codes.items():
        df[f'Kapitalkostnad_{year}'] = df[[f'capcost_{c}' for c in codes]].sum(axis=1)
    
    # Avkastning per år - krävs för incitamentjusteringens 1/3-cap
    # Cap appliceras per år på avkastningen, inte hela kapitalkostnaden
    for year, codes in year_to_codes.items():
        return_cols = []
        for code in codes:
            if f'return_ord_{code}' in df.columns:
                return_cols.append(f'return_ord_{code}')
            if f'return_tail_{code}' in df.columns:
                return_cols.append(f'return_tail_{code}')
        
        if return_cols:
            df[f'Avkastning_{year}'] = df[return_cols].sum(axis=1)
        else:
            df[f'Avkastning_{year}'] = 0.0
    
    # Avkastning periodsumma (för validering/analys)
    avkastning_year_cols = [f'Avkastning_{y}' for y in year_to_codes.keys()]
    df['Avkastning_Period'] = df[avkastning_year_cols].sum(axis=1)
    
    return df


def run_kent_calculations_batch(
    capbase_data: pd.DataFrame,
    wacc: float = 0.0453,
    normvalue_adjustments: Optional[Dict[int, float]] = None,
    lifetime_adjustments: Optional[Dict[int, Dict[str, int]]] = None
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Kör hela KENT-beräkningskedjan steg 5-8 för alla företag.
    
    Args:
        capbase_data: capbase_a DataFrame
        wacc: WACC att använda
        normvalue_adjustments: Procentuella normvärdejusteringar
        lifetime_adjustments: Livslängdsjusteringar
        
    Returns:
        Tuple med:
        - df_detailed: DataFrame med alla beräkningar per komponent
        - df_network: DataFrame med aggregerade värden per id_network
          Innehåller bl.a.:
          - Kapitalkostnad_2024: Årsvärde för DEA
          - Kapitalkostnad_Period: Periodsumma för intäktsram
          - Avkastning_{2024-2027}: Per-år avkastning för incitament-cap
          - Avkastning_Period: Total avkastning för perioden
    """
    
    # Applicera parameterjusteringar om några finns
    if normvalue_adjustments or lifetime_adjustments:
        capbase_data = apply_parameter_adjustments(
            capbase_data,
            normvalue_adjustments,
            lifetime_adjustments
        )
    
    # Steg 5: Åldrar och NUAV
    df_step5 = calculate_ages_and_nuav_batch(capbase_data)
    
    # Steg 6: Avskrivningar
    df_step6 = calculate_depreciation_batch(df_step5)
    
    # Steg 7: Avkastning
    df_step7 = calculate_returns_batch(df_step6, wacc=wacc)
    
    # Steg 8: Aggregera till id_network nivå
    df_network = aggregate_to_network_level(df_step7)
    
    # Beräkna kapitalkostnads-outputs (årsvärde + periodsumma + avkastning per år)
    df_network = calculate_capex_outputs(df_network)
    
    return df_step7, df_network
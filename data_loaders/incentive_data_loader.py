"""
data_loaders/incentive_data_loader.py

Laddar incitament-inputdata fran all_adjust_vars.csv.
Mappar reid (numerisk) till REId-format och forbereder for incentive_calculations.
"""

import pandas as pd
from pathlib import Path
from typing import Optional


def load_incentive_input(data_path: Optional[str] = None) -> pd.DataFrame:
    """
    Laddar incitament-inputdata fran all_adjust_vars.csv.
    
    Filen innehaller per-ar data for alla 148 foretag (4 ar = ~592 rader):
    - reid: Numerisk identifierare
    - year: 2024-2027
    - Normer och observerade varden for AIT/AIF, natforlust, belastning
    - AME-volymer per kundtyp
    
    Args:
        data_path: Sokvag till data-mapp (default: 'data/')
        
    Returns:
        DataFrame med incitament-input, REId tillagt
        
    Raises:
        FileNotFoundError: Om filen inte hittas
    """
    search_paths = []
    
    if data_path:
        search_paths.append(Path(data_path) / "all_adjust_vars.csv")
    
    search_paths.extend([
        Path("all_adjust_vars.csv"),
        Path("data/all_adjust_vars.csv"),
        Path("data_loaders/all_adjust_vars.csv"),
    ])
    
    df = None
    for path in search_paths:
        if path.exists():
            df = pd.read_csv(path)
            break
    
    if df is None:
        raise FileNotFoundError(
            f"all_adjust_vars.csv hittades inte. Sokvagar forsokta: "
            + ", ".join(str(p) for p in search_paths)
        )
    
    # Mappa reid (numerisk) till REId-format
    # reid=1 -> REL00001, reid=886 -> REL00886, etc.
    df['REId'] = 'REL' + df['reid'].astype(str).str.zfill(5)
    
    # Satt capcost till NaN (ska ersattas med faktisk avkastning)
    # Kolumnen 'capcost' ar en placeholder i originalfilen
    if 'capcost' in df.columns:
        df = df.drop(columns=['capcost'])
    
    return df


def prepare_incentive_input_with_return(
    df_incentive: pd.DataFrame,
    df_return_per_year: pd.DataFrame
) -> pd.DataFrame:
    """
    Kombinerar incitament-input med per-ar avkastning.
    
    Incitament-berakningen kraver 'ret_period' (avkastning per ar i kr)
    for att applicera 1/3-cap korrekt per ar.
    
    Args:
        df_incentive: DataFrame fran load_incentive_input()
        df_return_per_year: DataFrame med REId, Return_2024, Return_2025, etc. (tkr)
        
    Returns:
        DataFrame med ret_period tillagd (kr)
    """
    df = df_incentive.copy()
    
    # Skapa mapping fran REId + year till avkastning
    # df_return_per_year har kolumner: REId, Return_2024, Return_2025, Return_2026, Return_2027
    
    def get_return_for_row(row):
        reid = row['REId']
        year = row['year']
        
        col_name = f'Return_{year}'
        
        # Hitta raden for detta foretag
        match = df_return_per_year[df_return_per_year['REId'] == reid]
        
        if match.empty or col_name not in match.columns:
            return 0.0
        
        # Konvertera fran tkr till kr (incentive_calculations arbetar i kr)
        return float(match[col_name].iloc[0]) * 1000
    
    df['ret_period'] = df.apply(get_return_for_row, axis=1)
    
    return df


def get_return_per_year_baseline(
    df_all_companies: pd.DataFrame
) -> pd.DataFrame:
    """
    Hamtar per-ar avkastning fran baseline (Data_modeller.Avkastning).
    
    Anvander Data_modeller.Avkastning (arsvarde i tkr) for alla 4 ar.
    Detta ar konsekvent med att DEA anvander Data_modeller.Kapitalkostnad_2024.
    
    Approximation: Samma arsvarde for alla 4 ar (ret_2024 = ret_2025 = ret_2026 = ret_2027).
    
    Args:
        df_all_companies: DataFrame med REId och Avkastning (tkr/ar)
        
    Returns:
        DataFrame med REId, Return_2024, Return_2025, Return_2026, Return_2027 (tkr)
        
    Note:
        Skillnad mot SDF-metoden ar ~1.7%, vilket ar inom avrundningsfel.
        Data_modeller valjs for arkitektonisk konsistens.
    """
    if 'Avkastning' not in df_all_companies.columns:
        raise ValueError(
            "Kolumn 'Avkastning' saknas i df_all_companies. "
            "Kravs for incitament-berakning."
        )
    
    df = df_all_companies[['REId', 'Avkastning']].copy()
    
    # Samma arsvarde for alla 4 ar (approximation)
    for year in [2024, 2025, 2026, 2027]:
        df[f'Return_{year}'] = df['Avkastning']
    
    return df[['REId', 'Return_2024', 'Return_2025', 'Return_2026', 'Return_2027']]


def get_return_per_year_wacc_scaled(
    df_all_companies: pd.DataFrame,
    new_wacc: float,
    baseline_wacc: float
) -> pd.DataFrame:
    """
    Hamtar per-ar avkastning med WACC-skalning.
    
    Formel: ny_avkastning = baseline_avkastning * (new_wacc / baseline_wacc)
    
    Anvander Data_modeller.Avkastning som bas, skalad med WACC-kvot.
    Samma arsvarde for alla 4 ar (approximation).
    
    Args:
        df_all_companies: DataFrame med REId och Avkastning (tkr/ar)
        new_wacc: Ny WACC (real, fore skatt)
        baseline_wacc: Baseline WACC (0.0453)
        
    Returns:
        DataFrame med REId, Return_2024, Return_2025, Return_2026, Return_2027 (tkr)
    """
    if 'Avkastning' not in df_all_companies.columns:
        raise ValueError(
            "Kolumn 'Avkastning' saknas i df_all_companies. "
            "Kravs for incitament-berakning."
        )
    
    scaling_factor = new_wacc / baseline_wacc
    
    df = df_all_companies[['REId', 'Avkastning']].copy()
    df['Avkastning_Scaled'] = df['Avkastning'] * scaling_factor
    
    # Samma skalade arsvarde for alla 4 ar (approximation)
    for year in [2024, 2025, 2026, 2027]:
        df[f'Return_{year}'] = df['Avkastning_Scaled']
    
    return df[['REId', 'Return_2024', 'Return_2025', 'Return_2026', 'Return_2027']]


def get_return_per_year_kent(
    df_network: pd.DataFrame
) -> pd.DataFrame:
    """
    Hamtar per-ar avkastning fran KENT-berakningar.
    
    Summerar return_ord + return_tail per ar (tva halvar per ar).
    
    Tidskoder: 229=2024H1, 230=2024H2, 231=2025H1, etc.
    
    Args:
        df_network: DataFrame fran KENT aggregering med return_ord_{tc} och return_tail_{tc}
        
    Returns:
        DataFrame med REId, Return_2024, Return_2025, Return_2026, Return_2027 (tkr)
    """
    result = df_network[['REId']].copy()
    
    year_to_codes = {
        2024: [229, 230],
        2025: [231, 232],
        2026: [233, 234],
        2027: [235, 236],
    }
    
    for year, codes in year_to_codes.items():
        year_return = 0.0
        
        for tc in codes:
            ret_ord_col = f'return_ord_{tc}'
            ret_tail_col = f'return_tail_{tc}'
            
            if ret_ord_col in df_network.columns:
                year_return = year_return + df_network[ret_ord_col].fillna(0)
            
            if ret_tail_col in df_network.columns:
                year_return = year_return + df_network[ret_tail_col].fillna(0)
        
        result[f'Return_{year}'] = year_return
    
    return result
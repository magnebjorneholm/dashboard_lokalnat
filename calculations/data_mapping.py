"""
calculations/data_mapping.py

Funktioner för att mappa mellan id_network, REId och företagsdata.
Efter RER-filtrering har vi 1:1 mapping: id_network <-> REId.
"""

import pandas as pd
from typing import Dict

# Korrekt halvårsmappning
YEAR_TO_TIMECODES = {
    2024: [229, 230],  # H1 + H2
    2025: [231, 232],
    2026: [233, 234],
    2027: [235, 236],
}


def merge_kent_with_baseline(
    df_network: pd.DataFrame,
    df_all_companies: pd.DataFrame
) -> pd.DataFrame:
    """
    Mergar KENT-beraknad CAPEX med baseline foretagsdata.
    
    Efter RER-filtrering har vi 1:1 mapping: id_network <-> REId (148->148).
    KENT lagger till REId automatiskt, sa vi kan gora direct merge!
    
    Process:
    1. Verifiera att df_network har REId
    2. Direct merge pa REId
    3. Uppdatera TOTEX = OPEXp + CAPEX
    
    Args:
        df_network: DataFrame med kapitalkostnader per REId fran KENT
            Forvantar: REId, CAPEX, Kapitalkostnad_2024, Kapitalkostnad_Period
        df_all_companies: Baseline foretagsdata med OPEXp, volumes etc
        
    Returns:
        DataFrame med 148 foretag och uppdaterad CAPEX/TOTEX + periodsumma
    """
    
    # 1. Verifiera att REId finns
    if 'REId' not in df_network.columns:
        raise ValueError("df_network saknar REId-kolumn! Kor aggregate_to_network_level forst.")
    
    # 2. Direct merge pa REId
    # Ta allt fran df_all_companies utom Kapitalkostnad_2024 och TOTEX
    exclude_cols = ['Kapitalkostnad_2024', 'TOTEX', 'Kapitalkostnad_Period',
                    'Kapitalkostnad_2025', 'Kapitalkostnad_2026', 'Kapitalkostnad_2027']
    base_cols = [col for col in df_all_companies.columns if col not in exclude_cols]
    df_base = df_all_companies[base_cols].copy()
    
    # Kolumner att hamta fran KENT
    kent_cols = ['REId', 'Kapitalkostnad_2024', 'Kapitalkostnad_Period']
    # Lagg till arsvarden om de finns
    for year in [2024, 2025, 2026, 2027]:
        col = f'Kapitalkostnad_{year}'
        if col in df_network.columns:
            kent_cols.append(col)
    
    df_result = df_base.merge(
        df_network[[c for c in kent_cols if c in df_network.columns]],
        on='REId',
        how='left'
    )
    
    # 3. Berakna ny TOTEX = OPEXp + Kapitalkostnad_2024
    df_result['TOTEX'] = df_result['OPEXp'] + df_result['Kapitalkostnad_2024']
    
    # 4. For foretag utan CAPEX fran KENT (shouldn't happen), anvand baseline
    missing_capex = df_result['Kapitalkostnad_2024'].isna()
    if missing_capex.any():
        # If KENT ran correctly we expect values for all companies.
        # Raise an explicit error instead of silently falling back to baseline,
        # so the caller can decide how to handle partially missing KENT output.
        missing_reids = df_result.loc[missing_capex, 'REId'].tolist()
        msg = (
            f"KENT output saknar Kapitalkostnad_2024 for {missing_capex.sum()} företag. "
            f"Missing REIds: {missing_reids[:10]}{'...' if len(missing_reids) > 10 else ''}"
        )
        raise ValueError(msg)
    
    return df_result


def get_detailed_capex_data(
    df_network: pd.DataFrame,
    target_reid: str
) -> pd.DataFrame:
    """
    Hamtar detaljerad kapitalkostnadsdata for ett specifikt foretag.
    
    Args:
        df_network: DataFrame med kapitalkostnader per REId fran KENT
        target_reid: REId att hamta data for (ex: "REL00001")
        
    Returns:
        DataFrame med alla tidsperioder och kapitalkostnadskomponenter
    """
    
    # Direct filter pa REId
    df_filtered = df_network[df_network['REId'] == target_reid].copy()
    
    return df_filtered


def create_capex_breakdown(
    df_network: pd.DataFrame, 
    target_reid: str
) -> Dict:
    """
    Skapar en detaljerad uppdelning av CAPEX for ett foretag.
    
    Tidskoder ar HALVAR: 229=2024H1, 230=2024H2, etc.
    
    Args:
        df_network: DataFrame med kapitalkostnader per REId fran KENT
        target_reid: REId att analysera (ex: "REL00001")
        
    Returns:
        Dict med breakdown per ar och komponent
    """
    
    df_detailed = get_detailed_capex_data(df_network, target_reid)
    
    if df_detailed.empty:
        return {}
    
    breakdown = {}
    
    # Iterera over ar (inte halvar)
    for year, timecodes in YEAR_TO_TIMECODES.items():
        year_data = {
            'dep_ord': 0.0,
            'dep_tail': 0.0,
            'return_ord': 0.0,
            'return_tail': 0.0,
        }
        
        # Summera bada halvaren for detta ar
        for t in timecodes:
            dep_ord_col = f'dep_ord_{t}'
            dep_tail_col = f'dep_tail_{t}'
            ret_ord_col = f'return_ord_{t}'
            ret_tail_col = f'return_tail_{t}'
            
            if dep_ord_col in df_detailed.columns:
                year_data['dep_ord'] += df_detailed[dep_ord_col].iloc[0]
            if dep_tail_col in df_detailed.columns:
                year_data['dep_tail'] += df_detailed[dep_tail_col].iloc[0]
            if ret_ord_col in df_detailed.columns:
                year_data['return_ord'] += df_detailed[ret_ord_col].iloc[0]
            if ret_tail_col in df_detailed.columns:
                year_data['return_tail'] += df_detailed[ret_tail_col].iloc[0]
        
        year_data['total_dep'] = year_data['dep_ord'] + year_data['dep_tail']
        year_data['total_return'] = year_data['return_ord'] + year_data['return_tail']
        year_data['capcost_total'] = year_data['total_dep'] + year_data['total_return']
        
        breakdown[year] = year_data
    
    return breakdown


def create_halfyear_breakdown(
    df_network: pd.DataFrame, 
    target_reid: str
) -> Dict:
    """
    Skapar halvarsvis breakdown av kapitalkostnader.
    
    Args:
        df_network: DataFrame med kapitalkostnader per REId fran KENT
        target_reid: REId att analysera (ex: "REL00001")
        
    Returns:
        Dict med breakdown per halvar (ex: '2024H1', '2024H2', etc.)
    """
    
    df_detailed = get_detailed_capex_data(df_network, target_reid)
    
    if df_detailed.empty:
        return {}
    
    breakdown = {}
    
    for t in range(229, 237):
        # Konvertera tidskod till label
        year = 2024 + (t - 229) // 2
        half = ((t - 229) % 2) + 1
        label = f"{year}H{half}"
        
        dep_ord = df_detailed[f'dep_ord_{t}'].iloc[0] if f'dep_ord_{t}' in df_detailed.columns else 0
        dep_tail = df_detailed[f'dep_tail_{t}'].iloc[0] if f'dep_tail_{t}' in df_detailed.columns else 0
        ret_ord = df_detailed[f'return_ord_{t}'].iloc[0] if f'return_ord_{t}' in df_detailed.columns else 0
        ret_tail = df_detailed[f'return_tail_{t}'].iloc[0] if f'return_tail_{t}' in df_detailed.columns else 0
        
        breakdown[label] = {
            'timecode': t,
            'dep_ord': dep_ord,
            'dep_tail': dep_tail,
            'return_ord': ret_ord,
            'return_tail': ret_tail,
            'total_dep': dep_ord + dep_tail,
            'total_return': ret_ord + ret_tail,
            'capcost_total': dep_ord + dep_tail + ret_ord + ret_tail
        }
    
    return breakdown
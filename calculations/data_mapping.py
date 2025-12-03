"""
calculations/data_mapping.py

Funktioner för att mappa mellan id_network, REId och företagsdata.
Efter RER-filtrering har vi 1:1 mapping: id_network ↔ REId.
"""

import pandas as pd
from typing import Dict


def merge_kent_with_baseline(
    df_network: pd.DataFrame,
    df_all_companies: pd.DataFrame
) -> pd.DataFrame:
    """
    Mergar KENT-beräknad CAPEX med baseline företagsdata.
    
    Efter RER-filtrering har vi 1:1 mapping: id_network ↔ REId (148→148).
    KENT lägger till REId automatiskt, så vi kan göra direct merge!
    
    Process:
    1. Verifiera att df_network har REId
    2. Direct merge på REId
    3. Uppdatera TOTEX = OPEXp + CAPEX
    
    Args:
        df_network: DataFrame med CAPEX per REId från KENT
        df_all_companies: Baseline företagsdata med OPEXp, volumes etc
        
    Returns:
        DataFrame med 148 företag och uppdaterad CAPEX/TOTEX
    """
    
    # 1. Verifiera att REId finns
    if 'REId' not in df_network.columns:
        raise ValueError("df_network saknar REId-kolumn! Kör aggregate_to_network_level först.")
    
    # 2. Direct merge på REId - så enkelt!
    # Ta allt från df_all_companies utom CAPEX och TOTEX (som kommer från KENT)
    base_cols = [col for col in df_all_companies.columns if col not in ['CAPEX', 'TOTEX']]
    df_base = df_all_companies[base_cols].copy()
    
    df_result = df_base.merge(
        df_network[['REId', 'CAPEX']],
        on='REId',
        how='left'
    )
    
    # 3. Beräkna ny TOTEX = OPEXp + CAPEX
    df_result['TOTEX'] = df_result['OPEXp'] + df_result['CAPEX']
    
    # 4. För företag utan CAPEX från KENT (shouldn't happen), använd baseline
    missing_capex = df_result['CAPEX'].isna()
    if missing_capex.any():
        print(f"⚠️ {missing_capex.sum()} företag saknar KENT CAPEX - använder baseline")
        baseline_capex = df_all_companies.set_index('REId')['CAPEX']
        df_result.loc[missing_capex, 'CAPEX'] = df_result.loc[missing_capex, 'REId'].map(baseline_capex)
        df_result.loc[missing_capex, 'TOTEX'] = df_result.loc[missing_capex, 'OPEXp'] + df_result.loc[missing_capex, 'CAPEX']
    
    return df_result


def get_detailed_capex_data(
    df_network: pd.DataFrame,
    target_reid: str
) -> pd.DataFrame:
    """
    Hämtar detaljerad kapitalkostnadsdata för ett specifikt företag.
    
    Args:
        df_network: DataFrame med kapitalkostnader per REId från KENT
        target_reid: REId att hämta data för (ex: "REL00001")
        
    Returns:
        DataFrame med alla tidsperioder och kapitalkostnadskomponenter
    """
    
    # Direct filter på REId
    df_filtered = df_network[df_network['REId'] == target_reid].copy()
    
    return df_filtered


def create_capex_breakdown(
    df_network: pd.DataFrame, 
    target_reid: str
) -> Dict:
    """
    Skapar en detaljerad uppdelning av CAPEX för ett företag.
    
    Args:
        df_network: DataFrame med kapitalkostnader per REId från KENT
        target_reid: REId att analysera (ex: "REL00001")
        
    Returns:
        Dict med breakdown per år och komponent
    """
    
    df_detailed = get_detailed_capex_data(df_network, target_reid)
    
    if df_detailed.empty:
        return {}
    
    breakdown = {}
    
    for t in range(229, 237):
        year = 2024 + (t - 229)  # 229 → 2024, 230 → 2025, etc.
        
        dep_ord = df_detailed[f'dep_ord_{t}'].iloc[0] if f'dep_ord_{t}' in df_detailed.columns else 0
        dep_tail = df_detailed[f'dep_tail_{t}'].iloc[0] if f'dep_tail_{t}' in df_detailed.columns else 0
        ret_ord = df_detailed[f'return_ord_{t}'].iloc[0] if f'return_ord_{t}' in df_detailed.columns else 0
        ret_tail = df_detailed[f'return_tail_{t}'].iloc[0] if f'return_tail_{t}' in df_detailed.columns else 0
        
        breakdown[year] = {
            'dep_ord': dep_ord,
            'dep_tail': dep_tail,
            'return_ord': ret_ord,
            'return_tail': ret_tail,
            'total_dep': dep_ord + dep_tail,
            'total_return': ret_ord + ret_tail,
            'capcost_total': dep_ord + dep_tail + ret_ord + ret_tail
        }
    
    return breakdown
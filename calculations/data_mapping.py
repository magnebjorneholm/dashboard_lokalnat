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

# TEST_MODE: Tillåt körning med ofullständig capbase_a
# Sätt till False i produktion för att blockera PARAMETER_CHANGE med < 148 nätverk
TEST_MODE = True


def merge_kent_with_baseline(
    df_network: pd.DataFrame,
    df_all_companies: pd.DataFrame
) -> pd.DataFrame:
    """
    Mergar KENT-beräknad CAPEX med baseline företagsdata.
    
    Efter RER-filtrering har vi 1:1 mapping: id_network <-> REId (148->148).
    KENT lägger till REId automatiskt, så vi kan göra direct merge!
    
    Process:
    1. Verifiera att df_network har REId
    2. Direct merge på REId
    3. Hantera saknade företag (TEST_MODE eller fel)
    4. Uppdatera TOTEX = OPEXp + CAPEX
    
    Args:
        df_network: DataFrame med kapitalkostnader per REId från KENT
            Förväntar: REId, CAPEX, Kapitalkostnad_2024, Kapitalkostnad_Period
        df_all_companies: Baseline företagsdata med OPEXp, volumes etc
        
    Returns:
        DataFrame med 148 företag och uppdaterad CAPEX/TOTEX + periodsumma
    """
    
    # 1. Verifiera att REId finns
    if 'REId' not in df_network.columns:
        raise ValueError("df_network saknar REId-kolumn! Kör aggregate_to_network_level först.")
    
    # 2. Kontrollera täckning
    kent_reids = set(df_network['REId'].unique())
    baseline_reids = set(df_all_companies['REId'].unique())
    missing_reids = baseline_reids - kent_reids
    n_kent = len(kent_reids)
    n_baseline = len(baseline_reids)
    
    if missing_reids:
        if TEST_MODE:
            print(f"  ⚠️ TEST MODE: KENT har {n_kent}/{n_baseline} företag. "
                  f"{len(missing_reids)} företag får baseline-värden.")
        else:
            raise ValueError(
                f"KENT output saknar {len(missing_reids)}/{n_baseline} företag. "
                f"Kör med full capbase_a (148 nätverk) eller aktivera TEST_MODE. "
                f"Saknade REIds: {sorted(list(missing_reids))[:10]}..."
            )
    
    # 3. Förbered baseline-data (exkludera kolumner som ska ersättas)
    exclude_cols = ['Kapitalkostnad_2024', 'TOTEX', 'Kapitalkostnad_Period',
                    'Kapitalkostnad_2025', 'Kapitalkostnad_2026', 'Kapitalkostnad_2027',
                    'CAPEX', 'Avskrivning', 'Avkastning']
    base_cols = [col for col in df_all_companies.columns if col not in exclude_cols]
    df_base = df_all_companies[base_cols].copy()
    
    # 4. Kolumner att hämta från KENT
    kent_cols = ['REId', 'Kapitalkostnad_2024']
    optional_kent_cols = ['Kapitalkostnad_Period', 'CAPEX', 'Avskrivning', 'Avkastning',
                          'Kapitalkostnad_2025', 'Kapitalkostnad_2026', 'Kapitalkostnad_2027']
    for col in optional_kent_cols:
        if col in df_network.columns:
            kent_cols.append(col)
    
    # 5. Merge med reset_index för att undvika duplicerat index
    df_result = df_base.merge(
        df_network[[c for c in kent_cols if c in df_network.columns]],
        on='REId',
        how='left'
    ).reset_index(drop=True)
    
    # 6. Hantera saknade företag
    missing_capex = df_result['Kapitalkostnad_2024'].isna()
    if missing_capex.any():
        if TEST_MODE:
            # Fallback till baseline för saknade företag
            # Kolumner som behöver fallback
            fallback_cols = [
                'Kapitalkostnad_2024', 'Kapitalkostnad_Period',
                'Kapitalkostnad_2025', 'Kapitalkostnad_2026', 'Kapitalkostnad_2027'
            ]
            
            baseline_indexed = df_all_companies.set_index('REId')
            fallback_count = 0
            
            for col in fallback_cols:
                if col in baseline_indexed.columns:
                    # Säkerställ kolumn finns i result
                    if col not in df_result.columns:
                        df_result[col] = pd.NA
                    
                    for idx in df_result[missing_capex].index:
                        reid = df_result.loc[idx, 'REId']
                        if reid in baseline_indexed.index:
                            df_result.loc[idx, col] = baseline_indexed.loc[reid, col]
                    fallback_count += 1
            
            # Om Kapitalkostnad_Period saknas i baseline, approximera
            # I TEST_MODE: periodsumma ≈ 4 * årsvärde (rimlig approximation)
            # I PRODUKTION: Detta körs aldrig eftersom alla 148 får KENT-värden
            if 'Kapitalkostnad_Period' not in df_result.columns:
                df_result['Kapitalkostnad_Period'] = pd.NA
            
            period_missing = df_result['Kapitalkostnad_Period'].isna()
            if period_missing.any():
                # Approximera: 4 år ≈ 4x årsvärde
                df_result.loc[period_missing, 'Kapitalkostnad_Period'] = \
                    df_result.loc[period_missing, 'Kapitalkostnad_2024'] * 4
                print(f"  ⚠️ TEST MODE: Approximerade Kapitalkostnad_Period (4x årsvärde) för {period_missing.sum()} företag")
            
            print(f"  ✓ Fallback till baseline för {missing_capex.sum()} företag ({fallback_count} kolumner)")
        else:
            missing_list = df_result.loc[missing_capex, 'REId'].tolist()
            raise ValueError(
                f"KENT output saknar Kapitalkostnad_2024 för {missing_capex.sum()} företag. "
                f"Missing REIds: {missing_list[:10]}{'...' if len(missing_list) > 10 else ''}"
            )
    
    # 7. Beräkna ny TOTEX = OPEXp + Kapitalkostnad_2024
    df_result['TOTEX'] = df_result['OPEXp'] + df_result['Kapitalkostnad_2024']
    
    # 8. Säkerställ CAPEX-kolumn finns (alias för Kapitalkostnad_2024)
    if 'CAPEX' not in df_result.columns:
        df_result['CAPEX'] = df_result['Kapitalkostnad_2024']
    
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
    
    Tidskoder är HALVÅR: 229=2024H1, 230=2024H2, etc.
    
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
    
    # Iterera över år (inte halvår)
    for year, timecodes in YEAR_TO_TIMECODES.items():
        year_data = {
            'dep_ord': 0.0,
            'dep_tail': 0.0,
            'return_ord': 0.0,
            'return_tail': 0.0,
        }
        
        # Summera båda halvåren för detta år
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
    Skapar halvårsvis breakdown av kapitalkostnader.
    
    Args:
        df_network: DataFrame med kapitalkostnader per REId från KENT
        target_reid: REId att analysera (ex: "REL00001")
        
    Returns:
        Dict med breakdown per halvår (ex: '2024H1', '2024H2', etc.)
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
"""
calculations/incentive_calculations.py

Beräkningar för kvalitets- och nätincitament enligt Bilaga 4 (Ei).
Implementerar logiken från 3_functions.do.

Tre incitamenttyper:
1. Kvalitetsincitamentet (inter_incentive) - AIT/AIF-baserat
2. Nätförlustincitamentet (loss_incentive) - nätförlust vs norm
3. Belastningsincitamentet (util_incentive) - utnyttjningsgrad vs norm
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional

# Importera baseline-värden (används som defaults)
from .incentive_parameters import (
    KPI as BASELINE_KPI,
    K_NF as BASELINE_K_NF,
    ADJ_MAX_AGG as BASELINE_ADJ_MAX_AGG,
    ADJ_MAX_CEMI4 as BASELINE_ADJ_MAX_CEMI4,
    SHARING_NETLOSS as BASELINE_SHARING_NETLOSS,
    AIT_COSTS as BASELINE_AIT_COSTS,
    AIF_COSTS as BASELINE_AIF_COSTS,
    MISSING_DATA_IDS,
)


def calculate_interruption_incentives(
    df: pd.DataFrame,
    kpi: Optional[Dict[int, float]] = None,
    ait_costs: Optional[Dict[Tuple[str, int], float]] = None,
    aif_costs: Optional[Dict[Tuple[str, int], float]] = None,
) -> pd.DataFrame:
    """
    Beräknar kvalitetsincitament (AIT/AIF) per rad.
    
    Formel per indikator/kundtyp:
        inc = (norm - obs) * kostnad * ame * kpi
    
    Args:
        df: DataFrame med kolumner:
            - year
            - ait_{a,o}_{1-6}_{norm,obs}
            - aif_{a,o}_{1-6}_{norm,obs}
            - ame_{1-6}
        kpi: KPI per år (None = baseline)
        ait_costs: AIT-kostnader per (ann, sni) (None = baseline)
        aif_costs: AIF-kostnader per (ann, sni) (None = baseline)
            
    Returns:
        DataFrame med nya kolumner: inc_ait_*, inc_aif_*, inc_inter
    """
    df = df.copy()
    
    # Använd baseline om ej angivet
    kpi = kpi if kpi is not None else BASELINE_KPI
    ait_costs = ait_costs if ait_costs is not None else BASELINE_AIT_COSTS
    aif_costs = aif_costs if aif_costs is not None else BASELINE_AIF_COSTS
    
    # Sätt KPI per år
    df['kpi'] = df['year'].map(kpi)
    
    # Beräkna delincitament per typ/ann/sni
    for ind_type in ['ait', 'aif']:
        costs = ait_costs if ind_type == 'ait' else aif_costs
        
        for ann in ['a', 'o']:
            for sni in range(1, 7):
                norm_col = f'{ind_type}_{ann}_{sni}_norm'
                obs_col = f'{ind_type}_{ann}_{sni}_obs'
                ame_col = f'ame_{sni}'
                cost = costs.get((ann, sni), 0)
                
                # Kontrollera att kolumner finns
                if norm_col in df.columns and obs_col in df.columns:
                    df[f'inc_{ind_type}_{ann}_{sni}'] = (
                        (df[norm_col] - df[obs_col]) * cost * df[ame_col] * df['kpi']
                    )
                else:
                    df[f'inc_{ind_type}_{ann}_{sni}'] = np.nan
    
    # Summera alla delincitament (rowtotal med missing-hantering)
    inc_cols = [c for c in df.columns if c.startswith('inc_ait_') or c.startswith('inc_aif_')]
    df['inc_inter'] = df[inc_cols].sum(axis=1, skipna=True)
    
    return df


def apply_cemi4_correction(
    df: pd.DataFrame,
    adj_max_cemi4: float = BASELINE_ADJ_MAX_CEMI4,
) -> pd.DataFrame:
    """
    Applicerar CEMI4-korrigering på kvalitetsincitamentet.
    
    Om CEMI4 försämras (obs > norm) och incitamentet är positivt,
    eller om CEMI4 förbättras (obs < norm) och incitamentet är negativt,
    reduceras incitamentet med upp till adj_max_cemi4 (default 25%).
    
    Args:
        df: DataFrame med inc_inter, cemi4_norm, cemi4_obs
        adj_max_cemi4: Max CEMI4-korrigeringsfaktor (default 0.25)
        
    Returns:
        DataFrame med inter_incentive_a (efter CEMI4-justering)
    """
    df = df.copy()
    
    df['cemi4_diff'] = df['cemi4_norm'] - df['cemi4_obs']
    df['cemi4_adj_factor'] = df['cemi4_diff'].abs().clip(upper=adj_max_cemi4)
    
    # Starta med okorrigerat värde
    df['inter_incentive_a'] = df['inc_inter']
    
    # Applicera korrigering när tecken inte matchar
    # (försämrad CEMI4 med positivt incitament, eller förbättrad CEMI4 med negativt incitament)
    mask = (
        ((df['cemi4_diff'] < 0) & (df['inc_inter'] > 0)) |
        ((df['cemi4_diff'] > 0) & (df['inc_inter'] < 0))
    )
    df.loc[mask, 'inter_incentive_a'] = (
        df.loc[mask, 'inc_inter'] * (1 - df.loc[mask, 'cemi4_adj_factor'])
    )
    
    return df


def calculate_netloss_incentive(
    df: pd.DataFrame,
    k_nf: Optional[Dict[int, float]] = None,
    sharing_netloss: float = BASELINE_SHARING_NETLOSS,
) -> pd.DataFrame:
    """
    Beräknar nätförlustincitament.
    
    Formel:
        loss_incentive = sharing * (nf_norm - nf_obs) * k_nf * e_in
    
    Args:
        df: DataFrame med nf_norm, nf_obs, e_in, year
        k_nf: Nätförlustkostnad per år (None = baseline)
        sharing_netloss: Delningsfaktor (default 0.75)
        
    Returns:
        DataFrame med k_nf, loss_incentive_a
    """
    df = df.copy()
    
    # Använd baseline om ej angivet
    k_nf = k_nf if k_nf is not None else BASELINE_K_NF
    
    df['k_nf'] = df['year'].map(k_nf)
    df['loss_incentive_a'] = (
        sharing_netloss * (df['nf_norm'] - df['nf_obs']) * df['k_nf'] * df['e_in']
    )
    
    return df


def calculate_utilization_incentive(df: pd.DataFrame) -> pd.DataFrame:
    """
    Beräknar belastningsincitament.
    
    Formel:
        util_incentive = (ug_obs - ug_norm) * k_upstream
    
    Notera: Högre utnyttjning (obs > norm) ger positivt incitament.
    
    Args:
        df: DataFrame med ug_norm, ug_obs, k_upstream
        
    Returns:
        DataFrame med util_incentive_a
    """
    df = df.copy()
    
    df['util_incentive_a'] = (df['ug_obs'] - df['ug_norm']) * df['k_upstream']
    
    return df


def apply_caps(
    df: pd.DataFrame,
    ret_period_col: str = 'ret_period',
    adj_max_agg: float = BASELINE_ADJ_MAX_AGG,
) -> pd.DataFrame:
    """
    Applicerar 1/3-begränsning på incitament.
    
    1. Varje incitament begränsas individuellt till +/- max_adj
    2. Summan begränsas också till +/- max_adj
    
    Args:
        df: DataFrame med inter_incentive_a, loss_incentive_a, util_incentive_a, ret_period
        ret_period_col: Kolumnnamn för periodens avkastning (kr)
        adj_max_agg: Max andel av avkastning (default 1/3)
        
    Returns:
        DataFrame med inter_incentive, loss_incentive, util_incentive, incentive_total_year
    """
    df = df.copy()
    
    # Beräkna max justering (andel av avkastning)
    df['max_adj'] = adj_max_agg * df[ret_period_col]
    
    # Begränsa varje incitament individuellt
    for inc_type in ['inter', 'loss', 'util']:
        src_col = f'{inc_type}_incentive_a'
        dst_col = f'{inc_type}_incentive'
        
        df[dst_col] = df[src_col].clip(lower=-df['max_adj'], upper=df['max_adj'])
    
    # Summera och begränsa totalen
    df['incentive_total_year'] = (
        df['inter_incentive'] + df['loss_incentive'] + df['util_incentive']
    )
    df['incentive_total_year'] = df['incentive_total_year'].clip(
        lower=-df['max_adj'], upper=df['max_adj']
    )
    
    return df


def aggregate_period_totals(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregerar incitament över 4-årsperioden per reid.
    
    Args:
        df: DataFrame med reid, year, och årliga incitament
        
    Returns:
        DataFrame med periodsummor (kolumner läggs till på alla rader)
    """
    df = df.copy()
    
    # Beräkna periodsummor per reid
    period_sums = df.groupby('reid').agg({
        'incentive_total_year': 'sum',
        'inter_incentive': 'sum',
        'loss_incentive': 'sum',
        'util_incentive': 'sum',
    }).rename(columns={
        'incentive_total_year': 'incentive_total',
        'inter_incentive': 'inter_incentive_sum',
        'loss_incentive': 'loss_incentive_sum',
        'util_incentive': 'util_incentive_sum',
    })
    
    # Merge tillbaka till original (alla rader får samma periodsumma)
    df = df.merge(period_sums, on='reid', how='left')
    
    return df


def set_missing_data_to_nan(df: pd.DataFrame) -> pd.DataFrame:
    """
    Sätter alla incitamentvärden till NaN för REIds med saknad data.
    
    Args:
        df: DataFrame med reid och incitamentkolumner
        
    Returns:
        DataFrame med NaN för MISSING_DATA_IDS
    """
    df = df.copy()
    
    incentive_cols = [c for c in df.columns if 'incentive' in c]
    
    mask = df['reid'].isin(MISSING_DATA_IDS)
    df.loc[mask, incentive_cols] = np.nan
    
    return df


def calculate_all_incentives(
    df: pd.DataFrame,
    ret_period_col: str = 'ret_period',
    # Parametrar (None = använd baseline)
    kpi: Optional[Dict[int, float]] = None,
    k_nf: Optional[Dict[int, float]] = None,
    sharing_netloss: Optional[float] = None,
    adj_max_agg: Optional[float] = None,
    adj_max_cemi4: Optional[float] = None,
    ait_costs: Optional[Dict[Tuple[str, int], float]] = None,
    aif_costs: Optional[Dict[Tuple[str, int], float]] = None,
    # Aktivera/inaktivera incitament
    enable_quality: bool = True,
    enable_netloss: bool = True,
    enable_load: bool = True,
) -> pd.DataFrame:
    """
    Kör hela incitamentberäkningskedjan.
    
    Args:
        df: DataFrame med all input-data (från all_adjust_vars.csv)
            Måste innehålla: reid, year, och alla norm/obs-variabler
        ret_period_col: Kolumnnamn för periodens avkastning (kr)
        
        # Parametrar (None = använd baseline från incentive_parameters.py)
        kpi: KPI per år
        k_nf: Nätförlustkostnad per år
        sharing_netloss: Delningsfaktor nätförlust
        adj_max_agg: Max aggregerat incitament (andel av avkastning)
        adj_max_cemi4: Max CEMI4-korrigeringsfaktor
        ait_costs: AIT-kostnader per (ann, sni)
        aif_costs: AIF-kostnader per (ann, sni)
        
        # Aktivera/inaktivera
        enable_quality: Aktivera kvalitetsincitament (default True)
        enable_netloss: Aktivera nätförlustincitament (default True)
        enable_load: Aktivera belastningsincitament (default True)
        
    Returns:
        DataFrame med alla beräknade incitament
    """
    # Sätt defaults från baseline
    if sharing_netloss is None:
        sharing_netloss = BASELINE_SHARING_NETLOSS
    if adj_max_agg is None:
        adj_max_agg = BASELINE_ADJ_MAX_AGG
    if adj_max_cemi4 is None:
        adj_max_cemi4 = BASELINE_ADJ_MAX_CEMI4
    
    # Steg 1: Kvalitetsincitament (AIT/AIF)
    if enable_quality:
        df = calculate_interruption_incentives(df, kpi=kpi, ait_costs=ait_costs, aif_costs=aif_costs)
        df = apply_cemi4_correction(df, adj_max_cemi4=adj_max_cemi4)
    else:
        df = df.copy()
        df['inc_inter'] = 0.0
        df['inter_incentive_a'] = 0.0
    
    # Steg 2: Nätförlustincitament
    if enable_netloss:
        df = calculate_netloss_incentive(df, k_nf=k_nf, sharing_netloss=sharing_netloss)
    else:
        df['loss_incentive_a'] = 0.0
    
    # Steg 3: Belastningsincitament
    if enable_load:
        df = calculate_utilization_incentive(df)
    else:
        df['util_incentive_a'] = 0.0
    
    # Steg 4: Applicera begränsningar
    df = apply_caps(df, ret_period_col, adj_max_agg=adj_max_agg)
    
    # Steg 5: Aggregera periodsummor
    df = aggregate_period_totals(df)
    
    # Steg 6: Sätt saknad data till NaN
    df = set_missing_data_to_nan(df)
    
    return df


def calculate_incentives_summary(
    df: pd.DataFrame,
    ret_period_col: str = 'ret_period',
    **kwargs,
) -> pd.DataFrame:
    """
    Beräknar incitamentsummering per företag (en rad per reid).
    
    Args:
        df: DataFrame med all input-data
        ret_period_col: Kolumnnamn för periodens avkastning
        **kwargs: Parametrar som skickas till calculate_all_incentives
        
    Returns:
        DataFrame med en rad per reid, kolumner:
            - reid
            - quality_incentive_total (tkr)
            - network_loss_incentive_total (tkr)
            - load_incentive_total (tkr)
            - incentive_adjustment_total (tkr)
            - Missing_Incentive_Data (bool)
    """
    # Kör fullständig beräkning
    df_calc = calculate_all_incentives(df, ret_period_col, **kwargs)
    
    # Extrahera en rad per reid (periodsummor är samma på alla rader)
    df_summary = df_calc.groupby('reid').first().reset_index()[[
        'reid',
        'inter_incentive_sum',
        'loss_incentive_sum', 
        'util_incentive_sum',
        'incentive_total',
    ]]
    
    # Konvertera från kr till tkr
    for col in ['inter_incentive_sum', 'loss_incentive_sum', 'util_incentive_sum', 'incentive_total']:
        df_summary[col] = df_summary[col] / 1000
    
    # Rename to canonical English column names
    from config.column_names import (
        COL_QUALITY_INCENTIVE, COL_NETLOSS_INCENTIVE,
        COL_LOAD_INCENTIVE, COL_INCENTIVE_TOTAL,
    )
    df_summary = df_summary.rename(columns={
        'inter_incentive_sum': COL_QUALITY_INCENTIVE,
        'loss_incentive_sum': COL_NETLOSS_INCENTIVE,
        'util_incentive_sum': COL_LOAD_INCENTIVE,
        'incentive_total': COL_INCENTIVE_TOTAL,
    })
    
    # Flagga för saknad data
    df_summary['Missing_Incentive_Data'] = df_summary['reid'].isin(MISSING_DATA_IDS)
    
    return df_summary
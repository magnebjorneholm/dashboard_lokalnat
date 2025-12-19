"""
calculations/incentive_calculations.py

Berakningar for kvalitets- och natincitament enligt Bilaga 4 (Ei).
Implementerar logiken fran 3_functions.do.

Tre incitamenttyper:
1. Kvalitetsincitamentet (inter_incentive) - AIT/AIF-baserat
2. Natforlustincitamentet (loss_incentive) - natforlust vs norm
3. Belastningsincitamentet (util_incentive) - utnyttjningsgrad vs norm
"""

import pandas as pd
import numpy as np
from typing import Optional

from .incentive_parameters import (
    KPI, K_NF, ADJ_MAX_AGG, ADJ_MAX_CEMI4, SHARING_NETLOSS,
    AIT_COSTS, AIF_COSTS, MISSING_DATA_IDS
)


def calculate_interruption_incentives(df: pd.DataFrame) -> pd.DataFrame:
    """
    Beraknar kvalitetsincitament (AIT/AIF) per rad.
    
    Formel per indikator/kundtyp:
        inc = (norm - obs) * kostnad * ame * kpi
    
    Args:
        df: DataFrame med kolumner:
            - year
            - ait_{a,o}_{1-6}_{norm,obs}
            - aif_{a,o}_{1-6}_{norm,obs}
            - ame_{1-6}
            
    Returns:
        DataFrame med nya kolumner: inc_ait_*, inc_aif_*, inc_inter
    """
    df = df.copy()
    
    # Satt KPI per ar
    df['kpi'] = df['year'].map(KPI)
    
    # Berakna delincitament per typ/ann/sni
    for ind_type in ['ait', 'aif']:
        costs = AIT_COSTS if ind_type == 'ait' else AIF_COSTS
        
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


def apply_cemi4_correction(df: pd.DataFrame) -> pd.DataFrame:
    """
    Applicerar CEMI4-korrigering pa kvalitetsincitamentet.
    
    Om CEMI4 forsamras (obs > norm) och incitamentet ar positivt,
    eller om CEMI4 forbattras (obs < norm) och incitamentet ar negativt,
    reduceras incitamentet med upp till 25%.
    
    Args:
        df: DataFrame med inc_inter, cemi4_norm, cemi4_obs
        
    Returns:
        DataFrame med inter_incentive_a (efter CEMI4-justering)
    """
    df = df.copy()
    
    df['cemi4_diff'] = df['cemi4_norm'] - df['cemi4_obs']
    df['cemi4_adj_factor'] = df['cemi4_diff'].abs().clip(upper=ADJ_MAX_CEMI4)
    
    # Starta med okorrigerat varde
    df['inter_incentive_a'] = df['inc_inter']
    
    # Applicera korrigering nar tecken inte matchar
    # (forsamrad CEMI4 med positivt incitament, eller forbattrad CEMI4 med negativt incitament)
    mask = (
        ((df['cemi4_diff'] < 0) & (df['inc_inter'] > 0)) |
        ((df['cemi4_diff'] > 0) & (df['inc_inter'] < 0))
    )
    df.loc[mask, 'inter_incentive_a'] = (
        df.loc[mask, 'inc_inter'] * (1 - df.loc[mask, 'cemi4_adj_factor'])
    )
    
    return df


def calculate_netloss_incentive(df: pd.DataFrame) -> pd.DataFrame:
    """
    Beraknar natforlustincitament.
    
    Formel:
        loss_incentive = sharing * (nf_norm - nf_obs) * k_nf * e_in
    
    Args:
        df: DataFrame med nf_norm, nf_obs, e_in, year
        
    Returns:
        DataFrame med k_nf, loss_incentive_a
    """
    df = df.copy()
    
    df['k_nf'] = df['year'].map(K_NF)
    df['loss_incentive_a'] = (
        SHARING_NETLOSS * (df['nf_norm'] - df['nf_obs']) * df['k_nf'] * df['e_in']
    )
    
    return df


def calculate_utilization_incentive(df: pd.DataFrame) -> pd.DataFrame:
    """
    Beraknar belastningsincitament.
    
    Formel:
        util_incentive = (ug_obs - ug_norm) * k_upstream
    
    Notera: Hogre utnyttjning (obs > norm) ger positivt incitament.
    
    Args:
        df: DataFrame med ug_norm, ug_obs, k_upstream
        
    Returns:
        DataFrame med util_incentive_a
    """
    df = df.copy()
    
    df['util_incentive_a'] = (df['ug_obs'] - df['ug_norm']) * df['k_upstream']
    
    return df


def apply_caps(df: pd.DataFrame, ret_period_col: str = 'ret_period') -> pd.DataFrame:
    """
    Applicerar 1/3-begransning pa incitament.
    
    1. Varje incitament begransas individuellt till +/- max_adj
    2. Summan begransas ocksa till +/- max_adj
    
    Args:
        df: DataFrame med inter_incentive_a, loss_incentive_a, util_incentive_a, ret_period
        ret_period_col: Kolumnnamn for periodens avkastning (kr)
        
    Returns:
        DataFrame med inter_incentive, loss_incentive, util_incentive, incentive_total_year
    """
    df = df.copy()
    
    # Berakna max justering (1/3 av avkastning)
    df['max_adj'] = ADJ_MAX_AGG * df[ret_period_col]
    
    # Begrans varje incitament individuellt
    for inc_type in ['inter', 'loss', 'util']:
        src_col = f'{inc_type}_incentive_a'
        dst_col = f'{inc_type}_incentive'
        
        df[dst_col] = df[src_col].clip(lower=-df['max_adj'], upper=df['max_adj'])
    
    # Summera och begrans totalen
    df['incentive_total_year'] = (
        df['inter_incentive'] + df['loss_incentive'] + df['util_incentive']
    )
    df['incentive_total_year'] = df['incentive_total_year'].clip(
        lower=-df['max_adj'], upper=df['max_adj']
    )
    
    return df


def aggregate_period_totals(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregerar incitament over 4-arsperioden per reid.
    
    Args:
        df: DataFrame med reid, year, och arliga incitament
        
    Returns:
        DataFrame med periodsummor (kolumner laggs till pa alla rader)
    """
    df = df.copy()
    
    # Berakna periodsummor per reid
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
    
    # Merge tillbaka till original (alla rader far samma periodsumma)
    df = df.merge(period_sums, on='reid', how='left')
    
    return df


def set_missing_data_to_nan(df: pd.DataFrame) -> pd.DataFrame:
    """
    Sattar alla incitamentvarden till NaN for REIds med saknad data.
    
    Args:
        df: DataFrame med reid och incitamentkolumner
        
    Returns:
        DataFrame med NaN for MISSING_DATA_IDS
    """
    df = df.copy()
    
    incentive_cols = [c for c in df.columns if 'incentive' in c]
    
    mask = df['reid'].isin(MISSING_DATA_IDS)
    df.loc[mask, incentive_cols] = np.nan
    
    return df


def calculate_all_incentives(
    df: pd.DataFrame,
    ret_period_col: str = 'ret_period'
) -> pd.DataFrame:
    """
    Kor hela incitamentberakningskedjan.
    
    Args:
        df: DataFrame med all input-data (fran all_adjust_vars.csv)
            Maste innehalla: reid, year, och alla norm/obs-variabler
        ret_period_col: Kolumnnamn for periodens avkastning (kr)
        
    Returns:
        DataFrame med alla beraknade incitament
    """
    # Steg 1: Kvalitetsincitament (AIT/AIF)
    df = calculate_interruption_incentives(df)
    
    # Steg 2: CEMI4-korrigering
    df = apply_cemi4_correction(df)
    
    # Steg 3: Natforlustincitament
    df = calculate_netloss_incentive(df)
    
    # Steg 4: Belastningsincitament
    df = calculate_utilization_incentive(df)
    
    # Steg 5: Applicera begransningar
    df = apply_caps(df, ret_period_col)
    
    # Steg 6: Aggregera periodsummor
    df = aggregate_period_totals(df)
    
    # Steg 7: Satt saknad data till NaN
    df = set_missing_data_to_nan(df)
    
    return df


def calculate_incentives_summary(
    df: pd.DataFrame,
    ret_period_col: str = 'ret_period'
) -> pd.DataFrame:
    """
    Beraknar incitamentsummering per foretag (en rad per reid).
    
    Args:
        df: DataFrame med all input-data
        ret_period_col: Kolumnnamn for periodens avkastning
        
    Returns:
        DataFrame med en rad per reid, kolumner:
            - reid
            - Kvalitetsjustering_Total (tkr)
            - Natforlustjustering_Total (tkr)
            - Belastningsjustering_Total (tkr)
            - Incitamentjustering_Total (tkr)
            - Missing_Incentive_Data (bool)
    """
    # Kor fullstandig berakning
    df_calc = calculate_all_incentives(df, ret_period_col)
    
    # Extrahera en rad per reid (periodsummor ar samma pa alla rader)
    df_summary = df_calc.groupby('reid').first().reset_index()[[
        'reid',
        'inter_incentive_sum',
        'loss_incentive_sum', 
        'util_incentive_sum',
        'incentive_total',
    ]]
    
    # Konvertera fran kr till tkr
    for col in ['inter_incentive_sum', 'loss_incentive_sum', 'util_incentive_sum', 'incentive_total']:
        df_summary[col] = df_summary[col] / 1000
    
    # Rename till svenska
    df_summary = df_summary.rename(columns={
        'inter_incentive_sum': 'Kvalitetsjustering_Total',
        'loss_incentive_sum': 'Natforlustjustering_Total',
        'util_incentive_sum': 'Belastningsjustering_Total',
        'incentive_total': 'Incitamentjustering_Total',
    })
    
    # Flagga for saknad data
    df_summary['Missing_Incentive_Data'] = df_summary['reid'].isin(MISSING_DATA_IDS)
    
    return df_summary
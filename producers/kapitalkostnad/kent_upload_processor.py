"""
kent_upload_processor.py - Läs CAPEX från uppladdad KENT-fil
=============================================================

Förenklad version av capbase_prep.py för att extrahera CAPEX.
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional


DEPRECIATION_PARAMS = {
    1: {'ekdep': 50*2, 'maxdep': 62*2}, 2: {'ekdep': 50*2, 'maxdep': 62*2},
    3: {'ekdep': 50*2, 'maxdep': 62*2}, 4: {'ekdep': 50*2, 'maxdep': 62*2},
    5: {'ekdep': 10*2, 'maxdep': 12*2}, 6: {'ekdep': 30*2, 'maxdep': 37*2},
    7: {'ekdep': 40*2, 'maxdep': 50*2}, 8: {'ekdep': 60*2, 'maxdep': 75*2},
    9: {'ekdep': 40*2, 'maxdep': 50*2}, 10: {'ekdep': 40*2, 'maxdep': 50*2},
    11: {'ekdep': 50*2, 'maxdep': 62*2}, 12: {'ekdep': 10*2, 'maxdep': 12*2},
    13: {'ekdep': 40*2, 'maxdep': 50*2}, 14: {'ekdep': 40*2, 'maxdep': 50*2},
    15: {'ekdep': 15*2, 'maxdep': 18*2}, 16: {'ekdep': 40*2, 'maxdep': 50*2},
    17: {'ekdep': 50*2, 'maxdep': 62*2},
}


def read_kent_excel(file_obj) -> Dict[str, pd.DataFrame]:
    """Läser ark från KENT Excel-mall."""
    
    def read_normvarde(fp):
        df = pd.read_excel(fp, sheet_name='Normvärde', header=1, engine='openpyxl')
        df.columns = df.columns.str.strip().str.replace('\n', ' ').str.replace('  ', ' ')
        
        mapping = {
            'Anl.-kategori': 'anl_kat', 'Kod': 'kod', 'Typ av anläggning': 'anl_typ',
            'Antal': 'antal', 'Rådighet': 'rådighet',
            'Ursprungligen tagen i bruk': 'år_från',
            'Tidsperiod för ursprunglig tagen i bruk Från': 'tidsperiod_från',
            'Till': 'tidsperiod_till', 'År saknas (Ja eller blank)': 'år_saknas',
            'NUAV (kr)': 'nuav', 'NUAV': 'nuav'
        }
        
        avail = {}
        for kent, std in mapping.items():
            match = [c for c in df.columns if kent in c]
            if match:
                avail[match[0]] = std
        
        df = df.rename(columns=avail)
        df = df[df['kod'].notna()].copy()
        df['capbase_existing'] = 1
        df['metod'] = 'normvärde'
        return df
    
    def read_ovriga(fp):
        df = pd.read_excel(fp, sheet_name='Övriga värderingsmetoder', header=1, engine='openpyxl')
        df.columns = df.columns.str.strip().str.replace('\n', ' ').str.replace('  ', ' ')
        
        mapping = {
            'Ansk': 'ansk', 'Bokf': 'bokf', 'Annat': 'annat',
            'Anl.kategori': 'anl_kat', 'Typ av anläggning': 'anl_typ',
            'Antal': 'antal', 'Ursprungligen tagen i bruk': 'år_från',
            'Tidsperiod för ursprunglig tagen i bruk Från': 'tidsperiod_från',
            'Till': 'tidsperiod_till', 'År saknas (Ja eller blank)': 'år_saknas',
            'Rådighet': 'rådighet', 'NUAV 2022 (kr)': 'nuav', 'NUAV (2022)': 'nuav'
        }
        
        avail = {}
        for kent, std in mapping.items():
            match = [c for c in df.columns if kent in c]
            if match:
                avail[match[0]] = std
        
        df = df.rename(columns=avail)
        if 'anl_kat' in df.columns:
            df = df[df['anl_kat'].notna()].copy()
        
        df['metod'] = 'unknown'
        if 'ansk' in df.columns:
            df.loc[df['ansk'].notna(), 'metod'] = 'anskaffningsvärde'
        if 'bokf' in df.columns:
            df.loc[df['bokf'].notna(), 'metod'] = 'bokförtvärde'
        if 'annat' in df.columns:
            df.loc[df['annat'].notna(), 'metod'] = 'annatskäligtvärde'
        
        df['capbase_existing'] = 1
        return df
    
    result = {}
    result['normvarde'] = read_normvarde(file_obj)
    result['ovriga'] = read_ovriga(file_obj)
    
    return result


def process_kent_components(df: pd.DataFrame) -> pd.DataFrame:
    """Processar komponenter från KENT."""
    df = df.copy()
    
    if 'anl_kat' in df.columns:
        df['cat'] = df['anl_kat'].str.lower()
    if 'anl_typ' in df.columns:
        df['subcat'] = df['anl_typ'].str.lower()
    
    df['cat_encode'] = df['cat'].factorize()[0] + 1
    df['subcat_encode'] = df['subcat'].factorize()[0] + 1 if 'subcat' in df.columns else 1
    
    for code, params in DEPRECIATION_PARAMS.items():
        mask = df['cat_encode'] == code
        df.loc[mask, 'ekdep'] = params['ekdep']
        df.loc[mask, 'maxdep'] = params['maxdep']
    
    if 'rådighet' in df.columns:
        df['owned'] = df['rådighet'].apply(
            lambda x: 1 if str(x).strip().lower() == 'ägd' else 0
        )
    
    df['nuav_2022'] = 0.0
    if 'metod' in df.columns:
        mask = df['metod'] == 'normvärde'
        if 'nuav' in df.columns:
            df.loc[mask, 'nuav_2022'] = df.loc[mask, 'nuav']
        
        mask = df['metod'] == 'anskaffningsvärde'
        if 'nuav' in df.columns:
            df.loc[mask, 'nuav_2022'] = df.loc[mask, 'nuav']
        
        mask = df['metod'] == 'bokförtvärde'
        if 'nuav' in df.columns:
            df.loc[mask, 'nuav_2022'] = df.loc[mask, 'nuav']
    
    df['id_network'] = 1
    df['id_component'] = range(1, len(df) + 1)
    df['time_from'] = 220
    df['time_invest'] = pd.NA
    df['invest'] = pd.NA
    
    return df


def extract_capex_from_kent(file_obj, dmu_id: Optional[int] = None) -> pd.DataFrame:
    """
    Huvudfunktion: Extraherar CAPEX från KENT-fil.
    
    Args:
        file_obj: Uppladdad KENT Excel-fil
        dmu_id: DMU-id (oanvänd i denna version)
    
    Returns:
        DataFrame redo för kent_pipeline
    """
    kent_data = read_kent_excel(file_obj)
    
    all_components = []
    if not kent_data['normvarde'].empty:
        all_components.append(kent_data['normvarde'])
    if not kent_data['ovriga'].empty:
        all_components.append(kent_data['ovriga'])
    
    if not all_components:
        raise ValueError("Ingen kapitalbas hittades i KENT-filen")
    
    df = pd.concat(all_components, ignore_index=True)
    df = process_kent_components(df)
    
    return df
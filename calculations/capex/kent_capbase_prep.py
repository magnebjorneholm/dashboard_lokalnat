"""
calculations/kent_capbase_prep.py

Konverterar uppladdad KENT Excel-fil till capbase_a format (Steg 1-4).
capbase_a kan sedan anvandas i kent_calculations.py (Steg 5-8).

Fixar i v1.1:
- Hanterar duplicerade NUAV-kolumner i "Ovriga varderingsmetoder"
- reset_index(drop=True) innan concat for att undvika index-konflikter
- Robust kolumnmappning som prioriterar "NUAV 2022" framfor andra NUAV-kolumner
- Merge for livslangder istallet for df.loc (undviker pandas index-varningar)
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Any
import warnings

from config.asset_categories import BASELINE_LIFETIMES


def read_kent_excel(file_obj) -> Dict[str, pd.DataFrame]:
    """
    Laser alla relevanta ark fran KENT Excel-mallen.
    
    Args:
        file_obj: Filepath eller file-like object (BytesIO)
    
    Returns:
        Dictionary med DataFrames: normvarde, ovriga, investeringar
    """
    
    def _clean_columns(df: pd.DataFrame) -> pd.DataFrame:
        """Rensa kolumnnamn fran whitespace och radbrytningar."""
        df.columns = df.columns.str.strip().str.replace('\n', ' ').str.replace('  ', ' ')
        return df
    
    def _find_matching_column(df_columns, search_term: str) -> Optional[str]:
        """Hitta forsta kolumn som innehaller sokterm."""
        for col in df_columns:
            if search_term in col:
                return col
        return None
    
    def read_normvarde(filepath) -> pd.DataFrame:
        try:
            df = pd.read_excel(filepath, sheet_name='Normvärde', header=1, engine='openpyxl')
        except Exception:
            return pd.DataFrame()
        
        df = _clean_columns(df)
        
        column_mapping = {
            'Anl.-kategori': 'anl_kat',
            'Kod': 'kod',
            'Typ av anläggning': 'anl_typ',
            'Antal': 'antal',
            'Rådighet': 'radighet',
            'Ursprungligen tagen i bruk': 'ar_fran',
            'Tidsperiod för ursprunglig tagen i bruk Från': 'tidsperiod_fran',
            'Till': 'tidsperiod_till',
            'År saknas': 'ar_saknas',
            'NUAV': 'nuav'
        }
        
        rename_dict = {}
        used_cols = set()
        for kent_name, std_name in column_mapping.items():
            match = _find_matching_column([c for c in df.columns if c not in used_cols], kent_name)
            if match:
                rename_dict[match] = std_name
                used_cols.add(match)
        
        df = df.rename(columns=rename_dict)
        
        if 'kod' in df.columns:
            df = df[df['kod'].notna()].copy()
        
        df = df.reset_index(drop=True)
        df['capbase_existing'] = 1
        df['metod'] = 'normvarde'
        return df
    
    def read_ovriga_metoder(filepath) -> pd.DataFrame:
        try:
            df = pd.read_excel(filepath, sheet_name='Övriga värderingsmetoder', header=1, engine='openpyxl')
        except Exception:
            return pd.DataFrame()
        
        df = _clean_columns(df)
        
        # Hitta NUAV-kolumn (prioritera "NUAV 2022")
        nuav_cols = [col for col in df.columns if 'NUAV' in col.upper()]
        nuav_target = None
        for col in nuav_cols:
            if '2022' in col:
                nuav_target = col
                break
        if not nuav_target and nuav_cols:
            nuav_target = nuav_cols[-1]  # Sista NUAV-kolumnen som fallback
        
        column_mapping = {
            'Ansk': 'ansk',
            'Bokf': 'bokf',
            'Annat': 'annat',
            'Anl.kategori': 'anl_kat',
            'Typ av anläggning': 'anl_typ',
            'Antal': 'antal',
            'Ursprungligen tagen i bruk': 'ar_fran',
            'Tidsperiod för ursprunglig tagen i bruk Från': 'tidsperiod_fran',
            'Till': 'tidsperiod_till',
            'År saknas': 'ar_saknas',
            'Rådighet': 'radighet',
        }
        
        rename_dict = {}
        used_cols = set()
        for kent_name, std_name in column_mapping.items():
            match = _find_matching_column([c for c in df.columns if c not in used_cols], kent_name)
            if match:
                rename_dict[match] = std_name
                used_cols.add(match)
        
        if nuav_target:
            rename_dict[nuav_target] = 'nuav'
        
        df = df.rename(columns=rename_dict)
        
        # Ta bort duplicerade kolumner (behall sista)
        df = df.loc[:, ~df.columns.duplicated(keep='last')]
        
        if 'anl_kat' in df.columns:
            df = df[df['anl_kat'].notna()].copy()
        
        df = df.reset_index(drop=True)
        
        df['metod'] = 'unknown'
        if 'ansk' in df.columns:
            df.loc[df['ansk'].notna(), 'metod'] = 'anskaffningsvarde'
        if 'bokf' in df.columns:
            df.loc[df['bokf'].notna(), 'metod'] = 'bokfortvarde'
        if 'annat' in df.columns:
            df.loc[df['annat'].notna(), 'metod'] = 'annatskaligtavarde'
        
        df['capbase_existing'] = 1
        return df
    
    def read_investeringar(filepath) -> pd.DataFrame:
        try:
            df = pd.read_excel(filepath, sheet_name='Investeringar_Utrangeringar', header=1, engine='openpyxl')
        except Exception:
            return pd.DataFrame()
        
        df = _clean_columns(df)
        
        column_mapping = {
            'Investering / Utrangering': 'typavforandring',
            'Halvår': 'halvar',
            'Anl.kategori': 'anl_kat',
            'Typ av anläggning': 'anl_typ',
            'Antal': 'antal',
            'Ursprungligen tagen i bruk': 'ar_fran',
            'Totalt i kronor': 'varde',
            'Totalt': 'varde'
        }
        
        rename_dict = {}
        used_cols = set()
        for kent_name, std_name in column_mapping.items():
            match = _find_matching_column([c for c in df.columns if c not in used_cols], kent_name)
            if match:
                rename_dict[match] = std_name
                used_cols.add(match)
        
        df = df.rename(columns=rename_dict)
        
        if 'typavforandring' in df.columns:
            df = df[df['typavforandring'].notna()].copy()
        
        df = df.reset_index(drop=True)
        df['capbase_existing'] = 0
        df['metod'] = 'future_invest'
        return df
    
    result = {
        'normvarde': read_normvarde(file_obj),
        'ovriga': read_ovriga_metoder(file_obj),
        'investeringar': read_investeringar(file_obj)
    }
    
    if result['normvarde'].empty and result['ovriga'].empty:
        warnings.warn("Ingen befintlig kapitalbas hittades i KENT-filen")
    
    return result


# Mappning fran KENT-kategoritexter till cat_encode
CATEGORY_MAPPING = {
    'transformator': 17,
    'mätare': 12,
    'kabelskåp': 6,
    'nätstation': 13,
    'luftledning': 9,
    'kabel': 3,
    'it-system': 5,
    'it system': 5,
    'kontrollutrustning': 15,
    'styr': 15,
    'ställverk': 16,
    'shuntreaktor': 14,
    'markarbeten': 11,
    'byggnad': 11,
    'annan ledning': 3,
    'jordkabel': 3,
}


def get_category_encode(category_text: str) -> int:
    """Mappar kategoritext till cat_encode."""
    if pd.isna(category_text):
        return 17
    
    cat_lower = str(category_text).strip().lower()
    
    for key, code in CATEGORY_MAPPING.items():
        if key in cat_lower:
            return code
    
    return 17


def year_to_time_code(year) -> Optional[int]:
    """Konverterar ar till time_code (halvarsperioder)."""
    if pd.isna(year):
        return None
    try:
        year_f = float(year)
        return int((year_f - 1910) * 2 + 1)
    except (ValueError, TypeError):
        return None


def halvar_to_time_code(halvar_str) -> Optional[int]:
    """Konverterar halvarstring (ex: '2024 H1') till time_code."""
    if pd.isna(halvar_str):
        return None
    
    try:
        halvar_str = str(halvar_str).strip()
        parts = halvar_str.split()
        year = int(parts[0])
        h = 1 if 'H1' in halvar_str.upper() or (len(parts) > 1 and '1' in parts[-1]) else 2
        return (year - 1910) * 2 + h
    except (ValueError, IndexError):
        return None


def create_lifetime_lookup(lifetime_adjustments: Optional[Dict[int, Dict[str, int]]] = None) -> pd.DataFrame:
    """Skapar lookup-tabell for livslangder per kategori."""
    rows = []
    for cat_code in range(1, 18):
        baseline = BASELINE_LIFETIMES.get(cat_code, {'ekdep': 80, 'maxdep': 100})
        
        if lifetime_adjustments and cat_code in lifetime_adjustments:
            adj = lifetime_adjustments[cat_code]
            ekdep = adj.get('ekdep', baseline['ekdep'])
            maxdep = adj.get('maxdep', baseline['maxdep'])
        else:
            ekdep = baseline['ekdep']
            maxdep = baseline['maxdep']
        
        rows.append({'cat_encode': cat_code, 'ekdep': ekdep, 'maxdep': maxdep})
    
    return pd.DataFrame(rows)


def process_kent_components(
    kent_data: Dict[str, pd.DataFrame],
    lifetime_adjustments: Optional[Dict[int, Dict[str, int]]] = None
) -> pd.DataFrame:
    """Kombinerar och processar alla komponenter fran KENT-data."""
    dfs = []
    
    for key in ['normvarde', 'ovriga', 'investeringar']:
        if not kent_data[key].empty:
            df_copy = kent_data[key].copy().reset_index(drop=True)
            dfs.append(df_copy)
    
    if not dfs:
        raise ValueError("Ingen data att kombinera fran KENT-filen")
    
    df = pd.concat(dfs, ignore_index=True, sort=False)
    
    # Kategori-encoding
    if 'anl_kat' in df.columns:
        df['cat'] = df['anl_kat'].astype(str).str.lower().str.strip()
        df['cat_encode'] = df['cat'].apply(get_category_encode)
    else:
        df['cat'] = 'ovrigt'
        df['cat_encode'] = 17
    
    # Subkategori
    if 'anl_typ' in df.columns:
        df['subcat'] = df['anl_typ'].astype(str).str.lower().str.strip()
        df['subcat_encode'] = pd.factorize(df['subcat'])[0] + 1
    else:
        df['subcat'] = 'unknown'
        df['subcat_encode'] = 1
    
    # Time encoding
    df['time_from'] = None
    if 'ar_fran' in df.columns:
        df['time_from'] = df['ar_fran'].apply(year_to_time_code)
    
    df['time_invest'] = None
    if 'halvar' in df.columns:
        df['time_invest'] = df['halvar'].apply(halvar_to_time_code)
        fill_mask = df['time_from'].isna() & df['time_invest'].notna()
        df.loc[fill_mask, 'time_from'] = df.loc[fill_mask, 'time_invest']
    
    # Radighet
    if 'radighet' in df.columns:
        df['owned'] = df['radighet'].apply(
            lambda x: 1 if str(x).strip().lower() in ['agd', 'ägd', 'owned'] else 0
        )
    else:
        df['owned'] = 1
    
    # NUAV
    df['nuav_2022'] = 0.0
    if 'nuav' in df.columns:
        df['nuav_2022'] = pd.to_numeric(df['nuav'], errors='coerce').fillna(0)
    
    if 'varde' in df.columns:
        invest_mask = df['metod'] == 'future_invest'
        varde_numeric = pd.to_numeric(df['varde'], errors='coerce').fillna(0)
        df.loc[invest_mask, 'nuav_2022'] = varde_numeric[invest_mask]
    
    # Invest sign
    df['invest'] = np.nan
    if 'typavforandring' in df.columns:
        def get_invest_sign(x):
            if pd.isna(x):
                return np.nan
            x_lower = str(x).lower()
            if 'investering' in x_lower:
                return 1.0
            elif 'utrangering' in x_lower:
                return -1.0
            return np.nan
        
        df['invest'] = df['typavforandring'].apply(get_invest_sign)
        sign_mask = df['invest'].notna()
        df.loc[sign_mask, 'nuav_2022'] = df.loc[sign_mask, 'nuav_2022'] * df.loc[sign_mask, 'invest']
    
    # Livslangder via merge
    lifetime_df = create_lifetime_lookup(lifetime_adjustments)
    df = df.merge(lifetime_df, on='cat_encode', how='left')
    df['ekdep'] = df['ekdep'].fillna(80).astype(int)
    df['maxdep'] = df['maxdep'].fillna(100).astype(int)
    
    df = df.reset_index(drop=True)
    df['id_component'] = range(1, len(df) + 1)
    
    return df


def build_capbase_a_from_kent(
    kent_file,
    network_id: int,
    lifetime_adjustments: Optional[Dict[int, Dict[str, int]]] = None
) -> pd.DataFrame:
    """
    Huvudfunktion: Bygger capbase_a fran KENT Excel-fil.
    
    Args:
        kent_file: Filepath eller file-like object (BytesIO)
        network_id: id_network for detta natverk
        lifetime_adjustments: Eventuella livslangdsjusteringar
    
    Returns:
        capbase_a DataFrame redo for steg 5-8
    """
    kent_data = read_kent_excel(kent_file)
    df = process_kent_components(kent_data, lifetime_adjustments)
    df['id_network'] = network_id
    
    required_cols = [
        'id_component', 'id_network', 'time_from', 'time_invest', 
        'capbase_existing', 'ekdep', 'maxdep', 'nuav_2022', 
        'cat_encode', 'invest'
    ]
    extra_cols = ['cat', 'subcat', 'subcat_encode', 'antal', 'metod', 'owned']
    
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Saknade obligatoriska kolumner: {missing}")
    
    available = required_cols + [col for col in extra_cols if col in df.columns]
    capbase_a = df[available].copy().reset_index(drop=True)
    
    validation = validate_capbase_a(capbase_a)
    if not validation['valid']:
        raise ValueError(f"capbase_a validering misslyckades:\n" + "\n".join(validation['errors']))
    
    return capbase_a


def validate_capbase_a(df: pd.DataFrame) -> Dict[str, Any]:
    """Validerar capbase_a."""
    report = {'valid': True, 'errors': [], 'warnings': [], 'info': []}
    
    required = ['id_component', 'time_from', 'capbase_existing', 'ekdep', 
                'maxdep', 'nuav_2022', 'cat_encode', 'id_network']
    
    missing = [col for col in required if col not in df.columns]
    if missing:
        report['valid'] = False
        report['errors'].append(f"Saknade kolumner: {missing}")
        return report
    
    if df['capbase_existing'].notna().sum() > 0:
        if (~df['capbase_existing'].isin([0, 1])).any():
            report['errors'].append("capbase_existing har ogiltiga varden")
            report['valid'] = False
    
    if (df['ekdep'] <= 0).any():
        report['errors'].append("ekdep innehaller icke-positiva varden")
        report['valid'] = False
    
    if (df['maxdep'] <= 0).any():
        report['errors'].append("maxdep innehaller icke-positiva varden")
        report['valid'] = False
    
    existing = df['capbase_existing'] == 1
    problematic = existing & df['time_from'].isna()
    if problematic.any():
        report['warnings'].append(f"{problematic.sum()} befintliga komponenter saknar time_from")
    
    if (df['maxdep'] < df['ekdep']).any():
        report['warnings'].append("Vissa komponenter har maxdep < ekdep")
    
    report['info'].append(f"Totalt {len(df)} komponenter")
    report['info'].append(f"Total NUAV: {df['nuav_2022'].sum()/1e6:.1f} Mkr")
    
    return report


def get_kent_upload_summary(capbase_a: pd.DataFrame) -> Dict[str, Any]:
    """Skapar sammanfattning av uppladdad KENT-data."""
    summary = {
        'n_components': len(capbase_a),
        'n_existing': int((capbase_a['capbase_existing'] == 1).sum()),
        'n_investments': int((capbase_a['capbase_existing'] == 0).sum()),
        'n_categories': int(capbase_a['cat_encode'].nunique()),
        'total_nuav_mkr': float(capbase_a['nuav_2022'].sum() / 1e6),
        'categories': {}
    }
    
    for cat_code in sorted(capbase_a['cat_encode'].unique()):
        mask = capbase_a['cat_encode'] == cat_code
        cat_df = capbase_a[mask]
        cat_name = cat_df['cat'].iloc[0] if 'cat' in cat_df.columns else f"Kategori {cat_code}"
        summary['categories'][int(cat_code)] = {
            'name': str(cat_name),
            'n_components': int(len(cat_df)),
            'nuav_mkr': float(cat_df['nuav_2022'].sum() / 1e6)
        }
    
    return summary
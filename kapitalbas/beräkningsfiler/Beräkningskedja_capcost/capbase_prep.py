"""
capbase_prep.py - Komplett KENT-import och capbase_a-förberedelse (Steg 1-4)

Samlar hela kedjan från KENT Excel-mall till färdig capbase_a.parquet
som är redo för beräkningskedjan (steg 5-9).
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Optional, Tuple
import warnings
import io


# ============================================================================
# STEG 1: LÄS KENT EXCEL
# ============================================================================

def read_kent_excel(file_obj) -> Dict[str, pd.DataFrame]:
    """
    Läser alla relevanta ark från KENT Excel-mallen.
    
    Args:
        file_obj: Uploadad fil-objekt från st.file_uploader eller filepath
    
    Returns:
        Dictionary med DataFrames:
        - 'normvarde': Befintliga komponenter med normvärde
        - 'ovriga': Befintliga komponenter med andra metoder
        - 'investeringar': Planerade investeringar/utrangeringar
        - 'uppslagsvarden': Kategori-mappningar
    """
    
    def read_normvarde(filepath) -> pd.DataFrame:
        df = pd.read_excel(filepath, sheet_name='Normvärde', header=1, engine='openpyxl')
        df.columns = df.columns.str.strip().str.replace('\n', ' ').str.replace('  ', ' ')
        
        column_mapping = {
            'Anl.-kategori': 'anl_kat',
            'Kod': 'kod',
            'Typ av anläggning': 'anl_typ',
            'Antal': 'antal',
            'Rådighet': 'rådighet',
            'Ursprungligen tagen i bruk': 'år_från',
            'Tidsperiod för ursprunglig tagen i bruk Från': 'tidsperiod_från',
            'Till': 'tidsperiod_till',
            'År saknas (Ja eller blank)': 'år_saknas',
            'NUAV (kr)': 'nuav',
            'NUAV': 'nuav'  # Alternativ kolumnnamn
        }
        
        available_cols = {}
        for kent_name, std_name in column_mapping.items():
            matching = [col for col in df.columns if kent_name in col]
            if matching:
                available_cols[matching[0]] = std_name
        
        df = df.rename(columns=available_cols)
        df = df[df['kod'].notna()].copy()
        df['capbase_existing'] = 1
        df['metod'] = 'normvärde'
        return df
    
    def read_ovriga_metoder(filepath) -> pd.DataFrame:
        df = pd.read_excel(filepath, sheet_name='Övriga värderingsmetoder', header=1, engine='openpyxl')
        df.columns = df.columns.str.strip().str.replace('\n', ' ').str.replace('  ', ' ')
        
        column_mapping = {
            'Ansk': 'ansk',
            'Bokf': 'bokf',
            'Annat': 'annat',
            'Anl.kategori': 'anl_kat',
            'Typ av anläggning': 'anl_typ',
            'Antal': 'antal',
            'Ursprungligen tagen i bruk': 'år_från',
            'Tidsperiod för ursprunglig tagen i bruk Från': 'tidsperiod_från',
            'Till': 'tidsperiod_till',
            'År saknas (Ja eller blank)': 'år_saknas',
            'Rådighet': 'rådighet',
            'NUAV 2022 (kr)': 'nuav',
            'NUAV (2022)': 'nuav'  # Alternativ kolumnnamn
        }
        
        available_cols = {}
        for kent_name, std_name in column_mapping.items():
            matching = [col for col in df.columns if kent_name in col]
            if matching:
                available_cols[matching[0]] = std_name
        
        df = df.rename(columns=available_cols)
        
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
    
    def read_investeringar(filepath) -> pd.DataFrame:
        df = pd.read_excel(filepath, sheet_name='Investeringar_Utrangeringar', header=1, engine='openpyxl')
        df.columns = df.columns.str.strip().str.replace('\n', ' ').str.replace('  ', ' ')
        
        column_mapping = {
            'Investering / Utrangering': 'typavförändring',
            'Halvår': 'halvår',
            'Anl.kategori': 'anl_kat',
            'Typ av anläggning': 'anl_typ',
            'Antal': 'antal',
            'Ursprungligen tagen i bruk': 'år_från',
            'Totalt i kronor': 'värde',
            'Totalt': 'värde'  # Alternativ kolumnnamn
        }
        
        available_cols = {}
        for kent_name, std_name in column_mapping.items():
            matching = [col for col in df.columns if kent_name in col]
            if matching:
                available_cols[matching[0]] = std_name
        
        df = df.rename(columns=available_cols)
        
        if 'typavförändring' in df.columns:
            df = df[df['typavförändring'].notna()].copy()
        
        df['capbase_existing'] = 0
        df['metod'] = 'future_invest'
        return df
    
    def read_uppslagsvarden(filepath) -> pd.DataFrame:
        df = pd.read_excel(filepath, sheet_name='Uppslagsvärden', header=1, engine='openpyxl')
        df.columns = df.columns.str.strip().str.replace('\n', ' ').str.replace('  ', ' ')
        
        kat_col = [col for col in df.columns if 'Anläggningskategori' in col]
        typ_col = [col for col in df.columns if 'Typ av anläggning' in col]
        
        if not (kat_col and typ_col):
            raise ValueError("Kunde inte hitta kategori-kolumner i Uppslagsvärden")
        
        result = pd.DataFrame({
            'anläggningskategori': df[kat_col[0]],
            'typ_av_anläggning': df[typ_col[0]]
        })
        
        result = result[result['anläggningskategori'].notna()].copy()
        result = result.drop_duplicates()
        return result
    
    result = {}
    result['normvarde'] = read_normvarde(file_obj)
    result['ovriga'] = read_ovriga_metoder(file_obj)
    result['investeringar'] = read_investeringar(file_obj)
    result['uppslagsvarden'] = read_uppslagsvarden(file_obj)
    
    if result['normvarde'].empty and result['ovriga'].empty:
        warnings.warn("Ingen befintlig kapitalbas hittades i KENT-filen")
    
    return result


# ============================================================================
# STEG 2: SKAPA MAPPNINGAR
# ============================================================================

DEPRECIATION_PARAMS = {
    1: {'ekdep': 50*2, 'maxdep': 62*2},
    2: {'ekdep': 50*2, 'maxdep': 62*2},
    3: {'ekdep': 50*2, 'maxdep': 62*2},
    4: {'ekdep': 50*2, 'maxdep': 62*2},
    5: {'ekdep': 10*2, 'maxdep': 12*2},
    6: {'ekdep': 30*2, 'maxdep': 37*2},
    7: {'ekdep': 40*2, 'maxdep': 50*2},
    8: {'ekdep': 60*2, 'maxdep': 75*2},
    9: {'ekdep': 40*2, 'maxdep': 50*2},
    10: {'ekdep': 40*2, 'maxdep': 50*2},
    11: {'ekdep': 50*2, 'maxdep': 62*2},
    12: {'ekdep': 10*2, 'maxdep': 12*2},
    13: {'ekdep': 40*2, 'maxdep': 50*2},
    14: {'ekdep': 40*2, 'maxdep': 50*2},
    15: {'ekdep': 15*2, 'maxdep': 18*2},
    16: {'ekdep': 40*2, 'maxdep': 50*2},
    17: {'ekdep': 50*2, 'maxdep': 62*2},
}


def create_mappings(kent_data: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
    """Skapar alla mappningar från KENT-data."""
    
    def create_time_frame(start_year: int = 1910, end_year: int = 2030) -> pd.DataFrame:
        years = []
        halvars = []
        
        for year in range(start_year, end_year + 1):
            for h in [1, 2]:
                years.append(year)
                halvars.append(h)
        
        df = pd.DataFrame({'year': years, 'h': halvars})
        df['time'] = (df['year'] - 1910) * 2 + df['h']
        df['time_string'] = df['year'].astype(str) + ' H' + df['h'].astype(str)
        return df
    
    def create_category_encoding(uppslagsvarden_df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        df = uppslagsvarden_df.copy()
        df['anläggningskategori'] = df['anläggningskategori'].str.lower()
        df['typ_av_anläggning'] = df['typ_av_anläggning'].str.lower()
        
        cat_frame = df[['anläggningskategori']].drop_duplicates().copy()
        cat_frame = cat_frame.sort_values('anläggningskategori').reset_index(drop=True)
        cat_frame['cat_encode'] = range(1, len(cat_frame) + 1)
        cat_frame = cat_frame.rename(columns={'anläggningskategori': 'cat'})
        
        subcat_frame = df[['typ_av_anläggning']].drop_duplicates().copy()
        subcat_frame = subcat_frame.sort_values('typ_av_anläggning').reset_index(drop=True)
        subcat_frame['subcat_encode'] = range(1, len(subcat_frame) + 1)
        subcat_frame = subcat_frame.rename(columns={'typ_av_anläggning': 'subcat'})
        
        return cat_frame, subcat_frame
    
    mappings = {}
    mappings['time_frame'] = create_time_frame()
    cat_frame, subcat_frame = create_category_encoding(kent_data['uppslagsvarden'])
    mappings['cat_frame'] = cat_frame
    mappings['subcat_frame'] = subcat_frame
    
    return mappings


# ============================================================================
# STEG 3: ENCODAR OCH TRANSFORMERAR
# ============================================================================

def apply_all_encodings(df: pd.DataFrame, mappings: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Applicerar alla encodings och transformationer."""
    
    df = df.copy()
    
    # Encode kategorier
    if 'anl_kat' in df.columns:
        df['cat'] = df['anl_kat'].str.lower()
    if 'anl_typ' in df.columns:
        df['subcat'] = df['anl_typ'].str.lower()
    
    df = df.merge(mappings['cat_frame'], on='cat', how='left')
    if 'subcat' in df.columns:
        df = df.merge(mappings['subcat_frame'], on='subcat', how='left')
    
    # Encode tidsvariabler
    def parse_time(time_str):
        if pd.isna(time_str):
            return None
        time_str = str(time_str).strip()
        
        # Hantera endast årtal (t.ex. "2020" eller "2020.0")
        if '.' in time_str:
            time_str = time_str.split('.')[0]
        
        if 'H' not in time_str:
            time_str = time_str + ' H2'
        
        match = mappings['time_frame'][mappings['time_frame']['time_string'] == time_str]
        if not match.empty:
            return int(match.iloc[0]['time'])
        return None
    
    # Prioritera tidsperiod_från, sedan år_från som fallback
    if 'tidsperiod_från' in df.columns:
        df['time_from'] = df['tidsperiod_från'].apply(parse_time)
    
    # Om time_from fortfarande är NULL, använd år_från
    if 'time_from' not in df.columns or df['time_from'].isna().all():
        if 'år_från' in df.columns:
            df['time_from'] = df['år_från'].apply(parse_time)
    
    if 'halvår' in df.columns:
        df['time_invest'] = df['halvår'].apply(parse_time)
    
    # För investeringar: sätt time_from = time_invest om time_from saknas
    if 'capbase_existing' in df.columns:
        invest_mask = df['capbase_existing'] == 0
        if 'time_invest' in df.columns:
            missing_time_from = df['time_from'].isna()
            df.loc[invest_mask & missing_time_from, 'time_from'] = df.loc[invest_mask & missing_time_from, 'time_invest']
    
    df['time_from_missing'] = df.get('år_saknas', pd.Series()).apply(lambda x: 1 if x == 'Ja' else 0)
    
    # VARNING: Om befintliga komponenter saknar time_from
    if 'capbase_existing' in df.columns:
        existing_mask = df['capbase_existing'] == 1
        missing_time = df['time_from'].isna()
        problematic = existing_mask & missing_time
        if problematic.any():
            n_missing = problematic.sum()
            warnings.warn(
                f"⚠️ {n_missing} befintliga komponenter saknar 'Ursprungligen tagen i bruk'. "
                f"Dessa kommer inte inkluderas i beräkningar. "
                f"Fyll i kolumnen i KENT-filen eller markera 'År saknas'."
            )
    
    # Standardisera rådighet
    if 'rådighet' in df.columns:
        df['owned'] = df['rådighet'].apply(
            lambda x: 1 if str(x).strip().lower() == 'ägd' else 0
        )
    
    # Konsolidera värderingar till nuav_2022
    df['nuav_2022'] = 0.0
    
    if 'metod' in df.columns:
        # Normvärde - använd NUAV direkt
        mask = df['metod'] == 'normvärde'
        if 'nuav' in df.columns:
            df.loc[mask, 'nuav_2022'] = df.loc[mask, 'nuav']
        
        # Anskaffningsvärde - använd nuav om den finns (redan beräknad i Excel)
        mask = df['metod'] == 'anskaffningsvärde'
        if 'nuav' in df.columns:
            df.loc[mask, 'nuav_2022'] = df.loc[mask, 'nuav']
        
        # Bokfört värde - använd nuav om den finns
        mask = df['metod'] == 'bokförtvärde'
        if 'nuav' in df.columns:
            df.loc[mask, 'nuav_2022'] = df.loc[mask, 'nuav']
        
        # Annat skäligt värde - använd nuav om den finns
        mask = df['metod'] == 'annatskäligtvärde'
        if 'nuav' in df.columns:
            df.loc[mask, 'nuav_2022'] = df.loc[mask, 'nuav']
        
        # Investeringar - använd 'värde'
        mask = df['metod'] == 'future_invest'
        if 'värde' in df.columns:
            df.loc[mask, 'nuav_2022'] = df.loc[mask, 'värde']
    
    # Process invest sign
    if 'typavförändring' in df.columns:
        df['invest'] = df['typavförändring'].apply(
            lambda x: 1 if 'investering' in str(x).lower() else -1 if 'utrangering' in str(x).lower() else np.nan
        )
        if 'nuav_2022' in df.columns:
            df['nuav_2022'] = df['nuav_2022'] * df['invest'].fillna(1)
    else:
        df['invest'] = np.nan
    
    # Lägg till komponent-ID
    df['id_component'] = range(1, len(df) + 1)
    
    return df


# ============================================================================
# STEG 4: BYGG CAPBASE_A
# ============================================================================

def build_capbase_a_from_kent(
    kent_file,
    network_id: Optional[int] = None
) -> pd.DataFrame:
    """
    Huvudfunktion: Bygger capbase_a från KENT Excel-fil.
    
    Args:
        kent_file: Uploadad fil-objekt från st.file_uploader eller filepath
        network_id: Nätverks-ID för denna data
    
    Returns:
        capbase_a DataFrame redo för beräkningskedjan
    """
    
    # Steg 1: Läs KENT
    kent_data = read_kent_excel(kent_file)
    
    # Steg 2: Skapa mappningar
    mappings = create_mappings(kent_data)
    
    # Steg 3: Kombinera datasets
    dfs = []
    if not kent_data['normvarde'].empty:
        dfs.append(kent_data['normvarde'])
    if not kent_data['ovriga'].empty:
        dfs.append(kent_data['ovriga'])
    if not kent_data['investeringar'].empty:
        dfs.append(kent_data['investeringar'])
    
    if not dfs:
        raise ValueError("Ingen data att kombinera från KENT-filen")
    
    combined = pd.concat(dfs, ignore_index=True, sort=False)
    
    # Steg 4: Applicera encodings
    encoded = apply_all_encodings(combined, mappings)
    
    # Steg 5: Lägg till nätverks-ID
    if network_id is not None:
        encoded['id_network'] = network_id
    else:
        encoded['id_network'] = 1
        warnings.warn("Inget nätverks-ID tillgängligt, använder default värde 1")
    
    # Steg 6: Lägg till depreciering parametrar
    encoded['ekdep'] = encoded['cat_encode'].map(
        lambda x: DEPRECIATION_PARAMS.get(x, {}).get('ekdep', None)
    )
    encoded['maxdep'] = encoded['cat_encode'].map(
        lambda x: DEPRECIATION_PARAMS.get(x, {}).get('maxdep', None)
    )
    
    # Steg 7: Välj finala kolumner
    required_cols = [
        'id_component', 'time_from', 'time_invest', 'capbase_existing',
        'ekdep', 'maxdep', 'nuav_2022', 'cat_encode', 'id_network', 'invest'
    ]
    
    extra_cols = [
        'cat', 'subcat', 'subcat_encode', 'antal', 'metod'
    ]
    
    missing = [col for col in required_cols if col not in encoded.columns]
    if missing:
        raise ValueError(f"Saknade obligatoriska kolumner: {missing}")
    
    available = required_cols + [col for col in extra_cols if col in encoded.columns]
    capbase_a = encoded[available].copy()
    
    # Validering
    validation = validate_capbase_a(capbase_a)
    
    if not validation['valid']:
        error_msg = "\n".join(validation['errors'])
        raise ValueError(f"Capbase_a validering misslyckades:\n{error_msg}")
    
    return capbase_a


def validate_capbase_a(df: pd.DataFrame) -> Dict[str, any]:
    """Validerar att capbase_a uppfyller kraven."""
    
    report = {
        'valid': True,
        'errors': [],
        'warnings': [],
        'info': []
    }
    
    required = ['id_component', 'time_from', 'capbase_existing', 'ekdep', 
                'maxdep', 'nuav_2022', 'cat_encode', 'id_network']
    missing = [col for col in required if col not in df.columns]
    if missing:
        report['valid'] = False
        report['errors'].append(f"Saknade kolumner: {missing}")
        return report
    
    if df['capbase_existing'].notna().sum() > 0:
        invalid_existing = ~df['capbase_existing'].isin([0, 1])
        if invalid_existing.any():
            report['errors'].append(f"capbase_existing har ogiltiga värden: {invalid_existing.sum()} rader")
            report['valid'] = False
    
    if (df['ekdep'] <= 0).any():
        report['errors'].append("ekdep innehåller icke-positiva värden")
        report['valid'] = False
    
    if (df['maxdep'] <= 0).any():
        report['errors'].append("maxdep innehåller icke-positiva värden")
        report['valid'] = False
    
    # Kolla time_from för befintliga komponenter
    if 'capbase_existing' in df.columns:
        existing = df['capbase_existing'] == 1
        missing_time = df['time_from'].isna()
        problematic = existing & missing_time
        if problematic.any():
            report['warnings'].append(
                f"{problematic.sum()} befintliga komponenter saknar time_from - "
                f"dessa ger 0 i beräkningar"
            )
    
    inconsistent = df['maxdep'] < df['ekdep']
    if inconsistent.any():
        report['warnings'].append(f"{inconsistent.sum()} komponenter har maxdep < ekdep")
    
    negative_nuav = (df['nuav_2022'] < 0).sum()
    if negative_nuav > 0:
        report['warnings'].append(f"{negative_nuav} komponenter har negativt nuav_2022")
    
    report['info'].append(f"Totalt {len(df)} komponenter")
    report['info'].append(f"{(df['capbase_existing'] == 1).sum()} befintliga komponenter")
    report['info'].append(f"{(df['capbase_existing'] == 0).sum()} nya investeringar")
    report['info'].append(f"{df['cat_encode'].nunique()} unika kategorier")
    
    return report
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
from config.glossary import ASSET_CATEGORY_NAMES

# Authoritative exact-match map: KENT's official "Anl.kategori" text -> cat_encode.
# Mirrors the template's "Unika värden (Anl.kategori)" list 1:1 (case-insensitive).
# Tried before the substring CATEGORY_MAPPING so that e.g. the 220 kV category
# "Ledning ... med undantag för luftledning ..." resolves to its own code (7)
# instead of collapsing to Luftledning (9) on the substring "luftledning".
_OFFICIAL_CATEGORY_TO_ENCODE = {
    name.strip().lower(): ce for ce, name in ASSET_CATEGORY_NAMES.items()
}

# KENT sheet names expected in the template (used for upload diagnostics).
KENT_SHEETS = ('Normvärde', 'Övriga värderingsmetoder', 'Investeringar_Utrangeringar')


def _seek0(f):
    """Rewind a file-like object so it can be read once per sheet."""
    try:
        f.seek(0)
    except (AttributeError, OSError, ValueError):
        pass  # plain filepath string — nothing to rewind


def _clean_cell(v) -> str:
    """Normalise one raw cell to a comparable string (matches _clean_columns)."""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ''
    return str(v).strip().replace('\n', ' ').replace('  ', ' ')


def _uniquify(cols):
    """Mangle duplicate column labels (Excel allows repeats; pandas dedupes)."""
    seen: Dict[str, int] = {}
    out = []
    for c in cols:
        if c in seen:
            seen[c] += 1
            out.append(f"{c}.{seen[c]}")
        else:
            seen[c] = 0
            out.append(c)
    return out


def _read_sheet(filepath, sheet_name: str, markers: set, max_scan: int = 8) -> pd.DataFrame:
    """
    Read a KENT sheet, auto-detecting which row is the header.

    KENT sheets disagree on header position: 'Normvärde' puts the header on
    the first row, while 'Övriga värderingsmetoder' and
    'Investeringar_Utrangeringar' carry a title row above it. Scan the first
    rows and pick the first matching >=2 known header labels (cleaned,
    case-insensitive). Falls back to the second row (legacy header=1).
    """
    _seek0(filepath)
    try:
        raw = pd.read_excel(filepath, sheet_name=sheet_name, header=None, engine='openpyxl')
    except Exception:
        return pd.DataFrame()
    if raw.empty:
        return pd.DataFrame()

    header_row = None
    for i in range(min(max_scan, len(raw))):
        cells = {_clean_cell(v).lower() for v in raw.iloc[i].tolist()}
        if len(markers & cells) >= 2:
            header_row = i
            break
    if header_row is None:
        header_row = 1 if len(raw) > 1 else 0

    columns = _uniquify([
        _clean_cell(v) if _clean_cell(v) else f'_unnamed_{j}'
        for j, v in enumerate(raw.iloc[header_row].tolist())
    ])
    df = raw.iloc[header_row + 1:].copy()
    df.columns = columns
    return df.reset_index(drop=True)


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
        df = _read_sheet(filepath, 'Normvärde',
                         {'anl.-kategori', 'kod', 'typ av anläggning', 'antal', 'rådighet'})
        if df.empty:
            return df

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
        df = _read_sheet(filepath, 'Övriga värderingsmetoder',
                         {'ansk', 'bokf', 'annat', 'anl.kategori', 'rådighet'})
        if df.empty:
            return df

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
        df = _read_sheet(filepath, 'Investeringar_Utrangeringar',
                         {'anl.kategori', 'typ av anläggning', 'antal', 'halvår', 'enhet'})
        if df.empty:
            return df

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
        warnings.warn("No existing capital base found in the KENT file.")
    
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

    # 1. Exact match against KENT's official category texts (authoritative).
    exact = _OFFICIAL_CATEGORY_TO_ENCODE.get(cat_lower)
    if exact is not None:
        return exact

    # 2. Fallback: substring match (handles short/free-text labels, e.g. the
    #    reverse-engineered round-trip file's "Kabel", "Transformator", ...).
    for key, code in CATEGORY_MAPPING.items():
        if key in cat_lower:
            return code

    return 17


def category_match_kind(category_text) -> str:
    """
    Classify HOW a category text resolves to a cat_encode, for diagnostics.

    Returns:
        'exact'     - matched an official KENT category name (authoritative)
        'substring' - matched the substring fallback table
        'default'   - no match; silently assumed Transformator (17)
        'empty'     - blank / NaN category cell
    """
    if pd.isna(category_text):
        return 'empty'
    cat_lower = str(category_text).strip().lower()
    if not cat_lower:
        return 'empty'
    if cat_lower in _OFFICIAL_CATEGORY_TO_ENCODE:
        return 'exact'
    for key in CATEGORY_MAPPING:
        if key in cat_lower:
            return 'substring'
    return 'default'


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
        raise ValueError("No data could be read from the KENT file.")
    
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
        raise ValueError(f"Required columns are missing: {missing}")
    
    available = required_cols + [col for col in extra_cols if col in df.columns]
    capbase_a = df[available].copy().reset_index(drop=True)
    
    validation = validate_capbase_a(capbase_a)
    if not validation['valid']:
        raise ValueError("KENT validation failed:\n" + "\n".join(validation['errors']))
    
    return capbase_a


def validate_capbase_a(df: pd.DataFrame) -> Dict[str, Any]:
    """Validerar capbase_a."""
    report = {'valid': True, 'errors': [], 'warnings': [], 'info': []}
    
    required = ['id_component', 'time_from', 'capbase_existing', 'ekdep', 
                'maxdep', 'nuav_2022', 'cat_encode', 'id_network']
    
    missing = [col for col in required if col not in df.columns]
    if missing:
        report['valid'] = False
        report['errors'].append(f"Missing columns: {missing}")
        return report

    if df['capbase_existing'].notna().sum() > 0:
        if (~df['capbase_existing'].isin([0, 1])).any():
            report['errors'].append("capbase_existing has invalid values")
            report['valid'] = False

    if (df['ekdep'] <= 0).any():
        report['errors'].append("ekdep contains non-positive values")
        report['valid'] = False

    if (df['maxdep'] <= 0).any():
        report['errors'].append("maxdep contains non-positive values")
        report['valid'] = False

    existing = df['capbase_existing'] == 1
    problematic = existing & df['time_from'].isna()
    if problematic.any():
        report['warnings'].append(f"{problematic.sum()} existing components have no time_from")

    if (df['maxdep'] < df['ekdep']).any():
        report['warnings'].append("Some components have maxdep < ekdep")

    report['info'].append(f"{len(df)} components in total")
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


# Category texts that mean "no category given" once lowercased.
_EMPTYISH_CATEGORY = {'', 'nan', 'none', 'ovrigt'}


def _rows(n: int) -> str:
    """Pluralise 'row'/'rows' for diagnostic copy."""
    return "row" if n == 1 else "rows"


def _comp(n: int) -> str:
    """Pluralise 'component'/'components' for diagnostic copy."""
    return "component" if n == 1 else "components"


def _has(n: int) -> str:
    """Agree 'has'/'have' with the count for diagnostic copy."""
    return "has" if n == 1 else "have"


def _isare(n: int) -> str:
    """Agree 'is'/'are' with the count for diagnostic copy."""
    return "is" if n == 1 else "are"


def diagnose_kent_upload(
    kent_file,
    network_id: int,
    lifetime_adjustments: Optional[Dict[int, Dict[str, int]]] = None,
) -> Dict[str, Any]:
    """
    Validate an uploaded KENT file and return a structured deviation report
    WITHOUT raising. Used at upload time so the user sees, before the file is
    accepted into a case:
      - blocking errors (the file cannot be used), and
      - deviations/warnings (it can be used, but here is what we assume).

    Returns a dict:
        ok        -- bool; False if any blocking error
        errors    -- list of {issue, detail}              (cannot proceed)
        warnings  -- list of {issue, detail, assumption}  (proceed-but-flag)
        summary   -- get_kent_upload_summary(capbase) | None
    """
    report: Dict[str, Any] = {"ok": False, "errors": [], "warnings": [], "summary": None}

    def err(issue: str, detail: str = ""):
        report["errors"].append({"issue": issue, "detail": str(detail)})

    def warn(issue: str, detail: str = "", assumption: str = ""):
        report["warnings"].append(
            {"issue": issue, "detail": str(detail), "assumption": str(assumption)}
        )

    transformator = ASSET_CATEGORY_NAMES[17]

    # 1. File must open as a real .xlsx workbook
    try:
        _seek0(kent_file)
        xls = pd.ExcelFile(kent_file, engine="openpyxl")
        sheet_names = set(xls.sheet_names)
    except Exception as e:
        err("File could not be read as an Excel workbook.",
            f"Make sure it is a KENT file saved in .xlsx format ({type(e).__name__}).")
        return report

    # 2. Must contain at least one KENT sheet
    if not any(s in sheet_names for s in KENT_SHEETS):
        err("File does not match the KENT template.",
            "None of the KENT sheets ("
            + ", ".join(f"'{s}'" for s in KENT_SHEETS)
            + f") were found. Sheets in file: {sorted(sheet_names)[:8]}.")
        return report

    # Soft: a sheet from the template is entirely missing
    for s in KENT_SHEETS:
        if s not in sheet_names:
            warn(f"The '{s}' sheet is missing.",
                 "Only the sheets present are read.",
                 "No entries from this sheet are included.")

    # 3. Parse via the real pipeline path (surfaces schema/validation errors)
    try:
        capbase = build_capbase_a_from_kent(kent_file, network_id, lifetime_adjustments)
    except ValueError as e:
        err("KENT file could not be parsed.", str(e))
        return report
    except Exception as e:
        err("Unexpected error while parsing the KENT file.", f"{type(e).__name__}: {e}")
        return report

    report["summary"] = get_kent_upload_summary(capbase)

    # 4a. Unknown / blank categories -> silently assumed Transformator (17)
    if "cat" in capbase.columns:
        vc = capbase["cat"].astype(str).str.strip().str.lower().value_counts()
        unknown, n_empty = {}, 0
        for text, n in vc.items():
            if text in _EMPTYISH_CATEGORY:
                n_empty += int(n)
            elif category_match_kind(text) == "default":
                unknown[text] = int(n)
        if unknown:
            listed = ", ".join(f'"{t}" ({n} {_rows(n)})' for t, n in unknown.items())
            warn("Unknown asset category.",
                 f"Does not match the KENT category list: {listed}.",
                 f"Treated as '{transformator}' (code 17). Check the spelling in the file.")
        if n_empty:
            warn("Rows without a category.",
                 f"{n_empty} {_comp(n_empty)} {_has(n_empty)} no category text.",
                 f"Treated as '{transformator}' (code 17).")

    # 4b. Existing components without a year -> no age, excluded from the base
    existing = capbase["capbase_existing"] == 1
    n_no_year = int((existing & capbase["time_from"].isna()).sum())
    if n_no_year:
        warn("Components without a year.",
             f"{n_no_year} existing {_comp(n_no_year)} {_has(n_no_year)} no valid year.",
             "These get no age and do not contribute to the capital base.")

    # 4c. Zero / non-numeric NUAV among existing components
    n_zero_nuav = int((existing & (capbase["nuav_2022"] == 0)).sum())
    if n_zero_nuav:
        warn("Components with NUAV 0.",
             f"{n_zero_nuav} existing {_comp(n_zero_nuav)} {_has(n_zero_nuav)} NUAV 0 (blank or non-numeric).",
             "These do not contribute to the capital base.")

    # 4d. Lifetime sanity: maxdep < ekdep
    bad_life = int((capbase["maxdep"] < capbase["ekdep"]).sum())
    if bad_life:
        warn("Maximum lifetime shorter than ordinary lifetime.",
             f"{bad_life} {_comp(bad_life)} affected.",
             "Calculation proceeds; check the lifetime parameters.")

    # 4e. Best-effort: Normvärde rows that have a category but no 'Kod' are dropped
    try:
        _seek0(kent_file)
        raw_norm = _read_sheet(
            kent_file, "Normvärde",
            {'anl.-kategori', 'kod', 'typ av anläggning', 'antal', 'rådighet'},
        )
        if not raw_norm.empty:
            cols = {str(c).strip().lower(): c for c in raw_norm.columns}
            cat_col, kod_col = cols.get("anl.-kategori"), cols.get("kod")
            if cat_col is not None and kod_col is not None:
                has_cat = (raw_norm[cat_col].notna()
                           & (raw_norm[cat_col].astype(str).str.strip() != ""))
                dropped = int((has_cat & raw_norm[kod_col].isna()).sum())
                if dropped:
                    warn("Rows in 'Normvärde' without a category code.",
                         f"{dropped} {_rows(dropped)} {_has(dropped)} a category but no 'Kod' "
                         f"and {_isare(dropped)} left out.",
                         "Fill in the 'Kod' column for these rows.")
    except Exception:
        pass  # dropped-row detection is best-effort and never blocks

    report["ok"] = len(report["errors"]) == 0
    return report
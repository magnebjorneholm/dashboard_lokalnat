"""
data_loaders/baseline_data.py

Baseline data loader.
Laddar all data som behövs för baseline-beräkningar.

Uppdaterad för Data_modeller med per-år avkastning:
- Avkastning_2024, Avkastning_2025, Avkastning_2026, Avkastning_2027
- Avkastning_Period (periodsumma)
"""

from dataclasses import dataclass
import pandas as pd
from typing import Dict, Optional
from pathlib import Path


@dataclass(frozen=True)
class BaselineData:
    """
    Immutable baseline data container.
    Frozen = read-only, kan inte ändras efter skapande.
    """
    # Main data
    df_all_companies: pd.DataFrame  # 148 rader med CAPEX, OPEX, volymer, avkastning per år
    dea_results: pd.DataFrame       # 148 rader från EIs_DEA.xlsx
    sdf_ir: pd.DataFrame
    sdf_paverkbara: pd.DataFrame
    sdf_opaverkbara: pd.DataFrame
    reconciliation: pd.DataFrame    # Mapping REId ↔ id_network (har även DMU för kompatibilitet)
    
    # Parameters
    wacc: float = 0.0453  # Real WACC before tax


def _load_data_modeller(data_path: Optional[str] = None) -> pd.DataFrame:
    """
    Laddar Data_modeller.xlsx med DEA-data och per-år avkastning.
    
    Args:
        data_path: Sökväg till data-mapp. Om None, använd standardsökvägar.
    
    Returns:
        DataFrame med kolumner:
        ['DMU', 'REId', 'Företag', 'OPEXp', 'CAPEX', 'Avskrivning', 'Avkastning',
         'CU', 'MW', 'NS', 'MWhl', 'MWhh', 'TOTEX', 'Kapitalkostnad_2024',
         'Avkastning_2024', 'Avkastning_2025', 'Avkastning_2026', 'Avkastning_2027',
         'Avkastning_Period']
    """
    # Sökvägar att prova
    search_paths = []
    if data_path:
        search_paths.append(Path(data_path) / "Data_modeller.xlsx")
    
    search_paths.extend([
        Path("Data_modeller.xlsx"),
        Path("data/Data_modeller.xlsx"),
        Path("/mnt/project/Data_modeller.xlsx")
    ])
    
    data_file = None
    for path in search_paths:
        if path.exists():
            data_file = path
            break
    
    if data_file is None:
        raise FileNotFoundError(
            "Kunde inte hitta Data_modeller.xlsx. "
            f"Provade: {[str(p) for p in search_paths]}"
        )
    
    # Försök läsa från olika sheet-namn (för bakåtkompatibilitet)
    df = None
    sheet_names_to_try = ["Körning", "Sheet1", 0]
    
    for sheet_name in sheet_names_to_try:
        try:
            df = pd.read_excel(data_file, sheet_name=sheet_name, engine="openpyxl")
            break
        except Exception:
            continue
    
    if df is None:
        raise RuntimeError(
            f"Kunde inte läsa Data_modeller.xlsx. "
            f"Provade sheets: {sheet_names_to_try}"
        )
    
    # Validera grundläggande kolumner
    required_cols = ['DMU', 'REId', 'Företag', 'OPEXp', 'CAPEX', 'CU', 'MW', 'NS', 'MWhl', 'MWhh']
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Saknade kolumner i Data_modeller.xlsx: {missing}")
    
    # Konvertera numeriska kolumner
    numeric_cols = ['OPEXp', 'CAPEX', 'CU', 'MW', 'NS', 'MWhl', 'MWhh']
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    
    # Hantera Avskrivning och Avkastning (aggregat)
    if 'Avskrivning' in df.columns:
        df['Avskrivning'] = pd.to_numeric(df['Avskrivning'], errors="coerce")
    else:
        # Fallback om kolumn saknas
        df['Avskrivning'] = df['CAPEX'] * 0.5
        print("  VARNING: Avskrivning saknas, använder approximation (CAPEX * 0.5)")
    
    if 'Avkastning' in df.columns:
        df['Avkastning'] = pd.to_numeric(df['Avkastning'], errors="coerce")
    else:
        # Fallback om kolumn saknas
        df['Avkastning'] = df['CAPEX'] * 0.5
        print("  VARNING: Avkastning saknas, använder approximation (CAPEX * 0.5)")
    
    # Hantera per-år avkastningskolumner (nya i utökad Data_modeller)
    yearly_return_cols = ['Avkastning_2024', 'Avkastning_2025', 
                          'Avkastning_2026', 'Avkastning_2027']
    
    for col in yearly_return_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        else:
            # Fallback: approximera med aggregerad avkastning
            df[col] = df['Avkastning']
            print(f"  VARNING: {col} saknas, använder Avkastning som approximation")
    
    # Hantera Avkastning_Period (periodsumma)
    if 'Avkastning_Period' in df.columns:
        df['Avkastning_Period'] = pd.to_numeric(df['Avkastning_Period'], errors="coerce")
    else:
        # Beräkna från per-år kolumner
        df['Avkastning_Period'] = (
            df['Avkastning_2024'] + df['Avkastning_2025'] + 
            df['Avkastning_2026'] + df['Avkastning_2027']
        )
        print("  VARNING: Avkastning_Period saknas, beräknad från per-år värden")
    
    # Explicit alias för årsvärde (CAPEX är källnamn i Excel)
    df["Kapitalkostnad_2024"] = df["CAPEX"]

    # Beräkna TOTEX med intern standardkolumn
    df["TOTEX"] = df["OPEXp"] + df["Kapitalkostnad_2024"]
    
    return df


def _load_eis_dea(data_path: Optional[str] = None) -> pd.DataFrame:
    """
    Laddar Ei's referens-DEA resultat från Excel.

    Args:
        data_path: Sökväg till data-mapp. Om None, använd standardsökvägar.

    Returns:
        DataFrame med kolumner:
        - REId: Lokalnät-ID (primärnyckel)
        - DMU: Företags-DMU (finns även för kompatibilitet)
        - Företag: Företagsnamn
        - Effektivitet: Effektivitetsvärde (eller None för outliers)
        - Supereffektivitet: Supereffektivitetsvärde (eller None för outliers)
        - potential: Förbättringspotential
        - Effkrav_proc: Årligt effektiviseringskrav
        - is_outlier: Boolean flag
    """
    # Sökvägar att prova
    search_paths = []
    if data_path:
        search_paths.append(Path(data_path) / "EIs_DEA.xlsx")
    
    search_paths.extend([
        Path("EIs_DEA.xlsx"),
        Path("data/EIs_DEA.xlsx"),
        Path("/mnt/project/EIs_DEA.xlsx")
    ])
    
    data_file = None
    for path in search_paths:
        if path.exists():
            data_file = path
            break
    
    if data_file is None:
        raise FileNotFoundError(
            "Kunde inte hitta EIs_DEA.xlsx. "
            f"Provade: {[str(p) for p in search_paths]}"
        )
    
    try:
        df = pd.read_excel(data_file, sheet_name='Körning', engine='openpyxl')
    except Exception as e:
        raise RuntimeError(f"Fel vid inläsning av EIs_DEA.xlsx: {e}")
    
    # Hantera outliers
    df['is_outlier'] = df['Effektivitet'].astype(str).str.upper() == 'OUTLIER'
    
    # Konvertera Effektivitet till float (None för outliers)
    def parse_efficiency(val):
        if str(val).upper() == 'OUTLIER':
            return None
        try:
            return float(val)
        except (ValueError, TypeError):
            return None
    
    df['Effektivitet'] = df['Effektivitet'].apply(parse_efficiency)
    
    if 'Supereffektivitet' in df.columns:
        df['Supereffektivitet'] = df['Supereffektivitet'].apply(parse_efficiency)
    else:
        df['Supereffektivitet'] = None
    
    # Hantera potential
    if 'potential' in df.columns:
        df['potential'] = pd.to_numeric(df['potential'], errors='coerce').fillna(0.0)
    else:
        df['potential'] = 0.0
    
    # Konvertera Effkrav_proc till float
    if 'Effkrav_proc' in df.columns:
        df['Effkrav_proc'] = pd.to_numeric(df['Effkrav_proc'], errors='coerce').fillna(0.0)
    else:
        df['Effkrav_proc'] = 0.0
    
    return df


def _load_sdf_data(data_path: Optional[str] = None) -> Dict[str, pd.DataFrame]:
    """
    Laddar SDF-data från "Löpande kostnader från SDF" Excel-fil.
    
    Args:
        data_path: Sökväg till data-mapp
        
    Returns:
        Dict med tre DataFrames: 'ir', 'paverkbara', 'opaverkbara'
    """
    search_paths = []
    if data_path:
        search_paths.append(Path(data_path) / "Löpande kostnader från SDF 2024-27.xlsx")
    
    search_paths.extend([
        Path("Löpande kostnader från SDF 2024-27.xlsx"),
        Path("data/Löpande kostnader från SDF 2024-27.xlsx"),
    ])
    
    data_file = None
    for path in search_paths:
        if path.exists():
            data_file = path
            break
    
    if data_file is None:
        raise FileNotFoundError(
            "Kunde inte hitta SDF-fil. "
            f"Provade: {[str(p) for p in search_paths]}"
        )
    
    result = {}
    
    # Sheet-namn att försöka för varje typ
    sheet_mappings = {
        'ir': ['IR 2024-2027', 'IR 2024-27', 'IR'],
        'paverkbara': ['Påverkbara', 'Paverkbara'],
        'opaverkbara': ['Opåverkbara', 'Opaverkbara'],
    }
    
    for key, sheet_names in sheet_mappings.items():
        for sheet_name in sheet_names:
            try:
                df = pd.read_excel(data_file, sheet_name=sheet_name, engine="openpyxl")
                result[key] = df
                break
            except Exception:
                continue
        
        if key not in result:
            print(f"  VARNING: Kunde inte läsa SDF sheet '{key}'")
            result[key] = pd.DataFrame()
    
    return result


def _load_reconciliation(data_path: Optional[str] = None) -> pd.DataFrame:
    """
    Laddar reconciliation mapping mellan REId, id_network och DMU.
    
    Args:
        data_path: Sökväg till data-mapp
        
    Returns:
        DataFrame med mappningar
    """
    search_paths = []
    if data_path:
        search_paths.append(Path(data_path) / "reconciliation_id_network_firm_dmu.csv")
    
    search_paths.extend([
        Path("reconciliation_id_network_firm_dmu.csv"),
        Path("data/reconciliation_id_network_firm_dmu.csv"),
        Path("/mnt/project/reconciliation_id_network_firm_dmu.csv"),
    ])
    
    data_file = None
    for path in search_paths:
        if path.exists():
            data_file = path
            break
    
    if data_file is None:
        raise FileNotFoundError(
            "Kunde inte hitta reconciliation_id_network_firm_dmu.csv. "
            f"Provade: {[str(p) for p in search_paths]}"
        )
    
    df = pd.read_csv(data_file)
    
    # Hantera olika kolumnnamn (REId vs id_network_string)
    if 'id_network_string' in df.columns and 'REId' not in df.columns:
        df['REId'] = df['id_network_string']
    
    return df


def load_baseline_data(data_path: Optional[str] = None) -> BaselineData:
    """
    Huvudfunktion för att ladda all baseline-data.
    
    Args:
        data_path: Sökväg till data-mapp. Om None, använd standardsökvägar.
        
    Returns:
        BaselineData objekt med all data
        
    Raises:
        FileNotFoundError: Om kritiska filer saknas
        RuntimeError: Om inläsning misslyckas
    """
    
    # 1. Ladda Data_modeller.xlsx
    print("Laddar Data_modeller.xlsx...")
    df_all_companies = _load_data_modeller(data_path)
    print(f"  ✓ Laddade {len(df_all_companies)} företag")
    
    # Verifiera per-år avkastning
    yearly_cols = ['Avkastning_2024', 'Avkastning_2025', 
                   'Avkastning_2026', 'Avkastning_2027']
    has_yearly = all(col in df_all_companies.columns for col in yearly_cols)
    if has_yearly:
        print(f"  ✓ Per-år avkastning tillgänglig (2024-2027)")
    else:
        print(f"  ⚠ Per-år avkastning saknas eller approximerad")
    
    # 2. Ladda EIs_DEA.xlsx
    print("Laddar EIs_DEA.xlsx...")
    dea_results = _load_eis_dea(data_path)
    print(f"  ✓ Laddade DEA-resultat för {len(dea_results)} företag")
    
    # 3. Ladda SDF data
    print("Laddar Löpande kostnader från SDF...")
    sdf_data = _load_sdf_data(data_path)
    n_ir = len(sdf_data.get('ir', pd.DataFrame()))
    n_opav = len(sdf_data.get('opaverkbara', pd.DataFrame()))
    n_pav = len(sdf_data.get('paverkbara', pd.DataFrame()))
    print(f"  ✓ Laddade SDF-data (IR: {n_ir}, Opåverkbara: {n_opav}, Påverkbara: {n_pav} rader)")
    
    # 4. Ladda reconciliation mapping
    print("Laddar reconciliation...")
    reconciliation = _load_reconciliation(data_path)
    print(f"  ✓ Laddade reconciliation ({len(reconciliation)} mappningar)")
    
    # 5. Validera att alla dataset har samma antal företag
    n_companies = len(df_all_companies)
    n_dea = len(dea_results)
    
    if n_companies != n_dea:
        print(f"VARNING: Data_modeller har {n_companies} företag men EIs_DEA har {n_dea}")
    
    return BaselineData(
        df_all_companies=df_all_companies,
        dea_results=dea_results,
        sdf_ir=sdf_data['ir'],
        sdf_paverkbara=sdf_data['paverkbara'],
        sdf_opaverkbara=sdf_data['opaverkbara'],
        reconciliation=reconciliation,
        wacc=0.0453,
    )


def get_baseline_summary(baseline: BaselineData) -> Dict:
    """
    Hämta sammanfattning av baseline data.
    
    Args:
        baseline: BaselineData objekt
        
    Returns:
        Dict med summerad statistik
    """
    df = baseline.df_all_companies
    
    summary = {
        'n_dmu': len(df),
        'total_capex_tsek': float(df['Kapitalkostnad_2024'].sum()),
        'total_opex_tsek': float(df['OPEXp'].sum()),
        'total_totex_tsek': float(df['TOTEX'].sum()),
        'mean_capex_tsek': float(df['Kapitalkostnad_2024'].mean()),
        'mean_opex_tsek': float(df['OPEXp'].mean()),
        'total_customers': float(df['CU'].sum()),
        'total_mw': float(df['MW'].sum()),
        'total_network_km': float(df['NS'].sum()),
        'baseline_wacc': baseline.wacc,
        'n_dea_results': len(baseline.dea_results),
        'n_sdf_ir': len(baseline.sdf_ir),
        'n_sdf_paverkbara': len(baseline.sdf_paverkbara),
        'n_sdf_opaverkbara': len(baseline.sdf_opaverkbara),
        'n_reconciliation': len(baseline.reconciliation),
    }
    
    # Lägg till per-år avkastning om tillgängligt
    yearly_cols = ['Avkastning_2024', 'Avkastning_2025', 
                   'Avkastning_2026', 'Avkastning_2027']
    if all(col in df.columns for col in yearly_cols):
        summary['has_yearly_returns'] = True
        summary['total_avkastning_period'] = float(df['Avkastning_Period'].sum())
    else:
        summary['has_yearly_returns'] = False
    
    return summary
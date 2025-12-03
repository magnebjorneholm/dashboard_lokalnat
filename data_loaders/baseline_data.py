"""
data_loaders/baseline_data.py

Baseline data loader.
Laddar all data som behövs för baseline-beräkningar.
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
    df_all_companies: pd.DataFrame  # 148 rader med CAPEX, OPEX, volymer
    dea_results: pd.DataFrame       # 148 rader från EIs_DEA.xlsx
    sdf_ir: pd.DataFrame
    sdf_paverkbara: pd.DataFrame
    sdf_opaverkbara: pd.DataFrame
    reconciliation: pd.DataFrame    # Mapping REId ↔ id_network (har även DMU för kompatibilitet)
    
    # Parameters
    wacc: float = 0.0453  # Real WACC before tax


def _load_data_modeller(data_path: Optional[str] = None) -> pd.DataFrame:
    """
    Laddar Data_modeller.xlsx med DEA-data.
    
    Args:
        data_path: Sökväg till data-mapp. Om None, använd standardsökvägar.
    
    Returns:
        DataFrame med kolumner:
        ['DMU', 'REId', 'Företag', 'OPEXp', 'CAPEX', 'Avskrivning', 'Avkastning',
         'CU', 'MW', 'NS', 'MWhl', 'MWhh', 'TOTEX']
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
    
    # Läs från Körning-sheet
    try:
        df = pd.read_excel(data_file, sheet_name="Körning", engine="openpyxl")
    except Exception as e:
        raise RuntimeError(f"Fel vid inläsning av Data_modeller.xlsx: {e}")
    
    # Validera kolumner
    expected = ['DMU', 'REId', 'Företag', 'OPEXp', 'CAPEX', 'CU', 'MW', 'NS', 'MWhl', 'MWhh']
    missing = [c for c in expected if c not in df.columns]
    if missing:
        raise ValueError(f"Saknade kolumner i Data_modeller.xlsx: {missing}")
    
    # Konvertera numeriska kolumner
    numeric_cols = ['OPEXp', 'CAPEX', 'CU', 'MW', 'NS', 'MWhl', 'MWhh']
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    
    # Hantera Avskrivning och Avkastning om de finns
    if 'Avskrivning' in df.columns:
        df['Avskrivning'] = pd.to_numeric(df['Avskrivning'], errors="coerce")
    else:
        # Placeholder
        df['Avskrivning'] = df['CAPEX'] * 0.5
    
    if 'Avkastning' in df.columns:
        df['Avkastning'] = pd.to_numeric(df['Avkastning'], errors="coerce")
    else:
        # Placeholder
        df['Avkastning'] = df['CAPEX'] * 0.5
    
    # Beräkna TOTEX
    df["TOTEX"] = df["OPEXp"] + df["CAPEX"]
    
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
    Laddar Löpande kostnader från SDF 2024-27.xlsx.
    
    Laddar 3 sheets:
    - 'IR 2024-2027': Huvudsheet med totala intäktsramar
    - 'Opåverkbara': Opåverkbara kostnader uppdelade
    - 'Påverkbara': Påverkbara kostnader uppdelade
    
    Args:
        data_path: Sökväg till data-mapp. Om None, använd standardsökvägar.
    
    Returns:
        Dict med DataFrames per sheet: {'ir': df1, 'opaverkbara': df2, 'paverkbara': df3}
    """
    # Sökvägar att prova (med olika varianter av filnamn)
    search_paths = []
    if data_path:
        search_paths.append(Path(data_path) / "Löpande kostnader från SDF 2024-27.xlsx")
        search_paths.append(Path(data_path) / "Löpande_kostnader_från_SDF_202427.xlsx")
        search_paths.append(Path(data_path) / "Löpande kostnader från SDF 202427.xlsx")
    
    search_paths.extend([
        Path("Löpande kostnader från SDF 2024-27.xlsx"),
        Path("data/Löpande kostnader från SDF 2024-27.xlsx"),
        Path("Löpande_kostnader_från_SDF_202427.xlsx"),
        Path("Löpande kostnader från SDF 202427.xlsx"),
        Path("data/Löpande_kostnader_från_SDF_202427.xlsx"),
        Path("data/Löpande kostnader från SDF 202427.xlsx"),
        Path("/mnt/project/Löpande kostnader från SDF 2024-27.xlsx"),
        Path("/mnt/project/Löpande_kostnader_från_SDF_202427.xlsx"),
        Path("/mnt/project/Löpande kostnader från SDF 202427.xlsx")
    ])
    
    data_file = None
    for path in search_paths:
        if path.exists():
            data_file = path
            break
    
    if data_file is None:
        print("  ⚠️ SDF-fil hittades inte - returnerar tomma DataFrames")
        return {
            'ir': pd.DataFrame(),
            'opaverkbara': pd.DataFrame(),
            'paverkbara': pd.DataFrame()
        }
    
    try:
        # Läs alla 3 sheets
        ir_sheet = pd.read_excel(data_file, sheet_name='IR 2024-2027', engine='openpyxl')
        opav_sheet = pd.read_excel(data_file, sheet_name='Opåverkbara', engine='openpyxl')
        pav_sheet = pd.read_excel(data_file, sheet_name='Påverkbara', engine='openpyxl')
        
        return {
            'ir': ir_sheet,
            'opaverkbara': opav_sheet,
            'paverkbara': pav_sheet
        }
        
    except Exception as e:
        print(f"  ⚠️ Kunde inte ladda SDF-data: {e}")
        return {
            'ir': pd.DataFrame(),
            'opaverkbara': pd.DataFrame(),
            'paverkbara': pd.DataFrame()
        }


def _load_reconciliation(data_path: Optional[str] = None) -> pd.DataFrame:
    """
    Laddar reconciliation mapping.
    
    Args:
        data_path: Sökväg till data-mapp. Om None, använd standardsökvägar.
    
    Returns:
        DataFrame med kolumner: ['id_network', 'DMU', 'REId', 'Företag']
    """
    # Sökvägar att prova
    search_paths = []
    if data_path:
        search_paths.append(Path(data_path) / "reconciliation_id_network_firm_dmu.csv")
    
    search_paths.extend([
        Path("reconciliation_id_network_firm_dmu.csv"),
        Path("data/reconciliation_id_network_firm_dmu.csv"),
        Path("/mnt/project/reconciliation_id_network_firm_dmu.csv")
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
    
    try:
        rec = pd.read_csv(data_file)
        
        # Standardisera kolumnnamn (case-insensitive)
        rec.columns = [c.strip() for c in rec.columns]
        
        # Behåll endast relevanta kolumner
        keep_cols = []
        for col in ['id_network', 'DMU', 'REId', 'Företag', 'id_firm']:
            if col in rec.columns:
                keep_cols.append(col)
        
        rec = rec[keep_cols].drop_duplicates()
        
        # Konvertera datatyper
        if "DMU" in rec.columns:
            rec["DMU"] = pd.to_numeric(rec["DMU"], errors='coerce').astype('Int64')
        if "REId" in rec.columns:
            rec["REId"] = rec["REId"].astype(str).str.strip()
        if "id_network" in rec.columns:
            rec["id_network"] = pd.to_numeric(rec["id_network"], errors='coerce').astype('Int64')
        
        # Rensa bort rader utan DMU eller REId
        rec = rec.dropna(subset=['DMU', 'REId'])
        
        return rec
        
    except Exception as e:
        raise RuntimeError(f"Fel vid inläsning av reconciliation: {e}")


def load_baseline_data(data_path: Optional[str] = None) -> BaselineData:
    """
    Laddar all baseline data från projektets datafiler.
    
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
    
    # Räkna SDF-rader (separata attribut)
    n_sdf_ir = len(baseline.sdf_ir)
    n_sdf_opav = len(baseline.sdf_opaverkbara)
    n_sdf_pav = len(baseline.sdf_paverkbara)
    
    return {
        'n_dmu': len(df),
        'total_capex_tsek': float(df['CAPEX'].sum()),
        'total_opex_tsek': float(df['OPEXp'].sum()),
        'total_totex_tsek': float(df['TOTEX'].sum()),
        'mean_capex_tsek': float(df['CAPEX'].mean()),
        'mean_opex_tsek': float(df['OPEXp'].mean()),
        'total_customers': float(df['CU'].sum()),
        'total_mw': float(df['MW'].sum()),
        'total_network_km': float(df['NS'].sum()),
        'baseline_wacc': baseline.wacc,
        'n_dea_results': len(baseline.dea_results),
        'n_sdf_ir': len(baseline.sdf_ir),
        'n_sdf_paverkbara': len(baseline.sdf_paverkbara),
        'n_sdf_opaverkbara': len(baseline.sdf_opaverkbara),
        'n_reconciliation': len(baseline.reconciliation)
    }
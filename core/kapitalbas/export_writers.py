"""
export_writers.py - Fil-I/O för kapitalbas-export
=================================================

Hanterar export av beräkningsresultat till parquet-filer med JSON-metadata.
Stödjer både DEA-export (CAPEX baseline vs scenario) och IR-export 
(detaljerad kapitalkostnad för intäktsram-dekomposition).

Inga UI-beroenden - ren fil-I/O som kan användas av både Streamlit och Dash.
"""

import os
import json
from datetime import datetime
from typing import Tuple, Dict, Any
from pathlib import Path
import pandas as pd


# ============================================================================
# KONSTANTER
# ============================================================================

# Ei:s baseline WACC (används i metadata)
R_OLD: float = 0.0453


# ============================================================================
# FORMATERING
# ============================================================================

def format_wacc_tag(r_new: float) -> str:
    """
    Formaterar WACC-värde till tag för filnamn.
    
    Konverterar decimalpunkt till 'p' för att skapa filsystemsvänliga taggar.
    Exempel: 0.0475 → "0p0475"
    
    Args:
        r_new: WACC-värde som decimal (t.ex. 0.0475 för 4.75%)
        
    Returns:
        Formaterad sträng med 4 decimaler och 'p' istället för '.'
    """
    return f"{float(r_new):.4f}".replace(".", "p")


# ============================================================================
# KATALOGHANTERING
# ============================================================================

def ensure_dir(path: str) -> None:
    """
    Skapar katalog (och alla parent-kataloger) om den inte finns.
    
    Args:
        path: Sökväg till katalog som ska skapas
        
    Raises:
        OSError: Om katalog inte kan skapas p.g.a. rättighetsproblem
    """
    os.makedirs(path, exist_ok=True)


def get_org_export_dir(base_dir: str, org: str) -> str:
    """
    Skapar och returnerar organisationsspecifik exportkatalog.
    
    Args:
        base_dir: Baskatalog för export (t.ex. "scenario/kapitalbas/exports_to_dea")
        org: Organisations-ID
        
    Returns:
        Sökväg till organisationsspecifik katalog
    """
    org_path = os.path.join(base_dir, org)
    ensure_dir(org_path)
    return org_path


# ============================================================================
# DEA-EXPORT
# ============================================================================

def write_dea_export(
    df_export: pd.DataFrame, 
    tag: str,
    org: str,
    base_dir: str = "scenario/kapitalbas/exports_to_dea"
) -> Tuple[str, str]:
    """
    Skriver DEA-export till parquet + JSON metadata.
    
    Exporterar CAPEX baseline och scenario per DMU för DEA-analysen.
    Skapar organisationsspecifik underkatalog automatiskt.
    
    Filformat:
    - Data: capex_wacc_{tag}_y2024_dmu.parquet
    - Metadata: capex_wacc_{tag}_y2024_dmu.json
    
    Args:
        df_export: DataFrame med kolumner:
                   - DMU, Företag
                   - CAPEX_2024_tkr (baseline)
                   - CAPEX_2024_wacc_{tag}_tkr (scenario)
                   - delta_tkr, r_old, r_new, price_year
        tag: WACC-tag (t.ex. "0p0475" för 4.75%)
        org: Organisations-ID för underkatalog
        base_dir: Baskatalog för export
        
    Returns:
        Tuple med (data_path, meta_path) - fullständiga sökvägar till skapade filer
        
    Raises:
        ValueError: Om df_export saknar obligatoriska kolumner
        OSError: Om filer inte kan skrivas
    """
    # Validera input
    required_cols = ['DMU', 'Företag', 'CAPEX_2024_tkr', 'r_old', 'r_new', 'price_year']
    missing_cols = [col for col in required_cols if col not in df_export.columns]
    if missing_cols:
        raise ValueError(f"DataFrame saknar obligatoriska kolumner: {missing_cols}")
    
    # Skapa organisationsspecifik katalog
    export_dir = get_org_export_dir(base_dir, org)
    
    # Filnamn
    data_filename = f"capex_wacc_{tag}_y2024_dmu.parquet"
    data_path = os.path.join(export_dir, data_filename)
    meta_path = data_path.replace(".parquet", ".json")
    
    # Skriv data
    df_export.to_parquet(data_path, index=False)
    
    # Skapa metadata
    meta = {
        "description": "CAPEX export för DEA-pipen, DMU-nivå",
        "organization": org,
        "price_year": 2022,
        "unit": "tkr",
        "level": "DMU",
        "wacc_old": R_OLD,
        "wacc_new": float(tag.replace("p", ".")),
        "export_timestamp": datetime.now().isoformat(),
        "total_dmu_count": len(df_export),
        "file_format": "parquet",
        "data_file": data_filename,
        "constructed_as": (
            "Aggregated to annual level before scenario calculation and rounding. "
            "DMU level aggregation from id_network."
        ),
        "note": (
            "This export ensures methodological correctness in DEA efficiency analysis "
            "by applying the same WACC scenario to all DMUs."
        )
    }
    
    # Skriv metadata
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    
    return data_path, meta_path


# ============================================================================
# IR-EXPORT
# ============================================================================

def write_ir_export(
    df_export: pd.DataFrame,
    tag: str,
    org: str,
    base_dir: str = "scenario/kapitalbas/exports_to_ir",
    period_start: int = 2024,
    period_end: int = 2027
) -> Tuple[str, str]:
    """
    Skriver IR-export till parquet + JSON metadata.
    
    Exporterar detaljerad kapitalkostnad för IR-dekomposition.
    Data är summerad över hela regleringsperioden per DMU.
    
    Filformat:
    - Data: ir_kapkost_wacc_{tag}_y{start}_{end}_dmu.parquet
    - Metadata: ir_kapkost_wacc_{tag}_y{start}_{end}_dmu.json
    
    Args:
        df_export: DataFrame med kolumner:
                   - DMU, Företag
                   - Kapitalkostnad_Baseline, Kapitalkostnad_Ny
                   - Avskrivningar_Ny, Avkastning_Baseline, Avkastning_Ny
                   - dep_ord_Ny, dep_tail_Ny, return_ord_Ny, return_tail_Ny
                   - r_old, r_new, price_year, scenario_tag
        tag: WACC-tag (t.ex. "0p0475" för 4.75%)
        org: Organisations-ID för underkatalog
        base_dir: Baskatalog för export
        period_start: Startår för period (default: 2024)
        period_end: Slutår för period (default: 2027)
        
    Returns:
        Tuple med (data_path, meta_path) - fullständiga sökvägar till skapade filer
        
    Raises:
        ValueError: Om df_export saknar obligatoriska kolumner
        OSError: Om filer inte kan skrivas
    """
    # Validera input
    required_cols = [
        'DMU', 'Företag', 
        'Kapitalkostnad_Baseline', 'Kapitalkostnad_Ny',
        'Avskrivningar_Ny', 'Avkastning_Baseline', 'Avkastning_Ny',
        'r_old', 'r_new', 'price_year'
    ]
    missing_cols = [col for col in required_cols if col not in df_export.columns]
    if missing_cols:
        raise ValueError(f"DataFrame saknar obligatoriska kolumner: {missing_cols}")
    
    # Skapa organisationsspecifik katalog
    export_dir = get_org_export_dir(base_dir, org)
    
    # Filnamn
    data_filename = f"ir_kapkost_wacc_{tag}_y{period_start}_{period_end}_dmu.parquet"
    data_path = os.path.join(export_dir, data_filename)
    meta_path = data_path.replace(".parquet", ".json")
    
    # Skriv data
    df_export.to_parquet(data_path, index=False)
    
    # Skapa metadata
    meta = {
        "description": (
            f"Detaljerad kapitalkostnad för IR-dekomposition – "
            f"SUMMA {period_start}–{period_end}, DMU-nivå"
        ),
        "organization": org,
        "price_year": 2022,
        "unit": "tkr",
        "level": "DMU",
        "period": {
            "start": period_start,
            "end": period_end
        },
        "wacc_old": R_OLD,
        "wacc_new": float(tag.replace("p", ".")),
        "export_timestamp": datetime.now().isoformat(),
        "total_dmu_count": len(df_export),
        "file_format": "parquet",
        "data_file": data_filename,
        "constructed_as": (
            "Return-delar skalas per halvår (r_new/r_old); capcost_sum_new beräknas; "
            "därefter summeras H1+H2 för varje år och aggregeras till periodsumma "
            f"{period_start}–{period_end}; DMU-aggregat. Endast lokalnät (REId börjar på REL)."
        ),
        "components": {
            "Avskrivningar_Ny": "dep_ord + dep_tail (opåverkad av WACC)",
            "Avkastning_Ny": "return_ord_new + return_tail_new (påverkas av WACC)",
            "Kapitalkostnad_Ny": "Avskrivningar_Ny + Avkastning_Ny"
        },
        "note": (
            "Inkluderar koncessionsjusteringar för DMU som saknar dessa i originaldata. "
            "Dessa justeringar påverkas INTE av WACC-ändringar."
        )
    }
    
    # Skriv metadata
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    
    return data_path, meta_path


# ============================================================================
# GENERISK EXPORT (framtida utökning)
# ============================================================================

def write_generic_export(
    df_export: pd.DataFrame,
    filename: str,
    metadata: Dict[str, Any],
    org: str,
    base_dir: str
) -> Tuple[str, str]:
    """
    Generisk exportfunktion för framtida behov.
    
    Tillåter export av godtycklig data med anpassad metadata.
    
    Args:
        df_export: DataFrame att exportera
        filename: Filnamn (utan .parquet-suffix)
        metadata: Dict med metadata att spara
        org: Organisations-ID
        base_dir: Baskatalog för export
        
    Returns:
        Tuple med (data_path, meta_path)
    """
    export_dir = get_org_export_dir(base_dir, org)
    
    data_path = os.path.join(export_dir, f"{filename}.parquet")
    meta_path = os.path.join(export_dir, f"{filename}.json")
    
    # Lägg till standard metadata
    metadata.setdefault("export_timestamp", datetime.now().isoformat())
    metadata.setdefault("organization", org)
    metadata.setdefault("file_format", "parquet")
    metadata.setdefault("data_file", f"{filename}.parquet")
    
    # Skriv
    df_export.to_parquet(data_path, index=False)
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    
    return data_path, meta_path


# ============================================================================
# TESTER
# ============================================================================

if __name__ == "__main__":
    """
    Enkla tester för att validera export-funktionalitet.
    """
    import tempfile
    import shutil
    
    print("Testing export_writers.py...")
    print("=" * 60)
    
    # Test 1: format_wacc_tag
    print("\nTest 1: WACC-taggformatering")
    tag = format_wacc_tag(0.0475)
    print(f"0.0475 → '{tag}' (förväntat: '0p0475'): {'' if tag == '0p0475' else ''}")
    
    # Test 2: DEA-export
    print("\nTest 2: DEA-export")
    test_df_dea = pd.DataFrame({
        'DMU': [1, 2],
        'Företag': ['Test AB', 'Demo AB'],
        'CAPEX_2024_tkr': [1000.0, 2000.0],
        'CAPEX_2024_wacc_0p0475_tkr': [1100.0, 2200.0],
        'delta_tkr': [100.0, 200.0],
        'r_old': [R_OLD, R_OLD],
        'r_new': [0.0475, 0.0475],
        'price_year': [2022, 2022]
    })
    
    # Använd temporary directory
    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            data_path, meta_path = write_dea_export(
                test_df_dea, 
                "0p0475", 
                "test_org",
                base_dir=tmpdir
            )
            
            # Verifiera att filer skapades
            data_exists = Path(data_path).exists()
            meta_exists = Path(meta_path).exists()
            print(f"Data-fil skapad: {'' if data_exists else ''}")
            print(f"Meta-fil skapad: {'' if meta_exists else ''}")
            
            # Verifiera att data kan läsas tillbaka
            df_read = pd.read_parquet(data_path)
            print(f"Data kan läsas tillbaka: {'' if len(df_read) == 2 else ''}")
            
            # Verifiera metadata
            with open(meta_path, 'r') as f:
                meta = json.load(f)
            print(f"Metadata innehåller organization: {'' if 'organization' in meta else ''}")
            print(f"Metadata WACC-värde korrekt: {'' if abs(meta['wacc_new'] - 0.0475) < 0.0001 else ''}")
            
        except Exception as e:
            print(f" Fel vid DEA-export: {e}")
    
    # Test 3: IR-export
    print("\nTest 3: IR-export")
    test_df_ir = pd.DataFrame({
        'DMU': [1],
        'Företag': ['Test AB'],
        'Kapitalkostnad_Baseline': [5000.0],
        'Kapitalkostnad_Ny': [5500.0],
        'Avskrivningar_Ny': [3000.0],
        'Avkastning_Baseline': [2000.0],
        'Avkastning_Ny': [2500.0],
        'dep_ord_Ny': [2500.0],
        'dep_tail_Ny': [500.0],
        'return_ord_Ny': [2000.0],
        'return_tail_Ny': [500.0],
        'r_old': [R_OLD],
        'r_new': [0.0475],
        'price_year': [2022],
        'scenario_tag': ['0p0475']
    })
    
    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            data_path, meta_path = write_ir_export(
                test_df_ir,
                "0p0475",
                "test_org",
                base_dir=tmpdir
            )
            
            data_exists = Path(data_path).exists()
            meta_exists = Path(meta_path).exists()
            print(f"Data-fil skapad: {'' if data_exists else ''}")
            print(f"Meta-fil skapad: {'' if meta_exists else ''}")
            
            # Verifiera metadata har period-info
            with open(meta_path, 'r') as f:
                meta = json.load(f)
            has_period = 'period' in meta and 'start' in meta['period']
            print(f"Metadata innehåller period-info: {'' if has_period else ''}")
            
        except Exception as e:
            print(f" Fel vid IR-export: {e}")
    
    print("\n" + "=" * 60)
    print("Alla tester slutförda.")
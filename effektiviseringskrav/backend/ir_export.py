"""
Backend för export av effektiviseringskrav till IR.
====================================================

UPPDATERAD VERSION: Exporterar endast effektiviseringskrav-procent.
Beräkningen av påverkbara kostnader flyttad till IR-modulen.

DESIGN:
- Exporterar ENDAST: REId, DMU, Företag, Effkrav_proc
- Ingen beräkning av kostnader här
- IR ansvarar för att applicera kravet på OPEX eller TOTEX
- UI-agnostisk: tar session_state som optional parameter
"""

from pathlib import Path
from datetime import datetime
from typing import Tuple, Optional, Dict, Any
import json
import pandas as pd

# Import från core (UI-agnostisk)
from core.session_utils import get_user_org, ensure_org_dir


# Baskatalog för exports (utan org-specifikation)
BASE_EXPORT_DIR = "scenario/effektiviseringskrav/exports_to_ir"


def export_effektiviseringskrav_scenario(
    dea_result: pd.DataFrame,
    scenario_name: str,
    session_state: Optional[Dict[str, Any]] = None
) -> Tuple[str, str, dict]:
    """
    Exporterar effektiviseringskrav-procent till organisationsspecifik katalog.
    
    FÖRENKLAD VERSION: Exporterar endast kravprocenten, inte beräknade kostnader.
    IR-modulen ansvarar för att applicera kravet på OPEX eller TOTEX.
    
    Skapar två filer:
    1. Parquet-fil med kravprocent per REId/DMU
    2. JSON-fil med metadata
    
    Args:
        dea_result: DataFrame från DEA med kolumner:
            - DMU: DMU-nummer
            - REId: Redovisningsenhet (kan vara flera per DMU)
            - Företag: Företagsnamn (optional)
            - Effkrav_proc: Årligt effektiviseringskrav som decimal (t.ex. 0.0125)
            - Effektivitet: Effektivitetsmått från DEA (optional, för metadata)
            - is_outlier: Om företaget är outlier (optional, för metadata)
        scenario_name: Namn på scenariot (används i filnamn)
        session_state: Session state dict (optional, för org-identifiering)
        
    Returns:
        Tuple med:
        - data_path: Sökväg till parquet-fil
        - meta_path: Sökväg till metadata-fil
        - summary: Dict med sammanfattning för UI-feedback
        
    Raises:
        ValueError: Om dea_result saknar obligatoriska kolumner
    """
    # Validera input - endast grundläggande kolumner krävs
    required_cols = ['DMU', 'REId', 'Effkrav_proc']
    missing_cols = [col for col in required_cols if col not in dea_result.columns]
    if missing_cols:
        raise ValueError(f"DEA-resultat saknar obligatoriska kolumner: {missing_cols}")
    
    # Hämta organisation och skapa export-katalog
    org = get_user_org(session_state)
    export_dir = Path(ensure_org_dir(BASE_EXPORT_DIR, session_state))
    
    # Skapa filnamn med timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    safe_name = "".join(c for c in scenario_name if c.isalnum() or c in ['_', '-']).lower()
    if not safe_name:
        safe_name = "unnamed"
    
    filename = f"ir_effkrav_{safe_name}_{timestamp}.parquet"
    filepath = export_dir / filename
    
    # Förbered minimal export-data (endast det som IR behöver)
    export_cols = ['DMU', 'REId', 'Effkrav_proc']
    
    # Lägg till Företag om den finns (hjälpsam för IR-UI)
    if 'Företag' in dea_result.columns:
        export_cols.insert(2, 'Företag')
    
    final_export = dea_result[export_cols].copy()
    
    # Exportera som parquet
    final_export.to_parquet(filepath, index=False)
    
    # Beräkna sammanfattning för feedback
    summary = {
        "reid_count": len(final_export),
        "dmu_count": final_export['DMU'].nunique(),
        "mean_effkrav_pct": float(final_export['Effkrav_proc'].mean() * 100),
        "min_effkrav_pct": float(final_export['Effkrav_proc'].min() * 100),
        "max_effkrav_pct": float(final_export['Effkrav_proc'].max() * 100),
    }
    
    # Skapa metadata-fil
    metadata = {
        "description": "Effektiviseringskrav-procent från DEA för applicering i IR-dekomposition",
        "scenario_name": scenario_name,
        "organization": org,
        "analysis_method": _extract_analysis_method(dea_result),
        "export_timestamp": datetime.now().isoformat(),
        "application_note": "Appliceras i IR på antingen OPEX eller TOTEX enligt användarval",
        "data_format": {
            "DMU": "DMU-nummer (integer)",
            "REId": "Redovisningsenhet ID (string)",
            "Företag": "Företagsnamn (string, optional)",
            "Effkrav_proc": "Årligt effektiviseringskrav (decimal, t.ex. 0.0125 = 1.25%)"
        },
        **summary  # Merge summary into metadata
    }
    
    # Lägg till extra DEA-metadata om tillgänglig
    if 'Effektivitet' in dea_result.columns:
        metadata['mean_efficiency'] = float(dea_result['Effektivitet'].mean())
    
    if 'is_outlier' in dea_result.columns:
        metadata['outlier_count'] = int(dea_result['is_outlier'].sum())
    
    metadata_path = filepath.with_suffix('.json')
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    
    # Returnera sökvägar och sammanfattning
    return str(filepath), str(metadata_path), summary


def _extract_analysis_method(dea_result: pd.DataFrame) -> str:
    """Extraherar analysmetod från DEA-resultat om tillgänglig."""
    if 'Analysis_Method' in dea_result.columns:
        return dea_result['Analysis_Method'].iloc[0] if not dea_result.empty else "DEA"
    return "DEA"


def list_available_scenarios(
    session_state: Optional[Dict[str, Any]] = None
) -> pd.DataFrame:
    """
    Listar alla tillgängliga effektiviseringskrav-scenarion för aktuell organisation.
    
    UPPDATERAD: Letar efter nya filnamn (ir_effkrav_*.parquet)
    
    Args:
        session_state: Session state dict (optional)
        
    Returns:
        DataFrame med kolumner:
        - filename: Filnamn
        - scenario_name: Scenario-namn från metadata
        - timestamp: Export-tidsstämpel
        - reid_count: Antal REId
        - mean_effkrav_pct: Medel effektiviseringskrav (%)
        - filepath: Fullständig sökväg
    """
    org = get_user_org(session_state)
    export_dir = Path(BASE_EXPORT_DIR) / org
    
    if not export_dir.exists():
        return pd.DataFrame(columns=[
            'filename', 'scenario_name', 'timestamp', 
            'reid_count', 'mean_effkrav_pct', 'filepath'
        ])
    
    scenarios = []
    
    # Sök både nya och gamla filnamn för bakåtkompatibilitet
    pattern_list = ["ir_effkrav_*.parquet", "ir_paverkbara_*.parquet"]
    
    for pattern in pattern_list:
        for parquet_file in sorted(export_dir.glob(pattern)):
            meta_file = parquet_file.with_suffix('.json')
            
            if meta_file.exists():
                try:
                    with open(meta_file, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                    
                    scenarios.append({
                        'filename': parquet_file.name,
                        'scenario_name': metadata.get('scenario_name', 'Unknown'),
                        'timestamp': metadata.get('export_timestamp', 'Unknown'),
                        'reid_count': metadata.get('reid_count', 0),
                        'mean_effkrav_pct': metadata.get('mean_effkrav_pct', 0),
                        'filepath': str(parquet_file)
                    })
                except Exception:
                    # Skippa filer med korrupt metadata
                    continue
    
    return pd.DataFrame(scenarios)


def load_scenario(
    filepath: str
) -> Tuple[pd.DataFrame, dict]:
    """
    Laddar ett sparat effektiviseringskrav-scenario.
    
    Args:
        filepath: Sökväg till parquet-fil
        
    Returns:
        Tuple med:
        - data: DataFrame med scenario-data (REId, DMU, Effkrav_proc)
        - metadata: Dict med metadata
        
    Raises:
        FileNotFoundError: Om fil eller metadata saknas
        ValueError: Om data är korrupt
    """
    parquet_path = Path(filepath)
    meta_path = parquet_path.with_suffix('.json')
    
    if not parquet_path.exists():
        raise FileNotFoundError(f"Scenario-fil hittades inte: {filepath}")
    
    if not meta_path.exists():
        raise FileNotFoundError(f"Metadata-fil hittades inte: {meta_path}")
    
    try:
        data = pd.read_parquet(parquet_path)
    except Exception as e:
        raise ValueError(f"Kunde inte läsa scenario-data: {e}")
    
    try:
        with open(meta_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
    except Exception as e:
        raise ValueError(f"Kunde inte läsa metadata: {e}")
    
    return data, metadata


def delete_scenario(
    filepath: str
) -> bool:
    """
    Raderar ett scenario (både data och metadata).
    
    Args:
        filepath: Sökväg till parquet-fil
        
    Returns:
        True om lyckad radering, False annars
    """
    parquet_path = Path(filepath)
    meta_path = parquet_path.with_suffix('.json')
    
    success = True
    
    if parquet_path.exists():
        try:
            parquet_path.unlink()
        except Exception:
            success = False
    
    if meta_path.exists():
        try:
            meta_path.unlink()
        except Exception:
            success = False
    
    return success
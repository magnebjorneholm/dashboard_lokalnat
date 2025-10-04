"""
Backend för export av IR-påverkbara kostnader.
===============================================

Hanterar filskrivning och metadata-generering för IR-scenarion.
Använder session_utils för organisationsspecifika kataloger.

DESIGN:
- UI-agnostisk: tar session_state som optional parameter
- Skriver parquet + JSON metadata
- Returnerar sökvägar för UI-feedback
- Inga Streamlit/Dash imports
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


def export_ir_paverkbara_scenario(
    export_data: pd.DataFrame,
    scenario_name: str,
    session_state: Optional[Dict[str, Any]] = None
) -> Tuple[str, str, dict]:
    """
    Exporterar påverkbara kostnader till organisationsspecifik katalog.
    
    Skapar två filer:
    1. Parquet-fil med data
    2. JSON-fil med metadata
    
    Args:
        export_data: DataFrame från calculate_ir_paverkbara_export()
        scenario_name: Namn på scenariot (används i filnamn)
        session_state: Session state dict (optional, för org-identifiering)
        
    Returns:
        Tuple med:
        - data_path: Sökväg till parquet-fil
        - meta_path: Sökväg till metadata-fil
        - summary: Dict med sammanfattning för UI-feedback
        
    Raises:
        ValueError: Om export_data saknar obligatoriska kolumner
    """
    # Validera input
    required_cols = [
        'DMU', 'REId', 'Paverkbara_Baseline_4yr', 
        'Paverkbara_Target', 'Effektiviseringskrav', 'Total_Reduction_tkr'
    ]
    
    missing_cols = [col for col in required_cols if col not in export_data.columns]
    if missing_cols:
        raise ValueError(f"Export data saknar obligatoriska kolumner: {missing_cols}")
    
    # Hämta organisation och skapa export-katalog
    org = get_user_org(session_state)
    export_dir = Path(ensure_org_dir(BASE_EXPORT_DIR, session_state))
    
    # Skapa filnamn med timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    safe_name = "".join(c for c in scenario_name if c.isalnum() or c in ['_', '-']).lower()
    if not safe_name:
        safe_name = "unnamed"
    
    filename = f"ir_paverkbara_{safe_name}_{timestamp}.parquet"
    filepath = export_dir / filename
    
    # Förbered final export-data (endast nödvändiga kolumner för IR)
    export_cols = [
        'DMU', 'REId', 'Paverkbara_Baseline_4yr', 'Paverkbara_Target', 
        'Effektiviseringskrav', 'Total_Reduction_tkr'
    ]
    
    # Lägg till Företag om den finns
    if 'Företag' in export_data.columns:
        export_cols.insert(2, 'Företag')
    
    # Lägg till Analysis_Method om den finns
    if 'Analysis_Method' in export_data.columns:
        export_cols.append('Analysis_Method')
    
    final_export = export_data[export_cols].copy()
    
    # Exportera som parquet
    final_export.to_parquet(filepath, index=False)
    
    # Beräkna sammanfattning
    summary = {
        "reid_count": len(final_export),
        "total_baseline_tkr": float(final_export['Paverkbara_Baseline_4yr'].sum()),
        "total_target_tkr": float(final_export['Paverkbara_Target'].sum()),
        "total_reduction_tkr": float(final_export['Total_Reduction_tkr'].sum()),
        "mean_effkrav_pct": float(final_export['Effektiviseringskrav'].mean() * 100),
    }
    
    # Skapa metadata-fil
    metadata = {
        "description": "Påverkbara kostnader baserat på DEA-effektiviseringskrav för IR-dekomposition",
        "scenario_name": scenario_name,
        "organization": org,
        "analysis_method": export_data.get('Analysis_Method', ['DEA_corrected_exact_columns'])[0] 
                          if 'Analysis_Method' in export_data.columns else "DEA_corrected_exact_columns",
        "export_timestamp": datetime.now().isoformat(),
        "price_year": 2022,
        "unit": "tkr",
        "level": "REId",
        "period": "2024-2027",
        **summary  # Merge summary into metadata
    }
    
    metadata_path = filepath.with_suffix('.json')
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    
    # Returnera sökvägar och sammanfattning
    return str(filepath), str(metadata_path), summary


def list_available_scenarios(
    session_state: Optional[Dict[str, Any]] = None
) -> pd.DataFrame:
    """
    Listar alla tillgängliga IR-påverkbara scenarion för aktuell organisation.
    
    Args:
        session_state: Session state dict (optional)
        
    Returns:
        DataFrame med kolumner:
        - filename: Filnamn
        - scenario_name: Scenario-namn från metadata
        - timestamp: Export-tidsstämpel
        - reid_count: Antal REId
        - total_reduction_msek: Total reduktion i MSEK
        - filepath: Fullständig sökväg
    """
    org = get_user_org(session_state)
    export_dir = Path(BASE_EXPORT_DIR) / org
    
    if not export_dir.exists():
        return pd.DataFrame(columns=[
            'filename', 'scenario_name', 'timestamp', 
            'reid_count', 'total_reduction_msek', 'filepath'
        ])
    
    scenarios = []
    
    for parquet_file in sorted(export_dir.glob("ir_paverkbara_*.parquet")):
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
                    'total_reduction_msek': metadata.get('total_reduction_tkr', 0) / 1000,
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
    Laddar ett sparat scenario från parquet + metadata.
    
    Args:
        filepath: Sökväg till parquet-fil
        
    Returns:
        Tuple med:
        - data: DataFrame med scenario-data
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
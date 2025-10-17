"""
effektiviseringskrav/backend/ir_export.py
Export av effektiviseringskrav för intäktsram-användning

FÖRENKLAD VERSION: Exporterar BARA effektiviseringskrav-procent + DMU/REId.
IR-baseline laddas lokalt i intäktsramen när beräkning sker.
"""

import os
import json
from datetime import datetime
from typing import Tuple
from pathlib import Path
import pandas as pd

from core.session_utils import ensure_org_dir, get_user_org


def export_effektiviseringskrav_scenario(
    dea_result: pd.DataFrame,
    base_dir: str = "scenario/effektiviseringskrav/exports_to_ir"
) -> Tuple[str, str]:
    """
    Exporterar effektiviseringskrav för företagsanvändning.
    
    ENKEL VERSION - exporterar bara:
    - DMU
    - REId
    - Företag (om den finns)
    - Effkrav_proc
    
    Metod (OPEX/TOTEX) väljs vid import i Intäktsram-tabben.
    IR-baseline laddas lokalt i intäktsramen när beräkning sker.
    
    Args:
        dea_result: DataFrame med DEA-resultat (kolumner: DMU, REId, Effkrav_proc)
        base_dir: Baskatalog för export
        
    Returns:
        Tuple med (data_path, meta_path)
        
    Raises:
        ValueError: Om dea_result saknar kolumner
    """
    # Validera DEA-resultat
    required_cols = ['DMU', 'REId', 'Effkrav_proc']
    missing_cols = [col for col in required_cols if col not in dea_result.columns]
    if missing_cols:
        raise ValueError(f"DEA-resultat saknar kolumner: {missing_cols}")
    
    # Välj kolumner att exportera
    export_cols = ['DMU', 'REId', 'Effkrav_proc']
    
    # Lägg till Företag om den finns
    if 'Företag' in dea_result.columns:
        export_cols.insert(2, 'Företag')
    
    # Lägg till Effektivitet om den finns (för metadata/diagnostik)
    if 'Effektivitet' in dea_result.columns:
        export_cols.append('Effektivitet')
    
    export_data = dea_result[export_cols].copy()
    
    if export_data.empty:
        raise ValueError("Ingen data att exportera")
    
    # Lägg till timestamp-kolumn
    export_data['Export_Timestamp'] = datetime.now().isoformat()
    
    # Skapa organisationsspecifik katalog
    org = get_user_org()
    export_dir = ensure_org_dir(base_dir)
    
    # Filnamn baserat på timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    data_filename = f"ir_effkrav_company_{timestamp}.parquet"
    data_path = os.path.join(export_dir, data_filename)
    meta_path = data_path.replace(".parquet", ".json")
    
    # Skriv data
    export_data.to_parquet(data_path, index=False)
    
    # Skapa metadata
    metadata = {
        "description": (
            "Effektiviseringskrav för företagsanvändning. "
            "Innehåller endast effektiviseringskrav-procent. "
            "Metod (OPEX/TOTEX) väljs vid import. "
            "IR-baseline laddas lokalt i intäktsramen."
        ),
        "organization": org,
        "export_type": "company_use",
        "period": {
            "start": 2024,
            "end": 2027
        },
        "price_year": 2022,
        "unit": "procent för Effkrav_proc",
        "export_timestamp": datetime.now().isoformat(),
        "reid_count": len(export_data),
        "dmu_count": export_data['DMU'].nunique(),
        "mean_effkrav_pct": float(export_data['Effkrav_proc'].mean() * 100),
        "file_format": "parquet",
        "data_file": data_filename,
        "usage": (
            "Importera i företagsvy, välj OPEX/TOTEX. "
            "Beräkning sker automatiskt mot IR-baseline och aktuell kapitalkostnad."
        )
    }
    
    # Skriv metadata
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    print(f"Export klar: {data_filename}")
    print(f"  - {len(export_data)} REId")
    print(f"  - {export_data['DMU'].nunique()} DMU")
    print(f"  - Medel effektiviseringskrav: {metadata['mean_effkrav_pct']:.2f}%")
    
    return data_path, meta_path
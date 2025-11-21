"""
effektiviseringskrav/backend/ir_export.py
Export av effektivitetsvärden för intäktsram-användning

Exporterar effektivitet, supereffektivitet och potential.
Effektiviseringskrav beräknas i intäktsram-tabben baserat på användarens val.
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
    Exporterar effektivitetsvärden för företagsanvändning.
    
    Exporterar:
    - DMU
    - REId
    - Företag (om den finns)
    - Effektivitet (för diagnostik)
    - Supereffektivitet (för outlier-identifikation)
    - potential (1 - effektivitet, för beräkning av effektiviseringskrav)
    - is_outlier (flagga)
    
    Användaren väljer trunkering, outlier-definition och metod (OPEX/TOTEX) 
    vid import i Intäktsram-tabben.
    
    Args:
        dea_result: DataFrame med DEA-resultat
        base_dir: Baskatalog för export
        
    Returns:
        Tuple med (data_path, meta_path)
        
    Raises:
        ValueError: Om dea_result saknar kolumner
    """
    # Validera DEA-resultat
    required_cols = ['DMU', 'REId', 'Effektivitet', 'Supereffektivitet', 'potential', 'is_outlier']
    missing_cols = [col for col in required_cols if col not in dea_result.columns]
    if missing_cols:
        raise ValueError(f"DEA-resultat saknar kolumner: {missing_cols}")
    
    # Välj kolumner att exportera
    export_cols = ['DMU', 'REId', 'Effektivitet', 'Supereffektivitet', 'potential', 'is_outlier']
    
    # Lägg till Företag om den finns
    if 'Företag' in dea_result.columns:
        export_cols.insert(2, 'Företag')
    
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
            "Effektivitetsvärden för företagsanvändning. "
            "Innehåller effektivitet, supereffektivitet, potential och outlier-flagga. "
            "Effektiviseringskrav beräknas i intäktsram-tabben baserat på "
            "användarens val av trunkering, outlier-definition och metod (OPEX/TOTEX)."
        ),
        "organization": org,
        "export_type": "company_use",
        "period": {
            "start": 2024,
            "end": 2027
        },
        "price_year": 2022,
        "export_timestamp": datetime.now().isoformat(),
        "reid_count": len(export_data),
        "dmu_count": export_data['DMU'].nunique(),
        "mean_efficiency": float(export_data['Effektivitet'].mean()),
        "mean_potential": float(export_data['potential'].mean()),
        "outlier_count": int(export_data['is_outlier'].sum()),
        "file_format": "parquet",
        "data_file": data_filename,
        "usage": (
            "Importera i företagsvy för intäktsram-dekomposition. "
            "Välj trunkering, outlier-definition och metod (OPEX/TOTEX) vid import. "
            "Beräkning av effektiviseringskrav sker automatiskt."
        )
    }
    
    # Skriv metadata
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    print(f"Export klar: {data_filename}")
    print(f"  - {len(export_data)} REId")
    print(f"  - {export_data['DMU'].nunique()} DMU")
    print(f"  - Medeleffektivitet: {metadata['mean_efficiency']:.3f}")
    print(f"  - Outliers: {metadata['outlier_count']}")
    
    return data_path, meta_path
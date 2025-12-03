"""
effektivitet/backend/sfa_export.py
Export av SFA-resultat för intäktsram-användning.
"""

import os
import json
from datetime import datetime
from typing import Tuple
from pathlib import Path
import pandas as pd

from core.session_utils import ensure_org_dir, get_user_org


def export_sfa_results_to_ir(
    sfa_result: pd.DataFrame,
    base_dir: str = "scenario/effektiviseringskrav/exports_to_ir"
) -> Tuple[str, str]:
    """
    Exporterar SFA-resultat för intäktsram-användning.
    
    Exporterar:
    - DMU, REId, Företag
    - Effektivitet (TE_SFA)
    - potential (1 - effektivitet)
    - is_outlier (flagga)
    
    Args:
        sfa_result: DataFrame med SFA-resultat
        base_dir: Baskatalog för export
        
    Returns:
        Tuple med (data_path, meta_path)
    """
    # Validera SFA-resultat
    required_cols = ['DMU', 'REId', 'TE_SFA', 'potential', 'is_outlier']
    missing_cols = [col for col in required_cols if col not in sfa_result.columns]
    if missing_cols:
        raise ValueError(f"SFA-resultat saknar kolumner: {missing_cols}")
    
    # Välj kolumner att exportera
    export_cols = ['DMU', 'REId', 'TE_SFA', 'potential', 'is_outlier']
    
    # Lägg till Företag om den finns
    if 'Företag' in sfa_result.columns:
        export_cols.insert(2, 'Företag')
    
    # Byt namn på TE_SFA till Effektivitet för konsistens med DEA
    export_data = sfa_result[export_cols].copy()
    export_data = export_data.rename(columns={'TE_SFA': 'Effektivitet'})
    
    if export_data.empty:
        raise ValueError("Ingen data att exportera")
    
    # Lägg till timestamp och metod-markör
    export_data['Export_Timestamp'] = datetime.now().isoformat()
    export_data['Method'] = 'SFA'
    
    # Skapa organisationsspecifik katalog
    org = get_user_org()
    export_dir = ensure_org_dir(base_dir)
    
    # Filnamn baserat på timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    data_filename = f"ir_effkrav_sfa_{timestamp}.parquet"
    data_path = os.path.join(export_dir, data_filename)
    meta_path = data_path.replace(".parquet", ".json")
    
    # Skriv data
    export_data.to_parquet(data_path, index=False)
    
    # Skapa metadata
    metadata = {
        "description": (
            "SFA-effektivitetsvärden för intäktsram-användning. "
            "Innehåller teknisk effektivitet, potential och outlier-flagga. "
            "Effektiviseringskrav beräknas i intäktsram-tabben."
        ),
        "method": "SFA",
        "export_timestamp": datetime.now().isoformat(),
        "n_companies": len(export_data),
        "n_outliers": int(export_data['is_outlier'].sum()),
        "mean_efficiency": float(export_data['Effektivitet'].mean()),
        "columns": list(export_data.columns)
    }
    
    with open(meta_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    return data_path, meta_path
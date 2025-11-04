"""
foretag/view/scenario_utils.py
Delad logik för scenario-hantering
"""

import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Tuple
import json

from core.session_utils import ensure_org_dir


def list_available_kapitalbas_scenarios() -> pd.DataFrame:
    """
    Listar tillgängliga kapitalbas-exports för aktuell organisation.
    
    Returns:
        DataFrame med kolumner: filename, wacc_tag, timestamp, filepath
    """
    export_dir = Path(ensure_org_dir("scenario/kapitalbas/exports_to_ir"))
    
    if not export_dir.exists():
        return pd.DataFrame(columns=['filename', 'wacc_tag', 'timestamp', 'filepath'])
    
    scenarios = []
    
    for parquet_file in sorted(export_dir.glob("ir_kapkost_wacc_*.parquet")):
        json_file = parquet_file.with_suffix('.json')
        
        if json_file.exists():
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                
                wacc_new = metadata.get('wacc_new', 0)
                timestamp = metadata.get('export_timestamp', 'Unknown')
                
                scenarios.append({
                    'filename': parquet_file.name,
                    'wacc_tag': f"{wacc_new*100:.2f}%" if wacc_new else "N/A",
                    'timestamp': timestamp,
                    'filepath': str(parquet_file)
                })
            except Exception:
                continue
    
    return pd.DataFrame(scenarios)


def list_saved_scenarios() -> List[Tuple[str, str]]:
    """
    Listar sparade scenarier för aktuell organisation.
    
    Returns:
        Lista av tupler: (scenario_namn, filepath)
    """
    scenario_dir = Path(ensure_org_dir("scenario/saved"))
    
    if not scenario_dir.exists():
        return []
    
    scenarios = []
    
    for parquet_file in sorted(scenario_dir.glob("ir_scenario_*.parquet"), 
                               key=lambda p: p.stat().st_mtime, 
                               reverse=True):
        try:
            df = pd.read_parquet(parquet_file)
            metadata = df.attrs.get('scenario_metadata', {})
            name = metadata.get('name', parquet_file.stem)
            scenarios.append((name, str(parquet_file)))
        except Exception:
            continue
    
    return scenarios


def load_scenario_from_file(filepath: str) -> Tuple[pd.DataFrame, dict]:
    """
    Laddar scenario från parquet-fil.
    
    Args:
        filepath: Sökväg till scenario-fil
        
    Returns:
        Tuple av (DataFrame, metadata_dict)
    """
    df = pd.read_parquet(filepath)
    metadata = df.attrs.get('scenario_metadata', {})
    return df, metadata


def save_scenario_to_file(scenario_name: str, df_data: pd.DataFrame) -> str:
    """
    Sparar scenario till parquet-fil.
    
    Args:
        scenario_name: Namn på scenario
        df_data: DataFrame med scenario-data
        
    Returns:
        Sökväg till sparad fil
    """
    scenario_dir = Path(ensure_org_dir("scenario/saved"))
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"ir_scenario_{scenario_name.replace(' ', '_')}_{timestamp}.parquet"
    filepath = scenario_dir / filename
    
    from core.session_utils import get_user_org
    
    scenario_metadata = {
        'name': scenario_name,
        'organization': get_user_org(),
        'created': datetime.now().isoformat(),
        'modifications': st.session_state.scenario_data.get('modifications', {}),
        'component_sources': st.session_state.scenario_data.get('component_sources', {})
    }
    
    df_data.attrs['scenario_metadata'] = scenario_metadata
    df_data.to_parquet(filepath)
    
    return str(filepath)


def create_scenario(name: str, baseline_df: pd.DataFrame) -> bool:
    """
    Skapar nytt scenario med frysta baseline-kolumner.
    
    Args:
        name: Scenario-namn
        baseline_df: Baseline DataFrame
        
    Returns:
        True om scenario skapades, False om namn redan finns
    """
    name = name.strip()
    
    if not name:
        st.sidebar.error("Scenario-namn får inte vara tomt")
        return False
    
    saved_scenarios = list_saved_scenarios()
    existing_names = [s[0] for s in saved_scenarios]
    
    if name in existing_names:
        st.sidebar.error(f"Scenario '{name}' finns redan. Välj ett annat namn.")
        return False
    
    baseline_snapshot = baseline_df.copy()
    
    baseline_snapshot['Paverkbara_Kostnader_Baseline'] = baseline_snapshot['Paverkbara_Kostnader']
    baseline_snapshot['Opaverkbara_Kostnader_Baseline'] = baseline_snapshot['Opaverkbara_Kostnader']
    baseline_snapshot['Kapitalkostnad_Total_Baseline'] = baseline_snapshot['Kapitalkostnad_Total']
    baseline_snapshot['Intaktsram_Total_Baseline'] = baseline_snapshot['Intaktsram_Total']
    
    if 'Avskrivningar' in baseline_snapshot.columns:
        baseline_snapshot['Avskrivningar_Baseline'] = baseline_snapshot['Avskrivningar']
    if 'Avkastning' in baseline_snapshot.columns:
        baseline_snapshot['Avkastning_Baseline'] = baseline_snapshot['Avkastning']
    
    st.session_state.current_scenario_name = name
    st.session_state.scenario_data = {
        'baseline': baseline_snapshot,
        'modifications': {},
        'created': datetime.now(),
        'component_sources': {
            'paverkbara': 'baseline',
            'kapitalkostnad': 'baseline'
        }
    }
    
    return True


def reset_to_baseline():
    """Återställer alla komponenter till baseline."""
    if st.session_state.current_scenario_name:
        st.session_state.current_scenario_name = ""
        st.session_state.scenario_data = {}
        st.session_state.scenarios = {}
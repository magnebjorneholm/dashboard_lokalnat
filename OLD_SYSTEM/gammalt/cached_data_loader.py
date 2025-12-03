"""
Cached Data Loader
Cachade versioner av tunga data-laddnings operationer.
Minskar antal Excel-läsningar och förbättrar prestanda.
"""

import streamlit as st
import pandas as pd
from typing import Dict, Any


@st.cache_data(ttl=3600)
def load_baseline_data_cached(filepath: str) -> pd.DataFrame:
    """
    Cachad laddning av baseline intäktsram-data från Excel.
    Cache gäller i 1 timme.
    
    Args:
        filepath: Sökväg till Excel-fil
        
    Returns:
        DataFrame med baseline-data
    """
    from core.data_loader_intaktsram import load_baseline_data
    return load_baseline_data(filepath)


@st.cache_data(ttl=3600)
def load_reference_dea_cached() -> pd.DataFrame:
    """
    Cachad laddning av Ei:s referens-DEA resultat.
    Cache gäller i 1 timme.
    
    Returns:
        DataFrame med DEA-resultat
    """
    from effektivitet.backend.reference_dea_loader import load_reference_dea
    return load_reference_dea()


@st.cache_data(ttl=3600)
def get_reference_efficiency_cached(dmu: int) -> Dict[str, Any]:
    """
    Cachad hämtning av referens-effektivitet för ett företag.
    Cache gäller i 1 timme.
    
    Args:
        dmu: Företags-DMU
        
    Returns:
        Dictionary med effektivitetsdata
    """
    from effektivitet.backend.reference_dea_loader import get_reference_efficiency_for_dmu
    return get_reference_efficiency_for_dmu(dmu)


@st.cache_data(ttl=3600)
def load_ir_paverkbara_baseline_cached(filepath: str) -> pd.DataFrame:
    """
    Cachad laddning av påverkbara kostnader baseline från Excel.
    Cache gäller i 1 timme.
    
    Args:
        filepath: Sökväg till Excel-fil
        
    Returns:
        DataFrame med påverkbara kostnader
    """
    # The IR "påverkbara" baseline loader lives in the effektivitet backend
    # (implements Excel-exact parsing). Import from there instead of core.
    from effektivitet.backend.ir_calculations import load_ir_paverkbara_baseline
    return load_ir_paverkbara_baseline(filepath)


@st.cache_data
def prepare_diagram_data_cached(
    _entity_data_dict: Dict,
    _baseline_df_dict: Dict,
    modifications_hash: str
) -> Dict:
    """
    Cachad förberedelse av diagram-data.
    Cache invalideras när modifications_hash ändras.
    
    Args:
        _entity_data_dict: Entity data som dict (för hashability)
        _baseline_df_dict: Baseline DataFrame som dict
        modifications_hash: Hash av applied_modifications
        
    Returns:
        Dictionary med diagram-data
    """
    from intaktsram.frontend.intaktsram_dekomposition import prepare_diagram_data
    import pandas as pd
    
    # Konvertera tillbaka till pandas objects
    entity_data = pd.Series(_entity_data_dict)
    baseline_df = pd.DataFrame(_baseline_df_dict)
    
    return prepare_diagram_data(entity_data, baseline_df)


@st.cache_data(ttl=3600)
def load_reconciliation_foretag_info_cached() -> Dict[str, Any]:
    """
    Cachad laddning av företagsinformation för reconciliation.
    Cache gäller i 1 timme.
    
    Returns:
        Dictionary med företagsinformation
    """
    from core.session_utils import load_reconciliation_foretag_info
    return load_reconciliation_foretag_info()


@st.cache_data(ttl=3600)
def load_ei_effektiviseringskrav_cached(filepath: str, reid: str) -> float:
    """
    Cachad hämtning av Ei:s effektiviseringskrav från Excel kolumn DZ.
    Cache gäller i 1 timme.
    
    Args:
        filepath: Sökväg till Excel-fil
        reid: Lokalnät-ID
        
    Returns:
        Totalt avdrag (summa 4 år)
    """
    try:
        df = pd.read_excel(filepath, sheet_name="Påverkbara", engine="openpyxl")
        
        # Kolumn DZ = index 129 (totalt avdrag)
        if len(df.columns) > 129:
            reid_col = df.iloc[:, 0]
            matching_rows = df[reid_col == reid]
            
            if not matching_rows.empty:
                avdrag_value = matching_rows.iloc[0, 129]
                return float(avdrag_value) if pd.notna(avdrag_value) else 0.0
    except Exception:
        pass
    
    return 0.0


def clear_all_caches():
    """
    Rensar alla cachade data.
    Använd vid scenario-byte eller när fresh data behövs.
    """
    st.cache_data.clear()
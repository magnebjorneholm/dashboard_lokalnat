"""
Baseline Loaders - Ladda baseline data från Excel-filer

Producerar baseline-värden för:
- WACC
- CAPEX  
- OPEX (påverkbara och opåverkbara)
- Volumes (CU, MW, NS, MWhl, MWhh)

Data laddas från Data_modeller.xlsx
"""

import pandas as pd
from typing import Dict, Any
from pathlib import Path


def _load_data_modeller() -> pd.DataFrame:
    """
    Laddar Data_modeller.xlsx med DEA-data.
    
    Returns:
        DataFrame med kolumner:
        ['DMU', 'REId', 'Företag', 'OPEXp', 'CAPEX', 'CU', 'MW', 'NS', 'MWhl', 'MWhh']
    """
    # Sökväg till data
    data_file = Path("Data_modeller.xlsx")
    
    # Alternativa sökvägar (projektrot, container mount, eller central data-mapp)
    if not data_file.exists():
        data_file = Path("/mnt/project/Data_modeller.xlsx")
    if not data_file.exists():
        data_file = Path("data/Data_modeller.xlsx")
    if not data_file.exists():
        data_file = Path("effektivitet/data/Data_modeller.xlsx")
    
    if not data_file.exists():
        raise FileNotFoundError(
            "Kunde inte hitta Data_modeller.xlsx. "
            "Kontrollera att filen finns i projektroten eller effektivitet/data/"
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
    
    # Beräkna TOTEX
    df["TOTEX"] = df["OPEXp"] + df["CAPEX"]
    
    return df


def produce_wacc_from_baseline() -> float:
    """
    Producera baseline WACC.
    
    Ei's baseline WACC för reguleringsperioden 2024-2027 är 4.53%.
    
    Returns:
        WACC i decimal form (0.0453)
    """
    return 0.0453


def produce_capex_from_baseline() -> pd.DataFrame:
    """
    Producera baseline CAPEX från Data_modeller.xlsx.
    
    Returns:
        DataFrame med kolumner:
        ['DMU', 'REId', 'Företag', 'CAPEX']
        
    Enhet: TSEK (tusen kronor)
    """
    df = _load_data_modeller()
    
    # Returnera bara relevanta kolumner
    return df[['DMU', 'REId', 'Företag', 'CAPEX']].copy()


def produce_opex_paverkbara_from_baseline() -> pd.DataFrame:
    """
    Producera baseline påverkbara OPEX från Data_modeller.xlsx.
    
    Returns:
        DataFrame med kolumner:
        ['DMU', 'REId', 'Företag', 'OPEXp']
        
    Enhet: TSEK (tusen kronor)
    """
    df = _load_data_modeller()
    
    # Returnera bara relevanta kolumner
    return df[['DMU', 'REId', 'Företag', 'OPEXp']].copy()


def produce_opex_opaverkbara_from_baseline() -> pd.DataFrame:
    """
    Producera baseline opåverkbara OPEX.
    
    OBS: Data_modeller.xlsx innehåller endast OPEXp (påverkbara).
    Opåverkbara OPEX laddas från annan källa (Löpande kostnader från SDF).
    
    För nu returnerar vi en placeholder DataFrame.
    
    Returns:
        DataFrame med kolumner:
        ['DMU', 'REId', 'Företag', 'OPEXi']
        
    Enhet: TSEK (tusen kronor)
    """
    df = _load_data_modeller()
    
    # Placeholder - opåverkbara OPEX finns inte i Data_modeller.xlsx
    # I produktion skulle denna ladda från Löpande kostnader-filen
    result = df[['DMU', 'REId', 'Företag']].copy()
    result['OPEXi'] = 0.0  # Placeholder
    
    return result


def produce_volumes_from_baseline() -> pd.DataFrame:
    """
    Producera baseline volumes från Data_modeller.xlsx.
    
    Returns:
        DataFrame med kolumner:
        ['DMU', 'REId', 'Företag', 'CU', 'MW', 'NS', 'MWhl', 'MWhh']
        
    Enheter:
    - CU: Antal kunder
    - MW: Installerad effekt (MW)
    - NS: Nätlängd (km)
    - MWhl: Överförd energi låglast (MWh)
    - MWhh: Överförd energi höglast (MWh)
    """
    df = _load_data_modeller()
    
    # Returnera volumes-kolumner
    volume_cols = ['DMU', 'REId', 'Företag', 'CU', 'MW', 'NS', 'MWhl', 'MWhh']
    return df[volume_cols].copy()


def produce_capex_baseline_value() -> pd.DataFrame:
    """
    Producera baseline CAPEX (samma som produce_capex_from_baseline).
    
    Denna används specifikt för wacc_scaling producer.
    
    Returns:
        DataFrame med baseline CAPEX
    """
    return produce_capex_from_baseline()


def get_baseline_summary() -> Dict[str, Any]:
    """
    Hämta sammanfattning av baseline data.
    
    Användbart för debugging och översikt.
    
    Returns:
        Dict med summerad statistik
    """
    try:
        df = _load_data_modeller()
        
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
            'baseline_wacc': 0.0453
        }
    except Exception as e:
        return {
            'error': str(e)
        }


def load_baseline_data() -> Dict[str, Any]:
    """
    Convenience wrapper that returns baseline data in a dict-form
    expected by the VariableResolver and the Streamlit app.

    Keys included (non-exhaustive):
      - 'wacc': float
      - 'capex': DataFrame
      - 'capex_baseline': DataFrame (same as capex)
      - 'opex_paverkbara': DataFrame
      - 'opex_opaverkbara': DataFrame
      - 'volumes': DataFrame
      - 'capbase_a': DataFrame (if available)
      - 'baseline_summary': dict
      - 'intaktsram_total': float (placeholder if not available)

    Returns:
        dict
    """
    try:
        capex_df = produce_capex_from_baseline()
    except Exception:
        capex_df = None

    try:
        wacc_val = produce_wacc_from_baseline()
    except Exception:
        wacc_val = 0.0453

    try:
        opex_p_df = produce_opex_paverkbara_from_baseline()
    except Exception:
        opex_p_df = None

    try:
        opex_i_df = produce_opex_opaverkbara_from_baseline()
    except Exception:
        opex_i_df = None

    try:
        volumes_df = produce_volumes_from_baseline()
    except Exception:
        volumes_df = None

    summary = get_baseline_summary()

    # Try to include a capbase_a if present in the workbook (some producers expect it)
    capbase_a = None
    try:
        # Some pipelines expect a DataFrame named capbase_a; try to reuse capex_df if it fits
        if capex_df is not None:
            capbase_a = capex_df.copy()
    except Exception:
        capbase_a = None

    return {
        'wacc': wacc_val,
        'capex': capex_df,
        'capex_baseline': capex_df,
        'opex_paverkbara': opex_p_df,
        'opex_opaverkbara': opex_i_df,
        'volumes': volumes_df,
        'capbase_a': capbase_a,
        'baseline_summary': summary,
        'intaktsram_total': summary.get('total_totex_tsek', 0) if isinstance(summary, dict) else 0
    }
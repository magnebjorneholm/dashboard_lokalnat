"""
core/data_loader_dea.py

DEA-specifik datainläsning.
Laddar DEA-basdata från Excel.
"""

import pandas as pd


def load_data(filepath: str) -> pd.DataFrame:
    """
    Läser DEA-bas från Excel (blad 'Körning') och skapar TOTEX = OPEXp + CAPEX.

    Args:
        filepath: Sökväg till Excel-fil (vanligtvis Data_modeller.xlsx)

    Returns:
        DataFrame med kolumner:
        ['DMU', 'REId', 'Företag', 'OPEXp', 'CAPEX', 'CU', 'MW', 'NS', 'MWhl', 'MWhh', 'TOTEX']

    Enhet: tkr (tusen kronor)
    """
    try:
        df = pd.read_excel(filepath, sheet_name="Körning", engine="openpyxl")
    except Exception as e:
        raise RuntimeError(f"Fel vid inläsning av fil: {e}")

    expected = ['DMU', 'REId', 'Företag', 'OPEXp', 'CAPEX', 'CU', 'MW', 'NS', 'MWhl', 'MWhh']
    missing = [c for c in expected if c not in df.columns]
    if missing:
        raise ValueError(f"Saknade kolumner i Excel-filen: {missing}")

    # Säkerställ numerik för kostnader
    for c in ['OPEXp', 'CAPEX']:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    # Beräkna TOTEX
    df["TOTEX"] = df["OPEXp"] + df["CAPEX"]
    df.reset_index(drop=True, inplace=True)

    return df
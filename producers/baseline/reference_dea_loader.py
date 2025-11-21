"""
Reference DEA Loader - Ladda Ei's baseline efficiency från EIs_DEA.xlsx

Producerar baseline efficiency-värden från Ei's DEA-analys.
"""

import pandas as pd
from typing import Dict, Any
from pathlib import Path


def _load_eis_dea() -> pd.DataFrame:
    """
    Laddar Ei:s referens-DEA resultat från Excel.
    
    Returns:
        DataFrame med kolumner:
        - DMU: Företags-DMU
        - REId: Lokalnät-ID
        - Företag: Företagsnamn
        - Effektivitet: Effektivitetsvärde (eller 'OUTLIER')
        - Supereffektivitet: Supereffektivitetsvärde (eller 'OUTLIER')
        - potential: Förbättringspotential
        - Effkrav_proc: Årligt effektiviseringskrav
    """
    # Sökväg till data
    data_file = Path("EIs_DEA.xlsx")
    
    # Alternativa sökvägar
    if not data_file.exists():
        data_file = Path("/mnt/project/EIs_DEA.xlsx")
    if not data_file.exists():
        data_file = Path("data/EIs_DEA.xlsx")
    if not data_file.exists():
        data_file = Path("effektivitet/data/EIs_DEA.xlsx")
    
    if not data_file.exists():
        raise FileNotFoundError(
            "Kunde inte hitta EIs_DEA.xlsx. "
            "Kontrollera att filen finns i projektroten eller effektivitet/data/"
        )
    
    try:
        df = pd.read_excel(data_file, sheet_name='Körning', engine='openpyxl')
        return df
    except Exception as e:
        raise RuntimeError(f"Fel vid inläsning av EIs_DEA.xlsx: {e}")


def produce_efficiency_from_baseline() -> pd.DataFrame:
    """
    Producera baseline efficiency från Ei's DEA-analys.
    
    Returns:
        DataFrame med kolumner:
        ['DMU', 'REId', 'Företag', 'Effektivitet', 'Supereffektivitet', 
         'potential', 'Effkrav_proc', 'is_outlier']
        
    Effektivitet är 0-1 scale (där 1 = 100% effektiv)
    Outliers har Effektivitet = None
    """
    df = _load_eis_dea()
    
    # Hantera outliers
    df['is_outlier'] = df['Effektivitet'].astype(str).str.upper() == 'OUTLIER'
    
    # Konvertera Effektivitet till float (None för outliers)
    def parse_efficiency(val):
        if str(val).upper() == 'OUTLIER':
            return None
        try:
            return float(val)
        except (ValueError, TypeError):
            return None
    
    df['Effektivitet'] = df['Effektivitet'].apply(parse_efficiency)
    df['Supereffektivitet'] = df['Supereffektivitet'].apply(parse_efficiency)
    
    # Hantera potential
    def parse_potential(val):
        try:
            return float(val)
        except (ValueError, TypeError):
            return 0.0
    
    df['potential'] = df['potential'].apply(parse_potential)
    
    # Konvertera Effkrav_proc till float
    df['Effkrav_proc'] = pd.to_numeric(df['Effkrav_proc'], errors='coerce').fillna(0.0)
    
    return df


def get_efficiency_for_dmu(dmu: int) -> Dict[str, Any]:
    """
    Hämta efficiency för ett specifikt DMU.
    
    Args:
        dmu: DMU-nummer
        
    Returns:
        Dict med efficiency data:
        {
            'DMU': int,
            'REId': str,
            'Företag': str,
            'Effektivitet': float eller None,
            'Supereffektivitet': float eller None,
            'potential': float,
            'Effkrav_proc': float,
            'is_outlier': bool
        }
        
    Raises:
        ValueError: Om DMU inte finns
    """
    df = produce_efficiency_from_baseline()
    
    company = df[df['DMU'] == dmu]
    
    if company.empty:
        raise ValueError(f"DMU {dmu} finns inte i Ei's DEA-data")
    
    row = company.iloc[0]
    
    return {
        'DMU': int(row['DMU']),
        'REId': str(row['REId']),
        'Företag': str(row['Företag']),
        'Effektivitet': row['Effektivitet'],
        'Supereffektivitet': row['Supereffektivitet'],
        'potential': row['potential'],
        'Effkrav_proc': row['Effkrav_proc'],
        'is_outlier': row['is_outlier']
    }


def get_efficiency_for_reid(reid: str) -> Dict[str, Any]:
    """
    Hämta efficiency för ett specifikt lokalnät.
    
    Args:
        reid: Lokalnät-ID (t.ex. 'REL00001')
        
    Returns:
        Dict med efficiency data
        
    Raises:
        ValueError: Om REId inte finns
    """
    df = produce_efficiency_from_baseline()
    
    network = df[df['REId'] == reid]
    
    if network.empty:
        raise ValueError(f"REId {reid} finns inte i Ei's DEA-data")
    
    row = network.iloc[0]
    
    return {
        'DMU': int(row['DMU']),
        'REId': str(row['REId']),
        'Företag': str(row['Företag']),
        'Effektivitet': row['Effektivitet'],
        'Supereffektivitet': row['Supereffektivitet'],
        'potential': row['potential'],
        'Effkrav_proc': row['Effkrav_proc'],
        'is_outlier': row['is_outlier']
    }


def get_efficiency_summary() -> Dict[str, Any]:
    """
    Hämta sammanfattning av efficiency data.
    
    Returns:
        Dict med statistik
    """
    try:
        df = produce_efficiency_from_baseline()
        
        # Filtrera bort outliers för statistik
        valid_eff = df[df['Effektivitet'].notna()]['Effektivitet']
        
        return {
            'n_total': len(df),
            'n_valid': len(valid_eff),
            'n_outliers': df['is_outlier'].sum(),
            'mean_efficiency': float(valid_eff.mean()) if len(valid_eff) > 0 else None,
            'median_efficiency': float(valid_eff.median()) if len(valid_eff) > 0 else None,
            'min_efficiency': float(valid_eff.min()) if len(valid_eff) > 0 else None,
            'max_efficiency': float(valid_eff.max()) if len(valid_eff) > 0 else None,
            'mean_effkrav_pct': float(df['Effkrav_proc'].mean()) if 'Effkrav_proc' in df.columns else None
        }
    except Exception as e:
        return {
            'error': str(e)
        }
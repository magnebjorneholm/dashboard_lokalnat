"""
Hanterar laddning av referens-DEA data från Ei:s baseline-körning.
Används för att hämta baseline-effektivitetsvärden för företag.
"""

import pandas as pd
from typing import Optional


def load_reference_dea() -> pd.DataFrame:
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
    filepath = "effektivitet/data/EIs_DEA.xlsx"
    
    try:
        df = pd.read_excel(filepath, sheet_name='Körning', engine='openpyxl')
        return df
    except Exception as e:
        raise FileNotFoundError(f"Kunde inte ladda referens-DEA från {filepath}: {e}")


def get_reference_efficiency_for_dmu(dmu: int) -> Optional[dict]:
    """
    Hämtar referens-effektivitetsvärde för ett specifikt företag.
    
    Args:
        dmu: Företagets DMU
        
    Returns:
        Dictionary med effektivitetsdata eller None om inte hittat:
        {
            'DMU': int,
            'REId': str,
            'Företag': str,
            'Effektivitet': float eller None (om outlier),
            'Supereffektivitet': float eller None (om outlier),
            'potential': float,
            'Effkrav_proc': float,
            'is_outlier': bool
        }
    """
    df = load_reference_dea()
    
    company = df[df['DMU'] == dmu]
    
    if company.empty:
        return None
    
    row = company.iloc[0]
    
    # Hantera outliers
    is_outlier = str(row['Effektivitet']).upper() == 'OUTLIER'
    
    if is_outlier:
        effektivitet = None
        supereffektivitet = None
        potential = 0.0
    else:
        effektivitet = float(row['Effektivitet'])
        supereffektivitet = float(row['Supereffektivitet'])
        try:
            potential = float(row['potential'])
        except (ValueError, TypeError):
            potential = 0.0
    
    return {
        'DMU': int(row['DMU']),
        'REId': str(row['REId']),
        'Företag': str(row['Företag']),
        'Effektivitet': effektivitet,
        'Supereffektivitet': supereffektivitet,
        'potential': potential,
        'Effkrav_proc': float(row['Effkrav_proc']),
        'is_outlier': is_outlier
    }


def get_reference_efficiency_for_reid(reid: str) -> Optional[dict]:
    """
    Hämtar referens-effektivitetsvärde för ett specifikt lokalnät.
    
    Args:
        reid: Lokalnät-ID (REL00001 etc)
        
    Returns:
        Dictionary med effektivitetsdata eller None om inte hittat
    """
    df = load_reference_dea()
    
    network = df[df['REId'] == reid]
    
    if network.empty:
        return None
    
    row = network.iloc[0]
    
    # Hantera outliers
    is_outlier = str(row['Effektivitet']).upper() == 'OUTLIER'
    
    if is_outlier:
        effektivitet = None
        supereffektivitet = None
        potential = 0.0
    else:
        effektivitet = float(row['Effektivitet'])
        supereffektivitet = float(row['Supereffektivitet'])
        try:
            potential = float(row['potential'])
        except (ValueError, TypeError):
            potential = 0.0
    
    return {
        'DMU': int(row['DMU']),
        'REId': str(row['REId']),
        'Företag': str(row['Företag']),
        'Effektivitet': effektivitet,
        'Supereffektivitet': supereffektivitet,
        'potential': potential,
        'Effkrav_proc': float(row['Effkrav_proc']),
        'is_outlier': is_outlier
    }
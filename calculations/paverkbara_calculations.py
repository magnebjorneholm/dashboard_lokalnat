"""
calculations/paverkbara_calculations.py

Beräkningar för påverkbara kostnader med effektiviseringskrav.
Stöder både OPEX-metod (traditionell) och TOTEX-metod (Ei 2020).

TOTEX-metod: Effektiviseringskravet läggs på OPEX + CAPEX, men reduktionen
allokeras proportionellt och appliceras separat på respektive kostnadskomponent.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple


def calculate_paverkbara_with_effkrav(
    effkrav_data: pd.DataFrame,
    sdf_baseline: pd.DataFrame,
    capex_data: pd.DataFrame,
    method: str = 'OPEX'
) -> pd.DataFrame:
    """
    Beräknar påverkbara kostnader med effektiviseringskrav för alla företag.
    
    Implementerar Ei's metod:
    1. Definiera startvärde (OPEX: endast påverkbara, TOTEX: påverkbara + CAPEX/4)
    2. Beräkna årliga avdrag med compound growth
    3. Beräkna påverkbara per år (2024-2027)
    4. Summera periodsumma
    5. För TOTEX: Allokera effektivisering proportionellt mellan OPEX och CAPEX
    
    Args:
        effkrav_data: DataFrame med REId, Effkrav_proc (från effektiviseringskrav stage)
        sdf_baseline: DataFrame med REId, Paverkbara_Medelvarde, Neonjusteringar
        capex_data: DataFrame med REId, Kapitalkostnad_Total (periodsumma 2024-2027)
        method: 'OPEX' eller 'TOTEX'
        
    Returns:
        DataFrame med kolumner:
        - REId
        - Paverkbara_2024, Paverkbara_2025, Paverkbara_2026, Paverkbara_2027
        - Paverkbara_Periodsumma
        - Method_used
        - OPEX_Fore, OPEX_Efter, OPEX_Effektivisering
        - CAPEX_Fore, CAPEX_Efter, CAPEX_Effektivisering
    """
    if method not in ['OPEX', 'TOTEX']:
        raise ValueError(f"Method måste vara 'OPEX' eller 'TOTEX', fick '{method}'")
    
    # Merge alla datasets på REId
    df = effkrav_data[['REId', 'Effkrav_proc']].copy()
    
    # Merge med SDF baseline
    df = df.merge(
        sdf_baseline[['REId', 'Paverkbara_Medelvarde', 'Neonjusteringar']],
        on='REId',
        how='left'
    )
    
    # Merge med CAPEX data (behövs för TOTEX, och för CAPEX_Fore även i OPEX-läge)
    if 'Kapitalkostnad_Total' in capex_data.columns:
        df = df.merge(
            capex_data[['REId', 'Kapitalkostnad_Total']],
            on='REId',
            how='left'
        )
        df['Kapitalkostnad_Total'] = df['Kapitalkostnad_Total'].fillna(0)
    else:
        df['Kapitalkostnad_Total'] = 0
    
    # Validera att vi har data
    required_cols = ['REId', 'Effkrav_proc', 'Paverkbara_Medelvarde', 'Neonjusteringar']
    missing = [col for col in required_cols if col not in df.columns or df[col].isna().all()]
    if missing:
        raise ValueError(f"Saknade eller tomma kolumner: {missing}")
    
    # Beräkna för varje företag
    results = []
    
    for _, row in df.iterrows():
        result = _calculate_paverkbara_single_company(
            reid=row['REId'],
            effkrav_proc=row['Effkrav_proc'],
            paverkbara_medelvarde=row['Paverkbara_Medelvarde'],
            neonjusteringar=row['Neonjusteringar'],
            kapitalkostnad_total=row.get('Kapitalkostnad_Total', 0),
            method=method
        )
        results.append(result)
    
    return pd.DataFrame(results)


def _calculate_paverkbara_single_company(
    reid: str,
    effkrav_proc: float,
    paverkbara_medelvarde: float,
    neonjusteringar: float,
    kapitalkostnad_total: float,
    method: str
) -> Dict[str, Any]:
    """
    Beräknar påverkbara kostnader för ett enskilt företag.
    
    Beräkningskedja (enligt Ei's metod):
    1. Startvärde = Påverkbara_Medelvärde (OPEX) eller + CAPEX/4 (TOTEX)
    2. Årlig_Justering = Neonjusteringar / 4
    3. Årsbas_Effkrav = Startvärde + Årlig_Justering
    4. För varje år t:
       - Tillväxtfaktor_t = (1 + effkrav)^(t-1)
       - Årligt_Avdrag_t = effkrav * Årsbas * Tillväxtfaktor_t
       - Kumulativt_Avdrag_t = sum(Årligt_Avdrag[1:t+1])
       - Påverkbara_t = Startvärde - Kumulativt_Avdrag_t + Årlig_Justering
    5. Periodsumma = sum(Påverkbara[2024:2028])
    6. För TOTEX: Allokera effektivisering proportionellt mellan OPEX och CAPEX
    
    Args:
        reid: REId för företaget
        effkrav_proc: Årligt effektiviseringskrav (decimal)
        paverkbara_medelvarde: Medelvärde påverkbara 2018-2021 (tkr, årligt)
        neonjusteringar: Neonjusteringar (tkr, 4-års periodsumma)
        kapitalkostnad_total: Total kapitalkostnad 2024-2027 (tkr, 4-års periodsumma)
        method: 'OPEX' eller 'TOTEX'
        
    Returns:
        Dict med resultat för detta företag
    """
    arlig_justering = neonjusteringar / 4
    
    # OPEX-bas (årlig)
    opex_bas_arlig = paverkbara_medelvarde + arlig_justering
    
    # CAPEX-bas (årlig) - endast relevant för TOTEX
    capex_bas_arlig = kapitalkostnad_total / 4
    
    # Definiera startvärde för effektiviseringsberäkning
    if method == 'OPEX':
        startvarde = paverkbara_medelvarde
        total_bas_arlig = opex_bas_arlig
    else:  # TOTEX
        startvarde = paverkbara_medelvarde + capex_bas_arlig
        total_bas_arlig = opex_bas_arlig + capex_bas_arlig
    
    arsbas_effkrav = startvarde + arlig_justering

    # Beräkna årliga värden och total effektivisering
    paverkbara_per_ar = {}
    kumulativt_avdrag = 0
    
    for t in range(1, 5):  # t = 1,2,3,4 för 2024,2025,2026,2027
        tillvaxtfaktor = (1 + effkrav_proc) ** (t - 1)
        arligt_avdrag = effkrav_proc * arsbas_effkrav * tillvaxtfaktor
        kumulativt_avdrag += arligt_avdrag
        paverkbara_efter_avdrag = startvarde - kumulativt_avdrag + arlig_justering
        year = 2023 + t
        paverkbara_per_ar[f'Paverkbara_{year}'] = paverkbara_efter_avdrag
    
    # Total effektivisering (periodsumma)
    total_fore = (startvarde + arlig_justering) * 4
    total_efter = sum(paverkbara_per_ar.values())
    effektivisering_total = total_fore - total_efter
    
    # Beräkna OPEX/CAPEX-andelar och allokera effektivisering
    if method == 'OPEX' or total_bas_arlig == 0:
        opex_andel = 1.0
        capex_andel = 0.0
    else:  # TOTEX
        opex_andel = opex_bas_arlig / total_bas_arlig
        capex_andel = capex_bas_arlig / total_bas_arlig
    
    # OPEX före/efter (periodsumma)
    opex_fore = opex_bas_arlig * 4
    opex_effektivisering = effektivisering_total * opex_andel
    opex_efter = opex_fore - opex_effektivisering
    
    # CAPEX före/efter (periodsumma)
    if method == 'TOTEX':
        capex_fore = kapitalkostnad_total
        capex_effektivisering = effektivisering_total * capex_andel
        capex_efter = capex_fore - capex_effektivisering
    else:
        capex_fore = kapitalkostnad_total  # Visa CAPEX även i OPEX-läge (för referens)
        capex_effektivisering = 0.0
        capex_efter = capex_fore  # Ingen reduktion i OPEX-läge
    
    # Returnera resultat
    result = {
        'REId': reid,
        'Method_used': method,
        
        # Legacy-fält (bakåtkompatibilitet)
        'Paverkbara_Fore_Periodsumma': total_fore,
        'Paverkbara_Periodsumma': total_efter,
        'Effektivisering_Total': effektivisering_total,
        
        # Nya separata OPEX-fält (50.4.1, 50.4.3)
        'OPEX_Fore': opex_fore,
        'OPEX_Efter': opex_efter,
        'OPEX_Effektivisering': opex_effektivisering,
        
        # Nya separata CAPEX-fält (50.4.2, 50.4.4)
        'CAPEX_Fore': capex_fore,
        'CAPEX_Efter': capex_efter,
        'CAPEX_Effektivisering': capex_effektivisering,
        
        # Andelar (för transparens)
        'OPEX_Andel': opex_andel,
        'CAPEX_Andel': capex_andel,
    }
    result.update(paverkbara_per_ar)
    
    return result


def get_paverkbara_from_sdf(
    sdf_ir: pd.DataFrame,
    sdf_paverkbara: pd.DataFrame
) -> pd.DataFrame:
    """
    Extraherar påverkbara baseline-data från SDF Excel.

    KRITISKT: Använder MEDELVÄRDE 2018-2021 från Påverkbara-sheet,
    INTE periodsumman från IR-sheet!

    Args:
        sdf_ir: DataFrame från sheet "IR 2024-2027" (används ej längre för medelvärde)
        sdf_paverkbara: DataFrame från sheet "Påverkbara"
        
    Returns:
        DataFrame med REId, Paverkbara_Medelvarde, Neonjusteringar
    """
    # REId kolumn kan heta 'REid' eller 'REId' i Påverkbara sheet
    reid_col = 'REid' if 'REid' in sdf_paverkbara.columns else 'REId'
    
    # Kolumn 123: "Medelvärde 2018-2021 påverkbara kostnader"
    medelvarde_col = None
    for col in sdf_paverkbara.columns:
        col_lower = col.lower()
        if ('medelvärde' in col_lower or 'medelvarde' in col_lower) and '2018-2021' in col_lower:
            medelvarde_col = col
            break
    
    if medelvarde_col is None:
        raise ValueError(
            "Kunde inte hitta kolumn 'Medelvärde 2018-2021 påverkbara kostnader' "
            "i Påverkbara sheet. Kontrollera Excel-fil struktur."
        )
    
    # Kolumn 124: Neonjusteringar (separerat yrkandet)
    neojust_col = None
    for col in sdf_paverkbara.columns:
        if 'separerat yrkandet' in col.lower():
            neojust_col = col
            break
    
    if neojust_col is None:
        # Fallback: Leta efter annan neonjusteringskolumn
        for col in sdf_paverkbara.columns:
            if 'neojust' in col.lower() or ('neo' in col.lower() and 'andr' in col.lower()):
                neojust_col = col
                break
    
    # Extrahera data
    result = sdf_paverkbara[[reid_col, medelvarde_col]].copy()
    result.columns = ['REId', 'Paverkbara_Medelvarde']
    
    # Lägg till neonjusteringar
    if neojust_col:
        result['Neonjusteringar'] = sdf_paverkbara[neojust_col]
    else:
        result['Neonjusteringar'] = 0
    
    # Fyll NaN med 0
    result['Neonjusteringar'] = result['Neonjusteringar'].fillna(0)
    result['Paverkbara_Medelvarde'] = result['Paverkbara_Medelvarde'].fillna(0)
    
    return result


# Default metod
DEFAULT_PAVERKBARA_METHOD = 'OPEX'
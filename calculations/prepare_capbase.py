"""
calculations/prepare_capbase.py

Förbereder capbase_a för beräkningar efter RAB-editor ändringar.

Huvudfunktion:
    prepare_capbase_for_calculations(df) → df med omberäknad nuav_2022

Beräknar nuav_2022 från rådata baserat på vtype:
    - vtype=4: normvärde × count_comp (lookup från normvärdeslista om techspec ändrats)
    - vtype=1: annatskäligtvärde × count_comp
    - vtype=2: rapporteradnuav
    - vtype=5: value_invest
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, Tuple

# Importera från våra nya moduler
from .rab_editor_variables import (
    VType,
    beräkna_nuav_2022,
    validera_komponent,
    KATEGORIER,
)
from data.normvärdelista import (
    get_normvärde,
    get_normvärde_info,
    lookup_by_techspec,
    NORMVÄRDEN,
)

def prepare_capbase_for_calculations(
    df: pd.DataFrame,
    recalculate_all: bool = False,
) -> pd.DataFrame:
    """
    Förbereder capbase_a för kent_calculations efter RAB-editor ändringar.
    
    Denna funktion:
    1. Beräknar om nuav_2022 från rådata baserat på vtype
    2. Slår upp normvärden om techspec/volt ändrats (vtype=4)
    3. Validerar data
    4. Säkerställer att livslängder finns
    
    Args:
        df: DataFrame med capbase_a data (kan ha användarändringar)
        recalculate_all: Om True, beräkna om alla rader. 
                        Om False, beräkna bara rader markerade som ändrade.
    
    Returns:
        DataFrame redo för run_kent_calculations_batch()
    """
    df = df.copy()
    
    # Säkerställ att vtype finns
    if 'vtype' not in df.columns:
        raise ValueError("DataFrame saknar 'vtype' kolumn")
    
    # Beräkna nuav_2022 per vtype
    df = _recalculate_nuav_vtype4(df)
    df = _recalculate_nuav_vtype1(df)
    df = _recalculate_nuav_vtype2(df)
    df = _recalculate_nuav_vtype5(df)
    
    # Säkerställ livslängder från kategori
    df = _ensure_lifetimes(df)
    
    # Validera
    errors = _validate_capbase(df)
    if errors:
        # Logga varningar men fortsätt
        for err in errors[:10]:  # Max 10 fel
            print(f"Varning: {err}")
    
    return df


def _recalculate_nuav_vtype4(df: pd.DataFrame) -> pd.DataFrame:
    """
    Beräknar om nuav_2022 för vtype=4 (normvärderade).
    
    Formel: nuav_2022 = normvärde × count_comp
    
    Om id_comptype finns, använd det för lookup.
    Annars försök lookup via techspec+volt.
    """
    mask = df['vtype'] == VType.NORMVÄRDE
    
    if not mask.any():
        return df
    
    for idx in df[mask].index:
        row = df.loc[idx]
        
        # Hämta normvärde
        normvärde = row.get('normvärde', 0)
        
        # Om id_comptype finns, verifiera/uppdatera normvärde
        id_comptype = row.get('id_comptype')
        if pd.notna(id_comptype) and id_comptype in NORMVÄRDEN:
            nv_info = NORMVÄRDEN[id_comptype]
            normvärde = nv_info.normvärde
            df.loc[idx, 'normvärde'] = normvärde
        
        # Beräkna nuav_2022
        count_comp = row.get('count_comp', 0)
        if pd.notna(count_comp) and pd.notna(normvärde):
            df.loc[idx, 'nuav_2022'] = normvärde * count_comp
    
    return df


def _recalculate_nuav_vtype1(df: pd.DataFrame) -> pd.DataFrame:
    """
    Beräknar om nuav_2022 för vtype=1 (annat skäligt värde).
    
    Formel: nuav_2022 = annatskäligtvärde × count_comp
    """
    mask = df['vtype'] == VType.ANNAT_SKÄLIGT_VÄRDE
    
    if not mask.any():
        return df
    
    annatskäligt = df.loc[mask, 'annatskäligtvärde'].fillna(0)
    count_comp = df.loc[mask, 'count_comp'].fillna(0)
    
    df.loc[mask, 'nuav_2022'] = annatskäligt * count_comp
    
    return df


def _recalculate_nuav_vtype2(df: pd.DataFrame) -> pd.DataFrame:
    """
    Beräknar om nuav_2022 för vtype=2 (anskaffningsvärde).
    
    Formel: nuav_2022 = rapporteradnuav
    """
    mask = df['vtype'] == VType.ANSKAFFNINGSVÄRDE
    
    if not mask.any():
        return df
    
    df.loc[mask, 'nuav_2022'] = df.loc[mask, 'rapporteradnuav'].fillna(0)
    
    return df


def _recalculate_nuav_vtype5(df: pd.DataFrame) -> pd.DataFrame:
    """
    Beräknar om nuav_2022 för vtype=5 (investering/utrangering).
    
    Formel: nuav_2022 = value_invest (redan teckensatt)
    """
    mask = df['vtype'] == VType.INVESTERING
    
    if not mask.any():
        return df
    
    df.loc[mask, 'nuav_2022'] = df.loc[mask, 'value_invest'].fillna(0)
    
    return df


def _ensure_lifetimes(df: pd.DataFrame) -> pd.DataFrame:
    """
    Säkerställer att ekdep och maxdep finns baserat på cat_encode.
    
    Om livslängder saknas, hämta från KATEGORIER.
    """
    if 'ekdep' not in df.columns:
        df['ekdep'] = np.nan
    if 'maxdep' not in df.columns:
        df['maxdep'] = np.nan
    
    # Fyll i saknade livslängder från kategori
    for idx in df.index:
        cat_encode = df.loc[idx, 'cat_encode']
        
        if pd.isna(cat_encode):
            continue
        
        cat_encode = int(cat_encode)
        if cat_encode in KATEGORIER:
            kat = KATEGORIER[cat_encode]
            
            if pd.isna(df.loc[idx, 'ekdep']):
                df.loc[idx, 'ekdep'] = kat.ekdep
            
            if pd.isna(df.loc[idx, 'maxdep']):
                df.loc[idx, 'maxdep'] = kat.maxdep
    
    return df


def _validate_capbase(df: pd.DataFrame) -> list:
    """
    Validerar capbase_a data.
    
    Returns:
        Lista med felmeddelanden (tom om valid)
    """
    errors = []
    
    # Kontrollera obligatoriska kolumner
    required_cols = ['id_component', 'id_network', 'vtype', 'nuav_2022', 'cat_encode']
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        errors.append(f"Saknar kolumner: {missing}")
        return errors
    
    # Kontrollera att nuav_2022 är numerisk
    if not pd.api.types.is_numeric_dtype(df['nuav_2022']):
        errors.append("nuav_2022 är inte numerisk")
    
    # Kontrollera NaN i kritiska fält
    nan_nuav = df['nuav_2022'].isna().sum()
    if nan_nuav > 0:
        errors.append(f"{nan_nuav} rader har NaN i nuav_2022")
    
    # Kontrollera vtype-värden
    valid_vtypes = {1, 2, 4, 5}
    invalid_vtypes = set(df['vtype'].dropna().unique()) - valid_vtypes
    if invalid_vtypes:
        errors.append(f"Ogiltiga vtype-värden: {invalid_vtypes}")
    
    # Kontrollera att count_comp > 0 för vtype 1 och 4
    for vtype in [1, 4]:
        mask = df['vtype'] == vtype
        if mask.any():
            invalid_count = (df.loc[mask, 'count_comp'] <= 0).sum()
            if invalid_count > 0:
                errors.append(f"vtype={vtype}: {invalid_count} rader har count_comp <= 0")
    
    return errors


def update_normvärde_from_techspec(
    df: pd.DataFrame,
    idx: int,
    kategori: str,
    typ_anläggning: str,
    techspec: str,
    volt: str = None,
) -> pd.DataFrame:
    """
    Uppdaterar normvärde och id_comptype när användaren byter techspec.
    
    Används av RAB-editor UI när techspec-dropdown ändras.
    
    Args:
        df: DataFrame att uppdatera
        idx: Index för raden att uppdatera
        kategori: Anläggningskategori
        typ_anläggning: Typ av anläggning (subkategori)
        techspec: Ny teknisk specifikation
        volt: Spänningsnivå (valfritt)
    
    Returns:
        Uppdaterad DataFrame
    """
    result = lookup_by_techspec(kategori, typ_anläggning, techspec, volt)
    
    if result is None:
        raise ValueError(f"Kunde inte hitta normvärde för {techspec} ({kategori}/{typ_anläggning})")
    
    kod, normvärde = result
    
    df = df.copy()
    df.loc[idx, 'id_comptype'] = kod
    df.loc[idx, 'techspec'] = techspec
    df.loc[idx, 'normvärde'] = normvärde
    
    # Beräkna om nuav_2022
    count_comp = df.loc[idx, 'count_comp']
    if pd.notna(count_comp):
        df.loc[idx, 'nuav_2022'] = normvärde * count_comp
    
    return df


def create_new_investment(
    id_network: int,
    cat_encode: int,
    subcat: str,
    value: float,
    time_invest: int,
    is_retirement: bool = False,
) -> Dict:
    """
    Skapar en ny investering eller utrangering.
    
    Args:
        id_network: Företagets id_network
        cat_encode: Anläggningskategori (1-17)
        subcat: Underkategori (text)
        value: Belopp (positivt tal)
        time_invest: Tidskod för halvår (229-236)
        is_retirement: True för utrangering, False för investering
    
    Returns:
        Dict med komponentdata redo att lägga till i capbase
    """
    if cat_encode not in KATEGORIER:
        raise ValueError(f"Ogiltig kategori: {cat_encode}")
    
    kat = KATEGORIER[cat_encode]
    invest_sign = -1 if is_retirement else 1
    
    return {
        'id_network': id_network,
        'vtype': VType.INVESTERING,
        'cat_encode': cat_encode,
        'cat': kat.namn,
        'subcat': subcat,
        'value_invest': value * invest_sign,  # Teckensätt
        'invest': invest_sign,
        'time_invest': time_invest,
        'time_from': time_invest,
        'count_comp': 1.0,
        'nuav_2022': value * invest_sign,
        'capbase_existing': 0,
        'owned': 1,
        'ekdep': kat.ekdep,
        'maxdep': kat.maxdep,
    }


def create_new_component_vtype1(
    id_network: int,
    cat_encode: int,
    subcat: str,
    annatskäligtvärde: float,
    count_comp: float,
    time_from: int,
) -> Dict:
    """
    Skapar en ny komponent med annat skäligt värde (vtype=1).
    
    Args:
        id_network: Företagets id_network
        cat_encode: Anläggningskategori (1-17)
        subcat: Underkategori (text)
        annatskäligtvärde: Värde per enhet i kr
        count_comp: Antal enheter
        time_from: Tidskod för idrifttagande
    
    Returns:
        Dict med komponentdata
    """
    if cat_encode not in KATEGORIER:
        raise ValueError(f"Ogiltig kategori: {cat_encode}")
    
    kat = KATEGORIER[cat_encode]
    
    return {
        'id_network': id_network,
        'vtype': VType.ANNAT_SKÄLIGT_VÄRDE,
        'cat_encode': cat_encode,
        'cat': kat.namn,
        'subcat': subcat,
        'annatskäligtvärde': annatskäligtvärde,
        'count_comp': count_comp,
        'time_from': time_from,
        'nuav_2022': annatskäligtvärde * count_comp,
        'capbase_existing': 1,
        'owned': 1,
        'ekdep': kat.ekdep,
        'maxdep': kat.maxdep,
    }
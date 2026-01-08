"""
calculations/rab_editor_utils.py

Hjälpfunktioner för RAB-editor session state-hantering.

RAB-editorn låter användaren redigera sin kapitalbas direkt i UI.
Alla ändringar lagras i session state och konverteras till capbase_a
format för beräkningskedjan.

Session state struktur:
    st.session_state["rab_editor"] = {
        "original_components": pd.DataFrame,   # Omodifierad kopia
        "modified_components": pd.DataFrame,   # Med ändringar
        "added_components": List[Dict],        # Nya komponenter
        "removed_ids": Set[int],               # id_component att exkludera
        "id_network": int,                     # Aktivt företag
    }

Integrerar med:
    - rab_editor_variables.py: Tidskoder, vtype-definitioner, validering
    - prepare_capbase.py: NUAV-beräkning från rådata
    - normvärdeslista.py: Normvärde-lookup för techspec-ändringar
"""

import pandas as pd
import numpy as np
import streamlit as st
from typing import Dict, List, Set, Optional, Any, Tuple

# Importera från våra moduler (undvik duplicering)
from .rab_editor_variables import (
    VType,
    VTYPE_NAMN,
    KATEGORIER,
    timecode_to_year,
    year_to_timecode,
    HALFYEAR_TO_TIMECODE,
    TIMECODE_TO_HALFYEAR,
    TIMECODE_PERIOD_START,
    TIMECODE_PERIOD_END,
    get_redigerbara_fält,
    validera_komponent,
)

from .prepare_capbase import (
    prepare_capbase_for_calculations,
    update_normvärde_from_techspec,
    create_new_investment,
    create_new_component_vtype1,
)

from data.normvärdelista import (
    get_normvärde,
    get_normvärde_info,
    lookup_by_techspec,
    list_techspecs_for_category,
    list_typ_anläggning,
    list_categories,
    KATEGORI_TILL_CAT_ENCODE,
)


# =============================================================================
# TIDSKOD-HJÄLPFUNKTIONER (re-exportera för bakåtkompatibilitet)
# =============================================================================

def time_code_to_year(time_code: int) -> int:
    """
    Konverterar tidskod till år (ignorerar halvår).
    
    Args:
        time_code: Tidskod (t.ex. 221)
    
    Returns:
        År (t.ex. 2020)
    """
    if pd.isna(time_code) or time_code <= 0:
        return 0
    return int(timecode_to_year(time_code))


def year_to_time_code(year: int, half_year: int = 1) -> int:
    """
    Konverterar år (och halvår) till tidskod.
    
    Args:
        year: År (t.ex. 2020)
        half_year: Halvår (1 eller 2)
    
    Returns:
        Tidskod (t.ex. 221 för 2020H1)
    """
    return year_to_timecode(year, half_year)


def time_code_to_half_year(time_code: int) -> int:
    """
    Extraherar halvår från tidskod.
    
    Args:
        time_code: Tidskod
    
    Returns:
        Halvår (1 eller 2)
    """
    if pd.isna(time_code) or time_code <= 0:
        return 1
    return ((time_code - 1) % 2) + 1


def get_halfyear_options() -> List[Tuple[str, int]]:
    """
    Returnerar lista med halvårsalternativ för dropdown.
    
    Returns:
        Lista med tuples (visningstext, tidskod)
    """
    return [(label, code) for label, code in HALFYEAR_TO_TIMECODE.items()]


# =============================================================================
# INITIALISERING
# =============================================================================

def initialize_rab_editor(user_components: pd.DataFrame, id_network: int) -> None:
    """
    Initierar RAB-editor session state med användarens komponenter.
    
    Anropas när användaren öppnar RAB-editorn första gången eller
    när företag byts.
    
    Args:
        user_components: DataFrame med användarens komponenter från capbase_a
        id_network: Användarens id_network
    """
    current_id = st.session_state.get("rab_editor", {}).get("id_network")
    
    # Initiera om RAB-editor inte finns eller om företag byts
    if "rab_editor" not in st.session_state or current_id != id_network:
        st.session_state["rab_editor"] = {
            "original_components": user_components.copy(),
            "modified_components": user_components.copy(),
            "added_components": [],
            "removed_ids": set(),
            "id_network": id_network,
        }


def reset_rab_editor() -> None:
    """Återställer alla ändringar till originaldata."""
    rab = st.session_state.get("rab_editor", {})
    if rab and "original_components" in rab:
        rab["modified_components"] = rab["original_components"].copy()
        rab["added_components"] = []
        rab["removed_ids"] = set()


def clear_rab_editor() -> None:
    """Tar bort RAB-editor från session state helt."""
    if "rab_editor" in st.session_state:
        del st.session_state["rab_editor"]


# =============================================================================
# HÄMTA DATA
# =============================================================================

def get_user_capbase_with_edits() -> pd.DataFrame:
    """
    Returnerar användarens kapitalbas med alla redigeringar applicerade.
    
    Denna funktion skapar en capbase_a DataFrame redo för 
    run_kent_calculations_batch(). Den:
    1. Tar modified_components (med ändringar)
    2. Exkluderar borttagna komponenter
    3. Lägger till nya komponenter
    4. Beräknar om nuav_2022 från rådata
    
    Returns:
        DataFrame redo för run_kent_calculations_batch()
    
    Raises:
        ValueError: Om RAB-editor inte är initierad
    """
    rab = st.session_state.get("rab_editor", {})
    
    if not rab:
        raise ValueError("RAB-editor inte initierad")
    
    if "modified_components" not in rab:
        raise ValueError("RAB-editor saknar modified_components")
    
    id_network = rab.get("id_network")
    if id_network is None:
        raise ValueError("RAB-editor saknar id_network")
    
    # Börja med modifierade komponenter
    df = rab["modified_components"].copy()
    
    # Exkludera borttagna
    removed_ids = rab.get("removed_ids", set())
    if removed_ids:
        df = df[~df['id_component'].isin(removed_ids)]
    
    # Lägg till nya komponenter
    added = rab.get("added_components", [])
    if added:
        df_added = pd.DataFrame(added)
        df = pd.concat([df, df_added], ignore_index=True)
    
    # Säkerställ id_network
    df['id_network'] = id_network
    
    # Beräkna om nuav_2022 från rådata
    df = prepare_capbase_for_calculations(df)
    
    return df


def get_original_components() -> Optional[pd.DataFrame]:
    """Returnerar originalkomponenterna (omodifierade)."""
    rab = st.session_state.get("rab_editor", {})
    return rab.get("original_components")


def get_modified_components() -> Optional[pd.DataFrame]:
    """Returnerar modifierade komponenter."""
    rab = st.session_state.get("rab_editor", {})
    return rab.get("modified_components")


def get_added_components() -> List[Dict]:
    """Returnerar lista med tillagda komponenter."""
    rab = st.session_state.get("rab_editor", {})
    return rab.get("added_components", [])


def get_removed_ids() -> Set[int]:
    """Returnerar set med borttagna id_component."""
    rab = st.session_state.get("rab_editor", {})
    return rab.get("removed_ids", set())


def get_current_id_network() -> Optional[int]:
    """Returnerar aktivt id_network."""
    rab = st.session_state.get("rab_editor", {})
    return rab.get("id_network")


# =============================================================================
# HÄMTA DATA PER VTYPE
# =============================================================================

def get_components_by_vtype(vtype: int) -> pd.DataFrame:
    """
    Returnerar komponenter filtrerade på vtype.
    
    Args:
        vtype: Värderingsmetod (1, 2, 4, eller 5)
    
    Returns:
        Filtrerad DataFrame
    """
    df = get_modified_components()
    if df is None or df.empty:
        return pd.DataFrame()
    
    return df[df['vtype'] == vtype].copy()


def get_normvärderade() -> pd.DataFrame:
    """Returnerar normvärderade komponenter (vtype=4)."""
    return get_components_by_vtype(VType.NORMVÄRDE)


def get_övriga_metoder() -> pd.DataFrame:
    """Returnerar komponenter med annat skäligt värde eller anskaffningsvärde (vtype=1,2)."""
    df = get_modified_components()
    if df is None or df.empty:
        return pd.DataFrame()
    
    mask = df['vtype'].isin([VType.ANNAT_SKÄLIGT_VÄRDE, VType.ANSKAFFNINGSVÄRDE])
    return df[mask].copy()


def get_investeringar() -> pd.DataFrame:
    """Returnerar investeringar och utrangeringar (vtype=5)."""
    return get_components_by_vtype(VType.INVESTERING)


# =============================================================================
# ÄNDRINGSDETEKTERING
# =============================================================================

def has_changes() -> bool:
    """
    Kontrollerar om RAB-editor har några ändringar.
    
    Returns:
        True om det finns ändringar, annars False
    """
    rab = st.session_state.get("rab_editor", {})
    
    if not rab:
        return False
    
    # Kolla removed_ids
    if rab.get("removed_ids"):
        return True
    
    # Kolla added_components
    if rab.get("added_components"):
        return True
    
    # Kolla om modified_components skiljer sig från original
    original = rab.get("original_components")
    modified = rab.get("modified_components")
    
    if original is None or modified is None:
        return False
    
    # Jämför relevanta kolumner per vtype
    compare_cols_by_vtype = {
        VType.NORMVÄRDE: ['count_comp', 'time_from', 'techspec', 'volt', 'id_comptype'],
        VType.ANNAT_SKÄLIGT_VÄRDE: ['annatskäligtvärde', 'count_comp', 'time_from', 'cat_encode'],
        VType.ANSKAFFNINGSVÄRDE: ['anskaffningsvärde', 'rapporteradnuav', 'time_from', 'cat_encode'],
        VType.INVESTERING: ['value_invest', 'invest', 'time_invest', 'cat_encode', 'subcat'],
    }
    
    for vtype, cols in compare_cols_by_vtype.items():
        orig_vtype = original[original['vtype'] == vtype]
        mod_vtype = modified[modified['vtype'] == vtype]
        
        if len(orig_vtype) != len(mod_vtype):
            return True
        
        for col in cols:
            if col in original.columns and col in modified.columns:
                orig_vals = orig_vtype[col].reset_index(drop=True)
                mod_vals = mod_vtype[col].reset_index(drop=True)
                
                # Hantera NaN-jämförelse
                if not orig_vals.equals(mod_vals):
                    # Dubbelkolla med fillna för att hantera NaN
                    if not orig_vals.fillna('__NA__').equals(mod_vals.fillna('__NA__')):
                        return True
    
    return False


def get_change_summary() -> Dict[str, Any]:
    """
    Returnerar sammanfattning av ändringar.
    
    Returns:
        Dict med ändringsstatistik
    """
    rab = st.session_state.get("rab_editor", {})
    if not rab:
        return _empty_summary()
    
    original = rab.get("original_components", pd.DataFrame())
    modified = rab.get("modified_components", pd.DataFrame())
    added = rab.get("added_components", [])
    removed_ids = rab.get("removed_ids", set())
    
    summary = {
        'n_removed': len(removed_ids),
        'n_added': len(added),
        'n_modified': 0,
        'nuav_change_mkr': 0.0,
        'changes_by_vtype': {},
    }
    
    if original.empty or modified.empty:
        return summary
    
    # Räkna modifierade per vtype
    for vtype in [VType.NORMVÄRDE, VType.ANNAT_SKÄLIGT_VÄRDE, VType.ANSKAFFNINGSVÄRDE, VType.INVESTERING]:
        cols = get_redigerbara_fält(vtype)
        orig_vtype = original[original['vtype'] == vtype]
        mod_vtype = modified[modified['vtype'] == vtype]
        
        n_changed = 0
        for col in cols:
            if col in orig_vtype.columns and col in mod_vtype.columns:
                # Jämför rad för rad
                merged = orig_vtype[['id_component', col]].merge(
                    mod_vtype[['id_component', col]],
                    on='id_component',
                    suffixes=('_orig', '_mod')
                )
                col_orig = f'{col}_orig'
                col_mod = f'{col}_mod'
                if col_orig in merged.columns and col_mod in merged.columns:
                    diff = (merged[col_orig].fillna('__NA__') != merged[col_mod].fillna('__NA__')).sum()
                    n_changed += diff
        
        if n_changed > 0:
            summary['changes_by_vtype'][VTYPE_NAMN.get(vtype, str(vtype))] = n_changed
            summary['n_modified'] += n_changed
    
    # Beräkna NUAV-förändring (via prepare_capbase för korrekthet)
    try:
        df_with_edits = get_user_capbase_with_edits()
        original_nuav = original['nuav_2022'].sum()
        new_nuav = df_with_edits['nuav_2022'].sum()
        summary['nuav_change_mkr'] = (new_nuav - original_nuav) / 1_000_000
    except Exception:
        # Fallback om något går fel
        pass
    
    return summary


def _empty_summary() -> Dict[str, Any]:
    """Returnerar tom sammanfattning."""
    return {
        'n_removed': 0,
        'n_added': 0,
        'n_modified': 0,
        'nuav_change_mkr': 0.0,
        'changes_by_vtype': {},
    }


# =============================================================================
# MODIFIERING
# =============================================================================

def update_modified_components(df: pd.DataFrame) -> None:
    """
    Uppdaterar modified_components med ny DataFrame.
    
    Args:
        df: Uppdaterad DataFrame
    """
    rab = st.session_state.get("rab_editor", {})
    if rab:
        rab["modified_components"] = df.copy()


def update_component_field(id_component: int, field: str, value: Any) -> None:
    """
    Uppdaterar ett specifikt fält för en komponent.
    
    Args:
        id_component: Komponentens ID
        field: Fältnamn att uppdatera
        value: Nytt värde
    """
    rab = st.session_state.get("rab_editor", {})
    if not rab or "modified_components" not in rab:
        return
    
    df = rab["modified_components"]
    mask = df['id_component'] == id_component
    
    if mask.any():
        df.loc[mask, field] = value


def update_techspec(id_component: int, new_techspec: str, volt: str = None) -> bool:
    """
    Uppdaterar techspec för en normvärderad komponent.
    
    Slår upp nytt normvärde och uppdaterar id_comptype.
    
    Args:
        id_component: Komponentens ID
        new_techspec: Ny teknisk specifikation
        volt: Spänningsnivå (valfritt)
    
    Returns:
        True om lyckad, False annars
    """
    rab = st.session_state.get("rab_editor", {})
    if not rab or "modified_components" not in rab:
        return False
    
    df = rab["modified_components"]
    mask = df['id_component'] == id_component
    
    if not mask.any():
        return False
    
    row = df[mask].iloc[0]
    kategori = row.get('cat', '')
    typ_anläggning = row.get('subcat', '')
    
    try:
        df_updated = update_normvärde_from_techspec(
            df, df[mask].index[0],
            kategori, typ_anläggning, new_techspec, volt
        )
        rab["modified_components"] = df_updated
        return True
    except ValueError:
        return False


def add_component(component: Dict[str, Any]) -> int:
    """
    Lägger till en ny komponent.
    
    Args:
        component: Dict med komponentdata
    
    Returns:
        Nytt id_component för komponenten
    """
    rab = st.session_state.get("rab_editor", {})
    if not rab:
        raise ValueError("RAB-editor inte initierad")
    
    # Generera nytt id_component
    existing_ids = set()
    if "original_components" in rab:
        existing_ids.update(rab["original_components"]['id_component'].tolist())
    if "modified_components" in rab:
        existing_ids.update(rab["modified_components"]['id_component'].tolist())
    if "added_components" in rab:
        existing_ids.update(c.get('id_component', 0) for c in rab["added_components"])
    
    new_id = max(existing_ids, default=0) + 1
    component['id_component'] = new_id
    
    # Säkerställ id_network
    component['id_network'] = rab.get('id_network')
    
    # Lägg till i added_components
    rab["added_components"].append(component)
    
    return new_id


def add_investment(
    cat_encode: int,
    subcat: str,
    value: float,
    time_invest: int,
    is_retirement: bool = False,
) -> int:
    """
    Lägger till en ny investering eller utrangering.
    
    Args:
        cat_encode: Anläggningskategori (1-17)
        subcat: Underkategori
        value: Belopp (positivt tal)
        time_invest: Tidskod för halvår (229-236)
        is_retirement: True för utrangering
    
    Returns:
        Nytt id_component
    """
    rab = st.session_state.get("rab_editor", {})
    id_network = rab.get('id_network') if rab else None
    
    if id_network is None:
        raise ValueError("RAB-editor inte initierad")
    
    component = create_new_investment(
        id_network=id_network,
        cat_encode=cat_encode,
        subcat=subcat,
        value=value,
        time_invest=time_invest,
        is_retirement=is_retirement,
    )
    
    return add_component(component)


def add_component_vtype1(
    cat_encode: int,
    subcat: str,
    annatskäligtvärde: float,
    count_comp: float,
    time_from: int,
) -> int:
    """
    Lägger till en ny komponent med annat skäligt värde.
    
    Args:
        cat_encode: Anläggningskategori (1-17)
        subcat: Underkategori
        annatskäligtvärde: Värde per enhet
        count_comp: Antal enheter
        time_from: Tidskod för idrifttagande
    
    Returns:
        Nytt id_component
    """
    rab = st.session_state.get("rab_editor", {})
    id_network = rab.get('id_network') if rab else None
    
    if id_network is None:
        raise ValueError("RAB-editor inte initierad")
    
    component = create_new_component_vtype1(
        id_network=id_network,
        cat_encode=cat_encode,
        subcat=subcat,
        annatskäligtvärde=annatskäligtvärde,
        count_comp=count_comp,
        time_from=time_from,
    )
    
    return add_component(component)


def remove_component(id_component: int) -> None:
    """
    Markerar en komponent för borttagning.
    
    Args:
        id_component: ID för komponenten att ta bort
    """
    rab = st.session_state.get("rab_editor", {})
    if rab:
        rab["removed_ids"].add(id_component)


def restore_component(id_component: int) -> None:
    """
    Återställer en borttagen komponent.
    
    Args:
        id_component: ID för komponenten att återställa
    """
    rab = st.session_state.get("rab_editor", {})
    if rab and "removed_ids" in rab:
        rab["removed_ids"].discard(id_component)


# =============================================================================
# SKALNING
# =============================================================================

def apply_count_scaling(
    multiplier: float,
    cat_encode: Optional[int] = None,
    subcat: Optional[str] = None,
    vtype: int = VType.NORMVÄRDE,
) -> int:
    """
    Skalar count_comp för komponenter (vtype 1 eller 4).
    
    Till skillnad från den gamla apply_nuav_scaling() skalar denna
    rådata (count_comp) istället för nuav_2022 direkt.
    
    Args:
        multiplier: Skalningsfaktor (t.ex. 1.1 för +10%)
        cat_encode: Filtrera på kategori (None = alla)
        subcat: Filtrera på subkategori (None = alla)
        vtype: Värderingsmetod att skala (4 eller 1)
    
    Returns:
        Antal skalade komponenter
    """
    if vtype not in [VType.NORMVÄRDE, VType.ANNAT_SKÄLIGT_VÄRDE]:
        raise ValueError(f"Kan bara skala count_comp för vtype 1 eller 4, fick {vtype}")
    
    rab = st.session_state.get("rab_editor", {})
    if not rab or "modified_components" not in rab:
        return 0
    
    df = rab["modified_components"]
    
    # Bygg mask
    mask = df['vtype'] == vtype
    
    if cat_encode is not None:
        mask &= df['cat_encode'] == cat_encode
    
    if subcat is not None:
        mask &= df['subcat'] == subcat
    
    n_scaled = mask.sum()
    
    if n_scaled > 0:
        df.loc[mask, 'count_comp'] = df.loc[mask, 'count_comp'] * multiplier
    
    return n_scaled


def apply_value_scaling(
    multiplier: float,
    cat_encode: Optional[int] = None,
    is_investment: Optional[bool] = None,
) -> int:
    """
    Skalar value_invest för investeringar/utrangeringar (vtype=5).
    
    Args:
        multiplier: Skalningsfaktor
        cat_encode: Filtrera på kategori (None = alla)
        is_investment: True = bara inv, False = bara utr, None = alla
    
    Returns:
        Antal skalade komponenter
    """
    rab = st.session_state.get("rab_editor", {})
    if not rab or "modified_components" not in rab:
        return 0
    
    df = rab["modified_components"]
    
    mask = df['vtype'] == VType.INVESTERING
    
    if cat_encode is not None:
        mask &= df['cat_encode'] == cat_encode
    
    if is_investment is True:
        mask &= df['invest'] == 1
    elif is_investment is False:
        mask &= df['invest'] == -1
    
    n_scaled = mask.sum()
    
    if n_scaled > 0:
        df.loc[mask, 'value_invest'] = df.loc[mask, 'value_invest'] * multiplier
    
    return n_scaled


# =============================================================================
# DATA-LADDNING
# =============================================================================

def load_user_components(user_id_network: int) -> pd.DataFrame:
    """
    Laddar användarens komponenter från capbase_a.
    
    Args:
        user_id_network: Användarens id_network
    
    Returns:
        DataFrame med användarens komponenter
    """
    # Dynamisk import för att undvika cirkulär import
    from calculations.kent_calculations import load_capbase_a
    
    capbase = load_capbase_a()
    user_components = capbase[capbase['id_network'] == user_id_network].copy()
    
    return user_components


# =============================================================================
# UI-HJÄLPFUNKTIONER
# =============================================================================

def get_category_options() -> Dict[int, str]:
    """
    Returnerar kategorialternativ för dropdown.
    
    Returns:
        Dict {cat_encode: visningstext}
    """
    return {
        cat_encode: f"{cat_encode} - {kat.namn}"
        for cat_encode, kat in KATEGORIER.items()
    }


def get_subcat_options(cat_encode: int) -> List[str]:
    """
    Returnerar subkategorier för en kategori.
    
    Args:
        cat_encode: Kategorikod
    
    Returns:
        Lista med subkategorier
    """
    df = get_modified_components()
    if df is None or df.empty:
        return []
    
    subcats = df[df['cat_encode'] == cat_encode]['subcat'].dropna().unique()
    return sorted(subcats)


def get_techspec_options(kategori: str, typ_anläggning: str) -> List[Tuple[str, str, int]]:
    """
    Returnerar techspec-alternativ för dropdown.
    
    Args:
        kategori: Anläggningskategori (text)
        typ_anläggning: Subkategori (text)
    
    Returns:
        Lista med tuples (techspec, volt, normvärde)
    """
    techspecs = list_techspecs_for_category(kategori, typ_anläggning)
    return [(ts, volt, nv) for ts, volt, kod, nv in techspecs]


def apply_filters(
    df: pd.DataFrame,
    cat_encode: Optional[int] = None,
    subcat: Optional[str] = None,
    vtype: Optional[int] = None,
) -> pd.DataFrame:
    """
    Applicerar filter på DataFrame.
    
    Args:
        df: DataFrame att filtrera
        cat_encode: Kategorikod eller None
        subcat: Subkategori eller None
        vtype: Värderingsmetod eller None
    
    Returns:
        Filtrerad DataFrame
    """
    df_filtered = df.copy()
    
    if vtype is not None:
        df_filtered = df_filtered[df_filtered['vtype'] == vtype]
    
    if cat_encode is not None:
        df_filtered = df_filtered[df_filtered['cat_encode'] == cat_encode]
    
    if subcat is not None and 'subcat' in df_filtered.columns:
        df_filtered = df_filtered[df_filtered['subcat'] == subcat]
    
    return df_filtered


def render_summary_metrics(show_delta: bool = True) -> Dict[str, Any]:
    """
    Beräknar sammanfattnings-metrics för kapitalbasen.
    
    Args:
        show_delta: Om True, beräkna förändring mot original
    
    Returns:
        Dict med metrics
    """
    df_original = get_original_components()
    df_modified = get_modified_components()
    
    if df_modified is None or df_modified.empty:
        return {'n_components': 0, 'total_nuav_mkr': 0, 'delta_nuav_mkr': 0}
    
    n_components = len(df_modified) - len(get_removed_ids()) + len(get_added_components())
    
    # Beräkna NUAV med edits
    try:
        df_with_edits = get_user_capbase_with_edits()
        total_nuav = df_with_edits['nuav_2022'].sum() / 1_000_000
    except Exception:
        total_nuav = df_modified['nuav_2022'].sum() / 1_000_000
    
    delta_nuav = 0
    if show_delta and df_original is not None:
        original_nuav = df_original['nuav_2022'].sum() / 1_000_000
        delta_nuav = total_nuav - original_nuav
    
    return {
        'n_components': n_components,
        'total_nuav_mkr': total_nuav,
        'delta_nuav_mkr': delta_nuav,
    }


def get_vtype_summary() -> Dict[int, Dict[str, Any]]:
    """
    Returnerar sammanfattning per vtype.
    
    Returns:
        Dict {vtype: {n_components, nuav_mkr, ...}}
    """
    df = get_modified_components()
    if df is None or df.empty:
        return {}
    
    summary = {}
    for vtype in [VType.NORMVÄRDE, VType.ANNAT_SKÄLIGT_VÄRDE, VType.ANSKAFFNINGSVÄRDE, VType.INVESTERING]:
        subset = df[df['vtype'] == vtype]
        if not subset.empty:
            summary[vtype] = {
                'namn': VTYPE_NAMN.get(vtype, str(vtype)),
                'n_components': len(subset),
                'nuav_mkr': subset['nuav_2022'].sum() / 1_000_000,
                'andel_pct': len(subset) / len(df) * 100,
            }
    
    return summary
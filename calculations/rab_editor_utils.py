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
    }
"""

import pandas as pd
import numpy as np
import streamlit as st
from typing import Dict, List, Set, Optional, Any


# =============================================================================
# INITIALISERING
# =============================================================================

def initialize_rab_editor(user_components: pd.DataFrame) -> None:
    """
    Initierar RAB-editor session state med användarens komponenter.
    
    Anropas när användaren öppnar RAB-editorn första gången eller
    när företag byts.
    
    Args:
        user_components: DataFrame med användarens komponenter från capbase_a
    """
    if "rab_editor" not in st.session_state:
        st.session_state["rab_editor"] = {
            "original_components": user_components.copy(),
            "modified_components": user_components.copy(),
            "added_components": [],
            "removed_ids": set(),
        }
    else:
        # Kontrollera om det är en ny användare
        existing = st.session_state["rab_editor"].get("original_components")
        if existing is None or len(existing) != len(user_components):
            # Ny användare - återinitiera
            st.session_state["rab_editor"] = {
                "original_components": user_components.copy(),
                "modified_components": user_components.copy(),
                "added_components": [],
                "removed_ids": set(),
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

def get_user_capbase_with_edits(user_id_network: int) -> pd.DataFrame:
    """
    Returnerar användarens kapitalbas med alla redigeringar applicerade.
    
    Denna funktion skapar en capbase_a DataFrame redo för 
    run_kent_calculations_batch(). Den:
    1. Tar modified_components (med ändringar)
    2. Exkluderar borttagna komponenter
    3. Lägger till nya komponenter
    4. Säkerställer korrekt id_network
    
    Args:
        user_id_network: Användarens id_network
    
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
    df['id_network'] = user_id_network
    
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


# =============================================================================
# ÄNDRINGSDETEKTERING
# =============================================================================

def has_changes() -> bool:
    """
    Kontrollerar om RAB-editor har några ändringar.
    
    Returnerar True om:
    - Komponenter har tagits bort
    - Nya komponenter har lagts till
    - Befintliga komponenter har modifierats
    
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
    
    # Jämför relevanta kolumner
    compare_cols = ['nuav_2022', 'time_from', 'cat_encode', 'antal']
    for col in compare_cols:
        if col in original.columns and col in modified.columns:
            if not original[col].equals(modified[col]):
                return True
    
    return False


def get_change_summary() -> Dict[str, Any]:
    """
    Returnerar sammanfattning av ändringar.
    
    Returns:
        Dict med:
        - n_removed: Antal borttagna komponenter
        - n_added: Antal tillagda komponenter
        - n_modified: Antal modifierade fält
        - nuav_change_mkr: Total NUAV-förändring i Mkr
    """
    rab = st.session_state.get("rab_editor", {})
    if not rab:
        return {
            'n_removed': 0,
            'n_added': 0,
            'n_modified': 0,
            'nuav_change_mkr': 0.0,
        }
    
    original = rab.get("original_components", pd.DataFrame())
    modified = rab.get("modified_components", pd.DataFrame())
    
    summary = {
        'n_removed': len(rab.get("removed_ids", set())),
        'n_added': len(rab.get("added_components", [])),
        'n_modified': 0,
        'nuav_change_mkr': 0.0,
    }
    
    if not original.empty and not modified.empty:
        # Räkna modifierade fält
        for col in ['nuav_2022', 'time_from', 'cat_encode']:
            if col in original.columns and col in modified.columns:
                diff = (original[col] != modified[col]).sum()
                summary['n_modified'] += diff
        
        # Beräkna NUAV-förändring
        original_nuav = original['nuav_2022'].sum()
        modified_nuav = modified['nuav_2022'].sum()
        added_nuav = sum(c.get('nuav_2022', 0) for c in rab.get("added_components", []))
        
        # Ta hänsyn till borttagna
        removed_ids = rab.get("removed_ids", set())
        removed_nuav = original[original['id_component'].isin(removed_ids)]['nuav_2022'].sum()
        
        total_change = (modified_nuav - original_nuav) + added_nuav - removed_nuav
        summary['nuav_change_mkr'] = total_change / 1_000_000
    
    return summary


# =============================================================================
# MODIFIERING
# =============================================================================

def update_modified_components(df: pd.DataFrame) -> None:
    """
    Uppdaterar modified_components med ny DataFrame.
    
    Anropas typiskt efter st.data_editor har returnerat.
    
    Args:
        df: Uppdaterad DataFrame från data_editor
    """
    rab = st.session_state.get("rab_editor", {})
    if rab:
        rab["modified_components"] = df.copy()


def add_component(component: Dict[str, Any]) -> int:
    """
    Lägger till en ny komponent.
    
    Args:
        component: Dict med komponentdata (nuav_2022, cat_encode, etc.)
    
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
    if "added_components" in rab:
        existing_ids.update(c.get('id_component', 0) for c in rab["added_components"])
    
    new_id = max(existing_ids, default=0) + 1
    component['id_component'] = new_id
    
    # Lägg till i added_components
    rab["added_components"].append(component)
    
    return new_id


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


def apply_nuav_scaling(id_components: List[int], multiplier: float) -> None:
    """
    Skalar NUAV för specifika komponenter.
    
    Args:
        id_components: Lista med id_component att skala
        multiplier: Skalningsfaktor (t.ex. 1.1 för +10%)
    """
    rab = st.session_state.get("rab_editor", {})
    if not rab or "modified_components" not in rab:
        return
    
    df = rab["modified_components"]
    mask = df['id_component'].isin(id_components)
    df.loc[mask, 'nuav_2022'] = df.loc[mask, 'nuav_2022'] * multiplier


# =============================================================================
# TIDSKOD-KONVERTERING
# =============================================================================

def year_to_time_code(year: int, half_year: int = 1) -> int:
    """
    Konverterar år (och halvår) till tidskod.
    
    Tidskod = (år - 1910) * 2 + halvår
    
    Args:
        year: År (t.ex. 2020)
        half_year: Halvår (1 eller 2)
    
    Returns:
        Tidskod (t.ex. 221 för 2020H1)
    """
    return (year - 1910) * 2 + half_year


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
    return 1910 + (time_code - 1) // 2


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
    from calculations.kent_calculations import load_capbase_a
    
    capbase = load_capbase_a()
    user_components = capbase[capbase['id_network'] == user_id_network].copy()
    
    return user_components


# =============================================================================
# UI-HJÄLPFUNKTIONER
# =============================================================================

def render_summary_metrics(df_current: pd.DataFrame, df_original: pd.DataFrame) -> None:
    """
    Renderar sammanfattnings-metrics för kapitalbasen.
    
    Args:
        df_current: Nuvarande komponenter (med ändringar)
        df_original: Originalkomponenter
    """
    n_components = len(df_current)
    total_nuav = df_current['nuav_2022'].sum() / 1_000_000  # Mkr
    original_nuav = df_original['nuav_2022'].sum() / 1_000_000
    nuav_delta = total_nuav - original_nuav
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Komponenter", f"{n_components:,}")
    
    with col2:
        st.metric("Total NUAV", f"{total_nuav:.1f} Mkr")
    
    with col3:
        delta_str = f"{nuav_delta:+.2f} Mkr" if nuav_delta != 0 else None
        st.metric("Förändring", delta_str or "Ingen", delta=delta_str)


def get_filter_description(cat_encode: Optional[int], subcat: Optional[str]) -> str:
    """
    Skapar beskrivning av aktuellt filter.
    
    Args:
        cat_encode: Kategorikod eller None för alla
        subcat: Subkategori eller None för alla
    
    Returns:
        Beskrivande sträng
    """
    if cat_encode is None:
        return "alla komponenter"
    
    # Försök hämta kategorinamn
    try:
        from frontend.common.asset_categories import get_category_name
        desc = get_category_name(cat_encode)
    except ImportError:
        desc = f"Kategori {cat_encode}"
    
    if subcat:
        desc += f" > {subcat}"
    
    return desc


def apply_filters(
    df: pd.DataFrame,
    cat_encode: Optional[int] = None,
    subcat: Optional[str] = None,
) -> pd.DataFrame:
    """
    Applicerar kategori- och subkategori-filter.
    
    Args:
        df: DataFrame att filtrera
        cat_encode: Kategorikod eller None
        subcat: Subkategori eller None
    
    Returns:
        Filtrerad DataFrame
    """
    df_filtered = df.copy()
    
    if cat_encode is not None:
        df_filtered = df_filtered[df_filtered['cat_encode'] == cat_encode]
    
    if subcat is not None and 'subcat' in df_filtered.columns:
        df_filtered = df_filtered[df_filtered['subcat'] == subcat]
    
    return df_filtered
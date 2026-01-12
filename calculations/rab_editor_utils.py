"""
calculations/rab_editor_utils.py

Helper functions for RAB editor session state management.

UPDATED: Now filters to show only ordinarie components in UI,
while keeping all data (ordinarie + tail) for calculations.

Session state structure:
    st.session_state["rab_editor"] = {
        "original_components": pd.DataFrame,   # Unmodified copy
        "modified_components": pd.DataFrame,   # With changes
        "added_components": List[Dict],        # New components
        "removed_ids": Set[int],               # id_component to exclude
        "id_network": int,                     # Active company
    }
"""

import pandas as pd
import numpy as np
import streamlit as st
from typing import Dict, List, Set, Optional, Any, Tuple

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

from .rab_classification import (
    classify_components,
    filter_for_display,
    get_classification_summary,
    get_tail_summary,
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
# TIME CODE HELPERS (re-export for backwards compatibility)
# =============================================================================

def time_code_to_year(time_code: int) -> int:
    """Convert time code to year (ignoring half-year)."""
    if pd.isna(time_code) or time_code <= 0:
        return 0
    return int(timecode_to_year(time_code))


def year_to_time_code(year: int, half_year: int = 1) -> int:
    """Convert year (and half-year) to time code."""
    return year_to_timecode(year, half_year)


def time_code_to_half_year(time_code: int) -> int:
    """Extract half-year from time code."""
    if pd.isna(time_code) or time_code <= 0:
        return 1
    return ((time_code - 1) % 2) + 1


def get_halfyear_options() -> List[Tuple[str, int]]:
    """Return list of half-year options for dropdown."""
    return [(label, code) for label, code in HALFYEAR_TO_TIMECODE.items()]


# =============================================================================
# INITIALIZATION
# =============================================================================

def initialize_rab_editor(user_components: pd.DataFrame, id_network: int) -> None:
    """
    Initialize RAB editor session state with user's components.
    
    Called when user opens RAB editor for first time or when company changes.
    """
    current_id = st.session_state.get("rab_editor", {}).get("id_network")
    
    if "rab_editor" not in st.session_state or current_id != id_network:
        st.session_state["rab_editor"] = {
            "original_components": user_components.copy(),
            "modified_components": user_components.copy(),
            "added_components": [],
            "removed_ids": set(),
            "id_network": id_network,
        }


def reset_rab_editor() -> None:
    """Reset all changes to original data."""
    rab = st.session_state.get("rab_editor", {})
    if rab and "original_components" in rab:
        rab["modified_components"] = rab["original_components"].copy()
        rab["added_components"] = []
        rab["removed_ids"] = set()


def clear_rab_editor() -> None:
    """Remove RAB editor from session state entirely."""
    if "rab_editor" in st.session_state:
        del st.session_state["rab_editor"]


# =============================================================================
# GET DATA (for calculations - returns ALL data)
# =============================================================================

def get_user_capbase_with_edits() -> pd.DataFrame:
    """
    Return user's capital base with all edits applied.
    
    IMPORTANT: Returns ALL data (ordinarie + tail + expired) for calculations.
    The filtering to ordinarie/tail happens INSIDE kent_calculations.py.
    
    Returns:
        DataFrame ready for run_kent_calculations_batch()
    
    Raises:
        ValueError: If RAB editor not initialized
    """
    rab = st.session_state.get("rab_editor", {})
    
    if not rab:
        raise ValueError("RAB editor not initialized")
    
    if "modified_components" not in rab:
        raise ValueError("RAB editor missing modified_components")
    
    id_network = rab.get("id_network")
    if id_network is None:
        raise ValueError("RAB editor missing id_network")
    
    # Start with modified components (ALL of them)
    df = rab["modified_components"].copy()
    
    # Exclude removed
    removed_ids = rab.get("removed_ids", set())
    if removed_ids:
        df = df[~df['id_component'].isin(removed_ids)]
    
    # Add new components
    added = rab.get("added_components", [])
    if added:
        df_added = pd.DataFrame(added)
        df = pd.concat([df, df_added], ignore_index=True)
    
    # Ensure id_network
    df['id_network'] = id_network
    
    # Recalculate nuav_2022 from raw data
    df = prepare_capbase_for_calculations(df)
    
    return df  # Returns ALL data - ordinarie, tail AND expired


def get_original_components() -> Optional[pd.DataFrame]:
    """Return original components (unmodified, ALL)."""
    rab = st.session_state.get("rab_editor", {})
    return rab.get("original_components")


def get_modified_components() -> Optional[pd.DataFrame]:
    """Return modified components (ALL - unfiltered)."""
    rab = st.session_state.get("rab_editor", {})
    return rab.get("modified_components")


def get_added_components() -> List[Dict]:
    """Return list of added components."""
    rab = st.session_state.get("rab_editor", {})
    return rab.get("added_components", [])


def get_removed_ids() -> Set[int]:
    """Return set of removed id_component."""
    rab = st.session_state.get("rab_editor", {})
    return rab.get("removed_ids", set())


def get_current_id_network() -> Optional[int]:
    """Return active id_network."""
    rab = st.session_state.get("rab_editor", {})
    return rab.get("id_network")


# =============================================================================
# GET DATA PER VTYPE (for UI display - filtered to ordinarie only)
# =============================================================================

def get_components_by_vtype(vtype: int, for_display: bool = True) -> pd.DataFrame:
    """
    Return components filtered by vtype.
    
    Args:
        vtype: Valuation method type
        for_display: If True, filter to show only ordinarie (default True)
    """
    df = get_modified_components()
    if df is None or df.empty:
        return pd.DataFrame()
    
    if for_display:
        return filter_for_display(df, vtype_filter=vtype)
    else:
        return df[df['vtype'] == vtype].copy()


def get_normvärderade() -> pd.DataFrame:
    """
    Return normvärde components (vtype=4) for UI display.
    Only shows ordinarie components.
    """
    return get_components_by_vtype(VType.NORMVÄRDE, for_display=True)


def get_övriga_metoder() -> pd.DataFrame:
    """
    Return components with annat skäligt värde or anskaffningsvärde (vtype=1,2).
    Only shows ordinarie components.
    """
    df = get_modified_components()
    if df is None or df.empty:
        return pd.DataFrame()
    
    # Filter by vtype first
    mask = df['vtype'].isin([VType.ANNAT_SKÄLIGT_VÄRDE, VType.ANSKAFFNINGSVÄRDE])
    df_filtered = df[mask].copy()
    
    if df_filtered.empty:
        return df_filtered
    
    # Then filter for display (ordinarie only)
    return filter_for_display(df_filtered)


def get_investeringar() -> pd.DataFrame:
    """
    Return investments and retirements (vtype=5).
    All investments are shown (they have capbase_existing=0).
    """
    df = get_modified_components()
    if df is None or df.empty:
        return pd.DataFrame()
    
    return df[df['vtype'] == VType.INVESTERING].copy()


# =============================================================================
# CHANGE DETECTION
# =============================================================================

def has_changes() -> bool:
    """Check if RAB editor has any changes."""
    rab = st.session_state.get("rab_editor", {})
    
    if not rab:
        return False
    
    # Check removed_ids
    if rab.get("removed_ids"):
        return True
    
    # Check added_components
    if rab.get("added_components"):
        return True
    
    # Check if modified_components differs from original
    original = rab.get("original_components")
    modified = rab.get("modified_components")
    
    if original is None or modified is None:
        return False
    
    # Compare relevant columns per vtype
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
                
                # Handle NaN comparison
                if not orig_vals.equals(mod_vals):
                    if not orig_vals.fillna('__NA__').equals(mod_vals.fillna('__NA__')):
                        return True
    
    return False


def get_change_summary() -> Dict[str, Any]:
    """Return summary of changes."""
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
    
    # Count modified per vtype
    for vtype in [VType.NORMVÄRDE, VType.ANNAT_SKÄLIGT_VÄRDE, VType.ANSKAFFNINGSVÄRDE, VType.INVESTERING]:
        cols = get_redigerbara_fält(vtype)
        orig_vtype = original[original['vtype'] == vtype]
        mod_vtype = modified[modified['vtype'] == vtype]
        
        n_changed = 0
        for col in cols:
            if col in orig_vtype.columns and col in mod_vtype.columns:
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
    
    # Calculate NUAV change (via prepare_capbase for correctness)
    try:
        df_with_edits = get_user_capbase_with_edits()
        original_nuav = original['nuav_2022'].sum()
        new_nuav = df_with_edits['nuav_2022'].sum()
        summary['nuav_change_mkr'] = (new_nuav - original_nuav) / 1_000_000
    except Exception:
        pass
    
    return summary


def _empty_summary() -> Dict[str, Any]:
    """Return empty summary."""
    return {
        'n_removed': 0,
        'n_added': 0,
        'n_modified': 0,
        'nuav_change_mkr': 0.0,
        'changes_by_vtype': {},
    }


# =============================================================================
# MODIFICATION
# =============================================================================

def update_modified_components(df: pd.DataFrame) -> None:
    """Update modified_components with new DataFrame."""
    rab = st.session_state.get("rab_editor", {})
    if rab:
        rab["modified_components"] = df.copy()


def update_component_field(id_component: int, field: str, value: Any) -> None:
    """Update a specific field for a component."""
    rab = st.session_state.get("rab_editor", {})
    if not rab or "modified_components" not in rab:
        return
    
    df = rab["modified_components"]
    mask = df['id_component'] == id_component
    
    if mask.any():
        df.loc[mask, field] = value


def update_techspec(id_component: int, new_techspec: str, volt: str = None) -> bool:
    """
    Update techspec for a normvärde component.
    
    Looks up new normvärde and updates id_comptype.
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
    Add a new component.
    
    Returns:
        New id_component for the component
    """
    rab = st.session_state.get("rab_editor", {})
    if not rab:
        raise ValueError("RAB editor not initialized")
    
    # Generate new id_component
    existing_ids = set()
    if "original_components" in rab:
        existing_ids.update(rab["original_components"]['id_component'].tolist())
    if "modified_components" in rab:
        existing_ids.update(rab["modified_components"]['id_component'].tolist())
    if "added_components" in rab:
        existing_ids.update(c.get('id_component', 0) for c in rab["added_components"])
    
    new_id = max(existing_ids, default=0) + 1
    component['id_component'] = new_id
    
    # Ensure id_network
    component['id_network'] = rab.get('id_network')
    
    # Add to added_components
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
    Add a new investment or retirement.
    
    Args:
        cat_encode: Asset category (1-17)
        subcat: Subcategory
        value: Amount (positive number)
        time_invest: Time code for half-year (229-236)
        is_retirement: True for retirement
    
    Returns:
        New id_component
    """
    rab = st.session_state.get("rab_editor", {})
    id_network = rab.get('id_network') if rab else None
    
    if id_network is None:
        raise ValueError("RAB editor not initialized")
    
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
    Add a new component with annat skäligt värde.
    
    Args:
        cat_encode: Asset category (1-17)
        subcat: Subcategory
        annatskäligtvärde: Value per unit
        count_comp: Number of units
        time_from: Time code for commissioning
    
    Returns:
        New id_component
    """
    rab = st.session_state.get("rab_editor", {})
    id_network = rab.get('id_network') if rab else None
    
    if id_network is None:
        raise ValueError("RAB editor not initialized")
    
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
    """Mark a component for removal."""
    rab = st.session_state.get("rab_editor", {})
    if rab:
        rab["removed_ids"].add(id_component)


def restore_component(id_component: int) -> None:
    """Restore a removed component."""
    rab = st.session_state.get("rab_editor", {})
    if rab and "removed_ids" in rab:
        rab["removed_ids"].discard(id_component)


# =============================================================================
# SCALING
# =============================================================================

def apply_count_scaling(
    multiplier: float,
    cat_encode: Optional[int] = None,
    subcat: Optional[str] = None,
    vtype: int = VType.NORMVÄRDE,
) -> int:
    """
    Scale count_comp for components (vtype 1 or 4).
    
    Unlike the old apply_nuav_scaling(), this scales raw data (count_comp)
    instead of nuav_2022 directly.
    
    Args:
        multiplier: Scaling factor (e.g. 1.1 for +10%)
        cat_encode: Filter by category (None = all)
        subcat: Filter by subcategory (None = all)
        vtype: Valuation method to scale (4 or 1)
    
    Returns:
        Number of scaled components
    """
    if vtype not in [VType.NORMVÄRDE, VType.ANNAT_SKÄLIGT_VÄRDE]:
        raise ValueError(f"Can only scale count_comp for vtype 1 or 4, got {vtype}")
    
    rab = st.session_state.get("rab_editor", {})
    if not rab or "modified_components" not in rab:
        return 0
    
    df = rab["modified_components"]
    
    # Build mask
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
    Scale value_invest for investments/retirements (vtype=5).
    
    Args:
        multiplier: Scaling factor
        cat_encode: Filter by category (None = all)
        is_investment: True = only inv, False = only ret, None = all
    
    Returns:
        Number of scaled components
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
# DATA LOADING
# =============================================================================

def load_user_components(user_id_network: int) -> pd.DataFrame:
    """
    Load user's components from capbase_a.
    
    Returns ALL components (ordinarie + tail + expired).
    Filtering for UI display happens in get_normvärderade() etc.
    """
    # Dynamic import to avoid circular import
    from data_loaders.rab_data import load_capbase_a
    
    capbase = load_capbase_a()
    user_components = capbase[capbase['id_network'] == user_id_network].copy()
    
    return user_components


# =============================================================================
# UI HELPERS
# =============================================================================

def get_category_options() -> Dict[int, str]:
    """Return category options for dropdown."""
    return {
        cat_encode: f"{cat_encode} - {kat.namn}"
        for cat_encode, kat in KATEGORIER.items()
    }


def get_subcat_options(cat_encode: int) -> List[str]:
    """Return subcategories for a category."""
    df = get_modified_components()
    if df is None or df.empty:
        return []
    
    subcats = df[df['cat_encode'] == cat_encode]['subcat'].dropna().unique()
    return sorted(subcats)


def get_techspec_options(kategori: str, typ_anläggning: str) -> List[Tuple[str, str, int]]:
    """Return techspec options for dropdown."""
    techspecs = list_techspecs_for_category(kategori, typ_anläggning)
    return [(ts, volt, nv) for ts, volt, kod, nv in techspecs]


def apply_filters(
    df: pd.DataFrame,
    cat_encode: Optional[int] = None,
    subcat: Optional[str] = None,
    vtype: Optional[int] = None,
) -> pd.DataFrame:
    """Apply filters to DataFrame."""
    df_filtered = df.copy()
    
    if vtype is not None:
        df_filtered = df_filtered[df_filtered['vtype'] == vtype]
    
    if cat_encode is not None:
        df_filtered = df_filtered[df_filtered['cat_encode'] == cat_encode]
    
    if subcat is not None and 'subcat' in df_filtered.columns:
        df_filtered = df_filtered[df_filtered['subcat'] == subcat]
    
    return df_filtered


def render_summary_metrics(show_delta: bool = True) -> Dict[str, Any]:
    """Calculate summary metrics for capital base."""
    df_original = get_original_components()
    df_modified = get_modified_components()
    
    if df_modified is None or df_modified.empty:
        return {'n_components': 0, 'total_nuav_mkr': 0, 'delta_nuav_mkr': 0}
    
    n_components = len(df_modified) - len(get_removed_ids()) + len(get_added_components())
    
    # Calculate NUAV with edits
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


def render_summary_metrics_with_classification(show_delta: bool = True) -> Dict[str, Any]:
    """
    Extended summary metrics including classification breakdown.
    Shows how many components are ordinarie vs tail.
    """
    df = get_modified_components()
    
    if df is None or df.empty:
        return {
            'n_components': 0,
            'total_nuav_mkr': 0,
            'delta_nuav_mkr': 0,
            'n_ordinarie': 0,
            'n_tail': 0,
            'n_expired': 0,
            'n_investments': 0,
            'nuav_ordinarie_mkr': 0,
            'nuav_tail_mkr': 0,
        }
    
    summary = get_classification_summary(df, time=TIMECODE_PERIOD_START)
    
    n_ordinarie = summary['existing_components']['ordinarie']['count']
    n_tail = summary['existing_components']['tail']['count']
    n_expired = summary['existing_components']['expired']['count']
    n_investments = summary['investments']['count']
    
    # Calculate total NUAV
    try:
        df_with_edits = get_user_capbase_with_edits()
        total_nuav = df_with_edits['nuav_2022'].sum() / 1_000_000
    except Exception:
        total_nuav = df['nuav_2022'].sum() / 1_000_000
    
    # Calculate delta from original
    delta_nuav = 0
    if show_delta:
        rab = st.session_state.get("rab_editor", {})
        original = rab.get("original_components")
        if original is not None:
            original_nuav = original['nuav_2022'].sum() / 1_000_000
            delta_nuav = total_nuav - original_nuav
    
    return {
        'n_components': len(df) - len(get_removed_ids()) + len(get_added_components()),
        'total_nuav_mkr': total_nuav,
        'delta_nuav_mkr': delta_nuav,
        'n_ordinarie': n_ordinarie,
        'n_tail': n_tail,
        'n_expired': n_expired,
        'n_investments': n_investments,
        'nuav_ordinarie_mkr': summary['existing_components']['ordinarie']['nuav_mkr'],
        'nuav_tail_mkr': summary['existing_components']['tail']['nuav_mkr'],
    }


def get_vtype_summary() -> Dict[int, Dict[str, Any]]:
    """
    Return summary per vtype.
    
    NOTE: Counts are for UI display (ordinarie only for existing components).
    """
    df = get_modified_components()
    if df is None or df.empty:
        return {}
    
    summary = {}
    
    for vtype in [VType.NORMVÄRDE, VType.ANNAT_SKÄLIGT_VÄRDE, VType.ANSKAFFNINGSVÄRDE, VType.INVESTERING]:
        # Use filtered data for display counts
        if vtype == VType.INVESTERING:
            subset = get_investeringar()
        elif vtype in [VType.ANNAT_SKÄLIGT_VÄRDE, VType.ANSKAFFNINGSVÄRDE]:
            # For övriga, we need to filter each separately
            subset = filter_for_display(df[df['vtype'] == vtype])
        else:
            subset = get_normvärderade() if vtype == VType.NORMVÄRDE else pd.DataFrame()
        
        if not subset.empty:
            summary[vtype] = {
                'namn': VTYPE_NAMN.get(vtype, str(vtype)),
                'n_components': len(subset),
                'nuav_mkr': subset['nuav_2022'].sum() / 1_000_000,
                'andel_pct': len(subset) / len(filter_for_display(df)) * 100 if len(filter_for_display(df)) > 0 else 0,
            }
    
    return summary


def render_classification_info() -> None:
    """
    Render info about what's shown vs hidden.
    Call this in the RAB editor UI to inform users.
    """
    df = get_modified_components()
    if df is None or df.empty:
        return
    
    tail_info = get_tail_summary(df)
    
    if tail_info['count'] > 0:
        st.info(
            f"Showing ordinarie components only. "
            f"{tail_info['count']} tail components ({tail_info['nuav_mkr']:.1f} MSEK) "
            f"are hidden but included in calculations."
        )
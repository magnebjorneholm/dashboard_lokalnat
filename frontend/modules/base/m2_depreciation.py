"""
Module 2: Depreciation

Handles lifetime adjustments for asset categories.
Parameter-IDs: 2.X.1 (ordinary lifetime), 2.X.2 (tail period) per category X

Section-based rendering:
- render_lifetimes() -> 2.X Asset lifetimes
"""

import streamlit as st
import pandas as pd
from typing import Dict, Any, Optional

from config.asset_categories import ASSET_CATEGORIES
from frontend.utils.state_manager import get_config_value
from config.glossary import lifetime_ordinary_param_id, lifetime_tail_param_id

MODULE_KEY = "m2_depreciation"


def render_lifetimes(user_id_network: Optional[int] = None) -> Dict[str, Any]:
    """
    Render M2 lifetimes section: 2.X Asset lifetimes.

    Args:
        user_id_network: Logged-in company's id_network (for context columns)

    Returns:
        Dict with lifetime_adjustments (category-level only)
    """
    config: Dict[str, Any] = {}

    st.markdown("##### 2.1-2.17 Asset lifetimes")
    st.caption(
        "Modified values override baseline. Changes apply to all companies. "
        f"(Parameters {lifetime_ordinary_param_id(1)}-{lifetime_tail_param_id(17)})"
    )

    adjustments, validation_error = _render_cat_editor(user_id_network=user_id_network)

    if validation_error:
        st.warning(validation_error)
    if adjustments:
        config["lifetime_adjustments"] = adjustments
        st.caption(f":orange[Modified] - {len(adjustments)} lifetime adjustment(s)")

    return config


# =============================================================================
# EDITOR FUNCTIONS
# =============================================================================

def _render_cat_editor(
    user_id_network: Optional[int] = None,
) -> tuple[Optional[Dict[int, Dict[str, int]]], Optional[str]]:
    """Render editor for category-level adjustments."""
    editor_key = f"{MODULE_KEY}_cat_editor"
    source_key = f"{editor_key}_source"

    if source_key not in st.session_state or editor_key not in st.session_state:
        lifetime_adj = get_config_value(MODULE_KEY, "lifetime_adjustments", None)
        data = []
        for cat in ASSET_CATEGORIES:
            tail_period = cat.maxdep - cat.ekdep
            initial_ekdep = cat.ekdep
            initial_tail = tail_period
            if isinstance(lifetime_adj, dict) and cat.cat_encode in lifetime_adj:
                adj = lifetime_adj[cat.cat_encode]
                initial_ekdep = int(adj.get('ekdep', initial_ekdep))
                initial_tail = int(adj.get('maxdep', initial_ekdep + initial_tail)) - initial_ekdep
            data.append({
                'Param-ID': f"{cat.param_id_ekdep} / {cat.param_id_maxdep}",
                'Category': cat.name,
                'Ordinary lifetime': initial_ekdep,
                'Tail period': initial_tail,
                '_cat_encode': cat.cat_encode,
                '_baseline_ekdep': cat.ekdep,
                '_baseline_tail': tail_period,
            })
        baseline_df = pd.DataFrame(data)

        # Add company-specific depreciation context if available
        if user_id_network is not None:
            try:
                context = _get_depreciation_context(user_id_network)
                if not context.empty:
                    baseline_df = baseline_df.merge(
                        context,
                        left_on='_cat_encode',
                        right_on='cat_encode',
                        how='left',
                    ).drop(columns=['cat_encode'])
                    baseline_df['Dep ord (Mkr)'] = baseline_df['Dep ord (Mkr)'].fillna(0.0)
                    baseline_df['Dep tail (Mkr)'] = baseline_df['Dep tail (Mkr)'].fillna(0.0)
            except Exception:
                pass  # Graceful fallback — show editor without context

        st.session_state[source_key] = baseline_df
    else:
        baseline_df = st.session_state[source_key]

    has_context = 'Dep ord (Mkr)' in baseline_df.columns
    display_cols = (
        ['Param-ID', 'Category', 'Dep ord (Mkr)', 'Dep tail (Mkr)', 'Ordinary lifetime', 'Tail period']
        if has_context
        else ['Param-ID', 'Category', 'Ordinary lifetime', 'Tail period']
    )
    disabled_cols = (
        ['Param-ID', 'Category', 'Dep ord (Mkr)', 'Dep tail (Mkr)']
        if has_context
        else ['Param-ID', 'Category']
    )

    display_df = baseline_df[display_cols].copy()
    original_display = display_df.copy()

    col_config = {
        'Param-ID': st.column_config.TextColumn('Param-ID', width="small"),
        'Category': st.column_config.TextColumn('Category', width="large"),
        'Ordinary lifetime': st.column_config.NumberColumn(
            'Ordinary lifetime',
            min_value=4,
            max_value=150,
            step=1,
            format="%d yrs",
            width="small",
        ),
        'Tail period': st.column_config.NumberColumn(
            'Tail period',
            min_value=1,
            max_value=50,
            step=1,
            format="%d yrs",
            width="small",
        ),
    }
    if has_context:
        col_config['Dep ord (Mkr)'] = st.column_config.NumberColumn(
            'Dep ord (Mkr)', format="%.1f", width="small",
            help="Read-only",
        )
        col_config['Dep tail (Mkr)'] = st.column_config.NumberColumn(
            'Dep tail (Mkr)', format="%.1f", width="small",
            help="Read-only",
        )

    edited_df = st.data_editor(
        display_df,
        width='stretch',
        hide_index=True,
        num_rows="fixed",
        disabled=disabled_cols,
        column_config=col_config,
        key=f"{MODULE_KEY}_cat_editor",
    )

    return _extract_lifetime_changes(edited_df, original_display, baseline_df)


# =============================================================================
# CONTEXT DATA HELPERS
# =============================================================================

@st.cache_data(ttl=3600, show_spinner=False)
def _get_depreciation_context(user_id_network: int) -> pd.DataFrame:
    """
    Load company's baseline depreciation per category for 2024 (sum of H1+H2).

    Returns DataFrame with cat_encode, Dep ord (Mkr), Dep tail (Mkr).
    """
    from data_loaders.rab_data import load_user_capcost

    df = load_user_capcost(user_id_network)
    if df.empty:
        return pd.DataFrame(columns=['cat_encode', 'Dep ord (Mkr)', 'Dep tail (Mkr)'])

    # Sum 2024 H1 (229) + H2 (230) for annual 2024 depreciation
    df_2024 = df[df['time'].isin([229, 230])].copy()
    if df_2024.empty:
        return pd.DataFrame(columns=['cat_encode', 'Dep ord (Mkr)', 'Dep tail (Mkr)'])

    agg = df_2024.groupby('cat_encode').agg(
        dep_ord=('dep_ord', 'sum'),
        dep_tail=('dep_tail', 'sum'),
    ).reset_index()

    agg['Dep ord (Mkr)'] = agg['dep_ord'] / 1_000
    agg['Dep tail (Mkr)'] = agg['dep_tail'] / 1_000
    return agg[['cat_encode', 'Dep ord (Mkr)', 'Dep tail (Mkr)']]


# =============================================================================
# EXTRACTION HELPERS
# =============================================================================

def _extract_lifetime_changes(
    edited_df: pd.DataFrame,
    original_df: pd.DataFrame,
    baseline_df: pd.DataFrame
) -> tuple[Optional[Dict[int, Dict[str, int]]], Optional[str]]:
    """Extract lifetime adjustments for category level."""
    adjustments = {}
    clamped_messages = []

    for idx, edited_row in edited_df.iterrows():
        original_row = original_df.iloc[idx]
        baseline_row = baseline_df.iloc[idx]
        code = int(baseline_row['_cat_encode'])
        cat_name = baseline_row['Category']

        if pd.isna(edited_row['Ordinary lifetime']) or pd.isna(edited_row['Tail period']):
            continue

        new_ekdep = int(edited_row['Ordinary lifetime'])
        new_tail = int(edited_row['Tail period'])

        if new_tail > new_ekdep:
            clamped_messages.append(
                f"{cat_name}: tail ({new_tail} yrs) exceeds ordinary lifetime ({new_ekdep} yrs)"
                f", clamped to {new_ekdep} yrs in calculations"
            )
            new_tail = new_ekdep

        baseline_ekdep = int(baseline_row['_baseline_ekdep'])
        baseline_tail = int(baseline_row['_baseline_tail'])

        if new_ekdep != baseline_ekdep or new_tail != baseline_tail:
            adjustments[code] = {
                'ekdep': new_ekdep,
                'maxdep': new_ekdep + new_tail
            }

    if clamped_messages:
        info_msg = ". ".join(clamped_messages) + ". Adjust corresponding values above to resolve."
    else:
        info_msg = None
    return adjustments if adjustments else None, info_msg
"""
Module 4: Operating Expenditures

Handles controllable and non-controllable cost category overrides.
Parameter-IDs: 4.1.X (controllable categories), 4.2.X (non-controllable categories)
Variable-IDs: 40.X

Section-based rendering:
- render_scaling() -> 4.1 Controllable + 4.2 Non-controllable category scaling
- render_opex_vars() -> 40.X OPEX variables (reserved for future)
"""

import streamlit as st
import pandas as pd
from typing import Dict, Any, Optional

from frontend.utils.state_manager import get_config_value

MODULE_KEY = "m4_operating_exp"

# Controllable cost categories (from controllable_a.parquet)
CONTROLLABLE_CATEGORIES = [
    ("4.1.1", "RR7320_power_purchase", "Power purchase (RR7320)"),
    ("4.1.2", "RR73120_materials", "Materials (RR73120)"),
    ("4.1.3", "RR73130_external_services", "External services (RR73130)"),
    ("4.1.4", "RR73140_personnel", "Personnel costs (RR73140)"),
    ("4.1.5", "RR73180_other_operating", "Other operating (RR73180)"),
    ("4.1.6", "RR71_adjustments", "RR71 adjustments"),
    ("4.1.7", "KENT_deductions", "KENT/TN deductions"),
    ("4.1.8", "capital_cost_outside_base", "Capital cost outside base"),
    ("4.1.9", "neo_adjustments_per_year", "Neo adjustments (per year)"),
]

# Non-controllable cost categories (from non_controllable_a.parquet)
NON_CONTROLLABLE_CATEGORIES = [
    ("4.2.1", "network_loss_purchased", "Network loss - purchased"),
    ("4.2.2", "network_loss_own_production", "Network loss - own production"),
    ("4.2.3", "grid_subscription", "Grid subscription"),
    ("4.2.4", "grid_connection", "Grid connection"),
    ("4.2.5", "feed_in_compensation", "Feed-in compensation"),
    ("4.2.6", "regulatory_fees", "Regulatory fees"),
    ("4.2.7", "capacity_reserve", "Capacity reserve"),
]


def render_scaling() -> Dict[str, Any]:
    """
    Render M4 scaling section: controllable and non-controllable category overrides.

    Returns:
        Dict with controllable_category_overrides and non_controllable_category_overrides
    """
    config: Dict[str, Any] = {}

    # === 4.1 Controllable cost categories ===
    ctrl_overrides = _render_controllable_scaling()
    if ctrl_overrides:
        config["controllable_category_overrides"] = ctrl_overrides

    st.markdown("---")

    # === 4.2 Non-controllable cost categories ===
    nonctrl_overrides = _render_non_controllable_scaling()
    if nonctrl_overrides:
        config["non_controllable_category_overrides"] = nonctrl_overrides

    return config


def render_opex_vars() -> Dict[str, Any]:
    """
    Render M4 variables section: 40.X OPEX variables.

    Returns:
        Dict with OPEX variable overrides
    """
    config: Dict[str, Any] = {}

    st.markdown("##### 40.X OPEX variables")
    st.info(
        "OPEX variables (40.X) - planned for future release:\n"
        "- 40.1.1 Adjusted OPEX (OPEXp)\n"
        "- 40.1.2 Flexibility service cost\n"
        "- 40.2.1 Total non-adjustable costs (prognosis)"
    )

    return config


# =============================================================================
# CONTROLLABLE CATEGORIES
# =============================================================================

def _render_controllable_scaling() -> Optional[Dict[str, float]]:
    """Render controllable cost category scaling (Param 4.1.1-4.1.9)."""
    st.markdown("##### 4.1 Controllable cost categories")
    st.caption(
        "Scale controllable cost categories for your company. "
        "Affects DEA input (controllable_cost_average) and revenue frame. "
        "(Parameter-IDs: 4.1.1-4.1.9)"
    )

    # Build dataframe for editor
    data = []
    ctrl_conf = get_config_value(MODULE_KEY, "controllable_category_overrides", None)
    for param_id, cat_key, label in CONTROLLABLE_CATEGORIES:
        initial = 1.0
        if isinstance(ctrl_conf, dict):
            initial = float(ctrl_conf.get(cat_key, 1.0))
        data.append({
            "Param-ID": param_id,
            "Category": label,
            "Scaling": initial,
            "_cat_key": cat_key,
        })

    df = pd.DataFrame(data)

    edited_df = st.data_editor(
        df[["Param-ID", "Category", "Scaling"]],
        width="stretch",
        hide_index=True,
        num_rows="fixed",
        disabled=["Param-ID", "Category"],
        column_config={
            "Param-ID": st.column_config.TextColumn("Param-ID", width="small"),
            "Category": st.column_config.TextColumn("Category", width="large"),
            "Scaling": st.column_config.NumberColumn(
                "Scaling", min_value=0.5, max_value=2.0, step=0.01, format="%.2f"
            ),
        },
        key="m4_ctrl_cat_editor",
    )

    # Extract overrides (only where scaling != 1.0)
    adjustments: Dict[str, float] = {}
    for i, row in edited_df.iterrows():
        scaling = float(row["Scaling"])
        if abs(scaling - 1.0) > 1e-9:
            cat_key = df.iloc[i]["_cat_key"]
            adjustments[cat_key] = scaling

    if adjustments:
        st.caption(
            f":orange[Modified] - {len(adjustments)} controllable category scaling(s)"
        )

    return adjustments if adjustments else None


# =============================================================================
# NON-CONTROLLABLE CATEGORIES
# =============================================================================

def _render_non_controllable_scaling() -> Optional[Dict[str, float]]:
    """Render non-controllable cost category scaling (Param 4.2.1-4.2.7)."""
    st.markdown("##### 4.2 Non-controllable cost categories")
    st.caption(
        "Scale non-controllable (KENT) cost categories for your company. "
        "Only affects revenue frame (not DEA). "
        "(Parameter-IDs: 4.2.1-4.2.7)"
    )

    data = []
    nonctrl_conf = get_config_value(MODULE_KEY, "non_controllable_category_overrides", None)
    for param_id, cat_key, label in NON_CONTROLLABLE_CATEGORIES:
        initial = 1.0
        if isinstance(nonctrl_conf, dict):
            initial = float(nonctrl_conf.get(cat_key, 1.0))
        data.append({
            "Param-ID": param_id,
            "Category": label,
            "Scaling": initial,
            "_cat_key": cat_key,
        })

    df = pd.DataFrame(data)

    edited_df = st.data_editor(
        df[["Param-ID", "Category", "Scaling"]],
        width="stretch",
        hide_index=True,
        num_rows="fixed",
        disabled=["Param-ID", "Category"],
        column_config={
            "Param-ID": st.column_config.TextColumn("Param-ID", width="small"),
            "Category": st.column_config.TextColumn("Category", width="large"),
            "Scaling": st.column_config.NumberColumn(
                "Scaling", min_value=0.5, max_value=2.0, step=0.01, format="%.2f"
            ),
        },
        key="m4_nonctrl_cat_editor",
    )

    adjustments: Dict[str, float] = {}
    for i, row in edited_df.iterrows():
        scaling = float(row["Scaling"])
        if abs(scaling - 1.0) > 1e-9:
            cat_key = df.iloc[i]["_cat_key"]
            adjustments[cat_key] = scaling

    if adjustments:
        st.caption(
            f":orange[Modified] - {len(adjustments)} non-controllable category scaling(s)"
        )

    return adjustments if adjustments else None

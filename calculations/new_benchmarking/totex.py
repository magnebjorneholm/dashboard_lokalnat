"""
totex.py — assemble the new-model TOTEX per company (the single DEA input).

    opex_new  = controllable_cost_average + loss_valued + non_controllable_selected
    totex_new = opex_new + capital_cost_2024_env_adjusted

All figures annual, in tkr. Each component obeys its on/off switch in the config; a
switched-off component contributes zero so the schema stays stable and the effect of any
single piece can be isolated.
"""

from __future__ import annotations

import pandas as pd

from config.column_names import (
    COL_REID, COL_CONTROLLABLE_AVG, COL_LOSS_VALUED, COL_NONCTRL_SELECTED,
    COL_CAPITAL_COST_ENV_ADJ, COL_OPEX_NEW, COL_TOTEX_NEW,
)
from calculations.new_benchmarking.config import NewBenchmarkingConfig


def build_totex(
    cfg: NewBenchmarkingConfig,
    baseline_df: pd.DataFrame,
    opex_components_df: pd.DataFrame,
    capital_cost_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Combine the OPEX components and the förläggningsmiljö-adjusted capital cost into
    opex_new and totex_new per company.

    Args:
        baseline_df: 148-row frame with REId and controllable_cost_average.
        opex_components_df: from build_opex_components (REId, loss_valued, non_ctrl_selected).
        capital_cost_df: from compute_env_adjusted_capital_cost (REId, capital_cost_2024_env_adjusted).

    Returns one row per REId with the components and the totals.
    """
    df = baseline_df[[COL_REID, COL_CONTROLLABLE_AVG]].copy()
    df = df.merge(opex_components_df, on=COL_REID, how="left")
    df = df.merge(capital_cost_df, on=COL_REID, how="left")

    for col in (COL_CONTROLLABLE_AVG, COL_LOSS_VALUED, COL_NONCTRL_SELECTED, COL_CAPITAL_COST_ENV_ADJ):
        df[col] = df[col].fillna(0.0)

    controllable = df[COL_CONTROLLABLE_AVG] if cfg.include_controllable else 0.0
    losses = df[COL_LOSS_VALUED] if cfg.include_losses else 0.0
    # non-controllable selection is governed by cfg.non_controllable_categories
    nonctrl = df[COL_NONCTRL_SELECTED]
    capex = df[COL_CAPITAL_COST_ENV_ADJ] if cfg.include_capex else 0.0

    df[COL_OPEX_NEW] = controllable + losses + nonctrl
    df[COL_TOTEX_NEW] = df[COL_OPEX_NEW] + capex
    return df

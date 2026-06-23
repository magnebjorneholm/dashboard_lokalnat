"""
totex.py — assemble the new-model TOTEX per company (the single DEA input).

    opex_new  = opexp_dea + loss_valued + non_controllable_selected
    totex_new = opex_new + capital_cost_2024_env_adjusted

The frontier/DEA payable-cost post is Ei's raw OPEXp (opexp_dea), NOT the requirement-side
controllable_cost_average. The two are distinct quantities and must never be conflated:
benchmarking (the frontier) runs on opexp_dea; the efficiency requirement is later applied
to the SDF controllable_cost_average via the kr application base (cost_impact.py). Running
the DEA on opexp_dea is what reproduces Ei's published frontier; the controllable average is
carried through this frame only because cost_impact reads it for the requirement base.

All figures annual, in tkr. Each component obeys its on/off switch in the config; a
switched-off component contributes zero so the schema stays stable and the effect of any
single piece can be isolated.
"""

from __future__ import annotations

import pandas as pd

from config.column_names import (
    COL_REID, COL_CONTROLLABLE_AVG, COL_OPEXP_DEA, COL_LOSS_VALUED, COL_NONCTRL_SELECTED,
    COL_CAPITAL_COST_ENV_ADJ, COL_OPEX_NEW, COL_TOTEX_NEW, COL_CAPITAL_COST_2024,
    COL_NONCTRL_GRID_SUBSCRIPTION, COL_NONCTRL_GRID_CONNECTION,
    COL_NONCTRL_FEED_IN, COL_NONCTRL_CAPACITY_RESERVE,
    COL_CAPEX_CORR_CABLE, COL_CAPEX_CORR_STATION,
)
from new_benchmarking_model.config import NewBenchmarkingConfig

# Granular per-category / per-asset bridge columns carried through for the waterfall only;
# they never enter opex_new or totex_new (those use the aggregates).
_BRIDGE_BREAKDOWN_COLS = (
    COL_NONCTRL_GRID_SUBSCRIPTION, COL_NONCTRL_GRID_CONNECTION,
    COL_NONCTRL_FEED_IN, COL_NONCTRL_CAPACITY_RESERVE,
    COL_CAPEX_CORR_CABLE, COL_CAPEX_CORR_STATION,
)


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
        baseline_df: 148-row frame with REId, controllable_cost_average and the
            unadjusted capital_cost_2024 (carried through for the bridge waterfall).
        opex_components_df: from build_opex_components (REId, loss_valued, non_ctrl_selected).
        capital_cost_df: from compute_env_adjusted_capital_cost (REId, capital_cost_2024_env_adjusted).

    Returns one row per REId with the components and the totals. capital_cost_2024 (the
    unadjusted current-model capital cost) is kept alongside the env-adjusted one so the UI
    can bridge from the current TOTEX to the new TOTEX without re-reading baseline.
    """
    df = baseline_df[[COL_REID, COL_CONTROLLABLE_AVG, COL_OPEXP_DEA, COL_CAPITAL_COST_2024]].copy()
    df = df.merge(opex_components_df, on=COL_REID, how="left")
    df = df.merge(capital_cost_df, on=COL_REID, how="left")

    for col in (COL_CONTROLLABLE_AVG, COL_OPEXP_DEA, COL_LOSS_VALUED, COL_NONCTRL_SELECTED,
                COL_CAPITAL_COST_ENV_ADJ, *_BRIDGE_BREAKDOWN_COLS):
        df[col] = df[col].fillna(0.0)

    # Frontier payable post = opexp_dea (NOT controllable_cost_average — see module docstring).
    payable = df[COL_OPEXP_DEA] if cfg.include_controllable else 0.0
    losses = df[COL_LOSS_VALUED] if cfg.include_losses else 0.0
    # non-controllable selection is governed by cfg.non_controllable_categories
    nonctrl = df[COL_NONCTRL_SELECTED]
    capex = df[COL_CAPITAL_COST_ENV_ADJ] if cfg.include_capex else 0.0

    df[COL_OPEX_NEW] = payable + losses + nonctrl
    df[COL_TOTEX_NEW] = df[COL_OPEX_NEW] + capex
    return df

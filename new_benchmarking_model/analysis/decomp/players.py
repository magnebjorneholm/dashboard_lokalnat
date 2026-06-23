"""
players.py — the 7 cost-component players and how each composes a DEA subset.

The decomposition follows the nested waterfall (new_benchmarking_model/ui/charts.py,
render_shapley_waterfall): a phase-1 outer layer ("how the requirement is calculated")
and a phase-2 inner layer ("the cost components"). This module owns phase 2.

Phase-1 baseline v(∅) — the input every phase-2 player builds on:

    v(∅) input = opexp_dea + capex_unadj            (raw OPEXp + UNADJUSTED capital cost)
    v(∅) outputs = NEW_MODEL_BASE_OUTPUTS           (CU, MW, NS, MWhl, MWhh; no cable)

Phase-2 players (7). Five add an input cost post, one swaps capex to its env-adjusted
value, one adds the cable-length output:

    losses             + loss_valued
    grid_subscription  + grid_subscription
    grid_connection    + grid_connection
    feed_in            + feed_in
    capacity_reserve   + capacity_reserve
    capex_adj          capex_unadj → capex_adj      (förläggningsmiljö levelling)
    cable              + cable_length_km  (output)

The four non-controllable categories are the split of the old single `nonctrl` player
(players 4→7). All composition is pure arithmetic on the analysis spine — no KENT, no
re-read. v(N) (all players on) reproduces the bundle's totex_new DEA input exactly.
"""

from __future__ import annotations

from typing import FrozenSet, List

import pandas as pd

from config.column_names import COL_CABLE_LENGTH_KM
from new_benchmarking_model.config import NEW_MODEL_BASE_OUTPUTS

# Ordered player catalog (kept stable: the bitmask encoding in io.py depends on this order).
PLAYERS: tuple[str, ...] = (
    "losses",
    "grid_subscription",
    "grid_connection",
    "feed_in",
    "capacity_reserve",
    "capex_adj",
    "cable",
)
N_PLAYERS = len(PLAYERS)

# Players that add a spine cost column to the DEA input.
_INPUT_ADD: dict[str, str] = {
    "losses": "loss_valued",
    "grid_subscription": "grid_subscription",
    "grid_connection": "grid_connection",
    "feed_in": "feed_in",
    "capacity_reserve": "capacity_reserve",
}
_CAPEX_PLAYER = "capex_adj"   # swaps capex_unadj → capex_adj
_CABLE_PLAYER = "cable"       # adds the cable-length output

BASE_OUTPUTS: tuple[str, ...] = tuple(NEW_MODEL_BASE_OUTPUTS)


def subset_input(spine: pd.DataFrame, S: FrozenSet[str]) -> pd.Series:
    """The single DEA input column for player-subset S (pure arithmetic on the spine).

    Starts from the phase-1 baseline opexp_dea, adds every active input player, and uses
    env-adjusted capex iff capex_adj ∈ S (else unadjusted). cable is an output, not here.
    """
    inp = spine["opexp_dea"].copy()
    for player, col in _INPUT_ADD.items():
        if player in S:
            inp = inp + spine[col]
    inp = inp + (spine["capex_adj"] if _CAPEX_PLAYER in S else spine["capex_unadj"])
    return inp


def subset_outputs(S: FrozenSet[str]) -> List[str]:
    """DEA output columns for subset S — base outputs, plus cable length iff cable ∈ S."""
    return list(BASE_OUTPUTS) + ([COL_CABLE_LENGTH_KM] if _CABLE_PLAYER in S else [])

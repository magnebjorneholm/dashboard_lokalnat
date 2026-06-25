"""Compare a ReplicationResult against Ei's published facit."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .data import KNOWN_NONREPLICABLE, ModelData, load_facit
from .replicate import ReplicationResult


@dataclass
class Comparison:
    """Outcome of comparing replication vs facit (excluding the known anomaly)."""

    table: pd.DataFrame  # per-firm replicated/facit/diff columns
    max_eff_diff: float
    max_seff_diff: float
    n_eff_exceeding: int  # firms with |eff diff| above tolerance
    n_seff_exceeding: int
    tolerance: float
    excluded: list[str]  # firm ids excluded from the max-diff stats
    passed: bool


def build_table(md: ModelData, res: ReplicationResult,
                facit: pd.DataFrame | None = None) -> pd.DataFrame:
    """Join replication and facit row-for-row into a tidy DataFrame."""
    if facit is None:
        facit = load_facit()
    return pd.DataFrame({
        "REId": md.reid,
        "is_outlier": res.is_outlier,
        "eff_repl": res.efficiency,
        "eff_facit": facit["Effektivitet"].to_numpy(float),
        "seff_repl": res.super_efficiency,
        "seff_facit": facit["Supereffektivitet"].to_numpy(float),
    }).assign(
        eff_diff=lambda d: (d.eff_repl - d.eff_facit).abs(),
        seff_diff=lambda d: (d.seff_repl - d.seff_facit).abs(),
    )


def compare(md: ModelData, res: ReplicationResult, *, tolerance: float = 5e-9,
            facit: pd.DataFrame | None = None,
            exclude: tuple[str, ...] = (KNOWN_NONREPLICABLE,)) -> Comparison:
    """Compare replication to facit, excluding known-non-replicable firms.

    ``tolerance`` defaults to 5e-9 (the solver tolerance quoted in
    eis_dea_metod.md). The comparison "passes" when no included firm's
    efficiency or super-efficiency differs from facit by more than that.
    """
    table = build_table(md, res, facit)
    incl = ~table["REId"].isin(exclude)
    sub = table[incl]

    max_eff = float(np.nanmax(sub["eff_diff"]))
    max_seff = float(np.nanmax(sub["seff_diff"]))
    n_eff = int((sub["eff_diff"] > tolerance).sum())
    n_seff = int((sub["seff_diff"] > tolerance).sum())

    return Comparison(
        table=table,
        max_eff_diff=max_eff,
        max_seff_diff=max_seff,
        n_eff_exceeding=n_eff,
        n_seff_exceeding=n_seff,
        tolerance=tolerance,
        excluded=list(exclude),
        passed=(n_eff == 0 and n_seff == 0),
    )

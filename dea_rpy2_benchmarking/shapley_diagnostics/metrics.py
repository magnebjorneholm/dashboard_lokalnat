"""Native Benchmarking diagnostics per coalition (the new outputs).

For each coalition we derive, on the STANDARD frontier (per Erik's choice, not the
super-efficiency frontier), the structural diagnostics that reveal how brittle the
DEA result is to which cost posts are included:

    super-efficiency  theta (leave-one-out)        -> from scoring.py (sdea)
    number.peers      how load-bearing each frontier firm is
    n_peers_per_firm  how many peers each firm leans on
    shadow prices     u (input multipliers), v (output multipliers)   (dea.dual)

The frontier is built over the fixed frozen reference set R (the 144 firms that
are neither Ei-excluded nor the frozen REL03016). R's *inputs* change between
coalitions (each player adds a cost post / swaps capex / adds the cable output),
so peers and shadow prices move between coalitions — that movement is the
fragility signal. All diagnostics are therefore indexed by the reference firms.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from config.column_names import COL_REID
from new_benchmarking_model.analysis.decomp.players import subset_input, subset_outputs
from new_benchmarking_model.config import NewBenchmarkingConfig

from .scoring import FROZEN_REIDS, _np2r, _r2np
from dea_benchmarking.r_session import get_benchmarking

_PEER_TOL = 1e-6


@dataclass
class CoalitionDiagnostics:
    """Standard-frontier diagnostics for one coalition, indexed by reference firms."""

    ref_reid: np.ndarray          # the reference firms these rows refer to
    number_peers: np.ndarray      # times each ref firm serves as a peer (load-bearing)
    n_peers_per_firm: np.ndarray  # peers each ref firm leans on
    eff_standard: np.ndarray      # standard (capped) efficiency on the reference frontier
    u: np.ndarray                 # input multipliers  (n_ref x n_inputs)
    v: np.ndarray                 # output multipliers (n_ref x n_outputs)
    input_names: list[str]
    output_names: list[str]


def coalition_diagnostics(spine: pd.DataFrame, S, *,
                          cfg: NewBenchmarkingConfig | None = None) -> CoalitionDiagnostics:
    """Compute standard-frontier peers + shadow prices for coalition S (frozen R)."""
    cfg = cfg or NewBenchmarkingConfig()
    bench = get_benchmarking()
    reids = spine[COL_REID].to_numpy()
    ref_mask = ~np.isin(reids, FROZEN_REIDS)
    ref_idx = np.where(ref_mask)[0]

    out_cols = subset_outputs(S)
    X = subset_input(spine, S).to_numpy(dtype=float).reshape(-1, 1)[ref_idx]
    Y = spine[out_cols].to_numpy(dtype=float)[ref_idx]

    Xr, Yr = _np2r(X), _np2r(Y)

    # Standard DEA (self-referenced over R) -> efficiency + lambda (peer structure).
    e = bench.dea(Xr, Yr, RTS=cfg.rts, ORIENTATION="in")
    eff = _r2np(e.rx2("eff")).ravel()
    lam = _r2np(e.rx2("lambda"))
    if lam.ndim == 1:
        lam = lam.reshape(len(eff), -1)
    active = np.abs(lam) > _PEER_TOL
    number_peers = active.sum(axis=0).astype(float)      # per reference (column)
    n_peers_per_firm = active.sum(axis=1).astype(float)  # per scored firm (row)

    # Shadow prices / multipliers on the standard frontier (dea.dual).
    d = bench.dea_dual(Xr, Yr, RTS=cfg.rts, ORIENTATION="in")
    u = _r2np(d.rx2("u"))
    v = _r2np(d.rx2("v"))
    if u.ndim == 1:
        u = u.reshape(len(eff), -1)
    if v.ndim == 1:
        v = v.reshape(len(eff), -1)

    return CoalitionDiagnostics(
        ref_reid=reids[ref_idx],
        number_peers=number_peers,
        n_peers_per_firm=n_peers_per_firm,
        eff_standard=np.minimum(eff, 1.0),
        u=u, v=v,
        input_names=["totex"],
        output_names=list(out_cols),
    )

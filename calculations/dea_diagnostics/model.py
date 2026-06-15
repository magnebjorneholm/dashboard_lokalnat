"""
calculations/dea_diagnostics/model.py

Orchestration for the DEA-diagnostics standalone tool.

`run_dea_diagnostics(cfg, df)`:
    1. map COL_* inputs/outputs out of the all-companies frame,
    2. detect outliers via the shared frontier routine (super-eff + IQR),
    3. solve standard DEA (primal + dual) on the cleaned reference set,
    4. apply the selected diagnostics from the registry.

Pure logic: takes the all-companies DataFrame, returns a result dataclass. No
Streamlit, no data loading. Super-efficiency is confined to outlier detection;
the main solve is standard DEA (theta <= 1).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

import numpy as np
import pandas as pd

from calculations.dea_diagnostics.config import DeaDiagnosticsConfig
from calculations.dea_diagnostics import registry as reg
from calculations.dea_diagnostics.solvers import solve_dual, solve_primal
from calculations.frontier.outliers import detect_outliers_iterative


@dataclass
class DeaDiagnosticsResult:
    """Result of one DEA-diagnostics run.

    Cleaned-set arrays (firms, theta_*, lambdas, mu, nu) are indexed over the
    non-outlier firms in firm order. Outlier bookkeeping (all_firms, is_outlier,
    outlier_super_eff) spans the full sample.
    """

    config: DeaDiagnosticsConfig
    input_labels: List[str]
    output_labels: List[str]

    # Full-sample outlier bookkeeping
    all_firms: np.ndarray            # (n_all,) REIds
    is_outlier: np.ndarray           # (n_all,) bool
    outlier_super_eff: np.ndarray    # (n_all,) flag-time super-eff score; NaN if not flagged
    n_outlier_rounds: int

    # Cleaned-set solve
    firms: np.ndarray                # (n,) REIds
    theta_primal: np.ndarray         # (n,)
    theta_dual: np.ndarray           # (n,)
    lambdas: np.ndarray              # (n, n)
    mu: np.ndarray                   # (n, K)
    nu: np.ndarray                   # (n, J)
    primal_dual_max_abs_diff: float

    diagnostics: Dict[str, reg.DiagnosticOutput] = field(default_factory=dict)


def run_dea_diagnostics(
    cfg: DeaDiagnosticsConfig,
    df: pd.DataFrame,
) -> DeaDiagnosticsResult:
    """Run a full DEA-diagnostics pass.

    Args:
        cfg: the run configuration (inputs/outputs, RTS, outlier params, selection).
        df:  all-companies frame with a 'REId' column plus every cfg input/output.
    """
    if "REId" not in df.columns:
        raise ValueError("DataFrame must contain column 'REId'")

    input_cols = list(cfg.inputs)
    output_cols = list(cfg.outputs)

    missing = [c for c in input_cols + output_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Columns not found in data: {missing}")

    df = df.copy()
    inputs = df[input_cols].apply(pd.to_numeric, errors="coerce").values
    outputs = df[output_cols].apply(pd.to_numeric, errors="coerce").values
    all_firms = df["REId"].values

    n_all = len(df)

    # ── Outlier detection (super-eff + IQR), shared with the pipeline ────────
    if cfg.outlier_enable:
        out = detect_outliers_iterative(
            inputs, outputs, cfg.rts,
            q_lower=cfg.outlier_q_lower,
            q_upper=cfg.outlier_q_upper,
            multiplier=cfg.outlier_multiplier,
            max_rounds=cfg.outlier_max_rounds,
        )
        is_outlier = out.is_outlier
        outlier_super_eff = out.flag_scores
        n_rounds = out.n_rounds
    else:
        is_outlier = np.zeros(n_all, dtype=bool)
        outlier_super_eff = np.full(n_all, np.nan)
        n_rounds = 0

    clean = ~is_outlier
    x = inputs[clean]
    y = outputs[clean]
    firms = all_firms[clean]

    # ── Main solve: standard DEA, primal + dual ──────────────────────────────
    primal = solve_primal(x, y, rts=cfg.rts, super_eff=False)
    dual = solve_dual(x, y, rts=cfg.rts, super_eff=False)

    both_ok = np.isfinite(primal.theta) & np.isfinite(dual.theta)
    max_diff = (
        float(np.max(np.abs(primal.theta[both_ok] - dual.theta[both_ok])))
        if both_ok.any() else float("nan")
    )

    # ── Diagnostics ──────────────────────────────────────────────────────────
    ctx = reg.DeaSolveContext.build(
        firms=firms,
        input_labels=input_cols,
        output_labels=output_cols,
        x=x, y=y,
        theta=primal.theta,
        lambdas=primal.lambdas,
        mu=dual.mu,
        nu=dual.nu,
    )

    keys = list(cfg.diagnostics) if cfg.diagnostics is not None else reg.all_keys()
    diagnostics = {k: reg.compute(reg.get_spec(k), ctx) for k in keys}

    return DeaDiagnosticsResult(
        config=cfg,
        input_labels=input_cols,
        output_labels=output_cols,
        all_firms=all_firms,
        is_outlier=is_outlier,
        outlier_super_eff=outlier_super_eff,
        n_outlier_rounds=n_rounds,
        firms=firms,
        theta_primal=primal.theta,
        theta_dual=dual.theta,
        lambdas=primal.lambdas,
        mu=dual.mu,
        nu=dual.nu,
        primal_dual_max_abs_diff=max_diff,
        diagnostics=diagnostics,
    )

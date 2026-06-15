"""
calculations/dea_diagnostics/solvers.py

Primal (envelopment) and dual (multiplier) DEA LP builders.

Both input-oriented. CRS or VRS. Optional super-efficiency (leave-one-out).
By LP duality the two formulations return identical theta within numerical
tolerance.

Primal returns lambda intensity weights (peer references).
Dual returns nu input multipliers and mu output multipliers (plus omega for VRS).

Note: these solvers internally rescale each column to mean ~1 for conditioning.
theta is scale-invariant, so this does not affect efficiency scores or the
reproduction of Ei's results; multipliers are unscaled back to raw units.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pulp

RTS = Literal["crs", "vrs"]


@dataclass
class PrimalResult:
    theta: np.ndarray        # (n,) efficiency; may exceed 1 under super-efficiency
    lambdas: np.ndarray      # (n, n) intensity weights; lambdas[o, r] = weight of peer r for firm o
    status: list[str]        # per-firm solver status


@dataclass
class DualResult:
    theta: np.ndarray        # (n,) efficiency = dual objective value
    nu: np.ndarray           # (n, n_inputs) input multipliers
    mu: np.ndarray           # (n, n_outputs) output multipliers
    omega: np.ndarray        # (n,) free scale term; zeros under CRS
    status: list[str]


def _column_scales(arr: np.ndarray) -> np.ndarray:
    """Per-column mean of positive entries; 1.0 for all-zero columns.

    DEA efficiency is invariant to per-column rescaling of inputs and outputs.
    Normalizing each column to mean ~1 keeps the LP well-conditioned when raw
    data spans several orders of magnitude (e.g. TOTEX ~10^3..10^7, MWh ~10^3..10^7).
    """
    pos_mean = np.where(arr > 0, arr, np.nan)
    scales = np.nanmean(pos_mean, axis=0)
    scales = np.where(np.isfinite(scales) & (scales > 0), scales, 1.0)
    return scales


def solve_primal(
    x: np.ndarray,
    y: np.ndarray,
    rts: RTS = "crs",
    super_eff: bool = False,
) -> PrimalResult:
    """Envelopment (primal) input-oriented DEA.

    For firm o:
        min theta
        s.t.  sum_r lambda_r * y_rk >= y_ok             for k = 1..K
              sum_r lambda_r * x_rj <= theta * x_oj      for j = 1..J
              lambda_r >= 0
              sum_r lambda_r = 1                         (VRS only)
              r != o                                     (super_eff only)

    Inputs and outputs are internally scaled to mean ~1 per column for numerical
    conditioning; theta and lambdas are scale-invariant so no unscaling is needed.
    """
    x_scale = _column_scales(x)
    y_scale = _column_scales(y)
    x_s = x / x_scale
    y_s = y / y_scale

    n, J = x_s.shape
    _, K = y_s.shape

    theta = np.full(n, np.nan)
    lambdas = np.zeros((n, n))
    status: list[str] = []

    for o in range(n):
        prob = pulp.LpProblem(f"primal_{o}", pulp.LpMinimize)
        th = pulp.LpVariable("theta", lowBound=0.0)
        lam = [pulp.LpVariable(f"lam_{r}", lowBound=0.0) for r in range(n)]

        prob += th

        ref = [r for r in range(n) if not (super_eff and r == o)]

        for k in range(K):
            prob += pulp.lpSum(lam[r] * y_s[r, k] for r in ref) >= y_s[o, k]
        for j in range(J):
            prob += pulp.lpSum(lam[r] * x_s[r, j] for r in ref) <= th * x_s[o, j]

        if rts == "vrs":
            prob += pulp.lpSum(lam[r] for r in ref) == 1

        prob.solve(pulp.PULP_CBC_CMD(msg=0))
        st = pulp.LpStatus[prob.status]
        status.append(st)

        if st == "Optimal":
            theta[o] = pulp.value(th)
            for r in ref:
                lambdas[o, r] = pulp.value(lam[r]) or 0.0

    return PrimalResult(theta=theta, lambdas=lambdas, status=status)


def solve_dual(
    x: np.ndarray,
    y: np.ndarray,
    rts: RTS = "crs",
    super_eff: bool = False,
) -> DualResult:
    """Multiplier (dual) input-oriented DEA.

    For firm o:
        max   sum_k mu_k * y_ok    ( + omega under VRS )
        s.t.  sum_j nu_j * x_oj = 1                              (normalization)
              sum_k mu_k * y_rk - sum_j nu_j * x_rj <= 0          for r = 1..n (CRS)
              sum_k mu_k * y_rk - sum_j nu_j * x_rj + omega <= 0  for r = 1..n (VRS, omega free)
              mu_k, nu_j >= 0
              r != o                                              (super_eff only)
    """
    x_scale = _column_scales(x)
    y_scale = _column_scales(y)
    x_s = x / x_scale
    y_s = y / y_scale

    n, J = x_s.shape
    _, K = y_s.shape

    theta = np.full(n, np.nan)
    nu_scaled = np.zeros((n, J))
    mu_scaled = np.zeros((n, K))
    omega = np.zeros(n)
    status: list[str] = []

    for o in range(n):
        prob = pulp.LpProblem(f"dual_{o}", pulp.LpMaximize)
        nu_o = [pulp.LpVariable(f"nu_{j}", lowBound=0.0) for j in range(J)]
        mu_o = [pulp.LpVariable(f"mu_{k}", lowBound=0.0) for k in range(K)]
        om = pulp.LpVariable("omega", lowBound=None) if rts == "vrs" else None

        if rts == "vrs":
            prob += pulp.lpSum(mu_o[k] * y_s[o, k] for k in range(K)) + om
        else:
            prob += pulp.lpSum(mu_o[k] * y_s[o, k] for k in range(K))

        prob += pulp.lpSum(nu_o[j] * x_s[o, j] for j in range(J)) == 1

        ref = [r for r in range(n) if not (super_eff and r == o)]
        for r in ref:
            output_side = pulp.lpSum(mu_o[k] * y_s[r, k] for k in range(K))
            input_side = pulp.lpSum(nu_o[j] * x_s[r, j] for j in range(J))
            if rts == "vrs":
                prob += output_side - input_side + om <= 0
            else:
                prob += output_side - input_side <= 0

        prob.solve(pulp.PULP_CBC_CMD(msg=0))
        st = pulp.LpStatus[prob.status]
        status.append(st)

        if st == "Optimal":
            theta[o] = pulp.value(prob.objective)
            for j in range(J):
                nu_scaled[o, j] = pulp.value(nu_o[j]) or 0.0
            for k in range(K):
                mu_scaled[o, k] = pulp.value(mu_o[k]) or 0.0
            if rts == "vrs":
                omega[o] = pulp.value(om) or 0.0

    # Unscale multipliers back to original-data units so virtual shares
    # mu * y and nu * x are evaluated in raw units downstream.
    nu = nu_scaled / x_scale
    mu = mu_scaled / y_scale

    return DualResult(theta=theta, nu=nu, mu=mu, omega=omega, status=status)

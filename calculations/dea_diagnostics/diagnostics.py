"""
calculations/dea_diagnostics/diagnostics.py

Pure functions deriving firm- and sample-level DEA diagnostics from solver
output. No LP solving here. Each function takes raw numpy arrays so it can
be tested, swapped, or composed independently.

Two families:
    Peer-side  (operate on lambdas from PrimalResult)
    Multiplier-side (operate on mu/nu from DualResult, with raw x/y)
"""

from __future__ import annotations

import numpy as np


# ---------------------------------------------------------------------------
# Peer-side diagnostics  (lambdas: shape (n, n), lambdas[i, j] = weight of peer j for firm i)
# ---------------------------------------------------------------------------

def benchmark_composition(lambdas: np.ndarray, atol: float = 1e-6):
    """Split each firm's intensity vector into a peer *mix* and a *scale*.

    For firm o the (CRS) composite benchmark is the conic combination
        composite_o = sum_r lambda_or * (x_r, y_r).
    Factoring out the total intensity L_o = sum_r lambda_or gives a unit peer
    mix scaled by L_o:
        mix[o, r] = lambda_or / L_o    (each populated row sums to 1)
    This is the "30% A, 20% B, 50% C, scaled L times" reading of a firm's
    reference set. The transpose of `mix` is the dual reading: column o tells how
    much firm o contributes to every other firm's benchmark.

    Returns
    -------
    mix : (n, n) array
        mix[o, r] = lambda_or / sum_r lambda_or; populated rows sum to 1. Rows
        for firms with no active peer (should not happen for a solved firm) are NaN.
    scale : (n,) array
        scale[o] = sum_r lambda_or. Under CRS this doubles as a local
        returns-to-scale signal: < 1 increasing, > 1 decreasing, ~ 1 constant.
    """
    L = lambdas.copy()
    L[np.abs(L) <= atol] = 0.0
    scale = L.sum(axis=1)
    denom = np.where(scale > atol, scale, np.nan)
    mix = L / denom[:, None]
    return mix, scale


def peer_count(lambdas: np.ndarray, exclude_self: bool = True, atol: float = 1e-6) -> np.ndarray:
    """Number of distinct firms that reference firm j as a peer.

    peer_count[j] = |{i : lambda_ij > atol}|  (i != j by default).
    """
    L = lambdas.copy()
    if exclude_self:
        np.fill_diagonal(L, 0.0)
    return (L > atol).sum(axis=0)


def peers_per_firm(lambdas: np.ndarray, exclude_self: bool = True, atol: float = 1e-6) -> np.ndarray:
    """Number of distinct peers each firm i relies on.

    peers_per_firm[i] = |{j : lambda_ij > atol}|.
    """
    L = lambdas.copy()
    if exclude_self:
        np.fill_diagonal(L, 0.0)
    return (L > atol).sum(axis=1)


def isolated_efficient_firms(
    theta: np.ndarray,
    lambdas: np.ndarray,
    eff_tol: float = 1e-6,
    peer_tol: float = 1e-6,
) -> np.ndarray:
    """Boolean mask of efficient firms not referenced by any other firm.

    A firm j is isolated iff:
        theta_j >= 1 - eff_tol  OR  theta_j is NaN (super-eff infeasible),
        AND
        sum_{i != j} 1{lambda_ij > peer_tol} == 0.

    These are firms that score efficient by lack of comparators rather than
    genuine outperformance — unique corners of input-output space.
    """
    efficient = (theta >= 1.0 - eff_tol) | np.isnan(theta)
    referenced_by_others = peer_count(lambdas, exclude_self=True, atol=peer_tol) > 0
    return efficient & ~referenced_by_others


# ---------------------------------------------------------------------------
# Multiplier-side diagnostics  (mu, nu from DualResult; x, y in original units)
# ---------------------------------------------------------------------------

def virtual_inputs(nu: np.ndarray, x: np.ndarray) -> np.ndarray:
    """Per-firm input contributions: VI[i, j] = nu[i, j] * x[i, j].

    Under input-orientation normalization (sum_j nu_ij x_ij = 1), each row
    sums to 1 and entries are read as cost shares of input j in firm i's
    efficiency rating.
    """
    return nu * x


def virtual_outputs(mu: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Per-firm output contributions: VO[i, k] = mu[i, k] * y[i, k].

    Under input-orientation, rows sum to theta_i. Each entry is the
    contribution of output k to firm i's efficiency score.
    """
    return mu * y


def virtual_output_shares(mu: np.ndarray, y: np.ndarray, eps: float = 1e-12) -> np.ndarray:
    """Virtual outputs normalized so each row sums to 1.

    share[i, k] = (mu[i, k] * y[i, k]) / sum_k (mu[i, k] * y[i, k]).
    Useful for cross-firm comparison without theta scale dominating.
    """
    vo = virtual_outputs(mu, y)
    row_sum = vo.sum(axis=1, keepdims=True)
    row_sum = np.where(row_sum > eps, row_sum, np.nan)
    return vo / row_sum


def zero_weight_counts(weights: np.ndarray, atol: float = 1e-6) -> np.ndarray:
    """Per-variable count of firms placing ~zero weight on that variable.

    Works for both mu (output multipliers) and nu (input multipliers).
    Returns shape (n_variables,). High counts flag variables the LP routinely
    ignores (the variable is allowed to "drop out" for that firm).
    """
    return (np.abs(weights) <= atol).sum(axis=0)


def variance_decomposition(virtual_quantities: np.ndarray) -> np.ndarray:
    """Per-variable share of total variance across components (form B).

    For virtual quantities V of shape (n, p):
        share[k] = Var_i(V[i, k]) / sum_j Var_i(V[i, j]).

    Shares are non-negative and sum to 1 by construction, on both input and
    output sides. Each share is read as the fraction of cross-firm variation
    in component contributions attributable to variable k.

    Use this as the primary "which variable drives variation" diagnostic.
    See variance_ratio() for the complementary form A — informative as a
    substitution signal but not a proper share.
    """
    var_components = virtual_quantities.var(axis=0, ddof=1)
    return var_components / var_components.sum()


def variance_ratio(virtual_quantities: np.ndarray) -> np.ndarray:
    """Per-variable variance relative to row-sum variance (form A).

    For virtual quantities V of shape (n, p):
        ratio[k] = Var_i(V[i, k]) / Var_i(sum_j V[i, j]).

    NOT a share — sum across k can be anything >= 0:
        sum_k ratio[k] = 1 - 2*sum_cov / Var(row sum).
    Sum > 1 indicates strong negative covariances between components
    (substitution: when one component drives the row sum, others fade);
    sum < 1 indicates positive covariances (complementarity); sum ~ 1
    means components vary roughly independently.

    Use as a complement to variance_decomposition() to detect substitution
    structure. For the DEA output side, large sums quantify how aggressively
    the LP substitutes between active outputs. For the DEA input side under IO
    normalization (rows sum to 1 -> row-sum variance = 0) this is undefined and
    returns nan; apply only to the output side for DEA.
    """
    var_components = virtual_quantities.var(axis=0, ddof=1)
    var_total = virtual_quantities.sum(axis=1).var(ddof=1)
    if var_total < 1e-10 * max(var_components.max(), 1.0):
        return np.full_like(var_components, np.nan)
    return var_components / var_total

"""DEA diagnostics: standalone deep-dive tool (decoupled from the revenue-cap pipeline).

Pure calculation layer for the DEA-diagnostics standalone tool. Provides primal
(envelopment) and dual (multiplier) DEA solvers plus peer- and multiplier-side
diagnostics. Outlier detection is *not* here: it is shared with the pipeline and
imported from ``calculations.frontier.outliers`` so the two never drift.

This package is self-contained and removable: deleting it leaves the revenue-cap
pipeline untouched (the dependency points here -> frontier, never the reverse).
"""

from calculations.dea_diagnostics.solvers import (
    DualResult,
    PrimalResult,
    solve_dual,
    solve_primal,
)

__all__ = [
    "PrimalResult",
    "DualResult",
    "solve_primal",
    "solve_dual",
]

"""shapley_diagnostics — R/Benchmarking diagnostics over the Shapley coalitions.

Re-runs the new-benchmarking decomposition's per-coalition DEA on R's Benchmarking
(frozen outlier mode) to obtain, for every coalition, the structural diagnostics
PuLP does not expose: super-efficiency, number.peers, and shadow prices — plus
bootstrap inference on the endpoints. Gated by an exact parity check of efficiency
and the two-sided requirement against the existing PuLP value grid.

See README.md.
"""

from __future__ import annotations

from .inference import CoalitionInference, coalition_inference
from .metrics import CoalitionDiagnostics, coalition_diagnostics
from .scoring import CoalitionScore, FROZEN_REIDS, score_coalition

__all__ = [
    "score_coalition",
    "CoalitionScore",
    "coalition_diagnostics",
    "CoalitionDiagnostics",
    "coalition_inference",
    "CoalitionInference",
    "FROZEN_REIDS",
]

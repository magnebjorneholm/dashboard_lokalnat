"""dea_benchmarking — run Bogetoft & Otto's R 'Benchmarking' package from Python.

Quick start:
    from dea_benchmarking import dea, sdea
    res = dea(X, Y, rts="vrs", orientation="in")
    print(res.eff)

Full R API (anything not wrapped) via:
    from dea_benchmarking import package
    bench = package()          # the Benchmarking R package object
    bench.dea_boot(...)        # R's dea.boot, etc.
"""

from __future__ import annotations

from .conversions import as_matrix, check_xy
from .dea import dea, package, sdea
from .r_session import get_benchmarking, r, r_version
from .results import DEAResult

__all__ = [
    "dea",
    "sdea",
    "package",
    "DEAResult",
    "as_matrix",
    "check_xy",
    "get_benchmarking",
    "r",
    "r_version",
]

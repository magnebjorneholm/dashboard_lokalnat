"""
station_capex_adjustment — förläggningsmiljö correction for nätstation capex.

Levels every company's nätstation capital base down to the "outside tätort" cost level
by removing the City-/tätort surcharge, for use as a benchmarking (DEA/TOTEX) input.
Parallel to environment_capex_adjustment (jordkabel); see README.md for the method and
how the data model differs from the cable case.

Typical use:

    from new_benchmarking_model.components.station_capex_adjustment import run_station_adjustment

    result = run_station_adjustment(method="exact")
    result.per_company           # REId, original/adjusted value, effective_pct, reduction_factor
    result.calibration.coverage  # tätort premium + reliability diagnostics
"""

from __future__ import annotations

from . import config as C
from .data import load_station_components, classify_env
from .calibration import calibrate, StationCalibration
from .adjustment import apply_environment_adjustment, EnvironmentAdjustmentResult


def run_station_adjustment(
    capbase_path=None,
    method: str = C.METHOD_EXACT,
    override_percent: dict | None = None,
) -> EnvironmentAdjustmentResult:
    """Load capbase_a, calibrate the tätort premium, and apply the correction. One call."""
    components = load_station_components(capbase_path)
    calib = calibrate(components)
    return apply_environment_adjustment(components, calib, method, override_percent)


__all__ = [
    "run_station_adjustment",
    "load_station_components",
    "classify_env",
    "calibrate",
    "apply_environment_adjustment",
    "StationCalibration",
    "EnvironmentAdjustmentResult",
    "C",
]

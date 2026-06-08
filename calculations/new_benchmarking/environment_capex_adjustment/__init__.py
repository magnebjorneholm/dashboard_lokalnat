"""
environment_capex_adjustment — förläggningsmiljö correction for jordkabel capex.

Levels every company's jordkabel capital base down to the "landsbygd normal" cost
level, for use as a benchmarking (DEA/TOTEX) input. See README.md for the full method.

Typical use:

    from new_benchmarking_model.environment_capex_adjustment import run_environment_adjustment

    result = run_environment_adjustment(method="per_type")
    result.per_company           # REId, original/adjusted value, effective_pct, reduction_factor
    result.calibration.coverage  # per-environment premium + reliability diagnostics
"""

from __future__ import annotations

from . import config as C
from .data import load_jordkabel_components, classify_env
from .calibration import calibrate, EnvironmentCalibration
from .adjustment import apply_environment_adjustment, EnvironmentAdjustmentResult


def run_environment_adjustment(
    capbase_path=None,
    method: str = C.METHOD_PER_TYPE,
    override_percent: dict | None = None,
) -> EnvironmentAdjustmentResult:
    """Load capbase_a, calibrate the premium, and apply the correction. One call."""
    components = load_jordkabel_components(capbase_path)
    calib = calibrate(components)
    return apply_environment_adjustment(components, calib, method, override_percent)


__all__ = [
    "run_environment_adjustment",
    "load_jordkabel_components",
    "classify_env",
    "calibrate",
    "apply_environment_adjustment",
    "EnvironmentCalibration",
    "EnvironmentAdjustmentResult",
    "C",
]

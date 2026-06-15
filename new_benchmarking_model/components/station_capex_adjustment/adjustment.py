"""
adjustment.py — apply the placement-environment correction to each company's nätstationer.

The correction levels every company's station base down to the "outside tätort" cost
level by removing the City-/tätort surcharge. Two methods:

  exact             Per-company: remove the "City- och tätortstillägg nätstation" rows
                    in full (deduction = their value). Base rows are untouched. This uses the
                    actual booked premium, so reduction_factor varies company by company.

  schablon_percent  Schablon, Ei-style: deduction = value × percent[TATORT], applied as a flat
                    haircut across the WHOLE station base. An optional `override_percent` dict
                    (e.g. Ei's published figure) replaces the calibrated percentage. At the
                    sector level this matches `exact`; per company it discards the
                    company-specific tätort share.

Deductions are clipped to [0, value] in magnitude, sign-preserving, so a disposal
(negative value) is never flipped or over-credited. The result is a per-company station
capital-base value; because KENT capital cost is linear in the base value, an integrator
can apply the same `reduction_factor` to the station capital-cost component that enters
benchmarking. The intäktsram itself is unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import config as C
from .calibration import StationCalibration


@dataclass(frozen=True)
class EnvironmentAdjustmentResult:
    method: str
    components: pd.DataFrame        # per-component, with deduction & adjusted_value
    per_company: pd.DataFrame       # per REId: original / deduction / adjusted / effective_pct
    per_company_env: pd.DataFrame   # per (REId, env): original / deduction / adjusted
    calibration: StationCalibration


def _component_deductions(
    components: pd.DataFrame,
    calib: StationCalibration,
    method: str,
    override_percent: dict | None,
) -> pd.Series:
    """
    Return the per-component deduction [SEK] for the chosen method.

    Sign-consistent: capbase_a contains disposals (utrangeringar) with negative value.
    The deduction therefore carries the sign of `value` and its magnitude is capped at
    `abs(value)`, so the correction always shrinks a component toward the outside-tätort
    level without flipping its sign. Base rows get exactly zero under `itemized`.
    """
    env = components[C.COL_ENV]
    value = components[C.COL_VALUE].to_numpy()
    is_tatort = (env == C.TATORT).to_numpy()

    if method == C.METHOD_EXACT:
        # remove the tätort surcharge rows in full; everything else untouched
        ded = np.where(is_tatort, value, 0.0)

    elif method == C.METHOD_SCHABLON_PERCENT:
        rate = float(calib.percent.get(C.TATORT, 0.0))
        if override_percent and C.TATORT in override_percent:
            rate = float(override_percent[C.TATORT])
        # flat schablon haircut across the whole station base
        ded = value * rate

    else:
        raise ValueError(f"Unknown method {method!r}; expected one of {C.METHODS}")

    # cap magnitude at |value|, preserving the deduction's sign
    ded = np.sign(ded) * np.minimum(np.abs(ded), np.abs(value))
    return pd.Series(ded, index=components.index)


def apply_environment_adjustment(
    components: pd.DataFrame,
    calib: StationCalibration,
    method: str = C.METHOD_EXACT,
    override_percent: dict | None = None,
) -> EnvironmentAdjustmentResult:
    """Apply the environment correction and aggregate to company level."""
    comp = components.copy()
    comp[C.COL_DEDUCTION] = _component_deductions(comp, calib, method, override_percent)
    comp[C.COL_ADJ_VALUE] = comp[C.COL_VALUE] - comp[C.COL_DEDUCTION]

    # per (company, env)
    per_company_env = (
        comp.groupby([C.COL_REID, C.COL_ENV], as_index=False)
        .agg(**{
            C.COL_COUNT: (C.COL_COUNT, "sum"),
            C.COL_VALUE: (C.COL_VALUE, "sum"),
            C.COL_DEDUCTION: (C.COL_DEDUCTION, "sum"),
            C.COL_ADJ_VALUE: (C.COL_ADJ_VALUE, "sum"),
        })
    )

    # per company
    per_company = (
        comp.groupby(C.COL_REID, as_index=False)
        .agg(**{
            C.COL_COUNT: (C.COL_COUNT, "sum"),
            C.COL_VALUE: (C.COL_VALUE, "sum"),
            C.COL_DEDUCTION: (C.COL_DEDUCTION, "sum"),
            C.COL_ADJ_VALUE: (C.COL_ADJ_VALUE, "sum"),
        })
    )
    per_company[C.COL_EFFECTIVE_PCT] = np.where(
        per_company[C.COL_VALUE] > 0,
        per_company[C.COL_DEDUCTION] / per_company[C.COL_VALUE],
        0.0,
    )
    per_company[C.COL_REDUCTION_FACTOR] = np.where(
        per_company[C.COL_VALUE] > 0,
        per_company[C.COL_ADJ_VALUE] / per_company[C.COL_VALUE],
        1.0,
    )

    return EnvironmentAdjustmentResult(
        method=method,
        components=comp,
        per_company=per_company,
        per_company_env=per_company_env,
        calibration=calib,
    )

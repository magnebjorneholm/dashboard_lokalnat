"""
adjustment.py — apply the placement-environment correction to each company's jordkabel.

The correction levels every cable down to the landsbygd-normal cost level. Three methods:

  exact             Re-price each component at the landsbygd-normal unit price for its OWN
                    cable type (techspec × volt): adjusted = ref_price × km. Most precise.
                    Components whose type has no landsbygd-normal reference fall back to the
                    schablon_per_km method for their environment.

  schablon_per_km   deduction = km × sek_per_km[env]. One additive premium per environment.

  schablon_percent  deduction = value × percent[env]. One percent per environment. An optional
                    `override_percent` dict (e.g. Ei's published figures) replaces the
                    calibrated percentages.

Reference ("landsbygd normal") and OTHER cables (sjökabel/optokabel/unlabelled) are
never adjusted. Deductions are clipped to [0, value] so no component goes negative.
The result is a per-company jordkabel capital-base value; because KENT capital cost is
linear in the base value, an integrator can apply the same `reduction_factor` to the
jordkabel capital-cost component that enters benchmarking.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import config as C
from .calibration import EnvironmentCalibration


@dataclass(frozen=True)
class EnvironmentAdjustmentResult:
    method: str
    components: pd.DataFrame        # per-component, with deduction & adjusted_value
    per_company: pd.DataFrame       # per REId: original / deduction / adjusted / effective_pct
    per_company_env: pd.DataFrame   # per (REId, env): original / deduction / adjusted
    calibration: EnvironmentCalibration


def _component_deductions(
    components: pd.DataFrame,
    calib: EnvironmentCalibration,
    method: str,
    override_percent: dict | None,
) -> pd.Series:
    """
    Return the per-component deduction [SEK] for the chosen method.

    Sign-consistent: capbase_a contains disposals (utrangeringar) with negative value,
    for which `value != unit_price × km`. The deduction therefore carries the sign of
    `value` and its magnitude is capped at `abs(value)`, so the correction always shrinks
    a component toward the landsbygd-normal level without flipping its sign or
    over-crediting a disposal. Reference and OTHER cables get exactly zero.
    """
    env = components[C.COL_ENV]
    km = components[C.COL_KM].to_numpy()
    value = components[C.COL_VALUE].to_numpy()
    unit = components[C.COL_UNIT_PRICE].to_numpy()
    adjustable = env.isin(C.ADJUSTABLE_ENVS).to_numpy()

    if method == C.METHOD_SCHABLON_PERCENT:
        rates = dict(calib.percent)
        if override_percent:
            rates.update(override_percent)
        rate = env.map(rates).fillna(0.0).to_numpy()
        ded = value * rate

    elif method == C.METHOD_SCHABLON_PER_KM:
        per_km = env.map(calib.sek_per_km).fillna(0.0).to_numpy()
        ded = np.sign(value) * km * per_km

    elif method == C.METHOD_EXACT:
        merged = components.merge(
            calib.ref_price, on=[C.COL_TECHSPEC, C.COL_VOLT], how="left"
        )
        ref_price = merged[C.COL_REF_PRICE].to_numpy()
        has_unit = unit > 0
        matched = ~np.isnan(ref_price) & has_unit
        # exact re-pricing: scale value toward the landsbygd-normal price for its type.
        # For value = ±unit×km this equals (unit − ref)×km, but is sign-safe for disposals.
        # frac clamped to [0, 1]: the correction only levels DOWN — a cable type that is
        # cheaper than landsbygd normal (ref > unit) is left unchanged, not levelled up.
        frac = np.clip(
            np.where(matched, 1.0 - ref_price / np.where(has_unit, unit, np.nan), 0.0),
            0.0, 1.0,
        )
        ded = np.where(matched, value * frac, 0.0)
        # schablon fallback for types without a landsbygd-normal reference
        per_km = env.map(calib.sek_per_km).fillna(0.0).to_numpy()
        ded = np.where(~matched, np.sign(value) * km * per_km, ded)

    else:
        raise ValueError(f"Unknown method {method!r}; expected one of {C.METHODS}")

    ded = ded * adjustable
    # cap magnitude at |value|, preserving the deduction's sign
    ded = np.sign(ded) * np.minimum(np.abs(ded), np.abs(value))
    return pd.Series(ded, index=components.index)


def apply_environment_adjustment(
    components: pd.DataFrame,
    calib: EnvironmentCalibration,
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
            C.COL_KM: (C.COL_KM, "sum"),
            C.COL_VALUE: (C.COL_VALUE, "sum"),
            C.COL_DEDUCTION: (C.COL_DEDUCTION, "sum"),
            C.COL_ADJ_VALUE: (C.COL_ADJ_VALUE, "sum"),
        })
    )

    # per company
    per_company = (
        comp.groupby(C.COL_REID, as_index=False)
        .agg(**{
            C.COL_KM: (C.COL_KM, "sum"),
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

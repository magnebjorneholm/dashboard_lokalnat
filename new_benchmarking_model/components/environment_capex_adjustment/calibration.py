"""
calibration.py — derive the placement-environment premium from the data.

The reference level is "landsbygd normal" (LB_NORMAL). For every other environment
we measure how much more expensive the SAME cable type is, matched on
(techspec × volt), and summarise it two ways:

    sek_per_km[env] — volume-weighted additive premium [SEK/km]
                      = Σ(km · (unit_price − ref_price)) / Σ(km)   over matched components
    percent[env]    — premium as a share of value
                      = Σ(km · (unit_price − ref_price)) / Σ(value) over matched components

The additive form matches the cost driver (ground works per km are roughly constant
across cable cross-sections); the percent form matches Ei's wording ("schablonavdrag
i procent"). Both are calibrated on the actual installed mix (volume-weighted), so a
single per-environment number reflects this fleet, not an unweighted catalogue.

`ref_price` itself is built per (techspec × volt) as the km-weighted mean unit price
among LB_NORMAL components — i.e. the landsbygd-normal price list, as realised here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

import numpy as np
import pandas as pd

from . import config as C


@dataclass(frozen=True)
class EnvironmentCalibration:
    reference: str
    sek_per_km: Dict[str, float]      # env -> additive premium [SEK/km]
    percent: Dict[str, float]         # env -> premium as share of value [0..1]
    ref_price: pd.DataFrame           # (techspec, volt) -> ref_unit_price [SEK/km]
    coverage: pd.DataFrame            # per-env diagnostics (transparency / reliability)


def build_reference_price(components: pd.DataFrame) -> pd.DataFrame:
    """km-weighted landsbygd-normal unit price per (techspec × volt)."""
    ref = components[components[C.COL_ENV] == C.REFERENCE_ENV]

    def _wprice(g: pd.DataFrame) -> float:
        return float(np.average(g[C.COL_UNIT_PRICE], weights=g[C.COL_KM]))

    price = (
        ref.groupby([C.COL_TECHSPEC, C.COL_VOLT])
        .apply(_wprice, include_groups=False)
        .rename(C.COL_REF_PRICE)
        .reset_index()
    )
    return price


def calibrate(components: pd.DataFrame) -> EnvironmentCalibration:
    """Calibrate per-environment premiums from a prepared components frame."""
    ref_price = build_reference_price(components)

    adjustable = components[components[C.COL_ENV].isin(C.ADJUSTABLE_ENVS)].merge(
        ref_price, on=[C.COL_TECHSPEC, C.COL_VOLT], how="left"
    )
    adjustable[C.COL_PREMIUM_PER_KM] = (
        adjustable[C.COL_UNIT_PRICE] - adjustable[C.COL_REF_PRICE]
    )

    sek_per_km: Dict[str, float] = {}
    percent: Dict[str, float] = {}
    rows = []

    for env in C.ADJUSTABLE_ENVS:
        g = adjustable[adjustable[C.COL_ENV] == env]
        matched = g[g[C.COL_REF_PRICE].notna()]

        km_total = float(g[C.COL_KM].sum())
        km_matched = float(matched[C.COL_KM].sum())
        premium_sek = float((matched[C.COL_KM] * matched[C.COL_PREMIUM_PER_KM]).sum())
        value_matched = float(matched[C.COL_VALUE].sum())

        sek_per_km[env] = premium_sek / km_matched if km_matched > 0 else 0.0
        percent[env] = premium_sek / value_matched if value_matched > 0 else 0.0

        rows.append({
            C.COL_ENV: env,
            "n_components": int(len(g)),
            "n_types_matched": int(matched.groupby([C.COL_TECHSPEC, C.COL_VOLT]).ngroups),
            "km_total": km_total,
            "km_matched_share": km_matched / km_total if km_total > 0 else 0.0,
            "value_total": float(g[C.COL_VALUE].sum()),
            "premium_sek_matched": premium_sek,
            "sek_per_km": sek_per_km[env],
            "percent": percent[env],
        })

    coverage = pd.DataFrame(rows)
    return EnvironmentCalibration(
        reference=C.REFERENCE_ENV,
        sek_per_km=sek_per_km,
        percent=percent,
        ref_price=ref_price,
        coverage=coverage,
    )

"""
calibration.py — derive the placement-environment premium for nätstationer.

For stations the premium is observed directly: it is the booked value of the
"City- och tätortstillägg nätstation" rows (TATORT). There is no per-type reference
lookup as for jordkabel — the reference is simply "the station without the surcharge".

We summarise the premium two ways:

    sek_per_station — value-weighted mean surcharge [SEK/st]
                      = Σ(value_tatort) / Σ(count_tatort)            (≈ 126 861, the list price)
    percent[TATORT] — premium as a share of the TOTAL station base
                      = Σ(value_tatort) / Σ(value_all)

The percent is taken over the *total* station value (surcharge included), so applying
it as a flat haircut to a reported total station capital base removes the premium at
the sector level. It is calibrated on the actual fleet (value-weighted), so it reflects
this set of companies, not an unweighted catalogue.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

import numpy as np
import pandas as pd

from . import config as C


@dataclass(frozen=True)
class StationCalibration:
    reference: str
    percent: Dict[str, float]         # env -> premium as share of TOTAL station value [0..1]
    sek_per_station: float            # value-weighted mean surcharge [SEK/st]
    coverage: pd.DataFrame            # per-env diagnostics (transparency / reliability)


def calibrate(components: pd.DataFrame) -> StationCalibration:
    """Calibrate the tätort station premium from a prepared components frame."""
    total_value = float(components[C.COL_VALUE].sum())

    tat = components[components[C.COL_ENV] == C.TATORT]
    premium_value = float(tat[C.COL_VALUE].sum())
    count_tatort = float(tat[C.COL_COUNT].sum())

    sek_per_station = premium_value / count_tatort if count_tatort > 0 else 0.0
    percent = {
        C.TATORT: premium_value / total_value if total_value > 0 else 0.0
    }

    n_companies = int(components[C.COL_REID].nunique())
    n_companies_with = int(tat[C.COL_REID].nunique())

    coverage = pd.DataFrame([{
        C.COL_ENV: C.TATORT,
        "n_components": int(len(tat)),
        "n_stations": count_tatort,
        "premium_value": premium_value,
        "station_value_total": total_value,
        "percent": percent[C.TATORT],
        "sek_per_station": sek_per_station,
        "companies_with_surcharge": n_companies_with,
        "companies_total": n_companies,
    }])

    return StationCalibration(
        reference=C.REFERENCE_ENV,
        percent=percent,
        sek_per_station=sek_per_station,
        coverage=coverage,
    )

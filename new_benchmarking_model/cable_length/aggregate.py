"""
aggregate.py — sum physical line length [km] per company, with both axes
exposed as parameters.
"""

from __future__ import annotations

from typing import Iterable, Optional

import pandas as pd

from . import config as C


def aggregate_cable_length_per_firm(
    components: pd.DataFrame,
    include_types: Optional[Iterable[str]] = None,
    split_by_voltage: bool = False,
) -> pd.DataFrame:
    """
    Aggregate line length to one km figure per company.

    Parameters
    ----------
    components :
        Output of `load_cable_components` (one row per line component).
    include_types :
        Iterable of ledningstyp codes to include (see C.ALL_TYPES). None means all
        line types. Use C.ELECTRICAL_TYPES to exclude optical fibre (optokabel).
    split_by_voltage :
        If False (default) -> one total km row per company.
        If True            -> one row per (company, voltage_level), so low/high/unknown
                              voltage are reported separately.

    Returns
    -------
    A tidy DataFrame:
        split_by_voltage=False : columns [id_firm, km_total]
        split_by_voltage=True  : columns [id_firm, voltage_level, km_total]
    Every company present in `components` after filtering appears exactly once
    (per voltage_level when split). km_total is the summed physical length [km].
    """
    if include_types is not None:
        include_types = set(include_types)
        unknown = include_types - set(C.ALL_TYPES)
        if unknown:
            raise ValueError(
                f"Unknown ledningstyp(s): {sorted(unknown)}. "
                f"Valid values: {sorted(C.ALL_TYPES)}"
            )
        components = components[components[C.COL_LEDNINGSTYP].isin(include_types)]

    group_cols = [C.COL_ID_FIRM]
    if split_by_voltage:
        group_cols.append(C.COL_VOLTAGE_LEVEL)

    out = (
        components.groupby(group_cols, as_index=False)[C.COL_KM]
        .sum()
        .rename(columns={C.COL_KM: C.COL_KM_TOTAL})
        .sort_values(group_cols)
        .reset_index(drop=True)
    )
    return out

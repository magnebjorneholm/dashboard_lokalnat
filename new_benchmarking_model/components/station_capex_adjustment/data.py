"""
data.py — load nätstation components from capbase_a and normalise to a clean frame.

Verified data model (capbase_a, cat_encode == 13):
    nuav_2022  ==  normvärde × count_comp        (holds to 0.00% median error, 100% of rows)
where
    normvärde   = unit price [SEK/st] from Ei's normvärdeslista for the row's exact
                  station type / surcharge code,
    count_comp  = number of stations [st],
    nuav_2022   = the row's capital-base value [SEK] (NUAV 2022, pre-depreciation).

Unlike jordkabel, the placement-environment premium is NOT a variant of the base price
but a standalone "City- och tätortstillägg nätstation" surcharge row. classify_env
therefore reads techspec (where the surcharge lives), not subcat (which only carries
the functional type: nätstation / tillägg nätstation / kopplingsstation / ...).
"""

from __future__ import annotations

import pandas as pd

from . import config as C


def _resolve(columns, fragment: str) -> str:
    """Return the first column whose name contains `fragment` (handles non-UTF8 names)."""
    for col in columns:
        if fragment in col:
            return col
    raise KeyError(f"No column containing {fragment!r} in {list(columns)}")


def classify_env(techspec) -> str:
    """
    Map a capbase_a station `techspec` to a placement-environment code.

    The only förläggningsmiljö signal for stations is the "City- och tätortstillägg
    nätstation" surcharge (TATORT). Everything else — base stations, kopplingsstation
    and the functional tillägg (linjefack, effektbrytare, inhyst, inomhusbetjänad,
    nedbyggd) — is BASE and is never adjusted.

    Uses an ASCII-only discriminating substring so it is robust to the å/ä/ö
    encoding of the raw values.
    """
    s = str(techspec).lower()
    if C.TATORT_SURCHARGE_FRAG in s:   # "city- och tätortstillägg nätstation"
        return C.TATORT
    return C.BASE


def load_station_components(capbase_path=None) -> pd.DataFrame:
    """
    Load and normalise all nätstation components (cat_encode == 13) from capbase_a.

    Returns one row per component with columns:
        REId, id_network, techspec, volt, env, count, unit_price, value

    Rows with no usable value are dropped (value missing). Unlike jordkabel we keep
    rows regardless of count/unit_price: the itemized method needs only `value`, and
    base rows are part of the denominator even where unit_price is blank.
    """
    path = capbase_path or C.CAPBASE_PATH
    raw = pd.read_parquet(path)

    unit_price_col = _resolve(raw.columns, C.FRAG_UNIT_PRICE)

    station = raw[raw["cat_encode"] == C.STATION_CAT_ENCODE].copy()

    df = pd.DataFrame({
        C.COL_REID: station["id_network_string"].astype(str),
        C.COL_ID_NETWORK: station["id_network"],
        C.COL_TECHSPEC: station[C.COL_TECHSPEC].astype(str).str.strip(),
        C.COL_VOLT: station[C.COL_VOLT].astype(str).str.strip(),
        C.COL_ENV: station[C.COL_TECHSPEC].map(classify_env),
        C.COL_COUNT: pd.to_numeric(station["count_comp"], errors="coerce"),
        C.COL_UNIT_PRICE: pd.to_numeric(station[unit_price_col], errors="coerce"),
        C.COL_VALUE: pd.to_numeric(station["nuav_2022"], errors="coerce"),
    })

    df = df[df[C.COL_VALUE].notna()].reset_index(drop=True)
    return df

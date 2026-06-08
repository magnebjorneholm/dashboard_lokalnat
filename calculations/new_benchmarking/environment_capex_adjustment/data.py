"""
data.py — load jordkabel components from capbase_a and normalise to a clean frame.

Verified data model (capbase_a, cat_encode == 3):
    nuav_2022  ==  normvärde × count_comp        (holds to 0.00% median error, 100% of rows)
where
    normvärde   = unit price [SEK/km] from Ei's normvärdeslista for the component's
                  exact cable type (techspec × volt) AND placement environment,
    count_comp  = physical cable length [km],
    nuav_2022   = the component's capital-base value [SEK] (NUAV 2022, pre-depreciation).

Because the unit price already encodes the placement-environment premium, the
adjustment is a re-pricing problem, not a re-measurement problem.
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


def classify_env(subcat) -> str:
    """
    Map a capbase_a `subcat` string to a placement-environment code.

    Uses ASCII-only discriminating substrings so it is robust to the å/ä/ö
    encoding of the raw values ("jordkabel landsbygd svår" etc.).
    """
    s = str(subcat).lower()
    if "city" in s:
        return C.CITY
    if "landsbygd normal" in s:
        return C.LB_NORMAL
    if "landsbygd sv" in s:        # svår / svar
        return C.LB_SVAR
    if "tort" in s:               # tätort
        return C.TATORT
    return C.OTHER                # sjökabel, optokabel, övriga, plain "jordkabel"


def load_jordkabel_components(capbase_path=None) -> pd.DataFrame:
    """
    Load and normalise all cable components (cat_encode == 3) from capbase_a.

    Returns one row per component with columns:
        REId, id_network, techspec, volt, env, km, unit_price, value

    Rows with no usable length/price (km <= 0 or unit_price missing) are dropped,
    as they cannot be re-priced or premium-weighted.
    """
    path = capbase_path or C.CAPBASE_PATH
    raw = pd.read_parquet(path)

    unit_price_col = _resolve(raw.columns, C.FRAG_UNIT_PRICE)

    cable = raw[raw["cat_encode"] == C.CABLE_CAT_ENCODE].copy()

    df = pd.DataFrame({
        C.COL_REID: cable["id_network_string"].astype(str),
        C.COL_ID_NETWORK: cable["id_network"],
        C.COL_TECHSPEC: cable[C.COL_TECHSPEC].astype(str).str.strip(),
        C.COL_VOLT: cable[C.COL_VOLT].astype(str).str.strip(),
        C.COL_ENV: cable[C.COL_SUBCAT].map(classify_env),
        C.COL_KM: pd.to_numeric(cable["count_comp"], errors="coerce"),
        C.COL_UNIT_PRICE: pd.to_numeric(cable[unit_price_col], errors="coerce"),
        C.COL_VALUE: pd.to_numeric(cable["nuav_2022"], errors="coerce"),
    })

    df = df[(df[C.COL_KM] > 0) & df[C.COL_UNIT_PRICE].notna()].reset_index(drop=True)
    return df

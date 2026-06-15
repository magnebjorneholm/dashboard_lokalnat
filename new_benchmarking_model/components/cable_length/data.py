"""
data.py — load line components from capbase_a and classify them onto the two
parametrisation axes (ledningstyp, voltage_level).

Classification is keyword-based on the raw `subcat` / `volt` strings. capbase_a
stores some values with non-UTF8 bytes (å/ä/ö), so the discriminating substrings
are chosen to be robust to that encoding.
"""

from __future__ import annotations

from typing import Optional

import pandas as pd

from . import config as C


def classify_ledningstyp(subcat) -> Optional[str]:
    """
    Map a capbase_a `subcat` string to a line-type code (axis 1).

    Returns one of C.ALL_TYPES for line components, or None for anything that is
    not a line measured in kilometres. Notably None is returned for:
      * point components (kabelskåp, nätstation, mätare, transformator, alus, …),
      * 'tillägg' rows — capital-base cost supplements whose count_comp is a
        placeholder (often no normvärde, sometimes negative value), not real length.
    """
    s = str(subcat).lower()

    # Exclusions first — these would otherwise be caught by the keyword rules below.
    if "tillägg" in s or "tillagg" in s:
        return None
    if "kabelsk" in s:                       # kabelskåp — a point component
        return None

    if "sjökabel" in s or "sjokabel" in s:
        return C.SJOKABEL
    if "optokabel" in s:
        return C.OPTOKABEL
    if "hängkabel" in s or "hangkabel" in s:
        return C.HSP_HANGKABEL
    if "jordkabel" in s:
        return C.JORDKABEL
    if "luftledning" in s:
        return C.LUFTLEDNING
    if "ledning" in s:                       # "övriga ledningar", "annan ledning"
        return C.OVRIGA
    return None                              # not a line component


def classify_voltage_level(volt) -> str:
    """
    Map a capbase_a `volt` string to a voltage-level code (axis 2).

    Three-way on purpose: ~12 % of line km in capbase_a have no reported volt and
    are a genuine mix of low- and high-voltage lines, so they are surfaced as
    'unknown' rather than silently folded into either bucket.
        ''        -> unknown
        '0,4'     -> lsp   (lågspänning)
        anything  -> hsp   (högspänning; includes ranges/combos like '12', '12-24')
                            that contain a voltage above 0,4 kV
    """
    s = str(volt).strip()
    if s == "" or s.lower() in ("nan", "none", "-"):
        return C.VOLT_UNKNOWN
    if s == "0,4":
        return C.LSP
    return C.HSP


def load_cable_components(capbase_path=None) -> pd.DataFrame:
    """
    Load all line components from capbase_a, classified onto both axes.

    Returns one row per line component with columns:
        REId, subcat, ledningstyp, voltage_level, km

    Non-line rows (classify_ledningstyp -> None) and rows with km <= 0 are dropped,
    so every returned row carries a positive physical length in kilometres.

    Note: the source columns `subcat` and `volt` are referenced by their exact
    names. A substring lookup would be unsafe here — capbase_a also has a
    `subcat_encode` column, of which "subcat" is a prefix.
    """
    path = capbase_path or C.CAPBASE_PATH
    raw = pd.read_parquet(path)

    ledningstyp = raw[C.COL_SUBCAT].map(classify_ledningstyp)
    is_line = ledningstyp.notna()
    src = raw[is_line]

    df = pd.DataFrame({
        C.COL_REID: src[C.COL_SRC_REID].astype(str).values,
        C.COL_SUBCAT: src[C.COL_SUBCAT].astype(str).str.strip().values,
        C.COL_LEDNINGSTYP: ledningstyp[is_line].values,
        C.COL_VOLTAGE_LEVEL: src[C.COL_VOLT].map(classify_voltage_level).values,
        C.COL_KM: pd.to_numeric(src["count_comp"], errors="coerce").values,
    })

    df = df[df[C.COL_KM] > 0].reset_index(drop=True)
    return df

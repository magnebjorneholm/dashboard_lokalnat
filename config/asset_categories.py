"""
frontend/common/asset_categories.py

Asset categories according to Ei methodology (User Manual Tables 1 & 4).
Used for parameterization of norm values and asset lifetimes.

Parameter-IDs are sourced from config.glossary (single source of truth).
"""

from typing import Dict, List, NamedTuple

from config.glossary import (
    ASSET_CATEGORY_NAMES,
    scaling_param_id,
    lifetime_ordinary_param_id,
    lifetime_tail_param_id,
    PID_GENERAL_SCALING,
)


# Short display names for charts/compact displays (not in glossary)
_SHORT_NAMES: Dict[int, str] = {
    1: "Markarbeten, LK",
    2: "Annan ledning, LK",
    3: "Annan ledning, OK",
    4: "Luftledning (annan), LK",
    5: "It-system",
    6: "Kabelskåp",
    7: "Kabel 220kV+, LK",
    8: "Luftledning 220kV+, LK",
    9: "Luftledning, OK",
    10: "Markarbeten 220kV+, LK",
    11: "Markarbeten, OK",
    12: "Mätare",
    13: "Nätstation",
    14: "Shuntreaktor",
    15: "Styr/kontroll",
    16: "Ställverk",
    17: "Transformator",
}

# Baseline lifetimes: (ekdep, maxdep) per category
_LIFETIMES: Dict[int, tuple] = {
    1: (100, 124), 2: (100, 124), 3: (100, 124), 4: (100, 124),
    5: (20, 24),   6: (60, 74),   7: (80, 100),  8: (120, 150),
    9: (80, 100),  10: (80, 100), 11: (100, 124), 12: (20, 24),
    13: (80, 100), 14: (80, 100), 15: (30, 36),  16: (80, 100),
    17: (100, 124),
}


class AssetCategory(NamedTuple):
    """Asset category with baseline values and Parameter-IDs."""
    cat_encode: int
    name: str                       # Full Swedish name (per User Manual)
    short_name: str                 # Abbreviated name for charts/compact displays
    ekdep: int                      # Ordinary lifetime (years)
    maxdep: int                     # Maximum lifetime (years) = ekdep + tail
    param_id_ekdep: str             # Parameter-ID for ordinary lifetime (2.X.1)
    param_id_maxdep: str            # Parameter-ID for tail lifetime (2.X.2)
    scaling_param_id: str           # Parameter-ID for scaling factor (1.2.X)


# All 17 categories -- IDs sourced from config.glossary
ASSET_CATEGORIES: List[AssetCategory] = [
    AssetCategory(
        ce,
        ASSET_CATEGORY_NAMES[ce],
        _SHORT_NAMES[ce],
        _LIFETIMES[ce][0],
        _LIFETIMES[ce][1],
        lifetime_ordinary_param_id(ce),
        lifetime_tail_param_id(ce),
        scaling_param_id(ce),
    )
    for ce in range(1, 18)
]

# Lookup by cat_encode
CATEGORY_BY_CODE: Dict[int, AssetCategory] = {
    cat.cat_encode: cat for cat in ASSET_CATEGORIES
}

# Baseline lifetimes {cat_encode: {'ekdep': val, 'maxdep': val}}
BASELINE_LIFETIMES: Dict[int, Dict[str, int]] = {
    cat.cat_encode: {'ekdep': cat.ekdep, 'maxdep': cat.maxdep}
    for cat in ASSET_CATEGORIES
}

# Baseline scaling factors (all 1.00 per User Manual Table 1)
BASELINE_SCALING_FACTORS: Dict[int, float] = {
    cat.cat_encode: 1.00 for cat in ASSET_CATEGORIES
}

# General scaling factor -- ID from glossary, baseline value here
GENERAL_SCALING_FACTOR_PARAM_ID = PID_GENERAL_SCALING
GENERAL_SCALING_FACTOR_BASELINE = 1.00


def get_category_name(cat_encode: int) -> str:
    """Get full category name from cat_encode."""
    if cat_encode in CATEGORY_BY_CODE:
        return CATEGORY_BY_CODE[cat_encode].name
    return f"Unknown category ({cat_encode})"


def get_category_short_name(cat_encode: int) -> str:
    """Get abbreviated category name from cat_encode (for charts)."""
    if cat_encode in CATEGORY_BY_CODE:
        return CATEGORY_BY_CODE[cat_encode].short_name
    return f"Cat {cat_encode}"


def get_baseline_lifetime(cat_encode: int) -> Dict[str, int]:
    """Get baseline lifetimes for a category."""
    return BASELINE_LIFETIMES.get(cat_encode, {'ekdep': 0, 'maxdep': 0})


def get_lifetime_param_ids(cat_encode: int) -> Dict[str, str]:
    """
    Get Parameter-IDs for a category's lifetimes.
    
    Returns:
        Dict with 'ekdep' and 'maxdep' Parameter-IDs
    """
    if cat_encode in CATEGORY_BY_CODE:
        cat = CATEGORY_BY_CODE[cat_encode]
        return {
            'ekdep': cat.param_id_ekdep,
            'maxdep': cat.param_id_maxdep
        }
    return {'ekdep': '', 'maxdep': ''}


def get_scaling_param_id(cat_encode: int) -> str:
    """Get Parameter-ID for a category's scaling factor."""
    if cat_encode in CATEGORY_BY_CODE:
        return CATEGORY_BY_CODE[cat_encode].scaling_param_id
    return ""
"""
frontend/common/asset_categories.py

Asset categories according to Ei methodology (User Manual Tables 1 & 4).
Used for parameterization of norm values and asset lifetimes.

Parameter-ID structure:
- Module 1 (1.2.X): Scaling factors
- Module 2 (2.X.1): Ordinary lifetime (ekdep)
- Module 2 (2.X.2): Tail lifetime
"""

from typing import Dict, List, NamedTuple


class AssetCategory(NamedTuple):
    """Asset category with baseline values and Parameter-IDs."""
    cat_encode: int
    name: str                       # Swedish name (per User Manual)
    ekdep: int                      # Ordinary lifetime (years)
    maxdep: int                     # Maximum lifetime (years) = ekdep + tail
    param_id_ekdep: str             # Parameter-ID for ordinary lifetime (2.X.1)
    param_id_maxdep: str            # Parameter-ID for tail lifetime (2.X.2)
    scaling_param_id: str           # Parameter-ID for scaling factor (1.2.X)


# All 17 categories per User Manual Tables 1 & 4
ASSET_CATEGORIES: List[AssetCategory] = [
    AssetCategory(
        1,
        "Andra markarbeten och byggnader, linjekoncession",
        100, 124, "2.1.1", "2.1.2", "1.2.1"
    ),
    AssetCategory(
        2,
        "Annan ledning, linjekoncession",
        100, 124, "2.2.1", "2.2.2", "1.2.2"
    ),
    AssetCategory(
        3,
        "Annan ledning, områdeskoncession",
        100, 124, "2.3.1", "2.3.2", "1.2.3"
    ),
    AssetCategory(
        4,
        "Annan luftledning, linjekoncession",
        100, 124, "2.4.1", "2.4.2", "1.2.4"
    ),
    AssetCategory(
        5,
        "It-system",
        20, 24, "2.5.1", "2.5.2", "1.2.5"
    ),
    AssetCategory(
        6,
        "Kabelskåp",
        60, 74, "2.6.1", "2.6.2", "1.2.6"
    ),
    AssetCategory(
        7,
        "Ledning med en spänning om 220 kV eller mer, med undantag för luftledning, linjekoncession",
        80, 100, "2.7.1", "2.7.2", "1.2.7"
    ),
    AssetCategory(
        8,
        "Luftledning med en spänning om 220 kV eller mer, linjekoncession",
        120, 150, "2.8.1", "2.8.2", "1.2.8"
    ),
    AssetCategory(
        9,
        "Luftledning, områdeskoncession",
        80, 100, "2.9.1", "2.9.2", "1.2.9"
    ),
    AssetCategory(
        10,
        "Markarbeten och byggnader med anknytning till ett ledningsnät med en spänning om 220 kV eller mer, linjekoncession",
        80, 100, "2.10.1", "2.10.2", "1.2.10"
    ),
    AssetCategory(
        11,
        "Markarbeten och byggnader, områdeskoncession",
        100, 124, "2.11.1", "2.11.2", "1.2.11"
    ),
    AssetCategory(
        12,
        "Mätare",
        20, 24, "2.12.1", "2.12.2", "1.2.12"
    ),
    AssetCategory(
        13,
        "Nätstation",
        80, 100, "2.13.1", "2.13.2", "1.2.13"
    ),
    AssetCategory(
        14,
        "Shuntreaktor",
        80, 100, "2.14.1", "2.14.2", "1.2.14"
    ),
    AssetCategory(
        15,
        "Styr- och kontrollutrustning",
        30, 36, "2.15.1", "2.15.2", "1.2.15"
    ),
    AssetCategory(
        16,
        "Ställverk utan sekundärapparater",
        80, 100, "2.16.1", "2.16.2", "1.2.16"
    ),
    AssetCategory(
        17,
        "Transformator",
        100, 124, "2.17.1", "2.17.2", "1.2.17"
    ),
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

# General scaling factor (Parameter-ID 1.1.1)
GENERAL_SCALING_FACTOR_PARAM_ID = "1.1.1"
GENERAL_SCALING_FACTOR_BASELINE = 1.00


def get_category_name(cat_encode: int) -> str:
    """Get category name from cat_encode."""
    if cat_encode in CATEGORY_BY_CODE:
        return CATEGORY_BY_CODE[cat_encode].name
    return f"Unknown category ({cat_encode})"


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
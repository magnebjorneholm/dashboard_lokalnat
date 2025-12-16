"""
frontend/common/asset_categories.py

Tillgångskategorier enligt Ei's metodbeskrivning (User Manual Tabell 1).
Används för parametrisering av normvärden och livslängder.
"""

from typing import Dict, List, NamedTuple


class AssetCategory(NamedTuple):
    """En tillgångskategori med baseline-värden."""
    cat_encode: int
    name: str
    ekdep: int  # Ekonomisk livslängd (år)
    maxdep: int  # Maximal livslängd (år)
    param_id_ekdep: str  # Parameter-ID för ekonomisk livslängd
    param_id_maxdep: str  # Parameter-ID för maximal livslängd


# Alla 17 kategorier enligt User Manual Tabell 1
ASSET_CATEGORIES: List[AssetCategory] = [
    AssetCategory(1, "Andra markarbeten och byggnader, linjekoncession", 100, 124, "1.1.1", "1.1.2"),
    AssetCategory(2, "Annan ledning, linjekoncession", 100, 124, "1.2.1", "1.2.2"),
    AssetCategory(3, "Annan ledning, områdeskoncession", 100, 124, "1.3.1", "1.3.2"),
    AssetCategory(4, "Annan luftledning, linjekoncession", 100, 124, "1.4.1", "1.4.2"),
    AssetCategory(5, "It-system", 20, 24, "1.5.1", "1.5.2"),
    AssetCategory(6, "Kabelskåp", 60, 74, "1.6.1", "1.6.2"),
    AssetCategory(7, "Ledning ≥220 kV (ej luft), linjekoncession", 80, 100, "1.7.1", "1.7.2"),
    AssetCategory(8, "Luftledning ≥220 kV, linjekoncession", 120, 150, "1.8.1", "1.8.2"),
    AssetCategory(9, "Luftledning, områdeskoncession", 80, 100, "1.9.1", "1.9.2"),
    AssetCategory(10, "Markarbeten och byggnader ≥220 kV, linjekoncession", 80, 100, "1.10.1", "1.10.2"),
    AssetCategory(11, "Markarbeten och byggnader, områdeskoncession", 100, 124, "1.11.1", "1.11.2"),
    AssetCategory(12, "Mätare", 20, 24, "1.12.1", "1.12.2"),
    AssetCategory(13, "Nätstation", 80, 100, "1.13.1", "1.13.2"),
    AssetCategory(14, "Shuntreaktor", 80, 100, "1.14.1", "1.14.2"),
    AssetCategory(15, "Styr- och kontrollutrustning", 30, 36, "1.15.1", "1.15.2"),
    AssetCategory(16, "Ställverk utan sekundärapparater", 80, 100, "1.16.1", "1.16.2"),
    AssetCategory(17, "Transformator", 100, 124, "1.17.1", "1.17.2"),
]

# Lookup by cat_encode
CATEGORY_BY_CODE: Dict[int, AssetCategory] = {cat.cat_encode: cat for cat in ASSET_CATEGORIES}

# Baseline livslängder {cat_encode: {'ekdep': val, 'maxdep': val}}
BASELINE_LIFETIMES: Dict[int, Dict[str, int]] = {
    cat.cat_encode: {'ekdep': cat.ekdep, 'maxdep': cat.maxdep}
    for cat in ASSET_CATEGORIES
}


def get_category_name(cat_encode: int) -> str:
    """Hämta kategorinamn från cat_encode."""
    if cat_encode in CATEGORY_BY_CODE:
        return CATEGORY_BY_CODE[cat_encode].name
    return f"Okänd kategori ({cat_encode})"


def get_baseline_lifetime(cat_encode: int) -> Dict[str, int]:
    """Hämta baseline-livslängder för en kategori."""
    return BASELINE_LIFETIMES.get(cat_encode, {'ekdep': 0, 'maxdep': 0})
"""
config.py — constants for the förläggningsmiljö (placement environment) capex adjustment.

All identifiers and output column names are English. Swedish only appears where it
matches raw data values (subcat strings in capbase_a) or regulatory terms.
"""

from pathlib import Path

# ── Paths ───────────────────────────────────────────────────────────────────
# repo root = four levels up from this file:
#   .../dashboard_lokalnat/calculations/new_benchmarking/environment_capex_adjustment/config.py
REPO_ROOT = Path(__file__).resolve().parents[3]
CAPBASE_PATH = REPO_ROOT / "data" / "rab_and_capex" / "capbase_a.parquet"

# ── Category ────────────────────────────────────────────────────────────────
# cat_encode == 3 is "annan ledning / kabel" in capbase_a; all jordkabel lives here.
CABLE_CAT_ENCODE = 3

# ── Förläggningsmiljö (placement environment) codes ─────────────────────────
CITY = "city"
TATORT = "tatort"
LB_NORMAL = "lb_normal"   # reference level (Ei baseline: "landsbygd normal")
LB_SVAR = "lb_svar"
OTHER = "other"           # sjökabel / optokabel / övriga / jordkabel without env label

REFERENCE_ENV = LB_NORMAL

# Environments that carry a defined premium and are therefore adjustable.
ADJUSTABLE_ENVS = (CITY, TATORT, LB_SVAR)

# ── Adjustment methods ──────────────────────────────────────────────────────
METHOD_PER_TYPE = "per_type"        # exact re-pricing per cable type (most precise)
METHOD_SEK_PER_KM = "sek_per_km"    # one additive SEK/km premium per environment
METHOD_PERCENT = "percent"          # one percent-of-value deduction per environment
METHODS = (METHOD_PER_TYPE, METHOD_SEK_PER_KM, METHOD_PERCENT)

# ── Source column fragments in capbase_a (resolved by substring) ─────────────
# capbase_a stores some column names with non-UTF8 bytes (e.g. "normvärde"),
# so we resolve them by a safe ASCII substring instead of an exact match.
FRAG_UNIT_PRICE = "normv"          # normvärde  = unit price [SEK/km] for type × env
FRAG_ACQUISITION = "anskaff"       # anskaffningsvärde (sparse; kept for reference only)

# ── Working / output column names (English) ─────────────────────────────────
COL_REID = "REId"
COL_ID_NETWORK = "id_network"
COL_TECHSPEC = "techspec"
COL_VOLT = "volt"
COL_SUBCAT = "subcat"
COL_ENV = "env"                     # mapped placement environment
COL_KM = "km"                       # count_comp, physical cable length [km]
COL_UNIT_PRICE = "unit_price"       # normvärde [SEK/km] for this component's type × env
COL_VALUE = "value"                 # nuav_2022 = unit_price × km [SEK]

COL_REF_PRICE = "ref_unit_price"    # landsbygd-normal unit price for the same type [SEK/km]
COL_PREMIUM_PER_KM = "premium_per_km"   # unit_price − ref_unit_price [SEK/km]
COL_DEDUCTION = "deduction"         # amount removed from value [SEK]
COL_ADJ_VALUE = "adjusted_value"    # value − deduction [SEK]
COL_EFFECTIVE_PCT = "effective_pct"  # deduction / value, per company
COL_REDUCTION_FACTOR = "reduction_factor"  # adjusted_value / value

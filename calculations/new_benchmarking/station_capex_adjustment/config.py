"""
config.py — constants for the förläggningsmiljö (placement environment) capex
adjustment for NÄTSTATIONER.

Parallel to environment_capex_adjustment (jordkabel), but the data model differs:

  Jordkabel:  the environment premium is *embedded* in each component's per-km price
              (the same cable type has four prices, one per environment). The reference
              is "landsbygd normal" and the correction is a per-type re-pricing.

  Nätstation: the base station price is the SAME regardless of environment. The
              environment premium is instead booked as a SEPARATE, itemised line —
              "City- och tätortstillägg nätstation" (126 861 SEK/st, for stations
              inside SCB's tätort boundary). The reference is therefore "outside
              tätort" (no surcharge) and the correction is an exact removal of the
              surcharge rows. No per-type reference lookup is needed.

All identifiers and output column names are English. Swedish only appears where it
matches raw data values (techspec strings in capbase_a) or regulatory terms.
"""

from pathlib import Path

# ── Paths ───────────────────────────────────────────────────────────────────
# repo root = four levels up from this file:
#   .../dashboard_lokalnat/calculations/new_benchmarking/station_capex_adjustment/config.py
REPO_ROOT = Path(__file__).resolve().parents[3]
CAPBASE_PATH = REPO_ROOT / "data" / "rab_and_capex" / "capbase_a.parquet"

# ── Category ────────────────────────────────────────────────────────────────
# cat_encode == 13 is "nätstation" in capbase_a (incl. kopplingsstation, övriga
# stationer and all "tillägg nätstation" surcharge rows).
STATION_CAT_ENCODE = 13

# ASCII-safe substring that uniquely identifies the placement-environment surcharge
# row inside techspec ("City- och tätortstillägg nätstation"). It is the ONLY
# förläggningsmiljö tillägg; the other tillägg (linjefack, effektbrytare, inhyst,
# inomhusbetjänad, nedbyggd) are functional and must NOT be treated as environment.
TATORT_SURCHARGE_FRAG = "city- och"

# ── Förläggningsmiljö (placement environment) codes ─────────────────────────
TATORT = "tatort"   # the City-/tätort surcharge row (adjustable premium)
BASE = "base"       # base stations + all non-environment rows (reference, untouched)

REFERENCE_ENV = BASE
ADJUSTABLE_ENVS = (TATORT,)

# ── Adjustment methods ──────────────────────────────────────────────────────
METHOD_EXACT = "exact"                        # exact: remove the tätort surcharge rows in full (precise)
METHOD_SCHABLON_PERCENT = "schablon_percent"  # schablon: flat % haircut on the whole station base (Ei-style)
METHODS = (METHOD_EXACT, METHOD_SCHABLON_PERCENT)

# ── Source column fragments in capbase_a (resolved by substring) ─────────────
# capbase_a stores some column names with non-UTF8 bytes (e.g. "normvärde"),
# so we resolve them by a safe ASCII substring instead of an exact match.
FRAG_UNIT_PRICE = "normv"          # normvärde = unit price [SEK/st] for this row
FRAG_ACQUISITION = "anskaff"       # anskaffningsvärde (sparse; kept for reference only)

# ── Working / output column names (English) ─────────────────────────────────
COL_REID = "REId"
COL_ID_NETWORK = "id_network"
COL_TECHSPEC = "techspec"
COL_VOLT = "volt"
COL_SUBCAT = "subcat"
COL_ENV = "env"                     # mapped placement environment (tatort / base)
COL_COUNT = "count"                 # count_comp, number of stations [st]
COL_UNIT_PRICE = "unit_price"       # normvärde [SEK/st] for this row
COL_VALUE = "value"                 # nuav_2022 = unit_price × count [SEK]

COL_DEDUCTION = "deduction"         # amount removed from value [SEK]
COL_ADJ_VALUE = "adjusted_value"    # value − deduction [SEK]
COL_EFFECTIVE_PCT = "effective_pct"  # deduction / value, per company
COL_REDUCTION_FACTOR = "reduction_factor"  # adjusted_value / value

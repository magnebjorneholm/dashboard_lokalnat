"""
config.py — constants for the cable-length (ledningslängd) benchmarking input.

Computes physical line length [km] per company from capbase_a, with two
parametrisable axes:
    1. ledningstyp      — which line types to include (jordkabel, luftledning, …)
    2. voltage_level    — optional split into low / high voltage

All identifiers and output column names are English. Swedish only appears where it
matches raw data values (subcat strings in capbase_a) or established domain terms.

Data model (capbase_a):
    count_comp = physical line length [km] for line components
                 (= "antal kilometer" per Ei's reporting handbook, max 3 decimals).
                 For point components (mätare, nätstation, …) count_comp is a *count*,
                 which is why this module filters strictly to line types.
"""

from pathlib import Path

from config.data_paths import dataset_path

from config.column_names import COL_REID

# ── Paths ───────────────────────────────────────────────────────────────────
# repo root = four levels up from this file:
#   .../dashboard_lokalnat/new_benchmarking_model/components/cable_length/config.py
REPO_ROOT = Path(__file__).resolve().parents[3]
CAPBASE_PATH = dataset_path("capbase_a")

# ── Ledningstyp codes (axis 1) ──────────────────────────────────────────────
# ASCII codes, kept stable for use as parameter values / dict keys.
JORDKABEL = "jordkabel"
LUFTLEDNING = "luftledning"
HSP_HANGKABEL = "hsp_hangkabel"
SJOKABEL = "sjokabel"
OPTOKABEL = "optokabel"
OVRIGA = "ovriga"            # "Övriga ledningar", "annan ledning" without a finer type

# All line types present in capbase_a.
ALL_TYPES = (JORDKABEL, LUFTLEDNING, HSP_HANGKABEL, SJOKABEL, OPTOKABEL, OVRIGA)

# Electrical distribution lines — the sensible default for benchmarking.
# Excludes optokabel (optical fibre, not part of the electrical grid).
ELECTRICAL_TYPES = (JORDKABEL, LUFTLEDNING, HSP_HANGKABEL, SJOKABEL, OVRIGA)

# Human-readable labels (for any downstream UI; module logic never depends on these).
TYPE_LABELS = {
    JORDKABEL: "Jordkabel",
    LUFTLEDNING: "Luftledning",
    HSP_HANGKABEL: "HSP-hängkabel",
    SJOKABEL: "Sjökabel",
    OPTOKABEL: "Optokabel",
    OVRIGA: "Övriga ledningar",
}

# ── Voltage-level codes (axis 2) ────────────────────────────────────────────
LSP = "lsp"            # lågspänning, 0,4 kV
HSP = "hsp"            # högspänning, > 0,4 kV
VOLT_UNKNOWN = "unknown"   # volt not reported on the row (≈12 % of line km in capbase_a)

VOLTAGE_LEVELS = (LSP, HSP, VOLT_UNKNOWN)

# ── Source column names (capbase_a, raw) ─────────────────────────────────────
# `id_network_string` already carries the canonical REId ("REL#####"), so the
# module keys on REId from load onwards — no name/code remap downstream.
COL_SRC_REID = "id_network_string"

# ── Working / output column names (English) ─────────────────────────────────
# COL_REID ("REId") is imported from config.column_names — the canonical company
# key used across the app, so cable-length outputs join straight onto everything else.
COL_SUBCAT = "subcat"
COL_VOLT = "volt"
COL_LEDNINGSTYP = "ledningstyp"     # mapped line type (axis 1)
COL_VOLTAGE_LEVEL = "voltage_level"  # mapped voltage level (axis 2)
COL_KM = "km"                       # count_comp, physical line length [km]
COL_KM_TOTAL = "km_total"           # aggregated length per company [km]

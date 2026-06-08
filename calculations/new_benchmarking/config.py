"""
config.py — parameters for the new benchmarking model add-on.

`NewBenchmarkingConfig` is a plain dataclass with defaults that reproduce the
reference reading of Ei's proposal. Every user-facing choice flows through this
object; nothing else in the package reads ad-hoc settings.

All cost figures the model works with are annual and in tkr, mirroring the current
TOTEX definition (controllable_cost_average + capital_cost_2024) so the new model and
the current model can be compared on the same footing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

from calculations.efficiency.efficiency_requirement import DEFAULT_EFF_REQ_PARAMS
from calculations.new_benchmarking.cable_length import config as cable_C
from calculations.new_benchmarking.environment_capex_adjustment import config as env_C
from calculations.new_benchmarking.station_capex_adjustment import config as station_C

# Non-controllable categories (kent_category in non_controllable_a.parquet).
# Network losses are handled separately (valued at a common price), and
# regulatory fees are excluded from TOTEX per the proposal — so neither appears here.
NONCTRL_GRID_SUBSCRIPTION = "grid_subscription"
NONCTRL_GRID_CONNECTION = "grid_connection"
NONCTRL_FEED_IN = "feed_in_compensation"
NONCTRL_CAPACITY_RESERVE = "capacity_reserve"
NONCTRL_REGULATORY_FEES = "regulatory_fees"          # always excluded from TOTEX
NONCTRL_LOSS_PURCHASED = "network_loss_purchased"    # replaced by common-price valuation
NONCTRL_LOSS_OWN = "network_loss_own_production"      # replaced by common-price valuation

DEFAULT_NONCTRL_CATEGORIES: Tuple[str, ...] = (
    NONCTRL_GRID_SUBSCRIPTION,
    NONCTRL_GRID_CONNECTION,
    NONCTRL_FEED_IN,
    NONCTRL_CAPACITY_RESERVE,
)

# New-model base outputs (before optionally appending cable length).
# MWhh (gränspunkt) is deliberately omitted for now — it is deferred together with the
# "kostnad till övergripande nät" work, per the project owner.
NEW_MODEL_BASE_OUTPUTS: Tuple[str, ...] = ("CU", "MW", "NS", "MWhl")


@dataclass
class NewBenchmarkingConfig:
    """All choices for one new-benchmarking run. Defaults = reference reading."""

    # ── Network-loss valuation (gemensamt pris) ──────────────────────────────
    # nf_obs · k_nf · e_in. k_nf is a per-year price (kr/MWh); None → baseline K_NF.
    k_nf: Optional[Dict[int, float]] = None

    # ── TOTEX composition (på/av per delpost) ────────────────────────────────
    include_controllable: bool = True       # controllable_cost_average (påverkbara)
    include_losses: bool = True             # network losses @ common price
    include_capex: bool = True              # förläggningsmiljö-adjusted capital cost
    # which non-controllable categories enter TOTEX (regulatory_fees never included)
    non_controllable_categories: Tuple[str, ...] = DEFAULT_NONCTRL_CATEGORIES

    # ── Förläggningsmiljö capex correction ───────────────────────────────────
    cable_method: str = env_C.METHOD_PER_TYPE          # per_type | sek_per_km | percent
    cable_override_percent: Optional[dict] = None
    station_method: str = station_C.METHOD_ITEMIZED    # itemized | percent
    station_override_percent: Optional[dict] = None

    # ── DEA outputs: cable length (ledningslängd) ────────────────────────────
    include_cable_length: bool = True
    cable_types: Tuple[str, ...] = cable_C.ELECTRICAL_TYPES
    split_by_voltage: bool = False          # True → one length output per voltage level

    # ── DEA specification ────────────────────────────────────────────────────
    rts: str = "crs"                        # 'crs' | 'vrs'
    new_base_outputs: Tuple[str, ...] = NEW_MODEL_BASE_OUTPUTS

    # ── Efficiency-requirement parameters (Ei's method) ──────────────────────
    eff_req_params: Dict = field(default_factory=lambda: dict(DEFAULT_EFF_REQ_PARAMS))

    def resolved_k_nf(self) -> Dict[int, float]:
        """Per-year common price for network losses, falling back to baseline K_NF."""
        if self.k_nf is not None:
            return self.k_nf
        from config.incentive_parameters import K_NF
        return dict(K_NF)

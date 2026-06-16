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

from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from new_benchmarking_model.components.cable_length import config as cable_C
from new_benchmarking_model.components.environment_capex_adjustment import config as env_C
from new_benchmarking_model.components.station_capex_adjustment import config as station_C

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

# Companies Ei deems unsuitable for DEA (excluded from its current-model benchmarking:
# flagged is_outlier with no published efficiency). We honour that in the new model —
# they are removed from the frontier/E75 reference set so they cannot distort other
# firms' scores, and are themselves left unscored (NaN efficiency), mirroring Ei.
EI_DEA_EXCLUDED_REIDS: Tuple[str, ...] = ("REL00024", "REL00257", "REL00965")

# New-model base outputs (before optionally appending cable length).
# MWhh is plain delivered energy at high voltage. Only the *adjustment* of MWhh to include
# levererad energi i gränspunkt is deferred (together with the "kostnad till övergripande
# nät" work, per the project owner) — plain MWhh is part of the main model.
NEW_MODEL_BASE_OUTPUTS: Tuple[str, ...] = ("CU", "MW", "NS", "MWhl", "MWhh")


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
    cable_method: str = env_C.METHOD_EXACT             # exact | schablon_per_km | schablon_percent
    cable_override_percent: Optional[dict] = None
    station_method: str = station_C.METHOD_EXACT       # exact | schablon_percent
    station_override_percent: Optional[dict] = None

    # ── DEA outputs: cable length (ledningslängd) ────────────────────────────
    include_cable_length: bool = True
    cable_types: Tuple[str, ...] = cable_C.ELECTRICAL_TYPES
    split_by_voltage: bool = False          # True → one length output per voltage level

    # ── DEA specification ────────────────────────────────────────────────────
    rts: str = "crs"                        # 'crs' | 'vrs'
    new_base_outputs: Tuple[str, ...] = NEW_MODEL_BASE_OUTPUTS
    # REIds forced out of the DEA reference set (see EI_DEA_EXCLUDED_REIDS).
    exclude_reids: Tuple[str, ...] = EI_DEA_EXCLUDED_REIDS

    # ── Efficiency-requirement: two-sided third-quartile mechanic ────────────
    # The new model's requirement is a signed gap to the third quartile (E75), not the
    # legacy gap to the frontier. See efficiency_requirement_two_sided.py for the full
    # spec. s = sharing × supervision_period/realization_time = 0.50 × 4/8 = 0.25.
    reference_percentile: float = 75.0      # third quartile: threshold + reference value
    gap_cap: float = 0.30                    # symmetric cap on the signed gap (= legacy max)
    sharing: float = 0.50                    # customer sharing
    realization_time: int = 8                # years to realise the full gap
    supervision_period: int = 4              # years in the supervision period

    def resolved_k_nf(self) -> Dict[int, float]:
        """Per-year common price for network losses, falling back to baseline K_NF."""
        if self.k_nf is not None:
            return self.k_nf
        from config.incentive_parameters import K_NF
        return dict(K_NF)

    def signature(self) -> tuple:
        """Stable, hashable identity of this configuration.

        Two configs with the same signature produce the same NewBenchmarkingResult, so
        it is used both as the @st.cache_data key (pages/5_new_benchmarking.py) and as
        the validity token for the pre-computed main-spec bundle
        (new_benchmarking_model/data/loader.py). repr(signature()) is the on-disk form.
        """
        def _od(d):  # ordered, hashable view of an optional dict
            return tuple(sorted(d.items())) if d else None
        return (
            _od(self.resolved_k_nf()),
            self.include_controllable, self.include_losses, self.include_capex,
            tuple(self.non_controllable_categories),
            self.cable_method, _od(self.cable_override_percent),
            self.station_method, _od(self.station_override_percent),
            self.include_cable_length, tuple(self.cable_types), self.split_by_voltage,
            self.rts, tuple(self.new_base_outputs), tuple(self.exclude_reids),
            self.reference_percentile, self.gap_cap, self.sharing,
            self.realization_time, self.supervision_period,
        )

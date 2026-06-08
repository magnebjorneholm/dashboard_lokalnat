"""
cable_length — physical line length (ledningslängd) per company from capbase_a,
for use as a benchmarking variable in the new regulatory model.

Two parametrisable axes:
    1. ledningstyp   — which line types to include (jordkabel, luftledning, sjökabel,
                       hsp-hängkabel, optokabel, övriga ledningar)
    2. voltage_level — optional low/high/unknown voltage split

Typical use:

    from new_benchmarking_model.cable_length import (
        load_cable_components, aggregate_cable_length_per_firm, C,
    )

    comp = load_cable_components()

    # one total km per company (all electrical line types, fibre excluded)
    km = aggregate_cable_length_per_firm(comp, include_types=C.ELECTRICAL_TYPES)

    # broken down by voltage level
    km_v = aggregate_cable_length_per_firm(
        comp, include_types=C.ELECTRICAL_TYPES, split_by_voltage=True
    )
"""

from __future__ import annotations

from . import config as C
from .data import (
    load_cable_components,
    classify_ledningstyp,
    classify_voltage_level,
)
from .aggregate import aggregate_cable_length_per_firm

__all__ = [
    "load_cable_components",
    "classify_ledningstyp",
    "classify_voltage_level",
    "aggregate_cable_length_per_firm",
    "C",
]

"""
Baseline Producers - Ladda baseline data

Producerar baseline-värden från:
- Data_modeller.xlsx (WACC, CAPEX, OPEX, Volumes)
- EIs_DEA.xlsx (Efficiency)
"""

from .baseline_loaders import (
    produce_wacc_from_baseline,
    produce_capex_from_baseline,
    produce_opex_paverkbara_from_baseline,
    produce_opex_opaverkbara_from_baseline,
    produce_volumes_from_baseline
)

from .reference_dea_loader import produce_efficiency_from_baseline

__all__ = [
    'produce_wacc_from_baseline',
    'produce_capex_from_baseline',
    'produce_opex_paverkbara_from_baseline',
    'produce_opex_opaverkbara_from_baseline',
    'produce_volumes_from_baseline',
    'produce_efficiency_from_baseline'
]
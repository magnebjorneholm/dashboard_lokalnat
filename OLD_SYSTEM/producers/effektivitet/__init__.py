"""
efficiency - Efficiency producers
==================================

Exporterar efficiency-producers (DEA, framtida: SFA, StoNED).
"""

from .dea_producer import (
    produce_efficiency_from_dea,
    run_dea_analysis
)

__all__ = [
    'produce_efficiency_from_dea',
    'run_dea_analysis',
]
"""
calculations.new_benchmarking — isolated add-on for Ei's proposed new benchmarking model.

Builds a parameterised TOTEX per company (single DEA input) from raw grunddata and
compares the resulting efficiency / efficiency requirement against the current model.
See ARCHITECTURE.md and docs/ei_to_markdown/outputs/ny-modell-benchmarking-elnatsreglering.md.

Sub-packages (consolidated here from the former top-level new_benchmarking_model/):
    cable_length                — physical line length [km] per company (new DEA output)
    environment_capex_adjustment — jordkabel förläggningsmiljö capex correction
    station_capex_adjustment     — nätstation förläggningsmiljö capex correction

Public API:
    from calculations.new_benchmarking import run_new_benchmarking, NewBenchmarkingConfig
"""

from calculations.new_benchmarking.config import NewBenchmarkingConfig
from calculations.new_benchmarking.model import (
    run_new_benchmarking,
    NewBenchmarkingResult,
)

__all__ = [
    "run_new_benchmarking",
    "NewBenchmarkingResult",
    "NewBenchmarkingConfig",
]

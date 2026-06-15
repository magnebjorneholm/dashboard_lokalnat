"""
new_benchmarking_model — isolated add-on for Ei's proposed new benchmarking model.

Self-contained vertical feature module. Builds a parameterised TOTEX per company (single
DEA input) from raw grunddata and compares the resulting efficiency / efficiency
requirement against the current model. See docs/dependency_graph.md for the full chain and
ARCHITECTURE.md section 20.

Layout:
    config.py, model.py    — public entry point (run_new_benchmarking) and config
    totex/                 — TOTEX build (totex, opex_components, capex_environment)
    efficiency/            — two-sided requirement + kr cost impact
    components/            — parametrised DEA-input builders:
        cable_length                 — physical line length [km] per company (DEA output)
        environment_capex_adjustment — jordkabel förläggningsmiljö capex correction
        station_capex_adjustment     — nätstation förläggningsmiljö capex correction
    data/                  — precompute builder, runtime loader, committed parquet bundle
    ui/                    — Streamlit page + graph drawers (the only Streamlit layer)
    docs/                  — dependency graph + interpretation notes

Pure-calc rule: everything outside ui/ is Streamlit-free.

Public API:
    from new_benchmarking_model import run_new_benchmarking, NewBenchmarkingConfig
"""

from new_benchmarking_model.config import NewBenchmarkingConfig
from new_benchmarking_model.model import (
    run_new_benchmarking,
    NewBenchmarkingResult,
)

__all__ = [
    "run_new_benchmarking",
    "NewBenchmarkingResult",
    "NewBenchmarkingConfig",
]

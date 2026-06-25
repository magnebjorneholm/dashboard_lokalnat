"""ei_replication — reproduce Ei's published DEA (EIs_DEA.xlsx) via R/Benchmarking.

    from ei_replication.data import load_model_data, load_facit
    from ei_replication.replicate import replicate
    from ei_replication.compare import compare

    md = load_model_data()
    res = replicate(md.X, md.Y)
    cmp = compare(md, res)        # cmp.passed, cmp.max_seff_diff, cmp.table
"""

from __future__ import annotations

from .compare import Comparison, compare
from .data import ModelData, load_facit, load_model_data
from .replicate import ReplicationResult, replicate

__all__ = [
    "load_model_data",
    "load_facit",
    "ModelData",
    "replicate",
    "ReplicationResult",
    "compare",
    "Comparison",
]

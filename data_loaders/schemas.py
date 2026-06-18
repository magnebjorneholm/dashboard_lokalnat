"""
data_loaders/schemas.py

Lightweight, **non-mutating** column contracts for the datasets loaded at the
boundary. ``require_columns`` only asserts that the expected columns are present
and raises a clear error otherwise — it never reorders, coerces or drops data,
so it cannot change any downstream calculation.

The contracts list the join keys and the amount/value columns that the loaders
and calculations actually depend on; they are intentionally a *minimum* set, not
the full column list, so that additive changes to a source file don't trip them.
"""
from __future__ import annotations

from typing import Dict, Tuple

import pandas as pd

REQUIRED_COLUMNS: Dict[str, Tuple[str, ...]] = {
    # derived parquet
    "capbase_a": ("id_network", "cat_encode", "subcat_encode", "nuav_2022"),
    "capcost_a": (
        "id_network", "cat_encode", "time",
        "nuav_ord", "nuav_tail", "dep_ord", "dep_tail",
        "return_ord", "return_tail", "capcost_sum",
    ),
    "controllable_a": ("REId", "category", "year", "amount_nominal"),
    "controllable_meta": (
        "REId", "index_2018", "index_2019", "index_2020", "index_2021",
        "neo_adjustment", "eff_req_pct",
    ),
    "non_controllable_a": ("REId", "kent_category", "year", "amount"),

    # frozen snapshots (transformed loader output)
    "data_modeller": (
        "DMU", "REId", "company_name", "controllable_cost_average",
        "capital_cost_2024", "CU", "MW", "NS", "MWhl", "MWhh", "totex_first_year",
    ),
    "eis_dea": (
        "REId", "dea_efficiency", "dea_super_efficiency", "potential",
        "efficiency_requirement_annual", "is_outlier",
    ),

    # csv reference / inputs
    "adjustment_vars": ("reid", "year"),
    "reconciliation": ("id_network", "REId"),
    "company_names": ("REId", "name_full", "name_short"),
}


def require_columns(df: pd.DataFrame, schema_key: str) -> pd.DataFrame:
    """Assert that ``df`` contains the required columns for ``schema_key``.

    Returns ``df`` unchanged. Raises ``ValueError`` if columns are missing or
    ``KeyError`` if the schema key is unknown.
    """
    try:
        required = REQUIRED_COLUMNS[schema_key]
    except KeyError:
        raise KeyError(f"No schema registered for {schema_key!r}") from None
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(
            f"Dataset {schema_key!r} is missing required column(s) {missing}. "
            f"Present: {list(df.columns)}"
        )
    return df

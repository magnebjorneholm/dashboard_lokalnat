"""
data_loaders/cost_data.py

Loaders for controllable/non-controllable grunddata parquet files.
Follows the caching pattern from rab_data.py.
"""

import pandas as pd
from typing import Optional

from config.data_paths import require_dataset
from data_loaders._cache import cached
from data_loaders.schemas import require_columns


@cached(ttl=3600)
def load_controllable_detail(data_path: Optional[str] = None) -> pd.DataFrame:
    """Load controllable_a.parquet (company × category × year)."""
    df = pd.read_parquet(require_dataset("controllable_a", data_path))
    return require_columns(df, "controllable_a")


@cached(ttl=3600)
def load_controllable_meta(data_path: Optional[str] = None) -> pd.DataFrame:
    """Load controllable_meta.parquet (one row per company)."""
    df = pd.read_parquet(require_dataset("controllable_meta", data_path))
    return require_columns(df, "controllable_meta")


@cached(ttl=3600)
def load_non_controllable_detail(data_path: Optional[str] = None) -> pd.DataFrame:
    """Load non_controllable_a.parquet (company × kent_category × year)."""
    df = pd.read_parquet(require_dataset("non_controllable_a", data_path))
    return require_columns(df, "non_controllable_a")

"""
data_loaders/incentive_data.py

Loads incentive data from all_adjust_vars.csv and maps the numeric reid to the
REId format (REL00001, etc.).

Pure preparation/aggregation logic lives in
``calculations/incentive/incentive_prep.py``; the overridable-variable list and
UI metadata live in ``config/incentive_variables.py``.
"""

import pandas as pd
from typing import Optional, Dict

from config.data_paths import require_dataset
from config.incentive_variables import VARIABLE_COLUMNS
from data_loaders._cache import cached
from data_loaders.schemas import require_columns


@cached(ttl=3600)
def load_incentive_data(filepath: Optional[str] = None) -> pd.DataFrame:
    """
    Load incentive data and prepare it for calculation.

    Args:
        filepath: Path to all_adjust_vars.csv. If None, resolve via registry.

    Returns:
        DataFrame with all incentive variables, REId in the correct format.
        The 'capcost' placeholder column is dropped (replaced with actual return
        in the pipeline).
    """
    if filepath is None:
        filepath = require_dataset("adjustment_vars")

    df = pd.read_csv(filepath)
    require_columns(df, "adjustment_vars")

    # Map numeric reid to REId format (REL00001, REL00886, etc.)
    df['REId'] = df['reid'].apply(lambda x: f"REL{int(x):05d}")

    # Drop placeholder capcost — replaced with actual return in the pipeline
    if 'capcost' in df.columns:
        df = df.drop(columns=['capcost'])

    return df


def get_user_baseline_variables(
    user_reid: str,
    year: int = 2024,
    filepath: Optional[str] = None,
) -> Dict[str, float]:
    """
    Get baseline values for a company's incentive variables (default year 2024).

    Used in the UI to show baseline values in input fields.

    Args:
        user_reid: Company REId (e.g. "REL00886")
        year: Year to fetch values for (default 2024)
        filepath: Path to data (None = registry default)

    Returns:
        Dict of variable name -> baseline value (None for NaN cells).
        Empty dict if the company is not found.
    """
    try:
        df = load_incentive_data(filepath)
    except FileNotFoundError:
        return {}

    mask = (df['REId'] == user_reid) & (df['year'] == year)
    df_user = df[mask]

    if df_user.empty:
        return {}

    row = df_user.iloc[0]
    result: Dict[str, float] = {}
    for col in VARIABLE_COLUMNS:
        if col in row.index:
            val = row[col]
            result[col] = float(val) if pd.notna(val) else None
    return result

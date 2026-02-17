"""
Shared helpers for result output modules (M1-M5).

Consolidates duplicated data-loading, aggregation, filtering,
half-year extraction, and formatting functions that were previously
copy-pasted across multiple output files.
"""

import pandas as pd
from typing import List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from pipeline.core import PipelineResult

from config.colors import CHART_COLORS
from config.time_codes import (
    TIMECODE_TO_HALFYEAR as TIME_LABELS,
    PERIOD_2024_2027_CODES as TIME_CODES_ORDERED,
)

TOLERANCE = 0.01  # tkr

TKR_TO_MSEK = 1e3  # divide tkr by this to get MSEK

# ---------------------------------------------------------------------------
# Result table formatting (for Streamlit table display)
# ---------------------------------------------------------------------------

def fmt_tkr(value: float, show_sign: bool = False) -> str:
    """Format tkr value with comma thousand separators for table display."""
    if pd.isna(value):
        return "-"
    if show_sign and value > 0:
        return f"+{value:,.0f}"
    return f"{value:,.0f}"


def fmt_percent(value: float, decimals: int = 1, show_sign: bool = False,
                from_decimal: bool = False) -> str:
    """Format percentage value for table display.

    Args:
        value: percentage value (4.53) or decimal (0.0453) if from_decimal=True
        from_decimal: if True, multiply value by 100 first
    """
    if pd.isna(value):
        return "-"
    v = value * 100 if from_decimal else value
    if show_sign and v > 0:
        return f"+{v:.{decimals}f}%"
    return f"{v:.{decimals}f}%"


def fmt_msek(value: float) -> str:
    """Format tkr value as MSEK string (divide by 1000, 1 decimal)."""
    return f"{value / TKR_TO_MSEK:,.1f} MSEK"


def fmt_delta_msek(delta: float, tolerance: float = 0.01) -> "Optional[str]":
    """Format tkr delta as MSEK string with sign, or None if below tolerance."""
    if abs(delta) < tolerance:
        return None
    return f"{delta / TKR_TO_MSEK:+,.1f} MSEK"


def fmt_pct(value: float, decimals: int = 2) -> str:
    """Format decimal value as percentage string (0.0453 -> '4.53%')."""
    if pd.isna(value):
        return "-"
    return f"{value * 100:.{decimals}f}%"


def fmt_number(value: float, decimals: int = 4) -> str:
    """Format number with fixed decimals for table display."""
    if pd.isna(value):
        return "-"
    return f"{value:.{decimals}f}"


def calc_delta(case_val: float, baseline_val: float) -> Tuple[Optional[float], Optional[float]]:
    """Calculate absolute and percentage delta."""
    if pd.isna(case_val) or pd.isna(baseline_val):
        return None, None
    delta_abs = case_val - baseline_val
    delta_pct = (delta_abs / baseline_val * 100) if baseline_val != 0 else 0
    return delta_abs, delta_pct


# Chart colours for case/baseline ord/tail pattern
CLR_CASE_ORD = CHART_COLORS[0]       # Primary Blue
CLR_CASE_TAIL = "#93C5FD"            # Light blue (blue-300)
CLR_BL_ORD = "#64748B"               # Slate-500
CLR_BL_TAIL = "#CBD5E1"              # Slate-300


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_baseline_category_data(user_id_network: int) -> Optional[pd.DataFrame]:
    """Load baseline category data for user's company from capcost_a."""
    try:
        from data_loaders.rab_data import load_capcost_a
        df = load_capcost_a()
        return df[df['id_network'] == user_id_network].copy()
    except (FileNotFoundError, ImportError):
        return None


def get_case_category_data(
    case: "PipelineResult",
    user_id_network: int,
) -> Optional[pd.DataFrame]:
    """Get case category data from pipeline result."""
    df_cat = getattr(case.pre_dea, 'df_by_category', None)
    if df_cat is None:
        return None
    return df_cat[df_cat['id_network'] == user_id_network].copy()


# ---------------------------------------------------------------------------
# Column ensure / aggregate / filter
# ---------------------------------------------------------------------------

def ensure_component_cols(
    df: pd.DataFrame,
    col_ord: str,
    col_tail: str,
    col_total: str,
) -> pd.DataFrame:
    """Ensure ord, tail columns exist and compute total = ord + tail."""
    for col in [col_ord, col_tail]:
        if col not in df.columns:
            df[col] = 0.0
    df[col_total] = df[col_ord] + df[col_tail]
    return df


def aggregate_period(
    df: Optional[pd.DataFrame],
    col_ord: str,
    col_tail: str,
    col_total: str,
) -> pd.DataFrame:
    """Aggregate half-year data to period totals per category."""
    if df is None or df.empty:
        return pd.DataFrame()
    agg_cols = {c: 'sum' for c in [col_ord, col_tail] if c in df.columns}
    if not agg_cols:
        return pd.DataFrame()
    result = df.groupby('cat_encode').agg(agg_cols).reset_index()
    return ensure_component_cols(result, col_ord, col_tail, col_total)


def aggregate_halfyears(
    df: Optional[pd.DataFrame],
    col_ord: str,
    col_tail: str,
    col_total: str,
) -> pd.DataFrame:
    """Keep half-year granularity with component totals."""
    if df is None or df.empty:
        return pd.DataFrame()
    result = df.copy()
    result['time_label'] = result['time'].map(TIME_LABELS)
    return ensure_component_cols(result, col_ord, col_tail, col_total)


def active_categories(
    case_period: pd.DataFrame,
    baseline_period: pd.DataFrame,
    total_col: str,
) -> List[int]:
    """Return sorted cat_encode values with data above tolerance in either set."""
    active = set()
    for df in [case_period, baseline_period]:
        if df.empty:
            continue
        above = df[df[total_col].abs() > TOLERANCE]
        active.update(above['cat_encode'].tolist())
    return sorted(active)


def halfyear_values(
    df_hy: pd.DataFrame,
    cat_encode: int,
    col: str,
    divisor: float = 1.0,
) -> List[float]:
    """Extract ordered list of 8 half-year values for one category.

    Args:
        divisor: Divide each value by this (e.g. TKR_TO_MSEK for MSEK output).
    """
    if df_hy.empty:
        return [0.0] * 8
    cat_df = df_hy[df_hy['cat_encode'] == cat_encode]
    values = []
    for tc in TIME_CODES_ORDERED:
        row = cat_df[cat_df['time'] == tc]
        val = float(row[col].iloc[0]) / divisor if not row.empty else 0.0
        values.append(val)
    return values


def hy_row_values(
    df_hy: pd.DataFrame,
    cat_encode: int,
    time_code: int,
    col_ord: str,
    col_tail: str,
    col_total: str,
    divisor: float = 1.0,
) -> tuple:
    """Return (ord, tail, total) for one category + time code.

    Args:
        divisor: Divide each value by this (e.g. TKR_TO_MSEK for MSEK output).
    """
    if df_hy.empty:
        return (0.0, 0.0, 0.0)
    row = df_hy[(df_hy['cat_encode'] == cat_encode) & (df_hy['time'] == time_code)]
    if row.empty:
        return (0.0, 0.0, 0.0)
    return (
        float(row[col_ord].iloc[0]) / divisor,
        float(row[col_tail].iloc[0]) / divisor,
        float(row[col_total].iloc[0]) / divisor,
    )

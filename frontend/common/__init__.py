"""Common components för Regumetrica UI."""

from frontend.common.formatting import format_tkr, format_percent, format_number, format_delta
from frontend.common.parameter_input import parameter_input, parameter_select

__all__ = [
    "format_tkr",
    "format_percent",
    "format_number",
    "format_delta",
    "parameter_input",
    "parameter_select",
]

# Expose asset category utilities
from frontend.common.asset_categories import (
    ASSET_CATEGORIES,
    CATEGORY_BY_CODE,
    BASELINE_LIFETIMES,
    get_category_name,
    get_baseline_lifetime,
)

__all__ += [
    "ASSET_CATEGORIES",
    "CATEGORY_BY_CODE",
    "BASELINE_LIFETIMES",
    "get_category_name",
    "get_baseline_lifetime",
]

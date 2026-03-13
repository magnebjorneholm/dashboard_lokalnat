"""
frontend/results/

Module output rendering for the Results page.
Each module has its own file with a render() function.
"""

from frontend.results import (
    m1_asset_base_output,
    m2_depreciation_output,
    m3_cost_of_capital_output,
    m5_efficiency_output,
)

__all__ = [
    "m1_asset_base_output",
    "m2_depreciation_output",
    "m3_cost_of_capital_output",
    "m5_efficiency_output",
]

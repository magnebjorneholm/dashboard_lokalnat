"""
calculations module

CAPEX calculations, DEA analysis, efficiency requirements, controllable costs,
and revenue frame assembly for Regumetrica pipeline.

Subpackages:
  capex/      — KENT, WACC, data mapping (M1/M2/M3)
  opex/       — Controllable costs, grunddata aggregation (M4)
  frontier/   — DEA analysis (M7)
  incentive/  — Quality/loss/load adjustments (M3 incentive)
  efficiency/ — Efficiency requirement (M5)
"""

from .capex.kent_capbase_prep import (
    read_kent_excel,
    process_kent_components,
    build_capbase_a_from_kent,
    validate_capbase_a,
    get_category_encode,
    year_to_time_code,
    halvar_to_time_code,
    CATEGORY_MAPPING,
)
from .capex.kent_calculations import (
    calculate_ages_and_nuav_batch,
    calculate_depreciation_batch,
    calculate_returns_batch,
    aggregate_to_network_level,
    calculate_capex_outputs,
    run_kent_calculations_batch
)
from .capex.data_mapping import (
    merge_kent_with_baseline,
)
from .frontier.dea_calculations import (
    run_dea_analysis,
    BASELINE_DEA_SPEC
)
from .efficiency.efficiency_requirement import (
    calculate_eff_req_from_potential,
    calculate_eff_req_for_dataframe,
    DEFAULT_EFF_REQ_PARAMS
)
from .opex.controllable_cost_calculations import (
    calculate_controllable_with_eff_req,
    get_controllable_from_sdf,
    DEFAULT_CONTROLLABLE_METHOD
)
from .revenue_frame_assembly import (
    assemble_revenue_frame,
    extract_user_revenue_frame,
    create_revenue_frame_breakdown
)
from .capex.wacc_calculations import (
    CAPMInputs,
    calculate_wacc,
    BASELINE_WACC,
)
# Time code constants & helpers (now in config/)
from config.time_codes import (
    HALFYEAR_TO_TIMECODE,
    TIMECODE_TO_HALFYEAR,
    YEAR_TO_TIMECODES,
    PERIOD_2024_2027_CODES,
    YEAR_TO_FIRST_TIMECODE,
    timecode_to_year,
    timecode_to_halfyear,
    timecode_to_label,
    year_to_timecodes,
)

from config.incentive_parameters import MISSING_DATA_IDS
from .incentive.incentive_calculations import calculate_all_incentives

__all__ = [
    # KENT calculations
    'calculate_ages_and_nuav_batch',
    'calculate_depreciation_batch',
    'calculate_returns_batch',
    'aggregate_to_network_level',
    'calculate_capex_outputs',
    'run_kent_calculations_batch',

    # Data mapping
    'merge_kent_with_baseline',

    # DEA analysis
    'run_dea_analysis',
    'BASELINE_DEA_SPEC',

    # Efficiency requirements
    'calculate_eff_req_from_potential',
    'calculate_eff_req_for_dataframe',
    'DEFAULT_EFF_REQ_PARAMS',

    # Controllable costs
    'calculate_controllable_with_eff_req',
    'get_controllable_from_sdf',
    'DEFAULT_CONTROLLABLE_METHOD',

    # Revenue frame assembly
    'assemble_revenue_frame',
    'extract_user_revenue_frame',
    'create_revenue_frame_breakdown',

    # WACC calculations
    'CAPMInputs',
    'calculate_wacc',
    'BASELINE_WACC',

    # Kent capbase prep
    'read_kent_excel',
    'process_kent_components',
    'build_capbase_a_from_kent',
    'validate_capbase_a',
    'get_category_encode',
    'year_to_time_code',
    'halvar_to_time_code',
    'CATEGORY_MAPPING',

    # Time codes (re-exported from config)
    'HALFYEAR_TO_TIMECODE',
    'TIMECODE_TO_HALFYEAR',
    'YEAR_TO_TIMECODES',
    'PERIOD_2024_2027_CODES',
    'YEAR_TO_FIRST_TIMECODE',
    'timecode_to_year',
    'timecode_to_halfyear',
    'timecode_to_label',
    'year_to_timecodes',

    # Incentive calculations
    'MISSING_DATA_IDS',
    'calculate_all_incentives',
]

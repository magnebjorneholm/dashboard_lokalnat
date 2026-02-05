"""
calculations module

CAPEX calculations, DEA analysis, effektiviseringskrav, påverkbara kostnader, 
and intäktsram assembly for Regumetrica pipeline.
"""

from .kent_calculations import (
    calculate_ages_and_nuav_batch,
    calculate_depreciation_batch,
    calculate_returns_batch,
    aggregate_to_network_level,
    calculate_capex_outputs,
    run_kent_calculations_batch
)
from .data_mapping import (
    merge_kent_with_baseline,
    
)
from .dea_calculations import (
    run_dea_analysis,
    BASELINE_DEA_SPEC
)
from .effektiviseringskrav import (
    calculate_effkrav_from_potential,
    calculate_effkrav_for_dataframe,
    DEFAULT_EFFKRAV_PARAMS
)
from .paverkbara_calculations import (
    calculate_paverkbara_with_effkrav,
    get_paverkbara_from_sdf,
    DEFAULT_PAVERKBARA_METHOD
)
from .intaktsram_assembly import (
    assemble_intaktsram,
    extract_user_intaktsram,
    create_intaktsram_breakdown
)
from .wacc_calculations import (
    CAPMInputs,
    calculate_wacc,
    BASELINE_WACC,
)
# Time code constants & helpers
from .time_codes import (
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

from .incentive_parameters import MISSING_DATA_IDS
from .incentive_calculations import calculate_all_incentives

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
    
    # Effektiviseringskrav
    'calculate_effkrav_from_potential',
    'calculate_effkrav_for_dataframe',
    'DEFAULT_EFFKRAV_PARAMS',
    
    # Påverkbara kostnader
    'calculate_paverkbara_with_effkrav',
    'get_paverkbara_from_sdf',
    'DEFAULT_PAVERKBARA_METHOD',
    
    # Intäktsram assembly
    'assemble_intaktsram',
    'extract_user_intaktsram',
    'create_intaktsram_breakdown',

    # WACC calculations
    'CAPMInputs',
    'calculate_wacc',
    'BASELINE_WACC',
]

__all__ += [
    # Kent capbase prep
    'read_kent_excel',
    'process_kent_components',
    'build_capbase_a_from_kent',
    'validate_capbase_a',
    'get_category_encode',
    'year_to_time_code',
    'halvar_to_time_code',
    'CATEGORY_MAPPING',

    # Time codes
    'HALFYEAR_TO_TIMECODE',
    'TIMECODE_TO_HALFYEAR',
    'YEAR_TO_TIMECODES',
    'PERIOD_2024_2027_CODES',
    'YEAR_TO_FIRST_TIMECODE',
    'timecode_to_year',
    'timecode_to_halfyear',
    'timecode_to_label',
    'year_to_timecodes',

    #incentive calculations
    'MISSING_DATA_IDS',
    'calculate_all_incentives',
]
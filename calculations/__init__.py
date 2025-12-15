"""
calculations module

CAPEX calculations, DEA analysis, effektiviseringskrav, påverkbara kostnader, 
and intäktsram assembly for Regumetrica pipeline.
"""

from .wacc_scaling import (
    calculate_wacc_scaled_capex,
    get_wacc_scaling_summary
)
from .kent_calculations import (
    load_capbase_a,
    apply_parameter_adjustments,
    calculate_ages_and_nuav_batch,
    calculate_depreciation_batch,
    calculate_returns_batch,
    aggregate_to_network_level,
    calculate_capex_outputs,
    run_kent_calculations_batch
)
from .data_mapping import (
    merge_kent_with_baseline,
    get_detailed_capex_data,
    create_capex_breakdown
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

__all__ = [
    # WACC scaling
    'calculate_wacc_scaled_capex',
    'get_wacc_scaling_summary',
    
    # KENT calculations
    'load_capbase_a',
    'apply_parameter_adjustments',
    'calculate_ages_and_nuav_batch',
    'calculate_depreciation_batch',
    'calculate_returns_batch',
    'aggregate_to_network_level',
    'calculate_capex_outputs',
    'run_kent_calculations_batch',
    
    # Data mapping
    'merge_kent_with_baseline',
    'get_detailed_capex_data',
    'create_capex_breakdown',
    
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
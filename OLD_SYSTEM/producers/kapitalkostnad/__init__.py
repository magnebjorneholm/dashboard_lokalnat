"""
kapitalkostnad - CAPEX producers
=================================

Exporterar CAPEX-producers och beräkningsfunktioner.
"""

from .capex_producers import (
    produce_capex_from_wacc_scaling,
    produce_capex_from_kent_full,
    produce_capex_from_kent_upload
)

from .kent_pipeline import (
    calculate_ages_and_nuav,
    calculate_depreciation,
    calculate_returns,
    compile_capcost
)

from .kent_upload_processor import (
    extract_capex_from_kent
)

from .parameter_adjustments import (
    apply_normvalue_adjustments,
    apply_lifetime_adjustments
)

__all__ = [
    # Producers
    'produce_capex_from_wacc_scaling',
    'produce_capex_from_kent_full',
    'produce_capex_from_kent_upload',
    
    # Pipeline functions
    'calculate_ages_and_nuav',
    'calculate_depreciation',
    'calculate_returns',
    'compile_capcost',
    
    # Upload processor
    'extract_capex_from_kent',
    
    # Adjustments
    'apply_normvalue_adjustments',
    'apply_lifetime_adjustments',
]
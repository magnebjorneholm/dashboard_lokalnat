"""
bootstrap_registry.py

Helper to bind actual producer callables from `producers.*` to the
`ProducerSpec.method` entries created by `build_default_registry()`.

This keeps `build_default_registry()` lightweight (it can register
producer IDs and metadata) while allowing a single place to wire
the real functions.
"""
from typing import Any

from core.producer_registry import ProducerRegistry

from producers.baseline.baseline_loaders import (
    produce_wacc_from_baseline,
    produce_capex_from_baseline,
    produce_opex_paverkbara_from_baseline,
    produce_opex_opaverkbara_from_baseline,
    produce_volumes_from_baseline,
    produce_capex_baseline_value
)

from producers.wacc.wacc_producers import (
    produce_wacc_from_capm
)

from producers.kapitalkostnad.capex_producers import (
    produce_capex_from_wacc_scaling,
    produce_capex_from_kent_full,
    produce_capex_from_kent_upload
)

from producers.effektivitet.dea_producer import produce_efficiency_from_dea

from producers.intaktsram.effektiviseringskrav import produce_effektiviseringskrav
from producers.intaktsram.intaktsram_assembly import assemble_intaktsram


def bootstrap_registry(registry: ProducerRegistry) -> ProducerRegistry:
    """Bind producer functions to registry ProducerSpec.method in-place.

    Args:
        registry: ProducerRegistry returned from `build_default_registry()`

    Returns:
        The same registry instance with `method` fields populated where possible.
    """
    # WACC
    try:
        reg_wacc = registry.get_variable_spec('wacc')
        if 'baseline' in reg_wacc.producers:
            reg_wacc.producers['baseline'].method = produce_wacc_from_baseline
        if 'capm' in reg_wacc.producers:
            reg_wacc.producers['capm'].method = produce_wacc_from_capm
    except Exception:
        pass

    # WACC components producers
    try:
        reg_wc = registry.get_variable_spec('wacc_components')
        if 'baseline' in reg_wc.producers:
            reg_wc.producers['baseline'].method = (lambda: {
                'rf_nominal': 0.0287,
                'mrp_nominal': 0.0668,
                'beta_asset': 0.37,
                'debt_share': 0.36,
                'tax_rate': 0.206,
                'credit_spread': 0.0114,
                'inflation': 0.0202
            })
        # user_input producer reads from case_definition['parameters']
        # This is handled by variable_resolver, so method=None is correct
    except Exception:
        pass

    # CAPEX
    try:
        reg_capex = registry.get_variable_spec('capex')
        if 'baseline' in reg_capex.producers:
            reg_capex.producers['baseline'].method = produce_capex_from_baseline
        if 'wacc_scaling' in reg_capex.producers:
            reg_capex.producers['wacc_scaling'].method = produce_capex_from_wacc_scaling
        if 'kent_full' in reg_capex.producers:
            reg_capex.producers['kent_full'].method = produce_capex_from_kent_full
        if 'kent_upload' in reg_capex.producers:
            reg_capex.producers['kent_upload'].method = produce_capex_from_kent_upload
    except Exception:
        pass

    # Baseline helpers
    try:
        reg_capex_base = registry.get_variable_spec('capex_baseline')
        if 'baseline' in reg_capex_base.producers:
            reg_capex_base.producers['baseline'].method = produce_capex_baseline_value
    except Exception:
        pass

    # OPEX
    try:
        reg_opex_p = registry.get_variable_spec('opex_paverkbara')
        if 'baseline' in reg_opex_p.producers:
            reg_opex_p.producers['baseline'].method = produce_opex_paverkbara_from_baseline

        reg_opex_i = registry.get_variable_spec('opex_opaverkbara')
        if 'baseline' in reg_opex_i.producers:
            reg_opex_i.producers['baseline'].method = produce_opex_opaverkbara_from_baseline
    except Exception:
        pass

    # Volumes
    try:
        reg_vol = registry.get_variable_spec('volumes')
        if 'baseline' in reg_vol.producers:
            reg_vol.producers['baseline'].method = produce_volumes_from_baseline
    except Exception:
        pass

    # Efficiency
    try:
        reg_eff = registry.get_variable_spec('efficiency')
        if 'dea' in reg_eff.producers:
            reg_eff.producers['dea'].method = produce_efficiency_from_dea
    except Exception:
        pass

    # Effektiviseringskrav
    try:
        reg_effkr = registry.get_variable_spec('effektiviseringskrav')
        if 'calculation' in reg_effkr.producers:
            reg_effkr.producers['calculation'].method = produce_effektiviseringskrav
    except Exception:
        pass

    # Intaktsram assembly
    try:
        reg_ir = registry.get_variable_spec('intaktsram')
        if 'assembly' in reg_ir.producers:
            reg_ir.producers['assembly'].method = assemble_intaktsram
    except Exception:
        pass

    return registry
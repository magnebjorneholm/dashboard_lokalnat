"""
frontend/utils/config_adapter.py

Config Adapter for Regumetrica UI.

Converts UI configuration to CaseDefinition for backend pipeline.
This is the only bridge between frontend and backend.

UPDATED: Removed RAB-editor, simplified to use new m1_asset_base structure:
- general_scaling (Param 1.1.1)
- cat_scaling (Param 1.2.X)
- var_scaling (Var 10.X) - company-specific
- kent_file_bytes - company-specific override
"""

from typing import Any, Dict, List, Optional

import pandas as pd

from config.case_definition import (
    CaseDefinition,
    PreDeaConfig,
    DeaConfig,
    PostDeaConfig,
    IncentiveConfig,
    CapbaseSource,
    CapexMethod,
    EfficiencyMethod,
    ControllableMethod,
    reid_to_id_network,
)


# =============================================================================
# BASELINE VALUES
# =============================================================================

from calculations.wacc_calculations import BASELINE_WACC, BASELINE_CAPM, BASELINE_DERIVED as _WACC_DERIVED
from calculations.incentive_parameters import BASELINE_INCENTIVE

from calculations.dea_calculations import BASELINE_DEA_SPEC
from config.column_names import COL_CAPITAL_COST_2024, COL_CONTROLLABLE_AVG
from config.glossary import (
    PID_GENERAL_SCALING, PID_WACC_REAL, PID_LOSS_SCALING, PID_LOSS_SHARING,
    PID_MAX_POTENTIAL_CAP, PID_REALIZATION_TIME, PID_CUSTOMER_SHARING,
    PID_MIN_ANNUAL_REQ,
)

DEA_INPUT_OPTIONS = BASELINE_DEA_SPEC['inputs']
DEA_OUTPUT_OPTIONS = BASELINE_DEA_SPEC['outputs']

PARAM_TO_CONFIG = {
    PID_WACC_REAL: "m3_cost_of_capital.wacc_override",
    PID_MAX_POTENTIAL_CAP: "m5_efficiency.trunkering_max",
}


# =============================================================================
# MAIN FUNCTION
# =============================================================================

def build_case_definition(
    user_reid: str,
    ui_config: Dict[str, Any]
) -> CaseDefinition:
    """
    Build CaseDefinition from UI configuration.
    
    Args:
        user_reid: User's REId
        ui_config: Dict from session_state["ui_config"]
    
    Returns:
        CaseDefinition ready for pipeline
    """
    if not user_reid:
        raise ValueError("user_reid missing")
    if not user_reid.startswith("REL"):
        raise ValueError(f"Invalid REId format: {user_reid}")
    
    user_id_network = reid_to_id_network(user_reid)
    
    pre_dea = _build_pre_dea_config(ui_config, user_id_network)
    dea = _build_dea_config(ui_config)
    post_dea = _build_post_dea_config(ui_config)
    
    return CaseDefinition(
        name="UI Case",
        user_reid=user_reid,
        pre_dea=pre_dea,
        dea=dea,
        post_dea=post_dea
    )


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _build_pre_dea_config(
    ui_config: Dict[str, Any],
    user_id_network: int
) -> PreDeaConfig:
    """
    Build PreDeaConfig from UI configuration.
    
    SOURCE PRIORITY (data supply for logged-in company):
    1. KENT_UPLOAD (if file uploaded) - highest priority
    2. VAR_SCALED (if var_scaling set)
    3. BASELINE (no change)
    
    METHOD PRIORITY (calculation method for ALL companies):
    1. PARAMETER_CHANGE (if any parameter changed: WACC/normvalues/lifetimes)
    2. BASELINE (no change)
    
    IMPORTANT: Parameters (general_scaling, cat_scaling) affect ALL companies.
    Variables (var_scaling) only affect logged-in company.
    """
    m1 = ui_config.get("m1_asset_base", {})
    m2 = ui_config.get("m2_depreciation", {})
    m3 = ui_config.get("m3_cost_of_capital", {})
    
    # === CAPBASE SOURCE (for logged-in company) ===
    kent_file_bytes = m1.get("kent_file_bytes")
    var_scaling = m1.get("var_scaling")
    
    if kent_file_bytes is not None:
        capbase_source = CapbaseSource.KENT_UPLOAD
        user_capbase_scaled = None
    elif var_scaling:
        capbase_source = CapbaseSource.VAR_SCALED
        user_capbase_scaled = _get_scaled_user_capbase(user_id_network, var_scaling)
    else:
        capbase_source = CapbaseSource.BASELINE
        user_capbase_scaled = None
    
    # === NORMVALUE ADJUSTMENTS (Parameters - ALL companies) ===
    normvalue_adjustments = _combine_scaling_factors(
        general_scaling=m1.get("general_scaling"),
        cat_scaling=m1.get("cat_scaling")
    )
    
    # === CAPEX METHOD ===
    lifetime_adjustments = m2.get("lifetime_adjustments")
    wacc_override = m3.get("wacc_override")
    
    has_parameter_changes = (
        normvalue_adjustments is not None or 
        lifetime_adjustments is not None
    )
    has_wacc_change = (wacc_override is not None)
    
    # Any parameter or WACC change triggers PARAMETER_CHANGE (full KENT calculation)
    if has_parameter_changes or has_wacc_change:
        capex_method = CapexMethod.PARAMETER_CHANGE
    else:
        capex_method = CapexMethod.BASELINE
    
    # === WACC INPUT SPECIFICATION (for M3 output display) ===
    wacc_input_method, wacc_capm_inputs, wacc_derived_inputs = _extract_wacc_inputs(m3)
    
    return PreDeaConfig(
        # Source (for user's company)
        capbase_source=capbase_source,
        user_capbase_scaled=user_capbase_scaled,
        kent_file_bytes=kent_file_bytes if capbase_source == CapbaseSource.KENT_UPLOAD else None,
        kent_user_id_network=user_id_network if capbase_source == CapbaseSource.KENT_UPLOAD else None,
        
        # Method (for all companies)
        method=capex_method,
        wacc=wacc_override,
        normvalue_adjustments=normvalue_adjustments,
        lifetime_adjustments=lifetime_adjustments,
        
        # WACC input specification
        wacc_input_method=wacc_input_method,
        wacc_capm_inputs=wacc_capm_inputs,
        wacc_derived_inputs=wacc_derived_inputs,
    )


def _extract_wacc_inputs(m3: Dict[str, Any]) -> tuple:
    """
    Extract WACC input method and parameters from m3_cost_of_capital config.
    
    Returns:
        Tuple of (wacc_input_method, wacc_capm_inputs, wacc_derived_inputs)
    """
    # Derived method defaults (composed from centralized baseline constants)
    _DERIVED_DEFAULTS = {
        "cost_of_equity": _WACC_DERIVED["cost_of_equity_nominal"],
        "cost_of_debt": _WACC_DERIVED["cost_of_debt_nominal"],
        "debt_ratio": BASELINE_CAPM["debt_ratio"],
        "tax_rate": BASELINE_CAPM["tax_rate"],
        "inflation": BASELINE_CAPM["inflation"],
    }
    
    # No WACC override means baseline
    if m3.get("wacc_override") is None:
        return "baseline", None, None
    
    # Check for CAPM inputs (all 7 base parameters)
    capm_keys = ["debt_ratio", "asset_beta", "risk_free_rate", 
                 "market_risk_premium", "credit_risk_premium", "tax_rate", "inflation"]
    has_capm = any(m3.get(k) is not None for k in capm_keys)
    
    # Check for derived inputs
    derived_keys = ["cost_of_equity", "cost_of_debt", "debt_ratio_derived", 
                    "tax_rate_derived", "inflation_derived"]
    has_derived = any(m3.get(k) is not None for k in derived_keys)
    
    # Determine method based on what's present
    if has_capm:
        wacc_input_method = "capm"
        wacc_capm_inputs = {
            "debt_ratio": m3.get("debt_ratio", BASELINE_CAPM["debt_ratio"]),
            "asset_beta": m3.get("asset_beta", BASELINE_CAPM["asset_beta"]),
            "risk_free_rate": m3.get("risk_free_rate", BASELINE_CAPM["risk_free_rate"]),
            "market_risk_premium": m3.get("market_risk_premium", BASELINE_CAPM["market_risk_premium"]),
            "credit_risk_premium": m3.get("credit_risk_premium", BASELINE_CAPM["credit_risk_premium"]),
            "tax_rate": m3.get("tax_rate", BASELINE_CAPM["tax_rate"]),
            "inflation": m3.get("inflation", BASELINE_CAPM["inflation"]),
        }
        wacc_derived_inputs = None  # Will be calculated in pre_dea
        
    elif has_derived:
        wacc_input_method = "derived"
        wacc_capm_inputs = None
        wacc_derived_inputs = {
            "cost_of_equity": m3.get("cost_of_equity", _DERIVED_DEFAULTS["cost_of_equity"]),
            "cost_of_debt": m3.get("cost_of_debt", _DERIVED_DEFAULTS["cost_of_debt"]),
            "debt_ratio": m3.get("debt_ratio_derived", _DERIVED_DEFAULTS["debt_ratio"]),
            "tax_rate": m3.get("tax_rate_derived", _DERIVED_DEFAULTS["tax_rate"]),
            "inflation": m3.get("inflation_derived", _DERIVED_DEFAULTS["inflation"]),
        }
        
    else:
        # Direct input - only wacc_override is set
        wacc_input_method = "direct"
        wacc_capm_inputs = None
        wacc_derived_inputs = None
    
    return wacc_input_method, wacc_capm_inputs, wacc_derived_inputs


def _combine_scaling_factors(
    general_scaling: Optional[float],
    cat_scaling: Optional[Dict[int, float]]
) -> Optional[Dict[int, float]]:
    """
    Combine general and category scaling factors into normvalue_adjustments.
    
    Logic:
    - If only general_scaling: apply to all 17 categories
    - If only cat_scaling: use as-is
    - If both: multiply general * category for each
    
    Returns:
        Dict[cat_encode, combined_factor] or None if no changes
    """
    from frontend.common.asset_categories import ASSET_CATEGORIES
    
    has_general = general_scaling is not None and general_scaling != 1.0
    has_cat = cat_scaling is not None and len(cat_scaling) > 0
    
    if not has_general and not has_cat:
        return None
    
    result = {}
    
    for cat in ASSET_CATEGORIES:
        cat_encode = cat.cat_encode
        
        # Start with 1.0
        factor = 1.0
        
        # Apply general scaling
        if has_general:
            factor *= general_scaling
        
        # Apply category-specific scaling
        if has_cat and cat_encode in cat_scaling:
            factor *= cat_scaling[cat_encode]
        
        # Only include if different from 1.0
        if factor != 1.0:
            result[cat_encode] = factor
    
    return result if result else None


def _get_scaled_user_capbase(
    user_id_network: int,
    var_scaling: Dict[int, float]
) -> Optional[pd.DataFrame]:
    """
    Load user's capbase and apply variable scaling to ordinarie components.
    
    Returns:
        DataFrame ready for kent_calculations, or None on error
    """
    try:
        from data_loaders.rab_data import load_user_capbase
        from frontend.modules.base.m1_asset_base import apply_variable_scaling
        
        df = load_user_capbase(user_id_network)
        if df.empty:
            return None
        
        return apply_variable_scaling(df, var_scaling)
    except ImportError as e:
        print(f"WARNING: Could not import required modules: {e}")
        return None
    except Exception as e:
        print(f"WARNING: Could not load/scale user capbase: {e}")
        return None


def _build_dea_config(ui_config: Dict[str, Any]) -> DeaConfig:
    """Build DeaConfig from addon_benchmarking."""
    addon = ui_config.get("addon_benchmarking", {})
    
    _op = BASELINE_DEA_SPEC['outlier_params']
    if addon.get("dea_method") == "custom":
        return DeaConfig(
            method=EfficiencyMethod.DEA,
            inputs=addon.get("dea_inputs", DEA_INPUT_OPTIONS),
            outputs=addon.get("dea_outputs", DEA_OUTPUT_OPTIONS),
            rts=addon.get("dea_rts", BASELINE_DEA_SPEC['rts']),
            multiplier=addon.get("dea_multiplier", _op['multiplier']),
            q_lower=addon.get("dea_q_lower", _op['q_lower']),
            q_upper=addon.get("dea_q_upper", _op['q_upper']),
        )
    else:
        return DeaConfig(method=EfficiencyMethod.BASELINE)


def _is_empty_or_none(value: Any) -> bool:
    """Check if value is None or empty container."""
    if value is None:
        return True
    if isinstance(value, (dict, list)) and len(value) == 0:
        return True
    return False


def _build_incentive_config(ui_config: Dict[str, Any]) -> IncentiveConfig:
    """Build IncentiveConfig from m3_quality_adjustments."""
    m3q = ui_config.get("m3_quality_adjustments", {})
    m3v = ui_config.get("m3_incentive_variables", {})
    
    converted = _convert_incentive_keys(m3q)
    
    # Get values with proper None/empty handling
    kpi_converted = converted.get("kpi")
    kpi_raw = m3q.get("kpi")
    kpi = None
    if not _is_empty_or_none(kpi_converted):
        kpi = kpi_converted
    elif not _is_empty_or_none(kpi_raw):
        kpi = kpi_raw
    
    k_nf_converted = converted.get("k_nf")
    k_nf_raw = m3q.get("k_nf")
    k_nf = None
    if not _is_empty_or_none(k_nf_converted):
        k_nf = k_nf_converted
    elif not _is_empty_or_none(k_nf_raw):
        k_nf = k_nf_raw
    
    sharing_netloss = m3q.get("sharing_netloss")
    adj_max_agg = m3q.get("adj_max_agg")
    adj_max_cemi4 = m3q.get("adj_max_cemi4")
    
    ait_costs_converted = converted.get("ait_costs")
    ait_costs_raw = m3q.get("ait_costs")
    ait_costs = None
    if not _is_empty_or_none(ait_costs_converted):
        ait_costs = ait_costs_converted
    elif not _is_empty_or_none(ait_costs_raw):
        ait_costs = ait_costs_raw
    
    aif_costs_converted = converted.get("aif_costs")
    aif_costs_raw = m3q.get("aif_costs")
    aif_costs = None
    if not _is_empty_or_none(aif_costs_converted):
        aif_costs = aif_costs_converted
    elif not _is_empty_or_none(aif_costs_raw):
        aif_costs = aif_costs_raw
    
    enable_quality = m3q.get("enable_quality", True)
    enable_netloss = m3q.get("enable_netloss", True)
    enable_load = m3q.get("enable_load", True)
    
    variable_overrides = None
    if m3v:
        overrides = {
            k: v for k, v in m3v.items() 
            if v is not None and v != "NULL" and v != "null"
        }
        if overrides:
            variable_overrides = overrides
    
    return IncentiveConfig(
        kpi=kpi if kpi is not None else BASELINE_INCENTIVE["kpi"],
        k_nf=k_nf if k_nf is not None else BASELINE_INCENTIVE["k_nf"],
        sharing_netloss=sharing_netloss if sharing_netloss is not None else BASELINE_INCENTIVE["sharing_netloss"],
        adj_max_agg=adj_max_agg if adj_max_agg is not None else BASELINE_INCENTIVE["adj_max_agg"],
        adj_max_cemi4=adj_max_cemi4 if adj_max_cemi4 is not None else BASELINE_INCENTIVE["adj_max_cemi4"],
        ait_costs=ait_costs,
        aif_costs=aif_costs,
        enable_quality=enable_quality,
        enable_netloss=enable_netloss,
        enable_load=enable_load,
        variable_overrides=variable_overrides,
    )


def _convert_incentive_keys(m3q: Dict[str, Any]) -> Dict[str, Any]:
    """Convert JSON keys to backend format."""
    converted: Dict[str, Any] = {}
    
    if "kpi" in m3q and m3q["kpi"]:
        converted["kpi"] = {int(k): v for k, v in m3q["kpi"].items()}
    
    if "k_nf" in m3q and m3q["k_nf"]:
        converted["k_nf"] = {int(k): v for k, v in m3q["k_nf"].items()}
    
    if "ait_costs" in m3q and m3q["ait_costs"]:
        converted["ait_costs"] = {}
        for key, value in m3q["ait_costs"].items():
            parts = key.split("_")
            if len(parts) == 2:
                ann, sni = parts[0], int(parts[1])
                converted["ait_costs"][(ann, sni)] = value
    
    if "aif_costs" in m3q and m3q["aif_costs"]:
        converted["aif_costs"] = {}
        for key, value in m3q["aif_costs"].items():
            parts = key.split("_")
            if len(parts) == 2:
                ann, sni = parts[0], int(parts[1])
                converted["aif_costs"][(ann, sni)] = value
    
    return converted


def calculate_truncation_min_from_outlier_req(
    outlier_req: float,
    customer_sharing: float,
    realization_time: int,
    supervision_period: int
) -> float:
    """
    Calculate truncation_min that gives same annual requirement as outlier_req.

    This is the INVERSE calculation of the efficiency requirement formula.
    With baseline parameters (outlier_req=1%) this gives truncation_min ~ 16.24%
    """
    total_eff = (1 + outlier_req) ** supervision_period - 1
    realization_factor = supervision_period / realization_time
    potential = total_eff / (customer_sharing * realization_factor)
    return potential


def _build_post_dea_config(ui_config: Dict[str, Any]) -> PostDeaConfig:
    """Build PostDeaConfig from m5_efficiency, m3_quality_adjustments."""
    m5 = ui_config.get("m5_efficiency", {})

    truncation_max = m5.get("trunkering_max") if m5.get("trunkering_max") is not None else 0.30
    outlier_req = m5.get("outlier_krav") if m5.get("outlier_krav") is not None else 0.01
    realization_time = m5.get("realiseringstid") if m5.get("realiseringstid") is not None else 8
    customer_sharing = m5.get("kunddelning") if m5.get("kunddelning") is not None else 0.50
    supervision_period = m5.get("tillsynsperiod") if m5.get("tillsynsperiod") is not None else 4

    truncation_min_explicit = m5.get("trunkering_min")
    if truncation_min_explicit is not None:
        truncation_min = truncation_min_explicit
    else:
        truncation_min = calculate_truncation_min_from_outlier_req(
            outlier_req=outlier_req,
            customer_sharing=customer_sharing,
            realization_time=realization_time,
            supervision_period=supervision_period
        )

    # controllable_method is set in M5 (5.4.1 Cost base application)
    controllable_method_str = m5.get("paverkbara_method", "OPEX")
    incentive = _build_incentive_config(ui_config)

    return PostDeaConfig(
        truncation_min=truncation_min,
        truncation_max=truncation_max,
        outlier_req=outlier_req,
        customer_sharing=customer_sharing,
        realization_time=realization_time,
        supervision_period=supervision_period,
        controllable_method=ControllableMethod(controllable_method_str),
        incentive=incentive
    )


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_baseline_value(param_id: str) -> Any:
    """Get baseline value for a parameter."""
    PARAM_BASELINE = {
        PID_WACC_REAL: BASELINE_WACC,
        PID_LOSS_SHARING: BASELINE_INCENTIVE["sharing_netloss"],
        "3.6.1": BASELINE_INCENTIVE["adj_max_agg"],
        PID_MAX_POTENTIAL_CAP: 0.30,
        PID_REALIZATION_TIME: 8,
        PID_CUSTOMER_SHARING: 0.50,
        PID_MIN_ANNUAL_REQ: 0.01,
    }
    return PARAM_BASELINE.get(param_id)


def get_changed_parameters(ui_config: Dict[str, Any]) -> List[str]:
    """Return list of changed parameters for UI display."""
    changed = []
    
    # Module 1: Asset base
    m1 = ui_config.get("m1_asset_base", {})
    if m1.get("kent_file_bytes"):
        changed.append("KENT file uploaded")
    if m1.get("general_scaling") and m1.get("general_scaling") != 1.0:
        changed.append(f"{PID_GENERAL_SCALING} General scaling: {m1['general_scaling']:.2f}")
    if m1.get("cat_scaling"):
        n = len(m1["cat_scaling"])
        changed.append(f"1.2.X Category scaling ({n} categories)")
    if m1.get("var_scaling"):
        n = len(m1["var_scaling"])
        changed.append(f"10.X Asset quantities ({n} categories)")
    
    # Module 2: Depreciation
    m2 = ui_config.get("m2_depreciation", {})
    if m2.get("lifetime_adjustments"):
        n = len(m2.get("lifetime_adjustments", {}))
        changed.append(f"2.X.X Lifetimes ({n} categories)")
    
    # Module 3: Cost of capital (WACC)
    m3 = ui_config.get("m3_cost_of_capital", {})
    if m3.get("wacc_override") is not None:
        changed.append(f"{PID_WACC_REAL} WACC")
    
    # Module 3: Quality adjustments
    m3q = ui_config.get("m3_quality_adjustments", {})
    if not _is_empty_or_none(m3q.get("kpi")):
        changed.append("3.7.X KPI factors")
    if not _is_empty_or_none(m3q.get("k_nf")):
        changed.append(f"{PID_LOSS_SCALING} Electricity price (K_NF)")
    if m3q.get("sharing_netloss") is not None:
        changed.append(f"{PID_LOSS_SHARING} Network loss sharing")
    if m3q.get("adj_max_agg") is not None:
        changed.append("3.6.1 Max aggregate incentive")
    if m3q.get("adj_max_cemi4") is not None:
        changed.append("3.3.X CEMI correction")
    if not m3q.get("enable_quality", True):
        changed.append("3.6.1 Quality incentive OFF")
    if not m3q.get("enable_netloss", True):
        changed.append("3.6.2 Network loss incentive OFF")
    if not m3q.get("enable_load", True):
        changed.append("3.6.3 Load incentive OFF")
    
    # Module 5: Efficiency
    m5 = ui_config.get("m5_efficiency", {})
    if m5.get("trunkering_max") is not None:
        changed.append(f"{PID_MAX_POTENTIAL_CAP} Truncation max")
    if m5.get("trunkering_min") is not None:
        changed.append("Truncation min (derived)")
    if m5.get("realiseringstid") is not None:
        changed.append(f"{PID_REALIZATION_TIME} Realization time")
    if m5.get("kunddelning") is not None:
        changed.append(f"{PID_CUSTOMER_SHARING} Customer sharing")
    if m5.get("outlier_krav") is not None:
        changed.append(f"{PID_MIN_ANNUAL_REQ} Outlier requirement")
    
    return changed


def get_source_method_summary(ui_config: Dict[str, Any]) -> Dict[str, str]:
    """Return summary of selected source and method."""
    m1 = ui_config.get("m1_asset_base", {})
    m2 = ui_config.get("m2_depreciation", {})
    m3 = ui_config.get("m3_cost_of_capital", {})
    
    # Source (for user's company)
    if m1.get("kent_file_bytes"):
        source = "KENT_UPLOAD"
        source_desc = f"KENT file: {m1.get('kent_file_name', 'unknown')}"
    elif m1.get("var_scaling"):
        source = "VAR_SCALED"
        n = len(m1["var_scaling"])
        source_desc = f"Variable scaling ({n} categories)"
    else:
        source = "BASELINE"
        source_desc = "Baseline capbase_a"
    
    # Method (for all companies)
    has_general = m1.get("general_scaling") and m1.get("general_scaling") != 1.0
    has_cat = m1.get("cat_scaling")
    has_lifetime = m2.get("lifetime_adjustments")
    has_wacc = m3.get("wacc_override") is not None
    
    has_any_change = has_general or has_cat or has_lifetime or has_wacc
    
    if has_any_change:
        method = "PARAMETER_CHANGE"
        parts = []
        if has_general:
            parts.append(f"general={m1['general_scaling']:.2f}")
        if has_cat:
            parts.append(f"{len(m1['cat_scaling'])} cat scaling")
        if has_lifetime:
            parts.append(f"{len(m2['lifetime_adjustments'])} lifetimes")
        if has_wacc:
            parts.append(f"WACC={m3['wacc_override']:.4f}")
        method_desc = "Parameter changes: " + ", ".join(parts)
    else:
        method = "BASELINE"
        method_desc = "No parameter changes"
    
    return {
        "source": source,
        "source_description": source_desc,
        "method": method,
        "method_description": method_desc,
    }
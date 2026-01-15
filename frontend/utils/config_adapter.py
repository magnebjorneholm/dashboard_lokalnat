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
    PaverkbaraMethod,
)


# =============================================================================
# BASELINE VALUES
# =============================================================================

BASELINE_WACC = 0.0453

BASELINE_INCENTIVE = {
    "kpi": {2024: 1.1546, 2025: 1.1546, 2026: 1.1546, 2027: 1.1546},
    "k_nf": {2024: 753.44, 2025: 753.44, 2026: 753.44, 2027: 753.44},
    "sharing_netloss": 0.75,
    "adj_max_agg": 1/3,
    "adj_max_cemi4": 0.25,
    "ait_costs": None,
    "aif_costs": None,
}

DEA_OUTPUT_OPTIONS = ['CU', 'MW', 'NS', 'MWhl', 'MWhh']
DEA_INPUT_OPTIONS = ['Kapitalkostnad_2024', 'OPEXp']

PARAM_TO_CONFIG = {
    "3.2.5": "m3_cost_of_capital.wacc_override",
    "5.2.1": "m5_efficiency.trunkering_max",
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
    
    user_id_network = _reid_to_id_network(user_reid)
    
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

def _reid_to_id_network(reid: str) -> int:
    """Convert REId to id_network. Ex: "REL00886" -> 886"""
    try:
        numeric_part = reid.replace("REL", "").lstrip("0")
        if not numeric_part:
            return 0
        return int(numeric_part)
    except (ValueError, AttributeError):
        raise ValueError(f"Could not convert REId to id_network: {reid}")


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
    1. PARAMETER_CHANGE (if normvalues/lifetimes changed)
    2. WACC_SCALING (if only WACC changed)
    3. BASELINE (no change)
    
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
    
    if has_parameter_changes:
        capex_method = CapexMethod.PARAMETER_CHANGE
    elif has_wacc_change:
        capex_method = CapexMethod.WACC_SCALING
    else:
        capex_method = CapexMethod.BASELINE
    
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
    )


def _combine_scaling_factors(
    general_scaling: Optional[float],
    cat_scaling: Optional[Dict[int, float]]
) -> Optional[Dict[int, float]]:
    """
    Combine general and category scaling factors into normvalue_adjustments.
    
    Logic:
    - If only general_scaling: apply to all 17 categories
    - If only cat_scaling: use as-is
    - If both: multiply general × category for each
    
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
    
    if addon.get("dea_method") == "custom":
        return DeaConfig(
            method=EfficiencyMethod.DEA,
            inputs=addon.get("dea_inputs", ["CAPEX", "OPEXp"]),
            outputs=addon.get("dea_outputs", DEA_OUTPUT_OPTIONS),
            rts=addon.get("dea_rts", "crs"),
            multiplier=addon.get("dea_multiplier", 2.0),
            q_lower=addon.get("dea_q_lower", 25.0),
            q_upper=addon.get("dea_q_upper", 75.0),
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


def calculate_trunkering_min_from_outlier_krav(
    outlier_krav: float,
    kunddelning: float,
    realiseringstid: int,
    tillsynsperiod: int
) -> float:
    """
    Calculate trunkering_min that gives same annual requirement as outlier_krav.
    
    This is the INVERSE calculation of the efficiency requirement formula.
    With baseline parameters (outlier_krav=1%) this gives trunkering_min ~ 16.24%
    """
    total_eff = (1 + outlier_krav) ** tillsynsperiod - 1
    realization_factor = tillsynsperiod / realiseringstid
    potential = total_eff / (kunddelning * realization_factor)
    return potential


def _build_post_dea_config(ui_config: Dict[str, Any]) -> PostDeaConfig:
    """Build PostDeaConfig from m4, m5, m3_quality_adjustments."""
    m5 = ui_config.get("m5_efficiency", {})
    m4 = ui_config.get("m4_operating_exp", {})
    
    trunkering_max = m5.get("trunkering_max") if m5.get("trunkering_max") is not None else 0.30
    outlier_krav = m5.get("outlier_krav") if m5.get("outlier_krav") is not None else 0.01
    realiseringstid = m5.get("realiseringstid") if m5.get("realiseringstid") is not None else 8
    kunddelning = m5.get("kunddelning") if m5.get("kunddelning") is not None else 0.50
    tillsynsperiod = m5.get("tillsynsperiod") if m5.get("tillsynsperiod") is not None else 4
    
    trunkering_min_explicit = m5.get("trunkering_min")
    if trunkering_min_explicit is not None:
        trunkering_min = trunkering_min_explicit
    else:
        trunkering_min = calculate_trunkering_min_from_outlier_krav(
            outlier_krav=outlier_krav,
            kunddelning=kunddelning,
            realiseringstid=realiseringstid,
            tillsynsperiod=tillsynsperiod
        )
    
    paverkbara_method_str = m4.get("paverkbara_method", "OPEX")
    incentive = _build_incentive_config(ui_config)
    
    return PostDeaConfig(
        trunkering_min=trunkering_min,
        trunkering_max=trunkering_max,
        outlier_krav=outlier_krav,
        kunddelning=kunddelning,
        realiseringstid=realiseringstid,
        tillsynsperiod=tillsynsperiod,
        paverkbara_method=PaverkbaraMethod(paverkbara_method_str),
        incentive=incentive
    )


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_baseline_value(param_id: str) -> Any:
    """Get baseline value for a parameter."""
    PARAM_BASELINE = {
        "3.2.5": BASELINE_WACC,
        "3.4.2": BASELINE_INCENTIVE["sharing_netloss"],
        "3.6.1": BASELINE_INCENTIVE["adj_max_agg"],
        "5.2.1": 0.30,
        "5.2.2": 8,
        "5.2.3": 0.50,
        "5.3.1": 0.01,
        "5.3.2": 0.162416,
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
        changed.append(f"1.1.1 General scaling: {m1['general_scaling']:.2f}")
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
        changed.append("3.2.5 WACC")
    
    # Module 3: Quality adjustments
    m3q = ui_config.get("m3_quality_adjustments", {})
    if not _is_empty_or_none(m3q.get("kpi")):
        changed.append("3.7.X KPI factors")
    if not _is_empty_or_none(m3q.get("k_nf")):
        changed.append("3.4.1 Electricity price (K_NF)")
    if m3q.get("sharing_netloss") is not None:
        changed.append("3.4.2 Network loss sharing")
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
        changed.append("5.2.1 Truncation max")
    if m5.get("trunkering_min") is not None:
        changed.append("5.3.2 Truncation min")
    if m5.get("realiseringstid") is not None:
        changed.append("5.2.2 Realization time")
    if m5.get("kunddelning") is not None:
        changed.append("5.2.3 Customer sharing")
    if m5.get("outlier_krav") is not None:
        changed.append("5.3.1 Outlier requirement")
    
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
    
    has_params = has_general or has_cat or has_lifetime
    
    if has_params:
        method = "PARAMETER_CHANGE"
        parts = []
        if has_general:
            parts.append(f"general={m1['general_scaling']:.2f}")
        if has_cat:
            parts.append(f"{len(m1['cat_scaling'])} cat scaling")
        if has_lifetime:
            parts.append(f"{len(m2['lifetime_adjustments'])} lifetimes")
        method_desc = "Parameter changes: " + ", ".join(parts)
    elif has_wacc:
        method = "WACC_SCALING"
        method_desc = f"WACC scaling: {m3['wacc_override']:.4f}"
    else:
        method = "BASELINE"
        method_desc = "No parameter changes"
    
    return {
        "source": source,
        "source_description": source_desc,
        "method": method,
        "method_description": method_desc,
    }
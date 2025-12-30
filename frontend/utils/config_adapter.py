"""
Config Adapter for Regumetrica UI.

Converts UI configuration to CaseDefinition for backend pipeline.
This is the sole bridge between frontend and backend.
"""

from typing import Dict, Any, List, Optional, Tuple

from config.case_definition import (
    CaseDefinition,
    PreDeaConfig,
    DeaConfig,
    PostDeaConfig,
    IncentiveConfig,
    CapexMethod,
    EfficiencyMethod,
    PaverkbaraMethod,
)

# Parameter-ID -> (config_section, attribute_name, baseline_value)
# Structure follows User Manual v1.0 (December 2025)
PARAM_TO_CONFIG = {
    # Module 1: Regulatory asset base valuation
    # 1.1.1: General scaling factor (baseline 1.00)
    # 1.2.1-1.2.17: Category-specific scaling factors (baseline 1.00)
    
    # Module 2: Depreciation
    # 2.X.1: Ordinary lifetime per category
    # 2.X.2: Tail lifetime per category
    
    # Module 3: Cost of capital
    "3.2.5": ("pre_dea", "wacc", 0.0453),  # WACC real pre-tax
    
    # Module 3: Quality adjustments (3.3-3.6)
    "3.3.1": ("incentive", "kpi", {2024: 1.1546, 2025: 1.1546, 2026: 1.1546, 2027: 1.1546}),
    "3.4.1": ("incentive", "k_nf", {2024: 753.44, 2025: 753.44, 2026: 753.44, 2027: 753.44}),
    "3.4.2": ("incentive", "sharing_netloss", 0.75),
    "3.5.1": ("incentive", "adj_max_agg", 1/3),
    "3.5.2": ("incentive", "adj_max_cemi4", 0.25),
    "3.6.1": ("incentive", "enable_quality", True),
    "3.6.2": ("incentive", "enable_netloss", True),
    "3.6.3": ("incentive", "enable_load", True),
    
    # Module 5: Efficiency incentive
    "5.1.1": ("dea", "multiplier", 2.0),              # Outlier threshold (IQR multiplier)
    "5.2.1": ("post_dea", "trunkering_max", 0.30),    # Maximum efficiency potential cap
    "5.2.2": ("post_dea", "realiseringstid", 8),      # Realization time (years)
    "5.2.3": ("post_dea", "kunddelning", 0.50),       # Customer sharing factor
    "5.2.4": ("post_dea", "tillsynsperiod", 4),       # Regulatory period length
    "5.3.1": ("post_dea", "outlier_krav", 0.01),      # Minimum annual requirement (outliers)
    
    # Module 4: Operating expenditures (via Module 5)
    "5.4.1": ("post_dea", "paverkbara_method", "OPEX"),  # OPEX or TOTEX
}

# DEA column names (consistent with backend)
DEA_INPUT_OPTIONS: List[str] = ["CAPEX", "OPEXp", "TOTEX"]
DEA_OUTPUT_OPTIONS: List[str] = ["CU", "MW", "NS", "MWhl", "MWhh"]

# Baseline values for incentive calculations
BASELINE_INCENTIVE = {
    "kpi": {2024: 1.1546, 2025: 1.1546, 2026: 1.1546, 2027: 1.1546},
    "k_nf": {2024: 753.44, 2025: 753.44, 2026: 753.44, 2027: 753.44},
    "sharing_netloss": 0.75,
    "adj_max_agg": 1/3,
    "adj_max_cemi4": 0.25,
    "ait_costs": {
        ('o', 1): 34.35, ('o', 2): 159.96, ('o', 3): 175.06,
        ('o', 4): 96.97, ('o', 5): 5.84, ('o', 6): 96.01,
        ('a', 1): 14.10, ('a', 2): 76.00, ('a', 3): 79.31,
        ('a', 4): 43.70, ('a', 5): 4.98, ('a', 6): 45.16,
    },
    "aif_costs": {
        ('o', 1): 9.78, ('o', 2): 70.75, ('o', 3): 17.78,
        ('o', 4): 7.65, ('o', 5): 1.95, ('o', 6): 22.18,
        ('a', 1): 1.72, ('a', 2): 20.71, ('a', 3): 5.94,
        ('a', 4): 0.92, ('a', 5): 1.85, ('a', 6): 7.08,
    },
}


def build_case_definition(user_reid: str, ui_config: Dict[str, Any]) -> CaseDefinition:
    """
    Convert UI configuration to CaseDefinition.
    
    Args:
        user_reid: User's REId
        ui_config: Dict from session_state["ui_config"]
    
    Returns:
        CaseDefinition ready for pipeline execution
    
    Raises:
        ValueError: If input is invalid
    """
    if not user_reid:
        raise ValueError("user_reid is missing")
    if not user_reid.startswith("REL"):
        raise ValueError(f"Invalid REId format: {user_reid}")
    
    # --- Pre-DEA ---
    pre_dea = _build_pre_dea_config(ui_config)
    
    # If KENT upload, set kent_user_id_network from REId
    if pre_dea.method == CapexMethod.KENT_UPLOAD:
        pre_dea.kent_user_id_network = _reid_to_id_network(user_reid)
    
    # --- DEA ---
    dea = _build_dea_config(ui_config)
    
    # --- Post-DEA (incl. incentives) ---
    post_dea = _build_post_dea_config(ui_config)
    
    return CaseDefinition(
        name="UI Case",
        user_reid=user_reid,
        pre_dea=pre_dea,
        dea=dea,
        post_dea=post_dea
    )


def _reid_to_id_network(reid: str) -> int:
    """
    Convert REId to id_network.
    
    Example: "REL00886" -> 886
    """
    try:
        numeric_part = reid.replace("REL", "").lstrip("0")
        if not numeric_part:
            return 0
        return int(numeric_part)
    except (ValueError, AttributeError):
        raise ValueError(f"Could not convert REId to id_network: {reid}")


def _build_pre_dea_config(ui_config: Dict[str, Any]) -> PreDeaConfig:
    """
    Build PreDeaConfig based on m1, m2, m3.
    
    Priority order:
    1. KENT_UPLOAD (if file uploaded)
    2. PARAMETER_CHANGE (if norm values/lifetimes modified)
    3. WACC_SCALING (if only WACC changed)
    4. BASELINE (no changes)
    """
    m1 = ui_config.get("m1_asset_base", {})
    m2 = ui_config.get("m2_depreciation", {})
    m3 = ui_config.get("m3_cost_of_capital", {})
    
    normvalue_adjustments = m1.get("normvalue_adjustments")
    lifetime_adjustments = m2.get("lifetime_adjustments")
    wacc_override = m3.get("wacc_override")
    kent_file_bytes = m1.get("kent_file_bytes")
    
    has_kent_upload = (kent_file_bytes is not None)
    has_parameter_changes = (normvalue_adjustments is not None or lifetime_adjustments is not None)
    has_wacc_change = (wacc_override is not None)
    
    if has_kent_upload:
        return PreDeaConfig(
            method=CapexMethod.KENT_UPLOAD,
            wacc=wacc_override if wacc_override else 0.0453,
            normvalue_adjustments=normvalue_adjustments,
            lifetime_adjustments=lifetime_adjustments,
            kent_file_bytes=kent_file_bytes,
            kent_user_id_network=None,  # Set in build_case_definition
        )
    elif has_parameter_changes:
        return PreDeaConfig(
            method=CapexMethod.PARAMETER_CHANGE,
            wacc=wacc_override if wacc_override else 0.0453,
            normvalue_adjustments=normvalue_adjustments,
            lifetime_adjustments=lifetime_adjustments,
        )
    elif has_wacc_change:
        return PreDeaConfig(
            method=CapexMethod.WACC_SCALING,
            wacc=wacc_override
        )
    else:
        return PreDeaConfig(method=CapexMethod.BASELINE)


def _build_dea_config(ui_config: Dict[str, Any]) -> DeaConfig:
    """Build DeaConfig based on addon_benchmarking."""
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


def _convert_incentive_keys(m3q: Dict[str, Any]) -> Dict[str, Any]:
    """Convert JSON-compatible keys to backend format."""
    result = {}
    
    # kpi/k_nf: string year -> int year
    for key in ['kpi', 'k_nf']:
        if m3q.get(key):
            result[key] = {int(k): v for k, v in m3q[key].items()}
    
    # ait_costs/aif_costs: "o_1" -> ('o', 1)
    for key in ['ait_costs', 'aif_costs']:
        if m3q.get(key):
            converted = {}
            for k, v in m3q[key].items():
                ann, sni = k.split('_')
                converted[(ann, int(sni))] = v
            result[key] = converted
    
    return result


def _build_incentive_config(ui_config: Dict[str, Any]) -> IncentiveConfig:
    """
    Build IncentiveConfig based on m3_quality_adjustments.
    
    Handles both simple values and Dict format (per year, per customer type).
    """
    m3q = ui_config.get("m3_quality_adjustments", {})
    converted = _convert_incentive_keys(m3q)
    
    # Get values - None means "use baseline"
    kpi = converted.get("kpi") or m3q.get("kpi")
    k_nf = converted.get("k_nf") or m3q.get("k_nf")
    sharing_netloss = m3q.get("sharing_netloss")
    adj_max_agg = m3q.get("adj_max_agg")
    adj_max_cemi4 = m3q.get("adj_max_cemi4")
    ait_costs = converted.get("ait_costs") or m3q.get("ait_costs")
    aif_costs = converted.get("aif_costs") or m3q.get("aif_costs")

    enable_quality = m3q.get("enable_quality", True)
    enable_netloss = m3q.get("enable_netloss", True)
    enable_load = m3q.get("enable_load", True)
    
    return IncentiveConfig(
        kpi=kpi if kpi is not None else BASELINE_INCENTIVE["kpi"],
        k_nf=k_nf if k_nf is not None else BASELINE_INCENTIVE["k_nf"],
        sharing_netloss=sharing_netloss if sharing_netloss is not None else BASELINE_INCENTIVE["sharing_netloss"],
        adj_max_agg=adj_max_agg if adj_max_agg is not None else BASELINE_INCENTIVE["adj_max_agg"],
        adj_max_cemi4=adj_max_cemi4 if adj_max_cemi4 is not None else BASELINE_INCENTIVE["adj_max_cemi4"],
        ait_costs=ait_costs if ait_costs is not None else BASELINE_INCENTIVE["ait_costs"],
        aif_costs=aif_costs if aif_costs is not None else BASELINE_INCENTIVE["aif_costs"],
        enable_quality=enable_quality,
        enable_netloss=enable_netloss,
        enable_load=enable_load,
    )


def _build_post_dea_config(ui_config: Dict[str, Any]) -> PostDeaConfig:
    """Build PostDeaConfig based on m4, m5, m3_quality_adjustments."""
    m5 = ui_config.get("m5_efficiency", {})
    m4 = ui_config.get("m4_operating_exp", {})
    
    # Efficiency requirement parameters
    trunkering_max = m5.get("trunkering_max")
    if trunkering_max is None:
        trunkering_max = 0.30
    
    trunkering_min = m5.get("trunkering_min")
    if trunkering_min is None:
        trunkering_min = 0.162416
        
    outlier_krav = m5.get("outlier_krav")
    if outlier_krav is None:
        outlier_krav = 0.01
    
    # Efficiency requirement conversion parameters
    kunddelning = m5.get("kunddelning")
    if kunddelning is None:
        kunddelning = 0.50
    
    realiseringstid = m5.get("realiseringstid")
    if realiseringstid is None:
        realiseringstid = 8
    
    tillsynsperiod = m5.get("tillsynsperiod")
    if tillsynsperiod is None:
        tillsynsperiod = 4
    
    # Operating expenditure method
    paverkbara_method_str = m4.get("paverkbara_method", "OPEX")
    
    # Build incentive config
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


def get_baseline_value(param_id: str) -> Any:
    """
    Get baseline value for a parameter.
    
    Args:
        param_id: Parameter-ID (e.g., "3.2.5")
        
    Returns:
        Baseline value or None if parameter not found
    """
    if param_id in PARAM_TO_CONFIG:
        return PARAM_TO_CONFIG[param_id][2]
    return None


def get_changed_parameters(ui_config: Dict[str, Any]) -> List[str]:
    """
    Return list of changed parameters.
    
    Args:
        ui_config: UI configuration
        
    Returns:
        List of Parameter-IDs that have been changed from baseline
    """
    changed = []
    
    # Module 1: Regulatory asset base valuation
    m1 = ui_config.get("m1_asset_base", {})
    if m1.get("kent_file_bytes"):
        changed.append("KENT file uploaded")
    if m1.get("normvalue_adjustments"):
        n = len(m1.get("normvalue_adjustments", {}))
        level = m1.get("normvalue_level", "cat")
        changed.append(f"1.2.X Scaling factors ({n} {level})")
    
    # Module 2: Depreciation
    m2 = ui_config.get("m2_depreciation", {})
    if m2.get("lifetime_adjustments"):
        n = len(m2.get("lifetime_adjustments", {}))
        level = m2.get("lifetime_level", "cat")
        changed.append(f"2.X.X Lifetimes ({n} {level})")
    
    # Module 3: Cost of capital (WACC)
    m3 = ui_config.get("m3_cost_of_capital", {})
    if m3.get("wacc_override") is not None:
        changed.append("3.2.5 WACC")
    
    # Module 3: Quality adjustments (incentives)
    m3q = ui_config.get("m3_quality_adjustments", {})
    if m3q.get("kpi") is not None:
        changed.append("3.3.X Quality KPI factors")
    if m3q.get("k_nf") is not None:
        changed.append("3.4.1 Network loss price (K_NF)")
    if m3q.get("sharing_netloss") is not None:
        changed.append("3.4.2 Network loss sharing")
    if m3q.get("adj_max_agg") is not None:
        changed.append("3.5.1 Max aggregate adjustment")
    if m3q.get("adj_max_cemi4") is not None:
        changed.append("3.5.2 CEMI4 adjustment")
    if m3q.get("ait_costs") is not None:
        changed.append("3.3.X AIT costs")
    if m3q.get("aif_costs") is not None:
        changed.append("3.3.X AIF costs")
    if not m3q.get("enable_quality", True):
        changed.append("3.6.1 Quality incentive OFF")
    if not m3q.get("enable_netloss", True):
        changed.append("3.6.2 Network loss adjustment OFF")
    if not m3q.get("enable_load", True):
        changed.append("3.6.3 Utilization rate adjustment OFF")
    
    # Module 5: Efficiency incentive
    m5 = ui_config.get("m5_efficiency", {})
    if m5.get("trunkering_max") is not None:
        changed.append("5.2.1 Max efficiency potential")
    if m5.get("trunkering_min") is not None:
        changed.append("5.2.1 Min efficiency potential")
    if m5.get("realiseringstid") is not None:
        changed.append("5.2.2 Realization time")
    if m5.get("kunddelning") is not None:
        changed.append("5.2.3 Customer sharing factor")
    if m5.get("tillsynsperiod") is not None:
        changed.append("5.2.4 Regulatory period length")
    if m5.get("outlier_krav") is not None:
        changed.append("5.3.1 Outlier minimum requirement")
    
    # Module 4: Operating expenditures
    m4 = ui_config.get("m4_operating_exp", {})
    if m4.get("paverkbara_method", "OPEX") != "OPEX":
        changed.append("5.4.1 TOTEX method")
    
    # Add-on: Benchmarking
    addon = ui_config.get("addon_benchmarking", {})
    if addon.get("dea_method") == "custom":
        changed.append("Custom DEA specification")
    
    return changed
"""
Config Adapter for Regumetrica UI.

Converts UI configuration to CaseDefinition for backend pipeline.
This is the only bridge between frontend and backend.
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
from calculations.effektiviseringskrav import calculate_trunkering_min_from_outlier_krav

# Parameter-ID -> (config_section, attribute_name, baseline_value)
# Mapping according to User Manual Table 13
PARAM_TO_CONFIG = {
    # Module 3: Cost of capital (WACC)
    "3.2.5": ("pre_dea", "wacc", 0.0453),
    
    # Module 3: Quality adjustments (3.3-3.6)
    "3.3.1": ("incentive", "kpi", {2024: 1.1546, 2025: 1.1546, 2026: 1.1546, 2027: 1.1546}),
    "3.4.1": ("incentive", "k_nf", {2024: 753.44, 2025: 753.44, 2026: 753.44, 2027: 753.44}),
    "3.4.2": ("incentive", "sharing_netloss", 0.75),
    "3.5.1": ("incentive", "adj_max_agg", 1/3),
    "3.5.2": ("incentive", "adj_max_cemi4", 0.25),
    "3.6.1": ("incentive", "enable_quality", True),
    "3.6.2": ("incentive", "enable_netloss", True),
    "3.6.3": ("incentive", "enable_load", True),
    
    # Module 5: Efficiency incentive (per UM Table 13)
    "5.1.1": ("dea", "multiplier", 2.0),              # Outlier IQR threshold
    "5.2.1": ("post_dea", "trunkering_max", 0.30),    # Maximum efficiency potential cap
    "5.2.2": ("post_dea", "realiseringstid", 8),      # Realization time (years)
    "5.2.3": ("post_dea", "kunddelning", 0.50),       # Customer sharing factor
    "5.3.1": ("post_dea", "outlier_krav", 0.01),      # Minimum annual efficiency requirement
    
    # Module 4: Operating expenditures (via Module 5)
    "5.4.1": ("post_dea", "paverkbara_method", "OPEX"),  # OPEX or TOTEX
}

# Column names for DEA (consistent with backend)
DEA_INPUT_OPTIONS: List[str] = ["CAPEX", "OPEXp", "TOTEX"]
DEA_OUTPUT_OPTIONS: List[str] = ["CU", "MW", "NS", "MWhl", "MWhh"]

# Baseline values for incentives (not imported to avoid circular import)
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
        user_reid: User's REId (e.g., "REL00001")
        ui_config: Complete UI configuration from session_state
        
    Returns:
        CaseDefinition ready for pipeline execution
    """
    pre_dea = _build_pre_dea_config(ui_config)
    
    # If KENT upload, set user's id_network
    if pre_dea.method == CapexMethod.KENT_UPLOAD:
        pre_dea = PreDeaConfig(
            method=pre_dea.method,
            wacc=pre_dea.wacc,
            normvalue_adjustments=pre_dea.normvalue_adjustments,
            lifetime_adjustments=pre_dea.lifetime_adjustments,
            kent_file_bytes=pre_dea.kent_file_bytes,
            kent_user_id_network=_get_id_network_from_reid(user_reid),
        )
    
    dea = _build_dea_config(ui_config)
    post_dea = _build_post_dea_config(ui_config)
    
    return CaseDefinition(
        name=_generate_case_name(ui_config),
        user_reid=user_reid,
        pre_dea=pre_dea,
        dea=dea,
        post_dea=post_dea,
    )


def get_baseline_value(param_id: str) -> Any:
    """
    Get baseline value for a parameter.
    
    Args:
        param_id: Parameter ID (e.g., "3.2.5")
        
    Returns:
        Baseline value or None if parameter not found
    """
    if param_id in PARAM_TO_CONFIG:
        return PARAM_TO_CONFIG[param_id][2]
    return None


def get_changed_parameters(ui_config: Dict[str, Any]) -> List[str]:
    """
    Returns list of modified parameters.
    
    Args:
        ui_config: UI configuration
        
    Returns:
        List of Parameter IDs that have been changed from baseline
    """
    changed = []
    
    # Module 1: Asset base
    m1 = ui_config.get("m1_asset_base", {})
    if m1.get("kent_file_bytes"):
        changed.append("KENT file uploaded")
    if m1.get("normvalue_adjustments"):
        n = len(m1.get("normvalue_adjustments", {}))
        level = m1.get("normvalue_level", "cat")
        changed.append(f"1.X.X Norm values ({n} {level})")
    
    # Module 2: Depreciation
    m2 = ui_config.get("m2_depreciation", {})
    if m2.get("lifetime_adjustments"):
        n = len(m2.get("lifetime_adjustments", {}))
        level = m2.get("lifetime_level", "cat")
        changed.append(f"2.X.X Asset lifetimes ({n} {level})")
    
    # Module 3: Cost of capital (WACC)
    m3 = ui_config.get("m3_cost_of_capital", {})
    if m3.get("wacc_override") is not None:
        changed.append("3.2.5 WACC")
    
    # Module 3: Quality adjustments (incentives)
    m3q = ui_config.get("m3_quality_adjustments", {})
    if m3q.get("kpi") is not None:
        changed.append("3.7.X KPI factors")
    if m3q.get("k_nf") is not None:
        changed.append("3.4.1 Electricity price (K_NF)")
    if m3q.get("sharing_netloss") is not None:
        changed.append("3.4.2 Net loss sharing")
    if m3q.get("adj_max_agg") is not None:
        changed.append("3.6.1 Max aggregate incentive")
    if m3q.get("adj_max_cemi4") is not None:
        changed.append("3.3.X CEMI adjustment")
    if m3q.get("ait_costs") is not None:
        changed.append("3.3.X AIT costs")
    if m3q.get("aif_costs") is not None:
        changed.append("3.3.X AIF costs")
    if not m3q.get("enable_quality", True):
        changed.append("3.6.1 Quality incentive OFF")
    if not m3q.get("enable_netloss", True):
        changed.append("3.6.2 Net loss incentive OFF")
    if not m3q.get("enable_load", True):
        changed.append("3.6.3 Load incentive OFF")
    
    # Module 3: Incentive variables
    m3v = ui_config.get("m3_incentive_variables", {})
    if m3v:
        overrides = {k: v for k, v in m3v.items() if v is not None and v != "NULL"}
        if overrides:
            changed.append(f"3.X.X Incentive variables ({len(overrides)})")
    
    # Module 4: Operating expenditures
    m4 = ui_config.get("m4_operating_exp", {})
    if m4.get("paverkbara_method") and m4.get("paverkbara_method") != "OPEX":
        changed.append("5.4.1 Adjustable costs method")
    
    # Module 5: Efficiency
    m5 = ui_config.get("m5_efficiency", {})
    if m5.get("trunkering_max") is not None:
        changed.append("5.2.1 Truncation max")
    if m5.get("outlier_krav") is not None:
        changed.append("5.3.1 Outlier requirement")
    if m5.get("realiseringstid") is not None:
        changed.append("5.2.2 Realization time")
    if m5.get("kunddelning") is not None:
        changed.append("5.2.3 Customer sharing")
    
    # Add-on: Benchmarking (DEA)
    addon = ui_config.get("addon_benchmarking", {})
    if addon.get("dea_method") == "custom":
        changed.append("DEA: Custom model")
    
    return changed


def _build_pre_dea_config(ui_config: Dict[str, Any]) -> PreDeaConfig:
    """
    Build PreDeaConfig based on m1, m2, m3.
    
    Priority order:
    1. KENT upload (if file uploaded)
    2. PARAMETER_CHANGE (if norm values/lifetimes changed)
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
    
    # Determine method based on what changed
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
            kent_user_id_network=None,
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


def _build_post_dea_config(ui_config: Dict[str, Any]) -> PostDeaConfig:
    """
    Build PostDeaConfig based on m4, m5, m3_quality_adjustments.
    
    Note: trunkering_min is calculated automatically from outlier_krav to ensure
    that non-outliers with low potential get the same minimum requirement.
    """
    m5 = ui_config.get("m5_efficiency", {})
    m4 = ui_config.get("m4_operating_exp", {})
    
    # Truncation max (5.2.1)
    trunkering_max = m5.get("trunkering_max")
    if trunkering_max is None:
        trunkering_max = 0.30
    
    # Minimum annual requirement (5.3.1)
    outlier_krav = m5.get("outlier_krav")
    if outlier_krav is None:
        outlier_krav = 0.01
    
    # Realization time (5.2.2)
    realiseringstid = m5.get("realiseringstid")
    if realiseringstid is None:
        realiseringstid = 8
    
    # Customer sharing factor (5.2.3)
    kunddelning = m5.get("kunddelning")
    if kunddelning is None:
        kunddelning = 0.50
    
    # Regulatory period (fixed for 2024-2027)
    tillsynsperiod = m5.get("tillsynsperiod")
    if tillsynsperiod is None:
        tillsynsperiod = 4
    
    # Calculate trunkering_min automatically from outlier_krav
    trunkering_min = calculate_trunkering_min_from_outlier_krav(
        outlier_krav=outlier_krav,
        kunddelning=kunddelning,
        realiseringstid=realiseringstid,
        tillsynsperiod=tillsynsperiod
    )
    
    # Adjustable costs method (5.4.1)
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


def _convert_incentive_keys(m3q: Dict[str, Any]) -> Dict[str, Any]:
    """Converts JSON-compatible keys to backend format."""
    converted = {}
    
    # Convert kpi from {"2024": 1.15, ...} to {2024: 1.15, ...}
    if "kpi" in m3q and isinstance(m3q["kpi"], dict):
        converted["kpi"] = {int(k): v for k, v in m3q["kpi"].items()}
    
    # Convert k_nf similarly
    if "k_nf" in m3q and isinstance(m3q["k_nf"], dict):
        converted["k_nf"] = {int(k): v for k, v in m3q["k_nf"].items()}
    
    # Convert ait_costs from {"o_1": 34.35, ...} to {('o', 1): 34.35, ...}
    if "ait_costs" in m3q and isinstance(m3q["ait_costs"], dict):
        converted["ait_costs"] = {}
        for k, v in m3q["ait_costs"].items():
            parts = k.split("_")
            if len(parts) == 2:
                converted["ait_costs"][(parts[0], int(parts[1]))] = v
    
    # Convert aif_costs similarly
    if "aif_costs" in m3q and isinstance(m3q["aif_costs"], dict):
        converted["aif_costs"] = {}
        for k, v in m3q["aif_costs"].items():
            parts = k.split("_")
            if len(parts) == 2:
                converted["aif_costs"][(parts[0], int(parts[1]))] = v
    
    return converted


def _build_incentive_config(ui_config: Dict[str, Any]) -> IncentiveConfig:
    """
    Build IncentiveConfig based on m3_quality_adjustments.
    
    Handles both simple values and Dict format (per year, per customer type).
    Includes variable_overrides from m3_incentive_variables.
    """
    m3q = ui_config.get("m3_quality_adjustments", {})
    m3v = ui_config.get("m3_incentive_variables", {})

    # Convert JSON keys to backend format
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
    
    # Get variable_overrides from m3_incentive_variables
    # Filter out None values and "NULL" strings (= use baseline)
    variable_overrides = None
    if m3v:
        overrides = {
            k: v for k, v in m3v.items() 
            if v is not None and v != "NULL" and v != "null"
        }
        if overrides:
            variable_overrides = overrides
    
    # Build config - use baseline if None
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
        variable_overrides=variable_overrides,
    )


def _generate_case_name(ui_config: Dict[str, Any]) -> str:
    """Generate descriptive case name based on configuration."""
    changed = get_changed_parameters(ui_config)
    if not changed:
        return "Baseline"
    elif len(changed) == 1:
        return changed[0]
    else:
        return f"Custom ({len(changed)} changes)"


def _get_id_network_from_reid(user_reid: str) -> Optional[int]:
    """
    Get id_network from REId using reconciliation table.
    
    Args:
        user_reid: User's REId (e.g., "REL00001")
        
    Returns:
        id_network or None if not found
    """
    try:
        import pandas as pd
        from pathlib import Path
        
        recon_path = Path("data/reconciliation_id_network_firm_dmu.csv")
        if not recon_path.exists():
            return None
        
        df = pd.read_csv(recon_path)
        match = df[df["REId"] == user_reid]
        if not match.empty:
            return int(match.iloc[0]["id_network"])
    except Exception:
        pass
    
    return None
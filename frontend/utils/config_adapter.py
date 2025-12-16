"""
Config Adapter för Regumetrica UI.

Konverterar UI-konfiguration till CaseDefinition för backend-pipeline.
Detta är den enda bryggan mellan frontend och backend.
"""

from typing import Dict, Any, List, Optional

from config.case_definition import (
    CaseDefinition,
    PreDeaConfig,
    DeaConfig,
    PostDeaConfig,
    CapexMethod,
    EfficiencyMethod,
    PaverkbaraMethod,
)

# Parameter-ID -> (config_section, attribute_name, baseline_value)
PARAM_TO_CONFIG = {
    # Module 3: Cost of capital
    "3.2.5": ("pre_dea", "wacc", 0.0453),
    
    # Module 5: Efficiency incentive
    "5.1.1": ("dea", "multiplier", 2.0),              # Outlier IQR threshold
    "5.2.1": ("post_dea", "trunkering_max", 0.30),    # Max potential cap
    "5.2.2": ("post_dea", "trunkering_min", 0.162416),# Min potential for trunkering
    "5.2.3": ("post_dea", "realiseringstid", 8),      # Ar for full effektivisering
    "5.2.4": ("post_dea", "kunddelning", 0.50),       # Andel till kunder
    "5.2.5": ("post_dea", "tillsynsperiod", 4),       # Langd pa tillsynsperiod
    "5.3.1": ("post_dea", "outlier_krav", 0.01),      # Min arligt krav for outliers
    
    # Module 4: Operating expenditures (via Module 5)
    "5.4.1": ("post_dea", "paverkbara_method", "OPEX"),  # OPEX eller TOTEX
}

# Kolumnnamn för DEA (konsekvent med backend)
DEA_INPUT_OPTIONS: List[str] = ["CAPEX", "OPEXp", "TOTEX"]
DEA_OUTPUT_OPTIONS: List[str] = ["CU", "MW", "NS", "MWhl", "MWhh"]


def build_case_definition(user_reid: str, ui_config: Dict[str, Any]) -> CaseDefinition:
    """
    Konvertera UI-konfiguration till CaseDefinition.
    
    Args:
        user_reid: Anvandarens REId
        ui_config: Dict fran session_state["ui_config"]
    
    Returns:
        CaseDefinition redo for pipeline
    
    Raises:
        ValueError: Om input ar ogiltig
    """
    # Validera REId
    if not user_reid:
        raise ValueError("user_reid saknas")
    if not user_reid.startswith("REL"):
        raise ValueError(f"Ogiltigt REId-format: {user_reid}")
    
    # --- Pre-DEA ---
    pre_dea = _build_pre_dea_config(ui_config)
    
    # --- DEA ---
    dea = _build_dea_config(ui_config)
    
    # --- Post-DEA ---
    post_dea = _build_post_dea_config(ui_config)
    
    return CaseDefinition(
        name="UI Case",
        user_reid=user_reid,
        pre_dea=pre_dea,
        dea=dea,
        post_dea=post_dea
    )


def _build_pre_dea_config(ui_config: Dict[str, Any]) -> PreDeaConfig:
    """
    Bygg PreDeaConfig baserat pa m1, m2, m3.
    
    Logik:
    - Om normvarden eller livslangder andras -> PARAMETER_CHANGE
    - Om endast WACC andras -> WACC_SCALING
    - Annars -> BASELINE
    """
    m1 = ui_config.get("m1_asset_base", {})
    m2 = ui_config.get("m2_depreciation", {})
    m3 = ui_config.get("m3_cost_of_capital", {})
    
    normvalue_adjustments = m1.get("normvalue_adjustments")
    lifetime_adjustments = m2.get("lifetime_adjustments")
    wacc_override = m3.get("wacc_override")
    
    # Bestam metod baserat pa vad som andrats
    has_parameter_changes = (normvalue_adjustments is not None or lifetime_adjustments is not None)
    has_wacc_change = (wacc_override is not None)
    
    if has_parameter_changes:
        # Normvarden eller livslangder andrades -> kor full KENT-berakning
        return PreDeaConfig(
            method=CapexMethod.PARAMETER_CHANGE,
            wacc=wacc_override if wacc_override else 0.0453,
            normvalue_adjustments=normvalue_adjustments,
            lifetime_adjustments=lifetime_adjustments,
        )
    elif has_wacc_change:
        # Endast WACC andrad -> skala befintlig CAPEX
        return PreDeaConfig(
            method=CapexMethod.WACC_SCALING,
            wacc=wacc_override
        )
    else:
        # Ingen andring -> anvand baseline
        return PreDeaConfig(method=CapexMethod.BASELINE)


def _build_dea_config(ui_config: Dict[str, Any]) -> DeaConfig:
    """Bygg DeaConfig baserat pa addon_benchmarking."""
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
    """Bygg PostDeaConfig baserat pa m4, m5."""
    m5 = ui_config.get("m5_efficiency", {})
    m4 = ui_config.get("m4_operating_exp", {})
    
    # Trunkering
    trunkering_max = m5.get("trunkering_max")
    if trunkering_max is None:
        trunkering_max = 0.30
    
    trunkering_min = m5.get("trunkering_min")
    if trunkering_min is None:
        trunkering_min = 0.162416
        
    outlier_krav = m5.get("outlier_krav")
    if outlier_krav is None:
        outlier_krav = 0.01
    
    # Nya parametrar for effektiviseringskrav-omrakning
    kunddelning = m5.get("kunddelning")
    if kunddelning is None:
        kunddelning = 0.50
    
    realiseringstid = m5.get("realiseringstid")
    if realiseringstid is None:
        realiseringstid = 8
    
    tillsynsperiod = m5.get("tillsynsperiod")
    if tillsynsperiod is None:
        tillsynsperiod = 4
    
    # Paverkbara metod
    paverkbara_method_str = m4.get("paverkbara_method", "OPEX")
    
    return PostDeaConfig(
        trunkering_min=trunkering_min,
        trunkering_max=trunkering_max,
        outlier_krav=outlier_krav,
        kunddelning=kunddelning,
        realiseringstid=realiseringstid,
        tillsynsperiod=tillsynsperiod,
        paverkbara_method=PaverkbaraMethod(paverkbara_method_str)
    )


def get_baseline_value(param_id: str) -> Any:
    """
    Hamta baseline-varde for en parameter.
    
    Args:
        param_id: Parameter-ID (t.ex. "3.2.5")
        
    Returns:
        Baseline-varde eller None om parameter inte finns
    """
    if param_id in PARAM_TO_CONFIG:
        return PARAM_TO_CONFIG[param_id][2]
    return None


def get_changed_parameters(ui_config: Dict[str, Any]) -> List[str]:
    """
    Returnerar lista med andrade parametrar.
    
    Args:
        ui_config: UI-konfiguration
        
    Returns:
        Lista med Parameter-ID som har andrats fran baseline
    """
    changed = []
    
    # Module 1: Asset base
    m1 = ui_config.get("m1_asset_base", {})
    if m1.get("normvalue_adjustments"):
        n = len(m1.get("normvalue_adjustments", {}))
        level = m1.get("normvalue_level", "cat")
        changed.append(f"1.X.X Normvarden ({n} {level})")
    
    # Module 2: Depreciation
    m2 = ui_config.get("m2_depreciation", {})
    if m2.get("lifetime_adjustments"):
        n = len(m2.get("lifetime_adjustments", {}))
        level = m2.get("lifetime_level", "cat")
        changed.append(f"2.X.X Livslangder ({n} {level})")
    
    # Module 3: Cost of capital
    m3 = ui_config.get("m3_cost_of_capital", {})
    if m3.get("wacc_override") is not None:
        changed.append("3.2.5 WACC")
    
    # Module 5: Efficiency
    m5 = ui_config.get("m5_efficiency", {})
    if m5.get("trunkering_max") is not None:
        changed.append("5.2.1 Max potential")
    if m5.get("trunkering_min") is not None:
        changed.append("5.2.2 Min potential")
    if m5.get("realiseringstid") is not None:
        changed.append("5.2.3 Realiseringstid")
    if m5.get("kunddelning") is not None:
        changed.append("5.2.4 Kunddelning")
    if m5.get("tillsynsperiod") is not None:
        changed.append("5.2.5 Tillsynsperiod")
    if m5.get("outlier_krav") is not None:
        changed.append("5.3.1 Outlier-krav")
    
    # Module 4: Operating expenditures
    m4 = ui_config.get("m4_operating_exp", {})
    if m4.get("paverkbara_method", "OPEX") != "OPEX":
        changed.append("5.4.1 TOTEX-metod")
    
    # Add-on: Benchmarking
    addon = ui_config.get("addon_benchmarking", {})
    if addon.get("dea_method") == "custom":
        changed.append("Custom DEA")
    
    return changed
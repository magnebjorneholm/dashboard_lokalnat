"""
Config Adapter för Regumetrica UI.

Konverterar UI-konfiguration till CaseDefinition för backend-pipeline.
Detta är den enda bryggan mellan frontend och backend.
"""

from typing import Dict, Any, List

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
    "5.1.1": ("dea", "multiplier", 2.0),           # Outlier IQR threshold
    "5.2.1": ("post_dea", "trunkering_max", 0.30), # Max potential cap
    "5.3.1": ("post_dea", "outlier_krav", 0.01),   # Min årligt krav för outliers
    
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
        user_reid: Användarens REId
        ui_config: Dict från session_state["ui_config"]
    
    Returns:
        CaseDefinition redo för pipeline
    
    Raises:
        ValueError: Om input är ogiltig
    """
    # Validera REId
    if not user_reid:
        raise ValueError("user_reid saknas")
    if not user_reid.startswith("REL"):
        raise ValueError(f"Ogiltigt REId-format: {user_reid}")
    
    # --- Pre-DEA ---
    m3 = ui_config.get("m3_cost_of_capital", {})
    
    wacc_override = m3.get("wacc_override")
    if wacc_override is not None:
        pre_dea = PreDeaConfig(
            method=CapexMethod.WACC_SCALING,
            wacc=wacc_override
        )
    else:
        pre_dea = PreDeaConfig(method=CapexMethod.BASELINE)
    
    # --- DEA ---
    addon = ui_config.get("addon_benchmarking", {})
    
    if addon.get("dea_method") == "custom":
        dea = DeaConfig(
            method=EfficiencyMethod.DEA,
            inputs=addon.get("dea_inputs", ["CAPEX", "OPEXp"]),
            outputs=addon.get("dea_outputs", DEA_OUTPUT_OPTIONS),
            rts=addon.get("dea_rts", "crs"),
            multiplier=addon.get("dea_multiplier", 2.0),
        )
    else:
        dea = DeaConfig(method=EfficiencyMethod.BASELINE)
    
    # --- Post-DEA ---
    m5 = ui_config.get("m5_efficiency", {})
    m4 = ui_config.get("m4_operating_exp", {})
    
    # Använd None-safe defaults
    trunkering_max = m5.get("trunkering_max")
    if trunkering_max is None:
        trunkering_max = 0.30
        
    outlier_krav = m5.get("outlier_krav")
    if outlier_krav is None:
        outlier_krav = 0.01
    
    paverkbara_method_str = m4.get("paverkbara_method", "OPEX")
    
    post_dea = PostDeaConfig(
        trunkering_max=trunkering_max,
        outlier_krav=outlier_krav,
        paverkbara_method=PaverkbaraMethod(paverkbara_method_str)
    )
    
    return CaseDefinition(
        name="UI Case",
        user_reid=user_reid,
        pre_dea=pre_dea,
        dea=dea,
        post_dea=post_dea
    )


def get_baseline_value(param_id: str) -> Any:
    """
    Hämta baseline-värde för en parameter.
    
    Args:
        param_id: Parameter-ID (t.ex. "3.2.5")
        
    Returns:
        Baseline-värde eller None om parameter inte finns
    """
    if param_id in PARAM_TO_CONFIG:
        return PARAM_TO_CONFIG[param_id][2]
    return None


def get_changed_parameters(ui_config: Dict[str, Any]) -> List[str]:
    """
    Returnerar lista med ändrade parametrar.
    
    Args:
        ui_config: UI-konfiguration
        
    Returns:
        Lista med Parameter-ID som har ändrats från baseline
    """
    changed = []
    
    # Module 3
    m3 = ui_config.get("m3_cost_of_capital", {})
    if m3.get("wacc_override") is not None:
        changed.append("3.2.5 WACC")
    
    # Module 5
    m5 = ui_config.get("m5_efficiency", {})
    if m5.get("trunkering_max") is not None:
        changed.append("5.2.1 Max potential")
    if m5.get("outlier_krav") is not None:
        changed.append("5.3.1 Outlier-krav")
    
    # Module 4
    m4 = ui_config.get("m4_operating_exp", {})
    if m4.get("paverkbara_method", "OPEX") != "OPEX":
        changed.append("5.4.1 TOTEX-metod")
    
    # Add-on: Benchmarking
    addon = ui_config.get("addon_benchmarking", {})
    if addon.get("dea_method") == "custom":
        changed.append("Custom DEA")
    
    return changed

"""
frontend/utils/config_adapter.py

Config Adapter för Regumetrica UI.

Konverterar UI-konfiguration till CaseDefinition för backend-pipeline.
Detta är den enda bryggan mellan frontend och backend.

REFAKTORISERAD: Hanterar CapbaseSource och CapexMethod som separata dimensioner.
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
    "ait_costs": None,  # Använd default från incentive_data
    "aif_costs": None,
}

DEA_OUTPUT_OPTIONS = ['CU', 'MW', 'NS', 'MWhl', 'MWhh']

# Typiska DEA-input options (används av UI/exports)
DEA_INPUT_OPTIONS = ['Kapitalkostnad_2024', 'OPEXp']


# Mappning av parameter-ID eller UI-nyckel till config-path (placeholder)
# Håller namn som frontend.utils.__init__ förväntar sig. Kan utökas vid behov.
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
    Bygger CaseDefinition från UI-konfiguration.
    
    Konverterar session_state["ui_config"] till typad CaseDefinition
    som kan skickas till pipeline.
    
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
    
    # Hämta user_id_network för KENT-upload
    user_id_network = _reid_to_id_network(user_reid)
    
    # --- Pre-DEA ---
    pre_dea = _build_pre_dea_config(ui_config, user_id_network)
    
    # --- DEA ---
    dea = _build_dea_config(ui_config)
    
    # --- Post-DEA (inkl. incitament) ---
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
    """
    Konverterar REId till id_network.
    
    Ex: "REL00886" -> 886
    """
    try:
        numeric_part = reid.replace("REL", "").lstrip("0")
        if not numeric_part:
            return 0
        return int(numeric_part)
    except (ValueError, AttributeError):
        raise ValueError(f"Kunde inte konvertera REId till id_network: {reid}")


def _build_pre_dea_config(
    ui_config: Dict[str, Any],
    user_id_network: int
) -> PreDeaConfig:
    """
    Bygger PreDeaConfig med separation av source och method.
    
    PRIORITERING FÖR SOURCE (dataförsörjning):
    1. KENT_UPLOAD (om fil uppladdad) - högst prioritet
    2. RAB_MODIFIED (om RAB-editor har ändringar)
    3. BASELINE (ingen ändring)
    
    PRIORITERING FÖR METHOD (beräkningsmetod):
    1. PARAMETER_CHANGE (om normvärden/livslängder ändrats)
    2. WACC_SCALING (om endast WACC ändrats)
    3. BASELINE (ingen ändring)
    
    Source och method är oberoende dimensioner.
    """
    m1 = ui_config.get("m1_asset_base", {})
    m2 = ui_config.get("m2_depreciation", {})
    m3 = ui_config.get("m3_cost_of_capital", {})
    
    # === Bestäm CAPBASE SOURCE ===
    kent_file_bytes = m1.get("kent_file_bytes")
    rab_has_changes = m1.get("rab_has_changes", False)
    
    if kent_file_bytes is not None:
        # KENT har högst prioritet
        capbase_source = CapbaseSource.KENT_UPLOAD
        rab_user_capbase = None
    elif rab_has_changes:
        # RAB-editor har ändringar
        capbase_source = CapbaseSource.RAB_MODIFIED
        rab_user_capbase = _get_rab_capbase(user_id_network)
    else:
        capbase_source = CapbaseSource.BASELINE
        rab_user_capbase = None
    
    # === Bestäm CAPEX METHOD ===
    normvalue_adjustments = m1.get("normvalue_adjustments")
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
    
    # === Bygg config ===
    return PreDeaConfig(
        # Source
        capbase_source=capbase_source,
        rab_user_capbase=rab_user_capbase,
        kent_file_bytes=kent_file_bytes if capbase_source == CapbaseSource.KENT_UPLOAD else None,
        kent_user_id_network=user_id_network if capbase_source == CapbaseSource.KENT_UPLOAD else None,
        
        # Method
        method=capex_method,
        wacc=wacc_override,  # None = använd baseline
        normvalue_adjustments=normvalue_adjustments,
        lifetime_adjustments=lifetime_adjustments,
    )


def _get_rab_capbase(user_id_network: int) -> Optional[pd.DataFrame]:
    """
    Hämtar RAB-editor capbase från session state.
    
    Anropas endast om rab_has_changes=True, så vi förväntar oss
    att rab_editor finns i session state.
    
    Returns:
        DataFrame i capbase_a format eller None om något gick fel
    """
    try:
        from calculations.rab_editor_utils import get_user_capbase_with_edits
        return get_user_capbase_with_edits()
    except ImportError:
        print("VARNING: rab_editor_utils kunde inte importeras")
        return None
    except Exception as e:
        print(f"VARNING: Kunde inte hämta RAB-capbase: {e}")
        return None


def _build_dea_config(ui_config: Dict[str, Any]) -> DeaConfig:
    """Bygger DeaConfig baserat på addon_benchmarking."""
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
    """
    Kontrollerar om ett värde är None eller en tom container.
    
    Hanterar edge cases där UI kan skicka tomma dicts/lists istället för None.
    """
    if value is None:
        return True
    if isinstance(value, (dict, list)) and len(value) == 0:
        return True
    return False


def _build_incentive_config(ui_config: Dict[str, Any]) -> IncentiveConfig:
    """
    Bygger IncentiveConfig baserat på m3_quality_adjustments.
    
    FIX: Hanterar tomma dicts som None för korrekt baseline-fallback.
    """
    m3q = ui_config.get("m3_quality_adjustments", {})
    m3v = ui_config.get("m3_incentive_variables", {})
    
    # Konvertera JSON-nycklar till backend-format
    converted = _convert_incentive_keys(m3q)
    
    # Hämta värden - None ELLER tom dict betyder "använd baseline"
    # FIX: Använd _is_empty_or_none() för robust kontroll
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
    
    # Hämta variable_overrides från m3_incentive_variables
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
        ait_costs=ait_costs,  # None = använd default från incentive_data
        aif_costs=aif_costs,
        enable_quality=enable_quality,
        enable_netloss=enable_netloss,
        enable_load=enable_load,
        variable_overrides=variable_overrides,
    )


def _convert_incentive_keys(m3q: Dict[str, Any]) -> Dict[str, Any]:
    """
    Konverterar JSON-nycklar till backend-format.
    
    Hanterar:
    - kpi: {"2024": 1.0} -> {2024: 1.0}
    - k_nf: {"2024": 753.44} -> {2024: 753.44}
    - ait_costs: {"o_1": 34.35} -> {("o", 1): 34.35}
    - aif_costs: {"a_1": 14.10} -> {("a", 1): 14.10}
    """
    converted: Dict[str, Any] = {}
    
    # Konvertera kpi (år som strängar -> int)
    if "kpi" in m3q and m3q["kpi"]:
        converted["kpi"] = {int(k): v for k, v in m3q["kpi"].items()}
    
    # Konvertera k_nf (år som strängar -> int)
    if "k_nf" in m3q and m3q["k_nf"]:
        converted["k_nf"] = {int(k): v for k, v in m3q["k_nf"].items()}
    
    # Konvertera ait_costs ("o_1" -> ("o", 1))
    if "ait_costs" in m3q and m3q["ait_costs"]:
        converted["ait_costs"] = {}
        for key, value in m3q["ait_costs"].items():
            parts = key.split("_")
            if len(parts) == 2:
                ann, sni = parts[0], int(parts[1])
                converted["ait_costs"][(ann, sni)] = value
    
    # Konvertera aif_costs
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
    Beräknar trunkering_min som ger samma årskrav som outlier_krav.
    
    Detta är den OMVÄNDA beräkningen av effektiviseringskravsformeln:
        årskrav = (1 + potential × kunddelning × T_p/T_r)^(1/T_p) - 1
    
    Löser ut potential:
        total_eff = (1 + årskrav)^T_p - 1
        potential = total_eff / (kunddelning × T_p/T_r)
    
    Med baseline-parametrar (outlier_krav=1%) ger detta trunkering_min ≈ 16.24%
    
    Args:
        outlier_krav: Fast årligt krav för outliers (default 1%)
        kunddelning: Andel av effektivisering som tillfaller kunder (default 50%)
        realiseringstid: Antal år för att uppnå full effektivisering (default 8)
        tillsynsperiod: Längd på tillsynsperiod i år (default 4)
        
    Returns:
        trunkering_min (potential) som ger samma årskrav som outlier_krav
    """
    # Beräkna total effektivisering som krävs för att ge outlier_krav
    total_eff = (1 + outlier_krav) ** tillsynsperiod - 1
    
    # Lös ut potential från: total_eff = potential × kunddelning × (T_p/T_r)
    realization_factor = tillsynsperiod / realiseringstid
    potential = total_eff / (kunddelning * realization_factor)
    
    return potential


def _build_post_dea_config(ui_config: Dict[str, Any]) -> PostDeaConfig:
    """
    Bygger PostDeaConfig baserat på m4, m5, m3_quality_adjustments.
    
    trunkering_min beräknas alltid från formeln (som nu är korrekt).
    Med baseline-parametrar ger detta 16.24%.
    """
    m5 = ui_config.get("m5_efficiency", {})
    m4 = ui_config.get("m4_operating_exp", {})
    
    # Hämta värden med baseline-fallback
    trunkering_max = m5.get("trunkering_max") if m5.get("trunkering_max") is not None else 0.30
    outlier_krav = m5.get("outlier_krav") if m5.get("outlier_krav") is not None else 0.01
    realiseringstid = m5.get("realiseringstid") if m5.get("realiseringstid") is not None else 8
    kunddelning = m5.get("kunddelning") if m5.get("kunddelning") is not None else 0.50
    tillsynsperiod = m5.get("tillsynsperiod") if m5.get("tillsynsperiod") is not None else 4
    
    # Beräkna trunkering_min från formeln (eller använd explicit värde om satt)
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
    
    # Påverkbara metod (5.4.1)
    paverkbara_method_str = m4.get("paverkbara_method", "OPEX")
    
    # Bygg incitament-config
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
    """
    Hämta baseline-värde för en parameter.
    
    Args:
        param_id: Parameter-ID (t.ex. "3.2.5")
        
    Returns:
        Baseline-värde eller None om parameter inte finns
    """
    # Mappning av Parameter-ID till baseline-värden
    PARAM_BASELINE = {
        "3.2.5": BASELINE_WACC,
        "3.4.2": BASELINE_INCENTIVE["sharing_netloss"],
        "3.6.1": BASELINE_INCENTIVE["adj_max_agg"],
        "5.2.1": 0.30,  # trunkering_max
        "5.2.2": 8,     # realiseringstid
        "5.2.3": 0.50,  # kunddelning
        "5.3.1": 0.01,  # outlier_krav
        "5.3.2": 0.162416,  # trunkering_min (beräknat från baseline-parametrar)
    }
    return PARAM_BASELINE.get(param_id)


def get_changed_parameters(ui_config: Dict[str, Any]) -> List[str]:
    """
    Returnerar lista med ändrade parametrar för visning i UI.
    
    Args:
        ui_config: UI-konfiguration
        
    Returns:
        Lista med beskrivningar av ändrade parametrar
    """
    changed = []
    
    # Module 1: Asset base
    m1 = ui_config.get("m1_asset_base", {})
    if m1.get("kent_file_bytes"):
        changed.append("KENT-fil uppladdad")
    if m1.get("rab_has_changes"):
        changed.append("RAB-editor ändringar")
    if m1.get("normvalue_adjustments"):
        n = len(m1.get("normvalue_adjustments", {}))
        level = m1.get("normvalue_level", "cat")
        changed.append(f"1.X.X Normvärden ({n} {level})")
    
    # Module 2: Depreciation
    m2 = ui_config.get("m2_depreciation", {})
    if m2.get("lifetime_adjustments"):
        n = len(m2.get("lifetime_adjustments", {}))
        level = m2.get("lifetime_level", "cat")
        changed.append(f"2.X.X Livslängder ({n} {level})")
    
    # Module 3: Cost of capital (WACC)
    m3 = ui_config.get("m3_cost_of_capital", {})
    if m3.get("wacc_override") is not None:
        changed.append("3.2.5 WACC")
    
    # Module 3: Quality adjustments (incitament)
    m3q = ui_config.get("m3_quality_adjustments", {})
    if not _is_empty_or_none(m3q.get("kpi")):
        changed.append("3.7.X KPI-faktorer")
    if not _is_empty_or_none(m3q.get("k_nf")):
        changed.append("3.4.1 Elpris (K_NF)")
    if m3q.get("sharing_netloss") is not None:
        changed.append("3.4.2 Delning nätförlust")
    if m3q.get("adj_max_agg") is not None:
        changed.append("3.6.1 Max aggregerat incitament")
    if m3q.get("adj_max_cemi4") is not None:
        changed.append("3.3.X CEMI-korrigering")
    if not m3q.get("enable_quality", True):
        changed.append("3.6.1 Kvalitetsincitament AV")
    if not m3q.get("enable_netloss", True):
        changed.append("3.6.2 Nätförlustincitament AV")
    if not m3q.get("enable_load", True):
        changed.append("3.6.3 Belastningsincitament AV")
    
    # Module 5: Efficiency
    m5 = ui_config.get("m5_efficiency", {})
    if m5.get("trunkering_max") is not None:
        changed.append("5.2.1 Trunkering max")
    if m5.get("trunkering_min") is not None:
        changed.append("5.3.2 Trunkering min")
    if m5.get("realiseringstid") is not None:
        changed.append("5.2.2 Realiseringstid")
    if m5.get("kunddelning") is not None:
        changed.append("5.2.3 Kunddelning")
    if m5.get("outlier_krav") is not None:
        changed.append("5.3.1 Outlier-krav")
    
    return changed


def get_source_method_summary(ui_config: Dict[str, Any]) -> Dict[str, str]:
    """
    Returnerar sammanfattning av vald source och method.
    
    Användbart för debugging och UI-visning.
    """
    m1 = ui_config.get("m1_asset_base", {})
    m2 = ui_config.get("m2_depreciation", {})
    m3 = ui_config.get("m3_cost_of_capital", {})
    
    # Source
    if m1.get("kent_file_bytes"):
        source = "KENT_UPLOAD"
        source_desc = f"KENT-fil: {m1.get('kent_file_name', 'okänd')}"
    elif m1.get("rab_has_changes"):
        source = "RAB_MODIFIED"
        source_desc = "RAB-editor ändringar"
    else:
        source = "BASELINE"
        source_desc = "Baseline capbase_a"
    
    # Method
    has_params = m1.get("normvalue_adjustments") or m2.get("lifetime_adjustments")
    has_wacc = m3.get("wacc_override") is not None
    
    if has_params:
        method = "PARAMETER_CHANGE"
        parts = []
        if m1.get("normvalue_adjustments"):
            parts.append(f"{len(m1['normvalue_adjustments'])} normvärden")
        if m2.get("lifetime_adjustments"):
            parts.append(f"{len(m2['lifetime_adjustments'])} livslängder")
        method_desc = "Parameter-ändringar: " + ", ".join(parts)
    elif has_wacc:
        method = "WACC_SCALING"
        method_desc = f"WACC-skalning: {m3['wacc_override']:.4f}"
    else:
        method = "BASELINE"
        method_desc = "Ingen parameterändring"
    
    return {
        "source": source,
        "source_description": source_desc,
        "method": method,
        "method_description": method_desc,
    }
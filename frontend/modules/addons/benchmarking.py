"""
Add-on Module: Benchmarking

Hanterar DEA-konfiguration och framtida SFA/StoNED.
Ny DEA körs endast om konfigurationen skiljer sig från baseline.
"""

import streamlit as st
from typing import Dict, Any, List

from frontend.common.parameter_input import parameter_input
from frontend.common.formulas import (
    get_formula_with_caption,
    FORMULA_DEA_LP,
    FORMULA_DEA_COMPACT,
    FORMULA_DEA_VRS_CONSTRAINT,
    FORMULA_OUTLIER_THRESHOLD,
    FORMULA_EFFICIENCY_POTENTIAL,
)

MODULE_KEY = "addon_benchmarking"

# DEA-alternativ
DEA_INPUT_OPTIONS: List[str] = ["CAPEX", "OPEXp", "TOTEX"]
DEA_OUTPUT_OPTIONS: List[str] = ["CU", "MW", "NS", "MWhl", "MWhh"]

# Baseline-konfiguration (Ei's specifikation)
BASELINE_INPUTS = ["CAPEX", "OPEXp"]
BASELINE_OUTPUTS = ["CU", "MW", "NS", "MWhl", "MWhh"]
BASELINE_RTS = "crs"
BASELINE_MULTIPLIER = 2.0
BASELINE_Q_LOWER = 25.0
BASELINE_Q_UPPER = 75.0


def is_baseline_dea_config(config: Dict[str, Any]) -> bool:
    """
    Kontrollerar om DEA-konfigurationen matchar Ei's baseline.
    
    Args:
        config: DEA-konfiguration från UI
        
    Returns:
        True om config matchar baseline (ingen ny DEA behövs)
    """
    return (
        set(config.get("dea_inputs", [])) == set(BASELINE_INPUTS) and
        set(config.get("dea_outputs", [])) == set(BASELINE_OUTPUTS) and
        config.get("dea_rts", "crs") == BASELINE_RTS and
        abs(config.get("dea_multiplier", 2.0) - BASELINE_MULTIPLIER) < 0.001 and
        abs(config.get("dea_q_lower", 25.0) - BASELINE_Q_LOWER) < 0.001 and
        abs(config.get("dea_q_upper", 75.0) - BASELINE_Q_UPPER) < 0.001
    )


def render() -> Dict[str, Any]:
    """
    Renderar Add-on: Benchmarking module.
    
    DEA-konfiguration visas alltid. Om config skiljer sig från baseline
    körs ny DEA vid beräkning, annars används cachade resultat.
    
    Returns:
        Dict med användarens val. Keys:
        - dea_method: "baseline" eller "custom" (baserat på config-jämförelse)
        - dea_inputs: Lista med inputs
        - dea_outputs: Lista med outputs
        - dea_rts: "crs" eller "vrs"
        - dea_multiplier: Outlier IQR multiplier
        - dea_q_lower: Nedre percentil
        - dea_q_upper: Övre percentil
    """
    # Initiera config med baseline-värden
    config: Dict[str, Any] = {
        "dea_inputs": BASELINE_INPUTS.copy(),
        "dea_outputs": BASELINE_OUTPUTS.copy(),
        "dea_rts": BASELINE_RTS,
        "dea_multiplier": BASELINE_MULTIPLIER,
        "dea_q_lower": BASELINE_Q_LOWER,
        "dea_q_upper": BASELINE_Q_UPPER,
    }
    
    st.subheader("Add-on: Benchmarking")
    
    # === METODVAL ===
    st.markdown("##### Effektivitetsanalys")
    
    method = st.radio(
        "Metod",
        options=["DEA", "SFA (kommande)", "StoNED (kommande)"],
        index=0,
        key=f"{MODULE_KEY}_method",
        horizontal=True,
        help="DEA = Data Envelopment Analysis"
    )
    
    if method != "DEA":
        st.info(f"{method} kommer i framtida version.")
        config["dea_method"] = "baseline"
        return config
    
    # === DEA-KONFIGURATION ===
    with st.expander("DEA-konfiguration", expanded=True):
        
        # === BERÄKNINGSFORMLER ===
        st.markdown("**DEA-optimering (input-oriented)**")
        
        # Kompakt formel för snabb överblick
        formula_compact, caption_compact = get_formula_with_caption("DEA")
        st.latex(formula_compact)
        st.caption(caption_compact)
        
        # Fullständig LP-formulering i en sub-expander
        with st.expander("Visa fullständig LP-formulering", expanded=False):
            st.markdown("**Super-efficiency DEA** (exkluderar DMU i från referensmängden)")
            formula_lp, caption_lp = get_formula_with_caption("DEA_SUPER")
            st.latex(formula_lp)
            st.caption(caption_lp)
            
            st.markdown("**VRS-constraint** (om variabel skalavkastning)")
            st.latex(FORMULA_DEA_VRS_CONSTRAINT)
            st.caption("Läggs till vid VRS för att tillåta variabel skalavkastning")
            
            st.markdown("**Effektiviseringspotential**")
            st.latex(FORMULA_EFFICIENCY_POTENTIAL)
            st.caption("Potential = 1 - θ, där θ är effektivitetsscoren")
        
        st.divider()
        
        # --- Inputs ---
        st.markdown("**Inputs (kostnader)**")
        selected_inputs = st.multiselect(
            "Välj inputs",
            options=DEA_INPUT_OPTIONS,
            default=BASELINE_INPUTS,
            key=f"{MODULE_KEY}_inputs",
            help="CAPEX = kapitalkostnad, OPEXp = justerad OPEX, TOTEX = CAPEX + OPEXp"
        )
        
        if not selected_inputs:
            st.error("Minst en input krävs")
            selected_inputs = BASELINE_INPUTS
        
        config["dea_inputs"] = selected_inputs
        
        st.divider()
        
        # --- Outputs ---
        st.markdown("**Outputs (leverans)**")
        selected_outputs = st.multiselect(
            "Välj outputs",
            options=DEA_OUTPUT_OPTIONS,
            default=BASELINE_OUTPUTS,
            key=f"{MODULE_KEY}_outputs",
            help="CU=Abonnemang, MW=Pmax, NS=Nätstationer, MWhl=ELS, MWhh=EHS"
        )
        
        if not selected_outputs:
            st.error("Minst en output krävs")
            selected_outputs = BASELINE_OUTPUTS
        
        config["dea_outputs"] = selected_outputs
        
        st.divider()
        
        # --- Returns to scale ---
        st.markdown("**Skalavkastning**")
        rts = st.radio(
            "Returns to scale",
            options=["crs", "vrs"],
            index=0 if BASELINE_RTS == "crs" else 1,
            key=f"{MODULE_KEY}_rts",
            horizontal=True,
            help="CRS = Constant (default), VRS = Variable"
        )
        config["dea_rts"] = rts
        
        st.divider()
        
        # --- Outlier-detektion ---
        st.markdown("**Outlier-detektion (IQR-metod)**")
        
        # Visa outlier-formel
        st.latex(FORMULA_OUTLIER_THRESHOLD)
        st.caption("Företag med supereffektivitet över tröskeln klassas som outliers")
        
        col1, col2 = st.columns(2)
        with col1:
            q_lower = st.number_input(
                "Nedre percentil",
                value=BASELINE_Q_LOWER,
                min_value=0.0,
                max_value=50.0,
                step=5.0,
                key=f"{MODULE_KEY}_q_lower",
                help="Nedre gräns för IQR-beräkning (default: 25)"
            )
            config["dea_q_lower"] = q_lower
        
        with col2:
            q_upper = st.number_input(
                "Övre percentil",
                value=BASELINE_Q_UPPER,
                min_value=50.0,
                max_value=100.0,
                step=5.0,
                key=f"{MODULE_KEY}_q_upper",
                help="Övre gräns för IQR-beräkning (default: 75)"
            )
            config["dea_q_upper"] = q_upper
        
        multiplier = st.number_input(
            "IQR-multiplikator (5.1.1)",
            value=BASELINE_MULTIPLIER,
            min_value=1.0,
            max_value=5.0,
            step=0.5,
            key=f"{MODULE_KEY}_multiplier",
            help="Företag med supereffektivitet > Q_upper + multiplier*IQR klassas som outliers"
        )
        config["dea_multiplier"] = multiplier
        
        st.divider()
        
        # === STATUS: Baseline eller Custom ===
        is_baseline = is_baseline_dea_config(config)
        
        if is_baseline:
            config["dea_method"] = "baseline"
            st.success(
                "**Baseline-konfiguration**\n\n"
                "Matchar Ei's specifikation. Befintliga DEA-resultat används."
            )
        else:
            config["dea_method"] = "custom"
            
            # Visa vad som skiljer sig
            differences = []
            if set(config["dea_inputs"]) != set(BASELINE_INPUTS):
                differences.append(f"Inputs: {config['dea_inputs']} (baseline: {BASELINE_INPUTS})")
            if set(config["dea_outputs"]) != set(BASELINE_OUTPUTS):
                differences.append(f"Outputs: {config['dea_outputs']} (baseline: {BASELINE_OUTPUTS})")
            if config["dea_rts"] != BASELINE_RTS:
                differences.append(f"RTS: {config['dea_rts']} (baseline: {BASELINE_RTS})")
            if abs(config["dea_multiplier"] - BASELINE_MULTIPLIER) > 0.001:
                differences.append(f"Multiplier: {config['dea_multiplier']} (baseline: {BASELINE_MULTIPLIER})")
            if abs(config["dea_q_lower"] - BASELINE_Q_LOWER) > 0.001:
                differences.append(f"Q_lower: {config['dea_q_lower']} (baseline: {BASELINE_Q_LOWER})")
            if abs(config["dea_q_upper"] - BASELINE_Q_UPPER) > 0.001:
                differences.append(f"Q_upper: {config['dea_q_upper']} (baseline: {BASELINE_Q_UPPER})")
            
            st.warning(
                "**Custom konfiguration**\n\n"
                "Skiljer sig från baseline. Ny DEA körs vid beräkning.\n\n"
                "Ändringar:\n- " + "\n- ".join(differences)
            )
        
        # === SAMMANFATTNING ===
        st.divider()
        st.markdown("**Sammanfattning**")
        st.code(f"""Inputs:  {', '.join(config['dea_inputs'])}
Outputs: {', '.join(config['dea_outputs'])}
RTS:     {config['dea_rts'].upper()}
Outlier: Q{config['dea_q_lower']:.0f}-Q{config['dea_q_upper']:.0f}, multiplier={config['dea_multiplier']:.1f}""")
    
    return config
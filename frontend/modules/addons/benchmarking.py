"""
Add-on Module: Benchmarking

Hanterar DEA-konfiguration och framtida SFA/StoNED.
"""

import streamlit as st
from typing import Dict, Any, List

from frontend.common.parameter_input import parameter_input

MODULE_KEY = "addon_benchmarking"

# DEA-alternativ
DEA_INPUT_OPTIONS: List[str] = ["CAPEX", "OPEXp", "TOTEX"]
DEA_OUTPUT_OPTIONS: List[str] = ["CU", "MW", "NS", "MWhl", "MWhh"]

# Baseline
BASELINE_INPUTS = ["CAPEX", "OPEXp"]
BASELINE_OUTPUTS = ["CU", "MW", "NS", "MWhl", "MWhh"]
BASELINE_RTS = "crs"
BASELINE_MULTIPLIER = 2.0


def render() -> Dict[str, Any]:
    """
    Renderar Add-on: Benchmarking module.
    
    Returns:
        Dict med användarens val. Keys:
        - dea_method: "baseline" eller "custom"
        - dea_inputs: Lista med inputs
        - dea_outputs: Lista med outputs
        - dea_rts: "crs" eller "vrs"
        - dea_multiplier: Outlier IQR multiplier
    """
    config: Dict[str, Any] = {
        "dea_method": "baseline",
        "dea_inputs": BASELINE_INPUTS.copy(),
        "dea_outputs": BASELINE_OUTPUTS.copy(),
        "dea_rts": BASELINE_RTS,
        "dea_multiplier": BASELINE_MULTIPLIER,
    }
    
    st.subheader("Add-on: Benchmarking")
    
    # Metodval
    st.markdown("##### Effektivitetsanalys")
    
    use_custom = st.checkbox(
        "Använd custom DEA",
        value=False,
        key=f"{MODULE_KEY}_use_custom",
        help="Kryssa i för att konfigurera egen DEA-modell"
    )
    
    if use_custom:
        config["dea_method"] = "custom"
        
        with st.expander("DEA-konfiguration", expanded=True):
            
            # Inputs
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
            
            # Outputs
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
            
            # Returns to scale
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
            
            # Outlier threshold (5.1.1)
            st.markdown("**Outlier-detektion**")
            multiplier, mult_changed = parameter_input(
                module_key=MODULE_KEY,
                param_id="5.1.1",
                label="Outlier-tröskel (IQR)",
                baseline=BASELINE_MULTIPLIER,
                min_val=1.0,
                max_val=5.0,
                step=0.5,
                help_text="Företag med supereffektivitet > Q3 + multiplier*IQR klassas som outliers"
            )
            config["dea_multiplier"] = multiplier
            
            # Sammanfattning
            st.divider()
            st.markdown("**Sammanfattning**")
            st.code(f"""
Inputs:  {', '.join(config['dea_inputs'])}
Outputs: {', '.join(config['dea_outputs'])}
RTS:     {config['dea_rts'].upper()}
Outlier: Q3 + {config['dea_multiplier']:.1f} * IQR
            """)
    
    else:
        st.info(
            "Använder Ei's baseline DEA-resultat.\n\n"
            "Baseline-specifikation:\n"
            f"- Inputs: {', '.join(BASELINE_INPUTS)}\n"
            f"- Outputs: {', '.join(BASELINE_OUTPUTS)}\n"
            f"- RTS: {BASELINE_RTS.upper()}\n"
            f"- Outlier: Q3 + {BASELINE_MULTIPLIER} * IQR"
        )
    
    # Framtida metoder
    with st.expander("Framtida metoder", expanded=False):
        st.info(
            "Alternativa effektivitetsmetoder kommer i framtida version:\n"
            "- SFA (Stochastic Frontier Analysis)\n"
            "- StoNED (Stochastic Nonparametric Envelopment of Data)"
        )
    
    return config

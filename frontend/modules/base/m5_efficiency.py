"""
Module 5: Efficiency Incentive

Hanterar effektiviseringskrav-parametrar.
Parameter-IDs: 5.1.X - 5.4.X
Variable-IDs: 50.X
"""

import streamlit as st
from typing import Dict, Any

from frontend.common.parameter_input import parameter_input

MODULE_KEY = "m5_efficiency"

# Baseline-värden från Ei's metod för tillsynsperiod 2024-2027
BASELINE_OUTLIER_THRESHOLD = 2.0
BASELINE_MAX_POTENTIAL = 0.30
BASELINE_MIN_POTENTIAL = 0.162416
BASELINE_REALIZATION_TIME = 8
BASELINE_CUSTOMER_SHARING = 0.50
BASELINE_SUPERVISION_PERIOD = 4
BASELINE_MIN_REQUIREMENT = 0.01


def render() -> Dict[str, Any]:
    """
    Renderar Module 5: Efficiency incentive.
    
    Returns:
        Dict med användarens val. Keys:
        - trunkering_max: Max potential cap eller None
        - trunkering_min: Min potential för trunkering eller None
        - outlier_krav: Min årligt krav för outliers eller None
        - kunddelning: Andel som tillfaller kunder eller None
        - realiseringstid: År för full effektivisering eller None
        - tillsynsperiod: Längd på tillsynsperiod eller None
    """
    config: Dict[str, Any] = {}
    
    st.subheader("5. Efficiency Incentive")
    
    with st.expander("Parameters", expanded=True):
        st.markdown("##### 5.1 Outlier identification")
        
        # 5.1.1 Outlier threshold - hanteras i DEA add-on
        st.caption("Outlier threshold (5.1.1) konfigureras i Add-on: Benchmarking")
        
        st.divider()
        
        st.markdown("##### 5.2 Efficiency requirement conversion")
        
        # 5.2.1 Max potential cap
        max_pot, max_pot_changed = parameter_input(
            module_key=MODULE_KEY,
            param_id="5.2.1",
            label="Max effektiviseringspotential",
            baseline=BASELINE_MAX_POTENTIAL,
            min_val=0.0,
            max_val=1.0,
            step=0.01,
            help_text="Effektivitetspotential trunkeras vid detta tak.",
            format_as_percent=True
        )
        
        if max_pot_changed:
            config["trunkering_max"] = max_pot
        
        # 5.2.2 Realization time (enligt UM)
        real_time, real_time_changed = parameter_input(
            module_key=MODULE_KEY,
            param_id="5.2.2",
            label="Realiseringstid",
            baseline=float(BASELINE_REALIZATION_TIME),
            min_val=1.0,
            max_val=20.0,
            step=1.0,
            help_text="Antal år för att uppnå full effektivisering.",
            format_as_percent=False
        )
        
        if real_time_changed:
            config["realiseringstid"] = int(real_time)
        
        # 5.2.3 Customer sharing factor
        kund_del, kund_del_changed = parameter_input(
            module_key=MODULE_KEY,
            param_id="5.2.3",
            label="Kunddelning",
            baseline=BASELINE_CUSTOMER_SHARING,
            min_val=0.0,
            max_val=1.0,
            step=0.05,
            help_text="Andel av effektivisering som tillfaller kunder (resten till företaget).",
            format_as_percent=True
        )
        
        if kund_del_changed:
            config["kunddelning"] = kund_del
        
        st.divider()
        
        st.markdown("##### 5.3 Efficiency requirement bounds")
        
        # 5.3.1 Minimum annual requirement
        min_req, min_req_changed = parameter_input(
            module_key=MODULE_KEY,
            param_id="5.3.1",
            label="Minimum årligt effkrav",
            baseline=BASELINE_MIN_REQUIREMENT,
            min_val=0.0,
            max_val=0.10,
            step=0.001,
            help_text="Fast årligt krav som tillämpas på outliers.",
            format_as_percent=True
        )
        
        if min_req_changed:
            config["outlier_krav"] = min_req
        
        # Visa beräknat max årligt krav baserat på nuvarande parametrar
        st.divider()
        st.markdown("##### Beräknat max årligt effkrav")
        
        # Hämta aktuella värden (eller defaults)
        current_max = config.get("trunkering_max", BASELINE_MAX_POTENTIAL)
        current_kund = config.get("kunddelning", BASELINE_CUSTOMER_SHARING)
        current_real = config.get("realiseringstid", BASELINE_REALIZATION_TIME)
        current_tills = BASELINE_SUPERVISION_PERIOD  # Hårdkodat i denna version
        
        # Beräkna max årligt krav
        total_eff = current_max * current_kund * (current_tills / current_real)
        max_yearly = (1 + total_eff) ** (1 / current_tills) - 1
        
        st.metric(
            label="Max årligt effektiviseringskrav",
            value=f"{max_yearly*100:.2f}%",
            delta=f"{(max_yearly - 0.0182)*100:+.2f}pp vs baseline" if abs(max_yearly - 0.0182) > 0.0001 else None
        )
        st.caption("Beräknat från: trunkering_max * kunddelning * (tillsynsperiod / realiseringstid)")
    
    return config
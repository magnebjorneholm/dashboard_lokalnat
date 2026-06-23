"""
Module 5: Efficiency Incentive

Handles efficiency requirement parameters.
Parameter-IDs: 5.1.X - 5.4.X
Variable-IDs: 50.X

Section-based rendering:
- render_efficiency_params() -> 5.X Efficiency parameters
"""

import streamlit as st
from typing import Dict, Any

from frontend.common.parameter_input import parameter_input, parameter_select
from calculations.efficiency.efficiency_requirement import get_max_eff_req
from frontend.utils.state_manager import get_config_value
from config.glossary import (
    PID_OUTLIER_THRESHOLD, PID_MAX_POTENTIAL_CAP, PID_REALIZATION_TIME,
    PID_CUSTOMER_SHARING, PID_MIN_ANNUAL_REQ, PID_COST_BASE,
)

MODULE_KEY = "m5_efficiency"

# Baseline values from Ei methodology for regulatory period 2024-2027
BASELINE_MAX_POTENTIAL = 0.30
BASELINE_REALIZATION_TIME = 8
BASELINE_CUSTOMER_SHARING = 0.50
BASELINE_SUPERVISION_PERIOD = 4
BASELINE_MIN_REQUIREMENT = 0.01

# Fixed minimum for potential cap (16%) - provides margin for parameter changes
MIN_POTENTIAL_CAP = 0.17


def render_efficiency_params() -> Dict[str, Any]:
    """
    Render M5 efficiency parameters section: 5.X parameters.
    
    Returns:
        Dict with efficiency parameter overrides:
        - trunkering_max: Max potential cap
        - outlier_krav: Min annual requirement for outliers
        - kunddelning: Share allocated to customers
        - realiseringstid: Years for full efficiency realization
        - paverkbara_method: "OPEX" or "TOTEX"
    """
    config: Dict[str, Any] = {}
    
    st.markdown("##### 5.1 Outlier identification")
    st.caption(f"Outlier threshold ({PID_OUTLIER_THRESHOLD}): configured in the Benchmarking section above")
    
    st.divider()
    
    st.markdown("##### 5.2 Efficiency requirement conversion")
    
    # 5.2.1 Max potential cap (fixed min_val for stability)
    max_pot, max_pot_changed = parameter_input(
        module_key=MODULE_KEY,
        param_id=PID_MAX_POTENTIAL_CAP,
        label="Maximum efficiency potential cap",
        baseline=BASELINE_MAX_POTENTIAL,
        value=get_config_value(MODULE_KEY, "trunkering_max", BASELINE_MAX_POTENTIAL),
        min_val=MIN_POTENTIAL_CAP,
        max_val=1.0,
        step=0.01,
        help_text="Upper bound on assessed efficiency potential",
        format_as_percent=True
    )
    
    if max_pot_changed:
        config["trunkering_max"] = max_pot
    
    # 5.2.2 Realization time
    real_time, real_time_changed = parameter_input(
        module_key=MODULE_KEY,
        param_id=PID_REALIZATION_TIME,
        label="Realization time",
        baseline=float(BASELINE_REALIZATION_TIME),
        value=get_config_value(MODULE_KEY, "realiseringstid", float(BASELINE_REALIZATION_TIME)),
        min_val=1.0,
        max_val=20.0,
        step=1.0,
        unit="years",
        help_text="Time horizon for full efficiency realization",
        format_as_percent=False
    )
    
    if real_time_changed:
        config["realiseringstid"] = int(real_time)
    
    # 5.2.3 Customer sharing factor
    kund_del, kund_del_changed = parameter_input(
        module_key=MODULE_KEY,
        param_id=PID_CUSTOMER_SHARING,
        label="Customer sharing factor",
        baseline=BASELINE_CUSTOMER_SHARING,
        value=get_config_value(MODULE_KEY, "kunddelning", BASELINE_CUSTOMER_SHARING),
        min_val=0.01,
        max_val=1.0,
        step=0.05,
        help_text="Share of efficiency gains allocated to customers",
        format_as_percent=True
    )
    
    if kund_del_changed:
        config["kunddelning"] = kund_del
    
    st.divider()
    
    st.markdown("##### 5.3 Efficiency requirement bounds")
    
    # 5.3.1 Minimum requirement (for outliers)
    min_req, min_req_changed = parameter_input(
        module_key=MODULE_KEY,
        param_id=PID_MIN_ANNUAL_REQ,
        label="Minimum annual efficiency requirement",
        baseline=BASELINE_MIN_REQUIREMENT,
        value=get_config_value(MODULE_KEY, "outlier_krav", BASELINE_MIN_REQUIREMENT),
        min_val=0.0,
        max_val=0.10,
        step=0.001,
        format_str="%.3f",
        help_text="Annual requirement floor for outlier companies",
        format_as_percent=True
    )
    
    if min_req_changed:
        config["outlier_krav"] = min_req
    
    # Get current values for display
    current_real_time = int(real_time) if real_time_changed else BASELINE_REALIZATION_TIME
    current_kund_del = kund_del if kund_del_changed else BASELINE_CUSTOMER_SHARING
    current_min_req = min_req if min_req_changed else BASELINE_MIN_REQUIREMENT
    current_max_pot = max_pot if max_pot_changed else BASELINE_MAX_POTENTIAL
    
    # Calculate and display resulting range
    max_annual_req = get_max_eff_req(
        truncation_max=current_max_pot,
        customer_sharing=current_kund_del,
        realization_time=current_real_time,
        supervision_period=BASELINE_SUPERVISION_PERIOD
    )
    
    st.caption(
        f"Resulting range: {current_min_req*100:.2f}% - {max_annual_req*100:.2f}% annually"
    )
    
    st.divider()
    
    st.markdown("##### 5.4 Cost base application")
    
    # 5.4.1 Efficiency requirement cost base
    method, method_changed = parameter_select(
        module_key=MODULE_KEY,
        param_id=PID_COST_BASE,
        label="Apply efficiency requirement to",
        options=["OPEX", "TOTEX"],
        baseline="OPEX",
        value=get_config_value(MODULE_KEY, "paverkbara_method", "OPEX"),
        help_text="OPEX: adjustable costs. TOTEX: includes capital costs."
    )
    
    if method_changed:
        config["paverkbara_method"] = method

    # Ensure current widget values are included so they persist when saving/loading cases
    widget_map = {
        f"{MODULE_KEY}_input_{PID_MAX_POTENTIAL_CAP}": "trunkering_max",
        f"{MODULE_KEY}_input_{PID_REALIZATION_TIME}": "realiseringstid",
        f"{MODULE_KEY}_input_{PID_CUSTOMER_SHARING}": "kunddelning",
        f"{MODULE_KEY}_input_{PID_MIN_ANNUAL_REQ}": "outlier_krav",
        f"{MODULE_KEY}_select_{PID_COST_BASE}": "paverkbara_method",
    }
    for wkey, pname in widget_map.items():
        if wkey in st.session_state:
            config[pname] = st.session_state.get(wkey)

    return config
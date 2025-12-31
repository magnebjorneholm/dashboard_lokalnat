"""
Module 3: Incentive Variables

Handles company-specific variables for incentive calculations.
Variable-IDs: 30.2 (netloss), 30.3 (load), 30.4 (quality)

These are observed and norm values specific to the selected company.
Override values apply to ALL years (2024-2027).
"""

import streamlit as st
from typing import Dict, Any, Optional

from frontend.utils.state_manager import get_user_reid
from data_loaders.incentive_data import (
    get_user_baseline_variables,
    get_variable_metadata,
    VARIABLE_COLUMNS,
)

MODULE_KEY = "m3_incentive_variables"

# Kundtyper för AIT/AIF/ÅME
SNI_LABELS = {
    1: "Jordbruk",
    2: "Industri",
    3: "Handel/tjänster",
    4: "Offentlig verksamhet",
    5: "Hushåll",
    6: "Gränspunkt",
}


def render() -> Dict[str, Any]:
    """
    Render Module 3: Incentive Variables.
    
    Displays company-specific variables with baseline values from 2024.
    User can override any variable - the new value applies to all years.
    
    Returns:
        Dict with variable overrides: {variable_name: new_value, ...}
        Only includes variables that differ from baseline.
    """
    config: Dict[str, Any] = {}
    
    st.subheader("30. Incitamentvariabler")
    
    # Hämta valt företag
    user_reid = get_user_reid()
    if not user_reid:
        st.warning("Välj företag i sidopanelen för att se variabler.")
        return config
    
    # Ladda baseline-värden för företaget (år 2024)
    baseline = _load_baseline_cached(user_reid)
    
    if not baseline:
        st.error(f"Kunde inte ladda baseline-data för {user_reid}")
        return config
    
    # Info om hur variabler fungerar
    st.info(
        "Här kan du justera företagsspecifika variabler för incitamentberäkningen. "
        "Baseline visar värdet för 2024. Override-värden appliceras på **alla år** (2024-2027)."
    )
    
    # Räkna antal ändringar för sammanfattning
    n_changes = sum(1 for k, v in st.session_state.get("ui_config", {}).get(MODULE_KEY, {}).items() 
                    if v is not None)
    if n_changes > 0:
        st.success(f"**{n_changes} variabel(er) ändrade** från baseline")
    
    st.divider()
    
    # === 30.2 Nätförlust ===
    with st.expander("**30.2 Nätförlust**", expanded=False):
        _render_netloss_variables(config, baseline)
    
    # === 30.3 Belastning ===
    with st.expander("**30.3 Belastning**", expanded=False):
        _render_load_variables(config, baseline)
    
    # === 30.4 Kvalitet ===
    with st.expander("**30.4 Kvalitet (CEMI4)**", expanded=False):
        _render_cemi4_variables(config, baseline)
    
    with st.expander("**30.4 Kvalitet (AIF observerade)**", expanded=False):
        _render_aif_obs_variables(config, baseline)
    
    with st.expander("**30.4 Kvalitet (AIF norm)**", expanded=False):
        _render_aif_norm_variables(config, baseline)
    
    with st.expander("**30.4 Kvalitet (AIT observerade)**", expanded=False):
        _render_ait_obs_variables(config, baseline)
    
    with st.expander("**30.4 Kvalitet (AIT norm)**", expanded=False):
        _render_ait_norm_variables(config, baseline)
    
    with st.expander("**30.4 Kvalitet (ÅME)**", expanded=False):
        _render_ame_variables(config, baseline)
    
    return config


@st.cache_data(ttl=3600, show_spinner="Laddar baseline-variabler...")
def _load_baseline_cached(user_reid: str) -> Dict[str, float]:
    """Cachad laddning av baseline-variabler för ett företag."""
    return get_user_baseline_variables(user_reid, year=2024)


def _render_variable_input(
    config: Dict[str, Any],
    baseline: Dict[str, float],
    var_name: str,
    label: str,
    unit: str,
    format_str: str = "%.4f",
    help_text: str = None,
    min_value: float = None,
    max_value: float = None,
    step: float = None,
) -> None:
    """
    Render a single variable input with baseline comparison.
    
    Args:
        config: Dict to store overrides
        baseline: Baseline values dict
        var_name: Variable column name (e.g. "nf_obs")
        label: Display label
        unit: Unit string (e.g. "andel", "MWh")
        format_str: Number format (e.g. "%.4f")
        help_text: Optional help tooltip
        min_value: Optional minimum
        max_value: Optional maximum
        step: Optional step size
    """
    baseline_value = baseline.get(var_name)
    
    # Om baseline saknas, visa varning
    if baseline_value is None:
        st.caption(f"{label}: *Saknar baseline-data*")
        return
    
    # Hämta eventuellt tidigare override från session_state
    current_config = st.session_state.get("ui_config", {}).get(MODULE_KEY, {})
    current_override = current_config.get(var_name)
    
    # Visa input
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # Avgör default-värde (override eller baseline)
        display_value = current_override if current_override is not None else baseline_value
        
        # Sätt steg automatiskt om inte angivet
        if step is None:
            if abs(baseline_value) < 1:
                step = 0.0001
            elif abs(baseline_value) < 100:
                step = 0.1
            else:
                step = 100.0
        
        new_value = st.number_input(
            label,
            value=float(display_value),
            min_value=min_value,
            max_value=max_value,
            step=step,
            format=format_str,
            key=f"{MODULE_KEY}_{var_name}",
            help=help_text or f"Baseline (2024): {baseline_value:{format_str.replace('%', '')}} {unit}"
        )
    
    with col2:
        # Visa status
        if current_override is not None or abs(new_value - baseline_value) > 1e-9:
            st.markdown(f"<span style='color: orange;'>Ändrad</span>", unsafe_allow_html=True)
            config[var_name] = new_value
        else:
            st.caption(f"= baseline")
            # Sätt explicit till None för att markera "använd baseline"
            config[var_name] = None


def _render_netloss_variables(config: Dict[str, Any], baseline: Dict[str, float]) -> None:
    """Render 30.2 Network loss variables."""
    st.markdown("Variabler för nätförlustincitamentet.")
    st.caption("Formel: Justering = δ × (NF_norm - NF_obs) × E_in × K_NF × KPI")
    
    st.divider()
    
    _render_variable_input(
        config, baseline,
        var_name="nf_norm",
        label="Nätförlust norm",
        unit="andel",
        format_str="%.4f",
        help_text="Normerad nätförlust baserat på kundtäthet",
        min_value=0.0,
        max_value=0.5,
    )
    
    _render_variable_input(
        config, baseline,
        var_name="nf_obs",
        label="Nätförlust observerad",
        unit="andel",
        format_str="%.4f",
        help_text="Faktisk nätförlust (energi förlust / energi in)",
        min_value=0.0,
        max_value=0.5,
    )
    
    _render_variable_input(
        config, baseline,
        var_name="e_in",
        label="Energi in (E_in)",
        unit="MWh",
        format_str="%.0f",
        help_text="Total energi levererad till nätet",
        min_value=0.0,
        step=1000.0,
    )


def _render_load_variables(config: Dict[str, Any], baseline: Dict[str, float]) -> None:
    """Render 30.3 Load/utilization variables."""
    st.markdown("Variabler för belastningsincitamentet.")
    st.caption("Formel: Justering = (UG_obs - UG_norm) × K_upstream")
    
    st.divider()
    
    _render_variable_input(
        config, baseline,
        var_name="ug_norm",
        label="Utnyttjandegrad norm",
        unit="andel",
        format_str="%.4f",
        help_text="Normerad utnyttjandegrad baserat på kundtäthet",
        min_value=0.0,
        max_value=1.0,
    )
    
    _render_variable_input(
        config, baseline,
        var_name="ug_obs",
        label="Utnyttjandegrad observerad",
        unit="andel",
        format_str="%.4f",
        help_text="Faktisk utnyttjandegrad (energi / kapacitet × tid)",
        min_value=0.0,
        max_value=1.0,
    )
    
    _render_variable_input(
        config, baseline,
        var_name="k_upstream",
        label="Kostnad överliggande nät",
        unit="kr",
        format_str="%.0f",
        help_text="Abonnemangskostnad för överliggande nät",
        min_value=0.0,
        step=10000.0,
    )


def _render_cemi4_variables(config: Dict[str, Any], baseline: Dict[str, float]) -> None:
    """Render 30.4 CEMI4 variables."""
    st.markdown("CEMI4-index för korrigering av kvalitetsincitament.")
    st.caption("Om CEMI4_obs > CEMI4_norm reduceras kvalitetsincitamentet.")
    
    st.divider()
    
    _render_variable_input(
        config, baseline,
        var_name="cemi4_norm",
        label="CEMI4 norm",
        unit="index",
        format_str="%.4f",
        help_text="Normerat CEMI4-index baserat på kundtäthet",
        min_value=0.0,
        max_value=2.0,
    )
    
    _render_variable_input(
        config, baseline,
        var_name="cemi4_obs",
        label="CEMI4 observerad",
        unit="index",
        format_str="%.4f",
        help_text="Faktiskt CEMI4-index (avbrottsstatistik)",
        min_value=0.0,
        max_value=2.0,
    )


def _render_aif_obs_variables(config: Dict[str, Any], baseline: Dict[str, float]) -> None:
    """Render AIF observed variables (12 st)."""
    st.markdown("Antal avbrottsfall per kW effekt, observerade värden.")
    st.caption("Uppdelat på aviserade (a) och oaviserade (o) avbrott.")
    
    st.divider()
    
    st.markdown("**Oaviserade avbrott**")
    for sni, label in SNI_LABELS.items():
        _render_variable_input(
            config, baseline,
            var_name=f"aif_o_{sni}_obs",
            label=f"AIF oaviserad {label}",
            unit="antal/kW",
            format_str="%.6f",
            min_value=0.0,
        )
    
    st.divider()
    
    st.markdown("**Aviserade avbrott**")
    for sni, label in SNI_LABELS.items():
        _render_variable_input(
            config, baseline,
            var_name=f"aif_a_{sni}_obs",
            label=f"AIF aviserad {label}",
            unit="antal/kW",
            format_str="%.6f",
            min_value=0.0,
        )


def _render_aif_norm_variables(config: Dict[str, Any], baseline: Dict[str, float]) -> None:
    """Render AIF norm variables (12 st)."""
    st.markdown("Antal avbrottsfall per kW effekt, normerade värden.")
    st.caption("Baserat på kundtäthet och kundtyp.")
    
    st.divider()
    
    st.markdown("**Oaviserade avbrott**")
    for sni, label in SNI_LABELS.items():
        _render_variable_input(
            config, baseline,
            var_name=f"aif_o_{sni}_norm",
            label=f"AIF oaviserad {label} norm",
            unit="antal/kW",
            format_str="%.6f",
            min_value=0.0,
        )
    
    st.divider()
    
    st.markdown("**Aviserade avbrott**")
    for sni, label in SNI_LABELS.items():
        _render_variable_input(
            config, baseline,
            var_name=f"aif_a_{sni}_norm",
            label=f"AIF aviserad {label} norm",
            unit="antal/kW",
            format_str="%.6f",
            min_value=0.0,
        )


def _render_ait_obs_variables(config: Dict[str, Any], baseline: Dict[str, float]) -> None:
    """Render AIT observed variables (12 st)."""
    st.markdown("Avbrottstid per kWh energi, observerade värden.")
    st.caption("Uppdelat på aviserade (a) och oaviserade (o) avbrott.")
    
    st.divider()
    
    st.markdown("**Oaviserade avbrott**")
    for sni, label in SNI_LABELS.items():
        _render_variable_input(
            config, baseline,
            var_name=f"ait_o_{sni}_obs",
            label=f"AIT oaviserad {label}",
            unit="tim/kWh",
            format_str="%.6f",
            min_value=0.0,
        )
    
    st.divider()
    
    st.markdown("**Aviserade avbrott**")
    for sni, label in SNI_LABELS.items():
        _render_variable_input(
            config, baseline,
            var_name=f"ait_a_{sni}_obs",
            label=f"AIT aviserad {label}",
            unit="tim/kWh",
            format_str="%.6f",
            min_value=0.0,
        )


def _render_ait_norm_variables(config: Dict[str, Any], baseline: Dict[str, float]) -> None:
    """Render AIT norm variables (12 st)."""
    st.markdown("Avbrottstid per kWh energi, normerade värden.")
    st.caption("Baserat på kundtäthet och kundtyp.")
    
    st.divider()
    
    st.markdown("**Oaviserade avbrott**")
    for sni, label in SNI_LABELS.items():
        _render_variable_input(
            config, baseline,
            var_name=f"ait_o_{sni}_norm",
            label=f"AIT oaviserad {label} norm",
            unit="tim/kWh",
            format_str="%.6f",
            min_value=0.0,
        )
    
    st.divider()
    
    st.markdown("**Aviserade avbrott**")
    for sni, label in SNI_LABELS.items():
        _render_variable_input(
            config, baseline,
            var_name=f"ait_a_{sni}_norm",
            label=f"AIT aviserad {label} norm",
            unit="tim/kWh",
            format_str="%.6f",
            min_value=0.0,
        )


def _render_ame_variables(config: Dict[str, Any], baseline: Dict[str, float]) -> None:
    """Render ÅME variables (6 st)."""
    st.markdown("Årsmedeleffekt (ÅME) per kundtyp.")
    st.caption("Används för viktning av AIT/AIF till total kvalitetsjustering.")
    
    st.divider()
    
    for sni, label in SNI_LABELS.items():
        _render_variable_input(
            config, baseline,
            var_name=f"ame_{sni}",
            label=f"ÅME {label}",
            unit="kW",
            format_str="%.1f",
            min_value=0.0,
            step=100.0,
        )
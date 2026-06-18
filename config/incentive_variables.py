"""
config/incentive_variables.py

Static metadata for the incentive variables (quality / network loss / load):
the list of overridable columns and their UI presentation metadata.

This is configuration, not data loading or calculation — it lives in ``config``
so both the loader (``data_loaders/incentive_data.py``) and the UI can read it
without crossing layers. Swedish labels are intentional (UI display strings).
"""
from __future__ import annotations

from typing import Dict, List


# All variable columns that can be overridden — company-specific observed and
# norm values.
VARIABLE_COLUMNS: List[str] = [
    # Nätförlust
    "nf_norm", "nf_obs", "e_in",
    # Belastning
    "ug_norm", "ug_obs", "k_upstream",
    # CEMI4
    "cemi4_norm", "cemi4_obs",
    # AIF observerade (12 st)
    "aif_a_1_obs", "aif_a_2_obs", "aif_a_3_obs", "aif_a_4_obs", "aif_a_5_obs", "aif_a_6_obs",
    "aif_o_1_obs", "aif_o_2_obs", "aif_o_3_obs", "aif_o_4_obs", "aif_o_5_obs", "aif_o_6_obs",
    # AIF norm (12 st)
    "aif_a_1_norm", "aif_a_2_norm", "aif_a_3_norm", "aif_a_4_norm", "aif_a_5_norm", "aif_a_6_norm",
    "aif_o_1_norm", "aif_o_2_norm", "aif_o_3_norm", "aif_o_4_norm", "aif_o_5_norm", "aif_o_6_norm",
    # AIT observerade (12 st)
    "ait_a_1_obs", "ait_a_2_obs", "ait_a_3_obs", "ait_a_4_obs", "ait_a_5_obs", "ait_a_6_obs",
    "ait_o_1_obs", "ait_o_2_obs", "ait_o_3_obs", "ait_o_4_obs", "ait_o_5_obs", "ait_o_6_obs",
    # AIT norm (12 st)
    "ait_a_1_norm", "ait_a_2_norm", "ait_a_3_norm", "ait_a_4_norm", "ait_a_5_norm", "ait_a_6_norm",
    "ait_o_1_norm", "ait_o_2_norm", "ait_o_3_norm", "ait_o_4_norm", "ait_o_5_norm", "ait_o_6_norm",
    # ÅME per kundtyp (6 st)
    "ame_1", "ame_2", "ame_3", "ame_4", "ame_5", "ame_6",
]


def get_variable_metadata() -> Dict[str, Dict]:
    """Return label / category / unit / format metadata per incentive variable."""
    return {
        # Nätförlust
        "nf_norm": {"label": "Nätförlust norm", "category": "netloss", "unit": "andel", "format": ".4f"},
        "nf_obs": {"label": "Nätförlust observerad", "category": "netloss", "unit": "andel", "format": ".4f"},
        "e_in": {"label": "Energi in", "category": "netloss", "unit": "MWh", "format": ",.0f"},

        # Belastning
        "ug_norm": {"label": "Utnyttjandegrad norm", "category": "load", "unit": "andel", "format": ".4f"},
        "ug_obs": {"label": "Utnyttjandegrad observerad", "category": "load", "unit": "andel", "format": ".4f"},
        "k_upstream": {"label": "Kostnad överliggande nät", "category": "load", "unit": "kr", "format": ",.0f"},

        # CEMI4
        "cemi4_norm": {"label": "CEMI4 norm", "category": "quality", "unit": "andel", "format": ".4f"},
        "cemi4_obs": {"label": "CEMI4 observerad", "category": "quality", "unit": "andel", "format": ".4f"},

        # AIF observerade
        "aif_a_1_obs": {"label": "AIF aviserad jordbruk", "category": "aif_obs", "unit": "antal/kW", "format": ".4f"},
        "aif_a_2_obs": {"label": "AIF aviserad industri", "category": "aif_obs", "unit": "antal/kW", "format": ".4f"},
        "aif_a_3_obs": {"label": "AIF aviserad handel/tjänster", "category": "aif_obs", "unit": "antal/kW", "format": ".4f"},
        "aif_a_4_obs": {"label": "AIF aviserad offentlig", "category": "aif_obs", "unit": "antal/kW", "format": ".4f"},
        "aif_a_5_obs": {"label": "AIF aviserad hushåll", "category": "aif_obs", "unit": "antal/kW", "format": ".4f"},
        "aif_a_6_obs": {"label": "AIF aviserad gränspunkt", "category": "aif_obs", "unit": "antal/kW", "format": ".4f"},
        "aif_o_1_obs": {"label": "AIF oaviserad jordbruk", "category": "aif_obs", "unit": "antal/kW", "format": ".4f"},
        "aif_o_2_obs": {"label": "AIF oaviserad industri", "category": "aif_obs", "unit": "antal/kW", "format": ".4f"},
        "aif_o_3_obs": {"label": "AIF oaviserad handel/tjänster", "category": "aif_obs", "unit": "antal/kW", "format": ".4f"},
        "aif_o_4_obs": {"label": "AIF oaviserad offentlig", "category": "aif_obs", "unit": "antal/kW", "format": ".4f"},
        "aif_o_5_obs": {"label": "AIF oaviserad hushåll", "category": "aif_obs", "unit": "antal/kW", "format": ".4f"},
        "aif_o_6_obs": {"label": "AIF oaviserad gränspunkt", "category": "aif_obs", "unit": "antal/kW", "format": ".4f"},

        # AIF norm
        "aif_a_1_norm": {"label": "AIF aviserad jordbruk norm", "category": "aif_norm", "unit": "antal/kW", "format": ".4f"},
        "aif_a_2_norm": {"label": "AIF aviserad industri norm", "category": "aif_norm", "unit": "antal/kW", "format": ".4f"},
        "aif_a_3_norm": {"label": "AIF aviserad handel/tjänster norm", "category": "aif_norm", "unit": "antal/kW", "format": ".4f"},
        "aif_a_4_norm": {"label": "AIF aviserad offentlig norm", "category": "aif_norm", "unit": "antal/kW", "format": ".4f"},
        "aif_a_5_norm": {"label": "AIF aviserad hushåll norm", "category": "aif_norm", "unit": "antal/kW", "format": ".4f"},
        "aif_a_6_norm": {"label": "AIF aviserad gränspunkt norm", "category": "aif_norm", "unit": "antal/kW", "format": ".4f"},
        "aif_o_1_norm": {"label": "AIF oaviserad jordbruk norm", "category": "aif_norm", "unit": "antal/kW", "format": ".4f"},
        "aif_o_2_norm": {"label": "AIF oaviserad industri norm", "category": "aif_norm", "unit": "antal/kW", "format": ".4f"},
        "aif_o_3_norm": {"label": "AIF oaviserad handel/tjänster norm", "category": "aif_norm", "unit": "antal/kW", "format": ".4f"},
        "aif_o_4_norm": {"label": "AIF oaviserad offentlig norm", "category": "aif_norm", "unit": "antal/kW", "format": ".4f"},
        "aif_o_5_norm": {"label": "AIF oaviserad hushåll norm", "category": "aif_norm", "unit": "antal/kW", "format": ".4f"},
        "aif_o_6_norm": {"label": "AIF oaviserad gränspunkt norm", "category": "aif_norm", "unit": "antal/kW", "format": ".4f"},

        # AIT observerade
        "ait_a_1_obs": {"label": "AIT aviserad jordbruk", "category": "ait_obs", "unit": "tim/kWh", "format": ".4f"},
        "ait_a_2_obs": {"label": "AIT aviserad industri", "category": "ait_obs", "unit": "tim/kWh", "format": ".4f"},
        "ait_a_3_obs": {"label": "AIT aviserad handel/tjänster", "category": "ait_obs", "unit": "tim/kWh", "format": ".4f"},
        "ait_a_4_obs": {"label": "AIT aviserad offentlig", "category": "ait_obs", "unit": "tim/kWh", "format": ".4f"},
        "ait_a_5_obs": {"label": "AIT aviserad hushåll", "category": "ait_obs", "unit": "tim/kWh", "format": ".4f"},
        "ait_a_6_obs": {"label": "AIT aviserad gränspunkt", "category": "ait_obs", "unit": "tim/kWh", "format": ".4f"},
        "ait_o_1_obs": {"label": "AIT oaviserad jordbruk", "category": "ait_obs", "unit": "tim/kWh", "format": ".4f"},
        "ait_o_2_obs": {"label": "AIT oaviserad industri", "category": "ait_obs", "unit": "tim/kWh", "format": ".4f"},
        "ait_o_3_obs": {"label": "AIT oaviserad handel/tjänster", "category": "ait_obs", "unit": "tim/kWh", "format": ".4f"},
        "ait_o_4_obs": {"label": "AIT oaviserad offentlig", "category": "ait_obs", "unit": "tim/kWh", "format": ".4f"},
        "ait_o_5_obs": {"label": "AIT oaviserad hushåll", "category": "ait_obs", "unit": "tim/kWh", "format": ".4f"},
        "ait_o_6_obs": {"label": "AIT oaviserad gränspunkt", "category": "ait_obs", "unit": "tim/kWh", "format": ".4f"},

        # AIT norm
        "ait_a_1_norm": {"label": "AIT aviserad jordbruk norm", "category": "ait_norm", "unit": "tim/kWh", "format": ".4f"},
        "ait_a_2_norm": {"label": "AIT aviserad industri norm", "category": "ait_norm", "unit": "tim/kWh", "format": ".4f"},
        "ait_a_3_norm": {"label": "AIT aviserad handel/tjänster norm", "category": "ait_norm", "unit": "tim/kWh", "format": ".4f"},
        "ait_a_4_norm": {"label": "AIT aviserad offentlig norm", "category": "ait_norm", "unit": "tim/kWh", "format": ".4f"},
        "ait_a_5_norm": {"label": "AIT aviserad hushåll norm", "category": "ait_norm", "unit": "tim/kWh", "format": ".4f"},
        "ait_a_6_norm": {"label": "AIT aviserad gränspunkt norm", "category": "ait_norm", "unit": "tim/kWh", "format": ".4f"},
        "ait_o_1_norm": {"label": "AIT oaviserad jordbruk norm", "category": "ait_norm", "unit": "tim/kWh", "format": ".4f"},
        "ait_o_2_norm": {"label": "AIT oaviserad industri norm", "category": "ait_norm", "unit": "tim/kWh", "format": ".4f"},
        "ait_o_3_norm": {"label": "AIT oaviserad handel/tjänster norm", "category": "ait_norm", "unit": "tim/kWh", "format": ".4f"},
        "ait_o_4_norm": {"label": "AIT oaviserad offentlig norm", "category": "ait_norm", "unit": "tim/kWh", "format": ".4f"},
        "ait_o_5_norm": {"label": "AIT oaviserad hushåll norm", "category": "ait_norm", "unit": "tim/kWh", "format": ".4f"},
        "ait_o_6_norm": {"label": "AIT oaviserad gränspunkt norm", "category": "ait_norm", "unit": "tim/kWh", "format": ".4f"},

        # ÅME
        "ame_1": {"label": "ÅME jordbruk", "category": "ame", "unit": "kW", "format": ",.1f"},
        "ame_2": {"label": "ÅME industri", "category": "ame", "unit": "kW", "format": ",.1f"},
        "ame_3": {"label": "ÅME handel/tjänster", "category": "ame", "unit": "kW", "format": ",.1f"},
        "ame_4": {"label": "ÅME offentlig", "category": "ame", "unit": "kW", "format": ",.1f"},
        "ame_5": {"label": "ÅME hushåll", "category": "ame", "unit": "kW", "format": ",.1f"},
        "ame_6": {"label": "ÅME gränspunkt", "category": "ame", "unit": "kW", "format": ",.1f"},
    }

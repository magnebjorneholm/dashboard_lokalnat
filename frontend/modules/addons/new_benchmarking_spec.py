"""
new_benchmarking_spec.py — configuration panel for the new benchmarking model add-on.

Renders the user-facing controls and returns a fully-formed NewBenchmarkingConfig.
This add-on is standalone (its own page) and does NOT flow through the case/ui_config
system, so it builds the config object directly rather than a ui_config dict.
"""

from __future__ import annotations

import streamlit as st

from calculations.new_benchmarking.config import (
    NewBenchmarkingConfig,
    DEFAULT_NONCTRL_CATEGORIES,
    NONCTRL_GRID_SUBSCRIPTION, NONCTRL_GRID_CONNECTION,
    NONCTRL_FEED_IN, NONCTRL_CAPACITY_RESERVE,
)
from calculations.new_benchmarking.cable_length import C as cable_C
from calculations.new_benchmarking.environment_capex_adjustment import config as env_C
from calculations.new_benchmarking.station_capex_adjustment import config as st_C

# Baseline common loss price (kr/MWh) — same default as K_NF.
BASELINE_K_NF = 753.44

_NONCTRL_LABELS = {
    NONCTRL_GRID_SUBSCRIPTION: "Abonnemang överliggande nät",
    NONCTRL_GRID_CONNECTION: "Anslutning",
    NONCTRL_FEED_IN: "Inmatningsersättning",
    NONCTRL_CAPACITY_RESERVE: "Kapacitetsreserv",
}


def render_config_panel() -> NewBenchmarkingConfig:
    """Render the configuration controls and return a NewBenchmarkingConfig."""
    with st.container(border=True):
        st.markdown("**Konfiguration**")
        st.caption(
            "Justeringarna nedan påverkar endast den nya modellen. Nuvarande värden "
            "läses oförändrade från Ei:s publicerade resultat (EIs_DEA)."
        )

        col_a, col_b, col_c = st.columns(3)

        # ── Network losses @ common price ────────────────────────────────────
        with col_a:
            st.markdown("**Nätförluster**")
            k_nf = st.number_input(
                "Gemensamt pris (kr/MWh)",
                min_value=0.0, value=BASELINE_K_NF, step=10.0,
                help="Nätförluster värderas som nf_obs · pris · e_in. Baslinje 753,44 kr/MWh.",
                key="nb_k_nf",
            )
            rts = st.selectbox(
                "Skalavkastning (RTS)",
                options=["crs", "vrs"],
                index=0,
                format_func=lambda x: x.upper(),
                help="CRS = konstant, VRS = variabel skalavkastning i DEA.",
                key="nb_rts",
            )

        # ── Förläggningsmiljö (capex) ────────────────────────────────────────
        with col_b:
            st.markdown("**Förläggningsmiljö (capex)**")
            cable_method = st.selectbox(
                "Metod kabel",
                options=list(env_C.METHODS),
                index=list(env_C.METHODS).index(env_C.METHOD_PER_TYPE),
                help="per_type = exakt omprissättning, sek_per_km/percent = schabloner.",
                key="nb_cable_method",
            )
            station_method = st.selectbox(
                "Metod station",
                options=list(st_C.METHODS),
                index=list(st_C.METHODS).index(st_C.METHOD_ITEMIZED),
                help="itemized = ta bort tätortstillägg exakt, percent = schablon.",
                key="nb_station_method",
            )

        # ── DEA outputs: cable length ────────────────────────────────────────
        with col_c:
            st.markdown("**Outputs**")
            include_cable_length = st.checkbox(
                "Inkludera ledningslängd", value=True, key="nb_include_cable",
                help="Lägg till fysisk ledningslängd (km) som ny DEA-output.",
            )
            cable_types = st.multiselect(
                "Ledningstyper",
                options=list(cable_C.ALL_TYPES),
                default=list(cable_C.ELECTRICAL_TYPES),
                format_func=lambda t: cable_C.TYPE_LABELS.get(t, t),
                disabled=not include_cable_length,
                key="nb_cable_types",
            )
            split_by_voltage = st.checkbox(
                "Dela per spänningsnivå", value=False,
                disabled=not include_cable_length, key="nb_split_voltage",
            )

        # ── TOTEX composition ────────────────────────────────────────────────
        with st.expander("TOTEX-komponenter (på/av)"):
            c1, c2 = st.columns(2)
            with c1:
                include_controllable = st.checkbox(
                    "Påverkbara (controllable)", value=True, key="nb_inc_controllable")
                include_losses = st.checkbox(
                    "Nätförluster @ gemensamt pris", value=True, key="nb_inc_losses")
                include_capex = st.checkbox(
                    "Kapitalkostnad (justerad)", value=True, key="nb_inc_capex")
            with c2:
                selected_nonctrl = st.multiselect(
                    "Opåverkbara kategorier",
                    options=list(DEFAULT_NONCTRL_CATEGORIES),
                    default=list(DEFAULT_NONCTRL_CATEGORIES),
                    format_func=lambda c: _NONCTRL_LABELS.get(c, c),
                    help="Myndighetsavgifter exkluderas alltid ur TOTEX.",
                    key="nb_nonctrl_cats",
                )

    return NewBenchmarkingConfig(
        k_nf={2024: k_nf, 2025: k_nf, 2026: k_nf, 2027: k_nf},
        include_controllable=include_controllable,
        include_losses=include_losses,
        include_capex=include_capex,
        non_controllable_categories=tuple(selected_nonctrl),
        cable_method=cable_method,
        station_method=station_method,
        include_cable_length=include_cable_length,
        cable_types=tuple(cable_types),
        split_by_voltage=split_by_voltage,
        rts=rts,
    )

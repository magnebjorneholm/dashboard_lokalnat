"""
new_benchmarking_output.py — render the new-benchmarking comparison for one company.

Reuses the shared efficiency visualisations (frontend/results/_efficiency_charts.py),
mapping NEW model → "case" and CURRENT model (EIs_DEA) → "baseline". The headline is the
efficiency-requirement change, since efficiency *scores* live on each model's own frontier
and are only secondary context.
"""

from __future__ import annotations

from typing import Optional

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from frontend.common.styling import COLORS
from config.colors import get_plotly_template_safe
from config.formatting import format_percent, format_pp, format_number
from config.column_names import (
    COL_REID, COL_DEA_EFFICIENCY, COL_DEA_SUPER_EFF, COL_DEA_POTENTIAL, COL_IS_OUTLIER,
    COL_EFF_REQ_ANNUAL, COL_CONTROLLABLE_AVG, COL_LOSS_VALUED, COL_NONCTRL_SELECTED,
    COL_CAPITAL_COST_ENV_ADJ, COL_TOTEX_NEW,
)
from calculations.new_benchmarking.config import NewBenchmarkingConfig
from calculations.new_benchmarking.model import NewBenchmarkingResult
from frontend.results._efficiency_charts import (
    calc_trunkering_min, render_efficiency_summary, render_efficiency_distributions,
)


# ---------------------------------------------------------------------------
# Extraction helpers
# ---------------------------------------------------------------------------

def _val(df: pd.DataFrame, reid: str, col: str) -> Optional[float]:
    """Single value for a company, or None if missing/NaN."""
    if col not in df.columns:
        return None
    m = df[df[COL_REID] == reid]
    if m.empty:
        return None
    v = m.iloc[0][col]
    return None if pd.isna(v) else float(v)


def _flag(df: pd.DataFrame, reid: str, col: str) -> bool:
    m = df[df[COL_REID] == reid]
    return bool(m.iloc[0][col]) if not m.empty and col in df.columns else False


def _rank(df: pd.DataFrame, reid: str, eff_col: str = COL_DEA_EFFICIENCY) -> Optional[int]:
    """1-based rank by efficiency (1 = most efficient). None if the firm has no score."""
    d = df[[COL_REID, eff_col]].dropna(subset=[eff_col]).sort_values(
        eff_col, ascending=False).reset_index(drop=True)
    idx = d.index[d[COL_REID] == reid]
    return int(idx[0]) + 1 if len(idx) else None


def _params_from_cfg(cfg: NewBenchmarkingConfig) -> dict:
    """Map cfg.eff_req_params to the keys the efficiency charts expect."""
    p = cfg.eff_req_params
    params = {
        "trunkering_max": p["truncation_max"],
        "realiseringstid": p["realization_time"],
        "kunddelning": p["customer_sharing"],
        "outlier_krav": p["outlier_req"],
        "tillsynsperiod": p["supervision_period"],
    }
    params["trunkering_min"] = calc_trunkering_min(
        params["outlier_krav"], params["kunddelning"],
        params["realiseringstid"], params["tillsynsperiod"],
    )
    return params


# ---------------------------------------------------------------------------
# Main render
# ---------------------------------------------------------------------------

def render_company_view(
    result: NewBenchmarkingResult,
    user_reid: str,
    cfg: NewBenchmarkingConfig,
) -> None:
    """Full per-company view: headline → KPIs → distributions → TOTEX waterfall."""
    dea_new = result.dea_new
    dea_cur = result.dea_current

    new_eff = _val(dea_new, user_reid, COL_DEA_EFFICIENCY)
    cur_eff = _val(dea_cur, user_reid, COL_DEA_EFFICIENCY)
    new_pot = _val(dea_new, user_reid, COL_DEA_POTENTIAL)
    cur_pot = _val(dea_cur, user_reid, COL_DEA_POTENTIAL)
    new_req = _val(dea_new, user_reid, COL_EFF_REQ_ANNUAL)
    cur_req = _val(dea_cur, user_reid, COL_EFF_REQ_ANNUAL)
    is_outlier_new = _flag(dea_new, user_reid, COL_IS_OUTLIER)
    super_eff = _val(dea_new, user_reid, COL_DEA_SUPER_EFF)
    super_eff = super_eff if (super_eff is not None and super_eff >= 1.0) else None

    # ── Headline: efficiency-requirement change ──────────────────────────────
    st.markdown("#### Effektiviseringskrav — ny modell vs nuvarande")
    h1, h2, h3 = st.columns(3)
    with h1:
        st.metric("Nuvarande (EIs_DEA)", format_percent(cur_req) if cur_req is not None else "–")
    with h2:
        delta = (new_req - cur_req) if (new_req is not None and cur_req is not None) else None
        st.metric(
            "Nytt krav (ny modell)",
            format_percent(new_req) if new_req is not None else "–",
            delta=format_pp(delta) if delta is not None and abs(delta) > 1e-5 else None,
            delta_color="inverse",
        )
    with h3:
        st.metric(
            "Förändring",
            format_pp(delta) if delta is not None else "–",
            help="Positivt = högre effektiviseringskrav under den nya modellen.",
        )
    st.caption(
        "Nuvarande värden kommer direkt från Ei:s publicerade DEA (EIs_DEA). "
        "Effektivitetspoängen nedan mäts mot respektive modells egen front och är "
        "därför sekundär kontext — kravförändringen ovan är huvudresultatet."
    )

    st.divider()

    # ── Reused KPI summary + distributions (case = new, baseline = current) ──
    params = _params_from_cfg(cfg)
    eff_scores = dea_new[COL_DEA_EFFICIENCY].dropna().to_numpy()
    n_total = len(dea_new)

    render_efficiency_summary(
        eff_case=new_eff, eff_baseline=cur_eff,
        potential_case=new_pot, potential_baseline=cur_pot,
        effkrav_case=new_req, effkrav_baseline=cur_req,
        is_outlier=is_outlier_new, super_eff=super_eff,
        case_rank=_rank(dea_new, user_reid), bl_rank=_rank(dea_cur, user_reid),
        n_total=n_total, params=params, show_detail_tables=True,
    )

    st.caption("'Case' = ny modell · 'Baseline' = nuvarande modell (EIs_DEA).")
    st.divider()

    render_efficiency_distributions(
        eff_scores=eff_scores, eff_case=new_eff, eff_baseline=cur_eff,
        effkrav_all_df=dea_new, effkrav_case=new_req, effkrav_baseline=cur_req,
        params=params, key_prefix="nb",
    )

    st.divider()

    # ── TOTEX waterfall (new model composition) ──────────────────────────────
    _render_totex_waterfall(result.totex, user_reid)


def _render_totex_waterfall(totex: pd.DataFrame, user_reid: str) -> None:
    """Build-up waterfall of the new-model TOTEX for the selected company (MSEK)."""
    st.markdown("**Ny TOTEX — uppbyggnad**")

    row = totex[totex[COL_REID] == user_reid]
    if row.empty:
        st.info("Ingen TOTEX-data för valt företag.")
        return
    r = row.iloc[0]

    steps = [
        ("Påverkbara", _val(totex, user_reid, COL_CONTROLLABLE_AVG)),
        ("Förluster @ gemensamt pris", _val(totex, user_reid, COL_LOSS_VALUED)),
        ("Opåverkbara (valda)", _val(totex, user_reid, COL_NONCTRL_SELECTED)),
        ("Kapitalkostnad (justerad)", _val(totex, user_reid, COL_CAPITAL_COST_ENV_ADJ)),
    ]
    total = _val(totex, user_reid, COL_TOTEX_NEW) or 0.0

    labels = [s[0] for s in steps] + ["Ny TOTEX"]
    values = [(s[1] or 0.0) / 1e3 for s in steps] + [total / 1e3]  # tkr → MSEK
    measures = ["relative"] * len(steps) + ["total"]

    layout_kwargs, template = get_plotly_template_safe()
    fig = go.Figure(go.Waterfall(
        orientation="v",
        measure=measures,
        x=labels,
        y=values,
        connector=dict(line=dict(color=COLORS["bg_muted"])),
        increasing=dict(marker=dict(color=COLORS["primary"])),
        totals=dict(marker=dict(color=COLORS["text_primary"])),
        hovertemplate="%{x}: %{y:,.1f} MSEK<extra></extra>",
        text=[format_number(v, 1) for v in values],
        textposition="outside",
    ))
    fig.update_layout(
        **layout_kwargs,
        template=template,
        height=380,
        margin=dict(l=40, r=20, t=20, b=80),
        yaxis_title="MSEK/år",
        dragmode=False,
        xaxis=dict(fixedrange=True, linecolor=COLORS["bg_muted"]),
        yaxis=dict(fixedrange=True, gridcolor=COLORS["bg_subtle"], linecolor=COLORS["bg_muted"]),
    )
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False}, key="nb_totex_waterfall")

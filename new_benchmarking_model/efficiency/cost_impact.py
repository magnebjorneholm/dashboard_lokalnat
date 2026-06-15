"""
cost_impact.py — convert each model's efficiency requirement (%) into tkr.

The efficiency requirement is a percentage; the kronor impact is that percentage
applied to a cost base over the 4-year supervision period. The two models apply their
% to DIFFERENT bases, which is the whole point of the reform
(docs/ei_to_markdown/outputs/tillampningsmetod-effektiviseringsincitament.md):

    Current model:  % on OPEX        = controllable (påverkbara), lagged.
    New model:      % on full TOTEX  = all uncorrected cost posts.

Ei is explicit that the incentive is applied to the *uncorrected* costs even though the
benchmarking that sets the % runs on corrected costs (common-price losses,
förläggningsmiljö-levelled capex). So the capex in the new-model base is the UNADJUSTED
capital cost, not the env-adjusted one used for DEA
(ny-modell-benchmarking-elnatsreglering.md, "Korrigering görs för elområde").

The period mechanic is identical to the revenue-cap pipeline
(calculations/opex/controllable_cost_calculations.py): the annual % is applied with
compound growth over the four years and the cumulative deductions are summed.
period_efficiency_amount() reproduces the pipeline's efficiency_total exactly (asserted
in tests/test_new_benchmarking_cost_impact.py), so the current-model figure matches the
pipeline and the new model reuses the same formula on its broader base. A negative %
(a reward in the new model) yields a negative amount (an addition to the revenue cap).
"""

from __future__ import annotations

from typing import Optional

import pandas as pd

from config.column_names import (
    COL_REID, COL_CONTROLLABLE_AVG, COL_NEO_ADJUSTMENTS, COL_NONCTRL_SELECTED,
    COL_EFF_REQ_ANNUAL, COL_LOSS_ACTUAL, COL_CAPEX_PERIOD_UNADJ,
    COL_OPEX_BASE_CURRENT, COL_APPLICATION_BASE_NEW, COL_KR_CURRENT, COL_KR_NEW,
)
from new_benchmarking_model.config import (
    NONCTRL_LOSS_PURCHASED, NONCTRL_LOSS_OWN,
)
from new_benchmarking_model.totex.opex_components import compute_non_controllable_selected

SUPERVISION_YEARS = 4


def period_efficiency_amount(
    eff_req_pct: float, annual_base: float, n_years: int = SUPERVISION_YEARS
) -> float:
    """Efficiency requirement in tkr over the supervision period.

    Mirrors the revenue-cap pipeline's efficiency_total: the annual % is applied with
    compound growth (1 + r)^(t-1) each year, and the cumulative deductions are summed
    across the period — i.e. sum_{t=1..n} sum_{s=1..t} r·base·(1+r)^(s-1).

    Returns NaN if either input is NaN; handles negative r (a reward) naturally.
    """
    if pd.isna(eff_req_pct) or pd.isna(annual_base):
        return float("nan")
    cumulative = 0.0
    total = 0.0
    for t in range(1, n_years + 1):
        cumulative += eff_req_pct * annual_base * (1 + eff_req_pct) ** (t - 1)
        total += cumulative
    return total


def compute_loss_actual(non_controllable_detail: pd.DataFrame) -> pd.DataFrame:
    """Actual network losses (purchased + own production), annual avg, per company (tkr).

    The benchmarking values losses at a common price; the kr application uses the firm's
    actual loss cost. Both forecast loss categories are summed and averaged over the
    forecast years, reusing the non-controllable aggregation (cost negated to positive).
    """
    out = compute_non_controllable_selected(
        non_controllable_detail, [NONCTRL_LOSS_PURCHASED, NONCTRL_LOSS_OWN]
    )
    return out.rename(columns={COL_NONCTRL_SELECTED: COL_LOSS_ACTUAL})


def build_cost_impact(
    baseline_data,
    totex: pd.DataFrame,
    dea_new: pd.DataFrame,
    dea_current: pd.DataFrame,
    capcost: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """Per-company application bases and the kr efficiency impact for both models.

    Returns a frame keyed by REId with the loss/capex/neon building blocks, the two
    annual application bases, and the two 4-year-period kr figures. Only columns NOT
    already present in the totex frame are returned, so the orchestrator can merge it in
    without collisions. controllable_cost_average and non_controllable_selected are read
    from the totex frame and not re-emitted.
    """
    from calculations.opex.cost_aggregation import aggregate_controllable

    # Controllable + neon (the shared OPEX anchor), exactly as the pipeline computes it.
    ctrl = aggregate_controllable(
        baseline_data.controllable_detail, baseline_data.controllable_meta
    )[[COL_REID, COL_NEO_ADJUSTMENTS]]

    loss_actual = compute_loss_actual(baseline_data.non_controllable_detail)

    # Unadjusted capital cost, period sum 2024-2027 (capcost_network is constant per
    # network and equals the full-period sum across all categories and half-years).
    if capcost is None:
        from data_loaders.rab_data import load_capcost_a
        capcost = load_capcost_a()
    capex_period = capcost.groupby("id_network", as_index=False)["capcost_network"].first()
    capex_period[COL_REID] = capex_period["id_network"].apply(lambda x: f"REL{int(x):05d}")
    capex_period = capex_period.rename(
        columns={"capcost_network": COL_CAPEX_PERIOD_UNADJ}
    )[[COL_REID, COL_CAPEX_PERIOD_UNADJ]]

    # Assemble per company (controllable + selected non-ctrl come from the totex frame).
    df = totex[[COL_REID, COL_CONTROLLABLE_AVG, COL_NONCTRL_SELECTED]].copy()
    df = df.merge(ctrl, on=COL_REID, how="left")
    df = df.merge(loss_actual, on=COL_REID, how="left")
    df = df.merge(capex_period, on=COL_REID, how="left")
    for c in (COL_CONTROLLABLE_AVG, COL_NEO_ADJUSTMENTS, COL_NONCTRL_SELECTED,
              COL_LOSS_ACTUAL, COL_CAPEX_PERIOD_UNADJ):
        df[c] = df[c].fillna(0.0)

    neon_annual = df[COL_NEO_ADJUSTMENTS] / SUPERVISION_YEARS
    capex_annual = df[COL_CAPEX_PERIOD_UNADJ] / SUPERVISION_YEARS

    # Current applies on OPEX (controllable + neon); new on the full uncorrected TOTEX.
    df[COL_OPEX_BASE_CURRENT] = df[COL_CONTROLLABLE_AVG] + neon_annual
    df[COL_APPLICATION_BASE_NEW] = (
        df[COL_OPEX_BASE_CURRENT]
        + df[COL_LOSS_ACTUAL]
        + df[COL_NONCTRL_SELECTED]
        + capex_annual
    )

    cur = dea_current[[COL_REID, COL_EFF_REQ_ANNUAL]].rename(columns={COL_EFF_REQ_ANNUAL: "_cur"})
    new = dea_new[[COL_REID, COL_EFF_REQ_ANNUAL]].rename(columns={COL_EFF_REQ_ANNUAL: "_new"})
    df = df.merge(cur, on=COL_REID, how="left").merge(new, on=COL_REID, how="left")

    df[COL_KR_CURRENT] = df.apply(
        lambda r: period_efficiency_amount(r["_cur"], r[COL_OPEX_BASE_CURRENT]), axis=1)
    df[COL_KR_NEW] = df.apply(
        lambda r: period_efficiency_amount(r["_new"], r[COL_APPLICATION_BASE_NEW]), axis=1)

    return df[[
        COL_REID, COL_NEO_ADJUSTMENTS, COL_LOSS_ACTUAL, COL_CAPEX_PERIOD_UNADJ,
        COL_OPEX_BASE_CURRENT, COL_APPLICATION_BASE_NEW, COL_KR_CURRENT, COL_KR_NEW,
    ]]

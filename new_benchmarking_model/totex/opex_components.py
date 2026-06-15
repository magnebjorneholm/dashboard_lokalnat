"""
opex_components.py — the OPEX side of the new-model TOTEX.

Per what_do_we_need.md, the benchmarking OPEX is

    controllable_cost_average                       (påverkbara — reused from baseline)
  + nf_obs · k_nf · e_in                            (network losses @ a common price)
  + grid_subscription + grid_connection
  + feed_in_compensation + capacity_reserve         (selected non-controllable)
  − regulatory_fees                                 (excluded entirely)

This module computes the two *new* pieces (loss valuation and selected non-controllable)
per company; the controllable part is taken from baseline so the new and current models
share the exact same påverkbara figure (apples-to-apples comparison).

All figures are annual and in tkr.

Periodglapp (known model simplification): controllable_cost_average is the indexed
2018–2021 average, while the non-controllable items and nf_obs/e_in are the 2024–2027
forecast. We combine them as-is and annualise the forecast pieces by averaging over the
four years. This mirrors the current model, which likewise mixes a 2018–2021 OPEX
average with a 2024 capital cost.
"""

from __future__ import annotations

from typing import Dict, Iterable, Optional

import pandas as pd

from config.column_names import COL_REID, COL_LOSS_VALUED, COL_NONCTRL_SELECTED
from new_benchmarking_model.config import NewBenchmarkingConfig

# Forecast years present in the non-controllable grunddata and the adjustment variables.
FORECAST_YEARS = (2024, 2025, 2026, 2027)


def compute_loss_valued(
    incentive_df: pd.DataFrame,
    k_nf: Dict[int, float],
) -> pd.DataFrame:
    """
    Network losses valued at a common price, annualised, per company.

    loss_year [tkr] = nf_obs · k_nf[year] · e_in / 1000      (e_in in MWh, k_nf in kr/MWh)
    Returns one row per REId with the mean over the forecast years.

    `incentive_df` is the output of data_loaders.incentive_data.load_incentive_data()
    (columns include REId, year, nf_obs, e_in).
    """
    df = incentive_df[["REId", "year", "nf_obs", "e_in"]].copy()
    df = df[df["year"].isin(k_nf.keys())]
    df["nf_obs"] = pd.to_numeric(df["nf_obs"], errors="coerce").fillna(0.0)
    df["e_in"] = pd.to_numeric(df["e_in"], errors="coerce").fillna(0.0)
    df["k_nf"] = df["year"].map(k_nf)

    # kr → tkr
    df["loss_year"] = df["nf_obs"] * df["k_nf"] * df["e_in"] / 1000.0

    out = df.groupby("REId", as_index=False)["loss_year"].mean()
    return out.rename(columns={"loss_year": COL_LOSS_VALUED})


def compute_non_controllable_selected(
    detail: pd.DataFrame,
    categories: Iterable[str],
) -> pd.DataFrame:
    """
    Selected non-controllable categories, annualised, per company.

    `detail` is non_controllable_a.parquet (REId, kent_category, year, amount), where
    amount is stored negative (cost). We keep only `categories`, sum per company per
    year, negate to positive, and average over the forecast years → annual tkr.
    """
    categories = list(categories)
    df = detail[detail["kent_category"].isin(categories)].copy()

    yearly = df.groupby(["REId", "year"], as_index=False)["amount"].sum()
    yearly["amount"] = -yearly["amount"]  # negative cost → positive

    out = yearly.groupby("REId", as_index=False)["amount"].mean()
    return out.rename(columns={"amount": COL_NONCTRL_SELECTED})


def build_opex_components(
    cfg: NewBenchmarkingConfig,
    non_controllable_detail: pd.DataFrame,
    incentive_df: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """
    Per-company OPEX add-ons for the new model: loss valuation + selected non-controllable.

    Returns a DataFrame with REId, loss_valued_common_price, non_controllable_selected
    (both annual tkr). The controllable part is added later in totex.py from baseline.
    A component switched off in `cfg` contributes a zero column (stable schema).
    """
    if incentive_df is None:
        from data_loaders.incentive_data import load_incentive_data
        incentive_df = load_incentive_data()

    loss = (
        compute_loss_valued(incentive_df, cfg.resolved_k_nf())
        if cfg.include_losses
        else pd.DataFrame({COL_REID: [], COL_LOSS_VALUED: []})
    )
    nonctrl = compute_non_controllable_selected(
        non_controllable_detail, cfg.non_controllable_categories
    )

    # Outer-join on the full company set so every REId appears once.
    reids = pd.DataFrame({COL_REID: sorted(
        set(non_controllable_detail["REId"]).union(loss[COL_REID])
    )})
    out = reids.merge(loss, on=COL_REID, how="left").merge(nonctrl, on=COL_REID, how="left")
    out[COL_LOSS_VALUED] = out[COL_LOSS_VALUED].fillna(0.0)
    out[COL_NONCTRL_SELECTED] = out[COL_NONCTRL_SELECTED].fillna(0.0)
    return out

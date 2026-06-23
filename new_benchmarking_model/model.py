"""
model.py — orchestrator for the new benchmarking model.

Builds new-model TOTEX for all 148 companies, runs DEA on it (single input + new
outputs incl. ledningslängd), and compares the resulting efficiency and efficiency
requirement against the current model. The current side is read directly from Ei's
published baseline (EIs_DEA.xlsx / baseline_data.dea_results) — the firm's actual
"föregående värden" — not recomputed, matching how the rest of the app treats the
baseline. Only the new model runs a DEA pass.

    run_new_benchmarking(cfg) -> NewBenchmarkingResult

Everything downstream (UI) should read from the returned dataclass; this module is the
single entry point for the add-on.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import pandas as pd

from config.column_names import (
    COL_REID, COL_CU, COL_MW, COL_NS, COL_MWH_LOW, COL_MWH_HIGH,
    COL_OPEXP_DEA, COL_TOTEX_NEW, COL_CABLE_LENGTH_KM,
    COL_DEA_EFFICIENCY, COL_DEA_POTENTIAL, COL_IS_OUTLIER, COL_EFF_REQ_ANNUAL,
    COL_DEA_EFFICIENCY_NEW, COL_DEA_EFFICIENCY_CURRENT,
    COL_POTENTIAL_NEW, COL_POTENTIAL_CURRENT,
    COL_IS_OUTLIER_NEW, COL_IS_OUTLIER_CURRENT,
    COL_EFF_REQ_NEW, COL_EFF_REQ_CURRENT,
    COL_EFF_REQ_DELTA, COL_EFFICIENCY_DELTA,
)
from calculations.frontier.dea_calculations import run_dea_analysis
from new_benchmarking_model.efficiency.efficiency_requirement_two_sided import (
    calculate_two_sided_requirement,
)

from new_benchmarking_model.config import NewBenchmarkingConfig
from new_benchmarking_model.totex.capex_environment import (
    compute_env_adjusted_capital_cost, EnvCapexResult,
)
from new_benchmarking_model.totex.opex_components import build_opex_components
from new_benchmarking_model.totex.totex import build_totex
from new_benchmarking_model.efficiency.cost_impact import build_cost_impact
from new_benchmarking_model.components.cable_length import (
    load_cable_components, aggregate_cable_length_per_firm, C as cable_C,
)


@dataclass(frozen=True)
class NewBenchmarkingResult:
    """Everything one run produces."""
    comparison: pd.DataFrame        # per REId: new vs current efficiency / eff-req + deltas
    totex: pd.DataFrame             # per REId: TOTEX components and totals
    new_model_inputs: pd.DataFrame  # per REId: the DEA input (totex_new) and all outputs used
    new_model_outputs: List[str]    # names of the DEA output columns used in the new model
    dea_new: pd.DataFrame           # new-model DEA + eff-req
    dea_current: pd.DataFrame       # current model, read directly from EIs_DEA.xlsx
    env_capex: EnvCapexResult       # förläggningsmiljö diagnostics + adjusted capital cost
    config: NewBenchmarkingConfig


def _build_cable_outputs(cfg: NewBenchmarkingConfig) -> tuple[pd.DataFrame, List[str]]:
    """Cable-length DEA output(s) per company; returns (frame keyed by REId, output cols)."""
    comp = load_cable_components()
    if not cfg.split_by_voltage:
        agg = aggregate_cable_length_per_firm(comp, include_types=cfg.cable_types)
        agg = agg.rename(columns={cable_C.COL_KM_TOTAL: COL_CABLE_LENGTH_KM})
        return agg[[COL_REID, COL_CABLE_LENGTH_KM]], [COL_CABLE_LENGTH_KM]

    agg = aggregate_cable_length_per_firm(comp, include_types=cfg.cable_types, split_by_voltage=True)
    wide = (
        agg.pivot(index=cable_C.COL_REID, columns=cable_C.COL_VOLTAGE_LEVEL,
                  values=cable_C.COL_KM_TOTAL)
        .fillna(0.0)
        .reset_index()
    )
    out_cols = []
    for lvl in [c for c in wide.columns if c != COL_REID]:
        col = f"{COL_CABLE_LENGTH_KM}_{lvl}"
        wide = wide.rename(columns={lvl: col})
        if wide[col].sum() > 0:           # an all-zero output would not constrain DEA
            out_cols.append(col)
    return wide, out_cols


def run_new_benchmarking(
    cfg: Optional[NewBenchmarkingConfig] = None,
    baseline_data=None,
    capbase: Optional[pd.DataFrame] = None,
) -> NewBenchmarkingResult:
    """
    Run the full new-benchmarking comparison for all 148 companies.

    Args:
        cfg: parameters (defaults reproduce the reference reading).
        baseline_data: optional pre-loaded BaselineData (else loaded here).
        capbase: optional pre-loaded capbase_a (else loaded inside the capex step).
    """
    cfg = cfg or NewBenchmarkingConfig()

    if baseline_data is None:
        from data_loaders.baseline_data import load_baseline_data
        baseline_data = load_baseline_data()
    baseline_df = baseline_data.df_all_companies

    # 1. OPEX add-ons + förläggningsmiljö-adjusted capex → TOTEX
    opex_components = build_opex_components(cfg, baseline_data.non_controllable_detail)
    env_capex = compute_env_adjusted_capital_cost(cfg, capbase=capbase, wacc=baseline_data.wacc)
    totex = build_totex(cfg, baseline_df, opex_components, env_capex.capital_cost)

    # 2. New-model DEA: single TOTEX input + base outputs (+ cable length)
    new_outputs = list(cfg.new_base_outputs)
    # Carry opexp_dea into new_model_inputs so the offline decomposition analysis can read
    # the frontier payable post straight from the bundle (the DEA input itself is totex_new).
    new_df = totex[[COL_REID, COL_TOTEX_NEW]].merge(
        baseline_df[[COL_REID, COL_OPEXP_DEA, COL_CU, COL_MW, COL_NS, COL_MWH_LOW, COL_MWH_HIGH]],
        on=COL_REID, how="left",
    )
    if cfg.include_cable_length:
        cable_out, cable_cols = _build_cable_outputs(cfg)
        new_df = new_df.merge(cable_out, on=COL_REID, how="left")
        for c in cable_cols:
            new_df[c] = new_df[c].fillna(0.0)
        new_outputs += cable_cols

    dea_spec = {"inputs": [COL_TOTEX_NEW], "outputs": new_outputs, "rts": cfg.rts}
    if cfg.exclude_reids:
        # Force Ei's DEA-unsuitable firms out of the reference set (still reported).
        dea_spec["forced_outliers"] = new_df[COL_REID].isin(cfg.exclude_reids).to_numpy()
    dea_new = run_dea_analysis(new_df, dea_spec)
    dea_new = calculate_two_sided_requirement(
        dea_new,
        reference_percentile=cfg.reference_percentile,
        gap_cap=cfg.gap_cap,
        sharing=cfg.sharing,
        realization_time=cfg.realization_time,
        supervision_period=cfg.supervision_period,
    )

    # 3. Current model = Ei's published baseline (EIs_DEA.xlsx), read directly — the firm's
    #    actual "föregående värden". No recomputation: efficiency, potential, outlier flag
    #    and the official efficiency requirement (Effkrav_proc) all come straight from there.
    dea_current = baseline_data.dea_results[
        [COL_REID, COL_DEA_EFFICIENCY, COL_DEA_POTENTIAL, COL_IS_OUTLIER, COL_EFF_REQ_ANNUAL]
    ].copy()

    # 4. Cost impact: each model's efficiency requirement in tkr (current on the OPEX
    #    base, new on the full uncorrected TOTEX base). Merged onto the totex frame so
    #    the UI reads bases and kr from one place.
    cost_impact = build_cost_impact(baseline_data, totex, dea_new, dea_current)
    totex = totex.merge(cost_impact, on=COL_REID, how="left")

    # 5. Comparison table
    comparison = _build_comparison(dea_new, dea_current)

    return NewBenchmarkingResult(
        comparison=comparison,
        totex=totex,
        new_model_inputs=new_df,
        new_model_outputs=new_outputs,
        dea_new=dea_new,
        dea_current=dea_current,
        env_capex=env_capex,
        config=cfg,
    )


def _build_comparison(dea_new: pd.DataFrame, dea_current: pd.DataFrame) -> pd.DataFrame:
    """New vs current efficiency / potential / outlier / eff-req, with deltas (new − current)."""
    new = dea_new[[COL_REID, COL_DEA_EFFICIENCY, COL_DEA_POTENTIAL, COL_IS_OUTLIER, COL_EFF_REQ_ANNUAL]].rename(
        columns={
            COL_DEA_EFFICIENCY: COL_DEA_EFFICIENCY_NEW,
            COL_DEA_POTENTIAL: COL_POTENTIAL_NEW,
            COL_IS_OUTLIER: COL_IS_OUTLIER_NEW,
            COL_EFF_REQ_ANNUAL: COL_EFF_REQ_NEW,
        }
    )
    cur = dea_current[[COL_REID, COL_DEA_EFFICIENCY, COL_DEA_POTENTIAL, COL_IS_OUTLIER, COL_EFF_REQ_ANNUAL]].rename(
        columns={
            COL_DEA_EFFICIENCY: COL_DEA_EFFICIENCY_CURRENT,
            COL_DEA_POTENTIAL: COL_POTENTIAL_CURRENT,
            COL_IS_OUTLIER: COL_IS_OUTLIER_CURRENT,
            COL_EFF_REQ_ANNUAL: COL_EFF_REQ_CURRENT,
        }
    )
    out = new.merge(cur, on=COL_REID, how="outer")
    out[COL_EFFICIENCY_DELTA] = out[COL_DEA_EFFICIENCY_NEW] - out[COL_DEA_EFFICIENCY_CURRENT]
    out[COL_EFF_REQ_DELTA] = out[COL_EFF_REQ_NEW] - out[COL_EFF_REQ_CURRENT]
    return out

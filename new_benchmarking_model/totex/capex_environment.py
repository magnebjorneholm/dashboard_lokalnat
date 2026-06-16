"""
capex_environment.py — consolidated förläggningsmiljö (placement-environment) capex
correction for the new benchmarking model.

The two existing per-asset packages (jordkabel = cat_encode 3, nätstation = cat_encode 13)
each level a company's capital base down to a reference environment and expose a
per-component `deduction` [SEK] on the column `value`, where `value == nuav_2022`.

Because KENT capital cost is *linear* in `nuav_2022` (see calculations/capex/
kent_calculations.py), the exact way to push the correction through to capital cost is:

    1. subtract each component's deduction from its `nuav_2022` in capbase_a, then
    2. re-run KENT (steps 5–8) on the corrected capbase.

This module does exactly that and returns the förläggningsmiljö-adjusted
`capital_cost_2024` per company (REId), ready to enter TOTEX.

It reuses the substantive logic of the two packages (classify_env, calibrate,
apply_environment_adjustment) verbatim; only the component-loading is re-done here so
the original capbase_a index is preserved and the deduction can be mapped back exactly.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pandas as pd

from calculations.capex.kent_calculations import run_kent_calculations_batch
from calculations.capex.wacc_calculations import BASELINE_WACC
from data_loaders.rab_data import load_capbase_a

from new_benchmarking_model.config import NewBenchmarkingConfig
from new_benchmarking_model.components.environment_capex_adjustment import (
    config as env_C,
    data as env_data,
    calibration as env_calib,
    adjustment as env_adj,
)
from new_benchmarking_model.components.station_capex_adjustment import (
    config as st_C,
    data as st_data,
    calibration as st_calib,
    adjustment as st_adj,
)

from config.column_names import (
    COL_REID, COL_CAPITAL_COST_ENV_ADJ, COL_CAPEX_CORR_CABLE, COL_CAPEX_CORR_STATION,
)

CAPBASE_NUAV_COL = "nuav_2022"


@dataclass(frozen=True)
class EnvCapexResult:
    """Förläggningsmiljö-adjusted capital cost plus the two correction diagnostics."""
    capital_cost: pd.DataFrame          # REId, capital_cost_2024_env_adjusted
    cable_adjustment: env_adj.EnvironmentAdjustmentResult
    station_adjustment: st_adj.EnvironmentAdjustmentResult


def _resolve(columns, fragment: str) -> str:
    """First column whose name contains `fragment` (handles non-UTF8 capbase names)."""
    for col in columns:
        if fragment in col:
            return col
    raise KeyError(f"No column containing {fragment!r} in {list(columns)}")


def _cable_components_indexed(capbase: pd.DataFrame) -> pd.DataFrame:
    """load_jordkabel_components, but on an in-memory capbase and keeping its index."""
    unit_price_col = _resolve(capbase.columns, env_C.FRAG_UNIT_PRICE)
    cable = capbase[capbase["cat_encode"] == env_C.CABLE_CAT_ENCODE]
    df = pd.DataFrame(
        {
            env_C.COL_REID: cable["id_network_string"].astype(str),
            env_C.COL_ID_NETWORK: cable["id_network"],
            env_C.COL_TECHSPEC: cable[env_C.COL_TECHSPEC].astype(str).str.strip(),
            env_C.COL_VOLT: cable[env_C.COL_VOLT].astype(str).str.strip(),
            env_C.COL_ENV: cable[env_C.COL_SUBCAT].map(env_data.classify_env),
            env_C.COL_KM: pd.to_numeric(cable["count_comp"], errors="coerce"),
            env_C.COL_UNIT_PRICE: pd.to_numeric(cable[unit_price_col], errors="coerce"),
            env_C.COL_VALUE: pd.to_numeric(cable[CAPBASE_NUAV_COL], errors="coerce"),
        },
        index=cable.index,
    )
    return df[(df[env_C.COL_KM] > 0) & df[env_C.COL_UNIT_PRICE].notna()]


def _station_components_indexed(capbase: pd.DataFrame) -> pd.DataFrame:
    """load_station_components, but on an in-memory capbase and keeping its index."""
    unit_price_col = _resolve(capbase.columns, st_C.FRAG_UNIT_PRICE)
    station = capbase[capbase["cat_encode"] == st_C.STATION_CAT_ENCODE]
    df = pd.DataFrame(
        {
            st_C.COL_REID: station["id_network_string"].astype(str),
            st_C.COL_ID_NETWORK: station["id_network"],
            st_C.COL_TECHSPEC: station[st_C.COL_TECHSPEC].astype(str).str.strip(),
            st_C.COL_VOLT: station[st_C.COL_VOLT].astype(str).str.strip(),
            st_C.COL_ENV: station[st_C.COL_TECHSPEC].map(st_data.classify_env),
            st_C.COL_COUNT: pd.to_numeric(station["count_comp"], errors="coerce"),
            st_C.COL_UNIT_PRICE: pd.to_numeric(station[unit_price_col], errors="coerce"),
            st_C.COL_VALUE: pd.to_numeric(station[CAPBASE_NUAV_COL], errors="coerce"),
        },
        index=station.index,
    )
    return df[df[st_C.COL_VALUE].notna()]


def _cable_result(capbase: pd.DataFrame, cfg: NewBenchmarkingConfig) -> env_adj.EnvironmentAdjustmentResult:
    comp = _cable_components_indexed(capbase)
    return env_adj.apply_environment_adjustment(
        comp, env_calib.calibrate(comp),
        method=cfg.cable_method, override_percent=cfg.cable_override_percent,
    )


def _station_result(capbase: pd.DataFrame, cfg: NewBenchmarkingConfig) -> st_adj.EnvironmentAdjustmentResult:
    comp = _station_components_indexed(capbase)
    return st_adj.apply_environment_adjustment(
        comp, st_calib.calibrate(comp),
        method=cfg.station_method, override_percent=cfg.station_override_percent,
    )


def _subtract_deductions(capbase: pd.DataFrame, results) -> pd.DataFrame:
    """Copy of `capbase` with each result's per-component deduction subtracted from nuav_2022."""
    adjusted = capbase.copy()
    for res in results:
        ded = res.components[env_C.COL_DEDUCTION]
        adjusted.loc[ded.index, CAPBASE_NUAV_COL] = (
            adjusted.loc[ded.index, CAPBASE_NUAV_COL] - ded.to_numpy()
        )
    return adjusted


def build_adjusted_capbase(
    capbase: pd.DataFrame,
    cable_res: env_adj.EnvironmentAdjustmentResult,
    station_res: st_adj.EnvironmentAdjustmentResult,
) -> pd.DataFrame:
    """
    Return a copy of `capbase` with `nuav_2022` reduced to the förläggningsmiljö
    reference level for jordkabel (cat 3) and nätstation (cat 13).

    Exact: adjusted nuav_2022 = value − deduction, where value == nuav_2022, so the
    per-component deduction is simply subtracted from the matching capbase row. cat 3
    and cat 13 are disjoint, so the two index sets never overlap.
    """
    return _subtract_deductions(capbase, (cable_res, station_res))


def _kent_capital_cost(capbase: pd.DataFrame, wacc: float) -> pd.Series:
    """Run KENT (steps 5–8) on a capbase and return capital_cost_2024 per REId."""
    _, df_network, _ = run_kent_calculations_batch(capbase, wacc=wacc, return_detailed=False)
    reid = df_network["id_network"].apply(lambda x: f"REL{int(x):05d}")
    return pd.Series(df_network["capital_cost_2024"].to_numpy(), index=reid.to_numpy())


def compute_env_adjusted_capital_cost(
    cfg: NewBenchmarkingConfig,
    capbase: Optional[pd.DataFrame] = None,
    wacc: float = BASELINE_WACC,
) -> EnvCapexResult:
    """
    Förläggningsmiljö-adjusted `capital_cost_2024` per company.

    Runs KENT (steps 5–8) on the corrected capbase for all companies and maps the
    network-level result to REId. When `cfg.include_capex` is False the correction is
    skipped and KENT runs on the unmodified capbase (so the model can isolate the OPEX
    side); the diagnostics are still computed and the column keeps the *_env_adjusted name.

    For the bridge visualisation, the capital-cost correction is also split into its cable
    and station parts (COL_CAPEX_CORR_CABLE / _STATION). Because KENT is linear in nuav and
    the two asset sets are disjoint, the split is exact and additive: re-running KENT on the
    unadjusted and cable-only capbases gives cable = KENT(cable) − KENT(unadjusted) and
    station = KENT(both) − KENT(cable). This costs two extra KENT passes and is used only by
    the waterfall — the DEA input and all cost bases are unaffected.
    """
    if capbase is None:
        capbase = load_capbase_a()

    cable_res = _cable_result(capbase, cfg)
    station_res = _station_result(capbase, cfg)

    adjusted = build_adjusted_capbase(capbase, cable_res, station_res) if cfg.include_capex else capbase
    cc_both = _kent_capital_cost(adjusted, wacc)

    if cfg.include_capex:
        cc_unadj = _kent_capital_cost(capbase, wacc)
        cc_cable = _kent_capital_cost(_subtract_deductions(capbase, (cable_res,)), wacc)
        cable_corr = (cc_cable - cc_unadj).reindex(cc_both.index)
        station_corr = (cc_both - cc_cable).reindex(cc_both.index)
    else:
        cable_corr = pd.Series(0.0, index=cc_both.index)
        station_corr = pd.Series(0.0, index=cc_both.index)

    capital_cost = pd.DataFrame({
        COL_REID: cc_both.index.to_numpy(),
        COL_CAPITAL_COST_ENV_ADJ: cc_both.to_numpy(),
        COL_CAPEX_CORR_CABLE: cable_corr.to_numpy(),
        COL_CAPEX_CORR_STATION: station_corr.to_numpy(),
    })

    return EnvCapexResult(
        capital_cost=capital_cost,
        cable_adjustment=cable_res,
        station_adjustment=station_res,
    )

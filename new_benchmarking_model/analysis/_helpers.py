"""
_helpers.py — shared scaffolding for the TOTEX/CAPEX-vs-benchmarking analysis.

Built incrementally per temp/PLAN.md. Step 1 adds the bundle reader and the
`analysis_df` spine (one row per REId). Later steps append urban proxies (step 2),
the variant-DEA runner (step 3), etc.

Pure read of the committed bundle (new_benchmarking_model/data/precomputed/), plus the
light company-name CSV. No DEA, no KENT, no Streamlit — fail-loud, not the app loader.

Unit conventions (important, see PLAN "Implementationsnoter"):
  * cost parts (controllable, loss_valued, nonctrl_selected, capex_*, opex_new,
    totex_*, kr_*) are ANNUAL tkr (kr_* are 4-year period sums in tkr).
  * cable_ded / station_ded are SEK on the NUAV capital base (förläggningsmiljö
    deduction), a DIFFERENT layer from capex_cut (annual capital-cost tkr). They do
    NOT sum-reconcile with capex_cut. The clean cross-company comparable is the
    unitless cable_eff_pct / station_eff_pct (deduction / value).
  * req_* are signed decimals (×100 for %/yr); d_req_pp is in percentage points.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from config.column_names import (  # noqa: E402
    COL_REID,
    COL_CONTROLLABLE_AVG, COL_OPEXP_DEA, COL_LOSS_VALUED, COL_NONCTRL_SELECTED,
    COL_NONCTRL_GRID_SUBSCRIPTION, COL_NONCTRL_GRID_CONNECTION,
    COL_NONCTRL_FEED_IN, COL_NONCTRL_CAPACITY_RESERVE,
    COL_CAPITAL_COST_2024, COL_CAPITAL_COST_ENV_ADJ, COL_OPEX_NEW, COL_TOTEX_NEW,
    COL_DEA_EFFICIENCY, COL_EFF_REQ_ANNUAL, COL_DEA_REFERENCE,
    COL_KR_NEW, COL_KR_CURRENT,
    COL_CU, COL_MW, COL_NS, COL_MWH_LOW, COL_MWH_HIGH, COL_CABLE_LENGTH_KM,
    COL_APPLICATION_BASE_NEW,
)
from new_benchmarking_model.ui.charts import outcome_kind  # noqa: E402
from new_benchmarking_model.config import (  # noqa: E402
    NewBenchmarkingConfig, NEW_MODEL_BASE_OUTPUTS,
)
from calculations.frontier.dea_calculations import run_dea_analysis  # noqa: E402
from new_benchmarking_model.efficiency.efficiency_requirement_two_sided import (  # noqa: E402
    calculate_two_sided_requirement,
)
from new_benchmarking_model.efficiency.cost_impact import period_efficiency_amount  # noqa: E402
from new_benchmarking_model.components.cable_length import (  # noqa: E402
    load_cable_components, aggregate_cable_length_per_firm, C as cableC,
)
from new_benchmarking_model.components.environment_capex_adjustment.data import (  # noqa: E402
    load_jordkabel_components,
)
from new_benchmarking_model.components.environment_capex_adjustment.calibration import (  # noqa: E402
    calibrate,
)
from new_benchmarking_model.components.environment_capex_adjustment import config as envC  # noqa: E402

BUNDLE_DIR = REPO_ROOT / "new_benchmarking_model" / "data" / "precomputed"
NAMES_CSV = REPO_ROOT / "data" / "reference" / "company_names.csv"
OUT_DIR = Path(__file__).resolve().parent / "out"

_BUNDLE_FRAMES = (
    "dea_new", "dea_current", "comparison", "totex", "new_model_inputs",
    "env_cable_per_company", "env_station_per_company",
)


def read_bundle() -> dict[str, pd.DataFrame]:
    """Read every committed bundle frame. Fail loud if one is missing."""
    frames = {}
    for name in _BUNDLE_FRAMES:
        path = BUNDLE_DIR / f"{name}.parquet"
        if not path.exists():
            raise FileNotFoundError(f"Bundle frame missing: {path}")
        frames[name] = pd.read_parquet(path)
    return frames


def _rank_desc(s: pd.Series) -> pd.Series:
    """Rank by efficiency, 1 = most efficient. Ties share the min rank."""
    return s.rank(ascending=False, method="min").astype("Int64")


def load_analysis_df() -> pd.DataFrame:
    """Build the analysis spine: one row per REId, all bundle-derived columns.

    Returns the spine with PLAN's friendly aliases. Urban columns (step 2) are added
    later. NaN in cable_*/station_* is meaningful: a company with no förläggningsmiljö
    cable/station adjustment is absent from those per-company frames.
    """
    b = read_bundle()
    names = pd.read_csv(NAMES_CSV)[[COL_REID, "name_short"]]

    # ── cost parts + kr (totex frame) ────────────────────────────────────────
    totex = b["totex"].rename(columns={
        COL_CONTROLLABLE_AVG: "controllable",
        COL_OPEXP_DEA: "opexp_dea",
        COL_LOSS_VALUED: "loss_valued",
        COL_NONCTRL_SELECTED: "nonctrl_selected",
        COL_NONCTRL_GRID_SUBSCRIPTION: "grid_subscription",
        COL_NONCTRL_GRID_CONNECTION: "grid_connection",
        COL_NONCTRL_FEED_IN: "feed_in",
        COL_NONCTRL_CAPACITY_RESERVE: "capacity_reserve",
        COL_CAPITAL_COST_2024: "capex_unadj",
        COL_CAPITAL_COST_ENV_ADJ: "capex_adj",
        COL_OPEX_NEW: "opex_new",
        COL_TOTEX_NEW: "totex_new",
        COL_KR_NEW: "kr_new",
        COL_KR_CURRENT: "kr_cur",
    })[[
        COL_REID, "controllable", "opexp_dea", "loss_valued", "nonctrl_selected",
        "grid_subscription", "grid_connection", "feed_in", "capacity_reserve",
        "capex_unadj", "capex_adj", "opex_new", "totex_new", "kr_new", "kr_cur",
        COL_APPLICATION_BASE_NEW,
    ]]

    # ── new-model outcome (dea_new) ──────────────────────────────────────────
    dn = b["dea_new"].rename(columns={
        COL_DEA_EFFICIENCY: "eff_new",
        COL_EFF_REQ_ANNUAL: "req_new_pct",
        COL_DEA_REFERENCE: "e75",
    })[[COL_REID, "eff_new", "req_new_pct", "e75"]]

    # ── current-model outcome (dea_current) ──────────────────────────────────
    dc = b["dea_current"].rename(columns={
        COL_DEA_EFFICIENCY: "eff_cur",
        COL_EFF_REQ_ANNUAL: "req_cur_pct",
    })[[COL_REID, "eff_cur", "req_cur_pct"]]

    # ── DEA outputs (new_model_inputs) ───────────────────────────────────────
    out_cols = [COL_CU, COL_MW, COL_NS, COL_MWH_LOW, COL_MWH_HIGH, COL_CABLE_LENGTH_KM]
    outputs = b["new_model_inputs"][[COL_REID, *out_cols]]

    # ── env capex corrections (SEK / unitless; see module docstring) ─────────
    cable = b["env_cable_per_company"].rename(columns={
        "deduction": "cable_ded", "effective_pct": "cable_eff_pct",
    })[[COL_REID, "cable_ded", "cable_eff_pct"]]
    station = b["env_station_per_company"].rename(columns={
        "deduction": "station_ded", "effective_pct": "station_eff_pct",
    })[[COL_REID, "station_ded", "station_eff_pct"]]

    # ── assemble (totex is the 148-row backbone; left joins preserve it) ──────
    df = (
        totex
        .merge(names, on=COL_REID, how="left")
        .merge(dn, on=COL_REID, how="left")
        .merge(dc, on=COL_REID, how="left")
        .merge(outputs, on=COL_REID, how="left")
        .merge(cable, on=COL_REID, how="left")     # NaN = no cable env adjustment
        .merge(station, on=COL_REID, how="left")   # NaN = no station env adjustment
    )

    # ── derived columns ──────────────────────────────────────────────────────
    df["totex_unadj"] = df["opex_new"] + df["capex_unadj"]
    df["capex_cut"] = df["capex_unadj"] - df["capex_adj"]
    # Guard div-by-zero: REL00024 has capex_unadj=0 but capex_adj>0 (a source anomaly),
    # which would give -inf. Leave the pct NaN there rather than poison downstream stats.
    df["capex_cut_pct"] = (df["capex_cut"] / df["capex_unadj"]).replace(
        [float("inf"), float("-inf")], float("nan")
    )
    df["gap"] = df["e75"] - df["eff_new"]
    df["kind"] = df["req_new_pct"].map(outcome_kind)
    df["rank_new"] = _rank_desc(df["eff_new"])
    df["rank_cur"] = _rank_desc(df["eff_cur"])
    df["d_eff"] = df["eff_new"] - df["eff_cur"]
    df["d_rank"] = df["rank_new"] - df["rank_cur"]
    df["d_req_pp"] = (df["req_new_pct"] - df["req_cur_pct"]) * 100.0
    df["d_kr"] = df["kr_new"] - df["kr_cur"]

    # ── column order: id → cost parts → capex-corr → new → current → deltas → outputs
    cols = [
        COL_REID, "name_short",
        "controllable", "opexp_dea", "loss_valued", "nonctrl_selected",
        "grid_subscription", "grid_connection", "feed_in", "capacity_reserve",
        "capex_unadj", "capex_adj", "opex_new", "totex_new", "totex_unadj",
        COL_APPLICATION_BASE_NEW,
        "capex_cut", "capex_cut_pct",
        "cable_ded", "cable_eff_pct", "station_ded", "station_eff_pct",
        "eff_new", "rank_new", "req_new_pct", "kr_new", "e75", "gap", "kind",
        "eff_cur", "rank_cur", "req_cur_pct", "kr_cur",
        "d_eff", "d_rank", "d_req_pp", "d_kr",
        COL_CU, COL_MW, COL_NS, COL_MWH_LOW, COL_MWH_HIGH, COL_CABLE_LENGTH_KM,
    ]
    return df[cols].sort_values(COL_REID).reset_index(drop=True)


# ─────────────────────────────────────────────────────────────────────────────
# Step 2 — urban proxies (light live: capbase reads + calibration, no DEA/KENT)
# ─────────────────────────────────────────────────────────────────────────────

def _km_by_type(comp: pd.DataFrame, ledningstyp: str, name: str) -> pd.DataFrame:
    """Per-REId km for one line type, column renamed to `name`."""
    out = aggregate_cable_length_per_firm(comp, include_types=[ledningstyp])
    return out.rename(columns={cableC.COL_KM_TOTAL: name})


def urban_components() -> pd.DataFrame:
    """Per-REId physical km pieces for the urban proxies.

    From the line-type loader: jordkabel_km, luftledning_km (ledningstyp).
    From the env loader (cat_encode==3 cable, env-classified): city_km, tatort_km,
    lb_km (landsbygd normal + svår). Luftledning carries no env label by construction,
    so the urban km come from jordkabel only — the index is a descriptor, not a share.
    """
    comp = load_cable_components()
    jk = _km_by_type(comp, cableC.JORDKABEL, "jordkabel_km")
    luft = _km_by_type(comp, cableC.LUFTLEDNING, "luftledning_km")

    jc = load_jordkabel_components()
    env_km = (
        jc.groupby([COL_REID, envC.COL_ENV])[envC.COL_KM].sum()
        .unstack(fill_value=0.0)
    )
    env_km["city_km"] = env_km.get(envC.CITY, 0.0)
    env_km["tatort_km"] = env_km.get(envC.TATORT, 0.0)
    env_km["lb_km"] = env_km.get(envC.LB_NORMAL, 0.0) + env_km.get(envC.LB_SVAR, 0.0)
    env_km = env_km[["city_km", "tatort_km", "lb_km"]].reset_index()

    return jk.merge(luft, on=COL_REID, how="outer").merge(env_km, on=COL_REID, how="outer")


def urban_weights(basis: str = "percent") -> tuple[float, float]:
    """(w_city, w_tatort) derived from the jordkabel premium structure.

    w_city = 1; w_tatort = premium[tatort] / premium[city], on the calibrated installed
    mix. basis='percent' (share of value, main) or 'sek_per_km' (additive, sensitivity).
    Landsbygd sits at the 0-level (not weighted into the index).
    """
    cal = calibrate(load_jordkabel_components())
    w = cal.percent if basis == "percent" else cal.sek_per_km
    return 1.0, w[envC.TATORT] / w[envC.CITY]


def add_urban_proxies(df: pd.DataFrame, basis: str = "percent") -> pd.DataFrame:
    """Augment the spine with the three urban measures + validation shares.

    Core measures (PLAN step 2): density_cu_km, jordkabel_share, urbanity_index.
    Validation shares: luftledning_share, jordkabel_landsbygd_share.
    All denominators use the spine's cable_length_km (electrical total, excl. optokabel)
    so the measures stay consistent with the DEA cable-length output.
    """
    w_city, w_tatort = urban_weights(basis)
    feats = urban_components()
    df = df.merge(feats, on=COL_REID, how="left")
    for c in ["jordkabel_km", "luftledning_km", "city_km", "tatort_km", "lb_km"]:
        df[c] = df[c].fillna(0.0)

    km_total = df[COL_CABLE_LENGTH_KM]
    df["density_cu_km"] = df[COL_CU] / km_total
    df["jordkabel_share"] = df["jordkabel_km"] / km_total
    df["luftledning_share"] = df["luftledning_km"] / km_total
    df["urbanity_index"] = (w_city * df["city_km"] + w_tatort * df["tatort_km"]) / km_total
    # landsbygd share of jordkabel (NaN where a company has no jordkabel)
    df["jordkabel_landsbygd_share"] = (df["lb_km"] / df["jordkabel_km"]).where(df["jordkabel_km"] > 0)
    return df


# ─────────────────────────────────────────────────────────────────────────────
# Step 3 — variant DEA runner (heavy live: one DEA + two-sided requirement per call)
# ─────────────────────────────────────────────────────────────────────────────

def run_variant(
    spine: pd.DataFrame,
    input_col: str,
    output_cols: list[str],
    *,
    cfg: NewBenchmarkingConfig | None = None,
    base_col: str = COL_APPLICATION_BASE_NEW,
) -> pd.DataFrame:
    """Run one DEA variant and return per-REId outcome (eff, signed req, kr).

    A thin wrapper around run_dea_analysis + calculate_two_sided_requirement that takes
    a TOTEX input column and an output list, both read straight off the spine (pure
    arithmetic, no KENT). Uses the same forced exclusion (cfg.exclude_reids) and locked
    two-sided params as the main model, so a variant is directly comparable to it. kr is
    period_efficiency_amount(req, base_col) on the constant application base.
    """
    cfg = cfg or NewBenchmarkingConfig()
    frame = spine[[COL_REID, input_col, *output_cols]].copy()

    spec = {"inputs": [input_col], "outputs": list(output_cols), "rts": cfg.rts}
    if cfg.exclude_reids:
        spec["forced_outliers"] = frame[COL_REID].isin(cfg.exclude_reids).to_numpy()

    dea = run_dea_analysis(frame, spec)
    dea = calculate_two_sided_requirement(
        dea,
        reference_percentile=cfg.reference_percentile, gap_cap=cfg.gap_cap,
        sharing=cfg.sharing, realization_time=cfg.realization_time,
        supervision_period=cfg.supervision_period,
    )

    base = spine.set_index(COL_REID)[base_col]
    out = dea[[COL_REID, COL_DEA_EFFICIENCY, COL_EFF_REQ_ANNUAL]].copy()
    out["kr"] = [
        period_efficiency_amount(r, base.get(rid))
        for rid, r in zip(out[COL_REID], out[COL_EFF_REQ_ANNUAL])
    ]
    return out.rename(columns={COL_DEA_EFFICIENCY: "eff", COL_EFF_REQ_ANNUAL: "req"})

"""
engine.py — the parametrised decomposition core (value grid → Shapley + endpoints + outer layer).

One call to `compute_grids(spine, outlier_mode, cfg)` solves the 2^7 = 128 DEA subsets ONCE
for a given outlier mode and returns *both* outcome grids (efficiency and the two-sided
requirement) — the two share the same DEA solve, so the cost is 128 solves per mode, not per
outcome. `decompose(spine, grid, outcome, ...)` then derives the Shapley attribution, the
leave-one-out / add-one-in endpoints and the phase-1 outer layer for one outcome.

Outcome:
    "eff"  v(S) = capped DEA efficiency min(θ,1) in [0,1]   (φ>0 = raises efficiency = favours firm)
    "req"  v(S) = signed two-sided requirement in pp        (φ<0 = lowers requirement = favours firm)

Outlier mode:
    "dynamic"  each subset re-runs the iterative super-eff + IQR detection (max_rounds=None);
               the outlier set, and therefore E75, can differ between subsets.
    "frozen"   the full-model outlier set is fixed once and forced out of the reference/E75 in
               every subset (no per-subset re-detection). The 3 Ei-excluded firms stay unscored;
               any other frozen outlier is still scored against the fixed reference, so the same
               145 firms are scored in both modes and the two are directly comparable.

The frontier payable post is opexp_dea (see players.py / totex.py); the requirement base
(controllable_cost_average) is on the kr side and is untouched here.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from math import factorial
from typing import Dict, FrozenSet, List, Optional

import numpy as np
import pandas as pd

from config.column_names import (
    COL_REID, COL_DEA_EFFICIENCY, COL_DEA_POTENTIAL, COL_IS_OUTLIER,
    COL_EFF_REQ_ANNUAL,
)
from calculations.frontier.dea_calculations import run_dea_analysis
from calculations.frontier.outliers import super_eff_scores
from calculations.efficiency.efficiency_requirement import calculate_eff_req_for_dataframe
from new_benchmarking_model.config import NewBenchmarkingConfig
from new_benchmarking_model.efficiency.efficiency_requirement_two_sided import (
    calculate_two_sided_requirement, reference_efficiency,
)
from new_benchmarking_model.analysis.decomp.players import (
    PLAYERS, N_PLAYERS, BASE_OUTPUTS, subset_input, subset_outputs,
)

EMPTY: FrozenSet[str] = frozenset()
FULL: FrozenSet[str] = frozenset(PLAYERS)

# φ-sign that FAVOURS the firm, per outcome (used for the favoured/penalised summary counts).
_FAVOURED_SIGN = {"req": -1, "eff": +1}
# Display scale: requirement reported in percentage points, efficiency as the raw 0-1 score.
_SCALE = {"req": 100.0, "eff": 1.0}


def all_subsets(players=PLAYERS):
    """Every subset of `players` as a frozenset, smallest first."""
    for r in range(len(players) + 1):
        for c in combinations(players, r):
            yield frozenset(c)


# ─────────────────────────────────────────────────────────────────────────────
# DEA scoring — one input/output spec, either outlier mode
# ─────────────────────────────────────────────────────────────────────────────

def _frozen_efficiency(
    inputs: np.ndarray, outputs: np.ndarray, rts: str,
    frozen_mask: np.ndarray, unscored_mask: np.ndarray,
) -> np.ndarray:
    """Capped efficiency against a FIXED reference set R = ~frozen_mask (no re-detection).

    Firms in R are scored leave-one-out (super-efficiency). A frozen firm that is not
    unscored (e.g. the one dynamic outlier we still want an outcome for) is scored against R
    by adding it to the reference and reading its leave-one-out value (which removes it again,
    leaving exactly R). The unscored firms (Ei-excluded) stay NaN.
    """
    R = ~frozen_mask
    theta = super_eff_scores(inputs, outputs, rts, R)
    eff = np.minimum(theta, 1.0)
    for i in np.where(frozen_mask & ~unscored_mask)[0]:
        ref_i = R.copy()
        ref_i[i] = True
        s = super_eff_scores(inputs, outputs, rts, ref_i)
        eff[i] = min(float(s[i]), 1.0) if np.isfinite(s[i]) else np.nan
    eff[unscored_mask] = np.nan
    return eff


def _score(
    frame: pd.DataFrame, input_cols: List[str], output_cols: List[str], *,
    cfg: NewBenchmarkingConfig, ei_excluded_mask: np.ndarray,
    outlier_mode: str, frozen_mask: Optional[np.ndarray],
) -> pd.DataFrame:
    """Score one DEA spec → per-REId [efficiency (capped), potential, is_outlier].

    dynamic: full iterative detection (max_rounds=None), Ei firms forced out up front.
    frozen:  fixed reference set = ~frozen_mask, no re-detection.
    """
    if outlier_mode == "dynamic":
        spec = {"inputs": input_cols, "outputs": output_cols, "rts": cfg.rts,
                "forced_outliers": ei_excluded_mask}
        dea = run_dea_analysis(frame, spec)
        return dea[[COL_REID, COL_DEA_EFFICIENCY, COL_DEA_POTENTIAL, COL_IS_OUTLIER]]

    if outlier_mode == "frozen":
        if frozen_mask is None:
            raise ValueError("frozen mode requires frozen_mask")
        inputs = frame[input_cols].to_numpy(dtype=float)
        outputs = frame[output_cols].to_numpy(dtype=float)
        eff = _frozen_efficiency(inputs, outputs, cfg.rts, frozen_mask, ei_excluded_mask)
        pot = np.where(np.isfinite(eff), 1.0 - eff, np.nan)
        pot[frozen_mask & ~ei_excluded_mask] = 1.0   # frozen outliers: legacy treats via flag
        return pd.DataFrame({
            COL_REID: frame[COL_REID].to_numpy(),
            COL_DEA_EFFICIENCY: eff, COL_DEA_POTENTIAL: pot,
            COL_IS_OUTLIER: frozen_mask,
        })

    raise ValueError(f"unknown outlier_mode: {outlier_mode!r}")


def _two_sided_pp(scored: pd.DataFrame, cfg: NewBenchmarkingConfig) -> pd.Series:
    """Signed two-sided requirement in pp for a scored frame (E75 from its own distribution)."""
    d = calculate_two_sided_requirement(
        scored, reference_percentile=cfg.reference_percentile, gap_cap=cfg.gap_cap,
        sharing=cfg.sharing, realization_time=cfg.realization_time,
        supervision_period=cfg.supervision_period,
    )
    return d.set_index(COL_REID)[COL_EFF_REQ_ANNUAL] * 100.0


def full_model_outlier_mask(spine: pd.DataFrame, cfg: NewBenchmarkingConfig,
                            ei_excluded_mask: np.ndarray) -> np.ndarray:
    """The full-model (v(N)) outlier set under dynamic detection — what 'frozen' freezes."""
    S = FULL
    out_cols = subset_outputs(S)
    frame = spine[[COL_REID]].copy()
    frame["_inp"] = subset_input(spine, S)
    for oc in out_cols:
        frame[oc] = spine[oc].to_numpy()
    scored = _score(frame, ["_inp"], out_cols, cfg=cfg, ei_excluded_mask=ei_excluded_mask,
                    outlier_mode="dynamic", frozen_mask=None)
    return scored.set_index(COL_REID)[COL_IS_OUTLIER].reindex(spine[COL_REID]).to_numpy(bool)


# ─────────────────────────────────────────────────────────────────────────────
# Value grid — 128 subsets, both outcomes, one outlier mode
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class GridBundle:
    """Both outcome grids for one outlier mode (each dict maps a subset → per-REId Series)."""
    eff: Dict[FrozenSet[str], pd.Series]    # capped efficiency 0-1
    req: Dict[FrozenSet[str], pd.Series]    # signed requirement, pp
    e75: Dict[FrozenSet[str], float]        # reference efficiency per subset
    outlier_mode: str
    frozen_reids: List[str]                 # firms frozen out (frozen mode); [] for dynamic
    index: pd.Index                          # REId order


def compute_grids(spine: pd.DataFrame, outlier_mode: str,
                  cfg: Optional[NewBenchmarkingConfig] = None) -> GridBundle:
    """Solve all 128 subsets once; return both the efficiency and requirement grids."""
    cfg = cfg or NewBenchmarkingConfig()
    reids = spine[COL_REID]
    ei_excluded_mask = reids.isin(cfg.exclude_reids).to_numpy()

    frozen_mask = None
    frozen_reids: List[str] = []
    if outlier_mode == "frozen":
        frozen_mask = full_model_outlier_mask(spine, cfg, ei_excluded_mask)
        frozen_reids = reids[frozen_mask].tolist()

    eff: Dict[FrozenSet[str], pd.Series] = {}
    req: Dict[FrozenSet[str], pd.Series] = {}
    e75: Dict[FrozenSet[str], float] = {}
    idx = reids.copy()

    for S in all_subsets():
        out_cols = subset_outputs(S)
        frame = spine[[COL_REID]].copy()
        frame["_inp"] = subset_input(spine, S)
        for oc in out_cols:
            frame[oc] = spine[oc].to_numpy()
        scored = _score(frame, ["_inp"], out_cols, cfg=cfg,
                        ei_excluded_mask=ei_excluded_mask, outlier_mode=outlier_mode,
                        frozen_mask=frozen_mask)
        eff[S] = scored.set_index(COL_REID)[COL_DEA_EFFICIENCY].reindex(reids).reset_index(drop=True)
        e75[S] = reference_efficiency(
            scored[COL_DEA_EFFICIENCY], scored[COL_IS_OUTLIER], cfg.reference_percentile)
        req[S] = _two_sided_pp(scored, cfg).reindex(reids).reset_index(drop=True)

    return GridBundle(eff=eff, req=req, e75=e75, outlier_mode=outlier_mode,
                      frozen_reids=frozen_reids, index=pd.RangeIndex(len(reids)))


# ─────────────────────────────────────────────────────────────────────────────
# Decomposition — Shapley + endpoints + outer layer for ONE outcome
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class DecompResult:
    outcome: str
    outlier_mode: str
    scale_label: str
    frozen_reids: List[str]
    per_company: pd.DataFrame        # REId, name_short, v_empty, v_full, phi_<player>, sum_phi
    summary: pd.DataFrame            # per player: mean/abs phi, dominance, favoured/penalised
    loo: pd.DataFrame                # leave-one-out endpoint per player
    aoi: pd.DataFrame                # add-one-in endpoint per player
    ranking: pd.DataFrame            # players ranked by |effect|, LOO vs AOI gap
    grid_long: pd.DataFrame          # every v(S) per firm (finest level)
    outer_layer: pd.DataFrame        # phase-1 mechanic/input corners per firm
    checks: Dict[str, float]         # identity / cross-check residuals


def _value(grid: GridBundle, outcome: str) -> Dict[FrozenSet[str], pd.Series]:
    return grid.eff if outcome == "eff" else grid.req


def _shapley(V: Dict[FrozenSet[str], pd.Series], idx: pd.Index) -> Dict[str, pd.Series]:
    w = {s: factorial(s) * factorial(N_PLAYERS - s - 1) / factorial(N_PLAYERS)
         for s in range(N_PLAYERS)}
    phi = {p: pd.Series(0.0, index=idx) for p in PLAYERS}
    for p in PLAYERS:
        others = [x for x in PLAYERS if x != p]
        for S in all_subsets(others):
            phi[p] = phi[p] + w[len(S)] * (V[S | {p}] - V[S])
    return phi


def decompose(spine: pd.DataFrame, grid: GridBundle, outcome: str,
              cfg: Optional[NewBenchmarkingConfig] = None) -> DecompResult:
    cfg = cfg or NewBenchmarkingConfig()
    V = _value(grid, outcome)
    idx = grid.index
    reids = spine[COL_REID].reset_index(drop=True)
    names = spine["name_short"].reset_index(drop=True)
    fav = _FAVOURED_SIGN[outcome]

    phi = _shapley(V, idx)
    sum_phi = sum(phi.values())
    total = V[FULL] - V[EMPTY]
    identity_err = float(np.nanmax(np.abs((sum_phi - total).to_numpy())))

    # Per-company table
    per = pd.DataFrame({"REId": reids, "name_short": names,
                        "v_empty": V[EMPTY].to_numpy(), "v_full": V[FULL].to_numpy()})
    for p in PLAYERS:
        per[f"phi_{p}"] = phi[p].to_numpy()
    per["sum_phi"] = sum_phi.to_numpy()

    # Sector summary
    phi_df = pd.DataFrame({p: phi[p] for p in PLAYERS}).dropna()
    dominant = phi_df.abs().idxmax(axis=1)
    rows = []
    for p in PLAYERS:
        rows.append({
            "player": p,
            "mean_phi": round(float(phi_df[p].mean()), 5),
            "mean_abs_phi": round(float(phi_df[p].abs().mean()), 5),
            "share_dominant": round(float((dominant == p).mean()), 3),
            "n_favoured": int(((fav * phi_df[p]) > 0).sum()),
            "n_penalised": int(((fav * phi_df[p]) < 0).sum()),
        })
    summary = pd.DataFrame(rows).sort_values("mean_abs_phi", ascending=False).reset_index(drop=True)

    # LOO / AOI endpoints (subsets already in the grid)
    loo = pd.DataFrame({"REId": reids, "name_short": names, "v_full": V[FULL].to_numpy()})
    aoi = pd.DataFrame({"REId": reids, "name_short": names, "v_empty": V[EMPTY].to_numpy()})
    for p in PLAYERS:
        loo[f"d_{p}"] = (V[FULL] - V[FULL - {p}]).to_numpy()
        aoi[f"d_{p}"] = (V[EMPTY | {p}] - V[EMPTY]).to_numpy()

    rank_rows = []
    for p in PLAYERS:
        lo = float(np.nanmedian(np.abs(loo[f"d_{p}"].to_numpy())))
        ai = float(np.nanmedian(np.abs(aoi[f"d_{p}"].to_numpy())))
        sh = float(np.nanmedian(np.abs(phi_df[p].to_numpy())))
        rank_rows.append({"player": p, "loo_median_abs": round(lo, 5),
                          "aoi_median_abs": round(ai, 5), "shapley_median_abs": round(sh, 5),
                          "loo_aoi_gap": round(abs(lo - ai), 5)})
    ranking = pd.DataFrame(rank_rows).sort_values("shapley_median_abs", ascending=False).reset_index(drop=True)

    # Finest level: every v(S) per firm
    grid_long = _grid_long(grid, outcome, reids)

    # Phase-1 outer layer
    outer_layer, outer_checks = _outer_layer(spine, grid, outcome, cfg)

    checks = {"shapley_identity_max_resid": identity_err, **outer_checks}
    return DecompResult(
        outcome=outcome, outlier_mode=grid.outlier_mode, scale_label=_scale_label(outcome),
        frozen_reids=grid.frozen_reids, per_company=per, summary=summary,
        loo=loo, aoi=aoi, ranking=ranking, grid_long=grid_long,
        outer_layer=outer_layer, checks=checks,
    )


def _scale_label(outcome: str) -> str:
    return "pp/yr" if outcome == "req" else "efficiency (0-1)"


def _subset_mask(S: FrozenSet[str]) -> int:
    """Bitmask over PLAYERS order (stable encoding for the long grid)."""
    return sum(1 << i for i, p in enumerate(PLAYERS) if p in S)


def _grid_long(grid: GridBundle, outcome: str, reids: pd.Series) -> pd.DataFrame:
    V = _value(grid, outcome)
    blocks = []
    for S in all_subsets():
        mask = _subset_mask(S)
        players_csv = "+".join(p for p in PLAYERS if p in S) or "(baseline)"
        blocks.append(pd.DataFrame({
            "REId": reids.to_numpy(),
            "subset_mask": mask,
            "n_players": len(S),
            "players": players_csv,
            "value": V[S].to_numpy(),
            "e75": grid.e75[S],
        }))
    return pd.concat(blocks, ignore_index=True)


# ─────────────────────────────────────────────────────────────────────────────
# Phase-1 outer layer — "how the requirement is calculated"
# ─────────────────────────────────────────────────────────────────────────────
# Corners over the v(∅) composition (opexp_dea + capex_unadj, base outputs, env off):
#   input structure:  2 separate DEA inputs [opexp_dea, capex_unadj]  vs  1 summed TOTEX
#   mechanic (req only): legacy front-reference requirement  vs  two-sided E75
# req:  C1=2in/legacy, C2=2in/two-sided, C3=1in/legacy, C4=1in/two-sided (= v(∅)_req)
#       phi_mechanic = ½[(C2-C1)+(C4-C3)] ; phi_input = ½[(C3-C1)+(C4-C2)] ; sum = C4-C1.
# eff:  only the input aggregation matters (efficiency has no reference-rule change):
#       phi_input = eff(1in) - eff(2in). There is NO mechanic term.

def _legacy_req_pp(scored: pd.DataFrame) -> pd.Series:
    """Legacy front-reference annual requirement (pp): truncation 16.24-30 %, 1 % floor, 50/50, t=8."""
    d = calculate_eff_req_for_dataframe(scored)
    return d.set_index(COL_REID)[COL_EFF_REQ_ANNUAL] * 100.0


def _outer_layer(spine: pd.DataFrame, grid: GridBundle, outcome: str,
                 cfg: NewBenchmarkingConfig) -> tuple[pd.DataFrame, Dict[str, float]]:
    reids = spine[COL_REID].reset_index(drop=True)
    names = spine["name_short"].reset_index(drop=True)
    ei_excluded_mask = reids.isin(cfg.exclude_reids).to_numpy()
    frozen_mask = None
    if grid.outlier_mode == "frozen":
        frozen_mask = full_model_outlier_mask(spine, cfg, ei_excluded_mask)

    base_out = list(BASE_OUTPUTS)
    one = spine[[COL_REID]].copy()
    one["_totex"] = (spine["opexp_dea"] + spine["capex_unadj"]).to_numpy()
    two = spine[[COL_REID]].copy()
    two["opexp_dea"] = spine["opexp_dea"].to_numpy()
    two["capex_unadj"] = spine["capex_unadj"].to_numpy()
    for oc in base_out:
        one[oc] = spine[oc].to_numpy()
        two[oc] = spine[oc].to_numpy()

    def score(frame, input_cols):
        return _score(frame, input_cols, base_out, cfg=cfg, ei_excluded_mask=ei_excluded_mask,
                      outlier_mode=grid.outlier_mode, frozen_mask=frozen_mask)

    s2 = score(two, ["opexp_dea", "capex_unadj"])    # 2 separate inputs (Ei's real DEA spec)
    s1 = score(one, ["_totex"])                       # 1 summed TOTEX (= v(∅) input)

    out = pd.DataFrame({"REId": reids, "name_short": names})
    checks: Dict[str, float] = {}

    if outcome == "req":
        C1 = _legacy_req_pp(s2).reindex(reids).to_numpy()
        C2 = _two_sided_pp(s2, cfg).reindex(reids).to_numpy()
        C3 = _legacy_req_pp(s1).reindex(reids).to_numpy()
        C4 = _two_sided_pp(s1, cfg).reindex(reids).to_numpy()
        phi_mech = 0.5 * ((C2 - C1) + (C4 - C3))
        phi_inp = 0.5 * ((C3 - C1) + (C4 - C2))
        out["C1_legacy_2in"] = C1
        out["C2_twosided_2in"] = C2
        out["C3_legacy_1in"] = C3
        out["C4_twosided_1in"] = C4
        out["phi_mechanic"] = phi_mech
        out["phi_input"] = phi_inp
        v_empty = grid.req[EMPTY].to_numpy()
        checks["outer_C4_eq_v_empty"] = float(np.nanmax(np.abs(C4 - v_empty)))
        checks["outer_additivity"] = float(np.nanmax(np.abs((phi_mech + phi_inp) - (C4 - C1))))
    else:  # eff — input aggregation only, no mechanic
        E2 = s2.set_index(COL_REID)[COL_DEA_EFFICIENCY].reindex(reids).to_numpy()
        E1 = s1.set_index(COL_REID)[COL_DEA_EFFICIENCY].reindex(reids).to_numpy()
        out["E2_2in"] = E2
        out["E1_1in"] = E1
        out["phi_input"] = E1 - E2
        v_empty = grid.eff[EMPTY].to_numpy()
        checks["outer_E1_eq_v_empty"] = float(np.nanmax(np.abs(E1 - v_empty)))

    return out, checks

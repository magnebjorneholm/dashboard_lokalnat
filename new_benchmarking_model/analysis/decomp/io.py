"""
io.py — output layout and writers for the parametrised decomposition.

Provenance-keyed tree under analysis/out/:

    decomp_<outcome>/<outlier_mode>/
        shapley_percompany.csv   per REId: v_empty, v_full, phi_<player>, sum_phi
        shapley_summary.csv      per player: mean/abs phi, dominance, favoured/penalised
        loo.csv                  leave-one-out endpoint per player (full − player)
        aoi.csv                  add-one-in endpoint per player (baseline + player)
        ranking.csv              players ranked by |effect|, LOO/AOI gap
        value_grid.csv           every v(S) per firm (finest level: 128 × 145 rows)
        outer_layer.csv          phase-1 corners (mechanic/input for req, input for eff)
        manifest.json            params, frozen firms, cross-check residuals, timestamp

outcome ∈ {"req","eff"}, outlier_mode ∈ {"dynamic","frozen"}. The app reads these paths
through data/analysis_loader.py (updated when the UI graduates this analysis).
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from new_benchmarking_model.analysis.decomp.engine import DecompResult
from new_benchmarking_model.analysis.decomp.players import PLAYERS

OUT_DIR = Path(__file__).resolve().parents[1] / "out"


def run_dir(outcome: str, outlier_mode: str) -> Path:
    return OUT_DIR / f"decomp_{outcome}" / outlier_mode


def write_run(result: DecompResult) -> Path:
    """Persist every table + a manifest for one (outcome, outlier_mode) run."""
    d = run_dir(result.outcome, result.outlier_mode)
    d.mkdir(parents=True, exist_ok=True)

    result.per_company.to_csv(d / "shapley_percompany.csv", index=False)
    result.summary.to_csv(d / "shapley_summary.csv", index=False)
    result.loo.to_csv(d / "loo.csv", index=False)
    result.aoi.to_csv(d / "aoi.csv", index=False)
    result.ranking.to_csv(d / "ranking.csv", index=False)
    result.grid_long.to_csv(d / "value_grid.csv", index=False)
    result.outer_layer.to_csv(d / "outer_layer.csv", index=False)

    manifest = {
        "outcome": result.outcome,
        "outlier_mode": result.outlier_mode,
        "scale": result.scale_label,
        "players": list(PLAYERS),
        "n_subsets": 2 ** len(PLAYERS),
        "n_companies_scored": int(result.per_company["sum_phi"].notna().sum()),
        "frozen_reids": result.frozen_reids,
        "checks": result.checks,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }
    with open(d / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    return d

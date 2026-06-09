"""
Pre-compute the main-spec result for the new benchmarking model.

The new-benchmarking page (pages/5_new_benchmarking.py) shows a fixed "main model"
that is identical for every user, yet running it live (a 148-company KENT re-run plus a
DEA pass) costs several seconds on every cold start because @st.cache_data is in-memory
only and is wiped on each Render redeploy.

This script runs that fixed main spec once, offline, and serialises everything the page
reads into data/new_benchmarking/. At runtime the page loads the bundle via
data_loaders.new_benchmarking_data.load_precomputed_main() instead of recomputing.
Only the default NewBenchmarkingConfig() is pre-computed; the Experiment panel's tweaked
configs still run live.

Re-run this whenever the main spec, the calculation code, or the source data changes:
    ./venv/Scripts/python.exe scripts/precompute_new_benchmarking.py

The companion test (tests/test_new_benchmarking_precompute.py) recomputes live and fails
if the committed bundle has drifted — your signal that a re-run is overdue.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from calculations.new_benchmarking import run_new_benchmarking, NewBenchmarkingConfig

NB_DIR = PROJECT_ROOT / "data" / "new_benchmarking"


def main() -> None:
    cfg = NewBenchmarkingConfig()

    print("Running the new benchmarking main spec for all 148 companies…")
    result = run_new_benchmarking(cfg)

    NB_DIR.mkdir(parents=True, exist_ok=True)

    # Only the frames the frontend actually reads (option A): per-company environment
    # adjustments are stored as their per_company view only; everything else the
    # EnvironmentAdjustmentResult holds is rebuilt empty at load (the UI never touches it).
    frames = {
        "dea_new": result.dea_new,
        "dea_current": result.dea_current,
        "comparison": result.comparison,
        "totex": result.totex,
        "new_model_inputs": result.new_model_inputs,
        "env_cable_per_company": result.env_capex.cable_adjustment.per_company,
        "env_station_per_company": result.env_capex.station_adjustment.per_company,
    }
    for name, df in frames.items():
        path = NB_DIR / f"{name}.parquet"
        df.to_parquet(path, index=False)
        print(f"  saved {name + '.parquet':32s} ({len(df):3d} rows, {len(df.columns)} cols)")

    manifest = {
        "signature": repr(cfg.signature()),
        "new_model_outputs": list(result.new_model_outputs),
        "n_companies": int(len(result.dea_new)),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }
    manifest_path = NB_DIR / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    print(f"  saved {'manifest.json':32s} (signature + {len(manifest['new_model_outputs'])} outputs)")
    print(f"\nDone. Bundle written to {NB_DIR}")


if __name__ == "__main__":
    main()

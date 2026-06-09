"""
Load the pre-computed main-spec result for the new benchmarking model.

The new-benchmarking page shows a fixed "main model" (the default NewBenchmarkingConfig).
Running it live costs a 148-company KENT re-run plus a DEA pass on every cold start. This
module loads a committed bundle (data/new_benchmarking/, produced by
scripts/precompute_new_benchmarking.py) and reconstructs the NewBenchmarkingResult the
page expects, so the main view is instant and survives Render redeploys.

Only the fields the frontend actually reads are stored (option A): the förläggningsmiljö
sub-results are reconstructed with their per_company frame only — all the UI consumes —
and the remaining EnvironmentAdjustmentResult frames are left empty.

If the bundle is missing, incomplete, or its signature no longer matches the current
default config, load_precomputed_main() returns None and the caller falls back to a live
run. The signature guard catches changes to the default config; the companion test
(tests/test_new_benchmarking_precompute.py) catches drift in the calculation code or
source data that the signature cannot see.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import pandas as pd
import streamlit as st

from config.column_names import COL_REID, COL_CAPITAL_COST_ENV_ADJ
from calculations.new_benchmarking.config import NewBenchmarkingConfig
from calculations.new_benchmarking.model import NewBenchmarkingResult
from calculations.new_benchmarking.capex_environment import EnvCapexResult
from calculations.new_benchmarking.environment_capex_adjustment.adjustment import (
    EnvironmentAdjustmentResult as CableAdjustmentResult,
)
from calculations.new_benchmarking.station_capex_adjustment.adjustment import (
    EnvironmentAdjustmentResult as StationAdjustmentResult,
)

NB_DIR = Path("data/new_benchmarking")
MANIFEST_JSON = NB_DIR / "manifest.json"

_FRAME_NAMES = (
    "dea_new", "dea_current", "comparison", "totex", "new_model_inputs",
    "env_cable_per_company", "env_station_per_company",
)


@st.cache_data(ttl=3600)
def load_precomputed_main() -> Optional[NewBenchmarkingResult]:
    """Reconstruct the main-spec NewBenchmarkingResult from the committed bundle.

    Returns None (→ caller runs the spec live) if the bundle is absent, incomplete, or
    its signature no longer matches the current default NewBenchmarkingConfig().
    """
    try:
        if not MANIFEST_JSON.exists():
            return None
        with open(MANIFEST_JSON, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        cfg = NewBenchmarkingConfig()
        if manifest.get("signature") != repr(cfg.signature()):
            return None  # bundle built for a different main spec → recompute live

        frames = {}
        for name in _FRAME_NAMES:
            path = NB_DIR / f"{name}.parquet"
            if not path.exists():
                return None
            frames[name] = pd.read_parquet(path)

        cable_adj = CableAdjustmentResult(
            method=cfg.cable_method,
            components=pd.DataFrame(),
            per_company=frames["env_cable_per_company"],
            per_company_env=pd.DataFrame(),
            calibration=None,
        )
        station_adj = StationAdjustmentResult(
            method=cfg.station_method,
            components=pd.DataFrame(),
            per_company=frames["env_station_per_company"],
            per_company_env=pd.DataFrame(),
            calibration=None,
        )
        env_capex = EnvCapexResult(
            capital_cost=frames["totex"][[COL_REID, COL_CAPITAL_COST_ENV_ADJ]].copy(),
            cable_adjustment=cable_adj,
            station_adjustment=station_adj,
        )

        return NewBenchmarkingResult(
            comparison=frames["comparison"],
            totex=frames["totex"],
            new_model_inputs=frames["new_model_inputs"],
            new_model_outputs=list(manifest.get("new_model_outputs", [])),
            dea_new=frames["dea_new"],
            dea_current=frames["dea_current"],
            env_capex=env_capex,
            config=cfg,
        )
    except Exception:
        # Any malformed/partial bundle must never break the page — fall back to live.
        return None

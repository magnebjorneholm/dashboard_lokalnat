"""
Load pre-computed StoNED efficiency results.

StoNED models are computed offline and stored as parquet files in data/stoned/.
Each model has a metadata entry in data/stoned/models.json.

Results use the same column structure as DeaStageOutput.dea_results so they
slot into the existing pipeline without downstream changes.
"""

import json
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import streamlit as st

STONED_DIR = Path("data/stoned")
MODELS_JSON = STONED_DIR / "models.json"


@st.cache_data(ttl=3600)
def load_stoned_model_registry() -> Dict[str, Dict[str, Any]]:
    """Load metadata for all pre-computed StoNED models."""
    if not MODELS_JSON.exists():
        return {}
    with open(MODELS_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


@st.cache_data(ttl=3600)
def load_stoned_results(model_id: str) -> pd.DataFrame:
    """Load pre-computed StoNED efficiency results for a specific model.

    Returns DataFrame with columns matching DeaStageOutput.dea_results:
    REId, dea_efficiency, dea_super_efficiency, potential, is_outlier
    """
    path = STONED_DIR / f"{model_id}.parquet"
    if not path.exists():
        raise FileNotFoundError(
            f"StoNED model '{model_id}' not found at {path}"
        )
    return pd.read_parquet(path)


def get_available_stoned_models() -> List[str]:
    """Return list of available model IDs."""
    registry = load_stoned_model_registry()
    return list(registry.keys())


def get_stoned_model_info(model_id: str) -> Dict[str, Any]:
    """Return metadata for a specific model."""
    registry = load_stoned_model_registry()
    if model_id not in registry:
        raise KeyError(f"StoNED model '{model_id}' not in registry")
    return registry[model_id]

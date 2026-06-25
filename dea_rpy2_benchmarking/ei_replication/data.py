"""Load the Ei DEA inputs and the published facit.

Paths are resolved through the project's ``config/data_paths.py`` registry (never
hardcode ``data/`` paths, per CLAUDE.md). This module is the only place that
touches the project; everything else in ``ei_replication`` works on plain numpy.

Input/output specification (Ei's locked baseline, see eis_dea_metod.md and
calculations/frontier/dea_calculations.py:BASELINE_DEA_SPEC):

    inputs  (X): CAPEX, OPEXp          -- raw OPEXp, NOT the SDF-derived variant
    outputs (Y): CU, MW, NS, MWhl, MWhh
    rts: crs, input-oriented, leave-one-out super-efficiency
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

# Raw column names exactly as they appear in Data_modeller.xlsx / EIs_DEA.xlsx.
INPUT_COLS = ["CAPEX", "OPEXp"]
OUTPUT_COLS = ["CU", "MW", "NS", "MWhl", "MWhh"]
ID_COLS = ["DMU", "REId", "Företag"]

# The single firm Ei's published facit cannot be reproduced from any reference
# set on the published data (a data anomaly in that row, see eis_dea_metod.md).
KNOWN_NONREPLICABLE = "REL00193"


@dataclass
class ModelData:
    """DEA inputs/outputs plus identifiers, aligned row-for-row."""

    X: np.ndarray  # (n, n_inputs)
    Y: np.ndarray  # (n, n_outputs)
    reid: np.ndarray  # (n,) firm ids
    dmu: np.ndarray  # (n,) Ei DMU numbers
    names: np.ndarray  # (n,) company names

    @property
    def n(self) -> int:
        return int(self.X.shape[0])


def _resolve(name: str):
    """Resolve a registered dataset, importing the project registry lazily."""
    from config.data_paths import require_dataset

    return require_dataset(name)


def load_model_data() -> ModelData:
    """Load Data_modeller.xlsx into a ModelData (raw OPEXp/CAPEX inputs)."""
    df = pd.read_excel(_resolve("data_modeller"), sheet_name="Sheet1")
    X = df[INPUT_COLS].apply(pd.to_numeric, errors="coerce").to_numpy(float)
    Y = df[OUTPUT_COLS].apply(pd.to_numeric, errors="coerce").to_numpy(float)
    return ModelData(
        X=X,
        Y=Y,
        reid=df["REId"].to_numpy(),
        dmu=df["DMU"].to_numpy(),
        names=df["Företag"].to_numpy(),
    )


def load_facit() -> pd.DataFrame:
    """Load Ei's published results (EIs_DEA.xlsx), numeric columns coerced."""
    df = pd.read_excel(_resolve("eis_dea"), sheet_name="Körning")
    for col in ("Effektivitet", "Supereffektivitet", "potential", "Effkrav_proc"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df

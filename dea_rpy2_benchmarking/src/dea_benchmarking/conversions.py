"""numpy <-> R conversion helpers for DEA inputs/outputs.

Benchmarking's ``dea(X, Y, ...)`` expects X (inputs) and Y (outputs) as numeric
matrices with one row per DMU (decision-making unit) and one column per
input/output. These helpers coerce whatever the caller passes (1D or 2D
array-likes, lists, pandas frames) into a clean float64 2D numpy array so the
numpy2ri converter produces a proper R matrix.
"""

from __future__ import annotations

import numpy as np


def as_matrix(data, name: str = "data") -> np.ndarray:
    """Coerce ``data`` to a 2D float64 array (n_dmu, n_dim).

    A 1D input is treated as a single column (one input/output dimension).
    Accepts anything ``np.asarray`` understands, including pandas objects
    (their ``.values`` is used to avoid carrying an index into R).
    """
    if hasattr(data, "values") and hasattr(data, "columns"):  # pandas DataFrame
        arr = np.asarray(data.values, dtype=np.float64)
    elif hasattr(data, "values") and hasattr(data, "index"):  # pandas Series
        arr = np.asarray(data.values, dtype=np.float64)
    else:
        arr = np.asarray(data, dtype=np.float64)

    if arr.ndim == 1:
        arr = arr.reshape(-1, 1)
    if arr.ndim != 2:
        raise ValueError(f"{name} must be 1D or 2D, got shape {arr.shape}")
    if not np.isfinite(arr).all():
        raise ValueError(f"{name} contains NaN or inf values")
    return np.ascontiguousarray(arr)


def check_xy(X: np.ndarray, Y: np.ndarray) -> None:
    """Validate that X and Y describe the same set of DMUs."""
    if X.shape[0] != Y.shape[0]:
        raise ValueError(
            f"X has {X.shape[0]} DMUs but Y has {Y.shape[0]}; "
            "rows must align (one row per DMU)."
        )
    if X.shape[0] == 0:
        raise ValueError("No DMUs provided (zero rows).")


def r_to_numpy(obj) -> np.ndarray:
    """Convert an R numeric vector/matrix back to a numpy array."""
    return np.asarray(obj)

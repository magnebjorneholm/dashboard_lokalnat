"""High-level Python API around Benchmarking's DEA functions.

Two convenience wrappers cover the common cases:
- ``dea(...)``  -> standard Data Envelopment Analysis (Farrell efficiency)
- ``sdea(...)`` -> super-efficiency DEA (efficient units can score > 1)

Everything else in the package (``dea.boot``, ``malmquist``, ``cost.opt``,
``dea.add``, ``mea`` …) is reachable verbatim through ``package()`` — see the
module docstring of ``r_session``. These wrappers are sugar, not a wall.

RTS (returns to scale) accepts the Benchmarking string codes:
    "fdh", "vrs", "drs", "crs", "irs", "irs2", "add", "fdh+"
ORIENTATION accepts:
    "in" (input), "out" (output), "graph", "in-out"
"""

from __future__ import annotations

import numpy as np

# Import r_session FIRST: it configures R_HOME / RPY2_CFFI_MODE before rpy2 is
# imported anywhere. Importing rpy2 submodules above this line would initialize
# the binding too early and re-trigger the API-mode dlopen warning.
from .r_session import get_benchmarking, np_converter
from rpy2.robjects.conversion import get_conversion  # noqa: E402

from .conversions import as_matrix, check_xy
from .results import DEAResult

VALID_RTS = {"fdh", "vrs", "drs", "crs", "irs", "irs2", "add", "fdh+"}
VALID_ORIENTATION = {"in", "out", "graph", "in-out"}


def _np_to_r(arr):
    """Convert a numpy array to an R matrix object (valid outside the context)."""
    with np_converter.context():
        return get_conversion().py2rpy(arr)


def _r_to_np(robj) -> np.ndarray:
    """Convert an R vector/matrix object back to a numpy array."""
    with np_converter.context():
        return np.asarray(get_conversion().rpy2py(robj))


def package():
    """Return the raw Benchmarking R package object (full API surface)."""
    return get_benchmarking()


def _validate_opts(rts: str, orientation: str) -> None:
    if rts not in VALID_RTS:
        raise ValueError(f"rts={rts!r} not in {sorted(VALID_RTS)}")
    if orientation not in VALID_ORIENTATION:
        raise ValueError(
            f"orientation={orientation!r} not in {sorted(VALID_ORIENTATION)}"
        )


def _extract_total_slack(farrell) -> np.ndarray | None:
    """Sum input+output slacks from a Farrell object, or None if absent."""
    names = list(farrell.names) if farrell.names else []
    total = None
    for key in ("sx", "sy"):
        if key in names:
            try:
                arr = _r_to_np(farrell.rx2(key))
            except Exception:
                continue
            # R NULL (e.g. when SLACK was not requested) converts to a 0-d
            # object array -> skip anything that isn't real numeric data.
            if arr.dtype.kind not in "fiu" or arr.size == 0:
                continue
            arr = arr.reshape(arr.shape[0], -1) if arr.ndim > 1 else arr.reshape(-1, 1)
            rowsum = arr.sum(axis=1)
            total = rowsum if total is None else total + rowsum
    return total


def _to_result(
    farrell, rts: str, orientation: str, dmu_names: list[str] | None
) -> DEAResult:
    eff = _r_to_np(farrell.rx2("eff")).ravel()
    lambdas = _r_to_np(farrell.rx2("lambda"))
    if lambdas.ndim == 1:
        lambdas = lambdas.reshape(len(eff), -1)
    slack = _extract_total_slack(farrell)
    return DEAResult(
        eff=eff,
        lambdas=lambdas,
        rts=rts,
        orientation=orientation,
        dmu_names=list(dmu_names) if dmu_names else [],
        slack=slack,
        raw=farrell,
    )


def dea(
    X,
    Y,
    rts: str = "vrs",
    orientation: str = "in",
    slack: bool = False,
    dmu_names: list[str] | None = None,
    dual: bool = False,
) -> DEAResult:
    """Run standard DEA via ``Benchmarking::dea``.

    Args:
        X: Inputs, shape (n_dmu, n_inputs). 1D allowed (single input).
        Y: Outputs, shape (n_dmu, n_outputs). 1D allowed (single output).
        rts: Returns-to-scale assumption (see VALID_RTS).
        orientation: Efficiency orientation (see VALID_ORIENTATION).
        slack: If True, also compute slacks (second phase) -> result.slack.
        dmu_names: Optional DMU labels carried into the result.
        dual: If True, ask Benchmarking for dual (multiplier) values too.

    Returns:
        DEAResult with per-DMU efficiency and the lambda peer matrix.
    """
    _validate_opts(rts, orientation)
    Xm = as_matrix(X, "X")
    Ym = as_matrix(Y, "Y")
    check_xy(Xm, Ym)

    bench = get_benchmarking()
    farrell = bench.dea(
        _np_to_r(Xm), _np_to_r(Ym),
        RTS=rts, ORIENTATION=orientation, SLACK=slack, DUAL=dual,
    )
    return _to_result(farrell, rts, orientation, dmu_names)


def sdea(
    X,
    Y,
    rts: str = "vrs",
    orientation: str = "in",
    dmu_names: list[str] | None = None,
) -> DEAResult:
    """Run super-efficiency DEA via ``Benchmarking::sdea``.

    Each DMU is scored against a frontier built from all *other* DMUs, so
    efficient units obtain a score that can exceed 1 — useful for ranking
    units that standard DEA all pins at exactly 1 (and for outlier screening,
    cf. Ei's super-efficiency step).

    Returns:
        DEAResult; ``eff`` holds the super-efficiency scores. The lambda matrix
        from sdea has the diagonal (self-reference) removed by construction.
    """
    _validate_opts(rts, orientation)
    Xm = as_matrix(X, "X")
    Ym = as_matrix(Y, "Y")
    check_xy(Xm, Ym)

    bench = get_benchmarking()
    farrell = bench.sdea(
        _np_to_r(Xm), _np_to_r(Ym), RTS=rts, ORIENTATION=orientation
    )
    return _to_result(farrell, rts, orientation, dmu_names)

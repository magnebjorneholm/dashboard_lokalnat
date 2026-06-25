"""Typed result container for a DEA run.

The Benchmarking ``dea``/``sdea`` functions return an S3 object of class
"Farrell" which is, under the hood, a named R list. We extract the parts we
care about into a plain Python dataclass so downstream code never has to touch
rpy2 objects — while still keeping a handle to the raw R object (``raw``) for
anything not surfaced here (slacks decomposition, dual values, etc.).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass
class DEAResult:
    """Result of a DEA / super-efficiency DEA run.

    Attributes:
        eff: Efficiency score per DMU, shape (n_dmu,). Interpretation depends on
            orientation: input-oriented scores are in (0, 1] (1 = efficient);
            super-efficiency scores for efficient units may exceed 1.
        lambdas: Intensity/weight matrix, shape (n_dmu, n_dmu). Row i gives the
            convex combination of peers that spans DMU i's frontier projection.
        rts: Returns-to-scale assumption used ("crs", "vrs", ...).
        orientation: "in", "out" or "graph".
        dmu_names: Optional labels for the DMUs (else "DMU1".."DMUn").
        slack: Total slack per DMU if computed (SLACK=True), else None.
        raw: The original rpy2 "Farrell" object, for advanced access.
    """

    eff: np.ndarray
    lambdas: np.ndarray
    rts: str
    orientation: str
    dmu_names: list[str] = field(default_factory=list)
    slack: np.ndarray | None = None
    raw: object | None = None

    @property
    def n_dmu(self) -> int:
        return int(self.eff.shape[0])

    def efficient(self, tol: float = 1e-6) -> np.ndarray:
        """Boolean mask of DMUs on the frontier (eff within tol of 1)."""
        return np.abs(self.eff - 1.0) <= tol

    def as_dataframe(self):
        """Return a tidy pandas DataFrame (eff + peer count). Requires pandas."""
        import pandas as pd

        names = self.dmu_names or [f"DMU{i + 1}" for i in range(self.n_dmu)]
        peer_count = (np.abs(self.lambdas) > 1e-6).sum(axis=1)
        data = {"dmu": names, "eff": self.eff, "n_peers": peer_count}
        if self.slack is not None:
            data["slack"] = self.slack
        return pd.DataFrame(data)

    def __repr__(self) -> str:
        return (
            f"DEAResult(n_dmu={self.n_dmu}, rts={self.rts!r}, "
            f"orientation={self.orientation!r}, "
            f"n_efficient={int(self.efficient().sum())})"
        )

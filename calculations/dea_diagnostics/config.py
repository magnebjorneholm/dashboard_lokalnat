"""
calculations/dea_diagnostics/config.py

`DeaDiagnosticsConfig` — every user-facing choice for one DEA-diagnostics run.
Defaults reproduce Ei's specification (inputs, outputs, CRS, IQR fence), except
that outlier detection iterates to convergence by default (the tool's own
method). Set `outlier_max_rounds=1` to reproduce Ei's published results exactly.

Nothing else in the package reads ad-hoc settings; everything flows through here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from config.column_names import (
    COL_CAPITAL_COST_2024, COL_CONTROLLABLE_AVG,
    COL_CU, COL_MW, COL_NS, COL_MWH_LOW, COL_MWH_HIGH,
)

# Ei's baseline DEA specification.
EI_INPUTS: Tuple[str, ...] = (COL_CAPITAL_COST_2024, COL_CONTROLLABLE_AVG)
EI_OUTPUTS: Tuple[str, ...] = (COL_CU, COL_MW, COL_NS, COL_MWH_LOW, COL_MWH_HIGH)


@dataclass
class DeaDiagnosticsConfig:
    """All choices for one DEA-diagnostics run. Defaults = Ei spec, converged outliers."""

    # ── DEA specification ────────────────────────────────────────────────────
    inputs: Tuple[str, ...] = EI_INPUTS
    outputs: Tuple[str, ...] = EI_OUTPUTS
    rts: str = "crs"                         # 'crs' | 'vrs'

    # ── Outlier detection (super-eff + IQR, shared with the pipeline) ────────
    # Super-efficiency is used here only to identify outliers; the main DEA solve
    # is standard (theta <= 1). `outlier_max_rounds`: None = iterate to
    # convergence (tool default); 1 = Ei's single identification round.
    outlier_enable: bool = True
    outlier_q_lower: float = 25.0
    outlier_q_upper: float = 75.0
    outlier_multiplier: float = 2.0
    outlier_max_rounds: Optional[int] = None

    # ── Diagnostics selection ────────────────────────────────────────────────
    # None = compute every registered diagnostic; otherwise a subset of keys
    # from calculations.dea_diagnostics.registry.all_keys().
    diagnostics: Optional[Tuple[str, ...]] = None

    def signature(self) -> tuple:
        """Stable, hashable identity of this configuration.

        Two configs with the same signature produce the same result, so this can
        key an @st.cache_data wrapper or a pre-computed bundle's validity token.
        """
        return (
            tuple(self.inputs),
            tuple(self.outputs),
            self.rts,
            self.outlier_enable,
            self.outlier_q_lower, self.outlier_q_upper, self.outlier_multiplier,
            self.outlier_max_rounds,
            tuple(self.diagnostics) if self.diagnostics is not None else None,
        )

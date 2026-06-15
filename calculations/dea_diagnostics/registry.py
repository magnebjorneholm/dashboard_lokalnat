"""
calculations/dea_diagnostics/registry.py

Registry of DEA diagnostics. Each diagnostic is one isolated `DiagnosticSpec`
entry: adding or removing a diagnostic is a one-line change here, with no edits
to the solver or the model orchestration.

`run_dea_diagnostics` (model.py) solves the DEA once, packs the result into a
`DeaSolveContext`, and applies whichever specs the config selects. Every spec is
a pure function of the context, so specs compose and test independently.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional

import numpy as np

from calculations.dea_diagnostics import diagnostics as dg


# ---------------------------------------------------------------------------
# Context passed to every diagnostic (one solved DEA over the cleaned set)
# ---------------------------------------------------------------------------

@dataclass
class DeaSolveContext:
    """Everything a diagnostic may read. Built once per run from the solvers.

    All arrays are indexed over the cleaned (non-outlier) firm set, in firm
    order. Virtual quantities are precomputed so multiplier-side specs stay
    one-liners.
    """

    firms: np.ndarray            # (n,) cleaned-set REIds
    input_labels: List[str]
    output_labels: List[str]
    x: np.ndarray                # (n, J) raw inputs
    y: np.ndarray                # (n, K) raw outputs
    theta: np.ndarray            # (n,) primal efficiency
    lambdas: np.ndarray          # (n, n) intensity weights
    mu: np.ndarray               # (n, K) output multipliers
    nu: np.ndarray               # (n, J) input multipliers
    virtual_inputs: np.ndarray   # (n, J)  nu * x
    virtual_outputs: np.ndarray  # (n, K)  mu * y
    virtual_output_shares: np.ndarray  # (n, K) row-normalized
    benchmark_mix: np.ndarray    # (n, n)  row-normalized intensities (peer shares)
    benchmark_scale: np.ndarray  # (n,)    total intensity L_o (CRS scale)

    @classmethod
    def build(cls, firms, input_labels, output_labels, x, y,
              theta, lambdas, mu, nu) -> "DeaSolveContext":
        mix, scale = dg.benchmark_composition(lambdas)
        return cls(
            firms=firms,
            input_labels=list(input_labels),
            output_labels=list(output_labels),
            x=x, y=y, theta=theta, lambdas=lambdas, mu=mu, nu=nu,
            virtual_inputs=dg.virtual_inputs(nu, x),
            virtual_outputs=dg.virtual_outputs(mu, y),
            virtual_output_shares=dg.virtual_output_shares(mu, y),
            benchmark_mix=mix,
            benchmark_scale=scale,
        )


# ---------------------------------------------------------------------------
# Spec + computed output
# ---------------------------------------------------------------------------

# Result-row axis: row labels come from firms / input_labels / output_labels.
Axis = str  # 'firm' | 'input' | 'output'


@dataclass(frozen=True)
class DiagnosticSpec:
    """One diagnostic. `fn` maps a DeaSolveContext to its values array."""

    key: str
    label: str
    family: str                       # 'peer' | 'multiplier'
    index: Axis                       # what a row means
    fn: Callable[[DeaSolveContext], np.ndarray]
    columns_from: Optional[str] = None  # None | 'inputs' | 'outputs' | 'firms' (for 2D values)
    description: str = ""


@dataclass
class DiagnosticOutput:
    """Computed diagnostic, self-describing for the UI layer."""

    key: str
    label: str
    family: str
    index: Axis
    row_labels: List[str]
    columns: List[str]          # [] when values is 1D
    values: np.ndarray
    description: str = ""


# ---------------------------------------------------------------------------
# The registry — one entry per diagnostic
# ---------------------------------------------------------------------------

def _benchmark_role(c: "DeaSolveContext") -> np.ndarray:
    """Dual reading of the mix: role[j, i] = share of firm j in firm i's benchmark.

    The transpose of benchmark_mix, with the diagonal zeroed so a firm's own
    self-reference does not count as "serving as a benchmark for others".
    Row j answers: which firms use j as a benchmark, and by how much.
    """
    role = np.asarray(c.benchmark_mix, dtype=float).T.copy()
    np.fill_diagonal(role, 0.0)
    return role


DIAGNOSTICS: List[DiagnosticSpec] = [
    # Peer-side (intensity weights / lambdas) -------------------------------
    DiagnosticSpec(
        key="benchmark_composition", label="Benchmark composition", family="peer",
        index="firm", columns_from="firms",
        fn=lambda c: c.benchmark_mix,
        description="Each firm's reference set as peer shares (rows sum to 1): "
                    "'30% A, 20% B, 50% C'. Read for inefficient firms.",
    ),
    DiagnosticSpec(
        key="benchmark_scale", label="Benchmark scale (CRS)", family="peer", index="firm",
        fn=lambda c: c.benchmark_scale,
        description="Total intensity L = sum of lambdas: how many times the peer mix is "
                    "scaled. Under CRS, <1 increasing / >1 decreasing returns to scale.",
    ),
    DiagnosticSpec(
        key="benchmark_role", label="Benchmark role", family="peer",
        index="firm", columns_from="firms",
        fn=_benchmark_role,
        description="Where a firm serves as benchmark: row j = share of j in each other "
                    "firm's benchmark. Read for efficient firms.",
    ),
    DiagnosticSpec(
        key="peer_count", label="Peer count", family="peer", index="firm",
        fn=lambda c: dg.peer_count(c.lambdas),
        description="How many firms reference each firm as a peer.",
    ),
    DiagnosticSpec(
        key="peers_per_firm", label="Peers per firm", family="peer", index="firm",
        fn=lambda c: dg.peers_per_firm(c.lambdas),
        description="How many distinct peers each firm relies on.",
    ),
    DiagnosticSpec(
        key="isolated_efficient", label="Isolated efficient firms", family="peer", index="firm",
        fn=lambda c: dg.isolated_efficient_firms(c.theta, c.lambdas),
        description="Efficient firms no other firm references (efficient by lack of comparators).",
    ),
    # Multiplier-side (mu / nu, raw x / y) ----------------------------------
    DiagnosticSpec(
        key="virtual_output_shares", label="Virtual output shares", family="multiplier",
        index="firm", columns_from="outputs",
        fn=lambda c: c.virtual_output_shares,
        description="Per-firm share of each output in its efficiency rating (rows sum to 1).",
    ),
    DiagnosticSpec(
        key="output_variance_decomposition", label="Output variance decomposition",
        family="multiplier", index="output",
        fn=lambda c: dg.variance_decomposition(c.virtual_outputs),
        description="Fraction of cross-firm variation in output contributions per output (sums to 1).",
    ),
    DiagnosticSpec(
        key="output_variance_ratio", label="Output variance ratio (substitution)",
        family="multiplier", index="output",
        fn=lambda c: dg.variance_ratio(c.virtual_outputs),
        description="Output variance vs row-sum variance; large sums signal LP substitution.",
    ),
    DiagnosticSpec(
        key="output_zero_weight_counts", label="Output zero-weight counts",
        family="multiplier", index="output",
        fn=lambda c: dg.zero_weight_counts(c.mu),
        description="How many firms place ~zero weight on each output.",
    ),
    DiagnosticSpec(
        key="input_zero_weight_counts", label="Input zero-weight counts",
        family="multiplier", index="input",
        fn=lambda c: dg.zero_weight_counts(c.nu),
        description="How many firms place ~zero weight on each input.",
    ),
]

_BY_KEY = {d.key: d for d in DIAGNOSTICS}


def all_keys() -> List[str]:
    """Keys of every registered diagnostic, in display order."""
    return [d.key for d in DIAGNOSTICS]


def get_spec(key: str) -> DiagnosticSpec:
    if key not in _BY_KEY:
        raise KeyError(f"Unknown diagnostic '{key}'. Known: {list(_BY_KEY)}")
    return _BY_KEY[key]


def compute(spec: DiagnosticSpec, ctx: DeaSolveContext) -> DiagnosticOutput:
    """Run one diagnostic and wrap it as a self-describing DiagnosticOutput."""
    values = np.asarray(spec.fn(ctx))
    if spec.index == "firm":
        row_labels = list(ctx.firms)
    elif spec.index == "input":
        row_labels = list(ctx.input_labels)
    elif spec.index == "output":
        row_labels = list(ctx.output_labels)
    else:  # pragma: no cover - guarded by Axis values in the registry
        raise ValueError(f"Unknown index axis '{spec.index}'")

    if spec.columns_from == "outputs":
        columns = list(ctx.output_labels)
    elif spec.columns_from == "inputs":
        columns = list(ctx.input_labels)
    elif spec.columns_from == "firms":
        columns = list(ctx.firms)
    else:
        columns = []

    return DiagnosticOutput(
        key=spec.key, label=spec.label, family=spec.family, index=spec.index,
        row_labels=row_labels, columns=columns, values=values,
        description=spec.description,
    )

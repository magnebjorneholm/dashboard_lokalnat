"""Generate deterministic mock DMU data for trying out the DEA wrappers.

No real regulatory data here — just a small, well-understood synthetic set so we
can eyeball that efficiency scores look sane (a couple of units on the frontier,
the rest dominated).
"""

from __future__ import annotations

import numpy as np


def textbook_example():
    """The classic small single-input/single-output DEA example.

    5 firms, 1 input (x), 1 output (y). Firms on the line of best output-per-
    input form the frontier. Returns (X, Y, names).
    """
    X = np.array([[1.0], [2.0], [3.0], [4.0], [5.0]])
    Y = np.array([[1.0], [3.0], [4.0], [3.0], [5.0]])
    names = [f"firm_{i + 1}" for i in range(5)]
    return X, Y, names


def random_dmus(n_dmu: int = 20, n_inputs: int = 2, n_outputs: int = 2, seed: int = 42):
    """A larger random synthetic set (seeded -> reproducible).

    Inputs are uniform; outputs are a noisy increasing function of inputs so the
    frontier is non-trivial but realistic. Returns (X, Y, names).
    """
    rng = np.random.default_rng(seed)
    X = rng.uniform(10, 100, size=(n_dmu, n_inputs))
    base = X @ rng.uniform(0.5, 1.5, size=(n_inputs, n_outputs))
    noise = rng.uniform(0.6, 1.0, size=(n_dmu, n_outputs))  # <=1 => inefficiency
    Y = base * noise
    names = [f"dmu_{i + 1:02d}" for i in range(n_dmu)]
    return X, Y, names

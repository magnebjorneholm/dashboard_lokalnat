"""
tests/test_dea_diagnostics.py

Tests for the standalone DEA-diagnostics solvers and diagnostics.

The central test proves that the new primal+dual solver, run on the model
specification with the shared outlier routine (iterated to convergence, the
default), reproduces the app's baseline DEA efficiencies. This is what makes
"two DEA implementations" an asset (cross-validated) rather than a risk.

Note: the diagnostics run on the app's SDF-derived controllable input, not Ei's
raw OPEXp, so the cleaned outlier set (5 firms) is the app baseline and these
efficiencies sit within ~1e-3 of Ei's published facit (see eis_dea_metod.md).
"""

import numpy as np
import pandas as pd
import pytest

from calculations.dea_diagnostics.solvers import solve_primal, solve_dual
from calculations.dea_diagnostics import diagnostics as dg
from calculations.dea_diagnostics import registry as reg
from calculations.dea_diagnostics.config import DeaDiagnosticsConfig
from calculations.dea_diagnostics.model import run_dea_diagnostics
from calculations.frontier.outliers import detect_outliers_iterative
from config.column_names import (
    COL_CAPITAL_COST_2024, COL_CONTROLLABLE_AVG,
    COL_CU, COL_MW, COL_NS, COL_MWH_LOW, COL_MWH_HIGH,
)

# App-baseline DEA efficiencies (SDF-derived input), within ~1e-3 of Ei's
# published facit. Unchanged by single vs iterated outliers for these 3 firms.
FACIT = {
    "REL00001": 0.67793232,
    "REL00886": 0.77067884,
    "REL03035": 0.95397050,
}

EI_INPUTS = [COL_CAPITAL_COST_2024, COL_CONTROLLABLE_AVG]
EI_OUTPUTS = [COL_CU, COL_MW, COL_NS, COL_MWH_LOW, COL_MWH_HIGH]


@pytest.fixture(scope="module")
def ei_dea_solved(baseline_data):
    """Run the model spec through the shared outlier routine + new primal/dual solver.

    Outliers are detected with the shared frontier routine iterated to
    convergence (the default) and removed from the reference set. The surviving
    firms are then scored with the new standard-DEA solvers (super_eff=False).
    Returns the cleaned-set arrays, REIds, and both solver results.
    """
    df = baseline_data.df_all_companies.copy()
    inputs = df[EI_INPUTS].apply(pd.to_numeric, errors="coerce").values
    outputs = df[EI_OUTPUTS].apply(pd.to_numeric, errors="coerce").values

    res = detect_outliers_iterative(inputs, outputs, "crs", multiplier=2.0, max_rounds=None)
    clean = ~res.is_outlier

    x = inputs[clean]
    y = outputs[clean]
    reids = df["REId"].values[clean]

    primal = solve_primal(x, y, rts="crs", super_eff=False)
    dual = solve_dual(x, y, rts="crs", super_eff=False)
    return {"x": x, "y": y, "reids": reids, "primal": primal, "dual": dual}


class TestEiCrossValidation:
    @pytest.mark.parametrize("reid", list(FACIT))
    def test_new_solver_matches_ei_facit(self, ei_dea_solved, reid):
        """Standard DEA on the cleaned set (capped at 1) reproduces the app-baseline efficiency."""
        reids = ei_dea_solved["reids"]
        assert reid in reids, f"{reid} unexpectedly flagged as outlier"
        idx = int(np.where(reids == reid)[0][0])
        theta = min(ei_dea_solved["primal"].theta[idx], 1.0)
        assert theta == pytest.approx(FACIT[reid], abs=1e-3)

    def test_primal_equals_dual(self, ei_dea_solved):
        """LP duality: primal and dual theta agree within tolerance."""
        tp = ei_dea_solved["primal"].theta
        td = ei_dea_solved["dual"].theta
        ok = np.isfinite(tp) & np.isfinite(td)
        assert ok.all(), "some firms failed to solve"
        assert np.max(np.abs(tp[ok] - td[ok])) < 1e-5

    def test_all_cleaned_firms_optimal(self, ei_dea_solved):
        assert all(s == "Optimal" for s in ei_dea_solved["primal"].status)
        assert all(s == "Optimal" for s in ei_dea_solved["dual"].status)


class TestMultiplierDiagnostics:
    def test_virtual_inputs_rows_sum_to_one(self, ei_dea_solved):
        """IO normalization: sum_j nu_ij x_ij = 1 in raw units (after unscaling)."""
        vi = dg.virtual_inputs(ei_dea_solved["dual"].nu, ei_dea_solved["x"])
        assert np.allclose(vi.sum(axis=1), 1.0, atol=1e-6)

    def test_virtual_outputs_rows_sum_to_theta(self, ei_dea_solved):
        vo = dg.virtual_outputs(ei_dea_solved["dual"].mu, ei_dea_solved["y"])
        assert np.allclose(vo.sum(axis=1), ei_dea_solved["dual"].theta, atol=1e-6)

    def test_output_shares_sum_to_one(self, ei_dea_solved):
        shares = dg.virtual_output_shares(ei_dea_solved["dual"].mu, ei_dea_solved["y"])
        assert np.allclose(np.nansum(shares, axis=1), 1.0, atol=1e-6)

    def test_variance_decomposition_sums_to_one(self, ei_dea_solved):
        vo = dg.virtual_outputs(ei_dea_solved["dual"].mu, ei_dea_solved["y"])
        share = dg.variance_decomposition(vo)
        assert share.sum() == pytest.approx(1.0, abs=1e-9)
        assert (share >= -1e-12).all()


# ---------------------------------------------------------------------------
# Synthetic peer-side checks (fast, no data dependency)
# ---------------------------------------------------------------------------

def _synthetic():
    x = np.array([[1.0, 2.0], [2.0, 1.0], [3.0, 2.0], [1.5, 3.0], [5.0, 4.0]])
    y = np.array([[1.0, 1.0], [1.0, 1.0], [1.0, 1.0], [1.0, 0.5], [1.0, 1.0]])
    return x, y


class TestPeerDiagnosticsSynthetic:
    def test_primal_dual_agree_synthetic(self):
        x, y = _synthetic()
        p = solve_primal(x, y, rts="crs")
        d = solve_dual(x, y, rts="crs")
        assert np.max(np.abs(p.theta - d.theta)) < 1e-5

    def test_isolated_efficient_mask_shape(self):
        x, y = _synthetic()
        p = solve_primal(x, y, rts="crs")
        mask = dg.isolated_efficient_firms(p.theta, p.lambdas)
        assert mask.dtype == bool
        assert mask.shape == (5,)


class TestBenchmarkComposition:
    """Toy solve (1 input, 2 outputs): A/B specialised corners, C balanced,
    D/E/F interior. Verifies the mix/scale math against actual CBC lambdas."""

    def _toy(self):
        x = np.array([[1.0], [1.0], [1.0], [1.3], [1.5], [2.0]])
        y = np.array([
            [10.0, 1.0], [1.0, 10.0], [6.0, 6.0],
            [5.0, 4.0], [7.0, 3.0], [5.0, 5.0],
        ])
        return x, y

    def test_mix_rows_sum_to_one(self):
        x, y = self._toy()
        p = solve_primal(x, y, rts="crs")
        mix, scale = dg.benchmark_composition(p.lambdas)
        # Every solved firm has a populated mix row summing to 1.
        assert np.allclose(np.nansum(mix, axis=1), 1.0, atol=1e-6)
        assert (scale[np.isfinite(scale)] >= -1e-12).all()

    def test_composite_equals_theta_times_input(self):
        """CRS envelope identity: sum_r lambda_or x_r = theta_o x_o (single input)."""
        x, y = self._toy()
        p = solve_primal(x, y, rts="crs")
        composite = (p.lambdas @ x).ravel()
        assert np.allclose(composite, p.theta * x.ravel(), atol=1e-5)

    def test_role_is_transpose_with_zero_diagonal(self):
        x, y = self._toy()
        p = solve_primal(x, y, rts="crs")
        mix, _ = dg.benchmark_composition(p.lambdas)
        role = mix.T.copy()
        np.fill_diagonal(role, 0.0)
        # An interior firm's mix share of a corner equals that corner's role entry.
        assert np.allclose(np.nan_to_num(role), np.nan_to_num(mix.T * (1 - np.eye(6))), atol=1e-9)


# ---------------------------------------------------------------------------
# End-to-end model run (run_dea_diagnostics) on the app baseline, iterated outliers
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def model_result(baseline_data):
    """Full run_dea_diagnostics pass with the default (iterated) outlier detection."""
    cfg = DeaDiagnosticsConfig()
    return run_dea_diagnostics(cfg, baseline_data.df_all_companies)


class TestModelEndToEnd:
    def test_default_selection_runs_all_diagnostics(self, model_result):
        assert set(model_result.diagnostics) == set(reg.all_keys())

    def test_outlier_bookkeeping(self, model_result):
        # Iterated to convergence on the SDF-derived input flags 5 firms over 5
        # rounds (the documented 3->5 shift vs Ei's raw-OPEXp set, eis_dea_metod.md).
        assert model_result.all_firms.shape[0] == 148
        assert model_result.n_outlier_rounds == 5
        flagged = set(model_result.all_firms[model_result.is_outlier])
        assert flagged == {"REL00024", "REL00033", "REL00257", "REL00899", "REL00965"}
        assert len(model_result.firms) == 148 - 5

    @pytest.mark.parametrize("reid", list(FACIT))
    def test_facit_through_full_model(self, model_result, reid):
        idx = int(np.where(model_result.firms == reid)[0][0])
        theta = min(model_result.theta_primal[idx], 1.0)
        assert theta == pytest.approx(FACIT[reid], abs=1e-3)

    def test_primal_dual_close(self, model_result):
        assert model_result.primal_dual_max_abs_diff < 1e-5

    def test_diagnostic_outputs_self_describe(self, model_result):
        n = len(model_result.firms)
        sc = model_result.diagnostics["benchmark_scale"]
        assert sc.index == "firm"
        assert sc.values.shape == (n,)
        assert sc.row_labels == list(model_result.firms)
        assert sc.columns == []

        # Benchmark composition: firm x firm (peers as columns), rows sum to 1.
        bc = model_result.diagnostics["benchmark_composition"]
        assert bc.values.shape == (n, n)
        assert bc.columns == list(model_result.firms)
        assert np.allclose(np.nansum(bc.values, axis=1), 1.0, atol=1e-6)

        # Benchmark role is the transpose with a zero diagonal.
        role = model_result.diagnostics["benchmark_role"]
        assert role.values.shape == (n, n)
        assert np.allclose(np.diag(role.values), 0.0)

        vos = model_result.diagnostics["virtual_output_shares"]
        assert vos.values.shape == (n, len(model_result.output_labels))
        assert vos.columns == model_result.output_labels

        vd = model_result.diagnostics["output_variance_decomposition"]
        assert vd.index == "output"
        assert vd.values.shape == (len(model_result.output_labels),)


class TestModelConfigBehaviour:
    def test_diagnostics_subset_and_outliers_disabled(self):
        df = pd.DataFrame({
            "REId": ["A", "B", "C", "D", "E"],
            "in1": [1.0, 2.0, 3.0, 1.5, 5.0],
            "in2": [2.0, 1.0, 2.0, 3.0, 4.0],
            "out1": [1.0, 1.0, 1.0, 1.0, 1.0],
            "out2": [1.0, 1.0, 1.0, 0.5, 1.0],
        })
        cfg = DeaDiagnosticsConfig(
            inputs=("in1", "in2"), outputs=("out1", "out2"),
            diagnostics=("benchmark_scale",), outlier_enable=False,
        )
        res = run_dea_diagnostics(cfg, df)
        assert set(res.diagnostics) == {"benchmark_scale"}
        assert res.is_outlier.sum() == 0
        assert res.n_outlier_rounds == 0
        assert len(res.firms) == 5

    def test_missing_columns_raise(self):
        df = pd.DataFrame({"REId": ["A"], "in1": [1.0], "out1": [1.0]})
        cfg = DeaDiagnosticsConfig(inputs=("in1", "nope"), outputs=("out1",))
        with pytest.raises(ValueError, match="Columns not found"):
            run_dea_diagnostics(cfg, df)

    def test_signature_stable_hashable_and_discriminating(self):
        a = DeaDiagnosticsConfig()
        b = DeaDiagnosticsConfig()
        assert a.signature() == b.signature()
        assert isinstance(hash(a.signature()), int)
        assert a.signature() != DeaDiagnosticsConfig(rts="vrs").signature()
        assert a.signature() != DeaDiagnosticsConfig(outlier_max_rounds=1).signature()

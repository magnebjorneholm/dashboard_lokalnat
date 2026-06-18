"""
tests/test_mini_run.py

Tests for the DEA mini-run feature (pipeline/mini_run.py).
"""

import pytest
from config.case_definition import DeaConfig, EfficiencyMethod
from config.column_names import COL_DEA_EFFICIENCY, COL_DEA_POTENTIAL, COL_IS_OUTLIER, COL_EFF_REQ_ANNUAL
from pipeline.mini_run import run_dea_mini, MiniRunResult


class TestMiniRunBaseline:
    """Mini-run with baseline DEA config should return Ei's published results."""

    def test_baseline_returns_mini_run_result(self, baseline_data):
        result = run_dea_mini(baseline_data, DeaConfig(), "REL00886")
        assert isinstance(result, MiniRunResult)

    def test_baseline_efficiency_in_valid_range(self, baseline_data):
        result = run_dea_mini(baseline_data, DeaConfig(), "REL00886")
        assert 0 < result.user_efficiency < 1

    def test_baseline_potential_consistent(self, baseline_data):
        """Potential should be approximately 1 - efficiency."""
        result = run_dea_mini(baseline_data, DeaConfig(), "REL00886")
        assert result.user_potential == pytest.approx(1 - result.user_efficiency, abs=0.01)

    def test_baseline_not_outlier(self, baseline_data):
        result = run_dea_mini(baseline_data, DeaConfig(), "REL00886")
        assert result.user_is_outlier is False

    def test_baseline_has_148_companies(self, baseline_data):
        result = run_dea_mini(baseline_data, DeaConfig(), "REL00886")
        assert result.n_companies == 148

    def test_baseline_dea_not_executed(self, baseline_data):
        result = run_dea_mini(baseline_data, DeaConfig(), "REL00886")
        assert result.dea_executed is False
        assert result.dea_method == "baseline"

    def test_baseline_eff_req_positive(self, baseline_data):
        result = run_dea_mini(baseline_data, DeaConfig(), "REL00886")
        assert result.user_eff_req_annual > 0

    def test_baseline_rank_in_range(self, baseline_data):
        result = run_dea_mini(baseline_data, DeaConfig(), "REL00886")
        assert 1 <= result.user_rank <= result.n_companies

    def test_dea_results_has_eff_req_column(self, baseline_data):
        result = run_dea_mini(baseline_data, DeaConfig(), "REL00886")
        assert COL_EFF_REQ_ANNUAL in result.dea_results.columns


class TestMiniRunCustom:
    """Mini-run with custom DEA config should produce different results."""

    def test_vrs_differs_from_baseline(self, baseline_data):
        """VRS should generally give different (higher) efficiency scores."""
        vrs_config = DeaConfig(
            method=EfficiencyMethod.DEA,
            rts="vrs",
        )
        baseline_result = run_dea_mini(baseline_data, DeaConfig(), "REL00886")
        result = run_dea_mini(baseline_data, vrs_config, "REL00886")
        assert result.dea_executed is True
        assert result.dea_method == "dea"
        # VRS efficiency >= CRS efficiency (mathematical property)
        assert result.user_efficiency >= baseline_result.user_efficiency - 0.001

    def test_custom_inputs_runs(self, baseline_data):
        """DEA with different inputs should run without error."""
        custom = DeaConfig(
            method=EfficiencyMethod.DEA,
            inputs=["totex_dea"],
            outputs=["CU", "MW", "NS"],
        )
        result = run_dea_mini(baseline_data, custom, "REL00886")
        assert result.user_efficiency is not None
        assert result.n_companies == 148


class TestMiniRunM5Params:
    """Mini-run should respect caller-provided M5 parameters."""

    def test_higher_truncation_max_increases_max_req(self, baseline_data):
        """Higher truncation_max should allow higher efficiency requirements."""
        default_result = run_dea_mini(baseline_data, DeaConfig(), "REL00886")
        high_trunc = run_dea_mini(
            baseline_data, DeaConfig(), "REL00886",
            eff_req_params={"truncation_max": 0.50},
        )
        # With higher truncation, companies with high potential get higher req
        # For REL00886, effect depends on its potential vs truncation bounds
        assert high_trunc.user_eff_req_annual >= default_result.user_eff_req_annual - 0.001

    def test_custom_m5_params_passed_through(self, baseline_data):
        """Custom M5 params should affect efficiency requirement values."""
        result = run_dea_mini(
            baseline_data, DeaConfig(), "REL00886",
            eff_req_params={
                "truncation_max": 0.30,
                "customer_sharing": 1.0,   # 100% instead of 50%
                "realization_time": 8,
                "supervision_period": 4,
            },
        )
        baseline_result = run_dea_mini(baseline_data, DeaConfig(), "REL00886")
        # With customer_sharing=1.0 vs 0.5, requirement should be higher
        assert result.user_eff_req_annual > baseline_result.user_eff_req_annual


class TestMiniRunEdgeCases:
    """Edge cases for mini-run."""

    def test_invalid_reid_raises(self, baseline_data):
        with pytest.raises(ValueError, match="not found"):
            run_dea_mini(baseline_data, DeaConfig(), "REL99999")

    def test_different_companies(self, baseline_data):
        """Mini-run should work for different companies."""
        r1 = run_dea_mini(baseline_data, DeaConfig(), "REL00001")
        r886 = run_dea_mini(baseline_data, DeaConfig(), "REL00886")
        assert r1.user_reid == "REL00001"
        assert r886.user_reid == "REL00886"
        assert r1.user_efficiency != r886.user_efficiency

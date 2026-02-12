"""
tests/test_override_cascades.py

Integration tests for category override cascades through the pipeline.

Tests two scenarios:
1. Controllable override → changed DEA → changed eff_req → changed RF
2. Non-controllable override → changed RF only, unchanged DEA
"""

import pytest
from pipeline.core import PipelineResult, run_pipeline
from config.case_definition import (
    CaseDefinition, PreDeaConfig, PostDeaConfig, DeaConfig,
    CapbaseSource, CapexMethod, EfficiencyMethod,
)


USER_REID = "REL00886"

# Override multipliers for testing (10% increase)
CONTROLLABLE_OVERRIDE = {"RR73140_personnel": 1.10}
NON_CONTROLLABLE_OVERRIDE = {"grid_subscription": 1.10}


# =============================================================================
# Session-scoped fixtures — each pipeline run is expensive (~50s)
# =============================================================================

@pytest.fixture(scope="session")
def pipeline_ctrl_override(baseline_data):
    """Pipeline result with controllable category override (personnel +10%)."""
    config = CaseDefinition(
        name="Ctrl Override Test",
        user_reid=USER_REID,
        pre_dea=PreDeaConfig(
            capbase_source=CapbaseSource.BASELINE,
            method=CapexMethod.BASELINE,
            controllable_category_overrides=CONTROLLABLE_OVERRIDE,
        ),
        dea=DeaConfig(method=EfficiencyMethod.BASELINE),
        post_dea=PostDeaConfig(),
    )
    return run_pipeline(baseline_data, config, debug=False, validate=True)


@pytest.fixture(scope="session")
def pipeline_nc_override(baseline_data):
    """Pipeline result with non-controllable category override (grid_subscription +10%)."""
    config = CaseDefinition(
        name="NC Override Test",
        user_reid=USER_REID,
        pre_dea=PreDeaConfig(
            capbase_source=CapbaseSource.BASELINE,
            method=CapexMethod.BASELINE,
        ),
        dea=DeaConfig(method=EfficiencyMethod.BASELINE),
        post_dea=PostDeaConfig(
            non_controllable_category_overrides=NON_CONTROLLABLE_OVERRIDE,
        ),
    )
    return run_pipeline(baseline_data, config, debug=False, validate=True)


# =============================================================================
# Test: Controllable override cascade
# =============================================================================

class TestControllableOverrideCascade:
    """
    Controllable override flow:
    Pre-DEA (opex changes) → DEA re-runs → Extraction (new efficiency)
    → Post-DEA (new eff_req, new RF)
    """

    def test_pipeline_runs_successfully(self, pipeline_ctrl_override):
        assert isinstance(pipeline_ctrl_override, PipelineResult)

    def test_opex_increased(self, pipeline_result_886, pipeline_ctrl_override):
        """Personnel +10% should increase controllable_cost_average."""
        baseline_opex = pipeline_result_886.extraction.opex
        override_opex = pipeline_ctrl_override.extraction.opex
        assert override_opex > baseline_opex

    def test_totex_increased(self, pipeline_result_886, pipeline_ctrl_override):
        """TOTEX = CAPEX + OPEXp, so increased opex → increased totex."""
        baseline_totex = pipeline_result_886.extraction.totex
        override_totex = pipeline_ctrl_override.extraction.totex
        assert override_totex > baseline_totex

    def test_capex_unchanged(self, pipeline_result_886, pipeline_ctrl_override):
        """CAPEX should not be affected by controllable overrides."""
        assert pipeline_ctrl_override.extraction.capex == pytest.approx(
            pipeline_result_886.extraction.capex, rel=1e-9
        )

    def test_dea_re_executed(self, pipeline_ctrl_override):
        """DEA must re-run because controllable_cost_average is a DEA input."""
        assert pipeline_ctrl_override.dea.dea_executed is True
        assert pipeline_ctrl_override.dea.dea_method == "baseline_recalculated"

    def test_efficiency_changed(self, pipeline_result_886, pipeline_ctrl_override):
        """New DEA with higher opex → different efficiency score."""
        baseline_eff = pipeline_result_886.extraction.efficiency
        override_eff = pipeline_ctrl_override.extraction.efficiency
        assert override_eff != pytest.approx(baseline_eff, rel=1e-6)

    def test_eff_req_changed(self, pipeline_result_886, pipeline_ctrl_override):
        """Different DEA → different efficiency requirement."""
        baseline_req = pipeline_result_886.post_dea.user_eff_req_pct
        override_req = pipeline_ctrl_override.post_dea.user_eff_req_pct
        assert override_req != pytest.approx(baseline_req, rel=1e-6)

    def test_revenue_frame_changed(self, pipeline_result_886, pipeline_ctrl_override):
        """Changed controllable costs + changed eff_req → changed revenue frame."""
        baseline_rf = pipeline_result_886.post_dea.user_revenue_frame["revenue_frame_total"]
        override_rf = pipeline_ctrl_override.post_dea.user_revenue_frame["revenue_frame_total"]
        assert override_rf != pytest.approx(baseline_rf, rel=1e-6)

    def test_other_companies_unchanged(self, pipeline_result_886, pipeline_ctrl_override):
        """Only user's company should be affected, not the other 147."""
        import pandas as pd

        baseline_df = pipeline_result_886.pre_dea.df_all_companies
        override_df = pipeline_ctrl_override.pre_dea.df_all_companies

        # Compare controllable_cost_average for companies other than the user
        others_baseline = baseline_df[baseline_df["REId"] != USER_REID]["controllable_cost_average"]
        others_override = override_df[override_df["REId"] != USER_REID]["controllable_cost_average"]

        pd.testing.assert_series_equal(
            others_baseline.reset_index(drop=True),
            others_override.reset_index(drop=True),
        )

    def test_148_companies_preserved(self, pipeline_ctrl_override):
        """All 148 companies should be present."""
        assert len(pipeline_ctrl_override.pre_dea.df_all_companies) == 148
        assert len(pipeline_ctrl_override.dea.dea_results) == 148

    def test_pre_dea_opex_modified_flag(self, pipeline_ctrl_override):
        """The opex_modified flag should be set."""
        assert pipeline_ctrl_override.pre_dea.opex_modified is True


# =============================================================================
# Test: Non-controllable override cascade
# =============================================================================

class TestNonControllableOverrideCascade:
    """
    Non-controllable override flow:
    Only Post-DEA affected (revenue frame). DEA is unchanged.
    """

    def test_pipeline_runs_successfully(self, pipeline_nc_override):
        assert isinstance(pipeline_nc_override, PipelineResult)

    def test_dea_not_re_executed(self, pipeline_nc_override):
        """Non-controllable overrides don't affect DEA inputs."""
        assert pipeline_nc_override.dea.dea_executed is False
        assert pipeline_nc_override.dea.dea_method == "baseline"

    def test_efficiency_unchanged(self, pipeline_result_886, pipeline_nc_override):
        """DEA not re-run → same efficiency as baseline."""
        assert pipeline_nc_override.extraction.efficiency == pytest.approx(
            pipeline_result_886.extraction.efficiency, rel=1e-9
        )

    def test_opex_unchanged(self, pipeline_result_886, pipeline_nc_override):
        """Controllable costs not modified → same opex."""
        assert pipeline_nc_override.extraction.opex == pytest.approx(
            pipeline_result_886.extraction.opex, rel=1e-9
        )

    def test_eff_req_unchanged(self, pipeline_result_886, pipeline_nc_override):
        """Same DEA → same efficiency requirement."""
        assert pipeline_nc_override.post_dea.user_eff_req_pct == pytest.approx(
            pipeline_result_886.post_dea.user_eff_req_pct, rel=1e-9
        )

    def test_revenue_frame_changed(self, pipeline_result_886, pipeline_nc_override):
        """Non-controllable override → changed revenue frame total."""
        baseline_rf = pipeline_result_886.post_dea.user_revenue_frame["revenue_frame_total"]
        override_rf = pipeline_nc_override.post_dea.user_revenue_frame["revenue_frame_total"]
        assert override_rf != pytest.approx(baseline_rf, rel=1e-6)

    def test_non_controllable_component_changed(self, pipeline_result_886, pipeline_nc_override):
        """The non-controllable component should differ from baseline."""
        from config.column_names import COL_NON_CONTROLLABLE

        baseline_nc = pipeline_result_886.post_dea.user_revenue_frame.get(COL_NON_CONTROLLABLE, None)
        override_nc = pipeline_nc_override.post_dea.user_revenue_frame.get(COL_NON_CONTROLLABLE, None)

        if baseline_nc is not None and override_nc is not None:
            assert override_nc != pytest.approx(baseline_nc, rel=1e-6)

    def test_controllable_component_unchanged(self, pipeline_result_886, pipeline_nc_override):
        """The controllable component should be identical to baseline."""
        from config.column_names import COL_CONTROLLABLE_PERIOD

        baseline_ctrl = pipeline_result_886.post_dea.user_revenue_frame.get(COL_CONTROLLABLE_PERIOD, None)
        override_ctrl = pipeline_nc_override.post_dea.user_revenue_frame.get(COL_CONTROLLABLE_PERIOD, None)

        if baseline_ctrl is not None and override_ctrl is not None:
            assert override_ctrl == pytest.approx(baseline_ctrl, rel=1e-9)

    def test_148_companies_preserved(self, pipeline_nc_override):
        assert len(pipeline_nc_override.pre_dea.df_all_companies) == 148

    def test_pre_dea_opex_modified_flag_false(self, pipeline_nc_override):
        """No controllable override → opex_modified should be False."""
        assert pipeline_nc_override.pre_dea.opex_modified is False

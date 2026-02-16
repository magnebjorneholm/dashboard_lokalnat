"""
tests/test_override_cascades.py

Integration tests for M4 parameter/variable override cascades through the pipeline.

Tests:
1. opex_scaling=1.10 → OPEXp +10% all cos → DEA re-runs → eff_req changes → RF changes
2. non_adj_scaling=1.10 → non-controllable +10% → RF changes, DEA unchanged
3. flex_scaling=1.10 → flexibility +10% → RF changes, DEA unchanged
4. opex_override=X → user's OPEXp replaced → DEA may change
5. opex_scaling + opex_override → variable trumps for user's company
"""

import pytest
import pandas as pd
from pipeline.core import PipelineResult, run_pipeline
from config.case_definition import (
    CaseDefinition, PreDeaConfig, PostDeaConfig, DeaConfig,
    CapbaseSource, CapexMethod, EfficiencyMethod,
)


USER_REID = "REL00886"

# Scaling factors for testing
OPEX_SCALING = 1.10
NON_ADJ_SCALING = 1.10
FLEX_SCALING = 1.10


# =============================================================================
# Session-scoped fixtures — each pipeline run is expensive (~50s)
# =============================================================================

@pytest.fixture(scope="session")
def pipeline_opex_scaling(baseline_data):
    """Pipeline result with opex_scaling=1.10 (4.1.1 — all companies)."""
    config = CaseDefinition(
        name="OPEX Scaling Test",
        user_reid=USER_REID,
        pre_dea=PreDeaConfig(
            capbase_source=CapbaseSource.BASELINE,
            method=CapexMethod.BASELINE,
            opex_scaling=OPEX_SCALING,
        ),
        dea=DeaConfig(method=EfficiencyMethod.BASELINE),
        post_dea=PostDeaConfig(),
    )
    return run_pipeline(baseline_data, config, debug=False, validate=True)


@pytest.fixture(scope="session")
def pipeline_non_adj_scaling(baseline_data):
    """Pipeline result with non_adj_scaling=1.10 (4.1.3 — all companies)."""
    config = CaseDefinition(
        name="Non-Adj Scaling Test",
        user_reid=USER_REID,
        pre_dea=PreDeaConfig(
            capbase_source=CapbaseSource.BASELINE,
            method=CapexMethod.BASELINE,
        ),
        dea=DeaConfig(method=EfficiencyMethod.BASELINE),
        post_dea=PostDeaConfig(
            non_adj_scaling=NON_ADJ_SCALING,
        ),
    )
    return run_pipeline(baseline_data, config, debug=False, validate=True)


@pytest.fixture(scope="session")
def pipeline_flex_scaling(baseline_data):
    """Pipeline result with flex_scaling=1.10 (4.1.2 — all companies)."""
    config = CaseDefinition(
        name="Flex Scaling Test",
        user_reid=USER_REID,
        pre_dea=PreDeaConfig(
            capbase_source=CapbaseSource.BASELINE,
            method=CapexMethod.BASELINE,
        ),
        dea=DeaConfig(method=EfficiencyMethod.BASELINE),
        post_dea=PostDeaConfig(
            flex_scaling=FLEX_SCALING,
        ),
    )
    return run_pipeline(baseline_data, config, debug=False, validate=True)


@pytest.fixture(scope="session")
def pipeline_opex_override(baseline_data):
    """Pipeline result with opex_override for user's company (40.1.1)."""
    # Use a significantly different value — baseline is ~219k, use 250k
    config = CaseDefinition(
        name="OPEX Override Test",
        user_reid=USER_REID,
        pre_dea=PreDeaConfig(
            capbase_source=CapbaseSource.BASELINE,
            method=CapexMethod.BASELINE,
            opex_override=250000.0,
        ),
        dea=DeaConfig(method=EfficiencyMethod.BASELINE),
        post_dea=PostDeaConfig(),
    )
    return run_pipeline(baseline_data, config, debug=False, validate=True)


@pytest.fixture(scope="session")
def pipeline_scaling_plus_override(baseline_data):
    """Pipeline with both opex_scaling=1.10 and opex_override=250000."""
    config = CaseDefinition(
        name="Scaling+Override Test",
        user_reid=USER_REID,
        pre_dea=PreDeaConfig(
            capbase_source=CapbaseSource.BASELINE,
            method=CapexMethod.BASELINE,
            opex_scaling=OPEX_SCALING,
            opex_override=250000.0,
        ),
        dea=DeaConfig(method=EfficiencyMethod.BASELINE),
        post_dea=PostDeaConfig(),
    )
    return run_pipeline(baseline_data, config, debug=False, validate=True)


# =============================================================================
# Test 1: opex_scaling cascade (4.1.1)
# =============================================================================

class TestOpexScalingCascade:
    """
    4.1.1: Scale adjustable OPEX for all companies.
    Pre-DEA: COL_CONTROLLABLE_AVG *= 1.10 → TOTEX recalc → DEA re-runs.
    Post-DEA: sdf_controllable scaled → new eff_req → new RF.
    """

    def test_pipeline_runs_successfully(self, pipeline_opex_scaling):
        assert isinstance(pipeline_opex_scaling, PipelineResult)

    def test_opex_increased(self, pipeline_result_886, pipeline_opex_scaling):
        """All companies' OPEXp should increase by ~10%."""
        baseline_opex = pipeline_result_886.extraction.opex
        scaled_opex = pipeline_opex_scaling.extraction.opex
        assert scaled_opex > baseline_opex
        assert scaled_opex == pytest.approx(baseline_opex * OPEX_SCALING, rel=1e-6)

    def test_totex_increased(self, pipeline_result_886, pipeline_opex_scaling):
        baseline_totex = pipeline_result_886.extraction.totex
        scaled_totex = pipeline_opex_scaling.extraction.totex
        assert scaled_totex > baseline_totex

    def test_capex_unchanged(self, pipeline_result_886, pipeline_opex_scaling):
        assert pipeline_opex_scaling.extraction.capex == pytest.approx(
            pipeline_result_886.extraction.capex, rel=1e-9
        )

    def test_dea_re_executed(self, pipeline_opex_scaling):
        assert pipeline_opex_scaling.dea.dea_executed is True
        assert pipeline_opex_scaling.dea.dea_method == "baseline_recalculated"

    def test_efficiency_changed(self, pipeline_result_886, pipeline_opex_scaling):
        baseline_eff = pipeline_result_886.extraction.efficiency
        scaled_eff = pipeline_opex_scaling.extraction.efficiency
        assert scaled_eff != pytest.approx(baseline_eff, rel=1e-6)

    def test_eff_req_changed(self, pipeline_result_886, pipeline_opex_scaling):
        baseline_req = pipeline_result_886.post_dea.user_eff_req_pct
        scaled_req = pipeline_opex_scaling.post_dea.user_eff_req_pct
        assert scaled_req != pytest.approx(baseline_req, rel=1e-6)

    def test_revenue_frame_changed(self, pipeline_result_886, pipeline_opex_scaling):
        baseline_rf = pipeline_result_886.post_dea.user_revenue_frame["revenue_frame_total"]
        scaled_rf = pipeline_opex_scaling.post_dea.user_revenue_frame["revenue_frame_total"]
        assert scaled_rf != pytest.approx(baseline_rf, rel=1e-6)

    def test_all_companies_scaled(self, pipeline_result_886, pipeline_opex_scaling):
        """All 148 companies' controllable_cost_average should scale by 1.10."""
        baseline_df = pipeline_result_886.pre_dea.df_all_companies
        scaled_df = pipeline_opex_scaling.pre_dea.df_all_companies
        ratio = (
            scaled_df.set_index("REId")["controllable_cost_average"]
            / baseline_df.set_index("REId")["controllable_cost_average"]
        )
        assert ratio.mean() == pytest.approx(OPEX_SCALING, rel=1e-6)

    def test_pre_dea_opex_modified_flag(self, pipeline_opex_scaling):
        assert pipeline_opex_scaling.pre_dea.opex_modified is True

    def test_148_companies_preserved(self, pipeline_opex_scaling):
        assert len(pipeline_opex_scaling.pre_dea.df_all_companies) == 148


# =============================================================================
# Test 2: non_adj_scaling cascade (4.1.3)
# =============================================================================

class TestNonAdjScalingCascade:
    """
    4.1.3: Scale non-adjustable OPEX for all companies.
    Only affects RF. DEA and efficiency unchanged.
    """

    def test_pipeline_runs_successfully(self, pipeline_non_adj_scaling):
        assert isinstance(pipeline_non_adj_scaling, PipelineResult)

    def test_dea_not_re_executed(self, pipeline_non_adj_scaling):
        assert pipeline_non_adj_scaling.dea.dea_executed is False
        assert pipeline_non_adj_scaling.dea.dea_method == "baseline"

    def test_efficiency_unchanged(self, pipeline_result_886, pipeline_non_adj_scaling):
        assert pipeline_non_adj_scaling.extraction.efficiency == pytest.approx(
            pipeline_result_886.extraction.efficiency, rel=1e-9
        )

    def test_opex_unchanged(self, pipeline_result_886, pipeline_non_adj_scaling):
        assert pipeline_non_adj_scaling.extraction.opex == pytest.approx(
            pipeline_result_886.extraction.opex, rel=1e-9
        )

    def test_eff_req_unchanged(self, pipeline_result_886, pipeline_non_adj_scaling):
        assert pipeline_non_adj_scaling.post_dea.user_eff_req_pct == pytest.approx(
            pipeline_result_886.post_dea.user_eff_req_pct, rel=1e-9
        )

    def test_revenue_frame_changed(self, pipeline_result_886, pipeline_non_adj_scaling):
        baseline_rf = pipeline_result_886.post_dea.user_revenue_frame["revenue_frame_total"]
        scaled_rf = pipeline_non_adj_scaling.post_dea.user_revenue_frame["revenue_frame_total"]
        assert scaled_rf != pytest.approx(baseline_rf, rel=1e-6)

    def test_non_controllable_component_changed(self, pipeline_result_886, pipeline_non_adj_scaling):
        from config.column_names import COL_NON_CONTROLLABLE
        baseline_nc = pipeline_result_886.post_dea.user_revenue_frame.get(COL_NON_CONTROLLABLE, None)
        scaled_nc = pipeline_non_adj_scaling.post_dea.user_revenue_frame.get(COL_NON_CONTROLLABLE, None)
        if baseline_nc is not None and scaled_nc is not None:
            assert scaled_nc != pytest.approx(baseline_nc, rel=1e-6)

    def test_148_companies_preserved(self, pipeline_non_adj_scaling):
        assert len(pipeline_non_adj_scaling.pre_dea.df_all_companies) == 148


# =============================================================================
# Test 3: flex_scaling cascade (4.1.2)
# =============================================================================

class TestFlexScalingCascade:
    """
    4.1.2: Scale flexibility services for all companies.
    Only affects RF. DEA and efficiency unchanged.
    """

    def test_pipeline_runs_successfully(self, pipeline_flex_scaling):
        assert isinstance(pipeline_flex_scaling, PipelineResult)

    def test_dea_not_re_executed(self, pipeline_flex_scaling):
        assert pipeline_flex_scaling.dea.dea_executed is False

    def test_efficiency_unchanged(self, pipeline_result_886, pipeline_flex_scaling):
        assert pipeline_flex_scaling.extraction.efficiency == pytest.approx(
            pipeline_result_886.extraction.efficiency, rel=1e-9
        )

    def test_revenue_frames_changed_for_companies_with_flex(self, pipeline_result_886, pipeline_flex_scaling):
        """Companies with non-zero flexibility should see changed RF.
        Company 886 has 0 flexibility, so check all_revenue_frames instead."""
        baseline_all = pipeline_result_886.post_dea.all_revenue_frames
        scaled_all = pipeline_flex_scaling.post_dea.all_revenue_frames
        diff = (
            scaled_all.set_index("REId")["revenue_frame_total"]
            - baseline_all.set_index("REId")["revenue_frame_total"]
        )
        # At least 30 companies (out of 34 with non-zero flex) should differ
        assert (diff.abs() > 1.0).sum() >= 30


# =============================================================================
# Test 4: opex_override (40.1.1) — user's company only
# =============================================================================

class TestOpexOverride:
    """
    40.1.1: Override user's OPEXp with absolute value.
    Only user's company changes. DEA re-runs (opex_modified).
    """

    def test_pipeline_runs_successfully(self, pipeline_opex_override):
        assert isinstance(pipeline_opex_override, PipelineResult)

    def test_user_opex_overridden(self, pipeline_opex_override):
        assert pipeline_opex_override.extraction.opex == pytest.approx(250000.0, rel=1e-6)

    def test_dea_re_executed(self, pipeline_opex_override):
        assert pipeline_opex_override.dea.dea_executed is True

    def test_other_companies_unchanged(self, pipeline_result_886, pipeline_opex_override):
        baseline_df = pipeline_result_886.pre_dea.df_all_companies
        override_df = pipeline_opex_override.pre_dea.df_all_companies
        others_baseline = baseline_df[baseline_df["REId"] != USER_REID]["controllable_cost_average"]
        others_override = override_df[override_df["REId"] != USER_REID]["controllable_cost_average"]
        pd.testing.assert_series_equal(
            others_baseline.reset_index(drop=True),
            others_override.reset_index(drop=True),
        )

    def test_pre_dea_opex_modified_flag(self, pipeline_opex_override):
        assert pipeline_opex_override.pre_dea.opex_modified is True

    def test_revenue_frame_changed(self, pipeline_result_886, pipeline_opex_override):
        baseline_rf = pipeline_result_886.post_dea.user_revenue_frame["revenue_frame_total"]
        override_rf = pipeline_opex_override.post_dea.user_revenue_frame["revenue_frame_total"]
        assert override_rf != pytest.approx(baseline_rf, rel=1e-6)


# =============================================================================
# Test 5: opex_scaling + opex_override — variable trumps for user
# =============================================================================

class TestScalingPlusOverride:
    """
    Both opex_scaling=1.10 and opex_override=250000.
    For user: override value trumps (250000, not 219k*1.10).
    For others: scaling applied (all get *1.10).
    """

    def test_pipeline_runs_successfully(self, pipeline_scaling_plus_override):
        assert isinstance(pipeline_scaling_plus_override, PipelineResult)

    def test_user_gets_override_value(self, pipeline_scaling_plus_override):
        """User's opex should be the override, not baseline*scaling."""
        assert pipeline_scaling_plus_override.extraction.opex == pytest.approx(
            250000.0, rel=1e-6
        )

    def test_others_get_scaling(self, pipeline_result_886, pipeline_scaling_plus_override):
        """Other companies should have opex * 1.10."""
        baseline_df = pipeline_result_886.pre_dea.df_all_companies
        combo_df = pipeline_scaling_plus_override.pre_dea.df_all_companies

        others_bl = baseline_df[baseline_df["REId"] != USER_REID].set_index("REId")["controllable_cost_average"]
        others_co = combo_df[combo_df["REId"] != USER_REID].set_index("REId")["controllable_cost_average"]

        ratio = others_co / others_bl
        assert ratio.mean() == pytest.approx(OPEX_SCALING, rel=1e-6)

    def test_user_same_as_override_only(self, pipeline_opex_override, pipeline_scaling_plus_override):
        """User's extraction.opex should match the override-only scenario."""
        assert pipeline_scaling_plus_override.extraction.opex == pytest.approx(
            pipeline_opex_override.extraction.opex, rel=1e-6
        )

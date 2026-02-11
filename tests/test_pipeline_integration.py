"""
tests/test_pipeline_integration.py

Integration tests for the full pipeline.
Runs run_pipeline() with baseline config and validates structure and values.
"""

import pytest
import pandas as pd
from pipeline.core import PipelineResult, run_pipeline, validate_pipeline_result
from config.case_definition import get_baseline_config


# Hardcoded expected values for REL00886 pipeline result
PIPELINE_EXTRACTION_886 = {
    "user_reid": "REL00886",
    "capex": 421649.2177260368,
    "opex": 212723.3167140447,
    "totex": 634372.5344400815,
    "cu": 100485.0,
    "mw": 428.5,
    "ns": 2623.25,
    "efficiency": 0.793547303468252,
    "potential": 0.2064526965,
    "is_outlier": False,
}

PIPELINE_POST_DEA_886 = {
    "user_eff_req_pct": 0.012660813335849896,
    "revenue_frame_total": 3930334.9707558416,
}


class TestPipelineRuns:
    def test_baseline_runs_without_error(self, pipeline_result_886):
        assert isinstance(pipeline_result_886, PipelineResult)

    def test_validation_passes(self, pipeline_result_886):
        assert validate_pipeline_result(pipeline_result_886) is True


class TestPipelineStructure:
    def test_all_stages_present(self, pipeline_result_886):
        result = pipeline_result_886
        assert result.baseline is not None
        assert result.pre_dea is not None
        assert result.dea is not None
        assert result.extraction is not None
        assert result.post_dea is not None

    def test_148_companies_preserved(self, pipeline_result_886):
        result = pipeline_result_886
        assert len(result.baseline.df_all_companies) == 148
        assert len(result.pre_dea.df_all_companies) == 148

    def test_user_reid_consistent(self, pipeline_result_886):
        result = pipeline_result_886
        assert result.user_reid == "REL00886"
        assert result.extraction.user_reid == "REL00886"
        assert result.post_dea.user_reid == "REL00886"


class TestPipelineExtractionValues:
    def test_capex(self, pipeline_result_886):
        ext = pipeline_result_886.extraction
        assert ext.capex == pytest.approx(
            PIPELINE_EXTRACTION_886["capex"], rel=1e-3
        )

    def test_opex(self, pipeline_result_886):
        ext = pipeline_result_886.extraction
        assert ext.opex == pytest.approx(
            PIPELINE_EXTRACTION_886["opex"], rel=1e-3
        )

    def test_efficiency(self, pipeline_result_886):
        ext = pipeline_result_886.extraction
        assert ext.efficiency == pytest.approx(
            PIPELINE_EXTRACTION_886["efficiency"], rel=1e-3
        )

    def test_potential(self, pipeline_result_886):
        ext = pipeline_result_886.extraction
        assert ext.potential == pytest.approx(
            PIPELINE_EXTRACTION_886["potential"], rel=1e-3
        )

    def test_is_not_outlier(self, pipeline_result_886):
        assert pipeline_result_886.extraction.is_outlier == False

    def test_volumes(self, pipeline_result_886):
        ext = pipeline_result_886.extraction
        assert ext.cu == pytest.approx(PIPELINE_EXTRACTION_886["cu"], rel=1e-6)
        assert ext.mw == pytest.approx(PIPELINE_EXTRACTION_886["mw"], rel=1e-6)
        assert ext.ns == pytest.approx(PIPELINE_EXTRACTION_886["ns"], rel=1e-6)


class TestPipelinePostDEA:
    def test_user_eff_req(self, pipeline_result_886):
        post = pipeline_result_886.post_dea
        assert post.user_eff_req_pct == pytest.approx(
            PIPELINE_POST_DEA_886["user_eff_req_pct"], rel=1e-6
        )

    def test_revenue_frame_total(self, pipeline_result_886):
        post = pipeline_result_886.post_dea
        rf_total = post.user_revenue_frame["revenue_frame_total"]
        assert rf_total == pytest.approx(
            PIPELINE_POST_DEA_886["revenue_frame_total"], rel=1e-3
        )

    def test_all_revenue_frames_positive(self, pipeline_result_886):
        rf = pipeline_result_886.post_dea.all_revenue_frames
        # Filter to companies that have a valid revenue frame
        valid = rf[rf["revenue_frame_total"].notna()]
        n_positive = (valid["revenue_frame_total"] > 0).sum()
        # All 148 should be positive
        assert n_positive >= 148

    def test_all_eff_reqs_shape(self, pipeline_result_886):
        eff_reqs = pipeline_result_886.post_dea.all_eff_reqs
        assert len(eff_reqs) == 148

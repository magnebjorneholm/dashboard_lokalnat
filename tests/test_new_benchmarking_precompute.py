"""
tests/test_new_benchmarking_precompute.py

Guards the pre-computed main-spec bundle for the new benchmarking model
(data/new_benchmarking/, produced by scripts/precompute_new_benchmarking.py and loaded
by data_loaders.new_benchmarking_data.load_precomputed_main).

Two things are checked:
  1. The bundle loads and reconstructs a well-formed NewBenchmarkingResult.
  2. It still matches a live recomputation — the staleness guard. If this fails, the
     committed bundle has drifted from the code/data and must be regenerated:
         ./venv/Scripts/python.exe scripts/precompute_new_benchmarking.py
"""

import pytest
import pandas as pd

from config.column_names import (
    COL_REID, COL_DEA_EFFICIENCY, COL_TOTEX_NEW, COL_EFF_REQ_DELTA,
)
from calculations.new_benchmarking import run_new_benchmarking, NewBenchmarkingConfig
from data_loaders.new_benchmarking_data import load_precomputed_main, MANIFEST_JSON


pytestmark = pytest.mark.skipif(
    not MANIFEST_JSON.exists(),
    reason="No pre-computed bundle (run scripts/precompute_new_benchmarking.py)",
)


@pytest.fixture(scope="module")
def precomputed():
    result = load_precomputed_main()
    assert result is not None, "bundle present but failed to load / signature mismatch"
    return result


def _aligned(a: pd.DataFrame, b: pd.DataFrame, col: str):
    """Two REId-aligned series (precomputed, live) for the same column."""
    m = a[[COL_REID, col]].merge(b[[COL_REID, col]], on=COL_REID, suffixes=("_pc", "_lv"))
    return (
        m[f"{col}_pc"].reset_index(drop=True),
        m[f"{col}_lv"].reset_index(drop=True),
    )


class TestBundleShape:
    def test_148_rows(self, precomputed):
        assert len(precomputed.dea_new) == 148
        assert len(precomputed.dea_current) == 148

    def test_required_columns(self, precomputed):
        assert COL_DEA_EFFICIENCY in precomputed.dea_new.columns
        assert COL_TOTEX_NEW in precomputed.totex.columns
        assert COL_EFF_REQ_DELTA in precomputed.comparison.columns

    def test_env_per_company_present(self, precomputed):
        assert not precomputed.env_capex.cable_adjustment.per_company.empty
        assert not precomputed.env_capex.station_adjustment.per_company.empty

    def test_new_model_outputs_listed(self, precomputed):
        assert len(precomputed.new_model_outputs) > 0


class TestBundleFreshness:
    """The committed bundle must match a live recomputation of the default main spec."""

    @pytest.fixture(scope="class")
    def live(self, baseline_data):
        return run_new_benchmarking(NewBenchmarkingConfig(), baseline_data=baseline_data)

    def test_dea_efficiency_matches(self, precomputed, live):
        pc, lv = _aligned(precomputed.dea_new, live.dea_new, COL_DEA_EFFICIENCY)
        pd.testing.assert_series_equal(pc, lv, atol=1e-6, check_names=False)

    def test_totex_matches(self, precomputed, live):
        pc, lv = _aligned(precomputed.totex, live.totex, COL_TOTEX_NEW)
        pd.testing.assert_series_equal(pc, lv, rtol=1e-6, check_names=False)

    def test_eff_req_delta_matches(self, precomputed, live):
        pc, lv = _aligned(precomputed.comparison, live.comparison, COL_EFF_REQ_DELTA)
        pd.testing.assert_series_equal(pc, lv, atol=1e-6, check_names=False)

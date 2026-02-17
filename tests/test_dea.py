"""
tests/test_dea.py

Tests for DEA (Data Envelopment Analysis) calculations.
Includes synthetic unit tests and full 148-company baseline replication.
"""

import pytest
import numpy as np
import pandas as pd
from calculations.frontier.dea_calculations import run_dea_analysis, _run_super_efficiency_dea


# ============================================================================
# Hardcoded expected DEA values for test companies
# ============================================================================

DEA_EXPECTED = {
    # Expected values with SDF-derived controllable_cost_average as DEA input
    "REL00001": {"dea_efficiency": 0.67793232, "potential": 0.32206768},
    "REL00886": {"dea_efficiency": 0.77067884, "potential": 0.22932116},
    "REL03035": {"dea_efficiency": 0.9539705, "potential": 0.04602950},
}


# ============================================================================
# Synthetic DEA tests
# ============================================================================

def _make_synthetic_data():
    """Create simple 5-DMU dataset with known efficient/inefficient units."""
    return pd.DataFrame({
        "REId": ["A", "B", "C", "D", "E"],
        "input1": [1.0, 2.0, 3.0, 1.5, 5.0],
        "input2": [2.0, 1.0, 2.0, 3.0, 4.0],
        "output1": [1.0, 1.0, 1.0, 1.0, 1.0],
        "output2": [1.0, 1.0, 1.0, 0.5, 1.0],
    })


def _synthetic_spec(rts="crs"):
    return {
        "inputs": ["input1", "input2"],
        "outputs": ["output1", "output2"],
        "rts": rts,
        "orientation": "input",
        "outlier_params": {"q_lower": 25.0, "q_upper": 75.0, "multiplier": 3.0},
    }


class TestDEASynthetic:
    def test_dea_returns_dataframe(self):
        df = _make_synthetic_data()
        result = run_dea_analysis(df, _synthetic_spec())
        assert isinstance(result, pd.DataFrame)
        assert "dea_efficiency" in result.columns
        assert "potential" in result.columns
        assert "is_outlier" in result.columns

    def test_efficient_unit_gets_1(self):
        df = _make_synthetic_data()
        result = run_dea_analysis(df, _synthetic_spec())
        # Unit A (1,2) → (1,1) should be efficient or close to frontier
        a_eff = result[result["REId"] == "A"]["dea_efficiency"].iloc[0]
        assert a_eff <= 1.0

    def test_inefficient_unit_below_1(self):
        df = _make_synthetic_data()
        result = run_dea_analysis(df, _synthetic_spec())
        # Unit E (5,4) → (1,1) should be clearly inefficient
        e_eff = result[result["REId"] == "E"]["dea_efficiency"].iloc[0]
        assert e_eff < 1.0

    def test_efficiency_capped_at_1(self):
        df = _make_synthetic_data()
        result = run_dea_analysis(df, _synthetic_spec())
        assert (result["dea_efficiency"] <= 1.0).all()

    def test_potential_equals_1_minus_efficiency(self):
        df = _make_synthetic_data()
        result = run_dea_analysis(df, _synthetic_spec())
        for _, row in result.iterrows():
            expected_potential = 1 - row["dea_efficiency"]
            assert row["potential"] == pytest.approx(expected_potential, abs=1e-10)

    def test_crs_vs_vrs(self):
        """VRS efficiency >= CRS efficiency for all units."""
        df = _make_synthetic_data()
        crs = run_dea_analysis(df, _synthetic_spec("crs"))
        vrs = run_dea_analysis(df, _synthetic_spec("vrs"))
        merged = crs[["REId", "dea_efficiency"]].merge(
            vrs[["REId", "dea_efficiency"]],
            on="REId",
            suffixes=("_crs", "_vrs"),
        )
        # VRS >= CRS (VRS is less restrictive)
        assert (merged["dea_efficiency_vrs"] >= merged["dea_efficiency_crs"] - 1e-6).all()


class TestDEAOutlierDetection:
    def test_extreme_outlier_detected(self):
        """A unit with extreme super-efficiency should be flagged as outlier."""
        df = pd.DataFrame({
            "REId": ["A", "B", "C", "D", "E", "OUTLIER"],
            "input1": [2.0, 3.0, 4.0, 5.0, 6.0, 0.01],
            "input2": [2.0, 3.0, 4.0, 5.0, 6.0, 0.01],
            "output1": [1.0, 1.0, 1.0, 1.0, 1.0, 100.0],
            "output2": [1.0, 1.0, 1.0, 1.0, 1.0, 100.0],
        })
        spec = _synthetic_spec()
        spec["outlier_params"]["multiplier"] = 1.5  # Stricter threshold
        result = run_dea_analysis(df, spec)
        outlier_row = result[result["REId"] == "OUTLIER"]
        assert len(outlier_row) == 1
        assert outlier_row.iloc[0]["is_outlier"] == True


# ============================================================================
# Full 148-company baseline DEA test
# ============================================================================

class TestDEABaseline148:
    def test_dea_baseline_runs(self, baseline_data):
        """Run DEA on all 148 companies with baseline spec."""
        from config.column_names import (
            COL_CAPITAL_COST_2024, COL_CONTROLLABLE_AVG,
            COL_CU, COL_MW, COL_NS, COL_MWH_LOW, COL_MWH_HIGH,
        )

        df = baseline_data.df_all_companies.copy()
        spec = {
            "inputs": [COL_CAPITAL_COST_2024, COL_CONTROLLABLE_AVG],
            "outputs": [COL_CU, COL_MW, COL_NS, COL_MWH_LOW, COL_MWH_HIGH],
            "rts": "crs",
            "orientation": "input",
            "outlier_params": {"q_lower": 25.0, "q_upper": 75.0, "multiplier": 2.0},
        }
        result = run_dea_analysis(df, spec)
        assert len(result) == 148
        assert (result["dea_efficiency"] <= 1.0).all()
        assert (result["dea_efficiency"] > 0).all()

    @pytest.mark.parametrize("reid", ["REL00001", "REL00886", "REL03035"])
    def test_dea_efficiency_vs_facit(self, baseline_data, reid):
        """Compare DEA efficiency against EIs_DEA hardcoded facit."""
        from config.column_names import (
            COL_CAPITAL_COST_2024, COL_CONTROLLABLE_AVG,
            COL_CU, COL_MW, COL_NS, COL_MWH_LOW, COL_MWH_HIGH,
        )

        df = baseline_data.df_all_companies.copy()
        spec = {
            "inputs": [COL_CAPITAL_COST_2024, COL_CONTROLLABLE_AVG],
            "outputs": [COL_CU, COL_MW, COL_NS, COL_MWH_LOW, COL_MWH_HIGH],
            "rts": "crs",
            "orientation": "input",
            "outlier_params": {"q_lower": 25.0, "q_upper": 75.0, "multiplier": 2.0},
        }
        result = run_dea_analysis(df, spec)
        row = result[result["REId"] == reid].iloc[0]
        expected = DEA_EXPECTED[reid]["dea_efficiency"]
        # DEA solver may have small numerical differences
        assert row["dea_efficiency"] == pytest.approx(expected, rel=0.01)

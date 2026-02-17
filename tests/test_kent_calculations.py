"""
tests/test_kent_calculations.py

Tests for KENT capital cost calculations (steps 5-8).
Uses capbase_a_mini fixture (3 test companies).
"""

import pytest
import numpy as np
import pandas as pd
from conftest import WACC_BASELINE, TOLERANCE_REL


# Hardcoded expected values from baseline run
KENT_EXPECTED = {
    1: {
        "capital_cost_2024": 59620.580225047,
        "capital_cost_2025": 59469.50334744877,
        "capital_cost_2026": 59374.36580991927,
        "capital_cost_2027": 59248.55921606674,
        "capital_cost_period": 237713.00859848177,
        "depreciation_2024": 31020.081977323356,
        "depreciation_2025": 31189.43937972891,
        "depreciation_2026": 31407.014841634365,
        "depreciation_2027": 31599.689711031584,
        "depreciation_period": 125216.22590971823,
        "return_on_assets_2024": 28600.498247723648,
        "return_on_assets_2025": 28280.063967719867,
        "return_on_assets_2026": 27967.350968284904,
        "return_on_assets_2027": 27648.86950503515,
        "return_on_assets_period": 112496.78268876356,
    },
    886: {
        "capital_cost_2024": 421294.7929530114,
        "capital_cost_2025": 426379.45313688926,
        "capital_cost_2026": 430758.4156895735,
        "capital_cost_2027": 435833.0997066046,
        "capital_cost_period": 1714265.7614860786,
        "depreciation_2024": 231034.10364999977,
        "depreciation_2025": 234623.28254953108,
        "depreciation_2026": 237620.61005355237,
        "depreciation_2027": 241392.8488825707,
        "depreciation_period": 944670.8451356539,
        "return_on_assets_2024": 190260.68930301163,
        "return_on_assets_2025": 191756.1705873582,
        "return_on_assets_2026": 193137.80563602116,
        "return_on_assets_2027": 194440.25082403392,
        "return_on_assets_period": 769594.916350425,
    },
    3035: {
        "capital_cost_2024": 3530396.9421964325,
        "capital_cost_2025": 3506557.173876698,
        "capital_cost_2026": 3536402.37143972,
        "capital_cost_2027": 3614423.920061847,
        "capital_cost_period": 14187780.407574698,
        "depreciation_2024": 1804774.779466462,
        "depreciation_2025": 1792785.0836240505,
        "depreciation_2026": 1800509.2488166112,
        "depreciation_2027": 1830958.87470062,
        "depreciation_period": 7229027.986607743,
        "return_on_assets_2024": 1725622.1627299704,
        "return_on_assets_2025": 1713772.0902526479,
        "return_on_assets_2026": 1735893.1226231088,
        "return_on_assets_2027": 1783465.0453612274,
        "return_on_assets_period": 6958752.420966954,
    },
}


class TestKentReturnStructure:
    def test_returns_three_dataframes(self, kent_results_mini):
        df_detailed, df_network, df_category = kent_results_mini
        assert isinstance(df_detailed, pd.DataFrame)
        assert isinstance(df_network, pd.DataFrame)
        assert isinstance(df_category, pd.DataFrame)

    def test_network_has_3_companies(self, kent_results_mini):
        _, df_network, _ = kent_results_mini
        assert len(df_network) == 3
        assert set(df_network["id_network"]) == {1, 886, 3035}

    def test_network_column_presence(self, kent_results_mini):
        _, df_network, _ = kent_results_mini
        required_cols = [
            "id_network", "REId",
            "capital_cost_2024", "capital_cost_2025",
            "capital_cost_2026", "capital_cost_2027",
            "capital_cost_period",
            "depreciation_2024", "depreciation_period",
            "return_on_assets_2024", "return_on_assets_period",
        ]
        for col in required_cols:
            assert col in df_network.columns, f"Missing column: {col}"


class TestKentValues:
    def test_values_positive(self, kent_results_mini):
        _, df_network, _ = kent_results_mini
        for col in ["capital_cost_2024", "depreciation_2024", "return_on_assets_2024"]:
            assert (df_network[col] > 0).all(), f"{col} has non-positive values"

    @pytest.mark.parametrize("id_net", [1, 886, 3035])
    def test_capital_cost_2024(self, kent_results_mini, id_net):
        _, df_network, _ = kent_results_mini
        row = df_network[df_network["id_network"] == id_net].iloc[0]
        expected = KENT_EXPECTED[id_net]["capital_cost_2024"]
        assert row["capital_cost_2024"] == pytest.approx(expected, rel=1e-8)

    @pytest.mark.parametrize("id_net", [1, 886, 3035])
    def test_capital_cost_period(self, kent_results_mini, id_net):
        _, df_network, _ = kent_results_mini
        row = df_network[df_network["id_network"] == id_net].iloc[0]
        expected = KENT_EXPECTED[id_net]["capital_cost_period"]
        assert row["capital_cost_period"] == pytest.approx(expected, rel=1e-8)

    @pytest.mark.parametrize("id_net", [1, 886, 3035])
    def test_depreciation_2024(self, kent_results_mini, id_net):
        _, df_network, _ = kent_results_mini
        row = df_network[df_network["id_network"] == id_net].iloc[0]
        expected = KENT_EXPECTED[id_net]["depreciation_2024"]
        assert row["depreciation_2024"] == pytest.approx(expected, rel=1e-8)

    @pytest.mark.parametrize("id_net", [1, 886, 3035])
    def test_return_on_assets_period(self, kent_results_mini, id_net):
        _, df_network, _ = kent_results_mini
        row = df_network[df_network["id_network"] == id_net].iloc[0]
        expected = KENT_EXPECTED[id_net]["return_on_assets_period"]
        assert row["return_on_assets_period"] == pytest.approx(expected, rel=1e-8)


class TestKentConsistency:
    @pytest.mark.parametrize("id_net", [1, 886, 3035])
    def test_period_equals_yearly_sum(self, kent_results_mini, id_net):
        _, df_network, _ = kent_results_mini
        row = df_network[df_network["id_network"] == id_net].iloc[0]
        yearly_sum = sum(row[f"capital_cost_{y}"] for y in [2024, 2025, 2026, 2027])
        assert row["capital_cost_period"] == pytest.approx(yearly_sum, rel=1e-8)

    @pytest.mark.parametrize("id_net", [1, 886, 3035])
    def test_capcost_equals_dep_plus_return(self, kent_results_mini, id_net):
        _, df_network, _ = kent_results_mini
        row = df_network[df_network["id_network"] == id_net].iloc[0]
        for year in [2024, 2025, 2026, 2027]:
            dep = row[f"depreciation_{year}"]
            ret = row[f"return_on_assets_{year}"]
            cap = row[f"capital_cost_{year}"]
            assert cap == pytest.approx(dep + ret, rel=1e-6)

    def test_category_aggregation(self, kent_results_mini):
        _, df_network, df_category = kent_results_mini
        for id_net in [1, 886, 3035]:
            cat_rows = df_category[df_category["id_network"] == id_net]
            net_row = df_network[df_network["id_network"] == id_net].iloc[0]
            # Sum capcost_sum across categories and time codes for this network
            cat_total = cat_rows["capcost_sum"].sum()
            net_total = net_row["capital_cost_period"]
            assert cat_total == pytest.approx(net_total, rel=1e-6)


class TestKentWACCSensitivity:
    def test_higher_wacc_increases_returns(self, capbase_mini):
        from calculations.capex.kent_calculations import run_kent_calculations_batch

        _, net_low, _ = run_kent_calculations_batch(capbase_mini, wacc=0.03)
        _, net_high, _ = run_kent_calculations_batch(capbase_mini, wacc=0.06)

        for id_net in [1, 886, 3035]:
            low = net_low[net_low["id_network"] == id_net].iloc[0]["return_on_assets_2024"]
            high = net_high[net_high["id_network"] == id_net].iloc[0]["return_on_assets_2024"]
            assert high > low


class TestKentNormvalueAdjustment:
    def test_normvalue_scaling(self, capbase_mini):
        from calculations.capex.kent_calculations import run_kent_calculations_batch

        _, net_base, _ = run_kent_calculations_batch(capbase_mini, wacc=WACC_BASELINE)
        # Scale all categories by 1.1
        adjustments = {i: 1.1 for i in range(1, 18)}
        _, net_scaled, _ = run_kent_calculations_batch(
            capbase_mini, wacc=WACC_BASELINE, normvalue_adjustments=adjustments
        )

        for id_net in [1, 886, 3035]:
            base = net_base[net_base["id_network"] == id_net].iloc[0]["capital_cost_period"]
            scaled = net_scaled[net_scaled["id_network"] == id_net].iloc[0]["capital_cost_period"]
            # Scaled should be higher (more NUAV → more depreciation + return)
            assert scaled > base

"""
tests/test_controllable_costs.py

Tests for controllable cost calculations (OPEX/TOTEX methods).
"""

import pytest
import numpy as np
import pandas as pd
from calculations.controllable_cost_calculations import (
    calculate_controllable_with_eff_req,
    get_controllable_from_sdf,
    _calculate_controllable_single_company,
)


class TestControllableSingleCompany:
    """Test the core per-company calculation logic."""

    def test_opex_basic(self):
        result = _calculate_controllable_single_company(
            reid="REL00001",
            eff_req_pct=0.01,  # 1% annual
            controllable_average=100000.0,  # 100k tkr annual
            neon_adjustments=0.0,
            capital_cost_total=200000.0,  # 200k tkr period
            method="OPEX",
        )
        assert result["method_used"] == "OPEX"
        assert result["controllable_cost_period"] < 400000.0  # Less than 4×100k
        assert result["efficiency_deduction_total"] > 0

    def test_totex_basic(self):
        result = _calculate_controllable_single_company(
            reid="REL00001",
            eff_req_pct=0.01,
            controllable_average=100000.0,
            neon_adjustments=0.0,
            capital_cost_total=200000.0,
            method="TOTEX",
        )
        assert result["method_used"] == "TOTEX"
        assert result["capex_efficiency_deduction"] > 0
        assert result["opex_efficiency_deduction"] > 0

    def test_zero_eff_req_no_deduction(self):
        result = _calculate_controllable_single_company(
            reid="REL00001",
            eff_req_pct=0.0,
            controllable_average=100000.0,
            neon_adjustments=0.0,
            capital_cost_total=200000.0,
            method="OPEX",
        )
        assert result["efficiency_deduction_total"] == pytest.approx(0.0, abs=0.01)

    def test_neo_adjustments_applied(self):
        without_neo = _calculate_controllable_single_company(
            reid="REL00001",
            eff_req_pct=0.01,
            controllable_average=100000.0,
            neon_adjustments=0.0,
            capital_cost_total=200000.0,
            method="OPEX",
        )
        with_neo = _calculate_controllable_single_company(
            reid="REL00001",
            eff_req_pct=0.01,
            controllable_average=100000.0,
            neon_adjustments=40000.0,  # 10k/year
            capital_cost_total=200000.0,
            method="OPEX",
        )
        # NEO adjustments increase the base → higher period cost
        assert with_neo["controllable_cost_before_period"] > without_neo["controllable_cost_before_period"]

    def test_efficiency_deduction_grows_over_years(self):
        result = _calculate_controllable_single_company(
            reid="REL00001",
            eff_req_pct=0.015,  # 1.5%
            controllable_average=100000.0,
            neon_adjustments=0.0,
            capital_cost_total=200000.0,
            method="OPEX",
        )
        # Per-year controllable should decrease over time
        years = [result[f"controllable_cost_{y}"] for y in [2024, 2025, 2026, 2027]]
        for i in range(len(years) - 1):
            assert years[i] > years[i + 1], f"Year {2024+i} should be > year {2025+i}"

    def test_totex_allocates_to_opex_and_capex(self):
        result = _calculate_controllable_single_company(
            reid="REL00001",
            eff_req_pct=0.01,
            controllable_average=100000.0,
            neon_adjustments=0.0,
            capital_cost_total=200000.0,
            method="TOTEX",
        )
        total_ded = result["efficiency_deduction_total"]
        opex_ded = result["opex_efficiency_deduction"]
        capex_ded = result["capex_efficiency_deduction"]
        assert total_ded == pytest.approx(opex_ded + capex_ded, rel=1e-6)
        assert result["opex_share"] + result["capex_share"] == pytest.approx(1.0, rel=1e-6)


class TestGetControllableFromSDF:
    def test_returns_dataframe(self, sdf_ir, sdf_controllable):
        result = get_controllable_from_sdf(sdf_ir, sdf_controllable)
        assert isinstance(result, pd.DataFrame)
        assert "REId" in result.columns
        assert "controllable_cost_average" in result.columns
        assert "neo_adjustments_period" in result.columns

    def test_company_count(self, sdf_ir, sdf_controllable):
        result = get_controllable_from_sdf(sdf_ir, sdf_controllable)
        assert len(result) > 100  # Should have most of the 148 companies


class TestControllableWithEffReq:
    def test_opex_method_integration(self, dea_baseline, sdf_baseline_ctrl, sdf_ir):
        from calculations.efficiency_requirement import calculate_eff_req_for_dataframe

        eff_req = calculate_eff_req_for_dataframe(
            dea_baseline[["REId", "potential", "is_outlier"]].copy()
        )

        # capital_cost_period is in SDF IR, not Data_modeller
        capex = sdf_ir[["REId", "capital_cost_period"]].copy()

        result = calculate_controllable_with_eff_req(
            eff_req, sdf_baseline_ctrl, capex, method="OPEX"
        )
        assert isinstance(result, pd.DataFrame)
        assert "controllable_cost_period" in result.columns
        assert len(result) > 0

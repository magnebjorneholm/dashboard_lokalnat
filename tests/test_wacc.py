"""
tests/test_wacc.py

Unit tests for WACC/CAPM calculations.
Pure math module — no data dependencies.
"""

import pytest
from calculations.capex.wacc_calculations import (
    calculate_wacc,
    calculate_wacc_simple,
    CAPMInputs,
    WACCResult,
    BASELINE_WACC,
    _hamada,
)


# Expected values from baseline CAPM inputs
EXPECTED = {
    "equity_beta": 0.5352512500000001,
    "cost_of_equity_nominal": 0.0644547835,
    "cost_of_debt_nominal": 0.0401,
    "wacc_nominal_pre_tax": 0.06638947788413098,
    "wacc_real_pre_tax": 0.045274924411028206,
}


class TestBaselineWACC:
    def test_baseline_wacc_close_to_0453(self):
        result = calculate_wacc(CAPMInputs())
        assert result.wacc_real_pre_tax == pytest.approx(BASELINE_WACC, abs=5e-4)

    def test_baseline_wacc_exact(self):
        result = calculate_wacc(CAPMInputs())
        assert result.wacc_real_pre_tax == pytest.approx(
            EXPECTED["wacc_real_pre_tax"], rel=1e-10
        )

    def test_equity_beta(self):
        result = calculate_wacc(CAPMInputs())
        assert result.equity_beta == pytest.approx(
            EXPECTED["equity_beta"], rel=1e-10
        )

    def test_cost_of_equity_nominal(self):
        result = calculate_wacc(CAPMInputs())
        assert result.cost_of_equity_nominal == pytest.approx(
            EXPECTED["cost_of_equity_nominal"], rel=1e-10
        )

    def test_cost_of_debt_nominal(self):
        result = calculate_wacc(CAPMInputs())
        assert result.cost_of_debt_nominal == pytest.approx(
            EXPECTED["cost_of_debt_nominal"], rel=1e-10
        )

    def test_wacc_nominal_pre_tax(self):
        result = calculate_wacc(CAPMInputs())
        assert result.wacc_nominal_pre_tax == pytest.approx(
            EXPECTED["wacc_nominal_pre_tax"], rel=1e-10
        )


class TestHamadaConversion:
    def test_hamada_basic(self):
        # β_E = β_A × (1 + (1 - T) × D/E)
        # With D/E ratio: debt_ratio=0.36 → D/E = 0.36/0.64
        inputs = CAPMInputs()
        d_e = inputs.debt_ratio / (1 - inputs.debt_ratio)
        expected = inputs.asset_beta * (1 + (1 - inputs.tax_rate) * d_e)
        result = _hamada(inputs.asset_beta, inputs.debt_ratio, inputs.tax_rate)
        assert result == pytest.approx(expected, rel=1e-10)

    def test_zero_debt_ratio(self):
        # No debt → equity beta = asset beta
        result = _hamada(0.37, 0.0, 0.206)
        assert result == pytest.approx(0.37, rel=1e-10)

    def test_high_debt_ratio(self):
        # Higher leverage → higher equity beta
        low_leverage = _hamada(0.37, 0.2, 0.206)
        high_leverage = _hamada(0.37, 0.6, 0.206)
        assert high_leverage > low_leverage


class TestCAPMFormula:
    def test_capm_cost_of_equity(self):
        # E[r] = Rf + β_E × MRP
        inputs = CAPMInputs()
        result = calculate_wacc(inputs)
        expected_coe = inputs.risk_free_rate + result.equity_beta * inputs.market_risk_premium
        assert result.cost_of_equity_nominal == pytest.approx(expected_coe, rel=1e-10)


class TestFisherRealConversion:
    def test_fisher_equation(self):
        # real = (1 + nominal) / (1 + inflation) - 1
        result = calculate_wacc(CAPMInputs())
        inputs = CAPMInputs()
        expected_real = (1 + result.wacc_nominal_pre_tax) / (1 + inputs.inflation) - 1
        assert result.wacc_real_pre_tax == pytest.approx(expected_real, rel=1e-10)


class TestWACCSimpleWrapper:
    def test_simple_matches_full(self):
        full = calculate_wacc(CAPMInputs())
        simple = calculate_wacc_simple()
        assert simple == pytest.approx(full.wacc_real_pre_tax, rel=1e-10)


class TestWACCSensitivity:
    def test_higher_debt_ratio_changes_wacc(self):
        baseline = calculate_wacc(CAPMInputs())
        high_debt = calculate_wacc(CAPMInputs(debt_ratio=0.5))
        # Different debt ratio should give different WACC
        assert baseline.wacc_real_pre_tax != pytest.approx(
            high_debt.wacc_real_pre_tax, abs=1e-6
        )

    def test_higher_risk_free_rate_increases_wacc(self):
        baseline = calculate_wacc(CAPMInputs())
        high_rf = calculate_wacc(CAPMInputs(risk_free_rate=0.05))
        assert high_rf.wacc_real_pre_tax > baseline.wacc_real_pre_tax

"""
tests/test_efficiency_requirement.py

Unit tests for efficiency requirement calculations.
Pure math module — no data dependencies.
"""

import pytest
import numpy as np
import pandas as pd
from calculations.efficiency_requirement import (
    calculate_eff_req_from_potential,
    calculate_eff_req_for_dataframe,
    calculate_truncation_min_from_outlier_req,
    get_max_eff_req,
    get_min_eff_req,
)


TRUNCATION_MIN_EXPECTED = 0.1624160400000001


class TestTruncationMin:
    def test_truncation_min_from_default_params(self):
        result = calculate_truncation_min_from_outlier_req()
        assert result == pytest.approx(TRUNCATION_MIN_EXPECTED, rel=1e-6)

    def test_truncation_min_positive(self):
        result = calculate_truncation_min_from_outlier_req()
        assert result > 0

    def test_truncation_min_less_than_max(self):
        result = calculate_truncation_min_from_outlier_req()
        assert result < 0.30  # default truncation_max


class TestOutlierRequirement:
    def test_outlier_gets_1pct(self):
        result = calculate_eff_req_from_potential(0.20, is_outlier=True)
        assert result == pytest.approx(0.01, rel=1e-10)

    def test_outlier_ignores_potential(self):
        # Same result regardless of potential when is_outlier=True
        r1 = calculate_eff_req_from_potential(0.05, is_outlier=True)
        r2 = calculate_eff_req_from_potential(0.50, is_outlier=True)
        assert r1 == r2


class TestEfficiencyRequirementFormula:
    def test_min_potential_gives_1pct(self):
        result = calculate_eff_req_from_potential(TRUNCATION_MIN_EXPECTED, is_outlier=False)
        assert result == pytest.approx(0.01, rel=1e-3)

    def test_zero_potential_truncated_to_min(self):
        result = calculate_eff_req_from_potential(0.0, is_outlier=False)
        # 0.0 is below truncation_min, so truncated to min → ~1%
        assert result == pytest.approx(0.01, rel=1e-3)

    def test_max_potential_gives_182pct(self):
        result = calculate_eff_req_from_potential(0.30, is_outlier=False)
        assert result == pytest.approx(0.018244601098569957, rel=1e-6)

    def test_potential_above_max_truncated(self):
        # potential=0.50 should be truncated to 0.30
        r_max = calculate_eff_req_from_potential(0.30, is_outlier=False)
        r_above = calculate_eff_req_from_potential(0.50, is_outlier=False)
        assert r_above == pytest.approx(r_max, rel=1e-10)

    def test_potential_0_2(self):
        result = calculate_eff_req_from_potential(0.20, is_outlier=False)
        assert result == pytest.approx(0.012272234429039353, rel=1e-6)

    def test_monotonically_increasing(self):
        # Higher potential → higher efficiency requirement (within truncation range)
        r_low = calculate_eff_req_from_potential(0.18, is_outlier=False)
        r_mid = calculate_eff_req_from_potential(0.22, is_outlier=False)
        r_high = calculate_eff_req_from_potential(0.28, is_outlier=False)
        assert r_low < r_mid < r_high


class TestMinMaxHelpers:
    def test_min_eff_req(self):
        result = get_min_eff_req()
        assert result == pytest.approx(0.01, rel=1e-3)

    def test_max_eff_req(self):
        result = get_max_eff_req()
        assert result == pytest.approx(0.018244601098569957, rel=1e-6)

    def test_min_less_than_max(self):
        assert get_min_eff_req() < get_max_eff_req()


class TestDataFrameVersion:
    def test_matches_scalar_version(self):
        df = pd.DataFrame({
            "REId": ["REL00001", "REL00002", "REL00003"],
            "potential": [0.20, 0.30, 0.10],
            "is_outlier": [False, False, True],
        })
        result = calculate_eff_req_for_dataframe(df)

        for _, row in result.iterrows():
            scalar = calculate_eff_req_from_potential(
                row["potential"], row["is_outlier"]
            )
            assert row["efficiency_requirement_annual"] == pytest.approx(
                scalar, rel=1e-10
            )

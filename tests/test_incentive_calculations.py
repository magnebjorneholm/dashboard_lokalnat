"""
tests/test_incentive_calculations.py

Tests for incentive calculations (quality, network loss, load).
"""

import pytest
import numpy as np
import pandas as pd
from calculations.incentive.incentive_calculations import (
    calculate_all_incentives,
    calculate_interruption_incentives,
    calculate_netloss_incentive,
    calculate_utilization_incentive,
    apply_caps,
    aggregate_period_totals,
)
from config.incentive_parameters import (
    KPI, K_NF, ADJ_MAX_AGG, ADJ_MAX_CEMI4, SHARING_NETLOSS,
    AIT_COSTS, AIF_COSTS, MISSING_DATA_IDS,
)


def _make_incentive_df():
    """Create minimal incentive DataFrame for a single company, 4 years.

    Column format expected by the functions:
    - ait_{ann}_{sni}_{norm/obs} e.g. ait_a_1_norm
    - aif_{ann}_{sni}_{norm/obs} e.g. aif_o_3_obs
    - ame_{sni} e.g. ame_1
    """
    rows = []
    for year in [2024, 2025, 2026, 2027]:
        row = {
            "reid": "REL00886",
            "year": year,
            "ret_period": 100000.0,
            # Network loss
            "nf_norm": 0.05, "nf_obs": 0.04,
            "e_in": 500000.0,
            # Utilization
            "ug_obs": 0.55, "ug_norm": 0.50,
            "k_upstream": 10000.0,
        }
        # Quality: AIT/AIF per ann (a,o) per sni (1-6)
        for sni in range(1, 7):
            row[f"ame_{sni}"] = 100.0
            for ann in ["a", "o"]:
                row[f"ait_{ann}_{sni}_norm"] = 0.6
                row[f"ait_{ann}_{sni}_obs"] = 0.5
                row[f"aif_{ann}_{sni}_norm"] = 12.0
                row[f"aif_{ann}_{sni}_obs"] = 10.0
        rows.append(row)
    return pd.DataFrame(rows)


class TestQualityIncentive:
    def test_positive_when_norm_gt_obs(self):
        """norm > obs -> positive quality incentive (better than norm)."""
        df = _make_incentive_df()
        result = calculate_interruption_incentives(df, kpi=KPI, ait_costs=AIT_COSTS, aif_costs=AIF_COSTS)
        # inc_inter is the sum of all sub-incentives
        assert "inc_inter" in result.columns
        # norm > obs means company is better -> positive incentive
        assert (result["inc_inter"] >= 0).all()


class TestNetlossIncentive:
    def test_positive_when_norm_gt_obs(self):
        """nf_norm > nf_obs -> positive (lower losses than norm)."""
        df = _make_incentive_df()
        result = calculate_netloss_incentive(df, k_nf=K_NF, sharing_netloss=SHARING_NETLOSS)
        # Output column is loss_incentive_a (before capping)
        assert (result["loss_incentive_a"] > 0).all()

    def test_formula(self):
        """Verify: loss_incentive_a = sharing * (nf_norm - nf_obs) * k_nf * e_in."""
        df = _make_incentive_df()
        result = calculate_netloss_incentive(df, k_nf=K_NF, sharing_netloss=SHARING_NETLOSS)
        row = result[result["year"] == 2024].iloc[0]
        expected = SHARING_NETLOSS * (0.05 - 0.04) * K_NF[2024] * 500000.0
        assert row["loss_incentive_a"] == pytest.approx(expected, rel=1e-4)


class TestUtilizationIncentive:
    def test_positive_when_obs_gt_norm(self):
        """ug_obs > ug_norm -> positive utilization incentive."""
        df = _make_incentive_df()
        result = calculate_utilization_incentive(df)
        # Output column is util_incentive_a (before capping)
        assert (result["util_incentive_a"] > 0).all()

    def test_formula(self):
        """Verify: util_incentive_a = (ug_obs - ug_norm) * k_upstream."""
        df = _make_incentive_df()
        result = calculate_utilization_incentive(df)
        row = result.iloc[0]
        expected = (0.55 - 0.50) * 10000.0
        assert row["util_incentive_a"] == pytest.approx(expected, rel=1e-10)


class TestIncentiveCapping:
    def test_cap_at_one_third_return(self):
        """Incentives should be capped at +/-(adj_max_agg * ret_period)."""
        df = _make_incentive_df()
        # Set pre-cap (_a suffix) columns with extreme values
        df["inter_incentive_a"] = 50000.0  # Exceeds 1/3 * 100000
        df["loss_incentive_a"] = 50000.0
        df["util_incentive_a"] = 50000.0
        result = apply_caps(df, "ret_period", adj_max_agg=ADJ_MAX_AGG)
        max_val = ADJ_MAX_AGG * 100000.0  # ~33333
        for _, row in result.iterrows():
            assert abs(row["incentive_total_year"]) <= max_val + 1


class TestAggregation:
    def test_period_totals(self):
        df = _make_incentive_df()
        df["inter_incentive"] = 1000.0
        df["loss_incentive"] = 2000.0
        df["util_incentive"] = 500.0
        df["incentive_total_year"] = 3500.0
        result = aggregate_period_totals(df)
        # aggregate_period_totals merges sums back to all rows (4 rows remain)
        assert len(result) == 4
        # But each row should have the same period sum
        assert result.iloc[0]["inter_incentive_sum"] == pytest.approx(4000.0)  # 4 * 1000
        assert result.iloc[0]["loss_incentive_sum"] == pytest.approx(8000.0)   # 4 * 2000
        assert result.iloc[0]["util_incentive_sum"] == pytest.approx(2000.0)   # 4 * 500
        assert result.iloc[0]["incentive_total"] == pytest.approx(14000.0)     # 4 * 3500


class TestMissingDataHandling:
    def test_missing_data_ids_constant_exists(self):
        assert isinstance(MISSING_DATA_IDS, list)
        assert len(MISSING_DATA_IDS) > 0

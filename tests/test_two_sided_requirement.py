"""
tests/test_two_sided_requirement.py

Unit tests for the new-benchmarking two-sided efficiency mechanic
(new_benchmarking_model/efficiency/efficiency_requirement_two_sided.py).

Pure math / cross-sectional — no data dependencies. The legacy front-reference method
(calculations/efficiency/efficiency_requirement.py) is intentionally untouched and keeps
its own suite (test_efficiency_requirement.py); one test here cross-checks that the
deduction cap reproduces the legacy maximum so the two stay numerically consistent.
"""

import numpy as np
import pandas as pd
import pytest

from config.column_names import (
    COL_DEA_EFFICIENCY,
    COL_IS_OUTLIER,
    COL_EFF_REQ_ANNUAL,
    COL_DEA_REFERENCE,
)
from new_benchmarking_model.efficiency.efficiency_requirement_two_sided import (
    reference_efficiency,
    two_sided_requirement_from_gap,
    calculate_two_sided_requirement,
)
from calculations.efficiency.efficiency_requirement import calculate_eff_req_from_potential


# 75th percentile of [0.5, 0.6, 0.7, 0.8, 0.9] (numpy linear interp) = 0.80 exactly.
_THRESHOLD_EFFS = [0.5, 0.6, 0.7, 0.8, 0.9]
_E75 = 0.80


def _frame(effs, outliers=None):
    n = len(effs)
    outliers = [False] * n if outliers is None else outliers
    return pd.DataFrame({
        "REId": [f"REL{i:05d}" for i in range(n)],
        COL_DEA_EFFICIENCY: effs,
        COL_IS_OUTLIER: outliers,
    })


class TestReferenceEfficiency:
    def test_third_quartile_excludes_outliers(self):
        # The outlier at 2.0 would pull the percentile up if it were included.
        eff = _THRESHOLD_EFFS + [2.0]
        outl = [False] * 5 + [True]
        e75 = reference_efficiency(pd.Series(eff), pd.Series(outl))
        assert e75 == pytest.approx(_E75, rel=1e-9)

    def test_all_outliers_returns_nan(self):
        e75 = reference_efficiency(pd.Series([1.0, 1.0]), pd.Series([True, True]))
        assert np.isnan(e75)

    def test_ignores_nan_scores(self):
        e75 = reference_efficiency(
            pd.Series(_THRESHOLD_EFFS + [np.nan]),
            pd.Series([False] * 6),
        )
        assert e75 == pytest.approx(_E75, rel=1e-9)


class TestScalarFromGap:
    def test_zero_gap_gives_zero(self):
        assert two_sided_requirement_from_gap(0.0) == pytest.approx(0.0, abs=1e-12)

    def test_positive_gap_is_deduction(self):
        assert two_sided_requirement_from_gap(0.10) > 0

    def test_negative_gap_is_reward(self):
        assert two_sided_requirement_from_gap(-0.10) < 0

    def test_deduction_cap_matches_legacy_max(self):
        # gap_cap 0.30 must reproduce the legacy front-model maximum (1.82 %/yr) exactly,
        # so the two mechanics share the same deduction ceiling.
        capped = two_sided_requirement_from_gap(0.30)
        legacy_max = calculate_eff_req_from_potential(0.30, is_outlier=False)
        assert capped == pytest.approx(legacy_max, rel=1e-12)
        assert capped == pytest.approx(0.018244601098569957, rel=1e-9)

    def test_deduction_gap_above_cap_is_clipped(self):
        assert two_sided_requirement_from_gap(0.50) == pytest.approx(
            two_sided_requirement_from_gap(0.30), rel=1e-12
        )

    def test_reward_gap_below_cap_is_clipped(self):
        assert two_sided_requirement_from_gap(-0.50) == pytest.approx(
            two_sided_requirement_from_gap(-0.30), rel=1e-12
        )

    def test_cap_is_two_sided(self):
        assert two_sided_requirement_from_gap(0.30) > 0
        assert two_sided_requirement_from_gap(-0.30) < 0

    def test_nan_in_nan_out(self):
        assert np.isnan(two_sided_requirement_from_gap(np.nan))


class TestDataFrame:
    def test_firm_at_threshold_gets_zero(self):
        out = calculate_two_sided_requirement(_frame(_THRESHOLD_EFFS))
        at = out[out[COL_DEA_EFFICIENCY] == _E75].iloc[0]
        assert at[COL_EFF_REQ_ANNUAL] == pytest.approx(0.0, abs=1e-12)

    def test_below_threshold_deduction_above_reward(self):
        out = calculate_two_sided_requirement(_frame(_THRESHOLD_EFFS)).set_index(COL_DEA_EFFICIENCY)
        assert out.loc[0.5, COL_EFF_REQ_ANNUAL] > 0   # least efficient → deduction
        assert out.loc[0.9, COL_EFF_REQ_ANNUAL] < 0   # most efficient → reward

    def test_reference_column_is_constant_e75(self):
        out = calculate_two_sided_requirement(_frame(_THRESHOLD_EFFS))
        assert out[COL_DEA_REFERENCE].nunique() == 1
        assert out[COL_DEA_REFERENCE].iloc[0] == pytest.approx(_E75, rel=1e-9)

    def test_outlier_excluded_from_threshold_but_scored(self):
        # The outlier (capped to 1.0) must not move E75, yet still receive a reward.
        out = calculate_two_sided_requirement(
            _frame(_THRESHOLD_EFFS + [1.0], outliers=[False] * 5 + [True])
        )
        assert out[COL_DEA_REFERENCE].iloc[0] == pytest.approx(_E75, rel=1e-9)
        outlier_row = out.iloc[5]
        assert not np.isnan(outlier_row[COL_EFF_REQ_ANNUAL])
        assert outlier_row[COL_EFF_REQ_ANNUAL] < 0    # above the threshold → reward

    def test_monotonic_in_efficiency(self):
        out = calculate_two_sided_requirement(_frame([0.5, 0.65, 0.8, 0.95]))
        out = out.sort_values(COL_DEA_EFFICIENCY)
        reqs = out[COL_EFF_REQ_ANNUAL].to_numpy()
        assert np.all(np.diff(reqs) < 0)              # higher efficiency → lower requirement

    def test_nan_efficiency_propagates(self):
        out = calculate_two_sided_requirement(_frame(_THRESHOLD_EFFS[:-1] + [np.nan]))
        assert np.isnan(out.iloc[4][COL_EFF_REQ_ANNUAL])

    def test_missing_efficiency_column_raises(self):
        with pytest.raises(ValueError):
            calculate_two_sided_requirement(pd.DataFrame({COL_IS_OUTLIER: [False]}))

    def test_missing_outlier_column_raises(self):
        with pytest.raises(ValueError):
            calculate_two_sided_requirement(pd.DataFrame({COL_DEA_EFFICIENCY: [0.5]}))

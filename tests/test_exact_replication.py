"""
tests/test_exact_replication.py

Guards the end-to-end replication of Ei's published facit when the WHOLE chain
is computed from scratch (no lifting of precomputed values), via
get_exact_replication_config:
  - capital cost via KENT 5-8 for all 148 (PARAMETER_CHANGE, baseline WACC)
  - DEA on the RAW Data_modeller OPEXp, outlier fence iterated to convergence

Reproduces Ei's effektivitet to solver tolerance, and the SDF capital cost to
rounding, for every firm except the two documented data anomalies:
  - REL00193 (DEA: facit lower than any reference set can produce)
  - REL00584 (capital cost: KENT-from-capbase vs SDF-published, ~0.15%)

See eis_dea_metod.md.
"""

import pytest
import pandas as pd
import numpy as np

from config.column_names import (
    COL_DEA_EFFICIENCY, COL_IS_OUTLIER, COL_OPEXP_RAW,
    COL_CAPITAL_COST_PERIOD,
)

DEA_ANOMALY = "REL00193"
CAPEX_ANOMALY = "REL00584"


@pytest.fixture(scope="session")
def exact_replication_result(baseline_data):
    """Run the full-recompute exact-replication pipeline once (148 companies)."""
    from config.case_definition import get_exact_replication_config
    from pipeline.core import run_pipeline
    config = get_exact_replication_config("REL00001")
    return run_pipeline(baseline_data, config, debug=False, validate=True)


class TestRawOpexpColumn:
    """The raw OPEXp input column must survive into the baseline frame."""

    def test_opexp_raw_present(self, baseline_data):
        df = baseline_data.df_all_companies
        assert COL_OPEXP_RAW in df.columns
        assert df[COL_OPEXP_RAW].notna().sum() >= 140

    def test_opexp_raw_differs_from_sdf_derived(self, baseline_data):
        """Raw OPEXp and SDF-derived controllable diverge for a meaningful subset."""
        df = baseline_data.df_all_companies
        raw = pd.to_numeric(df[COL_OPEXP_RAW], errors="coerce")
        sdf = pd.to_numeric(df["controllable_cost_average"], errors="coerce")
        rel = (raw - sdf).abs() / sdf.abs().clip(lower=1.0)
        # eis_dea_metod.md: the two coincide for only 92/148 firms.
        assert (rel > 1e-6).sum() >= 40


class TestDeaExactReplication:
    """Genuine DEA (PuLP) on raw OPEXp + iterated fence must match Ei facit."""

    def test_pipeline_actually_ran_dea(self, exact_replication_result):
        assert exact_replication_result.dea.dea_executed is True
        assert exact_replication_result.dea.dea_method == "dea"

    def test_outlier_set_matches_ei(self, exact_replication_result, dea_baseline):
        n_calc = int(exact_replication_result.dea.dea_results[COL_IS_OUTLIER].sum())
        n_facit = int(dea_baseline[COL_IS_OUTLIER].sum())
        assert n_calc == n_facit, f"outliers: calc={n_calc}, facit={n_facit}"

    def test_efficiency_matches_facit_except_known_anomaly(
        self, exact_replication_result, dea_baseline
    ):
        calc = exact_replication_result.dea.dea_results.set_index("REId")
        facit = dea_baseline.set_index("REId")
        common = calc.index.intersection(facit.index)

        e_c = pd.to_numeric(calc.loc[common, COL_DEA_EFFICIENCY], errors="coerce")
        e_f = pd.to_numeric(facit.loc[common, COL_DEA_EFFICIENCY], errors="coerce")
        both = (~e_c.isna()) & (~e_f.isna())
        diff = (e_c[both] - e_f[both]).abs()

        # Only the documented anomaly may exceed solver tolerance.
        offenders = diff[diff > 1e-6].index.tolist()
        assert offenders == [DEA_ANOMALY], f"unexpected DEA mismatches: {offenders}"
        assert diff.drop(index=DEA_ANOMALY, errors="ignore").max() < 1e-6


class TestCapitalCostExactReplication:
    """KENT-recomputed capital cost must match SDF facit except the known anomaly."""

    def test_capital_cost_matches_sdf_except_known_anomaly(
        self, exact_replication_result, sdf_ir
    ):
        arf = exact_replication_result.post_dea.all_revenue_frames.set_index("REId")
        facit = sdf_ir[sdf_ir["REId"].str.startswith("REL")].set_index("REId")
        common = arf.index.intersection(facit.index)

        calc = pd.to_numeric(arf.loc[common, COL_CAPITAL_COST_PERIOD], errors="coerce")
        fac = pd.to_numeric(facit.loc[common, COL_CAPITAL_COST_PERIOD], errors="coerce")
        rel = (calc - fac).abs() / fac.abs().clip(lower=1.0)

        # All but the documented anomaly within 0.1%.
        offenders = rel[rel > 1e-3].index.tolist()
        assert offenders == [CAPEX_ANOMALY], f"unexpected capex mismatches: {offenders}"
        # And even the anomaly stays small (~0.15%).
        assert rel[CAPEX_ANOMALY] < 2e-3

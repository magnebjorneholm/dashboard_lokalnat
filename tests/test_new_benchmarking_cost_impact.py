"""
tests/test_new_benchmarking_cost_impact.py

Guards the kr quantification of the efficiency requirement for the new benchmarking
add-on (new_benchmarking_model/efficiency/cost_impact.py).

The central guarantee: period_efficiency_amount() reproduces the revenue-cap pipeline's
period efficiency_total exactly, so the current-model kr (OPEX base) matches the pipeline
"helt och hållet" and the new-model kr reuses the same compounding mechanic on its broader
TOTEX base.
"""

import numpy as np
import pandas as pd

from config.column_names import (
    COL_REID, COL_CONTROLLABLE_AVG, COL_NEO_ADJUSTMENTS, COL_EFF_REQ_ANNUAL,
    COL_EFFICIENCY_DEDUCTION, COL_OPEX_BASE_CURRENT, COL_APPLICATION_BASE_NEW,
    COL_KR_CURRENT, COL_KR_NEW,
)
from new_benchmarking_model.efficiency.cost_impact import (
    period_efficiency_amount, build_cost_impact, SUPERVISION_YEARS,
)
from calculations.opex.controllable_cost_calculations import calculate_controllable_with_eff_req


class TestPeriodMechanic:
    """period_efficiency_amount must equal the pipeline's OPEX efficiency_total."""

    def test_matches_pipeline_opex(self):
        eff = pd.DataFrame({
            COL_REID: ["A", "B", "C", "D"],
            COL_EFF_REQ_ANNUAL: [0.0182, 0.005, -0.004, 0.0],
        })
        base = pd.DataFrame({
            COL_REID: ["A", "B", "C", "D"],
            COL_CONTROLLABLE_AVG: [60000.0, 12000.0, 30000.0, 5000.0],
            COL_NEO_ADJUSTMENTS: [800.0, 0.0, -400.0, 250.0],
        })
        capex = pd.DataFrame({COL_REID: ["A", "B", "C", "D"]})  # OPEX: capex unused

        legacy = calculate_controllable_with_eff_req(eff, base, capex, method="OPEX")
        legacy = legacy.set_index(COL_REID)[COL_EFFICIENCY_DEDUCTION]

        for _, r in eff.merge(base, on=COL_REID).iterrows():
            annual = r[COL_CONTROLLABLE_AVG] + r[COL_NEO_ADJUSTMENTS] / SUPERVISION_YEARS
            ours = period_efficiency_amount(r[COL_EFF_REQ_ANNUAL], annual)
            assert abs(ours - legacy[r[COL_REID]]) < 1e-6

    def test_reward_is_negative(self):
        assert period_efficiency_amount(-0.01, 50000.0) < 0  # reward → addition

    def test_zero_req_is_zero(self):
        assert period_efficiency_amount(0.0, 50000.0) == 0.0

    def test_nan_propagates(self):
        assert np.isnan(period_efficiency_amount(float("nan"), 1000.0))
        assert np.isnan(period_efficiency_amount(0.01, float("nan")))


class TestBuildCostImpact:
    """build_cost_impact wires bases and kr together on the full company set."""

    def test_columns_and_signs(self, baseline_data):
        from new_benchmarking_model import run_new_benchmarking, NewBenchmarkingConfig
        result = run_new_benchmarking(NewBenchmarkingConfig(), baseline_data=baseline_data)
        tx = result.totex

        for col in (COL_OPEX_BASE_CURRENT, COL_APPLICATION_BASE_NEW, COL_KR_CURRENT, COL_KR_NEW):
            assert col in tx.columns, f"{col} missing from totex frame"

        # The new base adds cost posts, so it never falls below the OPEX base.
        assert (tx[COL_APPLICATION_BASE_NEW] >= tx[COL_OPEX_BASE_CURRENT] - 1e-6).all()
        # Current model only ever deducts; the new model is two-sided.
        assert (tx[COL_KR_CURRENT] >= -1e-6).all()
        assert (tx[COL_KR_NEW] < 0).any() and (tx[COL_KR_NEW] > 0).any()

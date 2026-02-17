"""
tests/test_cost_aggregation.py

Tests for cost_aggregation.py — verifies aggregation logic against SDF facit values.
"""

import pytest
import pandas as pd
import numpy as np

from calculations.opex.cost_aggregation import aggregate_controllable, aggregate_non_controllable
from config.column_names import (
    COL_CONTROLLABLE_AVG, COL_NEO_ADJUSTMENTS,
    COL_NON_CONTROLLABLE,
    COL_NON_CONTROLLABLE_2024, COL_NON_CONTROLLABLE_2025,
    COL_NON_CONTROLLABLE_2026, COL_NON_CONTROLLABLE_2027,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def ctrl_detail():
    return pd.read_parquet("data/controllable_a.parquet")


@pytest.fixture(scope="session")
def ctrl_meta():
    return pd.read_parquet("data/controllable_meta.parquet")


@pytest.fixture(scope="session")
def nonctrl_detail():
    return pd.read_parquet("data/non_controllable_a.parquet")


@pytest.fixture(scope="session")
def ctrl_aggregated(ctrl_detail, ctrl_meta):
    return aggregate_controllable(ctrl_detail, ctrl_meta)


@pytest.fixture(scope="session")
def nonctrl_aggregated(nonctrl_detail):
    return aggregate_non_controllable(nonctrl_detail)


@pytest.fixture(scope="session")
def sdf_ir():
    """Load SDF IR sheet for cross-verification."""
    from pathlib import Path
    sdf_file = Path("data/Löpande kostnader från SDF 2024-27.xlsx")
    df = pd.read_excel(sdf_file, sheet_name="IR 2024-2027", engine="openpyxl")
    reid_col = "REid" if "REid" in df.columns else "REId"
    df = df.rename(columns={reid_col: "REId"})
    df = df[df["REId"].astype(str).str.startswith("REL")]
    return df


@pytest.fixture(scope="session")
def sdf_controllable_sheet():
    """Load SDF Påverkbara sheet for Medelvärde verification."""
    from pathlib import Path
    sdf_file = Path("data/Löpande kostnader från SDF 2024-27.xlsx")
    df_raw = pd.read_excel(sdf_file, sheet_name="Påverkbara", engine="openpyxl", header=None)
    data = df_raw.iloc[2:].copy().reset_index(drop=True)
    data = data[data.iloc[:, 1] == "L"].reset_index(drop=True)
    data = data[data.iloc[:, 0].astype(str).str.startswith("REL")]
    return pd.DataFrame({
        "REId": data.iloc[:, 0].values,
        "medelvarde": pd.to_numeric(data.iloc[:, 123], errors="coerce").values,
        "neo_unsep": pd.to_numeric(data.iloc[:, 124], errors="coerce").fillna(0).values,
    })


# ---------------------------------------------------------------------------
# Controllable tests
# ---------------------------------------------------------------------------

class TestControllableMatchesSdfMedelvarde:
    """Aggregated controllable_cost_average must match SDF Medelvärde for all 148 companies."""

    def test_all_companies_match(self, ctrl_aggregated, sdf_controllable_sheet):
        merged = ctrl_aggregated.merge(sdf_controllable_sheet, on="REId")
        merged["diff"] = abs(merged[COL_CONTROLLABLE_AVG] - merged["medelvarde"])
        max_diff = merged["diff"].max()
        n_pass = (merged["diff"] <= 1.0).sum()
        assert n_pass == len(merged), (
            f"Only {n_pass}/{len(merged)} companies match. Max diff = {max_diff:.4f} tkr"
        )

    def test_148_companies(self, ctrl_aggregated):
        assert len(ctrl_aggregated) == 148

    @pytest.mark.parametrize("reid", ["REL00001", "REL00886", "REL03035"])
    def test_specific_company(self, ctrl_aggregated, sdf_controllable_sheet, reid):
        actual = ctrl_aggregated[ctrl_aggregated["REId"] == reid][COL_CONTROLLABLE_AVG].iloc[0]
        expected = sdf_controllable_sheet[sdf_controllable_sheet["REId"] == reid]["medelvarde"].iloc[0]
        assert abs(actual - expected) < 1.0, f"{reid}: {actual:.2f} vs {expected:.2f}"

    @pytest.mark.parametrize("reid", ["REL00001", "REL00886", "REL03035"])
    def test_neo_adjustments(self, ctrl_aggregated, sdf_controllable_sheet, reid):
        actual = ctrl_aggregated[ctrl_aggregated["REId"] == reid][COL_NEO_ADJUSTMENTS].iloc[0]
        expected = sdf_controllable_sheet[sdf_controllable_sheet["REId"] == reid]["neo_unsep"].iloc[0]
        assert abs(actual - expected) < 1.0, f"{reid}: neo={actual:.0f} vs {expected:.0f}"


class TestNonControllableMatchesSdfIr:
    """Aggregated non-controllable period total must match SDF IR for all companies."""

    def test_all_companies_match(self, nonctrl_aggregated, sdf_ir):
        nonctrl_col = None
        for col in sdf_ir.columns:
            if "opåverkbara" in col.lower() or "opaverkbara" in col.lower():
                nonctrl_col = col
                break
        assert nonctrl_col is not None, "Could not find non-controllable column in IR sheet"

        merged = nonctrl_aggregated.merge(
            sdf_ir[["REId", nonctrl_col]].rename(columns={nonctrl_col: "ir_value"}),
            on="REId",
        )
        merged["ir_value"] = pd.to_numeric(merged["ir_value"], errors="coerce")
        merged["diff"] = abs(merged[COL_NON_CONTROLLABLE] - merged["ir_value"])
        max_diff = merged["diff"].max()
        n_pass = (merged["diff"] <= 1.0).sum()
        assert n_pass == len(merged), (
            f"Only {n_pass}/{len(merged)} companies match. Max diff = {max_diff:.2f} tkr"
        )

    def test_148_companies(self, nonctrl_aggregated):
        assert len(nonctrl_aggregated) == 148

    def test_has_per_year_columns(self, nonctrl_aggregated):
        for col in [COL_NON_CONTROLLABLE_2024, COL_NON_CONTROLLABLE_2025,
                     COL_NON_CONTROLLABLE_2026, COL_NON_CONTROLLABLE_2027]:
            assert col in nonctrl_aggregated.columns

    def test_period_equals_year_sum(self, nonctrl_aggregated):
        year_sum = (
            nonctrl_aggregated[COL_NON_CONTROLLABLE_2024]
            + nonctrl_aggregated[COL_NON_CONTROLLABLE_2025]
            + nonctrl_aggregated[COL_NON_CONTROLLABLE_2026]
            + nonctrl_aggregated[COL_NON_CONTROLLABLE_2027]
        )
        diff = abs(nonctrl_aggregated[COL_NON_CONTROLLABLE] - year_sum)
        assert diff.max() < 0.01


class TestSdfDerivedVsOpexp:
    """
    Document the relationship between SDF-derived controllable and DM OPEXp.
    94/115 companies without NeoÄndringar should match. 21 differ.
    """

    def test_match_count(self, ctrl_aggregated, ctrl_meta):
        """At least 90 companies without Neo should match OPEXp."""
        from data_loaders.baseline_data import load_baseline_data
        baseline = load_baseline_data()
        dm = baseline.df_all_companies[["REId", COL_CONTROLLABLE_AVG]].copy()
        dm.columns = ["REId", "opexp_dm"]

        # Only companies without unseparated Neo
        no_neo = ctrl_meta[ctrl_meta["neo_adjustment"].abs() < 0.01]["REId"]
        merged = ctrl_aggregated[ctrl_aggregated["REId"].isin(no_neo)].merge(dm, on="REId")
        merged["diff"] = abs(merged[COL_CONTROLLABLE_AVG] - merged["opexp_dm"])
        n_match = (merged["diff"] <= 1.0).sum()
        n_total = len(merged)
        # At least 90 should match (plan says 94/115)
        assert n_match >= 90, f"Only {n_match}/{n_total} match OPEXp (expected >= 90)"

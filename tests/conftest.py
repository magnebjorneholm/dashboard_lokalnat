"""
tests/conftest.py

Shared fixtures for the Regumetrica test suite.
Session-scoped fixtures are loaded once and reused across all tests.
"""

import sys
import os
import pytest
import pandas as pd

# Ensure project root is on path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TEST_COMPANIES = {
    1:    {"REId": "REL00001", "name": "Ale El"},
    886:  {"REId": "REL00886", "name": "Kraftringen"},
    3035: {"REId": "REL03035", "name": "Stort bolag"},
}

from calculations.wacc_calculations import BASELINE_WACC as WACC_BASELINE
TOLERANCE_REL = 1e-3  # 0.1% relative tolerance


# ---------------------------------------------------------------------------
# Session-scoped fixtures (loaded once)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def baseline_data():
    """Load full baseline data (148 companies). Expensive — loaded once."""
    from data_loaders.baseline_data import load_baseline_data
    return load_baseline_data()


@pytest.fixture(scope="session")
def capbase_mini():
    """Load capbase_a_mini.parquet (3 test companies)."""
    return pd.read_parquet(os.path.join(PROJECT_ROOT, "data", "capbase_a_mini.parquet"))


@pytest.fixture(scope="session")
def capcost_a():
    """Load capcost_a.parquet (pre-aggregated capital costs by category)."""
    return pd.read_parquet(os.path.join(PROJECT_ROOT, "data", "capcost_a.parquet"))


@pytest.fixture(scope="session")
def dm(baseline_data):
    """Data_modeller DataFrame (148 companies)."""
    return baseline_data.df_all_companies


@pytest.fixture(scope="session")
def dea_baseline(baseline_data):
    """EIs DEA baseline results (148 companies)."""
    return baseline_data.dea_results


@pytest.fixture(scope="session")
def sdf_ir(baseline_data):
    """SDF IR sheet data."""
    return baseline_data.sdf_ir


@pytest.fixture(scope="session")
def sdf_controllable(baseline_data):
    """SDF Controllable sheet data."""
    return baseline_data.sdf_controllable


@pytest.fixture(scope="session")
def kent_results_mini(capbase_mini):
    """Run KENT calculations on mini capbase (3 companies). Cached per session."""
    from calculations.kent_calculations import run_kent_calculations_batch
    df_detailed, df_network, df_category = run_kent_calculations_batch(
        capbase_mini, wacc=WACC_BASELINE
    )
    return df_detailed, df_network, df_category


@pytest.fixture(scope="session")
def sdf_baseline_ctrl(baseline_data):
    """Controllable cost baseline from SDF sheets."""
    from calculations.controllable_cost_calculations import get_controllable_from_sdf
    return get_controllable_from_sdf(baseline_data.sdf_ir, baseline_data.sdf_controllable)


@pytest.fixture(scope="session")
def pipeline_result_886(baseline_data):
    """Full pipeline result for REL00886 with baseline config."""
    from config.case_definition import get_baseline_config
    from pipeline.core import run_pipeline
    config = get_baseline_config("REL00886")
    return run_pipeline(baseline_data, config, debug=False, validate=True)


# ---------------------------------------------------------------------------
# Function-scoped fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def baseline_config():
    """Baseline CaseDefinition for REL00886."""
    from config.case_definition import get_baseline_config
    return get_baseline_config("REL00886")

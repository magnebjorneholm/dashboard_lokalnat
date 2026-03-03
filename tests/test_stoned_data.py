"""
tests/test_stoned_data.py

Tests for pre-computed StoNED data loading and pipeline integration.
"""

import pytest
import pandas as pd

from config.case_definition import DeaConfig, EfficiencyMethod
from config.column_names import (
    COL_REID, COL_DEA_EFFICIENCY, COL_DEA_SUPER_EFF,
    COL_DEA_POTENTIAL, COL_IS_OUTLIER,
)
from data_loaders.stoned_data import (
    load_stoned_model_registry,
    load_stoned_results,
    get_available_stoned_models,
    get_stoned_model_info,
)

# Known outliers excluded ex ante in StoNED computation
EXPECTED_OUTLIERS = {"REL00024", "REL00257", "REL00965"}


def _has_stoned_models():
    """Check if any pre-computed StoNED models are available."""
    return len(get_available_stoned_models()) > 0


# =========================================================================
# Config / adapter tests (always run)
# =========================================================================

class TestStoNEDConfig:
    """Test that StoNED config types work correctly."""

    def test_stoned_enum_exists(self):
        assert EfficiencyMethod.STONED == "stoned"

    def test_dea_config_with_stoned(self):
        cfg = DeaConfig(method=EfficiencyMethod.STONED, stoned_model_id="stoned_01")
        assert cfg.method == EfficiencyMethod.STONED
        assert cfg.stoned_model_id == "stoned_01"

    def test_dea_config_default_no_stoned_id(self):
        cfg = DeaConfig()
        assert cfg.stoned_model_id is None

    def test_build_dea_config_stoned(self):
        from config.config_adapter import build_dea_config

        ui_config = {
            "addon_benchmarking": {
                "dea_method": "stoned",
                "stoned_model_id": "stoned_03",
            }
        }
        cfg = build_dea_config(ui_config)
        assert cfg.method == EfficiencyMethod.STONED
        assert cfg.stoned_model_id == "stoned_03"


class TestStoNEDRegistry:
    """Test the model registry loader (works even with empty registry)."""

    def test_registry_returns_dict(self):
        registry = load_stoned_model_registry()
        assert isinstance(registry, dict)

    def test_available_models_returns_list(self):
        models = get_available_stoned_models()
        assert isinstance(models, list)

    def test_invalid_model_id_raises(self):
        with pytest.raises(KeyError):
            get_stoned_model_info("nonexistent_model_xyz")


# =========================================================================
# Data validation tests (skip if no models available yet)
# =========================================================================

@pytest.mark.skipif(not _has_stoned_models(), reason="No StoNED models computed yet")
class TestStoNEDData:
    """Validate pre-computed StoNED parquet files."""

    def test_registry_has_required_fields(self):
        registry = load_stoned_model_registry()
        required = {"model_id", "label", "cost_variable", "output_variables",
                     "rts", "sigma_u", "sigma_v", "n_firms"}
        for mid, info in registry.items():
            missing = required - set(info.keys())
            assert not missing, f"Model {mid} missing fields: {missing}"

    def test_each_model_has_148_rows(self):
        for mid in get_available_stoned_models():
            df = load_stoned_results(mid)
            assert len(df) == 148, f"{mid}: expected 148 rows, got {len(df)}"

    def test_each_model_has_required_columns(self):
        expected_cols = {COL_REID, COL_DEA_EFFICIENCY, COL_DEA_SUPER_EFF,
                         COL_DEA_POTENTIAL, COL_IS_OUTLIER}
        for mid in get_available_stoned_models():
            df = load_stoned_results(mid)
            missing = expected_cols - set(df.columns)
            assert not missing, f"{mid} missing columns: {missing}"

    def test_outliers_flagged_correctly(self):
        for mid in get_available_stoned_models():
            df = load_stoned_results(mid)
            for reid in EXPECTED_OUTLIERS:
                row = df[df[COL_REID] == reid]
                assert len(row) == 1, f"{mid}: {reid} not found"
                assert row.iloc[0][COL_IS_OUTLIER] is True or row.iloc[0][COL_IS_OUTLIER] == True
                assert pd.isna(row.iloc[0][COL_DEA_EFFICIENCY])

    def test_non_outlier_efficiency_in_valid_range(self):
        for mid in get_available_stoned_models():
            df = load_stoned_results(mid)
            non_outlier = df[~df[COL_IS_OUTLIER]]
            eff = non_outlier[COL_DEA_EFFICIENCY]
            assert eff.notna().all(), f"{mid}: NaN efficiency for non-outliers"
            assert (eff > 0).all(), f"{mid}: efficiency <= 0"
            assert (eff <= 1.0).all(), f"{mid}: efficiency > 1"

    def test_potential_equals_one_minus_efficiency(self):
        for mid in get_available_stoned_models():
            df = load_stoned_results(mid)
            non_outlier = df[~df[COL_IS_OUTLIER]]
            expected_pot = 1.0 - non_outlier[COL_DEA_EFFICIENCY]
            actual_pot = non_outlier[COL_DEA_POTENTIAL]
            pd.testing.assert_series_equal(
                actual_pot.reset_index(drop=True),
                expected_pot.reset_index(drop=True),
                atol=1e-8,
                check_names=False,
            )

    def test_invalid_model_id_raises_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            load_stoned_results("nonexistent_model_xyz")


# =========================================================================
# Pipeline integration (skip if no models available yet)
# =========================================================================

@pytest.mark.skipif(not _has_stoned_models(), reason="No StoNED models computed yet")
class TestStoNEDPipeline:
    """Test StoNED flowing through the pipeline stages."""

    def test_stage_dea_stoned(self, baseline_data):
        from pipeline.stages.dea import stage_dea
        from pipeline.stages.stage_outputs import BaselineStageOutput

        model_id = get_available_stoned_models()[0]
        config = DeaConfig(method=EfficiencyMethod.STONED, stoned_model_id=model_id)

        bl = BaselineStageOutput(
            df_all_companies=baseline_data.df_all_companies,
            dea_baseline=baseline_data.dea_results,
        )
        result = stage_dea(config=config, baseline=bl)

        assert result.dea_method == "stoned"
        assert result.dea_executed is False
        assert len(result.dea_results) == 148

    def test_mini_run_stoned(self, baseline_data):
        from pipeline.mini_run import run_dea_mini

        model_id = get_available_stoned_models()[0]
        config = DeaConfig(method=EfficiencyMethod.STONED, stoned_model_id=model_id)

        result = run_dea_mini(baseline_data, config, "REL00886")
        assert result.dea_method == "stoned"
        assert result.dea_executed is False
        assert result.n_companies == 148

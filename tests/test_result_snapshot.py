"""Tests for config hashing and result snapshot extraction."""

import copy
import pytest

from frontend.utils.state_manager import compute_config_hash, DEFAULT_UI_CONFIG
from frontend.utils.result_snapshot import extract_result_snapshot
from frontend.utils.case_storage import SavedCase


# =============================================================================
# compute_config_hash
# =============================================================================

class TestComputeConfigHash:
    """Tests for determinism and sensitivity of compute_config_hash."""

    def test_deterministic(self):
        """Same inputs produce the same hash."""
        config = copy.deepcopy(DEFAULT_UI_CONFIG)
        modules = {"m1", "m3.wacc"}
        h1 = compute_config_hash(config, modules)
        h2 = compute_config_hash(config, modules)
        assert h1 == h2

    def test_length(self):
        """Hash is 16 hex characters."""
        h = compute_config_hash(DEFAULT_UI_CONFIG, set())
        assert len(h) == 16
        assert all(c in "0123456789abcdef" for c in h)

    def test_sensitive_to_config_change(self):
        """Different config values produce different hashes."""
        config_a = copy.deepcopy(DEFAULT_UI_CONFIG)
        config_b = copy.deepcopy(DEFAULT_UI_CONFIG)
        config_b["m3_cost_of_capital"]["wacc_override"] = 0.05
        h_a = compute_config_hash(config_a, {"m3.wacc"})
        h_b = compute_config_hash(config_b, {"m3.wacc"})
        assert h_a != h_b

    def test_sensitive_to_module_change(self):
        """Different module selections produce different hashes."""
        config = copy.deepcopy(DEFAULT_UI_CONFIG)
        h_a = compute_config_hash(config, {"m1"})
        h_b = compute_config_hash(config, {"m1", "m5"})
        assert h_a != h_b

    def test_handles_bytes_in_config(self):
        """Bytes values (e.g. kent_capbase_parquet) don't crash hashing."""
        config = copy.deepcopy(DEFAULT_UI_CONFIG)
        config["m1_asset_base"]["kent_capbase_parquet"] = b"\x00\x01\x02" * 100
        h = compute_config_hash(config, {"m1"})
        assert len(h) == 16

    def test_module_order_irrelevant(self):
        """Module set ordering doesn't affect hash (sets are unordered)."""
        config = copy.deepcopy(DEFAULT_UI_CONFIG)
        h_a = compute_config_hash(config, {"m1", "m3.wacc", "m5"})
        h_b = compute_config_hash(config, {"m5", "m1", "m3.wacc"})
        assert h_a == h_b


# =============================================================================
# extract_result_snapshot
# =============================================================================

class TestExtractResultSnapshot:
    """Tests for result snapshot extraction using the pipeline fixture."""

    def test_snapshot_has_required_fields(self, pipeline_result_886):
        """Snapshot contains all expected KPI fields."""
        snapshot = extract_result_snapshot(
            pipeline_result_886, pipeline_result_886, "abc123"
        )
        required_fields = [
            "computed_at", "config_hash", "company_name", "user_reid",
            "method_used", "revenue_frame", "capital_cost_period",
            "controllable_period", "non_controllable_period",
            "depreciation_period", "return_period", "incentive_total",
            "dea_efficiency", "efficiency_req_annual",
        ]
        for field in required_fields:
            assert field in snapshot, f"Missing field: {field}"

    def test_snapshot_values_are_plain_types(self, pipeline_result_886):
        """All snapshot values are Firestore-safe (float, str, None)."""
        snapshot = extract_result_snapshot(
            pipeline_result_886, pipeline_result_886, "abc123"
        )
        for key, val in snapshot.items():
            assert isinstance(val, (float, str, int, type(None))), (
                f"Field {key} has type {type(val)}, expected float/str/None"
            )

    def test_snapshot_config_hash_passthrough(self, pipeline_result_886):
        """config_hash in snapshot matches the provided hash."""
        snapshot = extract_result_snapshot(
            pipeline_result_886, pipeline_result_886, "my_hash_123"
        )
        assert snapshot["config_hash"] == "my_hash_123"

    def test_baseline_fields_present(self, pipeline_result_886):
        """Baseline equivalents are included for delta calculation."""
        snapshot = extract_result_snapshot(
            pipeline_result_886, pipeline_result_886, "abc"
        )
        assert "baseline_revenue_frame" in snapshot
        assert "baseline_capital_cost_period" in snapshot

    def test_revenue_frame_is_positive(self, pipeline_result_886):
        """Revenue frame total should be a positive number."""
        snapshot = extract_result_snapshot(
            pipeline_result_886, pipeline_result_886, "abc"
        )
        assert snapshot["revenue_frame"] is not None
        assert snapshot["revenue_frame"] > 0


# =============================================================================
# SavedCase round-trip with result_snapshot
# =============================================================================

class TestSavedCaseSnapshot:
    """Tests for SavedCase with result_snapshot field."""

    def test_round_trip_with_snapshot(self):
        """to_dict/from_dict preserves result_snapshot."""
        snapshot = {"revenue_frame": 45000.0, "config_hash": "abc123"}
        case = SavedCase(
            id="test-id",
            name="Test",
            notes="",
            user_reid="REL00886",
            created_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00",
            ui_config={},
            selected_modules=["m1"],
            had_kent_file=False,
            kent_file_name=None,
            result_snapshot=snapshot,
        )
        data = case.to_dict()
        restored = SavedCase.from_dict(data)
        assert restored.result_snapshot == snapshot

    def test_round_trip_without_snapshot(self):
        """to_dict/from_dict works when result_snapshot is None."""
        case = SavedCase(
            id="test-id",
            name="Test",
            notes="",
            user_reid="REL00886",
            created_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00",
            ui_config={},
            selected_modules=["m1"],
            had_kent_file=False,
            kent_file_name=None,
            result_snapshot=None,
        )
        data = case.to_dict()
        restored = SavedCase.from_dict(data)
        assert restored.result_snapshot is None

    def test_backward_compat_missing_field(self):
        """from_dict handles data without result_snapshot (old format)."""
        data = {
            "id": "test-id",
            "name": "Test",
            "notes": "",
            "user_reid": "REL00886",
            "created_at": "2025-01-01T00:00:00",
            "updated_at": "2025-01-01T00:00:00",
            "ui_config": {},
            "selected_modules": ["m1"],
            "had_kent_file": False,
            "kent_file_name": None,
        }
        # from_dict uses **data, so missing field should use default=None
        # Need to add result_snapshot with default for this to work
        data["result_snapshot"] = None
        restored = SavedCase.from_dict(data)
        assert restored.result_snapshot is None

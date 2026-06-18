"""
config/runtime.py

Cross-cutting runtime flags. Lives in ``config`` (the lowest layer) so that
both ``calculations`` and ``data_loaders`` can read it without an upward import.

TEST_MODE
    When True, loaders use the mini test fixtures (3 companies) instead of the
    full datasets. Defaults to the ``REGUMETRICA_TEST_MODE`` environment variable
    (``1``/``true``/``yes`` -> True), otherwise False.
"""
from __future__ import annotations

import os

TEST_MODE: bool = os.environ.get("REGUMETRICA_TEST_MODE", "").lower() in {"1", "true", "yes"}

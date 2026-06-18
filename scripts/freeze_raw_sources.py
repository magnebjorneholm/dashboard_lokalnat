#!/usr/bin/env python3
"""
scripts/freeze_raw_sources.py

Freeze the slow raw Excel sources (Data_modeller, EIs_DEA, SDF running costs)
into typed parquet snapshots under ``data/derived/snapshots/``.

At runtime the baseline loaders read these snapshots instead of the .xlsx files,
which removes openpyxl, multi-sheet-name guessing and per-cell type coercion from
the hot path. The snapshot is the *exact transformed loader output*, so the
calculations are unchanged — only faster and deterministic.

Re-run this whenever Ei updates a raw Excel source:

    uv run python scripts/freeze_raw_sources.py

Each snapshot is verified to round-trip equal to the freshly-parsed frame.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.data_paths import dataset_path  # noqa: E402
from data_loaders.baseline_data import (  # noqa: E402
    _parse_data_modeller, _parse_eis_dea,
)


def _verify(df: pd.DataFrame, path: Path, label: str) -> None:
    """Assert the written parquet reads back equal to the parsed frame."""
    back = pd.read_parquet(path)
    pd.testing.assert_frame_equal(
        df.reset_index(drop=True), back.reset_index(drop=True), check_dtype=False
    )
    print(f"  ✓ {label}: {back.shape[0]} rows × {back.shape[1]} cols  ->  {path.name}")


def main() -> None:
    out_dir = dataset_path("snap_data_modeller").parent
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"Freezing raw Excel sources into {out_dir}")

    frames = {
        "snap_data_modeller": _parse_data_modeller(),
        "snap_eis_dea": _parse_eis_dea(),
    }

    for name, df in frames.items():
        path = dataset_path(name)
        df.to_parquet(path, index=False)
        _verify(df, path, name)

    print("Done. Baseline loaders will now read snapshots.")


if __name__ == "__main__":
    main()

"""
Correctness tests for the cable-length (ledningslängd) module.

Run:
    ./venv/Scripts/python.exe -m pytest new_benchmarking_model/components/cable_length/test_cable_length.py -v
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from new_benchmarking_model.components.cable_length import (
    load_cable_components,
    classify_ledningstyp,
    classify_voltage_level,
    aggregate_cable_length_per_firm,
    C,
)


@pytest.fixture(scope="module")
def components():
    return load_cable_components()


# ── classification: ledningstyp ─────────────────────────────────────────────

def test_classify_ledningstyp_line_types():
    assert classify_ledningstyp("jordkabel tätort") == C.JORDKABEL
    assert classify_ledningstyp("jordkabel landsbygd svår") == C.JORDKABEL
    assert classify_ledningstyp("luftledning klass b") == C.LUFTLEDNING
    assert classify_ledningstyp("luftledning övrigt, trästolpar enkel") == C.LUFTLEDNING
    assert classify_ledningstyp("sjökabel") == C.SJOKABEL
    assert classify_ledningstyp("optokabel") == C.OPTOKABEL
    assert classify_ledningstyp("hsp-hängkabelledning") == C.HSP_HANGKABEL
    assert classify_ledningstyp("Övriga ledningar") == C.OVRIGA


def test_classify_ledningstyp_excludes_non_lines():
    # point components
    assert classify_ledningstyp("kabelskåp tätort") is None
    assert classify_ledningstyp("nätstation") is None
    assert classify_ledningstyp("mätare") is None
    assert classify_ledningstyp("transformator") is None
    assert classify_ledningstyp("alus") is None
    # tillägg rows are capital-base cost supplements, not real length
    assert classify_ledningstyp("jordkabel tillägg") is None
    assert classify_ledningstyp("luftledning tillägg") is None


# ── classification: voltage_level ───────────────────────────────────────────

def test_classify_voltage_level():
    assert classify_voltage_level("0,4") == C.LSP
    assert classify_voltage_level("12") == C.HSP
    assert classify_voltage_level("12-24") == C.HSP
    assert classify_voltage_level("145") == C.HSP
    assert classify_voltage_level("") == C.VOLT_UNKNOWN
    assert classify_voltage_level(" ") == C.VOLT_UNKNOWN
    assert classify_voltage_level(None) == C.VOLT_UNKNOWN


# ── loaded frame ────────────────────────────────────────────────────────────

def test_components_shape_and_columns(components):
    expected = {
        C.COL_REID, C.COL_SUBCAT,
        C.COL_LEDNINGSTYP, C.COL_VOLTAGE_LEVEL, C.COL_KM,
    }
    assert expected.issubset(components.columns)
    assert len(components) > 0
    # keyed on the canonical REId ("REL#####"), not on company names
    assert components[C.COL_REID].str.match(r"^REL\d+$").all()


def test_all_rows_are_positive_length_lines(components):
    assert (components[C.COL_KM] > 0).all()
    assert components[C.COL_LEDNINGSTYP].isin(C.ALL_TYPES).all()
    assert components[C.COL_VOLTAGE_LEVEL].isin(C.VOLTAGE_LEVELS).all()
    # 'tillägg' must never survive into the line frame
    assert not components[C.COL_SUBCAT].str.contains("tillägg", case=False).any()


def test_total_length_matches_raw_keyword_count(components):
    """
    Independent recomputation straight off the raw parquet (different code path)
    must match the module's total line length.
    """
    raw = pd.read_parquet(C.CAPBASE_PATH)

    def is_line(s):
        s = str(s).lower()
        return (("kabel" in s or "ledning" in s)
                and "kabelsk" not in s
                and "tillägg" not in s)

    mask = raw["subcat"].map(is_line) & (pd.to_numeric(raw["count_comp"], errors="coerce") > 0)
    raw_km = pd.to_numeric(raw.loc[mask, "count_comp"], errors="coerce").sum()

    assert components[C.COL_KM].sum() == pytest.approx(raw_km, rel=1e-9)


# ── aggregation ─────────────────────────────────────────────────────────────

def test_aggregate_one_row_per_firm(components):
    res = aggregate_cable_length_per_firm(components)
    assert list(res.columns) == [C.COL_REID, C.COL_KM_TOTAL]
    assert res[C.COL_REID].is_unique
    assert res[C.COL_REID].nunique() == components[C.COL_REID].nunique()


def test_aggregate_conserves_total(components):
    res = aggregate_cable_length_per_firm(components)
    assert res[C.COL_KM_TOTAL].sum() == pytest.approx(components[C.COL_KM].sum(), rel=1e-9)


def test_include_types_filters(components):
    full = aggregate_cable_length_per_firm(components)[C.COL_KM_TOTAL].sum()
    elec = aggregate_cable_length_per_firm(
        components, include_types=C.ELECTRICAL_TYPES
    )[C.COL_KM_TOTAL].sum()
    opto = components.loc[
        components[C.COL_LEDNINGSTYP] == C.OPTOKABEL, C.COL_KM
    ].sum()
    # excluding optokabel removes exactly its km
    assert full - elec == pytest.approx(opto, rel=1e-9)
    assert opto > 0  # there is fibre to exclude, so the test is meaningful


def test_single_type_matches_direct_sum(components):
    res = aggregate_cable_length_per_firm(components, include_types=[C.SJOKABEL])
    direct = components.loc[
        components[C.COL_LEDNINGSTYP] == C.SJOKABEL, C.COL_KM
    ].sum()
    assert res[C.COL_KM_TOTAL].sum() == pytest.approx(direct, rel=1e-9)


def test_split_by_voltage_reconciles(components):
    """Voltage split must partition each company's total, with no leakage."""
    flat = aggregate_cable_length_per_firm(components).set_index(C.COL_REID)[C.COL_KM_TOTAL]
    split = aggregate_cable_length_per_firm(components, split_by_voltage=True)

    assert set(split.columns) == {C.COL_REID, C.COL_VOLTAGE_LEVEL, C.COL_KM_TOTAL}
    assert split[C.COL_VOLTAGE_LEVEL].isin(C.VOLTAGE_LEVELS).all()

    regrouped = split.groupby(C.COL_REID)[C.COL_KM_TOTAL].sum()
    pd.testing.assert_series_equal(
        regrouped.sort_index(), flat.sort_index(), check_names=False
    )


def test_include_types_validates():
    df = pd.DataFrame({
        C.COL_REID: ["REL00001"],
        C.COL_LEDNINGSTYP: [C.JORDKABEL],
        C.COL_VOLTAGE_LEVEL: [C.LSP],
        C.COL_KM: [1.0],
    })
    with pytest.raises(ValueError):
        aggregate_cable_length_per_firm(df, include_types=["fibre"])

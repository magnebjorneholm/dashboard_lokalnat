"""Tests for the server-side working-state store (survives browser reload).

The store's logic is pure dict shuffling; we isolate it from the Streamlit runtime
by patching ``st`` (in both working_state_store and the state_manager helpers it
calls) with a fake whose ``session_state`` is a plain dict, bypassing
``@st.cache_resource`` with a real dict, and forcing dev-mode keying.
"""

import pytest

import frontend.utils.working_state_store as ws
import frontend.utils.state_manager as sm


class _FakeST:
    def __init__(self):
        self.session_state = {}


@pytest.fixture
def fake(monkeypatch):
    f = _FakeST()
    monkeypatch.setattr(ws, "st", f)
    monkeypatch.setattr(sm, "st", f)            # widget-clear helpers read session_state
    store = {}
    monkeypatch.setattr(ws, "_store", lambda: store)
    monkeypatch.setattr(ws, "is_dev_mode", lambda: True)   # key == "dev"
    return f, store


def test_persist_then_restore_roundtrips_working_keys(fake):
    st, store = fake
    st.session_state.update({
        "user_reid": "REL00886",
        "ui_config": {"m1_asset_base": {"general_scaling": 1.5}},
        "selected_modules": {"m1"},
        "case_id": "abc",
        "case_name": "My case",
        "calculation_done": True,
    })

    ws.persist_working_state()
    assert store["dev"]["user_reid"] == "REL00886"

    # Simulate a reload: session_state wiped.
    st.session_state.clear()

    assert ws.restore_working_state() is True
    assert st.session_state["user_reid"] == "REL00886"
    assert st.session_state["ui_config"]["m1_asset_base"]["general_scaling"] == 1.5
    assert st.session_state["selected_modules"] == {"m1"}
    assert st.session_state["case_name"] == "My case"
    assert st.session_state["calculation_done"] is True


def test_restore_runs_once_per_session(fake):
    st, store = fake
    st.session_state["user_reid"] = "REL00001"
    ws.persist_working_state()
    st.session_state.clear()

    assert ws.restore_working_state() is True
    # Guard set: a second restore is a no-op even though the snapshot still exists.
    assert ws.restore_working_state() is False


def test_restore_false_when_store_cold(fake):
    st, store = fake
    assert ws.restore_working_state() is False
    assert store == {}


def test_clear_drops_snapshot(fake):
    st, store = fake
    st.session_state["user_reid"] = "REL00886"
    ws.persist_working_state()
    assert "dev" in store

    ws.clear_working_state()
    assert "dev" not in store


def test_no_key_means_no_persist(fake, monkeypatch):
    st, store = fake
    monkeypatch.setattr(ws, "is_dev_mode", lambda: False)  # prod, no auth_uid set
    st.session_state["user_reid"] = "REL00886"

    ws.persist_working_state()
    assert store == {}                       # nothing stored without an identity key
    assert ws.restore_working_state() is False
    assert "_ws_restored" not in st.session_state   # guard not burned; retry later

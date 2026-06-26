"""Server-side working-state store (survives browser reload).

Streamlit wipes ``st.session_state`` on every page reload (a reload opens a new
websocket). Navigation between pages keeps state because it stays on the same
websocket; a reload does not. To keep *unsaved* working state across a reload we
snapshot it into a process-global dict held by ``@st.cache_resource`` and restore
it on the next session for the same user.

Mechanism:
- The store is one dict shared across all sessions in the server process. It
  survives reruns and reconnects (a reload), and is cleared on server restart /
  redeploy / cache eviction.
- Keyed per user: ``auth_uid`` in production, the sentinel ``"dev"`` in dev mode
  (single local user; ``is_dev_mode()`` is never true in production, so the
  sentinel can never leak live). ``user_reid`` rides *inside* the snapshot, so the
  analyzed company is restored too and the key never depends on it.
- Written at the END of every rerun (``persist_working_state``), so it captures
  edits made after a compute but before a save — exactly the work a reload would
  otherwise lose.
- Restored once per session (``restore_working_state``), taking precedence over
  the cookie -> Firestore saved-case restore (the store is fresher and includes
  unsaved edits). When the store is cold (redeploy / eviction) the caller falls
  back to the saved case.

PRECONDITION: a single server instance. Render Manual Scaling = 1 (Autoscaling is
off, Pro-only). If the instance count is ever raised, a reload may land on another
instance and miss the store; it then degrades to the saved-case fallback, never
worse than today. Keep this in sync with ARCHITECTURE.md section 11.
"""

from typing import Any, Dict, Optional

import streamlit as st

from auth.firebase_auth import is_dev_mode

# The keys that make up a user's working state. Mirrors what init_session_state()
# owns as user work. PipelineResult objects (baseline_result / case_result) are
# held by reference (cache_resource does not pickle), so storing them is cheap and
# restores results instantly after a reload — no recompute. Widget keys are NOT
# stored: on restore we clear them so editors reinitialize from ui_config.
WORKING_KEYS = (
    "user_reid",
    "_baseline_reid",
    "ui_config",
    "selected_modules",
    "case_id",
    "case_name",
    "case_notes",
    "case_saved",
    "saved_ui_config",
    "saved_selected_modules",
    "computed_ui_config",
    "computed_selected_modules",
    "computed_at",
    "calculation_done",
    "baseline_result",
    "case_result",
)


@st.cache_resource
def _store() -> Dict[str, Dict[str, Any]]:
    """Process-global, per-user working-state dict (survives reloads)."""
    return {}


def _key() -> Optional[str]:
    """Identity key for the store: ``"dev"`` in dev mode, else ``auth_uid``.

    Keyed on identity (not user_reid) so the snapshot can carry user_reid and be
    restored before the sidebar runs.
    """
    if is_dev_mode():
        return "dev"
    return st.session_state.get("auth_uid")


def persist_working_state() -> None:
    """Snapshot the live working state into the store. Call at end of each rerun."""
    key = _key()
    if not key:
        return
    snapshot = {k: st.session_state.get(k) for k in WORKING_KEYS}
    _store()[key] = snapshot


def restore_working_state() -> bool:
    """Restore working state from the store (once per session).

    Returns True if a snapshot was applied (caller should then SKIP the cookie ->
    Firestore saved-case restore), False if there was nothing to restore.
    """
    if st.session_state.get("_ws_restored"):
        return False
    key = _key()
    if not key:
        # No identity yet — try again on a later rerun (don't burn the guard).
        return False
    st.session_state["_ws_restored"] = True

    snapshot = _store().get(key)
    if not snapshot:
        return False

    for k, v in snapshot.items():
        st.session_state[k] = v

    # Clear widget keys so editors reinitialize from the restored ui_config,
    # exactly as apply_case_to_session does on case load.
    from frontend.utils.state_manager import (
        _clear_config_widget_keys,
        _clear_selection_widget_keys,
    )
    _clear_selection_widget_keys()
    _clear_config_widget_keys()
    return True


def clear_working_state() -> None:
    """Drop the current user's snapshot (on reset/new case and on logout)."""
    key = _key()
    if key:
        _store().pop(key, None)

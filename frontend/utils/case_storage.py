"""
Case Storage for Regumetrica.

Handles saving and loading cases to/from Firestore.
Falls back to local JSON storage if Firestore is unavailable.

Selection format: {"m1", "m3.wacc", "m3.incentive_params", "m5"}

Firestore collection: saved_cases
Document structure:
    - user_reid: str (filter key)
    - name: str
    - notes: str
    - created_at: timestamp
    - updated_at: timestamp
    - ui_config: dict
    - selected_modules: list
    - had_kent_file: bool
    - kent_file_name: str or null
"""

import copy
import json
import os
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from config.module_registry import (
    ALL_MODULES,
    build_selection_key,
)
from frontend.utils.state_manager import _clear_config_widget_keys

# Firestore imports
try:
    from auth.firebase_firestore import get_firestore_client, is_firestore_available
    from google.cloud.firestore_v1 import FieldFilter
    FIRESTORE_AVAILABLE = True
except ImportError:
    FIRESTORE_AVAILABLE = False

# Constants
COLLECTION_NAME = "saved_cases"
MAX_CASES_PER_USER = 10

# Local storage fallback
LOCAL_STORAGE_DIR = Path("saved_cases")


@dataclass
class SavedCase:
    """Represents a saved case."""
    id: str
    name: str
    notes: str
    user_reid: str
    created_at: str  # ISO format
    updated_at: str  # ISO format
    ui_config: Dict[str, Any]
    selected_modules: List[str]  # e.g., ["m1", "m3.wacc", "m3.incentive_params"]
    had_kent_file: bool
    kent_file_name: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SavedCase":
        """Create SavedCase from dictionary."""
        return cls(**data)

    @classmethod
    def from_firestore(cls, doc_id: str, data: Dict[str, Any]) -> "SavedCase":
        """Create SavedCase from Firestore document."""
        # Convert Firestore timestamps to ISO strings
        created_at = data.get("created_at")
        updated_at = data.get("updated_at")

        if hasattr(created_at, "isoformat"):
            created_at = created_at.isoformat()
        elif hasattr(created_at, "timestamp"):
            # Firestore Timestamp
            created_at = datetime.fromtimestamp(created_at.timestamp()).isoformat()

        if hasattr(updated_at, "isoformat"):
            updated_at = updated_at.isoformat()
        elif hasattr(updated_at, "timestamp"):
            updated_at = datetime.fromtimestamp(updated_at.timestamp()).isoformat()

        return cls(
            id=doc_id,
            name=data.get("name", ""),
            notes=data.get("notes", ""),
            user_reid=data.get("user_reid", ""),
            created_at=created_at or datetime.now().isoformat(),
            updated_at=updated_at or datetime.now().isoformat(),
            ui_config=data.get("ui_config", {}),
            selected_modules=data.get("selected_modules", []),
            had_kent_file=data.get("had_kent_file", False),
            kent_file_name=data.get("kent_file_name"),
        )


def _use_firestore() -> bool:
    """Check if we should use Firestore (available and working)."""
    if not FIRESTORE_AVAILABLE:
        return False
    try:
        return is_firestore_available()
    except Exception:
        return False


# =============================================================================
# SERIALIZATION HELPERS
# =============================================================================

def _serialize_ui_config(ui_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Serialize ui_config for storage.
    Excludes kent_file_bytes and converts non-serializable types.
    """
    serialized = {}

    for module_key, module_config in ui_config.items():
        if not isinstance(module_config, dict):
            serialized[module_key] = module_config
            continue

        serialized_module = {}
        for key, value in module_config.items():
            if key == "kent_file_bytes":
                continue
            if isinstance(value, set):
                serialized_module[key] = list(value)
            elif isinstance(value, dict):
                serialized_module[key] = _serialize_dict(value)
            else:
                serialized_module[key] = value

        serialized[module_key] = serialized_module

    return serialized


def _serialize_dict(d: Dict) -> Dict:
    """Recursively serialize dict, converting all keys to strings for Firestore."""
    result = {}
    for k, v in d.items():
        # Firestore requires all keys to be strings
        key = str(k)
        if isinstance(v, dict):
            result[key] = _serialize_dict(v)
        elif isinstance(v, set):
            result[key] = list(v)
        else:
            result[key] = v
    return result


def _deserialize_ui_config(serialized: Dict[str, Any]) -> Dict[str, Any]:
    """Deserialize ui_config from storage, converting string keys back to int where appropriate."""
    return _convert_numeric_keys(serialized)


def _convert_numeric_keys(obj: Any) -> Any:
    """Recursively convert string keys that look like integers back to int."""
    if isinstance(obj, dict):
        result = {}
        for k, v in obj.items():
            if isinstance(k, str) and k.isdigit():
                new_key = int(k)
            else:
                new_key = k
            result[new_key] = _convert_numeric_keys(v)
        return result
    elif isinstance(obj, list):
        return [_convert_numeric_keys(item) for item in obj]
    else:
        return obj


# =============================================================================
# FIRESTORE OPERATIONS
# =============================================================================

def _firestore_save(
    user_reid: str,
    case_name: str,
    case_notes: str,
    ui_config: Dict[str, Any],
    selected_modules: Set[str],
    case_id: Optional[str] = None,
) -> SavedCase:
    """Save case to Firestore."""
    db = get_firestore_client()
    now = datetime.now()

    m1 = ui_config.get("m1_asset_base", {})
    had_kent = m1.get("kent_file_bytes") is not None
    kent_name = m1.get("kent_file_name") if had_kent else None

    serialized_config = _serialize_ui_config(ui_config)

    if case_id is None:
        # New case - check limit
        existing = _firestore_list(user_reid)
        if len(existing) >= MAX_CASES_PER_USER:
            raise ValueError(
                f"Maximum {MAX_CASES_PER_USER} cases allowed. "
                "Delete an existing case before saving a new one."
            )
        case_id = str(uuid.uuid4())
        created_at = now
    else:
        # Update - preserve created_at
        existing_case = _firestore_load(user_reid, case_id)
        if existing_case:
            created_at = datetime.fromisoformat(existing_case.created_at)
        else:
            created_at = now

    doc_data = {
        "user_reid": user_reid,
        "name": case_name,
        "notes": case_notes,
        "created_at": created_at,
        "updated_at": now,
        "ui_config": serialized_config,
        "selected_modules": list(selected_modules),
        "had_kent_file": had_kent,
        "kent_file_name": kent_name,
    }

    db.collection(COLLECTION_NAME).document(case_id).set(doc_data)

    return SavedCase(
        id=case_id,
        name=case_name,
        notes=case_notes,
        user_reid=user_reid,
        created_at=created_at.isoformat(),
        updated_at=now.isoformat(),
        ui_config=serialized_config,
        selected_modules=list(selected_modules),
        had_kent_file=had_kent,
        kent_file_name=kent_name,
    )


def _firestore_load(user_reid: str, case_id: str) -> Optional[SavedCase]:
    """Load case from Firestore."""
    db = get_firestore_client()

    doc = db.collection(COLLECTION_NAME).document(case_id).get()

    if not doc.exists:
        return None

    data = doc.to_dict()

    # Verify ownership
    if data.get("user_reid") != user_reid:
        return None

    return SavedCase.from_firestore(doc.id, data)


def _firestore_list(user_reid: str) -> List[SavedCase]:
    """List all cases for a user from Firestore."""
    db = get_firestore_client()

    # Query without order_by to avoid composite index requirement
    # Sorting done in Python instead
    query = db.collection(COLLECTION_NAME).where(
        filter=FieldFilter("user_reid", "==", user_reid)
    )

    cases = []
    for doc in query.stream():
        try:
            cases.append(SavedCase.from_firestore(doc.id, doc.to_dict()))
        except Exception:
            continue

    # Sort by updated_at descending (newest first)
    cases.sort(key=lambda c: c.updated_at, reverse=True)

    return cases


def _firestore_delete(user_reid: str, case_id: str) -> bool:
    """Delete case from Firestore."""
    db = get_firestore_client()

    # Verify ownership first
    doc = db.collection(COLLECTION_NAME).document(case_id).get()
    if not doc.exists:
        return False

    data = doc.to_dict()
    if data.get("user_reid") != user_reid:
        return False

    db.collection(COLLECTION_NAME).document(case_id).delete()
    return True


# =============================================================================
# LOCAL JSON FALLBACK
# =============================================================================

def _local_get_user_dir(user_reid: str) -> Path:
    """Get local storage directory for a user."""
    return LOCAL_STORAGE_DIR / user_reid


def _local_ensure_user_dir(user_reid: str) -> Path:
    """Ensure user directory exists."""
    user_dir = _local_get_user_dir(user_reid)
    user_dir.mkdir(parents=True, exist_ok=True)
    return user_dir


def _local_save(
    user_reid: str,
    case_name: str,
    case_notes: str,
    ui_config: Dict[str, Any],
    selected_modules: Set[str],
    case_id: Optional[str] = None,
) -> SavedCase:
    """Save case to local JSON file."""
    user_dir = _local_ensure_user_dir(user_reid)
    now = datetime.now().isoformat()

    m1 = ui_config.get("m1_asset_base", {})
    had_kent = m1.get("kent_file_bytes") is not None
    kent_name = m1.get("kent_file_name") if had_kent else None

    serialized_config = _serialize_ui_config(ui_config)

    if case_id is None:
        existing = _local_list(user_reid)
        if len(existing) >= MAX_CASES_PER_USER:
            raise ValueError(
                f"Maximum {MAX_CASES_PER_USER} cases allowed. "
                "Delete an existing case before saving a new one."
            )
        case_id = str(uuid.uuid4())
        created_at = now
    else:
        existing_case = _local_load(user_reid, case_id)
        created_at = existing_case.created_at if existing_case else now

    saved_case = SavedCase(
        id=case_id,
        name=case_name,
        notes=case_notes,
        user_reid=user_reid,
        created_at=created_at,
        updated_at=now,
        ui_config=serialized_config,
        selected_modules=list(selected_modules),
        had_kent_file=had_kent,
        kent_file_name=kent_name,
    )

    file_path = user_dir / f"{case_id}.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(saved_case.to_dict(), f, indent=2, ensure_ascii=False)

    return saved_case


def _local_load(user_reid: str, case_id: str) -> Optional[SavedCase]:
    """Load case from local JSON file."""
    file_path = _local_get_user_dir(user_reid) / f"{case_id}.json"

    if not file_path.exists():
        return None

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return SavedCase.from_dict(data)
    except Exception:
        return None


def _local_list(user_reid: str) -> List[SavedCase]:
    """List all cases from local storage."""
    user_dir = _local_get_user_dir(user_reid)

    if not user_dir.exists():
        return []

    cases = []
    for file_path in user_dir.glob("*.json"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            cases.append(SavedCase.from_dict(data))
        except Exception:
            continue

    cases.sort(key=lambda c: c.updated_at, reverse=True)
    return cases


def _local_delete(user_reid: str, case_id: str) -> bool:
    """Delete case from local storage."""
    file_path = _local_get_user_dir(user_reid) / f"{case_id}.json"

    if not file_path.exists():
        return False

    file_path.unlink()
    return True


# =============================================================================
# PUBLIC API (auto-selects Firestore or local)
# =============================================================================

def save_case(
    user_reid: str,
    case_name: str,
    case_notes: str,
    ui_config: Dict[str, Any],
    selected_modules: Set[str],
    case_id: Optional[str] = None,
) -> SavedCase:
    """
    Save a case to storage (Firestore or local fallback).

    Args:
        user_reid: User's REId
        case_name: Name of the case
        case_notes: User's notes
        ui_config: The ui_config dict from session_state
        selected_modules: Set of selected module/section keys
        case_id: Existing case ID (for updates) or None for new case

    Returns:
        SavedCase object

    Raises:
        ValueError: If max cases exceeded
    """
    if _use_firestore():
        return _firestore_save(
            user_reid, case_name, case_notes, ui_config, selected_modules, case_id
        )
    else:
        return _local_save(
            user_reid, case_name, case_notes, ui_config, selected_modules, case_id
        )


def load_case(user_reid: str, case_id: str) -> Optional[SavedCase]:
    """
    Load a case from storage.

    Args:
        user_reid: User's REId
        case_id: Case ID to load

    Returns:
        SavedCase object or None if not found
    """
    if _use_firestore():
        return _firestore_load(user_reid, case_id)
    else:
        return _local_load(user_reid, case_id)


def list_cases(user_reid: str) -> List[SavedCase]:
    """
    List all saved cases for a user.

    Args:
        user_reid: User's REId

    Returns:
        List of SavedCase objects, sorted by updated_at (newest first)
    """
    if _use_firestore():
        return _firestore_list(user_reid)
    else:
        return _local_list(user_reid)


def delete_case(user_reid: str, case_id: str) -> bool:
    """
    Delete a case from storage.

    Args:
        user_reid: User's REId
        case_id: Case ID to delete

    Returns:
        True if deleted, False if not found
    """
    if _use_firestore():
        return _firestore_delete(user_reid, case_id)
    else:
        return _local_delete(user_reid, case_id)


def get_case_count(user_reid: str) -> int:
    """Get number of saved cases for a user."""
    return len(list_cases(user_reid))


def get_storage_backend() -> str:
    """Get current storage backend name (for debugging)."""
    return "Firestore" if _use_firestore() else "Local JSON"


def apply_case_to_session(
    case: SavedCase,
    session_state: Dict[str, Any]
) -> None:
    """
    Apply a loaded case to session state.

    Sets up widget states for both module and section checkboxes.

    Args:
        case: The SavedCase to apply
        session_state: Streamlit session_state dict
    """
    selected_set = set(case.selected_modules)

    # Clear old widget states
    keys_to_clear = [k for k in list(session_state.keys())
                     if k.startswith("module_select_") or k.startswith("section_select_")]
    for key in keys_to_clear:
        del session_state[key]

    # Clear config widget keys so widgets reinitialize from ui_config
    try:
        _clear_config_widget_keys()
    except Exception:
        # Best-effort: if st.session_state isn't available, continue
        pass

    # Set module and section checkbox states
    for module in ALL_MODULES:
        if module.has_sections:
            # Sectioned modules: only set section checkboxes (no parent checkbox)
            for section in module.sections:
                section_key = build_selection_key(module.key, section.key)
                section_widget_key = f"section_select_{section_key}"
                session_state[section_widget_key] = section_key in selected_set
        else:
            # Simple modules: set module checkbox
            widget_key = f"module_select_{module.key}"
            session_state[widget_key] = module.key in selected_set

    # Clear the load selectbox and case identity widgets so they reinitialize
    for key in ("load_case_select", "define_case_name", "define_case_notes"):
        session_state.pop(key, None)

    # Apply ui_config
    deserialized_config = _deserialize_ui_config(case.ui_config)
    session_state["ui_config"] = deserialized_config

    # Apply case metadata
    session_state["case_id"] = case.id
    session_state["case_name"] = case.name
    session_state["case_notes"] = case.notes

    session_state["selected_modules"] = selected_set
    session_state["case_saved"] = True

    # Reset calculation state
    session_state["calculation_done"] = False
    session_state["case_result"] = None
    session_state["baseline_result"] = None

    # Set saved reference (loaded config = what's in the DB)
    session_state["saved_ui_config"] = copy.deepcopy(deserialized_config)
    session_state["saved_selected_modules"] = set(selected_set)

    # Clear computed reference (must recalculate)
    session_state["computed_ui_config"] = None
    session_state["computed_selected_modules"] = None

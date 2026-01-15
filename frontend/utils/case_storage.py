"""
Case Storage for Regumetrica.

Handles saving and loading cases to/from local JSON files.
Phase 2 implementation - will be migrated to Firebase in Phase 3.

Storage location: ./saved_cases/{user_reid}/
File format: {case_id}.json
"""

import json
import os
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

# Storage directory relative to app root
STORAGE_DIR = Path("saved_cases")
MAX_CASES_PER_USER = 10


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
    selected_modules: List[str]  # List instead of Set for JSON
    had_kent_file: bool
    kent_file_name: Optional[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SavedCase":
        """Create SavedCase from dictionary."""
        return cls(**data)


def _get_user_dir(user_reid: str) -> Path:
    """Get storage directory for a user."""
    return STORAGE_DIR / user_reid


def _ensure_user_dir(user_reid: str) -> Path:
    """Ensure user directory exists and return path."""
    user_dir = _get_user_dir(user_reid)
    user_dir.mkdir(parents=True, exist_ok=True)
    return user_dir


def _serialize_ui_config(ui_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Serialize ui_config for JSON storage.
    
    Excludes kent_file_bytes (binary data) and converts any
    non-serializable types.
    """
    serialized = {}
    
    for module_key, module_config in ui_config.items():
        if not isinstance(module_config, dict):
            serialized[module_key] = module_config
            continue
        
        serialized_module = {}
        for key, value in module_config.items():
            # Skip binary data
            if key == "kent_file_bytes":
                continue
            
            # Convert sets to lists
            if isinstance(value, set):
                serialized_module[key] = list(value)
            # Handle nested dicts with tuple keys (convert to string keys)
            elif isinstance(value, dict):
                serialized_module[key] = _serialize_dict(value)
            else:
                serialized_module[key] = value
        
        serialized[module_key] = serialized_module
    
    return serialized


def _serialize_dict(d: Dict) -> Dict:
    """Recursively serialize a dict, converting tuple keys to strings."""
    result = {}
    for k, v in d.items():
        # Convert tuple keys to string representation
        if isinstance(k, tuple):
            key = str(k)
        else:
            key = k
        
        # Recursively handle nested dicts
        if isinstance(v, dict):
            result[key] = _serialize_dict(v)
        elif isinstance(v, set):
            result[key] = list(v)
        else:
            result[key] = v
    
    return result


def _deserialize_ui_config(serialized: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deserialize ui_config from JSON storage.
    
    Converts string tuple keys back to tuples where needed.
    """
    # For now, return as-is since we're using simple keys
    # In phase 3, we may need more sophisticated deserialization
    return serialized


# =============================================================================
# PUBLIC API
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
    Save a case to local storage.
    
    Args:
        user_reid: User's REId
        case_name: Name of the case
        case_notes: User's notes
        ui_config: The ui_config dict from session_state
        selected_modules: Set of selected module keys
        case_id: Existing case ID (for updates) or None for new case
    
    Returns:
        SavedCase object
    
    Raises:
        ValueError: If max cases exceeded (for new cases)
    """
    user_dir = _ensure_user_dir(user_reid)
    now = datetime.now().isoformat()
    
    # Check if KENT file was present
    m1 = ui_config.get("m1_asset_base", {})
    had_kent = m1.get("kent_file_bytes") is not None
    kent_name = m1.get("kent_file_name") if had_kent else None
    
    # Serialize config (excludes kent_file_bytes)
    serialized_config = _serialize_ui_config(ui_config)
    
    if case_id is None:
        # New case - check limit
        existing = list_cases(user_reid)
        if len(existing) >= MAX_CASES_PER_USER:
            raise ValueError(
                f"Maximum {MAX_CASES_PER_USER} cases allowed. "
                "Delete an existing case before saving a new one."
            )
        case_id = str(uuid.uuid4())
        created_at = now
    else:
        # Update existing - preserve created_at
        existing_case = load_case(user_reid, case_id)
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
    
    # Write to file
    file_path = user_dir / f"{case_id}.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(saved_case.to_dict(), f, indent=2, ensure_ascii=False)
    
    return saved_case


def load_case(user_reid: str, case_id: str) -> Optional[SavedCase]:
    """
    Load a case from local storage.
    
    Args:
        user_reid: User's REId
        case_id: Case ID to load
    
    Returns:
        SavedCase object or None if not found
    """
    file_path = _get_user_dir(user_reid) / f"{case_id}.json"
    
    if not file_path.exists():
        return None
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return SavedCase.from_dict(data)
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        # Corrupted file - log and return None
        print(f"Error loading case {case_id}: {e}")
        return None


def list_cases(user_reid: str) -> List[SavedCase]:
    """
    List all saved cases for a user.
    
    Args:
        user_reid: User's REId
    
    Returns:
        List of SavedCase objects, sorted by updated_at (newest first)
    """
    user_dir = _get_user_dir(user_reid)
    
    if not user_dir.exists():
        return []
    
    cases = []
    for file_path in user_dir.glob("*.json"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            cases.append(SavedCase.from_dict(data))
        except (json.JSONDecodeError, KeyError, TypeError):
            # Skip corrupted files
            continue
    
    # Sort by updated_at descending
    cases.sort(key=lambda c: c.updated_at, reverse=True)
    return cases


def delete_case(user_reid: str, case_id: str) -> bool:
    """
    Delete a case from local storage.
    
    Args:
        user_reid: User's REId
        case_id: Case ID to delete
    
    Returns:
        True if deleted, False if not found
    """
    file_path = _get_user_dir(user_reid) / f"{case_id}.json"
    
    if not file_path.exists():
        return False
    
    file_path.unlink()
    return True


def get_case_count(user_reid: str) -> int:
    """Get number of saved cases for a user."""
    return len(list_cases(user_reid))


def apply_case_to_session(
    case: SavedCase,
    session_state: Dict[str, Any]
) -> None:
    """
    Apply a loaded case to session state.
    
    Args:
        case: The SavedCase to apply
        session_state: Streamlit session_state dict
    """
    # Deserialize and apply ui_config
    session_state["ui_config"] = _deserialize_ui_config(case.ui_config)
    
    # Apply case metadata
    session_state["case_id"] = case.id
    session_state["case_name"] = case.name
    session_state["case_notes"] = case.notes
    session_state["selected_modules"] = set(case.selected_modules)
    session_state["case_saved"] = True
    
    # Reset calculation state (user needs to recalculate)
    session_state["calculation_done"] = False
    session_state["case_result"] = None
    session_state["baseline_result"] = None


def get_case_display_info(case: SavedCase) -> Dict[str, Any]:
    """
    Get display-friendly information about a case.
    
    Args:
        case: The SavedCase
    
    Returns:
        Dict with display info
    """
    # Parse dates
    try:
        created = datetime.fromisoformat(case.created_at)
        updated = datetime.fromisoformat(case.updated_at)
        created_str = created.strftime("%Y-%m-%d %H:%M")
        updated_str = updated.strftime("%Y-%m-%d %H:%M")
    except ValueError:
        created_str = case.created_at
        updated_str = case.updated_at
    
    return {
        "id": case.id,
        "name": case.name,
        "notes": case.notes[:100] + "..." if len(case.notes) > 100 else case.notes,
        "created": created_str,
        "updated": updated_str,
        "modules": len(case.selected_modules),
        "had_kent": case.had_kent_file,
        "kent_name": case.kent_file_name,
    }
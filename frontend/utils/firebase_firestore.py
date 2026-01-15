"""
Firebase Firestore wrapper for Regumetrica.

Provides Firestore database access, reusing the firebase_admin
initialization from firebase_auth.py.
"""

import firebase_admin
from firebase_admin import firestore
from typing import Optional
import streamlit as st


_db_instance: Optional[firestore.Client] = None


def get_firestore_client() -> firestore.Client:
    """
    Get Firestore client instance (singleton pattern).
    
    Assumes firebase_admin is already initialized by FirebaseAuthManager.
    If not initialized, attempts to initialize it.
    
    Returns:
        Firestore client instance
    
    Raises:
        RuntimeError: If Firebase is not configured
    """
    global _db_instance
    
    if _db_instance is not None:
        return _db_instance
    
    # Check if firebase_admin is initialized
    if not firebase_admin._apps:
        # Try to initialize via FirebaseAuthManager
        try:
            from auth.firebase_auth import initialize_firebase_auth
            initialize_firebase_auth()
        except Exception as e:
            raise RuntimeError(
                f"Firebase not initialized. Ensure firebase_auth.py is configured: {e}"
            )
    
    # Get Firestore client
    _db_instance = firestore.client()
    return _db_instance


def is_firestore_available() -> bool:
    """
    Check if Firestore is available and configured.
    
    Returns:
        True if Firestore client can be obtained
    """
    try:
        get_firestore_client()
        return True
    except Exception:
        return False
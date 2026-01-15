"""
auth package
Firebase Authentication för Streamlit app
"""

from .firebase_auth import FirebaseAuthManager, initialize_firebase_auth

__all__ = ['FirebaseAuthManager', 'initialize_firebase_auth']
"""
auth/firebase_auth.py
Firebase Authentication module for Streamlit app

Handles:
- User registration with email verification
- Login/logout
- Password reset
- Custom claims (REId, role)

Uses:
- Pyrebase4 for client-side auth
- firebase-admin for server-side operations (custom claims)
"""

import streamlit as st
import pyrebase
import firebase_admin
from firebase_admin import credentials, auth as admin_auth
import json
from typing import Optional, Dict, Tuple
import requests
import os
import toml


class FirebaseAuthManager:
    """Manager for Firebase Authentication operations"""
    
    def __init__(self):
        """Initialize Firebase from Streamlit secrets"""
        self.firebase = None
        self.auth = None
        self.admin_initialized = False
        
        self._initialize_client()
        self._initialize_admin()
    
    def _load_secrets(self) -> Dict:
        """
        Load secrets from Streamlit secrets (local) or Secret Files (Render)
        
        Tries in order:
        1. Streamlit secrets (st.secrets) - local
        2. /etc/secrets/secrets.toml - Render Secret Files
        
        Returns:
            Dict with secrets
        """
        # Try 1: Streamlit secrets (local)
        try:
            if hasattr(st, 'secrets') and 'firebase' in st.secrets:
                return st.secrets
        except:
            pass
        
        # Try 2: Render Secret Files
        secret_file_path = '/etc/secrets/secrets.toml'
        if os.path.exists(secret_file_path):
            try:
                with open(secret_file_path, 'r') as f:
                    secrets = toml.load(f)
                    return secrets
            except Exception as e:
                st.error(f"Could not read Secret File: {e}")
        
        raise ValueError("Could not find Firebase credentials")

    
    def _initialize_client(self):
        """Initialize Pyrebase for client-side operations"""
        try:
            secrets = self._load_secrets()
            
            firebase_config = {
                "apiKey": secrets["firebase"]["api_key"],
                "authDomain": secrets["firebase"]["auth_domain"],
                "databaseURL": secrets["firebase"]["database_url"],
                "storageBucket": secrets["firebase"]["storage_bucket"],
                "projectId": secrets["firebase"]["project_id"]
            }
            
            self.firebase = pyrebase.initialize_app(firebase_config)
            self.auth = self.firebase.auth()
            
        except Exception as e:
            st.error(f"Firebase client initialization failed: {e}")
            raise
    
    def _initialize_admin(self):
        """Initialize Firebase Admin SDK for server-side operations"""
        try:
            if not firebase_admin._apps:
                secrets = self._load_secrets()
                
                cred_dict = {
                    "type": secrets["firebase_admin"]["type"],
                    "project_id": secrets["firebase_admin"]["project_id"],
                    "private_key_id": secrets["firebase_admin"]["private_key_id"],
                    "private_key": secrets["firebase_admin"]["private_key"].replace('\\n', '\n'),
                    "client_email": secrets["firebase_admin"]["client_email"],
                    "client_id": secrets["firebase_admin"]["client_id"],
                    "auth_uri": secrets["firebase_admin"]["auth_uri"],
                    "token_uri": secrets["firebase_admin"]["token_uri"],
                    "auth_provider_x509_cert_url": secrets["firebase_admin"]["auth_provider_x509_cert_url"],
                    "client_x509_cert_url": secrets["firebase_admin"]["client_x509_cert_url"]
                }
                
                cred = credentials.Certificate(cred_dict)
                firebase_admin.initialize_app(cred)
            
            self.admin_initialized = True
            
        except Exception as e:
            st.warning(f"Firebase Admin SDK not initialized: {e}")
            self.admin_initialized = False
    
    def sign_up(
        self, 
        email: str, 
        password: str, 
        role: str,
        reid: Optional[str] = None
    ) -> Tuple[bool, Optional[str], Optional[Dict]]:
        """
        Register new user with email verification
        
        Args:
            email: User's email (becomes username)
            password: Password
            role: 'company' or 'regulator'
            reid: REId for the network (required for company users)
            
        Returns:
            (success, error_message, user_data)
        """
        try:
            # Validate inputs
            if role == 'company' and not reid:
                return False, "REId is required for company users", None
            
            if role not in ('company', 'regulator'):
                return False, "Invalid role. Must be 'company' or 'regulator'", None
            
            # Create user in Firebase Auth
            user = self.auth.create_user_with_email_and_password(email, password)
            
            # Send email verification
            self.auth.send_email_verification(user['idToken'])
            
            # Set custom claims (REId and role) if Admin SDK is initialized
            if self.admin_initialized:
                uid = user['localId']
                claims = {'role': role}
                if role == 'company' and reid:
                    claims['reid'] = reid
                admin_auth.set_custom_user_claims(uid, claims)
            
            return True, None, user
            
        except requests.exceptions.HTTPError as e:
            error_json = e.args[0]
            error_data = json.loads(error_json.response.text)
            error_message = error_data.get('error', {}).get('message', 'Unknown error')
            
            # Translate Firebase error messages
            if error_message == 'EMAIL_EXISTS':
                return False, "This email is already registered", None
            elif error_message == 'WEAK_PASSWORD':
                return False, "Password is too weak (minimum 6 characters required)", None
            elif error_message == 'INVALID_EMAIL':
                return False, "Invalid email address", None
            else:
                return False, f"Registration failed: {error_message}", None
                
        except Exception as e:
            return False, f"Unexpected error: {str(e)}", None
    
    def sign_in(self, email: str, password: str) -> Tuple[bool, Optional[str], Optional[Dict]]:
        """
        Log in user
        
        Args:
            email: Email
            password: Password
            
        Returns:
            (success, error_message, user_data)
        """
        try:
            user = self.auth.sign_in_with_email_and_password(email, password)
            
            # Get account info to check email verification
            account_info = self.auth.get_account_info(user['idToken'])
            user_info = account_info['users'][0]
            
            # Add emailVerified to user dict
            user['emailVerified'] = user_info.get('emailVerified', False)
            
            return True, None, user
            
        except requests.exceptions.HTTPError as e:
            error_json = e.args[0]
            error_data = json.loads(error_json.response.text)
            error_message = error_data.get('error', {}).get('message', 'Unknown error')
            
            if error_message == 'EMAIL_NOT_FOUND':
                return False, "Email address not found", None
            elif error_message == 'INVALID_PASSWORD':
                return False, "Incorrect password", None
            elif error_message == 'INVALID_LOGIN_CREDENTIALS':
                return False, "Invalid email or password", None
            elif error_message == 'USER_DISABLED':
                return False, "Account is disabled", None
            else:
                return False, f"Login failed: {error_message}", None
                
        except Exception as e:
            return False, f"Unexpected error: {str(e)}", None
    
    def sign_out(self) -> None:
        """Sign out current user by clearing session state"""
        keys_to_clear = [
            'auth_user',
            'auth_token', 
            'auth_email',
            'auth_role',
            'auth_reid',
            'auth_uid',
        ]
        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]
    
    def send_password_reset_email(self, email: str) -> Tuple[bool, Optional[str]]:
        """
        Send password reset link to email
        
        Args:
            email: Email address
            
        Returns:
            (success, error_message)
        """
        try:
            self.auth.send_password_reset_email(email)
            return True, None
            
        except requests.exceptions.HTTPError as e:
            error_json = e.args[0]
            error_data = json.loads(error_json.response.text)
            error_message = error_data.get('error', {}).get('message', 'Unknown error')
            
            if error_message == 'EMAIL_NOT_FOUND':
                return False, "Email address not found"
            else:
                return False, f"Could not send email: {error_message}"
                
        except Exception as e:
            return False, f"Unexpected error: {str(e)}"
    
    def resend_verification_email(self, id_token: str) -> Tuple[bool, Optional[str]]:
        """
        Resend verification link
        
        Args:
            id_token: User's ID token
            
        Returns:
            (success, error_message)
        """
        try:
            self.auth.send_email_verification(id_token)
            return True, None
            
        except Exception as e:
            return False, f"Could not send verification email: {str(e)}"
    
    def get_user_claims(self, id_token: str) -> Optional[Dict]:
        """
        Get custom claims from ID token
        
        Args:
            id_token: Firebase ID token
            
        Returns:
            Dict with claims (reid, role) or None
        """
        try:
            if not self.admin_initialized:
                return None
            
            # Verify token and get claims
            decoded_token = admin_auth.verify_id_token(id_token)
            
            return {
                'uid': decoded_token.get('uid'),
                'email': decoded_token.get('email'),
                'reid': decoded_token.get('reid'),
                'role': decoded_token.get('role', 'company'),
            }
            
        except Exception as e:
            st.error(f"Could not get claims: {e}")
            return None
    
    def update_user_reid(self, uid: str, new_reid: str) -> Tuple[bool, Optional[str]]:
        """
        Update REId for a user (admin function)
        
        Args:
            uid: User ID
            new_reid: New REId
            
        Returns:
            (success, error_message)
        """
        try:
            if not self.admin_initialized:
                return False, "Admin SDK not initialized"
            
            # Get existing claims first
            user = admin_auth.get_user(uid)
            existing_claims = user.custom_claims or {}
            
            # Update with new REId
            existing_claims['reid'] = new_reid
            admin_auth.set_custom_user_claims(uid, existing_claims)
            return True, None
            
        except Exception as e:
            return False, f"Could not update REId: {str(e)}"
    
    def update_user_role(self, uid: str, new_role: str) -> Tuple[bool, Optional[str]]:
        """
        Update role for a user (admin function)
        
        Args:
            uid: User ID
            new_role: New role ('company' or 'regulator')
            
        Returns:
            (success, error_message)
        """
        try:
            if not self.admin_initialized:
                return False, "Admin SDK not initialized"
            
            if new_role not in ('company', 'regulator'):
                return False, "Invalid role"
            
            # Get existing claims first
            user = admin_auth.get_user(uid)
            existing_claims = user.custom_claims or {}
            
            # Update role
            existing_claims['role'] = new_role
            admin_auth.set_custom_user_claims(uid, existing_claims)
            return True, None
            
        except Exception as e:
            return False, f"Could not update role: {str(e)}"


def initialize_firebase_auth() -> FirebaseAuthManager:
    """
    Initialize Firebase Auth Manager (singleton pattern)
    
    Returns:
        FirebaseAuthManager instance
    """
    if 'firebase_auth' not in st.session_state:
        st.session_state.firebase_auth = FirebaseAuthManager()
    
    return st.session_state.firebase_auth


def is_user_logged_in() -> bool:
    """Check if user is logged in"""
    return st.session_state.get('auth_user') is not None


def get_current_user() -> Optional[Dict]:
    """Get current logged in user data"""
    return st.session_state.get('auth_user')


def get_current_user_role() -> Optional[str]:
    """Get current user's role"""
    return st.session_state.get('auth_role')


def get_current_user_reid() -> Optional[str]:
    """Get current user's REId (for company users)"""
    return st.session_state.get('auth_reid')


def is_dev_mode() -> bool:
    """
    Check if dev mode is enabled (skip auth).
    
    Set in .streamlit/secrets.toml:
    [dev]
    skip_auth = true
    """
    try:
        return st.secrets.get('dev', {}).get('skip_auth', False)
    except:
        return False
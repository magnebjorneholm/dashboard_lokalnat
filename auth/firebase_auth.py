"""
auth/firebase_auth.py
Firebase Authentication module för Streamlit app

Hanterar:
- User registration med email verification
- Login/logout
- Password reset
- Custom claims (DMU, role)

Använder:
- Pyrebase4 för client-side auth
- firebase-admin för server-side operations (custom claims)
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
    """Manager för Firebase Authentication operations"""
    
    def __init__(self):
        """Initialiserar Firebase från Streamlit secrets"""
        self.firebase = None
        self.auth = None
        self.admin_initialized = False
        
        self._initialize_client()
        self._initialize_admin()
    
    def _load_secrets(self) -> Dict:
        """
        Laddar secrets från Streamlit secrets (lokalt) eller Secret Files (Render)
        
        Försöker i ordning:
        1. Streamlit secrets (st.secrets) - lokalt
        2. /etc/secrets/secrets.toml - Render Secret Files
        
        Returns:
            Dict med secrets
        """
        # Försök 1: Streamlit secrets (lokalt)
        try:
            if hasattr(st, 'secrets') and 'firebase' in st.secrets:
                return st.secrets
        except:
            pass
        
        # Försök 2: Render Secret Files
        secret_file_path = '/etc/secrets/secrets.toml'
        if os.path.exists(secret_file_path):
            try:
                with open(secret_file_path, 'r') as f:
                    secrets = toml.load(f)
                    return secrets
            except Exception as e:
                st.error(f"Kunde inte läsa Secret File: {e}")
        
        raise ValueError("Kunde inte hitta Firebase credentials")

    
    def _initialize_client(self):
        """Initialiserar Pyrebase för client-side operationss"""
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
        """Initialiserar Firebase Admin SDK för server-side operations"""
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
    
    def sign_up(self, email: str, password: str, dmu: int, reid: str = None) -> Tuple[bool, Optional[str], Optional[Dict]]:
        """
        Registrerar ny användare med email verification
        
        Args:
            email: Användarens email (blir username)
            password: Lösenord
            dmu: DMU-nummer för företaget
            reid: REId för nätverket (optional, för framtida användning)
            
        Returns:
            (success, error_message, user_data)
        """
        try:
            # Skapa användare i Firebase Auth
            user = self.auth.create_user_with_email_and_password(email, password)
            
            # Skicka email verification
            self.auth.send_email_verification(user['idToken'])
            
            # Sätt custom claims (DMU, REId och role) om Admin SDK är initialiserat
            if self.admin_initialized:
                uid = user['localId']
                claims = {
                    'dmu': dmu,
                    'role': 'company'
                }
                if reid:
                    claims['reid'] = reid
                admin_auth.set_custom_user_claims(uid, claims)
            
            return True, None, user
            
        except requests.exceptions.HTTPError as e:
            error_json = e.args[0]
            error_data = json.loads(error_json.response.text)
            error_message = error_data.get('error', {}).get('message', 'Unknown error')
            
            # Översätt Firebase-felmeddelanden
            if error_message == 'EMAIL_EXISTS':
                return False, "Email-adressen är redan registrerad", None
            elif error_message == 'WEAK_PASSWORD':
                return False, "Lösenordet är för svagt (minst 6 tecken krävs)", None
            elif error_message == 'INVALID_EMAIL':
                return False, "Ogiltig email-adress", None
            else:
                return False, f"Registrering misslyckades: {error_message}", None
                
        except Exception as e:
            return False, f"Oväntat fel: {str(e)}", None
    
    def sign_in(self, email: str, password: str) -> Tuple[bool, Optional[str], Optional[Dict]]:
        """
        Loggar in användare
        
        Args:
            email: Email
            password: Lösenord
            
        Returns:
            (success, error_message, user_data)
        """
        try:
            user = self.auth.sign_in_with_email_and_password(email, password)
            
            # Hämta account info för att kolla email verification
            account_info = self.auth.get_account_info(user['idToken'])
            user_info = account_info['users'][0]
            
            # Lägg till emailVerified i user dict
            user['emailVerified'] = user_info.get('emailVerified', False)
            
            return True, None, user
            
        except requests.exceptions.HTTPError as e:
            error_json = e.args[0]
            error_data = json.loads(error_json.response.text)
            error_message = error_data.get('error', {}).get('message', 'Unknown error')
            
            if error_message == 'EMAIL_NOT_FOUND':
                return False, "Email-adressen finns inte registrerad", None
            elif error_message == 'INVALID_PASSWORD':
                return False, "Felaktigt lösenord", None
            elif error_message == 'USER_DISABLED':
                return False, "Kontot är inaktiverat", None
            else:
                return False, f"Inloggning misslyckades: {error_message}", None
                
        except Exception as e:
            return False, f"Oväntat fel: {str(e)}", None
    
    def send_password_reset_email(self, email: str) -> Tuple[bool, Optional[str]]:
        """
        Skickar lösenordsåterställningslänk till email
        
        Args:
            email: Email-adress
            
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
                return False, "Email-adressen finns inte registrerad"
            else:
                return False, f"Kunde inte skicka email: {error_message}"
                
        except Exception as e:
            return False, f"Oväntat fel: {str(e)}"
    
    def resend_verification_email(self, id_token: str) -> Tuple[bool, Optional[str]]:
        """
        Skickar ny verifieringslänk
        
        Args:
            id_token: Användarens ID token
            
        Returns:
            (success, error_message)
        """
        try:
            self.auth.send_email_verification(id_token)
            return True, None
            
        except Exception as e:
            return False, f"Kunde inte skicka verifieringsemail: {str(e)}"
    
    def get_user_claims(self, id_token: str) -> Optional[Dict]:
        """
        Hämtar custom claims från ID token
        
        Args:
            id_token: Firebase ID token
            
        Returns:
            Dict med claims (dmu, reid, role) eller None
        """
        try:
            if not self.admin_initialized:
                return None
            
            # Verifiera token och hämta claims
            decoded_token = admin_auth.verify_id_token(id_token)
            
            return {
                'uid': decoded_token.get('uid'),
                'email': decoded_token.get('email'),
                'dmu': decoded_token.get('dmu'),
                'reid': decoded_token.get('reid'),
                'role': decoded_token.get('role')
            }
            
        except Exception as e:
            st.error(f"Kunde inte hämta claims: {e}")
            return None
    
    def update_user_dmu(self, uid: str, new_dmu: int) -> Tuple[bool, Optional[str]]:
        """
        Uppdaterar DMU för en användare (admin-funktion)
        
        Args:
            uid: User ID
            new_dmu: Nytt DMU-nummer
            
        Returns:
            (success, error_message)
        """
        try:
            if not self.admin_initialized:
                return False, "Admin SDK inte initialiserat"
            
            admin_auth.set_custom_user_claims(uid, {'dmu': new_dmu, 'role': 'company'})
            return True, None
            
        except Exception as e:
            return False, f"Kunde inte uppdatera DMU: {str(e)}"


def initialize_firebase_auth() -> FirebaseAuthManager:
    """
    Initialiserar Firebase Auth Manager (singleton pattern)
    
    Returns:
        FirebaseAuthManager instance
    """
    if 'firebase_auth' not in st.session_state:
        st.session_state.firebase_auth = FirebaseAuthManager()
    
    return st.session_state.firebase_auth
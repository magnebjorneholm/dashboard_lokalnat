"""
Login/Registration Page

Handles user authentication:
- Login with email/password
- Registration with role selection
- Company users select REId from dropdown
- Regulator users don't have fixed REId
"""

import streamlit as st
import pandas as pd
import base64
from pathlib import Path
from typing import List, Tuple, Optional
from frontend.utils.state_manager import set_user_reid

from auth.firebase_auth import (
    initialize_firebase_auth,
    is_user_logged_in,
    is_dev_mode,
)
from auth.cookie_session import set_auth_cookie


# =============================================================================
# STYLING
# =============================================================================

def apply_login_background():
    """Apply background image to login page."""
    image_path = Path("login_pic.jpg")
    
    if not image_path.exists():
        # Fallback: try other extensions
        for ext in [".png", ".jpeg"]:
            alt_path = Path(f"login_pic{ext}")
            if alt_path.exists():
                image_path = alt_path
                break
    
    if image_path.exists():
        with open(image_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode()
        
        st.markdown(
            f"""
            <style>
            [data-testid="stAppViewContainer"] {{
                background-image: url("data:image/jpeg;base64,{encoded}");
                background-size: cover;
                background-position: center;
                background-repeat: no-repeat;
                background-attachment: fixed;
            }}
            
            [data-testid="stHeader"] {{
                background: transparent;
            }}
            
            /* Semi-transparent overlay with blur for better readability */
            [data-testid="stAppViewContainer"]::before {{
                content: "";
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(255, 255, 255, 0.75);
                backdrop-filter: blur(8px);
                -webkit-backdrop-filter: blur(8px);
                z-index: 0;
            }}
            
            /* Ensure content is above overlay */
            [data-testid="stAppViewContainer"] > div {{
                position: relative;
                z-index: 1;
            }}
            
            /* Style the main content area */
            .main .block-container {{
                background: rgba(255, 255, 255, 0.6);
                backdrop-filter: blur(12px);
                -webkit-backdrop-filter: blur(12px);
                border-radius: 16px;
                padding: 2rem;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.12);
                border: 1px solid rgba(255, 255, 255, 0.3);
                max-width: 500px;
                margin: 2rem auto;
            }}
            
            /* Subtle text enhancement for title */
            h1 {{
                text-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
            }}
            </style>
            """,
            unsafe_allow_html=True
        )


# Apply background
apply_login_background()


# =============================================================================
# DATA LOADING
# =============================================================================

@st.cache_data
def load_company_list() -> List[Tuple[str, str, str]]:
    """
    Load list of companies for REId dropdown.
    
    Returns:
        List of tuples: (display_name, reid, company_name)
        Display format: "Company Name (REL00001)"
    """
    # Search paths for Data_modeller.xlsx
    search_paths = [
        Path("Data_modeller.xlsx"),
        Path("data/Data_modeller.xlsx"),
        Path("/mnt/project/Data_modeller.xlsx"),
    ]
    
    data_file = None
    for path in search_paths:
        if path.exists():
            data_file = path
            break
    
    if data_file is None:
        st.error("Could not find Data_modeller.xlsx")
        return []
    
    try:
        # Try different sheet names
        df = None
        for sheet in ["Körning", "Sheet1", 0]:
            try:
                df = pd.read_excel(data_file, sheet_name=sheet, engine="openpyxl")
                break
            except:
                continue
        
        if df is None:
            return []
        
        # Extract REId and company name
        companies = []
        for _, row in df.iterrows():
            reid = str(row.get('REId', ''))
            company = str(row.get('Företag', ''))
            if reid and company:
                display = f"{company} ({reid})"
                companies.append((display, reid, company))
        
        # Sort by company name
        companies.sort(key=lambda x: x[2].lower())
        return companies
        
    except Exception as e:
        st.error(f"Error loading company list: {e}")
        return []


# =============================================================================
# UI COMPONENTS
# =============================================================================

def render_login_form(auth_manager) -> None:
    """Render login form"""
    st.subheader("Login")
    
    with st.form("login_form"):
        email = st.text_input("Email", placeholder="your.email@company.com")
        password = st.text_input("Password", type="password")
        
        col1, col2 = st.columns([1, 1])
        with col1:
            submit = st.form_submit_button("Login", type="primary", width='stretch')
        with col2:
            forgot = st.form_submit_button("Forgot password?", width='stretch')
    
    if submit:
        if not email or not password:
            st.error("Please enter email and password")
            return
        
        with st.spinner("Logging in..."):
            success, error, user = auth_manager.sign_in(email, password)
        
        if success:
            # Check email verification
            if not user.get('emailVerified', False):
                st.warning("Please verify your email before logging in.")
                st.session_state['pending_verification_token'] = user.get('idToken')
                return
            
            # Save refresh token in cookie for session persistence
            set_auth_cookie(user.get('refreshToken', ''))

            # Get user claims
            claims = auth_manager.get_user_claims(user['idToken'])

            # Store in session state
            st.session_state['auth_user'] = user
            st.session_state['auth_token'] = user.get('idToken')
            st.session_state['auth_email'] = email
            st.session_state['auth_uid'] = user.get('localId')

            if claims:
                st.session_state['auth_role'] = claims.get('role', 'company')
                st.session_state['auth_reid'] = claims.get('reid')

                # Auto-set user_reid for company users
                if claims.get('role') == 'company' and claims.get('reid'):
                    set_user_reid(claims.get('reid'))

            st.success("Login successful!")
            st.rerun()
        else:
            st.error(error or "Login failed")
    
    if forgot:
        st.session_state['show_password_reset'] = True
        st.rerun()


def render_password_reset(auth_manager) -> None:
    """Render password reset form"""
    st.subheader("Reset Password")
    
    with st.form("reset_form"):
        email = st.text_input("Email", placeholder="your.email@company.com")
        
        col1, col2 = st.columns([1, 1])
        with col1:
            submit = st.form_submit_button("Send reset link", type="primary", width='stretch')
        with col2:
            back = st.form_submit_button("Back to login", width='stretch')
    
    if submit:
        if not email:
            st.error("Please enter your email")
            return
        
        success, error = auth_manager.send_password_reset_email(email)
        if success:
            st.success("Password reset link sent! Check your email.")
        else:
            st.error(error or "Could not send reset email")
    
    if back:
        st.session_state['show_password_reset'] = False
        st.rerun()


def render_registration_form(auth_manager) -> None:
    """Render registration form"""
    st.subheader("Create Account")
    
    # Load company list for dropdown
    companies = load_company_list()
    
    with st.form("register_form"):
        email = st.text_input("Email", placeholder="your.email@company.com")
        password = st.text_input("Password", type="password", help="Minimum 6 characters")
        password_confirm = st.text_input("Confirm password", type="password")
        
        st.markdown("---")
        
        # Role selection
        role = st.radio(
            "Account type",
            options=["company", "regulator"],
            format_func=lambda x: "Company user" if x == "company" else "Regulator",
            horizontal=True,
            help="Company users are linked to a specific network. Regulators can view all networks."
        )
        
        # REId dropdown (only for company users)
        selected_reid = None
        if role == "company":
            if companies:
                # Create options for selectbox
                options = ["-- Select your company --"] + [c[0] for c in companies]
                selected_idx = st.selectbox(
                    "Select your company",
                    range(len(options)),
                    format_func=lambda i: options[i],
                )
                
                if selected_idx > 0:
                    selected_reid = companies[selected_idx - 1][1]  # Get REId
            else:
                st.error("Could not load company list")
        
        submit = st.form_submit_button("Create account", type="primary", width='stretch')
    
    if submit:
        # Validation
        if not email or not password:
            st.error("Please fill in all required fields")
            return
        
        if password != password_confirm:
            st.error("Passwords do not match")
            return
        
        if len(password) < 6:
            st.error("Password must be at least 6 characters")
            return
        
        if role == "company" and not selected_reid:
            st.error("Please select your company")
            return
        
        with st.spinner("Creating account..."):
            success, error, user = auth_manager.sign_up(
                email=email,
                password=password,
                role=role,
                reid=selected_reid if role == "company" else None
            )
        
        if success:
            st.success(
                "Account created! Please check your email to verify your account, "
                "then return here to log in. "
                "If you don't see the email, check your junk/spam folder."
            )
        else:
            st.error(error or "Registration failed")


def render_verification_pending(auth_manager) -> None:
    """Render pending email verification notice"""
    st.warning("Your email is not yet verified.")
    st.info("Please check your inbox and click the verification link. "
            "If you don't see the email, check your junk/spam folder.")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        if st.button("Resend verification email", width='stretch'):
            token = st.session_state.get('pending_verification_token')
            if token:
                success, error = auth_manager.resend_verification_email(token)
                if success:
                    st.success("Verification email sent!")
                else:
                    st.error(error or "Could not send email")
    
    with col2:
        if st.button("Back to login", width='stretch'):
            st.session_state['pending_verification_token'] = None
            st.rerun()


# =============================================================================
# MAIN PAGE
# =============================================================================

def main():
    st.title("Regumetrica")
    
    # Check dev mode
    if is_dev_mode():
        st.info("**Dev mode enabled** - Authentication is bypassed")
        if st.button("Continue to app", type="primary"):
            st.switch_page("pages/0_case_definition.py")
        return
    
    # Check if already logged in
    if is_user_logged_in():
        st.success(f"Logged in as: {st.session_state.get('auth_email', 'Unknown')}")
        
        role = st.session_state.get('auth_role', 'company')
        reid = st.session_state.get('auth_reid')
        
        if role == 'company' and reid:
            st.info(f"Company: {reid}")
        elif role == 'regulator':
            st.info("Role: Regulator (can view all companies)")
        
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("Continue to app", type="primary", width='stretch'):
                st.switch_page("pages/0_case_definition.py")
        with col2:
            if st.button("Logout", width='stretch'):
                from auth.cookie_session import delete_auth_cookie
                delete_auth_cookie()
                auth_manager = initialize_firebase_auth()
                auth_manager.sign_out()
                st.rerun()
        return
    
    # Initialize Firebase
    try:
        auth_manager = initialize_firebase_auth()
    except Exception as e:
        st.error(f"Could not connect to authentication service: {e}")
        return
    
    # Check for pending verification
    if st.session_state.get('pending_verification_token'):
        render_verification_pending(auth_manager)
        return
    
    # Check for password reset flow
    if st.session_state.get('show_password_reset'):
        render_password_reset(auth_manager)
        return
    
    # Main login/register tabs
    tab_login, tab_register = st.tabs(["Login", "Create Account"])
    
    with tab_login:
        render_login_form(auth_manager)
    
    with tab_register:
        render_registration_form(auth_manager)


if __name__ == "__main__":
    main()
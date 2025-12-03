"""
Autentiseringskomponenter
Återanvänd från streamlit_app.py
"""

import streamlit as st
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "auth"))
from auth.firebase_auth import initialize_firebase_auth


def show_login_page():
    """Visar login-formulär med professionell design"""
    st.markdown("## Logga in")
    st.markdown("Ange din email och lösenord för att komma åt Regumetrica.")
    
    with st.form("login_form"):
        email = st.text_input("Email", placeholder="foretag@example.com")
        password = st.text_input("Lösenord", type="password")
        
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            login_button = st.form_submit_button(
                "Logga in", 
                type="primary", 
                use_container_width=True
            )
        with col2:
            register_button = st.form_submit_button(
                "Skapa konto", 
                use_container_width=True
            )
        with col3:
            reset_button = st.form_submit_button("Glömt lösenord?")
    
    if register_button:
        st.session_state.show_register = True
        st.rerun()
    
    if reset_button:
        st.session_state.show_reset_password = True
        st.rerun()
    
    if login_button:
        if not email or not password:
            st.error("Fyll i både email och lösenord")
            return
        
        with st.spinner("Loggar in..."):
            firebase_auth = initialize_firebase_auth()
            success, data, error = firebase_auth.sign_in(email, password)
        
        if success:
            st.session_state.access_granted = True
            st.session_state.current_user = data.get("localId")
            st.session_state.user_email = email
            
            custom_claims = data.get("custom_claims", {})
            st.session_state.user_role = custom_claims.get("role")
            st.session_state.user_dmu = custom_claims.get("dmu")
            st.session_state.user_reid = custom_claims.get("reid")
            
            st.success("Inloggning lyckades!")
            st.rerun()
        else:
            st.error(error)


def show_register_page():
    """Visar registreringsformulär"""
    st.markdown("## Skapa konto")
    st.markdown("Registrera dig för att få tillgång till Regumetrica.")
    
    with st.form("register_form"):
        email = st.text_input("Email", placeholder="foretag@example.com")
        password = st.text_input("Lösenord", type="password", help="Minst 6 tecken")
        password_confirm = st.text_input("Bekräfta lösenord", type="password")
        
        st.markdown("**Företagsinformation**")
        dmu = st.number_input(
            "DMU-nummer", 
            min_value=1, 
            max_value=999, 
            step=1,
            help="Ditt företags DMU-nummer från Ei"
        )
        
        col1, col2 = st.columns([1, 1])
        with col1:
            submit = st.form_submit_button(
                "Skapa konto", 
                type="primary", 
                use_container_width=True
            )
        with col2:
            back = st.form_submit_button(
                "Tillbaka", 
                use_container_width=True
            )
    
    if back:
        st.session_state.show_register = False
        st.rerun()
    
    if submit:
        if not email or not password:
            st.error("Fyll i alla obligatoriska fält")
            return
        
        if len(password) < 6:
            st.error("Lösenordet måste vara minst 6 tecken")
            return
        
        if password != password_confirm:
            st.error("Lösenorden matchar inte")
            return
        
        with st.spinner("Skapar konto..."):
            firebase_auth = initialize_firebase_auth()
            success, error = firebase_auth.create_user(
                email=email,
                password=password,
                role="company",
                dmu=int(dmu)
            )
        
        if success:
            st.success("Konto skapat! Du kan nu logga in.")
            
            if st.button("Gå till inloggning"):
                st.session_state.show_register = False
                st.rerun()
        else:
            st.error(error)


def show_reset_password_page():
    """Visar formulär för lösenordsåterställning"""
    st.markdown("## Återställ lösenord")
    st.markdown("Ange din email så skickar vi en länk för att återställa lösenordet.")
    
    with st.form("reset_password_form"):
        email = st.text_input("Email-adress", placeholder="foretag@example.com")
        
        col1, col2 = st.columns([1, 1])
        with col1:
            submit = st.form_submit_button(
                "Skicka återställningslänk", 
                type="primary", 
                use_container_width=True
            )
        with col2:
            back = st.form_submit_button("Tillbaka", use_container_width=True)
    
    if back:
        st.session_state.show_reset_password = False
        st.rerun()
    
    if submit:
        if not email:
            st.error("Ange email-adress")
            return
        
        with st.spinner("Skickar email..."):
            firebase_auth = initialize_firebase_auth()
            success, error = firebase_auth.send_password_reset_email(email)
        
        if success:
            st.success(f"Återställningslänk skickad till {email}")
            st.info("Kolla din inbox och följ instruktionerna i emailet")
            
            if st.button("Gå till inloggning"):
                st.session_state.show_reset_password = False
                st.rerun()
        else:
            st.error(error)


def render_user_info_sidebar():
    """Visar användarinfo och logout-knapp i sidebar"""
    with st.sidebar:
        st.markdown(f"**Inloggad som:** {st.session_state.user_email}")
        
        if st.session_state.user_role == "company":
            from core.data_loader_base import load_reconciliation
            
            try:
                rec = load_reconciliation()
                company_data = rec[rec['DMU'] == st.session_state.user_dmu]
                if not company_data.empty:
                    company_name = company_data.iloc[0].get('Företag', f'DMU {st.session_state.user_dmu}')
                    st.markdown(f"**Företag:** {company_name}")
            except:
                pass
            
            if st.session_state.user_reid:
                st.markdown(f"**Nätverk:** {st.session_state.user_reid}")
            st.markdown(f"**DMU:** {st.session_state.user_dmu}")
        
        st.markdown("---")
        
        if st.button("Logga ut", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
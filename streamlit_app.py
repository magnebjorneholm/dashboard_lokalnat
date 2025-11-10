"""
streamlit_app.py
Huvudfil för Streamlit-appen med Firebase Authentication

Rollbaserad access:
- company: Lokalnätföretag (filtreras per DMU)
- regulator: Energimarknadsinspektionen (tillgång till allt)
"""

import streamlit as st
from pathlib import Path
import sys

# Lägg till auth-mappen i Python path
sys.path.insert(0, str(Path(__file__).parent / "auth"))

from auth.firebase_auth import initialize_firebase_auth
from core.data_loader_base import load_reconciliation


# === SESSION STATE INITIALISERING ===
def initialize_session_state():
    """Initialiserar session state variabler"""
    if "access_granted" not in st.session_state:
        st.session_state.access_granted = False
    if "current_user" not in st.session_state:
        st.session_state.current_user = None
    if "user_role" not in st.session_state:
        st.session_state.user_role = None
    if "user_dmu" not in st.session_state:
        st.session_state.user_dmu = None
    if "user_reid" not in st.session_state:
        st.session_state.user_reid = None
    if "user_email" not in st.session_state:
        st.session_state.user_email = None
    if "show_register" not in st.session_state:
        st.session_state.show_register = False
    if "show_reset_password" not in st.session_state:
        st.session_state.show_reset_password = False


initialize_session_state()


# === HELPER FUNCTIONS ===
def get_company_name_from_dmu(dmu: int) -> str:
    """
    Hämtar företagsnamn från DMU
    
    Args:
        dmu: DMU-nummer
        
    Returns:
        Företagsnamn eller "DMU {dmu}"
    """
    try:
        rec = load_reconciliation()
        if rec.empty:
            return f"DMU {dmu}"
        
        company_data = rec[rec['DMU'] == dmu]
        if company_data.empty:
            return f"DMU {dmu}"
        
        return company_data.iloc[0].get('Företag', f"DMU {dmu}")
    
    except Exception:
        return f"DMU {dmu}"


# === LOGIN-SIDA ===
def show_login_page():
    """Visar login-formulär"""
    st.markdown("## Logga in")
    st.markdown("Ange din email och lösenord för att komma åt systemet.")
    
    with st.form("login_form"):
        email = st.text_input("Email", placeholder="foretag@example.com")
        password = st.text_input("Lösenord", type="password")
        
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            login_button = st.form_submit_button("Logga in", type="primary", use_container_width=True)
        with col2:
            register_button = st.form_submit_button("Skapa konto", use_container_width=True)
        with col3:
            reset_button = st.form_submit_button("Glömt lösenord?", use_container_width=True)
    
    if login_button:
        if not email or not password:
            st.error("Ange både email och lösenord")
            return
        
        with st.spinner("Loggar in..."):
            firebase_auth = initialize_firebase_auth()
            success, error, user = firebase_auth.sign_in(email, password)
        
        if not success:
            st.error(error)
            return
        
        # Kolla email verification
        if not user['emailVerified']:
            st.warning("⚠️ Din email är inte verifierad")
            st.info("Kolla din inbox för verifieringslänk")
            
            if st.button("Skicka ny verifieringslänk"):
                success, error = firebase_auth.resend_verification_email(user['idToken'])
                if success:
                    st.success("Ny verifieringslänk skickad!")
                else:
                    st.error(error)
            
            st.stop()
        
        # Hämta claims (DMU och role)
        claims = firebase_auth.get_user_claims(user['idToken'])
        
        if not claims:
            st.error("Kunde inte hämta användarinformation. Kontakta administratör.")
            st.stop()
        
        # Spara i session state (samma struktur som tidigare!)
        st.session_state.access_granted = True
        st.session_state.current_user = email
        st.session_state.user_email = email
        st.session_state.user_role = claims.get('role', 'company')
        st.session_state.user_dmu = claims.get('dmu')
        st.session_state.user_reid = claims.get('reid')
        
        # Visa välkomstmeddelande
        if st.session_state.user_role == 'company':
            company_name = get_company_name_from_dmu(st.session_state.user_dmu)
            welcome_msg = f"✅ Välkommen {company_name}!"
            if st.session_state.user_reid:
                welcome_msg += f" ({st.session_state.user_reid})"
            st.success(welcome_msg)
        else:
            st.success(f"✅ Välkommen {email}!")
        
        st.rerun()
    
    if register_button:
        st.session_state.show_register = True
        st.rerun()
    
    if reset_button:
        st.session_state.show_reset_password = True
        st.rerun()


# === REGISTRERINGS-SIDA ===
def show_register_page():
    """Visar registreringsformulär"""
    st.markdown("## Skapa nytt konto")
    st.markdown("Registrera ditt företag för att få tillgång till systemet.")
    
    with st.form("register_form"):
        email = st.text_input(
            "Email-adress",
            placeholder="foretag@example.com",
            help="Denna email används som användarnamn"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            password = st.text_input("Lösenord", type="password", help="Minst 6 tecken")
        with col2:
            password_confirm = st.text_input("Bekräfta lösenord", type="password")
        
        rec = load_reconciliation()
        if not rec.empty:
            local_nets = rec[rec['REId'].astype(str).str.startswith('REL', na=False)].copy()
            local_nets['display_name'] = local_nets.apply(
                lambda row: f"{row['Företag']} ({row['REId']})", 
                axis=1
            )
            local_nets = local_nets.sort_values('Företag')
            
            company_options = {row['display_name']: (row['REId'], row['DMU']) 
                             for _, row in local_nets.iterrows()}
            
            selected_company = st.selectbox(
                "Välj ditt företag",
                options=list(company_options.keys()),
                help="Välj det lokalnätsföretag du representerar"
            )
            
            reid, dmu = company_options[selected_company]
        else:
            st.error("Kunde inte ladda företagslista")
            reid = None
            dmu = None
        
        st.info("📧 Efter registrering skickas en verifieringslänk till din email")
        
        col1, col2 = st.columns([1, 1])
        with col1:
            submit = st.form_submit_button("Registrera", type="primary", use_container_width=True)
        with col2:
            back = st.form_submit_button("Tillbaka", use_container_width=True)
    
    if back:
        st.session_state.show_register = False
        st.rerun()
    
    if submit:
        # Validering
        if not email or not password:
            st.error("Email och lösenord krävs")
            return
        
        if password != password_confirm:
            st.error("Lösenorden matchar inte")
            return
        
        if len(password) < 6:
            st.error("Lösenordet måste vara minst 6 tecken")
            return
        
        if reid is None or dmu is None:
            st.error("Kunde inte hämta företagsinformation. Försök igen.")
            return
        
        # Registrera användare
        with st.spinner("Skapar konto..."):
            firebase_auth = initialize_firebase_auth()
            success, error, user = firebase_auth.sign_up(email, password, dmu, reid)
        
        if not success:
            st.error(error)
            return
        
        # Visa framgångsmeddelande
        company_name = get_company_name_from_dmu(dmu)
        st.success(f"✅ Konto skapat för {company_name}!")
        st.info(f"📧 En verifieringslänk har skickats till {email}")
        st.markdown(f"**Ditt nätverk:** {reid}")
        st.markdown("Kolla din inbox och klicka på länken för att verifiera ditt konto.")
        
        if st.button("Gå till inloggning"):
            st.session_state.show_register = False
            st.rerun()


# === LÖSENORDSÅTERSTÄLLNING ===
def show_reset_password_page():
    """Visar formulär för lösenordsåterställning"""
    st.markdown("## Återställ lösenord")
    st.markdown("Ange din email så skickar vi en länk för att återställa lösenordet.")
    
    with st.form("reset_password_form"):
        email = st.text_input("Email-adress", placeholder="foretag@example.com")
        
        col1, col2 = st.columns([1, 1])
        with col1:
            submit = st.form_submit_button("Skicka återställningslänk", type="primary", use_container_width=True)
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
            st.success(f"📧 Återställningslänk skickad till {email}")
            st.info("Kolla din inbox och följ instruktionerna i emailet")
            
            if st.button("Gå till inloggning"):
                st.session_state.show_reset_password = False
                st.rerun()
        else:
            st.error(error)


# === MAIN LOGIC ===
if not st.session_state.access_granted:
    # Visa rätt sida baserat på state
    if st.session_state.show_register:
        show_register_page()
    elif st.session_state.show_reset_password:
        show_reset_password_page()
    else:
        show_login_page()
    
    st.stop()


# === INLOGGAD - VISA SIDOR ===

# Sidebar med logout
with st.sidebar:
    st.markdown(f"**Inloggad som:** {st.session_state.user_email}")
    
    if st.session_state.user_role == "company":
        company_name = get_company_name_from_dmu(st.session_state.user_dmu)
        st.markdown(f"**Företag:** {company_name}")
        if st.session_state.user_reid:
            st.markdown(f"**Nätverk:** {st.session_state.user_reid}")
        st.markdown(f"**DMU:** {st.session_state.user_dmu}")
    
    st.markdown("---")
    
    if st.button("🚪 Logga ut", use_container_width=True):
        # Rensa session state
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()


# Definiera sidor baserat på roll
if st.session_state.user_role == "company":
    pages = [
        st.Page("pages/foretag/foretag_intaktsram.py", title="IR-dekomposition"),
    ]

else:
    st.error("Okänd användarroll. Kontakta administratör.")
    st.stop()

# Kör navigation
pg = st.navigation(pages)
pg.run()
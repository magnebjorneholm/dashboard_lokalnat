import streamlit as st
from pathlib import Path

# === Rollbaserad autentisering ===
if "access_granted" not in st.session_state:
    st.session_state.access_granted = False
if "current_user" not in st.session_state:
    st.session_state.current_user = None
if "user_role" not in st.session_state:
    st.session_state.user_role = None
if "user_dmu" not in st.session_state:
    st.session_state.user_dmu = None

def get_user_role_and_dmu(username):
    """Bestämmer användarroll och DMU baserat på username"""
    regulator_users = st.secrets.get("regulator_users", {})
    company_users = st.secrets.get("company_users", {})
    
    if username.lower() in regulator_users:
        return "regulator", None
    elif username.lower() in company_users:
        user_info = company_users[username.lower()]
        # AttrDict access för Streamlit secrets
        if hasattr(user_info, 'dmu'):
            return "company", user_info.dmu
        else:
            return "company", None
    return None, None

# === LOGIN-SIDA ===
if not st.session_state.access_granted:
    st.title("Logga in")
    st.markdown("Ange din organisations användarnamn och lösenord för att komma åt systemet.")
    
    col1, col2 = st.columns(2)
    with col1:
        username = st.text_input("Användarnamn")
    with col2:
        password = st.text_input("Lösenord", type="password")
    
    if st.button("Logga in", type="primary"):
        if username and password:
            regulator_users = st.secrets.get("regulator_users", {})
            company_users = st.secrets.get("company_users", {})
            
            user_role, user_dmu = get_user_role_and_dmu(username)
            
            if user_role == "regulator":
                if regulator_users[username.lower()] == password:
                    st.session_state.access_granted = True
                    st.session_state.current_user = username.lower()
                    st.session_state.user_role = "regulator"
                    st.session_state.user_dmu = None
                    st.success(f"Välkommen {username} (Regulator)!")
                    st.rerun()
                else:
                    st.error("Fel lösenord")
                    
            elif user_role == "company":
                user_info = company_users[username.lower()]
                expected_password = user_info.password if hasattr(user_info, 'password') else str(user_info)
                
                if expected_password == password:
                    st.session_state.access_granted = True
                    st.session_state.current_user = username.lower()
                    st.session_state.user_role = "company"
                    st.session_state.user_dmu = user_dmu  # Sparar DMU-värdet här
                    st.success(f"Välkommen {username} (Företag - DMU {user_dmu})!")
                    st.rerun()
                else:
                    st.error("Fel lösenord")
            else:
                st.error("Användarnamnet finns inte")
        else:
            st.warning("Ange både användarnamn och lösenord")
    
    st.stop()

# === NAVIGATION (endast när inloggad) ===
if st.session_state.user_role == "regulator":
    pages = [
        st.Page("pages/hem_regulator.py", title="Hem"),
        st.Page("pages/regulator/regulator_effektivitet.py", title="DEA och påverkbara kostnader"),
        st.Page("pages/kapitalbas.py", title="Kapitalbas"),
        st.Page("pages/kapitalbas_beräkningskedja.py", title="Beräkningskedja"),
        st.Page("pages/ir_dekomposition.py", title="IR-dekomposition")
    ]
    
elif st.session_state.user_role == "company":
    pages = [
    st.Page("pages/hem_foretag.py", title="Hem"),
    st.Page("pages/foretag/foretag_intaktsram.py", title="Intäktsram"),
    st.Page("pages/foretag/foretag_berakningskedja.py", title="Beräkningskedja"),
    st.Page("pages/foretag/foretag_effektivitet.py", title="DEA och påverkbara kostnader")
    ]

else:
    st.error("Okänd användarroll. Kontakta administratör.")
    st.stop()

# Kör navigation
pg = st.navigation(pages)

# Kör den valda sidan
pg.run()
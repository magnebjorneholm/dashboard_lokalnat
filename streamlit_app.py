import streamlit as st
import base64
from pathlib import Path
import streamlit.components.v1 as components

# === Organisationsbaserat lösenordsskydd ===
if "access_granted" not in st.session_state:
    st.session_state.access_granted = False
if "current_user" not in st.session_state:
    st.session_state.current_user = None

if not st.session_state.access_granted:
    st.title("Logga in")
    st.markdown("Ange din organisations användarnamn och lösenord för att komma åt systemet.")
    
    # Input-fält för användarnamn och lösenord
    col1, col2 = st.columns(2)
    with col1:
        username = st.text_input("Användarnamn", placeholder="t.ex. stina")
    with col2:
        password = st.text_input("Lösenord", type="password")
    
    if st.button("Logga in", type="primary"):
        if username and password:
            # Kontrollera mot secrets
            users = st.secrets.get("users", {})
            if username.lower() in users:
                if users[username.lower()] == password:
                    st.session_state.access_granted = True
                    st.session_state.current_user = username.lower()
                    st.success(f"Välkommen {username}!")
                    st.rerun()
                else:
                    st.error("Fel lösenord")
            else:
                st.error("Användarnamnet finns inte")
        else:
            st.warning("Ange både användarnamn och lösenord")
    
    # Hjälpinformation för testmiljö
    with st.expander("Testinformation"):
        st.info("Testorganisation: användarnamn='stina', lösenord='Bison'")
        st.caption("Kontakta administratören för att få tillgång med ditt organisations konto.")
    
    st.stop()

# === Visa inloggningsstatus ===
st.sidebar.success(f"Inloggad som: {st.session_state.current_user}")
if st.sidebar.button("Logga ut"):
    st.session_state.access_granted = False
    st.session_state.current_user = None
    st.rerun()

# === Ladda menybild ===
image_path = Path("images/reglering_oversikt.png")
if not image_path.exists():
    st.error("Kunde inte hitta bilden 'reglering_oversikt.png'")
    st.stop()

with open(image_path, "rb") as img_file:
    encoded_image = base64.b64encode(img_file.read()).decode()

# === Titel ===
st.title("Intäktsramsreglering – översikt")

# === Visa bild med klickbara områden ===
components.html(
    f"""
    <div style="overflow-x: auto;">
        <div style="width: 900px; margin: auto;">
            <img src="data:image/png;base64,{encoded_image}" usemap="#menu" width="900" style="border:1px solid #ccc;">
        </div>

        <map name="menu">
            <area shape="rect" coords="180,150,330,210" href="/effektiviseringskrav" alt="effektiviseringskrav">
            <area shape="rect" coords="590,87,906,138" href="/kapitalbas" alt="kapitalbas">
        </map>
    </div>
    """,
    height=700,
    scrolling=True
)
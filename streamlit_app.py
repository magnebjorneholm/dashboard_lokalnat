import streamlit as st
import base64
from pathlib import Path
import streamlit.components.v1 as components

# === Lösenordsskydd ===
if "access_granted" not in st.session_state:
    st.session_state.access_granted = False

if not st.session_state.access_granted:
    pw = st.text_input("Ange lösenord", type="password")
    if pw == st.secrets["password"]:
        st.session_state.access_granted = True
        st.rerun()
    elif pw != "":
        st.warning("Fel lösenord.")
    st.stop()

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
            <area shape="rect" coords="180,150,330,210" href="/Effektiviseringskrav" alt="Effektiviseringskrav">
            <area shape="rect" coords="590,87,906,138" href="/Kapitalbas" alt="Kapitalbas">
        </map>
    </div>
    """,
    height=700,
    scrolling=True
)


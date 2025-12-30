"""
Diagnostik för Regumetrica grafisk profil.

Kör detta script för att verifiera att styling är korrekt konfigurerad:
    streamlit run diagnostics_styling.py
"""

import streamlit as st
import os
from pathlib import Path

st.set_page_config(page_title="Regumetrica Styling Diagnostik", layout="wide")

st.title("Styling Diagnostik")

# === 1. CONFIG.TOML CHECK ===
st.header("1. Config.toml")

config_path = Path(".streamlit/config.toml")
if config_path.exists():
    with open(config_path, "r") as f:
        config_content = f.read()
    
    st.code(config_content, language="toml")
    
    # Kontrollera primaryColor
    if "primaryColor" in config_content:
        # Extrahera värdet
        for line in config_content.split("\n"):
            if "primaryColor" in line and "=" in line:
                color_value = line.split("=")[1].strip().strip('"').strip("'")
                
                if color_value.upper() == "#2563EB":
                    st.success(f"primaryColor är korrekt: {color_value}")
                else:
                    st.error(f"primaryColor är FEL: {color_value}")
                    st.info("Förväntat värde: #2563EB (Nordic Blue)")
                
                # Visa färgen
                st.markdown(
                    f'<div style="width: 100px; height: 50px; background: {color_value}; '
                    f'border-radius: 4px; border: 1px solid #ccc;"></div>',
                    unsafe_allow_html=True
                )
                st.caption(f"Aktuell primaryColor: {color_value}")
else:
    st.error("config.toml hittades inte!")
    st.info("Skapa .streamlit/config.toml med korrekt innehåll")


# === 2. STYLING.PY CHECK ===
st.header("2. Styling-modul")

styling_paths = [
    Path("frontend/common/styling.py"),
    Path("styling.py"),
]

styling_found = False
for path in styling_paths:
    if path.exists():
        st.success(f"styling.py hittad: {path}")
        styling_found = True
        break

if not styling_found:
    st.error("styling.py hittades inte!")
    st.info("Placera styling.py i frontend/common/")


# === 3. APPLY_STYLING CHECK ===
st.header("3. CSS-injektion")

try:
    from frontend.common.styling import apply_styling, COLORS, get_custom_css
    
    st.success("Import av styling-modul lyckades")
    
    # Visa färgpalett
    st.subheader("Färgpalett (COLORS dict)")
    cols = st.columns(4)
    for i, (name, hex_color) in enumerate(COLORS.items()):
        with cols[i % 4]:
            st.markdown(
                f'<div style="display: flex; align-items: center; margin: 4px 0;">'
                f'<div style="width: 24px; height: 24px; background: {hex_color}; '
                f'border-radius: 4px; border: 1px solid #ccc; margin-right: 8px;"></div>'
                f'<span style="font-size: 12px;">{name}: {hex_color}</span>'
                f'</div>',
                unsafe_allow_html=True
            )
    
    # Applicera styling
    st.subheader("Testa apply_styling()")
    if st.button("Applicera styling"):
        apply_styling()
        st.success("apply_styling() kördes!")
        st.info("Ladda om sidan (F5) för att se effekten")

except ImportError as e:
    st.error(f"Kunde inte importera styling-modul: {e}")
    st.info("Kontrollera att frontend/common/styling.py finns och har korrekt syntax")


# === 4. GOOGLE FONTS CHECK ===
st.header("4. Google Fonts")

st.markdown("""
Testa om Inter och IBM Plex Mono laddas korrekt:
""")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&display=swap');
</style>

<div style="font-family: 'Inter', sans-serif; margin: 16px 0;">
    <strong>Inter font test:</strong> The quick brown fox jumps over the lazy dog. 1234567890
</div>

<div style="font-family: 'IBM Plex Mono', monospace; margin: 16px 0;">
    <strong>IBM Plex Mono test:</strong> 1,234,567.89 | 0.0453 | REL00886
</div>
""", unsafe_allow_html=True)


# === 5. VISUAL TEST ===
st.header("5. Visuell test")

st.markdown("Dessa element bör använda Nordic Blue (#2563EB):")

col1, col2, col3 = st.columns(3)

with col1:
    st.button("Primary Button", type="primary")
    
with col2:
    st.slider("Slider test", 0, 100, 50)
    
with col3:
    st.checkbox("Checkbox test", value=True)

st.divider()

st.markdown("""
**Förväntad färg på ovanstående element:**

<div style="display: flex; gap: 16px; align-items: center;">
    <div style="width: 100px; height: 40px; background: #2563EB; border-radius: 4px; 
         display: flex; align-items: center; justify-content: center; color: white; font-weight: 500;">
        #2563EB
    </div>
    <span>Nordic Blue - detta är målsättningen</span>
</div>
""", unsafe_allow_html=True)


# === 6. CACHE CLEARING ===
st.header("6. Cache")

st.warning("""
Om färgerna fortfarande är fel efter config-uppdatering:

1. Stoppa Streamlit-servern (Ctrl+C)
2. Rensa browser-cache (Ctrl+Shift+Delete i Chrome)
3. Ta bort Streamlit-cache: `rm -rf ~/.streamlit/cache`
4. Starta om: `streamlit run streamlit_app.py`
""")


# === SAMMANFATTNING ===
st.header("Sammanfattning")

checks = {
    "config.toml finns": config_path.exists(),
    "styling.py finns": styling_found,
    "primaryColor korrekt": "#2563EB" in config_content.upper() if config_path.exists() else False,
}

all_ok = all(checks.values())

if all_ok:
    st.success("Alla grundläggande kontroller godkända!")
else:
    st.error("Några kontroller misslyckades - se detaljer ovan")

for check, status in checks.items():
    icon = "✓" if status else "✗"
    color = "green" if status else "red"
    st.markdown(f'<span style="color: {color};">{icon} {check}</span>', unsafe_allow_html=True)
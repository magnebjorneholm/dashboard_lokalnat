import streamlit as st
import pandas as pd
from pathlib import Path

if "access_granted" not in st.session_state or not st.session_state.access_granted:
    st.stop()

# Hämta företagsinformation
user_dmu = st.session_state.get('user_dmu')
user_name = st.session_state.get('current_user', 'Företag')

# Försök hämta företagsnamn från reconciliation
company_name = "Ditt företag"
if user_dmu:
    try:
        recon_path = "intaktsram/data/new_recon.csv"
        if Path(recon_path).exists():
            recon_df = pd.read_csv(recon_path)
            company_row = recon_df[recon_df['DMU'] == user_dmu]
            if not company_row.empty:
                company_name = company_row.iloc[0].get('Företag', f'DMU {user_dmu}')
    except Exception:
        company_name = f"DMU {user_dmu}" if user_dmu else "Ditt företag"

st.title(f"Välkommen, {company_name}")

if user_dmu:
    st.info(f"Du är inloggad som DMU {user_dmu}")

# Introduktion
st.markdown("""
**Företagsportalen för intäktsramsreglering**

Denna portal ger dig tillgång till analyser och data som är specifikt relevanta för ditt företag 
inom ramen för intäktsramsregleringen.
""")

# Status för företagsfunktionalitet
st.subheader("Företagsspecifika funktioner")

st.warning("**Under utveckling** - Företagsportalen utvecklas kontinuerligt med nya funktioner")

# Kommande funktioner
col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    **Planerade funktioner:**
    
    **Mitt företags prestanda**
    - Din effektivitetsposition relativt andra företag
    - Effektiviseringskrav och påverkan på påverkbara kostnader
    - Utveckling över tid
    - Detaljanalys per komponent
    """)
    
    st.markdown("""
    **Kapitalkostnadsanalys**
    - Påverkan av WACC-förändringar på ditt företag
    - Breakdown av avskrivningar och avkastning
    - Scenario-analys för olika räntelägen
    - Jämförelse med branschgenomsnitt
    """)

with col2:
    st.markdown("""
    **Branschpositionering**
    - Anonymiserad jämförelse med andra lokalnätsföretag
    - Histogram och fördelningar där ditt företag markeras
    - Quartiler och percentiler för olika nyckeltal
    - Trender inom branschen
    """)
    
    st.markdown("""
    **Export och rapportering**
    - Företagsspecifika datautdrag
    - Månadsrapporter och trendanalys
    - Export till Excel för intern vidarebearbetning
    - Anpassade dashboards för ledning
    """)

# Nuvarande tillgång via regulator-verktyg
st.markdown("---")
st.subheader("Tillgänglig funktionalitet idag")

st.info("""
**Temporär tillgång till analysverktyg**

Under utvecklingsperioden har företag begränsad tillgång till regulatorverktygen. 
Kontakta utvecklingsteamet för specifika analysönskemål eller om du behöver företagsspecifik data.
""")

# Vad företag kan förvänta sig
with st.expander("Vad kan jag förvänta mig av företagsportalen?"):
    st.markdown("""
    **Fokuserad användarupplevelse:**
    - Endast data och analyser relevanta för ditt företag
    - Förenklad navigation och tydliga insikter
    - Automatisk filtrering till dina nät och anläggningar
    
    **Benchmarking med integritet:**
    - Jämförelser med andra företag utan att avslöja specifika företagsdata
    - Anonymiserad branschstatistik
    - Positionering relativt medelvärden och kvartiler
    
    **Långsiktig planering:**
    - Scenario-analys för olika regleringsalternativ
    - Påverkan av effektiviseringskrav på din verksamhet
    - WACC-känslighetsanalys
    
    **Månadsvis rapportering:**
    - Sammanfattningar av regelförändringar som påverkar ditt företag
    - Uppdaterad branschdata och jämförelser
    - Export-funktioner för intern rapportering
    """)

# Datahantering och integritet
with st.expander("Datasäkerhet och integritet"):
    st.markdown("""
    **Säker datahantering:**
    - All företagsdata hanteras separat och säkert
    - Ingen data delas mellan olika företagsanvändare
    - Krypterad lagring och överföring
    
    **Integritetsskydd:**
    - Du ser endast din egen data och anonymiserade jämförelser
    - Ingen möjlighet att identifiera andra företag i jämförelser
    - Regelefterlevnad enligt GDPR och offentlighetslagen
    
    **Transparens:**
    - Full insyn i vilka beräkningar som ligger bakom dina resultat
    - Samma metodik som används av Energimarknadsinspektionen
    - Möjlighet att följa hela beräkningskedjan
    """)

# Timeline och utveckling
st.markdown("---")
st.subheader("Utvecklingsplan")

timeline_col1, timeline_col2 = st.columns(2)

with timeline_col1:
    st.markdown("""
    **Fas 1 (Pågående)**
    - Grundläggande företagsportal
    - Säker inloggning och datahantering
    - Företagsspecifik datafiltrering
    
    **Fas 2 (Q1 2025)**
    - Effektivitetsanalys per företag
    - WACC-påverkansanalys
    - Grundläggande branschpositionering
    """)

with timeline_col2:
    st.markdown("""
    **Fas 3 (Q2 2025)**
    - Avancerade jämförelseverkttyg
    - Månadsrapporter och trendanalys
    - Interaktiva dashboards
    
    **Fas 4 (Q3 2025)**
    - Fullständig scenario-analys
    - Avancerade exportfunktioner
    - Anpassningsbara rapporter
    """)

# Kontakt och support
st.markdown("---")
st.subheader("Kontakt och support")

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    **Utvecklingsteam:**
    - **Huvudutvecklare:** Magne Björneholm
    - **Organisation:** Energimarknadsinspektionen
    - **E-post:** [kontaktuppgifter tillkommer]
    
    **För företagsspecifika frågor:**
    - Analysönskemål och datauttag
    - Teknisk support
    - Förslag på nya funktioner
    """)

with col2:
    st.markdown("""
    **Support och feedback:**
    - **Tekniska problem:** Rapportera via utvecklingsteamet
    - **Datafel:** Kontakta omedelbart för korrigering
    - **Funktionsförslag:** Välkomna för att prioritera utveckling
    
    **Användartest:**
    - Möjlighet att delta i användarstudier
    - Tidig tillgång till nya funktioner
    - Påverka utvecklingsriktning
    """)

# Senaste nyheter
with st.expander("Senaste uppdateringar"):
    st.markdown(f"""
    **Senaste systemuppdatering:** {st.session_state.get('current_user', 'N/A')} inloggning konfigurerad
    
    **Kommande milstolpar:**
    - Företagsspecifik datafiltrering implementeras
    - Branschstatistik och jämförelser utvecklas
    - Export-funktioner för företagsrapporter
    
    **Känd problematik:**
    - Vissa äldre datauppsättningar kan innehålla luckor
    - WACC-scenarion kan variera beroende på datakälla
    - Exportformat standardiseras kontinuerligt
    """)

# Call-to-action för feedback
st.markdown("---")
st.success("""
**Hjälp oss förbättra företagsportalen!**

Din feedback är värdefull för utvecklingen. Kontakta utvecklingsteamet med:
- Vilka analyser som är viktigast för ditt företag
- Önskad rapporteringsfrekvens och format
- Integration med befintliga system
""")

# Footer med system-info
st.caption(f"""
Företagsportal version 1.0 | DMU: {user_dmu or 'N/A'} | 
Inloggning: {user_name} | Dataperiod: 2024-2027
""")

st.sidebar.markdown("---")
if st.sidebar.button("Logga ut"):
    st.session_state.access_granted = False
    st.session_state.current_user = None
    st.session_state.user_role = None
    st.session_state.user_dmu = None
    st.rerun()
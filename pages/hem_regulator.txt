import streamlit as st

if "access_granted" not in st.session_state or not st.session_state.access_granted:
    st.stop()

st.title("Intäktsramsreglering - Dashboard")
st.markdown("**Välkommen till analysverktygen för intäktsramsreglering**")

# Översikt av systemet
st.markdown("""
Detta dashboard innehåller fyra huvudmoduler för analys av intäktsramsreglering:
""")

# Modulöversikt
col1, col2 = st.columns(2)

with col1:
    st.subheader("Effektiviseringskrav")
    st.markdown("""
    - **DEA-modeller**: Data Envelopment Analysis för effektivitetsmätning
    - **SFA och PyStoned**: Stokastisk gränsanalys och färdiga körningar
    - **Jämförelseverkttyg**: Kompletterande analys och företagsspecifik data
    - **Geografiska kartor**: Visualisering av effektivitet per region
    - **Export**: Påverkbara kostnader till IR-dekomposition
    """)
    
    st.subheader("Kapitalbas")
    st.markdown("""
    - **WACC-beräkningar**: Kalkylränta från grunden med Ei:s metodik
    - **Tidsserianalys**: Utveckling av kapitalkostnader över tid
    - **Intensitetsanalys**: Kapitalkostnader per volym och kategori
    - **Export**: CAPEX-data till DEA och detaljerad kapitalkostnad till IR
    """)

with col2:
    st.subheader("IR-dekomposition")
    st.markdown("""
    - **Waterfall-analys**: Komponentvis uppbyggnad av intäktsram
    - **Scenario-hantering**: Kombinera data från olika moduler
    - **Företagsspecifik analys**: Detaljerad vy per företag/nät
    - **Export**: Kompletta scenarior för vidare analys
    """)
    
    st.subheader("Beräkningskedja")
    st.markdown("""
    - **Stegvis genomgång**: Kapitalkostnadsberäkning från grunden
    - **Interaktiv analys**: Påverka parametrar i varje steg
    - **Validering**: Jämför beräknade värden mot facit
    - **Metodikgenomgång**: Förstå hela beräkningskedjan
    """)

# Användartips
st.markdown("---")
st.subheader("Tips för användning")

with st.expander("Dataflöde mellan moduler"):
    st.markdown("""
    **Rekommenderat arbetsflöde:**
    
    1. **Kapitalbas** → Justera WACC och exportera till både DEA och IR
    2. **Effektiviseringskrav** → Kör DEA med uppdaterad CAPEX och exportera påverkbara kostnader
    3. **IR-dekomposition** → Skapa scenario med data från både kapitalbas och effektiviseringskrav
    4. **Beräkningskedja** → Fördjupa förståelsen för kapitalkostnadsberäkningar
    
    **Export-filer lagras organisationsspecifikt** och kan hämtas automatiskt mellan modulerna.
    """)

with st.expander("Vanliga arbetsuppgifter"):
    st.markdown("""
    **WACC-scenarior:**
    - Gå till Kapitalbas > Beräkna kalkylränta från grunden
    - Justera parametrar (riskfri ränta, MRP, etc.)
    - Exportera till både DEA och IR-dekomposition
    
    **Effektivitetsanalys:**
    - Använd Effektiviseringskrav > DEA för huvudanalys
    - Komplettera med SFA/PyStoned för robusthetskontroll
    - Jämför resultat mellan olika metoder
    
    **Företagsanalys:**
    - IR-dekomposition ger djupgående vy per företag
    - Kombinera med Beräkningskedja för detaljförståelse
    - Exportera företagsspecifika rapporter
    """)

# Systemstatus och information
st.markdown("---")
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Antal lokalnät (REL)", "~140", help="Aktiva lokalnät i systemet")

with col2: 
    st.metric("DMU-mappning", "Aktiv", help="Automatisk mappning mellan id_network och DMU")

with col3:
    st.metric("Datauppdatering", "2024-27", help="Regleringsperiod för nuvarande data")

# Kontaktinformation
st.markdown("---")
st.subheader("Support och utveckling")

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    **Utvecklingsteam:**
    - Magne Björneholm (Huvudutvecklare)
    - Energimarknadsinspektionen
    
    **Teknisk support:**
    - Vid tekniska problem, kontakta utvecklingsteamet
    - Loggar och felmeddelanden hjälper med felsökning
    """)

with col2:
    st.markdown("""
    **Feedback och förbättringar:**
    - Förslag på nya funktioner välkomnas
    - Rapportera buggar eller oväntade beteenden
    - Användarstudier genomförs regelbundet
    
    **Dokumentation:**
    - Metodikbeskrivningar finns i respektive modul
    - Expanderbara hjälprutor innehåller detaljerad information
    """)

# Senaste uppdateringar
with st.expander("Senaste uppdateringar och ändringar"):
    st.markdown("""
    **Version 2.0 - Rollbaserat system**
    - Separata vyer för regulatorer och företag
    - Förbättrad datahantering och export
    - Organisationsbaserad dataisolation
    
    **Tidigare uppdateringar:**
    - WACC-beräkning enligt Ei:s metodik
    - DMU-aggregering med automatisk mappning
    - Scenario-hantering mellan moduler
    - Exportfunktioner för vidare analys
    """)

st.sidebar.markdown("---")
if st.sidebar.button("Logga ut"):
    st.session_state.access_granted = False
    st.session_state.current_user = None
    st.session_state.user_role = None
    st.session_state.user_dmu = None
    st.rerun()
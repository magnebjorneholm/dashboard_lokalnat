"""
streamlit_app.py
Huvudfil för Streamlit-appen med Firebase Authentication och modulär arkitektur

Rollbaserad access:
- company: Lokalnätföretag (filtreras per DMU)
- regulator: Energimarknadsinspektionen (tillgång till allt)

Flow-baserad navigation:
1. Case Setup → Välj komponenter
2. Case Configuration → Konfigurera metoder
3. Execution → Kör beräkningar
4. Results → Visa resultat
"""

import streamlit as st
from pathlib import Path
import sys
import pandas as pd

# Lägg till auth-mappen i Python path
sys.path.insert(0, str(Path(__file__).parent / "auth"))

from auth.firebase_auth import initialize_firebase_auth
from core.data_loader_base import load_reconciliation
from core.producer_registry import build_default_registry
from core.variable_resolver import VariableResolver
from core.case_definition_manager import CaseDefinitionManager
from core.bootstrap_registry import bootstrap_registry


# === PAGE CONFIG ===
st.set_page_config(
    page_title="Regumetrica",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)


# === SESSION STATE INITIALISERING ===
def initialize_session_state():
    """Initialiserar session state variabler"""
    # Authentication state
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
    
    # Case state
    if "page" not in st.session_state:
        st.session_state.page = 'setup'
    # Case manager and case_definition (use CaseDefinitionManager to create canonical structure)
    if "producer_registry" not in st.session_state:
        # Build registry and bind actual producer callables
        registry = build_default_registry()
        try:
            registry = bootstrap_registry(registry)
        except Exception:
            # If bootstrap fails, keep registry as-is (methods may be None)
            pass
        st.session_state.producer_registry = registry

    if "case_manager" not in st.session_state:
        st.session_state.case_manager = CaseDefinitionManager(st.session_state.producer_registry)

    if "case_definition" not in st.session_state:
        # Create a default case using the CaseDefinitionManager; also keep a
        # lightweight 'selections' key for UI compatibility (the UI may still
        # rely on that temporary structure). The canonical fields are
        # 'parameters', 'modules' and 'module_configs'.
        default_case = st.session_state.case_manager.create_case("New Scenario")
        # ensure older UI code that expects 'selections' doesn't break
        default_case.setdefault('selections', {'parameters': [], 'variables': [], 'modules': []})
        default_case.setdefault('config', {})
        st.session_state.case_definition = default_case
    if "case_results" not in st.session_state:
        st.session_state.case_results = None
    # producer_registry already initialized above when creating case_manager


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
    st.markdown("Ange din email och lösenord för att komma åt Regumetrica.")
    
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
            st.warning("Din email är inte verifierad")
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
        
        # Spara i session state
        st.session_state.access_granted = True
        st.session_state.current_user = email
        st.session_state.user_email = email
        st.session_state.user_role = claims.get('role', 'company')
        st.session_state.user_dmu = claims.get('dmu')
        st.session_state.user_reid = claims.get('reid')
        
        # Visa välkomstmeddelande
        if st.session_state.user_role == 'company':
            company_name = get_company_name_from_dmu(st.session_state.user_dmu)
            welcome_msg = f"Välkommen {company_name}!"
            if st.session_state.user_reid:
                welcome_msg += f" ({st.session_state.user_reid})"
            st.success(welcome_msg)
        else:
            st.success(f"Välkommen {email}!")
        
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
    st.markdown("Registrera dig för att få tillgång till Regumetrica.")
    
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
        
        st.info("Efter registrering skickas en verifieringslänk till din email")
        
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
        st.success(f"Konto skapat för {company_name}!")
        st.info(f"En verifieringslänk har skickats till {email}")
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
            st.success(f"Återställningslänk skickad till {email}")
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


# === INLOGGAD - SIDEBAR ===
with st.sidebar:
    st.markdown("### Regumetrica")
    st.markdown("---")
    
    st.markdown(f"**Inloggad som:**")
    st.caption(st.session_state.user_email)
    
    if st.session_state.user_role == "company":
        company_name = get_company_name_from_dmu(st.session_state.user_dmu)
        st.markdown(f"**Företag:**")
        st.caption(company_name)
        if st.session_state.user_reid:
            st.markdown(f"**Nätverk:**")
            st.caption(st.session_state.user_reid)
        st.markdown(f"**DMU:**")
        st.caption(st.session_state.user_dmu)
    
    st.markdown("---")
    
    # Progress indicator
    pages_map = {
        'setup': 0,
        'config': 1,
        'execution': 2,
        'results': 3
    }
    
    current_step = pages_map.get(st.session_state.page, 0)
    
    steps = ["Setup", "Config", "Execution", "Results"]
    for i, step in enumerate(steps):
        if i < current_step:
            st.markdown(f"✓ {step}")
        elif i == current_step:
            st.markdown(f"**→ {step}**")
        else:
            st.markdown(f"○ {step}")
    
    st.markdown("---")
    
    if st.button("Logga ut", use_container_width=True):
        # Rensa session state
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()


# === HUVUDINNEHÅLL - FLOW-BASERAD NAVIGATION ===

# Import page renderers
from ui.pages.case_setup_page import render_case_setup_page
from ui.pages.case_config_page import render_case_config_page
from ui.pages.results_page import render_results_page

# Route baserat på current page
if st.session_state.page == 'setup':
    st.session_state.case_definition = render_case_setup_page(
        st.session_state.case_definition
    )

elif st.session_state.page == 'config':
    st.session_state.case_definition = render_case_config_page(
        st.session_state.case_definition
    )

elif st.session_state.page == 'execution':
    st.title("Kör beräkning")
    
    case_def = st.session_state.case_definition
    
    # Progress tracking
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        # Ladda baseline data
        status_text.text("Laddar baseline data...")
        progress_bar.progress(10)
        
        from producers.baseline.baseline_loaders import load_baseline_data
        baseline_data = load_baseline_data()
        
        # Skapa Variable Resolver
        status_text.text("Initialiserar Variable Resolver...")
        progress_bar.progress(20)
        
        resolver = VariableResolver(
            producer_registry=st.session_state.producer_registry,
            case_definition=case_def,
            baseline_data=baseline_data
        )
        
        # Hämta intäktsram (detta triggar hela dependency chain)
        status_text.text("Beräknar intäktsram...")
        progress_bar.progress(40)
        
        # 1. Visa execution plan
        st.write("### 🔍 Debug: Execution Plan")
        try:
            plan = resolver.get_execution_plan('intaktsram')
            st.write("Execution order:")
            for i, (var, prod) in enumerate(plan, 1):
                st.write(f"{i}. `{var}` via `{prod}`")
        except Exception as e:
            st.error(f"Kunde inte få execution plan: {e}")

        # 2. Testa varje variabel individuellt
        st.write("### 🔍 Debug: Variable Types")

        # Lista viktiga variabler att testa
        test_vars = [
            'wacc_components',
            'wacc', 
            'capex',
            'capex_baseline',
            'opex_paverkbara',
            'opex_opaverkbara',
            'volumes',
            'efficiency',
            'effektiviseringskrav'
        ]

        results = []
        for var_name in test_vars:
            try:
                value = resolver.get_variable(var_name)
                value_type = type(value).__name__
                
                # Extra info för DataFrames
                if isinstance(value, pd.DataFrame):
                    shape = f"{value.shape}"
                    info = f"DataFrame {shape}"
                elif isinstance(value, dict):
                    keys = list(value.keys())[:3]
                    info = f"Dict with keys: {keys}..."
                elif isinstance(value, (int, float)):
                    info = f"Value: {value:.6f}"
                else:
                    info = str(type(value))
                
                results.append({
                    'Variable': var_name,
                    'Type': value_type,
                    'Info': info,
                    'Status': '✅' if value_type in ['float', 'int', 'DataFrame', 'dict'] else '⚠️'
                })
            except Exception as e:
                results.append({
                    'Variable': var_name,
                    'Type': 'ERROR',
                    'Info': str(e)[:50],
                    'Status': '❌'
                })

        st.dataframe(pd.DataFrame(results), use_container_width=True)

        # 3. Kolla case_definition struktur
        st.write("### 🔍 Debug: Case Definition")
        st.write("**Parameters:**")
        params = st.session_state.case_definition.get('parameters', {})
        if isinstance(params, dict):
            for key, value in params.items():
                st.write(f"- `{key}`: {type(value).__name__}")
                if key == 'wacc_components' and isinstance(value, dict):
                    st.json(value)
        else:
            st.write(f"Type: {type(params)} (should be dict!)")

        st.write("**Modules:**")
        modules = st.session_state.case_definition.get('modules', {})
        if isinstance(modules, dict):
            for key, value in modules.items():
                st.write(f"- `{key}`: {value}")
        else:
            st.write(f"Type: {type(modules)}")

        # 4. Testa WACC specifikt
        st.write("### 🔍 Debug: WACC Detailed")
        try:
            # Vilken producer används för wacc?
            producer_id = resolver._determine_producer('wacc')
            st.write(f"WACC producer: `{producer_id}`")
            
            # Hämta wacc
            wacc_value = resolver.get_variable('wacc')
            st.write(f"WACC type: `{type(wacc_value).__name__}`")
            st.write(f"WACC value: `{wacc_value}`")
            
            # Kolla registry spec
            wacc_spec = resolver.registry.get_variable_spec('wacc')
            st.write(f"Expected dtype: `{wacc_spec.dtype}`")
            
        except Exception as e:
            st.error(f"WACC error: {e}")

        st.write("---")
        st.write("**Nu kan du fortsätta med intaktsram-beräkningen och se var det kraschar**")

















        intaktsram = resolver.get_variable('intaktsram')
        
        progress_bar.progress(80)
        status_text.text("Sammanställer resultat...")
        
        # Lagra resultat - spara canonical metadata (parameters/modules/module_configs)
        st.session_state.case_results = {
            'intaktsram': intaktsram,
            'metadata': {
                'case_name': case_def.get('name', 'Unnamed case'),
                'parameters': case_def.get('parameters', {}),
                'modules': case_def.get('modules', {}),
                'module_configs': case_def.get('module_configs', {}),
                'created_at': case_def.get('created_at'),
                'updated_at': case_def.get('updated_at')
            },
            'baseline_intaktsram': baseline_data.get('intaktsram_total', 0)
        }
        
        progress_bar.progress(100)
        status_text.text("Klart!")
        
        st.success("Beräkning klar!")
        
        # Automatisk navigation till resultat
        st.session_state.page = 'results'
        st.rerun()
        
    except Exception as e:
        st.error(f"Fel vid beräkning: {str(e)}")
        st.exception(e)
        
        if st.button("← Tillbaka till konfiguration"):
            st.session_state.page = 'config'
            st.rerun()

elif st.session_state.page == 'results':
    render_results_page(
        st.session_state.case_definition,
        st.session_state.case_results
    )

else:
    st.error(f"Okänd sida: {st.session_state.page}")
    if st.button("Gå till Setup"):
        st.session_state.page = 'setup'
        st.rerun()
"""
Dash Application - Intäktsramsreglering Dashboard
==================================================

ÄNDRINGAR FÖR BERÄKNINGSKEDJA:
1. Long Callbacks setup (efter Flask-Session init)
2. Route för /foretag/berakningskedja (i display_page callback)
"""

import dash
from dash import Dash, html, dcc, Input, Output, State, callback
import dash_bootstrap_components as dbc
from flask import Flask, session as flask_session
import os
from pathlib import Path
import redis
from flask_session import Session
import sys
from flask_caching import Cache

# ============== NYTT: Long Callbacks import ==============
from dash.long_callback import DiskcacheLongCallbackManager
import diskcache as dc
# =========================================================

# Hitta projektets root
DASH_DIR = Path(__file__).parent.absolute()
PROJECT_ROOT = DASH_DIR.parent.absolute()

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

print(f"DEBUG: DASH_DIR = {DASH_DIR}")
print(f"DEBUG: PROJECT_ROOT = {PROJECT_ROOT}")
print(f"DEBUG: Python path updated")

# Importera konsoliderade moduler
import auth
import components

# ============================================================================
# APP INITIALIZATION
# ============================================================================

# Flask server för mer kontroll över sessions och auth
server = Flask(__name__)

# PRODUCTION SESSION CONFIG
server.config.update(
    SECRET_KEY=os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production'),
    SESSION_TYPE='redis',
    SESSION_REDIS=redis.from_url(os.environ.get('REDIS_URL', 'redis://localhost:6379')),
    SESSION_COOKIE_SECURE=False,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=7200
)

# Initiera Flask-Session
Session(server)

# ============== NYTT: Long Callbacks Manager ==============
# Diskcache för long callbacks (tung beräkningar)
cache_dir = os.environ.get('CACHE_DIR', './.cache')
os.makedirs(cache_dir, exist_ok=True)
long_callback_cache = dc.Cache(cache_dir)
long_callback_manager = DiskcacheLongCallbackManager(long_callback_cache)
# ==========================================================

# Flask-Caching för data-loading
cache = Cache(server, config={
    'CACHE_TYPE': 'SimpleCache',
    'CACHE_DEFAULT_TIMEOUT': 3600
})

# Initiera Dash app med Bootstrap tema + Long Callbacks
app = Dash(
    __name__,
    server=server,
    external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.FONT_AWESOME],
    suppress_callback_exceptions=True,
    title="Intäktsramsreglering Dashboard",
    long_callback_manager=long_callback_manager  # ← NYTT
)

# ============================================================================
# LAYOUT (oförändrad)
# ============================================================================

app.layout = dbc.Container([
    dcc.Location(id='url', refresh=False),
    html.Div(id='page-content')
], fluid=True, className='p-0')


# ============================================================================
# MAIN ROUTING CALLBACK (MED NY ROUTE)
# ============================================================================

@callback(
    Output('page-content', 'children'),
    Input('url', 'pathname')
)
def display_page(pathname):
    """
    Huvudrouting - läser från Flask session direkt.
    """
    # Läs från Flask session istället för dcc.Store
    logged_in = flask_session.get('logged_in', False)
    user_role = flask_session.get('user_role')
    
    # DEBUG
    print(f"DEBUG: pathname={pathname}, logged_in={logged_in}, role={user_role}")
    
    # Kontrollera om användaren är inloggad
    if not logged_in:
        return auth.create_login_layout()
    
    # Skapa session_data dict för kompatibilitet med befintlig kod
    session_data = {
        'logged_in': logged_in,
        'user_role': user_role,
        'current_user': flask_session.get('current_user'),
        'user_dmu': flask_session.get('user_dmu'),
        'org': flask_session.get('org', 'default')
    }
    
    # Navbar för inloggade användare
    navbar_component = components.create_navbar(user_role, session_data)
    
    # Default till hem-sida om ingen specifik sida angiven
    if pathname == '/' or pathname is None:
        if user_role == 'regulator':
            from pages.regulator import hem as regulator_hem
            content = regulator_hem.layout(session_data)
        elif user_role == 'company':
            from pages.foretag import hem as foretag_hem
            content = foretag_hem.layout(session_data)
        else:
            content = html.Div([
                html.H3("Okänd användarroll"),
                html.P("Kontakta administratör.")
            ])
    
    # Regulator-sidor
    elif user_role == 'regulator':
        if pathname == '/regulator/effektivitet':
            from pages.regulator import effektivitet
            content = effektivitet.layout(session_data)
        elif pathname == '/regulator/kapitalbas':
            from pages.regulator import kapitalbas
            content = kapitalbas.layout(session_data)
        elif pathname == '/regulator/berakningskedja':
            from pages.regulator import berakningskedja
            content = berakningskedja.layout(session_data)
        elif pathname == '/regulator/ir-dekomposition':
            from pages.regulator import ir_dekomposition
            content = ir_dekomposition.layout(session_data)
        else:
            content = html.Div([
                html.H3("404 - Sidan hittades inte"),
                dcc.Link("Tillbaka till hem", href="/")
            ])
    
    # Företagssidor
    elif user_role == 'company':
        if pathname == '/foretag/effektivitet':
            from pages.foretag import effektivitet
            content = effektivitet.layout(session_data)
        elif pathname == '/foretag/intaktsram':
            from pages.foretag import intaktsram
            content = intaktsram.layout(session_data)
        # ============== NYTT: Beräkningskedja route ==============
        elif pathname == '/foretag/berakningskedja':
            from pages.foretag import berakningskedja
            content = berakningskedja.layout(session_data)
        # =========================================================
        else:
            content = html.Div([
                html.H3("404 - Sidan hittades inte"),
                dcc.Link("Tillbaka till hem", href="/")
            ])
    
    else:
        content = html.Div([
            html.H3("Åtkomst nekad"),
            html.P("Du har inte behörighet till denna sida.")
        ])
    
    # Kombinera navbar och innehåll
    return html.Div([
        navbar_component,
        dbc.Container([
            dbc.Row([
                dbc.Col(content, width=12)
            ])
        ], fluid=True, className='mt-4')
    ])


# ============================================================================
# RUN SERVER (oförändrad)
# ============================================================================

if __name__ == '__main__':
    # Development mode
    app.run(
        debug=True,
        host='0.0.0.0',
        port=8050
    )
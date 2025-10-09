"""
Authentication & Session Management - Konsoliderad modul
=========================================================

Innehåller ALLT relaterat till autentisering och session:
- Användardatabas
- Login layout
- Login/logout callbacks
- Session utilities (get_user_org, get_user_dmu, etc.)
"""

import dash
from dash import html, dcc, Input, Output, State, callback
import dash_bootstrap_components as dbc
from typing import Optional, Dict, Any
import os
from flask import session as flask_session


# ============================================================================
# USER DATABASE
# ============================================================================

USERS = {
    # Regulatorer
    "stina": {
        "password": "bison",
        "role": "regulator",
        "org": "ei",
        "dmu": None
    },
    "erik": {
        "password": "erik",
        "role": "regulator",
        "org": "ei",
        "dmu": None
    },
    
    # Företag
    "kraftringen": {
        "password": "kraftringen",
        "role": "company",
        "org": "kraftringen",
        "dmu": 121
    },
    "umea_energi": {
        "password": "umea",
        "role": "company",
        "org": "umea_energi",
        "dmu": 115
    },
    "almnas": {
        "password": "almnas",
        "role": "company",
        "org": "almnas",
        "dmu": 2
    },
    "vattenfall": {
        "password": "vattenfall",
        "role": "company",
        "org": "vattenfall",
        "dmu": 139
    }
}


# ============================================================================
# SESSION UTILITIES (kompatibelt med befintlig core/session_utils.py)
# ============================================================================

def get_user_org(session_data: Dict[str, Any] = None) -> str:
    """Hämtar organisations-ID från Flask session."""
    return flask_session.get('org', 'default')


def get_user_dmu(session_data: Dict[str, Any] = None) -> Optional[int]:
    """Hämtar användarens DMU från Flask session."""
    return flask_session.get('user_dmu', None)


def get_user_role(session_data: Dict[str, Any] = None) -> str:
    """Hämtar användarens roll från Flask session."""
    return flask_session.get('user_role', None)


def ensure_org_dir(base_path: str, session_data: Dict[str, Any] = None) -> str:
    """
    Skapar organisationsspecifik katalog och returnerar sökvägen.
    
    Args:
        base_path: Baskatalog (t.ex. "scenario/kapitalbas/exports_to_dea")
        session_data: Session state dict (ignoreras, använder Flask session)
        
    Returns:
        Fullständig sökväg till organisationsspecifik katalog
    """
    org = get_user_org()
    org_path = os.path.join(base_path, org)
    os.makedirs(org_path, exist_ok=True)
    return org_path


# ============================================================================
# LOGIN LAYOUT
# ============================================================================

def create_login_layout():
    """
    Skapar login-layout.
    
    Returns:
        Dash layout component
    """
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                # Centrerad login-card
                dbc.Card([
                    dbc.CardHeader([
                        html.H3("Intäktsramsreglering Dashboard", className="text-center mb-0")
                    ]),
                    dbc.CardBody([
                        html.H5("Logga in", className="card-title text-center mb-4"),
                        
                        # Alert för felmeddelanden
                        html.Div(id='login-alert-container'),
                        
                        # Username input
                        dbc.Row([
                            dbc.Label("Användarnamn", width=12),
                            dbc.Col([
                                dbc.Input(
                                    id='login-username',
                                    type='text',
                                    placeholder='Ange användarnamn',
                                    className='mb-3'
                                )
                            ], width=12)
                        ]),
                        
                        # Password input
                        dbc.Row([
                            dbc.Label("Lösenord", width=12),
                            dbc.Col([
                                dbc.Input(
                                    id='login-password',
                                    type='password',
                                    placeholder='Ange lösenord',
                                    className='mb-3'
                                )
                            ], width=12)
                        ]),
                        
                        # Login button
                        dbc.Row([
                            dbc.Col([
                                dbc.Button(
                                    "Logga in",
                                    id='login-button',
                                    color='primary',
                                    className='w-100',
                                    n_clicks=0
                                )
                            ], width=12)
                        ]),
                    ])
                ], className='shadow')
            ], width=12, lg=6, xl=4, className='mx-auto')
        ], className='min-vh-100 align-items-center')
    ], fluid=True)


# ============================================================================
# LOGIN CALLBACK
# ============================================================================

@callback(
    [Output('login-alert-container', 'children'),
     Output('url', 'pathname')],
    Input('login-button', 'n_clicks'),
    [State('login-username', 'value'),
     State('login-password', 'value')],
    prevent_initial_call=True
)
def handle_login(n_clicks, username, password):
    """
    Hanterar login-försök och uppdaterar Flask session.
    
    Args:
        n_clicks: Antal klick på login-knappen
        username: Angivet användarnamn
        password: Angivet lösenord
        
    Returns:
        Tuple med (alert_component, redirect_url)
    """
    if not username or not password:
        alert = dbc.Alert(
            "Ange både användarnamn och lösenord",
            color="warning",
            dismissable=True,
            className='mb-3'
        )
        return alert, dash.no_update
    
    # Validera användare
    if username in USERS and USERS[username]['password'] == password:
        user_info = USERS[username]
        
        # Uppdatera FLASK session (server-side!)
        flask_session['logged_in'] = True
        flask_session['current_user'] = username
        flask_session['user_role'] = user_info['role']
        flask_session['user_dmu'] = user_info.get('dmu')
        flask_session['org'] = user_info.get('org', 'default')
        flask_session.permanent = True
        
        print(f"LOGIN SUCCESS: {username}, role={user_info['role']}, dmu={user_info.get('dmu')}")
        
        # Redirect till hem-sida
        return None, '/'
    
    else:
        alert = dbc.Alert(
            "Felaktigt användarnamn eller lösenord",
            color="danger",
            dismissable=True,
            className='mb-3'
        )
        return alert, dash.no_update


# ============================================================================
# LOGOUT CALLBACK
# ============================================================================

@callback(
    Output('url', 'pathname', allow_duplicate=True),
    Input('logout-button', 'n_clicks'),
    prevent_initial_call=True
)
def handle_logout(n_clicks):
    """
    Hanterar logout och rensar Flask session.
    """
    # KRITISK FIX: Ignorera om n_clicks är None eller 0
    if not n_clicks or n_clicks == 0:
        raise dash.exceptions.PreventUpdate
    
    print("LOGOUT: Clearing Flask session")
    flask_session.clear()
    
    # Redirect till login
    return '/'
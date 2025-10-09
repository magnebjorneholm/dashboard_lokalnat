"""
berakningskedja.py - DUMMY TEST VERSION
========================================
Alla backend-imports ersatta med dummies för att testa UI.
"""

from dash import html, dcc, Input, Output, State, callback, dash_table, no_update
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate
import dash
from flask import session as flask_session
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, Tuple
from pathlib import Path
from app import app

import components
from utils import state_management

# ============================================================================
# DUMMY BACKEND FUNCTIONS
# ============================================================================

def load_reconciliation_foretag_info():
    return {'company_name': 'Test Företag AB', 'dmu': 121}

def validate_company_data():
    return {'details': {'dmu_networks': 2}}

def load_dmu_capbase_a(dmu):
    # Returnera tom DataFrame med rätt kolumner
    return pd.DataFrame({
        'cat_encode': [1, 2, 3],
        'cat': ['Kategori 1', 'Kategori 2', 'Kategori 3'],
        'ekdep': [40, 50, 60],
        'maxdep': [50, 60, 70],
        'id_network': [1, 1, 2]
    })

def validate_input_data(df):
    return {'status': 'ok'}

def calculate_ages_and_nuav(df):
    # Mock result
    df_result = df.copy()
    for t in range(229, 237):
        df_result[f'nuav_ord_{t}'] = 1000000
        df_result[f'nuav_tail_{t}'] = 500000
    return df_result

def calculate_depreciation_single_dmu(df):
    return {f'dep_ord_{t}': 50000 for t in range(229, 237)} | {f'dep_tail_{t}': 25000 for t in range(229, 237)}

def calculate_returns_single_dmu(df, interest_rate=0.0453):
    return {f'return_ord_{t}': 30000 for t in range(229, 237)} | {f'return_tail_{t}': 15000 for t in range(229, 237)}

def compile_capcost_single_dmu(step6_dict, step7_dict, dmu):
    data = []
    for t in range(229, 237):
        data.append({
            'time': t,
            'dep_ord': step6_dict.get(f'dep_ord_{t}', 0),
            'dep_tail': step6_dict.get(f'dep_tail_{t}', 0),
            'return_ord': step7_dict.get(f'return_ord_{t}', 0),
            'return_tail': step7_dict.get(f'return_tail_{t}', 0),
            'capcost_sum': (step6_dict.get(f'dep_ord_{t}', 0) + 
                           step6_dict.get(f'dep_tail_{t}', 0) +
                           step7_dict.get(f'return_ord_{t}', 0) + 
                           step7_dict.get(f'return_tail_{t}', 0))
        })
    return pd.DataFrame(data)

def load_facit_for_dmu(dmu):
    return pd.DataFrame()  # Tom för test

# Mock WACC calculations
R_OLD = 0.0453

class EiWaccInputs:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

def ei_wacc_real_pre_tax(inputs):
    return 0.06, 0.04, 0.05, 0.045  # re_nom, rd_nom, wacc_nom, wacc_real

# ============================================================================
# REST OF THE FILE - EXACT SAME AS BEFORE
# ============================================================================

def get_current_user_info() -> Dict[str, Any]:
    user_dmu = flask_session.get('user_dmu')
    org = flask_session.get('org', 'unknown')
    
    try:
        company_info = load_reconciliation_foretag_info()
        company_name = company_info.get('company_name', 'Ditt företag')
    except:
        company_name = 'Ditt företag'
    
    return {
        'user_dmu': user_dmu,
        'company_name': company_name,
        'org': org
    }

def load_baseline_data_for_company() -> Tuple[pd.DataFrame, Dict[str, Any]]:
    user_info = get_current_user_info()
    user_dmu = user_info['user_dmu']
    
    if user_dmu is None:
        return pd.DataFrame(), {'error': 'Ingen DMU hittades'}
    
    try:
        df = load_dmu_capbase_a(user_dmu)
        
        if df.empty:
            return df, {'error': f'Ingen data för DMU {user_dmu}'}
        
        validation = validate_input_data(df)
        
        status = {
            'rows': len(df),
            'networks': df['id_network'].nunique() if 'id_network' in df.columns else 0,
            'categories': df['cat_encode'].nunique() if 'cat_encode' in df.columns else 0,
            'validation': validation
        }
        
        return df, status
        
    except Exception as e:
        return pd.DataFrame(), {'error': str(e)}

def prepare_lifetime_table_data(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=['Kod', 'Beskrivning', 'Ekonomisk livslängd', 'Maximal livslängd'])
    
    group_cols = ['cat_encode']
    if 'cat' in df.columns:
        group_cols.append('cat')
    
    agg_df = df.groupby(group_cols).agg({
        'ekdep': 'first',
        'maxdep': 'first'
    }).reset_index()
    
    result = pd.DataFrame({
        'Kod': agg_df['cat_encode'],
        'Beskrivning': agg_df['cat'] if 'cat' in agg_df.columns else agg_df['cat_encode'],
        'Ekonomisk livslängd': agg_df['ekdep'].astype(int),
        'Maximal livslängd': agg_df['maxdep'].astype(int)
    })
    
    return result.sort_values('Kod').reset_index(drop=True)

def apply_lifetime_adjustments_to_data(df: pd.DataFrame, adjustments: pd.DataFrame) -> pd.DataFrame:
    df_adjusted = df.copy()
    
    for _, row in adjustments.iterrows():
        kod = row['Kod']
        new_ekdep = row['Ekonomisk livslängd']
        new_maxdep = row['Maximal livslängd']
        
        mask = df_adjusted['cat_encode'] == kod
        df_adjusted.loc[mask, 'ekdep'] = new_ekdep
        df_adjusted.loc[mask, 'maxdep'] = new_maxdep
    
    return df_adjusted

# ============================================================================
# MAIN LAYOUT
# ============================================================================

def layout(session_data: Dict[str, Any]) -> html.Div:
    user_info = get_current_user_info()
    company_name = user_info['company_name']
    user_dmu = user_info['user_dmu']
    
    validation = validate_company_data()
    
    return html.Div([
        dcc.Store(id='steps-store', storage_type='session', data={
            'completed_steps': [],
            'current_step': None,
            'wacc_for_step7': R_OLD
        }),
        
        html.H1("Beräkningskedja - Kapitalkostnader", className="mb-4"),
        
        components.create_company_info_alert(
            company_name,
            user_dmu,
            {
                'networks': validation.get('details', {}).get('dmu_networks', 'N/A'),
                'periods': 'H1-H2 2024-2027'
            }
        ),
        
        html.Div(id='progress-indicator'),
        
        dcc.Tabs(id='main-tabs', value='step5', children=[
            dcc.Tab(label='Steg 5: Åldrar & NUAV', value='step5', id='tab-step5'),
            dcc.Tab(label='Steg 6: Avskrivningar', value='step6', id='tab-step6', disabled=True),
            dcc.Tab(label='WACC-kalkylator', value='wacc', id='tab-wacc'),
            dcc.Tab(label='Steg 7: Avkastning', value='step7', id='tab-step7', disabled=True),
            dcc.Tab(label='Steg 8: Sammanställning', value='step8', id='tab-step8', disabled=True),
        ]),
        
        html.Div(id='tab-content', className='mt-4')
    ])

# ... (alla create_stepX_content funktioner - samma som innan)
# För brevity, kopiera från din nuvarande fil

def create_step5_content() -> html.Div:
    return html.Div([
        html.H3("Steg 5: Åldrar och NUAV-värden"),
        html.P("Beräknar komponenternas ålder och nuanskaffningsvärden för varje tidsperiod (2024-2027)."),
        
        dbc.Card([
            dbc.CardHeader("Beräkningslogik"),
            dbc.CardBody([
                html.P("""
                För varje komponent och tidsperiod beräknas:
                - Ålder: tid minus time_from
                - NUAV ordinarie: för komponenter inom ekonomisk livslängd
                - NUAV svans: för komponenter mellan ekonomisk och maximal livslängd
                """)
            ])
        ], className="mb-4"),
        
        html.Hr(),
        dbc.Button(
            "Kör Steg 5: Åldrar & NUAV",
            id='run-step5-btn',
            color='primary',
            size='lg',
            className='mb-3'
        ),
        
        html.Div(id='step5-status', children=[
            dbc.Alert("Klicka på 'Kör Steg 5' för att börja beräkningen", color="info")
        ]),
        html.Div(id='step5-results')
    ])

def create_step6_content() -> html.Div:
    return html.Div([
        html.H3("Steg 6: Avskrivningar"),
        html.P("Beräknar ordinarie och svansavskrivningar."),
        html.Div(id='step6-prerequisites'),
        html.Hr(),
        dbc.Button("Kör Steg 6", id='run-step6-btn', color='primary', disabled=True),
        html.Div(id='step6-status'),
        html.Div(id='step6-results')
    ])

def create_wacc_content() -> html.Div:
    return html.Div([
        html.H3("WACC-kalkylator"),
        html.P("Beräkna kalkylränta från grundparametrar."),
        html.Div(id='wacc-input-form'),
        html.Hr(),
        dbc.Button("Beräkna WACC", id='calc-wacc-btn', color='primary'),
        html.Div(id='wacc-results'),
        html.Div(id='wacc-use-in-step7')
    ])

def create_step7_content() -> html.Div:
    return html.Div([
        html.H3("Steg 7: Avkastning"),
        html.Div(id='step7-wacc-selector'),
        html.Div(id='step7-prerequisites'),
        html.Hr(),
        dbc.Button("Kör Steg 7", id='run-step7-btn', color='primary', disabled=True),
        html.Div(id='step7-status'),
        html.Div(id='step7-results')
    ])

def create_step8_content() -> html.Div:
    return html.Div([
        html.H3("Steg 8: Sammanställning"),
        html.Div(id='step8-prerequisites'),
        html.Hr(),
        dbc.Button("Kör Steg 8", id='run-step8-btn', color='primary', disabled=True),
        html.Div(id='step8-status'),
        html.Div(id='step8-results')
    ])

@callback(
    Output('tab-content', 'children'),
    Output('progress-indicator', 'children'),
    Input('main-tabs', 'value'),
    State('steps-store', 'data'),
    prevent_initial_call=False
)
def render_tab_content(active_tab, steps_data):
    user_info = get_current_user_info()
    if not user_info.get('user_dmu'):
        return html.Div([
            dbc.Alert("Session data saknas!", color="danger")
        ]), None
    
    completed = steps_data.get('completed_steps', []) if steps_data else []
    progress = components.create_step_progress_indicator(completed, total_steps=4)
    
    if active_tab == 'step5':
        return create_step5_content(), progress
    elif active_tab == 'step6':
        return create_step6_content(), progress
    elif active_tab == 'wacc':
        return create_wacc_content(), progress
    elif active_tab == 'step7':
        return create_step7_content(), progress
    elif active_tab == 'step8':
        return create_step8_content(), progress
    else:
        return html.Div("Okänd tab"), progress

print("DEBUG: Dummy berakningskedja.py loaded successfully!")
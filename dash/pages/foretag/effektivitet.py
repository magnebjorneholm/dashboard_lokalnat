"""
Företagsportalen - Effektivitetsanalys
======================================

Företagsspecifik DEA-analys med fokus på användarens företag.
Visar position i bransch, effektiviseringskrav och påverkbara kostnader.
"""

import dash
from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional
import io

# Import från backend (UI-agnostisk, fungerar direkt!)
from effektiviseringskrav.backend.dea_model import run_dea_model
from data_loaders import load_data, merge_capex_scenario, get_company_info
from effektiviseringskrav.backend.ir_calculations import calculate_ir_paverkbara_from_file
from effektiviseringskrav.backend.spatial_analysis import calculate_company_neighbor_gap

# Import från vår Dash-app
import auth
import components


def layout(session_data: Dict[str, Any]):
    """
    Skapar layout för företagsspecifik effektivitetsanalys.
    
    Args:
        session_data: Session state dict
        
    Returns:
        Dash layout
    """
    # Hämta företagsinformation
    user_dmu = auth.get_user_dmu(session_data)
    
    if not user_dmu:
        return dbc.Container([
            dbc.Alert("Ingen DMU hittades för inloggad användare", color="danger")
        ])
    
    # Hämta företagsnamn
    company_name = get_company_name(user_dmu)
    
    return dbc.Container([
        # Header
        dbc.Row([
            dbc.Col([
                html.H2(f"Effektivitetsanalys - {company_name}"),
                html.P(f"DMU {user_dmu} • Analysera ditt företags effektivitet och beräkna påverkbara kostnader", 
                       className="text-muted")
            ])
        ], className="mb-4"),
        
        # DEA-parametrar (sidebar-stil med Offcanvas eller Card)
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H5("DEA-parametrar", className="mb-0")),
                    dbc.CardBody([
                        html.Div(id='foretag-dea-parameters')
                    ])
                ])
            ], width=12, lg=3),
            
            # Huvudinnehåll
            dbc.Col([
                # Info om WACC-scenario
                html.Div(id='foretag-wacc-info'),
                
                # Kör DEA-knapp
                dbc.Button(
                    "Kör DEA-analys",
                    id='foretag-run-dea-button',
                    color='primary',
                    className='mb-3',
                    size='lg'
                ),
                
                # Loading spinner
                dcc.Loading(
                    id='foretag-dea-loading',
                    type='default',
                    children=[
                        html.Div(id='foretag-dea-results')
                    ]
                )
            ], width=12, lg=9)
        ])
        
    ], fluid=True)


# ============================================================================
# CALLBACKS
# ============================================================================
@callback(
    [Output('foretag-dea-parameters', 'children'),
     Output('foretag-wacc-info', 'children')],
    Input('url', 'pathname'),
    State('session-store', 'data'),
    prevent_initial_call=False
)
def load_dea_data_and_parameters(pathname, session_data):
    """
    Visar parameterkontroller UTAN att ladda hela datasetet.
    Data laddas först när användaren klickar "Kör DEA".
    """
    if pathname != '/foretag/effektivitet':
        raise dash.exceptions.PreventUpdate
    
    user_dmu = auth.get_user_dmu(session_data)
    
    if not user_dmu:
        return html.P("Ingen DMU hittad"), None
    
    # Visa defaultparametrar UTAN att ladda data
    parameters = html.Div([
        html.Label("Input-variabler:", className="fw-bold mt-2"),
        dcc.Checklist(
            id='foretag-dea-inputs',
            options=[
                {'label': 'CAPEX', 'value': 'CAPEX'},
                {'label': 'OPEXp', 'value': 'OPEXp'},
                {'label': 'TOTEX', 'value': 'TOTEX'}
            ],
            value=['CAPEX', 'OPEXp'],
            className='mb-3'
        ),
        
        html.Label("Output-variabler:", className="fw-bold mt-2"),
        dcc.Checklist(
            id='foretag-dea-outputs',
            options=[
                {'label': col, 'value': col} 
                for col in ['CU', 'MW', 'NS', 'MWhl', 'MWhh']
            ],
            value=['CU', 'MW', 'NS', 'MWhl', 'MWhh'],
            className='mb-3'
        ),
        
        html.Label("Skalavkastning (RTS):", className="fw-bold mt-2"),
        dcc.RadioItems(
            id='foretag-dea-rts',
            options=[
                {'label': 'CRS (Konstant)', 'value': 'crs'},
                {'label': 'VRS (Variabel)', 'value': 'vrs'}
            ],
            value='crs',
            className='mb-3'
        ),
        
        dbc.Checkbox(
            id='foretag-dea-outlier-filter',
            label="Filtrera outliers",
            value=True,
            className='mb-3'
        ),
        
        html.Label("Minsta trunkering:", className="fw-bold mt-2"),
        dcc.Slider(
            id='foretag-dea-trunk-min',
            min=0, max=0.3, step=0.005, value=0.162416,
            marks={0: '0%', 0.15: '15%', 0.3: '30%'},
            tooltip={"placement": "bottom", "always_visible": True}
        ),
        
        html.Label("Högsta trunkering:", className="fw-bold mt-3"),
        dcc.Slider(
            id='foretag-dea-trunk-max',
            min=0.1, max=0.5, step=0.005, value=0.3,
            marks={0.1: '10%', 0.3: '30%', 0.5: '50%'},
            tooltip={"placement": "bottom", "always_visible": True}
        )
    ])
    
    return parameters, None  # Ingen WACC-info förrän DEA körs


@callback(
    Output('foretag-dea-results', 'children'),
    Input('foretag-run-dea-button', 'n_clicks'),
    [State('foretag-dea-inputs', 'value'),
     State('foretag-dea-outputs', 'value'),
     State('foretag-dea-rts', 'value'),
     State('foretag-dea-outlier-filter', 'value'),
     State('foretag-dea-trunk-min', 'value'),
     State('foretag-dea-trunk-max', 'value'),
     State('session-store', 'data')],
    prevent_initial_call=True
)
def run_dea_analysis(n_clicks, input_cols, output_cols, rts, outlier_filter, 
                     trunk_min, trunk_max, session_data):
    """
    Kör DEA-analys och visar resultat för företaget.
    
    Returns:
        Layout med resultat
    """
    if not n_clicks:
        return dash.no_update
    
    user_dmu = auth.get_user_dmu(session_data)
    
    if not user_dmu or not input_cols or not output_cols:
        return dbc.Alert("Välj minst en input och en output", color="warning")
    
    try:
        # Ladda data
        data_file = "effektiviseringskrav/data/Data_modeller.xlsx"
        df = load_data(data_file)
        df, _ = merge_capex_scenario(df)
        
        # Validera att kolumner finns
        missing_cols = [c for c in input_cols + output_cols if c not in df.columns]
        if missing_cols:
            return dbc.Alert(f"Saknade kolumner: {missing_cols}", color="danger")
        
        # Kör DEA (använder backend direkt!)
        result = run_dea_model(
            df=df,
            input_cols=input_cols,
            output_cols=output_cols,
            rts=rts,
            trunkering_min=trunk_min,
            trunkering_max=trunk_max,
            outlier_filter=outlier_filter,
            outlier_krav=0.01  # 1%
        )
        
        if result is None or result.empty:
            return dbc.Alert("DEA-analys misslyckades", color="danger")
        
        # Filtrera till användarens företag
        company_result = result[result['DMU'] == user_dmu]
        
        if company_result.empty:
            return dbc.Alert(f"Inga resultat för DMU {user_dmu}", color="warning")
        
        company_row = company_result.iloc[0]
        
        # Skapa resultat-vy
        return create_company_results_view(company_row, result, user_dmu)
        
    except Exception as e:
        return dbc.Alert(f"Fel vid DEA-analys: {str(e)}", color="danger")


def create_company_results_view(company_row: pd.Series, full_results: pd.DataFrame, 
                                  user_dmu: int) -> html.Div:
    """
    Skapar resultat-vy för företaget.
    
    Args:
        company_row: Rad med företagets resultat
        full_results: Alla DEA-resultat
        user_dmu: Företagets DMU
        
    Returns:
        Dash layout med resultat
    """
    efficiency = company_row.get('Efficiency', 0)
    paverkbara_baseline = company_row.get('Paverkbara_Baseline_4yr', 0)
    effektiviseringskrav = company_row.get('Effektiviseringskrav', 0)
    paverkbara_target = company_row.get('Paverkbara_Target', 0)
    reduction = company_row.get('Total_Reduction_tkr', 0)
    
    # Branschposition
    all_efficiencies = full_results['Efficiency'].sort_values()
    company_rank = (all_efficiencies > efficiency).sum() + 1
    total_companies = len(all_efficiencies)
    percentile = (company_rank / total_companies) * 100
    
    return html.Div([
        # Nyckeltal i cards
        dbc.Row([
            dbc.Col([
                components.create_metric_card(
                    "Effektivitet",
                    f"{efficiency:.1%}",
                    f"Rank {company_rank} av {total_companies}",
                    color="primary" if efficiency >= 0.8 else "warning"
                )
            ], md=3),
            dbc.Col([
                components.create_metric_card(
                    "Effektiviseringskrav",
                    f"{effektiviseringskrav:.2%}",
                    "Årligt krav",
                    color="info"
                )
            ], md=3),
            dbc.Col([
                components.create_metric_card(
                    "Påverkbara baseline",
                    f"{paverkbara_baseline:,.0f} tkr",
                    "4-årsperiod",
                    color="secondary"
                )
            ], md=3),
            dbc.Col([
                components.create_metric_card(
                    "Total reduktion",
                    f"{reduction:,.0f} tkr",
                    "4-årsperiod",
                    color="danger" if reduction > 0 else "success"
                )
            ], md=3)
        ], className="mb-4"),
        
        # Histogram med företagets position
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H5("Din position i branschen", className="mb-0")),
                    dbc.CardBody([
                        dcc.Graph(
                            figure=components.create_histogram(
                                full_results,
                                'Efficiency',
                                'Effektivitetsfördelning',
                                bins=30,
                                highlight_value=efficiency
                            )
                        ),
                        html.P([
                            f"Du är mer effektiv än {100-percentile:.0f}% av företagen i analysen."
                        ], className="text-center text-muted mt-2")
                    ])
                ])
            ])
        ], className="mb-4"),
        
        # Sammanfattningstabell
        dbc.Row([
            dbc.Col([
                components.create_summary_table({
                    'Påverkbara kostnader (baseline)': f"{paverkbara_baseline:,.0f} tkr",
                    'Effektiviseringskrav (årligt)': f"{effektiviseringskrav:.2%}",
                    'Påverkbara kostnader (efter krav)': f"{paverkbara_target:,.0f} tkr",
                    'Total reduktion (4 år)': f"{reduction:,.0f} tkr",
                    'Effektivitet': f"{efficiency:.1%}",
                    'Position': f"{company_rank} av {total_companies}"
                }, title="Sammanfattning")
            ])
        ])
    ])


def get_company_name(dmu: int) -> str:
    """Hämtar företagsnamn från reconciliation."""
    if not dmu:
        return "Ditt företag"
    
    try:
        recon_path = "effektiviseringskrav/data/new_recon.csv"
        if Path(recon_path).exists():
            recon_df = pd.read_csv(recon_path)
            company_row = recon_df[recon_df['DMU'] == dmu]
            if not company_row.empty:
                return company_row.iloc[0].get('Företag', f'DMU {dmu}')
    except:
        pass
    
    return f"DMU {dmu}"
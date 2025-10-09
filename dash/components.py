"""
UI Components - Konsoliderad modul
===================================

Innehåller ALLA återanvändbara UI-komponenter:
- Navbar
- Tabeller
- Grafer/visualiseringar
- Kontroller (dropdowns, sliders, etc.)
"""

import dash
from dash import html, dcc, dash_table
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from typing import Dict, List, Any, Optional


# ============================================================================
# NAVBAR
# ============================================================================

def create_navbar(user_role: str, session_data: Dict[str, Any]) -> dbc.Navbar:
    """
    Skapar navbar baserat på användarroll.
    
    Args:
        user_role: 'regulator' eller 'company'
        session_data: Session state dict
        
    Returns:
        Bootstrap Navbar component
    """
    current_user = session_data.get('current_user', 'Användare')
    
    # Olika länkar beroende på roll
    if user_role == 'regulator':
        nav_items = [
            dbc.NavItem(dbc.NavLink("Hem", href="/", active="exact")),
            dbc.NavItem(dbc.NavLink("Effektiviseringskrav", href="/regulator/effektivitet")),
            dbc.NavItem(dbc.NavLink("Kapitalbas", href="/regulator/kapitalbas")),
            dbc.NavItem(dbc.NavLink("Beräkningskedja", href="/regulator/berakningskedja")),
            dbc.NavItem(dbc.NavLink("IR-dekomposition", href="/regulator/ir-dekomposition")),
        ]
    elif user_role == 'company':
        nav_items = [
            dbc.NavItem(dbc.NavLink("Hem", href="/", active="exact")),
            dbc.NavItem(dbc.NavLink("Effektivitet", href="/foretag/effektivitet")),
            dbc.NavItem(dbc.NavLink("Intäktsram", href="/foretag/intaktsram")),
            dbc.NavItem(dbc.NavLink("Beräkningskedja", href="/foretag/berakningskedja")),
        ]
    else:
        nav_items = []
    
    # Navbar
    navbar = dbc.Navbar(
        dbc.Container([
            dbc.Row([
                dbc.Col([
                    dbc.NavbarBrand("Intäktsramsreglering", className="ms-2")
                ], width="auto"),
            ], align="center", className="g-0"),
            
            dbc.Row([
                dbc.Col([
                    dbc.Nav(nav_items, navbar=True, className="ms-auto")
                ], width="auto"),
                dbc.Col([
                    html.Div([
                        html.I(className="fas fa-user me-2"),
                        html.Span(current_user, className="text-white me-2"),
                        html.Span(" | ", className="text-white mx-2"),
                        dbc.Button(
                            "Logga ut",
                            id="logout-button",
                            color="link",
                            size="sm",
                            className="text-white"
                        )
                    ], className="d-flex align-items-center")
                ], width="auto")
            ], align="center", className="g-0 ms-auto flex-nowrap")
        ], fluid=True),
        color="primary",
        dark=True,
        className="mb-4"
    )
    
    return navbar


# ============================================================================
# TABELLER
# ============================================================================

def create_data_table(
    df: pd.DataFrame,
    table_id: str,
    page_size: int = 20,
    style_data_conditional: Optional[List] = None
) -> dash_table.DataTable:
    """
    Skapar en formaterad datatabell.
    
    Args:
        df: DataFrame att visa
        table_id: Unikt ID för tabellen
        page_size: Antal rader per sida
        style_data_conditional: Villkorsstyrd formatering
        
    Returns:
        Dash DataTable component
    """
    return dash_table.DataTable(
        id=table_id,
        columns=[{"name": i, "id": i} for i in df.columns],
        data=df.to_dict('records'),
        page_size=page_size,
        page_action='native',
        sort_action='native',
        sort_mode='multi',
        filter_action='native',
        style_table={'overflowX': 'auto'},
        style_cell={
            'textAlign': 'left',
            'padding': '10px',
            'fontFamily': 'Arial, sans-serif',
            'fontSize': '14px'
        },
        style_header={
            'backgroundColor': 'rgb(230, 230, 230)',
            'fontWeight': 'bold'
        },
        style_data_conditional=style_data_conditional or []
    )


def create_summary_table(
    data: Dict[str, Any],
    title: str = "Sammanfattning"
) -> dbc.Card:
    """
    Skapar en sammanfattningstabell med nyckeltal.
    
    Args:
        data: Dictionary med nyckel-värde par
        title: Titel för tabellen
        
    Returns:
        Bootstrap Card med tabell
    """
    table_rows = [
        html.Tr([
            html.Td(html.Strong(key), style={'width': '50%'}),
            html.Td(str(value))
        ]) for key, value in data.items()
    ]
    
    return dbc.Card([
        dbc.CardHeader(html.H5(title, className="mb-0")),
        dbc.CardBody([
            html.Table(
                [html.Tbody(table_rows)],
                className="table table-sm"
            )
        ])
    ], className="mb-3")


# ============================================================================
# GRAFER / VISUALISERINGAR
# ============================================================================

def create_histogram(
    df: pd.DataFrame,
    column: str,
    title: str,
    bins: int = 30,
    highlight_value: Optional[float] = None
) -> go.Figure:
    """
    Skapar histogram med optional highlight.
    
    Args:
        df: DataFrame med data
        column: Kolumn att plotta
        title: Titel på grafen
        bins: Antal bins
        highlight_value: Värde att highlighta (t.ex. företagets värde)
        
    Returns:
        Plotly Figure
    """
    fig = go.Figure()
    
    # Histogram
    fig.add_trace(go.Histogram(
        x=df[column],
        nbinsx=bins,
        name='Distribution',
        marker_color='lightblue'
    ))
    
    # Highlight om angiven
    if highlight_value is not None:
        fig.add_vline(
            x=highlight_value,
            line_dash="dash",
            line_color="red",
            annotation_text="Ditt företag",
            annotation_position="top"
        )
    
    fig.update_layout(
        title=title,
        xaxis_title=column,
        yaxis_title="Antal",
        showlegend=False,
        template="plotly_white"
    )
    
    return fig


def create_waterfall(
    categories: List[str],
    values: List[float],
    title: str = "Waterfall"
) -> go.Figure:
    """
    Skapar waterfall-diagram (för IR-dekomposition).
    
    Args:
        categories: Lista med kategorier
        values: Lista med värden
        title: Titel på grafen
        
    Returns:
        Plotly Figure
    """
    fig = go.Figure(go.Waterfall(
        name="",
        orientation="v",
        measure=["relative"] * (len(values) - 1) + ["total"],
        x=categories,
        y=values,
        connector={"line": {"color": "rgb(63, 63, 63)"}},
    ))
    
    fig.update_layout(
        title=title,
        showlegend=False,
        template="plotly_white"
    )
    
    return fig


def create_time_series(
    df: pd.DataFrame,
    x_col: str,
    y_cols: List[str],
    title: str,
    labels: Optional[Dict] = None
) -> go.Figure:
    """
    Skapar tidsserie-graf.
    
    Args:
        df: DataFrame med data
        x_col: X-axel kolumn (tid)
        y_cols: Y-axel kolumner (kan vara flera)
        title: Titel på grafen
        labels: Dictionary med labels för kolumner
        
    Returns:
        Plotly Figure
    """
    fig = go.Figure()
    
    for col in y_cols:
        fig.add_trace(go.Scatter(
            x=df[x_col],
            y=df[col],
            mode='lines+markers',
            name=labels.get(col, col) if labels else col
        ))
    
    fig.update_layout(
        title=title,
        xaxis_title=x_col,
        yaxis_title="Värde",
        template="plotly_white",
        hovermode='x unified'
    )
    
    return fig


# ============================================================================
# KONTROLLER
# ============================================================================

def create_parameter_controls(
    params: Dict[str, Dict[str, Any]],
    control_id_prefix: str = "param"
) -> List[dbc.Row]:
    """
    Skapar kontroller för parametrar (sliders, dropdowns, etc.).
    
    Args:
        params: Dictionary med parameter-definitioner
                Format: {
                    'param_name': {
                        'label': 'Parameter Label',
                        'type': 'slider' eller 'dropdown' eller 'input',
                        'min': min_value (för slider),
                        'max': max_value (för slider),
                        'step': step_value (för slider),
                        'value': default_value,
                        'options': [...] (för dropdown)
                    }
                }
        control_id_prefix: Prefix för kontroll-ID:n
        
    Returns:
        Lista med Bootstrap Rows innehållande kontroller
    """
    controls = []
    
    for param_name, param_config in params.items():
        label = param_config.get('label', param_name)
        param_type = param_config.get('type', 'input')
        
        if param_type == 'slider':
            control = dbc.Row([
                dbc.Label(label, width=12),
                dbc.Col([
                    dcc.Slider(
                        id=f"{control_id_prefix}-{param_name}",
                        min=param_config.get('min', 0),
                        max=param_config.get('max', 100),
                        step=param_config.get('step', 1),
                        value=param_config.get('value', 50),
                        marks=None,
                        tooltip={"placement": "bottom", "always_visible": True}
                    )
                ], width=12)
            ], className="mb-3")
        
        elif param_type == 'dropdown':
            control = dbc.Row([
                dbc.Label(label, width=12),
                dbc.Col([
                    dcc.Dropdown(
                        id=f"{control_id_prefix}-{param_name}",
                        options=param_config.get('options', []),
                        value=param_config.get('value'),
                        clearable=False
                    )
                ], width=12)
            ], className="mb-3")
        
        else:  # input
            control = dbc.Row([
                dbc.Label(label, width=12),
                dbc.Col([
                    dbc.Input(
                        id=f"{control_id_prefix}-{param_name}",
                        type="number",
                        value=param_config.get('value', 0),
                        step=param_config.get('step', 0.01)
                    )
                ], width=12)
            ], className="mb-3")
        
        controls.append(control)
    
    return controls


# ============================================================================
# ALERT / MEDDELANDEN
# ============================================================================

def create_alert(
    message: str,
    alert_type: str = "info",
    dismissable: bool = True
) -> dbc.Alert:
    """
    Skapar alert-meddelande.
    
    Args:
        message: Meddelande att visa
        alert_type: 'success', 'info', 'warning', 'danger'
        dismissable: Om användaren kan stänga meddelandet
        
    Returns:
        Bootstrap Alert component
    """
    return dbc.Alert(
        message,
        color=alert_type,
        dismissable=dismissable,
        className="mb-3"
    )


# ============================================================================
# CARDS
# ============================================================================

def create_metric_card(
    title: str,
    value: Any,
    subtitle: Optional[str] = None,
    color: str = "primary"
) -> dbc.Card:
    """
    Skapar metric card för att visa nyckeltal.
    
    Args:
        title: Titel/label
        value: Värde att visa
        subtitle: Optional subtitle
        color: Bootstrap färg
        
    Returns:
        Bootstrap Card component
    """
    return dbc.Card([
        dbc.CardBody([
            html.H6(title, className="text-muted mb-2"),
            html.H3(str(value), className=f"text-{color} mb-0"),
            html.Small(subtitle, className="text-muted") if subtitle else None
        ])
    ], className="mb-3")


    # ============================================================================
# BERÄKNINGSKEDJA - SPECIFIKA KOMPONENTER
# ============================================================================
def create_metric_card_with_delta(
    title: str,
    baseline: float,
    new_value: float,
    unit: str = "tkr",
    show_delta: bool = True
) -> dbc.Card:
    """
    Skapar metric card med baseline och nytt värde + delta.
    Används för facit-jämförelse i Steg 8.
    
    Args:
        title: Label för metric
        baseline: Baseline-värde
        new_value: Beräknat värde
        unit: Enhet (tkr, MSEK, %)
        show_delta: Om delta ska visas
        
    Returns:
        Bootstrap Card component
    """
    delta = new_value - baseline
    
    # Formatera värden
    if unit == "tkr":
        baseline_str = f"{baseline:,.0f} tkr"
        new_str = f"{new_value:,.0f} tkr"
        delta_str = f"{delta:+,.0f} tkr"
    elif unit == "MSEK":
        baseline_str = f"{baseline/1000:.1f} MSEK"
        new_str = f"{new_value/1000:.1f} MSEK"
        delta_str = f"{delta/1000:+.1f} MSEK"
    else:
        baseline_str = f"{baseline:,.2f}"
        new_str = f"{new_value:,.2f}"
        delta_str = f"{delta:+,.2f}"
    
    # Färgkodning: röd om högre, grön om lägre
    if abs(delta) <= 1.0:
        delta_color = "secondary"
        delta_str = "≈ 0"
    elif delta > 0:
        delta_color = "danger"  # Rött = högre än baseline
    else:
        delta_color = "success"  # Grönt = lägre än baseline
    
    card_content = [
        html.H6(title, className="text-muted mb-2"),
        html.H4(new_str, className="mb-1")
    ]
    
    if show_delta:
        card_content.append(
            html.Div([
                html.Small("Δ: ", className="text-muted"),
                html.Small(delta_str, className=f"text-{delta_color} fw-bold")
            ])
        )
    
    return dbc.Card([
        dbc.CardBody(card_content)
    ], className="mb-3")


def create_wacc_input_form(
    form_id_prefix: str = "wacc",
    defaults: Optional[Dict] = None
) -> html.Div:
    """
    Skapar input-formulär för WACC-kalkylator.
    
    Args:
        form_id_prefix: Prefix för input-IDs
        defaults: Default-värden (om None används Ei-standard)
        
    Returns:
        Div med alla inputs
    """
    if defaults is None:
        defaults = {
            'rf_nom': 0.0287,
            'mrp': 0.0668,
            'infl': 0.0202,
            'credit': 0.0114,
            'debt_share': 0.36,
            'tax_rate': 0.206,
            'beta_mode': 'beta_a',
            'beta_a': 0.37,
            'beta_e': 0.54
        }
    
    return html.Div([
        dbc.Row([
            # Kolumn 1
            dbc.Col([
                dbc.Label("Riskfri ränta (nominell) Rf"),
                dbc.Input(
                    id=f"{form_id_prefix}-rf-nom",
                    type="number",
                    value=defaults['rf_nom'],
                    step=0.0001,
                    className="mb-3"
                ),
                
                dbc.Label("Marknadsriskpremie (nominell) MRP"),
                dbc.Input(
                    id=f"{form_id_prefix}-mrp",
                    type="number",
                    value=defaults['mrp'],
                    step=0.0001,
                    className="mb-3"
                ),
                
                dbc.Label("Inflation π (KPIF)"),
                dbc.Input(
                    id=f"{form_id_prefix}-infl",
                    type="number",
                    value=defaults['infl'],
                    step=0.0001,
                    className="mb-3"
                ),
            ], width=4),
            
            # Kolumn 2
            dbc.Col([
                dbc.Label("Kreditriskpremie (nominell)"),
                dbc.Input(
                    id=f"{form_id_prefix}-credit",
                    type="number",
                    value=defaults['credit'],
                    step=0.0001,
                    className="mb-3"
                ),
                
                dbc.Label("Skuldsättningsgrad S = D/(D+E)"),
                dbc.Input(
                    id=f"{form_id_prefix}-debt-share",
                    type="number",
                    value=defaults['debt_share'],
                    min=0,
                    max=0.95,
                    step=0.01,
                    className="mb-3"
                ),
                
                dbc.Label("Bolagsskatt T"),
                dbc.Input(
                    id=f"{form_id_prefix}-tax-rate",
                    type="number",
                    value=defaults['tax_rate'],
                    min=0,
                    max=0.99,
                    step=0.001,
                    className="mb-3"
                ),
            ], width=4),
            
            # Kolumn 3
            dbc.Col([
                dbc.Label("Beta-inmatning"),
                dbc.RadioItems(
                    id=f"{form_id_prefix}-beta-mode",
                    options=[
                        {'label': 'β_A (tillgångsbeta)', 'value': 'beta_a'},
                        {'label': 'β_E (aktiebeta)', 'value': 'beta_e'}
                    ],
                    value=defaults['beta_mode'],
                    className="mb-3"
                ),
                
                html.Div(id=f"{form_id_prefix}-beta-input-container")
            ], width=4)
        ])
    ])


def create_lifetime_table(
    df: pd.DataFrame,
    table_id: str = "lifetime-table"
) -> html.Div:
    """
    Skapar editerbar tabell för lifetime-justeringar.
    
    Args:
        df: DataFrame med kolumner: Kod, Beskrivning, Ekonomisk livslängd, Maximal livslängd
        table_id: ID för tabellen
        
    Returns:
        Div med tabell och kontroller
    """
    return html.Div([
        html.H5("Justera ekonomisk och maximal livslängd per kategori"),
        html.P(
            "Redigera värdena direkt i tabellen. Ändringar appliceras när du klickar 'Applicera'.",
            className="text-muted"
        ),
        
        dash_table.DataTable(
            id=table_id,
            columns=[
                {'name': 'Kod', 'id': 'Kod', 'editable': False},
                {'name': 'Beskrivning', 'id': 'Beskrivning', 'editable': False},
                {
                    'name': 'Ekonomisk livslängd (år)', 
                    'id': 'Ekonomisk livslängd', 
                    'editable': True,
                    'type': 'numeric'
                },
                {
                    'name': 'Maximal livslängd (år)', 
                    'id': 'Maximal livslängd', 
                    'editable': True,
                    'type': 'numeric'
                }
            ],
            data=df.to_dict('records'),
            editable=True,
            persistence=True,
            persisted_props=['data'],
            style_table={'overflowX': 'auto'},
            style_cell={
                'textAlign': 'left',
                'padding': '10px',
                'fontFamily': 'Arial, sans-serif'
            },
            style_header={
                'backgroundColor': 'rgb(230, 230, 230)',
                'fontWeight': 'bold'
            },
            style_data_conditional=[
                {
                    'if': {'state': 'active'},
                    'backgroundColor': 'rgba(0, 116, 217, 0.1)',
                    'border': '1px solid rgb(0, 116, 217)'
                }
            ]
        ),
        
        html.Div(id=f"{table_id}-validation", className="mt-2"),
        
        dbc.ButtonGroup([
            dbc.Button(
                "Applicera ändringar",
                id=f"{table_id}-apply-btn",
                color="primary",
                className="mt-3 me-2"
            ),
            dbc.Button(
                "Återställ",
                id=f"{table_id}-reset-btn",
                color="secondary",
                className="mt-3"
            )
        ])
    ])


def create_step_progress_indicator(
    completed_steps: List[int],
    total_steps: int = 4
) -> dbc.Progress:
    """
    Skapar progress bar för beräkningssteg.
    
    Args:
        completed_steps: Lista med slutförda steg (5, 6, 7, 8)
        total_steps: Totalt antal steg (default 4)
        
    Returns:
        Bootstrap Progress component
    """
    progress_value = (len(completed_steps) / total_steps) * 100
    
    step_labels = {
        5: "Steg 5: Åldrar & NUAV",
        6: "Steg 6: Avskrivningar",
        7: "Steg 7: Avkastning",
        8: "Steg 8: Sammanställning"
    }
    
    # Skapa progress bars för varje steg
    bars = []
    for step in [5, 6, 7, 8]:
        if step in completed_steps:
            bars.append(
                dbc.Progress(
                    value=25,
                    bar=True,
                    color="success",
                    label=step_labels[step].split(":")[0]
                )
            )
        else:
            bars.append(
                dbc.Progress(
                    value=25,
                    bar=True,
                    color="light",
                    label=step_labels[step].split(":")[0]
                )
            )
    
    return html.Div([
        dbc.Progress(bars, multi=True, className="mb-3"),
        html.Small(
            f"{len(completed_steps)} av {total_steps} steg slutförda",
            className="text-muted"
        )
    ])


def create_methodology_card(
    title: str,
    description: str,
    equations: Optional[List[str]] = None,
    expanded: bool = False
) -> dbc.Card:
    """
    Skapar expanderbar metodologikort med formler.
    
    Args:
        title: Titel på kortet
        description: Beskrivning av metodiken
        equations: Lista med LaTeX-ekvationer (optional)
        expanded: Om kortet ska vara expanderat från start
        
    Returns:
        Bootstrap Card med Collapse
    """
    card_id = f"methodology-{title.lower().replace(' ', '-')}"
    
    content = [html.P(description)]
    
    if equations:
        content.append(html.H6("Formler:", className="mt-3 mb-2"))
        for eq in equations:
            content.append(
                html.Div(
                    eq,
                    className="border rounded p-2 mb-2 bg-light font-monospace",
                    style={'fontSize': '0.9rem'}
                )
            )
    
    return dbc.Card([
        dbc.CardHeader(
            dbc.Button(
                [html.I(className="fas fa-info-circle me-2"), title],
                id=f"{card_id}-toggle",
                color="link",
                className="text-start w-100"
            )
        ),
        dbc.Collapse(
            dbc.CardBody(content),
            id=card_id,
            is_open=expanded
        )
    ], className="mb-3")


def create_company_info_alert(
    company_name: str,
    dmu_id: int,
    data_status: Dict[str, Any]
) -> dbc.Alert:
    """
    Skapar info-alert med företagsinformation.
    
    Args:
        company_name: Företagsnamn
        dmu_id: DMU-id
        data_status: Dict med info om data (antal nätverk, perioder, etc.)
        
    Returns:
        Bootstrap Alert component
    """
    return dbc.Alert([
        html.H5([
            html.I(className="fas fa-building me-2"),
            f"{company_name}"
        ], className="alert-heading"),
        html.Hr(),
        html.P([
            html.Strong("DMU: "), f"{dmu_id}", html.Br(),
            html.Strong("Nätverk: "), f"{data_status.get('networks', 'N/A')}", html.Br(),
            html.Strong("Tidsperioder: "), f"{data_status.get('periods', 'N/A')}"
        ], className="mb-0")
    ], color="info", className="mb-4")


def create_wacc_result_cards(
    re_nom: float,
    rd_nom: float,
    wacc_nom: float,
    wacc_real: float
) -> dbc.Row:
    """
    Skapar result cards för WACC-beräkning.
    
    Args:
        re_nom: Kostnad för eget kapital (nominell, efter skatt)
        rd_nom: Kostnad för skuld (nominell, före skatt)
        wacc_nom: WACC nominell, före skatt
        wacc_real: WACC real, före skatt
        
    Returns:
        Bootstrap Row med 4 cards
    """
    return dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("Re (nominell, efter skatt)", className="text-muted mb-2"),
                    html.H3(f"{re_nom*100:.2f} %", className="text-primary mb-0")
                ])
            ])
        ], width=3),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("Rd (nominell, före skatt)", className="text-muted mb-2"),
                    html.H3(f"{rd_nom*100:.2f} %", className="text-primary mb-0")
                ])
            ])
        ], width=3),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("WACC (nominell, före skatt)", className="text-muted mb-2"),
                    html.H3(f"{wacc_nom*100:.2f} %", className="text-primary mb-0")
                ])
            ])
        ], width=3),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("WACC (real, före skatt)", className="text-muted mb-2"),
                    html.H3(f"{wacc_real*100:.2f} %", className="text-success mb-0"),
                    html.Small("Används i Steg 7", className="text-muted")
                ])
            ])
        ], width=3)
    ], className="mb-4")
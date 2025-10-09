"""
Företagsportalen - Hem
=======================

Välkomstsida för inloggade företagsanvändare.
Visar översikt, status och planerade funktioner.
"""

import dash
from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc
import pandas as pd
from pathlib import Path
from typing import Dict, Any

# Import från backend (UI-agnostisk)
import auth


def layout(session_data: Dict[str, Any]):
    """
    Skapar layout för företagsportalen hem-sida.
    
    Args:
        session_data: Session state dict med användarinfo
        
    Returns:
        Dash layout
    """
    # Hämta företagsinformation
    user_dmu = auth.get_user_dmu(session_data)
    current_user = session_data.get('current_user', 'Företag')
    
    # Försök hämta företagsnamn från reconciliation
    company_name = get_company_name(user_dmu)
    
    return dbc.Container([
        # Header
        dbc.Row([
            dbc.Col([
                html.H1(f"Välkommen, {company_name}"),
                html.P(f"Du är inloggad som DMU {user_dmu}", className="text-muted") if user_dmu else None
            ])
        ], className="mb-4"),
        
        # Introduktion
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H5("Företagsportalen för intäktsramsreglering", className="mb-0")),
                    dbc.CardBody([
                        html.P([
                            "Denna portal ger dig tillgång till analyser och data som är specifikt relevanta ",
                            "för ditt företag inom ramen för intäktsramsregleringen."
                        ])
                    ])
                ], className="mb-4")
            ])
        ]),
        
        # Status
        dbc.Row([
            dbc.Col([
                html.H4("Företagsspecifika funktioner"),
                dbc.Alert([
                    html.Strong("Under utveckling"), " - Företagsportalen utvecklas kontinuerligt med nya funktioner"
                ], color="warning", className="mb-3")
            ])
        ]),
        
        # Planerade funktioner i två kolumner
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H6("Planerade funktioner", className="mb-0")),
                    dbc.CardBody([
                        html.H6("Mitt företags prestanda", className="mt-2"),
                        html.Ul([
                            html.Li("Din effektivitetsposition relativt andra företag"),
                            html.Li("Effektiviseringskrav och påverkan på påverkbara kostnader"),
                            html.Li("Utveckling över tid"),
                            html.Li("Detaljanalys per komponent")
                        ]),
                        
                        html.H6("Kapitalkostnadsanalys", className="mt-3"),
                        html.Ul([
                            html.Li("Påverkan av WACC-förändringar på ditt företag"),
                            html.Li("Breakdown av avskrivningar och avkastning"),
                            html.Li("Scenario-analys för olika räntelägen"),
                            html.Li("Jämförelse med branschgenomsnitt")
                        ])
                    ])
                ], className="mb-3")
            ], md=6),
            
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H6("Kommande funktioner", className="mb-0")),
                    dbc.CardBody([
                        html.H6("Branschpositionering", className="mt-2"),
                        html.Ul([
                            html.Li("Anonymiserad jämförelse med andra lokalnätsföretag"),
                            html.Li("Histogram och fördelningar där ditt företag markeras"),
                            html.Li("Quartiler och percentiler för olika nyckeltal"),
                            html.Li("Trender inom branschen")
                        ]),
                        
                        html.H6("Export och rapportering", className="mt-3"),
                        html.Ul([
                            html.Li("Företagsspecifika datautdrag"),
                            html.Li("Månadsrapporter och trendanalys"),
                            html.Li("Export till Excel för intern vidarebearbetning"),
                            html.Li("Anpassade dashboards för ledning")
                        ])
                    ])
                ], className="mb-3")
            ], md=6)
        ]),
        
        # Nuvarande tillgång
        html.Hr(),
        dbc.Row([
            dbc.Col([
                html.H4("Tillgänglig funktionalitet idag"),
                dbc.Alert([
                    html.H6("Temporär tillgång till analysverktyg", className="alert-heading"),
                    html.P([
                        "Under utvecklingsperioden har företag begränsad tillgång till analysverktygen. ",
                        "Kontakta utvecklingsteamet för specifika analysönskemål eller om du behöver företagsspecifik data."
                    ], className="mb-0")
                ], color="info")
            ])
        ], className="mb-4"),
        
        # Datasäkerhet
        dbc.Row([
            dbc.Col([
                dbc.Accordion([
                    dbc.AccordionItem([
                        html.H6("Vad kan jag förvänta mig av företagsportalen?"),
                        html.P([
                            html.Strong("Fokuserad användarupplevelse:"), html.Br(),
                            "• Endast data och analyser relevanta för ditt företag", html.Br(),
                            "• Förenklad navigation och tydliga insikter", html.Br(),
                            "• Automatisk filtrering till dina nät och anläggningar"
                        ]),
                        html.P([
                            html.Strong("Benchmarking med integritet:"), html.Br(),
                            "• Jämförelser med andra företag utan att avslöja specifika företagsdata", html.Br(),
                            "• Anonymiserad branschstatistik", html.Br(),
                            "• Positionering relativt medelvärden och kvartiler"
                        ]),
                        html.P([
                            html.Strong("Långsiktig planering:"), html.Br(),
                            "• Scenario-analys för olika regleringsalternativ", html.Br(),
                            "• Påverkan av effektiviseringskrav på din verksamhet", html.Br(),
                            "• WACC-känslighetsanalys"
                        ])
                    ], title="Förväntningar"),
                    
                    dbc.AccordionItem([
                        html.P([
                            html.Strong("Säker datahantering:"), html.Br(),
                            "• All företagdata hanteras separat och säkert", html.Br(),
                            "• Ingen data delas mellan olika företagsanvändare", html.Br(),
                            "• Krypterad lagring och överföring"
                        ]),
                        html.P([
                            html.Strong("Integritetsskydd:"), html.Br(),
                            "• Du ser endast din egen data och anonymiserade jämförelser", html.Br(),
                            "• Ingen möjlighet att identifiera andra företag i jämförelser", html.Br(),
                            "• Regelefterlevnad enligt GDPR och offentlighetslagen"
                        ]),
                        html.P([
                            html.Strong("Transparens:"), html.Br(),
                            "• Full insyn i vilka beräkningar som ligger bakom dina resultat", html.Br(),
                            "• Samma metodik som används av Energimarknadsinspektionen", html.Br(),
                            "• Möjlighet att följa hela beräkningskedjan"
                        ])
                    ], title="Datasäkerhet och integritet"),
                    
                    dbc.AccordionItem([
                        dbc.Row([
                            dbc.Col([
                                html.H6("Fas 1 (Pågående)"),
                                html.Ul([
                                    html.Li("Grundläggande företagsportal"),
                                    html.Li("Säker inloggning och datahantering"),
                                    html.Li("Företagsspecifik datafiltrering")
                                ]),
                                html.H6("Fas 2 (Q1 2025)"),
                                html.Ul([
                                    html.Li("Effektivitetsanalys per företag"),
                                    html.Li("WACC-påverkansanalys"),
                                    html.Li("Grundläggande branschpositionering")
                                ])
                            ], md=6),
                            dbc.Col([
                                html.H6("Fas 3 (Q2 2025)"),
                                html.Ul([
                                    html.Li("Avancerade jämförelseverktyg"),
                                    html.Li("Månadsrapporter och trendanalys"),
                                    html.Li("Interaktiva dashboards")
                                ]),
                                html.H6("Fas 4 (Q3 2025)"),
                                html.Ul([
                                    html.Li("Fullständig scenario-analys"),
                                    html.Li("Avancerade exportfunktioner"),
                                    html.Li("Anpassningsbara rapporter")
                                ])
                            ], md=6)
                        ])
                    ], title="Utvecklingsplan")
                ], start_collapsed=True)
            ])
        ], className="mb-4"),
        
        # Kontakt
        html.Hr(),
        dbc.Row([
            dbc.Col([
                html.H4("Kontakt och support"),
                dbc.Row([
                    dbc.Col([
                        html.H6("Utvecklingsteam:"),
                        html.P([
                            "Magne Björneholm (Huvudutvecklare)", html.Br(),
                            "Energimarknadsinspektionen", html.Br(),
                            html.Br(),
                            html.Strong("Teknisk support:"), html.Br(),
                            "Vid tekniska problem, kontakta utvecklingsteamet"
                        ])
                    ], md=6),
                    dbc.Col([
                        html.H6("Feedback och förbättringar:"),
                        html.P([
                            "• Förslag på nya funktioner välkomnas", html.Br(),
                            "• Rapportera buggar eller oväntade beteenden", html.Br(),
                            "• Användarstudier genomförs regelbundet"
                        ])
                    ], md=6)
                ])
            ])
        ])
        
    ], fluid=True)


def get_company_name(dmu: int) -> str:
    """
    Hämtar företagsnamn från reconciliation-fil.
    
    Args:
        dmu: DMU-nummer
        
    Returns:
        Företagsnamn eller "Ditt företag" om inget hittas
    """
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
    
    return f"DMU {dmu}" if dmu else "Ditt företag"
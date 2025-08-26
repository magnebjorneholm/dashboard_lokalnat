# Effektiviseringsdashboard för lokalnätsföretag

Detta är ett interaktivt Streamlit-dashboard som visualiserar och analyserar effektivitet och effektiviseringskrav för svenska elnätsföretag baserat på modellerna DEA, SFA och StoNED (via PyStoned).

## Funktioner

- **DEA-modell**: Data Envelopment Analysis med supereffektivitet, outlierdetektion, kravtrunkering.
- **SFA-modell**: Stokastisk frontieranalys via externt R-skript.
- **PyStoned-modell**: Semi-parametrisk ineffektivitetsmodell med QLE + KDE.
- **Jämför körningar**: Jämförelse av olika modellkörningar, korrelation, skillnader.

## Struktur

```
├── dashboard.py
├── app/
│   ├── data_loader.py
│   ├── dea_model.py
│   ├── sfa_model.py
│   ├── pystoned_model.py
│   ├── plots.py
│   └── run_logger.py
├── data/
│   └── Data_modeller.xlsx
├── runs/  # genereras automatiskt
├── requirements.txt
└── README.md
```

## Installation (lokalt)

```bash
git clone https://github.com/<ditt-användarnamn>/<repo-namn>.git
cd <repo-namn>
pip install -r requirements.txt
streamlit run dashboard.py
```

## Användning på Streamlit Cloud

1. Ladda upp denna kod till ett publikt GitHub-repo.
2. Gå till https://streamlit.io/cloud och logga in med GitHub.
3. Klicka på "New app".
4. Välj ditt repo, välj `dashboard.py` som fil.
5. Starta appen.

## Kommentarer

- SFA kräver att `Rscript` är installerat och att `app/sfa_r_model.R` finns.
- Resultat från körningar loggas i `runs/` och kan jämföras i dashboardet.
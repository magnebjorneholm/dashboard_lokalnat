# REGUMETRICA PIPELINE ARCHITECTURE DESIGN
**Version:** 1.0  
**Datum:** 2025-12-01  
**Syfte:** Svar på arkitekturfrågor och designrekommendationer

---

## SAMMANFATTNING OCH KÄRNREKOMMENDATIONER

### Övergripande rekommendation
Ersätt det nuvarande producer-registry-baserade systemet med en **explicit linjär pipeline** som följer dataflödet naturligt. Det nuvarande systemet är över-engineerat för det faktiska behovet: en linjär kedja där varje stage alltid triggar efterföljande stages.

### Fem kärnrekommendationer

1. **Funktionell pipeline-arkitektur (Option C)** - Funktioner utan klasser. Enklast att förstå, testa och underhålla för användare utan djup programmeringserfarenhet.

2. **Stage-baserad config (Option A)** - Strukturera config efter pipeline-stages med tydlig mapping till UI-terminologi. Behåller separation mellan användarens mentala modell (Parameters/Variables/Modules) och intern struktur.

3. **Explicit dependency declarations (Option A för FRÅGA A)** - Statisk deklaration av vilka config-nycklar som påverkar vilken stage. Hash-baserad automatisk detektion är överkomplext för 5 stages.

4. **Baseline-first strategi bekräftad** - All data finns i dataset, ingen komplex caching behövs. Ladda baseline en gång per session, jämför config mot baseline-config för att avgöra vilka stages som behöver köras.

5. **Batch-first implementation för kent_pipeline** - Refaktorera alla funktioner att hantera DataFrame med 148 företag (id_network som nyckel). Single-company är specialfall av batch.

---

## SVAR PÅ FRÅGORNA

### FRÅGA A: Dependency Tracking Implementation

**Rekommendation: Option 1 - Explicit comparison med explicit dependency declarations**

Motivering:
- Pipelinen har endast 5 stages med få config-parametrar
- Linjär kedja (pre_dea → dea → extraction → post_dea) gör cascading förutsägbart
- Hash-baserad detection är överkomplex och svårare att debugga

**Implementation:**

```python
# pipeline/config.py

STAGE_DEPENDENCIES = {
    'pre_dea': [
        'capex_method',      # baseline, wacc_scaling, parameter_adjustment, kent_full
        'wacc',              # float, None = use baseline
        'normvalue_adj',     # dict med justeringar eller None
        'lifetime_adj',      # dict med justeringar eller None
        'kent_file'          # UploadedFile eller None
    ],
    'dea': [
        'dea_method',        # baseline, dea, sfa, stoned (framtida)
        'dea_model_spec'     # {'inputs': [...], 'outputs': [...], 'rts': 'VRS'}
    ],
    'post_dea': [
        'effkrav_truncation',    # float 0-1
        'effkrav_iqr_mult',      # float
        'effkrav_outlier_fixed', # float (fast krav för outliers)
        'paverkbara_method'      # 'OPEX' eller 'TOTEX'
    ]
}

STAGE_ORDER = ['pre_dea', 'dea', 'extraction', 'post_dea']


def determine_stages_to_run(
    current_config: dict,
    baseline_config: dict
) -> list[str]:
    """
    Bestäm vilka stages som behöver köras baserat på config-ändringar.
    
    Returns:
        Lista med stage-namn i execution order
    """
    stages_to_run = []
    
    for stage in STAGE_ORDER:
        deps = STAGE_DEPENDENCIES.get(stage, [])
        
        # Om någon dependency ändrats -> stage behöver köras
        if any(current_config.get(d) != baseline_config.get(d) for d in deps):
            stages_to_run.append(stage)
    
    # Cascade: om pre_dea körs, måste dea och post_dea också köras
    if 'pre_dea' in stages_to_run:
        for s in ['dea', 'extraction', 'post_dea']:
            if s not in stages_to_run:
                stages_to_run.append(s)
    elif 'dea' in stages_to_run:
        for s in ['extraction', 'post_dea']:
            if s not in stages_to_run:
                stages_to_run.append(s)
    
    # Sortera i rätt ordning
    return [s for s in STAGE_ORDER if s in stages_to_run]
```

**Fördelar:**
- Explicit och lättläst
- Enkelt att utöka med nya stages (t.ex. quality_adjustment)
- Deterministiskt - samma config ger alltid samma stages
- Inga "magic" hash-beräkningar att debugga

---

### FRÅGA B: Error Handling i Pipeline

**Rekommendation: Fail-fast med tydlig felrapportering**

Om en stage failar ska hela pipelinen stoppas omedelbart. Användaren får tydlig information om:
1. Vilken stage som failade
2. Varför (teknisk och användarvänlig förklaring)
3. Förslag på åtgärd

**Implementation:**

```python
# pipeline/executor.py

from dataclasses import dataclass
from typing import Optional
import traceback


@dataclass
class PipelineError:
    """Strukturerad fel-information från pipeline."""
    stage: str
    error_type: str
    user_message: str
    technical_details: str
    suggested_action: str


class PipelineExecutionError(Exception):
    """Custom exception med strukturerad fel-info."""
    def __init__(self, error: PipelineError):
        self.error = error
        super().__init__(error.user_message)


def run_pipeline(
    config: dict,
    baseline: dict,
    user_dmu: int
) -> dict:
    """
    Kör pipeline med fail-fast error handling.
    
    Raises:
        PipelineExecutionError: Med strukturerad fel-info vid misslyckande
    """
    try:
        # Stage 1: Pre-DEA
        df_predea = run_pre_dea_stage(config, baseline)
        
    except Exception as e:
        raise PipelineExecutionError(PipelineError(
            stage='pre_dea',
            error_type=type(e).__name__,
            user_message='Fel vid beräkning av kapitalkostnader.',
            technical_details=traceback.format_exc(),
            suggested_action='Kontrollera KENT-fil eller parameterjusteringar.'
        ))
    
    try:
        # Stage 2: DEA
        if config.get('dea_method') == 'baseline':
            df_dea = baseline['dea_results']
        else:
            df_dea = run_dea_stage(df_predea, config.get('dea_model_spec'))
            
    except Exception as e:
        # DEA kan faila pga infeasible model
        if 'infeasible' in str(e).lower():
            raise PipelineExecutionError(PipelineError(
                stage='dea',
                error_type='InfeasibleModel',
                user_message='DEA-modellen kunde inte lösas med vald specifikation.',
                technical_details=str(e),
                suggested_action=(
                    'Prova att ändra inputs/outputs i modellspecifikationen. '
                    'Vanlig orsak: för få outputs relativt inputs.'
                )
            ))
        raise PipelineExecutionError(PipelineError(
            stage='dea',
            error_type=type(e).__name__,
            user_message='Fel vid effektivitetsberäkning.',
            technical_details=traceback.format_exc(),
            suggested_action='Kontakta support med teknisk information.'
        ))
    
    try:
        # Stage 3: Extraction
        df_company = extract_company(df_dea, user_dmu)
        
    except KeyError:
        raise PipelineExecutionError(PipelineError(
            stage='extraction',
            error_type='CompanyNotFound',
            user_message=f'Företag med DMU {user_dmu} hittades inte i data.',
            technical_details=f'DMU {user_dmu} finns ej i DEA-resultat.',
            suggested_action='Kontrollera att rätt företag är inloggat.'
        ))
    
    try:
        # Stage 4: Post-DEA
        intaktsram = run_post_dea_stage(df_company, config, baseline)
        
    except Exception as e:
        raise PipelineExecutionError(PipelineError(
            stage='post_dea',
            error_type=type(e).__name__,
            user_message='Fel vid beräkning av intäktsram.',
            technical_details=traceback.format_exc(),
            suggested_action='Kontrollera effektiviseringskrav-parametrar.'
        ))
    
    return {
        'intaktsram': intaktsram,
        'df_predea': df_predea,
        'df_dea': df_dea,
        'df_company': df_company
    }
```

**UI-integration:**

```python
# I Streamlit UI

try:
    results = run_pipeline(config, baseline, user_dmu)
    st.success("Beräkning slutförd!")
    
except PipelineExecutionError as e:
    st.error(f"**{e.error.user_message}**")
    st.warning(f"*{e.error.suggested_action}*")
    
    with st.expander("Teknisk information"):
        st.code(e.error.technical_details)
```

---

### FRÅGA C: Concurrent Users och Baseline Sharing

**Rekommendation: Ladda baseline separat per session**

Motivering:
1. **Enkelhet:** Ingen delad state = inga concurrency-problem
2. **Memory är acceptabelt:** 3 DataFrames × ~10MB = ~30MB per session. Med Render Standard (2GB) klarar vi ~50 samtidiga användare.
3. **Streamlit-design:** st.session_state är designat för per-session isolation

**Implementation:**

```python
# pipeline/baseline.py

import streamlit as st
import pandas as pd


def load_baseline_data() -> dict:
    """
    Laddar all baseline-data för en session.
    Använder st.cache_data för fil-caching men varje session
    får sina egna DataFrame-kopior.
    """
    return {
        'df_all_companies': _load_data_modeller(),
        'dea_results': _load_eis_dea(),
        'capbase_a': _load_capbase_a(),
        'sdf_data': _load_sdf_data(),
        'reconciliation': _load_reconciliation()
    }


@st.cache_data
def _load_data_modeller() -> pd.DataFrame:
    """Cachad laddning av Data_modeller.xlsx"""
    return pd.read_excel(
        'data/Data_modeller.xlsx',
        sheet_name='Körning'
    )


@st.cache_data
def _load_eis_dea() -> pd.DataFrame:
    """Cachad laddning av EIs_DEA.xlsx"""
    return pd.read_excel(
        'data/EIs_DEA.xlsx',
        sheet_name='Körning'
    )


@st.cache_data
def _load_capbase_a() -> pd.DataFrame:
    """Cachad laddning av capbase_a.parquet"""
    return pd.read_parquet('data/capbase_a.parquet')


@st.cache_data
def _load_sdf_data() -> dict:
    """Cachad laddning av SDF-data"""
    ir_sheet = pd.read_excel(
        'data/Löpande_kostnader_från_SDF_2024-27.xlsx',
        sheet_name='IR 2024-2027'
    )
    paverkbara_sheet = pd.read_excel(
        'data/Löpande_kostnader_från_SDF_2024-27.xlsx',
        sheet_name='Påverkbara'
    )
    opav_sheet = pd.read_excel(
        'data/Löpande_kostnader_från_SDF_2024-27.xlsx',
        sheet_name='Opåverkbara'
    )
    return {
        'ir': ir_sheet,
        'paverkbara': paverkbara_sheet,
        'opaverkbara': opav_sheet
    }


@st.cache_data
def _load_reconciliation() -> pd.DataFrame:
    """Cachad laddning av ID-mappning"""
    return pd.read_csv('data/reconciliation_id_network_firm_dmu.csv')
```

**Session state struktur:**

```python
# I streamlit_app.py vid startup

if 'baseline' not in st.session_state:
    with st.spinner("Laddar data..."):
        st.session_state.baseline = load_baseline_data()
        
        # Baseline config - alla värden som motsvarar "ingen ändring"
        st.session_state.baseline_config = {
            'capex_method': 'baseline',
            'wacc': 0.0453,  # Ei's baseline WACC
            'normvalue_adj': None,
            'lifetime_adj': None,
            'kent_file': None,
            'dea_method': 'baseline',
            'dea_model_spec': None,
            'effkrav_truncation': 0.30,
            'effkrav_iqr_mult': 2.0,
            'effkrav_outlier_fixed': 0.01,
            'paverkbara_method': 'OPEX'
        }
```

---

### Architectural Question 1: Pipeline Class Design

**Rekommendation: Option C - Functional Pipeline**

Motivering:
- Enklast att läsa och förstå
- Lätt att testa varje funktion isolerat
- Ingen implicit state i klasser
- Passar nationalekonomister utan djup OOP-erfarenhet

**Implementation:**

```python
# pipeline/executor.py

import pandas as pd
from typing import Optional

from pipeline.stages.pre_dea import run_pre_dea
from pipeline.stages.dea import run_dea
from pipeline.stages.extraction import extract_company
from pipeline.stages.post_dea import run_post_dea
from pipeline.config import determine_stages_to_run


def run_pipeline(
    config: dict,
    baseline: dict,
    user_dmu: int
) -> dict:
    """
    Huvudfunktion för pipeline-execution.
    
    Args:
        config: Användarens konfiguration
        baseline: Baseline-data (df_all_companies, dea_results, etc.)
        user_dmu: Inloggat företags DMU
        
    Returns:
        Dict med intäktsram och mellanresultat
    """
    # Bestäm vilka stages som behöver köras
    stages = determine_stages_to_run(config, baseline.get('config', {}))
    
    # Stage 1: Pre-DEA
    if 'pre_dea' in stages:
        df_predea = run_pre_dea(config, baseline)
    else:
        df_predea = baseline['df_all_companies']
    
    # Stage 2: DEA
    if 'dea' in stages:
        df_dea = run_dea(df_predea, config.get('dea_model_spec'))
    else:
        df_dea = baseline['dea_results']
    
    # Stage 3: Extraction (alltid körs - snabbt)
    df_company = extract_company(df_dea, user_dmu)
    
    # Stage 4: Post-DEA
    intaktsram = run_post_dea(df_company, config, baseline, user_dmu)
    
    return {
        'intaktsram': intaktsram,
        'intermediate': {
            'df_predea': df_predea,
            'df_dea': df_dea,
            'df_company': df_company
        },
        'stages_run': stages
    }
```

**Varför inte Option A (Monolithic class)?**
- Döljer komplexitet bakom self.cache
- Svårare att testa individuella stages
- Lätt att få implicit state-beroenden

**Varför inte Option B (Stage-based classes)?**
- Onödig abstraktion för 5 stages
- Kräver interface-definition och registrering
- Overhead utan tydlig vinst

---

### Architectural Question 2: Config Structure

**Rekommendation: Option A - Stage-based config med UI-mapping layer**

Strukturera config efter pipeline-stages internt, men exponera Parameters/Variables/Modules till UI.

**Config-struktur:**

```python
# Intern struktur (pipeline)
pipeline_config = {
    'pre_dea': {
        'method': 'wacc_scaling',  # baseline, wacc_scaling, parameter_adj, kent_full
        'wacc': 0.05,
        'normvalue_adjustments': None,
        'lifetime_adjustments': None,
        'kent_file': None
    },
    'dea': {
        'method': 'dea',  # baseline, dea, sfa, stoned
        'model_spec': {
            'inputs': ['CAPEX', 'OPEXp'],
            'outputs': ['CU', 'MW', 'NS'],
            'rts': 'VRS',
            'orientation': 'input'
        }
    },
    'post_dea': {
        'effkrav': {
            'truncation': 0.30,
            'iqr_multiplier': 2.0,
            'outlier_fixed_rate': 0.01
        },
        'paverkbara_method': 'OPEX'
    }
}
```

**UI-mapping layer:**

```python
# pipeline/ui_mapping.py

def ui_to_pipeline_config(
    parameters: dict,
    variables: dict,
    modules: dict
) -> dict:
    """
    Översätter UI-terminologi till pipeline-config.
    
    Args:
        parameters: Uniforma värden (WACC, normvärden, livslängder)
        variables: Företagsspecifika värden (KENT-fil)
        modules: Metodval (DEA/SFA, OPEX/TOTEX)
        
    Returns:
        Pipeline-config struktur
    """
    # Bestäm pre_dea method baserat på vad som är ifyllt
    if variables.get('kent_file') is not None:
        pre_dea_method = 'kent_full'
    elif (parameters.get('normvalue_adj') is not None or 
          parameters.get('lifetime_adj') is not None):
        pre_dea_method = 'parameter_adjustment'
    elif parameters.get('wacc') != 0.0453:  # Ej baseline WACC
        pre_dea_method = 'wacc_scaling'
    else:
        pre_dea_method = 'baseline'
    
    return {
        'pre_dea': {
            'method': pre_dea_method,
            'wacc': parameters.get('wacc', 0.0453),
            'normvalue_adjustments': parameters.get('normvalue_adj'),
            'lifetime_adjustments': parameters.get('lifetime_adj'),
            'kent_file': variables.get('kent_file')
        },
        'dea': {
            'method': modules.get('efficiency_method', 'baseline'),
            'model_spec': modules.get('dea_model_spec')
        },
        'post_dea': {
            'effkrav': {
                'truncation': parameters.get('effkrav_truncation', 0.30),
                'iqr_multiplier': parameters.get('effkrav_iqr_mult', 2.0),
                'outlier_fixed_rate': parameters.get('effkrav_outlier_fixed', 0.01)
            },
            'paverkbara_method': modules.get('paverkbara_method', 'OPEX')
        }
    }


def pipeline_to_ui_config(pipeline_config: dict) -> tuple[dict, dict, dict]:
    """
    Omvänd mapping: pipeline-config → UI-terminologi.
    Används för att visa nuvarande konfiguration i UI.
    """
    cfg = pipeline_config
    
    parameters = {
        'wacc': cfg['pre_dea']['wacc'],
        'normvalue_adj': cfg['pre_dea']['normvalue_adjustments'],
        'lifetime_adj': cfg['pre_dea']['lifetime_adjustments'],
        'effkrav_truncation': cfg['post_dea']['effkrav']['truncation'],
        'effkrav_iqr_mult': cfg['post_dea']['effkrav']['iqr_multiplier'],
        'effkrav_outlier_fixed': cfg['post_dea']['effkrav']['outlier_fixed_rate']
    }
    
    variables = {
        'kent_file': cfg['pre_dea']['kent_file']
    }
    
    modules = {
        'capex_method': cfg['pre_dea']['method'],
        'efficiency_method': cfg['dea']['method'],
        'dea_model_spec': cfg['dea']['model_spec'],
        'paverkbara_method': cfg['post_dea']['paverkbara_method']
    }
    
    return parameters, variables, modules
```

---

### Architectural Question 3: Dependency Tracking

**Se FRÅGA A ovan för fullständigt svar.**

Sammanfattning: Explicit dependency declarations är mest robust för en pipeline med 5 stages och ~15 config-parametrar. Hash-baserad detection skulle vara overhead utan motsvarande nytta.

---

### Architectural Question 4: Batch Processing för Kent Pipeline

**Rekommendation: Unified batch implementation med id_network som nyckel**

Alla funktioner ska designas för att hantera DataFrame med alla 148 företag. Single-company är bara ett specialfall (DataFrame med 1 rad filtrerat på id_network).

**Refactoring-strategi:**

```python
# pipeline/stages/kent_pipeline.py

import pandas as pd
import numpy as np


def calculate_ages_and_nuav_batch(
    capbase_all: pd.DataFrame,
    time_periods: list[int] = list(range(229, 237))
) -> pd.DataFrame:
    """
    Beräknar åldrar och NUAV för alla företag och alla tidsperioder.
    
    Args:
        capbase_all: DataFrame med alla komponenter för alla 148 företag
                     Måste innehålla kolumner: id_network, time_from, nuav_2022, ekdep, maxdep
        time_periods: Lista med tidskoder (default: 229-236 för 2024-2027)
        
    Returns:
        DataFrame med nya kolumner per tidsperiod:
        - age_component_{time}
        - nuav_ord_{time}
        - nuav_tail_{time}
    """
    result = capbase_all.copy()
    
    for time in time_periods:
        # Ålder vid denna tidpunkt
        result[f'age_component_{time}'] = time - result['time_from']
        
        # Ordinarie NUAV (inom ekonomisk livslängd)
        age = result[f'age_component_{time}']
        in_ord = age <= result['ekdep']
        result[f'nuav_ord_{time}'] = np.where(in_ord, result['nuav_2022'], 0)
        
        # Svans-NUAV (mellan ekonomisk och maximal livslängd)
        in_tail = (age > result['ekdep']) & (age <= result['maxdep'])
        result[f'nuav_tail_{time}'] = np.where(in_tail, result['nuav_2022'], 0)
    
    return result


def calculate_depreciation_batch(
    df: pd.DataFrame,
    time_periods: list[int] = list(range(229, 237))
) -> pd.DataFrame:
    """
    Beräknar avskrivningar för alla företag och alla tidsperioder.
    
    Returns:
        DataFrame med kolumner: dep_ord_{time}, dep_tail_{time}
    """
    result = df.copy()
    
    for time in time_periods:
        # Ordinarie avskrivning: NUAV / ekdep
        result[f'dep_ord_{time}'] = (
            result[f'nuav_ord_{time}'] / result['ekdep']
        ).fillna(0)
        
        # Svans-avskrivning: NUAV / (maxdep - ekdep)
        tail_life = result['maxdep'] - result['ekdep']
        result[f'dep_tail_{time}'] = (
            result[f'nuav_tail_{time}'] / tail_life.replace(0, np.nan)
        ).fillna(0)
    
    return result


def calculate_returns_batch(
    df: pd.DataFrame,
    wacc: float,
    time_periods: list[int] = list(range(229, 237))
) -> pd.DataFrame:
    """
    Beräknar avkastning för alla företag och alla tidsperioder.
    
    Args:
        df: DataFrame med nuav_ord_{time} och nuav_tail_{time}
        wacc: Kalkylränta (real, före skatt)
        
    Returns:
        DataFrame med kolumner: return_ord_{time}, return_tail_{time}
    """
    result = df.copy()
    
    # Halvårs-ränta
    r_half = wacc / 2
    
    for time in time_periods:
        # Avkastning = genomsnittlig NUAV × ränta
        # (förenkling: använder period-start värde × halvårsränta)
        result[f'return_ord_{time}'] = result[f'nuav_ord_{time}'] * r_half
        result[f'return_tail_{time}'] = result[f'nuav_tail_{time}'] * r_half
    
    return result


def aggregate_capcost_by_network_and_year(
    df: pd.DataFrame
) -> pd.DataFrame:
    """
    Aggregerar kapitalkostnader per id_network och år.
    
    Returns:
        DataFrame med kolumner:
        - id_network
        - year (2024, 2025, 2026, 2027)
        - Avskrivning
        - Avkastning
        - CAPEX
        - Avskrivning_periodsumma
        - Avkastning_periodsumma
        - CAPEX_periodsumma
    """
    # Tidskod → År mapping
    YEAR_TO_CODES = {
        2024: [229, 230],
        2025: [231, 232],
        2026: [233, 234],
        2027: [235, 236]
    }
    
    rows = []
    
    for id_network, group in df.groupby('id_network'):
        for year, codes in YEAR_TO_CODES.items():
            dep_ord = sum(group[f'dep_ord_{t}'].sum() for t in codes)
            dep_tail = sum(group[f'dep_tail_{t}'].sum() for t in codes)
            ret_ord = sum(group[f'return_ord_{t}'].sum() for t in codes)
            ret_tail = sum(group[f'return_tail_{t}'].sum() for t in codes)
            
            rows.append({
                'id_network': id_network,
                'year': year,
                'Avskrivning': dep_ord + dep_tail,
                'Avkastning': ret_ord + ret_tail,
                'CAPEX': dep_ord + dep_tail + ret_ord + ret_tail
            })
    
    yearly = pd.DataFrame(rows)
    
    # Lägg till periodsummor
    period_sums = yearly.groupby('id_network').agg({
        'Avskrivning': 'sum',
        'Avkastning': 'sum',
        'CAPEX': 'sum'
    }).rename(columns={
        'Avskrivning': 'Avskrivning_periodsumma',
        'Avkastning': 'Avkastning_periodsumma',
        'CAPEX': 'CAPEX_periodsumma'
    })
    
    yearly = yearly.merge(period_sums, on='id_network')
    
    return yearly


def extract_capex_for_dea(aggregated: pd.DataFrame) -> pd.DataFrame:
    """
    Extraherar CAPEX för år 2024 i format för DEA.
    
    Returns:
        DataFrame med kolumner: id_network, CAPEX (år 2024), Avskrivning, Avkastning
    """
    year_2024 = aggregated[aggregated['year'] == 2024].copy()
    return year_2024[['id_network', 'CAPEX', 'Avskrivning', 'Avkastning']]
```

**Användning för single-company (KENT-upload):**

```python
def process_kent_file_for_single_company(
    kent_file,
    user_network_id: int,
    baseline_capbase: pd.DataFrame,
    wacc: float
) -> pd.DataFrame:
    """
    Processerar KENT-fil för ett företag och kör beräkningskedjan.
    
    Returns:
        Aggregerad kapitalkostnad för alla 148 företag
        (147 från baseline + 1 från KENT)
    """
    # Steg 1-4: Bygg capbase_a från KENT
    kent_capbase = build_capbase_a_from_kent(kent_file, user_network_id)
    
    # Ersätt företagets data i baseline
    baseline_without_user = baseline_capbase[
        baseline_capbase['id_network'] != user_network_id
    ]
    combined_capbase = pd.concat([baseline_without_user, kent_capbase])
    
    # Steg 5-8: Kör beräkningskedja för ALLA 148
    step5 = calculate_ages_and_nuav_batch(combined_capbase)
    step6 = calculate_depreciation_batch(step5)
    step7 = calculate_returns_batch(step6, wacc)
    aggregated = aggregate_capcost_by_network_and_year(step7)
    
    return aggregated
```

---

### Baseline-First Strategy: Bekräftelse

**Strategin är optimal.** Bekräftar att baseline-first eliminerar behovet för komplex caching.

**Argument för:**

1. **All data finns i dataset:**
   - Pre-DEA baseline: Data_modeller.xlsx
   - DEA baseline: EIs_DEA.xlsx
   - Post-DEA baseline: SDF + EIs_DEA.xlsx

2. **Jämförelse är tillräckligt:**
   ```python
   if config['capex_method'] == 'baseline':
       df_predea = baseline['df_all_companies']  # Direkt, ingen beräkning
   ```

3. **Memory är acceptabelt:**
   - Data_modeller: ~2MB
   - EIs_DEA: ~1MB
   - capbase_a: ~50MB (parquet, komprimerat)
   - SDF: ~5MB
   - **Total: ~60MB per session**

4. **Streamlit's cache_data hanterar fil-laddning:**
   - Filer laddas från disk endast en gång
   - Varje session får egen DataFrame-kopia (copy-on-read)

**Edge cases där caching INTE behövs:**

| Scenario | Hantering |
|----------|-----------|
| Användare ändrar config ofta | Varje ändring triggar ny beräkning - OK (<5s) |
| Användare går tillbaka till baseline | Använd baseline direkt - 0s |
| Flera cases samtidigt | Varje case är en config, inte cachad beräkning |
| Session timeout | Ladda om baseline - ~2s |

**Ett edge case där vi KAN vilja cacha:**

Om kent_pipeline (steg 5-8) tar >5 sekunder för alla 148 företag kan det vara värt att cacha resultatet av parameter-ändringar. Men detta är en optimering som kan läggas till senare om det visar sig behövas.

---

## REKOMMENDERAD FILSTRUKTUR

```
regumetrica/
├── app.py                          # Streamlit entry point
│
├── pipeline/
│   ├── __init__.py
│   ├── executor.py                 # run_pipeline() huvudfunktion
│   ├── config.py                   # STAGE_DEPENDENCIES, determine_stages()
│   ├── ui_mapping.py               # UI ↔ pipeline config översättning
│   ├── errors.py                   # PipelineError, PipelineExecutionError
│   │
│   └── stages/
│       ├── __init__.py
│       ├── baseline.py             # load_baseline_data()
│       ├── pre_dea.py              # run_pre_dea(), CAPEX-metoder
│       ├── kent_pipeline.py        # Steg 5-8 batch processing
│       ├── capbase_prep.py         # Steg 1-4 KENT → capbase_a
│       ├── dea.py                  # run_dea(), DEA-modell
│       ├── extraction.py           # extract_company()
│       └── post_dea.py             # run_post_dea(), effkrav, intäktsram
│
├── calculations/
│   ├── __init__.py
│   ├── wacc.py                     # WACC från CAPM
│   ├── effektiviseringskrav.py     # Effkrav från potential
│   ├── paverkbara.py               # Påverkbara kostnader-beräkning
│   └── intaktsram.py               # Summering av intäktsram
│
├── ui/
│   ├── __init__.py
│   ├── components/
│   │   ├── parameter_inputs.py     # WACC, normvärden, livslängder
│   │   ├── kent_upload.py          # KENT-fil uppladdning
│   │   ├── dea_config.py           # DEA-modellspecifikation
│   │   └── results_display.py      # Intäktsram-visning
│   ├── pages/
│   │   ├── setup.py                # Case setup
│   │   ├── configuration.py        # Parameter/Variable/Module config
│   │   ├── execution.py            # Kör beräkning
│   │   └── results.py              # Visa resultat
│   └── styles.py                   # CSS, färgschema
│
├── data/                           # Datafiler (gitignored i prod)
│   ├── Data_modeller.xlsx
│   ├── EIs_DEA.xlsx
│   ├── capbase_a.parquet
│   ├── Löpande_kostnader_från_SDF_2024-27.xlsx
│   └── reconciliation_id_network_firm_dmu.csv
│
└── tests/
    ├── test_pipeline.py
    ├── test_stages/
    │   ├── test_pre_dea.py
    │   ├── test_dea.py
    │   └── test_post_dea.py
    └── fixtures/
        └── sample_data.py
```

---

## NAMNKONVENTIONER

### DataFrames

| Namn | Scope | Innehåll |
|------|-------|----------|
| `df_all_companies` | 148 rader | Baseline data från Data_modeller |
| `df_all_companies_modified` | 148 rader | Efter CAPEX-modifiering |
| `df_dea_results` | 148 rader | Efficiency, potential, is_outlier |
| `df_single_company` | 1 rad | Extraherat för inloggat företag |
| `capbase_all` | ~510k rader | Alla komponenter för alla företag |
| `capbase_single` | Varierar | Komponenter för ett företag |

### CAPEX-variabler

| Namn | Tidsperiod | Användning |
|------|------------|------------|
| `CAPEX` (i df_all_companies) | År 2024 | DEA-input |
| `CAPEX_year` | Ett år (2024/2025/2026/2027) | Mellanresultat |
| `CAPEX_periodsumma` | 2024-2027 | Intäktsram |
| `Avskrivning` | År 2024 | DEA-input (uppdelning) |
| `Avkastning` | År 2024 | DEA-input (uppdelning) |
| `Avskrivning_periodsumma` | 2024-2027 | Intäktsram |
| `Avkastning_periodsumma` | 2024-2027 | Intäktsram |

### WACC-variabler

| Namn | Typ | Beskrivning |
|------|-----|-------------|
| `wacc_baseline` | float | Ei's baseline = 0.0453 |
| `wacc_new` | float | Användarens valda WACC |
| `wacc_scaling_factor` | float | wacc_new / wacc_baseline |

### Config-nycklar

| UI-term | Config-nyckel | Typ | Möjliga värden |
|---------|---------------|-----|----------------|
| Parameter: WACC | `wacc` | float | 0.01 - 0.10 |
| Parameter: Normvärde | `normvalue_adj` | dict/None | {cat: factor} |
| Parameter: Livslängd | `lifetime_adj` | dict/None | {cat: delta} |
| Variable: KENT-fil | `kent_file` | UploadedFile/None | - |
| Module: CAPEX-metod | `capex_method` | str | baseline, wacc_scaling, parameter_adj, kent_full |
| Module: Effektivitetsmetod | `dea_method` | str | baseline, dea, sfa, stoned |
| Module: Påverkbara-metod | `paverkbara_method` | str | OPEX, TOTEX |

---

## MIGRATIONSPLAN

### Fas 1: Baseline-laddning (Dag 1-2)

**Mål:** Få baseline-data att laddas korrekt

1. Skapa `pipeline/stages/baseline.py`
2. Implementera `load_baseline_data()`
3. Verifiera att alla 148 företag laddas
4. Verifiera att EIs_DEA.xlsx ger korrekt Effkrav_proc

**Test:** Jämför laddad data mot Excel-filer manuellt.

### Fas 2: Pre-DEA Stage (Dag 3-5)

**Mål:** Implementera alla fyra CAPEX-metoder

1. Skapa `pipeline/stages/pre_dea.py`
2. Implementera Metod 1: Baseline (trivial - return baseline)
3. Implementera Metod 2: WACC-skalning
4. Refaktorera `kent_pipeline.py` för batch (Metod 3)
5. Integrera `capbase_prep.py` för KENT (Metod 4)

**Test:** Jämför CAPEX-output mot Ei's Excel för kända parametrar.

### Fas 3: DEA Stage (Dag 6-7)

**Mål:** DEA-beräkning med modellspecifikation

1. Skapa `pipeline/stages/dea.py`
2. Återanvänd `dea_model.py` (PuLP-implementation)
3. Lägg till baseline-check (använd EIs_DEA om baseline)
4. Verifiera outlier-identifiering

**Test:** Jämför efficiency mot EIs_DEA.xlsx för baseline.

### Fas 4: Post-DEA Stage (Dag 8-10)

**Mål:** Effektiviseringskrav och intäktsram

1. Skapa `pipeline/stages/post_dea.py`
2. Implementera `calculate_effkrav()` från potential
3. Implementera `calculate_paverkbara()` med OPEX/TOTEX
4. Implementera `calculate_intaktsram()` med alla komponenter

**Test:** Jämför intäktsram mot SDF för kända företag (t.ex. REL00001).

### Fas 5: Pipeline Integration (Dag 11-12)

**Mål:** Hela pipelinen körs end-to-end

1. Skapa `pipeline/executor.py`
2. Implementera `run_pipeline()`
3. Implementera `determine_stages_to_run()`
4. Lägg till error handling

**Test:** Kör hela pipelinen med baseline config, verifiera mot SDF.

### Fas 6: UI Integration (Dag 13-15)

**Mål:** Streamlit UI kopplas till pipeline

1. Uppdatera `app.py` för ny pipeline
2. Skapa UI-komponenter för config
3. Implementera results display
4. Testa alla CAPEX-metoder via UI

**Test:** Manuell testning av hela flödet.

---

## STAGE-KONTRAKT

### Stage 1: Baseline Loading

```python
def load_baseline_data() -> dict:
    """
    OUTPUT CONTRACT:
    {
        'df_all_companies': pd.DataFrame
            Kolumner: [DMU, REId, Företag, OPEXp, CAPEX, Avskrivning, 
                       Avkastning, CU, MW, NS, MWhl, MWhh]
            Rader: 148
            
        'dea_results': pd.DataFrame
            Kolumner: [DMU, REId, Företag, Effektivitet, Supereffektivitet,
                       potential, Effkrav_proc]
            Rader: 148
            
        'capbase_a': pd.DataFrame
            Kolumner: [id_component, id_network, time_from, nuav_2022, 
                       ekdep, maxdep, cat_encode, ...]
            Rader: ~510,000
            
        'sdf_data': dict
            {'ir': pd.DataFrame, 'paverkbara': pd.DataFrame, 
             'opaverkbara': pd.DataFrame}
            
        'reconciliation': pd.DataFrame
            Kolumner: [DMU, id_network, REId, Företag]
            Rader: 148
    }
    """
```

### Stage 2: Pre-DEA

```python
def run_pre_dea(
    config: dict,
    baseline: dict
) -> pd.DataFrame:
    """
    INPUT CONTRACT:
        config['pre_dea']['method']: str
            'baseline' | 'wacc_scaling' | 'parameter_adjustment' | 'kent_full'
        config['pre_dea']['wacc']: float (för wacc_scaling)
        config['pre_dea']['normvalue_adjustments']: dict | None
        config['pre_dea']['lifetime_adjustments']: dict | None
        config['pre_dea']['kent_file']: UploadedFile | None
        
        baseline: dict från load_baseline_data()
        
    OUTPUT CONTRACT:
        pd.DataFrame med kolumner:
            [DMU, REId, Företag, CAPEX, OPEXp, CU, MW, NS, MWhl, MWhh]
        Rader: 148
        
        CAPEX = Kapitalkostnad för år 2024 (tidskod 229+230)
    """
```

### Stage 3: DEA

```python
def run_dea(
    df_predea: pd.DataFrame,
    model_spec: dict
) -> pd.DataFrame:
    """
    INPUT CONTRACT:
        df_predea: pd.DataFrame med kolumner
            [DMU, REId, Företag, CAPEX, OPEXp, CU, MW, NS, MWhl, MWhh]
        Rader: 148
        
        model_spec: {
            'inputs': list[str]  # t.ex. ['CAPEX', 'OPEXp']
            'outputs': list[str] # t.ex. ['CU', 'MW', 'NS']
            'rts': str           # 'VRS' | 'CRS'
            'orientation': str   # 'input' | 'output'
        }
        
    OUTPUT CONTRACT:
        pd.DataFrame med kolumner:
            [DMU, REId, Företag, efficiency, super_efficiency, 
             potential, is_outlier]
        Rader: 148
        
        efficiency: float 0-1 (teknisk effektivitet)
        potential: float 0-1 (effektiviseringspotential)
        is_outlier: bool
    """
```

### Stage 4: Extraction

```python
def extract_company(
    df_dea: pd.DataFrame,
    user_dmu: int
) -> pd.DataFrame:
    """
    INPUT CONTRACT:
        df_dea: pd.DataFrame med 148 rader
        user_dmu: int (DMU för inloggat företag)
        
    OUTPUT CONTRACT:
        pd.DataFrame med 1 rad
        Samma kolumner som df_dea
        
    RAISES:
        KeyError om user_dmu inte finns i df_dea
    """
```

### Stage 5: Post-DEA

```python
def run_post_dea(
    df_company: pd.DataFrame,
    config: dict,
    baseline: dict,
    user_dmu: int
) -> dict:
    """
    INPUT CONTRACT:
        df_company: pd.DataFrame med 1 rad
            Kolumner: [DMU, potential, is_outlier, ...]
            
        config['post_dea']['effkrav']: {
            'truncation': float 0-1,
            'iqr_multiplier': float,
            'outlier_fixed_rate': float
        }
        config['post_dea']['paverkbara_method']: 'OPEX' | 'TOTEX'
        
        baseline: dict med 'sdf_data' för opåverkbara etc.
        user_dmu: int
        
    OUTPUT CONTRACT:
        dict med struktur:
        {
            'Intaktsram_Total': float,  # Periodsumma 2024-2027
            'Kapitalkostnad_Total': float,
            'Avskrivning_Total': float,
            'Avkastning_Total': float,
            'Paverkbara_Total': float,
            'Opaverkbara_Total': float,
            'Flexibilitet': float,
            'Avbrottsersattning': float,
            'Avdrag_Statligt_Stod': float,
            'Effkrav_proc': float,
            'per_year': {
                2024: {...},
                2025: {...},
                2026: {...},
                2027: {...}
            }
        }
    """
```

---

## AVSLUTANDE KOMMENTARER

### Kritiska beslut sammanfattade

1. **Funktionell pipeline** - Inga klasser, bara rena funktioner
2. **Explicit dependencies** - Statisk deklaration, inte runtime-detection
3. **Baseline-first** - Ingen caching, jämför mot baseline
4. **Batch-first för kent_pipeline** - id_network som nyckel
5. **UI-mapping layer** - Separera UI-terminologi från intern struktur

### Nästa steg

1. **Godkänn arkitektur** - Läs igenom och bekräfta design
2. **Börja med Fas 1** - Baseline-laddning
3. **Iterera** - Varje fas levererar fungerande kod

### Risker att bevaka

| Risk | Mitigation |
|------|------------|
| kent_pipeline tar >5s för 148 företag | Optimera med numpy vectorization, överväg caching |
| Memory overflow med stora KENT-filer | Validera filstorlek vid upload |
| DEA infeasible med vissa modellspec | Förtydlig UI med rekommendationer |
| SFA/StoNED integration | Design redan stödjer via dea_method |

---

**Dokumentslut**

*Detta dokument ska användas som referens för implementation av den nya pipeline-arkitekturen.*

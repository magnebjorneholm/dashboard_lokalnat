# ARKITEKTURSVAR: Regumetrica Pipeline Redesign

**Version:** 1.0  
**Datum:** 2025-01-XX  
**Från:** Claude Opus  
**Till:** Regumetrica development team  
**Relaterat dokument:** PROMPT_1_ARCHITECTURE.md

---

## INNEHÅLLSFÖRTECKNING

1. [Sammanfattning](#1-sammanfattning)
2. [Svar på Design Questions](#2-svar-på-design-questions)
3. [Svar på Architectural Questions](#3-svar-på-architectural-questions)
4. [Bekräftelse: Baseline-First Strategy](#4-bekräftelse-baseline-first-strategy)
5. [Rekommenderad Filstruktur](#5-rekommenderad-filstruktur)
6. [Namnkonventioner](#6-namnkonventioner)
7. [Migrationsplan](#7-migrationsplan)
8. [Appendix: Stage-kontrakt](#appendix-stage-kontrakt)

---

## 1. SAMMANFATTNING

### Kärnrekommendationer

| Område | Rekommendation |
|--------|----------------|
| Pipeline Design | **Funktionell pipeline** (Option C) med thin session wrapper |
| Config Structure | **Hybrid** - Stage-based internt, UI mapping layer för frontend |
| Dependency Tracking | **Explicit declarations** (Option A) |
| Batch Processing | **Unified implementation** - alltid 148 företag |
| Caching | **Baseline-first + @st.cache_data** - ingen komplex cache-hantering |
| Error Handling | **Stoppa pipeline** vid fel, visa förklaring |

### Huvudprinciper

1. **Format-agnosticism:** Varje stage bryr sig bara om input/output-format, inte datakälla
2. **Enkelhet framför cleverness:** Kod ska vara läsbar för nationalekonomister
3. **Explicit framför implicit:** Inga magiska beroenden eller hidden state
4. **Baseline finns alltid:** Eliminerar cache-komplexitet

---

## 2. SVAR PÅ DESIGN QUESTIONS

### FRÅGA A: Dependency Tracking Implementation

**Rekommendation: Option 2 (Stage dependency declarations) med förenkling**

#### Motivering

Option 1 (Explicit comparison) har problem:
- Logiken blir komplex när nya moduler läggs till
- if/elif-kedjor skalas dåligt
- Svårt att se helhetsbilden

Option 2 (Stage dependency declarations) är bättre eftersom:
- **Skalbarhet:** När SFA, StoNED eller kvalitetsjustering läggs till behöver man bara uppdatera en dict, inte if/elif-logik
- **Explicithet:** En ny utvecklare kan läsa `STAGE_TRIGGERS` och omedelbart förstå vilka parametrar som påverkar vilka stages
- **Testbarhet:** Dict-strukturen kan valideras och testas separat från exekveringslogiken
- **Dokumentation som kod:** Dict:en fungerar som levande dokumentation

#### Föreslagen implementation

```python
# pipeline_config.py

STAGE_TRIGGERS = {
    'pre_dea': [
        'capex_method',      # baseline, wacc_scaling, parameter_change, kent_upload
        'wacc',              # float, endast relevant för wacc_scaling och steg 7
        'normvalues',        # dict med kategori -> ny normvärde
        'lifetimes',         # dict med kategori -> ny livslängd
        'kent_file'          # UploadedFile eller None
    ],
    'dea': [
        'dea_method',        # baseline, dea, sfa, stoned
        'dea_model_spec'     # dict med inputs, outputs, rts, orientation
    ],
    'post_dea': [
        'effkrav_truncation',    # float, t.ex. 0.30
        'effkrav_iqr_multiplier', # float, t.ex. 2.0
        'effkrav_outlier_value',  # float, fast värde för outliers
        'paverkbara_method'       # 'OPEX' eller 'TOTEX'
    ]
}

# Stage-ordning är alltid fast
STAGE_ORDER = ['pre_dea', 'dea', 'extraction', 'post_dea']


def determine_stages_to_run(current_config: dict, baseline_config: dict) -> list:
    """
    Bestäm vilka stages som behöver köras baserat på config-ändringar.
    
    Kaskadering hanteras implicit: om pre_dea triggas, körs alla efterföljande stages.
    
    Args:
        current_config: Nuvarande case definition
        baseline_config: Baseline config (alla värden = default/baseline)
    
    Returns:
        Lista med stage-namn i exekveringsordning
    """
    first_triggered_stage = None
    
    for stage in STAGE_ORDER:
        triggers = STAGE_TRIGGERS.get(stage, [])
        
        for trigger in triggers:
            current_value = current_config.get(trigger)
            baseline_value = baseline_config.get(trigger)
            
            if current_value != baseline_value:
                first_triggered_stage = stage
                break
        
        if first_triggered_stage:
            break
    
    if first_triggered_stage is None:
        # Ingen ändring från baseline - returnera tom lista
        return []
    
    # Returnera denna stage och alla efterföljande
    start_index = STAGE_ORDER.index(first_triggered_stage)
    return STAGE_ORDER[start_index:]
```

#### Varför inte hash-baserad detection?

Hash-baserad automatic detection (nämnd som alternativ) avvisas av följande skäl:

1. **Debugging-svårighet:** När något går fel är det svårt att förstå "varför kördes denna stage?" med hash-jämförelser
2. **Floating-point problem:** `hash(0.0453)` kan skilja sig mellan körningar pga floating-point precision
3. **Serialiseringskomplexitet:** DataFrames och UploadedFile-objekt kräver custom serialisering för hashing
4. **Overkill:** Systemet har ~15 parametrar totalt - explicit jämförelse är trivialt

---

### FRÅGA B: Error Handling i Pipeline

**Rekommendation: Stoppa pipelinen och visa förklaring**

Jag håller med din rekommendation. Här är en utförlig implementation:

#### Principiellt ramverk

```python
from dataclasses import dataclass
from typing import Optional, Any
from enum import Enum


class StageStatus(Enum):
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"  # Användes baseline istället


@dataclass
class StageResult:
    """Resultat från en pipeline-stage."""
    stage_name: str
    status: StageStatus
    data: Optional[Any] = None
    error_message: Optional[str] = None
    error_details: Optional[dict] = None
    execution_time_ms: Optional[float] = None
    
    @property
    def success(self) -> bool:
        return self.status == StageStatus.SUCCESS


@dataclass
class PipelineResult:
    """Aggregerat resultat från hela pipelinen."""
    success: bool
    stage_results: dict  # stage_name -> StageResult
    final_output: Optional[dict] = None  # intaktsram_dict om success
    failed_stage: Optional[str] = None
    error_summary: Optional[str] = None
```

#### Felhantering per stage

```python
def run_pipeline_with_error_handling(config: dict, baseline: dict) -> PipelineResult:
    """
    Kör pipeline med robust felhantering.
    
    Vid fel:
    1. Stoppa exekvering
    2. Returnera information om vilken stage som failade
    3. Behåll resultat från lyckade stages (för debugging)
    """
    stage_results = {}
    
    # Stage 1: Pre-DEA
    try:
        result = run_pre_dea_stage(config, baseline)
        stage_results['pre_dea'] = StageResult(
            stage_name='pre_dea',
            status=StageStatus.SUCCESS,
            data=result
        )
    except PreDEAError as e:
        return PipelineResult(
            success=False,
            stage_results=stage_results,
            failed_stage='pre_dea',
            error_summary=f"Kapitalkostnadsberäkning misslyckades: {e.user_message}"
        )
    
    # Stage 2: DEA
    try:
        result = run_dea_stage(stage_results['pre_dea'].data, config, baseline)
        stage_results['dea'] = StageResult(
            stage_name='dea',
            status=StageStatus.SUCCESS,
            data=result
        )
    except DEAInfeasibleError as e:
        return PipelineResult(
            success=False,
            stage_results=stage_results,
            failed_stage='dea',
            error_summary=create_dea_error_message(e)
        )
    
    # ... fortsätt för övriga stages
```

#### Användarväntliga felmeddelanden

```python
DEA_ERROR_MESSAGES = {
    'infeasible': """
        **DEA-modellen kunde inte lösas**
        
        Detta händer vanligtvis när:
        - För få outputs valdes i förhållande till inputs
        - Modellspecifikationen är för restriktiv
        
        **Förslag:**
        - Lägg till fler output-variabler (t.ex. MW, MWh)
        - Byt från CRS till VRS
        - Kontrollera att alla företag har positiva värden för valda variabler
    """,
    
    'unbounded': """
        **DEA-modellen har ingen övre gräns**
        
        Detta är ovanligt och indikerar troligen ett dataproblem.
        
        **Förslag:**
        - Kontrollera att CAPEX och OPEXp är positiva för alla företag
        - Verifiera att valda volymer (CU, MW, NS) har rimliga värden
    """,
    
    'numerical_issues': """
        **Numeriska problem i DEA-beräkningen**
        
        **Förslag:**
        - Prova att normalisera input-data
        - Kontakta support om problemet kvarstår
    """
}


def create_dea_error_message(error: DEAInfeasibleError) -> str:
    """Skapa användarvänligt felmeddelande för DEA-fel."""
    base_message = DEA_ERROR_MESSAGES.get(error.error_type, "Okänt DEA-fel")
    
    # Lägg till teknisk detalj i expanderbar sektion
    return f"""
{base_message}

<details>
<summary>Teknisk information</summary>

- Solver status: {error.solver_status}
- Antal DMU:er: {error.n_dmus}
- Modellspecifikation: {error.model_spec}

</details>
"""
```

#### Streamlit UI-integration

```python
def display_pipeline_result(result: PipelineResult):
    """Visa pipeline-resultat i Streamlit."""
    
    if result.success:
        st.success("Beräkning genomförd")
        display_intaktsram(result.final_output)
    else:
        st.error(f"Beräkning avbröts i steg: {result.failed_stage}")
        st.markdown(result.error_summary)
        
        # Visa vilka stages som lyckades (för debugging)
        with st.expander("Genomförda steg"):
            for stage_name, stage_result in result.stage_results.items():
                if stage_result.success:
                    st.write(f"✅ {stage_name}")
                else:
                    st.write(f"❌ {stage_name}")
```

---

### FRÅGA C: Concurrent Users och Baseline Sharing

**Rekommendation: Ladda baseline separat i varje session**

#### Motivering

| Faktor | Analys |
|--------|--------|
| **Memory per session** | ~15-20 MB (3 DataFrames + metadata) |
| **Render Standard RAM** | 2 GB |
| **Max samtidiga sessioner** | ~100 (med marginal) |
| **Komplexitet vid delning** | Hög (locking, invalidation, race conditions) |
| **Vinst vid delning** | Marginell (~15 MB × antal sessioner) |

#### Detaljerad analys

**Dataset-storlekar:**
- `Data_modeller.xlsx`: 148 rader × 12 kolumner ≈ 50 KB i minnet
- `EIs_DEA.xlsx`: 148 rader × 7 kolumner ≈ 30 KB i minnet
- `capbase_a.parquet`: 510k rader × 33 kolumner ≈ 15 MB i minnet (största)

**Total per session:** ~15-20 MB

**Vid 50 samtidiga användare:** ~1 GB (hälften av tillgängligt RAM)

**Slutsats:** Memory är inte flaskhalsen. Enkelhet är viktigare.

#### Implementation med @st.cache_data

```python
# baseline_loader.py

import streamlit as st
import pandas as pd
from pathlib import Path


@st.cache_data(ttl=3600)  # Cache i 1 timme, delas mellan sessioner
def load_data_modeller() -> pd.DataFrame:
    """
    Ladda Data_modeller.xlsx.
    
    Denna funktion cachas globalt av Streamlit, så första sessionen
    laddar från disk, efterföljande sessioner får cached version.
    """
    return pd.read_excel("Data_modeller.xlsx", sheet_name="Körning")


@st.cache_data(ttl=3600)
def load_eis_dea() -> pd.DataFrame:
    """Ladda EIs_DEA.xlsx med baseline DEA-resultat."""
    return pd.read_excel("EIs_DEA.xlsx", sheet_name="Körning")


@st.cache_data(ttl=3600)
def load_capbase_a() -> pd.DataFrame:
    """Ladda capbase_a.parquet med komponentdata."""
    return pd.read_parquet("kapitalkostnad/data/capbase_a.parquet")


def initialize_session_baseline():
    """
    Initiera baseline i session_state.
    
    Anropas en gång per session vid app-start.
    Använder cached data från @st.cache_data.
    """
    if 'baseline' not in st.session_state:
        st.session_state.baseline = {
            'df_all_companies': load_data_modeller(),
            'dea_results': load_eis_dea(),
            'capbase_a': load_capbase_a(),
            'wacc': 0.0453,
            'initialized': True
        }
```

**Notera:** `@st.cache_data` delar cache mellan sessioner automatiskt. Första användaren laddar från disk (~2-3 sekunder), efterföljande får cached version (~10 ms).

---

## 3. SVAR PÅ ARCHITECTURAL QUESTIONS

### Question 1: Pipeline Class Design

**Rekommendation: Option C (Functional pipeline) med thin session wrapper**

#### Motivering

| Kriterium | Option A (Monolithic) | Option B (Stage classes) | Option C (Functional) |
|-----------|----------------------|-------------------------|----------------------|
| Enkelhet | ⚠️ Döljer komplexitet i klass | ⚠️ Många klasser att hålla reda på | ✅ Explicita funktioner |
| Testbarhet | ⚠️ Kräver mock av self | ⚠️ Kräver dependency injection | ✅ Pure functions, enkelt |
| Läsbarhet | ⚠️ Kräver OOP-förståelse | ⚠️ Kräver OOP + patterns | ✅ Läsbart för alla |
| Flexibilitet | ❌ Svårt att byta ut stages | ✅ Enkelt att byta stages | ✅ Enkelt att byta stages |
| State-hantering | ⚠️ Hidden state i self | ⚠️ Hidden state i instanser | ✅ Explicit state |

**Option C vinner** eftersom:
1. **Målgruppen** (nationalekonomister) förstår funktioner bättre än klasser
2. **Pure functions** är lättare att testa och debugga
3. **Inget hidden state** - all data flödar explicit genom funktionsargument
4. **Streamlit-idiomatiskt** - Streamlit själv är funktionsbaserat

#### Föreslagen implementation

```python
# pipeline_stages.py
"""
Pure functions för varje pipeline-stage.
Ingen klass, inget hidden state, inga sidoeffekter.
"""

import pandas as pd
from typing import Dict, Any, Optional


# =============================================================================
# STAGE 1: BASELINE LOADING
# =============================================================================

def load_baseline() -> Dict[str, Any]:
    """
    Ladda all baseline-data.
    
    Returns:
        Dict med:
        - df_all_companies: DataFrame (148 rader) från Data_modeller.xlsx
        - dea_results: DataFrame (148 rader) från EIs_DEA.xlsx
        - capbase_a: DataFrame (510k rader) från capbase_a.parquet
        - wacc: float (0.0453)
    """
    return {
        'df_all_companies': load_data_modeller(),
        'dea_results': load_eis_dea(),
        'capbase_a': load_capbase_a(),
        'wacc': 0.0453
    }


# =============================================================================
# STAGE 2: PRE-DEA (CAPEX MODIFICATION)
# =============================================================================

def apply_capex_method(
    df_all: pd.DataFrame,
    capbase_a: pd.DataFrame,
    config: Dict[str, Any]
) -> pd.DataFrame:
    """
    Applicera vald CAPEX-metod på alla 148 företag.
    
    Args:
        df_all: Baseline DataFrame (148 rader)
        capbase_a: Komponentdata (510k rader)
        config: Dict med capex_method, wacc, normvalues, etc.
    
    Returns:
        DataFrame (148 rader) med eventuellt modifierad CAPEX
    """
    method = config.get('capex_method', 'baseline')
    
    if method == 'baseline':
        return df_all.copy()
    
    elif method == 'wacc_scaling':
        return _apply_wacc_scaling(df_all, config['wacc'])
    
    elif method == 'parameter_change':
        return _apply_parameter_changes(df_all, capbase_a, config)
    
    elif method == 'kent_upload':
        return _apply_kent_upload(df_all, capbase_a, config)
    
    else:
        raise ValueError(f"Okänd capex_method: {method}")


def _apply_wacc_scaling(df: pd.DataFrame, new_wacc: float) -> pd.DataFrame:
    """
    Skala Avkastning-kolumnen proportionellt mot ny WACC.
    
    Formel:
        scaling_factor = new_wacc / baseline_wacc
        Avkastning_ny = Avkastning_baseline * scaling_factor
        CAPEX_ny = Avskrivning + Avkastning_ny
    """
    BASELINE_WACC = 0.0453
    
    result = df.copy()
    scaling_factor = new_wacc / BASELINE_WACC
    
    result['Avkastning'] = result['Avkastning'] * scaling_factor
    result['CAPEX'] = result['Avskrivning'] + result['Avkastning']
    result['TOTEX'] = result['CAPEX'] + result['OPEXp']
    
    return result


# =============================================================================
# STAGE 3: EFFICIENCY ANALYSIS
# =============================================================================

def calculate_efficiency(
    df_modified: pd.DataFrame,
    config: Dict[str, Any],
    baseline_dea: pd.DataFrame
) -> pd.DataFrame:
    """
    Beräkna effektivitet för alla 148 företag.
    
    Args:
        df_modified: DataFrame från Pre-DEA stage
        config: Dict med dea_method, dea_model_spec
        baseline_dea: EIs_DEA.xlsx för baseline-fallback
    
    Returns:
        DataFrame (148 rader) med efficiency, potential, is_outlier
    """
    method = config.get('dea_method', 'baseline')
    
    if method == 'baseline':
        # Använd Ei:s officiella DEA-resultat
        return baseline_dea[['DMU', 'REId', 'Företag', 
                            'Effektivitet', 'potential', 'Effkrav_proc']].copy()
    
    elif method == 'dea':
        model_spec = config.get('dea_model_spec', DEFAULT_DEA_SPEC)
        return run_dea_analysis(df_modified, model_spec)
    
    elif method == 'sfa':
        # Framtida implementation
        raise NotImplementedError("SFA ej implementerat ännu")
    
    else:
        raise ValueError(f"Okänd dea_method: {method}")


# =============================================================================
# STAGE 4: EXTRACTION
# =============================================================================

def extract_company(
    df_efficiency: pd.DataFrame,
    user_dmu: int
) -> pd.Series:
    """
    Extrahera data för inloggat företag.
    
    Args:
        df_efficiency: DataFrame (148 rader) från DEA stage
        user_dmu: DMU för inloggat företag
    
    Returns:
        Series med företagets data
    
    Raises:
        ValueError: Om DMU inte finns i DataFrame
    """
    company_data = df_efficiency[df_efficiency['DMU'] == user_dmu]
    
    if company_data.empty:
        raise ValueError(f"DMU {user_dmu} finns inte i datasetet")
    
    return company_data.iloc[0]


# =============================================================================
# STAGE 5: POST-DEA (INTÄKTSRAM)
# =============================================================================

def calculate_intaktsram(
    company_data: pd.Series,
    baseline: Dict[str, Any],
    config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Beräkna fullständig intäktsram för inloggat företag.
    
    Args:
        company_data: Series från Extraction stage
        baseline: Dict med SDF-data, opåverkbara kostnader, etc.
        config: Dict med effkrav_config, paverkbara_method
    
    Returns:
        Dict med intäktsram-dekomposition
    """
    # Steg 5.1: Beräkna effektiviseringskrav
    effkrav_proc = calculate_effkrav(
        potential=company_data['potential'],
        is_outlier=company_data.get('is_outlier', False),
        config=config.get('effkrav_config', {})
    )
    
    # Steg 5.2: Beräkna påverkbara kostnader
    paverkbara = calculate_paverkbara(
        effkrav_proc=effkrav_proc,
        baseline_paverkbara=baseline['paverkbara_medelv'],
        neonjusteringar=baseline['neonjusteringar'],
        method=config.get('paverkbara_method', 'OPEX'),
        kapitalkostnad=baseline.get('kapitalkostnad_total')
    )
    
    # Steg 5.3: Summera intäktsram
    intaktsram = assemble_intaktsram(
        kapitalkostnad=baseline['kapitalkostnad_total'],
        paverkbara=paverkbara,
        opaverkbara=baseline['opaverkbara'],
        flexibilitet=baseline.get('flexibilitet', 0),
        avbrott=baseline.get('avbrott_12_24h', 0),
        avdrag_statligt=baseline.get('avdrag_statligt', 0)
    )
    
    return intaktsram
```

#### Thin session wrapper för Streamlit

```python
# streamlit_runner.py
"""
Streamlit-specifik wrapper som hanterar session_state.
Separerar pipeline-logik från Streamlit-specifik kod.
"""

import streamlit as st
from pipeline_stages import (
    load_baseline,
    apply_capex_method,
    calculate_efficiency,
    extract_company,
    calculate_intaktsram
)


def initialize_session():
    """Initiera session vid app-start."""
    if 'baseline' not in st.session_state:
        st.session_state.baseline = load_baseline()
    
    if 'case_definition' not in st.session_state:
        st.session_state.case_definition = get_default_config()
    
    if 'result' not in st.session_state:
        st.session_state.result = None


def execute_pipeline():
    """
    Kör pipeline med nuvarande config.
    Anropas när användaren klickar "Beräkna".
    """
    config = st.session_state.case_definition
    baseline = st.session_state.baseline
    
    # Determine which stages to run
    stages_to_run = determine_stages_to_run(
        config, 
        get_baseline_config()
    )
    
    # Run pipeline
    result = run_pipeline(config, baseline, stages_to_run)
    
    # Store result
    st.session_state.result = result
    
    return result


def run_pipeline(
    config: dict, 
    baseline: dict, 
    stages_to_run: list
) -> dict:
    """
    Kör pipeline med smart execution.
    
    Endast stages i stages_to_run beräknas.
    Övriga använder baseline-värden.
    """
    
    # Pre-DEA
    if 'pre_dea' in stages_to_run:
        df_modified = apply_capex_method(
            baseline['df_all_companies'],
            baseline['capbase_a'],
            config
        )
    else:
        df_modified = baseline['df_all_companies']
    
    # DEA
    if 'dea' in stages_to_run:
        df_efficiency = calculate_efficiency(
            df_modified,
            config,
            baseline['dea_results']
        )
    else:
        df_efficiency = baseline['dea_results']
    
    # Extraction (alltid)
    company_data = extract_company(
        df_efficiency,
        config['user_dmu']
    )
    
    # Post-DEA (alltid, eftersom det är snabbt)
    intaktsram = calculate_intaktsram(
        company_data,
        baseline,
        config
    )
    
    return intaktsram
```

---

### Question 2: Config Structure

**Rekommendation: Hybrid - Stage-based internt (Option A), med UI mapping layer**

#### Motivering

**Problemet med endast Option A (Stage-based):**
- UI måste visa "Parameters, Variables, Modules" enligt User Manual
- Stage-struktur exponerar implementation details för användaren
- Bryter mot separation of concerns

**Problemet med endast Option B (Flat config):**
- Pipeline-logik måste "gissa" vilken stage varje parameter påverkar
- Svårare att implementera smart execution

**Hybrid-lösningen:**
- Backend arbetar med stage-based config (tydligt vilken stage påverkas)
- Frontend arbetar med UI-config (Parameters/Variables/Modules)
- Mapping layer översätter mellan dem

#### Implementation

```python
# config_types.py
"""
Definierar config-strukturer för UI och Backend.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


# =============================================================================
# UI CONFIG (vad användaren ser och redigerar)
# =============================================================================

@dataclass
class UIConfig:
    """
    Konfiguration strukturerad enligt User Manual terminologi.
    
    Tre kategorier:
    - Parameters: Uniforma värden för alla 148 företag
    - Variables: Företagsspecifika mätvärden
    - Modules: Val av beräkningsmetod
    """
    
    # Parameters (ID 2.x i User Manual)
    parameters: Dict[str, Any] = field(default_factory=lambda: {
        # WACC-komponenter (2.1-2.12)
        'rf_nominal': 0.0287,
        'mrp_nominal': 0.0668,
        'beta_asset': 0.37,
        'debt_share': 0.36,
        'tax_rate': 0.206,
        'credit_spread': 0.0114,
        'inflation': 0.0202,
        
        # Normvärdesjusteringar (2.13+)
        'normvalue_adjustments': {},  # kategori -> faktor
        
        # Livslängdsjusteringar (2.20+)
        'lifetime_adjustments': {},  # kategori -> ny livslängd
        
        # Effektiviseringskrav-parametrar
        'effkrav_truncation': 0.30,
        'effkrav_iqr_multiplier': 2.0,
        'effkrav_outlier_fixed': 0.01,
    })
    
    # Variables (företagsspecifika)
    variables: Dict[str, Any] = field(default_factory=lambda: {
        'kent_file': None,  # UploadedFile eller None
    })
    
    # Modules (metodval)
    modules: Dict[str, str] = field(default_factory=lambda: {
        'capex_method': 'baseline',      # baseline, wacc_scaling, parameter_change, kent_upload
        'efficiency_method': 'baseline', # baseline, dea, sfa, stoned
        'paverkbara_method': 'OPEX',     # OPEX, TOTEX
    })
    
    # Case metadata
    name: str = "Nytt case"
    user_dmu: Optional[int] = None


# =============================================================================
# PIPELINE CONFIG (vad backend använder)
# =============================================================================

@dataclass
class PipelineConfig:
    """
    Konfiguration strukturerad per pipeline-stage.
    Skapas från UIConfig via mapping.
    """
    
    pre_dea: Dict[str, Any] = field(default_factory=dict)
    dea: Dict[str, Any] = field(default_factory=dict)
    post_dea: Dict[str, Any] = field(default_factory=dict)
    
    user_dmu: Optional[int] = None


# =============================================================================
# MAPPING LAYER
# =============================================================================

def ui_to_pipeline_config(ui_config: UIConfig) -> PipelineConfig:
    """
    Översätt UI-terminologi till pipeline-stages.
    
    Args:
        ui_config: Konfiguration enligt User Manual struktur
    
    Returns:
        PipelineConfig strukturerad per stage
    """
    
    # Pre-DEA config
    pre_dea = {
        'method': ui_config.modules['capex_method'],
    }
    
    # Beräkna WACC från komponenter om relevant
    if ui_config.modules['capex_method'] in ['wacc_scaling', 'parameter_change', 'kent_upload']:
        pre_dea['wacc'] = calculate_wacc_from_components(ui_config.parameters)
    
    # Inkludera parameterjusteringar om relevant
    if ui_config.modules['capex_method'] in ['parameter_change', 'kent_upload']:
        pre_dea['normvalues'] = ui_config.parameters.get('normvalue_adjustments', {})
        pre_dea['lifetimes'] = ui_config.parameters.get('lifetime_adjustments', {})
    
    # Inkludera KENT-fil om relevant
    if ui_config.modules['capex_method'] == 'kent_upload':
        pre_dea['kent_file'] = ui_config.variables.get('kent_file')
    
    # DEA config
    dea = {
        'method': ui_config.modules['efficiency_method'],
        'model_spec': ui_config.parameters.get('dea_model_spec', DEFAULT_DEA_SPEC),
    }
    
    # Post-DEA config
    post_dea = {
        'effkrav_config': {
            'truncation': ui_config.parameters['effkrav_truncation'],
            'iqr_multiplier': ui_config.parameters['effkrav_iqr_multiplier'],
            'outlier_fixed': ui_config.parameters['effkrav_outlier_fixed'],
        },
        'paverkbara_method': ui_config.modules['paverkbara_method'],
    }
    
    return PipelineConfig(
        pre_dea=pre_dea,
        dea=dea,
        post_dea=post_dea,
        user_dmu=ui_config.user_dmu
    )


def pipeline_to_ui_config(pipeline_config: PipelineConfig) -> UIConfig:
    """
    Omvänd mapping - för att visa nuvarande config i UI.
    """
    # Implementation här...
    pass
```

#### Fördelar med hybrid-approach

1. **UI förblir konsekvent** med User Manual terminologi
2. **Pipeline-logik är tydlig** - varje stage vet exakt vilka parametrar den behöver
3. **Enkel att utöka** - nya parametrar läggs till i UIConfig, mapping uppdateras
4. **Testbar separat** - mapping-funktionen kan unit-testas

---

### Question 3: Dependency Tracking

**Rekommendation: Option A (Explicit dependency declarations)**

#### Motivering

Se svar på Fråga A ovan. Sammanfattning:

| Kriterium | Option A (Explicit) | Option B (Hash-based) |
|-----------|--------------------|-----------------------|
| Debuggbarhet | ✅ Tydligt vilka parametrar som triggar | ❌ "Varför kördes denna?" |
| Robusthet | ✅ Deterministisk | ⚠️ Floating-point issues |
| Underhåll | ✅ Läsbar dict | ⚠️ Serialiseringskod |
| Skalbarhet | ✅ Lägg till i dict | ✅ Automatisk |

**Hash-baserad** vinner endast på automatisk skalbarhet, men Regumetrica har ~15 parametrar - explicit hantering är trivialt.

---

### Question 4: Batch Processing för Kent Pipeline

**Rekommendation: Unified implementation som alltid tar alla 148 företag**

#### Motivering

1. **DEA kräver alla 148:** DEA-analys är relativ - ett företags effektivitet beror på alla andras. Att ha batch-kapacitet är inte valfritt.

2. **Duplicerade funktioner = divergens:** Om vi har `calculate_depreciation_single()` och `calculate_depreciation_batch()` kommer de att divergera över tid. En bug fixas i en men inte den andra.

3. **Pandas är optimerat för batch:** `groupby().apply()` är idiomatiskt och effektivt.

4. **Kent-upload är edge case:** Endast 1 av 4 CAPEX-metoder påverkar 1 företag. De andra 3 påverkar alla 148 eller ingen.

#### Implementation

```python
# kent_pipeline_batch.py
"""
Batch-version av beräkningskedja steg 5-8.
Hanterar alla 148 företag samtidigt via groupby på id_network.
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple


def run_kent_pipeline_batch(
    capbase_a: pd.DataFrame,
    wacc: float = 0.0453,
    normvalue_adjustments: Dict[int, float] = None,
    lifetime_adjustments: Dict[int, Dict[str, int]] = None
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Kör beräkningskedja steg 5-8 för ALLA företag.
    
    Args:
        capbase_a: Komponentdata (510k rader, alla 148 företag)
        wacc: WACC för avkastningsberäkning (steg 7)
        normvalue_adjustments: Dict med cat_encode -> skalningsfaktor
        lifetime_adjustments: Dict med cat_encode -> {'ekdep': x, 'maxdep': y}
    
    Returns:
        Tuple med:
        - capex_2024: DataFrame (148 rader) med CAPEX för år 2024 (för DEA)
        - capex_period: DataFrame (148 rader) med periodsumma 2024-2027 (för intäktsram)
    """
    
    # Steg 0: Kopiera och applicera justeringar
    df = capbase_a.copy()
    
    if normvalue_adjustments:
        df = apply_normvalue_adjustments_batch(df, normvalue_adjustments)
    
    if lifetime_adjustments:
        df = apply_lifetime_adjustments_batch(df, lifetime_adjustments)
    
    # Steg 5: Beräkna åldrar och NUAV för alla tidsperioder
    df = calculate_ages_and_nuav_batch(df)
    
    # Steg 6: Beräkna avskrivningar
    df = calculate_depreciation_batch(df)
    
    # Steg 7: Beräkna avkastning
    df = calculate_returns_batch(df, wacc)
    
    # Steg 8: Sammanställ kapitalkostnad per id_network och tidskod
    capcost_by_network_time = compile_capcost_batch(df)
    
    # Extrahera för DEA (endast 2024 = tidskod 229+230)
    capex_2024 = extract_capex_2024(capcost_by_network_time)
    
    # Extrahera för intäktsram (summa 2024-2027)
    capex_period = extract_capex_period(capcost_by_network_time)
    
    return capex_2024, capex_period


def calculate_ages_and_nuav_batch(df: pd.DataFrame) -> pd.DataFrame:
    """
    Steg 5: Beräkna åldrar och NUAV för alla företag och tidsperioder.
    
    Skillnad från single-DMU version:
    - Ingen filtrering på id_network
    - Groupby sker i efterföljande aggregering, inte här
    """
    
    for time in range(229, 237):
        # Beräkna ålder (samma formel för alla företag)
        df[f'age_component_{time}'] = time - df['time_from']
        df[f'age_component_{time}_invest'] = np.where(
            df['capbase_existing'] == 0,
            time - df['time_invest'],
            np.nan
        )
        
        # Beräkna base_ord och base_tail (vektoriserat)
        age = df[f'age_component_{time}']
        age_invest = df[f'age_component_{time}_invest']
        
        # Ordinarie kapitalbas
        base_ord = (
            ((age <= df['ekdep']) & (age > 0) & (df['capbase_existing'] == 1)) |
            ((age <= df['ekdep']) & (age_invest > 0) & (df['capbase_existing'] == 0))
        ).astype(int)
        
        df[f'base_ord_{time}'] = base_ord
        df[f'nuav_ord_{time}'] = df['nuav_2022'] * base_ord
        
        # Svanskapitalbas
        base_tail = (
            (age <= df['maxdep']) & 
            (age > df['ekdep']) & 
            (df['capbase_existing'] == 1)
        ).astype(int)
        
        df[f'base_tail_{time}'] = base_tail
        df[f'nuav_tail_{time}'] = df['nuav_2022'] * base_tail
    
    return df


def calculate_depreciation_batch(df: pd.DataFrame) -> pd.DataFrame:
    """
    Steg 6: Beräkna avskrivningar för alla företag.
    """
    
    for time in range(229, 237):
        # Ordinarie avskrivning
        df[f'dep_ord_{time}'] = df[f'nuav_ord_{time}'] / df['ekdep']
        
        # Beräkna age_reg för svansavskrivning
        age = df[f'age_component_{time}']
        adjustment = np.where(
            age % 2 == 1,
            np.where(age > 0, 1, -1),
            0
        )
        age_reg = age + adjustment
        df[f'age_reg_{time}'] = age_reg
        
        # Svansavskrivning (undvik division med 0)
        df[f'dep_tail_{time}'] = np.divide(
            df[f'nuav_tail_{time}'],
            age_reg,
            out=np.zeros(len(df)),
            where=(age_reg != 0)
        )
    
    return df


def calculate_returns_batch(df: pd.DataFrame, wacc: float) -> pd.DataFrame:
    """
    Steg 7: Beräkna avkastning för alla företag.
    
    Args:
        wacc: Kalkylränta (real, före skatt)
    """
    
    # Konvertera halvårsränta
    r_half = (1 + wacc) ** 0.5 - 1
    
    for time in range(229, 237):
        age = df[f'age_component_{time}']
        
        # Beräkna age_return (halvår)
        age_return = np.floor(age / 2).astype(int)
        age_return = np.clip(age_return, 0, None)  # Ej negativt
        
        # Ordinarie avkastning
        # Formel: NUAV * (1 - age_return/ekdep2) * r_half
        ekdep2 = df['ekdep'] / 2
        remaining_share = np.clip(1 - age_return / ekdep2, 0, 1)
        df[f'return_ord_{time}'] = df[f'nuav_ord_{time}'] * remaining_share * r_half
        
        # Svansavkastning
        maxdep2 = df['maxdep'] / 2
        remaining_share_tail = np.clip(1 - age_return / maxdep2, 0, 1)
        df[f'return_tail_{time}'] = df[f'nuav_tail_{time}'] * remaining_share_tail * r_half
    
    return df


def compile_capcost_batch(df: pd.DataFrame) -> pd.DataFrame:
    """
    Steg 8: Aggregera kapitalkostnad per id_network och tidskod.
    
    Returns:
        DataFrame med kolumner:
        [id_network, time, dep_ord, dep_tail, return_ord, return_tail, capcost_total]
    """
    
    results = []
    
    for time in range(229, 237):
        # Aggregera per id_network
        agg = df.groupby('id_network').agg({
            f'dep_ord_{time}': 'sum',
            f'dep_tail_{time}': 'sum',
            f'return_ord_{time}': 'sum',
            f'return_tail_{time}': 'sum'
        }).reset_index()
        
        # Byt namn och konvertera till tkr
        agg = agg.rename(columns={
            f'dep_ord_{time}': 'dep_ord',
            f'dep_tail_{time}': 'dep_tail',
            f'return_ord_{time}': 'return_ord',
            f'return_tail_{time}': 'return_tail'
        })
        
        # Konvertera till tkr
        for col in ['dep_ord', 'dep_tail', 'return_ord', 'return_tail']:
            agg[col] = agg[col] / 1000
        
        agg['time'] = time
        agg['capcost_total'] = (
            agg['dep_ord'] + agg['dep_tail'] + 
            agg['return_ord'] + agg['return_tail']
        )
        
        results.append(agg)
    
    return pd.concat(results, ignore_index=True)


def extract_capex_2024(capcost_df: pd.DataFrame) -> pd.DataFrame:
    """
    Extrahera CAPEX för år 2024 (tidskod 229+230) för DEA.
    
    Returns:
        DataFrame med [id_network, CAPEX, Avskrivning, Avkastning]
    """
    
    # Filtrera för 2024 (tidskod 229 och 230)
    df_2024 = capcost_df[capcost_df['time'].isin([229, 230])].copy()
    
    # Summera per id_network
    result = df_2024.groupby('id_network').agg({
        'dep_ord': 'sum',
        'dep_tail': 'sum',
        'return_ord': 'sum',
        'return_tail': 'sum',
        'capcost_total': 'sum'
    }).reset_index()
    
    # Beräkna aggregerade värden
    result['Avskrivning'] = result['dep_ord'] + result['dep_tail']
    result['Avkastning'] = result['return_ord'] + result['return_tail']
    result['CAPEX'] = result['capcost_total']
    
    return result[['id_network', 'CAPEX', 'Avskrivning', 'Avkastning']]


def extract_capex_period(capcost_df: pd.DataFrame) -> pd.DataFrame:
    """
    Extrahera kapitalkostnad för hela perioden 2024-2027.
    
    Returns:
        DataFrame med [id_network, Kapitalkostnad_Total, Avskrivning_Total, Avkastning_Total]
    """
    
    # Summera över alla tidskoder (229-236)
    result = capcost_df.groupby('id_network').agg({
        'dep_ord': 'sum',
        'dep_tail': 'sum',
        'return_ord': 'sum',
        'return_tail': 'sum',
        'capcost_total': 'sum'
    }).reset_index()
    
    result['Avskrivning_Total'] = result['dep_ord'] + result['dep_tail']
    result['Avkastning_Total'] = result['return_ord'] + result['return_tail']
    result['Kapitalkostnad_Total'] = result['capcost_total']
    
    return result[['id_network', 'Kapitalkostnad_Total', 'Avskrivning_Total', 'Avkastning_Total']]
```

---

## 4. BEKRÄFTELSE: BASELINE-FIRST STRATEGY

**Ja, jag bekräftar att baseline-first eliminerar behovet för komplex caching.**

### Varför det fungerar

1. **All baseline-data finns i filer:**
   - `Data_modeller.xlsx` → Pre-DEA baseline
   - `EIs_DEA.xlsx` → DEA baseline (Ei's officiella resultat)
   - `SDF` → Post-DEA baseline (opåverkbara, etc.)

2. **Baseline laddas en gång per session:**
   ```python
   st.session_state.baseline = load_baseline()  # ~15 MB
   ```

3. **Vid beräkning: baseline vs beräknad:**
   ```python
   if config['capex_method'] == 'baseline':
       df = baseline['df_all_companies']  # Ingen beräkning!
   else:
       df = apply_capex_method(...)  # Beräkning
   ```

4. **Ingen cache invalidation:**
   - Baseline är immutable (read-only från filer)
   - Beräknade resultat sparas inte mellan körningar
   - Varje "Beräkna"-klick kör relevant pipeline från scratch (snabbt nog)

### Edge cases

**Edge case 1: Tunga beräkningar som körs flera gånger**

Exempel: Användaren kör kent_pipeline med samma parametrar 5 gånger.

**Lösning:** `@st.cache_data` på funktionsnivå:
```python
@st.cache_data
def run_kent_pipeline_batch(
    _capbase_a_hash: str,  # Hash av DataFrame för cache key
    wacc: float,
    normvalue_adjustments: tuple,  # Hashable
    lifetime_adjustments: tuple    # Hashable
):
    ...
```

Notera: Detta är Streamlit-cache, inte vår egen cache-implementation.

**Edge case 2: capbase_a tar >10 sekunder att beräkna**

Aktuell tidskomplexitet för 510k rader:
- `calculate_ages_and_nuav`: ~2-3 sekunder
- `calculate_depreciation`: ~1-2 sekunder
- `calculate_returns`: ~1-2 sekunder
- **Total: ~5-7 sekunder**

Detta är acceptabelt. Om det blir långsammare:
1. Optimera med NumPy vektorisering (redan gjort i batch-versionen ovan)
2. Använd `@st.cache_data` för att undvika omberäkning
3. Visa progress bar under beräkning

**Edge case 3: Användaren vill jämföra flera cases**

Scenario: Användaren har Case A och Case B och vill se dem sida vid sida.

**Lösning:** Spara case-resultat i `st.session_state.saved_cases`:
```python
st.session_state.saved_cases = {
    'Case A': {...resultat...},
    'Case B': {...resultat...}
}
```

Detta är applikationslogik, inte cache-arkitektur.

### Slutsats

Baseline-first + `@st.cache_data` på tunga funktioner = tillräckligt för alla identifierade use cases. Ingen custom cache-arkitektur behövs.

---

## 5. REKOMMENDERAD FILSTRUKTUR

```
regumetrica/
│
├── app.py                          # Streamlit huvudapp
│
├── config/
│   ├── __init__.py
│   ├── config_types.py             # UIConfig, PipelineConfig dataclasses
│   ├── config_mapping.py           # ui_to_pipeline_config(), etc.
│   ├── stage_triggers.py           # STAGE_TRIGGERS dict
│   └── defaults.py                 # DEFAULT_DEA_SPEC, BASELINE_WACC, etc.
│
├── pipeline/
│   ├── __init__.py
│   ├── stages.py                   # Pure functions per stage
│   ├── runner.py                   # run_pipeline(), determine_stages_to_run()
│   └── errors.py                   # PipelineError, StageResult, etc.
│
├── baseline/
│   ├── __init__.py
│   └── loaders.py                  # load_data_modeller(), load_eis_dea(), etc.
│
├── pre_dea/
│   ├── __init__.py
│   ├── capex_methods.py            # apply_wacc_scaling(), etc.
│   └── kent_pipeline_batch.py      # run_kent_pipeline_batch()
│
├── dea/
│   ├── __init__.py
│   ├── dea_model.py                # DEA implementation (PuLP)
│   └── dea_runner.py               # run_dea_analysis()
│
├── post_dea/
│   ├── __init__.py
│   ├── effektiviseringskrav.py     # calculate_effkrav()
│   ├── paverkbara.py               # calculate_paverkbara()
│   └── intaktsram_assembly.py      # assemble_intaktsram()
│
├── ui/
│   ├── __init__.py
│   ├── pages/
│   │   ├── __init__.py
│   │   ├── overview.py             # Översiktssida
│   │   ├── case_setup.py           # Case-konfiguration
│   │   ├── results.py              # Resultatvisning
│   │   └── comparison.py           # Jämförelsesida
│   ├── components/
│   │   ├── __init__.py
│   │   ├── wacc_inputs.py          # WACC-komponent UI
│   │   ├── dea_config.py           # DEA-modellval UI
│   │   └── intaktsram_chart.py     # Stapeldiagram för intäktsram
│   └── styles.py                   # CSS, färger, etc.
│
├── utils/
│   ├── __init__.py
│   ├── reconciliation.py           # id_network <-> DMU mapping
│   └── formatting.py               # format_tsek(), format_percent(), etc.
│
└── data/
    ├── Data_modeller.xlsx
    ├── EIs_DEA.xlsx
    ├── capbase_a.parquet
    └── reconciliation_id_network_firm_dmu.csv
```

### Förklaring

| Mapp | Ansvar |
|------|--------|
| `config/` | Konfigurationstyper och mapping |
| `pipeline/` | Orkestrering av stages |
| `baseline/` | Laddning av baseline-data |
| `pre_dea/` | CAPEX-metoder (steg 1-8) |
| `dea/` | Effektivitetsanalys |
| `post_dea/` | Intäktsramsberäkning |
| `ui/` | Streamlit-specifik kod |
| `utils/` | Hjälpfunktioner |

---

## 6. NAMNKONVENTIONER

### DataFrame-namngivning

Suffix som indikerar scope:

| Suffix | Betydelse | Exempel |
|--------|-----------|---------|
| `_all` | Alla 148 företag | `df_all`, `capex_all` |
| `_single` | Ett företag | `df_single`, `company_data` |
| `_2024` | Data för år 2024 | `capex_2024` |
| `_period` | Periodsumma 2024-2027 | `capex_period`, `intaktsram_period` |

### CAPEX-funktioner

| Funktion | Returnerar | Scope |
|----------|------------|-------|
| `produce_capex_from_baseline()` | CAPEX för 2024 | 148 företag |
| `apply_wacc_scaling()` | CAPEX för 2024 (skalad) | 148 företag |
| `run_kent_pipeline_batch()` | Tuple: (capex_2024, capex_period) | 148 företag |
| `extract_capex_2024()` | CAPEX för 2024 | 148 företag |
| `extract_capex_period()` | Kapitalkostnad periodsumma | 148 företag |

### Config-namngivning

| Term | Betydelse | Exempel |
|------|-----------|---------|
| `ui_config` | Konfiguration i UI-format | `UIConfig(parameters={...})` |
| `pipeline_config` | Konfiguration per stage | `PipelineConfig(pre_dea={...})` |
| `baseline_config` | Default-konfiguration | Alla värden = baseline |

### Variabelnamn i kod

| Variabel | Typ | Beskrivning |
|----------|-----|-------------|
| `df_all` | DataFrame | 148 rader, alla företag |
| `df_modified` | DataFrame | 148 rader, efter Pre-DEA |
| `df_efficiency` | DataFrame | 148 rader, med effektivitet |
| `company_data` | Series | 1 rad, inloggat företag |
| `intaktsram` | dict | Dekomponerad intäktsram |
| `wacc` | float | Kalkylränta (decimal, t.ex. 0.0453) |
| `effkrav_proc` | float | Årligt effektiviseringskrav (decimal) |

---

## 7. MIGRATIONSPLAN

### Fas 1: Grundläggande pipeline (vecka 1-2)

**Mål:** Fungerande pipeline med baseline-metod

**Filer att skapa:**
1. `config/config_types.py` - UIConfig, PipelineConfig
2. `config/stage_triggers.py` - STAGE_TRIGGERS
3. `pipeline/stages.py` - Stage-funktioner (skelett)
4. `pipeline/runner.py` - run_pipeline()
5. `baseline/loaders.py` - Återanvänd befintlig `baseline_loaders.py`

**Filer att återanvända (direkt kopiering):**
- `baseline_loaders.py` → `baseline/loaders.py`
- `reference_dea_loader.py` → `baseline/loaders.py` (merge)

**Testfall:**
- Kör pipeline med `capex_method='baseline'`, `dea_method='baseline'`
- Verifiera att resultat matchar EIs_DEA.xlsx

### Fas 2: Pre-DEA batch (vecka 2-3)

**Mål:** WACC-skalning och parameter-ändringar fungerar

**Filer att skapa:**
1. `pre_dea/capex_methods.py` - WACC-skalning
2. `pre_dea/kent_pipeline_batch.py` - Batch-version av beräkningskedja

**Filer att återanvända (refaktorera):**
- `beräkningskedja.py` → `pre_dea/kent_pipeline_batch.py`
- `parameter_adjustments.py` → `pre_dea/kent_pipeline_batch.py` (merge)
- `capbase_prep.py` → Behåll som den är (steg 1-4)

**Testfall:**
- WACC-skalning: Ändra WACC till 5%, verifiera att CAPEX ändras proportionellt
- Parameter-ändring: Ändra livslängd för kategori 7, verifiera att avskrivning ändras

### Fas 3: DEA-integration (vecka 3)

**Mål:** DEA-analys fungerar i pipeline

**Filer att återanvända (direkt kopiering):**
- `dea_model.py` → `dea/dea_model.py`
- `dea_producer.py` → `dea/dea_runner.py` (simplifierad)

**Testfall:**
- Kör DEA med baseline CAPEX, verifiera mot EIs_DEA.xlsx
- Kör DEA med modifierad CAPEX (WACC 5%), verifiera att effektivitet ändras

### Fas 4: Post-DEA (vecka 3-4)

**Mål:** Effektiviseringskrav och intäktsram beräknas

**Filer att återanvända (refaktorera):**
- `effektiviseringskrav_calculations.py` → `post_dea/effektiviseringskrav.py`
- `intaktsram_assembly.py` (om finns) → `post_dea/intaktsram_assembly.py`

**Testfall:**
- Beräkna effkrav för DMU med potential=0.15, verifiera mot Excel
- Beräkna intäktsram, verifiera summa mot SDF

### Fas 5: UI (vecka 4-5)

**Mål:** Ny Streamlit-app med professionellt utseende

**Filer att skapa:**
1. `app.py` - Huvudapp med navigation
2. `ui/pages/overview.py` - Översiktssida
3. `ui/pages/case_setup.py` - Case-konfiguration
4. `ui/pages/results.py` - Resultatvisning
5. `ui/styles.py` - Mörkblå CSS-profil

**Grafisk profil:**
- Primärfärg: Mörkblå (#1a365d eller liknande)
- Sekundärfärg: Ljusblå för accenter
- Font: Sans-serif (Streamlit default)
- Inga emojis

---

## APPENDIX: STAGE-KONTRAKT

### Stage 1: Baseline Loading

```python
def load_baseline() -> Dict[str, Any]:
    """
    Ladda all baseline-data.
    
    Returns:
        Dict med nycklar:
        - 'df_all_companies': pd.DataFrame
            Kolumner: [DMU, REId, Företag, OPEXp, CAPEX, Avskrivning, 
                      Avkastning, CU, MW, NS, MWhl, MWhh, TOTEX]
            Rader: 148
            Enhet: tkr för kostnader
            
        - 'dea_results': pd.DataFrame
            Kolumner: [DMU, REId, Företag, Effektivitet, 
                      Supereffektivitet, potential, Effkrav_proc]
            Rader: 148
            
        - 'capbase_a': pd.DataFrame
            Kolumner: Se COMPLETE_DATASET_GUIDE
            Rader: ~510,000
            
        - 'wacc': float
            Baseline WACC = 0.0453
            
        - 'sdf_data': Dict[str, Any]
            Opåverkbara kostnader, neonjusteringar, etc. per REId
    """
```

### Stage 2: Pre-DEA

```python
def apply_capex_method(
    df_all: pd.DataFrame,
    capbase_a: pd.DataFrame,
    config: Dict[str, Any]
) -> pd.DataFrame:
    """
    Applicera vald CAPEX-metod.
    
    Args:
        df_all: Baseline DataFrame (148 rader)
        capbase_a: Komponentdata (510k rader)
        config: Dict med:
            - 'method': str ('baseline', 'wacc_scaling', 'parameter_change', 'kent_upload')
            - 'wacc': float (om relevant)
            - 'normvalues': Dict[int, float] (om relevant)
            - 'lifetimes': Dict[int, Dict] (om relevant)
            - 'kent_file': UploadedFile (om relevant)
    
    Returns:
        pd.DataFrame (148 rader)
        Kolumner: [DMU, REId, Företag, CAPEX, OPEXp, CU, MW, NS, MWhl, MWhh]
        CAPEX = Kapitalkostnad för år 2024 (tidskod 229+230)
    
    Side effects:
        Inga (pure function)
    """
```

### Stage 3: DEA

```python
def calculate_efficiency(
    df_modified: pd.DataFrame,
    config: Dict[str, Any],
    baseline_dea: pd.DataFrame
) -> pd.DataFrame:
    """
    Beräkna effektivitet för alla 148 företag.
    
    Args:
        df_modified: DataFrame från Pre-DEA (148 rader)
        config: Dict med:
            - 'method': str ('baseline', 'dea', 'sfa', 'stoned')
            - 'model_spec': Dict (om method != 'baseline')
                - 'inputs': List[str]
                - 'outputs': List[str]
                - 'rts': str ('CRS', 'VRS')
                - 'orientation': str ('input', 'output')
        baseline_dea: EIs_DEA.xlsx DataFrame
    
    Returns:
        pd.DataFrame (148 rader)
        Kolumner: [DMU, REId, Företag, efficiency, potential, is_outlier]
        
        efficiency: float [0, 1] - teknisk effektivitet
        potential: float [0, 1] - effektiviseringspotential
        is_outlier: bool - True om företag är outlier
    """
```

### Stage 4: Extraction

```python
def extract_company(
    df_efficiency: pd.DataFrame,
    user_dmu: int
) -> pd.Series:
    """
    Extrahera data för inloggat företag.
    
    Args:
        df_efficiency: DataFrame från DEA (148 rader)
        user_dmu: DMU för inloggat företag
    
    Returns:
        pd.Series med index:
        [DMU, REId, Företag, efficiency, potential, is_outlier]
    
    Raises:
        ValueError: Om user_dmu inte finns i DataFrame
    """
```

### Stage 5: Post-DEA

```python
def calculate_intaktsram(
    company_data: pd.Series,
    baseline: Dict[str, Any],
    config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Beräkna fullständig intäktsram.
    
    Args:
        company_data: Series från Extraction
        baseline: Dict med SDF-data, etc.
        config: Dict med:
            - 'effkrav_config': Dict
                - 'truncation': float
                - 'iqr_multiplier': float
                - 'outlier_fixed': float
            - 'paverkbara_method': str ('OPEX', 'TOTEX')
    
    Returns:
        Dict med:
        - 'intaktsram_total': float (tkr, periodsumma)
        - 'kapitalkostnad_total': float (tkr, periodsumma)
        - 'avskrivningar': float (tkr, periodsumma)
        - 'avkastning': float (tkr, periodsumma)
        - 'paverkbara_periodsumma': float (tkr)
        - 'opaverkbara': float (tkr, periodsumma)
        - 'effkrav_proc': float (årligt effektiviseringskrav)
        - 'per_year': Dict[int, Dict] (2024-2027, årsvis dekomposition)
        - 'metadata': Dict (config som användes, etc.)
    """
```

---

**Dokumentslut**

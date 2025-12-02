# REGUMETRICA PIPELINE ARCHITECTURE RESPONSE

**Version:** 1.0  
**Datum:** 2025-12-01  
**Från:** Claude Opus 4  
**Till:** Regumetrica development team

---

## INNEHÅLLSFÖRTECKNING

1. [Executive Summary](#1-executive-summary)
2. [Svar på FRÅGA A-C](#2-svar-på-fråga-a-c)
3. [Svar på Architectural Questions 1-4](#3-svar-på-architectural-questions-1-4)
4. [Bekräftelse av Baseline-First Strategy](#4-bekräftelse-av-baseline-first-strategy)
5. [Rekommenderad Filstruktur](#5-rekommenderad-filstruktur)
6. [Namnkonventioner](#6-namnkonventioner)
7. [Stage-kontrakt (Input/Output per Stage)](#7-stage-kontrakt)
8. [Migrationsplan](#8-migrationsplan)
9. [Kodexempel](#9-kodexempel)

---

## 1. EXECUTIVE SUMMARY

### Kärnrekommendationer

| Område | Rekommendation | Motivering |
|--------|----------------|------------|
| **Pipeline Design** | Option C: Funktionell pipeline med stage-functions | Enklast att förstå, underhålla och testa. Passar Python-ekosystemet. |
| **Config Structure** | Hybrid: Stage-based med UI-mapping layer | Balanserar backend-enkelhet med UI-terminologi (Parameters/Variables/Modules) |
| **Dependency Tracking** | Option 2: Stage dependency declarations med cascade | Explicit, underhållbart, lätt att utöka med nya moduler (SFA, StoNED) |
| **Batch Processing** | Unified implementation med `id_network` som nyckel | Undviker kod-duplicering, samma funktioner för 1 och 148 företag |
| **Baseline-First** | **Bekräftat som optimal strategi** | Eliminerar caching-komplexitet, deterministiskt, minneseffektivt |

### Övergripande Arkitektur

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           REGUMETRICA PIPELINE                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌───────┐ │
│  │ BASELINE │───►│ PRE-DEA  │───►│   DEA    │───►│EXTRACTION│───►│POST-  │ │
│  │ LOADING  │    │  CAPEX   │    │ ANALYSIS │    │(1 företag)│   │DEA    │ │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘    └───────┘ │
│       │               │               │               │              │      │
│  df_all_148      df_all_148      df_all_148        df_single    intaktsram  │
│                  _modified       _efficiency                      _dict     │
│                                                                             │
│  [Data_modeller] [capbase_a]    [EIs_DEA.xlsx]                   [SDF]     │
│  [reconciliation]               (baseline)                                  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. SVAR PÅ FRÅGA A-C

### FRÅGA A: Dependency Tracking Implementation

**Rekommendation: Option 2 (Stage Dependency Declarations) med explicit cascade**

```python
# pipeline/stage_dependencies.py

from typing import Set, List
from dataclasses import dataclass
from enum import Enum, auto

class Stage(Enum):
    """Pipeline stages i exekveringsordning."""
    BASELINE = auto()
    PRE_DEA = auto()
    DEA = auto()
    EXTRACTION = auto()
    POST_DEA = auto()

@dataclass
class StageDependencies:
    """Definierar vilka config-nycklar som triggar en stage."""
    stage: Stage
    triggers: Set[str]
    cascades_to: List[Stage]

STAGE_DEPENDENCY_MAP = {
    Stage.PRE_DEA: StageDependencies(
        stage=Stage.PRE_DEA,
        triggers={
            'capex_method',      # baseline, wacc_scaling, parameter_change, kent_upload
            'wacc_value',        # ny WACC-värde
            'normvalue_adj',     # normvärdejusteringar
            'lifetime_adj',      # livslängdsjusteringar
            'kent_file'          # uppladdad KENT-fil
        },
        cascades_to=[Stage.DEA, Stage.EXTRACTION, Stage.POST_DEA]
    ),
    Stage.DEA: StageDependencies(
        stage=Stage.DEA,
        triggers={
            'dea_method',        # baseline, dea, sfa, stoned
            'dea_model_spec',    # inputs, outputs, rts
            'outlier_config'     # q_lower, q_upper, multiplier
        },
        cascades_to=[Stage.EXTRACTION, Stage.POST_DEA]
    ),
    Stage.EXTRACTION: StageDependencies(
        stage=Stage.EXTRACTION,
        triggers={'user_dmu'},   # sällan ändras, men tekniskt en trigger
        cascades_to=[Stage.POST_DEA]
    ),
    Stage.POST_DEA: StageDependencies(
        stage=Stage.POST_DEA,
        triggers={
            'effkrav_truncation_min',
            'effkrav_truncation_max',
            'outlier_krav',
            'paverkbara_method'  # OPEX eller TOTEX
        },
        cascades_to=[]
    )
}

def determine_stages_to_run(
    current_config: dict,
    baseline_config: dict
) -> List[Stage]:
    """
    Bestämmer vilka stages som behöver köras baserat på config-ändringar.
    
    Returns:
        Lista med stages i exekveringsordning
    """
    stages_to_run: Set[Stage] = set()
    
    for stage_def in STAGE_DEPENDENCY_MAP.values():
        # Kolla om någon trigger har ändrats
        for trigger in stage_def.triggers:
            current_val = current_config.get(trigger)
            baseline_val = baseline_config.get(trigger)
            
            if current_val != baseline_val:
                stages_to_run.add(stage_def.stage)
                stages_to_run.update(stage_def.cascades_to)
                break
    
    # Sortera i exekveringsordning
    return sorted(stages_to_run, key=lambda s: s.value)

def is_baseline_only(current_config: dict, baseline_config: dict) -> bool:
    """Returnerar True om alla värden är baseline (ingen beräkning behövs)."""
    return len(determine_stages_to_run(current_config, baseline_config)) == 0
```

**Motivering:**
- Explicit och läsbart - vilka config-nycklar som triggar vilka stages är tydligt
- Cascade-logik är inbyggd - ingen risk att missa downstream-effekter
- Lätt att utöka med nya stages (t.ex. kvalitetsjustering) eller nya effektivitetsmetoder (SFA, StoNED)
- Deterministiskt - samma config ger alltid samma stages_to_run

---

### FRÅGA B: Error Handling i Pipeline

**Rekommendation: Stoppa pipeline och visa tydligt felmeddelande**

```python
# pipeline/error_handling.py

from dataclasses import dataclass
from typing import Optional
from enum import Enum

class PipelineErrorType(Enum):
    DATA_VALIDATION = "data_validation"
    DEA_INFEASIBLE = "dea_infeasible"
    DEA_UNBOUNDED = "dea_unbounded"
    MISSING_DATA = "missing_data"
    CALCULATION_ERROR = "calculation_error"
    KENT_PARSE_ERROR = "kent_parse_error"

@dataclass
class PipelineError:
    """Strukturerat fel från pipeline."""
    error_type: PipelineErrorType
    stage: str
    message: str
    user_message: str
    technical_details: Optional[str] = None
    suggested_action: Optional[str] = None

class PipelineExecutionError(Exception):
    """Exception för pipeline-fel med strukturerad info."""
    def __init__(self, error: PipelineError):
        self.error = error
        super().__init__(error.message)

# Predefinerade fel för vanliga scenarios
DEA_INFEASIBLE_ERROR = PipelineError(
    error_type=PipelineErrorType.DEA_INFEASIBLE,
    stage="DEA",
    message="DEA-modellen har ingen lösning (infeasible)",
    user_message="DEA-analysen kunde inte slutföras. Modellspecifikationen "
                 "resulterar i ett olösbart optimeringsproblem.",
    suggested_action="Prova att:\n"
                     "- Inkludera fler outputs (t.ex. lägg till MWh)\n"
                     "- Kontrollera att alla inputs har positiva värden\n"
                     "- Använd VRS istället för CRS"
)

DEA_NO_OUTPUTS_ERROR = PipelineError(
    error_type=PipelineErrorType.DATA_VALIDATION,
    stage="DEA",
    message="Inga outputs valda för DEA",
    user_message="Du måste välja minst en output-variabel för DEA-analysen.",
    suggested_action="Välj minst en av: CU, MW, NS, MWhl, MWhh"
)

def handle_dea_error(pulp_status: str, model_spec: dict) -> PipelineError:
    """Skapar användarvänligt fel från PuLP-status."""
    if pulp_status == "Infeasible":
        return DEA_INFEASIBLE_ERROR
    elif pulp_status == "Unbounded":
        return PipelineError(
            error_type=PipelineErrorType.DEA_UNBOUNDED,
            stage="DEA",
            message="DEA-modellen är obegränsad (unbounded)",
            user_message="DEA-modellen har ingen begränsad lösning.",
            technical_details=f"Model spec: {model_spec}",
            suggested_action="Kontrollera att inputs och outputs är korrekt valda."
        )
    else:
        return PipelineError(
            error_type=PipelineErrorType.CALCULATION_ERROR,
            stage="DEA",
            message=f"DEA misslyckades: {pulp_status}",
            user_message="Ett oväntat fel uppstod i DEA-beräkningen.",
            technical_details=f"PuLP status: {pulp_status}"
        )
```

**UI-integration i Streamlit:**

```python
# I streamlit_app.py eller pipeline runner

def run_pipeline_with_error_handling(config: dict, baseline: dict):
    """Kör pipeline med felhantering för UI."""
    try:
        result = run_pipeline(config, baseline)
        return {"success": True, "result": result}
    
    except PipelineExecutionError as e:
        error = e.error
        return {
            "success": False,
            "error": {
                "stage": error.stage,
                "message": error.user_message,
                "suggested_action": error.suggested_action,
                "technical_details": error.technical_details
            }
        }

# I UI:
result = run_pipeline_with_error_handling(config, baseline)
if not result["success"]:
    error = result["error"]
    st.error(f"**Fel i {error['stage']}:** {error['message']}")
    if error["suggested_action"]:
        st.info(f"**Förslag:** {error['suggested_action']}")
    with st.expander("Tekniska detaljer"):
        st.code(error.get("technical_details", "Inga detaljer"))
```

---

### FRÅGA C: Concurrent Users och Baseline Sharing

**Rekommendation: Ladda baseline separat per session**

**Ja, jag håller med att ladda baseline per session är bäst.** Här är analysen:

| Approach | Memory | Komplexitet | Concurrency Risk | Rekommendation |
|----------|--------|-------------|------------------|----------------|
| **Shared baseline (global)** | Låg | Hög | Medel (read-only safe men refcount issues) | ❌ |
| **Baseline per session** | Medel | Låg | Ingen | ✅ |
| **Lazy loading med cache** | Variabel | Hög | Låg | ❌ (onödig komplexitet) |

**Motivering:**

1. **Memory overhead är acceptabelt:**
   - Data_modeller.xlsx: ~148 rows × 12 cols = ~2KB
   - EIs_DEA.xlsx: ~148 rows × 7 cols = ~1KB  
   - capbase_a.parquet: ~510k rows × 33 cols = ~50-100MB (men delas via parquet caching)
   - Total per session: <5MB för de lätta filerna
   - Render Standard plan har 2GB RAM - stödjer ~20-40 concurrent sessions

2. **Streamlit's session_state är designat för detta:**
   ```python
   # session_state är isolerat per browser-session
   if 'baseline' not in st.session_state:
       st.session_state.baseline = load_all_baseline_data()
   ```

3. **Ingen risk för race conditions eller datakorruption**

4. **Parquet-filer cachas automatiskt av OS/pandas:**
   ```python
   # Parquet läsning är memory-mapped, så 20 sessioner delar samma fysiska data
   df = pd.read_parquet('capbase_a.parquet')  # Effektivt cachad
   ```

**Implementation:**

```python
# pipeline/session_baseline.py

import streamlit as st
import pandas as pd
from functools import lru_cache
from pathlib import Path

DATA_DIR = Path("data")

@st.cache_data(ttl=3600)  # Cache i 1 timme, delas mellan sessioner
def _load_data_modeller() -> pd.DataFrame:
    """Laddar Data_modeller.xlsx (liten fil, cachebart)."""
    return pd.read_excel(DATA_DIR / "Data_modeller.xlsx", sheet_name="Körning")

@st.cache_data(ttl=3600)
def _load_eis_dea() -> pd.DataFrame:
    """Laddar EIs_DEA.xlsx (Ei's officiella DEA-resultat)."""
    return pd.read_excel(DATA_DIR / "EIs_DEA.xlsx", sheet_name="Körning")

@st.cache_data(ttl=3600)
def _load_capbase_a() -> pd.DataFrame:
    """Laddar capbase_a.parquet (stor fil, memory-mapped)."""
    return pd.read_parquet(DATA_DIR / "capbase_a.parquet")

@st.cache_data(ttl=3600)
def _load_sdf() -> pd.DataFrame:
    """Laddar SDF-data för opåverkbara kostnader."""
    return pd.read_excel(
        DATA_DIR / "Löpande_kostnader_från_SDF_2024-27.xlsx",
        sheet_name="IR 2024-2027"
    )

@st.cache_data(ttl=3600)
def _load_reconciliation() -> pd.DataFrame:
    """Laddar ID-mappning mellan DMU, REId, id_network."""
    return pd.read_csv(DATA_DIR / "reconciliation_id_network_firm_dmu.csv")

def init_session_baseline():
    """Initierar baseline-data i session_state."""
    if 'baseline' not in st.session_state:
        st.session_state.baseline = {
            'df_all_companies': _load_data_modeller().copy(),
            'dea_baseline': _load_eis_dea().copy(),
            'capbase_a': _load_capbase_a(),  # Ingen copy() - stor fil
            'sdf': _load_sdf().copy(),
            'reconciliation': _load_reconciliation(),
            'wacc_baseline': 0.0453,
            'config_baseline': get_baseline_config()
        }

def get_baseline_config() -> dict:
    """Returnerar baseline-konfiguration (Ei's standardvärden)."""
    return {
        'capex_method': 'baseline',
        'wacc_value': 0.0453,
        'normvalue_adj': None,
        'lifetime_adj': None,
        'kent_file': None,
        'dea_method': 'baseline',
        'dea_model_spec': {
            'inputs': ['CAPEX', 'OPEXp'],
            'outputs': ['CU', 'MW', 'NS', 'MWhl', 'MWhh'],
            'rts': 'crs'
        },
        'outlier_config': {'q_lower': 25, 'q_upper': 75, 'multiplier': 2.0},
        'effkrav_truncation_min': 0.162416,
        'effkrav_truncation_max': 0.30,
        'outlier_krav': 0.01,
        'paverkbara_method': 'OPEX'
    }
```

---

## 3. SVAR PÅ ARCHITECTURAL QUESTIONS 1-4

### Architectural Question 1: Pipeline Class Design

**Rekommendation: Option C (Functional Pipeline) med Stage-protokoll**

```python
# pipeline/core.py

from typing import Protocol, Dict, Any, Optional
from dataclasses import dataclass
import pandas as pd

@dataclass
class StageResult:
    """Standardiserat resultat från varje stage."""
    data: pd.DataFrame
    metadata: Dict[str, Any]

class StageProtocol(Protocol):
    """Protokoll som alla stages måste följa."""
    def run(self, input_data: Any, config: dict) -> StageResult:
        ...

# Stage functions - rena funktioner utan sidoeffekter
def run_pre_dea_stage(
    df_baseline: pd.DataFrame,
    capbase_a: pd.DataFrame,
    config: dict
) -> StageResult:
    """
    Stage 2: Pre-DEA CAPEX Modification
    
    Input:
        df_baseline: DataFrame [148 rows] från Data_modeller.xlsx
        capbase_a: DataFrame [~510k rows] för CAPEX-beräkning
        config: {'capex_method': str, 'wacc_value': float, ...}
    
    Output:
        StageResult med df_all_companies_modified [148 rows]
    """
    method = config.get('capex_method', 'baseline')
    
    if method == 'baseline':
        return StageResult(
            data=df_baseline.copy(),
            metadata={'method': 'baseline', 'modified': False}
        )
    
    elif method == 'wacc_scaling':
        return _apply_wacc_scaling(df_baseline, config)
    
    elif method == 'parameter_change':
        return _apply_parameter_changes(df_baseline, capbase_a, config)
    
    elif method == 'kent_upload':
        return _apply_kent_upload(df_baseline, capbase_a, config)
    
    else:
        raise ValueError(f"Okänd capex_method: {method}")

def run_dea_stage(
    df_pre_dea: pd.DataFrame,
    dea_baseline: pd.DataFrame,
    config: dict
) -> StageResult:
    """
    Stage 3: Efficiency Analysis
    
    Input:
        df_pre_dea: DataFrame [148 rows] med CAPEX från Stage 2
        dea_baseline: DataFrame [148 rows] från EIs_DEA.xlsx (baseline)
        config: {'dea_method': str, 'dea_model_spec': dict, ...}
    
    Output:
        StageResult med df_all_companies_efficiency [148 rows]
    """
    method = config.get('dea_method', 'baseline')
    
    if method == 'baseline':
        return StageResult(
            data=dea_baseline.copy(),
            metadata={'method': 'baseline', 'source': 'EIs_DEA.xlsx'}
        )
    
    elif method == 'dea':
        return _run_dea_analysis(df_pre_dea, config)
    
    # Framtida: SFA, StoNED
    else:
        raise ValueError(f"Okänd dea_method: {method}")

def run_extraction_stage(
    df_efficiency: pd.DataFrame,
    user_dmu: int
) -> StageResult:
    """
    Stage 4: Extract single company
    
    Input:
        df_efficiency: DataFrame [148 rows] med efficiency scores
        user_dmu: int (DMU för inloggat företag)
    
    Output:
        StageResult med df_single_company [1 row]
    """
    df_single = df_efficiency[df_efficiency['DMU'] == user_dmu].copy()
    
    if df_single.empty:
        raise ValueError(f"DMU {user_dmu} finns inte i data")
    
    return StageResult(
        data=df_single,
        metadata={'user_dmu': user_dmu, 'extracted_at': 'extraction_stage'}
    )

def run_post_dea_stage(
    df_single: pd.DataFrame,
    sdf_data: pd.DataFrame,
    capex_periodsumma: Optional[pd.DataFrame],  # Från kent_pipeline om metod 3-4
    config: dict
) -> StageResult:
    """
    Stage 5: Intäktsram calculation
    
    Input:
        df_single: DataFrame [1 row] med efficiency för inloggat företag
        sdf_data: DataFrame med baseline opåverkbara etc.
        capex_periodsumma: DataFrame med kapitalkostnader per år (om beräknat)
        config: {'effkrav_*': ..., 'paverkbara_method': str}
    
    Output:
        StageResult med intäktsram-dict
    """
    # Beräkna effektiviseringskrav
    effkrav_proc = _calculate_effkrav(df_single, config)
    
    # Beräkna påverkbara kostnader
    paverkbara = _calculate_paverkbara(sdf_data, effkrav_proc, config)
    
    # Sammanställ intäktsram
    intaktsram = _assemble_intaktsram(
        kapitalkostnad=capex_periodsumma,
        paverkbara=paverkbara,
        sdf_data=sdf_data,
        config=config
    )
    
    return StageResult(
        data=pd.DataFrame([intaktsram]),
        metadata={'effkrav_proc': effkrav_proc, 'method': config.get('paverkbara_method')}
    )

# Pipeline orchestrator
def run_pipeline(config: dict, baseline: dict) -> dict:
    """
    Huvudfunktion för att köra hela pipelinen.
    
    Implementerar smart execution - hoppar över stages där baseline kan användas.
    """
    from pipeline.stage_dependencies import determine_stages_to_run, Stage
    
    stages_needed = determine_stages_to_run(config, baseline['config_baseline'])
    
    # Stage 1: Baseline alltid tillgänglig
    df_baseline = baseline['df_all_companies']
    capbase_a = baseline['capbase_a']
    dea_baseline = baseline['dea_baseline']
    sdf_data = baseline['sdf']
    
    # Stage 2: Pre-DEA
    if Stage.PRE_DEA in stages_needed:
        pre_dea_result = run_pre_dea_stage(df_baseline, capbase_a, config)
        df_pre_dea = pre_dea_result.data
        capex_periodsumma = pre_dea_result.metadata.get('capex_periodsumma')
    else:
        df_pre_dea = df_baseline
        capex_periodsumma = None
    
    # Stage 3: DEA
    if Stage.DEA in stages_needed:
        dea_result = run_dea_stage(df_pre_dea, dea_baseline, config)
        df_efficiency = dea_result.data
    else:
        df_efficiency = dea_baseline
    
    # Stage 4: Extraction (alltid snabb, kör alltid)
    extraction_result = run_extraction_stage(df_efficiency, config['user_dmu'])
    df_single = extraction_result.data
    
    # Stage 5: Post-DEA
    post_dea_result = run_post_dea_stage(
        df_single, sdf_data, capex_periodsumma, config
    )
    
    return {
        'intaktsram': post_dea_result.data.to_dict('records')[0],
        'metadata': {
            'stages_executed': [s.name for s in stages_needed],
            'pre_dea': pre_dea_result.metadata if Stage.PRE_DEA in stages_needed else None,
            'dea': dea_result.metadata if Stage.DEA in stages_needed else None,
            'post_dea': post_dea_result.metadata
        }
    }
```

**Motivering för funktionell approach:**

1. **Testbarhet:** Varje stage-funktion kan testas isolerat med mock-data
2. **Enkelhet:** Ingen klass-hierarki att navigera
3. **Transparens:** Hela flödet syns i `run_pipeline()`
4. **Pythoniskt:** Följer konventioner i pandas/numpy-ekosystemet
5. **Utbyggbart:** Lägg till ny stage = lägg till ny funktion

---

### Architectural Question 2: Config Structure

**Rekommendation: Stage-based config (Option A) med UI-mapping layer**

```python
# config/case_definition.py

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from enum import Enum

class CapexMethod(Enum):
    BASELINE = "baseline"
    WACC_SCALING = "wacc_scaling"
    PARAMETER_CHANGE = "parameter_change"
    KENT_UPLOAD = "kent_upload"

class EfficiencyMethod(Enum):
    BASELINE = "baseline"
    DEA = "dea"
    SFA = "sfa"        # Framtida
    STONED = "stoned"  # Framtida

class PaverkbaraMethod(Enum):
    OPEX = "OPEX"
    TOTEX = "TOTEX"

@dataclass
class PreDeaConfig:
    """Konfiguration för Stage 2: Pre-DEA"""
    method: CapexMethod = CapexMethod.BASELINE
    wacc_value: float = 0.0453
    normvalue_adjustments: Optional[Dict[str, float]] = None
    lifetime_adjustments: Optional[Dict[str, float]] = None
    kent_file_data: Optional[Any] = None

@dataclass
class DeaConfig:
    """Konfiguration för Stage 3: DEA"""
    method: EfficiencyMethod = EfficiencyMethod.BASELINE
    inputs: List[str] = field(default_factory=lambda: ["CAPEX", "OPEXp"])
    outputs: List[str] = field(default_factory=lambda: ["CU", "MW", "NS", "MWhl", "MWhh"])
    rts: str = "crs"
    outlier_q_lower: float = 25.0
    outlier_q_upper: float = 75.0
    outlier_multiplier: float = 2.0

@dataclass  
class PostDeaConfig:
    """Konfiguration för Stage 5: Post-DEA"""
    effkrav_truncation_min: float = 0.162416
    effkrav_truncation_max: float = 0.30
    outlier_krav: float = 0.01
    paverkbara_method: PaverkbaraMethod = PaverkbaraMethod.OPEX

@dataclass
class CaseDefinition:
    """Komplett case definition för pipeline."""
    name: str
    user_dmu: int
    pre_dea: PreDeaConfig = field(default_factory=PreDeaConfig)
    dea: DeaConfig = field(default_factory=DeaConfig)
    post_dea: PostDeaConfig = field(default_factory=PostDeaConfig)
    
    def to_flat_config(self) -> dict:
        """Konverterar till flat dict för pipeline execution."""
        return {
            'user_dmu': self.user_dmu,
            'capex_method': self.pre_dea.method.value,
            'wacc_value': self.pre_dea.wacc_value,
            'normvalue_adj': self.pre_dea.normvalue_adjustments,
            'lifetime_adj': self.pre_dea.lifetime_adjustments,
            'kent_file': self.pre_dea.kent_file_data,
            'dea_method': self.dea.method.value,
            'dea_model_spec': {
                'inputs': self.dea.inputs,
                'outputs': self.dea.outputs,
                'rts': self.dea.rts
            },
            'outlier_config': {
                'q_lower': self.dea.outlier_q_lower,
                'q_upper': self.dea.outlier_q_upper,
                'multiplier': self.dea.outlier_multiplier
            },
            'effkrav_truncation_min': self.post_dea.effkrav_truncation_min,
            'effkrav_truncation_max': self.post_dea.effkrav_truncation_max,
            'outlier_krav': self.post_dea.outlier_krav,
            'paverkbara_method': self.post_dea.paverkbara_method.value
        }
```

**UI-Mapping Layer (Parameters/Variables/Modules):**

```python
# ui/config_mapping.py

"""
Mappar UI-terminologi (Parameters, Variables, Modules) till backend CaseDefinition.

Terminologi från User Manual:
- Parameters: Uniforma värden för alla 148 företag (WACC, normvärden, livslängder)
- Variables: Företagsspecifika mätvärden (KENT-fil med nya komponenter)
- Modules: Val av beräkningsmetod (DEA vs SFA, OPEX vs TOTEX)
"""

from typing import Dict, Any, Tuple
from config.case_definition import CaseDefinition, CapexMethod, EfficiencyMethod

# Mapping: UI-koncept → backend config paths
UI_TO_CONFIG_MAPPING = {
    # PARAMETERS (uniform för alla 148)
    'parameters': {
        'wacc': ('pre_dea', 'wacc_value'),
        'normvärden': ('pre_dea', 'normvalue_adjustments'),
        'livslängder': ('pre_dea', 'lifetime_adjustments'),
        'trunkering_min': ('post_dea', 'effkrav_truncation_min'),
        'trunkering_max': ('post_dea', 'effkrav_truncation_max'),
        'outlier_krav': ('post_dea', 'outlier_krav'),
    },
    # VARIABLES (företagsspecifika)
    'variables': {
        'kent_fil': ('pre_dea', 'kent_file_data'),
        # Volymer är read-only från Data_modeller
    },
    # MODULES (metodval)
    'modules': {
        'capex_metod': ('pre_dea', 'method'),
        'effektivitet_metod': ('dea', 'method'),
        'dea_inputs': ('dea', 'inputs'),
        'dea_outputs': ('dea', 'outputs'),
        'dea_rts': ('dea', 'rts'),
        'paverkbara_metod': ('post_dea', 'paverkbara_method'),
    }
}

def apply_ui_change(
    case_def: CaseDefinition,
    ui_category: str,  # 'parameters', 'variables', 'modules'
    ui_key: str,
    value: Any
) -> CaseDefinition:
    """
    Applicerar en UI-ändring på CaseDefinition.
    
    Exempel:
        apply_ui_change(case, 'parameters', 'wacc', 0.05)
        apply_ui_change(case, 'modules', 'effektivitet_metod', 'dea')
    """
    if ui_category not in UI_TO_CONFIG_MAPPING:
        raise ValueError(f"Okänd UI-kategori: {ui_category}")
    
    mapping = UI_TO_CONFIG_MAPPING[ui_category]
    if ui_key not in mapping:
        raise ValueError(f"Okänd UI-nyckel: {ui_key}")
    
    stage_name, attr_name = mapping[ui_key]
    stage_config = getattr(case_def, stage_name)
    setattr(stage_config, attr_name, value)
    
    # Auto-uppdatera capex_method baserat på ändringar
    _update_capex_method_if_needed(case_def)
    
    return case_def

def _update_capex_method_if_needed(case_def: CaseDefinition):
    """Sätter capex_method baserat på vilka ändringar som gjorts."""
    pre_dea = case_def.pre_dea
    
    if pre_dea.kent_file_data is not None:
        pre_dea.method = CapexMethod.KENT_UPLOAD
    elif pre_dea.normvalue_adjustments or pre_dea.lifetime_adjustments:
        pre_dea.method = CapexMethod.PARAMETER_CHANGE
    elif pre_dea.wacc_value != 0.0453:
        pre_dea.method = CapexMethod.WACC_SCALING
    else:
        pre_dea.method = CapexMethod.BASELINE

def get_ui_value(case_def: CaseDefinition, ui_category: str, ui_key: str) -> Any:
    """Hämtar värde för UI-display."""
    stage_name, attr_name = UI_TO_CONFIG_MAPPING[ui_category][ui_key]
    stage_config = getattr(case_def, stage_name)
    return getattr(stage_config, attr_name)
```

---

### Architectural Question 3: Dependency Tracking

**Besvarad i FRÅGA A.** Sammanfattning:

- **Explicit dependency declarations** (Option 2) rekommenderas
- Cascade-logik inbyggd i `StageDependencies.cascades_to`
- Funktionen `determine_stages_to_run()` returnerar exakt vilka stages som behövs
- Enkelt att utöka: lägg till nya triggers eller stages i `STAGE_DEPENDENCY_MAP`

---

### Architectural Question 4: Batch Processing för Kent Pipeline

**Rekommendation: Unified implementation med `id_network` som grupperingsnyckel**

Nuvarande kod i `kent_pipeline.py` är byggd för enstaka DMU. För att stödja batch-processing (alla 148 företag) behöver vi:

1. **Behåll samma beräkningslogik** - den är korrekt
2. **Lägg till gruppering på `id_network`** - för att separera företag
3. **Returnera aggregerade resultat per företag och år**

```python
# pipeline/stages/kent_batch.py

"""
Kent Pipeline med batch-processing för alla 148 företag.
Återanvänder beräkningslogik från kent_pipeline.py.
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional

# Tidskod-konstanter
TIMECODES = {
    2024: [229, 230],
    2025: [231, 232],
    2026: [233, 234],
    2027: [235, 236]
}

def run_kent_pipeline_batch(
    capbase_a: pd.DataFrame,
    normvalue_adj: Optional[Dict[str, float]] = None,
    lifetime_adj: Optional[Dict[str, float]] = None,
    wacc: float = 0.0453
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Kör beräkningskedja steg 5-8 för ALLA 148 företag.
    
    Args:
        capbase_a: DataFrame med alla företags komponentdata (~510k rader)
        normvalue_adj: Dict med normvärdejusteringar (optional)
        lifetime_adj: Dict med livslängdsjusteringar (optional)
        wacc: Kalkylränta (default: Ei's 4.53%)
    
    Returns:
        Tuple med:
        - df_capex_2024: DataFrame [148 rows] med CAPEX för år 2024 (för DEA)
        - df_capex_period: DataFrame [148 rows × 4 years] med kapitalkostnader per år
    """
    df = capbase_a.copy()
    
    # Steg 5.1: Applicera normvärdejusteringar (om angivna)
    if normvalue_adj:
        df = _apply_normvalue_adjustments_batch(df, normvalue_adj)
    
    # Steg 5.2: Applicera livslängdsjusteringar (om angivna)
    if lifetime_adj:
        df = _apply_lifetime_adjustments_batch(df, lifetime_adj)
    
    # Steg 5.3: Beräkna åldrar och NUAV för alla tidskoder
    df = _calculate_ages_and_nuav_batch(df)
    
    # Steg 6: Beräkna avskrivningar
    df = _calculate_depreciation_batch(df)
    
    # Steg 7: Beräkna avkastning
    df = _calculate_returns_batch(df, wacc)
    
    # Steg 8: Aggregera till företagsnivå
    df_capex_2024 = _aggregate_capex_for_dea(df)
    df_capex_period = _aggregate_capex_period(df)
    
    return df_capex_2024, df_capex_period

def _calculate_ages_and_nuav_batch(df: pd.DataFrame) -> pd.DataFrame:
    """
    Beräknar åldrar och NUAV för alla tidsperioder och alla företag.
    Vectoriserad implementation för prestanda.
    """
    result = df.copy()
    
    for time in range(229, 237):
        # Ålder vid tidpunkt
        result[f'age_component_{time}'] = time - result['time_from']
        
        # Investeringsålder (för nya komponenter)
        result[f'age_invest_{time}'] = np.where(
            result['capbase_existing'] == 0,
            time - result['time_invest'],
            np.nan
        )
        
        # Ordinarie period (inom ekdep)
        mask_ord = (
            (result[f'age_component_{time}'] > 0) &
            (result[f'age_component_{time}'] <= result['ekdep'])
        )
        result[f'nuav_ord_{time}'] = np.where(mask_ord, result['nuav_2022'], 0)
        
        # Svansperiod (ekdep < ålder <= maxdep)
        mask_tail = (
            (result[f'age_component_{time}'] > result['ekdep']) &
            (result[f'age_component_{time}'] <= result['maxdep'])
        )
        result[f'nuav_tail_{time}'] = np.where(mask_tail, result['nuav_2022'], 0)
    
    return result

def _calculate_depreciation_batch(df: pd.DataFrame) -> pd.DataFrame:
    """Beräknar avskrivningar för alla tidskoder."""
    result = df.copy()
    
    for time in range(229, 237):
        # Ordinarie avskrivning
        result[f'dep_ord_{time}'] = result[f'nuav_ord_{time}'] / result['ekdep']
        
        # Svansavskrivning (baserad på kvarvarande livslängd)
        age = result[f'age_component_{time}']
        remaining = result['maxdep'] - age
        result[f'dep_tail_{time}'] = np.where(
            remaining > 0,
            result[f'nuav_tail_{time}'] / remaining,
            0
        )
    
    return result

def _calculate_returns_batch(df: pd.DataFrame, wacc: float) -> pd.DataFrame:
    """Beräknar avkastning för alla tidskoder."""
    result = df.copy()
    
    ekdep2 = result['ekdep'] / 2
    
    for time in range(229, 237):
        age = result[f'age_component_{time}']
        
        # Justera ålder för halvår
        age_adj = np.where(age % 2 == 1, age + 1, age) / 2 - 1
        
        # Kvarvarande kapital ordinarie period
        capbase_left_ord = np.where(
            age_adj >= 0,
            ((ekdep2 - age_adj) / ekdep2) * result[f'nuav_ord_{time}'],
            0
        )
        result[f'return_ord_{time}'] = wacc * capbase_left_ord / 2
        
        # Kvarvarande kapital svansperiod
        capbase_left_tail = np.where(
            age_adj > 0,
            result[f'nuav_tail_{time}'] / (age_adj + 1),
            0
        )
        result[f'return_tail_{time}'] = wacc * capbase_left_tail / 2
    
    return result

def _aggregate_capex_for_dea(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregerar CAPEX för år 2024 (tidskoder 229+230) per företag.
    Output: 148 rader med [id_network, Avskrivning, Avkastning, CAPEX]
    """
    # Summera för tidskoder 229 och 230 (2024)
    agg_dict = {}
    for tc in [229, 230]:
        for prefix in ['dep_ord_', 'dep_tail_', 'return_ord_', 'return_tail_']:
            col = f'{prefix}{tc}'
            if col in df.columns:
                if f'{prefix}sum' not in agg_dict:
                    agg_dict[f'{prefix}sum'] = df.groupby('id_network')[col].sum()
                else:
                    agg_dict[f'{prefix}sum'] += df.groupby('id_network')[col].sum()
    
    result = pd.DataFrame({
        'id_network': agg_dict['dep_ord_sum'].index,
        'Avskrivning': (agg_dict['dep_ord_sum'] + agg_dict['dep_tail_sum']).values / 1000,
        'Avkastning': (agg_dict['return_ord_sum'] + agg_dict['return_tail_sum']).values / 1000
    })
    result['CAPEX'] = result['Avskrivning'] + result['Avkastning']
    
    return result

def _aggregate_capex_period(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregerar kapitalkostnader per företag och år (2024-2027).
    Output: 148 rader med årsvisa kolumner + periodsumma
    """
    records = []
    
    for id_network in df['id_network'].unique():
        df_company = df[df['id_network'] == id_network]
        record = {'id_network': id_network}
        
        total_period = 0
        for year, timecodes in TIMECODES.items():
            year_total = 0
            for tc in timecodes:
                dep = df_company[f'dep_ord_{tc}'].sum() + df_company[f'dep_tail_{tc}'].sum()
                ret = df_company[f'return_ord_{tc}'].sum() + df_company[f'return_tail_{tc}'].sum()
                year_total += dep + ret
            
            record[f'CAPEX_{year}'] = year_total / 1000  # tkr
            total_period += year_total
        
        record['CAPEX_Period'] = total_period / 1000
        records.append(record)
    
    return pd.DataFrame(records)

def merge_kent_result_with_dea_input(
    df_baseline: pd.DataFrame,
    df_kent_capex: pd.DataFrame,
    reconciliation: pd.DataFrame
) -> pd.DataFrame:
    """
    Ersätter CAPEX i baseline med omberäknade värden från kent_pipeline.
    
    Args:
        df_baseline: Data_modeller.xlsx [148 rows]
        df_kent_capex: Output från _aggregate_capex_for_dea() [148 rows]
        reconciliation: ID-mappning
    
    Returns:
        df_baseline med uppdaterad CAPEX, Avskrivning, Avkastning
    """
    # Skapa mapping id_network → DMU
    id_to_dmu = reconciliation.set_index('id_network')['DMU'].to_dict()
    df_kent_capex['DMU'] = df_kent_capex['id_network'].map(id_to_dmu)
    
    # Merge och ersätt
    result = df_baseline.copy()
    kent_indexed = df_kent_capex.set_index('DMU')
    
    for dmu in kent_indexed.index:
        if dmu in result['DMU'].values:
            idx = result[result['DMU'] == dmu].index[0]
            result.loc[idx, 'CAPEX'] = kent_indexed.loc[dmu, 'CAPEX']
            result.loc[idx, 'Avskrivning'] = kent_indexed.loc[dmu, 'Avskrivning']
            result.loc[idx, 'Avkastning'] = kent_indexed.loc[dmu, 'Avkastning']
    
    return result
```

**Kritiska noteringar:**

1. **id_network är nyckeln** - alla aggregeringar sker per `id_network`, sedan mappas till DMU via reconciliation
2. **Två outputs:**
   - `df_capex_2024` → DEA (endast 2024, tidskod 229+230)
   - `df_capex_period` → Intäktsram (alla år + periodsumma)
3. **Vectoriserade operationer** - använder numpy/pandas broadcasting istället för loopar
4. **Enhetlig implementation** - samma kod för 1 eller 148 företag

---

## 4. BEKRÄFTELSE AV BASELINE-FIRST STRATEGY

**Jag bekräftar att Baseline-First Strategy är optimal för Regumetrica.**

### Varför det fungerar

| Aspekt | Baseline-First | Alternativ (Caching) |
|--------|---------------|---------------------|
| **Komplexitet** | Låg - "om baseline → använd fil, annars → beräkna" | Hög - cache invalidation, dependency tracking |
| **Determinism** | Samma config → samma resultat, alltid | Risk för stale cache |
| **Memory** | Endast baseline laddas per session | Alla varianter måste cachas |
| **Debugging** | Enkelt - tydligt varifrån data kommer | Svårt - oklart om cache eller beräkning |

### Baseline-data per stage (från datasets)

| Stage | Baseline Dataset | Alltid Tillgänglig |
|-------|------------------|-------------------|
| Pre-DEA | Data_modeller.xlsx (148 rader) | ✅ |
| DEA | EIs_DEA.xlsx (Ei's officiella resultat) | ✅ |
| Post-DEA | SDF + EIs_DEA.xlsx Effkrav_proc | ✅ |

### Edge Cases där beräkning krävs

1. **WACC-skalning:** Skala Avkastning-kolumnen → kör Pre-DEA + DEA + Post-DEA
2. **Parameter-ändringar:** Kör kent_pipeline batch → kör Pre-DEA + DEA + Post-DEA
3. **KENT-upload:** Kör capbase_prep + kent_pipeline → kör Pre-DEA + DEA + Post-DEA
4. **Ny DEA-modellspec:** Använd baseline CAPEX → kör DEA + Post-DEA
5. **Ny effkrav-config:** Använd baseline DEA → kör endast Post-DEA

### Implementation i kod

```python
def run_pipeline_smart(config: dict, baseline: dict) -> dict:
    """
    Smart execution med baseline-first strategy.
    """
    from pipeline.stage_dependencies import determine_stages_to_run, Stage, is_baseline_only
    
    # Snabbast möjliga: allt är baseline
    if is_baseline_only(config, baseline['config_baseline']):
        return _assemble_from_baseline_only(baseline, config['user_dmu'])
    
    # Annars: kör endast nödvändiga stages
    stages = determine_stages_to_run(config, baseline['config_baseline'])
    return _run_stages(stages, config, baseline)

def _assemble_from_baseline_only(baseline: dict, user_dmu: int) -> dict:
    """
    Sammanställ intäktsram enbart från baseline-data.
    Extremt snabbt - ingen beräkning.
    """
    dea_row = baseline['dea_baseline'][baseline['dea_baseline']['DMU'] == user_dmu].iloc[0]
    sdf_row = _get_sdf_row(baseline['sdf'], user_dmu)
    
    return {
        'intaktsram': {
            'Kapitalkostnad_Total': sdf_row['Kapitalkostnad'],
            'Avskrivningar': sdf_row['Kapital-förslitning'],
            'Avkastning': sdf_row['Kapital-bindning'],
            'Påverkbara_Periodsumma': sdf_row['Påverkbara kostnader'],
            'Opåverkbara_Kostnader': sdf_row['Opåverkbara kostnader'],
            'Intäktsram_Total': sdf_row['BERÄKNAD INTÄKTSRAM']
        },
        'metadata': {
            'stages_executed': [],
            'source': 'baseline_only'
        }
    }
```

---

## 5. REKOMMENDERAD FILSTRUKTUR

```
regumetrica/
├── streamlit_app.py              # Entry point
├── requirements.txt
│
├── config/
│   ├── __init__.py
│   ├── case_definition.py        # CaseDefinition dataclasses
│   ├── constants.py              # TIMECODES, BASELINE_WACC, etc.
│   └── ui_mapping.py             # Parameters/Variables/Modules → config
│
├── pipeline/
│   ├── __init__.py
│   ├── core.py                   # run_pipeline(), StageResult
│   ├── stage_dependencies.py     # determine_stages_to_run()
│   ├── error_handling.py         # PipelineError, PipelineExecutionError
│   │
│   └── stages/
│       ├── __init__.py
│       ├── baseline_loader.py    # init_session_baseline()
│       ├── pre_dea.py            # run_pre_dea_stage(), WACC-scaling
│       ├── kent_batch.py         # run_kent_pipeline_batch()
│       ├── dea.py                # run_dea_stage()
│       ├── extraction.py         # run_extraction_stage()
│       └── post_dea.py           # run_post_dea_stage()
│
├── calculations/
│   ├── __init__.py
│   ├── wacc.py                   # ei_wacc_real_pre_tax(), Hamada
│   ├── dea_model.py              # Super-efficiency DEA med PuLP
│   ├── effektiviseringskrav.py   # calculate_effkrav_from_potential()
│   ├── paverkbara.py             # calculate_paverkbara_avdrag()
│   └── intaktsram_assembly.py    # assemble_intaktsram()
│
├── data/
│   ├── Data_modeller.xlsx
│   ├── EIs_DEA.xlsx
│   ├── capbase_a.parquet
│   ├── Löpande_kostnader_från_SDF_2024-27.xlsx
│   └── reconciliation_id_network_firm_dmu.csv
│
├── ui/
│   ├── __init__.py
│   ├── auth/
│   │   └── firebase_auth.py
│   │
│   ├── pages/
│   │   ├── case_setup.py         # Skapa/välj case
│   │   ├── configuration.py      # Parameters, Variables, Modules tabs
│   │   ├── execution.py          # Kör pipeline, visa progress
│   │   └── results.py            # Visualisera intäktsram
│   │
│   └── components/
│       ├── wacc_calculator.py    # CAPM-UI
│       ├── dea_config.py         # DEA-modellspec UI
│       ├── kent_uploader.py      # KENT-fil upload
│       └── result_visualization.py  # Stapeldiagram, tabeller
│
└── tests/
    ├── test_pipeline.py
    ├── test_dea_model.py
    ├── test_kent_batch.py
    └── fixtures/
        └── test_data.py
```

---

## 6. NAMNKONVENTIONER

### DataFrame Scope-suffix

| Suffix | Betydelse | Antal rader | Exempel |
|--------|-----------|-------------|---------|
| `_all_148` | Alla 148 företag | 148 | `df_dea_input_all_148` |
| `_single` | Ett företag (user_dmu) | 1 | `df_efficiency_single` |
| `_batch` | Alla företag (för beräkning) | 148 | `capbase_results_batch` |

### CAPEX-funktioner

| Funktion | Returnerar | Granularitet | Användning |
|----------|-----------|--------------|------------|
| `get_capex_for_dea()` | CAPEX år 2024 | Per företag | Input till DEA |
| `get_capex_periodsumma()` | CAPEX 2024-2027 | Per företag, per år | Intäktsram |
| `apply_wacc_scaling()` | Skalad CAPEX | Per företag | Pre-DEA metod 2 |

### Config-nycklar

```python
# Konsekvent naming för config
CONFIG_KEYS = {
    # Pre-DEA
    'capex_method': str,        # 'baseline', 'wacc_scaling', 'parameter_change', 'kent_upload'
    'wacc_value': float,
    'normvalue_adj': dict,
    'lifetime_adj': dict,
    'kent_file': Any,
    
    # DEA
    'dea_method': str,          # 'baseline', 'dea', 'sfa', 'stoned'
    'dea_model_spec': dict,     # {'inputs': [...], 'outputs': [...], 'rts': str}
    'outlier_config': dict,     # {'q_lower': float, 'q_upper': float, 'multiplier': float}
    
    # Post-DEA
    'effkrav_truncation_min': float,
    'effkrav_truncation_max': float,
    'outlier_krav': float,
    'paverkbara_method': str,   # 'OPEX', 'TOTEX'
}
```

### Variabelnamn i DataFrames

| Nuvarande | Förslag | Motivering |
|-----------|---------|-----------|
| `CAPEX` | `CAPEX_2024` | Tydliggör att det är för ett år |
| `Effektivitet` | `efficiency` | Konsekvent engelska i kod |
| `Supereffektivitet` | `super_efficiency` | Konsekvent engelska |
| `potential` | `potential` | OK (redan engelska) |
| `is_outlier` | `is_outlier` | OK |
| `Effkrav_proc` | `effkrav_yearly_pct` | Tydligare enhet |

---

## 7. STAGE-KONTRAKT

### Stage 1: Baseline Loading

```python
@dataclass
class BaselineContract:
    """Kontrakt för baseline-laddning."""
    
    # Outputs
    df_all_companies: pd.DataFrame  # [148 rows]
    # Kolumner: [DMU, REId, Företag, OPEXp, CAPEX, Avskrivning, Avkastning, 
    #            CU, MW, NS, MWhl, MWhh]
    
    dea_baseline: pd.DataFrame  # [148 rows]
    # Kolumner: [DMU, REId, Företag, Effektivitet, Supereffektivitet, 
    #            potential, Effkrav_proc]
    
    capbase_a: pd.DataFrame  # [~510k rows]
    # Kolumner: [id_component, id_network, cat_encode, subcat_encode,
    #            time_from, nuav_2022, ekdep, maxdep, ...]
    
    sdf: pd.DataFrame  # [148+ rows]
    # Kolumner: [REId, Kapitalkostnad, Påverkbara kostnader, 
    #            Opåverkbara kostnader, ...]
    
    reconciliation: pd.DataFrame  # [148 rows]
    # Kolumner: [DMU, REId, id_network, Företag]
```

### Stage 2: Pre-DEA

```python
@dataclass
class PreDeaInputContract:
    """Input-kontrakt för Pre-DEA stage."""
    df_baseline: pd.DataFrame       # [148 rows] från Stage 1
    capbase_a: pd.DataFrame         # [~510k rows] för beräkningar
    config: dict                    # capex_method, wacc_value, etc.

@dataclass
class PreDeaOutputContract:
    """Output-kontrakt från Pre-DEA stage."""
    df_all_companies_modified: pd.DataFrame  # [148 rows]
    # Kolumner: [DMU, REId, Företag, OPEXp, CAPEX, CU, MW, NS, MWhl, MWhh]
    # CAPEX = Kapitalkostnad för år 2024 (tidskod 229+230)
    
    capex_periodsumma: Optional[pd.DataFrame]  # [148 rows × 5 cols] om beräknat
    # Kolumner: [id_network, CAPEX_2024, CAPEX_2025, CAPEX_2026, CAPEX_2027, CAPEX_Period]
    
    metadata: dict
    # {'method': str, 'wacc_used': float, 'modified_companies': int}
```

### Stage 3: DEA

```python
@dataclass
class DeaInputContract:
    """Input-kontrakt för DEA stage."""
    df_pre_dea: pd.DataFrame        # [148 rows] från Stage 2
    dea_baseline: pd.DataFrame      # [148 rows] från Stage 1 (för baseline-metod)
    config: dict                    # dea_method, dea_model_spec, outlier_config

@dataclass
class DeaOutputContract:
    """Output-kontrakt från DEA stage."""
    df_all_companies_efficiency: pd.DataFrame  # [148 rows]
    # Kolumner: [DMU, REId, Företag, efficiency, super_efficiency, 
    #            potential, is_outlier]
    
    metadata: dict
    # {'method': str, 'model_spec': dict, 'n_outliers': int, 
    #  'mean_efficiency': float}
```

### Stage 4: Extraction

```python
@dataclass
class ExtractionInputContract:
    """Input-kontrakt för Extraction stage."""
    df_efficiency: pd.DataFrame     # [148 rows] från Stage 3
    user_dmu: int                   # DMU för inloggat företag

@dataclass
class ExtractionOutputContract:
    """Output-kontrakt från Extraction stage."""
    df_single_company: pd.DataFrame  # [1 row]
    # Samma kolumner som input, filtrerat till user_dmu
    
    metadata: dict
    # {'user_dmu': int, 'reid': str, 'company_name': str}
```

### Stage 5: Post-DEA

```python
@dataclass
class PostDeaInputContract:
    """Input-kontrakt för Post-DEA stage."""
    df_single: pd.DataFrame         # [1 row] från Stage 4
    sdf_data: pd.DataFrame          # SDF-data för inloggat företag
    capex_periodsumma: Optional[pd.DataFrame]  # Om beräknat i Stage 2
    config: dict                    # effkrav_*, paverkbara_method

@dataclass  
class PostDeaOutputContract:
    """Output-kontrakt från Post-DEA stage."""
    intaktsram: dict
    # {
    #   'Kapitalkostnad_Total': float,
    #   'Avskrivningar': float,
    #   'Avkastning': float,
    #   'Påverkbara_Periodsumma': float,
    #   'Opåverkbara_Kostnader': float,
    #   'Flexibilitetstjänster': float,
    #   'Avbrottsersättning': float,
    #   'Avdrag_Statligt_Stöd': float,
    #   'Intäktsram_Total': float,
    #   # Per år breakdown
    #   'CAPEX_2024': float, 'CAPEX_2025': float, ...
    #   'Påverkbara_2024': float, 'Påverkbara_2025': float, ...
    # }
    
    metadata: dict
    # {'effkrav_proc': float, 'paverkbara_method': str, 
    #  'source': str}
```

---

## 8. MIGRATIONSPLAN

### Fas 1: Grundläggande Pipeline (Vecka 1-2)

**Mål:** Fungerande pipeline med baseline-only execution

| Uppgift | Prioritet | Beroenden | Filer att skapa |
|---------|-----------|-----------|-----------------|
| Skapa config/ struktur | Hög | - | `case_definition.py`, `constants.py` |
| Skapa pipeline/ core | Hög | config/ | `core.py`, `stage_dependencies.py` |
| Implementera baseline_loader | Hög | - | `stages/baseline_loader.py` |
| Implementera extraction stage | Medium | baseline | `stages/extraction.py` |
| Implementera post_dea (baseline) | Medium | extraction | `stages/post_dea.py` |
| Integration test | Hög | Alla ovan | `tests/test_pipeline.py` |

**Delmål:** `run_pipeline()` returnerar korrekt intäktsram för baseline-case

### Fas 2: Pre-DEA Stage (Vecka 3-4)

**Mål:** Alla 4 CAPEX-metoder fungerar

| Uppgift | Prioritet | Beroenden | Filer att skapa/ändra |
|---------|-----------|-----------|----------------------|
| WACC-skalning | Hög | Fas 1 | `stages/pre_dea.py` |
| Kent batch processing | Hög | Fas 1 | `stages/kent_batch.py` |
| Parameter-ändringar | Medium | kent_batch | `calculations/parameter_adj.py` |
| KENT-upload integration | Medium | kent_batch | `stages/pre_dea.py` |
| Merge till DEA-input | Hög | Alla ovan | `stages/pre_dea.py` |

**Delmål:** CAPEX kan modifieras med alla 4 metoder och propagerar till DEA

### Fas 3: DEA Stage (Vecka 5)

**Mål:** DEA-beräkning med outlier-hantering

| Uppgift | Prioritet | Beroenden | Filer att skapa/ändra |
|---------|-----------|-----------|----------------------|
| Migrera dea_model.py | Hög | - | `calculations/dea_model.py` |
| DEA stage wrapper | Hög | dea_model | `stages/dea.py` |
| Error handling för infeasible | Medium | dea.py | `error_handling.py` |

**Delmål:** DEA körs korrekt, outliers identifieras, potential beräknas

### Fas 4: Post-DEA Fullständig (Vecka 6)

**Mål:** Komplett intäktsram med alla komponenter

| Uppgift | Prioritet | Beroenden | Filer att skapa/ändra |
|---------|-----------|-----------|----------------------|
| Effektiviseringskrav | Hög | Fas 3 | `calculations/effektiviseringskrav.py` |
| Påverkbara kostnader | Hög | effkrav | `calculations/paverkbara.py` |
| Intäktsram assembly | Hög | Alla | `calculations/intaktsram_assembly.py` |
| OPEX vs TOTEX | Medium | paverkbara | `calculations/paverkbara.py` |

**Delmål:** Komplett intäktsram med breakdown per komponent

### Fas 5: UI Integration (Vecka 7-8)

**Mål:** Streamlit UI fungerar med nya pipelinen

| Uppgift | Prioritet | Beroenden | Filer att skapa |
|---------|-----------|-----------|-----------------|
| UI/config mapping | Hög | config/ | `config/ui_mapping.py` |
| Case setup page | Hög | ui_mapping | `ui/pages/case_setup.py` |
| Configuration tabs | Medium | case_setup | `ui/pages/configuration.py` |
| Results visualization | Medium | Fas 4 | `ui/pages/results.py` |

### Fas 6: Cleanup och Dokumentation (Vecka 9)

| Uppgift | Prioritet |
|---------|-----------|
| Ta bort gamla producers/ | Hög |
| Ta bort gamla core/ (registry, resolver) | Hög |
| Uppdatera README | Medium |
| API-dokumentation | Medium |

---

## 9. KODEXEMPEL

### Exempel 1: Komplett Pipeline Run

```python
# Exempel: Användare ändrar WACC till 5% och kör DEA med ny modellspec

from config.case_definition import CaseDefinition, PreDeaConfig, DeaConfig
from config.case_definition import CapexMethod, EfficiencyMethod
from pipeline.core import run_pipeline
from pipeline.stages.baseline_loader import init_session_baseline
import streamlit as st

# Initiera baseline (körs en gång per session)
init_session_baseline()
baseline = st.session_state.baseline

# Skapa case definition
case = CaseDefinition(
    name="Scenario: Högre WACC + Egen DEA",
    user_dmu=42,
    pre_dea=PreDeaConfig(
        method=CapexMethod.WACC_SCALING,
        wacc_value=0.05  # 5% istället för 4.53%
    ),
    dea=DeaConfig(
        method=EfficiencyMethod.DEA,
        inputs=["CAPEX"],  # Endast CAPEX, inte OPEXp
        outputs=["CU", "NS", "MWh"],  # Aggregerad MWh
        rts="vrs"
    )
)

# Kör pipeline
config = case.to_flat_config()
result = run_pipeline(config, baseline)

# Result innehåller
# {
#   'intaktsram': {...},
#   'metadata': {
#       'stages_executed': ['PRE_DEA', 'DEA', 'EXTRACTION', 'POST_DEA'],
#       ...
#   }
# }
```

### Exempel 2: Stage-isolerad Test

```python
# Test av DEA stage isolerat

import pytest
import pandas as pd
from pipeline.stages.dea import run_dea_stage
from pipeline.core import StageResult

@pytest.fixture
def sample_pre_dea_df():
    """Test-data med 10 företag."""
    return pd.DataFrame({
        'DMU': range(1, 11),
        'REId': [f'REL0000{i}' for i in range(1, 11)],
        'Företag': [f'Företag {i}' for i in range(1, 11)],
        'CAPEX': [100, 120, 80, 150, 90, 110, 130, 85, 140, 95],
        'OPEXp': [50, 60, 40, 75, 45, 55, 65, 42, 70, 48],
        'CU': [1000, 1200, 800, 1500, 900, 1100, 1300, 850, 1400, 950],
        'MW': [10, 12, 8, 15, 9, 11, 13, 8.5, 14, 9.5],
        'NS': [100, 120, 80, 150, 90, 110, 130, 85, 140, 95],
    })

def test_dea_stage_returns_correct_format(sample_pre_dea_df):
    """Verifiera att DEA stage returnerar rätt format."""
    config = {
        'dea_method': 'dea',
        'dea_model_spec': {
            'inputs': ['CAPEX', 'OPEXp'],
            'outputs': ['CU', 'NS'],
            'rts': 'crs'
        },
        'outlier_config': {'q_lower': 25, 'q_upper': 75, 'multiplier': 2.0}
    }
    
    result = run_dea_stage(
        df_pre_dea=sample_pre_dea_df,
        dea_baseline=pd.DataFrame(),  # Inte använd för method='dea'
        config=config
    )
    
    # Verifiera output
    assert isinstance(result, StageResult)
    assert len(result.data) == 10
    assert 'efficiency' in result.data.columns
    assert 'potential' in result.data.columns
    assert 'is_outlier' in result.data.columns
    assert result.data['efficiency'].between(0, 1).all() | result.data['is_outlier']
```

### Exempel 3: Error Handling i UI

```python
# streamlit_app.py - Error handling integration

import streamlit as st
from pipeline.core import run_pipeline
from pipeline.error_handling import PipelineExecutionError

def execute_and_display():
    """Kör pipeline och visa resultat eller fel."""
    
    config = st.session_state.current_case.to_flat_config()
    baseline = st.session_state.baseline
    
    with st.spinner("Kör beräkningar..."):
        try:
            result = run_pipeline(config, baseline)
            st.session_state.last_result = result
            st.success("Beräkning slutförd!")
            
        except PipelineExecutionError as e:
            error = e.error
            
            st.error(f"**Fel i {error.stage}**")
            st.markdown(error.user_message)
            
            if error.suggested_action:
                st.info(f"**Förslag:** {error.suggested_action}")
            
            with st.expander("Tekniska detaljer"):
                st.code(f"Error type: {error.error_type.value}")
                st.code(f"Message: {error.message}")
                if error.technical_details:
                    st.code(error.technical_details)
            
            return False
    
    return True
```

---

## SLUTSATS

Denna arkitektur-omdesign adresserar alla identifierade problem:

1. ✅ **Namnkonflikter lösta** med scope-suffix och tydliga funktionsnamn
2. ✅ **Över-engineering eliminerad** genom funktionell pipeline utan komplex registry
3. ✅ **Batch-processing implementerad** i kent_batch.py med id_network som nyckel
4. ✅ **Baseline-first bekräftad** som optimal strategi utan cache-behov
5. ✅ **Skalbarhet säkrad** genom stage-based design med tydliga kontrakt
6. ✅ **UI-terminologi bevarad** genom mapping layer för Parameters/Variables/Modules

Migrationsplanen är uppdelad i 6 faser över 9 veckor, med tydliga delmål och minimala beroenden mellan uppgifter.

---

**Dokumentslut**

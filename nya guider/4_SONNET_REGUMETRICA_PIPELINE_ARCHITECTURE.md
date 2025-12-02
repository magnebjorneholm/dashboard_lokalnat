# REGUMETRICA PIPELINE ARCHITECTURE - DESIGN SOLUTION

**Version:** 2.0  
**Datum:** 2024-12-01  
**För:** Regumetrica Development Team  
**Syfte:** Komplett arkitekturlösning för pipeline-baserad omdesign

---

## INNEHÅLLSFÖRTECKNING

1. [Executive Summary](#1-executive-summary)
2. [Kärnrekommendationer](#2-kärnrekommendationer)
3. [Svar på Designfrågor](#3-svar-på-designfrågor)
4. [Pipeline-Arkitektur](#4-pipeline-arkitektur)
5. [Stage-Kontrakt](#5-stage-kontrakt)
6. [Config-Struktur](#6-config-struktur)
7. [Dependency Tracking](#7-dependency-tracking)
8. [Namnkonventioner](#8-namnkonventioner)
9. [Filstruktur](#9-filstruktur)
10. [Migrationsplan](#10-migrationsplan)
11. [Kodexempel](#11-kodexempel)

---

## 1. EXECUTIVE SUMMARY

### 1.1 Problemanalys

Nuvarande system är **över-engineerat** för det faktiska behovet:
- ProducerRegistry/VariableResolver hanterar dependency tracking som aldrig behövs
- Systemet är en **linjär pipeline** men implementerat som komplext variabel-resolutionssystem
- Inga cirkulära dependencies existerar i verkligheten
- Namnkonflikter och inkonsekvent scope (148 vs 1 företag)

### 1.2 Rekommenderad Lösning

**Pipeline-arkitektur** med följande principer:
1. **Functional pipeline:** Sekvens av rena funktioner, inga klasser
2. **Format-agnosticism:** Varje stage bryr sig bara om input/output format
3. **Hash-baserad caching:** Automatisk detection av vilka stages som behöver köras om
4. **Baseline-first strategy:** Baseline data laddas en gång, modifieras efter behov
5. **Immutable operations:** Alla transformationer skapar nya DataFrames

### 1.3 Fördelar med Lösningen

| Aspekt | Nuvarande | Ny Lösning |
|--------|-----------|------------|
| **Komplexitet** | Hög (registry, resolver, circular detection) | Låg (functional pipeline) |
| **Förståelse** | Svår (många abstraktioner) | Enkel (läs uppifrån-och-ner) |
| **Testbarhet** | Svår (många dependencies) | Enkel (pure functions) |
| **Underhåll** | Svårt (många filer, abstrakt) | Enkelt (tydlig dataflöde) |
| **Skalbarhet** | Bra (men onödig) | Utmärkt (lätt lägga till stages) |
| **Performance** | God (men cache-logik komplex) | Utmärkt (hash-based caching) |

---

## 2. KÄRNREKOMMENDATIONER

### 2.1 Arkitektur

✅ **ANVÄND:** Functional pipeline med stage-funktioner  
❌ **ANVÄND INTE:** Class-baserad OOP med inheritance

✅ **ANVÄND:** Hash-baserad dependency tracking  
❌ **ANVÄND INTE:** Explicit dependency declarations

✅ **ANVÄND:** Stage-based config structure  
❌ **ANVÄND INTE:** Flat parameters/modules structure

### 2.2 Implementation

✅ **ANVÄND:** Immutable DataFrames (copy-on-modify)  
❌ **ANVÄND INTE:** In-place modifications

✅ **ANVÄND:** Scope-suffix i namn (`_all_companies`, `_single_company`)  
❌ **ANVÄND INTE:** Generiska namn utan scope-info

✅ **ANVÄND:** Batch processing för kent_pipeline med id_network  
❌ **ANVÄND INTE:** Loop över företag för parallella beräkningar

### 2.3 Fil-Organisation

```
pipeline/
├── core/
│   ├── pipeline.py              # Huvudorkestrator
│   ├── cache_manager.py         # Hash-baserad caching
│   └── config_validator.py      # Config validation
├── stages/
│   ├── stage_01_baseline.py     # Baseline loading
│   ├── stage_02_predea.py       # CAPEX modification
│   ├── stage_03_dea.py          # Efficiency calculation
│   ├── stage_04_extraction.py   # Filter till 1 företag
│   └── stage_05_postdea.py      # Intäktsram assembly
├── methods/
│   ├── wacc/
│   │   └── wacc_calculations.py
│   ├── capex/
│   │   ├── kent_batch_pipeline.py  # Batch-refactored kent_pipeline
│   │   ├── parameter_adjustments.py
│   │   └── capbase_prep.py
│   └── efficiency/
│       └── dea_model.py
└── data_loaders/
    ├── baseline_data.py         # Data_modeller, capbase_a, SDF
    └── reconciliation.py        # id_network mappings
```

---

## 3. SVAR PÅ DESIGNFRÅGOR

### FRÅGA A: Dependency Tracking Implementation

**Rekommendation:** Hash-baserad automatic detection

**Motivering:**
1. **Explicit declarations** kräver manuell uppdatering vid ändringar
2. **Hash-based** är automatiskt och mindre felbenäget
3. Ingen risk för glömda dependencies

**Implementation:**

```python
import hashlib
import json
from typing import Dict, Any

def hash_stage_config(stage_name: str, config: Dict[str, Any]) -> str:
    """
    Beräkna hash för stage-specific config.
    
    Exempel för 'predea' stage:
    - method: 'wacc_scaling'
    - wacc: 0.05
    - normvalues: {...}
    - lifetimes: {...}
    """
    stage_config = config.get('stages', {}).get(stage_name, {})
    
    # Sortera nycklar för konsistent hashing
    config_str = json.dumps(stage_config, sort_keys=True)
    
    return hashlib.sha256(config_str.encode()).hexdigest()


def needs_rerun(
    stage_name: str,
    config: Dict[str, Any],
    cache: Dict[str, Any]
) -> bool:
    """
    Avgör om en stage behöver köras om.
    
    Logik:
    1. Beräkna current hash från config
    2. Hämta cached hash
    3. Jämför
    """
    current_hash = hash_stage_config(stage_name, config)
    cached_hash = cache.get(f'{stage_name}_hash')
    
    # Om ingen cached hash, kör alltid
    if cached_hash is None:
        return True
    
    # Kör om hash har ändrats
    return current_hash != cached_hash


def cache_stage_result(
    stage_name: str,
    config: Dict[str, Any],
    result: Any,
    cache: Dict[str, Any]
) -> None:
    """
    Cacha stage resultat med hash.
    """
    result_hash = hash_stage_config(stage_name, config)
    cache[f'{stage_name}_result'] = result
    cache[f'{stage_name}_hash'] = result_hash
```

**Exempel-användning:**

```python
# Scenario 1: Användaren ändrar WACC
config = {
    'stages': {
        'predea': {'method': 'wacc_scaling', 'wacc': 0.06},  # Ändrad från 0.05
        'dea': {'model_spec': {...}},
        'postdea': {...}
    }
}

# Stage dependencies:
# - baseline: Påverkas INTE (ingen config ändrad)
# - predea: Påverkas (wacc ändrad)
# - dea: Påverkas (input från predea ändrad)
# - extraction: Påverkas (input från dea ändrad)
# - postdea: Påverkas (input från extraction ändrad)

# Resultat: baseline cachas, resten körs om
```

### FRÅGA B: Error Handling i Pipeline

**Rekommendation:** Stop-on-error med user-friendly meddelanden

**Motivering:**
1. Undvik partial results (fel-state)
2. Tydliga felmeddelanden för användaren
3. Enkel debugging för utvecklare

**Implementation:**

```python
class PipelineError(Exception):
    """Base exception för pipeline errors."""
    def __init__(self, stage: str, message: str, details: Dict[str, Any] = None):
        self.stage = stage
        self.message = message
        self.details = details or {}
        super().__init__(f"[{stage}] {message}")


class ValidationError(PipelineError):
    """Data validation error."""
    pass


class ConfigurationError(PipelineError):
    """Configuration error."""
    pass


class CalculationError(PipelineError):
    """Calculation error (t.ex. infeasible DEA)."""
    pass


def run_pipeline_with_error_handling(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Kör pipeline med robust error handling.
    """
    try:
        # Stage 1: Baseline
        try:
            baseline = stage_01_baseline(config)
        except Exception as e:
            raise PipelineError(
                stage='baseline',
                message='Kunde inte ladda baseline data',
                details={'error': str(e)}
            )
        
        # Stage 2: Pre-DEA
        try:
            predea = stage_02_predea(baseline, config)
        except ValueError as e:
            raise ConfigurationError(
                stage='predea',
                message='Invalid CAPEX method configuration',
                details={'error': str(e), 'config': config['stages']['predea']}
            )
        
        # Stage 3: DEA
        try:
            dea_result = stage_03_dea(predea, config)
        except Exception as e:
            # Specifik hantering för DEA infeasibility
            if 'infeasible' in str(e).lower():
                raise CalculationError(
                    stage='dea',
                    message='DEA-modellen är infeasible. Kontrollera modellspecifikation.',
                    details={
                        'error': str(e),
                        'model_spec': config['stages']['dea']['model_spec'],
                        'suggestion': 'Försök med färre inputs eller andra outputs'
                    }
                )
            else:
                raise CalculationError(
                    stage='dea',
                    message='DEA-beräkning misslyckades',
                    details={'error': str(e)}
                )
        
        # ... fortsätt för resterande stages
        
        return {'success': True, 'results': {...}}
    
    except PipelineError as e:
        # Pipeline-specifikt fel - visa user-friendly meddelande
        return {
            'success': False,
            'error': {
                'stage': e.stage,
                'message': e.message,
                'details': e.details
            }
        }
    
    except Exception as e:
        # Oväntat fel - visa generiskt meddelande
        return {
            'success': False,
            'error': {
                'stage': 'unknown',
                'message': 'Ett oväntat fel uppstod',
                'details': {'error': str(e)}
            }
        }
```

**UI Integration (Streamlit):**

```python
# I streamlit_app.py
result = run_pipeline_with_error_handling(st.session_state.config)

if not result['success']:
    error = result['error']
    
    # Visa error message med stage context
    st.error(f"**Fel i stage: {error['stage']}**")
    st.error(error['message'])
    
    # Visa details i expander för mer info
    if error['details']:
        with st.expander("Tekniska detaljer"):
            st.json(error['details'])
    
    # Stoppa vidare exekvering
    st.stop()
else:
    # Visa results
    st.success("Pipeline kördes framgångsrikt!")
    display_results(result['results'])
```

### FRÅGA C: Concurrent Users och Baseline Sharing

**Rekommendation:** Ladda baseline per session (ingen delning)

**Motivering:**

| Approach | Fördelar | Nackdelar | Rekommendation |
|----------|----------|-----------|----------------|
| **Global cache (delad)** | Mindre memory | Concurrency risk, complex locking | ❌ Ej lämplig |
| **Per-session (ingen delning)** | Ingen concurrency risk, enkel | Mer memory (~150 MB per session) | ✅ **REKOMMENDERAS** |

**Analys:**
1. **Memory overhead:** 
   - Data_modeller.xlsx: ~50 KB (148 rader × 12 kolumner)
   - capbase_a.parquet: ~50 MB (510k rader × 33 kolumner)
   - SDF: ~100 MB (148 rader × många kolumner för 2024-2027)
   - **Total per session:** ~150 MB
   
2. **Deployment constraints:**
   - Render Standard: 2 GB RAM
   - Max concurrent sessions: ~10 användare
   - **Tillräckligt för användningsfall**

3. **Concurrency:**
   - Streamlit session_state är isolerad per användare
   - Ingen risk för data-corruption
   - Ingen behov av locking-mekanismer

**Implementation:**

```python
# I streamlit_app.py

def initialize_baseline_data():
    """
    Ladda baseline data en gång per session.
    
    Cached i st.session_state för snabb access.
    """
    if 'baseline_data' not in st.session_state:
        st.session_state.baseline_data = {
            'data_modeller': load_data_modeller(),
            'capbase_a': load_capbase_a(),
            'sdf': load_sdf(),
            'reconciliation': load_reconciliation(),
            'eis_dea': load_eis_dea()
        }


# Användning i pipeline
def stage_01_baseline(config: Dict[str, Any]) -> Dict[str, pd.DataFrame]:
    """
    Stage 1: Return baseline data.
    
    Data laddas från st.session_state (already loaded).
    """
    baseline = st.session_state.baseline_data.copy()  # Shallow copy
    
    return {
        'data_modeller_all_companies': baseline['data_modeller'].copy(),  # Deep copy för safety
        'capbase_a_all_companies': baseline['capbase_a'],  # Stor data, ingen copy
        'sdf_all_companies': baseline['sdf'],
        'reconciliation': baseline['reconciliation'],
        'eis_dea_all_companies': baseline['eis_dea']
    }
```

### Architectural Question 1: Pipeline Class Design

**Rekommendation:** Option C - Functional pipeline

**Motivering:**

| Design | Komplexitet | Testbarhet | Läsbarhet | Flexibilitet | Rekommendation |
|--------|-------------|------------|-----------|--------------|----------------|
| A: Monolithic class | Medel | Svår | Medel | Låg | ❌ |
| B: Stage classes | Hög | Medel | Låg | Hög | ❌ |
| C: Functional | **Låg** | **Enkel** | **Hög** | **Hög** | ✅ |

**Kodexempel:**

```python
# pipeline/core/pipeline.py

from typing import Dict, Any
import pandas as pd
from pipeline.stages.stage_01_baseline import stage_01_baseline
from pipeline.stages.stage_02_predea import stage_02_predea
from pipeline.stages.stage_03_dea import stage_03_dea
from pipeline.stages.stage_04_extraction import stage_04_extraction
from pipeline.stages.stage_05_postdea import stage_05_postdea
from pipeline.core.cache_manager import CacheManager


def run_pipeline(
    config: Dict[str, Any],
    user_dmu: int,
    cache: CacheManager = None
) -> Dict[str, Any]:
    """
    Huvudorkestrator för Regumetrica pipeline.
    
    Flow:
    1. Baseline → 2. Pre-DEA → 3. DEA → 4. Extraction → 5. Post-DEA
    
    Args:
        config: Pipeline configuration
        user_dmu: DMU för inloggat företag
        cache: Optional cache manager
    
    Returns:
        Dict med results och metadata
    """
    cache = cache or CacheManager()
    
    # Stage 1: Baseline Loading
    baseline = cache.get_or_compute(
        stage_name='baseline',
        config=config,
        compute_fn=lambda: stage_01_baseline(config)
    )
    
    # Stage 2: Pre-DEA (CAPEX modification)
    predea = cache.get_or_compute(
        stage_name='predea',
        config=config,
        compute_fn=lambda: stage_02_predea(baseline, config)
    )
    
    # Stage 3: DEA (Efficiency calculation)
    dea_result = cache.get_or_compute(
        stage_name='dea',
        config=config,
        compute_fn=lambda: stage_03_dea(predea, config)
    )
    
    # Stage 4: Extraction (Filter till user_dmu)
    company_data = cache.get_or_compute(
        stage_name='extraction',
        config=config,
        compute_fn=lambda: stage_04_extraction(dea_result, user_dmu)
    )
    
    # Stage 5: Post-DEA (Intäktsram assembly)
    intaktsram = stage_05_postdea(company_data, baseline, config)
    
    return {
        'intaktsram': intaktsram,
        'dea_result': dea_result,
        'cache_stats': cache.get_stats()
    }
```

**Fördelar:**
1. **Enkel att förstå:** Läs uppifrån-och-ner, ser hela flödet
2. **Testbar:** Varje stage-funktion kan testas isolerat
3. **Flexibel:** Lätt lägga till nya stages eller ändra ordning
4. **Performance:** Hash-baserad caching för smart execution

### Architectural Question 2: Config Structure

**Rekommendation:** Stage-based config (Option A)

**Motivering:**
1. **Tydlig mappning:** Varje stage har sin egen config
2. **Enkelt att validera:** Kan validera stage-config isolerat
3. **Skalbart:** Lätt lägga till nya stages utan att påverka andra

**Config Structure:**

```python
{
    'case_id': 'case_20241201_001',
    'name': 'Scenario 1: WACC 6%',
    'description': 'Analysera effekten av högre WACC',
    'created_at': '2024-12-01T10:00:00',
    'updated_at': '2024-12-01T10:30:00',
    
    # Stage configurations
    'stages': {
        
        # Stage 1: Baseline (ingen config behövs, data laddas automatiskt)
        'baseline': {},
        
        # Stage 2: Pre-DEA
        'predea': {
            'method': 'wacc_scaling',  # Eller: 'baseline', 'parameter_adjustments', 'kent_upload'
            
            # Method-specific config
            'wacc_scaling': {
                'new_wacc': 0.06,
                'baseline_wacc': 0.0488
            },
            
            # Alternativt för 'parameter_adjustments'
            'parameter_adjustments': {
                'normvalues': {
                    'category_1': {'multiplier': 1.1},  # 10% ökning
                    'category_5': {'multiplier': 0.9}   # 10% minskning
                },
                'lifetimes': {
                    'category_1': {'ekdep_multiplier': 1.2, 'maxdep_multiplier': 1.2}
                },
                'wacc': 0.06  # Kombineras med parameter-ändringar
            },
            
            # Alternativt för 'kent_upload'
            'kent_upload': {
                'kent_file_path': '/path/to/kent.xlsx',
                'wacc': 0.06,
                'normvalues': {...},  # Optional
                'lifetimes': {...}    # Optional
            }
        },
        
        # Stage 3: DEA
        'dea': {
            'method': 'dea',  # Eller: 'sfa', 'stoned' (framtida)
            'model_spec': {
                'inputs': ['CAPEX', 'OPEXp'],
                'outputs': ['CU', 'NS', 'MW'],
                'rts': 'VRS',
                'orientation': 'input'
            },
            'outlier_detection': {
                'method': 'iqr',
                'iqr_multiplier': 2.0
            }
        },
        
        # Stage 4: Extraction (ingen config behövs, user_dmu från session)
        'extraction': {},
        
        # Stage 5: Post-DEA
        'postdea': {
            'effkrav_config': {
                'truncation': 0.30,
                'outlier_fixed_rate': 0.01,
                'method': 'OPEX'  # Eller 'TOTEX'
            },
            'components': {
                'include_flex': True,
                'include_avbrott': True,
                'include_quality': False
            }
        }
    }
}
```

**Mappning UI → Config:**

| UI Terminologi | Config Location | Typ | Exempel |
|----------------|-----------------|-----|---------|
| **Parameters** (uniform för alla 148) | `config['stages']['predea']['wacc']` | Uniform | WACC, normvärden, livslängder |
| **Variables** (specifikt för 1 företag) | `config['stages']['predea']['kent_upload']` | Company-specific | KENT-fil |
| **Modules** (val av metod) | `config['stages']['dea']['method']` | Method selection | DEA vs SFA |

### Architectural Question 3: Dependency Tracking

**Rekommendation:** Hash-based automatic detection (redan besvarat i FRÅGA A)

**Komplettering - Stage Dependencies:**

```python
# Pipeline dependency graph (implicit, ej explicit declarations)

STAGE_FLOW = [
    'baseline',      # Stage 1: Inga dependencies
    'predea',        # Stage 2: Depends on 'baseline'
    'dea',           # Stage 3: Depends on 'predea'
    'extraction',    # Stage 4: Depends on 'dea'
    'postdea'        # Stage 5: Depends on 'extraction' + 'baseline'
]

def get_stages_to_rerun(config: Dict[str, Any], cache: CacheManager) -> list:
    """
    Avgör vilka stages som behöver köras om.
    
    Logik:
    1. Iterera genom STAGE_FLOW
    2. För varje stage, kolla om config ändrats (hash)
    3. Om stage ändrats, kör om stage + alla efterföljande
    4. Om stage INTE ändrats, använd cached result
    """
    stages_to_run = []
    invalidate_rest = False
    
    for stage_name in STAGE_FLOW:
        # Om tidigare stage kördes om, kör om denna också
        if invalidate_rest:
            stages_to_run.append(stage_name)
            continue
        
        # Kolla om config ändrats för denna stage
        if cache.needs_rerun(stage_name, config):
            stages_to_run.append(stage_name)
            invalidate_rest = True  # Alla efterföljande stages måste också köras om
        
    return stages_to_run


# Exempel-användning:
config_v1 = {'stages': {'predea': {'method': 'baseline'}, 'dea': {...}}}
config_v2 = {'stages': {'predea': {'method': 'wacc_scaling', 'wacc': 0.06}, 'dea': {...}}}

# Första körningen: Alla stages
stages = get_stages_to_rerun(config_v1, cache)
# → ['baseline', 'predea', 'dea', 'extraction', 'postdea']

# Andra körningen (ändrat predea): predea + efterföljande
stages = get_stages_to_rerun(config_v2, cache)
# → ['predea', 'dea', 'extraction', 'postdea']  (baseline cachas)

# Tredje körningen (ingen ändring): Inga stages
stages = get_stages_to_rerun(config_v2, cache)
# → []  (allt cachas)
```

### Architectural Question 4: Batch Processing för Kent Pipeline

**Rekommendation:** Unified batch implementation

**Motivering:**
1. **Undvik kodduplicering:** En implementation för både single och batch
2. **Performance:** Vectorized operations där möjligt
3. **Maintainability:** Enklare att underhålla en funktion

**Implementation Strategy:**

```python
# pipeline/methods/capex/kent_batch_pipeline.py

import pandas as pd
from typing import Dict, Any

def run_kent_pipeline_batch(
    capbase_all_companies: pd.DataFrame,
    wacc: float,
    normvalue_adjustments: Dict[int, float] = None,
    lifetime_adjustments: Dict[int, Dict[str, float]] = None
) -> pd.DataFrame:
    """
    Kör kent_pipeline för ALLA 148 företag samtidigt.
    
    Batch-processing med id_network som key.
    
    Args:
        capbase_all_companies: capbase_a för alla företag (~510k rader)
        wacc: WACC att använda för avkastningsberäkning
        normvalue_adjustments: Dict med cat_encode -> multiplier
        lifetime_adjustments: Dict med cat_encode -> {'ekdep_multiplier': ..., 'maxdep_multiplier': ...}
    
    Returns:
        DataFrame med kapitalkostnader per id_network och år
        
        Kolumner:
        - id_network
        - år (2024, 2025, 2026, 2027)
        - Avskrivning
        - Avkastning
        - CAPEX (Avskrivning + Avkastning)
    """
    df = capbase_all_companies.copy()
    
    # Steg 0: Applicera justeringar (om angivna)
    if normvalue_adjustments:
        df = apply_normvalue_adjustments_batch(df, normvalue_adjustments)
    
    if lifetime_adjustments:
        df = apply_lifetime_adjustments_batch(df, lifetime_adjustments)
    
    # Steg 5: Beräkna åldrar och NUAV för alla tidskoder (vectorized)
    time_codes = [229, 230, 231, 232, 233, 234, 235, 236]  # 2024h1-2027h2
    
    for time_code in time_codes:
        df[f'age_component_{time_code}'] = time_code - df['time_from']
        df[f'nuav_ord_{time_code}'] = calculate_nuav_ord_vectorized(df, time_code)
        df[f'nuav_tail_{time_code}'] = calculate_nuav_tail_vectorized(df, time_code)
    
    # Steg 6: Beräkna avskrivningar (vectorized)
    for time_code in time_codes:
        df[f'dep_ord_{time_code}'] = calculate_depreciation_ord_vectorized(df, time_code)
        df[f'dep_tail_{time_code}'] = calculate_depreciation_tail_vectorized(df, time_code)
    
    # Steg 7: Beräkna avkastning (vectorized)
    for time_code in time_codes:
        df[f'return_ord_{time_code}'] = df[f'nuav_ord_{time_code}'] * wacc / 2
        df[f'return_tail_{time_code}'] = df[f'nuav_tail_{time_code}'] * wacc / 2
    
    # Steg 8: Aggregera per id_network och år
    results = []
    
    for year, codes in [(2024, [229, 230]), (2025, [231, 232]), 
                        (2026, [233, 234]), (2027, [235, 236])]:
        
        # Summera över båda halvåren
        year_data = df.groupby('id_network').agg({
            **{f'dep_ord_{c}': 'sum' for c in codes},
            **{f'dep_tail_{c}': 'sum' for c in codes},
            **{f'return_ord_{c}': 'sum' for c in codes},
            **{f'return_tail_{c}': 'sum' for c in codes}
        })
        
        # Beräkna totaler
        year_data['Avskrivning'] = sum(
            year_data[f'dep_ord_{c}'] + year_data[f'dep_tail_{c}'] 
            for c in codes
        )
        year_data['Avkastning'] = sum(
            year_data[f'return_ord_{c}'] + year_data[f'return_tail_{c}']
            for c in codes
        )
        year_data['CAPEX'] = year_data['Avskrivning'] + year_data['Avkastning']
        year_data['år'] = year
        
        results.append(year_data[['år', 'Avskrivning', 'Avkastning', 'CAPEX']])
    
    # Kombinera alla år
    result_df = pd.concat(results).reset_index()
    
    return result_df


def extract_capex_2024_for_dea(kent_result: pd.DataFrame) -> pd.DataFrame:
    """
    Extrahera CAPEX för år 2024 att använda i DEA.
    
    Args:
        kent_result: Output från run_kent_pipeline_batch
    
    Returns:
        DataFrame med kolumner [id_network, CAPEX]
    """
    capex_2024 = kent_result[kent_result['år'] == 2024].copy()
    return capex_2024[['id_network', 'CAPEX']]


def aggregate_period_sum(kent_result: pd.DataFrame) -> pd.DataFrame:
    """
    Beräkna periodsumma (2024-2027) för intäktsram.
    
    Args:
        kent_result: Output från run_kent_pipeline_batch
    
    Returns:
        DataFrame med kolumner [id_network, Kapitalkostnad_Total, Avskrivning_Total, Avkastning_Total]
    """
    period_sum = kent_result.groupby('id_network').agg({
        'Avskrivning': 'sum',
        'Avkastning': 'sum',
        'CAPEX': 'sum'
    }).rename(columns={
        'CAPEX': 'Kapitalkostnad_Total',
        'Avskrivning': 'Avskrivning_Total',
        'Avkastning': 'Avkastning_Total'
    })
    
    return period_sum.reset_index()
```

**Integration med Pre-DEA Stage:**

```python
# pipeline/stages/stage_02_predea.py

def stage_02_predea(
    baseline: Dict[str, pd.DataFrame],
    config: Dict[str, Any]
) -> Dict[str, pd.DataFrame]:
    """
    Stage 2: Pre-DEA CAPEX modification.
    
    Returnerar DataFrame med 148 rader för DEA.
    """
    predea_config = config['stages']['predea']
    method = predea_config['method']
    
    # Start med baseline data
    df = baseline['data_modeller_all_companies'].copy()
    
    if method == 'baseline':
        # Ingen ändring
        pass
    
    elif method == 'wacc_scaling':
        # Skala endast Avkastning
        wacc_config = predea_config['wacc_scaling']
        new_wacc = wacc_config['new_wacc']
        baseline_wacc = wacc_config['baseline_wacc']
        scaling_factor = new_wacc / baseline_wacc
        
        df['Avkastning'] = df['Avkastning'] * scaling_factor
        df['CAPEX'] = df['Avskrivning'] + df['Avkastning']
    
    elif method == 'parameter_adjustments':
        # Kör batch kent pipeline för ALLA företag
        param_config = predea_config['parameter_adjustments']
        
        kent_result = run_kent_pipeline_batch(
            capbase_all_companies=baseline['capbase_a_all_companies'],
            wacc=param_config['wacc'],
            normvalue_adjustments=param_config.get('normvalues'),
            lifetime_adjustments=param_config.get('lifetimes')
        )
        
        # Extrahera CAPEX för 2024
        capex_2024 = extract_capex_2024_for_dea(kent_result)
        
        # Merge med data_modeller (behåll OPEXp, volymer)
        df = df.merge(
            capex_2024[['id_network', 'CAPEX']],
            left_on='REId',  # Behöver mapping via reconciliation
            right_on='id_network',
            how='left',
            suffixes=('_old', '')
        )
        
        # Spara periodsumma för senare användning i Post-DEA
        period_sum = aggregate_period_sum(kent_result)
        df.attrs['period_sum'] = period_sum  # Metadata
    
    elif method == 'kent_upload':
        # Läs KENT-fil för 1 företag → Steg 1-4 → Steg 5-8
        kent_config = predea_config['kent_upload']
        
        # Steg 1-4: Bygg capbase för inloggat företag
        capbase_user = process_kent_file(kent_config['kent_file_path'])
        
        # Kör batch pipeline: 147 från baseline + 1 från KENT
        capbase_combined = combine_capbase(
            baseline['capbase_a_all_companies'],
            capbase_user,
            user_id_network=kent_config['user_id_network']
        )
        
        kent_result = run_kent_pipeline_batch(
            capbase_all_companies=capbase_combined,
            wacc=kent_config['wacc'],
            normvalue_adjustments=kent_config.get('normvalues'),
            lifetime_adjustments=kent_config.get('lifetimes')
        )
        
        # ... samma som parameter_adjustments
    
    return {
        'data_all_companies': df,
        'metadata': {
            'method': method,
            'capex_source': 'baseline' if method == 'baseline' else 'calculated'
        }
    }
```

---

## 4. PIPELINE-ARKITEKTUR

### 4.1 Översikt

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         REGUMETRICA PIPELINE                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  INPUT: config (stage-based), user_dmu                                      │
│                                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                    │
│  │   STAGE 1   │ →  │   STAGE 2   │ →  │   STAGE 3   │                    │
│  │  BASELINE   │    │   PRE-DEA   │    │     DEA     │                    │
│  │  LOADING    │    │   CAPEX     │    │  ANALYSIS   │                    │
│  └─────────────┘    └─────────────┘    └─────────────┘                    │
│        │                  │                  │                              │
│        ↓                  ↓                  ↓                              │
│  148 companies      148 modified       148 efficiency                       │
│   baseline data      CAPEX data           results                           │
│                                                                             │
│                                            │                                │
│                                            ↓                                │
│                       ┌─────────────┐    ┌─────────────┐                  │
│                       │   STAGE 5   │ ←  │   STAGE 4   │                  │
│                       │  POST-DEA   │    │ EXTRACTION  │                  │
│                       │  INTÄKTSRAM │    │ (1 company) │                  │
│                       └─────────────┘    └─────────────┘                  │
│                             │                  │                            │
│                             ↓                  ↓                            │
│                       Intäktsram          Company data                      │
│                       breakdown           + efficiency                      │
│                                                                             │
│  OUTPUT: intaktsram_dict, dea_results, metadata                            │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

SMART EXECUTION (hash-based caching):
- Stage ändrad → Kör om stage + alla efterföljande
- Stage oförändrad → Använd cached result
```

### 4.2 Dataflöde

```
DATA_MODELLER.XLSX (148 rows)
        ↓
    BASELINE LOADING
        ↓
┌───────────────────────────────┐
│  df_data_all_companies        │  148 rows
│  Kolumner: DMU, REId, CAPEX,  │
│  OPEXp, CU, MW, NS, MWh       │
└───────────────────────────────┘
        ↓
    PRE-DEA (4 methods)
        ↓
┌───────────────────────────────┐
│  df_data_all_companies        │  148 rows
│  CAPEX modified (wacc/params) │
└───────────────────────────────┘
        ↓
    DEA ANALYSIS
        ↓
┌───────────────────────────────┐
│  df_dea_all_companies         │  148 rows
│  + efficiency, potential      │
└───────────────────────────────┘
        ↓
    EXTRACTION (filter by DMU)
        ↓
┌───────────────────────────────┐
│  df_company                   │  1 row
│  Data för user_dmu            │
└───────────────────────────────┘
        ↓
    POST-DEA
        ↓
┌───────────────────────────────┐
│  intaktsram_dict              │
│  Alla komponenter summerade   │
└───────────────────────────────┘
```

---

## 5. STAGE-KONTRAKT

### Stage 1: Baseline Loading

**Input:**
```python
config: Dict[str, Any]  # Pipeline configuration (ingen stage-specific config)
```

**Output:**
```python
{
    'data_modeller_all_companies': pd.DataFrame,  # 148 rows × 12 cols
    'capbase_a_all_companies': pd.DataFrame,      # ~510k rows × 33 cols
    'sdf_all_companies': pd.DataFrame,            # 148 rows × 36 cols
    'reconciliation': pd.DataFrame,               # 148 rows × 3 cols
    'eis_dea_all_companies': pd.DataFrame         # 148 rows × 7 cols
}
```

**DataFrame Contracts:**

**`data_modeller_all_companies`:**
| Kolumn | Typ | Beskrivning | Constraints |
|--------|-----|-------------|-------------|
| DMU | int | Decision Making Unit (1-148) | Primary key |
| REId | str | Nätverks-ID (REL00001, ...) | Unique |
| Företag | str | Företagsnamn | Not null |
| OPEXp | float | Påverkbara OPEX (tkr) | ≥ 0 |
| CAPEX | float | Kapitalkostnad 2024 (tkr) | ≥ 0 |
| Avskrivning | float | Avskrivningar 2024 (tkr) | ≥ 0 |
| Avkastning | float | Avkastning 2024 (tkr) | ≥ 0 |
| CU | float | Antal kunder | > 0 |
| MW | float | Installerad effekt (MW) | ≥ 0 |
| NS | float | Nätlängd (km) | > 0 |
| MWhl | float | Överförd energi låglast (MWh) | ≥ 0 |
| MWhh | float | Överförd energi höglast (MWh) | ≥ 0 |

**Invariant:** `CAPEX == Avskrivning + Avkastning` (inom 0.01 tkr precision)

### Stage 2: Pre-DEA

**Input:**
```python
baseline: Dict[str, pd.DataFrame]  # Output från Stage 1
config: Dict[str, Any]            # config['stages']['predea']
```

**Output:**
```python
{
    'data_all_companies': pd.DataFrame,  # 148 rows med modifierad CAPEX
    'metadata': {
        'method': str,           # 'baseline', 'wacc_scaling', 'parameter_adjustments', 'kent_upload'
        'capex_source': str,     # 'baseline' eller 'calculated'
        'period_sum': pd.DataFrame  # Optional: Kapitalkostnad 2024-2027 per id_network
    }
}
```

**DataFrame Contract för `data_all_companies`:**
- Samma struktur som `data_modeller_all_companies` från Stage 1
- CAPEX kan vara modifierad beroende på method
- Om method != 'baseline': metadata['period_sum'] måste finnas

### Stage 3: DEA

**Input:**
```python
predea: Dict[str, pd.DataFrame]  # Output från Stage 2
config: Dict[str, Any]          # config['stages']['dea']
```

**Output:**
```python
{
    'dea_all_companies': pd.DataFrame,  # 148 rows
    'metadata': {
        'model_spec': dict,
        'outliers': list,  # Lista med DMU för outliers
        'stats': dict      # DEA-statistik
    }
}
```

**DataFrame Contract för `dea_all_companies`:**
| Kolumn | Typ | Beskrivning | Constraints |
|--------|-----|-------------|-------------|
| DMU | int | Decision Making Unit | Primary key |
| REId | str | Nätverks-ID | Unique |
| Företag | str | Företagsnamn | Not null |
| efficiency | float | Teknisk effektivitet | 0 < efficiency ≤ 1 |
| super_efficiency | float | Super-efficiency score | > 0 |
| potential | float | Effektiviseringspotential | 0 ≤ potential ≤ 1 |
| is_outlier | bool | Outlier-flagga | True/False |

### Stage 4: Extraction

**Input:**
```python
dea_result: Dict[str, pd.DataFrame]  # Output från Stage 3
user_dmu: int                        # DMU för inloggat företag
```

**Output:**
```python
{
    'company_data': pd.DataFrame,  # 1 row
    'metadata': {
        'dmu': int,
        'reid': str,
        'company_name': str
    }
}
```

**DataFrame Contract för `company_data`:**
- Samma kolumner som `dea_all_companies` från Stage 3
- Endast 1 rad (user_dmu)

### Stage 5: Post-DEA

**Input:**
```python
company_data: Dict[str, pd.DataFrame]  # Output från Stage 4
baseline: Dict[str, pd.DataFrame]      # Output från Stage 1
config: Dict[str, Any]                # config['stages']['postdea']
```

**Output:**
```python
{
    'intaktsram': pd.DataFrame,  # 1 row med intäktsram breakdown
    'paverkbara': pd.DataFrame,  # 4 rows (2024-2027)
    'metadata': {
        'effkrav_proc': float,
        'method': str,  # 'OPEX' eller 'TOTEX'
        'components': dict
    }
}
```

**DataFrame Contract för `intaktsram`:**
| Kolumn | Typ | Beskrivning | Enhet |
|--------|-----|-------------|-------|
| DMU | int | Decision Making Unit | - |
| Intaktsram_Total | float | Total intäktsram 2024-2027 | tkr |
| Kapitalkostnad_Total | float | Kapitalkostnader | tkr |
| Paverkbara_Total | float | Påverkbara efter avdrag | tkr |
| Opaverkbara_Total | float | Opåverkbara kostnader | tkr |
| Flexibilitet | float | Flexibilitetstjänster | tkr |
| Avbrott | float | Avbrottsersättning | tkr |
| Avdrag | float | Avdrag statligt stöd | tkr |
| Kvalitet | float | Kvalitetsjustering (optional) | tkr |

---

## 6. CONFIG-STRUKTUR

Se **Architectural Question 2** för fullständig config structure.

**Sammanfattning:**
- **Stage-based:** `config['stages'][stage_name]`
- **Method selection:** `config['stages'][stage_name]['method']`
- **Method config:** `config['stages'][stage_name][method_name]`

---

## 7. DEPENDENCY TRACKING

Se **FRÅGA A** och **Architectural Question 3** för fullständig implementation.

**Sammanfattning:**
- **Hash-based automatic detection**
- **Linear dependency flow:** baseline → predea → dea → extraction → postdea
- **Smart execution:** Kör endast stages som påverkats

---

## 8. NAMNKONVENTIONER

### 8.1 DataFrame Naming

**Scope-suffix:**
- `_all_companies`: DataFrame med 148 rader (alla företag)
- `_single_company`: DataFrame med 1 rad (inloggat företag)
- `_batch`: Används för batch-processing (148 företag)

**Exempel:**
```python
data_modeller_all_companies   # 148 rows
dea_all_companies             # 148 rows
company_data                  # 1 row (implicit single)
```

### 8.2 Variable Naming

**CAPEX-relaterade:**
- `capex_2024`: CAPEX för år 2024 (för DEA)
- `capex_period`: CAPEX för hela perioden 2024-2027 (för intäktsram)
- `avskrivning_2024`: Avskrivningar för år 2024
- `avkastning_2024`: Avkastning för år 2024

**WACC-relaterade:**
- `wacc_value`: Float med WACC-värde (t.ex. 0.0488)
- `wacc_scaling_factor`: Float med skalningsfaktor (new_wacc / baseline_wacc)
- `baseline_wacc`: WACC från Data_modeller

**Efficiency-relaterade:**
- `efficiency`: Teknisk effektivitet (0-1)
- `super_efficiency`: Super-efficiency score (>0)
- `potential`: Effektiviseringspotential (0-1)
- `effkrav_proc`: Årligt effektiviseringskrav (procent)

### 8.3 Function Naming

**Stage functions:**
- `stage_01_baseline()`: Stage 1
- `stage_02_predea()`: Stage 2
- etc.

**Method functions:**
- `run_kent_pipeline_batch()`: Batch processing
- `apply_wacc_scaling()`: Method implementation
- `calculate_effkrav_from_potential()`: Calculation

**Helper functions:**
- `extract_capex_2024_for_dea()`: Specifik extraction
- `aggregate_period_sum()`: Aggregering
- `validate_stage_output()`: Validation

### 8.4 Config Keys

**Konsekvent naming:**
- `method`: Val av metod (inte `module`)
- `model_spec`: Modellspecifikation (inte `config`)
- `wacc`: WACC-värde (inte `interest_rate`)

---

## 9. FILSTRUKTUR

```
regumetrica/
├── pipeline/
│   ├── __init__.py
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── pipeline.py              # Huvudorkestrator: run_pipeline()
│   │   ├── cache_manager.py         # CacheManager för hash-baserad caching
│   │   └── config_validator.py      # Validera config structure
│   │
│   ├── stages/
│   │   ├── __init__.py
│   │   ├── stage_01_baseline.py     # Stage 1: Baseline loading
│   │   ├── stage_02_predea.py       # Stage 2: Pre-DEA CAPEX modification
│   │   ├── stage_03_dea.py          # Stage 3: DEA efficiency calculation
│   │   ├── stage_04_extraction.py   # Stage 4: Extraction till 1 företag
│   │   └── stage_05_postdea.py      # Stage 5: Post-DEA intäktsram
│   │
│   ├── methods/
│   │   ├── __init__.py
│   │   │
│   │   ├── wacc/
│   │   │   ├── __init__.py
│   │   │   └── wacc_calculations.py # WACC från CAPM
│   │   │
│   │   ├── capex/
│   │   │   ├── __init__.py
│   │   │   ├── kent_batch_pipeline.py     # Batch-refactored kent_pipeline
│   │   │   ├── parameter_adjustments.py   # Normvärde/livslängd
│   │   │   ├── capbase_prep.py            # KENT-fil processing (steg 1-4)
│   │   │   └── wacc_scaling.py            # WACC-skalning method
│   │   │
│   │   ├── efficiency/
│   │   │   ├── __init__.py
│   │   │   ├── dea_model.py               # DEA implementation (PuLP)
│   │   │   └── outlier_detection.py       # IQR-based outlier detection
│   │   │
│   │   └── intaktsram/
│   │       ├── __init__.py
│   │       ├── effektiviseringskrav.py    # Effkrav-beräkningar
│   │       ├── paverkbara.py              # Påverkbara kostnader
│   │       └── intaktsram_assembly.py     # Summera intäktsram
│   │
│   └── data_loaders/
│       ├── __init__.py
│       ├── baseline_data.py        # Ladda Data_modeller, capbase_a, SDF
│       └── reconciliation.py       # id_network ↔ DMU mappings
│
├── ui/
│   ├── __init__.py
│   ├── streamlit_app.py            # Huvudfil med navigation
│   ├── pages/
│   │   ├── 01_case_setup.py
│   │   ├── 02_case_configuration.py
│   │   ├── 03_execution.py
│   │   └── 04_results.py
│   └── components/
│       ├── __init__.py
│       ├── case_selector.py
│       ├── config_editor.py
│       └── results_display.py
│
├── auth/
│   ├── __init__.py
│   └── firebase_auth.py
│
├── tests/
│   ├── __init__.py
│   ├── test_pipeline.py
│   ├── test_stages.py
│   └── test_methods.py
│
├── data/
│   ├── Data_modeller.xlsx
│   ├── capbase_a.parquet
│   ├── SDF.xlsx
│   └── reconciliation.csv
│
├── requirements.txt
└── README.md
```

---

## 10. MIGRATIONSPLAN

### Fas 1: Core Pipeline Infrastructure (Vecka 1)

**Mål:** Skapa grundläggande pipeline-struktur utan metod-implementation

**Tasks:**
1. ✅ Skapa `pipeline/core/pipeline.py` med `run_pipeline()`
2. ✅ Skapa `pipeline/core/cache_manager.py` med hash-baserad caching
3. ✅ Skapa `pipeline/core/config_validator.py`
4. ✅ Skapa tomma stage-filer i `pipeline/stages/`
5. ✅ Skapa `pipeline/data_loaders/baseline_data.py` för datainläsning

**Deliverables:**
- Körbar pipeline-struktur (tom implementation)
- Unit tests för cache_manager
- Config validation

**Kod att återanvända:**
- `core/data_loader_base.py` → `pipeline/data_loaders/baseline_data.py`

### Fas 2: Stage 1-2 Implementation (Vecka 2)

**Mål:** Implementera Baseline Loading + Pre-DEA med alla CAPEX-metoder

**Tasks:**
1. ✅ Implementera `stage_01_baseline()`
   - Ladda Data_modeller
   - Ladda capbase_a
   - Ladda SDF
   - Ladda reconciliation
   - Ladda EIs_DEA
2. ✅ Implementera `stage_02_predea()` med methods:
   - Baseline (ingen ändring)
   - WACC-scaling
   - Parameter adjustments
   - KENT upload
3. ✅ Refactorize `kent_pipeline.py` → `kent_batch_pipeline.py`
   - Batch processing för alla 148 företag
   - Vectorized operations

**Deliverables:**
- Fungerande Pre-DEA stage med alla metoder
- Unit tests för varje method
- Integration tests för Stage 1-2

**Kod att återanvända:**
- `producers/baseline/baseline_loaders.py` → `stage_01_baseline()`
- `producers/wacc/wacc_producers.py` → `methods/wacc/wacc_calculations.py`
- `producers/kapitalkostnad/kent_pipeline.py` → `methods/capex/kent_batch_pipeline.py` (refactored)
- `producers/kapitalkostnad/parameter_adjustments.py` → `methods/capex/parameter_adjustments.py`
- `producers/kapitalkostnad/capbase_prep.py` → `methods/capex/capbase_prep.py`

### Fas 3: Stage 3 Implementation (Vecka 3)

**Mål:** Implementera DEA-analys

**Tasks:**
1. ✅ Implementera `stage_03_dea()`
   - DEA med PuLP
   - Outlier detection (IQR)
   - Super-efficiency
2. ✅ Återanvänd DEA-kod från nuvarande system
3. ✅ Integration med Pre-DEA output

**Deliverables:**
- Fungerande DEA stage
- Unit tests för DEA-model
- Integration tests för Stage 1-3

**Kod att återanvända:**
- `producers/effektivitet/dea_model.py` → `methods/efficiency/dea_model.py`
- `producers/effektivitet/dea_producer.py` → `stage_03_dea()`

### Fas 4: Stage 4-5 Implementation (Vecka 4)

**Mål:** Implementera Extraction + Post-DEA (Intäktsram)

**Tasks:**
1. ✅ Implementera `stage_04_extraction()`
   - Filtrera till user_dmu
2. ✅ Implementera `stage_05_postdea()`
   - Effektiviseringskrav
   - Påverkbara kostnader
   - Intäktsram assembly
3. ✅ Integration med SDF baseline data

**Deliverables:**
- Fullständig pipeline (alla 5 stages)
- End-to-end tests
- Excel-validation (jämför med facit)

**Kod att återanvända:**
- `effektiviseringskrav.py` → `methods/intaktsram/effektiviseringskrav.py`
- `effektiviseringskrav_calculations.py` → `methods/intaktsram/effektiviseringskrav.py`
- `intaktsram_dekomposition.py` → `methods/intaktsram/intaktsram_assembly.py`

### Fas 5: UI Integration (Vecka 5)

**Mål:** Integrera nya pipeline-arkitekturen med Streamlit UI

**Tasks:**
1. ✅ Uppdatera `streamlit_app.py`
   - Byt från VariableResolver till run_pipeline()
   - Behåll befintlig UI-struktur (case setup → config → execution → results)
2. ✅ Uppdatera case_configuration.py
   - Stage-based config editor
   - Method selection per stage
3. ✅ Uppdatera execution.py
   - Visa pipeline progress
   - Cache stats
   - Error handling
4. ✅ Uppdatera results.py
   - Visualisera intäktsram
   - DEA-resultat
   - Export till Excel

**Deliverables:**
- Fungerande UI med nya backend
- User acceptance testing
- Documentation

### Fas 6: Testing & Validation (Vecka 6)

**Mål:** Omfattande testning mot Excel-facit

**Tasks:**
1. ✅ Excel-validation för alla scenarios
2. ✅ Performance testing
3. ✅ Edge case testing
4. ✅ User acceptance testing
5. ✅ Documentation

**Deliverables:**
- Test report
- Validated system
- Deployment-ready code

---

## 11. KODEXEMPEL

### 11.1 Huvudorkestrator

```python
# pipeline/core/pipeline.py

from typing import Dict, Any
import streamlit as st
from pipeline.stages.stage_01_baseline import stage_01_baseline
from pipeline.stages.stage_02_predea import stage_02_predea
from pipeline.stages.stage_03_dea import stage_03_dea
from pipeline.stages.stage_04_extraction import stage_04_extraction
from pipeline.stages.stage_05_postdea import stage_05_postdea
from pipeline.core.cache_manager import CacheManager


def run_pipeline(
    config: Dict[str, Any],
    user_dmu: int,
    cache: CacheManager = None
) -> Dict[str, Any]:
    """
    Kör Regumetrica pipeline med smart caching.
    
    Args:
        config: Pipeline configuration (stage-based)
        user_dmu: DMU för inloggat företag
        cache: Optional cache manager (default: använd session_state cache)
    
    Returns:
        Dict med:
        - intaktsram: DataFrame med intäktsram breakdown
        - paverkbara: DataFrame med påverkbara per år
        - dea_result: DataFrame med efficiency för alla 148
        - metadata: Pipeline metadata
    """
    # Använd session_state cache om ingen cache angiven
    if cache is None:
        if 'pipeline_cache' not in st.session_state:
            st.session_state.pipeline_cache = CacheManager()
        cache = st.session_state.pipeline_cache
    
    # Stage 1: Baseline Loading
    baseline = cache.get_or_compute(
        stage_name='baseline',
        config=config,
        compute_fn=lambda: stage_01_baseline(config)
    )
    
    # Stage 2: Pre-DEA
    predea = cache.get_or_compute(
        stage_name='predea',
        config=config,
        compute_fn=lambda: stage_02_predea(baseline, config)
    )
    
    # Stage 3: DEA
    dea_result = cache.get_or_compute(
        stage_name='dea',
        config=config,
        compute_fn=lambda: stage_03_dea(predea, config)
    )
    
    # Stage 4: Extraction (alltid kör om, user_dmu kan ändras)
    company_data = stage_04_extraction(dea_result, user_dmu)
    
    # Stage 5: Post-DEA (alltid kör om, beror på extraction)
    intaktsram_result = stage_05_postdea(company_data, baseline, predea, config)
    
    return {
        'intaktsram': intaktsram_result['intaktsram'],
        'paverkbara': intaktsram_result['paverkbara'],
        'dea_result': dea_result['dea_all_companies'],
        'metadata': {
            'cache_stats': cache.get_stats(),
            'stages_computed': cache.get_computed_stages()
        }
    }
```

### 11.2 Cache Manager

```python
# pipeline/core/cache_manager.py

import hashlib
import json
from typing import Dict, Any, Callable


class CacheManager:
    """
    Hash-baserad cache manager för pipeline stages.
    """
    
    def __init__(self):
        self.cache: Dict[str, Any] = {}
        self.hashes: Dict[str, str] = {}
        self.computed_stages: list = []
    
    def get_or_compute(
        self,
        stage_name: str,
        config: Dict[str, Any],
        compute_fn: Callable
    ) -> Any:
        """
        Hämta cached result eller kör compute_fn.
        
        Args:
            stage_name: Namnet på stage
            config: Pipeline config
            compute_fn: Function att köra om cache miss
        
        Returns:
            Stage result (cached eller nyberäknat)
        """
        current_hash = self._hash_stage_config(stage_name, config)
        cached_hash = self.hashes.get(stage_name)
        
        # Cache hit
        if cached_hash == current_hash and stage_name in self.cache:
            return self.cache[stage_name]
        
        # Cache miss - compute
        result = compute_fn()
        
        # Cache result
        self.cache[stage_name] = result
        self.hashes[stage_name] = current_hash
        self.computed_stages.append(stage_name)
        
        return result
    
    def _hash_stage_config(self, stage_name: str, config: Dict[str, Any]) -> str:
        """
        Beräkna hash för stage-specific config.
        """
        stage_config = config.get('stages', {}).get(stage_name, {})
        config_str = json.dumps(stage_config, sort_keys=True)
        return hashlib.sha256(config_str.encode()).hexdigest()
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Hämta cache-statistik.
        """
        return {
            'total_stages': len(self.cache),
            'computed_this_run': len(self.computed_stages),
            'cached_stages': list(self.cache.keys())
        }
    
    def get_computed_stages(self) -> list:
        """
        Returnera lista med stages som kördes (inte cachades).
        """
        return self.computed_stages.copy()
    
    def clear(self):
        """
        Rensa cache.
        """
        self.cache.clear()
        self.hashes.clear()
        self.computed_stages.clear()
```

### 11.3 Stage 2: Pre-DEA

```python
# pipeline/stages/stage_02_predea.py

import pandas as pd
from typing import Dict, Any
from pipeline.methods.capex.wacc_scaling import apply_wacc_scaling
from pipeline.methods.capex.kent_batch_pipeline import (
    run_kent_pipeline_batch,
    extract_capex_2024_for_dea,
    aggregate_period_sum
)
from pipeline.methods.capex.capbase_prep import process_kent_file


def stage_02_predea(
    baseline: Dict[str, pd.DataFrame],
    config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Stage 2: Pre-DEA CAPEX modification.
    
    Fyra metoder:
    1. baseline: Ingen ändring
    2. wacc_scaling: Skala Avkastning proportionellt
    3. parameter_adjustments: Kör kent_pipeline för alla 148 företag
    4. kent_upload: KENT-fil för 1 företag → kent_pipeline för alla 148
    
    Args:
        baseline: Output från stage_01_baseline
        config: Pipeline config
    
    Returns:
        Dict med:
        - data_all_companies: DataFrame (148 rows)
        - metadata: Method info och periodsummor
    """
    predea_config = config['stages']['predea']
    method = predea_config['method']
    
    # Start med baseline data
    df = baseline['data_modeller_all_companies'].copy()
    metadata = {'method': method, 'capex_source': 'baseline'}
    
    if method == 'baseline':
        # Ingen ändring
        pass
    
    elif method == 'wacc_scaling':
        # Method 2: Skala Avkastning
        wacc_config = predea_config['wacc_scaling']
        df = apply_wacc_scaling(
            df,
            new_wacc=wacc_config['new_wacc'],
            baseline_wacc=wacc_config['baseline_wacc']
        )
        metadata['capex_source'] = 'wacc_scaled'
    
    elif method == 'parameter_adjustments':
        # Method 3: Kör kent_pipeline för ALLA 148 företag
        param_config = predea_config['parameter_adjustments']
        
        kent_result = run_kent_pipeline_batch(
            capbase_all_companies=baseline['capbase_a_all_companies'],
            wacc=param_config['wacc'],
            normvalue_adjustments=param_config.get('normvalues'),
            lifetime_adjustments=param_config.get('lifetimes')
        )
        
        # Extrahera CAPEX för 2024 (för DEA)
        capex_2024 = extract_capex_2024_for_dea(kent_result)
        
        # Merge med data_modeller (behåll OPEXp, volymer)
        df = merge_capex_with_baseline(df, capex_2024, baseline['reconciliation'])
        
        # Spara periodsumma för Post-DEA
        metadata['period_sum'] = aggregate_period_sum(kent_result)
        metadata['capex_source'] = 'kent_pipeline'
    
    elif method == 'kent_upload':
        # Method 4: KENT-fil för 1 företag → kent_pipeline för alla
        kent_config = predea_config['kent_upload']
        
        # Steg 1-4: Bygg capbase för inloggat företag
        capbase_user = process_kent_file(kent_config['kent_file_path'])
        
        # Kombinera: 147 från baseline + 1 från KENT
        capbase_combined = replace_company_capbase(
            baseline['capbase_a_all_companies'],
            capbase_user,
            user_id_network=kent_config['user_id_network']
        )
        
        # Steg 5-8: Kör kent_pipeline för alla 148
        kent_result = run_kent_pipeline_batch(
            capbase_all_companies=capbase_combined,
            wacc=kent_config['wacc'],
            normvalue_adjustments=kent_config.get('normvalues'),
            lifetime_adjustments=kent_config.get('lifetimes')
        )
        
        # Extrahera och merge
        capex_2024 = extract_capex_2024_for_dea(kent_result)
        df = merge_capex_with_baseline(df, capex_2024, baseline['reconciliation'])
        
        metadata['period_sum'] = aggregate_period_sum(kent_result)
        metadata['capex_source'] = 'kent_upload'
    
    else:
        raise ValueError(f"Unknown Pre-DEA method: {method}")
    
    return {
        'data_all_companies': df,
        'metadata': metadata
    }


def merge_capex_with_baseline(
    data_modeller: pd.DataFrame,
    capex_2024: pd.DataFrame,
    reconciliation: pd.DataFrame
) -> pd.DataFrame:
    """
    Merge CAPEX från kent_pipeline med Data_modeller baseline.
    
    Behåller OPEXp, volymer från baseline.
    Ersätter CAPEX, Avskrivning, Avkastning med beräknade värden.
    """
    # Merge via reconciliation (id_network → REId)
    capex_with_reid = capex_2024.merge(
        reconciliation[['id_network', 'REId']],
        on='id_network',
        how='left'
    )
    
    # Merge med data_modeller
    df = data_modeller.merge(
        capex_with_reid[['REId', 'CAPEX', 'Avskrivning', 'Avkastning']],
        on='REId',
        how='left',
        suffixes=('_baseline', '')
    )
    
    # Ta bort baseline-kolumner
    df = df.drop(columns=['CAPEX_baseline', 'Avskrivning_baseline', 'Avkastning_baseline'])
    
    return df


def replace_company_capbase(
    capbase_all: pd.DataFrame,
    capbase_user: pd.DataFrame,
    user_id_network: int
) -> pd.DataFrame:
    """
    Ersätt ett företags capbase med ny KENT-data.
    
    Args:
        capbase_all: capbase_a för alla 148 företag
        capbase_user: capbase från KENT-fil för 1 företag
        user_id_network: id_network för företaget
    
    Returns:
        Combined DataFrame (147 + 1)
    """
    # Ta bort gamla rader för user_id_network
    capbase_filtered = capbase_all[capbase_all['id_network'] != user_id_network].copy()
    
    # Lägg till nya rader
    capbase_combined = pd.concat([capbase_filtered, capbase_user], ignore_index=True)
    
    return capbase_combined
```

---

## 12. SLUTSATSER OCH REKOMMENDATIONER

### 12.1 Slutsatser

1. **Nuvarande arkitektur är över-engineerad** för det faktiska behovet
2. **Pipeline-arkitektur med functional design** är optimal lösning
3. **Hash-baserad caching** ger automatisk smart execution
4. **Stage-based config** ger tydlig struktur och mappning till UI
5. **Batch processing** för kent_pipeline är nödvändigt för parameter-ändringar

### 12.2 Kärnrekommendationer

✅ **Implementera functional pipeline** (Option C från Architectural Question 1)  
✅ **Använd stage-based config** (Option A från Architectural Question 2)  
✅ **Hash-based dependency tracking** (automatisk detection)  
✅ **Batch processing för kent_pipeline** (unified implementation)  
✅ **Per-session baseline loading** (ingen delning mellan användare)  
✅ **Stop-on-error** med user-friendly meddelanden  
✅ **Scope-suffix i DataFrame-namn** (`_all_companies`, `_single_company`)

### 12.3 Nästa Steg

1. **Review:** Granska detta dokument med teamet
2. **Godkänn:** Beslut om arkitektur-approach
3. **Implementera:** Följ migrationsplanen (Fas 1-6)
4. **Testa:** Excel-validation för alla scenarios
5. **Deploy:** Production deployment när validerad

### 12.4 Förväntade Resultat

Efter implementation:
- **50% mindre kod** (ta bort ProducerRegistry, VariableResolver)
- **Enklare att förstå** (functional pipeline)
- **Lättare att testa** (pure functions)
- **Bättre performance** (smart caching)
- **Enklare att underhålla** (tydlig struktur)
- **Skalbart** (lätt lägga till nya metoder/stages)

---

**Dokumentslut**

# Regumetrica - Master Reference for Claude

**Syfte:** Denna fil ger Claude kontext för arkitektur och principer i Regumetrica-kodbasen.  
**Version:** 2.0 (Nov 2025)  
**Status:** Arkitektur definierad, implementation utvärderas.

> **VIKTIGT:** För detaljerad information om specifika områden, se:
> - **PRODUCER_STANDARD.md** - Producer return-format (ProducerReturn) och kontrakt
> - **KLARGORANDEN_FRAN_ANVANDARE.md** - Dataflöde (150 → DEA → 1) och Parameter/Variable-logik
> - **INTAKTSRAM_DEKOMPOSITION_REFERENS.md** - Post-DEA beräkningar (effektiviseringskrav → intäktsram)
> - **PRE_DEA_KONCEPTUELL_GUIDE.md** - Pre-DEA beräkningar (WACC => parametrar/variables => CAPEX) 

---

## 1. Executive Summary - Vad Claude BehÃ¶ver Veta FÃ¶rst

### 1.1 Vad Systemet GÃ¶r

Regumetrica Ã¤r ett interaktivt dashboard fÃ¶r att berÃ¤kna och analysera intÃ¤ktsramar fÃ¶r svenska lokalnÃ¤tfÃ¶retag enligt Energimarknadsinspektionens (Ei) regulatoriska ramverk. AnvÃ¤ndarna Ã¤r elmarknadsanalytiker och fÃ¶retag som behÃ¶ver:

1. **BerÃ¤kna intÃ¤ktsramar** med olika antaganden och metoder
2. **Analysera effektivitet** via DEA (och framtida: SFA, StoNED)
3. **KÃ¶ra scenarioanalyser** fÃ¶r att fÃ¶rstÃ¥ regulatoriska effekter
4. **JÃ¤mfÃ¶ra med baseline** (Ei's officiella vÃ¤rden)

### 1.2 Systemets Arkitektoniska Revolution

**FÃ¶re (gamla systemet):**
- Tab-baserad UI med tight coupling
- HÃ¥rdkodade datakÃ¤llor
- Brutna beroenden mellan komponenter
- SvÃ¥rt att lÃ¤gga till nya analysmetoder

**Nu (modulÃ¤r arkitektur):**
- Flow-based UI (Setup â†’ Config â†’ Execute â†’ Results)
- Multipla producers per variabel
- Automatisk dependency resolution
- LÃ¤tt att lÃ¤gga till nya metoder (SFA = 120 rader kod vs 1000+ fÃ¶re)

**Status:** Implementationen Ã¤r 95% klar och production-ready.

---

## 2. Arkitektoniska Principer - Hur Claude Ska TÃ¤nka

### 2.1 Separation of Concerns

Systemet Ã¤r uppdelat i tre huvuddelar med tydliga ansvar:

```
CORE (Infrastructure)
â”œâ”€ Vad: Datalogik, orkestrering, validering
â”œâ”€ Ansvar: HÃ¥lla systemet kÃ¶rande
â””â”€ Regel: Ã„NDRA INTE utan god anledning

PRODUCERS (Business Logic)
â”œâ”€ Vad: BerÃ¤kningar och dataproduktion
â”œâ”€ Ansvar: Producera variabler (WACC, CAPEX, efficiency, etc.)
â””â”€ Regel: HÃ„R lÃ¤gger du till ny funktionalitet

UI (Presentation)
â”œâ”€ Vad: AnvÃ¤ndarinteraktion och visualisering
â”œâ”€ Ansvar: Visa data och samla anvÃ¤ndarinput
â””â”€ Regel: HÃ„R Ã¤ndrar du hur saker visas
```

**Viktigt fÃ¶r Claude:** NÃ¤r anvÃ¤ndaren ber om en ny feature:
1. FrÃ¥ga dig: "Ã„r detta en ny berÃ¤kning (producer) eller en UI-Ã¤ndring?"
2. BerÃ¤kning â†’ `producers/`
3. UI â†’ `ui/`
4. Infrastructure â†’ Diskutera fÃ¶rst, Ã¤ndra med fÃ¶rsiktighet

### 2.2 Contract-Based Design

Alla producers fÃ¶ljer ett standardiserat kontrakt:

```python
# ProducerSpec definierar kontraktet
@dataclass
class ProducerSpec:
    method: Callable          # Funktionen som producerar vÃ¤rdet
    requires: List[str]       # Vilka dependencies behÃ¶vs
    provides: str             # Vad produceras
    description: str          # Dokumentation
    optional: List[str]       # Optionella dependencies
    ui_component: str         # Vilket UI som konfigurerar denna
    default: bool             # Ã„r detta default-producer?
```

**Konsekvens fÃ¶r Claude:**
- Alla producers MÃ…STE fÃ¶lja detta kontrakt
- Dependencies deklareras explicit i `requires`
- Producers Ã¤r pure functions (ingen side effects)
- Producers vet INTE var deras input kommer ifrÃ¥n

### 2.3 Dependency-Driven Execution

VariableResolver bygger automatiskt execution order baserat pÃ¥ dependencies:

```
Exempel: AnvÃ¤ndaren vill ha 'intaktsram'
  â””â”€ Resolver ser: intaktsram requires ['kapitalkostnad', 'effektiviseringskrav', ...]
      â””â”€ effektiviseringskrav requires ['efficiency']
          â””â”€ efficiency (DEA) requires ['capex', 'opex_p', 'volumes', 'dea_config']
              â””â”€ capex requires ['wacc', ...]
                  â””â”€ wacc requires ['rf', 'mrp', 'beta', ...]

Result: Resolver kÃ¶r i ordning: rf â†’ mrp â†’ beta â†’ wacc â†’ capex â†’ volumes â†’ 
        opex_p â†’ dea_config â†’ efficiency â†’ effektiviseringskrav â†’ ... â†’ intaktsram
```

**Viktigt fÃ¶r Claude:** 
- BehÃ¶ver du ALDRIG tÃ¤nka pÃ¥ execution order sjÃ¤lv
- Deklarera bara dependencies i ProducerSpec
- Resolver hanterar resten (inklusive caching och cirkulÃ¤ra dependencies)

### 2.4 Canonical Case Definition Structure

All anvÃ¤ndarinput och konfiguration lagras i en standardiserad `case_definition`:

```python
case_definition = {
    'name': str,                    # Scenario-namn
    'description': str,             # Beskrivning
    'created_at': ISO timestamp,    
    'updated_at': ISO timestamp,
    
    # Tre huvudsektioner (den KANONISKA strukturen):
    'parameters': {                 # Regulatoriska parametrar
        'rf': 0.0287,
        'mrp': 0.0668,
        # ... alla regulatoriska val
    },
    
    'modules': {                    # Vilken producer anvÃ¤nds fÃ¶r varje variabel
        'wacc': 'capm',             # AnvÃ¤nd CAPM fÃ¶r WACC
        'capex': 'kent_full',       # AnvÃ¤nd kent_full fÃ¶r CAPEX
        'efficiency': 'dea'         # AnvÃ¤nd DEA fÃ¶r efficiency
    },
    
    'module_configs': {             # Konfiguration per producer
        'dea': {
            'inputs': ['capex', 'opex_p'],
            'outputs': ['CU', 'MW', 'NS'],
            'returns_to_scale': 'CRS'
        }
    }
}
```

**Viktigt fÃ¶r Claude:**
- ALL anvÃ¤ndarinput hamnar hÃ¤r
- LÃ¤s frÃ¥n `case_definition` fÃ¶r att veta vad anvÃ¤ndaren vill
- Uppdatera via `CaseDefinitionManager` (inte direkt!)
- Metadata sparas ocksÃ¥ i denna struktur i resultat

### 2.5 Immutability och State Management

**Regel:** Producers ska ALDRIG modifiera input eller session state direkt.

```python
# âœ… BRA: Pure function
def produce_capex_from_wacc_scaling(baseline_capex, wacc, baseline_wacc):
    """Tar input, returnerar nytt vÃ¤rde, modifierar inget"""
    scaling_factor = wacc / baseline_wacc
    return baseline_capex * scaling_factor

# âŒ DÃ…LIGT: Modifierar state
def produce_capex_from_wacc_scaling(baseline_capex, wacc, baseline_wacc):
    st.session_state.capex = baseline_capex * (wacc / baseline_wacc)  # NEJ!
    return st.session_state.capex
```

**VarfÃ¶r:** 
- GÃ¶r testing enkelt
- Undviker side effects
- MÃ¶jliggÃ¶r caching
- Resolver kan kÃ¶ra om berÃ¤kningar sÃ¤kert

---

## 3. Core Infrastructure - Vad Varje Fil GÃ¶r

### 3.1 core/producer_registry.py

**Ansvar:** Central registrering av alla variabler och deras producers.

**Nyckelkomponenter:**
- `ProducerRegistry` class: HÃ¥ller registret
- `build_default_registry()`: Skapar registret med alla variabler
- `validate_registry()`: Kontrollerar att allt Ã¤r korrekt

**NÃ¤r Claude ska Ã¤ndra denna fil:**
1. LÃ¤gga till ny variabel (t.ex. 'sfa_config')
2. LÃ¤gga till ny producer fÃ¶r befintlig variabel (t.ex. 'sfa' fÃ¶r 'efficiency')

**NÃ¤r Claude INTE ska Ã¤ndra:**
- NÃ¤r man vill Ã¤ndra hur en producer fungerar (â†’ Ã¤ndra producer-filen istÃ¤llet)
- NÃ¤r man vill Ã¤ndra UI (â†’ Ã¤ndra UI-filen istÃ¤llet)

**Exempel pÃ¥ tillÃ¤gg:**
```python
# I build_default_registry(), lÃ¤gg till ny producer:
registry.register_variable(
    'efficiency',
    producers={
        'baseline': {...},
        'dea': {...},
        'sfa': {  # NY PRODUCER
            'method': None,  # Binds in bootstrap_registry
            'requires': ['capex', 'opex_p', 'volumes', 'sfa_config'],
            'description': "Stochastic Frontier Analysis",
            'ui_component': 'sfa_config_ui'
        }
    }
)
```

**Viktiga metodnamn Claude behÃ¶ver kÃ¤nna till:**
- `register_variable()` - Registrera ny variabel
- `get_variable_spec()` - HÃ¤mta spec fÃ¶r variabel
- `get_producer_spec()` - HÃ¤mta spec fÃ¶r en producer
- `list_variables()` - Lista alla variabler
- `validate_registry()` - Kontrollera att registret Ã¤r OK

### 3.2 core/bootstrap_registry.py

**Ansvar:** Binder faktiska producer-funktioner till registry-entries.

**VarfÃ¶r existerar denna fil separat?**
- `producer_registry.py` definierar STRUKTUREN (vad finns)
- `bootstrap_registry.py` binder IMPLEMENTATIONEN (hur det gÃ¶rs)
- Detta hÃ¥ller registry lÃ¤ttviktigt och importerar inte alla dependencies

**NÃ¤r Claude ska Ã¤ndra:**
1. NÃ¤r ny producer skapats och behÃ¶ver bindas
2. NÃ¤r import-sÃ¶kvÃ¤g Ã¤ndrats

**MÃ¶nster:**
```python
def bootstrap_registry(registry: ProducerRegistry) -> ProducerRegistry:
    # Bind varje producer
    try:
        reg_var = registry.get_variable_spec('efficiency')
        if 'sfa' in reg_var.producers:
            from producers.effektivitet.sfa_producer import produce_efficiency_from_sfa
            reg_var.producers['sfa'].method = produce_efficiency_from_sfa
    except Exception:
        pass  # Graceful failure om import misslyckas
    
    return registry
```

**Viktigt:** AnvÃ¤nd alltid try/except fÃ¶r att inte krascha om import misslyckas.

### 3.3 core/variable_resolver.py

**Ansvar:** Resolva dependencies och kÃ¶ra producers i rÃ¤tt ordning.

**Nyckelmetoder:**
- `get_variable(var_name)`: Huvudmetod - hÃ¤mtar/berÃ¤knar variabel
- `_determine_producer()`: BestÃ¤mmer vilken producer som ska anvÃ¤ndas
- `_resolve_dependencies()`: Bygger dependency chain rekursivt

**Hur det fungerar internt:**
1. AnvÃ¤ndaren: `resolver.get_variable('intaktsram')`
2. Resolver checkar cache - finns det redan? Returnera det
3. Resolver lÃ¤ser `case_definition['modules']` fÃ¶r att bestÃ¤mma producer
4. Resolver resolvar rekursivt alla dependencies
5. Resolver kÃ¶r producer med dependencies som arguments
6. Resolver cachar resultat
7. Resolver returnerar vÃ¤rde

**NÃ¤r Claude ska Ã¤ndra:** NÃ¤stan aldrig! Denna fungerar generiskt fÃ¶r alla producers.

**Undantag:** Om ny feature behÃ¶ver speciell logik (t.ex. conditional dependencies).

### 3.4 core/case_definition_manager.py

**Ansvar:** Skapa och manipulera case definitions enligt kanonisk struktur.

**API Claude ska anvÃ¤nda:**
```python
manager = CaseDefinitionManager(registry)

# Skapa nytt case
case_def = manager.create_case("Mitt scenario", "Beskrivning")

# Uppdatera parameter
case_def = manager.update_parameter(case_def, 'rf', 0.035)

# VÃ¤lj producer fÃ¶r variabel
case_def = manager.set_module(case_def, 'efficiency', 'sfa')

# SÃ¤tt konfiguration fÃ¶r producer
case_def = manager.set_module_config(case_def, 'efficiency', {'inputs': [...]})

# HÃ¤mta active producers
active = manager.get_active_producers(case_def)
```

**Viktigt:** AnvÃ¤nd ALLTID CaseDefinitionManager fÃ¶r att Ã¤ndra case_definition, inte direkt dictionary-manipulation.

**VarfÃ¶r:** 
- Validering
- Timestamp-uppdatering
- Ensures kanonisk struktur
- Framtida features (undo/redo, versioning) kan lÃ¤ggas till hÃ¤r

### 3.5 core/validation_framework.py

**Ansvar:** Validera data mellan steg.

**NÃ¤r detta kÃ¶rs:**
- Efter varje producer
- Innan data skickas till UI
- NÃ¤r case_definition uppdateras

**Claude behÃ¶ver sÃ¤llan Ã¤ndra denna**, men bra att veta att validering sker automatiskt.

### 3.6 core/results_manager.py

**Ansvar:** Lagra och jÃ¤mfÃ¶ra resultat frÃ¥n olika scenarios.

**API:**
```python
results_mgr = ResultsManager()
results_mgr.store_results("Scenario 1", results_dict)
results = results_mgr.get_results("Scenario 1")
comparison = results_mgr.compare_results("Scenario 1", "Scenario 2")
```

**Status:** Implementerad men anvÃ¤nds begrÃ¤nsat fÃ¶r nÃ¤rvarande. Kan utÃ¶kas fÃ¶r scenariojÃ¤mfÃ¶relser.

---

## 4. Producers - DÃ¤r Claude LÃ¤gger Till Funktionalitet

### 4.1 Producer File Structure

Producers organiseras hierarkiskt:

```
producers/
â”œâ”€â”€ baseline/          # Ladda baseline-data frÃ¥n Ei's filer
â”œâ”€â”€ wacc/             # BerÃ¤kna WACC frÃ¥n komponenter eller baseline
â”œâ”€â”€ kapitalkostnad/   # BerÃ¤kna CAPEX via olika metoder
â”œâ”€â”€ effektivitet/     # BerÃ¤kna efficiency via DEA (framtida: SFA)
â””â”€â”€ intaktsram/       # Assemblera intÃ¤ktsram frÃ¥n komponenter
```

**Regel:** En producer per fil eller logiskt grupperade producers i samma fil.

### 4.2 Producer Function Signature

**Standard-mÃ¶nster:**
```python
def produce_<variable>_from_<source>(
    dependency1: Type,
    dependency2: Type,
    ...,
    config: dict
) -> ReturnType:
    """
    Producerar <variable> via <source>-metoden.
    
    Args:
        dependency1: Beskrivning (frÃ¥n vilken producer det kommer)
        dependency2: Beskrivning
        config: Konfiguration frÃ¥n UI
        
    Returns:
        <variable> i korrekt format
        
    Raises:
        ValueError: Om input Ã¤r invalid
    """
    # 1. Validera input
    if dependency1 is None:
        raise ValueError("dependency1 krÃ¤vs")
    
    # 2. FÃ¶rbered data
    processed_data = preprocess(dependency1, dependency2)
    
    # 3. KÃ¶r berÃ¤kning
    result = calculate(processed_data, config)
    
    # 4. Validera output
    if not validate_output(result):
        raise ValueError("Output validation failed")
    
    # 5. Returnera
    return result
```

**Namnkonvention:**
- `produce_` prefix
- `<variable>` Ã¤r registry variable name
- `from_<source>` beskriver metoden
- Exempel: `produce_efficiency_from_sfa`, `produce_capex_from_kent_upload`

### 4.3 Producer Dependencies

**Regel:** Dependencies MÃ…STE matcha `requires` i ProducerSpec exakt (namn och ordning).

```python
# I registry:
'sfa': {
    'requires': ['capex', 'opex_p', 'volumes', 'sfa_config'],
    ...
}

# I producer-funktion (MÃ…STE matcha):
def produce_efficiency_from_sfa(capex, opex_p, volumes, sfa_config):
    #                            â†‘        â†‘        â†‘         â†‘
    #                     Exakt samma namn och ordning!
```

**VarfÃ¶r:** VariableResolver anvÃ¤nder denna mappning fÃ¶r att passa arguments.

### 4.4 Ã…teranvÃ¤nda Befintlig Kod

Mycket kod finns redan i gamla systemet (`effektivitet/`, `kapitalkostnad/`, `intaktsram/`).

**Strategi:**
```python
# Producer wrapper kring befintlig logik
def produce_efficiency_from_dea(capex, opex_p, volumes, dea_config):
    """Ny producer som anvÃ¤nder befintlig DEA-kod"""
    
    # Importera befintlig kod
    from effektivitet.backend.dea_model import run_dea_analysis
    
    # Anpassa data till fÃ¶rvÃ¤ntat format
    input_data = prepare_dea_input(capex, opex_p, volumes)
    
    # KÃ¶r befintlig logik
    dea_results = run_dea_analysis(
        input_data=input_data,
        config=dea_config
    )
    
    # Extrahera det vi behÃ¶ver
    efficiency_scores = dea_results['efficiency']
    
    return efficiency_scores
```

**FÃ¶rdelar:**
- Ã…teranvÃ¤nder testad kod
- Producer blir en "adapter" mellan nytt och gammalt system
- Gradvis migration mÃ¶jlig

### 4.5 Baseline Producers

Speciellt case: Producers som laddar frÃ¥n Ei's filer (`Data_modeller.xlsx`, `EIs_DEA.xlsx`).

**Placering:** `producers/baseline/baseline_loaders.py`

**Konsoliderad baseline loader:**
```python
# I baseline_loaders.py finns:
def load_baseline_data() -> dict:
    """
    Laddar ALL baseline data i en operation.
    
    Returns:
        Dict med alla baseline-variabler:
        {
            'wacc': float,
            'capex': DataFrame,
            'opex_p': DataFrame,
            'opex_o': DataFrame,
            'volumes': DataFrame,
            'efficiency': DataFrame,
            ...
        }
    """
```

**FÃ¶rdel:** En fil-lÃ¤sning, alla baseline-producers fÃ¥r samma data.

**Producers anvÃ¤nder sedan:**
```python
def produce_wacc_from_baseline(baseline_data):
    return baseline_data['wacc']  # LÃ¤tt!
```

---

## 5. UI Structure - Hur AnvÃ¤ndarinteraktion Fungerar

### 5.1 Flow-Based Navigation

AnvÃ¤ndaren gÃ¥r igenom fyra steg:

```
1. SETUP (case_setup_page.py)
   â””â”€ VÃ¤lj VAD som ska Ã¤ndras
      â””â”€ Checkboxes fÃ¶r parameters/variables/modules
   
2. CONFIG (case_config_page.py)
   â””â”€ Konfigurera HUR det ska Ã¤ndras
      â””â”€ Radio buttons fÃ¶r metod
      â””â”€ Producer-specifik UI frÃ¥n producer_ui/
   
3. EXECUTION (streamlit_app.py, inline)
   â””â”€ Systemet kÃ¶r berÃ¤kningar automatiskt
      â””â”€ Progress bar
      â””â”€ Automatisk Ã¶vergÃ¥ng till Results
   
4. RESULTS (results_page.py)
   â””â”€ Visa resultat och breakdown
      â””â”€ JÃ¤mfÃ¶relse med baseline
      â””â”€ Export till Excel
```

**Navigation:** Styrs av `st.session_state.page` som kan vara: 'setup', 'config', 'execution', 'results'.

### 5.2 UI File Responsibilities

**ui/pages/case_setup_page.py:**
- Visa checkboxes fÃ¶r vad anvÃ¤ndaren vill Ã¤ndra
- Spara i `case_definition['selections']` (legacy field fÃ¶r UI-kompatibilitet)
- Returnera uppdaterad case_definition

**ui/pages/case_config_page.py:**
- FÃ¶r varje vald kategori: visa konfiguration
- Radio buttons fÃ¶r att vÃ¤lja producer
- Importera och visa producer-specifik UI frÃ¥n `ui/producer_ui/`
- Spara i `case_definition['modules']` och `case_definition['module_configs']`

**ui/pages/results_page.py:**
- Visa intÃ¤ktsram och breakdown
- Visa metadata (vilka metoder anvÃ¤ndes)
- Export-funktionalitet
- Kan Ã¥teranvÃ¤nda visualiseringar frÃ¥n `intaktsram/frontend/intaktsram_tabs/`

### 5.3 Producer-Specific UI Components

**Placering:** `ui/producer_ui/<producer>_ui.py`

**Namnkonvention:** `render_<producer>_config()`

**MÃ¶nster:**
```python
def render_<producer>_config() -> dict:
    """
    Visar UI fÃ¶r att konfigurera <producer>.
    
    Returns:
        dict: Konfiguration som producenten behÃ¶ver
    """
    st.subheader("<Producer> Konfiguration")
    
    # Visa inputs
    input1 = st.text_input("Label", value="default")
    input2 = st.selectbox("VÃ¤lj", options=[...])
    input3 = st.slider("Parameter", min_value=0, max_value=100)
    
    # Returnera som dict
    return {
        'input1': input1,
        'input2': input2,
        'input3': input3
    }
```

**Viktigt:** 
- Funktionen returnerar en dict
- Denna dict blir `case_definition['module_configs'][variable]`
- Producenten fÃ¥r denna dict som `config` argument

**Exempel - Integration i case_config_page:**
```python
# I case_config_page.py:
if method == 'sfa':
    from ui.producer_ui.sfa_config_ui import render_sfa_config
    config = render_sfa_config()  # KÃ¶r UI-funktionen
    case_definition['module_configs']['efficiency'] = config  # Spara config
```

### 5.4 Ã…teranvÃ¤nda Gamla UI-Komponenter

Gamla systemet har mÃ¥nga bra visualiseringar i `intaktsram/frontend/intaktsram_tabs/`.

**Strategi fÃ¶r Ã¥teranvÃ¤ndning:**

**Option 1: Direct import**
```python
# I results_page.py
from intaktsram.frontend.intaktsram_tabs.effektiviseringskrav import (
    show_dea_results,
    create_efficiency_heatmap
)

# AnvÃ¤nd direkt
show_dea_results(efficiency_data)
```

**Option 2: Wrapper function**
```python
def show_efficiency_results(efficiency_data, method):
    """Wrapper som anpassar till ny struktur"""
    if method == 'dea':
        from intaktsram.frontend.intaktsram_tabs.effektiviseringskrav import show_dea_results
        show_dea_results(efficiency_data)
    elif method == 'sfa':
        show_sfa_results(efficiency_data)  # Ny funktion
```

**Option 3: Copy and adapt**
- Kopiera funktion till `ui/components/`
- Ã„ndra fÃ¶r att passa ny datastruktur
- AnvÃ¤nd fÃ¶r bÃ¥de DEA och SFA

### 5.5 Session State Management

**NyckelvÃ¤rden i st.session_state:**
```python
st.session_state = {
    # Auth
    'access_granted': bool,
    'user_role': 'company' | 'regulator',
    'user_dmu': int,
    
    # Navigation
    'page': 'setup' | 'config' | 'execution' | 'results',
    
    # Core objects
    'producer_registry': ProducerRegistry,
    'case_manager': CaseDefinitionManager,
    
    # Case data
    'case_definition': dict,  # Kanonisk struktur
    'case_results': dict,     # Resultat frÃ¥n senaste kÃ¶rning
}
```

**Regel:** Ã„ndra aldrig direkt, anvÃ¤nd managers:
- `case_definition` â†’ Ã„ndra via `CaseDefinitionManager`
- `case_results` â†’ Ã„ndra via `ResultsManager` (eller direkt assignment efter execution)

---

## 6. DataflÃ¶den - Hur Data RÃ¶r Sig

### 6.1 Setup â†’ Config â†’ Execution â†’ Results

**Setup Phase:**
```
AnvÃ¤ndare bockar checkboxes
    â†“
case_definition['selections'] uppdateras
    â†“
[NÃ¤sta] button klickas
    â†“
st.session_state.page = 'config'
```

**Config Phase:**
```
FÃ¶r varje vald kategori:
    â†“
Visa radio button fÃ¶r metod
    â†“
AnvÃ¤ndaren vÃ¤ljer metod (t.ex. 'sfa')
    â†“
case_definition['modules']['efficiency'] = 'sfa'
    â†“
Visa producer_ui fÃ¶r SFA
    â†“
AnvÃ¤ndaren konfigurerar
    â†“
case_definition['module_configs']['efficiency'] = {...}
    â†“
[KÃ¶r berÃ¤kning] button klickas
    â†“
st.session_state.page = 'execution'
```

**Execution Phase:**
```
Ladda baseline_data
    â†“
Skapa VariableResolver(registry, case_definition, baseline_data)
    â†“
resolver.get_variable('intaktsram')
    â†“
Resolver bestÃ¤mmer execution order
    â†“
Resolver kÃ¶r producers i ordning:
    baseline â†’ wacc â†’ capex â†’ efficiency â†’ effkrav â†’ intaktsram
    â†“
Spara resultat i st.session_state.case_results
    â†“
st.session_state.page = 'results' (automatiskt)
```

**Results Phase:**
```
HÃ¤mta case_results frÃ¥n session state
    â†“
Visa intÃ¤ktsram
    â†“
Visa breakdown
    â†“
Visa metadata (vilka metoder anvÃ¤ndes)
    â†“
Export till Excel
```

### 6.2 Producer Dependency Resolution

**Exempel: Efficiency (DEA) berÃ¤kning**

```
1. AnvÃ¤ndaren vill ha intaktsram
   â””â”€ intaktsram requires effektiviseringskrav

2. effektiviseringskrav requires efficiency
   â””â”€ efficiency producer vald: 'dea'

3. DEA producer spec:
   requires: ['capex', 'opex_p', 'volumes', 'dea_config']

4. Resolver resolvar dependencies:
   
   capex:
   â””â”€ capex producer vald: 'kent_full'
   â””â”€ kent_full requires: ['wacc', 'kent_parameters', ...]
       â””â”€ wacc producer vald: 'capm'
       â””â”€ capm requires: ['rf', 'mrp', 'beta', ...]
           â””â”€ rf frÃ¥n baseline
           â””â”€ mrp frÃ¥n baseline
           â””â”€ beta frÃ¥n baseline
   
   opex_p:
   â””â”€ frÃ¥n baseline
   
   volumes:
   â””â”€ frÃ¥n baseline
   
   dea_config:
   â””â”€ frÃ¥n case_definition['module_configs']['efficiency']

5. Execution order (topological sort):
   baseline â†’ rf â†’ mrp â†’ beta â†’ wacc â†’ kent_params â†’ capex â†’ 
   opex_p â†’ volumes â†’ dea_config â†’ efficiency â†’ effkrav â†’ intaktsram

6. Varje producer kÃ¶rs med sina dependencies som arguments
```

**Viktigt fÃ¶r Claude:** Du behÃ¶ver ALDRIG skriva denna logik sjÃ¤lv. Deklarera bara dependencies i `requires` och Resolver gÃ¶r resten.

### 6.3 Config â†’ Producer Mapping

**Hur anvÃ¤ndarkonfiguration nÃ¥r producenten:**

```
1. AnvÃ¤ndaren konfigurerar i UI:
   ui/producer_ui/dea_config_ui.py
   â””â”€ render_dea_config() returnerar:
       {
           'inputs': ['capex', 'opex_p'],
           'outputs': ['CU', 'MW', 'NS'],
           'returns_to_scale': 'CRS'
       }

2. case_config_page sparar detta:
   case_definition['module_configs']['efficiency'] = <config dict>

3. Under execution:
   VariableResolver ser att 'efficiency' behÃ¶ver 'dea_config'
   â””â”€ Resolver skapar en config-producer som returnerar:
       case_definition['module_configs']['efficiency']

4. DEA producer fÃ¥r config som argument:
   produce_efficiency_from_dea(
       capex=<DataFrame>,
       opex_p=<DataFrame>,
       volumes=<DataFrame>,
       dea_config={'inputs': [...], 'outputs': [...], ...}
   )
```

**Pattern fÃ¶r config-variabler:**

Om din producer behÃ¶ver config frÃ¥n UI:
1. Skapa en config-variabel i registry (t.ex. 'sfa_config')
2. LÃ¤gg till 'sfa_config' i din producers `requires`
3. Registry skapar automatiskt en config-producer som lÃ¤ser frÃ¥n case_definition
4. Din producer fÃ¥r config som argument

---

## 7. LÃ¤gga Till Ny Funktionalitet - Konkreta Steg

### 7.1 Checklista: LÃ¤gga Till Ny Producer (t.ex. SFA)

**Backend (BerÃ¤kningslogik):**

1. **Skapa producer-fil:** `producers/effektivitet/sfa_producer.py`
   ```python
   def produce_efficiency_from_sfa(capex, opex_p, volumes, sfa_config):
       """Producerar efficiency via SFA"""
       # Implementation hÃ¤r
       return efficiency_scores
   ```

2. **Registrera i registry:** `core/producer_registry.py`
   - Hitta `build_default_registry()`
   - LÃ¤gg till 'sfa' under 'efficiency' producers
   - Om config behÃ¶vs, lÃ¤gg till 'sfa_config' som ny variabel

3. **Bind i bootstrap:** `core/bootstrap_registry.py`
   ```python
   if 'sfa' in reg_eff.producers:
       from producers.effektivitet.sfa_producer import produce_efficiency_from_sfa
       reg_eff.producers['sfa'].method = produce_efficiency_from_sfa
   ```

**Frontend (UI):**

4. **Skapa config UI:** `ui/producer_ui/sfa_config_ui.py`
   ```python
   def render_sfa_config() -> dict:
       """Visar SFA-konfiguration"""
       # UI-komponenter hÃ¤r
       return config_dict
   ```

5. **Integrera i config page:** `ui/pages/case_config_page.py`
   - LÃ¤gg till 'sfa' i radio button options
   - LÃ¤gg till elif-block som importerar och kÃ¶r render_sfa_config()

**Total kod:** ~120 rader i 5 filer.

### 7.2 Checklista: LÃ¤gga Till Ny Variabel

**Om du behÃ¶ver en helt ny variabel** (t.ex. 'quality_metrics'):

1. **Registrera variabeln:** `core/producer_registry.py`
   ```python
   registry.register_variable(
       'quality_metrics',
       dtype=pd.DataFrame,
       description="Kvalitetsmetrik per nÃ¤t",
       producers={
           'baseline': {
               'method': None,
               'requires': [],
               'description': "FrÃ¥n Data_modeller.xlsx"
           },
           'user_adjustment': {
               'method': None,
               'requires': ['baseline_quality', 'adjustment_params'],
               'description': "AnvÃ¤ndaren justerar vÃ¤rden"
           }
       }
   )
   ```

2. **Skapa producers:** `producers/quality/quality_producers.py`

3. **Bind i bootstrap:** `core/bootstrap_registry.py`

4. **Skapa UI om behÃ¶vs:** `ui/producer_ui/quality_ui.py`

### 7.3 Checklista: Ã„ndra Befintlig UI

**Om du vill Ã¤ndra hur nÃ¥got visas:**

1. **Identifiera rÃ¤tt fil:**
   - Setup-steg? â†’ `ui/pages/case_setup_page.py`
   - Config-steg? â†’ `ui/pages/case_config_page.py`
   - Results-steg? â†’ `ui/pages/results_page.py`
   - Producer-config? â†’ `ui/producer_ui/<producer>_ui.py`

2. **GÃ¶r Ã¤ndringar:** 
   - Streamlit-komponenter (st.checkbox, st.selectbox, etc.)
   - Returnera uppdaterad data

3. **Testa:** KÃ¶r app, navigera till rÃ¤tt steg, verifiera

### 7.4 Checklista: Ã…teranvÃ¤nda Befintlig Kod

**FrÃ¥n gamla systemet:**

1. **Hitta rÃ¤tt funktion:** 
   - DEA-visualiseringar? â†’ `effektivitet/frontend/`
   - Kapitalkostnad? â†’ `kapitalkostnad/frontend/`
   - IntÃ¤ktsram? â†’ `intaktsram/frontend/`

2. **Importera:**
   ```python
   from intaktsram.frontend.intaktsram_tabs.effektiviseringskrav import show_dea_results
   ```

3. **AnvÃ¤nd eller anpassa:**
   ```python
   # Direct use:
   show_dea_results(efficiency_data)
   
   # Eller wrap:
   def show_results(data, method):
       if method == 'dea':
           show_dea_results(data)
       elif method == 'sfa':
           show_sfa_results(data)
   ```

---

## 8. Viktiga Konventioner och MÃ¶nster

### 8.1 Namnkonventioner

**Filer:**
- Producers: `<category>_producer.py` eller `<category>_producers.py` (plural om flera)
- UI: `<producer>_ui.py` eller `<producer>_config_ui.py`
- Backend logic: `<function>_calculations.py` eller `<module>_model.py`

**Funktioner:**
- Producers: `produce_<variable>_from_<source>()`
- UI: `render_<producer>_config()`
- Helper: `prepare_<something>()`, `calculate_<something>()`

**Variabler i registry:**
- Lowercase med underscore: `wacc`, `capex`, `opex_p`, `efficiency`
- Descriptive: `dea_config`, `kent_parameters`, `sfa_config`

**Producer IDs:**
- Lowercase, descriptive: `baseline`, `capm`, `dea`, `sfa`, `kent_full`, `kent_upload`

### 8.2 Import Patterns

**Preferens:** Explicit imports
```python
# âœ… Bra
from producers.effektivitet.dea_producer import produce_efficiency_from_dea

# âŒ Undvik
from producers.effektivitet.dea_producer import *
```

**Try/except vid bootstrap:**
```python
# I bootstrap_registry.py, alltid:
try:
    # imports och bindings
except Exception:
    pass  # Graceful failure
```

**Conditional imports i producers:**
```python
def produce_something(...):
    # Import inside function fÃ¶r att undvika circular imports
    from some.module import heavy_calculation
    return heavy_calculation(...)
```

### 8.3 Error Handling

**I producers:**
```python
def produce_variable_from_method(...):
    # Validera input
    if required_arg is None:
        raise ValueError("required_arg cannot be None")
    
    # FÃ¶rsÃ¶k berÃ¤kning
    try:
        result = calculate(...)
    except SomeSpecificError as e:
        raise ValueError(f"Calculation failed: {e}") from e
    
    # Validera output
    if not validate_result(result):
        raise ValueError("Output validation failed")
    
    return result
```

**I UI:**
```python
def render_config():
    try:
        # UI-kod
        return config
    except Exception as e:
        st.error(f"Fel i konfiguration: {e}")
        return None  # eller default config
```

**I execution (streamlit_app.py):**
```python
try:
    intaktsram = resolver.get_variable('intaktsram')
    st.success("BerÃ¤kning klar!")
except Exception as e:
    st.error(f"Fel vid berÃ¤kning: {e}")
    st.exception(e)  # Visa full traceback fÃ¶r debugging
```

### 8.4 Documentation Standards

**Docstrings fÃ¶r producers:**
```python
def produce_variable_from_method(dep1, dep2, config):
    """
    En-liners beskrivning av vad producenten gÃ¶r.
    
    LÃ¤ngre beskrivning om behÃ¶vs, inkludera:
    - Vilken metod/algoritm som anvÃ¤nds
    - Viktiga antaganden
    - Referenser till dokumentation
    
    Args:
        dep1: Beskrivning, inkludera datatyp och kÃ¤lla
        dep2: Beskrivning
        config: Konfiguration frÃ¥n UI, keys: ['key1', 'key2']
        
    Returns:
        Beskrivning av returvÃ¤rde, format och struktur
        
    Raises:
        ValueError: NÃ¤r nÃ¥got Ã¤r fel
        
    Example:
        >>> config = {'inputs': ['capex'], 'outputs': ['CU']}
        >>> result = produce_variable_from_method(capex, opex, config)
    """
```

**Inline comments:**
- AnvÃ¤nd sparsamt
- FÃ¶rklara VARFÃ–R, inte VAD
- AnvÃ¤nd TODO: fÃ¶r saker som behÃ¶ver gÃ¶ras

**Registry documentation:**
- Fyll alltid i `description` field
- Dokumentera vilka keys `config` fÃ¶rvÃ¤ntas ha

---

## 9. Testing och Debugging

### 9.1 Manuell Testing av Producer

**Skapa test-fil:** `test_<producer>.py`

```python
import pandas as pd
from producers.effektivitet.sfa_producer import produce_efficiency_from_sfa

# Mock dependencies
capex = pd.DataFrame({
    'DMU': [1, 2, 3],
    'capex': [100, 200, 150]
})

opex_p = pd.DataFrame({
    'DMU': [1, 2, 3],
    'opex_p': [50, 100, 75]
})

volumes = pd.DataFrame({
    'DMU': [1, 2, 3],
    'CU': [1000, 2000, 1500],
    'MW': [10, 20, 15]
})

sfa_config = {
    'inputs': ['capex', 'opex_p'],
    'outputs': ['CU', 'MW'],
    'distribution': 'half_normal'
}

# Test
try:
    result = produce_efficiency_from_sfa(capex, opex_p, volumes, sfa_config)
    print("Success!")
    print(result)
    
    # Validera
    assert 'efficiency' in result.columns
    assert len(result) == 3
    assert all(result['efficiency'] >= 0)
    assert all(result['efficiency'] <= 1)
    
except Exception as e:
    print(f"Failed: {e}")
    import traceback
    traceback.print_exc()
```

### 9.2 Debugging i Streamlit

**St.write debugging:**
```python
# Visa mellansteg
st.write("Debug: case_definition", case_definition)
st.write("Debug: config", config)
st.dataframe(result.head())  # Visa data
```

**Session state inspection:**
```python
# LÃ¤gg till i sidebar eller results page
with st.expander("Debug: Session State"):
    st.write(st.session_state)
```

**Exception handling:**
```python
try:
    result = some_calculation()
except Exception as e:
    st.exception(e)  # Visar full traceback
```

### 9.3 Vanliga Problem och LÃ¶sningar

**Problem 1: "Variable not found in registry"**
```
LÃ¶sning: Kolla att variabeln Ã¤r registrerad i build_default_registry()
```

**Problem 2: "Producer method is None"**
```
LÃ¶sning: Kolla att producenten Ã¤r bound i bootstrap_registry()
```

**Problem 3: "Circular dependency detected"**
```
LÃ¶sning: Kolla requires fÃ¶r alla producers i kedjan, en mÃ¥ste ha felaktig dependency
```

**Problem 4: "TypeError: missing required argument"**
```
LÃ¶sning: Producer function signature mÃ¥ste matcha ProducerSpec.requires exakt
```

**Problem 5: UI uppdateras inte**
```
LÃ¶sning: Streamlit cachar. Tryck 'c' i terminalen fÃ¶r clear cache, eller st.rerun()
```

---

## 10. Avancerade Topics

### 10.1 Conditional Dependencies

**Om en producer behÃ¶ver olika dependencies beroende pÃ¥ config:**

```python
# I registry:
'variable': {
    'requires': ['common_dep', 'conditional_dep'],
    'optional': ['conditional_dep']  # Markera som optional
}

# I producer:
def produce_variable(common_dep, conditional_dep=None):
    if conditional_dep is not None:
        # AnvÃ¤nd conditional_dep
        pass
    else:
        # AnvÃ¤nd default-logik
        pass
```

**Resolver kommer skicka None om optional dependency inte finns.**

### 10.2 Multiple Output Producers

**Om en producer producerar flera variabler samtidigt:**

Nuvarande design: En producer = en variabel.

**Om du MÃ…STE ha multiple outputs:**
1. Skapa en producer fÃ¶r primÃ¤r output
2. Skapa "extractor" producers fÃ¶r sekundÃ¤ra outputs
3. Extractor lÃ¤ser cached primÃ¤r output

```python
# Primary producer
def produce_dea_results(capex, opex_p, volumes, config):
    dea_output = run_dea_analysis(...)
    # Cache i session state eller liknande
    st.session_state.dea_full_output = dea_output
    return dea_output['efficiency']  # PrimÃ¤r output

# Extractor producer
def produce_dea_slack_variables():
    if 'dea_full_output' in st.session_state:
        return st.session_state.dea_full_output['slack']
    raise ValueError("DEA must be run first")
```

**BÃ¤ttre approach:** Strukturera producers sÃ¥ att en variabel = en output.

### 10.3 Caching Strategies

**Resolver har inbyggd caching:**
- Varje variable cachas efter fÃ¶rsta get_variable() call
- Cache Ã¤r per resolver instance
- Cache rensas vid ny resolver (ny execution)

**FÃ¶r tung preprocessing:**
```python
@st.cache_data
def load_heavy_data():
    # Denna kÃ¶rs bara en gÃ¥ng, cachas av Streamlit
    return pd.read_excel("large_file.xlsx")

def produce_variable(...):
    data = load_heavy_data()  # HÃ¤mtar frÃ¥n cache
    # Process data
    return result
```

**Viktigt:** Var fÃ¶rsiktig med st.cache_data pÃ¥ functions som anvÃ¤nder st.session_state.

### 10.4 Role-Based Access Control

**Nuvarande implementation:**
- `st.session_state.user_role` Ã¤r 'company' eller 'regulator'
- `st.session_state.user_dmu` innehÃ¥ller anvÃ¤ndarens DMU (fÃ¶r companies)

**Filtrera data i producer:**
```python
def produce_variable(...):
    result = calculate_for_all_dmus(...)
    
    # Filtrera baserat pÃ¥ roll
    if st.session_state.user_role == 'company':
        user_dmu = st.session_state.user_dmu
        result = result[result['DMU'] == user_dmu]
    
    return result
```

**Alternativt:** Filtrera i UI (results_page), inte i producer.

---

## 11. Roadmap och Future Features

> **OBS:** Denna sektion reflekterar arkitektur-design. Befintlig implementation
> är problematisk och behöver omarbetas enligt nya guider (se dokumenthierarki ovan).

### 11.1 Arkitektur-komponenter (Definierade, behöver omarbetas)

âœ… **Core Infrastructure:**
- ProducerRegistry
- VariableResolver
- CaseDefinitionManager
- ValidationFramework
- ResultsManager

âœ… **Producers:**
- Baseline loaders
- WACC (CAPM)
- CAPEX (4 metoder: baseline, wacc_scaling, kent_full, kent_upload)
- DEA-analys
- Effektiviseringskrav
- IntÃ¤ktsram assembly

âœ… **UI:**
- Flow-based navigation (Setup â†’ Config â†’ Execute â†’ Results)
- Producer-specific UI components
- Progress tracking
- Firebase authentication
- Role-based access

### 11.2 Pågående Arbete (Kritiskt)

**Kritiskt att åtgärda först:**
- Producer return-format → Se PRODUCER_STANDARD.md
- Dataflöde 148→DEA→1 → Se KLARGORANDEN_FRAN_ANVANDARE.md
- Post-DEA beräkningar → Se INTAKTSRAM_DEKOMPOSITION_REFERENS.md

âš ï¸ **Mindre gaps:**
- Efficiency baseline producer (referens-DEA) - behÃ¶ver binding
- Trunkering_params baseline - behÃ¶ver implementation
- Integration/E2E tests
- Dokumentation (user guide)

ðŸ”® **Future features (ej blockerat av arkitektur):**
- SFA (Stochastic Frontier Analysis) - 120 rader kod
- StoNED (Stochastic Nonparametric Envelopment)
- Volume scenarios (tillvÃ¤xt, merger)
- Quality scenarios (AIT-fÃ¶rbÃ¤ttring, weather hardening)
- OPEX scenarios (justerade vÃ¤rden)
- Multiple scenario comparison side-by-side
- Time series analysis (flera Ã¥rs data)
- Export till Word/PDF
- API fÃ¶r external tools

**PoÃ¤ngen:** Arkitekturen Ã¤r redo. Dessa features Ã¤r straight-forward att lÃ¤gga till.

### 11.3 Legacy Code Status

**Filer som INTE anvÃ¤nds lÃ¤ngre:**
- `pages/foretag/foretag_intaktsram.py` - Ersatt av flow-based UI
- `pages/foretag/foretag_effektivitet.py` - Ersatt
- Gamla tab-baserade sidor

**Dessa finns kvar fÃ¶r:**
1. Referens (tills flow-based UI Ã¤r 100% stabil)
2. Visualiseringar kan Ã¥teranvÃ¤ndas

**Kan tas bort nÃ¤r:** Flow-based UI Ã¤r verifierat i produktion (1-2 mÃ¥nader).

---

## 12. Snabbreferens fÃ¶r Claude

### 12.1 BeslutstrÃ¤: Vart Ska Kod Placeras?

```
Ã„r det en ny berÃ¤kning/algoritm?
â”œâ”€ JA â†’ producers/<kategori>/<namn>_producer.py
â”‚       Exempel: producers/effektivitet/sfa_producer.py
â”‚
â””â”€ NEJ â†’ Ã„r det hur anvÃ¤ndaren interagerar?
    â”œâ”€ JA â†’ ui/producer_ui/<namn>_ui.py eller ui/pages/
    â”‚       Exempel: ui/producer_ui/sfa_config_ui.py
    â”‚
    â””â”€ NEJ â†’ Ã„r det datahantering/infrastruktur?
        â”œâ”€ JA â†’ core/<funktion>.py
        â”‚       Exempel: core/data_loader_base.py
        â”‚
        â””â”€ NEJ â†’ Ã„r det visualisering/presentation?
            â””â”€ JA â†’ ui/components/ eller Ã¥teranvÃ¤nd frÃ¥n intaktsram/frontend/
```

### 12.2 Vanliga Uppgifter - Kod-Lokation

| Uppgift | Fil(er) att Ã¤ndra |
|---------|-------------------|
| LÃ¤gg till ny berÃ¤kningsmetod | `producers/<kategori>/<metod>_producer.py` (skapa)<br>`core/producer_registry.py` (registrera)<br>`core/bootstrap_registry.py` (bind) |
| LÃ¤gg till UI fÃ¶r metod | `ui/producer_ui/<metod>_ui.py` (skapa)<br>`ui/pages/case_config_page.py` (integrera) |
| Ã„ndra hur resultat visas | `ui/pages/results_page.py` |
| Ã„ndra setup-steg | `ui/pages/case_setup_page.py` |
| LÃ¤gg till ny variabel | `core/producer_registry.py` (registrera)<br>`producers/<kategori>/` (skapa producers) |
| Ã…teranvÃ¤nda gamla visualiseringar | Importera frÃ¥n `intaktsram/frontend/intaktsram_tabs/` |
| Ã„ndra datavalidering | `core/validation_framework.py` |
| Ladda ny datafil | `producers/baseline/baseline_loaders.py` eller `core/data_loader_base.py` |

### 12.3 Filer att ALDRIG Ã¤ndra (utan diskussion)

ðŸ”´ **RÃ¶r ej:**
- `core/variable_resolver.py` - Fungerar generiskt
- `streamlit_app.py` - Endast fÃ¶r routing och bootstrapping
- `core/case_definition_manager.py` - API Ã¤r stabilt

âš ï¸ **Ã„ndra med fÃ¶rsiktighet:**
- `core/producer_registry.py` - Endast fÃ¶r registrering
- `core/bootstrap_registry.py` - Endast fÃ¶r binding
- `core/validation_framework.py` - Endast fÃ¶r nya valideringsregler

### 12.4 Quick Commands fÃ¶r Debugging

**Visa registry:**
```python
registry = st.session_state.producer_registry
st.write("Variables:", registry.list_variables())
st.write("Producers for efficiency:", registry.list_producers('efficiency'))
```

**Visa case definition:**
```python
st.json(st.session_state.case_definition)
```

**Visa dependency chain:**
```python
registry = st.session_state.producer_registry
chain = registry.get_dependency_chain('intaktsram', 'assembly')
st.write("Execution order:", chain)
```

**Validate registry:**
```python
errors = registry.validate_registry()
if errors:
    st.error("Registry errors:")
    for error in errors:
        st.write(f"- {error}")
```

---

## 13. Key Takeaways fÃ¶r Claude

### 13.1 De Viktigaste Principerna

1. **Separation of Concerns**
   - Core = infrastructure (Ã¤ndra sÃ¤llan)
   - Producers = business logic (lÃ¤gg till ofta)
   - UI = presentation (Ã¤ndra fÃ¶r anvÃ¤ndarupplevelse)

2. **Contract-Based Design**
   - Producers fÃ¶ljer ProducerSpec
   - Dependencies explicit deklarerade
   - Pure functions, ingen side effects

3. **Dependency-Driven Execution**
   - Resolver gÃ¶r allt automatiskt
   - Deklarera bara requires
   - Oroa dig inte fÃ¶r ordning

4. **Canonical Case Definition**
   - ALL anvÃ¤ndarinput i case_definition
   - Uppdatera via CaseDefinitionManager
   - Metadata sparas konsekvent

5. **Immutability**
   - Producers returnerar nya vÃ¤rden
   - Ingen direct st.session_state manipulation
   - Testability och reproducibility

### 13.2 Fem Vanligaste Misstagen (Undvik!)

1. âŒ **Ã„ndra core/* utan att fÃ¶rstÃ¥ konsekvenserna**
   - âœ… LÃ¤gg till producers och UI istÃ¤llet

2. âŒ **GlÃ¶mma registrera ny producer i registry OCH bootstrap**
   - âœ… BÃ¥da behÃ¶vs: registry (struktur) + bootstrap (implementation)

3. âŒ **Producer function signature matchar inte requires**
   - âœ… Exakt samma namn och ordning

4. âŒ **Direkt modifiera case_definition eller session state**
   - âœ… AnvÃ¤nd CaseDefinitionManager

5. âŒ **Producer har side effects (modifierar input, anvÃ¤nder global state)**
   - âœ… Pure functions only

### 13.3 NÃ¤r Claude Ã„r OsÃ¤ker

**FrÃ¥ga dig sjÃ¤lv:**
1. Finns liknande kod redan? (Titta i samma kategori under producers/)
2. FÃ¶ljer jag etablerade mÃ¶nster? (JÃ¤mfÃ¶r med befintliga producers/UI)
3. Ã„r detta en core-Ã¤ndring? (Om ja, diskutera med anvÃ¤ndaren fÃ¶rst)
4. Kan jag Ã¥teranvÃ¤nda befintlig kod? (Mycket finns i gamla systemet)

**Om fortfarande osÃ¤ker:**
1. FÃ¶reslÃ¥ lÃ¶sning MEN nÃ¤mn alternativ
2. FrÃ¥ga anvÃ¤ndaren om preferens
3. Visa kod-exempel fÃ¶r bÃ¥da approaches

---

## 14. Slutord - Använd Dokumentationen Effektivt

### Dokumenthierarki

| Dokument | Innehåll |
|----------|----------|
| **MASTER_REFERENCE** (denna fil) | Arkitektur & principer |
| **PRODUCER_STANDARD.md** | Return-format, kontrakt |
| **KLARGORANDEN_FRAN_ANVANDARE.md** | Dataflöde 480→DEA→1 |
| **INTAKTSRAM_DEKOMPOSITION_REFERENS.md** | Post-DEA beräkningar |

### Läsordning

**Ny kontext:** Denna fil (avsnitt 1-2) → Relevant guide

**Producer-arbete:** PRODUCER_STANDARD.md först
**Dataflöde:** KLARGORANDEN först  
**Post-DEA:** INTAKTSRAM_DEKOMPOSITION först

**Under kodning:** Avsnitt 12 (Snabbreferens)

---

## Appendix: Viktiga Filreferenser

**NÃ¤r Claude behÃ¶ver se faktisk kod, lÃ¤s dessa:**

- **Core infrastructure:** `core/producer_registry.py`, `core/variable_resolver.py`
- **Producer exempel:** `producers/wacc/wacc_producers.py`, `producers/effektivitet/dea_producer.py`
- **UI exempel:** `ui/pages/case_config_page.py`, `ui/producer_ui/dea_config_ui.py`
- **Main app:** `streamlit_app.py`
- **Baseline loading:** `producers/baseline/baseline_loaders.py`
- **Old system reference (fÃ¶r Ã¥teranvÃ¤ndning):** `intaktsram/frontend/`, `effektivitet/frontend/`

**Alla dessa filer finns i Claude's projekt-knowledge.**

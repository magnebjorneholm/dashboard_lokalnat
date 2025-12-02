# PROMPT 1: REGUMETRICA PIPELINE ARCHITECTURE DESIGN

**Version:** 1.0  
**Datum:** 2025-12-01  
**För:** Claude Opus 4  
**Från:** Regumetrica development team

---

## EXECUTIVE SUMMARY

### Vad systemet gör
Regumetrica är ett interaktivt Streamlit-dashboard för analys av svenska lokalnätföretags intäktsramar under tillsynsperioden 2024-2027. Systemet används av:
- **Lokalnätföretag:** Simulera egna scenarier (filtrerat per DMU)
- **Energimarknadsinspektionen (Ei):** Tillgång till alla 148 företag

### Nuvarande problem
Det modulära systemet med ProducerRegistry, VariableResolver och CaseDefinitionManager är **över-engineerat** för det faktiska behovet. Systemet är i grunden en **linjär pipeline** (Baseline → Pre-DEA → DEA → Extraction → Post-DEA) men implementerat som ett komplext variabel-resolutions-system med dependency tracking.

### Mål med omdesign
Omdesigna systemet till en **pipeline-arkitektur** med:
1. **Format-agnosticism:** Varje stage bryr sig bara om att input/output är i rätt format, inte var data kommer ifrån
2. **Smart execution:** Kör endast stages som påverkas av användarens ändringar (intelligent caching)
3. **Skalbarhet:** Enkelt att lägga till nya metoder (SFA, StoNED) utan att ändra pipeline-logik
4. **Enkelhet:** Lättare att förstå och underhålla för nationalekonomister utan djup programmeringserfarenhet

---

## CURRENT STATE OVERVIEW

### Bifogade guider (läs dessa först)
1. **COMPLETE_DATASET_AND_DATAFLOW_GUIDE.md** - Dataset och dataflöde
2. **Funktioner_for_regumetrica.md** - Beskriver beräkningsfiler och metoder
3. **Regumetrica_full_arkitektur.md** - Fullständigt dataflöde (komplement till COMPLETE)
4. **Regumetrica_UM.pdf** - User manual med UI-terminologi

### Centrala koncept från guiderna

#### Tre typer av användarval (från User Manual)
1. **Parameters:** Uniforma värden som gäller alla 148 företag (t.ex. WACC, normvärden, livslängder)
2. **Variables:** Företagsspecifika mätvärden som kan ändras (t.ex. KENT-fil med nya komponenter)
3. **Modules:** Val av beräkningsmetod (t.ex. DEA vs SFA, OPEX vs TOTEX)

#### Pipeline-flöde (konceptuellt)
```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   BASELINE   │ → │   PRE-DEA    │ → │     DEA      │ → │  EXTRACTION  │ → │   POST-DEA   │
│   LOADING    │    │   CAPEX MOD  │    │   ANALYSIS   │    │  (1 company) │    │  INTÄKTSRAM  │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
  df_148              df_148_modified    df_148_efficiency     df_1              intaktsram_dict

Data sources:
- Stage 1: Data_modeller.xlsx (148 företag)
- Stage 3: EIs_DEA.xlsx (baseline efficiency för 148 företag)
- Stage 5: SDF/Löpande kostnader (opåverkbara per företag)
```

**KRITISKT:** EIs_DEA.xlsx innehåller Ei's officiella DEA-resultat (Effektivitet, potential, Effkrav_proc) vilket betyder att DEA-stage kan skippa beräkning om baseline-konfiguration används.

### Nuvarande kod-arkitektur

#### Core infrastructure (nuvarande implementation)
```
core/
├── bootstrap_registry.py       # Binder producer functions till registry
├── case_definition_manager.py  # Hanterar case definitions
├── producer_registry.py        # Registry över producers och deras dependencies
├── variable_resolver.py        # Resolver för variabel-dependencies
├── validation_framework.py     # Validering av data och case definitions
└── results_manager.py          # Hanterar resultat (oklart om används)
```

#### Producers (nuvarande PROPBLEMATISKA implementation)
```
producers/
├── baseline/
│   ├── baseline_loaders.py     # Laddar Data_modeller.xlsx
│   └── reference_dea_loader.py # Laddar baseline DEA-resultat
├── wacc/
│   └── wacc_producers.py       # WACC från CAPM
├── kapitalkostnad/
│   ├── capex_producers.py      # WACC-skalning, kent_full, kent_upload
│   ├── kent_pipeline.py        # Steg 5-8 i beräkningskedjan
│   ├── capbase_prep.py         # Steg 1-4 från KENT-fil
│   └── parameter_adjustments.py # Normvärde/livslängd-justeringar
├── effektivitet/
│   ├── dea_producer.py         # DEA-analys
│   └── dea_model.py            # DEA-implementation (PuLP)
└── intaktsram/
    └── intaktsram_assembly.py  # Summerar intäktsram
```

---

## IDENTIFIED PROBLEMS

### 1. Namnkonflikter och inkonsekvent scope

#### Problem A: CAPEX-beräkningar
- `produce_capex_from_baseline()` returnerar DataFrame med kolumn 'CAPEX'
- Men Data_modeller.xlsx har nu Avskrivning + Avkastning uppdelat
- DEA behöver CAPEX för **år 2024**, men `capex_producers.py` returnerar **periodsummor (2024-2027)**
- Ingen tydlig funktion som extraherar CAPEX_2024 från periodsummor

**Konsekvens:** Oklart vilken CAPEX som används var i pipelinen.

#### Problem B: DataFrame scope-förvirring
- Vissa producers returnerar 148 rader (för DEA)
- Vissa producers returnerar 1 rad (för intäktsram)
- Inga naming conventions för att skilja scope

**Konsekvens:** Svårt att veta om en DataFrame innehåller alla företag eller bara inloggat företag.

#### Problem C: WACC-dubbel användning
- WACC används både för att skala Avkastning direkt (Pre-DEA metod 2)
- OCH som parameter i kent_pipeline (Pre-DEA metod 3-4, steg 7)
- Ingen tydlig separation mellan `wacc_value` (float) och `wacc_scaling_factor` (float)

**Konsekvens:** Risk för förvirring om WACC appliceras dubbelt.

#### Problem D: Parameter vs Variable terminology
- Guiderna pratar om "parameter-ändringar" (uniform för alla 148)
- Guiderna pratar om "variable-ändringar" (specifikt för 1 företag)
- Men i code används `case_definition['parameters']` för BÅDA

**Konsekvens:** Backend-struktur matchar inte domänterminologi.

### 2. Över-engineering

#### ProducerRegistry/VariableResolver komplexitet
- **Nuvarande:** Dependency tracking med circular dependency detection, caching, rekursiv resolution
- **Faktiskt behov:** Linjär pipeline där varje stage triggas av föregående
- **Exempel:** DEA beror ALLTID på Pre-DEA output, det finns inga cirkulära dependencies

#### Bootstrap complexity
- Många try-except blocks som gömmer problem
- Lambda functions för trivial logic
- Onödiga "hjälpvariabler" (`capex_baseline`, `kent_parameters`, `kent_file`)

### 3. Saknade komponenter


#### CAPEX för alla 148 företag samtidigt
`kent_pipeline.py` är byggd för att hantera 1 företag åt gången, men vid parameter-ändringar (normvärden/livslängder) måste alla 148 företag omberäknas. Behöver refaktoreras för batch-processing med `id_network` som nyckel.

---

## REQUIREMENTS & VISION

### Funktionella krav (från User Manual och diskussion)

#### 1. Användardriven flexibilitet
- **DEA-modellspecifikation:** Användaren väljer själv vilka inputs/outputs som används för DEA-analys
- **CAPEX-metoder:** 4 metoder (baseline, WACC-skalning, parameter-ändringar, KENT-uppladdning)
- **Efficiency-metoder:** DEA (nu), SFA och StoNED (framtida)
- **Effektiviseringskrav:** Användaren väljer trunkering, IQR-multiplikator, OPEX vs TOTEX

#### 2. Format-agnosticism (KRITISKT)
Varje pipeline-stage ska vara **källoberoende**:

**Exempel 1: DEA-stage**
```python
# DEA bryr sig INTE om HUR CAPEX beräknades
# Den kräver bara att input har rätt format:

def run_dea(df_all_companies: pd.DataFrame, model_spec: dict) -> pd.DataFrame:
    """
    Input contract:
        df_all_companies: DataFrame med kolumner [DMU, REId, Företag, CAPEX, OPEXp, CU, MW, NS, MWhl, MWhh]
        model_spec: {'inputs': [...], 'outputs': [...], 'rts': 'VRS', 'orientation': 'input'}
    
    Output contract:
        DataFrame med kolumner [DMU, efficiency, potential, is_outlier]
    
    Källan till CAPEX (baseline/wacc-skalning/parameter-ändringar/KENT) spelar INGEN roll.
    """
```

**Exempel 2: Effektiviseringskrav-stage**
```python
# Effektiviseringskrav bryr sig INTE om efficiency beräknades med DEA/SFA/StoNED
# Den kräver bara rätt format:

def calculate_effkrav(df_efficiency: pd.DataFrame, config: dict) -> pd.DataFrame:
    """
    Input contract:
        df_efficiency: DataFrame med kolumner [DMU, efficiency, potential, is_outlier]
        config: {'truncation': 0.30, 'iqr_multiplier': 2.0, ...}
    
    Output contract:
        DataFrame med kolumner [DMU, effkrav_proc]
    
    Källan till efficiency spelar INGEN roll.
    """
```

#### 3. Smart pipeline execution
Användaren ska inte behöva köra hela pipelinen varje gång:

**Scenario 1:** Användaren ändrar endast DEA-modellspecifikation
- ❌ Ineffektivt: Kör om Pre-DEA + DEA + Post-DEA
- ✅ Effektivt: Använd baseline Pre-DEA result → Kör endast DEA + Post-DEA

**Scenario 2:** Användaren ändrar WACC
- ❌ Ineffektivt: Ladda om Data_modeller.xlsx
- ✅ Effektivt: Använd cached baseline för data_modeller.xl → Skala avkastning och beräkna ny CAPEX och kör DEA + Post-DEA

**Scenario 3:** Användaren ändrar effektiviseringskrav-config (trunkering)
- ❌ Ineffektivt: Kör om Pre-DEA + DEA + Post-DEA
- ✅ Effektivt: Använd baseline DEA result → Kör endast Post-DEA med ny trunkrting

#### 4. UI-terminologi måste bevaras
Frontend måste visa "Parameters, Variables, Modules" enligt User Manual, men backend kan ha enklare struktur. Behöver **mapping layer** mellan UI-koncept och pipeline-config.

### Pipeline-stages detaljerat

#### Stage 1: Baseline Loading
```python
Output: df_all_companies (148 rader)
Kolumner: [DMU, REId, Företag, OPEXp, CAPEX, Avskrivning, Avkastning, CU, MW, NS, MWhl, MWhh]
Källa: Data_modeller.xlsx
Påverkas av: Ingenting (körs alltid första gången)
```

#### Stage 2: Pre-DEA CAPEX Modification
**Fyra metoder (användaren väljer EN):**

**Metod 1: Baseline**
- Input: df_all_companies från Stage 1
- Process: Ingen ändring
- Output: df_all_companies (oförändrad)

**Metod 2: WACC-skalning**
- Input: df_all_companies från Stage 1 + ny WACC
- Process: Skala endast Avkastning-kolumnen för alla 148 företag
  ```python
  scaling_factor = wacc_new / 0.0453
  df['Avkastning'] = df['Avkastning'] * scaling_factor
  df['CAPEX'] = df['Avskrivning'] + df['Avkastning']
  ```
- Output: df_all_companies_modified (148 rader, skalad CAPEX)

**Metod 3: Parameter-ändringar (normvärden/livslängder)**
- Input: capbase_a (510k rader för alla 148 företag) + parameter-ändringar
- Process: 
  1. Applicera normvärdejusteringar på capbase_a
  2. Applicera livslängdsjusteringar på capbase_a
  3. Kör kent_pipeline steg 5-8 för ALLA 148 företag
  4. Extrahera CAPEX_2024 från resultat (DOCK ska periodsumman för capex till intäktsramen)
  5. Ersätt CAPEX-kolumnen i df_all_companies
- Output: df_all_companies_modified (148 rader, omberäknad CAPEX)
- **NOTERA:** Denna metod kan kombineras med WACC (WACC används i steg 7 så ingen wacc-skalning)

**Metod 4: KENT-uppladdning**
- Input: KENT-fil (1 företag) + eventuella parameter-ändringar
- Process:
  1. Kör capbase_prep (steg 1-4) på KENT-fil → ny capbase_a för 1 företag
  2. Ersätt denna företags data i capbase_a (lämna 147 andra orörda)
  3. Kör kent_pipeline steg 5-8 för ALLA 148 företag (med eventuella parameter-ändringar)
  4. Extrahera CAPEX_2024 från resultat
  5. Ersätt CAPEX-kolumnen i df_all_companies (endast 1 rad ändrad)
- Output: df_all_companies_modified (148 rader, 1 företag med ny CAPEX)
- **NOTERA:** Denna metod kan kombineras med WACC och parameter-ändringar

**Output från Stage 2:**
```python
df_all_companies_modified: DataFrame (148 rader)
Kolumner: [DMU, REId, Företag, CAPEX, OPEXp, CU, MW, NS, MWhl, MWhh]
CAPEX = Kapitalkostnad för år 2024 (tidskod 229+230)
```

#### Stage 3: Efficiency Analysis
```python
Input: df_all_companies_modified från Stage 2 + model_spec
Process: 
  - Kör vald metod (DEA, SFA, StoNED)
  - Alla metoder måste returnera samma format
Output: df_all_companies_efficiency (148 rader)
Kolumner: [DMU, REId, Företag, efficiency, potential, is_outlier]
```

**DEA-implementation (nuvarande):**
- Super-efficiency DEA med PuLP
- Outlier-identifiering via IQR-metod
- Omberäkning utan outliers

**Framtida: SFA och StoNED**
- Måste returnera samma output-format som DEA
- Implementation kan vara helt annorlunda internt

#### Stage 4: Extraction
```python
Input: df_all_companies_efficiency från Stage 3 + user_dmu
Process: Filtrera till inloggat företags DMU
Output: df_single_company (1 rad)
Kolumner: [DMU, REId, Företag, efficiency, potential, is_outlier]
```

#### Stage 5: Post-DEA (Intäktsram)

**Steg 5.1: Ladda SDF-data för inloggat företag**
```python
Input: user_dmu eller user_reid
Process: Ladda opåverkbara kostnader, neonjusteringar, etc.
Output: baseline_data (dict med opåverkbara, adj, etc.)
```

**Steg 5.2: Beräkna effektiviseringskrav**
```python
Input: potential från Stage 4 + config (trunkering, IQR, min_effkrav)
Process: Omvandla potential → årligt effektiviseringskrav (effkrav_proc)
Output: effkrav_proc (float)
```

**Steg 5.3: Beräkna påverkbara kostnader**
```python
Input: effkrav_proc + baseline påverkbara + val av metod (OPEX/TOTEX)
Process: Applicera effektiviseringskrav enligt formel
Output: paverkbara_periodsumma (summa 2024-2027)
```

**Steg 5.4: Summera intäktsram**
```python
Input: 
  - Kapitalkostnad_periodsumma (från kent_pipeline om metod 3-4, annars från baseline)
  - paverkbara_periodsumma
  - opåverkbara kostnader
  - övriga komponenter
Output: intaktsram_dict med dekomposition
```

---

## BASELINE-FIRST STRATEGY: Varför Caching är Onödigt

### KRITISK INSIKT
Alla pipeline-stages har **baseline-data i dataseten**. Detta eliminerar behovet för komplex cache-hantering.

### Baseline-data per stage

#### Stage 1: Baseline Loading
```
Dataset: Data_modeller.xlsx
Kolumner: [DMU, REId, Företag, OPEXp, CAPEX, Avskrivning, Avkastning, CU, MW, NS, MWhl, MWhh]
Laddas: En gång per session
Scope: Alla 148 företag
```

#### Stage 2: Pre-DEA
```
Baseline = Data_modeller.xlsx (ingen modifiering)
Om användaren väljer capex_method='baseline' → använd direkt från Stage 1
Ingen beräkning behövs
```

#### Stage 3: DEA
```
Dataset: EIs_DEA.xlsx
Kolumner: [DMU, REId, Företag, Effektivitet, Supereffektivitet, potential, Effkrav_proc]
Detta är Ei's officiella DEA-resultat för nuvarande reglering
Om användaren inte vill ändra modellspecifikation → använd direkt från EIs_dea.xlsx
Ingen beräkning behövs
```

#### Stage 4: Extraction
```
Baseline = Filtrera EIs_DEA.xlsx till inloggat företag
```

#### Stage 5: Post-DEA
```
Dataset: SDF (Löpande kostnader)
Innehåller: Opåverkbara kostnader, neonjusteringar, baseline Effkrav_proc
Om användaren väljer baseline effkrav-config → använd Effkrav_proc från EIs_DEA.xlsx
```

### Smart Execution utan Cache

**Scenario 1:** Användaren ändrar endast DEA-modellspecifikation
```python
stages_to_run = ['dea', 'extraction', 'post_dea']
baseline_used = {
    'pre_dea': Data_modeller.xlsx  # Ingen beräkning, direkt från minnet
}
Resultat: Pre-DEA hoppas över, använd baseline CAPEX
```

**Scenario 2:** Användaren ändrar WACC till 5.0%
```python
stages_to_run = ['pre_dea', 'dea', 'extraction', 'post_dea']
baseline_used = {}  # Pre-DEA måste beräknas med ny WACC
Resultat: Hela pipelinen körs
```

**Scenario 3:** Användaren ändrar effkrav-config (trunkering från 0.30 till 0.25)
```python
stages_to_run = ['post_dea']
baseline_used = {
    'pre_dea': Data_modeller.xlsx,  # Använd baseline CAPEX
    'dea': EIs_DEA.xlsx             # Använd baseline DEA-resultat
}
Resultat: Endast Post-DEA körs, beräknar om effektiviseringskrav med ny trunkering
```

**Scenario 4:** Användaren går tillbaka till "full baseline"
```python
stages_to_run = []  # INGENTING körs!
baseline_used = {
    'pre_dea': Data_modeller.xlsx,
    'dea': EIs_DEA.xlsx,
    'post_dea': SDF + EIs_DEA.xlsx['Effkrav_proc']
}
Resultat: Bara sammanställ baseline intäktsram (några millisekunder)
```

### Implementation i Session State
```python
# Streamlit session_state struktur
st.session_state.baseline = {
    'df_all_companies': pd.read_excel('Data_modeller.xlsx'),  # Laddas en gång
    'capbase_a': pd.read_parquet('capbase_a.parquet'),        # Laddas en gång
    'dea_results': pd.read_excel('EIs_DEA.xlsx'),             # Laddas en gång
    'wacc': 0.0453,
    # ... övriga baseline-värden
}

# Smart execution
def run_pipeline(config, baseline):
    results = {}
    
    # Stage 2: Pre-DEA
    if config['capex_method'] == 'baseline':
        df_predea = baseline['df_all_companies']  # Direkt från minnet!
    else:
        df_predea = apply_capex_method(baseline['df_all_companies'], config)
    
    # Stage 3: DEA
    if config['dea_method'] == 'baseline':
        df_dea = baseline['dea_results']  # Direkt från minnet!
    else:
        df_dea = run_dea(df_predea, config['dea_model_spec'])
    
    # Stage 4-5: Alltid körs (snabbt)
    df_company = extract_company(df_dea, config['user_dmu'])
    intaktsram = calculate_intaktsram(df_company, config)
    
    return intaktsram
```

### Fördelar med Baseline-First Strategy

✅ **Ingen cache management:** Baseline finns alltid i session_state
✅ **Deterministiskt:** Samma config → samma resultat, varje gång
✅ **Snabbt:** Baseline är redan i minnet (pandas DataFrames)
✅ **Enkelt att förstå:** "Om baseline → använd fil, annars → beräkna"
✅ **Ingen cache invalidation:** Problem försvinner helt
✅ **Memory-effektivt:** Endast baseline laddas, inte alla möjliga variationer

### Fråga till Opus
**Bekräfta att denna strategi är optimal:** Håller du med om att baseline-first eliminerar behovet för komplex caching? Finns det edge cases där caching ändå behövs?

---

## DESIGN QUESTIONS FOR OPUS

### FRÅGA A: Dependency Tracking Implementation
Hur ska systemet bestämma vilka stages som behöver köras baserat på vad användaren ändrat? **Nedan hittar du exemepel på lösningar, du ska fortfarande komma på själv**.

**Option 1: Explicit comparison**
```python
def determine_stages(config, baseline_config):
    stages = []
    
    if config['capex'] != baseline_config['capex']:
        stages.extend(['pre_dea', 'dea', 'extraction', 'post_dea'])
    elif config['dea'] != baseline_config['dea']:
        stages.extend(['dea', 'extraction', 'post_dea'])
    elif config['effkrav'] != baseline_config['effkrav']:
        stages.extend(['post_dea'])
    
    return stages
```

**Option 2: Stage dependency declarations**
```python
STAGE_DEPENDENCIES = {
    'pre_dea': ['capex_method', 'wacc', 'normvalues', 'lifetimes'],
    'dea': ['dea_method', 'dea_model_spec'],
    'post_dea': ['effkrav_truncation', 'effkrav_iqr', 'paverkbara_method']
}

def determine_stages(config, last_config):
    stages = []
    for stage, deps in STAGE_DEPENDENCIES.items():
        if any(config.get(d) != last_config.get(d) for d in deps):
            stages.append(stage)
            # Cascade: if pre_dea changes, dea and post_dea must run too
            if stage == 'pre_dea':
                stages.extend(['dea', 'extraction', 'post_dea'])
            elif stage == 'dea':
                stages.extend(['extraction', 'post_dea'])
    return list(dict.fromkeys(stages))  # Remove duplicates, preserve order
```

**Fråga till Opus:** Vilken approach är mest robust, skalbar för integrering av nya moduler (exempelvis SFA/Pystoned eller kvalitetsjustering) och underhållbar för dependency tracking?

### FRÅGA B: Error Handling i Pipeline
Om Stage 3 (DEA) failar (t.ex. infeasible model pga dålig modellspecifikation), vad händer?

Jag (användaren) rekomenderar att hela pipelinen stoppas och förklaring för vad som gick fel kommer upp.

### FRÅGA C: Concurrent Users och Baseline Sharing
Med baseline-first strategin:
- **Baseline data kan delas mellan användare** (read-only DataFrames)
- **Beräkningar sker per session** (session_state)
- **Ingen risk för kollisioner** (varje användare har egen session)

Håller du med att ladda baseline separat i varje session är bäst?
  - Fördelar: Enklast, ingen risk för concurrency issues
  - Nackdelar: Memory overhead (varje session = 3 DataFrames laddade)

---

## ARCHITECTURAL QUESTIONS

### 1. Pipeline Class Design
Hur ska pipeline-klassen designas?

**Option A: Single monolithic class**
```python
class RegumetricaPipeline:
    def __init__(self, config):
        self.config = config
        self.cache = {}
    
    def run(self):
        df_baseline = self.load_baseline()
        df_modified = self.apply_capex_method(df_baseline)
        df_efficiency = self.calculate_efficiency(df_modified)
        df_company = self.extract_company(df_efficiency)
        intaktsram = self.calculate_intaktsram(df_company)
        return intaktsram
```

**Option B: Stage-based classes**
```python
class BaselineLoader:
    def run(self) -> pd.DataFrame: ...

class PreDEAStage:
    def run(self, df_baseline, config) -> pd.DataFrame: ...

class DEAStage:
    def run(self, df_predea, config) -> pd.DataFrame: ...

# Pipeline orchestrator
class Pipeline:
    def __init__(self, stages):
        self.stages = stages
    
    def run(self, config):
        data = None
        for stage in self.stages:
            data = stage.run(data, config)
        return data
```

**Option C: Functional pipeline**
```python
def run_pipeline(config):
    df_baseline = load_baseline()
    df_modified = apply_capex_method(df_baseline, config['capex'])
    df_efficiency = calculate_efficiency(df_modified, config['dea'])
    df_company = extract_company(df_efficiency, config['user_dmu'])
    intaktsram = calculate_intaktsram(df_company, config['post_dea'])
    return intaktsram
```

**Fråga till Opus:** Vilken design passar bäst för skalbarhet och underhåll?

### 2. Config Structure
Hur ska case_definition struktureras för pipeline-arkitektur?

**Option A: Stage-based config**
```python
{
    'name': 'Case 1',
    'stages': {
        'pre_dea': {
            'method': 'wacc_scaling',
            'wacc': 0.05
        },
        'dea': {
            'method': 'dea',
            'model_spec': {
                'inputs': ['CAPEX', 'OPEXp'],
                'outputs': ['CU', 'MW', 'MWh'],
                'rts': 'VRS'
            }
        },
        'post_dea': {
            'effkrav_config': {...},
            'paverkbara_method': 'OPEX'
        }
    }
}
```

**Option B: Flat config (nuvarande stil)**
```python
{
    'name': 'Case 1',
    'parameters': {'wacc': 0.05},
    'modules': {'capex': 'wacc_scaling', 'efficiency': 'dea'},
    'module_configs': {'dea': {...}}
}
```

**Fråga till Opus:** Hur mappas UI-terminologi (Parameters/Variables/Modules) till pipeline config? Behöver vi en mapping layer?

### 3. Dependency Tracking
Hur identifierar systemet vilka stages som påverkas av en config-ändring?

**Option A: Explicit dependency declarations**
```python
STAGE_DEPENDENCIES = {
    'pre_dea': ['wacc', 'normvalues', 'lifetimes', 'kent_file'],
    'dea': ['pre_dea_result', 'dea_model_spec'],
    'post_dea': ['dea_result', 'effkrav_config', 'paverkbara_method']
}
```

**Option B: Hash-based automatic detection**
```python
def needs_rerun(stage_name, config, cache):
    current_hash = hash_stage_inputs(stage_name, config)
    cached_hash = cache.get(f'{stage_name}_hash')
    return current_hash != cached_hash
```

**Fråga till Opus:** Vilken approach är mest robust och underhållbar?

### 4. Batch Processing för Kent Pipeline
Kent_pipeline.py måste kunna hantera alla 148 företag samtidigt (för parameter-ändringar).

**Current state:** Funktioner tar ett företags capbase_a åt gången
**Needed state:** Funktioner tar capbase_a för alla 148 företag, använder id_network för att separera

**Fråga till Opus:** Hur ska refactoring av kent_pipeline.py göras för att stödja batch processing? Ska vi duplicera funktioner (single vs batch) eller göra en unified implementation?

---

## CONSTRAINTS

### Technical Stack
- **Framework:** Streamlit 1.50.0
- **Language:** Python 3.11+
- **Key libraries:** pandas, PuLP (för DEA), Firebase (auth)
- **Deployment:** Render.com Standard plan

### Data Constraints
- **Företag:** 148 svenska lokalnätföretag
- **Tidsperiod:** 2024-2027 (4 år)
- **Datasets:** 
  - **Data_modeller.xlsx** (148 rader, 12 kolumner) - CAPEX, OPEX, volymer för baseline
  - **EIs_DEA.xlsx** (148 rader, 7 kolumner) - Ei's officiella DEA-resultat med Effektivitet, Supereffektivitet, potential, Effkrav_proc
  - **capbase_a.parquet** (510k rader för alla företag, 33 kolumner) - Detaljerad anläggningsdata för CAPEX-beräkningar
  - **SDF/Löpande kostnader** (oklart format, behöver klargöras) - Opåverkbara kostnader per företag
  - **KENT-filer** (användaruppladdade Excel-filer) - Nya/ändrade komponenter för specifikt företag
  - **reconciliation_id_network_firm_dmu.csv** - Mappning mellan DMU, REId, och företagsnamn

### User Experience
- **UI must retain terminology:** Parameters, Variables, Modules (User Manual)
- **Flow:** Case Setup → Configuration → Execution → Results
- **Performance:** Beräkningar ska kännas snabba (<5 sekunder för enkel case)
- **Visual profile:** Professionell, mörkblå, teknisk men ej överväldigande
- **UI-filer**: Flera UI-filer finns tillgängliga men de har fel namn, men de kan tas inspiration från. Vi fokuserar på backend först.

### Scalability
- **New efficiency methods:** Måste kunna lägga till SFA och StoNED utan att ändra pipeline-logik
- **New parameters:** Måste kunna lägga till fler regulatoriska parametrar
- **New stages:** Pipeline-design ska tillåta insertion av nya stages (t.ex. kvalitetsjustering)

---

## DELIVERABLES REQUESTED FROM OPUS

### 1. Architecture Document
Detaljerad beskrivning av rekommenderad pipeline-arkitektur med:
- Class diagram eller funktionell design
- Stage interfaces (input/output contracts)
- Config structure och mapping till UI
- Dependency tracking mechanism
- Caching strategy

### 2. Answers to Design Questions
Konkreta svar på frågor

### 3. Migration Strategy
Användaren vill att vi skapar nya filer för att förenkla nya namn och minska risk för att vi försöker anpassa systemet för att funka hela tiden. Användaren vill ENDAST att allt ska funka i slutändan. MYCKET kan dock direkt återanvändas med små namnförändringar.

### 4. Naming Conventions
Konsolidering av namn för:
- Tydligare namn för vad data faktiskt är
- DataFrames (scope-suffix: `_all_companies` vs `_single_company`)
- CAPEX-funktioner (separera DEA-capex från periodsumma-capex)
- Parameters vs Variables vs Modules
- Samma data som används i flera ställen

### 5. File Structure Recommendation
Förslag på ny filstruktur som stödjer pipeline-arkitektur.
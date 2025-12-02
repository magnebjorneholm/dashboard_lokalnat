# Regumetrica – Arkitektur- och pipelineförslag

*(Anpassat till att jag inte ser de faktiska .py-filerna, bara arkitektur- och dataguiderna.)*

---

## 1. Sammanfattning – kärnrekommendationer

### 1. Inför en tydlig Pipeline/Stage-modell

Dela upp Regumetrica i tre huvudsteg:
**Pre-DEA → DEA → Post-DEA** (Effkrav + Påverkbara + Intäktsram).

Varje steg implementeras som en **Stage** med:
- namn/id
- explicita inputs (nycklar i en kontext)
- explicita outputs (nycklar i kontexten)
- `run(context)` som är ren deterministisk logik.

### 2. Beroendehantering på Stage-nivå, inte per variabel

Behåll idén med ett registry, men låt registryt hantera **steg** (t.ex. `pre_dea.preprocess`, `kent.compute_capcost`, `post_dea.build_intaktsram`) snarare än enskilda kolumner.

Låt en enkel **DAG/topologisk sort** styra körordningen. Detta gör TOTEX-beroendet mot `Kapitalkostnad_Total` transparent: Post-DEA/TOTEX-steget får ett explicit beroende mot KENT-steget.

### 3. Strukturerad felhantering

Inför **domänspecifika undantag**, t.ex. `DataValidationError`, `StageExecutionError`, `DomainConsistencyError`.

Alla stages returnerar även en lista med **issues** (warnings/errors) vid t.ex. saknade tidskoder, mismatch mellan periodsummor och årssummor, osv.

### 4. Baseline som read-only, per-case overrides i en CaseContext

Ladda alla baseline-datasets (`Data_modeller`, `capbase_a`, `SDF`, `EIs_DEA`, `reconciliation`) en gång vid start i ett **BaselineData-objekt**.

För varje körning skapas en **CaseContext**:
- referens till `BaselineData`
- en per-case kopia av de DataFrames som faktiskt modifieras (särskilt CAPEX/DEA-input och SDF-värden för det inloggade företaget).

### 5. Bekräfta "Baseline-first" men gör den explicit

**Ja**, baseline-first-strategin är rimlig: alla case bygger ovanpå Ei:s baseline, och WACC/parametrar/KENT ger justeringar relativt denna.

Gör den tydlig i arkitekturen genom:
- ett `BaselineData`-objekt
- kontrakt som säger att Post-DEA alltid tar in uppdaterade värden för just det case som körs.

### 6. KENT: batch-runner + single-DMU-runner

Implementera KENT som en separat "sub-pipeline" med **två lägen**:
- **Batch** (148 DMU) för ändring av normvärden/livslängder/WACC.
- **Single DMU** (metod 4) där KENT-filen för ett företag läses in, ersätter komponenterna och körs genom steg 1–4 och sedan 5–8.

### 7. Konfigurationsstruktur

**Pydantic/YAML-baserad konfiguration** med tre nivåer:
- `GlobalConfig` (filvägar, miljö)
- `ModelConfig` (Pre-DEA, DEA, Post-DEA, KENT)
- `CaseConfig` (user_dmu, id_network, metodval, OPEX/TOTEX).

---

## 2. Svar på varje fråga (med motivering och kodskisser)

### FRÅGA A: Dependency Tracking Implementation

#### Problem idag (av det vi ser):
- Det finns ett `producer_registry` och en `variable_resolver` som försöker lösa beroenden mellan producers och variabler.
- Samtidigt är pipelineflödet redan relativt fast: Pre-DEA → DEA → Post-DEA, och inom KENT pipeline 1–4 → 5–8.

#### Förslag: Stage-baserat beroendesystem ovanpå registryt

**1. Abstrahera producers till Stages**

Definiera en `Stage`-klass som ersätter "ad hoc"-producenter för pipeline-delar:

```python
from dataclasses import dataclass, field
from typing import Callable, Set, Dict, Any

@dataclass
class Stage:
    id: str                      # t.ex. "pre_dea.prepare_input"
    requires: Set[str]           # t.ex. {"df_data_modeller", "case_config"}
    provides: Set[str]           # t.ex. {"df_predea", "predea_meta"}
    fn: Callable[[Dict[str, Any]], None]  # muterar context med outputs
```

**2. Context som single source of truth**

```python
Context = Dict[str, Any]  # enklast; kan bytas mot dataclass senare
```

**3. StageRegistry + enkel topologisk sort**

```python
class StageRegistry:
    def __init__(self):
        self._stages: Dict[str, Stage] = {}

    def register(self, stage: Stage):
        self._stages[stage.id] = stage

    def get(self, stage_id: str) -> Stage:
        return self._stages[stage_id]
```

**4. Dependency resolution per Stage, inte per kolumn**

När du vill producera `intaktsram.case` definieras en **target sequence**:
```python
["pre_dea.prepare_input", "dea.run", "post_dea.compute_effkrav", 
 "post_dea.apply_paverkbara", "post_dea.assemble_intaktsram"]
```

**TOTEX-specifika beroenden:**
- Om Post-DEA körs i TOTEX-läge ska dess stage `post_dea.apply_paverkbara` inkludera `{"capcost_case"}` i `requires`.
- Då syns tydligt att KENT-steget (`kent.compute_capcost`) måste köras före Post-DEA/TOTEX.

**5. Integration med befintlig producer_registry**

`producer_registry` kan bli en teknisk detalj för att bygga `Stage`-objekt:
- varje "producer" motsvarar en stage
- `variable_resolver` kan användas för generisk DAG-lösning, men på Stage-nivå snarare än hundratals variabler.

#### Motivering

- Du får mer **förklarbara beroenden** (få stora noder i DAG:en istället för många små).
- **Debuggning blir enklare**: du kan logga "Stage X startar, Stage Y misslyckades" istället av "producer Z kunde inte hitta variabel Q".
- Kravet på att TOTEX ska bero på `Kapitalkostnad_Total` blir **explicit** i stagekontrakten, inte dold i intern logik i Post-DEA.

---

### FRÅGA B: Error Handling i Pipeline

#### Princip: Fail fast på hårda databasfel, men mjukt på domän-"warnings"

**1. Typ av fel**

- **DataLoadingError**
  - Fil saknas, går inte att läsa Excel/Parquet.

- **DataValidationError**
  - T.ex. CAPEX != Avskrivning + Avkastning för `Data_modeller`.
  - `time_from` saknas utan att `time_from_missing` är satt.
  - TOTEX negativt, osv.

- **DomainConsistencyError**
  - `reconciliation` saknar matchning mellan REId och id_network.

- **StageExecutionError**
  - Oväntade Python-fel i själva beräkningslogiken (IndexError, etc).

**2. Issues-objekt per Stage**

Varje stage returnerar både sin output och en lista med "issues":

```python
from enum import Enum

class IssueLevel(str, Enum):
    WARNING = "warning"
    ERROR = "error"

@dataclass
class Issue:
    level: IssueLevel
    stage_id: str
    code: str       # t.ex. "MISSING_TIME_FROM"
    message: str
    context: dict   # t.ex. {"id_network": 886}
```

**Stage-funktion:**

```python
def run_pre_dea(context: Context):
    issues: list[Issue] = []
    df = context["df_data_modeller"]

    # exempel på validering
    bad = df[df["CAPEX"] != df["Avskrivning"] + df["Avkastning"]]
    if not bad.empty:
        issues.append(Issue(
            level=IssueLevel.ERROR,
            stage_id="pre_dea.prepare_input",
            code="CAPEX_MISMATCH",
            message="CAPEX != Avskrivning + Avkastning för vissa rader",
            context={"rows": bad.index.tolist()}
        ))

    context["df_predea"] = df  # ev efter transform
    context.setdefault("issues", []).extend(issues)
```

**Pipeline-runnern kan sedan:**
- stoppa om det finns `IssueLevel.ERROR`
- visa warnings i UI men ändå returnera resultat.

**3. Var validering bör ske** (kopplat till dataguiderna)

- **Vid dataladdning** (`Data_modeller`, `capbase_a`, `SDF`, `reconciliation`, `EIs_DEA`):
  - kontrollera strukturer som anges i guiden (antal rader, obligatoriska kolumner, kritiska samband).

- **I KENT-pipeline steg 5–8**:
  - t.ex. att `nuav_2022` inte är negativ (utom vid utrangeringar).

- **I Post-DEA**:
  - kontrollera att summan av årsdata = periodsumma för påverkbara och opåverkbara.

**4. Mapping mot frontend**

För varje feltyp definieras ett **användarvänligt budskap**:
> "Din KENT-fil saknar årtal för komponenter X, Y – kontrollera kolumnen 'Ursprungligen tagen i bruk'."

Eftersom beräkningarna gärna ska matcha Excel exakt, är det bättre att **stoppa helt** än att gissa vid allvarliga avvikelser.

---

### FRÅGA C: Concurrent Users och Baseline Sharing

#### Antaganden:
- `user_dmu` kommer från Firebase och är konstant under sessionen.
- 1:1 mellan företag och `id_network`.
- KENT-upload ersätter alla komponenter för företaget.
- Körning <10 sekunder är ok.

**1. BaselineData – shared, read-only**

```python
@dataclass(frozen=True)
class BaselineData:
    df_data_modeller: pd.DataFrame
    df_capbase_a: pd.DataFrame
    df_sdf_ir: pd.DataFrame
    df_sdf_paverkbara: pd.DataFrame
    df_dea_baseline: pd.DataFrame
    df_reconciliation: pd.DataFrame
```

Laddas **en gång** vid uppstart från:
- `Data_modeller.xlsx`
- `capbase_a.parquet`
- `Löpande kostnader från SDF 2024-27.xlsx` (IR + Påverkbara)
- `EIs_DEA.xlsx`
- `reconciliation.csv`.

**2. CaseContext – per session / per körning**

```python
@dataclass
class CaseContext:
    baseline: BaselineData
    case_config: "CaseConfig"
    # kopior eller vyer som får muteras
    df_predea: pd.DataFrame | None = None
    df_dea: pd.DataFrame | None = None
    df_kent_capcost: pd.DataFrame | None = None
    df_paverkbara_case: pd.DataFrame | None = None
    df_intaktsram_case: pd.DataFrame | None = None
    issues: list[Issue] = field(default_factory=list)
```

Vid körning:
- hämtas de 148 raderna från baseline.
- För det inloggade företaget görs en **copy-on-write**:
  - CAPEX justeras via WACC/parametrar/KENT.
  - Påverkbara efter effkrav skrivs bara i `df_paverkbara_case` för just detta företag.

**3. Hantering av KENT för många användare**

**Scenario 1: Endast inloggat företag laddar KENT-fil, inga parameterändringar**
- kör steg 1–4 på KENT-filen för `id_network = case.id_network`
- ersätt bara komponenterna för detta `id_network` i en kopierad version av `baseline-df_capbase_a`
- kör steg 5–8 för alla 148 på den kopierade versionen.

**Scenario 2: KENT + parameterändringar**
- samma som ovan men med justerade WACC/livslängder/normvärden i steg 5–8.

I båda fallen ligger `BaselineData` orörd → **concurrency-säkert**.

**4. Prestanda (<10 s)**

`capbase_a` (~510k rader) * 148 företag * 8 tidskoder kan bli tungt, men <10 s bör vara rimligt i Python om:
- du använder **vektoriserad Pandas/Numpy**, inte loops.
- du **cache:ar resultat** per kombination av (WACC, livslängder, normvärden) för att slippa köra om allt för identiska scenarion.

---

## Architectural Question 1: Pipeline Class Design

**Mål:** En central klass som kör hela kedjan för ett case (ett inloggat företag + valda metoder).

```python
class RegumetricaPipeline:
    def __init__(self, registry: StageRegistry, baseline: BaselineData):
        self._registry = registry
        self._baseline = baseline

    def run_case(self, case_config: "CaseConfig") -> "PipelineResult":
        ctx = {"baseline": self._baseline, "case_config": case_config}
        # Kör i definierad ordning (eller låt registry göra DAG-lösning)
        for stage_id in [
            "pre_dea.prepare_input",
            "dea.run",
            "post_dea.compute_effkrav",
            "post_dea.apply_paverkbara",
            "post_dea.assemble_intaktsram",
        ]:
            stage = self._registry.get(stage_id)
            self._run_stage(stage, ctx)

        return PipelineResult.from_context(ctx)

    def _run_stage(self, stage: Stage, ctx: Context):
        missing = stage.requires - ctx.keys()
        if missing:
            raise StageExecutionError(
                f"Stage {stage.id} saknar inputs: {missing}"
            )
        stage.fn(ctx)
```

**PipelineResult** kan innehålla:
- `df_intaktsram_case`
- `df_paverkbara_case`
- ev. `df_dea_case` och metadata.

---

## Architectural Question 2: Config Structure

### Separera global, modell och case-konfiguration

```python
from pydantic import BaseModel
from typing import Literal, List, Optional

class PreDeaConfig(BaseModel):
    capex_method: Literal["baseline", "wacc_scaling", "parameter_change", "kent"]
    wacc: Optional[float] = None
    apply_lifetime_adjustments: bool = False
    apply_normvalue_adjustments: bool = False

class DeaConfig(BaseModel):
    inputs: List[str]          # t.ex. ["CAPEX", "OPEXp"] eller ["TOTEX"]
    outputs: List[str]         # ["CU", "MW", "NS", "MWhl", "MWhh"]
    rts: Literal["CRS", "VRS"] # returns to scale

class PostDeaConfig(BaseModel):
    effkrav_method: Literal["baseline", "from_potential"]
    cost_method: Literal["OPEX", "TOTEX"]

class CaseConfig(BaseModel):
    user_dmu: int
    id_network: int
    scenario_name: str
    pre_dea: PreDeaConfig
    dea: DeaConfig
    post_dea: PostDeaConfig
```

**GlobalConfig** (t.ex. från YAML):

```yaml
data:
  data_modeller_path: "data/Data_modeller.xlsx"
  capbase_path: "data/capbase_a.parquet"
  sdf_path: "data/Löpande kostnader från SDF 2024-27.xlsx"
  dea_baseline_path: "data/EIs_DEA.xlsx"
  reconciliation_path: "data/reconciliation_id_network_firm_dmu.csv"

defaults:
  pre_dea:
    capex_method: "baseline"
  dea:
    inputs: ["CAPEX", "OPEXp"]
    outputs: ["CU", "MW", "NS", "MWhl", "MWhh"]
    rts: "CRS"
  post_dea:
    effkrav_method: "from_potential"
    cost_method: "OPEX"
```

#### Motivering

Strukturen följer exakt de koncept som beskrivs i funktionsdokumentet:
- 4 Pre-DEA-metoder, DEA-modell, och Post-DEA med OPEX/TOTEX.
- Den är **stabil över tid** även om intern kod ändras.

---

## Architectural Question 3: Dependency Tracking (fördjupning)

### Nyckelberoenden att få rätt:

1. **df_predea** beror på:
   - `df_data_modeller` (baseline)
   - ev. `df_kent_capcost_2024` om du väljer TOTEX redan i Pre-DEA (om du använder TOTEX = CAPEX + OPEXp).

2. **df_dea** beror på:
   - `df_predea`
   - DEA-modellkonfiguration.

3. **df_paverkbara_case** beror på:
   - `df_sdf_paverkbara` (baseline)
   - `effkrav_proc_case`
   - `Kapitalkostnad_Total_case` vid TOTEX-metod.

4. **df_intaktsram_case** beror på:
   - `df_kent_capcost_case`
   - `df_paverkbara_case`
   - baseline-värden för opåverkbara, flex, avbrott, avdrag.

Alla dessa kan skrivas som **Stage-kontrakt** (se sektion 6).

### Implementation:

- Registrera beroenden per Stage i registryt.
- Låt `case_definition_manager` välja vilken variant av t.ex. `pre_dea.prepare_input` som ska användas beroende på `capex_method`.
- `variable_resolver` kan ersättas av ett enklare system som:
  - bygger en DAG med edges `requires → provides`
  - gör topologisk sort (Kahn's algorithm) för att hitta körordning.

---

## Architectural Question 4: Batch Processing för Kent Pipeline

**Mål:**

Stödja 2–3 olika körlägen utan att duplicera logik:
1. **Baseline/Parameter-ändring** (alla 148)
2. **KENT full** (1 företag)
3. **KENT + parametrar** (1 företag + ändrade livslängder/normvärden/WACC)

Enligt guiderna ska steg 5–8 alltid producera kapitalkostnader uppdelade på avskrivning/avkastning per `id_network` och tidskod, med aggregat för 2024 och perioden 2024–2027.

### Förslag: KentRunner

```python
class KentRunner:
    def __init__(self, baseline: BaselineData):
        self._baseline = baseline

    def run_for_all(self, params: "KentParams") -> pd.DataFrame:
        """
        Kör steg 5-8 för alla 148 företag.
        Används vid ändring av normvärden/livslängder/WACC.
        """
        df_capbase = self._baseline.df_capbase_a.copy()
        df_prepared = prep_capbase(df_capbase, params)
        df_with_ages = calculate_ages_and_nuav(df_prepared, params)
        dep = calculate_depreciation(df_with_ages, params)
        ret = calculate_returns(df_with_ages, params)
        capcost = compile_capcost(dep, ret)   # 148 * tidskoder
        return capcost

    def run_for_single_dmu(self, dmu_id: int, params: "KentParams",
                           kent_file_df: pd.DataFrame) -> pd.DataFrame:
        """
        Kör steg 1-4 på KENT-fil (1 företag), ersätter komponenter, sedan 5-8.
        """
        df_capbase = self._baseline.df_capbase_a.copy()
        df_capbase = replace_firm_components(df_capbase, dmu_id, kent_file_df)
        df_prepared = prep_capbase(df_capbase, params)
        df_with_ages = calculate_ages_and_nuav(df_prepared, params)
        dep = calculate_depreciation(df_with_ages, params)
        ret = calculate_returns(df_with_ages, params)
        capcost = compile_capcost(dep, ret)
        return capcost[capcost["dmu_id"] == dmu_id]
```

Denna struktur följer direkt den beräkningskedja för steg 5–8 som beskrivs (ålder, NUAV, avskrivningar, avkastning, sammanställning till `capcost_sum`).

---

## Bekräfta eller ifrågasätt Baseline-First Strategy

**Baseline-first =**
- läs in Ei:s baseline (`Data_modeller`, `SDF`, `EIs_DEA`),
- gör alla beräkningar som justeringar jämfört med den.

### Bedömning:

**Starkt att behålla:**
- Säkerställer att du alltid kan återskapa Ei:s ursprungliga intäktsram exakt.
- Gör det tydligt vilka effekter som beror på metodval (OPEX/TOTEX, WACC, KENT).
- Underlättar regressionstester och jämförelser.

**Men: gör den explicit**
- Baseline bör finnas som eget objekt (`BaselineData`) och inte blandas ihop med case-specifika DataFrames.
- Alla stage-kontrakt bör vara skrivna i stil med:
  > "Tar in baseline + case overrides, returnerar case-resultat".

**Så: ja, bekräfta baseline-first, men formaliserad i arkitekturen.**

---

## 3. Rekommenderad filstruktur

### Utgångspunkt från nuvarande struktur:

```
core/
  bootstrap_registry.py
  case_definition_manager.py
  producer_registry.py
  variable_resolver.py
  validation_framework.py
  results_manager.py

producers/
  baseline/
    baseline_loaders.py
    reference_dea_loader.py
  wacc/
    wacc_producers.py
  kapitalkostnad/
    capex_producers.py
    kent_pipeline.py
    capbase_prep.py
    parameter_adjustments.py
  effektivitet/
    dea_producer.py
    dea_model.py
  intaktsram/
    intaktsram_assembly.py
```

### Föreslagen omstrukturering:

```
regumetrica/
├── core/
│   ├── pipeline.py             # Stage, StageRegistry, RegumetricaPipeline
│   ├── context.py              # BaselineData, CaseContext, PipelineResult
│   ├── errors.py               # DataLoadingError, DataValidationError, ...
│   ├── validation.py           # Generella validerare, shared
│   └── logging.py              # Enhetlig logging
│
├── config/
│   ├── models.py               # GlobalConfig, CaseConfig, PreDeaConfig, ...
│   └── loader.py               # Läs YAML/ENV → Pydantic
│
├── data_access/
│   ├── load_baseline.py        # läser Data_modeller, capbase_a, SDF, DEA, reconciliation
│   └── io_utils.py
│
├── pipelines/
│   ├── pre_dea.py              # Stage-implementationer för Pre-DEA
│   ├── dea.py                  # Stage-implementationer för DEA
│   ├── post_dea.py             # Stage-implementationer för effkrav, påverkbara, intäktsram
│   └── kent.py                 # KentRunner och Kent-stages
│
├── domain/
│   ├── dea_models.py           # DEA model spec, ev. wrapper runt dea_model.py
│   ├── capcost_models.py       # dataklasser för capex/capcost
│   └── paverkbara_models.py
│
└── legacy/
    ├── baseline_loaders.py     # importeras in i pipelines/pre_dea.py
    ├── kent_pipeline.py        # bryts upp men ligger kvar under migration
    └── intaktsram_dekomposition.py
```

På sikt kan `legacy/`-koden rensas när `pipelines/`-modulerna är stabila.

`producers/`-namngivningen blir mindre viktig när Stage-konceptet tar över.

---

## 4. Namnkonventioner

### 4.1 Kod

- **Moduler**: `snake_case.py` (t.ex. `pre_dea.py`, `kent.py`).
- **Klasser**: `PascalCase` (`RegumetricaPipeline`, `BaselineData`).
- **Funktioner**: `snake_case` med verb (`run_dea`, `calculate_returns`).
- **Stages**: `"<område>.<verb>_<objekt>"`, t.ex.:
  - `pre_dea.prepare_input`
  - `dea.run`
  - `post_dea.apply_paverkbara`
  - `post_dea.assemble_intaktsram`

### 4.2 DataFrames och kolumner

**DataFrames:**
- `df_data_modeller`, `df_capbase_a`, `df_sdf_ir`, `df_sdf_paverkbara`, `df_dea`, `df_predea`, `df_kent_capcost`, `df_intaktsram`.

**Kolumner:**
- `DMU`, `REId`, `CAPEX`, `OPEXp`, `TOTEX` (ej TOTEXp).
- **Outputs från DEA**: `efficiency`, `super_efficiency`, `theta`, `is_outlier`, `potential`.
- **Påverkbara**: `Paverkbara_Target` som periodsumma, `Paverkbara_Efter_Avdrag_2024` etc om du expanderar årsvis.
- **Kapitalkostnad**: `dep_ord`, `dep_tail`, `return_ord`, `return_tail`, `capcost_sum`, `capcost_2024`, `capcost_period`.
- **Intäktsram**: `Intaktsram_Total`, `Avskrivningar`, `Avkastning`, `Opaverkbara_Kostnader`, `Flexibilitet`, `Avbrott`, `Avdrag_Statligt_Stöd`, osv.

---

## 5. Migrationsplan i faser

### Fas 0 – Förberedelser

**Åtgärder:**
- Skapa `BaselineData` och funktion för att ladda allt från Excel/Parquet/CSV.
- Lägg till Pydantic-modeller för `GlobalConfig` och `CaseConfig`.

**Definition of done:**
- Du kan i en REPL skapa `BaselineData` och ett `CaseConfig`-objekt för ett företag.

---

### Fas 1 – Stage/Pipeline-skelett

**Åtgärder:**
- Implementera `Stage`, `StageRegistry`, `RegumetricaPipeline` och `CaseContext`.
- Registrera stub-stages:
  - `pre_dea.prepare_input` (anropar nuvarande `baseline_loaders.py`).
  - `dea.run` (wrappar `dea_model.py`).
  - `post_dea.compute_effkrav`, `post_dea.apply_paverkbara`, `post_dea.assemble_intaktsram` som tomma placeholders.

**Definition of done:**
- En enkel pipeline som tar `Data_modeller` och `EIs_DEA` och returnerar baseline-intäktsram för ett företag (utan KENT/logik – bara baseline).

---

### Fas 2 – Pre-DEA på riktigt

**Åtgärder:**
- Anpassa `baseline_loaders.py` och WACC-/parameterlogiken enligt Funktionsdokumentet:
  - införa **fyra metoder** (Baseline, WACC-skalning, Parameter-ändring, KENT).
- `pre_dea.prepare_input`:
  - läs `Data_modeller`
  - applicera vald CAPEX-metod
  - bygg `df_predea` (148 rader med DMU, CAPEX, OPEXp, volymer).

**Definition of done:**
- Byta mellan de fyra Pre-DEA-metoderna ska ge olika `df_predea`, men DEA och Post-DEA kör fortfarande baseline-logik.

---

### Fas 3 – DEA-integration

**Åtgärder:**
- Gör en ren wrapper runt `dea_model.py` som tar `df_predea` + modellkonfiguration och returnerar `df_dea`.
- Lägg till validering för outputs (`efficiency` inom [0,1], osv.).

**Definition of done:**
- Samma DEA-resultat som Ei:s baseline när `df_predea` = baseline-`Data_modeller`.

---

### Fas 4 – Post-DEA + Påverkbara

**Åtgärder:**
- Implementera `post_dea.compute_effkrav`:
  - extrahera `potential` och `is_outlier` för `user_dmu`
  - beräkna `effkrav_proc` enligt regeln: outliers får fast 1%, annars funktion av potential.
- Implementera `post_dea.apply_paverkbara`:
  - läs SDF "Påverkbara"
  - applicera OPEX- eller TOTEX-formeln (med TOTEX = CAPEX + OPEXp när relevant).

**Definition of done:**
- Du får en `Paverkbara_Target` som matchar Excel-modellen för baseline-fall.

---

### Fas 5 – KENT-pipeline

**Åtgärder:**
- Implementera `KentRunner` och stages:
  - `kent.compute_capcost_baseline` (alla 148)
  - `kent.compute_capcost_single` (KENT-fil för 1 företag).
- Koppla in TOTEX-beroendet:
  - `post_dea.apply_paverkbara` kräver `capcost_case` när `cost_method == "TOTEX"`.

**Definition of done:**
- KENT-scenarier ger Excel-identisk kapitalkostnad 2024 och 2024–2027 för testföretag.

---

### Fas 6 – Städa och avveckla legacy

**Åtgärder:**
- Flytta kvarvarande domänlogik från `legacy`-moduler in i `pipelines`/domänlager.
- Rensa bort överflödigt `producer_registry`/`variable_resolver`-bruk om Stage-systemet täcker allt.

---

## 6. Stage-kontrakt (input/output per stage)

Här ger jag förslag på centrala kontrakt. De kan konkretiseras ytterligare när du ser den faktiska koden.

### 6.1 load_baseline_data (data_access)

**Input:**
- `GlobalConfig` (stigar till filer).

**Output (till BaselineData):**
- `df_data_modeller` (148 rader, DMU, REId, CAPEX, OPEXp, volymer).
- `df_capbase_a` (~510k rader komponentdata).
- `df_sdf_ir` (IR 2024–2027, per REId).
- `df_sdf_paverkbara` ("Påverkbara"-sheet).
- `df_dea_baseline` (EIs_DEA).
- `df_reconciliation` (id_network → DMU).

---

### 6.2 pre_dea.prepare_input

**Requires:**
- `baseline.df_data_modeller`
- `case_config.pre_dea`

**Provides:**
- `df_predea` (148 rader)
- `predea_meta` (t.ex. vilka antaganden som användes)

**df_predea-kolumner:**
- `DMU`, `REId`, `Företag`
- `CAPEX` (justerat om WACC/KENT/parametrar valts)
- `OPEXp`
- `TOTEX` (beräknat som CAPEX + OPEXp).
- `CU`, `MW`, `NS`, `MWhl`, `MWhh`.

---

### 6.3 dea.run

**Requires:**
- `df_predea`
- `case_config.dea`

**Provides:**
- `df_dea` (148 rader med DEA-resultat)

**df_dea-kolumner:**
- `DMU`, `REId`, `Företag`
- `efficiency`, `super_efficiency`, `theta`, `is_outlier`, `potential`.

---

### 6.4 post_dea.compute_effkrav

**Requires:**
- `df_dea`
- `case_config.user_dmu`
- `case_config.post_dea.effkrav_method`

**Provides:**
- `effkrav_proc_case` (float)
- `is_outlier_case` (bool)

**Logik:**
- om `is_outlier_case` → effkrav = 1 %
- annars beräkna från `potential`.

---

### 6.5 kent.compute_capcost_case (via KentRunner)

**Requires:**
- `baseline.df_capbase_a`
- ev. `kent_file_df` (om KENT-metod)
- `case_config.pre_dea` (parametrar/WACC)
- `case_config.user_dmu` / `id_network`

**Provides:**
- `df_kent_capcost_case`
- `capcost_2024_case` (float)
- `capcost_period_case` (float)

`df_kent_capcost_case` har kolumnerna `time`, `dep_ord`, `dep_tail`, `return_ord`, `return_tail`, `capcost_sum`; dessa aggregeras till års-/periodvärden.

---

### 6.6 post_dea.apply_paverkbara

**Requires:**
- `baseline.df_sdf_paverkbara`
- `effkrav_proc_case`
- `case_config.post_dea.cost_method`
- `capcost_period_case` (om TOTEX)
- ev. `OPEXp_case` (från `Data_modeller`).

**Provides:**
- `df_paverkbara_case` (årsvärden 2024–2027 och periodsumma `Paverkbara_Target`)

**Logik** följer OPEX/TOTEX-formlerna:
- `Startvärde`
- `Årlig_Justering`
- `Årsbas_Effkrav`
- `Årligt_Avdrag_t`
- `Kumulativt_Avdrag_t`
- `Påverkbara_Efter_Avdrag_t`
- `Paverkbara_Periodsumma`.

---

### 6.7 post_dea.assemble_intaktsram

**Requires:**
- `df_kent_capcost_case` eller direkt `Avskrivningar`, `Avkastning`
- `df_paverkbara_case` (`Paverkbara_Periodsumma`)
- `baseline.df_sdf_ir` (Opåverkbara, Flex, Avbrott, Avdrag)

**Provides:**
- `df_intaktsram_case` med:
  - `Kapitalkostnad_Total`
  - `Påverkbara_Periodsumma`
  - `Opåverkbara_Kostnader`
  - `Flexibilitetstjänster`
  - `Avbrottsersättning_12_24h`
  - `Avdrag_Statligt_Stöd`
  - `Intaktsram_Total`.

---

*End of document*

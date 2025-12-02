# BERÄKNINGSFLÖDE - KONCEPTUELL GUIDE

**Version:** 1.0  
**Syfte:** Beskriva hela beräkningsflödet från data till intäktsram på konceptuell nivå

---

## ÖVERSIKT

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            BERÄKNINGSFLÖDET                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐                 │
│  │   PRE-DEA   │ ───► │     DEA     │ ───► │  POST-DEA   │                 │
│  │  148 → 148  │      │  148 → 148  │      │   1 → 1     │                 │
│  └─────────────┘      └─────────────┘      └─────────────┘                 │
│                                                                             │
│  Förbered data        Beräkna              Beräkna intäktsram              │
│  för jämförelse       effektivitet         för ETT företag                 │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 1. PRE-DEA

### Syfte
Förbereda en DataFrame med 148 rader (alla företag) där CAPEX kan vara modifierad enligt olika metoder. Målet är att kunna testa "vad händer med effektiviteten om kapitalkostnaden beräknas annorlunda?"

### Dataflöde

```
Data_modeller.xlsx (148 rader)
        │
        ▼
┌───────────────────────────────────────────────────────────┐
│                    VÄLJ METOD                              │
│                                                            │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌──────┐ │
│  │  Baseline  │  │   WACC-    │  │  Capbase-  │  │ KENT │ │
│  │            │  │  skalning  │  │   kedja    │  │ full │ │
│  └────────────┘  └────────────┘  └────────────┘  └──────┘ │
│                                                            │
└───────────────────────────────────────────────────────────┘
        │
        ▼
DataFrame (148 rader) → DEA
```

### De fyra metoderna

| # | Metod | Beskrivning | Scope | Kombineras med WACC? |
|---|-------|-------------|-------|----------------------|
| 1 | **Baseline** | Använd Data_modeller utan ändringar | - | Nej |
| 2 | **WACC-skalning** | Skala Avkastning-kolumnen proportionellt | Alla 148 | Ja (är WACC) |
| 3 | **Capbase-kedja** | Kör beräkningskedja 5-8 på capbase_a | Alla 148 | Ja (steg 7) |
| 4 | **KENT-full** | Läs KENT-fil → steg 1-4 → ersätt i capbase_a → steg 5-8 | 1 + alla 148 | Ja (steg 7) |

### Detaljerad beskrivning per metod

#### Metod 1: Baseline
- **Input:** Data_modeller.xlsx
- **Process:** Ingen - använd som den är
- **Output:** 148 rader med originalvärden
- **Användning:** Referens, eller när användaren inte vill ändra CAPEX

#### Metod 2: WACC-skalning
- **Input:** Data_modeller.xlsx + ny WACC
- **Process:** 
  - Beräkna skalningsfaktor = ny_wacc / baseline_wacc
  - Skala endast Avkastning-kolumnen (INTE Avskrivning)
  - Räkna om CAPEX = Avskrivning + ny Avkastning
- **Output:** 148 rader med skalad CAPEX
- **Användning:** Snabb känslighetanalys för ränteförändringar

#### Metod 3: Capbase-kedja
- **Input:** capbase_a.parquet (510k rader för alla 148 företag) + parametrar
- **Process:**
  - Applicera normvärdejusteringar (valfritt)
  - Applicera livslängdsjusteringar (valfritt)
  - Kör steg 5: Beräkna åldrar och NUAV
  - Kör steg 6: Beräkna avskrivningar
  - Kör steg 7: Beräkna avkastning (med WACC som parameter)
  - Kör steg 8: Sammanställ kapitalkostnad
  - Aggregera till DMU-nivå
- **Output:** 148 rader med omberäknad CAPEX
- **Användning:** Testa ändrade normvärden/livslängder för ALLA företag

#### Metod 4: KENT-full
- **Input:** KENT-fil (1 företag) + capbase_a.parquet + parametrar
- **Process:**
  - Kör steg 1-4: Läs KENT-fil → bygg capbase_a för 1 företag
  - Ersätt det företagets data i den fullständiga capbase_a
  - Kör steg 5-8 på ALLA 148 företag (som metod 3)
  - Aggregera till DMU-nivå
- **Output:** 148 rader (1 från KENT, 147 från baseline eller omberäknade)
- **Användning:** Företag vill testa sin egen inrapporterade data

### Kombinationer

WACC är en **parameter** i steg 7 (calculate_returns). Därför:

| Kombination | Möjlig? | Beskrivning |
|-------------|---------|-------------|
| Baseline + ny WACC | Ja, men → metod 2 | Blir WACC-skalning |
| Capbase-kedja + ny WACC | Ja | Steg 7 använder ny WACC |
| KENT-full + ny WACC | Ja | Steg 7 använder ny WACC |
| Capbase-kedja + normvärden | Ja | Appliceras före steg 5 |
| KENT-full + normvärden | Ja | Appliceras på hela capbase_a |

### Data som behövs

| Dataset | Innehåll | Scope | Används av |
|---------|----------|-------|------------|
| Data_modeller.xlsx | DMU, CAPEX, OPEX, volymer | 148 rader | Baseline, WACC-skalning, DEA |
| capbase_a.parquet | Komponentdata | 510k rader (alla 148 via id_network) | Capbase-kedja, KENT-full |
| KENT-fil | Inrapporterad kapitalbas | 1 företag | KENT-full |
| reconciliation.csv | id_network → DMU mapping | 148 företag | Aggregering |

### Nuvarande status vs korrekt beteende

| Steg | Nuvarande | Korrekt | Fil med korrekt kod |
|------|-----------|---------|---------------------|
| Ladda baseline | ✅ Fungerar | 148 rader | baseline_loaders.py |
| WACC-skalning | ✅ Korrekt i github-synk | Skala endast Avkastning | capex_producers.py (github) |
| Steg 1-4 (KENT → capbase_a) | ✅ Komplett | Bygg capbase_a | capbase_prep.py (github) |
| Steg 5-8 | ✅ Komplett | Beräkna kapitalkostnad | beräkningskedja.py (github) |
| Aggregering id_network → DMU | ❌ Saknas | Summera per DMU | Behöver skapas |
| Orchestrator | ❌ Saknas | Välj metod, koordinera | Behöver skapas |

---

## 2. DEA

### Syfte
Beräkna effektivitet för alla 148 företag genom jämförelse mot varandra.

### Dataflöde

```
┌─────────────────────────────────────────┐
│           INPUT TILL DEA                │
├─────────────────────────────────────────┤
│  DataFrame (148 rader)                  │
│  - DMU, Företag                         │
│  - CAPEX (ev. modifierad)               │
│  - OPEXp                                │
│  - Volymer: CU, MW, NS, MWhl, MWhh      │
├─────────────────────────────────────────┤
│  Modellspecifikation                    │
│  - Inputs: [CAPEX, OPEXp]               │
│  - Outputs: [CU, MW, NS, MWhl, MWhh]    │
│  - RTS: VRS/CRS                         │
│  - Orientation: input                   │
│  - Outlier-hantering                    │
└─────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────┐
│           DEA-ALGORITM                  │
│                                         │
│  Super-efficiency DEA                   │
│  Outlier-identifiering                  │
│  Omberäkning utan outliers              │
│                                         │
└─────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────┐
│          OUTPUT FRÅN DEA                │
├─────────────────────────────────────────┤
│  DataFrame (148 rader)                  │
│  - DMU, Företag                         │
│  - Efficiency (0-1+)                    │
│  - Potential (%)                        │
│  - is_outlier (bool)                    │
│  - Peers, lambdas                       │
└─────────────────────────────────────────┘
```

### Vad DEA gör

1. **Jämför alla mot alla** - Varje företag jämförs mot alla andra
2. **Hittar effektiva företag** - De som ingen annan dominerar
3. **Beräknar ineffektivitet** - Hur långt från fronten är varje företag
4. **Identifierar peers** - Vilka effektiva företag ska ineffektiva jämföras med

### Viktigt: DEA kräver alla 148

DEA är en **relativ** effektivitetsmätning. Om du ändrar CAPEX för ett företag påverkar det potentiellt ALLA företags effektivitet eftersom fronten kan flytta sig.

Därför:
- Pre-DEA måste producera 148 rader
- DEA måste köras på alla 148
- Post-DEA extraherar sedan resultatet för 1 företag

### Data som behövs

| Dataset | Innehåll | Scope |
|---------|----------|-------|
| DEA-input DataFrame | Från Pre-DEA | 148 rader |
| Modellspecifikation | Inputs, outputs, RTS | Metadata |

### Nuvarande status vs korrekt beteende

| Steg | Nuvarande | Korrekt | Fil |
|------|-----------|---------|-----|
| DEA-algoritm | ✅ Fungerar | Super-efficiency med outliers | dea_producer.py |
| Input-hantering | ⚠️ Tar 3 DataFrames | Bör ta 1 merged DataFrame | dea_producer.py |

---

## 3. POST-DEA

### Syfte
Beräkna intäktsram för ETT företag baserat på dess effektivitet.

### Dataflöde

```
DEA-output (148 rader)
        │
        ▼
┌───────────────────────────────────────┐
│       EXTRAKTION (148 → 1)            │
│                                       │
│  Filtrera på inloggat företags DMU    │
│  Output: 1 rad med efficiency, etc.   │
└───────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────┐
│       EFFEKTIVISERINGSKRAV            │
│                                       │
│  Potential → Effkrav_proc             │
│  Baserat på Ei:s formel               │
└───────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────┐
│       PÅVERKBARA KOSTNADER            │
│                                       │
│  Applicera effkrav över 4 år          │
│  OPEX eller TOTEX-metod               │
└───────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────┐
│       INTÄKTSRAM                      │
│                                       │
│  Summera alla komponenter             │
│  Output: Intäktsram per år            │
└───────────────────────────────────────┘
```

### Beräkningsstegen

#### Steg 1: Extraktion
- **Input:** DEA-output (148 rader)
- **Process:** Filtrera på användarens DMU
- **Output:** 1 rad med efficiency, potential

#### Steg 2: Effektiviseringskrav
- **Input:** Potential (från DEA)
- **Process:** Ei:s formel för effektiviseringskrav
- **Output:** Effkrav_proc (%)

#### Steg 3: Påverkbara kostnader
- **Input:** Baseline-kostnader + Effkrav_proc
- **Process:** 
  - OPEX-metod: Applicera på OPEXp
  - TOTEX-metod: Applicera på TOTEX
  - Progressiv reduktion över 4 år
- **Output:** Påverkbara kostnader per år

#### Steg 4: Intäktsram
- **Input:** Alla komponenter (påverkbara, opåverkbara, kapitalkostnad, etc.)
- **Process:** Summera enligt Ei:s 11-stegsmodell
- **Output:** Total intäktsram per år

### Data som behövs

| Dataset | Innehåll | Scope |
|---------|----------|-------|
| DEA-output | Efficiency, potential | 1 rad (filtrerad) |
| Baseline-kostnader | OPEXp, CAPEX, etc. | 1 företag |

### Nuvarande status vs korrekt beteende

| Steg | Nuvarande | Korrekt | Fil |
|------|-----------|---------|-----|
| Extraktion | ❌ Ej explicit | Filtrera till 1 rad | Behöver skapas |
| Effektiviseringskrav | ✅ Fungerar | Ei:s formel | effektiviseringskrav.py |
| Påverkbara | ✅ Fungerar | OPEX/TOTEX | intaktsram_assembly.py |
| Intäktsram | ✅ Fungerar | 11-stegsmodell | intaktsram_assembly.py |

---

## SAMMANFATTNING: FUNKTIONER OCH FILER

### Pre-DEA funktioner

| Funktion | Syfte | Fil | Status | Namnändring? |
|----------|-------|-----|--------|--------------|
| `load_baseline_data()` | Ladda Data_modeller | baseline_loaders.py | ✅ | Nej |
| `produce_capex_from_wacc_scaling()` | WACC-skalning | capex_producers.py (github) | ✅ | → `produce_dea_input_wacc_scaling()` |
| `build_capbase_a_from_kent()` | Steg 1-4: KENT → capbase_a | capbase_prep.py (github) | ✅ | Nej |
| `apply_normvalue_adjustments()` | Justera normvärden | parameter_adjustments.py (github) | ✅ | Nej |
| `apply_lifetime_adjustments()` | Justera livslängder | parameter_adjustments.py (github) | ✅ | Nej |
| `calculate_ages_and_nuav()` | Steg 5: Åldrar/NUAV | beräkningskedja.py (github) | ✅ | Nej |
| `calculate_depreciation_single_dmu()` | Steg 6: Avskrivningar | beräkningskedja.py (github) | ✅ | → `calculate_depreciation()` |
| `calculate_returns_single_dmu()` | Steg 7: Avkastning | beräkningskedja.py (github) | ✅ | → `calculate_returns()` |
| `compile_capcost_single_dmu()` | Steg 8: Sammanställning | beräkningskedja.py (github) | ✅ | → `compile_capcost()` |
| `aggregate_capbase_to_dmu()` | Aggregera till DMU | - | ❌ Saknas | Ny |
| `orchestrate_pre_dea()` | Koordinera metoder | - | ❌ Saknas | Ny |

### DEA funktioner

| Funktion | Syfte | Fil | Status | Namnändring? |
|----------|-------|-----|--------|--------------|
| `run_dea_analysis()` | Kör DEA | dea_producer.py | ✅ | Nej |
| `_run_super_efficiency_dea()` | Super-efficiency | dea_producer.py | ✅ | Nej |

### Post-DEA funktioner

| Funktion | Syfte | Fil | Status | Namnändring? |
|----------|-------|-----|--------|--------------|
| `extract_company_result()` | Extraktion 148 → 1 | - | ❌ Saknas | Ny |
| `calculate_effkrav_from_potential()` | Effektiviseringskrav | effektiviseringskrav.py | ✅ | Nej |
| `calculate_paverkbara_with_effkrav()` | Påverkbara kostnader | intaktsram_assembly.py | ✅ | Nej |
| `assemble_intaktsram()` | Intäktsram | intaktsram_assembly.py | ✅ | Nej |

### Datafiler

| Fil | Innehåll | Plats | Scope |
|-----|----------|-------|-------|
| Data_modeller.xlsx | Baseline CAPEX/OPEX/volymer | data/ | 148 rader |
| capbase_a.parquet | Komponentdata alla företag | data/ | 510k rader |
| reconciliation.csv | id_network → DMU | data/ | Mapping |
| EIs_DEA.xlsx | Ei:s DEA-resultat (referens) | data/ | 148 rader |

---

## VAD SOM BEHÖVER GÖRAS

### Saknas (måste skapas)

| Komponent | Syfte | Prioritet |
|-----------|-------|-----------|
| `aggregate_capbase_to_dmu()` | Summera från komponent till DMU | Hög |
| `orchestrate_pre_dea()` | Välj metod och koordinera | Hög |
| `extract_company_result()` | Filtrera DEA-output till 1 företag | Medium |

### Synkas (finns i github, behöver till projekt)

| Fil | Från | Till |
|-----|------|------|
| beräkningskedja.py | github-synk | /mnt/project/ |
| capbase_prep.py | github-synk | /mnt/project/ |
| parameter_adjustments.py | github-synk | /mnt/project/ |
| capex_producers.py | github-synk | /mnt/project/ (→ pre_dea_producers.py) |

### Namnändringar (kosmetiskt, låg prioritet)

| Nuvarande | Nytt | Anledning |
|-----------|------|-----------|
| `_single_dmu` suffix | Ta bort | Missvisande - fungerar på alla |
| capex_producers.py | pre_dea_producers.py | Tydligare syfte |

---

## KRITISKT ATT FÖRSTÅ

1. **DEA kräver alltid 148 rader** - Alla företag måste vara med för att jämförelsen ska fungera

2. **Pre-DEA handlar om att förbereda dessa 148 rader** - Oavsett metod ska output vara 148 rader

3. **Post-DEA handlar om 1 företag** - Efter DEA extraherar vi resultatet för det företag användaren är intresserad av

4. **WACC är en parameter i steg 7** - Det är därför WACC kan kombineras med capbase-kedja och KENT-full

5. **Aggregering är kritisk** - capbase_a är på komponent-nivå, DEA behöver DMU-nivå

---

**END OF DOCUMENT**

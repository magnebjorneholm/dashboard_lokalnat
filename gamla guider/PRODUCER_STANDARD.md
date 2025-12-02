# PRODUCER STANDARD - KONCEPTUELL GUIDE

**Version:** 1.0  
**Datum:** 2025-01-XX  
**Syfte:** Definiera långsiktig standard för producer-arkitektur i Regumetrica

---

## 1. SYFTE & OMFATTNING

### 1.1 Varför denna standard?

Regumetrica är ett system där beräkningar flödar genom en kedja av producers. En producer tar input (data från tidigare steg), gör en beräkning, och returnerar output (data för nästa steg). 

**Problemet utan standard:**
- Producer A returnerar DataFrame
- Producer B returnerar Tuple med (DataFrame, dict)
- Producer C returnerar Dict med {'result': DataFrame}
- Producer D vet inte vad den får som input → Systemet kraschar

**Lösningen med standard:**
- ALLA producers returnerar SAMMA format
- Nästa producer vet EXAKT vad den får
- Systemet är robust och förutsägbart

### 1.2 Vad denna standard löser

✅ **Konsistens:** Samma format överallt, inga överraskningar  
✅ **Långsiktighet:** Enkelt att lägga till nya producers i framtiden  
✅ **Source-agnostic:** Downstream bryr sig inte VAR data kommer ifrån (DEA, SFA, baseline, manuell input)  
✅ **Spårbarhet:** Metadata följer med genom hela kedjan  
✅ **Kontrollflöde:** Metadata styr vad systemet ska göra härnäst  

### 1.3 Vad detta dokument INTE är

❌ Inte en implementation-guide (se MASTER_REFERENCE_FOR_CLAUDE.md för det)  
❌ Inte en kodexempel-samling (se befintliga producers för det)  
❌ Inte en fullständig arkitektur-beskrivning (se ARCHITEKTUR_SAMMANFATTNING.md)

**Detta är:** En konceptuell guide för att förstå VARFÖR vi har denna standard och VAD den innebär i princip.

---

## 2. GRUNDPRINCIPER

### 2.1 Source-Agnostic Beräkningar

**Princip:** Beräkningar bryr sig inte om VAR data kommer ifrån, bara att den har RÄTT FORMAT.

**Exempel:**
```
Effektivitet kan beräknas via:
- DEA (Data Envelopment Analysis)
- SFA (Stochastic Frontier Analysis)
- StoNED (Stochastic Nonparametric DEA)
- Baseline (från Excel)
- Manuell input (användaren skriver in)

→ Effektiviseringskrav-beräkningen bryr sig INTE om källan
→ Den bryr sig bara om att få en DataFrame med kolumnen 'Effektivitet'
```

**Varför detta är viktigt:**
- Lätt att byta metod (DEA → SFA) utan att ändra downstream-kod
- Lätt att lägga till nya metoder (StoNED) utan att bryta befintligt
- Flexibilitet för framtida tillägg

### 2.2 Kontrakt-Baserad Design

**Princip:** Alla producers följer samma kontrakt (samma input/output-format).

**Kontrakt = Överenskommelse:**
- "Jag lovar att returnera Dict med 'data' och 'metadata'"
- "Du kan lita på att jag alltid följer detta"
- "Du behöver inte kolla vad jag returnerar - du VET redan"

**Fördelar:**
- Ingen kod som kollar "är detta en DataFrame eller en Tuple?"
- Ingen felhantering för olika format
- Enklare att läsa och förstå kod

### 2.3 DataFrame som Kärnformat

**Princip:** All tabelldata (företagsdata, beräkningsresultat) är ALLTID DataFrame, övriga värden (scalers) är enstaka värden som används i funktioner (se 2.4) och ska INTE va dataframe.

**Även om:**
- Det bara är 1 rad → Fortfarande DataFrame (t.ex. efter man extraherar värden för inloggat företags effektivitet och fortsätter med beräkningar post-DEA)
- Det bara är 2 kolumner → Fortfarande DataFrame

**Varför DataFrame:**
- Pandas-fördelar: merge, filter, calculate
- Konsekvent genom hela systemet
- Enkel att validera och debugga
- Stöd för kolumnnamn och typer

### 2.4 Två Typer av Outputs

**Tabelldata-producers** (DataFrame + metadata):
- Returnerar data för flera/ett företag
- Exempel: CAPEX (148 rader), Efficiency (148 rader), Intäktsram (1 rad)
- Format: `{'data': DataFrame, 'metadata': dict}`

**Parameter-funktioner**:
- Returnerar enstaka värden som används i senare funktioner och beräkningar
- Exempel: WACC, skattesats, CAPM-komponenter, potential efter DEA, effektivitetskrav
- Format: Direkt värde (float, int) eller lagras i case_definition['parameters']
- Dessa är INTE producers i samma mening.

### 2.5 Metadata för Spårbarhet OCH Kontrollflöde

**Princip:** Metadata har DUBBEL funktion.

**Funktion 1 - Spårbarhet:**
- "Vad gjordes?"
- "Vilken metod användes?"
- "Hur många företag ingick?"

**Funktion 2 - Kontrollflöde (KRITISKT):**
- "Ska vi beräkna nytt eller använda baseline?"
- "Vilken metod ska nästa steg använda?" (OPEX vs TOTEX)
- "Har denna modifikation applicerats?"

**Exempel på kontrollflöde:**
```
Producer A returnerar metadata: {'source': 'baseline'}
Producer B läser: "Aha, detta är baseline, jag hoppar över avancerad beräkning"

Producer C returnerar metadata: {'method': 'TOTEX'}
Producer D läser: "TOTEX valdes, jag inkluderar CAPEX i min beräkning"
```

### 2.6 Långsiktighet över Kortsiktiga Lösningar

**Princip:** Ingen teknisk skuld. Gör det rätt från början.

**Vi undviker:**
- "Hybrid-lösningar" som funkar för vissa producers
- "Quick fixes" som bara täpper hål
- "Workarounds" som gör kod svårläst

**Vi föredrar:**
- En standard som gäller FÖR ALLTID
- Konsekvent kod även om det tar längre tid
- Långsiktig arkitektur som skalas

---

## 3. PRODUCER-OUTPUTS - TVÅ TYPER

### 3.1 Översikt

Regumetrica har **två typer av outputs** som producers/funktioner returnerar:

| Typ | Returnerar | Används för | Exempel |
|-----|-----------|-------------|---------|
| **Tabelldata** | DataFrame + metadata | Företagsdata, beräkningsresultat | CAPEX, Efficiency, Intäktsram |
| **Skalärer** | Enstaka värde (float/int) | Parametrar i beräkningar | WACC, rf, mrp, skattesats |

### 3.2 Tabelldata-producers (ProducerReturn)

**Definition:** Producers som returnerar data för ett eller flera företag.

**Format:**
```python
return {
    'data': DataFrame,      # Tabelldata (rader × kolumner)
    'metadata': dict        # Om beräkningen + kontrollflöde
}
```

**Exempel:**
- CAPEX-producer → 148 rader (alla företag)
- Efficiency-producer → 148 rader (alla företag)
- Effektiviseringskrav-producer → 1 rad (efter extraktion)
- Intäktsram-producer → 1 rad (inloggat företag)

**Regler:**
- Data är ALLTID DataFrame, även för 1 rad
- Metadata innehåller minst `source` och `n_companies`
- Returnera aldrig None, Tuple, eller bara DataFrame

### 3.3 Skalär-funktioner (Parametervärden)

**Definition:** Funktioner som returnerar enstaka värden som används direkt i beräkningar.

**Format:**
```python
return value  # float, int, eller dict med config
```

**Exempel:**
- `ei_wacc_real_pre_tax()` → returnerar `(Re, Rd, Wn, Wr)` där Wr är WACC som float
- CAPM-komponenter → rf (float), mrp (float), beta (float)
- Skattesats → float
- Skalningsfaktor → float

**Hur de används:**
```python
# WACC beräknas och returneras som float
wacc = ei_wacc_real_pre_tax(inputs)[3]  # 0.0453

# Används direkt i andra funktioner
scaling_factor = wacc_new / wacc_baseline
df['Avkastning'] = df['Avkastning'] * scaling_factor

# Eller som argument
calculate_returns(capbase_a, interest_rate=wacc)
```

**Lagring:**
Skalärer lagras i `case_definition['parameters']`:
```python
case_definition['parameters'] = {
    'wacc': 0.0453,
    'rf': 0.0287,
    'mrp': 0.0668,
    # ...
}
```

### 3.4 Varför två typer?

**Tabelldata** representerar resultat som varierar per företag:
- Varje företag har sin egen CAPEX
- Varje företag har sin egen Efficiency
- Kräver DataFrame för att hålla alla värden

**Skalärer** representerar antaganden som gäller lika för alla:
- WACC är samma för alla 148 företag
- Skattesats är samma för alla
- Behöver inte DataFrame - ett värde räcker

**Konsekvens:** Tvinga inte skalärer in i DataFrame-format. Det skapar onödig komplexitet utan nytta.

### 3.5 Sammanfattning

| Aspekt | Tabelldata | Skalärer |
|--------|-----------|----------|
| **Returnerar** | `{'data': DataFrame, 'metadata': dict}` | `float`, `int`, eller `tuple` |
| **Representerar** | Per-företag data | Globala antaganden |
| **Scope** | 148 rader eller 1 rad | N/A |
| **Lagras i** | Passeras mellan producers | `case_definition['parameters']` |
| **Exempel** | CAPEX, Efficiency | WACC, rf, skattesats |

---

---

## 4. DATA VS METADATA - KONCEPTUELL FÖRKLARING

### 4.1 Tre typer av information

| Typ | Vad det är | Format | Exempel |
|-----|-----------|--------|---------|
| **Tabelldata** | Per-företag resultat | DataFrame | CAPEX, Efficiency, Intäktsram |
| **Skalärer** | Globala parametrar | float/int | WACC, rf, skattesats |
| **Metadata** | Information OM beräkningen | dict | source, method, n_companies |

### 4.2 Tabelldata (DataFrame)

**Definition:** Data där varje rad representerar ett företag.

**Egenskaper:**
- Strukturerad i rader och kolumner
- Varje rad = ett företag (identifieras via DMU eller REId)
- Varje kolumn = en variabel (t.ex. Effektivitet, CAPEX)
- Används i pandas-operationer (merge, filter, calculate) eller DEA.

**Exempel - Efficiency-data:**
```
DataFrame (148 rader):
DMU | REId     | Effektivitet | potential | is_outlier
----|----------|--------------|-----------|------------
1   | REL00001 | 0.85         | 0.15      | False
2   | REL00002 | 0.92         | 0.08      | False
3   | REL00003 | 0.78         | 0.22      | True
...
148 | REL00148 | 0.88         | 0.12      | False
```

**Exempel - Intäktsram (1 rad efter extraktion):**
```
DataFrame (1 rad):
DMU | REId     | Kapitalkostnad | Paverkbara | Intaktsram_Total
----|----------|----------------|------------|------------------
42  | REL00042 | 125000         | 85000      | 245000
```

### 4.3 Skalärer (float/int)

**Definition:** Enstaka värden som representerar parametrar eller antaganden.

**Egenskaper:**
- Ett värde, inte en tabell
- Gäller lika för alla företag (eller hela beräkningen)
- Används direkt i formler och funktionsanrop
- Lagras i `case_definition['parameters']`

**Exempel - WACC och komponenter:**
```python
# Skalärer - enstaka värden
wacc = 0.0453           # Kalkylränta
rf = 0.0287             # Riskfri ränta
mrp = 0.0668            # Marknadsriskpremie
scaling_factor = 1.104  # WACC-skalning

# Används direkt
df['Avkastning'] = df['Avkastning'] * scaling_factor
calculate_returns(data, interest_rate=wacc)
```

**Exempel - Lagring:**
```python
case_definition['parameters'] = {
    'wacc': 0.0453,
    'rf': 0.0287,
    'mrp': 0.0668,
    'beta_asset': 0.37,
    'debt_share': 0.36,
    'tax_rate': 0.206,
    'inflation': 0.0202
}
```

### 4.4 Metadata (dict)

**Definition:** Information OM data och beräkningen - inte data i sig.

**Egenskaper:**
- Key-value pairs (dict)
- Beskriver hela datasetet, inte enskilda rader
- Används för KONTROLLFLÖDE och SPÅRBARHET

**Exempel - Efficiency-metadata:**
```python
metadata = {
    'source': 'calculated',
    'method': 'DEA',
    'n_companies': 148,
    'n_outliers': 5,
    'dea_orientation': 'input',
    'returns_to_scale': 'CRS'
}
```

### 4.5 Vad hör hemma var?

| Koncept | Tabelldata | Skalär | Metadata |
|---------|-----------|--------|----------|
| Företagets CAPEX | ✅ | ❌ | ❌ |
| WACC-värde | ❌ | ✅ | ❌ |
| Företagets effektivitet | ✅ | ❌ | ❌ |
| Antal företag totalt | ❌ | ❌ | ✅ |
| Skalningsfaktor | ❌ | ✅ | ❌ |
| Vilken metod användes | ❌ | ❌ | ✅ |
| Är företag X outlier | ✅ (kolumn) | ❌ | ❌ |
| Antal outliers totalt | ❌ | ❌ | ✅ |
| Skattesats | ❌ | ✅ | ❌ |
| Intäktsram per företag | ✅ | ❌ | ❌ |

**Tumregler:**
- Per-företag data → **Tabelldata** (DataFrame)
- Globala antaganden/parametrar → **Skalärer** (float/int)
- Om beräkningen (hur, vad, hur många) → **Metadata** (dict)

### 4.6 Varför separera?

**Tekniska skäl:**
- Tabelldata är stor (148 rader), skalärer och metadata är små
- Tabelldata används i pandas-operationer
- Skalärer används direkt i formler
- Metadata används i if-satser och logging

**Konceptuella skäl:**
- Tabelldata = "Vad är resultatet per företag?"
- Skalärer = "Vilka antaganden gäller?"
- Metadata = "Hur kom vi hit?" + "Vad gör vi nu?"

---


## 5. PRODUCER-KONTRAKT - REGLER
**KRITISKT:** Dessa regler gäller för tabelldata-producers (de som returnerar DataFrame + metadata). 
För skalär-funktioner (WACC, etc.), se sektion 3.3.

### 5.1 Vad en Producer MÅSTE Göra

✅ **Returnera korrekt format:**
```
return {
    'data': DataFrame,
    'metadata': dict
}
```

✅ **Data MÅSTE vara DataFrame:**
- Även för 1 rad → DataFrame med 1 rad
- Även för 2 kolumner → DataFrame med 2 kolumner
- ALDRIG Series, list, dict, eller annat

✅ **Metadata MÅSTE vara dict:**
- Minst 'source' nyckel
- Kan innehålla godtyckligt många fält
- ALDRIG None, list, eller annat

✅ **Validera sina inputs:**
- Kolla att dependencies har rätt format
- Kasta exception vid fel, returnera aldrig partial results

✅ **Dokumentera sitt kontrakt:**
- Vilka dependencies krävs?
- Vilka kolumner i data returneras?
- Vilka metadata-fält finns?

### 5.2 Vad en Producer FÅR Göra

✅ **Läsa metadata från dependencies:**
```python
# Om producer behöver veta vilken metod tidigare steg använde
method = dependency['metadata'].get('method')
```

✅ **Kedja metadata framåt:**
```python
metadata = {
    'source': 'calculated',
    'input_metadata': {
        'efficiency': efficiency_dep['metadata'],
        'capex': capex_dep['metadata']
    }
}
```

✅ **Lägga till frivillig metadata:**
```python
metadata = {
    'source': 'calculated',  # Obligatorisk
    'method': 'OPEX',        # Frivillig men användbar
    'debug_info': {...}      # Frivillig för diagnostik
}
```

### 5.3 Vad en Producer ALDRIG Får Göra

❌ **Modifiera input DataFrames:**
```python
# FEL
def bad_producer(dependency):
    df = dependency['data']
    df['new_column'] = 123  # Modifierar original!
    
# RÄTT
def good_producer(dependency):
    df = dependency['data'].copy()  # Kopiera först
    df['new_column'] = 123
```

❌ **Returnera olika format beroende på config:**
```python
# FEL
def bad_producer(config):
    if config['mode'] == 'simple':
        return dataframe  # Bara DataFrame
    else:
        return {'data': dataframe, 'metadata': {}}  # Dict
        
# RÄTT
def good_producer(config):
    # ALLTID samma format, oavsett config
    return {'data': dataframe, 'metadata': {...}}
```

❌ **Ha side effects:**
```python
# FEL
def bad_producer():
    global_variable = 123  # Ändrar global state
    st.session_state.x = 456  # Ändrar session state
    
# RÄTT
def good_producer():
    # Pure function - bara input → output
    return {'data': ..., 'metadata': ...}
```

❌ **Returnera None eller partiella resultat:**
```python
# FEL
def bad_producer():
    if error:
        return None  # Returnerar ingenting
        
# RÄTT
def good_producer():
    if error:
        raise ValueError("Beskrivande felmeddelande")
```

### 5.4 Pure Functions

**Princip:** Producers är pure functions.

**Vad detta betyder:**
- Samma input → Samma output (deterministiskt)
- Inga side effects (ingen global state)
- Inga I/O operationer utom att läsa config/dependencies
- Testbart (kan köra utan hela systemet)

**Undantag:**
- Baseline producers FÅR läsa från fil (det är deras jobb)
- Producers FÅR logga för debugging (warnings)

---

## 6. DEPENDENCY FLOW - KONCEPTUELL FÖRKLARING

### 6.1 Hur Dependencies Flödar

**Konceptuellt flöde:**
```
Baseline Loader
    ↓ (returnerar ProducerReturn)
Producer A
    ↓ (returnerar ProducerReturn)
Producer B (tar A som dependency)
    ↓ (returnerar ProducerReturn)
Producer C (tar A och B som dependencies)
    ↓ (returnerar ProducerReturn)
Final Assembly
```

**Viktigt:**
- Alla pilar är SAMMA format (ProducerReturn)
- Ingen pil är "speciell"
- Kedjan kan bli hur lång som helst
- Formatet förändras aldrig

### 6.2 Source-Agnostic Downstream

**Exempel - Effektivitet kan komma från 4 källor:**

```
Möjliga källor för 'efficiency':
┌─────────────────────────────────────┐
│ 1. DEA (produce_efficiency_from_dea)│
│ 2. SFA (produce_efficiency_from_sfa)│
│ 3. StoNED (...from_stoned)          │
│ 4. Baseline (...from_baseline)      │ 
└─────────────────────────────────────┘
            ↓ (alla returnerar samma ProducerReturn)
┌─────────────────────────────────────┐
│ Effektiviseringskrav                │
│ (bryr sig INTE om källan)           │
└─────────────────────────────────────┘
```

**Downstream producer ser:**
```python
def produce_effektiviseringskrav(efficiency, config):
    # efficiency är ProducerReturn - källan spelar ingen roll
    df = efficiency['data']  # DataFrame med 'Effektivitet' kolumn
    
    # Om vi vill veta källan (för diagnostik):
    source = efficiency['metadata']['source']  # 'DEA' eller 'SFA' etc
```

### 6.3 Metadata för Kontrollflöde

**Exempel 1 - Conditional Calculation:**
```
Producer: Intäktsram Assembly
Dependencies: capex, opex, paverkbara_effkrav (optional)

Logik:
if paverkbara_effkrav är None:
    → Använd baseline påverkbara kostnader
else:
    → Använd beräknade påverkbara (efter effektiviseringskrav)
```

**Exempel 2 - Method-Dependent Calculation:**
```
Producer: Påverkbara Kostnader
Dependencies: effkrav_data, ir_baseline, capex_data

Läser metadata:
method = effkrav_data['metadata']['method']  # 'OPEX' eller 'TOTEX'

if method == 'OPEX':
    → Applicera effkrav bara på OPEX
elif method == 'TOTEX':
    → Applicera effkrav på OPEX + CAPEX
```

**Exempel 3 - Source-Based Decision:**
```
Producer: Results Display
Dependencies: intaktsram

Läser metadata:
source = intaktsram['metadata']['source']

if source == 'baseline':
    → Visa "Inga ändringar - baseline visas"
elif source == 'calculated':
    → Visa "Scenario-beräkning klar"
```

---

## 7. BASELINE VS CALCULATED PRODUCERS

### 7.1 Två Typer av Producers

**Baseline Producer:**
- Läser från fil (Excel, CSV, etc)
- Inga dependencies (eller bara config)
- Returnerar ProducerReturn med source='baseline'

**Calculated Producer:**
- Tar andra ProducerReturn som dependencies
- Gör beräkningar på data
- Returnerar ProducerReturn med source='calculated'

### 7.2 Skillnader och Likheter

| Aspekt | Baseline Producer | Calculated Producer |
|--------|-------------------|---------------------|
| **Dependencies** | Inga (eller config) | 1+ ProducerReturn |
| **Input** | Fil-path i config | DataFrame från dependencies |
| **Beräkning** | Läser och formaterar | Gör matematik/analys |
| **Metadata source** | 'baseline' | 'calculated' |
| **Return format** | ProducerReturn | ProducerReturn |
| **Kontrakt** | Samma | Samma |

**Viktigt:** Båda returnerar SAMMA format → Downstream bryr sig inte om skillnaden.

---

## 8. METADATA BEST PRACTICES

### 8.1 Obligatoriska Fält

**Alla metadata MÅSTE innehålla:**

```python
metadata = {
    'source': 'baseline' | 'calculated' | 'manual' | ...,
    'n_companies': int  # Antal rader i data
}
```

**Varför obligatoriskt:**
- `source`: Kontrollflöde (baseline vs calculated)
- `n_companies`: Validering (säkerställ data inte är tom)

### 8.2 Rekommenderade Fält

**För calculated producers:**
```python
metadata = {
    'source': 'calculated',
    'n_companies': 150,
    'method': str,              # Vilken metod/algoritm
    'total_<värde>': float,     # Aggregerade totaler
    'mean_<värde>': float,      # Medelvärden
}
```

**För producers som läser andra producers:**
```python
metadata = {
    'source': 'calculated',
    'n_companies': 150,
    'input_metadata': {         # Kedja metadata från dependencies
        'efficiency': efficiency_dep['metadata'],
        'capex': capex_dep['metadata']
    }
}
```

### 8.3 Frivilliga Fält för Diagnostik

```python
metadata = {
    # ... obligatoriska fält ...
    
    'warnings': [               # Varningar under beräkning
        "5 företag saknade CAPEX-data",
        "3 outliers detekterades"
    ],
    'calculation_time_s': 2.3,  # Performance-mätning
    'debug_info': {...},        # Extra info för debugging
    'validation': {             # Validerings-resultat
        'passed': True,
        'errors': []
    }
}
```

### 8.4 Kontrollflöde-Metadata

**Metadata för att styra nästa steg:**

```python
# Producer returnerar
metadata = {
    'source': 'baseline',
    'has_modifications': False  # ← Indikerar att baseline ska användas
}

# Nästa producer läser
if dependency['metadata']['has_modifications']:
    # Gör avancerad beräkning
else:
    # Använd baseline direkt
```

**Andra exempel:**
```python
metadata = {
    'method': 'TOTEX',          # Styr hur nästa steg beräknas
    'include_quality': True,    # Styr om kvalitetsjustering ska läggas till
    'is_outlier_excluded': True # Styr om outliers ska filtreras
}
```

### 8.5 Bra vs Dålig Metadata-Struktur

**❌ Dålig:**
```python
metadata = {
    'stuff': [1, 2, 3],          # Vad betyder detta?
    'x': True,                   # Oklart namn
    'result': 'done'             # Vag information
}
```

**✅ Bra:**
```python
metadata = {
    'source': 'calculated',
    'method': 'DEA_VRS',
    'n_companies': 150,
    'n_outliers': 5,
    'outlier_ids': ['REL00123', 'REL00456'],
    'dea_orientation': 'input',
    'returns_to_scale': 'variable',
    'total_efficiency_sum': 127.8,
    'mean_efficiency': 0.852
}
```

**Varför bra:**
- Tydliga namn
- Beskrivande värden
- Användbar för både kontrollflöde och diagnostik
- Strukturerad och lätt att läsa

---

## 9. VALIDATION & FEL

### 9.1 Varför Vi Validerar Return-Format

**Problem utan validering:**
```
Producer A råkar returnera fel format
→ Nästa producer förväntar sig ett format men får ett annat
→ Systemet kraschar med kryptiskt fel
→ Svårt att debugga
```

**Lösning med validering:**
```
Producer A returnerar fel format
→ Validator fångar felet DIREKT
→ Tydligt felmeddelande: "Producer måste returnera dataframe med 'data' och 'metadata'"
→ Enkelt att fixa
```

### 9.2 Vad Händer vid Fel?

**Vid validation-fel:**
1. Exception kastas omedelbart
2. Tydligt felmeddelande med:
   - Vilket producer som failade
   - Vad som var fel
   - Vad som förväntades
3. Beräkningen stoppas (ingen partial result)

**Exempel-fel:**
```
ValidationError: Producer 'efficiency' returned invalid format.
Expected: Dict with 'data' (DataFrame) and 'metadata' (dict)
Got: DataFrame

→ Producer måste wrappa returvärdet i Dict-format
```

### 9.3 Producer Ansvar

**Producer är ansvarig för:**
- ✅ Returnera korrekt format
- ✅ Validera sina inputs (dependencies)
- ✅ Kasta exception vid fel (inte returnera None)
- ✅ Ge beskrivande felmeddelanden

**Resolver är ansvarig för:**
- ✅ Validera return-format från producer
- ✅ Validera att dependencies har rätt format
- ✅ Ge kontext vid fel (vilken producer, vilken dependency)

---

## 10. ANTI-PATTERNS - VAD MAN INTE SKA GÖRA

### 10.1 Varierande Return-Format

**❌ FEL:**
```python
def bad_producer(config):
    if config['simple_mode']:
        return dataframe  # Bara DataFrame
    else:
        return {'data': dataframe, 'metadata': {}}  # Dict
```

**✅ RÄTT:**
```python
def good_producer(config):
    # ALLTID samma format, oavsett config
    return {
        'data': dataframe,
        'metadata': {'mode': config.get('simple_mode', False)}
    }
```

### 10.2 Returnera Tuple Istället för Dict

**❌ FEL:**
```python
def bad_producer():
    return (dataframe, metadata)  # Tuple
```

**Problem:** Nästa producer måste veta ORDNING

**✅ RÄTT:**
```python
def good_producer():
    return {'data': dataframe, 'metadata': metadata}  # Dict
```

**Fördel:** Nästa producer använder NAMN, inte ordning

### 10.3 Modifiera Input DataFrames

**❌ FEL:**
```python
def bad_producer(dependency):
    df = dependency['data']
    df['new_col'] = 123  # Modifierar original!
    return {'data': df, 'metadata': {}}
```

**Problem:** Sidoeffekter - andra producers påverkas

**✅ RÄTT:**
```python
def good_producer(dependency):
    df = dependency['data'].copy()  # Kopiera FÖRST
    df['new_col'] = 123
    return {'data': df, 'metadata': {}}
```

### 10.4 Returnera Series eller Skalär istället för DataFrame

**❌ FEL:**
```python
def bad_producer():
    # "Det är ju bara ett värde, varför DataFrame?"
    return {'data': 0.85, 'metadata': {}}  # Skalär
```

**❌ OCKSÅ FEL:**
```python
def bad_producer():
    # "Det är ju bara en kolumn, varför DataFrame?"
    return {'data': pd.Series([0.85]), 'metadata': {}}  # Series
```

**✅ RÄTT:**
```python
def good_producer():
    # ALLTID DataFrame, även för 1 värde
    df = pd.DataFrame({'value': [0.85]})
    return {'data': df, 'metadata': {}}
```

**Varför:** Konsistens. Nästa producer vet ALLTID vad den får.

### 10.5 Tom eller Inkonsekvent Metadata

**❌ FEL:**
```python
def bad_producer():
    return {
        'data': df,
        'metadata': {}  # Tom metadata - ingen info
    }
```

**❌ OCKSÅ FEL:**
```python
def bad_producer(config):
    if config['mode'] == 'A':
        metadata = {'source': 'calculated', 'method': 'A'}
    else:
        metadata = {'source': 'calculated'}  # Inkonsistent - 'method' saknas
    
    return {'data': df, 'metadata': metadata}
```

**✅ RÄTT:**
```python
def good_producer(config):
    metadata = {
        'source': 'calculated',
        'n_companies': len(df),
        'method': config.get('mode', 'default')  # ALLTID finns
    }
    return {'data': df, 'metadata': metadata}
```

### 10.6 Sammanfattning Anti-Patterns

| ❌ Gör INTE | ✅ Gör ISTÄLLET |
|-------------|-----------------|
| Returnera bara DataFrame | Returnera Dict med 'data' + 'metadata' |
| Returnera Tuple | Returnera Dict |
| Modifiera input DataFrame | Kopiera först, ändra sedan |
| Returnera Series/skalär | Alltid DataFrame |
| Tom metadata | Minst 'source' + 'n_companies' |
| Varierande format | ALLTID samma format |
| Side effects | Pure function |

---

## 11. VANLIGA FRÅGOR (FAQ)

### Q1: Måste jag returnera DataFrame även för 1 värde?

**A:** Ja. ALLTID DataFrame, även för 1 rad eller 1 kolumn.

**Varför:** Konsistens. Nästa producer ska ALDRIG behöva kolla "är detta DataFrame eller skalär?"

**Exempel:**
```python
# ✅ Rätt - även för 1 värde
df = pd.DataFrame({'wacc': [0.0453]})
return {'data': df, 'metadata': {...}}
```

---

### Q2: Vad om jag inte har någon metadata?

**A:** Du har ALLTID minst 'source' och 'n_companies'.

**Minimum:**
```python
metadata = {
    'source': 'baseline' | 'calculated',
    'n_companies': len(dataframe)
}
```

---

### Q3: Kan en producer returnera None?

**A:** NEJ. Aldrig returnera None.

**Om det är fel:** Kasta exception istället
```python
if data_is_invalid:
    raise ValueError("Beskrivande felmeddelande")
```

**Om data saknas:** Returnera tom DataFrame
```python
return {
    'data': pd.DataFrame(),  # Tom men giltig DataFrame
    'metadata': {'source': 'baseline', 'n_companies': 0}
}
```

---

### Q4: Kan jag returnera extra nycklar i Dict?

**A:** NEJ. Endast 'data' och 'metadata'.

**❌ Fel:**
```python
return {
    'data': df,
    'metadata': {},
    'extra_info': 123  # Extra nyckel - INTE tillåtet
}
```

**✅ Rätt:**
```python
return {
    'data': df,
    'metadata': {
        'extra_info': 123  # Lägg extra info I metadata
    }
}
```

---

### Q5: Vad om baseline saknas?

**A:** Kasta exception med tydligt meddelande.

```python
def produce_from_baseline(config):
    filepath = config['file_path']
    
    if not os.path.exists(filepath):
        raise FileNotFoundError(
            f"Baseline-fil saknas: {filepath}. "
            f"Systemet kan inte fortsätta utan baseline-data."
        )
```

---

### Q6: Kan jag ändra formatet i framtiden?

**A:** NEJ. Detta är LÅNGSIKTIG standard.

Om du behöver lägga till något:
- ✅ Lägg till i metadata (flexibel dict)
- ✅ Lägg till kolumn i DataFrame
- ❌ Ändra inte top-level struktur

---

### Q7: Hur hanterar jag flera outputs?

**A:** En producer = en output. Om du behöver flera:

**Alternativ 1:** Stoppa alla i samma DataFrame (olika kolumner)
```python
df = pd.DataFrame({
    'efficiency': [...],
    'slack': [...],
    'lambda': [...]
})
```

**Alternativ 2:** Skapa separata producers
```python
# Producer 1
def produce_efficiency(...)
    return {'data': df_efficiency, 'metadata': {}}

# Producer 2 (läser samma input)
def produce_slack(...)
    return {'data': df_slack, 'metadata': {}}
```

---

## 12. CHECKLISTA FÖR PRODUCER-FÖRFATTARE

**Innan du skriver en producer, kontrollera:**

### Design-fas:
- [ ] Vilka dependencies behöver jag? (skrivs i 'requires')
- [ ] Vilken data ska jag returnera? (vilka kolumner i DataFrame)
- [ ] Vilken metadata behövs? (minst source + n_companies)
- [ ] Behöver nästa steg läsa min metadata för kontrollflöde?

### Implementation-fas:
- [ ] Tar dependencies som ProducerReturn (Dict med 'data' + 'metadata')
- [ ] Extraherar DataFrame via `dependency['data']`
- [ ] Kopierar DataFrames innan modifiering (`.copy()`)
- [ ] Validerar inputs (kastar exception vid fel)
- [ ] Returnerar Dict med exakt 'data' och 'metadata'
- [ ] 'data' är DataFrame (även för 1 rad)
- [ ] 'metadata' är dict med minst 'source' och 'n_companies'
- [ ] Dokumenterat vilka kolumner 'data' innehåller
- [ ] Dokumenterat vilka metadata-fält som finns
- [ ] Pure function (inga side effects)

### Test-fas:
- [ ] Testat med 1 företag (1 rad)
- [ ] Testat med 150 företag
- [ ] Testat med tom input (0 rader)
- [ ] Testat felfall (kastar rätt exception)
- [ ] Verifierat att return-format är korrekt

---

## 13. SAMMANFATTNING

### 13.1 Kärnan i Denna Standard

**En mening:** ALLA producers returnerar Dict med 'data' (DataFrame) och 'metadata' (dict).

**Varför:**
- Konsistens genom hela systemet
- Source-agnostic beräkningar
- Långsiktig arkitektur utan teknisk skuld
- Metadata för både spårbarhet OCH kontrollflöde

### 13.2 Tre Nycklar till Framgång

1. **Kontrakt:** Alla följer samma kontrakt → Förutsägbart system
2. **DataFrame:** All tabelldata är DataFrame → Konsekvent datahantering
3. **Metadata:** Både spårbarhet OCH kontrollflöde → Flexibelt system

### 13.3 Vad Kommer Härnäst?

**Detta dokument ger:** Konceptuell förståelse av VARFÖR och VAD.

**Nästa steg:** Implementation-guide med KONKRET kod (se MASTER_REFERENCE_FOR_CLAUDE.md).

**Långsiktigt:** Denna standard gäller för ALLA framtida producers - inga undantag.

---

**END OF DOCUMENT**

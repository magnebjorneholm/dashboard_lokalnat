# FULLSTÄNDIG REGUMETRICA FLOW

## 1. Innehåll
1. Beskrivning av data
2. Översikt av flöde
3. Mer detaljerat flöde med funktioner
4. övriga insikter

## 1. Beskrivning av data
Se dataset_guide.md för komplett redogörelse.

## 2. Översikt av flöde
1. Pre-DEA
SYFTE: Laddar dataset som ska användas för DEA (Data_modeller.xlsx).
=> beräknar ny capex (avkskrivning + avkastning) som ska in i DEA för alla 148 företag.
=> skickar vidare dataframe med uppdaterade värden + metadata med modellspecifikation.

2. DEA
Tar dataframe med uppdaterade värden och modellspecifkation.
=> kör DEA och beräknar effektivitet, potential och outlier-status i dataframe.

3. Post-DEA.
Filtrerar datframe med 148 företag och extraherar inloggat företags potential.
=> beräknar årligt effektiviseringskrav (effkrav_proc) givet antaganden om trunkering och IQR-multiplikator.
=> Välj om effektiviseringskravet ska läggas på OPEXp eller TOTEX (OBS! TOTEX ska va den uppdaterade från beräkningskedjan med nya antaganden i caset!).
=> Effektiviseringskrav applicerar enlgit formel för att beräkna Paverkbara_avdrag.
=> Fullständig intaktsram summeras med alla komponenter, se fullständig dekomposition i intaktsram_assembly.

## 2. Mer detaljerat flöde. 
## 2.1 PRE-DEA

### Syfte
Förbereda en DataFrame med 148 rader (alla företag) där CAPEX kan vara modifierad enligt olika metoder. Målet är att kunna testa "vad händer med effektiviteten om kapitalkostnaden beräknas annorlunda?"

### Dataflöde

```
Data_modeller.xlsx (148 rader) laddas.
        │
        ▼
┌───────────────────────────────────────────────────────────┐
│                  ANVÄNDARE VÄLJER METOD                   │
│                                                           │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌──────┐ │
│  │  Baseline  │  │   WACC-    │  │  Capbase-  │  │ KENT │ │
│  │            │  │  skalning  │  │   kedja    │  │ full │ │
│  └────────────┘  └────────────┘  └────────────┘  └──────┘ │
│                                                           │
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
| 4 | **KENT-full** | Läs KENT-fil med nya komponenter för inloggat företag → steg 1-4 → steg 5-8 | 1 | Ja (steg 7) |

### Detaljerad beskrivning per metod

#### Metod 1: Baseline
- **Input:** Data_modeller.xlsx
- **Process:** Ingen - använd som den är
- **Output:** 148 rader med originalvärden
- **Användning:** Referens, eller när användaren inte vill ändra CAPEX.

#### Metod 2: WACC-skalning
- **Input:** Data_modeller.xlsx + ny WACC
- **Process:** 
  - Beräkna skalningsfaktor = ny_wacc / baseline_wacc
  - Skala endast Avkastning-kolumnen (INTE Avskrivning)
  - Räkna om CAPEX = Avskrivning + ny Avkastning
  - Räkna om TOTEX = CAPEX + OPEXp
- **Output:** 148 rader med skalad CAPEX och uppdaterad TOTEX
- **Användning:** Snabb känslighetanalys för ränteförändringar

#### Metod 3: Capbase-kedja
- **Input:** capbase_a.parquet (510k rader för alla 148 företag) + information om ändringar i parametrar (normvärden, livlsängder, etc.) som motsvarar steg i beräkningskedjan
- **Process:**
  - Applicera normvärdejusteringar (valfritt)
  - Applicera livslängdsjusteringar (valfritt)
  - Kör steg 5: Beräkna åldrar och NUAV med nya normvärden
  - Kör steg 6: Beräkna avskrivningar med nya livslängder
  - Kör steg 7: Beräkna avkastning (med WACC som parameter)
  - Kör steg 8: Sammanställ kapitalkostnad (dep_total, return_total, capex) per id_network och år (2024-2027) och periodsumma (kapitalkostnad_periodsumma) som kan användas för efterföljande delar av regumetrica.

- **Output:** 148 rader med omberäknad CAPEX
- **Användning:**  Beräkna kapitalkostnader (avskrivning och avkastning) från capbase_a med justerbara parametrar som WACC, normvärden och livslängder. Output produceras på de aggregeringsnivåer som krävs av efterföljande beräkningssteg. Funktionen run_kent_pipeline() returnerar kapitalkostnader uppdelat på avskrivning och avkastning per id_network och år (2024-2027), samt en periodsumma per id_network för hela tillsynsperioden. Kapitalkostnaderna för år 2024 (tidskoder 229+230) med uppdelning på avskrivning, avkastning och total CAPEX skickas vidare till DEA-analysen där de används som input tillsammans med övriga 147 företag. Periodsumman (Kapitalkostnad_Total) ersätter motsvarande värde i intäktsramsberäkningen och går in i intaktsram_assembly() för att beräkna den slutliga intäktsramen.

#### Metod 4: KENT-full
- **Input:** KENT-fil (1 företag) med nya komponenter (företaget kanske vill se hur en ny investering påverkar kapitalkostnaden och intäktsramen)
- **Process:**
  - Kör steg 1-4: Läs KENT-fil → bygg capbase_a för 1 företag
  - Kör "Metod 3: capbase-kedja" (se ovan) med datan från steg 1-4 för 1 företag.
- **Output:** 148 rader (1 från KENT)
- **Användning:** Företag har nya komponenter och vill se hur det påverkar kapitalkostnaden och intäktsramen

### Kombinationer
- WACC, normvärden och livslängder är **parametrar** som ska appliceras på alla företag. 
- Parametrarna är en del av beräkningskedjan så det finns ingen krock.
- Om WACC + normvärde/livslängd => beräkningskedja 5-8 för ALLA företag
- Om WACC/livslängder/normvärden + KENT-fil => Beräkningskedja steg 1-4 för inloggat företag => ersätt inloggat företags data i capbase_a med det som motsvarar nya KENT-filen, lämna resterade 147 företag orörda => kör beräkningskedja 5-8 med alla 148 företag med nya antaganden om WACC/livslängder/normvärden.


### Data som behövs

| Dataset | Innehåll | Scope | Används av |
|---------|----------|-------|------------|
| Data_modeller.xlsx | DMU, CAPEX (uppdelad på avskrivningar och avkastning), OPEXp, volymer | 148 rader | Baseline, WACC-skalning, DEA |
| capbase_a.parquet | Komponentdata | 510k rader (alla 148 via id_network) | Capbase-kedja|
| KENT-fil | Inrapporterad kapitalbas | 1 företag | KENT-full |
| reconciliation.csv | id_network → DMU mapping | 148 företag | Aggregering |

## NOTERING ANGÅENDE Data_modeller.xlsx
- TOTEX måste skapas som CAPEX + OPEXp
- CAPEX (uppdelad på avskrivningar och avkastning) motsvarar endast kapitalkostnaden för år 2024. Det är därmed viktigt att rätt CAPEX skickas till DEA.

## SLUT PÅ PRE-DEA
1. Dataframe med uppdaterade värden samt metadata med modellspecifikationer finns.

## 2.2 DEA
FYLL PÅ

## 2.3 POST-DEA
### 2.3.1 Beräkningsflöde

1. DEA/Efficiency → Effkrav_proc (årligt effektiviseringskrav)
   Input:  DataFrame med 148 företag
   Output: DataFrame med 148 företag + Effkrav_proc
   Filter: → DataFrame med 1 företag (användarens DMU)
                          ↓
2. Påverkbara kostnader → Applicera effektiviseringskrav
   Input:  DataFrame med 1 företag
   Val:    OPEX eller TOTEX
   Output: DataFrame med 1 företag + årsvisa avdrag (2024-2027)
           Resultat: Paverkbara_Target (efter avdrag)
                          ↓
3. Intäktsram assembly → Summera alla komponenter
   Input:  DataFrame med 1 företag (alla komponenter)
   Output: DataFrame med 1 företag + Intaktsram_Total
           = Kapitalkostnad + Påverkbara + Opåverkbara + Övriga

## KRITISKT
Värdena som används måste vara de uppdaterade/modifierade för caset som beräknats i de olika beräkningskedjorna. Påverkbara_Medelvärde (OPEXp) hämtas från Excel-baseline (kolumn DT), medan Kapitalkostnad_Total beräknas i kent_pipeline.py och används både i TOTEX-metoden och i den slutliga intäktsramen.

# 2.3.2 Påverkbara kostnader - Beräkningskedja

**Syfte:** Tydlig referens för beräkning av påverkbara kostnader med effektiviseringskrav enligt Ei:s metod.

## 2.3.2.1 Variabelmappning

### Input-variabler (från Ei:s Excel)

| Kodnamn | Excel-kolumn | Faktiskt namn | Beskrivning |
|---------|--------------|---------------|-------------|
| `B_raw` | DT | **Påverkbara_Medelvärde** | Medelvärde 2018-2021 påverkbara kostnader (tkr, 4-årsperiod) |
| `Adj` | DU | **Neonjusteringar** | Ändringar där nätföretaget inte separerat yrkandet per år (tkr, 4-årsperiod) |
| `mu_factor` | EF | **Omvandlingsränta** | Parameter för OPEX-beräkning |

Årligt effektiviseringskrav hämtas från dataframe från DEA.

### Mellanvariabler (beräknade)

| Kodnamn | Faktiskt namn | Formel |
|---------|---------------|--------|
| `DT` | **Startvärde** | Påverkbara_Medelvärde (OPEX) eller Påverkbara_Medelvärde + CAPEX/4 (TOTEX) |
| `Delta` | **Årlig_Justering** | Neonjusteringar / 4 |
| `B` | **Årsbas_Effkrav** | Startvärde + Årlig_Justering |
| `Inc_t` | **Årligt_Avdrag** | Avdraget som görs år t |
| `Avdrag_t` | **Kumulativt_Avdrag** | Summa av alla avdrag till och med år t |

### Output-variabler

| Kodnamn | Excel-kolumn | Faktiskt namn | Beskrivning |
|---------|--------------|---------------|-------------|
| `Y_t` | EA-ED | **Påverkbara_Efter_Avdrag** | Påverkbara kostnader efter avdrag för år t |
| `Paverkbara_Target` | EE | **Påverkbara_Periodsumma** | Totalsumma påverkbara kostnader 2024-2027 efter avdrag |

---

## 2.3.2.2. Beräkningskedja

### Steg 1: Definiera startvärden

```
OPEX-metod:
  Startvärde = Påverkbara_Medelvärde

TOTEX-metod:
  Startvärde = Påverkbara_Medelvärde + (Kapitalkostnad_Total / 4)

Årlig_Justering = Neonjusteringar / 4

Årsbas_Effkrav = Startvärde + Årlig_Justering
```

### Steg 2: Beräkna årliga avdrag

För varje år t = 1, 2, 3, 4 (motsvarar 2024, 2025, 2026, 2027):

```
Tillväxtfaktor_t = (1 + Årligt_Effkrav_Procent)^(t-1)

Årligt_Avdrag_t = Årligt_Effkrav_Procent × Årsbas_Effkrav × Tillväxtfaktor_t

Kumulativt_Avdrag_t = Σ(Årligt_Avdrag_i) för i = 1 till t
```

### Steg 3: Beräkna påverkbara kostnader per år

```
Påverkbara_Efter_Avdrag_t = Startvärde - Kumulativt_Avdrag_t + Årlig_Justering
```

### Steg 4: Summera för perioden

```
Påverkbara_Periodsumma = Påverkbara_2024 + Påverkbara_2025 + Påverkbara_2026 + Påverkbara_2027
```

---

## 2.3.2.3 Exempel: REL00886 (Kraftringen Nät AB)

### Input

| Variabel | Värde |
|----------|-------|
| Påverkbara_Medelvärde | 219 438.70 tkr |
| Neonjusteringar | 73 097.00 tkr |
| Årligt_Effkrav_Procent | 0.012661 (1.27%) |

### Steg 1: Startvärden

```
Startvärde = 219 438.70 tkr
Årlig_Justering = 73 097 / 4 = 18 274.25 tkr
Årsbas_Effkrav = 219 438.70 + 18 274.25 = 237 712.95 tkr
```

### Steg 2-3: Årliga beräkningar

| År | t | Tillväxtfaktor | Årligt_Avdrag | Kumulativt_Avdrag | Påverkbara_Efter_Avdrag |
|----|---|----------------|---------------|-------------------|-------------------------|
| 2024 | 1 | 1.0000 | 3 009.64 | 3 009.64 | 234 703.31 tkr |
| 2025 | 2 | 1.0127 | 3 047.75 | 6 057.39 | 231 655.56 tkr |
| 2026 | 3 | 1.0255 | 3 086.33 | 9 143.72 | 228 569.23 tkr |
| 2027 | 4 | 1.0385 | 3 125.40 | 12 269.12 | 225 443.83 tkr |

### Steg 4: Periodsumma

```
Påverkbara_Periodsumma = 234 703.31 + 231 655.56 + 228 569.23 + 225 443.83
                       = 920 371.93 tkr
```

---

## 2.3.2.4 Formler i matematisk notation

### Generell formel

$$\text{Årligt\_Avdrag}_t = e \times B \times (1 + e)^{t-1}$$

$$\text{Kumulativt\_Avdrag}_t = \sum_{i=1}^{t} \text{Årligt\_Avdrag}_i$$

$$\text{Påverkbara\_Efter\_Avdrag}_t = \text{Startvärde} - \text{Kumulativt\_Avdrag}_t + \text{Årlig\_Justering}$$

Där:
- $e$ = Årligt_Effkrav_Procent
- $B$ = Årsbas_Effkrav
- $t$ = År (1-4 för 2024-2027)

---

## 2.3.2.5 Skillnad OPEX vs TOTEX

| Aspekt | OPEX | TOTEX |
|--------|------|-------|
| Startvärde | Påverkbara_Medelvärde | Påverkbara_Medelvärde + CAPEX/4 |
| Effkrav appliceras på | Endast påverkbara driftskostnader | Påverkbara + kapitalkostnader |
| Resultat | Lägre avdrag | Högre avdrag (större bas) |

CAPEX ingår alltid i den slutliga intäktsramen oavsett metod.

---

## 2.3.2.6 Excel-kolumnreferens

| Kolumn | Innehåll |
|--------|----------|
| A | REId (Redovisningsenhet) |
| DT | Medelvärde 2018-2021 påverkbara kostnader |
| DU | Neonjusteringar |
| EA-ED | Påverkbara efter avdrag per år (2024-2027) |
| EE | Totalsumma påverkbara 2024-2027 |
| EF | Omvandlingsränta (mu) |
| EG | Årligt effektiviseringskrav (%) |

---

**Källa:** Ei:s beräkningsmodell för intäktsramar 2024-2027

# 2.4 Intäktsram - Summering och dekomposition

**Syfte:** Tydlig referens för hur intäktsramen beräknas och vilka komponenter som ingår.

---

## 2.4.1 Intäktsramens komponenter

### Huvudformel

```
Intäktsram_Total = Kapitalkostnad_Total
                 + Påverkbara_Periodsumma
                 + Opåverkbara_Kostnader
                 + Övriga_Komponenter
```

### Expanderad formel

```
Intäktsram_Total = Avskrivningar
                 + Avkastning
                 + Påverkbara_Periodsumma
                 + Opåverkbara_Kostnader
                 + Flexibilitetstjänster
                 + Avbrottsersättning_12_24h
                 - Avdrag_Statligt_Stöd
                 + Kvalitetsjustering
```

---

## 2.4.2 Variabelmappning

### Komponenter och källor

| Komponent | Excel-kolumn | Källa | Beskrivning |
|-----------|--------------|-------|-------------|
| **Avskrivningar** | 10 | `kent_pipeline.py` → `period['Avskrivning']` | Kapitalförslitning (tkr, 4-årsperiod) |
| **Avkastning** | 11 | `kent_pipeline.py` → `period['Avkastning']` | Kapitalbindning (tkr, 4-årsperiod) |
| **Kapitalkostnad_Total** | 9 | Beräknad: Avskrivningar + Avkastning | Total kapitalkostnad (tkr, 4-årsperiod) |
| **Påverkbara_Periodsumma** | 4 |  kapitel 2.2 Påverkbara kostnader  | Påverkbara efter effkrav-avdrag (tkr, 4-årsperiod) |
| **Opåverkbara_Kostnader** | 5 | Excel-baseline | Ej påverkbara driftskostnader (tkr, 4-årsperiod) |
| **Flexibilitetstjänster** | 6 | Excel-baseline | Kostnader för flexibilitetstjänster (tkr) |
| **Avbrottsersättning_12_24h** | 7 | Excel-baseline | Avbrottsersättning 12-24 timmar (tkr) |
| **Avdrag_Statligt_Stöd** | 8 | Excel-baseline | Avdrag pga. statligt finansierade anläggningar (tkr) |
| **Kvalitetsjustering** | — | Beräknad (optional) | Justering baserad på leveranskvalitet (tkr) |
| **Intäktsram_Total** | 3 | Beräknad summa | Total intäktsram (tkr, 4-årsperiod) |

---

## 2.4.3. Koppling till beräkningskedjor

### Kapitalkostnad (från kent_pipeline.py)

```
kent_pipeline.run_kent_pipeline(capbase_a, interest_rate=WACC)
    │
    └── period['Kapitalkostnad_Total']  → Intäktsram
        period['Avskrivning']           → Intäktsram (uppdelat)
        period['Avkastning']            → Intäktsram (uppdelat)
```

### Påverkbara kostnader (från 2.2)

```
Påverkbara_Medelvärde (Excel DT)
    │
    ├── Effektiviseringskrav (från DEA)
    │
    └── Påverkbara_Periodsumma  → Intäktsram
```

### Dataflöde

```
┌─────────────────────────────────────────────────────────────────┐
│                         INTÄKTSRAM                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   kent_pipeline.py              Excel-baseline                  │
│   ────────────────              ──────────────                  │
│   Avskrivningar ──────┐         Opåverkbara_Kostnader ────┐    │
│   Avkastning ─────────┤                                   │    │
│                       │         Flexibilitetstjänster ────┤    │
│   ir_calculations.py  │                                   │    │
│   ──────────────────  │         Avbrottsersättning ───────┤    │
│   Påverkbara_Period ──┼────────────────────────────────────┼──► │
│                       │                                   │    │
│                       │         Avdrag_Statligt_Stöd ─────┤    │
│                       │                                   │    │
│                       │         Kvalitetsjustering ───────┘    │
│                       │                                        │
│                       └──────────► INTÄKTSRAM_TOTAL            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
---

## 5. Exempel: REL00001 (Ale El ek. för.)

### Input från Excel-baseline

| Komponent | Värde (tkr) |
|-----------|-------------|
| Påverkbara kostnader | 176 859.80 |
| Opåverkbara kostnader | 108 280.00 |
| Flexibilitetstjänster | 0 |
| Avbrottsersättning 12-24h | 0 |
| Kapitalkostnad | 237 713.01 |
| - varav Avskrivningar | 125 216.23 |
| - varav Avkastning | 112 496.78 |

### Beräkning

```
Intäktsram_Total = 237 713.01 + 176 859.80 + 108 280.00 + 0 + 0
                 = 522 852.81 tkr
```

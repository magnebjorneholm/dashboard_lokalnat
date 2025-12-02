# REGUMETRICA DATASET & DATAFLÖDE GUIDE
**Version:** 2.0  
**Datum:** 2024-12-01  
**Syfte:** Komplett kartläggning av alla dataset, kolumner och dataflöde genom pipeline

---

## INNEHÅLLSFÖRTECKNING

1. [Dataset-inventering](#1-dataset-inventering)
2. [Dataflöde genom pipeline](#2-dataflöde-genom-pipeline)
3. [Beräkningskedja steg 1-8](#3-beräkningskedja-steg-1-8)
4. [Tidskod-mappning](#4-tidskod-mappning)
5. [Kolumnanvändning per pipeline-stage](#5-kolumnanvändning-per-pipeline-stage)

---

## 1. DATASET-INVENTERING

### 1.1 Data_modeller.xlsx
**Källa:** Ei's bearbetade data för DEA-modeller  
**Scope:** 148 företag (alla lokalnät i Sverige)  
**Tidsperiod:** År 2024  
**Användning:** Baseline inputs för DEA-analys

#### Sheet: "Körning"
**Dimensioner:** 148 rader × 12 kolumner

| Kolumn | Datatyp | Beskrivning | Enhet | Pipeline-användning |
|--------|---------|-------------|-------|---------------------|
| DMU | int | Decision Making Unit nummer (1-148) | - | ID-matching, DEA-analys |
| REId | string | Nätverks-ID (REL00001, etc.) | - | ID-matching |
| Företag | string | Företagsnamn | - | Metadata |
| OPEXp | float | Påverkbara operativa kostnader | tkr | DEA input (optional) |
| CAPEX | float | Total kapitalkostnad för 2024 | tkr | DEA input (mandatory) |
| Avskrivning | float | Avskrivningar 2024 | tkr | Baseline kapitalkostnad |
| Avkastning | float | Avkastning 2024 | tkr | Baseline kapitalkostnad |
| CU | float | Antal kunder | antal | DEA output |
| MW | float | Installerad effekt | MW | DEA output (optional) |
| NS | float | Nätlängd | km | DEA output |
| MWhl | float | Överförd energi låglast | MWh | DEA output (optional) |
| MWhh | float | Överförd energi höglast | MWh | DEA output (optional) |

**Beräknade kolumner (i kod):**
- `TOTEX = OPEXp + CAPEX`

**Kritiska samband:**
- `CAPEX = Avskrivning + Avkastning` (för 2024)
- CAPEX-värdet ska kunna uppdateras via WACC-skalning eller full beräkningskedja

---

### 1.2 EIs_DEA.xlsx
**Källa:** Ei's officiella DEA-resultat för tillsynsperioden 2024-2027  
**Scope:** 148 företag  
**Användning:** Baseline efficiency och effektiviseringskrav

#### Sheet: "Körning"
**Dimensioner:** 148 rader × 7 kolumner

| Kolumn | Datatyp | Beskrivning | Enhet | Pipeline-användning |
|--------|---------|-------------|-------|---------------------|
| DMU | int | Decision Making Unit nummer (1-148) | - | ID-matching |
| REId | string | Nätverks-ID | - | ID-matching |
| Företag | string | Företagsnamn | - | Metadata |
| Effektivitet | float | Teknisk effektivitet (0-1) | - | DEA-resultat |
| Supereffektivitet | float | Super-efficiency score | - | DEA-resultat |
| potential | float | Effektiviseringspotential (0-1) | - | Input till effektiviseringskrav |
| Effkrav_proc | float | Årligt effektiviseringskrav | procent | Baseline effektiviseringskrav |

**Kritiska samband:**
- `Effkrav_proc` beräknas från `potential` med trunkering och outlier-hantering
- Outliers får fast effektiviseringskrav om 1%

---

### 1.3 capbase_a.parquet / capbase_a_exempel.xlsx
**Källa:** Ei's KENT-inrapportering från alla företag  
**Scope:** Alla anläggningskomponenter för alla 148 företag  
**Användning:** Beräkningskedja steg 5-8 (åldrar, avskrivningar, avkastning)

**OBS:** `capbase_a_exempel.xlsx` är endast representativt exempel för ETT företag (id_network=886)

#### Struktur
**Dimensioner (full data):** ~510,000 rader × 33 kolumner  
**Dimensioner (exempel):** Varierar per företag

| Kolumn | Datatyp | Beskrivning | Enhet | Pipeline-användning |
|--------|---------|-------------|-------|---------------------|
| id_comptype | string | Komponenttyp-ID | - | Metadata |
| id_component | int | Unik komponent-ID | - | Primary key |
| id_network | int | Nätverks-ID (1-159) | - | Foreign key till DMU |
| id_network_string | string | Nätverks-ID som string (REL00001) | - | Mapping |
| id_firm | int | Företags-ID | - | Företagsstruktur |
| time_from_missing | bool | Flagga om time_from saknas | - | Validering |
| time_from | int | Tidskod när komponent togs i bruk | tidskod | Åldersberäkning |
| time_to | int | Tidskod när komponent utrangeras | tidskod | Livslängd |
| time_invest | int | Tidskod för investering | tidskod | Investeringsålder |
| time_acquired | int | Tidskod när förvärvad | tidskod | Förvärvshantering |
| cat_encode | int | Kategori-encode (1-17) | - | Mapping till ekdep/maxdep |
| subcat_encode | int | Subkategori-encode | - | Detaljerad kategorisering |
| count_comp | int | Antal komponenter | antal | Aggregering |
| cat | string | Kategorinamn | - | Metadata |
| subcat | string | Subkategorinamn | - | Metadata |
| techspec | string | Teknisk specifikation | - | Metadata |
| volt | float | Spänningsnivå | kV | Teknisk spec |
| normvärde | float | Normvärde från Ei's lista | kr | Värdering |
| owned | int | Ägd (1) eller hyrd (0) | - | Ägandeform |
| nuav | float | Nuanskaffningsvärde | kr | Värdering |
| annatskäligtvärde | float | Annat skäligt värde | kr | Alternativ värdering |
| anskaffningsvärde | float | Ursprungligt anskaffningsvärde | kr | Alternativ värdering |
| rapporteradnuav | float | Rapporterat NUAV | kr | Validering |
| bokförtvärde | float | Bokfört värde | kr | Alternativ värdering |
| erapportstatus | string | Rapportstatus | - | Metadata |
| capbase_existing | int | Befintlig (1) eller investering (0) | - | Typ av komponent |
| invest | float | Investeringsbelopp | kr | Framtida investering |
| value_invest | float | Investeringsvärde | kr | Framtida investering |
| level | string | Lokal/Regional | - | Företagsnivå |
| vtype | string | Värderingstyp | - | Metod |
| nuav_2022 | float | **NUAV i 2022 års prisnivå** | kr | **Huvudinput till beräkningar** |
| ekdep | int | Ekonomisk avskrivningstid | halvår | Beräknad från cat_encode |
| maxdep | int | Maximal avskrivningstid | halvår | Beräknad från cat_encode |

**Livslängdsparametrar per kategori:**

| cat_encode | Beskrivning | ekdep (halvår) | maxdep (halvår) |
|------------|-------------|----------------|-----------------|
| 1-4 | Kablar och ledningar | 100 | 124 |
| 5 | Mätarutrustning | 20 | 24 |
| 6 | Stationer | 60 | 74 |
| 7 | Transformatorer | 80 | 100 |
| 8 | Stolpar och master | 120 | 150 |
| 9-11 | Fördelning och skydd | 80-100 | 100-124 |
| 12 | IT-system | 20 | 24 |
| 13-14 | Manöverutrustning | 80 | 100 |
| 15 | Fastigheter | 30 | 36 |
| 16-17 | Övriga anläggningar | 80-100 | 100-124 |

**Kritiska beräknade kolumner (skapas i steg 5-8):**
- `age_component_{time}` - Ålder vid tidskod {time}
- `nuav_ord_{time}` - NUAV ordinarie vid tidskod {time}
- `nuav_tail_{time}` - NUAV svans vid tidskod {time}
- `dep_ord_{time}` - Avskrivning ordinarie
- `dep_tail_{time}` - Avskrivning svans
- `return_ord_{time}` - Avkastning ordinarie
- `return_tail_{time}` - Avkastning svans

---

### 1.4 Löpande_kostnader_från_SDF_2024-27.xlsx (SDF)
**Källa:** Ei's beräknade intäktsram från SDF-systemet  
**Scope:** 148 lokala företag + några regionala  
**Tidsperiod:** Hela perioden 2024-2027  
**Användning:** Baseline för hela intäktsramen inkl. påverkbara, opåverkbara, kapitalkostnader

#### Sheet 1: "IR 2024-2027"
**Dimensioner:** 148+ rader × 12 kolumner

| Kolumn | Datatyp | Beskrivning | Enhet | Pipeline-användning |
|--------|---------|-------------|-------|---------------------|
| REId | string | Nätverks-ID | - | ID-matching |
| Lokal/ Region | string | L eller R | - | Företagstyp |
| (Unnamed) | - | Tom kolumn | - | - |
| (tkr, 2022 års prisnivå) BERÄKNAD INTÄKTSRAM | float | Total intäktsram perioden | tkr | **Baseline intäktsram total** |
| Påverkbara kostnader | float | Påverkbara totalt perioden | tkr | Baseline påverkbara |
| Opåverkbara kostnader | float | Opåverkbara totalt perioden | tkr | Baseline opåverkbara |
| Kostnader för flexibilitetstjänster | float | Flexibilitetstjänster perioden | tkr | Baseline flex |
| Avbrottsersättning 12-24 timmar | float | Avbrottsersättning perioden | tkr | Baseline avbrott |
| Avdrag av kapitalkostnader pga anläggningar med statligt stöd | float | Avdrag statligt stöd | tkr | Baseline avdrag |
| Kapitalkostnad | float | Total kapitalkostnad perioden | tkr | **Baseline kapitalkostnad** |
| -varav Kapital-förslitning | float | Avskrivningar perioden | tkr | **Baseline avskrivningar** |
| varav Kapital-bindning | float | Avkastning perioden | tkr | **Baseline avkastning** |

**Kritiska samband:**
- `INTÄKTSRAM = Påverkbara + Opåverkbara + Flexibilitet + Avbrott - Avdrag + Kapitalkostnad`
- `Kapitalkostnad = Kapital-förslitning + Kapital-bindning`

#### Sheet 2: "Opåverkbara"
**Dimensioner:** 148+ rader × 36 kolumner

**Huvudkolumner:**
| Kolumn | Beskrivning | Tidsdimension | Pipeline-användning |
|--------|-------------|---------------|---------------------|
| ReId | Nätverks-ID | - | ID-matching |
| Unnamed: 1 | Tom | - | - |
| Företag (exkl. SvK) | Företagsnamn | - | Metadata |
| KENT - Kostnader för att täcka nätförluster, inköp | Nätförluster inköp | 4 kolumner (2024-2027) | Baseline opåverkbara |
| KENT - Kostnader för att täcka nätförluster, egen produktion | Nätförluster egen | 4 kolumner (2024-2027) | Baseline opåverkbara |
| KENT - Kostnader för abonnemang till överliggande nät | Abonnemang | 4 kolumner (2024-2027) | Baseline opåverkbara |
| KENT - Kostnader för anslutningar till överliggande nät | Anslutningar | 4 kolumner (2024-2027) | Baseline opåverkbara |
| KENT - Ersättning till produktionsanläggning (nätnytto) | Nätnyttoersättning | 4 kolumner (2024-2027) | Baseline opåverkbara |
| KENT - Kostnader för myndighetsavgifter | Myndighetsavgifter | 4 kolumner (2024-2027) | Baseline opåverkbara |
| KENT - Kostnader för nätkapacitetsreserv | Nätkapacitetsreserv | 4 kolumner (2024-2027) | Baseline opåverkbara |
| Totala opåverkbara kostnader (prognos) per år | Summa per år | 4 kolumner (2024-2027) | Baseline opåverkbara per år |
| Totala opåverkbara kostnader (prognos) per period | Summa perioden | 1 kolumn | **Baseline opåverkbara total** |

**Struktur per kostnadskategori:**
- 4 kolumner: År 2024, 2025, 2026, 2027
- Enhet: tkr i 2022 års prisnivå

#### Sheet 3: "Påverkbara"
**Dimensioner:** 148+ rader × 137 kolumner (!)

**Struktur:** Mycket komplex med många "Unnamed" kolumner. Varje kostnadskategori har 4 kolumner (2024-2027).

**Huvudkategorier (varje med 4 årliga kolumner):**

1. **Kostnader från årsrapport:**
   - RR7320 Transitering och inköp av kraft
   - RR73120 Råvaror och förnödenheter
   - RR73130 Övriga externa kostnader
   - RR73140 Personalkostnader
   - RR73180 Övriga rörelsekostnader
   - **Summa Kostnader** (4 kolumner)

2. **Avgår:**
   - RR71120 Förändring av varulager
   - RR71140 Aktiverat arbete för egen räkning
   - TN630450/TN730401 Kostnader nätförluster inköp
   - TN630451/TN730402 Kostnader nätförluster egen produktion
   - TN630100/TN730150 Abonnemang överliggande nät
   - TN630150/TN730100 Anslutning överliggande nät
   - TN630500/TN730403 Nätnyttoersättning
   - RR7323 Ersättning från överliggande nät avbrott
   - KENT Avbrottsersättning från överliggande nät
   - RR7324 Myndighetsavgifter
   - KENT Kostnader åldersbestämning investeringar
   - KENT Nätkapacitetsreserv
   - KENT Avbrottsersättning till kund ≤24h
   - KENT Avbrottsersättning till kund >24h
   - KENT Leasing/hyra anläggningar i kapitalbasen
   - **Summa avgår** (4 kolumner)

3. **Påverkbara kostnader:**
   - Påverkbara kostnader (4 kolumner)
   - KENT Utgående bokfört värde (4 kolumner)
   - KENT Årets avskrivningar (4 kolumner)
   - Kapitalkostnad för anläggningar ej i kapitalbasen (4 kolumner)
   - Ändringar pga yrkande 2018-2021 (4 kolumner)
   - **Totala påverkbara kostnader** (4 kolumner)

4. **Indexering och effektiviseringskrav:**
   - Index L/R (4 kolumner)
   - Summa påverkbara i 2022 års prisnivå (4 kolumner)
   - Medelvärde 2018-2021 påverkbara kostnader (1 kolumn)
   - Ändringar oseparerade yrkanden (1 kolumn)
   - Avdrag för effektiviseringskrav (beräknat från medel) (4 kolumner)
   - **Totalt avdrag effektiviseringskrav 2024-2027** (1 kolumn)
   - Påverkbara efter avdrag effektiviseringskrav (4 kolumner)
   - **Totalsumma påverkbara kostnader perioden 2024-2027** (1 kolumn)

5. **Parametrar:**
   - Parametrar OPEX Omvandlingsränta (1 kolumn)
   - Parametrar OPEX Årligt eff.krav procent (1 kolumn)

**Kritiska kolumner för pipeline:**
- `Totalsumma påverkbara kostnader för perioden 2024-2027` → Baseline påverkbara total
- `Påverkbara löpande kostnader efter avdrag för effektiviseringskrav` (4 år) → Per år efter effektiviseringskrav
- `Parametrar OPEX Årligt eff.krav procent` → Effektiviseringskrav per företag

#### Sheet 4 & 5: "Påverkbara Halvnya" och "Påverkbara Prognos"
Samma struktur som "Påverkbara" men för andra företagstyper.

---

### 1.5 facit_paverkbara.xlsx
**Källa:** Testfil för validering  
**Scope:** ETT representativt företag (REL00886)  
**Användning:** Testning och validering av beräkningar

**OBS:** Detta är INTE ett komplett facit för alla företag, utan en testfil för att verifiera att beräkningar är korrekta.

#### Sheet: "Påverkbara"
**Dimensioner:** 2 rader × 137 kolumner

**Struktur:** Identisk med SDF "Påverkbara" sheet, men endast för ett företag.

**Användning:**
- Rad 1: Kolumnrubriker
- Rad 2: Företag REL00886 data

**Testmetodik:**
- Kör beräkningar på REL00886
- Jämför output med värden i denna fil
- Verifiera Excel-exakt precision

---

### 1.6 reconciliation_id_network_firm_dmu.csv
**Källa:** Manuellt skapad mappningsfil  
**Scope:** 159 rader (alla nätverksenheter)  
**Användning:** ID-mappning mellan olika system

#### Struktur
**Dimensioner:** 159 rader × 6 kolumner

| Kolumn | Datatyp | Beskrivning | Exempel | Pipeline-användning |
|--------|---------|-------------|---------|---------------------|
| id_network | int | Numeriskt nätverks-ID | 1, 3, 4, 5... | Capbase_a foreign key |
| id_network_string | string | String-format nätverks-ID | REL00001, REL00003 | REId matching |
| id_firm | int | Företags-ID | Olika från id_network | Företagsstruktur |
| DMU | int | Decision Making Unit nummer | 1-148 | DEA-matching |
| in_reference | bool | Finns i referensdata | True/False | Validering |
| in_data_modeller | bool | Finns i Data_modeller.xlsx | True/False | Validering |

**Kritiska samband:**
- `id_network` (1-159) ≠ `DMU` (1-148)
- Vissa id_network har samma id_firm (koncernstruktur)
- Vissa id_network saknar DMU (ej med i DEA)
- 148 unika DMU, 159 unika id_network, 154 unika id_firm

**Användning i pipeline:**
1. Översätt REId (REL00001) → id_network (1)
2. Översätt id_network → DMU för DEA-matching
3. Översätt DMU → id_network för capbase-matching

---

## 2. DATAFLÖDE GENOM PIPELINE

### 2.1 Pipeline-översikt

```
┌─────────────────────────────────────────────────────────────────┐
│                        BASELINE DATA                              │
│  Data_modeller.xlsx + EIs_DEA.xlsx + SDF + capbase_a.parquet   │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                         PRE-DEA STAGE                            │
│              Förbereda DataFrame (148 rader)                     │
│                                                                   │
│  Inputs: CAPEX, OPEXp, Volumes (alla 148 företag)              │
│                                                                   │
│  4 metoder:                                                      │
│  1. Baseline         → Data_modeller.xlsx (ingen ändring)      │
│  2. WACC-skalning    → Skala Avkastning med ny WACC            │
│  3. Parameter-ändring → Ändra normvärden/livslängder           │
│                         → Kör steg 5-8 för ALLA 148             │
│  4. KENT-fil         → Ladda företagets KENT                   │
│                         → Kör steg 1-4 för 1 företag            │
│                         → (Optional) Parameter-ändring          │
│                         → Kör steg 5-8 för ALLA 148             │
│                                                                   │
│  Output: df_predea [148 × (CAPEX, OPEXp, CU, MW, NS, ...)]    │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                          DEA STAGE                               │
│               Analysera effektivitet (148 företag)              │
│                                                                   │
│  Inputs:                                                         │
│    - CAPEX (eller TOTEX) som input                              │
│    - CU, MW, NS, MWhl, MWhh som outputs                        │
│                                                                   │
│  Process:                                                        │
│    1. Super-efficiency DEA                                      │
│    2. Identifiera outliers (IQR-metod)                         │
│    3. Omberäkning utan outliers                                │
│                                                                   │
│  Output: df_dea [148 × (efficiency, potential, is_outlier)]   │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                        POST-DEA STAGE                            │
│          Beräkna intäktsram för inloggat företag                │
│                                                                   │
│  Steg 1: EXTRAKTION                                             │
│    Filtrera DEA-output till 1 rad (inloggat företags REId)     │
│    → potential, is_outlier                                      │
│                                                                   │
│  Steg 2: EFFEKTIVISERINGSKRAV                                   │
│    IF is_outlier → Effkrav = 1% (fast)                         │
│    ELSE → calculate_effkrav_from_potential(potential)          │
│                                                                   │
│  Steg 3: PÅVERKBARA KOSTNADER                                   │
│    Baseline: SDF "Påverkbara" sheet                            │
│    Applicera effektiviseringskrav:                              │
│      - OPEX-metod: På OPEXp                                     │
│      - TOTEX-metod: På (OPEXp + CAPEX)                         │
│                                                                   │
│  Steg 4: INTÄKTSRAM                                             │
│    Summera: Påverkbara + Opåverkbara + Kapitalkostnad +        │
│             Flexibilitet + Avbrott - Avdrag                     │
│                                                                   │
│  Output: Intäktsram_Total per år (2024-2027) och periodsumma  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Pre-DEA: Detaljerat dataflöde

#### Metod 1: Baseline (ingen ändring)

```
Data_modeller.xlsx
    ├── DMU, REId, Företag, CAPEX, OPEXp, CU, MW, NS, MWhl, MWhh
    │
    └→ df_predea_baseline [148 rader]
       ├── CAPEX (2024)
       ├── OPEXp (2024)
       └── Volumes (CU, MW, NS, MWhl, MWhh)
```

#### Metod 2: WACC-skalning

```
Data_modeller.xlsx
    ├── CAPEX = Avskrivning + Avkastning
    │
    └→ Ny WACC från CAPM
       │
       ├── Avskrivning (oförändrad)
       ├── Avkastning_NY = Avkastning_BASELINE × (WACC_NY / WACC_BASELINE)
       │
       └→ CAPEX_NY = Avskrivning + Avkastning_NY
          │
          └→ df_predea_wacc [148 rader med uppdaterad CAPEX]
```

**Formel:**
- WACC_BASELINE = 0.0453 (Ei's baseline)
- WACC_NY = beräknad från CAPM
- Skalningsfaktor = WACC_NY / WACC_BASELINE
- CAPEX_NY = Avskrivning + (Avkastning × Skalningsfaktor)

#### Metod 3: Parameter-ändring (normvärden/livslängder)

```
capbase_a.parquet (ALLA 148 företag)
    │
    ├→ apply_normvalue_adjustments()
    │   ├── Ändra 'normvärde' för utvalda kategorier/subkategorier
    │   └── Uppdatera nuav_2022 baserat på nya normvärden
    │
    ├→ apply_lifetime_adjustments()
    │   ├── Ändra 'ekdep' och 'maxdep' för utvalda kategorier
    │   └── Uppdatera livslängdsparametrar
    │
    └→ Beräkningskedja steg 5-8 (för ALLA 148)
       ├── Steg 5: calculate_ages_and_nuav()
       ├── Steg 6: calculate_depreciation()
       ├── Steg 7: calculate_returns(wacc)
       └── Steg 8: compile_capcost()
          │
          └→ Se till att alla CAPEX-värden (total, avkastning och avskrivning) finns för varje år (2024 ska skickas till DEA) samt som periodsumma (som ska till intäktsramen)
```

#### Metod 4: KENT-fil (ett företag)

```
Användarens KENT Excel-fil (ett företag)
    │
    └→ Beräkningskedja steg 1-4
       ├── Steg 1: read_kent_excel()
       │   ├── Sheet "Normvärde"
       │   ├── Sheet "Övriga värderingsmetoder"
       │   └── Sheet "Investeringar"
       │
       ├── Steg 2: create_mappings()
       │   ├── Kategori-encoding (cat_encode)
       │   └── Subkategori-encoding (subcat_encode)
       │
       ├── Steg 3: apply_all_encodings()
       │   ├── Tidskodsberäkning (time_from, time_invest)
       │   └── NUAV-konsolidering (nuav_2022)
       │
       └── Steg 4: build_capbase_a_from_kent()
          ├── Lägg till id_network
          ├── Lägg till ekdep/maxdep från cat_encode
          └→ capbase_a_user (ett företag)
             │
             ├→ (Optional) Parameter-ändringar
             │
             └→ Ersätt i capbase_a för ALLA 148
                │
                ├── capbase_all = baseline.copy()
                ├── capbase_all[id_network == user] = capbase_a_user
                │
                └→ Beräkningskedja steg 5-8 (för ALLA 148)
                   │
                   └→ df_predea_kent [148 rader med användarens CAPEX]
```

### 2.3 DEA: Detaljerat dataflöde

```
df_predea [148 rader]
    │
    ├── Inputs:
    ├── Outputs:
    │
    └→ DEA-modell
       │
       ├── Steg 1: Super-efficiency DEA
       │   ├── För varje DMU i, beräkna maximal radiell expansion
       │   └→ super_efficiency[i] = θ*
       │
       ├── Steg 2: Identifiera outliers
       │   ├── IQR-metod: Q1 - 1.5×IQR, Q3 + 1.5×IQR
       │   └→ is_outlier[i] = True/False
       │
       └── Steg 3: Omberäkning utan outliers
          ├── Exkludera outliers från referensset
          ├── Beräkna efficiency för alla (inkl outliers)
          └→ potential[i] = 1 - efficiency[i]
             │
             └→ df_dea [148 rader]
                ├── DMU
                ├── efficiency
                ├── super_efficiency
                ├── potential
                └── is_outlier
```

### 2.4 Post-DEA: Detaljerat dataflöde

#### Steg 1: Extraktion

```
df_dea [148 rader]
    │
    └→ Filtrera till inloggat företags DMU
       │
       └→ entity_dea [1 rad]
          ├── potential
          └── is_outlier
```
#### Steg 2: Effektiviseringskrav

```
potential, is_outlier
    │
    ├→ IF is_outlier == True
    │   └→ Effkrav = 1.0% (fast krav) eller det krav som användaren vill ge outliers.
    │
    └→ ELSE
       └→ calculate_effkrav_from_potential(potential)
          ├── Trunkering vid 0 och 1
          ├── Applicera formel
          └→ Effkrav (procent)
```

#### Steg 3: Påverkbara kostnader

```
Se "2.3.2 Påverkbara kostnader - Beräkningskedja" i Regumetrica_full_arkitektur.md
```

#### Steg 4: Intäktsram

```
SDF komponenter [1 företag]
    │
    ├── Påverkbara (efter effektiviseringskrav)
    ├── Opåverkbara (baseline)
    ├── Kapitalkostnad (från Pre-DEA steg eller baseline)
    ├── Flexibilitetstjänster (baseline)
    ├── Avbrottsersättning (baseline)
    └── Avdrag statligt stöd (baseline)
       │
       └→ Intäktsram_Total[år] = 
          Påverkbara[år] + 
          Opåverkbara[år] + 
          Kapitalkostnad[år] + 
          Flexibilitet[år] + 
          Avbrott[år] - 
          Avdrag[år]
          │
          └→ Intäktsram per år [2024, 2025, 2026, 2027]
             Intäktsram total (periodsumma)
```

## 3. BERÄKNINGSKEDJA STEG 1-8

### 3.1 Steg 1-4: KENT → capbase_a (capbase_prep.py)

#### Steg 1: Läs KENT Excel

**Funktion:** `read_kent_excel(file_obj)`

**Input:** KENT Excel-fil (uploaded file object via st.file_uploader)

**Output:** Dict med 4 DataFrames:
- `'normvarde'`: Befintliga komponenter med normvärdemetoden
- `'ovriga'`: Befintliga komponenter med andra metoder (anskaffning, bokfört, annat skäligt)
- `'investeringar'`: Planerade investeringar/utrangeringar
- `'uppslagsvarden'`: Kategori-mappningar från Excel

**Process:**

1. **Läs "Normvärde" sheet:**
   - Header på rad 2 (rad 1 innehåller kategorier)
   - Kolumner: Anl.-kategori, Kod, Typ av anläggning, Antal, Rådighet, Ursprungligen tagen i bruk, etc.
   - Filtrera bort tomma rader (där 'kod' är NaN)
   - Lägg till: `capbase_existing = 1`, `metod = 'normvärde'`

2. **Läs "Övriga värderingsmetoder" sheet:**
   - Struktur identisk med Normvärde
   - Kolumner inkluderar värderingsmetod (Anskaffningsvärde, Bokfört värde, Annat skäligt)
   - Lägg till: `capbase_existing = 1`, `metod = {värderingsmetod}`

3. **Läs "Investeringar" sheet:**
   - Header på rad 2
   - Kolumner: Tidpunkt, Typ av förändring, Anl.-kategori, Antal, Värde, etc.
   - Typ av förändring: "Investering" eller "Utrangering"
   - Lägg till: `capbase_existing = 0`, `metod = 'future_invest'`

4. **Läs "Uppslagsvärden" sheet:**
   - Kategori-mappningar mellan Anläggningskategori och Typ av anläggning
   - Används för att skapa `cat_encode` och `subcat_encode`

**Kritiska felhanteringar:**
- Om "Ursprungligen tagen i bruk" saknas men "År saknas" INTE är markerat → Varning
- Om både normvärde och övriga sheets är tomma → Varning

#### Steg 2: Skapa mappningar

**Funktion:** `create_mappings(kent_data)`

**Input:** Dict från steg 1

**Output:** Dict med mappnings-DataFrames:
- `'cat_mapping'`: Anläggningskategori → cat_encode
- `'subcat_mapping'`: (Anläggningskategori, Typ av anläggning) → subcat_encode

**Process:**

1. **Kategori-encoding:**
   - Läs "uppslagsvarden" DataFrame
   - Extrahera unika anläggningskategorier
   - Tilldela cat_encode (1-17) enligt Ei's standard

2. **Subkategori-encoding:**
   - För varje (kategori, typ av anläggning) par
   - Tilldela subcat_encode

**Ei's kategori-mappning:**
```python
CATEGORY_MAPPING = {
    'Kablar och ledningar, högspänning': 1,
    'Kablar och ledningar, lågspänning': 2,
    'Luftledningar, högspänning': 3,
    'Luftledningar, lågspänning': 4,
    'Mätarutrustning': 5,
    'Stationer': 6,
    'Transformatorer i mark': 7,
    'Stolpar och master': 8,
    'Kopplings- och fördelningsanläggningar, högspänning': 9,
    'Kopplings- och fördelningsanläggningar, lågspänning': 10,
    'Skydds- och övervakningsutrustning': 11,
    'IT-system för drift, underhåll och mätning': 12,
    'Fjärrstyrningsutrustning': 13,
    'Manöverutrustning': 14,
    'Fastigheter': 15,
    'Övriga maskiner och inventarier': 16,
    'Andra anläggningar': 17
}
```

#### Steg 3: Kombinera och standardisera

**Funktion:** `apply_all_encodings(combined, mappings)`

**Input:** 
- `combined`: Concatenated DataFrame från normvärde + övriga + investeringar
- `mappings`: Från steg 2

**Output:** DataFrame med standardiserade kolumner

**Process:**

1. **Applicera kategori-encoding:**
   - Merge med cat_mapping på 'anl_kat'
   - Merge med subcat_mapping på ('anl_kat', 'anl_typ')

2. **Beräkna tidskoder:**
   - `time_from`: Konvertera "Ursprungligen tagen i bruk" (år) till tidskod
   - Formel: `time = (year - 1910) * 2`
   - Om halvår 2: `time = (year - 1910) * 2 + 1`
   - För investeringar: `time_invest` från "Tidpunkt"

3. **Konsolidera värderingar till nuav_2022:**
   - **Normvärde:** `nuav_2022 = nuav` (från KENT)
   - **Anskaffningsvärde:** `nuav_2022 = nuav` (redan beräknad i Excel)
   - **Bokfört värde:** `nuav_2022 = nuav`
   - **Annat skäligt värde:** `nuav_2022 = nuav`
   - **Investeringar:** `nuav_2022 = värde`

4. **Hantera investerings-tecken:**
   - Om "Typ av förändring" = "Investering" → `invest = +1`
   - Om "Typ av förändring" = "Utrangering" → `invest = -1`
   - `nuav_2022 = nuav_2022 × invest`

5. **Standardisera rådighet:**
   - Om "Rådighet" = "Ägd" → `owned = 1`
   - Annars → `owned = 0`

6. **Lägg till komponent-ID:**
   - `id_component = range(1, len(df) + 1)`

#### Steg 4: Bygg capbase_a

**Funktion:** `build_capbase_a_from_kent(kent_file, network_id)`

**Input:**
- `kent_file`: KENT Excel-fil
- `network_id`: id_network för detta företag

**Output:** capbase_a DataFrame redo för steg 5-8

**Process:**

1. **Kör steg 1-3**
2. **Lägg till network_id:**
   - `id_network = network_id` (från input parameter)
3. **Lägg till livslängdsparametrar:**
   - `ekdep = DEPRECIATION_PARAMS[cat_encode]['ekdep']`
   - `maxdep = DEPRECIATION_PARAMS[cat_encode]['maxdep']`
4. **Välj finala kolumner:**
   - Obligatoriska: `id_component, time_from, time_invest, capbase_existing, ekdep, maxdep, nuav_2022, cat_encode, id_network, invest`
   - Extra: `cat, subcat, subcat_encode, antal, metod`
5. **Validera:**
   - Alla obligatoriska kolumner finns
   - Inga negativa nuav_2022 (förutom utrangeringar)
   - Alla cat_encode har ekdep/maxdep

**Validering:**
```python
def validate_capbase_a(df):
    errors = []
    
    # Obligatoriska kolumner
    required = ['id_component', 'time_from', 'nuav_2022', 'ekdep', 'maxdep', 'cat_encode']
    missing = [c for c in required if c not in df.columns]
    if missing:
        errors.append(f"Missing columns: {missing}")
    
    # Negativa NUAV (utom utrangeringar)
    mask = (df['nuav_2022'] < 0) & (df['invest'] != -1)
    if mask.any():
        errors.append(f"Negative nuav_2022 for {mask.sum()} non-retirement components")
    
    # Saknade livslängder
    if df['ekdep'].isna().any() or df['maxdep'].isna().any():
        errors.append("Missing ekdep or maxdep values")
    
    return {
        'valid': len(errors) == 0,
        'errors': errors
    }
```

### 3.2 Steg 5: Beräkna åldrar och NUAV (kent_pipeline.py)

**Funktion:** `calculate_ages_and_nuav(df)`

**Input:** capbase_a från steg 4

**Output:** capbase_a med tillagda kolumner för tidskoder 229-236 (2024-2027)

**Process för varje tidskod t ∈ [229, 230, ..., 236]:**

1. **Beräkna komponentålder:**
   ```python
   age_component_{t} = t - time_from
   ```

2. **Beräkna investeringsålder:**
   ```python
   age_component_{t}_invest = t - time_invest  # Endast för investeringar (capbase_existing = 0)
   ```

3. **Bestäm om komponent är i "ordinarie" avskrivning:**
   ```python
   base_ord_{t} = 1 if:
       (capbase_existing == 1 AND age_component_{t} <= ekdep AND age_component_{t} > 0) OR
       (capbase_existing == 0 AND age_component_{t}_invest <= ekdep AND age_component_{t}_invest > 0)
   else:
       base_ord_{t} = 0
   ```

4. **Beräkna NUAV ordinarie:**
   ```python
   nuav_ord_{t} = nuav_2022 × base_ord_{t}
   ```

5. **Bestäm om komponent är i "svans" avskrivning:**
   ```python
   base_tail_{t} = 1 if:
       (capbase_existing == 1 AND ekdep < age_component_{t} <= maxdep) OR
       (capbase_existing == 0 AND ekdep < age_component_{t} <= maxdep AND time_invest < t)
   else:
       base_tail_{t} = 0
   ```

6. **Beräkna NUAV svans:**
   ```python
   nuav_tail_{t} = nuav_2022 × base_tail_{t}
   ```

7. **Aggregera per kategori och nätverk:**
   ```python
   sum_nuav_ord_{t} = SUM(nuav_ord_{t}) / 1000  # Per (cat_encode, id_network)
   sum_nuav_tail_{t} = SUM(nuav_tail_{t}) / 1000  # Per (cat_encode, id_network)
   ```

**Resultat:** DataFrame med nya kolumner:
- `age_component_{229-236}`
- `age_component_{229-236}_invest`
- `base_ord_{229-236}`
- `nuav_ord_{229-236}`
- `base_tail_{229-236}`
- `nuav_tail_{229-236}`
- `sum_nuav_ord_{229-236}`
- `sum_nuav_tail_{229-236}`

### 3.3 Steg 6: Beräkna avskrivningar

**Funktion:** `calculate_depreciation_single_dmu(df)` eller `calculate_depreciation(df)`

**Input:** DataFrame från steg 5

**Output:** Dict med avskrivningar per tidskod

**Process för varje tidskod t ∈ [229, 230, ..., 236]:**

1. **Beräkna avskrivning ordinarie:**
   ```python
   dep_ord_{t} = (2 / ekdep) × sum_nuav_ord_{t}
   ```

2. **Beräkna avskrivning svans:**
   ```python
   # Beräkna avskrivningsålder
   age_return_{t} = age_component_{t}
   # Justera för jämna tidskoder
   if age_return_{t} % 2 == 1:
       age_return_{t} += 1 if age_return_{t} > 0 else -1
   age_return_{t} = age_return_{t} / 2 - 1
   
   # Beräkna återstående avskrivningstid
   remaining_years_{t} = maxdep/2 - age_return_{t}
   
   # Avskrivning svans
   dep_tail_{t} = (1 / remaining_years_{t}) × sum_nuav_tail_{t}
   ```

3. **Aggregera per kategori och nätverk:**
   ```python
   total_dep_ord_{t} = SUM(dep_ord_{t})  # Per id_network eller totalt
   total_dep_tail_{t} = SUM(dep_tail_{t})
   ```

**Resultat:** Dict med nycklar:
- `dep_ord_{229}`, `dep_ord_{230}`, ..., `dep_ord_{236}`
- `dep_tail_{229}`, `dep_tail_{230}`, ..., `dep_tail_{236}`

**Enhet:** tkr (tusen kronor) i 2022 års prisnivå

### 3.4 Steg 7: Beräkna avkastning

**Funktion:** `calculate_returns_single_dmu(df, interest_rate)` eller `calculate_returns(df, interest_rate)`

**Input:** 
- DataFrame från steg 5
- `interest_rate`: WACC (real, före skatt)

**Output:** Dict med avkastning per tidskod

**Process för varje tidskod t ∈ [229, 236]:**

1. **Beräkna återstående kapitalbas ordinarie:**
   ```python
   # Använd samma age_return som i steg 6
   capbase_left_ord_{t} = ((ekdep/2 - age_return_{t}) / (ekdep/2)) × nuav_ord_{t}
   capbase_left_ord_{t} = 0 if age_return_{t} < 0
   ```

2. **Beräkna avkastning ordinarie:**
   ```python
   # Avkastning på genomsnittligt bundet kapital under halvåret
   return_ord_{t} = interest_rate × capbase_left_ord_{t} / 2
   ```

3. **Beräkna återstående kapitalbas svans:**
   ```python
   capbase_left_tail_{t} = (1 / (age_return_{t} + 1)) × nuav_tail_{t}
   ```

4. **Beräkna avkastning svans:**
   ```python
   return_tail_{t} = interest_rate × capbase_left_tail_{t} / 2
   ```

5. **Aggregera per kategori och nätverk:**
   ```python
   total_return_ord_{t} = SUM(return_ord_{t}) / 1000  # Per id_network
   total_return_tail_{t} = SUM(return_tail_{t}) / 1000
   ```

**Resultat:** Dict med nycklar:
- `return_ord_{229}`, `return_ord_{230}`, ..., `return_ord_{236}`
- `return_tail_{229}`, `return_tail_{230}`, ..., `return_tail_{236}`

**Enhet:** tkr (tusen kronor) i 2022 års prisnivå

### 3.5 Steg 8: Sammanställ kapitalkostnad

**Funktion:** `compile_capcost_single_dmu(dep_data, ret_data, dmu_id)` eller `compile_capcost(dep_data, ret_data)`

**Input:**
- `dep_data`: Dict från steg 6
- `ret_data`: Dict från steg 7
- `dmu_id`: (optional) DMU för filtrering

**Output:** DataFrame med kapitalkostnad per tidskod

**Process:**

1. **För varje tidskod t ∈ [229, 236]:**
   ```python
   capcost_{t} = dep_ord_{t} + dep_tail_{t} + return_ord_{t} + return_tail_{t}
   ```

2. **Skapa resultat-DataFrame:**
   ```python
   pd.DataFrame([
       {
           'time': 229,
           'dep_ord': dep_ord_229,
           'dep_tail': dep_tail_229,
           'return_ord': return_ord_229,
           'return_tail': return_tail_229,
           'capcost_sum': capcost_229
       },
       # ... för alla tidskoder 229-236
   ])
   ```

**Resultat:** DataFrame med kolumner:
- `time`: Tidskod (229-236)
- `dep_ord`: Avskrivning ordinarie
- `dep_tail`: Avskrivning svans
- `return_ord`: Avkastning ordinarie
- `return_tail`: Avkastning svans
- `capcost_sum`: Total kapitalkostnad

**Enhet:** tkr per halvår

**Aggregering till årsdata:**
```python
# För 2024 (tidskoder 229 + 230)
capcost_2024 = df[df['time'].isin([229, 230])]['capcost_sum'].sum()

# För hela perioden 2024-2027 (tidskoder 229-236)
capcost_period = df['capcost_sum'].sum()
```

---

## 4. TIDSKOD-MAPPNING

### 4.1 Tidskod-formel

**Formel:**
```
time = (year - 1910) × 2 + halvår
```

Där:
- `year` = kalenderår (t.ex. 2024)
- `halvår` = 0 för H1 (jan-jun), 1 för H2 (jul-dec)

TIME_LABEL_TO_CODE = {
    "2024h1": 229, "2024h2": 230,
    "2025h1": 231, "2025h2": 232,
    "2026h1": 233, "2026h2": 234,
    "2027h1": 235, "2027h2": 236,
}

YEAR_TO_CODES = {
    2024: [229, 230],
    2025: [231, 232],
    2026: [233, 234],
    2027: [235, 236]
}

## 5. KOLUMNANVÄNDNING PER PIPELINE-STAGE

### 5.1 Pre-DEA Stage

#### Inputs från dataset:

**Data_modeller.xlsx → Baseline:**
| Kolumn | Används som | Output-variabel | Granularitet |
|--------|-------------|-----------------|--------------|
| DMU | ID-matching | DMU | - |
| REId | ID-matching | REId | - |
| Företag | Metadata | Företag | - |
| CAPEX | variabel i DEA | CAPEX | År 2024 |
| OPEXp |variabel i DEA | OPEXp | År 2024 |
| CU | variabel i DEA  | CU | År 2024 |
| MW | variabel i DEA  | MW | År 2024 |
| NS | variabel i DEA  | NS | År 2024 |
| MWhl | variabel i DEA | MWhl | År 2024 |
| MWhh | variabel i DEA  | MWhh | År 2024 |

**Data_modeller.xlsx → WACC-skalning:**
| Kolumn | Operation | Output-variabel | Formel |
|--------|-----------|-----------------|--------|
| Avskrivning | Kopieras | Avskrivning | Oförändrad |
| Avkastning | Skalas | Avkastning_NY | `Avkastning × (WACC_NY / WACC_BASELINE)` |
| CAPEX | Omberäknas | CAPEX | `Avskrivning + Avkastning_NY` |

**capbase_a.parquet → Parameter-ändring:**
| Kolumn | Modifieras av | Operation | Påverkar |
|--------|---------------|-----------|----------|
| normvärde | `apply_normvalue_adjustments()` | Ändra värde | `nuav_2022` |
| nuav_2022 | `apply_normvalue_adjustments()` | Omberäknas | Steg 5-8 |
| ekdep | `apply_lifetime_adjustments()` | Ändra värde | Steg 5-8 |
| maxdep | `apply_lifetime_adjustments()` | Ändra värde | Steg 5-8 |
| cat_encode | - | Mapping key | `ekdep`, `maxdep` lookup |

**KENT → Steg 1-4:**
| Input (Excel sheet) | Kolumn | Mappas till capbase_a | Används i steg |
|---------------------|--------|----------------------|----------------|
| Normvärde | Anl.-kategori | cat → cat_encode | Steg 2, 5-8 |
| Normvärde | Typ av anläggning | subcat → subcat_encode | Steg 2 |
| Normvärde | Antal | antal | Metadata |
| Normvärde | Rådighet | owned | Metadata |
| Normvärde | Ursprungligen tagen i bruk | time_from | Steg 5 |
| Normvärde | NUAV (kr) | nuav_2022 | Steg 5-8 |
| Investeringar | Tidpunkt | time_invest | Steg 5 |
| Investeringar | Typ av förändring | invest | Steg 5 |
| Investeringar | Värde | nuav_2022 | Steg 5-8 |

#### Outputs till DEA:

**DataFrame struktur: df_predea [148 rader]**

| Kolumn | Datatyp | Källa | Metod | Enhet |
|--------|---------|-------|-------|-------|
| DMU | int | Data_modeller | Alla | - |
| REId | string | Data_modeller | Alla | - |
| Företag | string | Data_modeller | Alla | - |
| CAPEX | float | Data_modeller / Beräkning | Baseline / WACC / Parameter / KENT | tkr |
| OPEXp | float | Data_modeller | Alla | tkr |
| CU | float | Data_modeller | Alla | antal |
| MW | float | Data_modeller | Alla | MW |
| NS | float | Data_modeller | Alla | km |
| MWhl | float | Data_modeller | Alla | MWh |
| MWhh | float | Data_modeller | Alla | MWh |

### 5.2 DEA Stage

#### Inputs från Pre-DEA:

**Användaren väljer mellan:**
- `DMU`: ID
- `CAPEX och OPEXp` (eller `TOTEX = CAPEX + OPEXp`): Input
- `CU`: Aantal kunder
- `NS`: Nätstationer
- `MW`: Installerad effekt (MW)
- `MWhl`: Överförd energi låglast (MWh)
- `MWhh`: Överförd energi höglast (MWh)

#### DEA-process kolumner:

**Skapade under DEA:**
| Kolumn | Skapas i steg | Beskrivning | Enhet |
|--------|---------------|-------------|-------|
| efficiency | Super-efficiency DEA | Teknisk effektivitet | 0-1 |
| super_efficiency | Super-efficiency DEA | Super-efficiency score | >0 |
| theta | Outlier-identifiering | Radiell expansion | >0 |
| is_outlier | IQR-metod | Outlier-flagga | bool |
| potential | Omberäkning utan outliers | Effektiviseringspotential | 0-1 |

#### Outputs från DEA:

**DataFrame struktur: df_dea [148 rader]**

| Kolumn | Datatyp | Beskrivning | Pipeline-användning | Enhet |
|--------|---------|-------------|---------------------|-------|
| DMU | int | Decision Making Unit | ID-matching | - |
| REId | string | Nätverks-ID | ID-matching | - |
| Företag | string | Företagsnamn | Metadata | - |
| efficiency | float | Teknisk effektivitet | Resultatvisning | 0-1 |
| super_efficiency | float | Super-efficiency score | Outlier-identifiering | >0 |
| potential | float | Effektiviseringspotential | **Input till effektiviseringskrav** | 0-1 |
| is_outlier | bool | Outlier-flagga | **Bestämmer effektiviseringskrav** | bool |

### 5.3 Post-DEA Stage

#### Inputs från DEA (1 företag):

| Kolumn | Extraheras för | Används i | Output till |
|--------|----------------|-----------|-------------|
| potential | Inloggat företag | Effektiviseringskrav-beräkning | `effkrav_proc` |
| is_outlier | Inloggat företag | Fast krav eller beräknat | `effkrav_proc` |

#### Inputs från SDF:

**"Påverkbara" sheet → Påverkbara kostnader:**
| Kolumn | Granularitet | Pipeline-användning | Enhet |
|--------|--------------|---------------------|-------|
| Påverkbara kostnader | 4 kolumner (2024-2027) | Baseline påverkbara per år | tkr |
| Totalsumma påverkbara kostnader för perioden 2024-2027 | 1 kolumn | Baseline påverkbara total | tkr |
| Parametrar OPEX Årligt eff.krav procent | 1 kolumn | Baseline effektiviseringskrav | procent |

**"IR 2024-2027" sheet → Övriga komponenter:**
| Kolumn | Pipeline-användning | Enhet |
|--------|---------------------|-------|
| Kapitalkostnad | Baseline kapitalkostnad total | tkr |
| -varav Kapital-förslitning | Baseline avskrivningar | tkr |
| varav Kapital-bindning | Baseline avkastning | tkr |
| Kostnader för flexibilitetstjänster | Flexibilitet | tkr |
| Avbrottsersättning 12-24 timmar | Avbrott | tkr |
| Avdrag kapitalkostnader statligt stöd | Avdrag | tkr |

## SLUTKOMMENTARER

### Datakvalitet och validering

1. **Data_modeller.xlsx:**
   - Alla 148 företag måste ha giltiga värden för CAPEX, OPEXp, och volumes
   - CAPEX = Avskrivning + Avkastning (verifieras)

2. **capbase_a:**
   - Alla komponenter måste ha giltiga cat_encode → ekdep/maxdep
   - nuav_2022 får inte vara negativ (förutom utrangeringar)
   - time_from måste vara valid tidskod

3. **SDF:**
   - Alla periodsummor ska matcha summan av årsdata
   - Intäktsram = Påverkbara + Opåverkbara + Kapitalkostnad + Flex + Avbrott - Avdrag

4. **reconciliation:**
   - Alla REId i Data_modeller måste finnas i reconciliation
   - Alla id_network i capbase_a måste finnas i reconciliation

### Kritiska beräkningsprecision

- **Excel-exakthet:** Alla beräkningar ska matcha Excel exakt (12 decimalers precision)
- **Rounding:** Endast vid final presentation, aldrig i mellanberäkningar
- **Floating-point:** Använd Decimal vid behov för finansiella beräkningar

### Nästa steg

Denna guide ger underlaget för att:
1. Definiera konsekvent namngivning för alla DataFrames i pipeline
2. Skapa tydliga kontrakt mellan pipeline-stages
3. Implementera validering på rätt ställen
4. Säkerställa Excel-exakt precision genom hela kedjan

---

**Dokumentslut**

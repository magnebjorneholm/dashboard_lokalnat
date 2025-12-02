# KRITISKA KLARGÖRANDEN FRÅN ANVÄNDAREN
## Regumetrica Dataflöde & Producer-Kontrakt

**Datum:** 2024-11-24  
**Källa:** Konversation med användaren efter Del 1 + Del 2 arkitektonisk analys  
**Syfte:** Klargöra missförstånd och definiera korrekt dataflöde

---

## HUVUDINSIKT: Systemet ska arbeta med alla 148 företag genom data_modeller.slsx fram till DEA för att sen extrahera effektivitet (efficiency score) för inloggat företag och arbeta med endast inloggat företag därefter.

### Varför detta är kritiskt: **DEA (Data Envelopment Analysis) MÅSTE jämföra alla företag med uppdaterade antagenden (parameters, variables, modulus) för att ge korrekta och representative efficiency scores.**

Om endast inloggat företag används i DEA eller endast inloggat företags data uppdateras blir jämförelsen meningslös

---

## DATAFLÖDE GENOM SYSTEMET

### Steg 1: Ladda baseline Data (ALLTID 148 företag)

```
Data_modeller.xlsx (Excel-fil med alla svenska nätföretag)
├─ Kolumner: DMU, REId, Företag, CAPEX, OPEXp, CU, MW, NS, MWhl, MWhh
└─ Detta är UTGÅNGSPUNKTEN för flera beräkningar fram till och med DEA och det är denna data som kan ändras beroende på vad användaren väljer att ändra.
```

**Laddas via:** `baseline_loaders.py` → `_load_data_modeller()`

---

### Steg 2: User-Modifications (på baseline data)

**TRE typer av ändringar:**

#### A: Parameter-ändringar (gäller ALLA 148 företag)

**Definition av Parameters från User manual (Regumetrica_UM.pdf):**
> Fixed values that define structural relationships within the regulatory model. 
> They capture assumptions or policy choices that apply UNIFORMLY across regulated entities.

**Exempel:**
- WACC (Weighted Average Cost of Capital)
- Ekonomiska livslängder för tillgångar
- Normvärden
- Ovanstående ska alltså appliceras på alla 148 DMU's i dataframen.

**Dataflöde:**
```
User ändrar WACC från 4.53% till 5.0%
  ↓
Beräkna ny CAPEX för ALLA 148 företag genom skalning.
  ↓
DataFrame 148 rader (alla uppdaterade med ny WACC)
  ↓
Skicka till DEA → jämför alla 148 med ny CAPEX
```

#### B: Variable-ändringar från User manual (Regumetrica_UM.pdf) (gäller ENDAST inloggat företag)

**Definition av Variables:**
> Measurable inputs that vary across regulated entities. 
> They correspond to real-world data, such as asset quantities, operating costs, or energy delivered.

**Exempel:**
- Ändra levererad energi (volumes) eller driftkostnader (OPEXp) => Ska endast appliceras på inloggat företags kolumner för OPEXp, CU, MW, NS, MWhl, MWhh som går in i DEA. Enklaste är att man kan redigera detssa värden direkt med streamlits st.data_editor
- Ladda upp KENT-fil (Inrapporterad data över företagens nättillgångar, investeringar och kostnader med värderingar, klassificering och prognoser). Uppladdning av egen KENT-fil innebär att ny CAPEX för inloggat företag måste beräknas, den backenden finns och beräknar korrekta kapitalkostnader.

**Dataflöde:**
```
User (företag REId=123) laddar upp ny KENT-fil eller ändrar värden för OPEXp, CU, MW, NS, MWhl, MWhh via st.data_editor
  ↓
Ny CAPEX beräknas för inloggat företag baserat på ny KENT-fil.
  ↓
DataFrame 148 rader från baseline från data_modeller.xlsx
  ↓
Uppdatera ENDAST rad där REId=123 med ny data (CAPEX, OPEXp, CU, MW, NS, MWhl, MWhh)
Övriga 149 rader: OFÖRÄNDRAD baseline
  ↓
DataFrame 148 rader (1 modifierad, 147 baseline)
  ↓
Skicka till DEA.
```

#### C: Kombinerade ändringar (parameter + variable)

**Exempel:** User ändrar WACC OCH laddar upp KENT

**KRITISK INSIKT:** Parameter ska appliceras på alla företag medans variable ska appliceras endast på inloggat företag! Här kan det va olika kombinationer av parameter + variables.

**Dataflöde:**
```
User (REId=123) ändrar WACC till 5.0% OCH laddar upp KENT
  ↓
DataFrame 148 rader från baseline
  ↓
Applicera ny WACC (5.0%) på alla 148 företag → alla skalade
  ↓
Uppdatera rad REId=123 med KENT-data (beräknad med WACC=5.0%)
Övriga 147 rader: baseline skalat med WACC=5.0%
  ↓
DataFrame 148 rader (alla har ny WACC, men bara 123 har KENT-anläggningar)
  ↓
Skicka till DEA → jämför alla 148
```

---

### Steg 3: DEA-analys (ALLTID alla 148 företag)

```
DEA tar:
├─ CAPEX: DataFrame 148 rader
├─ OPEX: DataFrame 148 rader
├─ Volumes: DataFrame 148 rader (CU, MW, NS, MWhl, MWhh)
└─ Config: Vilken DEA-modell (CRS/VRS, input/output-orientering)

DEA returnerar:
└─ Efficiency: DataFrame 148 rader med kolumner [DMU, REId, Efficiency]
```

**Efficiency scores för alla 148 företag**

---

### Steg 4: Extraktion och summering
    1. Extrahera endast inloggat företags potential (1-effektivitet) och om det är outlier eller inte (is_outlier)
    2. Beräkna effektiviseringskrav (effkrav_proc) genom calculate_effkrav_from_potential()
    3. Välj om kravet ska läggas på OPEX eller TOTEX.
    4. Utför beräkningar enligt guide


---

**Kritisk förståelse att ha:**
- DataFrame 148 rader fram till DEA (ALLTID)
- Parameter = alla företag, Variable = inloggat företag
- Extraktion sker EFTER DEA

**END OF DOCUMENT**

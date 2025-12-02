# INTÄKTSRAMENS FULLSTÄNDIGA DEKOMPOSITION

**Version:** 2.0  
**Datum:** 2025-01-XX  
**Syfte:** Arkitektur-oberoende referens för korrekt beräkning av intäktsram med effektiviseringskrav

---

## INNEHÅLLSFÖRTECKNING

1. [Översikt](#1-översikt)
2. [Matematisk grund - Arkitektur-oberoende](#2-matematisk-grund---arkitektur-oberoende)
3. [Variabeldefinitioner](#3-variabeldefinitioner)
4. [Beräkningsformler](#4-beräkningsformler)
5. [Återanvändbara funktioner](#5-återanvändbara-funktioner)
6. [Praktisk validering](#6-praktisk-validering)

---

## 1. ÖVERSIKT

### 1.1 Beräkningsflöde

```
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
```

### 1.2 DataFrame-approach genom hela flödet

**KRITISKT:** Vi använder **alltid DataFrame** genom hela beräkningskedjan, aldrig dict/Series.

**Efter DEA-körning:**
```python
# DEA kräver alla 148 företag för jämförande analys
dea_result_full = produce_efficiency_from_dea(...)  # DataFrame: 148 rader

# Filtrera till användarens företag
user_dmu = get_user_dmu()  # t.ex. 886
dea_result_user = dea_result_full[dea_result_full['DMU'] == user_dmu].copy()
# dea_result_user är nu DataFrame med 1 rad

# Använd samma funktion som vanligt
effkrav_result = produce_effektiviseringskrav(
    efficiency_data=dea_result_user  # DataFrame: 1 rad
)
# Fungerar identiskt som med 148 rader, men snabbare
```

**Fördelar med DataFrame (även för 1 rad):**
- ✅ Konsekvent API genom hela systemet
- ✅ Samma funktioner fungerar för 1 eller 148 företag
- ✅ Enkel merge, filtering, calculations
- ✅ Minimal minnesanvändning (några KB för 1 rad)
- ✅ Pandas fördelar: .loc, .iloc, .merge(), .apply()
- ✅ Enklare debugging och testning

### 1.3 Två metoder för effektiviseringskrav

- **OPEX (traditionell):** Effektiviseringskrav appliceras endast på påverkbara driftskostnader
- **TOTEX (Ei:s förslag 2020):** Effektiviseringskrav appliceras på påverkbara + kapitalkostnader

**Teoretisk ekvivalens:** Om CAPEX = 0, ger OPEX och TOTEX identiskt resultat.

---

## 2. MATEMATISK GRUND - ARKITEKTUR-OBEROENDE

### 2.1 Grundprincip

Effektiviseringskravet reducerar påverkbara kostnader progressivt över 4-årsperioden:

```
År t: Y_t = Startvärde - Kumulativa_Avdrag_t + Justering
```

### 2.2 Generell formel (giltig för både OPEX och TOTEX)

**Steg 1: Definiera bas för effektiviseringskrav**

```
DT_method = {
    OPEX:  B_raw
    TOTEX: B_raw + (Kapitalkostnad_Total / 4)
}

Delta = Adj / 4

B = DT_method + Delta
```

**Där:**
- `B_raw` = Påverkbara kostnader baseline (tkr för hela perioden)
- `Adj` = NeonÄndringar/justeringar (tkr för hela perioden)
- `Kapitalkostnad_Total` = Total kapitalkostnad för 4-årsperioden
- `B` = Årsbas som effektiviseringskravet appliceras på

**Steg 2: Beräkna årsvisa inkrement och avdrag**

```
För varje år t ∈ {1, 2, 3, 4} (2024-2027):

Inc_t = e × B × (1 + e)^(t-1)

Avdrag_t = Σ(Inc_i för i=1 till t)
         = Inc_1 + Inc_2 + ... + Inc_t
```

**Där:**
- `e` = Effkrav_proc (årligt effektiviseringskrav, decimal)
- `Inc_t` = Årligt inkrement (avdraget för år t)
- `Avdrag_t` = Kumulativt avdrag vid slutet av år t

**Steg 3: Beräkna årligt påverkbart värde**

```
Y_t = DT_method - Avdrag_t + Delta
```

**Steg 4: Summera över perioden**

```
Paverkbara_Target = Σ(Y_t för t=1 till 4)
                  = Y_2024 + Y_2025 + Y_2026 + Y_2027
```

**Viktigt:** `Paverkbara_Target` är värdet **EFTER** effektiviseringsavdrag.

### 2.3 Expliciterad formel per metod

#### OPEX-metod:
```
DT = B_raw
B = DT + (Adj / 4)
e = Effkrav_proc

För t = 1,2,3,4:
    Inc_t = e × B × (1 + e)^(t-1)
    Avdrag_t = Σ(Inc_i, i=1..t)
    Y_t = DT - Avdrag_t + (Adj / 4)

Paverkbara_Target = Σ(Y_t, t=1..4)
```

#### TOTEX-metod:
```
DT = B_raw + (Kapitalkostnad_Total / 4)
B = DT + (Adj / 4)
e = Effkrav_proc

För t = 1,2,3,4:
    Inc_t = e × B × (1 + e)^(t-1)
    Avdrag_t = Σ(Inc_i, i=1..t)
    Y_t = DT - Avdrag_t + (Adj / 4)

Paverkbara_Target = Σ(Y_t, t=1..4)
```

**Kritisk skillnad:** TOTEX inkluderar CAPEX i DT (basen), vilket gör att effektiviseringskravet appliceras på både OPEX och CAPEX. Men CAPEX ingår i slutsumman oavsett metod.

### 2.4 Total intäktsram

```
Intaktsram_Total = Kapitalkostnad_Total 
                 + Paverkbara_Target 
                 + Opaverkbara_Kostnader 
                 + Ovriga_Komponenter
```

**Expanderat:**
```
Intaktsram_Total = Avskrivningar
                 + Avkastning
                 + Paverkbara_Target
                 + Opaverkbara_Kostnader
                 + Flexibilitetstjanster        (optional)
                 + Avbrottsersattning_12_24h   (optional)
                 + Kvalitetsjustering          (optional)
```

---

## 3. VARIABELDEFINITIONER

### 3.1 Input-variabler (från Excel baseline)

| Variabel | Excel-kolumn | Beskrivning | Enhet |
|----------|--------------|-------------|-------|
| `REId` | A | Redovisningsenhet ID | string |
| `B_raw` | DT | Påverkbara kostnader baseline | tkr (4-årsperiod) |
| `Adj` | DU | NeonÄndringar/justeringar | tkr (4-årsperiod) |
| `e_base` | EG | Baseline effektiviseringskrav | decimal | Beräknad | Total kapitalkostnad | tkr (4-årsperiod) |
| `Opaverkbara_Kostnader` | Från data | Opåverkbara kostnader | tkr (4-årsperiod) |
| `Avskrivningar` | Beräknad | Kapitalförslitning | tkr (4-årsperiod) |
| `Avkastning` | Beräknad | Kapitalbindning | tkr (4-årsperiod) |

### 3.2 Beräknade variabler

| Variabel | Formel | Beskrivning | Enhet |
|----------|--------|-------------|-------|
| `DT_opex` | `B_raw` | OPEX-bas | tkr (periodbas) |
| `B_capex` | `Kapitalkostnad_Total / 4` | CAPEX årsbas | tkr (årligt) |
| `Delta_opex` | `Adj / 4` | Justering per år | tkr (årligt) |
| `DT` | `DT_opex` (OPEX) eller `DT_opex + B_capex` (TOTEX) | Total bas | tkr (periodbas) |
| `B` | `DT + Delta_opex` | Årsbas för effektiviseringskrav | tkr (årligt) |

### 3.3 Output-variabler (per REId)

| Variabel | Beskrivning | Enhet |
|----------|-------------|-------|
| `Paverkbara_Target` | Påverkbara kostnader efter avdrag | tkr (4-årsperiod) |
| `Total_Reduction_tkr` | Total reduktion från baseline | tkr (4-årsperiod) |
| `Y2024_scenario`, `Y2025_scenario`, ... | Årsvisa påverkbara värden | tkr (årligt) |
| `Avdrag_2024_scn`, `Avdrag_2025_scn`, ... | Kumulativa avdrag per år | tkr (kumulativt) |
| `Inc_2024_scn`, `Inc_2025_scn`, ... | Årliga inkrement | tkr (årligt) |

---

## 4. BERÄKNINGSFORMLER

### 4.1 Excel-exakt avrundning

**Viktigt:** Använd Excel-exakt half-up avrundning för kompatibilitet.

```python
def excel_half_up_round(x: float) -> int:
    """Excel-exakt half-up avrundning"""
    return int(math.floor(float(x) + 0.5))
```

**Exempel:**
- `excel_half_up_round(2.5)` → 3
- `excel_half_up_round(2.4)` → 2
- `excel_half_up_round(3.5)` → 4

### 4.2 Detaljerad årlig beräkning

```python
# Initialisering
DT = DT_method  # Från metodval
Delta = Adj / 4
B = DT + Delta
e = Effkrav_proc

# Arrayer för lagring
inc_exact_vals = []
avdrag_vals = []
year_vals = []

# Beräkna för varje år
for t in range(1, 5):  # t = 1,2,3,4
    # Årligt inkrement med full precision
    growth_factor = (1.0 + e) ** (t - 1)
    inc_exact = e * B * growth_factor
    inc_exact_vals.append(inc_exact)
    
    # Kumulativt avdrag (summa av alla inkrement hittills)
    avdrag_kum = sum(inc_exact_vals)
    avdrag_vals.append(avdrag_kum)
    
    # Årligt påverkbart värde
    y_exact = DT - avdrag_kum + Delta
    year_vals.append(y_exact)

# Totalt över perioden
Paverkbara_Target = sum(year_vals)
```

### 4.3 Exempel-beräkning (OPEX-metod)

**Given:**
- B_raw = 10000 tkr
- Adj = 200 tkr
- Effkrav_proc = 0.03 (3% årligt)
- Metod = OPEX

**Beräkning:**
```
DT = 10000
Delta = 200 / 4 = 50
B = 10000 + 50 = 10050

År 2024 (t=1):
    Inc_2024 = 0.03 × 10050 × (1.03)^0 = 301.5
    Avdrag_2024 = 301.5
    Y_2024 = 10000 - 301.5 + 50 = 9748.5

År 2025 (t=2):
    Inc_2025 = 0.03 × 10050 × (1.03)^1 = 310.545
    Avdrag_2025 = 301.5 + 310.545 = 612.045
    Y_2025 = 10000 - 612.045 + 50 = 9437.955

År 2026 (t=3):
    Inc_2026 = 0.03 × 10050 × (1.03)^2 = 319.861
    Avdrag_2026 = 301.5 + 310.545 + 319.861 = 931.906
    Y_2026 = 10000 - 931.906 + 50 = 9118.094

År 2027 (t=4):
    Inc_2027 = 0.03 × 10050 × (1.03)^3 = 329.457
    Avdrag_2027 = 301.5 + 310.545 + 319.861 + 329.457 = 1261.363
    Y_2027 = 10000 - 1261.363 + 50 = 8788.637

Paverkbara_Target = 9748.5 + 9437.955 + 9118.094 + 8788.637 = 37093.186 tkr
```

---

## 5. ÅTERANVÄNDBARA FUNKTIONER

### 5.1 Funktioner som kan användas direkt

Dessa funktioner är arkitektur-oberoende och kan återanvändas utan ändringar:

#### Från `effektiviseringskrav_calculations.py`:

```python
✅ calculate_effkrav_from_potential(
    potential: float,
    is_outlier: bool,
    trunkering_min: float = 0.162416,
    trunkering_max: float = 0.3,
    outlier_krav: float = 0.01
) -> float
```
**Återanvändning:** 100% - behöver inga ändringar.

```python
✅ calculate_effkrav_for_dataframe(
    df: pd.DataFrame,
    potential_col: str = 'potential',
    outlier_col: str = 'is_outlier',
    trunkering_min: float = 0.162416,
    trunkering_max: float = 0.3,
    outlier_krav: float = 0.01
) -> pd.DataFrame
```
**Återanvändning:** 100% - behöver inga ändringar.

#### Från `ir_calculations.py`:

```python
✅ excel_half_up_round(x: float) -> int
```
**Återanvändning:** 100% - arkitektur-oberoende utility.

```python
✅ load_ir_paverkbara_baseline(filepath: str) -> pd.DataFrame
```
**Återanvändning:** 100% - men kan behöva wrappas i baseline loader.

```python
⚠️ calculate_ir_paverkbara_export(
    dea_result: pd.DataFrame,
    ir_baseline: pd.DataFrame,
    working_df: pd.DataFrame,
    method: str = 'OPEX'
) -> Tuple[pd.DataFrame, dict]
```
**Återanvändning:** ~90% - kärn-logiken är återanvändbar, men behöver anpassas till producer-signaturer.

### 5.2 Funktioner som behöver anpassas

#### Från `intaktsram_assembly.py` (GAMMAL FEL VERSION):

```python
❌ calculate_paverkbara_with_effkrav()
```
**Status:** Ska ERSÄTTAS med logik från `calculate_ir_paverkbara_export()`.

```python
❌ assemble_intaktsram()
```
**Status:** Behöver OMSKRIVAS för producer-arkitektur.

---

## 6. PRAKTISK VALIDERING

### 6.1 Validering mot Excel-facit

**Testdata:** `Facit_paverkbara.xlsx` - REL00886

Denna fil innehåller verkliga värden från Ei:s baseline och kan användas för att verifiera att beräkningarna är korrekta.

**Testfall: REL00886 (OPEX-metod)**

```python
# Extrahera data från Excel
facit_df = pd.read_excel('Facit_paverkbara.xlsx', sheet_name='Påverkbara', header=1)
facit_row = facit_df[facit_df.iloc[:, 0] == 'REL00886'].iloc[0]

# Input-värden
REId = 'REL00886'
B_raw = facit_row.iloc[123]      # Kolumn DT: 219438.70 tkr
Adj = facit_row.iloc[124]        # Kolumn DU: 73097.00 tkr
e_base = facit_row.iloc[136]     # Kolumn EG: 0.012661 (1.27%)
y2024_excel = facit_row.iloc[130]  # Kolumn EA: 234703.31 tkr (FACIT)

# Skapa input DataFrame (1 rad)
efficiency_data = pd.DataFrame({
    'REId': [REId],
    'DMU': [886],
    'Effkrav_proc': [e_base]
})

ir_baseline = pd.DataFrame({
    'REId': [REId],
    'B_raw': [B_raw],
    'Adj': [Adj],
    'e_base': [e_base]
})

capex_data = pd.DataFrame({
    'REId': [REId],
    'Kapitalkostnad_Total': [0]  # Ingen CAPEX i detta test
})

# Kör beräkning (din implementation)
result = calculate_ir_paverkbara_export(
    dea_result=efficiency_data,
    ir_baseline=ir_baseline,
    working_df=capex_data,
    method='OPEX'
)

# Validera resultat
calc_y2024 = result['Y2024_scenario'].iloc[0]
diff = abs(calc_y2024 - y2024_excel)

print(f"Excel Y2024:    {y2024_excel:.2f} tkr")
print(f"Beräknat Y2024: {calc_y2024:.2f} tkr")
print(f"Differens:      {diff:.2f} tkr")

# Acceptabel tolerans: 0.01 tkr (avrundningsfel)
assert diff < 0.01, f"För stor avvikelse från Excel-facit!"
print("✅ Validering godkänd!")
```

### 6.2 Debug-utskrifter för felsökning

**Lägg till i beräkningsfunktionen:**

```python
def calculate_ir_paverkbara_export(...):
    # ... beräkningar ...
    
    # Debug-utskrifter
    print("\n=== DEBUG: Påverkbara kostnader ===")
    print(f"REId: {export_data['REId'].iloc[0]}")
    print(f"Method: {method}")
    print(f"\nInput:")
    print(f"  B_raw: {DT_opex.iloc[0]:.2f} tkr")
    print(f"  Adj: {DU_opex.iloc[0]:.2f} tkr")
    print(f"  e_scn: {e_scn.iloc[0]:.6f} ({e_scn.iloc[0]*100:.2f}%)")
    
    if method == 'TOTEX':
        print(f"  CAPEX_periodsumma: {export_data['CAPEX_periodsumma'].iloc[0]:.2f} tkr")
        print(f"  CAPEX_arsbas: {export_data['CAPEX_arsbas'].iloc[0]:.2f} tkr")
    
    print(f"\nMellanberäkningar:")
    print(f"  DT: {DT.iloc[0]:.2f} tkr")
    print(f"  Delta: {Delta.iloc[0]:.2f} tkr")
    print(f"  B (årsbas): {B.iloc[0]:.2f} tkr")
    
    print(f"\nÅrsvisa inkrement (scenario):")
    print(f"  Inc_2024: {export_data['Inc_2024_scn'].iloc[0]:.2f} tkr")
    print(f"  Inc_2025: {export_data['Inc_2025_scn'].iloc[0]:.2f} tkr")
    print(f"  Inc_2026: {export_data['Inc_2026_scn'].iloc[0]:.2f} tkr")
    print(f"  Inc_2027: {export_data['Inc_2027_scn'].iloc[0]:.2f} tkr")
    
    print(f"\nKumulativa avdrag (scenario):")
    print(f"  Avdrag_2024: {export_data['Avdrag_2024_scn'].iloc[0]:.2f} tkr")
    print(f"  Avdrag_2025: {export_data['Avdrag_2025_scn'].iloc[0]:.2f} tkr")
    print(f"  Avdrag_2026: {export_data['Avdrag_2026_scn'].iloc[0]:.2f} tkr")
    print(f"  Avdrag_2027: {export_data['Avdrag_2027_scn'].iloc[0]:.2f} tkr")
    
    print(f"\nÅrsvisa påverkbara värden (scenario):")
    print(f"  Y_2024: {export_data['Y2024_scenario'].iloc[0]:.2f} tkr")
    print(f"  Y_2025: {export_data['Y2025_scenario'].iloc[0]:.2f} tkr")
    print(f"  Y_2026: {export_data['Y2026_scenario'].iloc[0]:.2f} tkr")
    print(f"  Y_2027: {export_data['Y2027_scenario'].iloc[0]:.2f} tkr")
    
    print(f"\nResultat:")
    print(f"  Paverkbara_Target: {export_data['Paverkbara_Target'].iloc[0]:.2f} tkr")
    print(f"  Total_Reduction: {export_data['Total_Reduction_tkr'].iloc[0]:.2f} tkr")
    print("="*40 + "\n")
    
    return export_data, metadata
```

### 6.3 Manuell steg-för-steg validering

**Beräkna manuellt med Python för REL00886:**

```python
import math

# Input från Excel
B_raw = 219438.70
Adj = 73097.00
e = 0.012661
method = 'OPEX'

# Steg 1: Beräkna bas
DT = B_raw  # För OPEX
Delta = Adj / 4.0
B = DT + Delta

print(f"DT = {DT:.2f}")
print(f"Delta = {Delta:.2f}")
print(f"B = {B:.2f}\n")

# Steg 2: Årsvisa beräkningar
def excel_half_up_round(x):
    return int(math.floor(float(x) + 0.5))

inc_exact_vals = []
avdrag_vals = []
year_vals = []

for t in range(1, 5):
    # Inkrement
    growth_factor = (1.0 + e) ** (t - 1)
    inc_exact = e * B * growth_factor
    inc_exact_vals.append(inc_exact)
    
    # Kumulativt avdrag
    avdrag_kum = sum(inc_exact_vals)
    avdrag_vals.append(avdrag_kum)
    
    # Årsvärde
    y_exact = DT - avdrag_kum + Delta
    year_vals.append(y_exact)
    
    year = 2023 + t
    print(f"År {year} (t={t}):")
    print(f"  Inc_{year} = {inc_exact:.2f}")
    print(f"  Avdrag_{year} = {avdrag_kum:.2f}")
    print(f"  Y_{year} = {y_exact:.2f}")

# Steg 3: Totalsumma
Paverkbara_Target = sum(year_vals)
print(f"\nPaverkbara_Target = {Paverkbara_Target:.2f} tkr")

# Jämför med Excel (Y2024 ska vara ~234703.31)
print(f"\nJämförelse med Excel:")
print(f"  Excel Y2024:    234703.31 tkr")
print(f"  Beräknat Y2024: {year_vals[0]:.2f} tkr")
print(f"  Differens:      {abs(year_vals[0] - 234703.31):.2f} tkr")
```

### 6.4 TOTEX-testfall (teoretiskt)

**Teoretisk validering: CAPEX = 0 → OPEX = TOTEX**

```python
# Om CAPEX = 0 ska OPEX och TOTEX ge samma resultat

# OPEX-metod
result_opex = calculate_ir_paverkbara_export(
    dea_result=efficiency_data,
    ir_baseline=ir_baseline,
    working_df=capex_data,  # CAPEX = 0
    method='OPEX'
)

# TOTEX-metod (med CAPEX = 0)
result_totex = calculate_ir_paverkbara_export(
    dea_result=efficiency_data,
    ir_baseline=ir_baseline,
    working_df=capex_data,  # CAPEX = 0
    method='TOTEX'
)

# Resultat ska vara identiska
diff = abs(
    result_opex['Paverkbara_Target'].iloc[0] - 
    result_totex['Paverkbara_Target'].iloc[0]
)

assert diff < 0.01, "OPEX och TOTEX ska ge samma resultat när CAPEX=0"
print("✅ OPEX ≈ TOTEX när CAPEX=0")
```

**Med CAPEX > 0:**

```python
# TOTEX ska ge LÄGRE påverkbara (mer reducerat) än OPEX

capex_data_with_capex = pd.DataFrame({
    'REId': ['REL00886'],
    'Kapitalkostnad_Total': [100000]  # 100,000 tkr CAPEX
})

result_opex = calculate_ir_paverkbara_export(..., method='OPEX')
result_totex = calculate_ir_paverkbara_export(..., method='TOTEX')

# TOTEX ska vara mindre (större bas → större avdrag)
assert result_totex['Paverkbara_Target'].iloc[0] < result_opex['Paverkbara_Target'].iloc[0]
print("✅ TOTEX ger lägre påverkbara när CAPEX > 0")
```

---

## 7. SAMMANFATTNING

### 7.1 Kritiska punkter

1. **DataFrame genom hela flödet** - Aldrig dict/Series
2. **Metodval (OPEX vs TOTEX)** påverkar enbart DT (basen för effektiviseringskrav)
3. **CAPEX ingår alltid i slutsumman** oavsett metod
4. **Årsvisa avdrag är kumulativa** (Avdrag_t = summa av alla inkrement till och med år t)
5. **Excel-exakt avrundning** är kritisk för kompatibilitet
6. **Full precision** genom beräkning, avrunda endast slutresultat

### 7.2 Återanvändning från befintlig kod

| Funktion | Källa | Återanvändning | Anpassning |
|----------|-------|----------------|------------|
| `calculate_effkrav_from_potential()` | effektiviseringskrav_calculations.py | 100% | Nej |
| `calculate_effkrav_for_dataframe()` | effektiviseringskrav_calculations.py | 100% | Nej |
| `excel_half_up_round()` | ir_calculations.py | 100% | Nej |
| `load_ir_paverkbara_baseline()` | ir_calculations.py | 100% | Wrapper till baseline |
| `calculate_ir_paverkbara_export()` | ir_calculations.py | 90% | Anpassa signaturer |

### 7.3 Nästa steg för implementation

1. Skapa beräkningsfunktion baserad på formler i detta dokument
2. Validera mot Excel-facit (REL00886)
3. Integrera i producer-struktur enligt er arkitektur
4. Lägg till debug-utskrifter för felsökning
5. Dokumentera i er implementationsguide

---

**END OF DOCUMENT**

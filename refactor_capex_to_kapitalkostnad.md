# Refaktorering: CAPEX → Kapitalkostnad_2024

## Syfte

Byt namn på kolumnen `CAPEX` till `Kapitalkostnad_2024` i hela kodbasen för konsekvent namngivning.

## Kontext

- `Kapitalkostnad_2024` är ett **årsvärde** (tkr) för 2024 som används som input till DEA-analys
- `Kapitalkostnad_Period` är **periodsumman** 2024-2027 för intäktsramen (annan kolumn, rör ej)
- `CAPEX` i Excel-filen `Data_modeller.xlsx` behåller sitt namn (extern datakälla)

## Regler

1. `CAPEX` som **DataFrame-kolumnnamn** → byt till `Kapitalkostnad_2024`
2. `CAPEX` i **kommentarer/docstrings** → uppdatera till `Kapitalkostnad_2024` där det refererar till kolumnen
3. `capex` som **variabelnamn** (t.ex. `baseline_capex`, `missing_capex`, `scaled_capex`) → behåll (lokala variabler)
4. `TOTEX` → behåll (annat koncept: `OPEXp + Kapitalkostnad_2024`)
5. `CAPEX` vid **läsning från Excel** i `baseline_data.py` → behåll (externt kolumnnamn)

---

## Ändringar per fil

### baseline_data.py

Rad 98 - Lägg till namnbyte och ändra TOTEX-beräkning:
```python
# ERSÄTT:
df["TOTEX"] = df["OPEXp"] + df["CAPEX"]

# Explicit alias for arsvarde (CAPEX ar redan arsvarde)
df["Kapitalkostnad_2024"] = df["CAPEX"]

# MED:
df["Kapitalkostnad_2024"] = df["CAPEX"]  # Byt namn från Excel-kolumn till intern standard
df["TOTEX"] = df["OPEXp"] + df["Kapitalkostnad_2024"]
```

Rad 394 och 397 - Ändra kolumnreferenser i summary:
```python
# ERSÄTT:
'total_capex_tsek': float(df['CAPEX'].sum()),
'mean_capex_tsek': float(df['CAPEX'].mean()),

# MED:
'total_capex_tsek': float(df['Kapitalkostnad_2024'].sum()),
'mean_capex_tsek': float(df['Kapitalkostnad_2024'].mean()),
```

---

### dea_calculations.py

Rad 22-24 - Uppdatera docstring:
```python
# ERSÄTT:
df: DataFrame med alla 148 företag, kolumner: REId, CAPEX, OPEXp, CU, MW, NS, MWhl, MWhh
    - inputs: Lista med input-kolumner (default: ['CAPEX', 'OPEXp'])

# MED:
df: DataFrame med alla 148 företag, kolumner: REId, Kapitalkostnad_2024, OPEXp, CU, MW, NS, MWhl, MWhh
    - inputs: Lista med input-kolumner (default: ['Kapitalkostnad_2024', 'OPEXp'])
```

Rad 42 - Ändra default inputs:
```python
# ERSÄTT:
input_cols = model_spec.get('inputs', ['CAPEX', 'OPEXp'])

# MED:
input_cols = model_spec.get('inputs', ['Kapitalkostnad_2024', 'OPEXp'])
```

Rad 217 - Ändra EI_BASELINE_SPEC:
```python
# ERSÄTT:
'inputs': ['CAPEX', 'OPEXp'],

# MED:
'inputs': ['Kapitalkostnad_2024', 'OPEXp'],
```

---

### case_definition.py

Rad 59 - Ändra default inputs i dataclass:
```python
# ERSÄTT:
inputs: List[str] = field(default_factory=lambda: ['CAPEX', 'OPEXp'])

# MED:
inputs: List[str] = field(default_factory=lambda: ['Kapitalkostnad_2024', 'OPEXp'])
```

Rad 210 - Uppdatera docstring:
```python
# ERSÄTT:
- Inputs: CAPEX, OPEXp

# MED:
- Inputs: Kapitalkostnad_2024, OPEXp
```

Rad 228 - Ändra exempel:
```python
# ERSÄTT:
inputs=['CAPEX', 'OPEXp'],

# MED:
inputs=['Kapitalkostnad_2024', 'OPEXp'],
```

---

### data_mapping.py

Rad 41 - Ändra exclude_cols:
```python
# ERSÄTT:
base_cols = [col for col in df_all_companies.columns if col not in ['CAPEX', 'TOTEX']]

# MED:
base_cols = [col for col in df_all_companies.columns if col not in ['Kapitalkostnad_2024', 'TOTEX']]
```

Rad 45 - Ändra merge-kolumner:
```python
# ERSÄTT:
df_network[['REId', 'CAPEX']],

# MED:
df_network[['REId', 'Kapitalkostnad_2024']],
```

Rad 51 - Ändra TOTEX-beräkning:
```python
# ERSÄTT:
df_result['TOTEX'] = df_result['OPEXp'] + df_result['CAPEX']

# MED:
df_result['TOTEX'] = df_result['OPEXp'] + df_result['Kapitalkostnad_2024']
```

Rad 54-59 - Ändra missing_capex hantering:
```python
# ERSÄTT:
missing_capex = df_result['CAPEX'].isna()
if missing_capex.any():
    print(f"⚠️ {missing_capex.sum()} företag saknar KENT CAPEX - använder baseline")
    baseline_capex = df_all_companies.set_index('REId')['CAPEX']
    df_result.loc[missing_capex, 'CAPEX'] = df_result.loc[missing_capex, 'REId'].map(baseline_capex)
    df_result.loc[missing_capex, 'TOTEX'] = df_result.loc[missing_capex, 'OPEXp'] + df_result.loc[missing_capex, 'CAPEX']

# MED:
missing_capex = df_result['Kapitalkostnad_2024'].isna()
if missing_capex.any():
    print(f"  Varning: {missing_capex.sum()} företag saknar KENT Kapitalkostnad_2024 - använder baseline")
    baseline_capex = df_all_companies.set_index('REId')['Kapitalkostnad_2024']
    df_result.loc[missing_capex, 'Kapitalkostnad_2024'] = df_result.loc[missing_capex, 'REId'].map(baseline_capex)
    df_result.loc[missing_capex, 'TOTEX'] = df_result.loc[missing_capex, 'OPEXp'] + df_result.loc[missing_capex, 'Kapitalkostnad_2024']
```

---

### wacc_scaling.py

Rad 7-9 - Uppdatera modul-docstring:
```python
# ERSÄTT:
CAPEX = Avskrivning + Avkastning
Ny Avkastning = Baseline Avkastning × (ny_WACC / baseline_WACC)
Ny CAPEX = Avskrivning + Ny Avkastning

# MED:
Kapitalkostnad_2024 = Avskrivning + Avkastning
Ny Avkastning = Baseline Avkastning × (ny_WACC / baseline_WACC)
Ny Kapitalkostnad_2024 = Avskrivning + Ny Avkastning
```

Rad 49 - Ändra required_cols:
```python
# ERSÄTT:
required_cols = ['CAPEX', 'Avskrivning', 'Avkastning', 'OPEXp']

# MED:
required_cols = ['Kapitalkostnad_2024', 'Avskrivning', 'Avkastning', 'OPEXp']
```

Rad 69-70 - Ändra beräkning:
```python
# ERSÄTT:
# Ny CAPEX = Avskrivning + Ny Avkastning
df['CAPEX'] = df['Avskrivning'] + df['Avkastning']

# MED:
# Ny Kapitalkostnad_2024 = Avskrivning + Ny Avkastning
df['Kapitalkostnad_2024'] = df['Avskrivning'] + df['Avkastning']
```

Rad 72-73 - Ändra TOTEX-beräkning:
```python
# ERSÄTT:
# Uppdatera TOTEX = OPEXp + CAPEX
df['TOTEX'] = df['OPEXp'] + df['CAPEX']

# MED:
# Uppdatera TOTEX = OPEXp + Kapitalkostnad_2024
df['TOTEX'] = df['OPEXp'] + df['Kapitalkostnad_2024']
```

Rad 97-98 - Ändra summary-beräkning:
```python
# ERSÄTT:
baseline_capex = df_baseline['CAPEX'].sum()
scaled_capex = df_scaled['CAPEX'].sum()

# MED:
baseline_capex = df_baseline['Kapitalkostnad_2024'].sum()
scaled_capex = df_scaled['Kapitalkostnad_2024'].sum()
```

Uppdatera även docstrings på rad 22, 27-28, 32, 37, 45 där `CAPEX` nämns som kolumnnamn.

---

### extraction.py

Rad 62 - Ändra kolumnreferens:
```python
# ERSÄTT:
capex=float(row['CAPEX']),

# MED:
capex=float(row['Kapitalkostnad_2024']),
```

---

### kent_calculations.py

Rad 447-449 - Ta bort CAPEX från docstring:
```python
# ERSÄTT:
- Kapitalkostnad_2024: Årsvärde för 2024 (H1+H2) - används för DEA
- Kapitalkostnad_Period: Periodsumma 2024-2027 (8 halvår) - används för intäktsram
- CAPEX: Alias för Kapitalkostnad_2024 (bakåtkompatibilitet med DEA)

# MED:
- Kapitalkostnad_2024: Årsvärde för 2024 (H1+H2) - används för DEA
- Kapitalkostnad_Period: Periodsumma 2024-2027 (8 halvår) - används för intäktsram
```

Rad 472-473 - Ta bort CAPEX-alias (radera dessa rader helt):
```python
# TA BORT:
# CAPEX alias för bakåtkompatibilitet (årsvärde för DEA)
df['CAPEX'] = df['Kapitalkostnad_2024']
```

---

### post_dea.py

Rad 180 - Ändra kolumnreferens:
```python
# ERSÄTT:
df = pre_dea.df_all_companies[['REId', 'CAPEX']].copy()

# MED:
df = pre_dea.df_all_companies[['REId', 'Kapitalkostnad_2024']].copy()
```

Rad 184 - Ändra beräkning:
```python
# ERSÄTT:
'Kapitalkostnad_Total': df['CAPEX'] * 4

# MED:
'Kapitalkostnad_Total': df['Kapitalkostnad_2024'] * 4
```

---

### stage_outputs.py

Rad 19 - Uppdatera docstring:
```python
# ERSÄTT:
df_all_companies: pd.DataFrame  # 148 företag med CAPEX, OPEX, volumes

# MED:
df_all_companies: pd.DataFrame  # 148 företag med Kapitalkostnad_2024, OPEXp, volumes
```

Rad 33 - Uppdatera docstring:
```python
# ERSÄTT:
DataFrame med alla 148 företag, potentiellt modifierad CAPEX.

# MED:
DataFrame med alla 148 företag, potentiellt modifierad Kapitalkostnad_2024.
```

Rad 35 - Uppdatera kommentar:
```python
# ERSÄTT:
df_all_companies: pd.DataFrame  # 148 rows, potentially modified CAPEX/OPEX

# MED:
df_all_companies: pd.DataFrame  # 148 rows, potentially modified Kapitalkostnad_2024/OPEXp
```

---

### pre_dea.py

Uppdatera docstrings och kommentarer på följande rader där `CAPEX` refererar till kolumnnamnet:
- Rad 5: `CAPEX/OPEX` → `Kapitalkostnad_2024/OPEXp`
- Rad 37: `modified CAPEX/OPEX` → `modified Kapitalkostnad_2024/OPEXp`
- Rad 39: `CAPEX ändrades` → `Kapitalkostnad_2024 ändrades`
- Rad 78-79: `Ny CAPEX` → `Ny Kapitalkostnad_2024`
- Rad 94: `CAPEX skalad` → `Kapitalkostnad_2024 skalad`
- Rad 126: `baseline CAPEX` → `baseline Kapitalkostnad_2024`
- Rad 154: `baseline CAPEX` → `baseline Kapitalkostnad_2024`

---

## Verifiering

Kör efter ändringar:

```bash
# Ska ENDAST returnera rader i baseline_data.py som läser från Excel
grep -rn "df\['CAPEX'\]\|df\[\"CAPEX\"\]" *.py
```

Förväntat resultat: Endast träffar i `baseline_data.py` rad 80, 89, 95 och raden där vi gör `df["Kapitalkostnad_2024"] = df["CAPEX"]`.

```bash
# Ska returnera INGA träffar utanför baseline_data.py
grep -rn "'CAPEX'" *.py | grep -v "baseline_data.py"
```

Förväntat resultat: Tomt (inga träffar).

---

## Sammanfattning

| Fil | Ändringar |
|-----|-----------|
| baseline_data.py | 3 ställen |
| dea_calculations.py | 3 ställen |
| case_definition.py | 3 ställen |
| data_mapping.py | 4 ställen |
| wacc_scaling.py | 5 ställen + docstrings |
| extraction.py | 1 ställe |
| kent_calculations.py | 2 ställen (varav 1 radering) |
| post_dea.py | 2 ställen |
| stage_outputs.py | 3 docstrings |
| pre_dea.py | 7 docstrings/kommentarer |

**Version:** 1.0  
**Datum:** 2025-01-XX   
**Scope:** Beräkningsfiler (exkluderar infrastructure som registry, resolver, validation)

---
## 2. VAD BEHÖVS KONCEPTUELLT?

### 2.1 Pre-DEA

**Syfte:** Förbereda DataFrame (148 rader) med eventuellt modifierad CAPEX för DEA.

**Fyra metoder:**

| # | Metod | Beskrivning | Beräkningssteg |
|---|-------|-------------|----------------|
| 1 | Baseline | Använd Data_modeller utan ändringar | Inga |
| 2 | WACC-skalning | Skala Avkastning-kolumnen | Enkel skalning |
| 3 | Änding av parameter | Normvärden/livslängder → steg 5-8 | 5-8 (alla 148) |
| 4 | KENT-fil| KENT-fil → steg 1-4 → steg 5-8 | 1-4 (1), 5-8 (1) |

**Kombinationer:**
- WACC kan kombineras med metod 3 och 4 (parameter i steg 7)
- Vid kombination KENT + ändring av parametrar körs steg 1-4 på inloggat företag och sen 5-8 på alla 148

**Output:** DataFrame (148 rader) + metadata med modellspecifikation

---

### 2.2 DEA

**Syfte:** Beräkna effektivitet för alla 148 företag genom jämförelse.

**Input:**
- DataFrame (148 rader): DMU, CAPEX, OPEXp, volymer
- Modellspecifikation: inputs, outputs, RTS

**Process:**
- Super-efficiency DEA
- Outlier-identifiering (IQR-metod)
- Omberäkning utan outliers

**Output:** DataFrame (148 rader) med efficiency, potential, is_outlier

---

### 2.3 Post-DEA

**Syfte:** Beräkna intäktsram för inloggat företag.

**Steg:**
1. **Extraktion:** Filtrera DEA-output till 1 rad (inloggat företags REId)
2. **Effektiviseringskrav:** Beräkna Effkrav_proc från potential med antaganden om trunkering och fast krav för outliers
3. **Påverkbara kostnader:** Applicera effektiviseringskrav (OPEX eller TOTEX-metod)
4. **Intäktsram:** Summera alla komponenter

**Output:** Intäktsram_Total per år och periodsumma

---

## 3. FILER OCH FUNKTIONER SOM BEHÖVS
### KRITISKT: Dessa filer är ursprunligen anpassade för gammal struktur men själva beräkningarna är korrekta, vi måste därför anpassa dessa filer för att passa nya dataflödet med 148 vs. 1 företag.

### 3.1 Pre-DEA
1. Ladda all baselinedata för DEA genom _load_data_modeller(), produce_capex_from_baseline(), produce_opex_paverkbara_from_baseline(), produce_volumes_from_baseline() från baseline_loaders.py. Här är det nog bra att ändra namnen på funktionerna så det framgår att dessa ska in i DEA.**NOTERA:** Uppdaterad data_modeller.xlsx innehåller kolumner för avkastning och avskrivning, så funktion för detta behövs. **Det är dessa värden som ska kunna uppdateras!**
2. Ladda capbase_a.xlsx för alla företag.
3. WACC-funktioner: EiWaccInputs, _hamada(), och ei_wacc_real_pre_tax() från calculations.py eller wacc_calculations.py. Vi behöver hålla reda på vilken variabel som motsvarar den WACC som ska användas framöver (och vilka som bara är för visuellt).
3. CAPEX-metoder:
    - **Baseline**: Ingenting, produce_capex_from_baseline() från första dataladdningen.
    - **WACC-skalning**: Behöver skapa ny funktion som endast skalar avkastning i dataframen som ska in i DEA.
    - **Parameter-ändring**: Ändrade antaganden om livslängder och normvärden kräver att man kör om beräkningskedja 5-8 för alla företag => Se om apply_normvalue_adjustments() och apply_lifetime_adjustments() från parameter_adjustments.py räcker eller om vi behöver göra göra så att calculate_ages_and_nuav(), calculate_depreciation(), calculate_returns(), compile_capcost() i kent_pipeline.py behöver göras modulär. Troligtvis behöver vi kombinera dessa. Se även noteringen om behov av omvandling av tidskoder till år för att kunna skicka rätt capex (2024) till DEA.
    - **KENT-fil**: Inloggat företag laddar upp egen KENT-fil (med nya komponenter/investeringar) => återanvänd hela capbase_prep.py helt enkelt => om ingen annat antagande om parameter-ändring gjorts => fortsätt beräkningskedja 5-8 från kent_pipeline.py. **Kritiskt** Om wacc eller parameter (livslängd eller normvärden) ändrats, ersätt inloggat företags capbase från capbase_a med den som beräknats från KENT-fil genom beräkningskedja 1-4 => kör beräkningskedja 5-8 som beskrivs ovan.
    - **Kritiskt** Beräkningskedja 5-8 ska producera kapitalkostnader uppdelat på avskrivning och avkastning per id_network och år (2024-2027), samt en periodsumma per id_network för hela tillsynsperioden. Kapitalkostnaderna för år 2024 (tidskoder 229+230) med uppdelning på avskrivning, avkastning och total CAPEX skickas vidare till DEA-analysen. Därav måste vi se till att det finns en funktion som fixar det.

### 3.2 DEA
Hela backenden som behövs finns i dea_model.py, dock behövs kanske den göras om så att den ger output i rätt format.

### 3.3 Post-DEA
1. Extrahera potential och outlier-flagga för inloggat företag.
2. Om företag är outlier => fast krav.
3. Om företag inte är outlier => beräkna effektiviseringskrav från potential genom calculate_effkrav_from_potential() (tar en float) eller calculate_effkrav_for_dataframe() (tar dataframe)
4. Beräkning av påverkbara kostnder: Ta från funktionerna load_ir_paverkbara_baseline() och calculate_ir_paverkbara_export() i filen ir_calculations.py, men se till att det är den uppdaterade datan som används.
5. Summera och visualisera intäktsram: Funktioner kan tas från intaktsram_dekomposition.py, men vi **MÅSTE** se till att det är rätt data. Själva metoden i filen är rätt men den är anpassad för äldre data.

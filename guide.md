# Implementeringsguide: Incitamentjusteringar

## Bakgrund

Enligt Bilaga 4 i Ei:s föreskrifter justeras intäktsramen med tre incitament:

| Incitament | Syfte | Riktning |
|------------|-------|----------|
| **Kvalitetsincitamentet** | Premiera bättre leveranssäkerhet (färre/kortare avbrott) | Lägre AIT/AIF än norm → positivt incitament |
| **Nätförlustincitamentet** | Premiera lägre nätförluster | Lägre förlust än norm → positivt incitament |
| **Belastningsincitamentet** | Premiera högre utnyttjningsgrad | Högre utnyttjning än norm → positivt incitament |

Varje incitament begränsas individuellt till max 1/3 av avkastningen per år, och summan begränsas också till 1/3.

---

## 1. Incitamentjusteringens plats i intäktsramen

Incitamentjusteringen läggs till som **separat post** i intäktsramen:

```
Intäktsram_Total = Kapitalkostnad_Total
                 + Påverkbara_Periodsumma
                 + Opåverkbara_Kostnader
                 + Flexibilitetstjänster
                 + Avbrottsersättning_12_24h
                 - Avdrag_Statligt_Stöd
                 + Incitamentjustering_Total    <-- NY POST
```

### Fördelar med separat post

| Fördel | Beskrivning |
|--------|-------------|
| **Enkel dekomposition** | Kan visa kvalitet/nätförlust/belastning separat i UI |
| **Parametriserbar** | Enkelt att slå av/på komponenter, ändra normer, kostnader |
| **DEA opåverkad** | CAPEX i DEA förblir ren kapitalkostnad utan incitamentjusteringar |
| **Transparent** | Användaren ser exakt vad incitamentet bidrar med |
| **Minimal refaktorering** | Behövs endast lägga till en kolumn i intäktsram-assembleringen |

---

## 2. Per-år-data krav för 1/3-cap

Incitamentberäkningen kräver **avkastning per år** för att applicera begränsningarna korrekt:

```python
# Per år (4 gånger under perioden)
max_adj_year = avkastning_year / 3

# Varje incitament begränsas individuellt
inter_incentive = clip(inter_incentive_a, -max_adj_year, +max_adj_year)
loss_incentive  = clip(loss_incentive_a,  -max_adj_year, +max_adj_year)
util_incentive  = clip(util_incentive_a,  -max_adj_year, +max_adj_year)

# Summan begränsas också
incentive_year = clip(inter + loss + util, -max_adj_year, +max_adj_year)

# Sedan summeras över perioden
incentive_total = sum(incentive_year for year in 2024..2027)
```

**Viktigt:** Om man istället applicerar cap på periodsumman direkt (4 år) blir resultatet felaktigt. Begränsningen måste ske per år innan summering.

---

## 3. Avkastning per år - källor

Avkastning per år (`ret_year`) hämtas från olika källor beroende på `capex_method`:

| capex_method | Källa för `ret_year` |
|--------------|----------------------|
| `baseline` | SDF-kolumn "varav Kapital-bindning" (periodsumma) dividerat med 4 |
| `wacc_scaling` | Baseline-avkastning skalad med WACC-kvot: `baseline_ret_year * (new_wacc / baseline_wacc)` |
| `kent_upload` | Summera return-komponenter per år: `return_ord + return_tail` för båda halvor |
| `parameter_change` | Samma som kent_upload |

### Notering om enheter

- SDF-data är i **tkr** (tusen kronor)
- Incitamentberäkningen sker i **kr**
- Konvertera: `ret_year_kr = ret_year_tkr * 1000`
- Slutresultatet konverteras tillbaka till tkr för intäktsramen

---

## 4. Cap baseras på AVKASTNING, inte kapitalkostnad

En kritisk detalj: begränsningen (1/3-regeln) appliceras på **avkastningen** (return on capital), inte hela kapitalkostnaden:

```
Kapitalkostnad = Avskrivning + Avkastning
               = Kapital-förslitning + Kapital-bindning

Cap = Avkastning / 3    <-- ENDAST avkastningsdelen
```

Terminologin "WACC-justering" används eftersom incitamenten endast påverkar avkastningskomponenten.

---

## 5. Beräkningslogik - översikt

### 5.1 Kvalitetsincitamentet (inter_incentive)

Baseras på AIT (avbrottstid) och AIF (avbrottsfrekvens) per kundtyp och avbrottstyp:

```
inc = (norm - obs) * kostnad * årsmedeleeffekt * KPI
```

- 6 kundtyper (jordbruk, industri, handel/tjänster, offentlig, hushåll, gränspunkt)
- 2 avbrottstyper (aviserade, oaviserade)
- Totalt 24 delincitament som summeras

**CEMI4-korrigering:** Om andelen kunder med 4+ avbrott/år avviker från norm, reduceras kvalitetsincitamentet med upp till 25%.

### 5.2 Nätförlustincitamentet (loss_incentive)

```
loss_incentive = delningsfaktor * (nf_norm - nf_obs) * k_nf * e_in
```

- `delningsfaktor` = 0.75 (företaget får 75% av skillnaden)
- `k_nf` = nätförlustkostnad (kr/MWh)
- `e_in` = inmatad energi (MWh)

### 5.3 Belastningsincitamentet (util_incentive)

```
util_incentive = (ug_obs - ug_norm) * k_upstream
```

- `ug` = utnyttjningsgrad
- `k_upstream` = kostnad överliggande nät (kr)

Notera: Högre utnyttjning (obs > norm) ger **positivt** incitament.

---

## 6. Parametrar för framtida konfiguration

Följande parametrar bör kunna justeras i framtiden:

### Globala parametrar

| Parameter | Nuvarande värde | Beskrivning |
|-----------|-----------------|-------------|
| `ADJ_MAX_AGG` | 1/3 | Max justering per incitament (andel av avkastning) |
| `ADJ_MAX_CEMI4` | 0.25 | Max CEMI4-korrigering (25%) |
| `SHARING_NETLOSS` | 0.75 | Delningsfaktor nätförlust |

### Per-år-parametrar

| Parameter | Beskrivning |
|-----------|-------------|
| `KPI` | Prisjustering till 2022 års priser |
| `K_NF` | Nätförlustkostnad (kr/MWh) |

### Kostnadsviktning (per kundtyp och avbrottstyp)

- `AIT_COSTS[(ann, sni)]` - Avbrottstidskostnad (kr/kWh)
- `AIF_COSTS[(ann, sni)]` - Avbrottsfrekvenskostnad (kr/kW)

### Per-företag-variabler (från input-data)

- Normer: `ait_*_norm`, `aif_*_norm`, `nf_norm`, `ug_norm`, `cemi4_norm`
- Observerade: `ait_*_obs`, `aif_*_obs`, `nf_obs`, `ug_obs`, `cemi4_obs`
- Volymer: `ame_1..6`, `e_in`, `k_upstream`

---

## 7. REIds med saknad data

Fyra företag saknar fullständig incitamentdata och ska få `NaN` (eller 0 med flagga):

| REId | Företag |
|------|---------|
| 139 | Nackans Elnät AB |
| 168 | Skyllbergs Bruks AB |
| 177 | Sturefors Eldistribution AB |
| 3050 | Nackans Elnät AB (tidigare Viggafors) |

---

## 8. Backend-status

Beräkningslogiken är implementerad och verifierad:

- `incentive_parameters.py` - Alla konstanter
- `incentive_calculations.py` - Beräkningsfunktioner

**Testresultat:** Alla 11 resultatkolumner matchar Stata-facitfilen med max 5.5 kr skillnad (avrundningsfel mellan Python/Stata).

---

## 9. Implementeringssteg (översikt)

1. **Skaffa per-år avkastning** - Skapa funktion som returnerar `ret_year` baserat på `capex_method`
2. **Ladda incitament-input** - Hämta `all_adjust_vars.csv` (baseline-fil med normer och observerade värden)
3. **Kör beräkning** - Använd `calculate_all_incentives()` från `incentive_calculations.py`
4. **Lägg till i intäktsram** - Inkludera `Incitamentjustering_Total` som ny post
5. **UI-integration** - Visa dekomposition (kvalitet/nätförlust/belastning) i resultatvyn

---

## 10. Framtida utökningar
- **Parametriserbart UI** - Låt användaren justera normer, kostnader, delningsfaktorer
- **Export** - Inkludera incitamentdetaljer i Excel-export
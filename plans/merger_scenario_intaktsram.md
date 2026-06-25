# Plan (bordlagd): Fusionsscenario och kombinerad intäktsram

> **Status: bordlagd / framtida arbete.** Inget är byggt. Detta är ett
> tankedokument som fångar designen, beroendena och varningarna så att en
> framtida session (eller person) kan plocka upp tråden utan att börja om.
>
> **Kontext:** diskussion i juni 2026 om huruvida man, givet två (eller fler)
> geografiskt lämpliga elnätsföretag, kan beräkna deras *kombinerade* intäktsram,
> inte som en naiv summa utan som ett fullständigt scenario, eftersom flera
> komponenter har interaktionseffekter. Hör ihop med det isolerade delprojektet
> `dea_rpy2_benchmarking/` (DEA via R-paketet Benchmarking) och dess
> `dea.merge`-genomgång (`dea_rpy2_benchmarking/BENCHMARKING_CAPABILITIES.md`).

---

## 1. Två skilda frågor (håll isär dem)

Det finns två relaterade men olika "fusionsfrågor". Båda är värda att kunna svara på,
men de besvaras med olika verktyg.

- **(A) Vilken intäktsram får den fusionerade enheten under regleringen?**
  Besvaras genom att **köra om hela intäktsrams-pipelinen** på en modifierad
  population (två DMU:er ersatta av en sammanslagen). Detta är huvudfrågan i detta
  dokument.
- **(B) Vilken potentiell effektiviseringsvinst finns i själva fusionen?**
  Besvaras med `dea.merge` (`learning` / `harmony` / `size` / `Estar`). En
  teknologisk potential, inte en kronpost.

**Koppling:** interaktionseffekten i (A) *är* i praktiken DEA-fusionseffekten i (B).
Den sammanslagna firmans DEA-poäng (som driver effektivitetskravet på den påverkbara
kostnaden) är just det `dea.merge` rapporterar som `Eff`, och `learning/harmony/size`
förklarar *varför*. Så (B) är en förklaringsmodell ovanpå (A).

---

## 2. Kandidatgenerering (vilka fusioner är giltiga)

`dea.merge` och pipelinen *utvärderar* en given fusion; de *söker* inte. Vilka
bolag som är lämpliga kandidater måste avgöras i ett separat lager.

- **Geografi (hård restriktion).** Två elnät kan realistiskt bara slås ihop om de
  **gränsar till varandra**. Bygg en grannskapsgraf ur shapefilen:
  - Logiskt namn: `network_areas_shapefile` →
    `data/raw/shapefiles/all_network_operator_areas.shp`
    (registrerat i `config/data_paths.py`).
  - Granne = delar gräns (`touches` / `intersects` i geopandas/shapely).
  - Begränsar kandidater till sammanhängande kluster **och** gör sökningen körbar
    (148 bolag → ~10 800 par utan restriktion; grannskap beskär detta drastiskt).
  - **Varning:** utan denna restriktion slår DEA-matematiken gärna ihop ett bolag
    i Skåne med ett i Norrbotten och rapporterar en fysiskt meningslös "skalvinst".
- **Övriga variabler (filter eller redovisning, inte fusionsmatematik).**
  Intäktsram, nätförluster, kundtäthet m.m. kan användas som
  similaritets-/rimlighetsfilter i kandidatsteget, eller bara redovisas bredvid.
  De påverkar **inte** beräkningen om de inte införs som DEA-input/output, och då
  ändras modellspecen (se §6, varning om låst spec).

---

## 3. Kärninsikten: kombinerad intäktsram ≠ naiv summa

Intäktsramen monteras i
[`calculations/revenue_frame_assembly.py`](../calculations/revenue_frame_assembly.py)
(`assemble_revenue_frame`, topp-nivå) som:

```
REVENUE_FRAME_TOTAL =  CAPITAL_COST_IN_RF
                     + CONTROLLABLE_IN_RF          (efter effektiviseringsavdrag)
                     + NON_CONTROLLABLE_COST
                     + FLEXIBILITY_SERVICES
                     + INTERRUPTION_COMPENSATION
                     - STATE_SUBSIDY_DEDUCTION
                     + INCENTIVE_ADJUSTMENT_TOTAL
```

Vissa termer är additiva över bolag, andra inte. **Det är de icke-additiva som gör
att man måste köra ett scenario, inte summera.**

### 3.1 Additiva komponenter (får summeras rakt av)

| Komponent | Kolumnkonstant | Varför additiv |
|-----------|----------------|----------------|
| Kapitalkostnad (avskrivning + avkastning) | `COL_CAPITAL_COST_IN_RF` | Kapitalbasen behåller sitt konserverade värde (värdekonsistent övergång); summeras per nätområde. Se `kapitalbas_vardering_och_dashboard.md`. |
| Icke-påverkbar kostnad | `COL_NON_CONTROLLABLE` | Nätnivåkostnader (stationer, kablar, anslutningar) summeras per område. |
| Flexibilitetstjänster | `COL_FLEXIBILITY` | Bolagsspecifik baspost. |
| Avbrottsersättning (kronpost) | `COL_INTERRUPTION` | Bolagsspecifik baspost. |
| Avdrag statligt stöd | `COL_STATE_DEDUCTION` | Tillgångsspecifikt avdrag. |
| **Rå** påverkbar kostnadsbas (före avdrag) | `COL_CONTROLLABLE_AVG` | SDF-snitt 2018–2021, summeras per bolag. |

Kolumnkonstanter: [`config/column_names.py`](../config/column_names.py).

### 3.2 Icke-additiva komponenter (kräver omkörning)

| Komponent | Var | Varför INTE additiv vid fusion |
|-----------|-----|--------------------------------|
| **DEA-effektivitet** | [`calculations/frontier/dea_calculations.py`](../calculations/frontier/dea_calculations.py) | Den sammanslagna DMU:n får **en** poäng, inte två, och **fronten flyttar sig** (två DMU:er bort, en större in). In-/output summeras rent, men poängen är en frontfunktion. |
| **Effektivitetskravet** (`1 − eff`, trunkerat → årlig %) | [`calculations/efficiency/efficiency_requirement.py`](../calculations/efficiency/efficiency_requirement.py) | Härleds ur DEA-potentialen; inte medel av de två bolagens krav. |
| **Påverkbar kostnad efter avdrag** | [`calculations/opex/controllable_cost_calculations.py`](../calculations/opex/controllable_cost_calculations.py) | Kronbasen additiv, men *procenten* är den sammanslagna firmans enda krav applicerat på den kombinerade basen (kumulativt över 4 år). TOTEX-metoden splittar dessutom avdraget OPEX/CAPEX efter den sammanslagna firmans ratio. |
| **Incitamentsjustering** (kvalitet, nätförlust, last) | [`calculations/incentive/incentive_calculations.py`](../calculations/incentive/incentive_calculations.py) | Räknas på den sammanslagna firmans egna KPI:er (norm vs utfall) och takas mot dess avkastning (≈ fördubblad). Summan av två ≠ den sammanslagna. |

---

## 4. Spridningseffekten (relativ reglering)

DEA jämför alla mot alla. En fusion flyttar fronten för **hela populationen**, så
strikt sett ändras effektivitetskravet (och därmed intäktsramen) **en liten gnutta
för samtliga ~148 bolag**, inte bara för de två som fusionerar. Ett "fullständigt
scenario" är därför rätt mentalmodell: en fusion är inte en lokal operation på två
rader. En scenariokörning bör därför rapportera både:
- den fusionerade enhetens intäktsram, och
- nettoförändringen för övriga bolag (spridningen).

---

## 5. Föreslaget flöde för (A) intäktsramsscenario

1. **Välj kandidater** (REId-par/kluster), filtrerade på grannskap (§2).
2. **Bygg den sammanslagna DMU:n** i baseline-datan:
   - Summera DEA-input/output: `CAPEX, OPEXp` och `CU, MW, NS, MWhl, MWhh`.
   - Summera de additiva intäktsramskomponenterna (§3.1).
   - Definiera den sammanslagna firmans incitamentsnormer (se varning §7.1).
   - Ta bort de två ursprungliga REId:erna, lägg till en sammanslagen REId.
3. **Kör om pipelinen** på den modifierade populationen (DEA → effektivitetskrav →
   påverkbar kostnad efter avdrag → incitament → `assemble_revenue_frame`).
   Orkestrering: [`pipeline/core.py`](../pipeline/core.py) (`run_pipeline`),
   post-DEA-steget [`pipeline/stages/post_dea.py`](../pipeline/stages/post_dea.py).
4. **Läs av och jämför:**
   - fusionerad intäktsram vs **naiv summa** (differensen = interaktionseffekten),
   - spridningseffekt på övriga bolag (§4),
   - lägg `dea.merge`-dekomponeringen (`learning/harmony/size`) bredvid som
     förklaring (§1, fråga B).

---

## 6. Beroenden och kopplingar (sammanfattning)

- **Repo-data via registret.** Hårdkoda aldrig `data/`-vägar; gå via
  `config/data_paths.py` (`network_areas_shapefile`, `data_modeller`, m.fl.).
- **DEA-spec är låst till Ei:s baseline.** Input `[capital_cost_2024, opexp_dea]`,
  output `[CU, MW, NS, MWhl, MWhh]`, CRS, input-orienterad. Att lägga in
  intäktsram/nätförluster som DEA-variabler bryter facit-specen i
  `eis_dea_metod.md` och bör i så fall vara ett uttryckligt, separat beslut.
- **`dea_rpy2_benchmarking/`** ger R/Benchmarking-motorn (`dea`, `sdea`, `dea.merge`).
  `ei_replication/` visar redan att R-motorn reproducerar Ei:s DEA exakt
  (~8·10⁻¹¹), så DEA-delen av scenariot kan köras antingen via projektets
  PuLP-pipeline eller via R, med samma resultat.
- **Pipeline-stegen** måste kunna köras på en godtycklig population, inte bara de
  fasta 148. Kontrollera att inget steg hårdkodar antalet bolag eller en specifik
  REId-mängd innan detta byggs.

---

## 7. Varningar (läs innan något byggs)

### 7.1 Incitamentsnormerna är den enda icke-mekaniska biten
Norm-värden (nf_norm, ug_norm, kvalitetsnormer) är per kund / per ledningslängd, så
den sammanslagna firmans norm är **inte** en summa, den måste räknas om på det
kombinerade nätets egenskaper. Utfallsvärden (faktiska förluster, levererad energi)
summeras, men normerna kräver tankearbete. Detta är den största öppna frågan.

### 7.2 VRS ger `Inf`
En fusion blir ofta större än allt i urvalet → utanför VRS-teknologin → olösbar
input-orienterad LP → `Inf`/`NaN` (verifierat i `dea.merge`-genomgången). Kör **CRS**
för fusionsscenarier (vilket också är Ei:s DEA-spec), eller hantera Inf explicit.

### 7.3 Sök på rätt storhet
En naiv sökning som rangordnar på total `Eff` belönar bolag som bara är dåligt
skötta var för sig (det fångas av `learning`). Vill man hitta *äkta* fusionsvärde
ska man söka på `Estar` (= `harmony × size`), inte `Eff`.

### 7.4 Modellen fångar regleringen, inte verkliga driftsynergier
Scenariot räknar den *regulatoriska* intäktsramen givet de sammanslagna
*historiska* kostnaderna och volymerna. Att två bolag faktiskt skulle bli billigare
att driva efter en fusion (verklig OPEX-besparing) ligger utanför, det är
`dea.merge`-potentialen, inte pipeline-utfallet.

### 7.5 Giltighet som analysunderlag
Pipelinen reproducerar **nuvarande reglering** (RP4, WACC 4.53 %). Ett
fusionsscenario är alltså "allt annat lika under nuvarande regler", en
mekanismanalys, inte en prognos för RP5. Kapitalbasvärderingsbytet 2028, KPI-
omindexering, ny 8-årig WACC och anslutningsavgiftsavdrag finns inte i datan
(se `kapitalbas_vardering_och_dashboard.md`, §"Gränser").

---

## 8. Öppna frågor att besluta innan bygge

1. **Klusterstorlek:** bara par, eller även tripplar/större grannkluster?
2. **Incitamentsnormer (§7.1):** hur definieras den sammanslagna firmans normer?
   (Längd-/kundviktat snitt? Behöver underlagskolumner identifieras i
   `data/raw/adjustments/all_adjust_vars.csv`.)
3. **Övriga variabler:** ska intäktsram/nätförluster vara *filter* i kandidatsteget
   eller bara redovisas bredvid resultatet?
4. **Motor:** köra DEA-delen via projektets PuLP-pipeline (enklast, återanvänder
   allt) eller via R/Benchmarking (möjliggör `dea.merge`-dekomponeringen i samma
   körning)? Troligen båda: PuLP för intäktsramen, R för `dea.merge`-förklaringen.
5. **Placering:** ny modul i `dea_rpy2_benchmarking/` (isolerat) eller som ett
   verktyg som lånar pipeline-stegen direkt? Påverkar hur tätt det kopplas till
   appen.

---

## 9. Relaterade dokument

- `dea_rpy2_benchmarking/README.md` — R/Benchmarking-bryggan.
- `dea_rpy2_benchmarking/BENCHMARKING_CAPABILITIES.md` — full katalog, inkl.
  `dea.merge`-dekomponeringen.
- `dea_rpy2_benchmarking/ei_replication/README.md` — exakt DEA-replikering.
- `eis_dea_metod.md` — Ei:s DEA-metod och den låsta input/output-specen.
- `kapitalbas_vardering_och_dashboard.md` — kapitalbasens giltighet och gränser.
- `ARCHITECTURE.md` — pipeline-lager och intäktsramsmontering.

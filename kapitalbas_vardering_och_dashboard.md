# Värderingsprincip för kapitalbasen och dashboardets giltighet som analysunderlag

Sammanfattning av diskussion om hur Ei:s byte av värderingsprincip påverkar den
nuvarande kapitalbasen, och vad det betyder för att använda pipeline- och
new_benchmarking_model-datan som utgångspunkt för analyser.

Källa: [docs/ei_to_markdown/outputs/inriktning-reglering-intaktsramar-2028-2031.md](docs/ei_to_markdown/outputs/inriktning-reglering-intaktsramar-2028-2031.md)
(Ei: "Inriktning för reglering av elnätsföretagens intäktsramar 2028–2031", presentation,
101 slides, hämtad 2026-06-05). Radhänvisningar nedan avser den markdown-filen.

---

## 1. Ei byter värderingsprincip från och med tillsynsperioden 2028–2031

Tre alternativ analyserades (rad 209-213):

- **Nuvarande hantering** – anläggningarna marknadsvärderas enligt en **kapacitetsbevarande
  princip** (normvärdeslista + sektorsspecifikt index).
- **Alternativ 1** – fortsatt kapacitetsbevarande, men med korrigering för
  nettonuvärdesneutralitet. Valdes bort (rad 215-221).
- **Alternativ 2 (vald inriktning)** – anläggningarna värderas enligt en
  **förmögenhetsbevarande princip** till ursprungliga anskaffningsvärden.

> "**Nuvarande hantering:** Anläggningarna marknadsvärderas enligt en kapacitetsbevarande
> princip." / "**Inriktning från och med tillsynsperioden 2028–2031:** Anläggningarna värderas
> enligt en förmögenhetsbevarande princip." (rad 168, 170)

Definitioner (rad 176-177):

- **Förmögenhetsbevarande** – kostnadstäckning utifrån verkliga anskaffningsvärden för
  genomförda investeringar.
- **Kapacitetsbevarande** – anläggningarna marknadsvärderas till vad det kostar att anskaffa
  motsvarande anläggningar idag.

Skälet till bytet: marknadsvärderingen skapar risk för systematisk över- eller
underavkastning eftersom olika index används för att värdera basen (sektorsspecifikt) och för
att beräkna den reala kalkylräntan (allmänt index), och dessa har historiskt skilt sig åt
(rad 185-199).

---

## 2. Hur den NUVARANDE kapitalbasen förändras vid bytet

Detta är kärnfrågan. Svaret: **den nuvarande kapitalbasen omvärderas inte retroaktivt – den
behåller sitt värde vid övergången.**

Ei väljer **värdekonsistent metod** för den ingående kapitalbasen, av tre möjliga
övergångsmetoder (rad 245-277):

| Övergångsmetod | Innebörd | Status |
|----------------|----------|--------|
| **Metodkonsistent** | Räknar om restvärdet som om förmögenhetsbevarande principen gällt under hela livslängden | Vald bort: uppfyller inte krav på förutsägbarhet, stor värdepåverkan (rad 247, 254-256) |
| **Värdekonsistent** | Utgår från det nuvarande kapacitetsbevarande restvärdet; marknadsvärderingen t.o.m. 2027 konserveras | **VALD** (rad 248, 259-261) |
| **Parallell** | Kör båda principerna parallellt under anläggningarnas livslängd | Vald bort: administrativ börda i upp till 75 år (rad 263-267) |

> "Befintliga anläggningar behåller därmed värdet de har i nuvarande metod vid övergången till
> en förmögenhetsbevarande princip tillsynsperioden 2028–2031." (rad 276)

> "Anläggningar som anskaffats från och med tillsynsperioden 2028–2031 ska värderas med
> ursprungligt anskaffningsvärde enligt den förmögenhetsbevarande principen." (rad 277)

Effekten på kort sikt är liten:

> "**Förändringar i kapitalbasvärdering** ... På kort sikt: Mycket små effekter till RP5." (rad 730-733)

### Vad som faktiskt ändras för den befintliga basen framåt

Mekaniken (avskrivning + avkastning) fortsätter på det konserverade värdet, men **två
parameter-/metodbyten** gäller även den befintliga basen:

1. **Indexbyte:** basen prisjusteras framåt med **KPI** i stället för sektorsspecifikt
   index/normvärden, från beräkningen av kapitalkostnaderna för första halvåret 2028
   (rad 301, 315). Här uppstår den reella driften över tid (liten i RP5, växande därefter).
2. **Kalkylräntan:** real WACC räknas om på **åttaårig historik** och deflateras med KPI
   (rad 452-457, 491). Sannolikt lägre intäktsram i RP5 enligt Ei (rad 738).

---

## 3. Terminologisk precisering: "befintlig" vs "nuvarande" kapitalbas

"Befintlig", "nuvarande" och "ingående" kapitalbas är **synonymer** – samma anläggningar
(den kapitalbas som rapporterades inför 2024–2027 inkl. investeringar/utrangeringar den
perioden, rad 243). Det finns inte två olika sorters kapitalbas.

Skillnaden ligger i **tre separata begrepp** som lätt blandas ihop:

1. **Tillgångarna** – befintliga anläggningar (före 2028) vs nya (från 2028).
2. **Värderingsprincipen** – kapacitetsbevarande (t.o.m. 2027) vs förmögenhetsbevarande
   (fr.o.m. 2028).
3. **Övergångsmetoden** – värdekonsistent metod = bron som sätter ingångsvärdet i den nya
   principen lika med det gamla kapacitetsbevarande värdet.

Det korrekta: **samma uppsättning befintliga anläggningar värderas kapacitetsbevarande t.o.m.
2027 och förmögenhetsbevarande fr.o.m. 2028, med den värdekonsistenta metoden som bro.**

---

## 4. Konsekvens för dashboardet (main pipeline + new_benchmarking_model)

**Slutsats: datan och outputen är en rimlig utgångspunkt för att analysera mekanism-
förändringar (t.ex. ett tvåsidigt effektiviseringskrav) "allt annat lika".**

Varför det håller:

1. **Det nuvarande kapitalbasvärdet ÄR ingångsvärdet för 2028.** Den värdekonsistenta metoden
   låser in just det kapacitetsbevarande restvärde som ligger i
   [data/rab_and_capex/capbase_a.parquet](data/rab_and_capex/capbase_a.parquet) (rad 248, 276).
2. **new_benchmarking_model rör inte värderingsprincipen, bara mekaniken.** Verifierat i koden:
   - TOTEX byggs av `controllable_cost_average`, nätförluster till gemensamt pris, utvalda
     icke-påverkbara poster och kapitalkostnaden. Den enda justeringen av kapitaldelen är en
     förläggningsmiljö-korrigering för DEA-jämförbarhet, inte ett byte av värderingsprincip
     (se ARCHITECTURE.md §20).
   - Kronbasen för det nya kravet är den **ojusterade** TOTEX med ojusterad kapitalkostnad;
     förläggningsmiljö-korrigeringen sätter procenten men aldrig kronbasen (ARCHITECTURE.md §20).
   - [new_benchmarking_model/efficiency/efficiency_requirement_two_sided.py](new_benchmarking_model/efficiency/efficiency_requirement_two_sided.py)
     ändrar bara hur effektiviteten översätts till krav (signerat gap till E75), inte
     kapitalbasen.
3. **Ei:s egen bedömning:** kapitalbasvärderingsbytet ger "mycket små effekter till RP5"
   (rad 733), så nuvarande värde är en bra proxy för ingångsvärdet på kort sikt.

### Gränser – vad datan INTE fångar

- **Inga nya förmögenhetsbevarande investeringar.** Datan är den *befintliga* basen.
  Anläggningar från 2028 (anskaffningsvärde) finns inte här. Bra för "befintlig bas +
  mekanismändring", inte för att projicera en framtida bas full av nyinvesteringar.
- **Ingen KPI-omindexering och ingen ny åttaårig WACC** är inbyggd – pipelinen reproducerar
  nuvarande reglering (RP4, WACC 4.53 %).
- **Inget anslutningsavgiftsavdrag** (ny post från 2028, rad 567-572).

Som *anchor* för "hur rör en mekanismförändring intäktsramen, allt annat lika" är datan giltig.
Som *prognos för RP5:s faktiska kapitalkostnad* fattas index-, WACC- och nyinvesteringsbitarna.

---

## Sammanfattande tabell

| Aspekt | Nuvarande (t.o.m. 2027) | Inriktning (fr.o.m. 2028) | I dashboardet |
|--------|--------------------------|----------------------------|---------------|
| Värderingsprincip | Kapacitetsbevarande (marknadsvärde) | Förmögenhetsbevarande (anskaffningsvärde) | Kapacitetsbevarande (RP4) |
| Befintlig bas vid övergång | – | Behåller värdet (värdekonsistent metod) | = ingångsvärdet, giltig anchor |
| Prisjustering av basen | Sektorsspecifikt index/normvärden | KPI (allmänt index) | Ej omindexerad |
| Kalkylränta | Real WACC, mix prognos/historik | Real WACC, 8-årig historik, KPI-deflator | 4.53 % (RP4) |
| Nya investeringar fr.o.m. 2028 | – | Anskaffningsvärde, KPI | Saknas i datan |
| Anslutningsavgifter | Avstäms efter perioden | Avdrag från intäktsramen | Saknas i pipelinen |

# Övergången i Ei:s effektiviseringsincitament — teknisk tolkning

> **Status:** Arbetsdokument / tolkning. Bygger på Ei:s publicerade inriktningar
> (dec 2025 + våren 2026), den nuvarande DEA-baserade kravmetoden, samt
> Ofgems *RIIO-ED2 Final Determinations* (Core Methodology + Overview, feb 2023)
> som Ei refererar till. Skiljer uttryckligen på vad som är **säkert givet vår
> tolkning** och vad som **fortfarande är ospecificerat** i Ei:s material.

---

## 1. Sammanhang

Ei avser att gå från dagens kostnadseffektivitetsmetod (effektiviseringskravet)
till en **TOTEX-lösning** där samtliga kostnadsposter ingår i effektivitets-
bedömningen. Tillämpningen sker via **enstegsmetoden**: en benchmarking på
historiska data omvandlas till ett utfall i procent, som appliceras på samma
periods totala kostnadsnivå och påverkar nästa tillsynsperiods intäktsram.

Två centrala principiella inriktningar:

1. **Inget särskilt generellt effektiviseringskrav** — den branschgemensamma
   produktivitetsutvecklingen antas redan ligga i det faktiska kostnadsutfallet,
   och den rörliga relativa gränsen antas ge fortsatt tryck.
2. **Full kostnadstäckning vid tredje kvartilen (75:e percentilen)** — en rörlig,
   relativ gräns i stället för en fast (t.ex. "90 % effektivitet"). Realiserings-
   tiden ligger kvar på **8 år**.

Detta dokument tolkar vad punkt 2 innebär *mekaniskt*, och hur den nya modellen
förhåller sig till dagens.

---

## 2. Nuvarande modell — DEA → årligt effektiviseringskrav

Dagens kedja (föregående reglerperiod), för referens:

**Steg 0 — DEA-poäng.** DEA ger ett effektivitetstal `E_i ∈ (0, 1]`
(`1` = fronten). Potential mot fronten:

```
potential = 1 − E_i
```

**Steg 1 — Trunkering.** Potentialen kapas till ett intervall:

```
potential_kapad = clip(potential, 0.1624, 0.30)
```

- Tak `truncation_max = 0.30`
- Golv `truncation_min ≈ 0.1624` (baklängesräknat så att det ger exakt 1 %/år)

**Steg 2 — Customer sharing.** Halva ineffektiviteten realiseras som krav:

```
× 0.50
```

**Steg 3 — Realiseringstid.** Potentialen ska realiseras över 8 år, men kravet
sätts per 4-årig tillsynsperiod:

```
× (4 / 8) = × 0.50
```

**Steg 2 + 3** ⇒ potentialen multipliceras med `0.25` för periodens
effektivisering:

```
total_effektivisering_perioden = potential_kapad × 0.50 × (4/8)
```

**Steg 4 — Annualisering** (sammansatt):

```
årligt_krav = (1 + total_effektivisering_perioden)^(1/4) − 1
```

**Steg 5 — Outliers.** DEA-outliers får inte ett DEA-baserat krav utan ett fast
`outlier_req = 1 %/år`.

**Hela kedjan:**

```
årligt_krav = (1 + clip(1 − E_i, 0.1624, 0.30) × 0.50 × 4/8)^(1/4) − 1
```

Egenskap att notera: **referenspunkten är fronten (`E = 1`)**, potentialen är
alltid `≥ 0`, och därför får **alla** företag ett avdrag.

---

## 3. Den nya modellen — vår bästa och rimligaste tolkning

### 3.1 Den principiella förändringen

Två saker ändras jämfört med dagens modell:

1. **Referenspunkten flyttas** från fronten (`E = 1`) till
   tredjekvartilsföretaget (`E₇₅`, effektivitetspoängen vid 75:e percentilen).
2. **Tecknet kan bli negativt.** Gapet mot referensen kan vara positivt
   (företaget är mindre effektivt → avdrag) eller negativt (mer effektivt →
   tillägg). Dagens modell tillät bara avdrag.

I övrigt antas maskineriet (sharing, realiseringsskalning, annualisering, någon
form av kapning) i allt väsentligt vara kvar — se osäkerheterna i avsnitt 6.

### 3.2 Referensbytet: front → tredje kvartilen

```
Gammal referens:   E_ref = 1            (fronten)
Ny referens:       E_ref = E₇₅          (75:e percentilen = tredje kvartilen)
```

`E₇₅` är **rörlig**: den räknas om varje tillsynsperiod ur den aktuella
tvärsnittsfördelningen av effektivitetspoäng. När branschen som helhet blir
effektivare sjunker `E₇₅`-företagets kostnadsnivå, och ribban höjs automatiskt.
Det är denna självkalibrering som Ei lutar sig mot i stället för ett separat
generellt krav.

### 3.3 Signerad potential

Dagens `potential = 1 − E_i` ersätts av ett **signerat** gap mot tredje kvartilen:

```
signerad_potential = E₇₅ − E_i
```

- `E_i < E₇₅`  ⇒  `signerad_potential > 0`  ⇒  **avdrag** på intäktsramen
- `E_i = E₇₅`  ⇒  `signerad_potential = 0`  ⇒  **full kostnadstäckning** (noll effekt)
- `E_i > E₇₅`  ⇒  `signerad_potential < 0`  ⇒  **tillägg** på intäktsramen

Eftersom tröskeln ligger vid 75:e percentilen är det per definition den översta
fjärdedelen (företag på eller över `E₇₅`) som får full täckning eller mer — vilket
är exakt Ei:s formulering att "en fjärdedel av företagen skulle få full
kostnadstäckning eller mer".

### 3.4 Skattat periodutfall (analogt med dagens kedja)

En rimlig fortsättning som speglar dagens pipeline, med en (möjligen separat)
skalningsfaktor `s` för sharing/realiseringstid och en kapning `cap`:

```
utfall_perioden = clip( (E₇₅ − E_i) × s , −cap , +cap )

årligt_utfall   = (1 + utfall_perioden)^(1/p) − 1     # p = antal år i perioden
```

där `årligt_utfall < 0` motsvarar ett tillägg och `> 0` ett avdrag. Notera att
`s` och `cap` här är platshållare — deras värden (och om de är symmetriska för
tillägg respektive avdrag) är **inte** fastlagda; se avsnitt 6.

### 3.5 Percentilens två roller

Percentilen gör **två** distinkta jobb — och *bara* dessa två:

1. **Tröskelsättning:** avgör vem som hamnar på avdrags-, noll- respektive
   tilläggssidan.
2. **Val av referensvärde:** pekar ut vilket kardinalt effektivitetstal (`E₇₅`)
   som gapet mäts emot.

Percentilen styr **inte** magnitudens storlek direkt. Storleken kommer från det
**kardinala** avståndet `E₇₅ − E_i`.

### 3.6 Varför magnituden är kardinal, inte rang-baserad

Det starkaste argumentet följer av att effektivitetspoängen **klustrar tätt** nära
toppen. I RIIO-ED2 låg 75:e percentilen på `≈ 0,99` och 85:e på `≈ 0,98`
(ED1: övre kvartil `0,97`).

- **Kardinal magnitud** ger små justeringar för företag som faktiskt är nästan
  lika effektiva — rimligt.
- **Rang-/percentilbaserad magnitud** skulle blåsa upp bråkdelsskillnader: två i
  praktiken identiska företag (t.ex. `0,985` vs `0,984`) kan ligga långt isär i
  rang och få mycket olika utfall — godtyckligt och snedvridande.

Dessutom: robustheten mot DEA-brus och frontoutliers levereras redan av att
*tröskeln* backas från fronten till 75:e percentilen. Man behöver inte också
offra den kardinala informationen i magnituden — det vore att betala två gånger
för samma robusthet och kasta bort information om *hur* ineffektivt ett företag är.

---

## 4. Koppling till den brittiska förebilden (RIIO-ED2)

Ei refererar uttryckligen till Storbritannien för tredjekvartilsvalet. Relevant
kontext från Ofgems *RIIO-ED2 Final Determinations* (feb 2023):

- **Riktmärket väljs via percentil i en kardinal poängfördelning.** ED2 använder
  ett viktat snitt av tre totex-regressionsmodeller (16,67 % vardera) plus en
  disaggregerad benchmarking (50 %). Riktmärket sätts vid 75:e percentilen i denna
  sammanvägda fördelning — inte i en enskild regression.
- **Glidbana 75 → 85.** ED2 nöjer sig inte med tredje kvartilen statiskt utan
  glider från 75:e till 85:e percentilen över tre år (85:e gäller de två sista
  åren). 75:e percentilen var målnivån redan i ED1 och är ED2:s startpunkt år 1.
- **Separat löpande effektivitetskrav.** Ofgem lägger dessutom ett *ongoing
  efficiency*-krav på `1,0 % per år` för **alla** företag, ovanpå
  percentil-riktmärket.
- **Låg materialitet i percentilvalet.** Eftersom poängen klustrar (`0,99` vs
  `0,98`) är skillnaden mellan att tillämpa enbart 75:e percentilen och glidbanan
  till 85:e bara ca `112 mn £`, eller `0,44 %` av intäktsramarna.
- **Regulatory judgement.** Ofgem understryker att valet av riktmärke ytterst är
  en fråga om regleringsmässigt omdöme, motiverat av förbättrad datakvalitet och
  jämförbarhet.

**Skillnad mot Ei:** Ei beskriver hittills bara den *statiska* tredjekvartil-
versionen (= Ofgems ED1-nivå / ED2:s startpunkt), **utan** glidbana till 85:e och
**utan** ett separat löpande 1 %-krav. Ei förlitar sig alltså tyngre på att enbart
den rörliga relativa gränsen ska driva branschens produktivitet. Detta är en
genuint svagare konstruktion än den brittiska förebilden den hänvisar till.

---

## 5. Vad som är säkert (givet vår tolkning)

1. **Percentilen sätter tröskeln.** Avdrag under `E₇₅`, noll vid `E₇₅`, tillägg
   över. (Direkt ur Ei:s text.)
2. **Tröskeln är rörlig och relativ.** `E₇₅` räknas om per period ur den aktuella
   fördelningen; ingen fast absolut effektivitetsnivå. (Direkt ur Ei:s text.)
3. **Den översta fjärdedelen får full täckning eller mer.** Följer av att
   tröskeln är just 75:e percentilen. (Direkt ur Ei:s text.)
4. **Magnituden är kardinal, inte rang-baserad.** Storleken på avdrag/tillägg
   speglar det kardinala gapet `E₇₅ − E_i`. (Stark slutsats av klustringsevidensen
   och konsistens med RIIO-ED2:s mekanik — vår tolkning, inte explicit hos Ei.)
5. **Referenspunkten flyttas front → tredje kvartil.** Den enda principiella
   skillnaden mot dagens `1 − E_i` är att `1` byts mot `E₇₅` och att tecknet kan
   bli negativt. (Vår tolkning.)
6. **Realiseringstiden förblir 8 år.** Någon period-/realiseringsskalning lär
   därför finnas kvar. (Direkt ur Ei:s text; skalningens exakta form osäker.)

---

## 6. Vad som är osäkert (ospecificerat i Ei:s material)

1. **Funktionsformen för omvandling effektivitet → procent.** Linjär i gapet?
   Ratio (`1 − E_i/E₇₅`)? Något annat? Inte fastlagt.
2. **Customer sharing.** Ei:s "få behålla en del av effektiviseringen" antyder en
   sharing-faktor `< 1`, men varken dess existens i ny form eller dess värde
   (`0,50`?) är bekräftade.
3. **Symmetri belöning vs straff.** Oklart om tillägg ovanför `E₇₅` skalas med
   samma faktor som avdrag nedanför. Asymmetri är fullt möjlig.
4. **Taket på magnituden (`cap`).** Detta är **explicit** en av Ei:s öppna frågor
   till våren 2026 ("hur mycket incitamentet som mest ska kunna påverka
   intäktsramen") — i praktiken den nya modellens motsvarighet till dagens
   `truncation_max = 0,30`.
5. **Golv / outlier-hantering.** Dagens golv (`16,24 %`, baklängesräknat till
   1 %/år) och outlier-regeln är konceptuellt mindre meningsfulla när referensen
   inte längre är fronten och gapen därmed blir mindre. Oklart vad som ersätter dem.
6. **Benchmarkingmotorn.** Om svensk modell, liksom ED2, väger flera modeller
   (totex-regression + disaggregerat) eller behåller ren DEA — och hur `E₇₅`
   då definieras — är inte specificerat.
7. **Justeringar för olika förutsättningar.** Skillnader i elpris mellan elområden
   (nätförlustkostnader), markförutsättningar (investeringskostnader) m.m. utreds
   under första halvan av 2026 och påverkar hur `E_i` beräknas.

---

## 7. Modelljämförelse i en formel

**Nuvarande (front som referens, endast avdrag):**

```
årligt_krav = (1 + clip(1 − E_i, 0.1624, 0.30) × 0.50 × 4/8)^(1/4) − 1
```

**Ny (vår tolkning; tredje kvartilen som referens, tvåsidig):**

```
årligt_utfall = (1 + clip((E₇₅ − E_i) × s, −cap, +cap))^(1/p) − 1
```

| Komponent              | Nuvarande                | Ny (tolkning)                          |
|------------------------|--------------------------|----------------------------------------|
| Referenspunkt          | Front, `E = 1`           | Tredje kvartilen, `E₇₅` (rörlig)       |
| Tecken                 | Endast avdrag (`≥ 0`)    | Avdrag **och** tillägg                 |
| Magnitud styrs av      | Kardinalt gap till front | Kardinalt gap till `E₇₅`               |
| Percentilens roll      | Ingen                    | Tröskel + val av referensvärde         |
| Sharing-faktor `s`     | `0.50` (uttryckligt)     | Sannolik men ospecificerad             |
| Realiseringsskalning   | `4/8` (8 år / 4-årsperiod)| Lär finnas kvar (8 år bekräftat)      |
| Kapning `cap`          | `[0.1624, 0.30]`         | **Öppen fråga** (utreds våren 2026)    |
| Generellt krav         | Inget separat            | Inget separat (till skillnad från Ofgem)|

---

*Notera: avsnitt 3–7 blandar Ei:s explicita inriktningar med vår tolkning av den
underliggande mekaniken. Det som är märkt "vår tolkning" är inte fastställt av Ei
och bör behandlas som en arbetshypotes tills modellspecifikationen publiceras.*

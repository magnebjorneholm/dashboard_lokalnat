# Revisionsplan — frontend för ny benchmarking-modell

Levande dokument. Vi bygger upp det successivt, en sak i taget, och implementerar
sedan utifrån det. Utgår från idéerna i [`frontend_idea.md`](frontend_idea.md) och
audit:en i [`docs/new_benchmarking_ui_audit.md`](../docs/new_benchmarking_ui_audit.md).

Status-märkning: **[LÅST]** = beslutat · **[ÖPPET]** = kvar att besluta · **[BACKEND]** = kodändring utanför frontend.

---

## 1. Övergripande struktur (progressiv disclosure)

**[LÅST]** Användaren möts *inte* av konfiguration. Inkommande vy, uppifrån och ned:

1. **Kort, saklig info** om vad nya modellen ändrar mot nuvarande (engelsk, konsult-ton,
   ingen pratig brödtext). Knyt varje ändring till källdokumentet
   (`docs/ei_to_markdown/outputs/ny-modell-benchmarking-elnatsreglering.md`).
2. **Huvudmodellens resultat visas direkt** — ingen "Kör analys"-knapp först.
   Huvudmodellen ("main new benchmarking model") har fasta specs (se §3).
   - Övergripande/utforskande statistik för alla 148 företag (övergripande effekter)
   - Effekter på det enskilda valda företaget
3. **Experimentläge (valfritt, hopfällt)** — endast finjustering av huvudmodellen.
   Triggar omräkning. Endast visualiseringarna från punkt 2 uppdateras.

**[LÅST]** Konsekvens: huvudmodellen ska köra/cache:as direkt vid sidladdning;
omräkning sker bara när användaren ändrar i experimentläget.

---

## 2. Finjusteringsreglage (experimentläge)

**[LÅST]** Endast dessa tre saker ska gå att ändra. Allt annat är fast i huvudmodellen.
"Hellre göra en sak bra än flera dåligt."

### 2.1 Gemensamt pris för nätförlustkostnad
- `k_nf` (kr/MWh). Nätförluster värderas `nf_obs · k_nf · e_in`. Baslinje 753,44.

### 2.2 Metod för förläggningsmiljö (kabel + station)
Ska ha **tydlig förklaring av vad varje metod gör** (idag bara tunn tooltip).
Grundat i justeringsmodulernas config:

- **Kabel** (`environment_capex_adjustment`, jordkabel, cat 3) — premien ligger
  *inbäddad* i per-km-priset (normvärde) per kabeltyp × miljö; referens = landsbygd normal.
  - `per_type` — exakt omprissättning per kabeltyp mot referenspris (mest precist)
  - `sek_per_km` — en additiv SEK/km-premie per miljö (schablon)
  - `percent` — ett procentuellt värdeavdrag per miljö (schablon)
- **Station** (`station_capex_adjustment`, nätstation, cat 13) — premien bokförs som en
  *separat* post "City- och tätortstillägg nätstation" (126 861 SEK/st); referens = utanför tätort.
  - `itemized` — ta bort tätortstilläggsraderna exakt (precist)
  - `percent` — schablonmässig procentuell haircut på hela stationsbasen (Ei-stil)

### 2.3 Ledningstyper i ledningslängd
- Vilka av `cable_length`-typerna som ingår i variabeln ledningslängd:
  jordkabel, luftledning, HSP-hängkabel, sjökabel, optokabel, övriga.
  Default = elektriska (alla utom optokabel).
- **[LÅST]** Ledningslängd är *alltid* med som output (se §3), bara typurvalet justeras.

**[ÖPPET]** `split_by_voltage` (dela ledningslängd per spänningsnivå) — nämns inte som
finjustering. Förslag: låses till `False` i huvudmodellen och tas bort ur UI. Bekräfta.

---

## 3. Huvudmodellens specs ("main new benchmarking model")  [LÅST 2026-06-08]

Kärninsikt efter genomläsning av Ei-dokumentet + de tre modulerna: **config-defaultarna
kodar redan i princip huvudmodellen.** Enda saknade biten var MWhh i outputs (nu tillagt).
Mappat mot Ei:s Figur 2 (modell 2028–2031).

### 3.1 TOTEX — en kostnadsinput  [doc-trogen]
`TOTEX_ny = påverkbara + nätförluster @ gemensamt pris + valda opåverkbara + förläggningsmiljö-justerad kapitalkostnad`
- påverkbara = `controllable_cost_average`
- kapitalkostnad = `capital_cost_2024`, med förläggningsmiljö-`reduction_factor` applicerad på
  jordkabel- resp. nätstationsdelen (integration i `capex_environment.py` / `totex.py`)
- **opåverkbara som ingår:** abonnemang överliggande nät (`grid_subscription`), anslutning
  (`grid_connection`), inmatningsersättning (`feed_in_compensation`), kapacitetsreserv
  (`capacity_reserve`)
- **alltid exkluderat:** myndighetsavgifter (`regulatory_fees`) — per doc; köpta/egna
  nätförluster ersätts av gemensamt-pris-värderingen
- Allt detta är **fast** i huvudmodellen (ej i UI).

### 3.2 Outputs  [LÅST + BACKEND]
CU, MW, NS, MWhl, **MWhh**, + ledningslängd.
- MWhh = vanlig MWhh (gränspunkts*justeringen* är det som är uppskjutet, inte MWhh själv).
- ledningslängd alltid med; default ledningstyper = `ELECTRICAL_TYPES` (alla utom optokabel).
- **[BACKEND]** `NEW_MODEL_BASE_OUTPUTS` i
  [`config.py:44`](../calculations/new_benchmarking/config.py#L44) ska bli
  `("CU", "MW", "NS", "MWhl", "MWhh")` (ledningslängd läggs på via `include_cable_length`).

### 3.3 Elområdeskorrigering
Nätförluster värderas till **gemensamt pris** (`k_nf`, default 753,44 kr/MWh per år):
`nf_obs · k_nf · e_in`.
- **FÖRSLAG:** endast nätförluster common-prisas (ej abonnemang), trots att doc tillåter
  "nätförluster, abonnemang eller båda". Abonnemang ingår i TOTEX till sitt faktiska värde.

### 3.4 Förläggningsmiljökorrigering
Metodnamn (omdöpta 2026-06-08): kabel `exact` / `schablon_per_km` / `schablon_percent`,
station `exact` / `schablon_percent`.
- **Jordkabel:** `exact` (exakt omprissättning mot landsbygd-normal per `techspec × volt`;
  schablon-fallback för ~6–12 % av city/tätort-km utan referenspris). Mest precist, kräver
  inte Ei:s ännu opublicerade schablon-%.
- **Nätstation:** `exact` (ta bort "City- och tätortstillägg nätstation"-raderna exakt,
  126 861 SEK/st). Per företag.
- Båda ger en `reduction_factor` per företag som multiplicerar respektive kapitalkostnadsdel
  i TOTEX (intäktsramen oförändrad).
- Finare metodförklaringar i tooltip/help byggs i frontend-arbetet (§2).

### 3.5 DEA-spec
- **RTS = `crs`** (som nuvarande EIs_DEA). Fast.
- `split_by_voltage = False` → en ledningslängd-output (inte uppdelad per spänningsnivå).
- Outlier/effektiviseringskrav-konvertering = Ei:s `DEFAULT_EFF_REQ_PARAMS`, oförändrat.

### 3.6 Modelltolkning som MÅSTE bekräftas  [VIKTIG]
Ei:s Figur 2 ritar kundtäthet (NS + ledningslängd), elområde och förläggningsmiljö som
"exogena/strukturella faktorer". Implementationen översätter dem så här:

| Figur 2 (exogen faktor) | Implementation |
|---|---|
| Kundtäthet: antal nätstationer | DEA-**output** NS (som nuvarande EIs_DEA) |
| Kundtäthet: ledningslängd | DEA-**output** ledningslängd |
| Elområde | **kostnadskorrigering** (nätförluster @ gemensamt pris) |
| Förläggningsmiljö (jordkabel/station) | **kostnadskorrigering** (capex-haircut) |

Dvs. inget separat exogent DEA-variabelblock — faktorerna blir antingen outputs eller
kostnadssidans korrigeringar. Konsekvent med nuvarande input-orienterade DEA, men det är en
*tolkning* av figuren. **Bekräfta att huvudmodellen ska se ut så.**

---

## 4. Backend-ändringar — KLARA 2026-06-08

- **[KLAR]** MWhh tillagt i `NEW_MODEL_BASE_OUTPUTS`. Outputs körs nu
  `CU, MW, NS, MWhl, MWhh, cable_length_km` (verifierat end-to-end, 148 företag).
- **[KLAR]** Metod-rename: kabel `exact / schablon_per_km / schablon_percent`, station
  `exact / schablon_percent`. Rör de tre `config.py`, `adjustment.py`, `__init__.py`,
  `NewBenchmarkingConfig`, frontend-spec, tester och READMEs. 37 modultester gröna.

---

## 4b. Bekräftat (§3 låst)

1. ✅ Modelltolkningen i §3.6 (NS + ledningslängd = outputs; elområde + förläggningsmiljö = kostnadskorrigeringar).
2. ✅ Elområde: endast nätförluster common-prisas nu (abonnemang senare).
3. ✅ Default-metoder kabel + station = `exact` (omdöpta).
4. ✅ RTS `crs` fast + `split_by_voltage = False` (en ledningslängd-output).
5. ✅ Opåverkbara = de fyra i §3.1 (myndighetsavgifter exkluderas).
6. ✅ Ledningstyper = `ELECTRICAL_TYPES` (alla utom optokabel).

---

## 5. Visualiseringar — övergripande effekter + enskilt företag  [LÅST 2026-06-09]

### 5.1 Jämförelseramverk
Tre artefakter finns, men varje vy är **parvis**:
1. **Nuvarande modell** — Ei:s publicerade DEA (EIs_DEA, 2024–27); `dea_current`. Företagets faktiska nuläge.
2. **Ny modell (main spec)** — förslaget 2028–31; default som användaren ser först.
3. **Finjusterad ny modell** — experimentläget.

**Ankaret är alltid (1) nuvarande modell.** Ny-sidan = (2) main spec som default, (3) finjusterad
i experimentläge. Då ligger (2)-vs-(1) och (3)-vs-(1) på **samma skala** → "Δ effektiviseringskrav"
betyder alltid samma sak.

**Sekundär indikator (experimentläge):** behåll (3)-vs-(1) som headline, men visa en liten diskret
feedback-siffra "din justering ändrade kravet med ±X pp jämfört med main spec" (= (3)-vs-(2)). Fångar
den tredje storheten utan att bryta tvåvägsregeln.

**Headline-princip:** Δ **effektiviseringskrav** (pp) är det jämförbara måttet. Effektivitets*poäng*
lever på respektive modells egen front → cross-modell-jämförelse av poäng är sekundär kontext, aldrig
headline.

### 5.2 Sektor-headline (överst)
- **KPI-rad:** median/medel Δ krav, antal företag med höjt krav, antal med sänkt, antal oförändrade/outliers.
- **Histogram över Δ krav (pp)**, med ditt företags läge utmarkerat (vertikal markör). Färgdelning
  vid 0 — obs delta-konventionen: höjt krav = sämre för företaget, alltså *inte* automatiskt "grönt = positivt".
- **Histogram över effektivitet** (nya modellen) med antal och andel inom respektive trunkeringszon.

### 5.3 Utforskande
- **Scatter:** Δ krav (y) mot en **valbar strukturvariabel** (x): kundtäthet (kunder per km ledning),
  storlek (CU), förläggningsmiljö-exponering (`env_capex` reduction-factor), ledningslängd. Ditt
  företag highlightat. Testar om modellen gör vad Ei avser (gynnar tuff miljö / låg kundtäthet).

### 5.4 Enskilt företag i kontext
Befintlig per-företagsvy (headline-KPI:er, fördelningar) behålls; företaget markeras i sektorvyerna
5.2–5.3 (percentil/markör). **TOTEX build-up är en placeholder i V1** — detaljerna (waterfall,
delposter) tas senare.

### 5.5 Datakällor (allt finns i `NewBenchmarkingResult`)
- `comparison` — `COL_EFF_REQ_DELTA`, `COL_EFF_REQ_NEW/CURRENT`, outlier-flaggor (KPI + histogram Δ krav)
- `dea_new` — effektivitetspoäng + trunkeringszoner (effektivitetshistogram)
- `env_capex` — per-företags `reduction_factor` (strukturvariabel "förläggningsmiljö-exponering")
- `new_model_inputs` — outputs inkl. `cable_length_km` (strukturvariabel "ledningslängd")
- `baseline_df` — CU, NS m.m. för kundtäthet/storlek

### 5.6 Medvetet utelämnat (övervägt, ej med)
Rangordnad vinnare/förlorare-stapel, "största rörelser"-tabell, rank-vs-rank-scatter — kan läggas till
senare men ingår inte i v1.

---

## 6. Layout-skiss (wireframe)  [LÅST 2026-06-09]

Vertikal struktur uppifrån och ned. Wireframe — bestämmer ordning och progressive disclosure,
inte styling (den följer designsystemet vid implementering). Ordning **sektor före företag** (per §5).
Engelska etiketter (UI-språk byts enligt §2).

```
┌──────────────────────────────────────────────────────────────┐
│ Regumetrica                                                    │
│ New benchmarking model                                         │
│ Company: <Name> (REL00XXX)                                     │
├──────────────────────────────────────────────────────────────┤
│ ▸ What this model changes vs. the current one     [expander]   │
│   • Costs → one TOTEX input (all costs excl. authority fees)   │
│   • Losses valued at a common price (price-area correction)    │
│   • Capex levelled for placement environment (cable + station) │
│   • Outputs gain cable length (+ high-voltage delivered energy)│
├──────────────────────────────────────────────────────────────┤
│ SECTOR HEADLINE                          (§5.2)                │
│  [KPI row: median Δ · higher N/148 · lower N/148 · outliers]   │
│  [ Histogram: Δ eff-req (pp) — your firm marked ▲ ]            │
│  [ Histogram: efficiency w/ truncation zones (count & share) ] │
├──────────────────────────────────────────────────────────────┤
│ YOUR COMPANY                             (§5.4)                │
│  current krav  →  new krav     ( Δ +X pp )                     │
│  [ efficiency / potential / rank context ]                    │
│  [ TOTEX build-up — PLACEHOLDER i V1, detaljer tas senare ]    │
├──────────────────────────────────────────────────────────────┤
│ EXPLORE                                  (§5.3)                │
│  x-axis: [ density ▼ ]  (density / size / env-exposure / length)│
│  [ Scatter: Δ eff-req vs <x> — your firm highlighted ]        │
├──────────────────────────────────────────────────────────────┤
│ ▸ Experiment — fine-tune the model       [expander, collapsed] │
│   Common loss price [____]   Cable method [▼]   Station [▼]    │   (§2)
│   Cable types in length [ multiselect ]                       │
│   ⓘ Your tweak changed the requirement by ±X pp vs. main spec  │   (§5.1)
└──────────────────────────────────────────────────────────────┘
```

**Principer:**
- **Ingen "Kör analys"-knapp** — main spec-resultatet renderas direkt; bara experimentläget triggar omräkning.
- Modell-diffen i expander högst upp (kort, saklig — §1.1).
- Experimentläget hopfällt längst ned; sekundär "Δ mot main spec"-indikator visas först när man justerat.
- Sektor → enskilt företag → utforskande → experiment.
- **TOTEX build-up: placeholder i V1.** Visa en enkel platshållare; den slutliga uppbyggnaden
  (waterfall, exakta delposter) designas senare.

---

## 7. Att göra härnäst (kö)

Design klar för hela kedjan (§1–§6). Återstår implementation:

1. ✅ Huvudmodellens exakta spec (§3) — KLAR (inkl. backend).
2. ✅ Innehåll i övergripande effekter (§5) — KLAR (design).
3. ✅ Layout-skiss (§6) — KLAR.
4. Implementation, förslagsvis i ordning:
   a. Config-panel → engelska + tre reglage + Advanced/Experiment-expander (§2)
   b. Page-shell → progressive disclosure, ingen körknapp, modell-diff (§1, §6)
   c. Output → englishifiering + sektorvyer (§5.2–5.3) + sekundär indikator (§5.1)

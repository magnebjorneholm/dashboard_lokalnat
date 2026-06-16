# Explorativ analys: TOTEX/CAPEX-dekomposition vs benchmarkingutfall

> Arbetsdokument / implementationsplan. Analys i `new_benchmarking_model/analysis/`, körd
> offline (inte vid request); CSV-outputen läses av appen via `data/analysis_loader.py`.
> Mål: förstå hur den nya benchmarkingmodellens kostnads-
> komponenter (TOTEX, CAPEX) hänger ihop med utfallet, och om förläggningsmiljö-
> justeringen ger den avsedda effekten. Allt utfall redovisas i **både procent och kronor**.

---

## 0. Designprinciper (gäller alla steg)

- **Två datalager.** *Bundle* = committad förberäkning (`new_benchmarking_model/data/precomputed/`, per bolag,
  instant). *Live* = körs vid behov. Vi delar live i två kostnadsklasser:
  - **Light live:** laddar `capbase_a` / cable-komponenter, klassar miljö/ledningstyp, groupby.
    Ingen DEA, ingen KENT. Sekunder.
  - **Heavy live:** kör om DEA (och i undantagsfall KENT). Se kostnadsinsikten nedan.
- **Kostnadsinsikt som gör dekompositionen billig:** bundlen lagrar redan *både*
  `capital_cost_2024` (ojusterad) och `capital_cost_2024_env_adjusted`, samt `opex_new`
  och varje TOTEX-delpost per bolag. Därför kan **alla TOTEX-varianter byggas med ren
  aritmetik på bundle-kolumner** — bara DEA + kravberäkning behöver köras, aldrig KENT
  (så länge vi håller oss till default kabel/stations-metod). Det gör att även Shapley
  (~24-32 DEA-körningar) är överkomligt och att leave-one-out blir billigt.
- **kr-basen är konstant.** Per Ei appliceras incitamentet på den *okorrigerade* TOTEX-basen
  (`application_base_new`, finns i bundlen). Den ändras inte av benchmarkingvarianterna, så
  kr-utfallet för varje variant = `period_efficiency_amount(variant_%, application_base_new)`.
  Procent och kronor faller alltså ut för varje variant utan extra körning.
- **Teckenkonvention** (företagsperspektiv, återanvänd från `new_benchmarking_model/ui/charts.outcome_kind`):
  `r > 0` avdrag, `r < 0` belöning, `r ≈ 0` full täckning. Färger: avdrag amber, belöning grön.
- **Offline, inte vid request.** Stegen körs offline (tung DEA) och persisterar `.csv`;
  appens chart-grupp läser dessa via `data/analysis_loader.py` och räknar aldrig om vid
  request. Sektoraggregat, identiska för alla användare (bolaget bara highlightas).
- **Ingen visualisering i utvecklingsfasen.** Stegen producerar **endast `.csv`** i
  `new_benchmarking_model/analysis/out/`. Inga figurer byggs, renderas eller sparas i detta skede — utfallet
  läses och utvärderas direkt ur tabellerna. Skälet: visualisering i utvecklingsfasen vore
  dubbelarbete eftersom den ändå skulle byggas om vid graduering till appen. All grafik skjuts
  till implementeringsfasen (efter validering), och byggs då en gång, mot appens designsystem
  (`config/colors`, `format_*`). Skripten skrivs som `# %%`-celler (körbara cell-för-cell i VSCode)
  så mellanresultat kan inspekteras, men outputen som persisteras är tabeller, inte figurer.
- **Identifikation vs deskription.** Urban-index är en *deskriptor*, korrelerad med
  behandlingsdosen by construction. Den rena läsningen av "gynnas urban?" kommer från
  **kanal-isoleringen** (steg 3), inte från regression på urbanitet.

---

## Filstruktur

```
new_benchmarking_model/analysis/
  PLAN.md              # detta dokument
  _helpers.py          # delad: dataladdning, analysram (spine), variant-DEA-runner, urban-proxy, plot-tema
  s1_descriptive.py    # Steg 1 — bundle: deskriptivt, Q1, Q4
  s2_urban.py          # Steg 2 — light live: urban-proxies + valideringstester
  s3_channels.py       # Steg 3 — heavy live: tvåkanals-isolering (capex vs ledningslängd)
  s4_decomposition.py  # Steg 4 — heavy live: leave-one-out + add-one-in
  s5_shapley.py        # Steg 5 — heavy live (valfritt): Shapley-attribution
  out/                 # persisterade tabeller (.csv) — endast tabeller, ingen visualisering i utvecklingsfasen
```

Stegen är **oberoende implementerbara** i ordning. Var och en har en "definition of done".
`_helpers.py` byggs inkrementellt: steg 1 lägger spine + bundle-laddning, steg 2 urban-proxy,
steg 3 variant-runnern, osv.

---

## Den gemensamma analysramen (`analysis_df`, byggs i steg 1)

En rad per `REId`, ryggraden alla steg lutar sig mot. Kolumngrupper:

| Grupp | Kolumner | Källa |
|-------|----------|-------|
| Id | `REId`, `name_short` | bundle + company_names |
| TOTEX-delar | `controllable`, `loss_valued`, `nonctrl_selected`, `capex_unadj` (=`capital_cost_2024`), `capex_adj` (=`..._env_adjusted`), `opex_new`, `totex_new`, `totex_unadj` (=`opex_new+capex_unadj`) | `totex.parquet` |
| Capex-korr | `capex_cut` (=`capex_unadj−capex_adj`), `capex_cut_pct`, `cable_ded`, `cable_eff_pct`, `station_ded`, `station_eff_pct` | `totex` + `env_cable/station_per_company` |
| Utfall ny | `eff_new`, `rank_new`, `req_new_pct`, `kr_new`, `e75`, `gap`(=`e75−eff_new`), `kind` | `dea_new`, `totex` |
| Utfall nuv | `eff_cur`, `rank_cur`, `req_cur_pct`, `kr_cur` | `dea_current`, `totex` |
| Deltan | `d_eff`, `d_rank`, `d_req_pp`, `d_kr` | beräknat |
| Outputs | `CU`, `MW`, `NS`, `MWhl`, `MWhh`, `cable_length_km` | `new_model_inputs` |
| Urban (steg 2) | `density_cu_km`, `jordkabel_share`, `urbanity_index` | light live |

---

## Steg 1 — Deskriptivt (bundle, instant)

**Syfte:** etablera analysramen och svara på de frågor som inte kräver någon körning.

**Innehåll:**
1. Bygg `analysis_df` i `_helpers.load_analysis_df()` (ren bundle-läsning) — ryggraden för steg 2-5.

Inget annat. Q1/Q4-scattrar och övrigt deskriptivt utgår helt.

**Output:** `out/analysis_df.csv`.

**Metodnoter:** `kr_*` är 4-årig periodsumma (tkr); `req_*` är signerade decimaler (×100 för %/år);
`d_req_pp` är i procentenheter. NaN i `cable_*`/`station_*` är meningsfulla (bolag utan kabel/station).

**Definition of done:** `analysis_df` validerad (148 rader, inga oväntade NaN utöver de bolag som
saknar kabel/station).

---

## Steg 2 — Urban-proxies + validering (light live)

**Syfte:** bygg den deskriptiva urban/rural-axeln och validera luftledning=landsbygd-antagandet.

**Beroende:** steg 1 (`analysis_df`).

**Innehåll (light live — capbase/cable-komponenter, ingen DEA/KENT):**
1. **Tre urban-mått** (stege med ökande upplösning *och* ökande närhet till behandlingen):
   - `density_cu_km` = `CU / cable_length_km`. Exogent mot justeringen. Ankare.
   - `jordkabel_share` = jordkabel-km / total elektrisk ledningslängd. Kabelmix (grävt vs luft),
     bara svagt korrelerad med behandlingen — confoundern i renaste form.
   - `urbanity_index` = `(w_city·city_km + w_tätort·tätort_km) / km_total`, landsbygd = 0-nivå.
     `city_km`/`tätort_km` ur jordkabel via `classify_env()`. **Vikterna härleds ur premiestrukturen**
     (jordkabel-kalibreringen, `env_calibration.calibrate().percent`): `w_city = 1`,
     `w_tätort = percent[tätort] / percent[city]` — den relativa kostnadsintensiteten tätort vs city,
     kalibrerad på den faktiskt installerade mixen, inte ett tyckande. **Känslighet:** samma kvot på
     `sek_per_km` i stället för `percent`. Landsbygd-svår ligger kvar på 0 (rural, ej urban); dess
     capex-justering syns i dosen, inte i indexet.
   - `km_total` = elektriska ledningar (exkl. optokabel), konsekvent med cable_length-outputen.
2. **Korrelationsmatris** mellan de tre måtten + `capex_cut_pct`/`effective_pct` (dosen). Visar
   robusthet (om 1/2/3 samstämmiga → urban-etiketten håller) och att index ≈ dos (väntat).
3. **Valideringstest A:** samvarierar luftledningsandel med jordkabel-landsbygd-andel över bolag?
4. **Valideringstest B (oberoende):** har luftledningstunga bolag låg `density_cu_km`?
   Två oberoende tester triangulerar luft=rural.

**Output:** `out/analysis_df.csv` (uppdaterad med urban-kolumner), `out/s2_urban_corr.csv`,
`out/s2_validation.csv`.

**Metodnoter:** premie-härledda vikter ökar kollineariteten mot dosen något, men indexet är
fortfarande **km-viktat** (dosen är värde-viktad) så det förblir en distinkt **deskriptor, inte
identifikation**. Stations-urbanitet (cat 13) fångas inte av km-indexet — notera explicit.
Validering är "konsistent med", inte bevis (luftledning saknar egen miljöetikett).

**Definition of done:** tre urban-mått i `analysis_df`, korrelationsmatris + båda
valideringstesterna producerade, viktkänsligheten dokumenterad.

---

## Steg 3 — Tvåkanals-isolering (heavy live, ~2 DEA-körningar)

**Syfte:** analysens centrum. Isolera de två motverkande kanalerna och projicera dem på
urban-axeln.

**Beroende:** steg 1-2. Kräver `_helpers.run_variant(input_col, output_cols, ...)` — en tunn
wrapper runt `run_dea_analysis` + `calculate_two_sided_requirement` som tar en TOTEX-inputkolumn
och en outputlista, byggd via aritmetik på `analysis_df`/bundle (ingen KENT).

**Innehåll:**
1. **Kanal A — capex-justering (förväntas gynna urban):**
   `env-off`-input = `opex_new + capex_unadj` (ren aritmetik). Kör DEA + krav.
   Utfallsändring (Δ% och Δkr) mot full ny modell, regredierad mot `urbanity_index` (OLS-lutning).
   Förväntan: positiv lutning.
2. **Kanal B — ledningslängd-output (förväntas gynna rural):**
   Kör DEA på `totex_new` men **utan** `cable_length_km` i outputs. Utfallsändring mot full modell,
   regredierad mot urbanitet. Förväntan: negativ lutning.
3. **Netto:** full modells utfall mot urbanitet. **Nyckelhypotes:** kan vara nästan platt trots
   att varje kanal var för sig är stark, om de tar ut varandra längs urban/rural-axeln. Redovisa de
   tre lutningarna (A, B, netto) i samma tabell + enkel OLS-lutning med CI per kanal.

**Output:** `out/s3_channels.csv` (per bolag: Δ% och Δkr för kanal A, kanal B, netto),
`out/s3_slopes.csv`.

**Metodnoter:** Δ för en kanal mäts genom att slå *av* den från fulla modellen (marginal vid
fullt sätt). Eftersom DEA är relativ är detta "hur hela fördelningen rör sig när kanalen tas bort".
kr-utfall via konstant `application_base_new`. OLS-lutningen är deskriptiv (urbanitet endogen),
men kanal-Δ:t i sig är en ren isolering.

> **Statistisk modell (åtgärdad).** Det DEA-inducerade korsberoendet hanteras nu i
> `s3_inference.py`: OLS behålls som punktskattning, men CI:t kommer från DEA-medveten
> subsampling (återskattar front + E75 + alla specar per resample, kopplat). De naiva
> OLS-CI:na var anti-konservativa (~2.5–3× för smala); under de korrekta CI:na är ingen
> kanalgradient skild från noll. Se README "DEA-medveten inferens".

**Definition of done:** tre lutningar kvantifierade + tvåkanals-tabellen (`out/s3_slopes.csv`)
som visar om de neutraliserar varandra.

---

## Steg 4 — Leave-one-out + add-one-in (heavy live, ~5-6 DEA-körningar)

**Syfte:** Q3 — vilken förändring ger störst effekt? De två "ändpunkterna" före Shapley.

**Beroende:** steg 1-3 (variant-runnern).

**Spelare (rena kostnadskomponenter):** losses@gemensamt pris, valda non-controllable,
förläggningsmiljö-capexjustering, ledningslängd-output. (Mekanikbytet tvåsidig vs legacy hålls
utanför här — se öppen fråga.)

**Innehåll:**
1. **Leave-one-out:** för varje spelare, full modell minus den spelaren → Δ% och Δkr per bolag,
   samt sektoraggregat (median |Δ|, andel som byter `kind`). Alla varianter byggs via aritmetik:
   - losses av: `totex_new − loss_valued`
   - nonctrl av: `totex_new − nonctrl_selected`
   - capexjustering av: `opex_new + capex_unadj` (= kanal A från steg 3)
   - ledningslängd av: DEA utan `cable_length_km`-output
2. **Add-one-in:** från en baslinje (alla nya spelare av) läggs en spelare i taget.
3. **Jämförelse LOO vs AOI:** visa att de skiljer sig (interaktioner) → motiverar Shapley.

**Output:** `out/s4_loo.csv`, `out/s4_aoi.csv`, `out/s4_ranking.csv` (spelare rangordnade på effekt).

**Metodnoter:** DEA icke-linjär → LOO och AOI **summerar inte** till totalen; redovisa båda som
intervall/ändpunkter, inte som en additiv uppdelning.

**Definition of done:** spelarna rangordnade på effekt (i % och kr), LOO/AOI-skillnaden synlig.

---

## Steg 5 — Shapley-attribution (heavy live, valfritt, ~24-32 DEA-körningar)

**Syfte:** den vattentäta additiva uppdelningen: `Σ φ_k = Δ` exakt, trots DEA:s icke-linjäritet.

**Beroende:** steg 4 (variant-runnern + spelardefinitionen).

**Innehåll:**
1. **Värdefunktion** `v(S)` = bolagets utfall (% och kr) när bara delmängden `S` av spelarna är på.
   Distinkta DEA-körningar = kombinationer av (losses) × (nonctrl) × (capexnivå: av/ojust/just) ×
   (ledningslängd-output) — alla via aritmetik på bundle, ingen KENT. Cacha per delmängd.
2. **Baslinjedefinition `v(∅)`:** välj så nära nuvarande modell som möjligt; redovisa
   **resttermen** `v(∅) − faktisk nuvarande` separat som "strukturell/övrigt" (input-struktur +
   front-referens skiljer sig och ingår inte i spelarmängden).
3. **Shapley per bolag och spelare** `φ_k` (genomsnittlig marginaleffekt över alla ordningar),
   i både % och kr. Verifiera `Σ φ_k = v(full) − v(∅)`.
4. **Sektor-syntes:** medel-|φ| per spelare, fördelning, vilken spelare som dominerar för vem.

**Output:** `out/s5_shapley_percompany.csv`, `out/s5_shapley_summary.csv`.

**Metodnoter:** välj spelarmängd så att **varje delmängd är beräkningsbar**. Shapley är en
rättvis fördelning given värdefunktionen, inte en kausal policy-kontrafaktisk. Med 4 rena
spelare = 16 delmängder; 5 (om mekaniken inkluderas) = 32.

**Definition of done:** `φ_k` summerar till totalen (verifierat), resttermen redovisad,
sektor-syntesen producerad.

---

## Beslut (bekräftade)

1. **Mekanikbytet (tvåsidig E₇₅ vs legacy front-referens)** hålls **utanför** Shapley-spelarna
   (de rena kostnadskomponenterna) och **redovisas separat** som en egen post.
2. **Urbanitetsvikterna härleds ur premiestrukturen** (jordkabel-kalibreringen):
   `w_city = 1`, `w_tätort = percent[tätort]/percent[city]`. Känslighet på samma kvot via
   `sek_per_km`. Landsbygd (normal + svår) = 0-nivå.
3. **Output: endast `.csv` i utvecklingsfasen.** Inga figurer byggs eller sparas; utfallet läses
   och utvärderas ur tabellerna. All visualisering skjuts till implementeringsfasen (efter
   validering) och byggs då en gång mot appens designsystem.

---

## Stegberoenden (sammanfattning)

```
s1 (bundle) ──► s2 (light live) ──► s3 (heavy live) ──► s4 (heavy live) ──► s5 (heavy live, valfritt)
   │                                    ▲
   └── analysis_df ────────────────────┘  (spine återanvänds av alla)
```

Föreslagen leverans: **steg 1+2 först** (snabbt, ger Q1/Q4 + urban-axeln + validering), därefter
**steg 3** (kanal-isoleringen, analysens centrum), sedan 4 och eventuellt 5.

---

## Implementationsnoter (variabler och baser)

Sex preciseringar avstämda mot koden. De är lätta att tappa bort när stegen kodas, så de
ligger samlade här.

1. **`period_efficiency_amount` tar signerad årsdecimal, inte procent.** Signaturen är
   `period_efficiency_amount(eff_req_pct, annual_base, n_years=4)` och inputen är samma sak som
   `efficiency_requirement_annual` (t.ex. `0.0182`, inte `1.82`). Den appliceras med compound
   över 4 år: `Σ_{t=1..4} Σ_{s=1..t} r·base·(1+r)^(s-1)`. "variant_%" i texten ovan är alltså
   den signerade årsdecimalen ut ur `calculate_two_sided_requirement`, inte en procentsats.
   (`new_benchmarking_model/efficiency/cost_impact.py:46`)

2. **Tre baser får aldrig blandas ihop.** De är distinkta storheter:
   - *DEA-input full modell* = `totex_new` = `opex_new + capital_cost_2024_env_adjusted`
     (gemensamt pris på förluster, env-justerad capex).
   - *DEA-input kanal A (env-off)* = `totex_unadj` = `opex_new + capital_cost_2024`
     (env-ojusterad capex).
   - *kr-applikationsbas* = `application_base_new` (okorrigerad: faktiska förluster + ojusterad
     capex annualiserad + neon).
   kr-basen är **konstant** över alla benchmarkingvarianter; bara DEA-inputen varieras. Använd
   aldrig `totex_unadj`/`totex_new` som kr-bas. (`cost_impact.py:129`, `totex/totex.py:5`)

3. **`opex_new` ≠ opex-delen av `application_base_new`.** `opex_new` (DEA) har förluster till
   *gemensamt pris* (`loss_valued_common_price`); `application_base_new` (kr) har bolagets
   *faktiska* förluster (`loss_actual`) + neon. Principen: benchmarka på korrigerat, applicera
   på okorrigerat.

4. **`name_short` finns inte i bundlen.** Spine-kolumnen kräver en extern company-name-lookup
   (baseline-meta); alla övriga spine-kolumner läses ur bundlen.

5. **`calibrate().percent` är inte förberäknad.** Bundlen lagrar bara per-bolags-`deduction`/
   `effective_pct` (`env_cable_per_company`), inte kalibreringens `percent`/`sek_per_km`-dictar.
   Urbanitetsvikterna i steg 2 kräver därför en live-körning av `calibrate()` (light, cheap),
   inte en ren bundle-läsning. (`environment_capex_adjustment/calibration.py:58`)

6. **Två olika klassificerare med snarlika namn.** Urban-indexets `city_km`/`tätort_km` använder
   env-modulens `classify_env()` (city/tätort/lb, på `cat_encode==3`-jordkabel,
   `environment_capex_adjustment/data.py:31`). Det är *inte* cable_length-paketets
   `classify_ledningstyp()` (jordkabel/luftledning/…). Förväxla dem inte.

# TOTEX/CAPEX-dekomposition vs benchmarkingutfall

Explorativ analys av hur den nya benchmarkingmodellens kostnadskomponenter hänger ihop
med utfallet, och om förläggningsmiljö-justeringen ger den avsedda fördelningseffekten
mellan urbana och rurala bolag. Frikopplad från appen, körbar cell-för-cell, **endast
tabell-output** (`.csv` i [out/](out/)), ingen visualisering i detta skede.

Planen i sin helhet: [PLAN.md](PLAN.md). Implementationsnoterna om variabler och baser
finns där under "Implementationsnoter".

---

## Snabbstart

```bash
.venv/bin/python temp/nb_analysis/s1_descriptive.py   # bundle, instant
.venv/bin/python temp/nb_analysis/s2_urban.py         # light live (capbase + kalibrering)
.venv/bin/python temp/nb_analysis/s3_channels.py      # heavy live, 2 DEA
.venv/bin/python temp/nb_analysis/s4_decomposition.py # heavy live, ~9 DEA
.venv/bin/python temp/nb_analysis/s5_shapley.py       # heavy live, 16 DEA
.venv/bin/python temp/nb_analysis/s3_inference.py     # DEA-aware bootstrap CIs for s3 (~15 min, parallel)
```

All delad logik (spine-laddning, urban-proxies, variant-DEA-runner) ligger i
[_helpers.py](_helpers.py). Stegen läser den committade bundlen
([new_benchmarking_model/data/precomputed/](../../new_benchmarking_model/data/precomputed/))
och importerar produktionsmodulens funktioner — de skriver inget tillbaka in i appen.

---

## Konventioner (läs först)

**Utfallsvariabeln är det signerade årliga effektiviseringskravet `req`** (decimaler, ×100
för pp/år), inte effektivitet och inte kronor. `req` är slutkravet bolaget möter och fångar
*både* bolagets egen effektivitetsändring och referensförskjutningen (E75) — till skillnad
från effektivitet ensam.

| `req` | innebörd | bolaget |
|---|---|---|
| `> 0` | avdrag (deduction) | **missgynnat** |
| `< 0` | belöning (reward) | **gynnat** |
| `≈ 0` | full täckning | neutralt |

Klassificeringen görs av [`outcome_kind`](../../new_benchmarking_model/ui/charts.py).
Drivkraft: `gap = E75 − E_i`, `req` har samma tecken som gap
([efficiency_requirement_two_sided.py](../../new_benchmarking_model/efficiency/efficiency_requirement_two_sided.py)).

**Konvention (a) för komponentbidrag** (steg 3–5): en komponents bidrag är
`φ = req(med komponenten) − req(utan)`. **`φ < 0` = komponenten sänker kravet = gynnar
bolaget.** Detta ger den rena additiva Shapley-identiteten `Σ φ_k = req_full − req_baseline`.

**kr utelämnas ur all regression/rangordning** (skalar med bolagsstorlek →
heteroskedasticitet). Per-bolags-kr finns kvar som rådata i CSV:erna, plus enstaka
deskriptiva summor.

---

## Datagrund

- **Bundle** = committad förberäkning av default-specen, läst per bolag. Snabbt.
- **DEA-exkludering:** tre bolag som Ei bedömer olämpliga för DEA (REL00024 Carlfors Bruk,
  REL00257 Övik Energi, REL00965 Sörbylunds Elnät) tas ur referenssetet och E75 i den nya
  modellen, och lämnas oscorade (`req = NaN`). Se
  [`NewBenchmarkingConfig.exclude_reids`](../../new_benchmarking_model/config.py) och
  [`detect_outliers_iterative(forced_outliers=…)`](../../calculations/frontier/outliers.py).
  **Konsekvens:** alla utfallsmått nedan gäller **145** scorade bolag; de tre faller ur Δ,
  lutningar och φ.

---

## Steg 1 — Deskriptiv spine ([s1_descriptive.py](s1_descriptive.py))

Bygger `analysis_df` (en rad per REId, ren bundle-läsning) i
[`load_analysis_df`](_helpers.py). Output: [out/analysis_df.csv](out/analysis_df.csv).

**Resultat (145 scorade bolag):**

| Storhet | Värde |
|---|---|
| Utfallstyper (ny modell) | 107 avdrag, 37 belöning, 1 full täckning |
| E75 (referens, 75:e percentilen excl. outliers) | 0.931 |
| eff_new (min / median / max) | 0.51 / 0.83 / 1.00 |
| req_new pp/år (min / median / max) | −0.43 / +0.61 / +1.82 |
| Σ kr ny modell (4-årig periodsumma, tkr) | 2 839 762 |
| Σ kr nuvarande modell (tkr) | 1 368 744 |
| Σ Δkr (ny − nuv) | +1 474 257 |
| Förläggningsmiljö-avdrag Σ capex_cut | 4 818 763 tkr/år (20.4 % av ojusterad capex) |

**Tolkning.** Att ~75 % hamnar i avdrag är väntat by construction (E75 = 75:e percentilen).
Att req_cur har golv vid +1.00 %/år speglar Ei:s generella 1%-krav + en individuell del.
Headline: nya modellen ungefär **fördubblar** sektorns samlade krav i kronor.

**Begränsningar.** Fördubblingen är till stor del **mekanisk** — incitamentet appliceras på
hela TOTEX i nya modellen mot bara OPEX i den nuvarande — inte ett nytt empiriskt fynd.
Nuvarande modell är läst rakt ur Ei:s publicerade baseline, inte omräknad, så jämförelsen
blandar mekanikbyte och basbyte (kvantifieras separat i steg 5:s restterm). Två
källanomalier är hanterade och dokumenterade i s1: de tre exkluderade bolagen och REL00024
(`capex_unadj = 0`, ger `capex_cut_pct = NaN` istället för −∞).

---

## Steg 2 — Urban-proxies + validering ([s2_urban.py](s2_urban.py))

Tre urban-mått (light live; capbase-läsning + jordkabel-kalibrering, ingen DEA) byggda i
[`add_urban_proxies`](_helpers.py). Vikterna härleds ur premiestrukturen:
`w_city = 1`, `w_tätort = percent[tätort]/percent[city] = 0.87` (känslighet på `sek_per_km`:
0.61).

**Mått (148 bolag):** density_cu_km [3.3 / 9.9 / 30.4], jordkabel_share [0.23 / 0.94 / 1.00],
urbanity_index [0.00 / 0.39 / 0.83].

**Korrelationer** ([out/s2_urban_corr.csv](out/s2_urban_corr.csv)):

|  | density | jordkabel | urbanity | capex_cut_pct | cable_eff_pct |
|---|---|---|---|---|---|
| density_cu_km | 1.00 | 0.53 | 0.82 | 0.62 | 0.70 |
| jordkabel_share | | 1.00 | 0.60 | 0.52 | 0.44 |
| urbanity_index | | | 1.00 | **0.89** | **0.91** |

**Validering** (luftledning = landsbygd, [out/s2_validation.csv](out/s2_validation.csv)):

| Test | Pearson | Spearman | konsistent |
|---|---|---|---|
| A: luftledning vs jordkabel-landsbygd | +0.44 | +0.66 | ✓ |
| B: luftledning vs kunddensitet | −0.53 | −0.70 | ✓ |

**Tolkning.** De tre måtten samstämmer (urban-etiketten håller), och båda
valideringstesterna pekar åt väntat håll → luftledning ≈ landsbygd är rimligt.

**Begränsningar (viktiga).** `urbanity_index` är **endogent mot behandlingsdosen** (korr
0.89–0.91 mot capex-justeringen) eftersom vikterna kommer ur samma premiestruktur — det är
en **deskriptor, inte identifikation**. `density_cu_km` är det renaste (mest exogena)
ankaret. Valideringen är "konsistent med", inte bevis (luftledning saknar egen
miljöetikett). Spearman > Pearson i båda testerna → monotont men icke-linjärt samband.
Stations-urbanitet fångas inte av det km-viktade indexet.

---

## Steg 3 — Tvåkanals-isolering ([s3_channels.py](s3_channels.py))

Analysens centrum. Isolerar de två motverkande kanalerna via
[`run_variant`](_helpers.py) (full modell läst ur bundlen; 2 DEA-varianter live) och
projicerar dem på urban-axeln. Per bolag: `φ = req(med kanal) − req(utan)`.

**Lutningar mot urbanity_index** ([out/s3_slopes.csv](out/s3_slopes.csv), allt i pp). Punkt =
OLS; två CI:n: naiv OLS-t och DEA-medveten bootstrap (subsampling m=75, se nedan):

| Kanal | lutning | naiv OLS-CI | **DEA-medveten CI** |
|---|---|---|---|
| A: capex-justering | **−0.148** | [−0.242, −0.054] (p=0.002, exkl. 0) | **[−0.274, +0.124] (inkl. 0)** |
| B: ledningslängd | **+0.129** | [−0.004, 0.262] (p=0.058) | **[−0.244, +0.210] (inkl. 0)** |
| Netto: full modell (nivå) | −0.109 | [−0.63, +0.41] | [−0.61, +0.31] (inkl. 0) |

**Tolkning (konservativ).** Punktskattningarna pekar åt mekanismen: kanal A gynnar urbant
(negativ), kanal B gynnar ruralt (positiv), motriktade och nästan lika stora → konsistent
med att kanalerna **neutraliserar varandra** längs urban-axeln (netto platt). **Men under
DEA-medveten inferens är ingen av de tre gradienterna skild från noll.** Vi kan alltså inte
fastställa att kanalerna har nollskilda motverkande gradienter, bara att data är förenligt
med modesta motverkande effekter som tar ut varandra.

**Den naiva OLS:en var anti-konservativ.** De DEA-medvetna standardfelen är ~2.5–3× större;
kanal A:s skenbara signifikans (p=0.002) försvinner när frontier- och E75-beroendet
propageras. Punktestimaten flyttar inte — det är osäkerheten som var underskattad. Tecknet:
r² var redan litet (0.06 / 0.025), så signifikansen vilade på n=145-antagandet om oberoende,
inte på en tät relation; när det effektiva n kollapsar pga beroendet faller signifikansen.

**Begränsningar.** Gradienten är **deskriptiv, inte kausal** (urbanitet endogen, se steg 2);
den rena isoleringen är kanal-Δ:t i sig (regressionsfritt, oförändrat), inte regressionen.
kr-lutningar är medvetet bortvalda.

### DEA-medveten inferens ([s3_inference.py](s3_inference.py))

Det naiva t-intervallet antar oberoende bolag; DEA gör dem beroende (delad front + E75 är en
sampel-percentil). [s3_inference.py](s3_inference.py) räknar om **hela** pipelinen
(full/offA/offB + tvåsidiga kravet + E75) på varje resample, så beroendet propageras in i
CI:t. OLS-lutningen behålls som punktskattning; kopplat by construction (β_A = β_full − β_offA
exakt per replikat). Output: [out/s3_slopes_robustness.csv](out/s3_slopes_robustness.csv).

- **Primärt: subsampling utan återläggning** (m<n), √m-omskalat CI. Undviker dubblett-DMU:er
  (som n-av-n med återläggning skapar och som konstlat lyfter effektivitet). Stabilt mellan
  m=75 och m=110 → takt-/m-valet ändrar inte slutsatsen.
- **n-av-n-kontrast** ger smalare, noll-*exkluderande* CI:n — dubblett-snedvridningen/
  inkonsistensen biter, så den avfärdas (förregistrerat att lita på subsampling).

---

## Steg 4 — Leave-one-out + add-one-in ([s4_decomposition.py](s4_decomposition.py))

Rangordnar de fyra spelarna (förluster, non-controllable, capex-justering, ledningslängd)
på marginaleffekt från båda ändar: LOO = full minus spelaren, AOI = bar baslinje plus
spelaren. Rangordning på `median |Δ pp|`. Output: [out/s4_loo.csv](out/s4_loo.csv),
[out/s4_aoi.csv](out/s4_aoi.csv), [out/s4_ranking.csv](out/s4_ranking.csv).

| Spelare | LOO median \|Δ\| pp | AOI median \|Δ\| pp | gap (interaktion) |
|---|---|---|---|
| **nonctrl** | 0.307 | 0.303 | 0.004 |
| capex_adj | 0.074 | 0.108 | 0.034 |
| losses | 0.043 | 0.066 | 0.023 |
| **cable** | 0.021 | 0.131 | **0.110** |

**Tolkning.** Non-controllable dominerar (~4× näst största), och stabilt (LOO ≈ AOI) → dess
effekt är nästan kontextoberoende. Ledningslängd har den **starkaste interaktionen**: liten
marginaleffekt i full kontext men stor från bar baslinje → dess värde är ordningsberoende.

**Begränsningar.** DEA är icke-linjär → LOO och AOI **summerar inte** till full−baslinje;
de är två ändpunkter som omsluter varje spelares effekt, inte en additiv uppdelning. Det är
just gapet (särskilt cable) som motiverar Shapley. Rangordningen bygger på `|Δ|` (storlek),
inte riktning. kr endast deskriptivt.

---

## Steg 5 — Shapley-attribution ([s5_shapley.py](s5_shapley.py))

Den exakta additiva uppdelningen `Σ φ_k = req_full − req_baseline` över 16 delmängder
(4 spelare). Output: [out/s5_shapley_percompany.csv](out/s5_shapley_percompany.csv),
[out/s5_shapley_summary.csv](out/s5_shapley_summary.csv).

**Exakthet verifierad:** `V(full)` reproducerar bundlens modell exakt (max |Δ| = 0), och
Shapley-identiteten håller till maskinprecision (max residual 4.4e-16).

| Spelare | mean φ pp | mean \|φ\| pp | dominant-andel | gynnade / missgynnade |
|---|---|---|---|---|
| **nonctrl** | −0.014 | **0.381** | **77.9 %** | 78 / 67 |
| capex_adj | +0.039 | 0.110 | 11.7 % | 49 / 96 |
| cable | −0.013 | 0.097 | 6.2 % | 44 / 101 |
| losses | −0.017 | 0.070 | 4.1 % | 75 / 70 |

**Tolkning.** Non-controllable dominerar attributionen (avgörande spelare för 78 % av
bolagen) men `mean φ ≈ 0` med jämn split 78/67 → den **omfördelar** snarare än skiftar alla
åt samma håll. Shapley försonar LOO/AOI för cable (0.097, mellan LOO 0.021 och AOI 0.131).
Tecknen är konsistenta med steg 3: capex_adj missgynnar de flesta men gynnar den urbana
delmängden; cable gynnar de rurala hög-km-bolagen.

**Begränsningar.** **Resttermen `v(∅) − nuvarande = −0.443 pp` (median) är stor** och hålls
medvetet utanför spelarna — den fångar mekanikbytet (tvåsidig E75 vs legacy front-referens)
och strukturella input-skillnader. En stor del av skillnaden mellan ny och nuvarande modell
ligger alltså *utanför* de fyra kostnadskomponenterna. Shapley är en rättvis fördelning
**given** värdefunktionen (spelardefinitioner + baslinjeval) — ett modelleringsval, inte en
kausal policy-kontrafaktisk.

---

## Genomgående begränsningar

- **Relativ DEA:** alla effekter är **fördelningsmässiga**, inte absoluta — att flytta en
  komponent förskjuter fronten/E75 och därmed allas relativa utfall. Aggregat- och
  gradient-utsagor kan peka åt olika håll (t.ex. capex-justeringen höjer aggregatkravet
  något men gynnar urbant i gradienten).
- **Tre exkluderade bolag** lämnas oscorade; av mindre intresse men påverkar E75 och därmed
  andras utfall marginellt.
- **Endogenitet:** urban-axeln är korrelerad med behandlingsdosen by construction → all
  urban-regression är deskriptiv, inte kausal.
- **Inferens (åtgärdad):** naiva OLS-CI:n ignorerar DEA-korsberoende och var anti-konservativa.
  DEA-medveten subsampling (s3_inference.py) ger ~2.5–3× bredare CI:n; under dem är ingen
  kanalgradient skild från noll. Punktskattningarna kvarstår som deskriptiva. Gäller bara
  s3:s gradienter; s4/s5 (regressionsfria) är opåverkade.
- **kr** är medvetet utelämnat ur regression/rangordning (storleksheteroskedasticitet).
- **En spec, en period:** default-konfigurationen; viktkänslighet (premie vs sek_per_km) är
  bara delvis utforskad.

---

## Output-scheman ([out/](out/))

Enheter genomgående: **kostnader = årliga tkr** (utom `kr_*` = 4-årig periodsumma i tkr,
signerad, `<0` = belöning); **`req_*` = signerat årsdecimal** (×100 = pp/år); **`*_pp` /
`d*_pp` / `phi_*` / lutningar = procentenheter (pp)**; **`*_pct` / `*_share` / index /
`eff*` = andel/index 0–1**; **`cable_ded` / `station_ded` = SEK på NUAV-kapitalbasen**
(annan storhet än `capex_cut`, se konventionsavsnittet).

### `analysis_df.csv` — spine, en rad per REId (148)
| Grupp | Kolumner | Enhet |
|---|---|---|
| Id | `REId`, `name_short` | — |
| TOTEX-delar | `controllable`, `loss_valued`, `nonctrl_selected`, `capex_unadj`, `capex_adj`, `opex_new`, `totex_new`, `totex_unadj`, `application_base_new` | årlig tkr |
| Capex-korr | `capex_cut` (tkr), `capex_cut_pct` (andel), `cable_ded`/`station_ded` (SEK), `cable_eff_pct`/`station_eff_pct` (andel) | se ovan |
| Utfall ny | `eff_new` (0–1), `rank_new` (1=bäst), `req_new_pct` (decimal), `kr_new` (tkr, 4 år), `e75` (0–1), `gap`=`e75−eff_new`, `kind` (reward/deduction/coverage) | se ovan |
| Utfall nuv | `eff_cur`, `rank_cur`, `req_cur_pct`, `kr_cur` | se ovan |
| Deltan | `d_eff`, `d_rank`, `d_req_pp` (pp), `d_kr` (tkr) | se ovan |
| DEA-outputs | `CU`, `MW`, `NS`, `MWhl`, `MWhh` (Ei:s outputmått), `cable_length_km` (km) | — |
| Urban (steg 2) | `jordkabel_km`/`luftledning_km`/`city_km`/`tatort_km`/`lb_km` (km), `density_cu_km` (kund/km), `jordkabel_share`/`luftledning_share`/`urbanity_index`/`jordkabel_landsbygd_share` (andel/index) | — |

De tre DEA-exkluderade bolagen har NaN i alla utfallskolumner; `capex_cut_pct` är NaN för
REL00024 (`capex_unadj=0`). Kostnads- och urban-kolumner är ifyllda för alla 148.

### `s2_urban_corr.csv` / `s2_urban_corr_spearman.csv` — korrelationsmatris (5×5)
Pearson resp. Spearman mellan `density_cu_km`, `jordkabel_share`, `urbanity_index`,
`capex_cut_pct`, `cable_eff_pct`. Enhetslöst [−1, 1]. Första kolumnen = radnamn.

### `s2_validation.csv` — valideringstester (2 rader)
`test`, `expect` (positive/negative), `pearson`, `spearman`, `n`, `consistent_with_expectation` (bool).

### `s3_channels.csv` — per REId (145 scorade)
`urbanity_index`; full modell `req_full` (decimal), `kr_full` (tkr); varianter `eff_offA`/`req_offA`/`kr_offA` (kanal A av), `eff_offB`/`req_offB`/`kr_offB` (kanal B av); bidrag **`dA_pp`/`dB_pp` = φ = req(med)−req(utan) i pp** (φ<0 = gynnar); `dA_kr`/`dB_kr` (tkr); `req_full_pp` (pp, för netto-regressionen).

### `s3_slopes.csv` — lutningar (3 rader)
`channel`, `expect`, `slope` (pp per indexenhet), `ci_low`/`ci_high` (naiv OLS-t, pp), `r2`, `p`, `n`, `consistent`; plus `boot_ci_low`/`boot_ci_high` (DEA-medveten subsampling m=75, pp) och `boot_se`. Läs `boot_ci_*`, inte de naiva.

### `s3_slopes_robustness.csv` — alla resampling-scheman (9 rader)
`scheme` (subsample/nofn), `m`, `B`, `slope` (beta_net/beta_A/beta_B), `point` (OLS-punkt), `ci_low`/`ci_high` (pp), `boot_se`. Subsampling m=75 = primär, m=110 = stabilitet, nofn = brasklappad kontrast.

### `s4_loo.csv` / `s4_aoi.csv` — per REId (145)
LOO: `req_full_pp`; AOI: `req_base_pp`. Per spelare (`losses`/`nonctrl`/`capex_adj`/`cable`): `dpp_<spelare>` (pp marginaleffekt), `dkr_<spelare>` (tkr). LOO har även `kind_<spelare>` (variantens utfallstyp, för kind-flip).

### `s4_ranking.csv` — per spelare (4 rader)
`loo_median_abs_pp`, `aoi_median_abs_pp` (pp), `loo_kind_flip_share` (andel), `loo_sum_abs_kr`, `aoi_sum_abs_kr` (tkr, deskriptivt).

### `s5_shapley_percompany.csv` — per REId (145)
`v_empty_pp` (baslinje), `v_full_pp` (full); `phi_<spelare>` (pp Shapley-bidrag, φ<0 = gynnar); `sum_phi` (pp, = `v_full_pp−v_empty_pp`); `residual_vs_current_pp` (pp, mekanik + struktur, utanför spelarna).

### `s5_shapley_summary.csv` — per spelare (4 rader)
`mean_phi_pp`, `mean_abs_phi_pp` (pp), `share_dominant` (andel), `n_favoured(phi<0)`, `n_penalised(phi>0)` (antal bolag).

---

## Filöversikt

| Fil | Steg | Innehåll |
|---|---|---|
| [PLAN.md](PLAN.md) | — | Fullständig plan + implementationsnoter |
| [_helpers.py](_helpers.py) | alla | Spine, urban-proxies, `run_variant` |
| [s1_descriptive.py](s1_descriptive.py) | 1 | Spine + validering |
| [s2_urban.py](s2_urban.py) | 2 | Urban-mått + korrelation + validering |
| [s3_channels.py](s3_channels.py) | 3 | Tvåkanals-isolering |
| [s3_inference.py](s3_inference.py) | 3 | DEA-medveten bootstrap-CI för kanal-lutningarna |
| [s4_decomposition.py](s4_decomposition.py) | 4 | Leave-one-out + add-one-in |
| [s5_shapley.py](s5_shapley.py) | 5 | Shapley-attribution |
| [out/](out/) | — | Persisterade tabeller (`.csv`) |

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

**OLS-lutningar mot urbanity_index** ([out/s3_slopes.csv](out/s3_slopes.csv), allt i pp):

| Kanal | lutning | 95% CI | p | konsistent |
|---|---|---|---|---|
| A: capex-justering | **−0.148** | [−0.242, −0.054] | 0.002 | ✓ gynnar urbant |
| B: ledningslängd | **+0.129** | [−0.004, 0.262] | 0.058 | ✓ gynnar ruralt |
| Netto: full modell (nivå) | −0.109 | [−0.63, +0.41] | 0.68 | ≈ platt |

**Tolkning.** Kanal A (capex-justering) gynnar urbant (φ blir mer negativt med urbanitet,
tydligt: p=0.002). Kanal B (ledningslängd-output) gynnar ruralt (marginellt, p=0.058).
Var för sig är de starka och motriktade (−0.148 vs +0.129); **den fulla modellens
urban-gradient går inte att skilja från noll** (p=0.68). Kanalerna tar i praktiken ut
varandra → modellen är approximativt urban/rural-neutral. Det är planens centrala hypotes.

**Begränsningar.** Netto-punktestimatet (−0.109) är **inte** literalt noll — det är svagt
urbant — men CI:t spänner brett över noll, så vi kan inte hävda en netto-skevhet.
OLS-lutningen är **deskriptiv, inte kausal** (urbanitet endogen, se steg 2); den rena
isoleringen är kanal-Δ:t i sig, inte regressionen. **CI:t är indikativt** — standardfelen
ignorerar DEA-inducerat korsberoende mellan bolag (öppen fråga; robust statistisk modell
tas senare, se PLAN). kr-lutningar är medvetet bortvalda.

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
- **Inferens:** OLS-CI:n ignorerar DEA-korsberoende → läs p-värden indikativt. En robust
  statistisk modell är en öppen fråga (tas senare).
- **kr** är medvetet utelämnat ur regression/rangordning (storleksheteroskedasticitet).
- **En spec, en period:** default-konfigurationen; viktkänslighet (premie vs sek_per_km) är
  bara delvis utforskad.

---

## Filöversikt

| Fil | Steg | Innehåll |
|---|---|---|
| [PLAN.md](PLAN.md) | — | Fullständig plan + implementationsnoter |
| [_helpers.py](_helpers.py) | alla | Spine, urban-proxies, `run_variant` |
| [s1_descriptive.py](s1_descriptive.py) | 1 | Spine + validering |
| [s2_urban.py](s2_urban.py) | 2 | Urban-mått + korrelation + validering |
| [s3_channels.py](s3_channels.py) | 3 | Tvåkanals-isolering |
| [s4_decomposition.py](s4_decomposition.py) | 4 | Leave-one-out + add-one-in |
| [s5_shapley.py](s5_shapley.py) | 5 | Shapley-attribution |
| [out/](out/) | — | Persisterade tabeller (`.csv`) |

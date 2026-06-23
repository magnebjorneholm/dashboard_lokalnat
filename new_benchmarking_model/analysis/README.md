# Dekomposition av benchmarkingutfallet (Shapley)

Offline-analys som delar upp den nya benchmarkingmodellens utfall i dess kostnadskomponenter
med Shapley-värden. Körs cell-för-cell / som skript, skriver **endast tabeller** (`.csv` +
`manifest.json` i [out/](out/)); appens (dolda) chart-grupp läser dem via
[data/analysis_loader.py](../data/analysis_loader.py).

> **För framtida Claude-konversationer:** läs detta avsnitt först. Den här analysen gjordes
> **om från grunden** (2026-06). Det som ändrades mot den gamla `s4`/`s5`-versionen, och
> varför, står under [Vad som ändrades i omgörningen](#vad-som-ändrades-i-omgörningen). Den
> gamla versionen var förankrad i fel kostnadspost och bör inte användas som referens.

---

## Vad som ändrades i omgörningen

Fem saker, alla bekräftade med Erik:

1. **Frontbasen är `opexp_dea`, inte `controllable_cost_average`.** DEA/fronten körs på Ei:s
   råa OPEXp; kravet appliceras separat på SDF-baserade `controllable_cost_average` (kr-sidan,
   orörd här). De två är olika tal och får aldrig blandas. Detta är en ändring i **produktions-
   modellen** ([Steg A](#steg-a--opexp_dea-som-frontbas-produktionsmodellen)), inte bara i
   analysen, och bundlen är omregenererad. Bekräftelse: vår omräknade legacy-DEA på `opexp_dea`
   reproducerar Ei:s **publicerade** krav exakt (median |Δ| = 0.000 pp), mot brus i den gamla
   controllable-versionen.
2. **Två utfall, inte ett.** `req` (signerat tvåsidigt krav, pp) **och** `eff` (cappad
   DEA-effektivitet `min(θ,1)`, 0–1). Skilda mappar `decomp_req/` resp. `decomp_eff/`.
3. **Sju spelare, inte fyra.** Den hopslagna `nonctrl`-spelaren är uppdelad i sina fyra
   kategorier (grid_subscription, grid_connection, feed_in, capacity_reserve). Spelarna går
   4→7, Shapleyn 2⁴=16 → 2⁷=128 DEA-delmängder.
4. **Två outlier-lägen, jämförda.** `dynamic` (iterera outlier-detektionen per delmängd, som
   förr) och `frozen` (frys fulla modellens outlier-set och tvinga det i varje delmängd). Båda
   körs så att robustheten kan jämföras.
5. **Ingen restterm.** Den gamla `residual_vs_current_pp` (en hopbuntad stapel `v(∅) − nuvarande`)
   var en V1-relik och är borttagen. Det nästlade **yttre skiktet** (mekanik + input-aggregering,
   "hur kravet beräknas") finns kvar som en exakt 2-faktors-uppdelning, men utan
   reconciliation/publikationsgap-term (vår legacy = Ei:s publicerade, så det stänger ändå).

Parametriseringen gör de fyra kombinationerna (`req`/`eff` × `dynamic`/`frozen`) till
parameterval i **en** runner, inte kopierad kod. `s4_decomposition.py` och `s5_shapley.py` är
borttagna och ersatta av [run_decomposition.py](run_decomposition.py) + paketet
[decomp/](decomp/).

---

## Steg A — `opexp_dea` som frontbas (produktionsmodellen)

| Fil | Ändring |
|---|---|
| [totex/totex.py](../totex/totex.py) | `opex_new = opexp_dea + loss_valued + nonctrl_selected` (var: `controllable + …`); `totex_new = opex_new + capex_env_adj`. `controllable_cost_average` bärs vidare i framen för kravsidan. |
| [model.py](../model.py) | `opexp_dea` exponeras i `new_model_inputs` (bundlen) så analysen kan läsa frontposten direkt. |
| [data/precompute.py](../data/precompute.py) | Bundlen omregenererad: `totex.parquet` (22 kol, +opexp_dea), `new_model_inputs.parquet` (9 kol, +opexp_dea). |
| [tests/test_new_benchmarking.py](../../tests/test_new_benchmarking.py) | `test_component_toggle_excludes_losses` omförankrad på `opexp_dea`. |

Konsekvens: appens nya-modell-utfall (`req_new`, `eff_new`) skiftar. E75 = 0.9309,
utfallstyper 108 avdrag / 37 belöning (var 107/37/1). Kravbasen/kr (`application_base_new`,
`controllable_cost_average`) är **oförändrad**. Kör om bundlen med
`uv run python new_benchmarking_model/data/precompute.py` om en källa ändras.

---

## Datagrund (spine)

[`load_analysis_df`](_helpers.py) bygger spine (en rad per REId, ren bundle-läsning). Omgörningen
lade till `opexp_dea` och de fyra non-ctrl-kategorierna (`grid_subscription`, `grid_connection`,
`feed_in`, `capacity_reserve`). Invarianter (verifierade): kategorierna summerar till
`nonctrl_selected`; `opexp_dea + loss_valued + nonctrl_selected + capex_adj == totex_new`
(DEA-inputen).

**DEA-exkludering:** tre bolag Ei bedömer olämpliga (REL00024, REL00257, REL00965) tas ur
referenssetet/E75 och lämnas oscorade. Alla utfallsmått gäller därför **145** scorade bolag.

---

## Kvarvarande steg (oförändrade i sak)

| Fil | Steg | Innehåll | Status efter omgörning |
|---|---|---|---|
| [s1_descriptive.py](s1_descriptive.py) | 1 | Spine + validering | Giltig; kör om för uppdaterad `analysis_df.csv` |
| [s2_urban.py](s2_urban.py) | 2 | Urban-mått + korrelation + validering | Giltig; urban-axeln är oberoende av frontbasen |
| [s3_channels.py](s3_channels.py) | 3 | Tvåkanals-isolering (capex vs ledningslängd) | Giltig metod; **kör om** (`run_variant` läser nu opexp-baserad spine) |
| [s3_inference.py](s3_inference.py) | 3 | DEA-medveten bootstrap-CI | Som ovan |

`run_variant` i [_helpers.py](_helpers.py) är oförändrad men matar nu opexp-baserade
input-kolumner (spine bytte bas), så s3 ger nya siffror vid omkörning.

---

## Dekompositionen ([run_decomposition.py](run_decomposition.py) + [decomp/](decomp/))

### Parametrisering

```
outcome      ∈ {"req", "eff"}        # signerat tvåsidigt krav (pp) | cappad effektivitet (0-1)
outlier_mode ∈ {"dynamic", "frozen"} # iterera per delmängd | frys fulla modellens set
```

För varje outlier-läge löses de 128 DEA-delmängderna **en gång** och återanvänds för båda
utfallen (effektivitet och krav delar samma DEA-lösning). Ett fullt svep = 128 × 2 = **256**
DEA-lösningar, inte 512.

### Spelarna (7) och den nästlade strukturen

Följer waterfallen i [ui/charts.py](../ui/charts.py) `render_shapley_waterfall`, bidrag för
bidrag, i två faser:

**Fas 1 — "hur kravet beräknas"** (yttre skikt, baslinjen `v(∅)`). Hörn över v(∅)-
kompositionen `opexp_dea + capex_unadj` (basoutputs, miljöjustering av):
- *input-aggregering*: 2 separata DEA-inputs `[opexp_dea, capex_unadj]` → 1 summerad TOTEX.
- *mekanik* (**endast `req`**): legacy front-referens → tvåsidig E75. `eff` har **inget**
  referensbyte, bara input-aggregeringen.
- `req`: C1=2in/legacy, C2=2in/tvåsidig, C3=1in/legacy, C4=1in/tvåsidig (= `v(∅)_req`).
  `φ_mekanik = ½[(C2−C1)+(C4−C3)]`, `φ_input = ½[(C3−C1)+(C4−C2)]`, summa = C4−C1.
- `eff`: `φ_input = eff(1in) − eff(2in)`. Ingen mekanik.

**Fas 2 — "kostnadskomponenterna"** (de 7 spelarna ovanpå `v(∅)`):

| Spelare | Effekt på DEA-specen |
|---|---|
| `losses` | + `loss_valued` (input) |
| `grid_subscription` | + kategori (input) |
| `grid_connection` | + kategori (input) |
| `feed_in` | + kategori (input) |
| `capacity_reserve` | + kategori (input) |
| `capex_adj` | byter `capex_unadj` → `capex_adj` (förläggningsmiljö-justering) |
| `cable` | + `cable_length_km` (output) |

`v(N)` (alla på) reproducerar bundlens `totex_new`-DEA exakt (verifierat max |Δ| = 0).

### Outlier-lägen

- **dynamic:** varje delmängd kör om den iterativa supereff + IQR-detektionen
  ([outliers.py](../../calculations/frontier/outliers.py), `max_rounds=None`). Outlier-setet, och
  därmed E75, kan skilja mellan delmängder. De 3 Ei-bolagen tvingas ut; dynamiskt funna
  outliers scoras ändå.
- **frozen:** fulla modellens outlier-set (`{REL00024, REL00257, REL00965, REL03016}`) fryses
  och tvingas ut ur referens/E75 i **varje** delmängd, ingen omdetektion. De 3 Ei-bolagen
  lämnas oscorade; övriga frysta (REL03016) scoras mot den fixa referensen, så **samma 145
  bolag** scoras i båda lägena och de är direkt jämförbara.

### Shapley, LOO/AOI

Per bolag och spelare: `φ_k = Σ_S w(|S|)·[v(S∪k) − v(S)]`, `Σ_k φ_k = v(N) − v(∅)` exakt
(identitet verifieras till maskinprecision per körning, se `manifest.json`). LOO (full minus
spelaren) och AOI (baslinje plus spelaren) är ändpunkterna som omsluter varje spelares effekt;
deras gap är interaktionssignalen. **Teckenkonvention:** `req` → `φ < 0` gynnar bolaget (sänker
kravet); `eff` → `φ > 0` gynnar bolaget (höjer effektiviteten).

---

## Köra

```bash
.venv/bin/python new_benchmarking_model/analysis/run_decomposition.py                 # alla 4
.venv/bin/python new_benchmarking_model/analysis/run_decomposition.py --outcomes req  # bara req
.venv/bin/python new_benchmarking_model/analysis/run_decomposition.py --modes frozen  # bara frozen
```

Ett fullt svep tar storleksordningen ~15–25 min (256 DEA, offline). Körningen skriver
cross-check-residualer till stdout och till varje `manifest.json`.

---

## Resultat (körning 2026-06-23, 145 scorade bolag)

Alla cross-checks exakta i alla fyra körningarna: Shapley-identitet ≤ 7e-16 (maskinprecision),
`C4 == v(∅)` och outer-additivitet = 0.0.

**req — spelare efter mean |φ| (pp), dynamic vs frozen:**

| Spelare | dynamic | frozen | dominant-andel |
|---|---|---|---|
| grid_subscription | **0.380** | **0.386** | 71.7 % |
| capex_adj | 0.120 | 0.118 | 11.7 % |
| cable | 0.101 | 0.098 | 5.5 % |
| losses | 0.072 | 0.074 | ~3 % |
| feed_in | 0.069 | 0.080 | 6.9 % |
| grid_connection | 0.030 | 0.026 | 1.4 % |
| capacity_reserve | 0.007 | 0.007 | 0 % |

**Yttre skikt (req, median pp):** `φ_mekanik` −0.342 (dynamic) / −0.320 (frozen) dominerar;
`φ_input` −0.105 / −0.107 litet. `eff` har bara input-aggregering: median −0.004.

**Tre fynd.**
1. **Uppdelningen lokaliserar dominansen.** Den gamla hopslagna `nonctrl`-spelaren splittras,
   och hela dominansen sitter i **grid_subscription** (mean |φ| 0.38 pp, avgörande för 72 % av
   bolagen). De tre andra non-ctrl-kategorierna är små; capacity_reserve är försumbar.
2. **Robust mot outlier-läget.** Magnituderna rör sig knappt mellan dynamic och frozen
   (grid_subscription 0.380 vs 0.386, capex_adj 0.120 vs 0.118). Valet av outlier-strategi
   ändrar inte den kvalitativa bilden. Rangordningen är identisk.
3. **req och eff är ungefär spegelvända**, med `cable` som undantag: cable gynnar nästan alla
   bolag i `eff` (128/145) och de rurala hög-km-bolagen i `req` — den enda output-sidiga
   spelaren beter sig annorlunda än de input-sidiga.

`eff` är genomgående mindre i magnitud (mean |φ| 0.06 för grid_subscription) eftersom den bara
fångar fronteffekten, inte E75-referensförskjutningen som `req` lägger till.

---

## Output ([out/](out/))

```
out/
  analysis_df.csv                       spine (s1/s2)
  s2_*.csv  s3_*.csv                      urban + kanaler (oförändrad metod)
  decomp_<outcome>/<outlier_mode>/        en mapp per (outcome × mode)
    shapley_percompany.csv               per REId: v_empty, v_full, phi_<7 spelare>, sum_phi
    shapley_summary.csv                  per spelare: mean_phi, mean_abs_phi, share_dominant, n_favoured, n_penalised
    loo.csv / aoi.csv                    per REId: d_<spelare> (LOO resp. AOI ändpunkt)
    ranking.csv                          per spelare: loo/aoi/shapley_median_abs, loo_aoi_gap
    value_grid.csv                       FINASTE NIVÅ: varje v(S) per firma (128×145 rader): REId, subset_mask, n_players, players, value, e75
    outer_layer.csv                      fas-1-hörn per REId (req: C1–C4 + phi_mechanic/phi_input; eff: E1/E2 + phi_input)
    manifest.json                        parametrar, frozen_reids, cross-checks, timestamp
```

Enheter: `req`-utfall i **pp/år** (`value`, `phi_*`, `v_*`, `d_*`, `C*`); `eff`-utfall i
**andel 0–1**. `subset_mask` = bitmask över spelarordningen i
[decomp/players.py](decomp/players.py). De tre Ei-exkluderade har NaN i utfallskolumnerna.

---

## Filöversikt

| Fil | Innehåll |
|---|---|
| [_helpers.py](_helpers.py) | Spine-laddning, urban-proxies, `run_variant` |
| [decomp/players.py](decomp/players.py) | De 7 spelarna + `subset_input`/`subset_outputs` (fas-2-komposition) |
| [decomp/engine.py](decomp/engine.py) | Scoring (båda outlier-lägen), value-grid, Shapley, LOO/AOI, fas-1-outer-layer |
| [decomp/io.py](decomp/io.py) | Mappstruktur, writers, manifest |
| [run_decomposition.py](run_decomposition.py) | Drivern (parametriserad, ersätter s4/s5) |
| [s1/s2/s3*.py](.) | Spine, urban, kanaler (oförändrade i sak) |

---

## Kvarvarande (ej i detta steg)

- **UI-graduering:** [ui/charts.py](../ui/charts.py) / [data/analysis_loader.py](../data/analysis_loader.py)
  pekar fortfarande på de gamla `s5_*`-filnamnen och den hopslagna `nonctrl`-spelaren. De
  uppdateras i ett separat implementeringssteg (PLAN-principen: tabeller först, grafik en gång
  efter validering). Chart-gruppen är dold i V1, så appen degraderar tyst tills dess.
- **TOTEX-bryggan** i [ui/company_view.py](../ui/company_view.py) rekonstruerar från
  `controllable_cost_average` och stänger inte längre mot den opexp-baserade `totex_new`; fixas
  i samma UI-steg.
- **s3 omkörning:** kör om s3/s3_inference för uppdaterade kanal-CSV:er på opexp-basen.

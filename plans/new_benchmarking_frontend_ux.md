# Implementationsplan: New benchmarking model, frontend/UX + kr-kvantifiering

> Arbetsplan för UX-omarbetningen av sidan 5 (New benchmarking model) plus
> backend-stödet för att kvantifiera effektiviseringskravet i kronor. Varje
> `#`-sektion nedan är ett självständigt implementationssteg som kan göras och
> testas ett i taget. Block I (steg 1 och 2) är grunden och bör göras först;
> resten är frontend och kan tas i valfri ordning efter det.

## Låsta beslut (referens)

- **Två kostnadsbaser, det är kärnan i reformen:**
  - Nuvarande modell appliceras på **OPEX** (påverkbara kostnader).
  - Nya modellen appliceras på **full faktisk okorrigerad TOTEX** (Ei: incitamentet
    räknas på korrigerad TOTEX i benchmarkingen men *tillämpas* på de faktiska,
    okorrigerade kostnaderna, se `docs/ei_to_markdown/outputs/ny-modell-benchmarking-elnatsreglering.md`
    avsnittet "Korrigering görs för elområde").
- **kr-siffror är årliga** (utfallet är redan ett årligt procenttal).
- **#4** löses med: hero som "från X till Y"-text, nuvarande-markör i den befintliga
  utfallsfördelningen (ingen fristående dumbbell), av-duplicerade KPI:er, kr tillagt.
- **#9** TOTEX-breakdown byggs på nivå 2 utan att röra DEA-kedjan; prototyp först.
- **Precompute utökas** med de nya kr-baserna.
- **Inga em-dashes** i UI-text vi rör.

### kr-formler

```
Nuvarande kr/yr = cur_req_%  ×  OPEX-bas
                  OPEX-bas   = controllable_cost_average            (+ neon/4 om vi vill matcha pipeline exakt)

Nya kr/yr       = nytt_utfall_%  ×  full faktisk okorrigerad TOTEX
                  bas = controllable_cost_average
                      + faktiska nätförluster   (network_loss_purchased + network_loss_own_production)
                      + valda icke-påverkbara   (grid_subscription + grid_connection + feed_in + capacity_reserve)
                      + okorrigerad capex       (capital_cost_2024, ej env-justerad)
```

Faktiska nätförluster och icke-påverkbart tas från `baseline_data.non_controllable_detail`,
snitt över prognosåren 2024-2027, teckenvända till positivt (samma mönster som
`compute_non_controllable_selected` i `opex_components.py`).

---

# 1. Backend: kr-baser i beräkningskedjan

**Mål:** producera de två tillämpnings-baserna per bolag, i *både* live-körning och
precompute (annars faller freshness-testet).

**Filer:**
- `config/column_names.py` — nya konstanter, t.ex. `COL_OPEX_BASE_CURRENT`,
  `COL_APPLICATION_BASE_NEW`, ev. `COL_LOSS_ACTUAL`.
- `calculations/new_benchmarking/opex_components.py` — helper för faktiska nätförluster
  (återanvänd `compute_non_controllable_selected`-mönstret med kategorierna
  `network_loss_purchased`, `network_loss_own_production`).
- `calculations/new_benchmarking/totex.py` — lägg `COL_OPEX_BASE_CURRENT` och
  `COL_APPLICATION_BASE_NEW` som kolumner i totex-framen.
- `calculations/new_benchmarking/model.py` — säkerställ att kolumnerna kommer med i
  `NewBenchmarkingResult.totex` (inget nytt API behövs om de ligger i totex-framen).

**Steg:**
1. Lägg kolumnkonstanterna i `column_names.py`.
2. Helper `compute_loss_actual(detail)` (eller parametrisera befintlig non-ctrl-helper)
   som ger faktiska förluster per REId, årssnitt, positivt tecken.
3. I `build_totex`: beräkna och lägg till de två baskolumnerna. OPEX-basen =
   `controllable_cost_average` (+ neon/4 om vi exponerar neon; annars not:a som
   refinement). Nya basen = summan enligt formeln ovan med okorrigerad `capital_cost_2024`.
4. Bekräfta att baserna *inte* påverkar `totex_new` (DEA-inputen) eller signaturen.

**Klart när:** `run_new_benchmarking()` returnerar en totex-frame med de två nya
kolumnerna; inga befintliga värden ändras.

---

# 2. Precompute + test

**Mål:** den committade bundeln innehåller de nya baskolumnerna och vaktas av testet.

**Filer:**
- `scripts/precompute_new_benchmarking.py`
- `data/new_benchmarking/totex.parquet` (regenereras)
- `tests/test_new_benchmarking_precompute.py`

**Steg:**
1. Kör om `./venv/Scripts/python.exe scripts/precompute_new_benchmarking.py` (eller
   `uv run python scripts/precompute_new_benchmarking.py`) så att `totex.parquet` får
   de nya kolumnerna. Signaturen i `manifest.json` ska vara oförändrad.
2. Verifiera/uppdatera `test_new_benchmarking_precompute.py` så att jämförelsen
   live vs committad bundle täcker de nya kolumnerna.
3. Kör `uv run pytest tests/ -v` och bekräfta grönt.

**Klart när:** testsviten är grön och `data_loaders/new_benchmarking_data.py`
rekonstruerar totex-framen med baserna.

---

# 3. Frontend: flytta experimentpanelen + bolagsrubrik

**Mål:** #1 (resultat före experiment) och #3 (förankra bolaget).

**Filer:** `pages/5_new_benchmarking.py`

**Steg:**
1. Flytta `with st.expander("Experiment: adjust the model", ...)` till *under*
   `render_company_view(...)`. Behåll pending/committed-mönstret och
   `indicator_area` (sekundärindikatorn) inuti expandern.
2. Lägg en bolagsrubrik högst upp via `get_company_display(reid)`
   (`frontend.utils.company_directory`), t.ex. titel + subheader med
   "Kortnamn (REL0XXXX)".

**Klart när:** sidan visar bolag i rubriken och experimentpanelen ligger sist.

---

# 4. Frontend: verdikt-hero + KPI-nivåer + kr

**Mål:** #4. Ta bort dupliceringen hero/Outcome, gör övergången gammalt→nytt till
huvudbudskapet, lägg till kr.

**Filer:** `frontend/results/new_benchmarking_output.py`, `config/formatting.py`
(återanvänd `format_tkr`, `format_percent`, `format_pp`).

**Steg:**
1. Läs OPEX-basen och TOTEX-basen från `result.totex` för bolaget; beräkna
   `cur_kr = cur_req × opex_base` och `new_kr = new_out × application_base`.
2. **Hero** = från/till-statement med både procent och kr, t.ex.
   "Under den nya modellen går ditt effektiviseringskrav från +0.46%/yr (+X tkr/yr
   avdrag) till -0.12%/yr (-Y tkr/yr tillägg)." Färg styrs av riktningen på
   förändringen (bättre för bolaget = grön). Inga em-dashes.
3. **KPI-rad** av-dupliceras till nivåer:
   - Nuvarande krav: `cur_req_%` + `cur_kr` (OPEX-bas)
   - Nytt utfall: `new_out_%` + `new_kr` (TOTEX-bas)
   - Förändring: swing i pp (+ ev. kr-skillnad)
   - Effektivitet / E75-benchmark + rank
4. Var tydlig i caption/tooltip att de två kr-talen ligger på *olika baser*
   (OPEX vs TOTEX), det är en del av poängen.

**Klart när:** ingen post säger samma sak två gånger; kr syns för båda modellerna.

---

# 5. Frontend: nuvarande-markör i utfallsfördelning + positionsdiagram

**Mål:** #4 (visuell kontext för övergången) och #7 (finputs på diagrammen).

**Filer:** `frontend/results/_two_sided_charts.py`

**Steg:**
1. `render_outcome_distribution`: lägg en andra markör för bolagets *nuvarande* krav
   (cur_req) bredvid den nya, på samma %/yr-axel, så övergången syns mot sektorn.
2. Bedöm `render_position_chart`: överväg att förenkla (dubbelaxeln är tung). Behåll
   principen att transferkurvan återanvänder `two_sided_requirement_from_gap` så att
   diagrammet alltid speglar modellen.
3. Inga em-dashes i captions.

**Klart när:** utfallsfördelningen visar bolag-idag vs bolag-nytt; diagrammen är
fortfarande modelltrogna.

---

# 6. Frontend: KPI-förklaringar till tooltips

**Mål:** #5. Mindre visuellt brus.

**Filer:** `frontend/results/new_benchmarking_output.py`

**Steg:**
1. Flytta förklarande undertexter (t.ex. "E75, the reference peer",
   "vs current published requirement") till `st.metric(..., help=...)`.
2. Behåll *data* synligt (t.ex. rank "Rank 12th / 148"), bara förklaringar göms.

**Klart när:** KPI-raden är ren; förklaringar finns på hover.

---

# 7. Frontend: reset-knapp i experimentpanelen

**Mål:** #8. Lätt väg tillbaka till huvudmodellen.

**Filer:** `frontend/modules/addons/new_benchmarking_spec.py`

**Steg:**
1. Lägg en "Reset to main model"-knapp som rensar `nb_committed_cfg` och
   widget-nycklarna (`nb_k_nf`, `nb_cable_method`, `nb_station_method`,
   `nb_cable_types`) och kör `st.rerun()`.
2. (Valfritt) Ta bort dubbletten `BASELINE_K_NF = 753.44` genom att läsa från
   `config.incentive_parameters.K_NF`.

**Klart när:** ett klick återställer panelen till huvudspecet.

---

# 8. Frontend: TOTEX-breakdown nivå 2 (prototyp)

**Mål:** #9. Djupare, korrekt nedbrytning utan att röra DEA-kedjan.

**Filer:** ny helper i `frontend/results/_two_sided_charts.py` eller egen
`frontend/results/_totex_breakdown.py`; anropas från `new_benchmarking_output.py`.

**Data (allt finns i runtime, inget precompute-beroende utöver steg 1-2):**
- Icke-påverkbart i 4 kategorier (`grid_subscription`, `grid_connection`,
  `feed_in_compensation`, `capacity_reserve`) från `non_controllable_detail`.
- Förlust-drivare (nf_obs-andel × pris × e_in), visas som drivare, inte additiv stapel.
- Capex-cut kabel vs station i **nuav-termer** (`env_cable_per_company.deduction`,
  `env_station_per_company.deduction`), tydligt etiketterat som kapitalbas.

**Steg:**
1. Bygg en hierarkisk vy (waterfall eller sunburst/treemap: TOTEX → OPEX/CAPEX →
   delposter).
2. Visa i appen, utvärdera visuellt.
3. Beslut: räcker nivå 2, eller behöver vi utöka precompute för capex-cut i
   kostnadstermer / per tillgångskategori (kräver detaljerad KENT-output i bundeln)?

**Klart när:** en prototyp finns att titta på och vi kan ta beslutet om djupare nivå.

**Undvik:** controllable-nedbrytning per kategori (controllable_cost_average är
indexerat 2018-2021-snitt; `controllable_a.parquet` är nominellt 2024-2027, de
reconcilar inte och skulle vilseleda).

---

# 9. Genomgående: inga em-dashes

**Mål:** #6. Stilpolicy i all UI-text vi rör.

**Steg:**
1. När en sträng på sidan 5 redigeras (hero, KPI-captions, diagram-captions i
   `new_benchmarking_output.py` och `_two_sided_charts.py`): byt em-dash mot komma,
   kolon, parentes eller " - " beroende på mening.
2. Ingen blanket-sweep i oberörd kod/kommentarer.

**Klart när:** alla strängar vi rört saknar "—".

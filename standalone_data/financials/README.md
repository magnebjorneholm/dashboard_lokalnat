# Lokalnät – ekonomisk och finansiell data (Ei R2026:05)

Tidy, analysklar data om svenska **lokalnätsföretag** (eldistribution), härledd
från Energimarknadsinspektionens (Ei) rapportbilagor i serien **R2026:05**.

> **Omfattning:** Endast **lokalnät**. All data om regionnät och
> transmissionsnät har tagits bort (se [Lokalnätsfilter](#lokalnätsfilter)).
> Detta är ett **fristående** datalager – det har inga beroenden till resten av
> repot.

---

## Innehåll i korthet

| Mapp / fil | Beskrivning |
|---|---|
| `raw/` | Originalfilerna från Ei (oförändrade Excel-bilagor 1–8). Källa till allt nedan. |
| `lokalnat/parquet/` | Tidy dataset i **Parquet** (typade, kompakta – primärt format för analys). |
| `lokalnat/csv/` | Identiska dataset i **CSV** (för verktyg utan Parquet-stöd, t.ex. Excel/R). |
| `lokalnat/reference/` | Referenstabeller: metric-ordlista och företagens nätnivåer. |
| `lokalnat/manifest.json` | Maskinläsbar översikt över alla dataset (rader, kolumner, perioder). |
| `build_lokalnat_data.py` | Reproducerbart ETL-skript som bygger hela `lokalnat/` från `raw/`. |

---

## Datakatalog

Varje rad i tabellerna är **en observation** (long/tidy-format). Alla dataset
finns både som `.parquet` och `.csv`.

| Dataset | Period | Granularitet | Mått | Bilaga | Innehåll |
|---|---|---|---|---|---|
| `technical_indicators` | 2012–2024 | enhet + företag | 4 | 3 | Ledningslängd (km), transformatoreffekt (MVA), antal uttagspunkter, antal inmatningspunkter. |
| `investments` | 2011–2027 (perioder) | enhet + företag | – | 2 | Investeringar per fyraårsperiod: utfall & prognos, totalt/re-/nyinvestering. tkr i 2022 års prisnivå. |
| `key_figures` | 2020–2024 | företag | 7 | 4 | Nyckeltal: soliditet, justerad soliditet, rörelseresultat, vinstmarginal, avkastning på eget/totalt kapital, skuldsättningsgrad. |
| `key_figures_underlying` | 2020–2024 | enhet | 16 | 4 | Underliggande balans-/resultatposter (BR/RR-koder) bakom nyckeltalen. |
| `income_statement_items` | 2020–2024 | enhet + företag | 15 | 7 | Poster ur resultaträkningen (RR-/TU-koder): nettoomsättning, rörelseresultat, koncernbidrag, skatt, årets resultat, utdelning m.m. |
| `return_on_capital` | 2020–2024 | enhet + företag | 8 | 8 | Genomsnittligt sysselsatt kapital, EBIT, EBITA, RFP, ROCE, beräknad avkastning för intäktsramar 2020–2023. |
| `capital_employed_components` | 2019–2024 | enhet | 31 | 8 | Alla balansposter (UB/IB-koder) bakom beräkningen av sysselsatt kapital. |
| `group_contributions` | 2020–2024 | enhet + företag | 16 | 6 | Utdelning, koncernbidrag (netto/lämnat/erhållet) och interna lånekostnader – som andel av omsättning och i tkr. |
| `interest_and_loans` | 2020–2024 | företag | 9 | 5 | Interna/externa räntebärande lån och räntekostnader, beräknade räntor, andelar. |
| `accounting_unit_changes` | 2020–2024 | enhet | – | 1 | Spårning av redovisningsenheter (Re-ID) över tid + härledd ändringstyp. |
| `all_yearly_long` | 2012–2024 | enhet + företag | 101 | 3–8 | **Sammanslagning** av samtliga årsbaserade dataset ovan (`dataset`-kolumn skiljer dem åt). |

"Granularitet" avser observationsnivån:

* **`company`** = per elnätsföretag (`org_nr`). Siffrorna avser hela bolaget.
* **`accounting_unit`** = per redovisningsenhet (`re_id`, t.ex. `REL00018`). Detta
  är den nivå där lokalnät kan isoleras rent (se nedan).

---

## Schema

### Årsbaserade dataset (alla utom `investments` och `accounting_unit_changes`)

| Kolumn | Typ | Beskrivning |
|---|---|---|
| `dataset` | str | Datasetets namn (användbart i `all_yearly_long`). |
| `granularity` | str | `company` eller `accounting_unit`. |
| `company` | str | Företagsnamn. |
| `org_nr` | str | Organisationsnummer (`NNNNNN-NNNN`). |
| `re_id` | str | Redovisningsenhetens id (endast `accounting_unit`; alltid `REL…` = lokalnät). |
| `network_level` | str | Nätnivå – alltid `Lokalnät`, eller `None` för bolagsnivå utan uppdelning. |
| `metric_code` | str | Ei:s kontokod (RR/BR/IB/TU) om sådan finns, annars `None`. |
| `metric_name` | str | Måttets namn (svenska, som i källan). |
| `year` | int | Räkenskapsår. |
| `value` | float | Värdet. Tomma celler (`-`) i källan är borttagna (inga NaN-rader). |
| `unit` | str | Bästa gissning: `tkr`, `ratio`, `km`, `MVA`, `MW`, `count`. |
| `source_file` | str | Källfil i `raw/`. |
| `company_has_nonlocal_units` | bool | `True` om bolagsraden (`org_nr`) **även** driver region-/transmissionsnät (se varning nedan). |

### `investments`

Värdena är **periodsummor**, inte årsvärden.

| Kolumn | Beskrivning |
|---|---|
| `basis` | `outcome` (utfall) eller `forecast` (prognos). |
| `period_window` | Mätfönster, t.ex. `2019H2-2023H1`. |
| `period_start` / `period_end` | Start-/slutår för fönstret. |
| `investment_category` | `total`, `reinvestment` eller `new_investment`. |
| `value` | Belopp, **tkr i 2022 års prisnivå** (`unit`-kolumnen anger detta). |

### `accounting_unit_changes`

| Kolumn | Beskrivning |
|---|---|
| `track_id` | Spårnings-id (en logisk enhet följd över åren). |
| `year`, `re_id`, `company` | Re-ID och namn det aktuella året. |
| `change_type` | `no_change`, `name_change`, `reid_change` (ny juridisk person) eller `new_accounting_unit`. Härlett ur länkningen mellan åren. |

---

## Lokalnätsfilter

Region- och transmissionsnät har tagits bort med två regler:

1. **Blad med `Nätnivå`-kolumn** (tekniska indikatorer, investeringar):
   rader filtreras till `Nätnivå == 'Lokalnät'`.
2. **Blad per redovisningsenhet utan `Nätnivå`** (de finansiella bilagorna):
   filtreras på Re-ID-prefix – `REL` = lokalnät, `RER` = regionnät (borttaget),
   `RET` = transmissionsnät (borttaget).

> ⚠️ **Bolagsnivå (`granularity == 'company'`) kan inte delas per nätnivå.**
> Ett bolags resultat-/balansräkning avser hela juridiska personen. För bolag
> som även driver region-/transmissionsnät (t.ex. E.ON, Ellevio, Jämtkraft –
> 30 st totalt) blandar siffrorna alla nätnivåer. Sådana rader är **flaggade**
> med `company_has_nonlocal_units = True`. För rena lokalnätsanalyser:
> använd antingen `accounting_unit`-nivån (alltid `REL…`) eller filtrera bort
> de flaggade bolagen. Referenstabellen
> `reference/company_network_levels.csv` listar varje bolags nätnivåer.

---

## Referenstabeller (`lokalnat/reference/`)

* **`metric_dictionary.csv`** – unika `(dataset, metric_code, metric_name, unit)`
  för alla mått (109 st). Slå upp vad en kod betyder.
* **`company_network_levels.csv`** – per `org_nr`: vilka nätnivåer bolaget driver
  samt flaggorna `has_local`, `has_regional`, `has_transmission`.

---

## Att tänka på

* **`Abonnerad effekt`** (ur bilaga 3) finns **inte** med – den rapporteras
  enbart för regionnät och har därför inga lokalnätsrader.
* **`group_contributions`** beskrivs i källan som 2012–2024 men innehåller
  faktisk data först från **2020**.
* **`capital_employed_components`** innehåller 2019 (ingående balanser, IB) utöver
  2020–2024.
* Tomma värden (`-`/`–`) i källan tolkas som saknade och har tagits bort, så
  varje rad har ett faktiskt `value`.
* Fotnot i bilaga 1: *RER00828 Röbergsfjället Nät AB delades under 2023 upp
  mellan Ellevio AB och Bliekevare Nät AB* (regionnät – ej i lokalnätsdatan,
  noteras för spårbarhet).

---

## Bygg om datan

```bash
# från denna mapp, med projektets uv-miljö
uv run python build_lokalnat_data.py
```

Skriptet läser allt i `raw/`, skriver om hela `lokalnat/` och skriver ut
`manifest.json`. Det är idempotent – kör om det när källfilerna uppdateras.

**Källa:** Energimarknadsinspektionen, rapport **R2026:05**, bilagorna 1–8.

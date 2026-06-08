# New benchmarking add-on — UI/presentation audit

Audit of the *presentation layer* of the new-benchmarking add-on against the rest of
the Regumetrica frontend and the conventions in `CLAUDE.md` / `ARCHITECTURE.md` §17.

**Scope:** presentation only. Backend (`calculations/new_benchmarking/`) and the
decoupled run mechanism are out of scope — they are clean and isolated.

**Files reviewed**
- `frontend/modules/addons/new_benchmarking_spec.py` (config panel)
- `frontend/results/new_benchmarking_output.py` (per-company output)
- `pages/5_new_benchmarking.py` (page shell)

**Reference (the conventions the module should match)**
- `frontend/modules/addons/benchmarking.py`, `frontend/modules/base/m5_efficiency.py`
- `frontend/results/m5_efficiency_output.py`, `frontend/results/m1_asset_base_output.py`
- `frontend/common/parameter_input.py`, `pages/4_revenue_frame.py`

---

## 1. Language & tone

The whole add-on UI is in Swedish; the entire rest of the frontend is in English.
`CLAUDE.md` and `ARCHITECTURE.md` §17 are explicit: **UI text = English**; Swedish is
reserved for domain terms that have no good English equivalent (intäktsram, KENT, NUAV,
påverkbara).

Swedish strings that should be English:

| Location | Current (sv) | Reference convention |
|---|---|---|
| `new_benchmarking_spec.py:37` | `**Konfiguration**` | `m5`: `##### 5.2 Efficiency requirement conversion` |
| `:38-41` | `"Justeringarna nedan påverkar endast den nya modellen…"` | `benchmarking.py:79` `"Configure efficiency analysis model"` |
| `:47` | `**Nätförluster**` | English heading |
| `:49-52` | `"Gemensamt pris (kr/MWh)"`, help text | English label + help |
| `:55` | `"Skalavkastning (RTS)"` | `benchmarking.py:126` `"Returns to scale"` |
| `:65` | `**Förläggningsmiljö (capex)**` | English heading |
| `:66,74` | `"Metod kabel"`, `"Metod station"` | English |
| `:83-98` | `"Outputs"`, `"Inkludera ledningslängd"`, `"Ledningstyper"`, `"Dela per spänningsnivå"` | English |
| `:102-118` | `"TOTEX-komponenter (på/av)"`, `"Påverkbara (controllable)"`, `"Opåverkbara kategorier"` | English |
| `output.py:102-124` | `"Effektiviseringskrav — ny modell vs nuvarande"`, `"Nuvarande (EIs_DEA)"`, `"Nytt krav (ny modell)"`, `"Förändring"`, caption | `m5_output`: `"Cost impact"`, English metrics |
| `output.py:159-171` | waterfall labels `"Påverkbara"`, `"Förluster @ gemensamt pris"`, `"Opåverkbara (valda)"`, `"Kapitalkostnad (justerad)"`, `"Ny TOTEX"` | `m5_output:172-177` `"OPEX before"`, `"Controllable after"` |
| `page 5:67-96` | subheader, caption, warnings, `"Kör analys"`, `"Välj ett företag…"`, `"Företag:"` | `page 4`: `"Results"`, English throughout |
| `_NONCTRL_LABELS:26-31` | `"Abonnemang överliggande nät"`, `"Anslutning"`, … | English category labels |

**Tone.** The Swedish copy is conversational/explanatory ("…allt annat lika?",
"…är därför sekundär kontext — kravförändringen ovan är huvudresultatet"). The house
style is terse professional-consultancy: short captions, no rhetorical questions, no
narration of which result "matters most".

---

## 2. Configuration UI does not use the design system

The rest of the app configures parameters through the shared component
`frontend/common/parameter_input.py`:
`parameter_input()`, `parameter_select()`, `parameter_header()`. These render a
4-column row — **param ID (monospace) · label · input · baseline/Modified badge** —
and return `(value, is_changed)`.

The add-on instead calls **raw `st.number_input` / `st.selectbox` / `st.checkbox` /
`st.multiselect`** with default Streamlit styling, inside a bordered container and an
expander. Consequences:

1. **No "Modified" affordance.** Nothing tells the user which inputs differ from the
   reference reading. This is the single most important pattern in the app
   (`CLAUDE.md` design rules: *"Modified values: amber warning badge"*, *"Case vs
   baseline always shown side by side"*; ARCHITECTURE §17 *None = baseline*). The
   config defaults already reproduce Ei's reference reading (`config.py:49`), so a
   baseline-vs-changed indicator is exactly what's missing.
2. **No parameter IDs / manual references.** Every other module tags inputs with an ID
   (`5.2.1`, `PID_*`). The add-on has none, so it reads as a different product.
3. **No `parameter_header` section dividers.** Headings are ad-hoc `**bold**`
   markdown (`:37,47,65,83`) instead of the bottom-bordered section headers used
   elsewhere.
4. **Generic-Streamlit look.** `CLAUDE.md`: *"If a component looks 'generic
   Streamlit', it's unfinished."* The three-column-+-expander panel is exactly that.

(The decoupled page legitimately does not flow through `ui_config`, so it can't reuse
the `get_config_value` plumbing verbatim — but `parameter_input`/`parameter_select`
take an explicit `baseline=` and work standalone. The visual contract can be matched
without the case system.)

---

## 3. "Too much to change" vs. "what is actually changing"

The panel exposes ~10 controls, several of them deeply technical, while offering almost
no framing of *what the new model is* or *what each knob does to the result*:

- `k_nf` common loss price
- `rts` (CRS/VRS)
- `cable_method` — `per_type` / `sek_per_km` / `percent` (exact re-pricing vs two schablon methods)
- `station_method` — `itemized` / `percent`
- `include_cable_length`, `cable_types` (multiselect), `split_by_voltage`
- TOTEX on/off: `include_controllable`, `include_losses`, `include_capex`
- `non_controllable_categories` (multiselect)

Problems:

1. **Prominence is inverted.** The most esoteric controls — `cable_method` and
   `station_method` (förläggningsmiljö schablon choices) — sit in the **primary**
   columns (`:64-79`), while the conceptually central question *"what enters TOTEX"*
   is hidden in an **expander** (`:102-119`). It should be the reverse: lead with the
   conceptual composition, push schablon/method internals into an "Advanced" section.
2. **Defaults already are the reference reading** (`config.py` docstring). Per the
   "Intentional defaults" principle, the rarely-touched knobs (cable/station method,
   `split_by_voltage`, TOTEX on/off, category multiselect) belong behind a single
   **Advanced** expander, leaving a clean primary surface.
3. **No model diff is surfaced.** The source doc
   (`docs/ei_to_markdown/outputs/ny-modell-benchmarking-elnatsreglering.md`) frames the
   new model as a small set of changes vs. the current one: costs collapsed into a
   single TOTEX input; outputs gain delivered energy at gränspunkt; structural factors
   gain elområde, förläggningsmiljö and ledningslängd. The UI never states this
   "current → new" delta, so the user sees a wall of toggles with no map back to the
   regulatory change they represent. A short "What this model changes vs. the current
   one" framing (and tying each control to one of those changes) would let users
   understand before they touch anything.
4. **Conceptually muddled grouping.** `rts` (a DEA spec choice) is grouped under the
   **Nätförluster** column (`:46-61`), unrelated to network losses.

---

## 4. Smaller inconsistencies

- **Output headline verbosity** (`output.py:102-124`): a `####` heading plus a long
  Swedish caption explaining which number is the "huvudresultat". House style states
  the metric and lets side-by-side case-vs-baseline speak for itself (cf.
  `m5_efficiency_output` / `page 4`).
- **`delta_color="inverse"`** (`output.py:113`) — defensible (a higher efficiency
  requirement is worse for the firm), but it inverts the app-wide convention
  (`CLAUDE.md`: positive = green/up). If kept, it should be a deliberate, labelled
  choice; right now it's silent.
- **Reinvented run/staleness mechanism** (`page 5:82-96`): own `"Kör analys"` button +
  signature + Swedish staleness warning, parallel to the app's central Compute + stale
  indicator. Acceptable for a decoupled page, but the copy is Swedish and ad hoc.
- **Number formatting:** the `k_nf` input shows a bare `753.44` with default Streamlit
  formatting and no baseline reference, vs. the app's space-thousands / `format_*`
  conventions and the Modified badge.

---

## What the module already does right

- Reuses the shared efficiency visuals (`_efficiency_charts.render_efficiency_summary`
  / `render_efficiency_distributions`) — correct mapping new→case, current→baseline.
- TOTEX waterfall uses `get_plotly_template_safe()`, `COLORS`, and `format_number` —
  on-palette and on-grid.
- Page shell matches the `st.title("Regumetrica")` + `st.subheader(...)` pattern.
- Backend is cleanly isolated and config-driven.

---

## Summary

The presentation differs from the rest of the app on three axes, in priority order:

1. **Language** — fully Swedish; must be English (domain terms excepted), professional-
   consultancy tone.
2. **Design system** — bypasses `parameter_input`/`parameter_select`/`parameter_header`,
   so it loses the Modified-vs-baseline badge, parameter IDs, and section styling that
   define the app's look.
3. **Information architecture** — too many co-equal technical knobs, esoteric ones
   given top billing, and no framing of *what the new model changes vs. the current
   one*. Lead with the headline comparison + a short model-diff; demote method/schablon
   internals to an Advanced expander.

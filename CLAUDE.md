# CLAUDE.md

## Project

Regumetrica — regulatory analysis of Swedish electricity distribution companies (revenue cap calculation).
Entrypoint: `streamlit_app.py` (Streamlit, Python 3.11).

## Startup

Read `ARCHITECTURE.md` at the start of every conversation for full project context.

**Do not read `MIGRATION_PRINCIPER.md`** — it is a scratch/working note, not authoritative
project context. Skip it unless the user explicitly asks you to open it. (A `Read` deny rule
in `.claude/settings.json` also blocks the Read tool for this file.)


## Language

- **Conversation:** Swedish
- **Code, identifiers, column names:** English
- **Commit messages:** English, short and concise

## Workflow

- Run tests after changes to `calculations/`, `pipeline/`, or `data_loaders/`:
  ```
  ./venv/Scripts/python.exe -m pytest tests/ -v
  ```
- Skip tests for pure UI/cosmetic changes.
- Stick to what's requested. Don't flag unrelated issues unless asked.

## User manual (LaTeX)

LaTeX source for the user manual PDF lives in `user_manual_latex/`. Toolchain (MiKTeX + `latexmk` + VS Code **LaTeX Workshop**) is wired up via `user_manual_latex/latexmkrc` and the `latex-workshop.*` keys in `.vscode/settings.json`.

- **Build in VS Code:** open `user_manual_latex/Regumetrica user manual.tex`, press **Ctrl+Alt+B**. Preview with **Ctrl+Alt+V**.
- **Build from terminal:** `cd user_manual_latex && latexmk -pdf "Regumetrica user manual.tex"`
- **Output:** `user_manual_latex/build/Regumetrica user manual.pdf` (gitignored).
- See `user_manual_latex/LATEX_VSCODE_SETUP.md` for first-time setup, SyncTeX usage, and troubleshooting.

## Key conventions

- `None` in `ui_config` = "use baseline value". Non-None = user adjustment.
- All DataFrame columns use English `COL_*` constants from `config/column_names.py`.
- Swedish column names only appear in `data_loaders/` (the load boundary).
- `calculations/` is pure logic — no UI or Streamlit imports allowed.
- Dependencies flow strictly downward (see ARCHITECTURE.md layer diagram).

### Design for the target, not the legacy (scoped)

When reworking a feature, prefer the clean design over patching around the old
version's quirks — but scope it to the layer you're changing.

- Reuse stable lower layers (auth, pipeline, state, config) as the sound
  contracts they are, not as "limitations" to discard.
- Heuristic: drop what exists only because of how the code grew; keep what
  exists because it's correct.
- For a non-trivial retire/replace or any cross-layer change, agree the scope
  with the user first. In autonomous runs (no user to ask), take the smallest
  change that works rather than blocking.
- Example: replacing `login.py` with the sign-in dialog warranted a discussion —
  reusing `auth_manager` / `state_manager` did not.

## Visual identity — "Nordic Energy"

Clean Scandinavian finance dashboard. Communicates precision, regulatory authority,
and energy-sector competence. Light backgrounds, cool blue tones, generous whitespace,
tabular numbers.

### Color palette (config/colors.py)

| Token            | Hex       | Usage                                    |
|------------------|-----------|------------------------------------------|
| primary          | #2563EB   | Buttons, links, active states, headers   |
| bg_page          | #F8FAFC   | Page background                          |
| bg_subtle        | #F1F5F9   | Sidebar, secondary panels                |
| bg_muted         | #E2E8F0   | Borders, dividers, disabled states       |
| text_primary     | #0F172A   | Headings, body text                      |
| text_secondary   | #475569   | Labels, captions                         |
| text_muted       | #64748B   | Hints, placeholders                      |
| success          | #059669   | Positive delta, confirmation             |
| warning          | #D97706   | "Modified" badge, stale indicator        |
| error            | #DC2626   | Negative delta, validation errors        |

Chart palette (7 colors, colorblind-safe):
`#2563EB` `#0891B2` `#7C3AED` `#059669` `#EA580C` `#DC2626` `#64748B`

### Typography

- Body: Inter (400/500/600/700)
- Data/code: IBM Plex Mono (400/500)
- Financial data uses tabular figures (`font-feature-settings: 'tnum'`)
- Number format: space as thousands separator, period as decimal
  - `1 234 567 tkr`, `4.53%`, `+1 234 tkr`

### Design rules

- Modified values: amber warning badge — never change the value's own color
- Positive delta: green + arrow up. Negative: red + arrow down. Zero: no arrow
- Case vs baseline always shown side by side
- Charts: plotly_white base, transparent backgrounds, Inter font
- Tables: hide index, stretch width, monospace in grid cells
- Never add custom padding/margin hacks — use framework defaults

### Frontend craft

When building or modifying UI, think before coding:
- **Audience first:** Regulators and energy companies expect precision and predictability.
  Every visual choice should reinforce professional trust — never surprise, never decorate.
- **Intentional defaults:** Don't accept raw Streamlit defaults when the design system has
  an opinion. Apply `COLORS`, `CHART_COLORS`, `get_plotly_template()`, and `format_*`
  helpers consistently. If a component looks "generic Streamlit", it's unfinished.
- **Data is the interface:** Charts and tables are first-class UI. Treat axis labels,
  grid lines, number formatting, and column alignment with the same care as buttons
  and navigation.
- **Subtle polish:** Hover states, focus rings, and smooth transitions (CSS only, ≤200ms)
  convey quality. Never add decorative animations, overlays, or visual effects.

## Update ARCHITECTURE.md

Only update `ARCHITECTURE.md` when changes are confirmed and ready to commit. Commit and ARCHITECTURE.md update go hand in hand.

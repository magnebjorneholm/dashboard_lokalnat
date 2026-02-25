# CLAUDE.md

## Project

Regumetrica — regulatory analysis of Swedish electricity distribution companies (revenue cap calculation).
Entrypoint: `streamlit_app.py` (Streamlit, Python 3.11).

## Startup

Read `ARCHITECTURE.md` at the start of every conversation for full project context.


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

## Key conventions

- `None` in `ui_config` = "use baseline value". Non-None = user adjustment.
- All DataFrame columns use English `COL_*` constants from `config/column_names.py`.
- Swedish column names only appear in `data_loaders/` (the load boundary).
- `calculations/` is pure logic — no UI or Streamlit imports allowed.
- Dependencies flow strictly downward (see ARCHITECTURE.md layer diagram).

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
- Number format: European — space as thousands separator, comma as decimal
  - `1 234 567 tkr`, `4,53%`, `+1 234 tkr`

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
- **Restraint is the aesthetic:** When in doubt, remove rather than add. White space,
  consistent alignment, and typographic hierarchy do the heavy lifting.

## Update ARCHITECTURE.md

Only update `ARCHITECTURE.md` when changes are confirmed and ready to commit. Commit and ARCHITECTURE.md update go hand in hand.

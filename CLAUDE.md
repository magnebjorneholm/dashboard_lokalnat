# CLAUDE.md

## Project

Regumetrica — regulatory analysis of Swedish electricity distribution companies (revenue cap calculation).
Entrypoint: `streamlit_app.py` (Streamlit, Python 3.11).

## Startup

Read `ARCHITECTURE.md` at the start of every conversation for full project context.

## Branches — IMPORTANT

This repo has two active branches. **Always confirm which branch we're on before starting work.**

- **`main`** — Production Streamlit app. Bug fixes, new features, maintenance.
- **`react_migration`** — React (Next.js) + FastAPI migration. See `migration_plan.md` on that branch.

At the start of every session, check the current branch with `git branch --show-current` and
ask the user which branch they want to work on if unclear. Never make changes intended for
one branch on the other.

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

## Update ARCHITECTURE.md

Only update `ARCHITECTURE.md` when changes are confirmed and ready to commit. Commit and ARCHITECTURE.md update go hand in hand.

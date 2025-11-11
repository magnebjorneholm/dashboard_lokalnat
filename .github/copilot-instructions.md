# Copilot / AI helper instructions for this repository

Purpose: give AI coding agents the practical, repo-specific knowledge needed to be productive fast.

1) Big picture
- This is a Streamlit-based analysis dashboard for Swedish local network revenue regulation (IR). The entrypoint is `streamlit_app.py` which handles Firebase auth and navigation to page scripts under `pages/`.
- Major modules:
  - `core/` — shared data loaders and utilities (use these for canonical data access). Example: `core/data_loader_base.py` provides `load_reconciliation()` and other cached loaders.
  - `effektivitet/` — DEA/efficiency analysis and related frontend components (`effektivitet/frontend/components.py`, `effektivitet/backend/dea_model.py`).
  - `intaktsram/` — IR-specific frontends and data (see `intaktsram/frontend/...`).
  - `kapitalkostnad/` — capital cost datasets and exporters used by scenario flows.
  - `auth/` — Firebase auth wrapper used by the Streamlit app (`auth/firebase_auth.py`).

2) Data & IO conventions (important)
- Data files live under module-specific `data/` folders (e.g. `intaktsram/data/`, `effektivitet/data/`, `kapitalkostnad/data/`). Code expects relative paths from repo root.
- `core/data_loader_base.py` tries multiple fallback paths (e.g. `intaktsram/data/new_recon.csv` first, then `effektivitet/data/reconciliation_id_network_firm_dmu.csv`). Follow this pattern when adding loaders.
- Many loaders are cached with Streamlit's `@st.cache_data`. If you change source CSVs, clear Streamlit cache or restart the app to pick up changes.

3) Auth & secrets
- `auth/firebase_auth.py` loads credentials from `st.secrets['firebase']` locally or `/etc/secrets/secrets.toml` in hosted environments. Do NOT hardcode secrets. Unit tests should mock `initialize_firebase_auth()` or `st.secrets`.
- Custom claims set by admin SDK include `dmu`, `reid`, and `role` (common values: `company`, `regulator`). UI logic in `streamlit_app.py` expects these claims.

4) UI / session conventions
- UI code uses Streamlit session state heavily. Core modules prefer explicit parameters (e.g., functions accept `dmu` rather than reading session) — prefer that in refactors and tests.
- Helpers like `core/session_utils.py` provide a contract: UI reads session state, core functions accept explicit args or optional session dicts for testability (see `get_user_org`, `get_user_dmu`).
- Pages are referenced in `streamlit_app.py` (e.g. `pages/foretag/foretag_intaktsram.py`). Follow existing patterns for adding pages (keep UI logic separate from core calculation logic).

5) Typical developer workflows
- Run the app locally:
  - Ensure Python deps from `requirements.txt` are installed (virtualenv/venv recommended).
  - Provide Firebase secrets in `~/.streamlit/secrets.toml` or set `st.secrets` in your environment.
  - Start: `streamlit run streamlit_app.py` (run from repo root)
- Tests: repository includes unit tests (e.g. `test_sfa_backend.py`, `core/test_core_with_real_data.py`). Run via `pytest -q` from repo root.

6) Patterns and gotchas for edits
- Use `core/data_loader_base.py` and `@st.cache_data` for shared data access — don't duplicate reconciliation loading logic.
- Exports and scenario files are stored per-organisation using `core/session_utils.ensure_org_dir()` / `ensure_user_export_dir()`; use these helpers to place output files.
- Frontend components (e.g., `effektivitet/frontend/components.py`) build controls in `st.sidebar` and return parameter dicts — follow that approach for new analysis pages.
- Geographical visualizations rely on reconciliation `REId` matching; failing matches are surfaced in UI diagnostics — when changing shapefile matching, update the diagnostic messages in the same component.

7) Integration points & other references
- DEA logic: `effektivitet/backend/dea_model.py` and `effektivitet/backend/ir_calculations.py` (for applying efficiency to IR exports).
- IR export builder/writer patterns: `core/export_builders.py` and `core/export_writers.py`.
- Runs and outputs: `runs/` contains DEA/IR run directories — useful for examples and regression data.


If anything in this summary looks wrong or you'd like more detail (e.g. full run matrix, CI commands, or where to put new scenario exports), tell me which area and I'll expand the section or merge in any existing guidance you want preserved.

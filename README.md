# Optiverse (PyQt6)

Modern, modular rewrite of the 2D ray‑optics sandbox and component editor.

## Quickstart

- Create venv and install dev deps:
  - `python -m venv .venv && .venv\\Scripts\\activate` (Windows)
  - `pip install -e .[dev]`
- Run tests (first time will be mostly empty):
  - `pytest -q`
- Lint, typecheck:
  - `ruff check .`
  - `mypy src/`
- Launch app (after implementation):
  - `python -m optiverse.app.main`

## Development

- Build UI resources when `.ui` or `.qrc` files are added:
  - `python tools/compile_ui.py`
  - `python tools/compile_rc.py`
- Coverage:
  - `coverage run -m pytest && coverage report`

See `MIGRATION_PLAN.md` for the migration details and acceptance criteria.

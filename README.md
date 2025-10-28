# Optiverse (PyQt6)

Modern, modular rewrite of the 2D ray‑optics sandbox and component editor.

## Quickstart

- Create venv and install dev deps:
  - `python -m venv .venv && .venv\\Scripts\\activate` (Windows)
  - `python -m venv .venv && source .venv/bin/activate` (Mac/Linux)
  - `pip install -e .[dev]`
- Run tests (first time will be mostly empty):
  - `pytest -q`
- Lint, typecheck:
  - `ruff check .`
  - `mypy src/`
- Launch app:
  - `python -m optiverse.app.main` or `optiverse`

## Platform-Specific Features

### macOS Optimizations

Optiverse includes native Mac trackpad gesture support and performance optimizations:

**Trackpad Gestures:**
- 🖱️ **Two-finger scroll** → Pan canvas (like in Safari, Finder)
- 🤏 **Pinch gesture** → Zoom in/out (like in Photos, Preview)
- ⌘ **Cmd + scroll** → Alternative zoom method

**Performance:**
- Optimized rendering for Retina displays (60-80% faster)
- Smart viewport updates reduce lag during pan/zoom
- Background caching for grid rendering

**Test Mac Optimizations:**
```bash
python tools/test_mac_optimizations.py
```

See [docs/MAC_TRACKPAD_OPTIMIZATION.md](docs/MAC_TRACKPAD_OPTIMIZATION.md) for technical details.

## Development

- Build UI resources when `.ui` or `.qrc` files are added:
  - `python tools/compile_ui.py`
  - `python tools/compile_rc.py`
- Coverage:
  - `coverage run -m pytest && coverage report`

See `MIGRATION_PLAN.md` for the migration details and acceptance criteria.

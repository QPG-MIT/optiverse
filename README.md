# Optiverse (PyQt6)

Modern, modular rewrite of the 2D ray‑optics sandbox and component editor.

## Installation

### macOS (Recommended)

```bash
# 1. Clone the repository
git clone https://github.com/QPG-MIT/optiverse.git
cd optiverse

# 2. Create conda environment (recommended for best compatibility)
conda create -n optiverse python=3.11
conda activate optiverse

# 3. Install dependencies
pip install -e .
pip install pyobjc-framework-Cocoa  # For native macOS menu bar integration

# 4. Run the setup script to create the app bundle
python tools/setup_macos_app.py

# 5. Launch Optiverse
open Optiverse.app
```

### Windows/Linux or Python venv

```bash
# 1. Clone the repository
git clone https://github.com/QPG-MIT/optiverse.git
cd optiverse

# 2. Create and activate virtual environment
python -m venv .venv

# Windows:
.venv\Scripts\activate
# Linux:
source .venv/bin/activate

# 3. Install in editable mode with all dependencies
pip install -e .

# 4. Launch Optiverse
python -m optiverse.app.main
# or simply:
optiverse
```

### Development Installation

```bash
# Install with development tools (testing, linting, type checking):
pip install -e .[dev]
```

### ⚠️ Python Version Recommendations

**For maximum raytracing speed (4-8x speedup):**
- ✅ **Python 3.9, 3.10, or 3.11** (Numba fully supported)
- `numba` provides JIT compilation for fast raytracing

**If using Python 3.12+:**
- ⚠️ Everything works, but raytracing is slower (Numba not yet supported)
- Parallel processing is auto-disabled to prevent performance degradation
- Consider Python 3.11 if performance is critical

## Quickstart

### macOS
```bash
# Launch via app bundle (shows as "Optiverse" in menu bar)
open Optiverse.app

# Or use command line
optiverse
```

**First time setup:**
```bash
python tools/setup_macos_app.py  # Creates Optiverse.app (one-time)
```

### Windows / Linux
```bash
# Launch via entry point
optiverse

# Or directly
python -m optiverse.app.main
```

### Development
- Run tests: `pytest -q`
- Lint: `ruff check .`
- Type check: `mypy src/`
- Create icons: `python scripts/create_icon.py` (requires Pillow)

## Performance

### Raytracing Speedup (Numba JIT + Threading)

Optiverse uses a hybrid Numba JIT + Threading approach for fast raytracing:

- **With Numba (Python 3.9-3.11)**: **4-8x speedup** on multi-core CPUs
- **Without Numba (Python 3.12+)**: Normal speed (pure Python)
- Automatically enabled when Numba is available
- Works on all platforms: Windows, Mac, Linux

**To enable speedup:**
```bash
pip install numba  # Requires Python 3.9-3.11
```

See [PARALLEL_RAYTRACING.md](PARALLEL_RAYTRACING.md) for technical details and benchmarks.

## Platform-Specific Features

### macOS Optimizations

Optiverse includes native Mac trackpad gesture support and rendering optimizations:

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

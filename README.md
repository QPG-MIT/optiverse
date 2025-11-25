# Optiverse

**A modern 2D ray-optics simulation and component editor built with PyQt6**

Optiverse is a powerful, interactive tool for designing and simulating optical systems. Create complex setups with mirrors, lenses, beamsplitters, and custom components, then visualize ray propagation in real-time with hardware-accelerated rendering.

## Features

- **Interactive Ray Tracing**: Real-time visualization of light propagation through optical systems
- **Component Editor**: Create custom optical components with multiple interfaces (lenses, mirrors, beamsplitters)
- **Hardware-Accelerated Rendering**: OpenGL-powered ray display (100x+ faster than software rendering)
- **Numba JIT Optimization**: 4-8x raytracing speedup on all Python versions (3.9-3.12+)
- **Collaboration Mode**: Real-time multi-user editing via WebSocket server
- **Zemax Import**: Import optical designs from Zemax (.zmx) files
- **Polarization Support**: Jones vector formalism for polarization-dependent optics
- **Platform-Native UI**: macOS trackpad gestures, native menu bars, dark mode support

## Installation

### Quick Start (All Platforms)

```bash
# Clone the repository
git clone https://github.com/QPG-MIT/optiverse.git
cd optiverse

# Create virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install
pip install -e .

# Run
optiverse
```

### macOS (with App Bundle)

```bash
# 1. Clone and setup
git clone https://github.com/QPG-MIT/optiverse.git
cd optiverse

# 2. Create conda environment
conda create -n optiverse python=3.11
conda activate optiverse

# 3. Install dependencies
pip install -e .

# 4. Create macOS app bundle (optional, for native menu bar)
python tools/setup_macos_app.py

# 5. Launch
open Optiverse.app  # Or: optiverse
```

### Windows/Linux

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

# 3. Install
pip install -e .

# 4. Launch
optiverse
# Or directly:
python -m optiverse.app.main
```

### Development Installation

```bash
# Install with development tools (testing, linting, type checking)
pip install -e .[dev]
```

## Python Version Support

**Optiverse supports Python 3.9 through 3.12+ with full Numba JIT acceleration.**

| Python Version | Numba JIT | Speedup | Status |
|---------------|-----------|---------|--------|
| 3.9           | ✅ Yes    | 4-8x    | ✅ Fully supported |
| 3.10          | ✅ Yes    | 4-8x    | ✅ Fully supported |
| 3.11          | ✅ Yes    | 4-8x    | ✅ Fully supported |
| 3.12+         | ✅ Yes    | 4-8x    | ✅ Fully supported (Numba 0.60+) |

**Note**: Previous versions of this documentation incorrectly stated that Python 3.12+ was not supported by Numba. As of Numba 0.60+, Python 3.12 and newer versions are fully supported with JIT compilation.

## Usage

### macOS
```bash
# Launch via app bundle (shows as "Optiverse" in menu bar)
open Optiverse.app

# Or via command line
optiverse
```

### Windows / Linux
```bash
# Launch via entry point
optiverse

# Or directly
python -m optiverse.app.main
```

### Basic Workflow

1. **Add Components**: Drag optical elements from the library or use the toolbar
2. **Configure Properties**: Double-click elements to adjust parameters
3. **Add Light Sources**: Place sources and configure wavelength, polarization
4. **Trace Rays**: Real-time visualization updates automatically
5. **Save/Load**: Save your optical systems as JSON files

### Keyboard Shortcuts

| Action | Windows/Linux | macOS |
|--------|---------------|-------|
| **File** | | |
| Open Assembly | `Ctrl+O` | `⌘O` |
| Save | `Ctrl+S` | `⌘S` |
| Save As | `Ctrl+Shift+S` | `⌘⇧S` |
| **Edit** | | |
| Undo | `Ctrl+Z` | `⌘Z` |
| Redo | `Ctrl+Y` | `⌘Y` |
| Copy | `Ctrl+C` | `⌘C` |
| Paste | `Ctrl+V` | `⌘V` |
| Delete | `Delete` / `Backspace` | `Delete` / `⌫` |
| Preferences | `Ctrl+,` | `⌘,` |
| **View** | | |
| Zoom In | `Ctrl++` | `⌘+` |
| Zoom Out | `Ctrl+-` | `⌘-` |
| Fit Scene | `Ctrl+0` | `⌘0` |
| Recenter View | `Ctrl+Shift+0` | `⌘⇧0` |
| **Tools** | | |
| Retrace Rays | `Space` | `Space` |
| Component Editor | `Ctrl+E` | `⌘E` |
| Show Log Window | `Ctrl+L` | `⌘L` |
| **Collaboration** | | |
| Connect/Host Session | `Ctrl+Shift+C` | `⌘⇧C` |
| **General** | | |
| Cancel Current Tool | `Esc` | `Esc` |

### Component Editor

Create custom optical components:

1. **File → Component Editor** (or use existing components from library)
2. Load an image (PNG/SVG) or import from Zemax (.zmx)
3. Define optical interfaces (lenses, mirrors, beamsplitters)
4. Set refractive indices and geometric properties
5. Save to library for reuse in main canvas

## Performance

### Hardware-Accelerated Rendering

Optiverse uses OpenGL for ray rendering, providing **100x+ speedup** compared to software rendering:
- 4x MSAA anti-aliasing for smooth visuals
- 60+ FPS even with thousands of rays
- Optimized for Retina/HiDPI displays

### Raytracing Speedup (Numba JIT + Threading)

The raytracing engine uses Numba JIT compilation and multi-threading for **4-8x speedup**:

- **Numba JIT**: Compiles hot paths to native machine code (2-3x faster)
- **Multi-threading**: Distributes rays across CPU cores (2-4x additional speedup)
- **Auto-detection**: Automatically enabled when Numba is available
- **Cross-platform**: Works on Windows, macOS, and Linux

**Performance (typical 4-core CPU, Python 3.9-3.12):**
```
100 rays, 20 elements:  100ms → 20-30ms  (3-5x speedup)
500 rays, 20 elements:  500ms → 100-150ms (3-5x speedup)
```

For technical details, see [docs/PARALLEL_RAYTRACING.md](docs/PARALLEL_RAYTRACING.md).

## Platform-Specific Features

### macOS

**Native Trackpad Gestures:**
- 🖱️ **Two-finger scroll** → Pan canvas
- 🤏 **Pinch gesture** → Zoom in/out
- ⌘ **Cmd + scroll** → Alternative zoom

**App Bundle:**
```bash
# Create native macOS app (optional)
python tools/setup_macos_app.py
open Optiverse.app
```

**Performance Optimizations:**
- Retina display rendering optimizations (60-80% faster)
- Smart viewport caching reduces lag during interactions
- Native menu bar integration via pyobjc

See [docs/MAC_TRACKPAD_OPTIMIZATION.md](docs/MAC_TRACKPAD_OPTIMIZATION.md) for details.

## Collaboration Mode

Real-time multi-user editing via WebSocket:

**Start collaboration server:**
```bash
python tools/collaboration_server.py --host 0.0.0.0 --port 8765
```

**Connect from Optiverse:**
1. **Tools → Collaboration → Connect**
2. Enter server address and session ID
3. Changes sync in real-time across all connected users

See [docs/COLLABORATION.md](docs/COLLABORATION.md) for setup and architecture details.

## Development

### Running Tests
```bash
# All tests
pytest

# Specific module
pytest tests/raytracing/ -v

# With coverage
pytest --cov=src --cov-report=html
```

### Code Quality
```bash
# Lint
ruff check .

# Type checking
mypy src/

# Format (if needed)
black src/ tests/
```

### Building Resources
```bash
# Compile Qt UI files
python tools/compile_ui.py

# Compile Qt resource files  
python tools/compile_rc.py

# Create application icons
python scripts/create_icon.py
```

### Testing Platform Features
```bash
# Test macOS optimizations
python tools/test_mac_optimizations.py

# Test collaboration
python tools/test_collaboration.py

# Manual save/load testing
python tools/test_save_load_manual.py
```

## Project Structure

```
optiverse/
├── src/optiverse/
│   ├── app/           # Application entry point
│   ├── core/          # Physics engine (Snell's law, Fresnel, etc.)
│   ├── raytracing/    # Polymorphic ray tracing engine
│   ├── objects/       # Qt graphics items (mirrors, lenses, sources)
│   ├── ui/            # User interface (main window, dialogs, widgets)
│   ├── services/      # Singletons (storage, settings, collaboration)
│   ├── data/          # Data structures
│   ├── platform/      # OS-specific utilities
│   └── integration/   # Legacy compatibility layer
├── tests/             # Test suite (pytest)
├── docs/              # Documentation
├── tools/             # Utility scripts
├── scripts/           # Build scripts
└── examples/          # Example assemblies and demos
```

## Feature Requests & Bugs

### Known Bugs
- colaborative work is broken
- waveplates do not always rotate the polarization correctly
- QWP seems to adjust polarisation correctly but PBS does not reflect correctly in the pbs + qwp + backreflector mirror config.

### Feature Requests
- zemax black box model
- isolator
- distance measure tool across edges


## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes with tests
4. Run tests and linting (`pytest`, `ruff check .`, `mypy src/`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

### Code Style

- Follow PEP 8 (enforced by Ruff)
- Use type hints (checked by mypy)
- Write docstrings for public APIs
- Add tests for new features

## License

MIT License - see pyproject.toml for details.

## Acknowledgments

- Built with PyQt6 for cross-platform GUI
- Numba for JIT-compiled physics calculations
- OpenGL for hardware-accelerated rendering
- WebSockets for real-time collaboration

## Support

- **Issues**: [GitHub Issues](https://github.com/QPG-MIT/optiverse/issues)
- **Documentation**: See `docs/` folder for detailed guides
- **Examples**: Check `examples/` for demo assemblies
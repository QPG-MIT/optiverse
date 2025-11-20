# Optiverse - AI Agent Guidelines

## Project Overview
Optiverse is a 2D ray-optics simulation and component editor built with PyQt6. Users design optical systems by placing components (lenses, mirrors, beamsplitters) on a canvas and visualize ray propagation in real-time.

## Architecture

### Core Components
- **`src/optiverse/raytracing/`** - Polymorphic raytracing engine with interface-based optical elements
- **`src/optiverse/core/`** - Physics calculations (Snell's law, Fresnel equations, polarization), data models, geometry helpers
- **`src/optiverse/objects/`** - Qt graphics items (sources, mirrors, lenses, etc.) that render on canvas
- **`src/optiverse/ui/views/`** - Main windows (`main_window.py`, `component_editor_dialog.py`)
- **`src/optiverse/services/`** - Singleton services (storage, settings, logging, collaboration)

### Key Data Flow
1. User places/edits components → `objects/*_item.py` (Qt items with `params` dataclass)
2. On retrace: `main_window.py` collects params → `core/use_cases.py:trace_rays()`
3. Physics calculations in `core/geometry.py` (Numba-optimized) compute ray paths
4. Results rendered via `ui/ray_overlay_gl.py` (OpenGL) for performance

### Coordinate Systems
- **Scene coordinates**: Millimeters (mm), origin at center, Y-up convention
- **User angle**: 0° = right, counter-clockwise positive (standard math)
- **Qt angle**: 0° = right, clockwise positive (convert with `user_angle_to_qt()`/`qt_angle_to_user()`)
- **Interface coordinates**: Local to component, first interface defines reference line

## Performance Critical Paths

### Raytracing Speedup (4-8x with Numba)
- **Python 3.9-3.11 recommended** - Numba JIT compilation available
- **Python 3.12+** - Works but slower (Numba not yet supported)
- Key functions in `core/geometry.py` use `@jit(nopython=True, cache=True)`
- Threading enabled when Numba available (`core/use_cases.py:trace_rays()`)
- Check `NUMBA_AVAILABLE` flag before enabling parallel processing

### OpenGL Rendering
- `ui/ray_overlay_gl.py` - Hardware-accelerated ray rendering (100x+ faster than QPainter)
- Configured in `app/main.py` with 4x MSAA, OpenGL 2.1 for macOS compatibility
- Canvas uses `GraphicsView` with optimized viewport updates

## Project-Specific Patterns

### Object Registration System
All graphical items use decorator-based registration:
```python
@register_type("mirror", MirrorParams)
class MirrorItem(BaseObj):
    ...
```
- Registry in `objects/type_registry.py` maps type strings to (ItemClass, ParamsClass)
- Enables generic save/load: `serialize_item(item)` → JSON → `deserialize_item(data)`

### Interface-Based Components
Components (like achromatic doublets) contain multiple optical interfaces:
- Each interface is an `InterfaceDefinition` with type, geometry, and optical properties
- Interfaces stored in `ComponentParams.interfaces: List[InterfaceDefinition]`
- Component editor (`ui/views/component_editor_dialog.py`) provides visual editing
- Coordinates in mm relative to component origin

### Service Singletons
Services use factory pattern (not Qt parent hierarchy):
```python
from optiverse.services.log_service import get_log_service
log = get_log_service()  # Returns shared instance
log.info("Message", "Category")
```
- `log_service` - Application-wide logging with filterable categories
- `settings_service` - Persistent settings (QSettings wrapper) with GUI preferences dialog
- `storage_service` - Component library I/O with import/export, supports multiple library paths
- `collaboration_manager` - WebSocket-based real-time collaboration

**Settings System:**
- User preferences accessible via **Edit → Preferences...**
- Library paths stored in settings, enables portable assemblies
- Components serialize with library-relative paths (`@library/{library_name}/...`)
- Automatic resolution across all configured libraries

### Polarization System
Jones vector formalism throughout:
- `Polarization` dataclass wraps complex numpy array `[Ex, Ey]`
- Transformations in `core/geometry.py`: `transform_polarization_mirror()`, `transform_polarization_waveplate()`, etc.
- Each ray carries polarization state, updated at each interaction

## Development Workflows

### Running the App
```bash
python -m optiverse.app.main  # or just `optiverse` if installed
```

### Testing
```bash
pytest -q                      # Quick test run
pytest tests/raytracing/ -v    # Specific module
pytest --cov=src --cov-report=html  # Coverage report
```
- Fixtures in `tests/conftest.py`: `qtbot`, `qapp` for PyQt testing
- Use `qtbot.addWidget()` for widgets, `qtbot.waitUntil()` for async operations

### Type Checking & Linting
```bash
mypy src/                      # Type checking (config in mypy.ini)
ruff check .                   # Fast linting (config in pyproject.toml)
```

### Compiling UI Resources
When adding `.ui` or `.qrc` files:
```bash
python tools/compile_ui.py     # Convert Qt Designer files
python tools/compile_rc.py     # Compile resource files
```

### Collaboration Server
Start standalone WebSocket server for multi-user editing:
```bash
python tools/collaboration_server.py --host 0.0.0.0 --port 8765
```
- Protocol: JSON over WebSocket at `/ws/{session_id}/{user_id}`
- First user becomes host, subsequent users receive full state sync
- Messages: `sync:full_state`, `item:added`, `item:moved`, etc.

## Testing Conventions

### Fixture Usage
```python
def test_example(qtbot, main_window):
    # qtbot: pytest-qt helper for Qt testing
    # main_window: From tests/ui/test_*.py fixtures
    window = MainWindow()
    qtbot.addWidget(window)
    qtbot.waitExposed(window)
```

### Raytracing Tests
- `tests/raytracing/` - Tests for polymorphic engine
- `tests/integration/test_backward_compatibility.py` - Ensures new engine matches legacy behavior
- Compare results with `np.allclose(legacy_path.points, poly_path.points, atol=1e-6)`

## Common Pitfalls

1. **Angle conversion**: Always use `user_angle_to_qt()` when setting Qt rotations, `qt_angle_to_user()` when reading
2. **Numba compatibility**: Don't use Python lists/dicts in `@jit` functions - use NumPy arrays and primitives
3. **Collaboration broadcast loops**: Use `_suppress_broadcast` flag when applying remote changes
4. **Path handling**: 
   - Use `platform/paths.py` helpers for cross-platform compatibility
   - Component images use library-relative format (`@library/{library_name}/...`) for portability
   - Pass `settings_service` to `serialize_component()` and `deserialize_component()` for proper path resolution
5. **Qt cleanup**: Set `WA_DeleteOnClose` attribute for dialogs to prevent memory leaks
6. **Library paths**: Always initialize `StorageService` with `settings_service` parameter

## External Dependencies

### Critical Libraries
- **PyQt6** - GUI framework (requires PyQt6-WebEngine for collaboration)
- **NumPy** - Array operations and linear algebra
- **Numba** - JIT compilation for raytracing (optional but highly recommended)
- **PyOpenGL** - Hardware-accelerated rendering
- **websockets** - Collaboration server (server-side only)

### Platform-Specific
- **macOS**: `pyobjc-framework-Cocoa` for menu bar app naming and trackpad gestures
- Trackpad gestures in `ui/views/graphics_view.py`: two-finger scroll (pan), pinch (zoom)

## Component Editor Workflow

1. **File → Component Editor** opens `ComponentEditorDialog`
2. Load image (PNG/SVG) or import Zemax file (`.zmx`)
3. Set **Object Height** (physical size in mm) for calibration
4. Add interfaces via **Interface Tree Panel** or drag on canvas
5. Each interface has type dropdown (lens, mirror, beamsplitter, etc.) and properties
6. **Save** adds to user library (`~/.optiverse_library/`)
7. Components draggable from library tree in main window

### Zemax Import
- Parser: `services/zemax_parser.py` reads `.zmx` text format
- Converter: `services/zemax_converter.py` → `ComponentRecord` with interfaces
- Glass catalog: `services/glass_catalog.py` (Schott, Ohara) provides refractive indices
- Creates curved interfaces with proper curvature radius and aperture

## File Organization

```
src/optiverse/
  app/           - Entry point (main.py)
  core/          - Physics, models, pure Python logic
  raytracing/    - Polymorphic ray engine (no Qt deps)
  objects/       - Qt items (sources, mirrors, lenses, components)
  ui/            - Windows, dialogs, widgets
  services/      - Singletons (storage, settings, logging, collaboration)
  platform/      - OS-specific utilities (paths, gestures)
  integration/   - Legacy/new engine adapter
  data/          - Data structures (interfaces, geometry)
tests/           - pytest suite mirroring src/ structure
tools/           - Standalone utilities (collaboration server, benchmarks)
docs/            - Markdown documentation of features/fixes
```

## Key Files to Reference

- **Raytracing entry**: `core/use_cases.py:trace_rays()` or `raytracing/engine.py:trace_rays_polymorphic()`
- **Physics**: `core/geometry.py` (Snell, Fresnel, polarization transforms)
- **Main UI**: `ui/views/main_window.py` (2000+ lines, central orchestrator)
- **Component editor**: `ui/views/component_editor_dialog.py`
- **Object base class**: `objects/base_object.py:BaseObj`
- **Type registry**: `objects/type_registry.py` (maps type strings to classes)

---

When adding features, maintain the separation between Qt UI (`objects/`, `ui/`) and pure Python physics (`core/`, `raytracing/`). This allows raytracing to run in background threads and simplifies testing.

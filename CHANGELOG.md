# Changelog

All notable changes to Optiverse will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Live cursor coordinates** (#78): Status bar displays real-time X/Y scene coordinates as the cursor moves over the canvas, with units (mm, µm, nm) adapting automatically to the current zoom level
- **Dynamic scale bar units** (#79): Scale bar automatically switches between mm, µm, and nm at high zoom levels, with a dynamically sized bar representing a clean round number
- **Arrow key nudging** (#89): Move selected items with arrow keys (0.1 mm step) or Shift+Arrow (1.0 mm step); both step sizes are configurable in Preferences → Canvas & Editing
- **Configurable ruler label positioning** (#90): Ruler labels can be placed Above, Below, Left, or Right relative to the segment via the Edit dialog; setting is serialized and fully undoable
- **Cross-instance copy/paste** (#34): Items copied in one Optiverse window can be pasted into another via the system clipboard (uses custom MIME type for serialization)
- **PyOpticL export**: New File menu entry **Export PyOpticL Layout…** produces a self-contained folder (`<name>.py` plus `models/<stem>/<stem>.step` and `<stem>.json` per component) shaped exactly the way `PyOpticL.utils.import_model` expects, ready to run in FreeCAD with the PyOpticL workbench. Components must have an attached STEP file (set when importing a STEP into a component); a warning dialog lists any without one before export

### Changed

- **Zoom-invariant ruler rendering** (#80): Ruler endpoint bars, labels, selection bounds, and hit-test areas now maintain constant screen size regardless of zoom level, matching the existing cosmetic-pen line behavior

## [0.3.4] - 2026-04-30

### Added

- **Group relative locking**: Locked items inside an unlocked group now move together as a unit when any locked member is dragged, preserving relative positions. Locking an individual element means "only movable as part of the group, not independently." A locked group still blocks all movement
- **Rectangle & Text Note locking**: `RectangleItem` and `TextNoteItem` now support the full lock workflow — context-menu toggle, blocked movement/rotation/deletion, forbidden cursor, and lock state persisted in save files
- **Linked Assemblies**: Reference external assembly files instead of copying their content (File > 🔗 Link Assembly… or Ctrl+Shift+L). Linked sub-assemblies appear as locked groups marked with 🔗 in the layer panel, with the following capabilities:
  - **File watching with user-confirmed updates**: When a linked source file changes on disk, you are notified and can choose to update
  - **Multiple instances**: The same source file can be linked multiple times with independent position/rotation
  - **Edit in Context** (SolidWorks-style): Right-click a linked group > "Edit in Context" to unlock items for editing; changes write back to the source file on "Finish Editing"
  - **Unlink (Embed)**: Convert a linked group to a regular group, breaking the external reference
  - **Refresh from Source**: Manually reload linked content from the source file
  - **Offline resilience**: Cached snapshots allow assemblies to open even if source files are temporarily unavailable
  - **Deterministic UUIDs**: Linked item UUIDs are stable across reloads, preserving undo history and references
  - **Circular link detection**: Prevents A→B→C→A reference cycles (up to depth 5)
  - **Portable paths**: Uses `@assembly/` relative paths so linked assemblies work when project directories are moved
- **Export Selected as Assembly**: Right-click selected items in the layer panel or on the canvas and choose "Export Selected as Assembly…" to save them as a new `.json` assembly file, preserving group hierarchy
- **Ruler Edit dialog**: Right-click or layer-panel "Edit..." opens a dialog with display name and per-segment length/angle controls
- **Angle Measure Edit dialog**: Right-click or layer-panel "Edit..." opens a dialog with display name, inner angle, and arm length controls
- **Ruler / Angle Measure locking**: Lock toggle in context menu and layer panel; blocks movement, point dragging, editing, and deletion; persisted in save files
- **Multi-element lock**: Locking an item via context menu now applies to the entire selection
- **Marimo demo**: Interactive ray-tracing demo notebook under `examples/`
- **Autolabel**: Right-click a component and toggle "Autolabel" to display its key optical property (e.g. "f = 100 mm" for a lens, "QWP @ 45°" for a waveplate) as a text label. Labels follow their owner when moved, are cascade-deleted when the owner is removed, and are fully undoable. Repositioning a label manually is preserved across subsequent owner moves
- **Layer panel nesting for autolabels**: Autolabel items appear as collapsible children of their owner component in the layer panel, with dimmed italic styling. They cannot be independently dragged or deleted from the panel

### Removed

- **Dead code cleanup**: Removed ~1,176 lines of unused code left behind from past restructurings — 3 entire modules (`BaseMeasureItem`, `ray_layer`, `beamsplitter_cube_factory`), 7 unused classes, 6 unused functions, and 12 speculative exception subclasses that were never raised

### Changed

- **Locked items remain selectable**: Locked items now stay selectable (clickable) on the canvas; previously locking removed `ItemIsSelectable`, making locked items completely inert. This enables group-relative-lock dragging and aligns with Photoshop/Figma-style lock behavior
- **Layer panel icons**: Image-based layer-type icons were removed in favor of programmatically drawn shapes so the layer panel renders consistently across environments (including WSL and mixed-DPI setups)

### Fixed

- **Built-in library toggle**: The standard component library can now be unchecked in Preferences; previously the checkbox was force-locked and the library dock always showed built-in components regardless
- **Lens Size scaling**: Standard Edit dialog now scales interface endpoint coordinates proportionally when "Size" changes, so lenses resize beyond 1" correctly (previously only the sprite scaled, not the optical surface)
- **Snap guide persistence**: Purple dotted magnetic-snap guide lines no longer remain on the canvas after releasing a drag; `clear_snap_guides` is now called after all `setPos` calls in `handle_drag_end`, added to `handle_rotation_end`, and a safety-net clear in `BaseObj.mouseReleaseEvent`
- **Gaussian beam rendering**: Detect mid-segment beam waist for proper subsampling; use per-segment intensity for brightness
- **Component resolve order**: User library roots are resolved before built-in paths for `@component` lookups
- **Component Editor shortcuts**: Keyboard shortcuts (Save, Undo, Redo, Copy, Paste) now correctly target the Component Editor when it is the active window instead of routing to the main window. Fixed undo/redo leaking across windows via `ApplicationShortcut`, and enabled the native menu bar on macOS so the editor's menus appear at the screen top when active
- **Save dialog shows previous files**: The Save As dialog now opens in the directory of the last saved file and automatically appends `.json` when the user omits the extension, ensuring previously saved assemblies are visible in the file browser
- **Component Editor disappears on file dialog cancel**: On macOS, cancelling a file dialog (Open Image, Import Zemax, etc.) caused the Component Editor to fall behind the main window, appearing to close. Fixed by making the editor an independent top-level window so the OS correctly returns focus to it
- **Auto-delete empty groups**: Groups are now automatically removed when all their members are deleted. Nested groups cascade correctly, linked assembly groups are excluded, and the cleanup is fully undoable/redoable
- **Text note color**: Text notes now use theme-aware colors (white in dark mode, black in light mode) instead of hardcoded dark blue that was difficult to read on dark backgrounds
- **Text note editing UX**: Double-click reliably enters edit mode with all text selected; Escape exits edit mode and deselects; text selection highlighting is properly cleared when exiting edit mode; clicking elsewhere while editing correctly exits edit mode


## [0.3.3] - 2026-03-28

### Added

- **Update Canvas Instances**: Component Editor **Canvas** menu **Update Canvas Instances…** — after confirmation, updates every placed component on the main canvas that matches the current component name (single batch undo; pose and lock preserved)
- **Gaussian Beam Propagation**: Full Gaussian beam support using the complex beam parameter (q-parameter)
  - ABCD matrix transforms through lenses, curved refractive surfaces, and free-space propagation
  - Source editor toggle for Gaussian mode with configurable beam waist
  - Per-point beam radius (`1/e²`) tracked along every ray path
  - GLSL per-pixel Gaussian shader for smooth beam envelope rendering (replaces contour polygon rasteriser)
  - Mirror reflection splits Gaussian beams at each segment to prevent corner artifacts
  - Inspect tool shows beam waist, Rayleigh range, and divergence at any point along the beam
- **Component Editor Save To**: **Create New…** (pick a folder and register it as a library) and **Manage Libraries…** (opens Preferences on the Library page)
- **Preferences expansion**: Four new Preferences pages — **General** (autosave toggle + interval, max recent files), **Appearance** (dark mode, scale bar visibility), **Canvas & Editing** (grid snap size, magnetic snap tolerance, rotation snap angle, scroll-wheel sensitivity, auto-trace, default ray width, max ray events, clone offset), **Export Defaults** (PNG scale, PDF DPI, export margin). All settings are persisted via `QSettings` and take effect immediately or on next startup as appropriate.
- **Runtime preferences module** (`core/preferences.py`): module-level attributes loaded from `SettingsService` on startup and refreshed when Preferences are saved; consumers read values directly without coupling to `QSettings`.

### Changed

- **Component Editor**: Full **menu bar** (File, Edit, Library, Canvas); on macOS menus render **inside the editor window** (`setNativeMenuBar(False)`) so they clearly belong to the tool; removed the duplicate **toolbar** (text-only menus, no redundant icon strip)
- **Component Editor** interface list: **incremental** tree updates and suppressed auto-scroll when selection is updated from the canvas, fixing the list **jumping to the top** on mis-clicks
- **Component Editor** coordinates: **SmartDoubleSpinBox** fields for direct mm editing (replaces double-click coordinate labels)
- **Component Editor** name field: after loading or renaming, the caret is placed at the **start** so long names show the beginning instead of the truncated tail
- **Theme stylesheets**: Added `QTableWidget`, `QHeaderView`, and `QListWidget` rules to both dark and light QSS themes for consistent rendering (fixes grid-line color mismatch in dark mode)

### Fixed

- **Raytracing engine**: `remaining_length` is now correctly decremented after each optical interaction — previously rays could propagate beyond the source's configured `ray_length_mm` after hitting any element
- **Waveplate directionality tests**: Corrected 5 tests that had wrong physics expectations — waveplate Jones matrix is symmetric (`J = J^T`), so forward and backward passes are identical; the mirror between passes (not the waveplate direction) is what flips handedness in double-pass setups
- **TIR test geometry**: Fixed surface normal direction in total-internal-reflection test so the ray is correctly interpreted as traveling from glass (n=1.5) into air (n=1.0)
- **Angle convention in raytracing tests**: Corrected source angle from 90° to 270° (user-angle convention where 270° = +Y direction) across parity, use-case, and refractive tests
- **Refractive rotation side test**: Swap `n1`/`n2` when flipping surface endpoints so both orientations model the same physical interface
- **Collaboration tests**: Replaced `QGraphicsScene` with lightweight mocks to eliminate Qt widget dependency in unit tests
- **Beamsplitter widget test**: Updated to verify tool-controller infrastructure instead of removed direct-insert API
- **UI best practices test**: Fixed renamed attribute paths (`editor_state` → `_editor_state`, `_clipboard` → `component_ops._clipboard`) and keyboard shortcut API
- **Gaussian beam rendering**: Free stale VBO data after GPU upload; cleaned up docstrings for software/GLSL render paths
- **Type hints**: Modernized `Optional[X]` → `X | None` and `Union[...]` → `|` syntax across source and test files
- **External Component Storing**: Centralized library management via new `LibraryService` — fixes settings-configured library paths being silently ignored by the dock, scene loading, and collaboration. Components from all configured libraries now appear correctly everywhere.
  - **Library enable/disable**: Libraries can be toggled on/off in Preferences without removing them (ideal for switching between project contexts)
  - **Save To selector**: Component Editor lets you choose which library to save into
  - **Link vs Copy import**: Importing a library folder now offers "Link" (register the path, ideal for git repos) or "Copy" (legacy behavior)
  - **Missing component report**: Scene loading warns when components cannot be resolved, with guidance to configure library paths
  - **Preferences overhaul**: Library page uses a table with Name, Path, Components, Status columns and enable/disable checkboxes
  - **Open Library Folder submenu**: Tools menu lists all known libraries for quick access
- **Component Editor** file dialogs: cancelling **Export**, **Import**, or **Load library from path** no longer closes the editor (explicit `QFileDialog` with `WA_QuitOnClose` disabled)
- **Component Editor** interface tree: selection styling uses **palette** roles for correct contrast in dark mode
- **Component Editor** save: saving no longer copies component JSON to the **clipboard** automatically
- **Layer model**: Guard against stale C++ objects (`sip.isdeleted`) when resolving cached `QGraphicsItem` references, preventing crashes during rapid undo/delete sequences

### Removed

- **Component Editor**: Obsolete legacy methods from an older UI revision and the redundant main **toolbar**

## [0.3.2] - 2026-03-26

### Added

- **Placed components on canvas**: context menu **Edit in Component Editor…** (save updates library and instance, undoable) and **Apply Properties to All…** (choose scope and fields, single batch undo)
- **Layer panel context menu**: **Edit…**, **Edit in Component Editor…** for items, and **Z-Order** submenu (bring forward/back, to front/back)
- **Save guards** when saving from the Component Editor to reduce accidental silent duplication
- **Undo commands** for operations that were previously missing from the stack: layer rename; visibility and lock toggles; z-order changes; inline text note edits; rectangle property edits from the editor dialog

### Changed

- **Hover and hitboxes**: Clearer hover feedback and more forgiving hit targets for sources, component sprites, rectangle annotations, and shared base item behavior
- **Developer layout**: Build and icon scripts live under `tools/`; generated `.icns` / `.ico` go to `tools/generated_icons/`; Ruff and Mypy settings consolidated in `pyproject.toml`

### Fixed

- **Undo/redo consistency**: Layer model changes, z-order from multiple UI paths, annotation deletes, path measure wiring on load, component editor save baseline, and related cases no longer leave Ctrl+Z targeting the wrong action
- **Group rotation undo**: Restores rotations for ruler and angle measure items included in the group
- **Drag + autosave**: Undo merge during moves emits `commandPushed` so the autosave debounce resets correctly
- **Collaboration**: Starting the local server from the dialog raises `OSError` on failure so errors surface properly
- **Rotation tracking**: Missing `AngleMeasureItem` import in rotation startup
- **Raytracing engine**: Removed dead parallel-detection branch (condition was never true)
- **Documentation site**: GitHub Pages header shows the home button label again

### Removed

- Tracked `optiverse.iconset/` PNGs (icons are generated locally); root `resources/` placeholder directory
- Obsolete `tools/` helpers (`compile_ui.py`, `compile_rc.py`, old lint/WebSocket test scripts); duplicate `.ruff.toml` and `mypy.ini` (see `pyproject.toml`)
- Unused `StorageService.ensure_standard_components` and other dead code paths cleaned up for the release

## [0.3.1] - 2026-03-25

### Added

- **Linear Polarizer Element**: Full raytracing support with Malus's Law, finite extinction ratio, Jones vector decomposition, and drag-and-drop library component
- **Faraday Rotator Element**: Non-reciprocal polarization rotation via magneto-optic effect for optical isolator designs; includes library component
- **Per-Segment Intensity Tracking**: Ray segments before lossy elements render at full brightness while downstream segments render dimmer (both software and OpenGL renderers)
- **Per-Segment Polarization Tracking**: Inspect tool now shows correct polarization state at each point along the ray
- **Library Search/Filter Bar**: Filter components in the library tree by name
- **Smart Spinboxes**: Replace plain spinboxes with SmartDoubleSpinBox/SmartSpinBox across source, rectangle, and component editors

### Changed

- **Source Editor Live Editing**: All parameters now apply live instead of only on OK click
- **Lens Physics**: Use ideal non-paraxial deflection formula (arctan) instead of paraxial approximation, eliminating spurious aberration at large impact parameters
- **Unified Item Drag Handling**: Single code path for all non-Ctrl left-button drags, eliminating competition between Qt's built-in drag and custom handler
- **Polarizer Properties Panel**: Only shows properties relevant to the selected polarizer subtype (waveplate, linear polarizer, Faraday rotator)
- **Undo Merge Window**: 0.5s merge window for MoveItemCommand to reduce undo stack noise

### Fixed

- Fix wavelength editing not persisting when source editor is in "Custom Color" mode
- Fix collaboration crash when syncing RulerItem/TextNoteItem (only BaseObj subclasses have 'edited' signal)
- Fix host state transfer: host now uploads canvas to server on connect instead of requesting empty state
- Fix collaboration server leaking commands across sessions (connections now scoped per session)
- Fix multi-selection drag: clicking an already-selected item preserves current selection
- Fix rubber band selection appearing during item drag
- Fix waveplate backward propagation: use transpose (not conjugate) for Jones matrix
- Fix mirror polarization: use r_s = r_p = -1 (Born & Wolf convention) to prevent spurious phase at normal incidence
- Fix context menu delete to emit requestDelete signal for proper undo integration and automatic retrace
- Fix signal reconnection on file load for optical items, text notes, and rectangles
- Fix layer panel orphan items and ghost node deletion
- Fix lock state sync between BaseObj and LayerNode
- Fix component editor endpoint dragging to find closest endpoint globally

## [0.3.0] - 2025-12-20

### Added

- **Layer Widget System Overhaul**: Complete rewrite using Qt Model/View/Delegate pattern
  - `LayerTreeState` as single source of truth for hierarchy and z-order
  - `LayerNode` dataclass for tree nodes (groups and items)
  - `LayerItemModel` with full drag-and-drop support
  - `LayerItemDelegate` for custom icon painting (visibility, lock, folder icons)
  - `KeyboardLayerTreeView` with Delete/Backspace key handling
  - `LayerZOrderApplier` for automatic z-value synchronization
- **Group Management**: Full support for creating, deleting, and nesting groups
  - Photoshop-style effective visibility (inherit from parent chain)
  - Effective lock state (locked if self or any ancestor is locked)
  - Drag-and-drop reordering within and between groups
- **Undo/Redo for Layer Operations**
  - `CreateGroupCommand` for grouping items
  - `DeleteGroupCommand` for ungrouping/deleting groups
  - `MoveNodeCommand` for z-order and hierarchy changes
  - `BatchCommand` for combining multiple operations
- **Parallel Raytracing**: Multi-threaded ray tracing for 2-4x speedup on multi-core CPUs
- **Debounced UI Updates**: Smart refresh timers (50-100ms) to prevent UI flicker during rapid changes

### Changed

- **Drag System Architecture**: Refactored to work with Qt patterns instead of against them
- **Z-Order Management**: Now derived from layer tree traversal order, no longer stored directly on items
- **Item Visibility**: Controlled through layer panel with effective state inheritance

### Fixed

- Fixed z-order signaling issues causing items to appear in wrong order
- Fixed double-click bug in layer panel
- Fixed bug when loading files with layer state
- Fixed source visibility not updating correctly
- Fixed renaming items/groups in layer panel
- Fixed save/load problems with layer hierarchy
- Fixed closing errors and removed debug print statements
- Fixed beam block component behavior
- Increased hitbox size for easier selection

### Removed

- Legacy raytracing implementation (replaced by parallel processing engine)

## [0.2.x] - Previous Releases

Prior versions did not maintain a changelog. See git history for details.


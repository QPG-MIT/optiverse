# Objects Restructure Strategy

## Overview

Restructure the optical elements architecture to provide better organization and a comprehensive component library system.

## Goals

1. **Rename `widgets` → `objects`**: Better semantic naming for optical components
2. **Organize by category**: Create subfolders for lenses, mirrors, beamsplitters, sources
3. **Standard components**: Pre-populate library with standard components using specific images
4. **Component registry**: Central system to manage available components
5. **Library integration**: Seamlessly integrate standard components into UI and shortcuts

## File Structure Changes

### Before
```
src/optiverse/
└── widgets/
    ├── __init__.py
    ├── base_obj.py
    ├── lens_item.py
    ├── mirror_item.py
    ├── beamsplitter_item.py
    ├── source_item.py
    ├── ruler_item.py
    ├── text_note_item.py
    ├── graphics_view.py
    ├── image_canvas.py
    ├── component_sprite.py
    └── images/
        ├── lens_1_inch_mounted.png
        ├── standard_mirror_1_inch.png
        ├── beamsplitter_50_50_1_inch.png
        └── ...
```

### After
```
src/optiverse/
└── objects/
    ├── __init__.py              (exports all public classes)
    ├── base_obj.py
    ├── component_sprite.py
    ├── component_registry.py    (NEW: standard component definitions)
    ├── lenses/
    │   ├── __init__.py
    │   └── lens_item.py
    ├── mirrors/
    │   ├── __init__.py
    │   └── mirror_item.py
    ├── beamsplitters/
    │   ├── __init__.py
    │   └── beamsplitter_item.py
    ├── sources/
    │   ├── __init__.py
    │   └── source_item.py
    ├── annotations/             (ruler, text)
    │   ├── __init__.py
    │   ├── ruler_item.py
    │   └── text_note_item.py
    ├── views/                   (graphics view, canvas)
    │   ├── __init__.py
    │   ├── graphics_view.py
    │   └── image_canvas.py
    └── images/
        ├── lens_1_inch_mounted.png
        ├── standard_mirror_1_inch.png
        ├── beamsplitter_50_50_1_inch.png
        └── ...
```

## Standard Component Definitions

### Standard Lens
- **Name**: "Standard Lens (1\" mounted)"
- **Image**: `lens_1_inch_mounted.png`
- **Properties**:
  - EFL: 100.0 mm
  - Length: 25.4 mm (1 inch)
  - mm_per_pixel: 0.1
  - line_px: Calibrated to image

### Standard Mirror
- **Name**: "Standard Mirror (1\")"
- **Image**: `standard_mirror_1_inch.png`
- **Properties**:
  - Length: 25.4 mm (1 inch)
  - mm_per_pixel: 0.1
  - line_px: Calibrated to image

### Standard Beamsplitter
- **Name**: "Standard Beamsplitter (50/50 1\")"
- **Image**: `beamsplitter_50_50_1_inch.png`
- **Properties**:
  - Split T: 50%
  - Split R: 50%
  - Length: 25.4 mm (1 inch)
  - mm_per_pixel: 0.1
  - line_px: Calibrated to image

### Standard Source
- **Name**: "Standard Source"
- **Properties**:
  - n_rays: 5
  - spread_deg: 5.0
  - size_mm: 10.0
  - ray_length_mm: 500.0

## Component Registry System

Create `component_registry.py` with:

```python
class ComponentRegistry:
    """Central registry for all standard optical components."""
    
    @staticmethod
    def get_standard_components() -> list[dict]:
        """Return list of standard component definitions."""
        pass
    
    @staticmethod
    def get_components_by_category() -> dict[str, list[dict]]:
        """Return components organized by category."""
        pass
```

## Implementation Steps (TDD)

### Phase 1: Setup and Tests
1. ✅ Create strategy document
2. Write tests for component registry
3. Write tests for import structure

### Phase 2: Create New Structure
4. Create `objects/` folder with subfolders
5. Create `component_registry.py`
6. Move files to new locations
7. Update `__init__.py` files for clean imports

### Phase 3: Update Storage Service
8. Modify `storage_service.py` to auto-populate with standard components
9. Ensure library JSON is created/updated with defaults

### Phase 4: Update Imports
10. Update `main_window.py` imports
11. Update test imports
12. Update any other files importing from widgets

### Phase 5: UI Integration
13. Update `MainWindow._build_library_dock()` to show categories
14. Update `MainWindow.populate_library()` to organize by category
15. Update menu shortcuts to use standard components from registry

### Phase 6: Testing
16. Run all existing tests
17. Fix any import errors
18. Verify all functionality works

## Import Changes Required

### Files to Update
1. `src/optiverse/ui/views/main_window.py`
2. `src/optiverse/core/undo_commands.py` (if it imports widgets)
3. All test files in `tests/`
4. Any other files discovered during grep

### Pattern
```python
# Before
from ...widgets.lens_item import LensItem
from ...widgets.mirror_item import MirrorItem
from ...widgets.beamsplitter_item import BeamsplitterItem
from ...widgets.source_item import SourceItem
from ...widgets.graphics_view import GraphicsView

# After
from ...objects import LensItem, MirrorItem, BeamsplitterItem, SourceItem, GraphicsView
# OR more explicitly
from ...objects.lenses import LensItem
from ...objects.mirrors import MirrorItem
from ...objects.beamsplitters import BeamsplitterItem
from ...objects.sources import SourceItem
from ...objects.views import GraphicsView
```

## Library UI Enhancement

### Current: Flat List
- All components in one list
- No organization

### New: Categorized View
- Use QTreeWidget or QListWidget with separators
- Categories: Lenses, Mirrors, Beamsplitters, Sources
- Each category shows its standard components
- Custom components grouped under category

## Menu Shortcuts Integration

### Current Behavior
```python
def add_lens(self):
    L = LensItem(LensParams())  # Creates with empty defaults
```

### New Behavior
```python
def add_lens(self):
    # Use standard lens from registry
    std_lens = ComponentRegistry.get_standard_lens()
    L = LensItem(LensParams(**std_lens))
```

This ensures menu shortcuts create the same components as the library.

## Testing Strategy

### Unit Tests
- `test_component_registry.py`: Test registry returns correct definitions
- `test_objects_imports.py`: Test import structure works

### Integration Tests
- `test_main_window.py`: Verify library population
- `test_component_creation.py`: Verify standard components create correctly

### Manual Tests
- Open app, verify library shows categories
- Drag standard components, verify they have correct images
- Use menu shortcuts, verify they match library components

## Rollback Plan

If issues arise:
1. Git commit after each phase
2. Can revert to previous commit
3. Import structure allows gradual migration if needed

## Success Criteria

- ✅ All files moved to new structure
- ✅ All imports updated
- ✅ All tests passing
- ✅ Component library shows standard components
- ✅ Standard components use specified images
- ✅ Menu shortcuts use standard components
- ✅ No linter errors
- ✅ App runs without errors

## Timeline Estimate

- Phase 1-2: 30 minutes (setup, structure)
- Phase 3: 15 minutes (storage service)
- Phase 4: 30 minutes (imports)
- Phase 5: 30 minutes (UI integration)
- Phase 6: 30 minutes (testing)

**Total**: ~2.5 hours

## Notes

- Keep `base_obj.py` and `component_sprite.py` at objects root (shared by all)
- Keep `ruler_item` and `text_note_item` in annotations subfolder (not optical elements)
- Keep `graphics_view` and `image_canvas` in views subfolder (UI components)
- Maintain backward compatibility where possible during transition


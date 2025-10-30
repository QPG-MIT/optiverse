# Quick Reference: Interface Coordinate System

## ✅ **FIXED - New Simplified System**

### Coordinate System (Everywhere)

**Origin**: IMAGE CENTER (0, 0)  
**Y-axis direction**:
- Editor Canvas: Y points UP ↑ (intuitive for editing)
- Storage/Scene: Y points DOWN ↓ (Qt standard)

```
         Y ↑ (editor)
          |
    -X ←──┼──→ +X
          |
         ↓ Y (storage/scene)
```

### Example Coordinates

**Interface at image center:**
```
Storage: (-5, 0) → (5, 0)  // horizontal line through center
Canvas:  (-5, 0) → (5, 0)  // same (Y=0 appears at center)
```

**Interface 5mm above center:**
```
Storage: (-5, -5) → (5, -5)  // Y negative = above center
Canvas:  (-5, +5) → (5, +5)  // Y positive displays up
```

**Interface 5mm below center:**
```
Storage: (-5, +5) → (5, +5)  // Y positive = below center  
Canvas:  (-5, -5) → (5, -5)  // Y negative displays down
```

### Transformation Formula

**Storage ↔ Canvas:**
```python
y_canvas = -y_storage    # Just flip Y!
x_canvas = x_storage     # X unchanged
```

That's it! No complex transformations, no origin shifting, no dimension tracking.

### Quick Test

1. Open Component Editor
2. Add interface → should appear at (0, 0) = center
3. Drag up 5mm → coordinates show (0, 5) in editor
4. Save → stored as (0, -5) in JSON (Y-down)
5. Drag to scene → appears at item center ✓

### Files Changed

1. **component_editor_dialog.py** - Simplified coordinate transformation
2. **main_window.py** - Added refractive_object handler
3. **interface_tree_panel.py** - Default position now (0, 0)

### Status

✅ Tests pass  
✅ Code ready  
🔄 Awaiting user testing with real components

---

**Next**: Test with your Thorlabs objective lens!


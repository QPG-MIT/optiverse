# Quick Reference Card: RaytracingV2 → Optiverse Port

## 🎯 Implementation Phases

```
┌─────────────────────────────────────────────────────┐
│  PHASE 1: Critical (5-7 hours)                     │
│  ✓ Ghost preview during drag                       │
│  ✓ Clickable sprites (hit testing)                 │
├─────────────────────────────────────────────────────┤
│  PHASE 2: Visual Feedback (2-3 hours)              │
│  ✓ Selection tint on sprites                       │
│  ✓ ItemChange sprite updates                       │
├─────────────────────────────────────────────────────┤
│  PHASE 3: Polish (1.5 hours)                       │
│  ✓ Pan controls (Space + Middle button)            │
│  ✓ Insert menu                                     │
└─────────────────────────────────────────────────────┘
```

---

## 📋 Checklist

### Ghost Preview (graphics_view.py)
```python
# Add to __init__:
□ self._ghost_item: Optional[...] = None
□ self._ghost_rec: Optional[dict] = None

# Add methods:
□ def _clear_ghost(self)
□ def _make_ghost(self, rec, scene_pos)

# Modify methods:
□ dragEnterEvent() - create ghost
□ dragMoveEvent() - move ghost
□ dragLeaveEvent() - clear ghost
□ dropEvent() - clear ghost before real item
```

### Sprite Helpers (base_obj.py)
```python
# Add methods to BaseObj:
□ def _sprite_rect_in_item(self) -> Optional[QRectF]
□ def _shape_union_sprite(self, path) -> QPainterPath
□ def _bounds_union_sprite(self, rect) -> QRectF

# Modify itemChange():
□ Add sprite update on selection change
```

### Element Items (lens/mirror/bs_item.py)
```python
# Modify in each:
□ boundingRect() - wrap with _bounds_union_sprite()
□ shape() - wrap with _shape_union_sprite()
```

### Selection Feedback (component_sprite.py)
```python
# Add to ComponentSprite:
□ def paint(self, p, opt, widget)
    # Draw blue tint if parent selected
```

### Pan Controls (graphics_view.py)
```python
# Add to __init__:
□ self._hand = False

# Add/modify methods:
□ keyPressEvent() - Space handling
□ keyReleaseEvent() - Space handling
□ mousePressEvent() - Middle button
□ mouseReleaseEvent() - Middle button
```

---

## 🔢 Line Number Reference (V2 → Package)

| Feature | RaytracingV2.py | Package File | Status |
|---------|-----------------|--------------|--------|
| Ghost vars | 1210-1211 | graphics_view.py | ❌ Add |
| _clear_ghost | 1212-1220 | graphics_view.py | ❌ Add |
| _make_ghost | 1222-1283 | graphics_view.py | ❌ Add |
| Sprite helpers | 165-187 | base_obj.py | ❌ Add |
| Selection tint | 399-406 | component_sprite.py | ❌ Add |
| Pan controls | 1354-1383 | graphics_view.py | ❌ Add |

---

## 💻 Code Snippets

### Ghost Preview Basics
```python
# In GraphicsView.__init__:
self._ghost_item: Optional[QtWidgets.QGraphicsItem] = None
self._ghost_rec: Optional[dict] = None

def _clear_ghost(self):
    if self._ghost_item is not None:
        try:
            self.scene().removeItem(self._ghost_item)
        except Exception:
            pass
    self._ghost_item = None
    self._ghost_rec = None

# In dragEnterEvent:
self._clear_ghost()
self._make_ghost(rec, self.mapToScene(e.pos()))

# In dropEvent:
self._clear_ghost()
```

### Sprite Union Helpers
```python
# In BaseObj:
def _sprite_rect_in_item(self) -> Optional[QtCore.QRectF]:
    sp = getattr(self, "_sprite", None)
    if sp is None or not sp.isVisible():
        return None
    return sp.mapRectToParent(sp.boundingRect())

def _bounds_union_sprite(self, base_rect):
    r = self._sprite_rect_in_item()
    if r is not None:
        pad = 2.0
        r = r.adjusted(-pad, -pad, pad, pad)
        base_rect = base_rect.united(r)
    return base_rect

# In LensItem.boundingRect():
rect = QtCore.QRectF(...)  # your existing rect
return self._bounds_union_sprite(rect)
```

### Selection Feedback
```python
# In ComponentSprite:
def paint(self, p: QtGui.QPainter, opt, widget=None):
    super().paint(p, opt, widget)
    par = self.parentItem()
    if par is not None and par.isSelected():
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        p.setPen(QtCore.Qt.PenStyle.NoPen)
        p.setBrush(QtGui.QColor(30, 144, 255, 70))
        p.drawRect(self.boundingRect())
```

### Pan Controls
```python
# In GraphicsView:
def keyPressEvent(self, e: QtGui.QKeyEvent):
    if e.key() == QtCore.Qt.Key.Key_Space:
        self._hand = True
        self.setDragMode(self.DragMode.ScrollHandDrag)
        return
    super().keyPressEvent(e)

def mousePressEvent(self, e: QtGui.QMouseEvent):
    if e.button() == QtCore.Qt.MouseButton.MiddleButton:
        self.setDragMode(self.DragMode.ScrollHandDrag)
        # Create fake left button event...
```

---

## 🧪 Testing Checklist

### After Ghost Preview
- [ ] Ghost appears when drag enters canvas
- [ ] Ghost follows cursor
- [ ] Ghost shows sprite if available
- [ ] Ghost disappears on drag leave
- [ ] Ghost cleared on drop
- [ ] No memory leaks (test repeated drags)

### After Sprite Helpers
- [ ] Can click sprite to select
- [ ] Can drag by clicking sprite
- [ ] Bounds encompass sprite
- [ ] Shape includes sprite
- [ ] Performance OK with large images

### After Selection Feedback
- [ ] Blue tint appears on select
- [ ] Tint disappears on deselect
- [ ] Works with multiple items
- [ ] No flickering

### After Pan Controls
- [ ] Space + drag pans
- [ ] Middle button + drag pans
- [ ] Both restore drag mode on release

---

## ⚠️ Common Pitfalls

1. **Ghost memory leak**: Always call `_clear_ghost()` in ALL exit paths
2. **Sprite not clickable**: Must modify BOTH `shape()` AND `boundingRect()`
3. **Tint flicker**: Ensure `sp.update()` called in `itemChange()`
4. **Ghost sprite missing**: Call `_maybe_attach_sprite()` on ghost item
5. **Pan stuck**: Always restore `RubberBandDrag` mode

---

## 🎯 Priority Order

```
1. _clear_ghost()         ← Start here
2. _make_ghost()          ← Core ghost logic
3. Modify drag events     ← Hook up ghost
4. _sprite_rect_in_item() ← Sprite foundation
5. Union helpers          ← Make sprites clickable
6. Use in element items   ← Apply to all elements
7. Selection feedback     ← Visual polish
8. Pan controls           ← Extra convenience
```

---

## 📏 Success Criteria

**Minimum Viable:**
- ✅ Ghost preview works
- ✅ Sprites are clickable

**Fully Complete:**
- ✅ All Phase 1 + Phase 2
- ✅ Selection tint
- ✅ Pan controls

**Production Ready:**
- ✅ All phases done
- ✅ All tests pass
- ✅ No memory leaks
- ✅ Smooth performance

---

## 🚨 If You Get Stuck

1. **Ghost not appearing?**
   - Check `_make_ghost()` is being called
   - Verify scene.addItem() called on ghost
   - Check ghost zValue is high (9999+)

2. **Sprite still not clickable?**
   - Verify BOTH shape() and boundingRect() modified
   - Check `_sprite_rect_in_item()` returns valid rect
   - Print debug info in shape() to verify union

3. **Tint not showing?**
   - Check `paint()` override in ComponentSprite
   - Verify `isSelected()` returns True when expected
   - Check alpha value (70 is good, higher = more visible)

4. **Performance issues?**
   - Profile with large sprites
   - Consider caching sprite bounds
   - Check for unnecessary repaints

---

## 🎓 Key Concepts

**Ghost Preview:**
- Temporary item during drag
- Semi-transparent (0.7 opacity)
- Non-interactive (NoButton)
- High z-value (renders on top)

**Shape Union:**
- shape() = mouse click hit area
- boundingRect() = repaint/collision area
- Must include sprite for clickability

**Selection Feedback:**
- Override paint() in sprite
- Check parent's isSelected()
- Draw translucent overlay

---

## ⏱️ Time Budget

| Task | Time | Running Total |
|------|------|---------------|
| Ghost preview | 3-4h | 4h |
| Sprite helpers | 2-3h | 7h |
| Selection feedback | 1-2h | 9h |
| Pan controls | 1h | 10h |
| Testing | 2-3h | 13h |
| **TOTAL** | **~13h** | |

---

## 📞 Quick Help

**Need detailed instructions?** → IMPLEMENTATION_STRATEGY.md  
**Want to see comparisons?** → FEATURE_COMPARISON.md  
**Need overview?** → IMPLEMENTATION_SUMMARY.md  
**Start from scratch?** → RAYTRACINGV2_ANALYSIS.md

---

**Last Updated:** 2025-10-27  
**Version:** 1.0


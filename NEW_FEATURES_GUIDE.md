# New Features Guide

## 🎯 Quick Start: Try the New Features!

All the improvements from RaytracingV2.py have been successfully implemented. Here's how to use them:

---

## 1. 👻 Ghost Preview During Drag

### What It Does
See a semi-transparent preview of components as you drag them from the library.

### How to Use
1. Open the Component Library dock (right side)
2. Click and drag any component (Lens, Mirror, etc.)
3. **✨ You'll see a ghost preview following your cursor!**
4. The preview shows exactly what will be dropped, including the decorative sprite
5. Drop to place the component, or drag outside to cancel

### Tips
- The ghost uses the correct default angle for each component type:
  - Lens: 90°
  - Mirror: 0°
  - Beamsplitter: 45°
- Works with components that have custom images

---

## 2. 🖱️ Clickable Component Sprites

### What It Does
Click anywhere on the component image, not just the thin geometry line.

### How to Use
1. Add a component to the canvas (especially one with a decorative image)
2. **✨ Click anywhere on the component image - it will select!**
3. You can also hover over the image and see the cursor change

### Before vs After
**Before:** Had to precisely click the thin line  
**After:** Click anywhere on the component image

### Benefits
- Much faster component selection
- Less frustration with small/thin components
- More intuitive workflow

---

## 3. 🎨 Selection Visual Feedback

### What It Does
Selected components show a translucent blue tint on their sprite.

### How to Use
1. Click on any component with a decorative image
2. **✨ The entire image lights up with a blue tint!**
3. Click elsewhere to deselect - tint disappears

### What You'll See
- Blue overlay (semi-transparent) on selected component sprites
- Works with all component types: Lens, Mirror, Beamsplitter
- Clean, immediate visual feedback

---

## 4. ⌨️ Pan Controls

### Space Key Pan
**Hold Space + Drag = Pan the view**

1. Hold down the **Space** key
2. **✨ Cursor changes to indicate pan mode**
3. Click and drag to pan the view
4. Release Space to return to selection mode

### Middle Mouse Button Pan
**Middle Button + Drag = Pan the view**

1. Click and hold the **Middle Mouse Button**
2. **✨ Drag to pan the view**
3. Release to return to selection mode

### Bonus: Zoom Shortcuts
- **Plus (+) or Equal (=)** - Zoom in
- **Minus (-) or Underscore (_)** - Zoom out

---

## 5. 📋 Insert Menu

### What It Does
Better menu organization with a dedicated "Insert" menu.

### How to Use
1. Look at the menu bar: **File | Insert | View | Tools**
2. **✨ New Insert menu!**
3. Click to see all insertion actions:
   - Source
   - Lens
   - Mirror
   - Beamsplitter
   - ─────────
   - Ruler
   - Text

### Benefits
- Cleaner menu organization
- All insertion actions in one place
- Easier to discover features

---

## 🎮 Quick Controls Reference

### Navigation
| Action | Method 1 | Method 2 |
|--------|----------|----------|
| Pan View | Hold Space + Drag | Middle Button + Drag |
| Zoom In | + or = key | Mouse Wheel Up |
| Zoom Out | - or _ key | Mouse Wheel Down |
| Fit View | Ctrl+0 | View > Fit Scene |

### Selection
| Action | Method |
|--------|--------|
| Select Component | Click anywhere on image or line |
| Multi-Select | Ctrl+Click or Rubber Band |
| Rotate | Ctrl+Wheel on selected item |
| Delete | Right-click > Delete |

### Insertion
| Action | Method 1 | Method 2 |
|--------|----------|----------|
| Add Component | Drag from Library | Insert Menu |
| Add Ruler | Toolbar or Insert > Ruler | Two clicks on canvas |
| Add Text | Toolbar or Insert > Text | - |

---

## 💡 Pro Tips

### Ghost Preview
- The ghost preview works even for components with custom images
- Cancel a drag by moving outside the canvas area
- The preview shows the exact size and orientation

### Clickable Sprites
- Larger components are now MUCH easier to click
- Useful when components overlap - click the visible sprite
- Works in combination with ghost preview

### Selection Feedback
- Blue tint only shows on components with decorative sprites
- Helps when you have many components on screen
- Tint disappears immediately on deselection

### Pan Controls
- Use Space pan for quick repositioning while working
- Use Middle button pan if you prefer mouse-only workflow
- Pan mode automatically switches back to selection mode
- Plus/Minus zoom works while in any mode

### Insert Menu
- Still works alongside the toolbar
- Use menu if toolbar is hidden
- Keyboard shortcuts still work (if assigned)

---

## 🐛 Troubleshooting

### Ghost preview doesn't show
- Make sure you're dragging from the Component Library
- Try dragging a different component
- Check that the mime type is "application/x-optics-component"

### Can't click on sprite
- Make sure the component has a decorative sprite image
- Try clicking closer to the center of the image
- If clicking the line works but not the sprite, file a bug report

### Selection tint not showing
- Tint only appears on components with decorative sprite images
- Make sure the component is actually selected (check outline)
- Try deselecting and selecting again

### Pan not working
- Make sure you're holding Space key or middle button
- Try clicking and dragging while holding the key
- Check that no other app is capturing the key/button

---

## 📊 Feature Comparison

### Before (Old Package)
- ❌ No drag preview
- ❌ Only thin lines clickable
- ⚠️ Subtle selection feedback
- ❌ No Space/Middle pan
- ❌ No Insert menu

### After (With RaytracingV2 Improvements)
- ✅ Ghost preview during drag
- ✅ Full sprite images clickable
- ✅ Blue tint selection feedback
- ✅ Space + Middle button pan
- ✅ Organized Insert menu

---

## 🎓 Learning More

### Keyboard Shortcuts
- Check the menu bar for keyboard shortcuts (shown on right side)
- Ctrl+E opens Component Editor
- Ctrl+O opens assembly file
- Ctrl+S saves assembly

### Advanced Features
- Right-click on components for context menu
- Ctrl+Wheel on selected items to rotate
- Double-click text notes to edit
- Ruler tool: two clicks to place, right-click to delete

---

## 🚀 Get Started Now!

1. **Run the application:**
   ```bash
   python -m optiverse.app.main
   ```

2. **Try ghost preview:**
   - Drag a component from the library
   - Watch the ghost follow your cursor!

3. **Try clickable sprites:**
   - Add a component with an image
   - Click anywhere on the image to select it

4. **Try pan controls:**
   - Hold Space and drag to pan
   - Or use middle mouse button

5. **Explore the Insert menu:**
   - Check out the new menu organization

---

## 🎉 Enjoy the Improved Experience!

These features make the optiverse application:
- **More intuitive** - see what you're doing
- **Faster to use** - easier selection and navigation
- **More polished** - professional visual feedback

Have fun building optical systems! 🔬✨


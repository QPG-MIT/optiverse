# Quick Test: Visual Interface System

## 🚀 Quick Start

Run the component editor:
```bash
python -m optiverse.app.main
```

Then: **Tools → Component Editor**

## ✅ Test 1: Simple Lens (30 seconds)

1. **Kind** dropdown → Select "lens"
2. Drag an image file onto the canvas (any lens image)
3. **Look for**:
   - ✅ ONE **cyan line** in center of image
   - ✅ Status bar: "Drag the colored line endpoints..."
   - ✅ Console: `[DEBUG] Created calibration line for lens...`
   - ✅ NO "Line Points (px)" section in right panel

4. **Drag** one of the line endpoints
5. **Look for**:
   - ✅ Line moves with your mouse
   - ✅ Console shows updates

**✨ SUCCESS**: You see a single cyan line you can drag!

## ✅ Test 2: BS Cube (1 minute)

1. **Kind** dropdown → Select "refractive_object"
2. Drag any image onto canvas
3. Click **"BS Cube Preset"** button
4. Enter **25.4** mm (1 inch cube)
5. Click **OK**

6. **Look for**:
   - ✅ **FIVE colored lines** forming a square with diagonal:
     - 4 **blue** lines (edges)
     - 1 **green** diagonal line (beam splitter)
   - ✅ Interface list shows 5 items
   - ✅ Console: `[DEBUG] Added interface line 1...` through 5
   - ✅ Console: `[DEBUG] paintEvent: Drawing 5 line(s)`

7. **Drag** any line endpoint
8. **Look for**:
   - ✅ Line moves
   - ✅ Geometry updates

9. **Click** on "Interface 3" in the list (the green diagonal)
10. **Look for**:
    - ✅ That line highlights on canvas

**✨ SUCCESS**: You see multiple colored lines you can drag!

## ✅ Test 3: Change Component Type (30 seconds)

1. **Kind** → "mirror"
2. **Look for**:
   - ✅ Line changes to **orange**

3. **Kind** → "beamsplitter"
4. **Look for**:
   - ✅ Line changes to **green**

5. **Kind** → "lens"
6. **Look for**:
   - ✅ Line changes to **cyan**

**✨ SUCCESS**: Line color updates based on component type!

## 🐛 If Something's Wrong

### No lines visible?
1. Check console for debug output
2. If you see "Created calibration line..." but no line:
   - Try resizing the window
   - Try clicking on the canvas
3. Check the image loaded correctly (you can see it)

### Old "Line Points" UI still visible?
1. Make sure you accepted the file changes
2. Restart the application
3. Check you're running from the correct directory

### Lines created but in wrong place?
Check console output for coordinates. For a 1000x600 image:
- Line at (450, 300) to (550, 300) should be visible in center
- Line at (0, 0) means something's wrong

## 📊 Expected Console Output

### For Simple Component (Lens)
```
[DEBUG] Created calibration line for lens: (450.0, 300.0) to (550.0, 300.0), color=#00b4b4
[DEBUG] Canvas now has 1 line(s)
[DEBUG] paintEvent: Drawing 1 line(s)
[DEBUG]   Line 0: (450.0, 300.0) to (550.0, 300.0), color=#00b4b4
```

### For BS Cube
```
[DEBUG] Added interface line 1: ... color=#6464ff
[DEBUG] Added interface line 2: ... color=#6464ff
[DEBUG] Added interface line 3: ... color=#009678
[DEBUG] Added interface line 4: ... color=#6464ff
[DEBUG] Added interface line 5: ... color=#6464ff
[DEBUG] Canvas now has 5 line(s)
[DEBUG] paintEvent: Drawing 5 line(s)
```

## ✅ All Tests Pass?

**Congratulations!** The visual interface system is working correctly. You now have:

- ✅ Visual line editing (no more coordinate spinboxes)
- ✅ Color-coded interfaces
- ✅ Drag-and-drop endpoint adjustment
- ✅ Multiple lines for complex optical components
- ✅ Unified system for simple and refractive objects

## 📝 Next Steps

- Create your own optical components
- Use the visual editor to align interfaces with your images
- Save components to the library
- Build complex optical systems!

---

**Need help?** Check:
- `docs/VISUAL_INTERFACE_FIXES_APPLIED.md` - Detailed fix documentation
- `docs/INTERFACE_COLOR_GUIDE.md` - Color scheme reference
- `docs/VISUAL_INTERFACE_EDITOR_COMPLETE.md` - Complete technical docs


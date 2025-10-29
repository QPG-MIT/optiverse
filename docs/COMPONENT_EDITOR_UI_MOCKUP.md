# Component Editor UI Mockup - Generalized Design

## Current UI vs Target UI

### Current UI Structure

```
┌────────────────────────────────────────────────────┐
│ Component Editor                        [─][□][×]  │
├────────────────────────────────────────────────────┤
│ [New] [Open] [Paste] [Clear] │ [Copy] [Save] [Reload] │
├─────────────────────┬──────────────────────────────┤
│                     │ Component Settings           │
│                     ├──────────────────────────────┤
│                     │ Name: [PBS 1-inch     ]     │
│                     │ Type: [beamsplitter ▼]      │
│                     │ Object height: [25.4  ] mm   │
│                     │ Line length: 100.00 px       │
│                     │ → mm/px: 0.254 mm/px        │
│      IMAGE          │ → Image height: 254.00 mm    │
│      CANVAS         │                              │
│                     │ Interfaces (drag on canvas): │
│   [Colorful         │ ┌──────────────────────────┐│
│    lines on         │ │ Calibration line (BS)    ││
│    image]           │ └──────────────────────────┘│
│                     │ [Add] [Edit] [Delete] [Preset]│
│                     │                              │
│                     │ ─── Properties ───           │
│                     │ EFL (lens): [100.0  ] mm     │
│                     │ Split T (BS): [50.0  ] %     │
│                     │ Split R (BS): [50.0  ] %     │
│                     │ Cutoff λ: [550.0] nm         │
│                     │ ...                          │
│                     │                              │
│                     │ ─────────────────────────    │
│                     │ Library                      │
│                     │ ┌──────────────────────────┐│
│                     │ │ [📷] PBS 1"              ││
│                     │ │ [📷] Lens 50mm          ││
│                     │ │ [📷] Mirror 2"           ││
│                     │ └──────────────────────────┘│
└─────────────────────┴──────────────────────────────┘
```

### Target UI Structure (Generalized)

```
┌────────────────────────────────────────────────────┐
│ Component Editor                        [─][□][×]  │
├────────────────────────────────────────────────────┤
│ [New] [Open] [Paste] [Clear] │ [Copy] [Save] [Reload] │
├─────────────────────┬──────────────────────────────┤
│                     │ Component Settings           │
│                     ├──────────────────────────────┤
│                     │ Name: [Optical System ]      │
│                     │ Object Height: [25.4  ] mm   │
│                     │                              │
│                     │ Interfaces                   │
│      IMAGE          │ ┌──────────────────────────┐│
│      CANVAS         │ │▼ 🔵 Interface 1: Lens    ││
│                     │ │  Type: [Lens ▼]          ││
│   [Colorful         │ │  x₁: [-12.7] mm  y₁: [0.0] mm  ││
│    lines on         │ │  x₂: [12.7 ] mm  y₂: [0.0] mm  ││
│    image]           │ │  ─ Lens Properties ─     ││
│                     │ │  EFL: [100.0] mm         ││
│  Multiple lines     │ └──────────────────────────┘│
│  each with own      │ ┌──────────────────────────┐│
│  color and type     │ │▶ 🟢 Interface 2: BS      ││
│                     │ └──────────────────────────┘│
│                     │ ┌──────────────────────────┐│
│                     │ │▶ 🔵 Interface 3: Ref.    ││
│                     │ └──────────────────────────┘│
│                     │                              │
│                     │ [Add Interface ▼]            │
│                     │  ├─ Lens                     │
│                     │  ├─ Mirror                   │
│                     │  ├─ Beam Splitter            │
│                     │  ├─ Dichroic                 │
│                     │  └─ Refractive Interface     │
│                     │                              │
│                     │ ─────────────────────────    │
│                     │ Library                      │
│                     │ ┌──────────────────────────┐│
│                     │ │ [📷] Multi-element       ││
│                     │ │      (3 interfaces)      ││
│                     │ │ [📷] Simple Lens         ││
│                     │ │      (1 interface)       ││
│                     │ └──────────────────────────┘│
└─────────────────────┴──────────────────────────────┘
```

## Detailed Interface Widget Mockups

### Collapsed Interface Widget

```
┌────────────────────────────────────────┐
│ ▶ 🔵 Interface 1: Input Lens           │
│   Lens • 100mm EFL • at (0.0, 0.0) mm  │
└────────────────────────────────────────┘
```

### Expanded Interface Widget - Lens

```
┌────────────────────────────────────────┐
│ ▼ 🔵 Interface 1: Input Lens   [×]     │
├────────────────────────────────────────┤
│ Element Type: [Lens               ▼]   │
│                                        │
│ ┌── Geometry ───────────────────────┐ │
│ │ Point 1 (Start)                   │ │
│ │   x₁: [-12.70] mm  (456.2 px)     │ │
│ │   y₁: [  0.00] mm  (500.0 px)     │ │
│ │ Point 2 (End)                     │ │
│ │   x₂: [ 12.70] mm  (543.8 px)     │ │
│ │   y₂: [  0.00] mm  (500.0 px)     │ │
│ │                                   │ │
│ │ Length: 25.40 mm  [🎯 Snap Horizontal] │ │
│ └───────────────────────────────────┘ │
│                                        │
│ ┌── Lens Properties ────────────────┐ │
│ │ Effective Focal Length             │ │
│ │ EFL: [100.00] mm                   │ │
│ │                                   │ │
│ │ [🔬 Advanced Lens Properties...]   │ │
│ └───────────────────────────────────┘ │
└────────────────────────────────────────┘
```

### Expanded Interface Widget - Beam Splitter

```
┌────────────────────────────────────────┐
│ ▼ 🟢 Interface 2: BS Coating   [×]     │
├────────────────────────────────────────┤
│ Element Type: [Beam Splitter      ▼]   │
│                                        │
│ ┌── Geometry ───────────────────────┐ │
│ │ Point 1: (-10.0, -10.0) mm        │ │
│ │ Point 2: ( 10.0,  10.0) mm        │ │
│ │ Length: 28.28 mm  Angle: 45.0°   │ │
│ └───────────────────────────────────┘ │
│                                        │
│ ┌── Beam Splitter Properties ───────┐ │
│ │ Split Ratio                        │ │
│ │   Transmission: [50.0] %           │ │
│ │   Reflection:   [50.0] %           │ │
│ │                                   │ │
│ │ ☐ Polarizing (PBS)                │ │
│ │   PBS Axis: [  0.0] °  [disabled] │ │
│ │                                   │ │
│ │ [🔬 Advanced BS Properties...]     │ │
│ └───────────────────────────────────┘ │
└────────────────────────────────────────┘
```

### Expanded Interface Widget - Refractive Interface

```
┌────────────────────────────────────────┐
│ ▼ 🔵 Interface 3: Glass Surface [×]    │
├────────────────────────────────────────┤
│ Element Type: [Refractive Interface ▼]  │
│                                        │
│ ┌── Geometry ───────────────────────┐ │
│ │ Point 1: (-5.0, 10.0) mm          │ │
│ │ Point 2: ( 5.0, 10.0) mm          │ │
│ │ Length: 10.00 mm  Angle: 0.0°     │ │
│ └───────────────────────────────────┘ │
│                                        │
│ ┌── Refractive Properties ──────────┐ │
│ │ Incident Medium                    │ │
│ │   n₁: [1.0000] (Air)  [Presets ▼] │ │
│ │                                   │ │
│ │ Transmitted Medium                 │ │
│ │   n₂: [1.5170] (BK7)  [Presets ▼] │ │
│ │                                   │ │
│ │ Interface Angle: 0.0° (horizontal) │ │
│ │ Critical Angle: 40.8°             │ │
│ │                                   │ │
│ │ [🔬 Advanced Refraction...]        │ │
│ └───────────────────────────────────┘ │
└────────────────────────────────────────┘
```

### Expanded Interface Widget - Dichroic

```
┌────────────────────────────────────────┐
│ ▼ 🟣 Interface 4: Dichroic Filter [×]  │
├────────────────────────────────────────┤
│ Element Type: [Dichroic            ▼]  │
│                                        │
│ ┌── Geometry ───────────────────────┐ │
│ │ Point 1: (0.0, -15.0) mm          │ │
│ │ Point 2: (0.0,  15.0) mm          │ │
│ │ Length: 30.00 mm  Angle: 90.0°    │ │
│ └───────────────────────────────────┘ │
│                                        │
│ ┌── Dichroic Properties ────────────┐ │
│ │ Cutoff Wavelength                  │ │
│ │   λ₀: [550.0] nm                   │ │
│ │                                   │ │
│ │ Transition Width                   │ │
│ │   Δλ: [50.0] nm                    │ │
│ │                                   │ │
│ │ Pass Type: ⦿ Longpass  ○ Shortpass│ │
│ │                                   │ │
│ │ ┌─ Transmission Curve ──────────┐ │ │
│ │ │ 100% │         ╱────────      │ │ │
│ │ │      │        ╱               │ │ │
│ │ │   0% │────────                │ │ │
│ │ │      └────────────────        │ │ │
│ │ │      500  550  600 nm         │ │ │
│ │ └───────────────────────────────┘ │ │
│ │                                   │ │
│ │ [🔬 Advanced Dichroic...]         │ │
│ └───────────────────────────────────┘ │
└────────────────────────────────────────┘
```

### Expanded Interface Widget - Mirror

```
┌────────────────────────────────────────┐
│ ▼ 🟠 Interface 5: Mirror       [×]     │
├────────────────────────────────────────┤
│ Element Type: [Mirror              ▼]  │
│                                        │
│ ┌── Geometry ───────────────────────┐ │
│ │ Point 1: (20.0, -12.7) mm         │ │
│ │ Point 2: (20.0,  12.7) mm         │ │
│ │ Length: 25.40 mm  Angle: 90.0°    │ │
│ └───────────────────────────────────┘ │
│                                        │
│ ┌── Mirror Properties ──────────────┐ │
│ │ Reflectivity: [99.0] %             │ │
│ │                                   │ │
│ │ ☐ Curved (radius of curvature)    │ │
│ │   R: [  ∞  ] mm  [disabled]       │ │
│ │                                   │ │
│ │ [🔬 Advanced Mirror...]            │ │
│ └───────────────────────────────────┘ │
└────────────────────────────────────────┘
```

## Add Interface Menu

```
┌────────────────────────────┐
│ [Add Interface ▼]          │
└────┬───────────────────────┘
     │
     ├─────────────────────────────────┐
     │ 🔵 Lens                         │  ← Adds thin lens interface
     │ 🟠 Mirror                       │  ← Adds reflective interface
     │ 🟢 Beam Splitter                │  ← Adds partial reflection
     │ 🟣 Dichroic                     │  ← Adds wavelength-selective
     │ 🔵 Refractive Interface         │  ← Adds glass-air boundary
     ├─────────────────────────────────┤
     │ 📦 Presets                   ▶  │  ── ┐
     └─────────────────────────────────┘     │
                                             │
         ┌───────────────────────────────────┘
         │
         ├─────────────────────────────────┐
         │ BS Cube (5 interfaces)          │
         │ PBS Cube (5 interfaces)         │
         │ Right-Angle Prism (3 interfaces)│
         │ Penta Prism (5 interfaces)      │
         │ Custom...                       │
         └─────────────────────────────────┘
```

## Interface List Context Menu

```
Right-click on interface:
┌─────────────────────────────┐
│ ✎ Edit Properties           │
│ 📋 Duplicate                │
│ ↑ Move Up                   │
│ ↓ Move Down                 │
│ ─────────────────────────   │
│ 🔒 Lock (prevent dragging)  │
│ 👁 Hide (keep in data)       │
│ ─────────────────────────   │
│ 🗑 Delete                    │
└─────────────────────────────┘
```

## Workflow Examples

### Example 1: Creating a Simple Lens

1. **Create new component**
   - Click `[New]`
   - Name: "Lens 1-inch f=100mm"
   - Object Height: 25.4 mm

2. **Add lens interface**
   - Click `[Add Interface ▼]` → "Lens"
   - Interface appears on canvas (horizontal line)
   - Drag endpoints to match lens in image
   - Set EFL: 100.0 mm

3. **Save**
   - Click `[Save]`
   - Component added to library

### Example 2: Creating a PBS Cube

1. **Create new component**
   - Click `[New]`
   - Name: "PBS Cube 1-inch"
   - Object Height: 25.4 mm

2. **Use preset**
   - Click `[Add Interface ▼]` → "Presets" → "PBS Cube"
   - 5 interfaces created automatically:
     - 4 refractive interfaces (blue) - cube faces
     - 1 beam splitter interface (purple) - diagonal coating

3. **Adjust if needed**
   - Drag endpoints to match image
   - Expand PBS interface, adjust split ratio
   - Expand PBS interface, set transmission axis

4. **Save**
   - Component ready for use in optical system

### Example 3: Creating Custom Multi-Element

1. **Create new component**
   - Name: "Custom Multi-Element"
   - Object Height: 50.0 mm

2. **Add interfaces one by one**
   - Add refractive interface (air → glass entrance)
   - Add lens interface (focusing element)
   - Add refractive interface (glass → air exit)
   - Add mirror interface (back reflector)

3. **Position on canvas**
   - Drag each interface to correct position
   - Verify coordinates in mm

4. **Set properties**
   - Expand each interface
   - Set refractive indices, EFL, etc.

5. **Save**

## UI Improvements from Current Design

### ✅ Removed Complexity
- No more component type selector (type is per-interface)
- No more scattered type-specific fields
- No more modal edit dialogs
- Cleaner, more focused layout

### ✅ Added Clarity
- Each interface is self-contained
- Visual color coding matches interface type
- Collapsible widgets reduce visual clutter
- Coordinates in physically meaningful units (mm)

### ✅ Enhanced Flexibility
- Mix interface types in one component
- Each interface fully customizable
- Preset system for common configurations
- Inline editing without modal dialogs

### ✅ Better Workflow
- Progressive disclosure (expand only what you need)
- Direct manipulation (drag on canvas)
- Immediate feedback (color changes, coordinate updates)
- Clear visual hierarchy

## Responsive Design Considerations

### For Wide Screens (>1400px)
```
┌──────────────────────────────────────────────────────────┐
│                                                          │
│  IMAGE CANVAS (larger)    │   INTERFACE PANEL (wider)   │
│                          │                             │
└──────────────────────────────────────────────────────────┘
```

### For Narrow Screens (<1000px)
```
┌──────────────────────────┐
│   INTERFACE PANEL        │
│   (stacked on left)      │
│                          │
├──────────────────────────┤
│                          │
│   IMAGE CANVAS           │
│   (bottom, full width)   │
│                          │
└──────────────────────────┘
```

### For Very Small Screens (<800px)
- Tabs: "Canvas" | "Interfaces" | "Library"
- Switch between views
- Prevent cramped UI

## Accessibility

- **Keyboard navigation**: Tab through interfaces, Enter to expand/collapse
- **Screen reader support**: Proper labels, ARIA attributes
- **High contrast mode**: Distinct colors, thick lines
- **Font scaling**: Responsive to system font size settings

## Color Coding Reference

| Interface Type | Color | Emoji | RGB |
|----------------|-------|-------|-----|
| Lens | Cyan | 🔵 | (0, 180, 180) |
| Mirror | Orange | 🟠 | (255, 140, 0) |
| Beam Splitter | Green | 🟢 | (0, 150, 120) |
| PBS | Purple | 🟣 | (150, 0, 150) |
| Dichroic | Magenta | 🟣 | (255, 0, 255) |
| Refractive | Blue | 🔵 | (100, 100, 255) |

## Animation and Feedback

- **Expand/collapse**: Smooth 150ms ease animation
- **Drag endpoint**: Cursor changes to move cursor
- **Hover interface**: Line thickness increases slightly
- **Select interface**: Line highlights, list item highlights
- **Add interface**: Fade in animation
- **Delete interface**: Fade out + slide animation
- **Property change**: Color updates immediately on canvas


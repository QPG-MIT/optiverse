---
layout: default
title: Refractive Index Labels
nav_order: 12
parent: User Guides
---

# Refractive Index Labels in Component Editor

## Overview

The component editor now displays **refractive index labels** at the endpoints of refractive interfaces. This visual enhancement helps you identify which side of an interface has which refractive index (n₁ and n₂), making it easier to correctly configure optical components.

## What's New

### Visual Labels

When you draw or edit a refractive interface in the component editor, you'll now see:

- **n₁ label** near the first endpoint (start point of the line)
- **n₂ label** near the second endpoint (end point of the line)

Each label shows:
- The index identifier (n₁ or n₂) with proper Unicode subscripts
- The numerical value to 3 decimal places (e.g., "1.517")
- Format: `n₁=1.000` and `n₂=1.517`

### Label Appearance

The labels are designed for clarity and readability:

- **Position**: Perpendicular to the interface line, offset from endpoints
- **Background**: Semi-transparent white background for readability
- **Border**: Colored border matching the interface line color
- **Font**: Bold, 9-point text for easy reading
- **Visibility**: Always visible (unless the line is dimmed)

## Usage

### Creating Refractive Interfaces

1. **Open Component Editor**
   - From main menu: File → Component Editor
   - Or click the Component Editor toolbar button

2. **Add a Refractive Object**
   - Load an image of your optical component
   - Select "refractive_object" from the Type dropdown (if not already)
   - Click "Add Interface" button

3. **Configure the Interface**
   - Set **n1**: Refractive index on the incident side (first endpoint)
   - Set **n2**: Refractive index on the transmitted side (second endpoint)
   - Position the line endpoints to match the physical interface

4. **Visual Feedback**
   - The canvas immediately shows the line with n₁ and n₂ labels
   - Labels update automatically when you edit the refractive indices
   - Labels stay positioned correctly when you drag endpoints

### Understanding the Labels

The convention for refractive interfaces:

When you draw a line from **p1** to **p2**, imagine standing at p1 and looking toward p2:
- **n₁** is the medium on your **RIGHT** side
- **n₂** is the medium on your **LEFT** side

Technically, the normal vector points 90° counterclockwise from the reversed direction (p2→p1), which determines:
- **n₁** = medium on the side the normal points toward
- **n₂** = medium on the side the normal points away from

This matches the physical interpretation where:
- **n₁** is typically the "incident" or "incoming" medium
- **n₂** is typically the "transmitted" or "outgoing" medium

### Example: Glass Plate

For a parallel-sided glass plate in air with horizontal light:

```
Entry Surface (vertical line, drawn top to bottom):
  p1 = (x, y_top), p2 = (x, y_bottom)
  Looking top→bottom: right side is air, left side is glass
  n₁ = 1.000 (air, right/incident side)
  n₂ = 1.517 (glass, left/transmitted side)

Exit Surface (vertical line, drawn top to bottom):
  p1 = (x, y_top), p2 = (x, y_bottom)  
  Looking top→bottom: right side is glass, left side is air
  n₁ = 1.517 (glass, right/incident side)
  n₂ = 1.000 (air, left/transmitted side)
```

The labels make it immediately clear which side is which!

## When Labels Are Shown

Labels are displayed when:
- ✓ The interface is a `refractive_interface` type
- ✓ The indices are different (|n₁ - n₂| > 0.01)
- ✓ The line is not dimmed (drag-locked on a different interface)

Labels are **not** shown when:
- ✗ Both indices are the same (no refraction occurs)
- ✗ The interface is dimmed (another interface is being edited)
- ✗ The interface type is not `refractive_interface`

## Technical Details

### Implementation

- **File**: `src/optiverse/objects/views/multi_line_canvas.py`
- **Method**: `_draw_refractive_index_labels()`
- **Integration**: Called automatically during line drawing in `_draw_line()`

### Label Positioning

Labels are positioned using a perpendicular offset algorithm:

1. Calculate the line direction vector
2. Compute the perpendicular (normal) vector
3. Offset each label 15 pixels perpendicular to the line
4. Center the text at the offset position

This ensures labels don't overlap the line itself and remain readable at any angle.

### Performance

- Labels are rendered as part of the normal paint cycle
- No performance impact on canvas responsiveness
- Text rendering is hardware-accelerated via Qt's QPainter

## Common Refractive Indices

For reference, here are common optical materials:

| Material | Refractive Index (at 589nm) |
|----------|---------------------------|
| Vacuum | 1.0000 |
| Air | 1.000293 |
| Water | 1.333 |
| Fused Silica | 1.458 |
| BK7 Glass | 1.517 |
| Sapphire | 1.77 |
| SF11 Glass | 1.785 |

## Tips and Best Practices

### Tip 1: Check Your Convention

When creating an interface:
- Draw the line from p1 to p2
- Stand at p1 and look toward p2
- n₁ is on your RIGHT, n₂ is on your LEFT
- For light going left-to-right: draw vertical line top-to-bottom, put air (n₁) on right
- The labels will help you verify this visually

### Tip 2: Use Presets

The interface editor includes common material presets:
- Air (1.000293)
- BK7 Glass (1.517)
- Fused Silica (1.458)
- And more...

Select these from the dropdown instead of typing values manually.

### Tip 3: Zoom In for Precision

If labels overlap or are hard to read:
- The component editor canvas scales automatically
- Resize the window to get a larger view
- Labels scale with the canvas for consistent readability

## Troubleshooting

### Labels Not Appearing?

Check:
1. Is the interface type set to `refractive_interface`?
2. Are n₁ and n₂ different values (difference > 0.01)?
3. Is the interface visible on the canvas?
4. Is another interface drag-locked (dimming others)?

### Labels Overlapping?

If multiple interfaces are close together:
- Select one interface at a time to edit
- Use drag-lock mode to focus on a single interface
- Reposition interfaces to have better spacing

### Can't Read Label Text?

- Increase the window size for better visibility
- The font is bold 9-point for readability
- Labels have white backgrounds for contrast
- Labels should be readable at any zoom level

## Demo Example

Try the demo script to see the feature in action:

```bash
python examples/refractive_index_labels_demo.py
```

This opens the component editor with pre-configured refractive interfaces showing the label feature.

## Related Documentation

- [Component Editor Guide](COMPONENT_EDITOR_REFRACTIVE_GUIDE.md)
- [Visual Interface Editor](VISUAL_INTERFACE_EDITOR_COMPLETE.md)
- [Interface Types](../src/optiverse/core/interface_types.py)

## Future Enhancements

Possible future improvements:
- Toggle labels on/off via preferences
- Adjustable label font size
- Show additional information (angle, Brewster angle, etc.)
- Color-code labels by material type
- Show critical angle warnings for total internal reflection

---

**Version**: 1.0  
**Last Updated**: October 2025  
**Author**: Optiverse Development Team


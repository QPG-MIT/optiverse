---
layout: default
title: Interface Color Guide
nav_order: 11
parent: User Guides
---

# Optical Interface Color Guide

## Component Editor Visual System

All optical interfaces are now displayed as colored lines in the component editor. The color indicates the interface type:

## Interface Colors

### Refractive Objects

| Color | RGB | Interface Type | Description |
|-------|-----|----------------|-------------|
| 🔵 **Blue** | (100, 100, 255) | Refractive Interface | Normal glass-air boundary (n1 ≠ n2) |
| 🟢 **Green** | (0, 150, 120) | Beam Splitter | Partially reflecting coating |
| 🟣 **Purple** | (150, 0, 150) | PBS | Polarizing beam splitter |
| ⚪ **Gray** | (150, 150, 150) | Same Index | n1 = n2 (boundary with no refraction) |

### Simple Components (Calibration Lines)

| Color | RGB | Component Type |
|-------|-----|----------------|
| 🔵 **Cyan** | (0, 180, 180) | Lens |
| 🟠 **Orange** | (255, 140, 0) | Mirror |
| 🟢 **Green** | (0, 150, 120) | Beam Splitter |
| 🟣 **Magenta** | (255, 0, 255) | Dichroic Filter |

## Visual Examples

### Beam Splitter Cube (BS Cube Preset)

When you create a BS cube preset, you'll see:
- 4 blue lines forming the square perimeter (glass-air surfaces)
- 1 green diagonal line (beam splitter coating at 45°)

```
     Top (blue)
    ╱─────────╲
   ╱  ╱green╲  ╲ Right (blue)
  ╱  ╱  BS   ╲  ╲
 ╱  ╱  45°    ╲  ╲
╱──╱───────────╲──╲
Left (blue)  Bottom (blue)
```

### PBS Cube

Same geometry as BS cube, but:
- 4 blue lines for glass-air surfaces
- 1 **purple** diagonal line for the polarizing coating

### Custom Refractive Object

Example: Prism with 3 surfaces
- 3 blue lines at angles forming a triangular prism
- Each line can be dragged independently to adjust geometry

## Color Changes Dynamically

When you edit an interface's properties:
- Change `is_beam_splitter` to `True` → line turns green
- Enable `is_polarizing` → line turns purple
- Change `n1` to match `n2` → line turns gray
- Reset to normal refraction → line turns blue

## Usage Tips

1. **Hover over endpoints** to see crosshair cursor
2. **Click and drag** any endpoint to reposition
3. **Click on a line** to select it (highlighted in list)
4. **Select in list** to highlight on canvas
5. **Color indicates type** at a glance

## Accessibility Note

For users who have difficulty distinguishing colors, the interface list provides text descriptions:
- "Interface 1: BS n=1.000→1.520 T/R=50/50" (green line)
- "Interface 2: n=1.000→1.520" (blue line)
- "Interface 3: PBS n=1.520→1.520 T/R=0/100" (purple line)

You can always double-click an interface in the list to see its full properties, regardless of color.


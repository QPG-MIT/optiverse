# Pipet Tool - Quick Start Guide

## 🎯 What It Does
Click on any ray to see its:
- **Position** (X, Y coordinates)
- **Intensity** (0-100%)
- **Wavelength** (if specified)
- **Polarization state** (Jones vector, Stokes parameters, angle)

## 🚀 How to Use

### Step 1: Activate
Click the **eyedropper icon** 🔬 in the toolbar (or Tools → Pipet)

### Step 2: Click
Click on any ray in your optical setup

### Step 3: View Info
A dialog shows all ray properties at that position

### Step 4: Deactivate
Click the eyedropper icon again to return to normal mode

## 💡 Tips

- **Zoom independent**: Works at any zoom level
- **15-pixel tolerance**: Don't need to click exactly on the ray
- **Multiple rays**: Close dialog, click another ray to compare
- **Mode switching**: Auto-disables when placing rulers

## 📊 What The Information Means

### Intensity
- **100%**: Full brightness
- **50%**: Half brightness (e.g., after 50/50 beamsplitter)
- **<2%**: Ray is terminated (too dim to continue)

### Stokes Parameters
- **I**: Total intensity (always positive)
- **Q > 0**: More horizontal polarization
- **Q < 0**: More vertical polarization
- **U > 0**: More +45° polarization
- **U < 0**: More -45° polarization
- **V > 0**: Right circular polarization
- **V < 0**: Left circular polarization

### Polarization Angle
- **0°**: Horizontal linear
- **90°**: Vertical linear
- **45°**: Diagonal (+45°) linear
- **-45°**: Diagonal (-45°) linear

### Degree of Polarization
- **100%**: Pure polarization state (fully polarized)
- **50%**: Partially polarized
- **0%**: Unpolarized light

## 🧪 Example: Testing a QWP

1. Add horizontal polarized source
2. Add quarter-wave plate (QWP) at 45°
3. Enable pipet tool
4. Click ray **before** QWP:
   - Stokes: Q=1, U=0, V=0 (horizontal linear)
5. Click ray **after** QWP:
   - Stokes: Q=0, U=0, V=1 (right circular!)

## 🎓 Learning Tips

### Polarization States to Try

**Linear Horizontal**:
- Source: Horizontal polarization
- After mirror: Still horizontal
- Jones: [1, 0]
- Stokes: Q=1, U=0, V=0

**Linear Vertical**:
- Source: Vertical polarization
- After mirror: Still vertical
- Jones: [0, 1]
- Stokes: Q=-1, U=0, V=0

**Linear +45°**:
- Source: +45° polarization
- Jones: [0.707, 0.707]
- Stokes: Q=0, U=1, V=0

**Circular**:
- Pass horizontal through QWP at 45°
- Jones: [0.707, 0.707i]
- Stokes: Q=0, U=0, V=1

**Unpolarized** (mixed):
- Source: Random polarization
- Degree of polarization: 0%

### Intensity Loss Examples

**50/50 Beamsplitter**:
- Input: 100%
- Transmitted: 50%
- Reflected: 50%

**Polarizing Beamsplitter (PBS)**:
- Horizontal in: 100% transmitted, 0% reflected
- Vertical in: 0% transmitted, 100% reflected
- +45° in: 50% each (equal H/V components)

**Multiple Mirrors**:
- Each bounce: ~100% intensity (ideal mirrors)
- 3 bounces: Still ~100%

**Fresnel Reflection**:
- Glass interface: ~4% reflected, ~96% transmitted
- Multiple interfaces: Multiply losses

## 🐛 Troubleshooting

**"No Ray Found"**:
- Click closer to a ray
- Zoom in for better precision
- Make sure rays are visible (enable auto-trace)

**Polarization shows zeros**:
- Source might have no polarization specified
- Check source polarization type setting

**Intensity looks wrong**:
- Check source ray_length_mm (rays fade over distance)
- Verify beamsplitter split ratios
- Look for multiple bounces (intensity decreases)

## 🎨 Icon Note
Current eyedropper icon is a placeholder. Feel free to replace `src/optiverse/ui/icons/pipet.png` with a custom design!

## 📚 More Info
See `docs/PIPET_TOOL.md` for complete technical documentation.

---

**Have fun exploring your optical setups! 🔬✨**


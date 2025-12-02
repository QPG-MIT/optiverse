# Optiverse Documentation

Welcome to the Optiverse documentation! This directory contains comprehensive guides for users and developers.

## 📚 Documentation Index

### 🚀 Getting Started

- **[macOS Installation Guide](MACOS_SETUP.md)**  
  Step-by-step instructions for setting up Optiverse on macOS with native app bundle support.

### 👥 User Guides

#### Component Editor
- **[Component Editor: Interface Color Guide](INTERFACE_COLOR_GUIDE.md)**  
  Learn how optical interfaces are color-coded in the component editor for easy identification.

- **[Component Editor: Refractive Index Labels](REFRACTIVE_INDEX_LABELS.md)**  
  Understanding how refractive index labels (n₁, n₂) are displayed and used in the component editor.

- **[Component Editor: Ruler Visual Guide](RULER_VISUAL_GUIDE.md)**  
  Visual guide to using rulers and coordinate systems in the component editor.

#### Features
- **[Zemax Import Guide](ZEMAX_IMPORT_UI_GUIDE.md)**  
  Complete guide to importing optical designs from Zemax (.zmx) files into Optiverse.

- **[Collaboration Guide](COLLABORATION.md)**  
  Real-time collaborative editing with multiple users via WebSocket connections.

- **[Inspect Tool](INSPECT_TOOL.md)**  
  How to use the inspect (eyedropper) tool to view detailed ray properties.

### 🔬 Physics & Optics

- **[Raytracing Physics](RAYTRACING_PHYSICS.md)** ⭐  
  **Comprehensive mathematical description** of raytracing algorithms, Snell's law, Fresnel equations, thin lens approximation, and optical interface structure. Includes detailed equations and derivations.

- **[Dichroic Mirrors and Wavelength System](DICHROIC_MIRRORS_AND_WAVELENGTH_SYSTEM.md)**  
  Implementation details for wavelength-dependent optical elements and color representation.

- **[Polarizing Interfaces](POLARIZING_INTERFACES.md)**  
  Architecture and usage of polarization-modifying optical elements (waveplates, polarizers).

- **[Waveplate Directionality](WAVEPLATE_DIRECTIONALITY.md)**  
  Physics implementation of directional waveplate behavior and polarization transformations.

### 🏗️ Architecture & Development

- **[Unified Interface System](UNIFIED_INTERFACE_SYSTEM.md)**  
  Design document explaining the unified interface-based component system.

- **[Testing Architecture](TESTING_ARCHITECTURE.md)**  
  Comprehensive guide to the testing framework, patterns, and best practices.

- **[Error Handling System](ERROR_HANDLING.md)**  
  Documentation for the global error handling system and error management patterns.

- **[Error Handling Quick Reference](ERROR_HANDLING_QUICK_REFERENCE.py)**  
  Quick reference code examples for using the error handling system.

- **[Logging System](LOGGING_SYSTEM.md)**  
  Guide to using the centralized logging system and log window.

### ⚡ Performance

- **[Parallel Raytracing](PARALLEL_RAYTRACING.md)**  
  Numba JIT compilation and threading optimizations for 4-8x raytracing speedup.

- **[macOS Trackpad Optimization](MAC_TRACKPAD_OPTIMIZATION.md)**  
  Mac-specific performance improvements and native trackpad gesture support.

## 📖 Quick Links

### For New Users
1. Start with [macOS Installation Guide](MACOS_SETUP.md) (if on Mac)
2. Learn about [Component Editor features](INTERFACE_COLOR_GUIDE.md)
3. Try [importing a Zemax file](ZEMAX_IMPORT_UI_GUIDE.md)

### For Developers
1. Read [Testing Architecture](TESTING_ARCHITECTURE.md) for testing guidelines
2. Understand [Unified Interface System](UNIFIED_INTERFACE_SYSTEM.md) architecture
3. Review [Error Handling](ERROR_HANDLING.md) for error management patterns

### For Optical Engineers
1. Explore [Polarizing Interfaces](POLARIZING_INTERFACES.md) for polarization optics
2. Understand [Waveplate Directionality](WAVEPLATE_DIRECTIONALITY.md) physics
3. Learn about [Dichroic Mirrors](DICHROIC_MIRRORS_AND_WAVELENGTH_SYSTEM.md) and wavelength systems

## 🔍 Finding Documentation

### By Topic

**Installation & Setup**
- macOS: [MACOS_SETUP.md](MACOS_SETUP.md)

**Component Editor**
- [INTERFACE_COLOR_GUIDE.md](INTERFACE_COLOR_GUIDE.md)
- [REFRACTIVE_INDEX_LABELS.md](REFRACTIVE_INDEX_LABELS.md)
- [RULER_VISUAL_GUIDE.md](RULER_VISUAL_GUIDE.md)

**Import/Export**
- [ZEMAX_IMPORT_UI_GUIDE.md](ZEMAX_IMPORT_UI_GUIDE.md)

**Collaboration**
- [COLLABORATION.md](COLLABORATION.md)

**Physics & Optics**
- [DICHROIC_MIRRORS_AND_WAVELENGTH_SYSTEM.md](DICHROIC_MIRRORS_AND_WAVELENGTH_SYSTEM.md)
- [POLARIZING_INTERFACES.md](POLARIZING_INTERFACES.md)
- [WAVEPLATE_DIRECTIONALITY.md](WAVEPLATE_DIRECTIONALITY.md)

**Development**
- [TESTING_ARCHITECTURE.md](TESTING_ARCHITECTURE.md)
- [UNIFIED_INTERFACE_SYSTEM.md](UNIFIED_INTERFACE_SYSTEM.md)
- [ERROR_HANDLING.md](ERROR_HANDLING.md)
- [LOGGING_SYSTEM.md](LOGGING_SYSTEM.md)

**Performance**
- [PARALLEL_RAYTRACING.md](PARALLEL_RAYTRACING.md)
- [MAC_TRACKPAD_OPTIMIZATION.md](MAC_TRACKPAD_OPTIMIZATION.md)

## 📝 Contributing to Documentation

When adding new documentation:

1. **User Guides**: Focus on step-by-step instructions with examples
2. **Architecture Docs**: Explain design decisions and system structure
3. **API Docs**: Include code examples and usage patterns
4. **Update this index**: Add new files to the appropriate section above

## 🔗 External Resources

- [Main README](../README.md) - Project overview and quick start
- [GitHub Repository](https://github.com/QPG-MIT/optiverse) - Source code and issues
- [Examples](../examples/) - Example assemblies and demos

---

*Last updated: Documentation organized and cleaned up for GitHub Pages*


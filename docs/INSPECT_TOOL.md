# Inspect Tool Implementation

## Overview
The inspect (eyedropper) tool allows users to click on any ray in the optical system and view detailed information about that ray's properties at the clicked position.

## Features

### 1. Tool Activation
- **Location**: Available in both the toolbar and Tools menu
- **Icon**: Eyedropper icon (dummy placeholder for now)
- **Toggle**: Click once to activate, click again to deactivate
- **Cursor**: Changes to crosshair when active

### 2. Information Displayed
When clicking on a ray, the tool displays:

#### Position
- X and Y coordinates in millimeters (scene coordinates)

#### Intensity
- Current ray intensity as a percentage (0-100%)
- Derived from the ray's alpha channel

#### Wavelength
- Ray wavelength in nanometers (if specified)
- Shows "Not specified" for non-wavelength-specific rays

#### Polarization State
When polarization information is available:

**Jones Vector**: Complex electric field components [Ex, Ey]

**Stokes Parameters**:
- I: Total intensity
- Q: Horizontal/vertical polarization difference
- U: Diagonal polarization difference  
- V: Circular polarization

**Derived Properties**:
- Degree of Polarization: 0-100%
- Linear Polarization Angle: -90° to +90°

## Usage

1. **Activate the tool**: Click the inspect icon in the toolbar or select Tools → Inspect
2. **Click on a ray**: Click anywhere near a ray path
3. **View information**: A dialog will display all ray properties at that location
4. **Close dialog**: Click "Close" or press Escape
5. **Deactivate**: Click the inspect icon again to return to normal mode

## Technical Details

### Click Detection
- **Tolerance**: 15 pixels (zoom-independent)
- **Algorithm**: Finds nearest ray point to click within tolerance
- **Zoom-aware**: Tolerance scales with view zoom level for consistent UX

### Data Storage
- Each `QGraphicsPathItem` ray has corresponding `RayPath` data stored
- `ray_items` list: Graphics items for rendering
- `ray_data` list: Physics data (polarization, intensity, wavelength)

### Integration
- Automatically disabled when entering ruler placement mode
- Event filter in `MainWindow` handles click events
- Works with all ray types (primary, reflected, transmitted, refracted)

## Code Structure

### Main Components
1. `_build_actions()`: Creates inspect action
2. `_build_toolbar()`: Adds inspect button to toolbar
3. `_build_menubar()`: Adds inspect to Tools menu
4. `_toggle_inspect()`: Handles tool activation/deactivation
5. `_handle_inspect_click()`: Finds clicked ray
6. `_show_ray_info_dialog()`: Displays ray information

### Data Flow
```
retrace() 
  → trace_rays() returns RayPath objects
  → Store in ray_data list alongside ray_items
  → inspect click → find nearest point in ray_data
  → display dialog with polarization/intensity
```

## Future Enhancements

### Icon
- Replace dummy icon with proper eyedropper icon
- Could be designed in vector format (SVG) for better scaling

### Display Improvements
- Add visual feedback: highlight clicked ray
- Show ray direction arrow
- Display ray history (which elements it passed through)

### Additional Information
- Show which optical element the ray last interacted with
- Display ray splitting history for beamsplitter rays
- Show refractive index if inside a refractive object

### Export
- Add "Copy to Clipboard" button
- Export ray information to CSV
- Plot polarization state on Poincaré sphere

## Testing

To test the inspect tool:

1. Launch the application
2. Add a light source
3. Add some optical elements (mirrors, beamsplitters, waveplates)
4. Enable auto-trace to see rays
5. Click the inspect tool in the toolbar
6. Click on various rays to see their properties

### Test Cases
- ✓ Click on primary ray from source
- ✓ Click on reflected ray from mirror
- ✓ Click on transmitted/reflected rays from beamsplitter
- ✓ Click on polarization-modified ray after waveplate
- ✓ Click on refracted ray through lens
- ✓ Verify zoom-independent click tolerance
- ✓ Verify tool deactivates when starting ruler placement


"""
Test script for the inspect tool feature.

This script creates a simple optical setup and demonstrates the inspect tool functionality.
To test manually:
1. Run this script
2. Click the inspect icon in the toolbar
3. Click on various rays to see their properties
4. Notice how polarization changes after passing through optical elements
"""

import sys
from PyQt6 import QtWidgets, QtCore

# Import the main application
from optiverse.ui.views.main_window import MainWindow
from optiverse.core.models import SourceParams, MirrorParams, WaveplateParams, BeamsplitterParams
from optiverse.objects import SourceItem, MirrorItem, WaveplateItem, BeamsplitterItem


def setup_test_scene(window: MainWindow):
    """Create a simple optical setup for testing the inspect tool."""
    
    # Clear any existing items
    window.scene.clear()
    window.ray_items.clear()
    window.ray_data.clear()
    
    # Add a source at the origin
    source_params = SourceParams(
        x_mm=0,
        y_mm=0,
        angle_deg=0,
        n_rays=5,
        size_mm=50,
        spread_deg=10,
        ray_length_mm=500,
        color_hex="#FF0000",
        wavelength_nm=633,  # Red laser
        polarization_type="horizontal"  # Horizontal polarization
    )
    source = SourceItem(source_params)
    window.scene.addItem(source)
    source.edited.connect(window._maybe_retrace)
    
    # Add a quarter-wave plate at x=150mm (vertical fast axis, will convert to circular)
    qwp_params = WaveplateParams(
        x_mm=150,
        y_mm=0,
        angle_deg=90,  # Vertical orientation
        object_height_mm=80,
        phase_shift_deg=90,  # QWP
        fast_axis_deg=90,  # Fast axis vertical
        name="QWP"
    )
    qwp = WaveplateItem(qwp_params)
    window.scene.addItem(qwp)
    qwp.edited.connect(window._maybe_retrace)
    
    # Add a polarizing beamsplitter at x=300mm, y=0
    pbs_params = BeamsplitterParams(
        x_mm=300,
        y_mm=0,
        angle_deg=45,  # 45 degrees
        object_height_mm=80,
        split_T=50,
        split_R=50,
        is_polarizing=True,
        pbs_transmission_axis_deg=0,  # Horizontal transmission
        name="PBS"
    )
    pbs = BeamsplitterItem(pbs_params)
    window.scene.addItem(pbs)
    pbs.edited.connect(window._maybe_retrace)
    
    # Add a mirror to catch the reflected beam
    mirror_params = MirrorParams(
        x_mm=300,
        y_mm=150,
        angle_deg=135,  # Angled to reflect back
        object_height_mm=80,
        name="Mirror"
    )
    mirror = MirrorItem(mirror_params)
    window.scene.addItem(mirror)
    mirror.edited.connect(window._maybe_retrace)
    
    # Retrace to show the rays
    window.retrace()
    
    # Fit the view to show all elements
    window.view.fitInView(
        window.scene.itemsBoundingRect(),
        QtCore.Qt.AspectRatioMode.KeepAspectRatio
    )
    
    # Show instructions
    QtWidgets.QMessageBox.information(
        window,
        "Inspect Tool Test",
        """Test Setup Complete!

This setup includes:
• Red laser source (633nm, horizontal polarization)
• Quarter-wave plate (converts to circular polarization)
• Polarizing beamsplitter (splits by polarization)
• Mirror (reflects one beam)

To test the inspect tool:
1. Click the inspect icon in the toolbar (eyedropper)
2. Click on rays at different positions:
   - Before QWP: horizontal linear polarization
   - After QWP: circular polarization (note Stokes V parameter)
   - After PBS: polarization-split beams
3. Notice how intensity and polarization change!
4. Click the inspect icon again to deactivate

Have fun exploring! 🔬"""
    )


def main():
    """Run the test application."""
    app = QtWidgets.QApplication(sys.argv)
    
    # Create main window
    window = MainWindow()
    window.show()
    
    # Setup test scene after a short delay to ensure window is ready
    QtCore.QTimer.singleShot(100, lambda: setup_test_scene(window))
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()


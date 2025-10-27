"""
Manual test script for magnetic snap feature.

Run this to test the magnetic snap feature manually:
    python test_magnetic_snap_manual.py

Expected behavior:
1. Window opens with two lenses
2. Drag the red lens near the blue lens
3. You should see magenta alignment guides appear
4. The red lens should snap to align with the blue lens
5. Toggle "Magnetic snap" in View menu to enable/disable
"""
import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from optiverse.ui.views.main_window import MainWindow
from optiverse.widgets.lens_item import LensItem
from optiverse.core.models import LensParams


def main():
    app = QApplication(sys.argv)
    
    window = MainWindow()
    window.setWindowTitle("Magnetic Snap Test - Drag red lens near blue lens")
    
    # Add a blue lens at (0, 0)
    lens1 = LensItem(LensParams(x_mm=0, y_mm=0, name="Blue Reference Lens"))
    window.scene.addItem(lens1)
    lens1._ready = True
    
    # Add a red lens at (200, 30) - nearby
    lens2 = LensItem(LensParams(x_mm=200, y_mm=30, name="Red Draggable Lens"))
    window.scene.addItem(lens2)
    lens2._ready = True
    
    # Add another lens at (0, 100)
    lens3 = LensItem(LensParams(x_mm=0, y_mm=100, name="Green Reference Lens"))
    window.scene.addItem(lens3)
    lens3._ready = True
    
    # Add lens at (200, 100)
    lens4 = LensItem(LensParams(x_mm=200, y_mm=100, name="Yellow Reference Lens"))
    window.scene.addItem(lens4)
    lens4._ready = True
    
    # Center view
    window.view.fitInView(window.scene.itemsBoundingRect(), Qt.AspectRatioMode.KeepAspectRatio)
    
    # Show info
    print("\n" + "="*70)
    print("MAGNETIC SNAP MANUAL TEST - FIXED VERSION")
    print("="*70)
    print("\nInstructions:")
    print("1. Drag any lens near another lens")
    print("2. Watch for MAGENTA alignment guide lines")
    print("3. Feel the lens LOCK into alignment - it should HOLD in place!")
    print("4. Try to drag it off the alignment - you should feel resistance")
    print("5. Drag it far away - it releases and follows the mouse again")
    print("6. Toggle 'Magnetic snap' in View menu to enable/disable")
    print("\nWhat You Should Feel:")
    print("  ✓ Strong 'magnetic pull' when near alignment")
    print("  ✓ Object LOCKS and won't move off the alignment line")
    print("  ✓ Can still move along the aligned axis (e.g., left-right)")
    print("  ✓ Smooth release when moved beyond ~10 pixels away")
    print("\nCurrent state: Magnetic snap is", 
          "ENABLED" if window.magnetic_snap else "DISABLED")
    print("="*70 + "\n")
    
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()


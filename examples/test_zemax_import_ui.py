"""
Test script for Zemax import UI integration.

This script opens the Component Editor and allows you to test the
Zemax import functionality.

Usage:
    python examples/test_zemax_import_ui.py
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from PyQt6 import QtWidgets
from optiverse.ui.views.component_editor_dialog import ComponentEditor
from optiverse.services.storage_service import StorageService


def main():
    """Open Component Editor for testing Zemax import."""
    app = QtWidgets.QApplication(sys.argv)
    
    # Create storage service
    storage = StorageService()
    
    # Create and show Component Editor
    editor = ComponentEditor(storage)
    editor.show()
    
    # Show instructions
    print("=" * 70)
    print("ZEMAX IMPORT UI TEST")
    print("=" * 70)
    print()
    print("Component Editor is now open.")
    print()
    print("To test Zemax import:")
    print("  1. Look for the 'Import Zemax…' button in the toolbar")
    print("  2. Click it to open file dialog")
    print("  3. Select a .zmx file (e.g., AC254-100-B-Zemax.zmx)")
    print("  4. Review the imported interfaces")
    print()
    print("The button should appear after 'Clear Points' in the toolbar.")
    print()
    print("Try importing: ~/Downloads/AC254-100-B-Zemax(ZMX).zmx")
    print()
    print("Press Ctrl+C in terminal or close window to exit.")
    print("=" * 70)
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()


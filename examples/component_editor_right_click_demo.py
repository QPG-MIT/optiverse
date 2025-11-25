"""
Demonstration of right-click context menu in Component Library.

This example shows how to:
1. Right-click on any component in the Component Library
2. Select "Edit Component" from the context menu
3. The Component Editor opens with that component loaded

Usage:
    python examples/component_editor_right_click_demo.py

Then in the application:
    - Look at the Component Library on the right side
    - Right-click on any component (e.g., "1 inch lens", "Standard Mirror")
    - Click "Edit Component" in the menu
    - The Component Editor opens with that component's data pre-loaded
"""

import sys
from PyQt6 import QtWidgets
from optiverse.ui.views.main_window import MainWindow


def main():
    app = QtWidgets.QApplication(sys.argv)

    # Create and show main window
    window = MainWindow()
    window.show()

    print("=" * 60)
    print("Component Library Right-Click Demo")
    print("=" * 60)
    print("\nInstructions:")
    print("1. Look at the 'Component Library' dock on the right side")
    print("2. RIGHT-CLICK on any component (not the category header)")
    print("3. Select 'Edit Component' from the context menu")
    print("4. The Component Editor will open with that component loaded")
    print("\nYou can then:")
    print("  - View the component's properties")
    print("  - Modify the component")
    print("  - Save changes back to the library")
    print("=" * 60)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()




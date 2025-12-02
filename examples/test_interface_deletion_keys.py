"""Manual test for Delete/Backspace keyboard shortcuts in InterfaceTreePanel.

Run this script to test the keyboard shortcuts:
1. Select an interface in the list
2. Press Delete or Backspace
3. Confirm the deletion dialog
4. The interface should be removed
"""

import sys

from PyQt6 import QtCore, QtWidgets

from optiverse.core.interface_definition import InterfaceDefinition
from optiverse.ui.widgets.interface_tree_panel import InterfaceTreePanel


def main():
    """Run the manual test."""
    app = QtWidgets.QApplication(sys.argv)

    # Create main window
    window = QtWidgets.QMainWindow()
    window.setWindowTitle("Interface Tree Panel - Delete/Backspace Test")
    window.resize(400, 600)

    # Create interface panel
    panel = InterfaceTreePanel()
    window.setCentralWidget(panel)

    # Add some test interfaces
    for i in range(5):
        interface = InterfaceDefinition(element_type="refractive_interface")
        interface.name = f"Test Interface {i + 1}"
        interface.n1 = 1.0
        interface.n2 = 1.5
        interface.x1_mm = -10.0
        interface.y1_mm = i * 2.0
        interface.x2_mm = 10.0
        interface.y2_mm = i * 2.0
        panel.add_interface(interface)

    # Add instructions
    instructions = QtWidgets.QLabel(
        "Instructions:\n"
        "1. Select one or more interfaces in the list\n"
        "2. Press Delete or Backspace key\n"
        "3. Confirm the deletion dialog\n"
        "4. The interface(s) should be removed\n\n"
        "You can also test:\n"
        "- Multi-selection (Cmd/Ctrl+Click)\n"
        "- Canceling deletion (click No)\n"
        "- No selection (nothing should happen)"
    )
    instructions.setWordWrap(True)
    instructions.setStyleSheet("padding: 10px; background-color: #f0f0f0;")

    # Create dock for instructions
    dock = QtWidgets.QDockWidget("Instructions", window)
    dock.setWidget(instructions)
    window.addDockWidget(QtCore.Qt.DockWidgetArea.BottomDockWidgetArea, dock)

    # Show window
    window.show()

    # Run application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

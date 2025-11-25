#!/usr/bin/env python3
"""
Demo: Refractive Index Labels in Component Editor

This example demonstrates the new feature that displays refractive index
labels (n₁ and n₂) at the endpoints of refractive interfaces in the
component editor.

The labels help you identify which side of the interface has which
refractive index, making it easier to correctly configure optical components.
"""

import sys
from PyQt6 import QtWidgets, QtGui, QtCore
from src.optiverse.services.storage_service import StorageService
from src.optiverse.ui.views.component_editor_dialog import ComponentEditor
from src.optiverse.core.interface_definition import InterfaceDefinition


def create_demo_image():
    """Create a simple diagram showing a glass plate."""
    pixmap = QtGui.QPixmap(600, 400)
    pixmap.fill(QtGui.QColor(250, 250, 250))

    painter = QtGui.QPainter(pixmap)

    # Draw grid
    painter.setPen(QtGui.QPen(QtGui.QColor(220, 220, 220), 1))
    for x in range(0, 600, 50):
        painter.drawLine(x, 0, x, 400)
    for y in range(0, 400, 50):
        painter.drawLine(0, y, 600, y)

    # Draw a glass block outline
    painter.setPen(QtGui.QPen(QtGui.QColor(100, 100, 255), 3))
    painter.setBrush(QtGui.QBrush(QtGui.QColor(200, 200, 255, 50)))
    painter.drawRect(150, 100, 300, 200)

    # Add labels
    painter.setPen(QtGui.QPen(QtCore.Qt.GlobalColor.black))
    font = QtGui.QFont()
    font.setPointSize(12)
    painter.setFont(font)
    painter.drawText(QtCore.QRect(0, 10, 600, 30),
                     QtCore.Qt.AlignmentFlag.AlignCenter,
                     "Glass Block Example")

    painter.drawText(20, 200, "Air")
    painter.drawText(480, 200, "Air")
    painter.drawText(280, 200, "Glass")

    painter.end()
    return pixmap


def main():
    """Run the demo."""
    app = QtWidgets.QApplication(sys.argv)

    # Create storage service
    storage = StorageService()

    # Create component editor
    editor = ComponentEditor(storage)
    editor.setWindowTitle("Demo: Refractive Index Labels")

    # Set up the demo image
    pixmap = create_demo_image()
    editor.canvas.set_pixmap(pixmap, None)

    # Define object height (for scaling)
    editor.object_height_mm.setValue(100.0)
    editor.name_edit.setText("Glass Block with Refractive Labels")

    # Create left interface (air → glass)
    left_interface = InterfaceDefinition(
        x1_mm=-75, y1_mm=-50,  # Top point
        x2_mm=-75, y2_mm=50,   # Bottom point
        element_type='refractive_interface',
        n1=1.0,      # Air (left side)
        n2=1.517,    # BK7 glass (right side)
        name="Entry Surface"
    )

    # Create right interface (glass → air)
    right_interface = InterfaceDefinition(
        x1_mm=75, y1_mm=-50,   # Top point
        x2_mm=75, y2_mm=50,    # Bottom point
        element_type='refractive_interface',
        n1=1.517,    # BK7 glass (left side)
        n2=1.0,      # Air (right side)
        name="Exit Surface"
    )

    # Create a diagonal interface for variety
    diagonal_interface = InterfaceDefinition(
        x1_mm=-50, y1_mm=-30,
        x2_mm=0, y2_mm=0,
        element_type='refractive_interface',
        n1=1.0,      # Air
        n2=1.785,    # SF11 glass (high index)
        name="Diagonal Surface"
    )

    # Add interfaces to the panel
    editor.interface_panel.add_interface(left_interface)
    editor.interface_panel.add_interface(right_interface)
    editor.interface_panel.add_interface(diagonal_interface)

    # Sync to canvas (this triggers the visual display with labels)
    editor._sync_interfaces_to_canvas()

    # Set informative status message
    editor.statusBar().showMessage(
        "✓ Refractive index labels (n₁ and n₂) are displayed at line endpoints. "
        "Drag endpoints to reposition interfaces."
    )

    # Add instructions in notes
    editor.notes.setPlainText(
        "INSTRUCTIONS:\n"
        "- Each blue line represents a refractive interface\n"
        "- n₁ label shows the refractive index on the first side (start point)\n"
        "- n₂ label shows the refractive index on the second side (end point)\n"
        "- Labels are positioned perpendicular to the interface line\n"
        "- Click on any interface in the list to select it\n"
        "- Drag line endpoints to reposition the interface"
    )

    # Show the editor
    editor.show()
    editor.resize(1200, 700)

    print("\n" + "="*70)
    print("Refractive Index Labels Demo")
    print("="*70)
    print("\nNew Feature:")
    print("  ✓ Refractive interfaces now show n₁ and n₂ labels at endpoints")
    print("  ✓ Labels help identify which side has which refractive index")
    print("  ✓ Labels are color-coded to match the interface line")
    print("\nWhat to Look For:")
    print("  • Left interface:  n₁=1.000 (air) → n₂=1.517 (glass)")
    print("  • Right interface: n₁=1.517 (glass) → n₂=1.000 (air)")
    print("  • Diagonal:        n₁=1.000 (air) → n₂=1.785 (SF11 glass)")
    print("\nInteraction:")
    print("  • Drag any endpoint to move the interface")
    print("  • Labels stay positioned relative to the line")
    print("  • Click 'Edit' to modify refractive indices")
    print("="*70 + "\n")

    sys.exit(app.exec())


if __name__ == '__main__':
    main()




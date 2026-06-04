"""
Interface Widget Components - Reusable widgets for the InterfaceTreePanel.

This module contains:
- InterfaceTreeWidget: Tree widget with delete key handling
- ColoredCircleLabel: Color indicator label
"""

from __future__ import annotations

from PyQt6 import QtCore, QtGui, QtWidgets


class InterfaceTreeWidget(QtWidgets.QTreeWidget):
    """Custom QTreeWidget that handles Delete/Backspace and F2 keys."""

    deleteKeyPressed = QtCore.pyqtSignal()
    renameKeyPressed = QtCore.pyqtSignal()

    def __init__(self, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)
        self._suppress_scroll = False

    def keyPressEvent(self, event: QtGui.QKeyEvent | None):
        """Override to handle Delete/Backspace and F2 keys."""
        if event is None:
            return
        if event.key() in (QtCore.Qt.Key.Key_Delete, QtCore.Qt.Key.Key_Backspace):
            if self.state() != QtWidgets.QAbstractItemView.State.EditingState:
                self.deleteKeyPressed.emit()
                event.accept()
                return

        # Check if F2 key is pressed (standard rename key)
        if event.key() == QtCore.Qt.Key.Key_F2:
            if self.state() != QtWidgets.QAbstractItemView.State.EditingState:
                self.renameKeyPressed.emit()
                event.accept()
                return

        # Pass to parent for all other keys or when editing
        super().keyPressEvent(event)

    def mouseDoubleClickEvent(self, event: QtGui.QMouseEvent | None) -> None:
        """Ignore tree double-click behavior to avoid scroll jumps.

        The interface panel embeds spin boxes, combo boxes, and checkboxes inside
        tree rows. Letting QTreeWidget process double-clicks can call scrollTo()
        while those child editors are receiving focus, which causes the component
        editor panel to jump. Expansion by double-click is disabled separately;
        F2 remains the explicit rename path.
        """
        if event is not None:
            event.accept()
        return

    def scrollTo(
        self,
        index: QtCore.QModelIndex,
        hint: QtWidgets.QAbstractItemView.ScrollHint = (
            QtWidgets.QAbstractItemView.ScrollHint.EnsureVisible
        ),
    ):
        """Override to prevent unwanted scrolling.

        Blocks scroll when:
        - An embedded widget (spinbox, checkbox, etc.) has focus
        - A programmatic selection change is in progress (_suppress_scroll)
        """
        if self._suppress_scroll:
            return
        focused = QtWidgets.QApplication.focusWidget()
        if focused is not None and focused is not self and self.isAncestorOf(focused):
            return
        super().scrollTo(index, hint)


class ColoredCircleLabel(QtWidgets.QLabel):
    """A small colored circle indicator."""

    def __init__(self, color: str, size: int = 12, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)
        self._color = color
        self._size = size
        self.setFixedSize(size, size)
        self._update_style()

    def _update_style(self) -> None:
        """Update the stylesheet for the circle."""
        self.setStyleSheet(
            f"QLabel {{ background-color: {self._color}; border-radius: {self._size // 2}px; }}"
        )

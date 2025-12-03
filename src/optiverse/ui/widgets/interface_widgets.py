"""
Interface Widget Components - Reusable widgets for the InterfaceTreePanel.

This module contains:
- InterfaceTreeWidget: Tree widget with delete key handling
- EditableLabel: Double-click-to-edit label widget
- ColoredCircleLabel: Color indicator label
"""

from __future__ import annotations

from PyQt6 import QtCore, QtGui, QtWidgets


class InterfaceTreeWidget(QtWidgets.QTreeWidget):
    """Custom QTreeWidget that handles Delete/Backspace and F2 keys."""

    deleteKeyPressed = QtCore.pyqtSignal()
    renameKeyPressed = QtCore.pyqtSignal()

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

    def scrollTo(
        self,
        index: QtCore.QModelIndex,
        hint: QtWidgets.QAbstractItemView.ScrollHint = (
            QtWidgets.QAbstractItemView.ScrollHint.EnsureVisible
        ),
    ):
        """Override to prevent scrolling when embedded widgets have focus.

        This prevents the tree from scrolling when the user is interacting
        with property widgets (EditableLabel, checkboxes, etc.) embedded in tree items.
        """
        # Check if focus is on an embedded widget inside this tree
        app = QtGui.QGuiApplication.instance()
        if app:
            focused = app.focusWidget()
            if focused is not None and focused is not self and self.isAncestorOf(focused):
                # Don't scroll - user is interacting with an embedded widget
                return
        super().scrollTo(index, hint)


class EditableLabel(QtWidgets.QWidget):
    """A label that becomes editable when double-clicked."""

    valueChanged = QtCore.pyqtSignal(str)

    def __init__(self, initial_value: str = "", parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)
        self._value = initial_value
        self._editing = False

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._stack = QtWidgets.QStackedWidget()

        self._label = QtWidgets.QLabel(initial_value)
        self._stack.addWidget(self._label)

        self._edit = QtWidgets.QLineEdit(initial_value)
        self._edit.returnPressed.connect(self._finish_editing)
        self._edit.editingFinished.connect(self._finish_editing)
        self._stack.addWidget(self._edit)

        layout.addWidget(self._stack)
        self._stack.setCurrentWidget(self._label)

    def mouseDoubleClickEvent(self, event: QtGui.QMouseEvent | None):
        """Switch to edit mode on double-click."""
        if event is None:
            return
        # Accept the event to prevent propagation to parent tree widget
        event.accept()
        self._start_editing()

    def _start_editing(self) -> None:
        """Switch to edit mode."""
        if self._editing:
            return
        self._editing = True
        self._edit.setText(self._label.text())
        self._stack.setCurrentWidget(self._edit)
        self._edit.setFocus()
        self._edit.selectAll()

    def _finish_editing(self) -> None:
        """Finish editing and switch back to label mode."""
        if not self._editing:
            return
        self._editing = False

        new_value = self._edit.text()
        if new_value != self._value:
            self._value = new_value
            self._label.setText(new_value)
            self.valueChanged.emit(new_value)
        else:
            self._label.setText(self._value)

        self._stack.setCurrentWidget(self._label)

    def setText(self, text: str) -> None:
        """Set the displayed text value."""
        self._value = text
        self._label.setText(text)
        if self._editing:
            self._edit.setText(text)

    def text(self) -> str:
        """Get the current text value."""
        return self._value

    def setPlaceholderText(self, text: str) -> None:
        """Set placeholder text for the edit field."""
        self._edit.setPlaceholderText(text)


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

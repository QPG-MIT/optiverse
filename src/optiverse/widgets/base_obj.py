from __future__ import annotations

from typing import Any, Dict

from PyQt6 import QtCore, QtGui, QtWidgets


class BaseObj(QtWidgets.QGraphicsObject):
    """
    Base class for all optical elements (Source, Lens, Mirror, Beamsplitter).
    
    Provides common functionality:
    - Standard flags (movable, selectable, sends geometry changes)
    - Context menu (Edit, Delete)
    - Ctrl+Wheel rotation
    - Position/rotation sync with params
    - Serialization interface
    """
    
    edited = QtCore.pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.setFlags(
            QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            | QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)
        self.setCursor(QtCore.Qt.CursorShape.OpenHandCursor)
        self.setTransformOriginPoint(0.0, 0.0)
        self._ready = False  # Set to True after full initialization
    
    def itemChange(self, change, value):
        """Sync params when position or rotation changes."""
        if change in (
            QtWidgets.QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged,
            QtWidgets.QGraphicsItem.GraphicsItemChange.ItemRotationHasChanged,
        ):
            if getattr(self, "_ready", False) and self.scene() is not None:
                self._sync_params_from_item()
                self.edited.emit()
        return super().itemChange(change, value)
    
    def _sync_params_from_item(self):
        """
        Sync internal params from item's position and rotation.
        Override in subclasses that have params.
        """
        pass
    
    def _parent_window(self):
        """Get the parent window for dialogs."""
        sc = self.scene()
        if sc:
            views = sc.views()
            if views:
                return views[0].window()
        return QtWidgets.QApplication.activeWindow()
    
    def wheelEvent(self, ev: QtWidgets.QGraphicsSceneWheelEvent):
        """Ctrl + wheel → rotate element."""
        if self.isSelected() and (ev.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier):
            dy = ev.angleDelta().y()
            steps = dy / 120.0
            self.setRotation(self.rotation() + 2.0 * steps)
            self.edited.emit()
            ev.accept()
        else:
            ev.ignore()
    
    def contextMenuEvent(self, ev: QtWidgets.QGraphicsSceneContextMenuEvent):
        """Right-click context menu with Edit and Delete."""
        m = QtWidgets.QMenu()
        act_edit = m.addAction("Edit…")
        act_delete = m.addAction("Delete")
        a = m.exec(ev.screenPos())
        if a == act_edit:
            self.open_editor()
        elif a == act_delete and self.scene():
            self.scene().removeItem(self)
    
    # Abstract interface methods (subclasses should override)
    def open_editor(self):
        """Open editor dialog for this element."""
        pass
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize element to dictionary."""
        return {}
    
    def from_dict(self, d: Dict[str, Any]):
        """Deserialize element from dictionary."""
        pass


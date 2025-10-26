from __future__ import annotations

from typing import Dict, Any

from PyQt6 import QtCore, QtGui, QtWidgets


class TextNoteItem(QtWidgets.QGraphicsTextItem):
    """
    Movable, editable text note. Double-click to edit; right-click → Delete/Edit.
    """
    
    def __init__(self, text: str = "Text"):
        super().__init__(text)
        self.setFlags(
            QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            | QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
        )
        self.setDefaultTextColor(QtGui.QColor(10, 10, 40))
        f = self.font()
        f.setPointSizeF(11.0)
        self.setFont(f)
        self.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.NoTextInteraction)

    def mouseDoubleClickEvent(self, ev: QtWidgets.QGraphicsSceneMouseEvent):
        self.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextEditorInteraction)
        super().mouseDoubleClickEvent(ev)

    def focusOutEvent(self, ev: QtGui.QFocusEvent):
        super().focusOutEvent(ev)
        self.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.NoTextInteraction)
    
    def contextMenuEvent(self, ev: QtWidgets.QGraphicsSceneContextMenuEvent):
        """Right-click context menu with Edit and Delete."""
        m = QtWidgets.QMenu()
        act_edit = m.addAction("Edit")
        act_del = m.addAction("Delete")
        a = m.exec(ev.screenPos())
        if a == act_edit:
            self.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextEditorInteraction)
            cursor = self.textCursor()
            cursor.movePosition(QtGui.QTextCursor.MoveOperation.End)
            self.setTextCursor(cursor)
            self.setFocus()
        elif a == act_del and self.scene():
            self.scene().removeItem(self)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize text note to dictionary."""
        return {
            "type": "text",
            "text": self.toPlainText(),
            "x": float(self.scenePos().x()),
            "y": float(self.scenePos().y()),
            "color": self.defaultTextColor().name(),
            "point_size": float(self.font().pointSizeF()),
        }
    
    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "TextNoteItem":
        """Deserialize text note from dictionary."""
        item = TextNoteItem(d.get("text", "Text"))
        col = QtGui.QColor(d.get("color", "#0A0A28"))
        item.setDefaultTextColor(col)
        f = item.font()
        ps = d.get("point_size")
        if ps is not None:
            f.setPointSizeF(float(ps))
            item.setFont(f)
        item.setPos(float(d.get("x", 0.0)), float(d.get("y", 0.0)))
        return item



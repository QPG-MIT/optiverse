from __future__ import annotations

import uuid
from typing import Any

from PyQt6 import QtCore, QtGui, QtWidgets

from ...core.zorder_utils import handle_z_order_from_menu


class TextNoteItem(QtWidgets.QGraphicsTextItem):
    """
    Movable, editable text note. Double-click to edit; right-click → Delete/Edit.
    """

    def __init__(self, text: str = "Text", item_uuid: str | None = None):
        super().__init__(text)
        # Generate or use provided UUID for collaboration
        self.item_uuid = item_uuid if item_uuid else str(uuid.uuid4())

        self.setFlags(
            QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            | QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
        )
        self.setDefaultTextColor(QtGui.QColor(10, 10, 40))
        f = self.font()
        f.setPointSizeF(11.0)
        self.setFont(f)
        self.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.NoTextInteraction)

        # Compensate for the view's Y-axis inversion (view has scale(1, -1))
        # Apply scale(1, -1) to flip text back to readable orientation
        self.setTransform(QtGui.QTransform.fromScale(1.0, -1.0))

    def mouseDoubleClickEvent(self, ev: QtWidgets.QGraphicsSceneMouseEvent):
        self.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextEditorInteraction)
        super().mouseDoubleClickEvent(ev)

    def focusOutEvent(self, ev: QtGui.QFocusEvent):
        super().focusOutEvent(ev)
        self.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.NoTextInteraction)

    def contextMenuEvent(self, ev: QtWidgets.QGraphicsSceneContextMenuEvent):
        """Right-click context menu with Edit, Delete, and Z-Order options."""
        m = QtWidgets.QMenu()
        act_edit = m.addAction("Edit")
        act_del = m.addAction("Delete")

        # Add z-order options
        m.addSeparator()
        act_bring_to_front = m.addAction("Bring to Front")
        act_bring_forward = m.addAction("Bring Forward")
        act_send_backward = m.addAction("Send Backward")
        act_send_to_back = m.addAction("Send to Back")

        a = m.exec(ev.screenPos())
        if a == act_edit:
            self.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextEditorInteraction)
            cursor = self.textCursor()
            cursor.movePosition(QtGui.QTextCursor.MoveOperation.End)
            self.setTextCursor(cursor)
            self.setFocus()
        elif a == act_del and self.scene():
            self.scene().removeItem(self)
        else:
            # Handle z-order actions via utility
            handle_z_order_from_menu(
                self,
                a,
                {
                    act_bring_to_front: "bring_to_front",
                    act_bring_forward: "bring_forward",
                    act_send_backward: "send_backward",
                    act_send_to_back: "send_to_back",
                },
            )

    def clone(self, offset_mm: tuple[float, float] = (20.0, 20.0)) -> TextNoteItem:
        """Create a deep copy of this text note with optional position offset."""
        from PyQt6.QtCore import QPointF

        # Create new text note with same text
        new_item = TextNoteItem(self.toPlainText())

        # Copy properties
        new_item.setDefaultTextColor(self.defaultTextColor())
        new_item.setFont(self.font())
        new_item.setZValue(self.zValue())

        # Set offset position
        new_pos = self.scenePos() + QPointF(offset_mm[0], offset_mm[1])
        new_item.setPos(new_pos)

        return new_item

    def to_dict(self) -> dict[str, Any]:
        """Serialize text note to dictionary."""
        return {
            "type": "text",
            "text": self.toPlainText(),
            "x": float(self.scenePos().x()),
            "y": float(self.scenePos().y()),
            "color": self.defaultTextColor().name(),
            "point_size": float(self.font().pointSizeF()),
            "item_uuid": self.item_uuid,
            "z_value": float(self.zValue()),
        }

    @staticmethod
    def from_dict(d: dict[str, Any]) -> TextNoteItem:
        """Deserialize text note from dictionary."""
        item_uuid = d.get("item_uuid")
        item = TextNoteItem(d.get("text", "Text"), item_uuid)
        col = QtGui.QColor(d.get("color", "#0A0A28"))
        item.setDefaultTextColor(col)
        f = item.font()
        ps = d.get("point_size")
        if ps is not None:
            f.setPointSizeF(float(ps))
            item.setFont(f)
        item.setPos(float(d.get("x", 0.0)), float(d.get("y", 0.0)))

        # Restore z-value if present
        if "z_value" in d:
            item.setZValue(float(d["z_value"]))

        return item

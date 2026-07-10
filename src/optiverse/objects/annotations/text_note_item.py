from __future__ import annotations

import uuid
from typing import Any

from PyQt6 import QtCore, QtGui, QtWidgets

from ...core.protocols import HasLayerState
from ...ui.theme_manager import is_dark_mode


class TextNoteItem(QtWidgets.QGraphicsTextItem):
    """
    Movable, editable text note. Double-click to edit; right-click → Delete/Edit.

    When ``owner_uuid`` is set, this item acts as an **autolabel** — a label
    that is logically owned by another scene item (typically a ComponentItem).
    Autolabels follow their owner's position and are cascade-deleted when the
    owner is removed.
    """

    # Type name for layer panel identification
    type_name: str = "text"

    def __init__(self, text: str = "Text", item_uuid: str | None = None):
        super().__init__(text)
        # Generate or use provided UUID for collaboration
        self.item_uuid = item_uuid if item_uuid else str(uuid.uuid4())
        # Custom display name for layer panel (None = use type_name)
        self.display_name: str | None = None

        # Autolabel owner link — UUID of the parent item this label belongs to.
        # When set, the label follows the owner and is deleted with it.
        self.owner_uuid: str | None = None
        # Local offset from owner's scene position (set when label is created)
        self._owner_offset: QtCore.QPointF = QtCore.QPointF(0.0, 0.0)

        self.setFlags(
            QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            | QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self._locked = False
        self._group_drag_override = False
        self.setDefaultTextColor(
            QtGui.QColor("white") if is_dark_mode() else QtGui.QColor("black")
        )
        f = self.font()
        f.setPointSizeF(11.0)
        self.setFont(f)
        self.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.NoTextInteraction)
        self._text_before_edit: str | None = None

        # Compensate for the view's Y-axis inversion (view has scale(1, -1))
        # Apply scale(1, -1) to flip text back to readable orientation
        self.setTransform(QtGui.QTransform.fromScale(1.0, -1.0))

    # ========== Autolabel helpers ==========

    @property
    def is_autolabel(self) -> bool:
        """True if this text note is an autolabel owned by another item."""
        return self.owner_uuid is not None

    def follow_owner(self) -> None:
        """Reposition this label relative to its owner's current scene position.

        Called as a slot connected to the owner's ``edited`` signal.
        """
        owner = self._find_owner()
        if owner is None:
            return
        new_pos = owner.scenePos() + self._owner_offset
        if (new_pos - self.pos()).manhattanLength() > 0.01:
            self.setPos(new_pos)

    def _find_owner(self) -> QtWidgets.QGraphicsItem | None:
        """Look up the owner item in the scene by UUID."""
        if self.owner_uuid is None:
            return None
        scene = self.scene()
        if scene is None:
            return None
        for it in scene.items():
            if getattr(it, "item_uuid", None) == self.owner_uuid:
                return it
        return None

    # ========== Locking ==========

    def is_locked(self) -> bool:
        return self._locked

    def set_locked(self, locked: bool) -> None:
        self._locked = locked
        self._sync_lock_to_layer_node(locked)
        if locked:
            self.setCursor(QtCore.Qt.CursorShape.ForbiddenCursor)
        else:
            self.setCursor(QtCore.Qt.CursorShape.IBeamCursor)
        self.update()

    def _sync_lock_to_layer_node(self, locked: bool) -> None:
        scene = self.scene()
        if not scene or not scene.views():
            return
        window = scene.views()[0].window()
        layer_state = getattr(window, "layer_state", None)
        if layer_state is None:
            return
        node = layer_state.get_node(self.item_uuid)
        if node:
            node.locked = locked

    def itemChange(self, change, value):
        if change == QtWidgets.QGraphicsItem.GraphicsItemChange.ItemPositionChange:
            if self._locked and not self._group_drag_override:
                return self.pos()
        elif change == QtWidgets.QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            if self.owner_uuid is not None:
                owner = self._find_owner()
                if owner is not None:
                    self._owner_offset = self.pos() - owner.scenePos()
        return super().itemChange(change, value)

    # ========== Events ==========

    def mouseDoubleClickEvent(self, ev: QtWidgets.QGraphicsSceneMouseEvent | None):
        if ev is None:
            return
        if self._locked:
            return
        self._text_before_edit = self.toPlainText()
        self.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextEditorInteraction)
        self.setFocus()
        cursor = self.textCursor()
        cursor.select(QtGui.QTextCursor.SelectionType.Document)
        self.setTextCursor(cursor)

    def keyPressEvent(self, ev: QtGui.QKeyEvent | None):
        if ev is None:
            return
        if ev.key() == QtCore.Qt.Key.Key_Escape:
            self.clearFocus()
            self.setSelected(False)
            ev.accept()
            return
        super().keyPressEvent(ev)

    def focusOutEvent(self, ev: QtGui.QFocusEvent | None):
        if ev is None:
            return
        super().focusOutEvent(ev)
        cursor = self.textCursor()
        cursor.clearSelection()
        self.setTextCursor(cursor)
        self.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.NoTextInteraction)
        old_text = getattr(self, "_text_before_edit", None)
        if old_text is not None:
            new_text = self.toPlainText()
            if old_text != new_text:
                from ...core.undo_commands import TextEditCommand

                cmd = TextEditCommand(self, old_text, new_text)
                scene = self.scene()
                if scene and scene.views():
                    mw = scene.views()[0].window()
                    undo_stack = getattr(mw, "undo_stack", None)
                    if undo_stack:
                        undo_stack.push(cmd)
            self._text_before_edit = None

    def contextMenuEvent(self, ev: QtWidgets.QGraphicsSceneContextMenuEvent | None):
        """Right-click context menu with Edit, Delete, Lock, and Z-Order options."""
        m = QtWidgets.QMenu()
        act_edit = m.addAction("Edit")
        act_del = m.addAction("Delete")

        m.addSeparator()
        act_lock = m.addAction("Lock")
        if act_lock is not None:
            act_lock.setCheckable(True)
            act_lock.setChecked(self._locked)

        if self._locked:
            if act_edit is not None:
                act_edit.setEnabled(False)
            if act_del is not None:
                act_del.setEnabled(False)
                act_del.setToolTip("Item is locked")

        # Add z-order options
        m.addSeparator()
        act_bring_to_front = m.addAction("Bring to Front")
        act_bring_forward = m.addAction("Bring Forward")
        act_send_backward = m.addAction("Send Backward")
        act_send_to_back = m.addAction("Send to Back")

        from ..context_menu_helpers import add_export_selected_action

        add_export_selected_action(m, self.scene())

        if ev is None:
            return
        a = m.exec(ev.screenPos())
        if a == act_lock and act_lock is not None:
            self.set_locked(act_lock.isChecked())
        elif a == act_edit:
            if not self._locked:
                self._text_before_edit = self.toPlainText()
                self.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextEditorInteraction)
                cursor = self.textCursor()
                cursor.movePosition(QtGui.QTextCursor.MoveOperation.End)
                self.setTextCursor(cursor)
                self.setFocus()
        elif a == act_del:
            if not self._locked:
                scene = self.scene()
                if scene is not None:
                    from ...core.undo_commands import RemoveItemCommand

                    layer_state = None
                    undo_stack = None
                    if scene.views():
                        mw = scene.views()[0].window()
                        if isinstance(mw, HasLayerState):
                            layer_state = mw.layer_state
                        undo_stack = getattr(mw, "undo_stack", None)
                    cmd = RemoveItemCommand(scene, self, layer_state)
                    if undo_stack:
                        undo_stack.push(cmd)
                    else:
                        cmd.execute()
        else:
            # Handle z-order actions
            action_map = {
                act_bring_to_front: "bring_to_front",
                act_bring_forward: "bring_forward",
                act_send_backward: "send_backward",
                act_send_to_back: "send_to_back",
            }
            if op := action_map.get(a):
                scene = self.scene()
                if scene and scene.views():
                    main_window = scene.views()[0].window()
                    if isinstance(main_window, HasLayerState) and main_window.layer_state:
                        items = list(scene.selectedItems()) if self.isSelected() else [self]
                        uuids = [it.item_uuid for it in items if hasattr(it, "item_uuid")]
                        if uuids:
                            from ...core.undo_commands import ZOrderCommand

                            cmd = ZOrderCommand(main_window.layer_state, uuids, op)
                            undo_stack = getattr(main_window, "undo_stack", None)
                            if undo_stack:
                                undo_stack.push(cmd)
                            else:
                                cmd.execute()

    def clone(self, offset_mm: tuple[float, float] = (20.0, 20.0)) -> TextNoteItem:
        """Create a deep copy of this text note with optional position offset.

        Autolabel ownership is intentionally *not* copied — the clone becomes
        a standalone text note.  The caller (e.g. copy/paste) is responsible
        for re-linking if desired.
        """
        from PyQt6.QtCore import QPointF

        new_item = TextNoteItem(self.toPlainText())

        new_item.display_name = self.display_name  # keep custom layer name for indexing
        new_item.setDefaultTextColor(self.defaultTextColor())
        new_item.setFont(self.font())
        new_item.setZValue(self.zValue())

        new_pos = self.scenePos() + QPointF(offset_mm[0], offset_mm[1])
        new_item.setPos(new_pos)

        return new_item

    def to_dict(self) -> dict[str, Any]:
        """Serialize text note to dictionary."""
        d: dict[str, Any] = {
            "type": "text",
            "text": self.toPlainText(),
            "x": float(self.scenePos().x()),
            "y": float(self.scenePos().y()),
            "color": self.defaultTextColor().name(),
            "point_size": float(self.font().pointSizeF()),
            "item_uuid": self.item_uuid,
            "z_value": float(self.zValue()),
        }
        if self._locked:
            d["locked"] = True
        if self.display_name:
            d["display_name"] = self.display_name
        if self.owner_uuid is not None:
            d["owner_uuid"] = self.owner_uuid
            d["owner_offset_x"] = float(self._owner_offset.x())
            d["owner_offset_y"] = float(self._owner_offset.y())
        return d

    @staticmethod
    def from_dict(d: dict[str, Any]) -> TextNoteItem:
        """Deserialize text note from dictionary."""
        item_uuid = d.get("item_uuid")
        item = TextNoteItem(d.get("text", "Text"), item_uuid)
        raw_color = d.get("color", "")
        if raw_color and raw_color.lower() != "#0a0a28":
            col = QtGui.QColor(raw_color)
        else:
            col = QtGui.QColor("white") if is_dark_mode() else QtGui.QColor("black")
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
        if d.get("locked"):
            item.set_locked(True)
        if d.get("display_name"):
            item.display_name = str(d["display_name"])

        # Restore autolabel link
        owner_uuid = d.get("owner_uuid")
        if owner_uuid:
            item.owner_uuid = owner_uuid
            item._owner_offset = QtCore.QPointF(
                float(d.get("owner_offset_x", 0.0)),
                float(d.get("owner_offset_y", 0.0)),
            )

        return item

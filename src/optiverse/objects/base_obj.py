from __future__ import annotations

from typing import Any

from PyQt6 import QtCore, QtGui, QtWidgets


class BaseObj(QtWidgets.QGraphicsObject):
    """
    Base class for all optical elements (Source, Lens, Mirror, Beamsplitter).
    
    Provides common functionality:
    - Standard flags (movable, selectable, sends geometry changes)
    - Context menu (Edit, Delete)
    - Ctrl+Wheel rotation
    - Position/rotation sync with params
    - Sprite helper methods for clickable sprites
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
        """Sync params when position or rotation changes, and apply magnetic snap."""
        
        # Magnetic snap: intercept position changes during interactive moves
        if change == QtWidgets.QGraphicsItem.GraphicsItemChange.ItemPositionChange:
            if getattr(self, "_ready", False) and self.scene() is not None:
                # Get the main window to check if magnetic snap is enabled
                scene = self.scene()
                if scene:
                    views = scene.views()
                    if views:
                        main_window = views[0].window()
                        # Check if magnetic snap is enabled and this is an interactive move
                        if hasattr(main_window, 'magnetic_snap') and main_window.magnetic_snap:
                            if hasattr(main_window, '_snap_helper'):
                                # value is the new position being proposed
                                new_pos = value
                                
                                # Calculate snap
                                snap_result = main_window._snap_helper.calculate_snap(
                                    new_pos,
                                    self,
                                    scene,
                                    views[0]
                                )
                                
                                if snap_result.snapped:
                                    # Update guide lines
                                    views[0].set_snap_guides(snap_result.guide_lines)
                                    # Return snapped position instead of proposed position
                                    return snap_result.position
                                else:
                                    # Clear guides if not snapping
                                    views[0].clear_snap_guides()
        
        if change in (
            QtWidgets.QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged,
            QtWidgets.QGraphicsItem.GraphicsItemChange.ItemRotationHasChanged,
        ):
            if getattr(self, "_ready", False) and self.scene() is not None:
                self._sync_params_from_item()
                self.edited.emit()

        # Phase 2.2: Ensure sprite re-renders when selection toggles (remove lingering tint)
        if change in (
            QtWidgets.QGraphicsItem.GraphicsItemChange.ItemSelectedChange,
            QtWidgets.QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged,
        ):
            # Repaint this item and its sprite (if any)
            self.update()
            sp = getattr(self, "_sprite", None)
            if sp is not None:
                sp.update()

        return super().itemChange(change, value)

    def _sync_params_from_item(self):
        """
        Sync internal params from item's position and rotation.
        Override in subclasses that have params.
        """
        pass

    # ----- Sprite Helper Methods (Phase 1.2: Clickable Sprites) -----
    def _sprite_rect_in_item(self) -> QtCore.QRectF | None:
        """
        Get sprite bounds in item-local coordinates.
        
        Returns None if sprite doesn't exist or is invisible.
        This is used to make sprites part of the clickable area.
        """
        sp = getattr(self, "_sprite", None)
        if sp is None or not sp.isVisible():
            return None
        # parent == this item ⇒ returned rect is in *item-local* coords
        return sp.mapRectToParent(sp.boundingRect())

    def _shape_union_sprite(self, shape_path: QtGui.QPainterPath) -> QtGui.QPainterPath:
        """
        Union sprite bounds into shape for hit testing.
        
        This makes the sprite clickable, not just the geometry line.
        Call this at the end of shape() method.
        """
        r = self._sprite_rect_in_item()
        if r is not None:
            pad = 1.0
            rp = QtGui.QPainterPath()
            rp.addRect(r.adjusted(-pad, -pad, pad, pad))
            shape_path = shape_path.united(rp)
        return shape_path

    def _bounds_union_sprite(self, base_rect: QtCore.QRectF) -> QtCore.QRectF:
        """
        Union sprite bounds into bounding rect.
        
        Ensures the bounding box encompasses the entire sprite.
        Call this at the end of boundingRect() method.
        """
        r = self._sprite_rect_in_item()
        if r is not None:
            pad = 2.0
            r = r.adjusted(-pad, -pad, pad, pad)
            base_rect = base_rect.united(r)
        return base_rect

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

    def to_dict(self) -> dict[str, Any]:
        """Serialize element to dictionary."""
        return {}

    def from_dict(self, d: dict[str, Any]):
        """Deserialize element from dictionary."""
        pass


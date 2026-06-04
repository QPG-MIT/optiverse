from __future__ import annotations

from typing import Any

import numpy as np
from PyQt6 import QtCore, QtGui, QtWidgets

from ...core.interface_definition import InterfaceDefinition
from ...core.models import ComponentParams
from ...core.raytracing_math import qt_angle_to_user, user_angle_to_qt
from ...ui.widgets.interface_properties_widget import InterfacePropertiesWidget
from ...ui.widgets.smart_spinbox import SmartDoubleSpinBox
from ..base_obj import BaseObj
from ..component_sprite import ComponentSprite, create_component_sprite
from ..type_registry import deserialize_item, register_type, serialize_item


@register_type("component", ComponentParams)
class ComponentItem(BaseObj):
    """
    Generic optical component that holds any collection of interfaces.

    Each interface behaves independently based on its element_type.
    The component is just a container/grouping mechanism.

    Supports any combination of:
    - Lenses (thin lens approximation with focal length)
    - Mirrors (pure reflection)
    - Beamsplitters (partial reflection/transmission)
    - Dichroics (wavelength-dependent)
    - Waveplates (polarization rotation)
    - Refractive interfaces (Snell's law refraction)
    - Beam blocks (ray absorption)
    - Background/decorative items (empty interfaces list)

    COORDINATE SYSTEM:
    - Interfaces are stored in InterfaceDefinition objects (Y-up, mm, image-center origin)
    - When displayed, coordinates are transformed from image-center to picked-line-center
    - The picked line offset accounts for centering the sprite on the reference line
    - ComponentSprite handles Y-up to Y-down conversion for Qt display
    """

    type_name: str = "component"

    def __init__(self, params: ComponentParams, item_uuid: str | None = None):
        super().__init__(item_uuid)
        self.params = params
        self._sprite: ComponentSprite | None = None
        self._actual_length_mm: float | None = None
        self._update_geom()
        self.setPos(self.params.x_mm, self.params.y_mm)
        self.setRotation(user_angle_to_qt(self.params.angle_deg))
        self._maybe_attach_sprite()
        self._ready = True

    def _sync_params_from_item(self):
        """Sync params from item position/rotation."""
        self.params.x_mm = float(self.pos().x())
        self.params.y_mm = float(self.pos().y())
        self.params.angle_deg = qt_angle_to_user(self.rotation())

    def _update_geom(self):
        """Update geometry based on interfaces."""
        self.prepareGeometryChange()

        # Get picked line offset for coordinate transformation
        offset_x, offset_y = getattr(self, "_picked_line_offset_mm", (0.0, 0.0))

        # Compute bounding box from all interfaces
        if self.params.interfaces:
            all_x = []
            all_y = []
            for iface in self.params.interfaces:
                # Apply picked line offset transformation
                # Interfaces are stored relative to image center,
                # but item (0,0) is at picked line center
                all_x.extend([iface.x1_mm - offset_x, iface.x2_mm - offset_x])
                all_y.extend([iface.y1_mm - offset_y, iface.y2_mm - offset_y])

            if all_x and all_y:
                min_x = min(all_x)
                max_x = max(all_x)
                min_y = min(all_y)
                max_y = max(all_y)

                # Store bounds for rendering
                self._bounds = QtCore.QRectF(min_x, min_y, max_x - min_x, max_y - min_y)
            else:
                # Default bounds
                L = self.params.object_height_mm
                self._bounds = QtCore.QRectF(-L / 2, -L / 2, L, L)
        else:
            # Default bounds if no interfaces
            L = self.params.object_height_mm
            self._bounds = QtCore.QRectF(-L / 2, -L / 2, L, L)

    def _maybe_attach_sprite(self):
        """Attach or update component sprite if image available."""
        if getattr(self, "_sprite", None):
            try:
                if self.scene():
                    self.scene().removeItem(self._sprite)
            except RuntimeError:
                pass  # Sprite may already be removed from scene
            self._sprite = None

        # Calculate picked line offset for coordinate transformation
        self._picked_line_offset_mm = (0.0, 0.0)  # Default: no offset

        # Use first interface to compute reference line for sprite positioning
        if self.params.image_path and self.params.interfaces and len(self.params.interfaces) > 0:
            first_interface = self.params.interfaces[0]

            # Get interface center and length
            cx = 0.5 * (first_interface.x1_mm + first_interface.x2_mm)
            cy = 0.5 * (first_interface.y1_mm + first_interface.y2_mm)

            dx = first_interface.x2_mm - first_interface.x1_mm
            dy = first_interface.y2_mm - first_interface.y1_mm
            (dx**2 + dy**2) ** 0.5

            # Use the interface itself as the reference line for most element types
            # For refractive objects, we might want perpendicular, but for lens/mirror/BS
            # the interface line IS the optical element
            reference_line_mm = (
                first_interface.x1_mm,
                first_interface.y1_mm,
                first_interface.x2_mm,
                first_interface.y2_mm,
            )

            self._sprite = create_component_sprite(
                self.params.image_path,
                reference_line_mm,
                self.params.object_height_mm,
                self,
            )
            self._actual_length_mm = self._sprite.picked_line_length_mm

            # Store offset: interfaces are at image center,
            # but item (0,0) is at reference line center
            self._picked_line_offset_mm = (cx, cy)

            self._update_geom()
            # Note: z-value is set by layer panel based on tree position

        elif self.params.image_path and (
            not self.params.interfaces or len(self.params.interfaces) == 0
        ):
            # Background objects (no interfaces) - use default horizontal reference line
            # This allows tables, breadboards, etc. to display their sprites
            reference_line_mm = (-50.0, 0.0, 50.0, 0.0)  # Horizontal line at center

            self._sprite = create_component_sprite(
                self.params.image_path,
                reference_line_mm,
                self.params.object_height_mm,
                self,
            )
            self._actual_length_mm = self._sprite.picked_line_length_mm

            # No interface offset for background objects
            self._picked_line_offset_mm = (0.0, 0.0)

            self._update_geom()
            # Note: z-value is set by layer panel based on tree position

    def boundingRect(self) -> QtCore.QRectF:
        """Return bounding rectangle."""
        rect = self._bounds.adjusted(-8, -8, 8, 8)
        return self._bounds_union_sprite(rect)

    def shape(self) -> QtGui.QPainterPath:
        """Return shape for hit testing."""
        path = QtGui.QPainterPath()

        # Get picked line offset for coordinate transformation
        offset_x, offset_y = getattr(self, "_picked_line_offset_mm", (0.0, 0.0))

        # Add all interfaces to shape
        if self.params.interfaces is None:
            return path
        for iface in self.params.interfaces:
            # Transform from image-center coords to picked-line-center coords
            p1 = QtCore.QPointF(iface.x1_mm - offset_x, iface.y1_mm - offset_y)
            p2 = QtCore.QPointF(iface.x2_mm - offset_x, iface.y2_mm - offset_y)
            line_path = QtGui.QPainterPath()
            line_path.moveTo(p1)
            line_path.lineTo(p2)

            s = QtGui.QPainterPathStroker()
            s.setWidth(10)
            path.addPath(s.createStroke(line_path))

        return self._shape_union_sprite(path)

    def _get_interface_color(self, element_type: str) -> QtGui.QColor:
        """Get color for interface based on element type."""
        color_map = {
            "lens": QtGui.QColor(50, 120, 220),  # Blue
            "mirror": QtGui.QColor(150, 150, 150),  # Grey
            "beam_splitter": QtGui.QColor(15, 160, 80),  # Green
            "beamsplitter": QtGui.QColor(15, 160, 80),  # Green
            "dichroic": QtGui.QColor(200, 50, 200),  # Magenta
            "waveplate": QtGui.QColor(100, 200, 100),  # Light green
            "polarizing_interface": QtGui.QColor(100, 200, 100),  # Light green
            "refractive_interface": QtGui.QColor(100, 100, 255),  # Light blue
            "beam_block": QtGui.QColor(50, 50, 50),  # Dark grey
        }
        return color_map.get(element_type, QtGui.QColor(150, 100, 255))  # Purple default

    def paint(self, p: QtGui.QPainter | None, opt, widget=None):
        """Paint all interfaces with appropriate colors."""
        if p is None:
            return
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)

        # If no interfaces and no sprite, draw placeholder (for background items)
        if not self.params.interfaces and self._sprite is None:
            pen = QtGui.QPen(QtGui.QColor(150, 150, 150), 2)
            pen.setStyle(QtCore.Qt.PenStyle.DashLine)
            pen.setCosmetic(True)
            p.setPen(pen)
            p.drawRect(self.boundingRect())

            # Draw text
            p.setPen(QtGui.QColor(100, 100, 100))
            font = p.font()
            font.setPointSize(10)
            p.setFont(font)
            p.drawText(
                self.boundingRect(),
                QtCore.Qt.AlignmentFlag.AlignCenter,
                self.params.name or "Background",
            )
            return

        # Get picked line offset for coordinate transformation
        offset_x, offset_y = getattr(self, "_picked_line_offset_mm", (0.0, 0.0))

        if self.params.interfaces is None:
            return
        for iface in self.params.interfaces:
            # Get color based on element type
            color = self._get_interface_color(iface.element_type)
            width = 3

            pen = QtGui.QPen(color, width)
            pen.setCosmetic(True)
            p.setPen(pen)

            # Transform from image-center coords to picked-line-center coords (item local coords)
            p1 = QtCore.QPointF(iface.x1_mm - offset_x, iface.y1_mm - offset_y)
            p2 = QtCore.QPointF(iface.x2_mm - offset_x, iface.y2_mm - offset_y)

            # Check if curved (for lenses with curvature)
            if (
                hasattr(iface, "is_curved")
                and iface.is_curved
                and abs(getattr(iface, "radius_of_curvature_mm", 0.0)) > 0.1
            ):
                self._draw_curved_surface(p, p1, p2, iface.radius_of_curvature_mm)
            else:
                p.drawLine(p1, p2)

    def _draw_curved_surface(
        self, p: QtGui.QPainter, p1: QtCore.QPointF, p2: QtCore.QPointF, radius_mm: float
    ):
        """Draw a curved surface as an arc."""
        import math

        # Midpoint
        mid_x = (p1.x() + p2.x()) / 2.0
        mid_y = (p1.y() + p2.y()) / 2.0

        # Chord vector
        dx = p2.x() - p1.x()
        dy = p2.y() - p1.y()
        chord_length = math.sqrt(dx * dx + dy * dy)

        if chord_length < 0.01:
            p.drawLine(p1, p2)
            return

        # Perpendicular to chord
        perp_x = -dy / chord_length
        perp_y = dx / chord_length

        # Distance from midpoint to center
        r = abs(radius_mm)
        half_chord = chord_length / 2.0

        if r < half_chord:
            # Radius too small, draw straight line
            p.drawLine(p1, p2)
            return

        d = math.sqrt(r * r - half_chord * half_chord)

        # Center position (direction depends on sign of radius)
        # Cartesian Sign Convention: positive R = center to the RIGHT (downstream)
        # Note: Component editor uses mm coords directly but Qt renders Y-down,
        # so we flip signs compared to canvas (which already converts mm to screen)
        if radius_mm > 0:
            center_x = mid_x + d * perp_x
            center_y = mid_y + d * perp_y
        else:
            center_x = mid_x - d * perp_x
            center_y = mid_y - d * perp_y

        # Calculate angles (flip Y for Qt's Y-down rendering)
        angle1 = math.atan2(center_y - p1.y(), p1.x() - center_x) * 180.0 / math.pi
        angle2 = math.atan2(center_y - p2.y(), p2.x() - center_x) * 180.0 / math.pi

        # Span angle (always draw shorter arc)
        span = angle2 - angle1
        if span > 180:
            span -= 360
        elif span < -180:
            span += 360

        # Draw arc
        rect = QtCore.QRectF(center_x - r, center_y - r, 2 * r, 2 * r)
        p.drawArc(rect, int(angle1 * 16), int(span * 16))  # Qt uses 1/16th degree units

    def get_interfaces_scene(self):
        """
        Get all optical interfaces in scene coordinates.

        Each interface retains its element_type and behaves independently.

        Returns:
            List of (p1, p2, interface) tuples where p1 and p2 are numpy arrays
            in scene coordinates, and interface is an InterfaceDefinition.
        """
        # Get picked line offset for coordinate transformation
        offset_x, offset_y = getattr(self, "_picked_line_offset_mm", (0.0, 0.0))

        result = []
        for iface in self.params.interfaces:
            # Transform from image-center coords to item local coords
            p1_local = QtCore.QPointF(iface.x1_mm - offset_x, iface.y1_mm - offset_y)
            p2_local = QtCore.QPointF(iface.x2_mm - offset_x, iface.y2_mm - offset_y)

            # Transform to scene coordinates
            p1_scene = self.mapToScene(p1_local)
            p2_scene = self.mapToScene(p2_local)

            p1 = np.array([p1_scene.x(), p1_scene.y()])
            p2 = np.array([p2_scene.x(), p2_scene.y()])
            result.append((p1, p2, iface))

        return result

    def apply_state(self, state):
        """Override to handle InterfaceDefinition deserialization."""
        # Convert interface dictionaries to InterfaceDefinition objects BEFORE calling super()
        # This is necessary because super().apply_state() calls _update_geom() which expects
        # InterfaceDefinition objects, not dicts
        if "params" in state and "interfaces" in state["params"]:
            interfaces_data = state["params"]["interfaces"]
            if (
                interfaces_data
                and len(interfaces_data) > 0
                and isinstance(interfaces_data[0], dict)
            ):
                state["params"]["interfaces"] = [
                    InterfaceDefinition.from_dict(iface_dict) for iface_dict in interfaces_data
                ]

        # Now call base class implementation (which will call _update_geom())
        super().apply_state(state)

    def open_editor(self):
        """Open editor dialog for component parameters."""
        # Capture initial state for undo
        initial_state = self.capture_state()

        parent = self._parent_window()
        d = QtWidgets.QDialog(parent)
        d.setWindowTitle(f"Edit {self.params.name or 'Component'}")
        f = QtWidgets.QFormLayout(d)

        # Save initial state for rollback on cancel
        initial_x = self.pos().x()
        initial_y = self.pos().y()
        initial_ang = qt_angle_to_user(self.rotation())
        initial_length = self.params.object_height_mm

        # Save initial interface states (use .copy() method to preserve type)
        ([iface.copy() for iface in self.params.interfaces] if self.params.interfaces else [])

        x = SmartDoubleSpinBox()
        x.setRange(-1e6, 1e6)
        x.setDecimals(3)
        x.setSuffix(" mm")
        x.setValue(initial_x)

        y = SmartDoubleSpinBox()
        y.setRange(-1e6, 1e6)
        y.setDecimals(3)
        y.setSuffix(" mm")
        y.setValue(initial_y)

        ang = SmartDoubleSpinBox()
        ang.setRange(-1e6, 1e6)
        ang.setDecimals(2)
        ang.setSuffix(" °")
        ang.setValue(initial_ang)
        ang.setToolTip("Component angle (0° = right →, 90° = down ↓, 180° = left ←)")

        length = SmartDoubleSpinBox()
        length.setRange(1, 1e7)
        length.setDecimals(2)
        length.setSuffix(" mm")
        length.setValue(initial_length)

        # Live update connections
        def update_position():
            self.setPos(x.value(), y.value())
            self.params.x_mm = x.value()
            self.params.y_mm = y.value()
            self.edited.emit()

        def update_angle():
            user_angle = ang.value()
            self.setRotation(user_angle_to_qt(user_angle))
            self.params.angle_deg = user_angle
            self.edited.emit()

        def update_length():
            old_height = self.params.object_height_mm
            new_height = length.value()
            if old_height > 0 and abs(new_height - old_height) > 1e-9:
                scale = new_height / old_height
                if self.params.interfaces:
                    for iface in self.params.interfaces:
                        iface.x1_mm *= scale
                        iface.y1_mm *= scale
                        iface.x2_mm *= scale
                        iface.y2_mm *= scale
            self.params.object_height_mm = new_height
            self._update_geom()
            self._maybe_attach_sprite()
            self.edited.emit()

        # Update spinboxes when item is modified externally
        def sync_from_item():
            x.blockSignals(True)
            y.blockSignals(True)
            ang.blockSignals(True)

            user_angle = qt_angle_to_user(self.rotation())

            x.setValue(self.pos().x())
            y.setValue(self.pos().y())
            ang.setValue(user_angle)

            x.blockSignals(False)
            y.blockSignals(False)
            ang.blockSignals(False)

        x.valueChanged.connect(update_position)
        y.valueChanged.connect(update_position)
        ang.valueChanged.connect(update_angle)
        length.valueChanged.connect(update_length)

        self.edited.connect(sync_from_item)

        f.addRow("X Position", x)
        f.addRow("Y Position", y)
        f.addRow("Angle", ang)
        f.addRow("Size", length)

        # Add interface properties section
        if self.params.interfaces:
            separator = QtWidgets.QFrame()
            separator.setFrameShape(QtWidgets.QFrame.Shape.HLine)
            f.addRow(separator)

            interface_widget = InterfacePropertiesWidget(self.params.interfaces)
            interface_widget.propertiesChanged.connect(self.edited.emit)
            f.addRow(interface_widget)

        btn = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        f.addRow(btn)
        btn.accepted.connect(d.accept)
        btn.rejected.connect(d.reject)

        result = d.exec()

        self.edited.disconnect(sync_from_item)

        if result:
            # User clicked OK - create undo command for property change
            final_state = self.capture_state()
            if initial_state != final_state:
                from ...core.undo_commands import PropertyChangeCommand

                cmd = PropertyChangeCommand(self, initial_state, final_state)
                self.commandCreated.emit(cmd)
        else:
            # User clicked Cancel - restore initial state
            self.apply_state(initial_state)

    def to_component_dict(self) -> dict[str, Any]:
        """Extract a library-compatible component dict from this placed instance.

        The returned dict is suitable for passing to ComponentEditor._load_from_dict().
        """
        data: dict[str, Any] = {
            "name": self.params.name or "",
            "image_path": self.params.image_path or "",
            "object_height_mm": self.params.object_height_mm,
            "category": self.params.category or "",
            "notes": self.params.notes or "",
            "angle_deg": self.params.angle_deg,
        }
        if self.params.step_file_path:
            data["step_file_path"] = self.params.step_file_path
        if self.params.interfaces:
            data["interfaces"] = [iface.to_dict() for iface in self.params.interfaces]
        return data

    # ------------------------------------------------------------------
    # Context menu
    # ------------------------------------------------------------------

    def contextMenuEvent(self, ev: QtWidgets.QGraphicsSceneContextMenuEvent | None):
        """Right-click context menu with component-specific actions."""
        if ev is None:
            return

        m = QtWidgets.QMenu()
        act_edit = m.addAction("Edit\u2026")
        act_edit_in_editor = m.addAction("Edit in Component Editor\u2026")

        m.addSeparator()
        act_apply_all = m.addAction("Apply Properties to All\u2026")

        # Autolabel toggle
        has_label = self._find_autolabel() is not None
        act_autolabel = m.addAction("Autolabel")
        if act_autolabel is not None:
            act_autolabel.setCheckable(True)
            act_autolabel.setChecked(has_label)

        act_delete = m.addAction("Delete")

        m.addSeparator()
        act_lock = m.addAction("Lock")
        if act_lock is not None:
            act_lock.setCheckable(True)
            act_lock.setChecked(self._locked)

        if self._locked and act_delete is not None:
            act_delete.setEnabled(False)
            act_delete.setToolTip("Item is locked")

        m.addSeparator()
        act_bring_to_front = m.addAction("Bring to Front")
        act_bring_forward = m.addAction("Bring Forward")
        act_send_backward = m.addAction("Send Backward")
        act_send_to_back = m.addAction("Send to Back")

        from ..context_menu_helpers import add_export_selected_action

        add_export_selected_action(m, self.scene())

        a = m.exec(ev.screenPos())
        if a is None:
            return
        if a == act_edit:
            self.open_editor()
        elif a == act_edit_in_editor:
            self._open_in_component_editor()
        elif a == act_apply_all:
            self._apply_properties_to_all()
        elif a == act_autolabel:
            self._toggle_autolabel()
        elif a == act_lock and act_lock is not None:
            new_locked = act_lock.isChecked()
            scene = self.scene()
            selected = scene.selectedItems() if scene else []
            peers = [
                item for item in selected
                if item is not self and hasattr(item, "set_locked")
            ]
            if peers:
                self._batch_set_locked([self] + peers, new_locked)
            else:
                self.set_locked(new_locked)
        elif a == act_delete and act_delete is not None:
            if not self._locked:
                self.requestDelete.emit(self)
        elif a in (act_bring_to_front, act_bring_forward, act_send_backward, act_send_to_back):
            self._handle_z_order_action(
                a, act_bring_to_front, act_bring_forward, act_send_backward, act_send_to_back
            )

    def _open_in_component_editor(self):
        """Open this component in the full Component Editor window."""
        main_window = self._parent_window()
        if main_window is None:
            return
        if not hasattr(main_window, "open_component_editor_for_item"):
            return
        main_window.open_component_editor_for_item(self)

    def _apply_properties_to_all(self):
        """Propagate this component's properties to other components on the canvas."""
        main_window = self._parent_window()
        if main_window is None:
            return
        if not hasattr(main_window, "apply_component_properties_to_all"):
            return
        main_window.apply_component_properties_to_all(self)

    # ------------------------------------------------------------------
    # Autolabel
    # ------------------------------------------------------------------

    def get_autolabel_text(self) -> str:
        """Build a concise label string from this component's optical interfaces."""
        if not self.params.interfaces:
            return self.params.name or "Component"

        parts: list[str] = []
        for iface in self.params.interfaces:
            et = iface.element_type
            if et == "lens":
                parts.append(f"f = {iface.efl_mm:g} mm")
            elif et == "mirror":
                parts.append("Mirror")
            elif et == "beam_splitter":
                label = "PBS" if iface.is_polarizing else "BS"
                parts.append(f"{label} {iface.split_T:g}/{iface.split_R:g}")
            elif et == "dichroic":
                parts.append(f"\u03bbc = {iface.cutoff_wavelength_nm:g} nm")
            elif et == "polarizing_interface":
                sub = iface.polarizer_subtype
                if sub == "waveplate":
                    if iface.phase_shift_deg == 90.0:
                        parts.append(f"QWP @ {iface.fast_axis_deg:g}\u00b0")
                    elif iface.phase_shift_deg == 180.0:
                        parts.append(f"HWP @ {iface.fast_axis_deg:g}\u00b0")
                    else:
                        parts.append(
                            f"WP {iface.phase_shift_deg:g}\u00b0 @ {iface.fast_axis_deg:g}\u00b0"
                        )
                elif sub == "linear_polarizer":
                    parts.append(f"Pol @ {iface.transmission_axis_deg:g}\u00b0")
                elif sub == "faraday_rotator":
                    parts.append(f"Faraday {iface.rotation_angle_deg:g}\u00b0")
                else:
                    parts.append("Polarizer")
            elif et == "refractive_interface":
                parts.append(f"n = {iface.n1:g} \u2192 {iface.n2:g}")
            elif et == "beam_block":
                parts.append("Block")
        return ", ".join(parts) if parts else (self.params.name or "Component")

    def _find_autolabel(self):
        """Return the existing autolabel TextNoteItem for this component, or None."""
        from ..annotations.text_note_item import TextNoteItem

        scene = self.scene()
        if scene is None:
            return None
        for it in scene.items():
            if isinstance(it, TextNoteItem) and it.owner_uuid == self.item_uuid:
                return it
        return None

    def _label_offset(self, label_width: float = 0.0) -> QtCore.QPointF:
        """Compute a default offset to place the label centered above the element."""
        br = self.boundingRect()
        above_y = br.bottom() + 10.0
        center_x = br.center().x() - label_width / 2.0
        return QtCore.QPointF(center_x, above_y)

    def create_autolabel(self):
        """Create an autolabel TextNoteItem and add it to the scene."""
        from ..annotations.text_note_item import TextNoteItem

        scene = self.scene()
        if scene is None:
            return None

        if self._find_autolabel() is not None:
            return None

        text = self.get_autolabel_text()
        label = TextNoteItem(text)
        label.owner_uuid = self.item_uuid

        f = label.font()
        f.setPointSizeF(9.0)
        label.setFont(f)
        from ...ui.theme_manager import is_dark_mode

        label.setDefaultTextColor(
            QtGui.QColor("white") if is_dark_mode() else QtGui.QColor("black")
        )

        label_width = label.boundingRect().width()
        label._owner_offset = self._label_offset(label_width)
        label.setPos(self.scenePos() + label._owner_offset)

        self.edited.connect(label.follow_owner)

        return label

    def remove_autolabel(self):
        """Remove the autolabel from the scene (if any) and return it."""
        label = self._find_autolabel()
        if label is None:
            return None
        try:
            self.edited.disconnect(label.follow_owner)
        except (TypeError, RuntimeError):
            pass
        return label

    def _toggle_autolabel(self):
        """Toggle the autolabel on/off via undo stack."""
        from ...core.undo_commands import AddItemCommand, RemoveItemCommand

        scene = self.scene()
        if scene is None:
            return

        undo_stack = None
        layer_state = None
        if scene.views():
            mw = scene.views()[0].window()
            undo_stack = getattr(mw, "undo_stack", None)
            layer_state = getattr(mw, "layer_state", None)

        existing = self._find_autolabel()
        if existing is not None:
            # Remove existing autolabel
            try:
                self.edited.disconnect(existing.follow_owner)
            except (TypeError, RuntimeError):
                pass
            cmd = RemoveItemCommand(scene, existing, layer_state)
            if undo_stack:
                undo_stack.push(cmd)
            else:
                cmd.execute()
        else:
            # Create new autolabel
            label = self.create_autolabel()
            if label is not None:
                cmd = AddItemCommand(
                    scene, label, layer_state, parent_uuid=str(self.item_uuid)
                )
                if undo_stack:
                    undo_stack.push(cmd)
                else:
                    cmd.execute()

    def connect_autolabel(self) -> None:
        """Reconnect the edited signal to an existing autolabel (used after load)."""
        label = self._find_autolabel()
        if label is not None:
            self.edited.connect(label.follow_owner)

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return serialize_item(self)

    @staticmethod
    def from_dict(d: dict[str, Any]) -> ComponentItem:
        """Static factory method: deserialize from dictionary and return new ComponentItem."""
        item = deserialize_item(d)
        if not isinstance(item, ComponentItem):
            raise TypeError(f"Expected ComponentItem, got {type(item)}")
        return item

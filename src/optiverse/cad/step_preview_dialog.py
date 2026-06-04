"""
Interactive STEP preview dialog.

Shows a 3-D mesh viewer (pyqtgraph GLViewWidget) alongside a live 2-D
orthographic projection. The user rotates the model to choose the
projection plane, then clicks "Use This View" to capture the result.
"""

from __future__ import annotations

import logging
import math
from typing import cast

import numpy as np
from PyQt6 import QtCore, QtGui, QtWidgets

from .step_renderer import (
    PRESET_VIEWS,
    is_viewer_available,
    mesh_bounding_box,
    project_mesh_to_2d,
)

_logger = logging.getLogger(__name__)


def _rotation_from_gl_view(gl_widget) -> np.ndarray:
    """Extract the 3x3 rotation matrix directly from pyqtgraph's view matrix."""
    vm = gl_widget.viewMatrix()
    data = np.array(vm.data(), dtype=np.float64).reshape(4, 4).T
    return cast(np.ndarray, data[:3, :3].copy())


class StepPreviewDialog(QtWidgets.QDialog):
    """Dialog for interactively choosing a 2-D projection from a STEP mesh.

    Attributes:
        result_pixmap: The captured 2-D QPixmap (set after accept).
        result_rotation: The 3x3 rotation matrix used for the projection.
        result_height_mm: Physical height the user entered.
    """

    result_pixmap: QtGui.QPixmap | None = None
    result_rotation: np.ndarray | None = None
    result_height_mm: float = 25.4

    def __init__(
        self,
        vertices: np.ndarray,
        faces: np.ndarray,
        face_colors: np.ndarray | None = None,
        initial_rotation: np.ndarray | None = None,
        initial_height_mm: float = 25.4,
        parent: QtWidgets.QWidget | None = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Import STEP – Choose Projection View")
        self.resize(900, 520)

        self._vertices = vertices
        self._faces = faces
        self._face_colors = face_colors
        self._current_rotation = (
            initial_rotation.copy()
            if initial_rotation is not None
            else PRESET_VIEWS["Front"].copy()
        )

        # Compute auto height from bounding box (longest XY extent)
        bbox_min, bbox_max = mesh_bounding_box(vertices)
        bbox_size = bbox_max - bbox_min
        self._auto_height_mm = float(max(bbox_size[0], bbox_size[1], bbox_size[2]))

        self._build_ui(initial_height_mm)
        self._update_preview()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self, initial_height_mm: float):
        layout = QtWidgets.QVBoxLayout(self)

        # Top: split between 3-D viewer and 2-D preview
        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)

        # Left: 3-D GL viewer
        if is_viewer_available():
            import sys

            import pyqtgraph.opengl as gl

            if sys.platform == "darwin":
                fmt = QtGui.QSurfaceFormat()
                fmt.setRenderableType(QtGui.QSurfaceFormat.RenderableType.OpenGL)
                fmt.setProfile(QtGui.QSurfaceFormat.OpenGLContextProfile.CoreProfile)
                fmt.setVersion(4, 1)
                QtGui.QSurfaceFormat.setDefaultFormat(fmt)

            self._gl_widget = gl.GLViewWidget()
            self._gl_widget.setMinimumSize(400, 380)
            self._gl_widget.setBackgroundColor((80, 80, 80))
            elev, azim = self._rotation_to_elev_azim(self._current_rotation)
            self._gl_widget.setCameraPosition(
                distance=self._auto_height_mm * 2.5, elevation=elev, azimuth=azim,
            )

            from pyqtgraph.opengl import shaders as gl_shaders

            _brighter_shader = gl_shaders.ShaderProgram("_stepBright", [
                gl_shaders.VertexShader("""
                    uniform mat4 u_mvp;
                    uniform mat3 u_normal;
                    attribute vec4 a_position;
                    attribute vec3 a_normal;
                    attribute vec4 a_color;
                    varying vec4 v_color;
                    varying vec3 v_normal;
                    void main() {
                        v_normal = normalize(u_normal * a_normal);
                        v_color = a_color;
                        gl_Position = u_mvp * a_position;
                    }
                """),
                gl_shaders.FragmentShader("""
                    #ifdef GL_ES
                    precision mediump float;
                    #endif
                    varying vec4 v_color;
                    varying vec3 v_normal;
                    void main() {
                        vec3 norm = normalize(v_normal);
                        vec3 lightDir = normalize(vec3(0.0, 1.0, 1.0));
                        float diff = max(dot(norm, lightDir), 0.0) * 0.65;
                        vec3 viewDir = vec3(0.0, 0.0, 1.0);
                        vec3 halfDir = normalize(lightDir + viewDir);
                        float spec = pow(max(dot(norm, halfDir), 0.0), 32.0) * 0.3;
                        vec3 rgb = v_color.rgb * (0.55 + diff) + vec3(spec);
                        gl_FragColor = vec4(min(rgb, vec3(1.0)), v_color.a);
                    }
                """),
            ])

            mesh_kwargs = dict(
                vertexes=self._vertices,
                faces=self._faces,
                smooth=False,
                drawEdges=False,
                shader=_brighter_shader,
            )
            if self._face_colors is not None:
                mesh_kwargs["faceColors"] = self._face_colors
            mesh_item = gl.GLMeshItem(**mesh_kwargs)
            self._gl_widget.addItem(mesh_item)
            splitter.addWidget(self._gl_widget)

            # Timer to sync rotation from GL camera on mouse release
            self._sync_timer = QtCore.QTimer(self)
            self._sync_timer.setInterval(200)
            self._sync_timer.setSingleShot(True)
            self._sync_timer.timeout.connect(self._on_camera_changed)
            self._gl_widget.installEventFilter(self)
        else:
            placeholder = QtWidgets.QLabel(
                "pyqtgraph not installed.\n\n"
                "Install with: pip install pyqtgraph\n\n"
                "Use the preset view buttons below."
            )
            placeholder.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            placeholder.setMinimumSize(400, 380)
            splitter.addWidget(placeholder)
            self._gl_widget = None

        # Right: 2-D projection preview
        self._preview_label = QtWidgets.QLabel()
        self._preview_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self._preview_label.setMinimumSize(300, 380)
        self._preview_label.setStyleSheet(
            "QLabel { background-color: white; border: 1px solid #ccc; }"
        )
        splitter.addWidget(self._preview_label)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        layout.addWidget(splitter)

        # Controls row
        controls = QtWidgets.QHBoxLayout()

        controls.addWidget(QtWidgets.QLabel("Physical height:"))
        self._height_spin = QtWidgets.QDoubleSpinBox()
        self._height_spin.setRange(0.1, 1e6)
        self._height_spin.setDecimals(2)
        self._height_spin.setSuffix(" mm")
        self._height_spin.setValue(self._auto_height_mm)
        controls.addWidget(self._height_spin)

        controls.addSpacing(16)

        self._flip_h = QtWidgets.QCheckBox("Flip horizontal")
        self._flip_h.toggled.connect(self._update_preview)
        controls.addWidget(self._flip_h)

        self._flip_v = QtWidgets.QCheckBox("Flip vertical")
        self._flip_v.toggled.connect(self._update_preview)
        controls.addWidget(self._flip_v)

        controls.addStretch()
        layout.addLayout(controls)

        # Snap-to-view buttons
        snap_row = QtWidgets.QHBoxLayout()
        snap_row.addWidget(QtWidgets.QLabel("Snap to:"))
        for name in PRESET_VIEWS:
            btn = QtWidgets.QPushButton(name)
            btn.setMaximumWidth(80)
            btn.clicked.connect(lambda checked, n=name: self._snap_to_view(n))
            snap_row.addWidget(btn)
        snap_row.addStretch()
        layout.addLayout(snap_row)

        # Dialog buttons
        btn_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        ok_btn = btn_box.button(QtWidgets.QDialogButtonBox.StandardButton.Ok)
        if ok_btn:
            ok_btn.setText("Use This View")
        btn_box.accepted.connect(self._on_accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    # ------------------------------------------------------------------
    # Event filter for camera changes
    # ------------------------------------------------------------------

    def eventFilter(self, obj, event):
        if obj is self._gl_widget and event.type() in (
            QtCore.QEvent.Type.MouseButtonRelease,
            QtCore.QEvent.Type.Wheel,
        ):
            self._sync_timer.start()
        return super().eventFilter(obj, event)

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------

    def _on_camera_changed(self):
        """Sync rotation matrix from GL camera and update 2-D preview."""
        if self._gl_widget is not None:
            self._current_rotation = _rotation_from_gl_view(self._gl_widget)
        self._update_preview()

    def _snap_to_view(self, name: str):
        if self._gl_widget is not None:
            elev, azim = self._rotation_to_elev_azim(PRESET_VIEWS[name])
            self._gl_widget.setCameraPosition(elevation=elev, azimuth=azim)
            self._current_rotation = _rotation_from_gl_view(self._gl_widget)
        else:
            self._current_rotation = PRESET_VIEWS[name].copy()
        self._update_preview()

    @staticmethod
    def _rotation_to_elev_azim(rot: np.ndarray) -> tuple[float, float]:
        """Convert a 3x3 rotation to (elevation, azimuth) in degrees for pyqtgraph.

        Inverse of _rotation_from_gl_view. Camera position direction in world
        coords is rot^T @ [0, 0, 1] (positive Z in view = towards viewer).
        pyqtgraph: pos = (cos(e)*cos(a), cos(e)*sin(a), sin(e)) * dist.
        """
        pos_dir = rot.T @ np.array([0, 0, 1], dtype=np.float64)
        elev = math.degrees(math.asin(np.clip(pos_dir[2], -1, 1)))
        azim = math.degrees(math.atan2(pos_dir[1], pos_dir[0]))
        return elev, azim

    def _update_preview(self):
        """Re-render the 2-D projection and display it."""
        rot = self._current_rotation.copy()

        if self._flip_h.isChecked():
            rot[0, :] *= -1  # flip X
        if self._flip_v.isChecked():
            rot[1, :] *= -1  # flip Y

        # Update height from projected Y-extent
        rotated = (rot @ self._vertices.T).T
        proj_height_mm = float(rotated[:, 1].max() - rotated[:, 1].min())
        if proj_height_mm > 0:
            self._height_spin.blockSignals(True)
            self._height_spin.setValue(proj_height_mm)
            self._height_spin.blockSignals(False)

        pix = project_mesh_to_2d(
            self._vertices,
            self._faces,
            rot,
            face_colors=self._face_colors,
            height_px=800,
        )
        if pix and not pix.isNull():
            scaled = pix.scaled(
                self._preview_label.size(),
                QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                QtCore.Qt.TransformationMode.SmoothTransformation,
            )
            self._preview_label.setPixmap(scaled)
        else:
            self._preview_label.setText("(projection failed)")

    def _on_accept(self):
        """Capture the final pixmap and rotation, then accept."""
        rot = self._current_rotation.copy()
        if self._flip_h.isChecked():
            rot[0, :] *= -1
        if self._flip_v.isChecked():
            rot[1, :] *= -1

        self.result_pixmap = project_mesh_to_2d(
            self._vertices,
            self._faces,
            rot,
            face_colors=self._face_colors,
            height_px=1000,
            margin_fraction=0.0,
        )
        self.result_rotation = rot
        self.result_height_mm = self._height_spin.value()
        self.accept()

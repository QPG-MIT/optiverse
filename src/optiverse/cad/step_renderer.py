"""
STEP file loading, tessellation, and 2D orthographic projection.

All functions in this module require optional dependencies (cadquery/OCP).
Use ``is_cad_available()`` to check before calling rendering functions.

Install with:  pip install cadquery pyqtgraph
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from PyQt6.QtGui import QPixmap

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Dependency probing
# ---------------------------------------------------------------------------

_CAD_AVAILABLE: bool | None = None
_PYQTGRAPH_AVAILABLE: bool | None = None


def is_cad_available() -> bool:
    """Return True if cadquery/OCP is importable."""
    global _CAD_AVAILABLE
    if _CAD_AVAILABLE is None:
        try:
            import OCP.STEPControl  # noqa: F401

            _CAD_AVAILABLE = True
        except ImportError:
            _CAD_AVAILABLE = False
    return _CAD_AVAILABLE


def is_viewer_available() -> bool:
    """Return True if pyqtgraph (OpenGL 3-D viewer) is importable."""
    global _PYQTGRAPH_AVAILABLE
    if _PYQTGRAPH_AVAILABLE is None:
        try:
            import pyqtgraph.opengl  # noqa: F401

            _PYQTGRAPH_AVAILABLE = True
        except ImportError:
            _PYQTGRAPH_AVAILABLE = False
    return _PYQTGRAPH_AVAILABLE


def missing_dependency_message() -> str:
    """Human-readable message listing which optional packages are missing."""
    missing: list[str] = []
    if not is_cad_available():
        missing.append("cadquery")
    if not is_viewer_available():
        missing.append("pyqtgraph")
    if not missing:
        return ""
    pkgs = " ".join(missing)
    return (
        f"Optional dependencies not installed: {', '.join(missing)}.\n"
        f"Install with:  pip install {pkgs}"
    )


# ---------------------------------------------------------------------------
# STEP loading & tessellation (with per-face colors)
# ---------------------------------------------------------------------------


def load_step_mesh(
    step_path: str,
    linear_deflection: float = 0.1,
    angular_deflection: float = 0.5,
) -> tuple[np.ndarray, np.ndarray, np.ndarray] | None:
    """Load a STEP file and tessellate its shape into a colored triangle mesh.

    Extracts per-solid colors from the STEP file's XDE document when available.

    Args:
        step_path: Path to a ``.step`` or ``.stp`` file.
        linear_deflection: Maximum linear deviation of tessellation (mm).
        angular_deflection: Maximum angular deviation of tessellation (radians).

    Returns:
        ``(vertices, faces, face_colors)`` where *vertices* is ``(N, 3)`` float64,
        *faces* is ``(M, 3)`` int32, and *face_colors* is ``(M, 4)`` float32 RGBA
        (values 0-1). Returns ``None`` on failure.
    """
    if not is_cad_available():
        _logger.warning("cadquery/OCP not available – cannot load STEP file")
        return None

    try:
        from OCP.BRep import BRep_Tool
        from OCP.BRepMesh import BRepMesh_IncrementalMesh
        from OCP.TopAbs import TopAbs_FACE, TopAbs_SOLID
        from OCP.TopExp import TopExp_Explorer
        from OCP.TopLoc import TopLoc_Location
        from OCP.TopoDS import TopoDS

        # Try XDE reader for color support
        color_tool = None
        shape = None
        try:
            from OCP.STEPCAFControl import STEPCAFControl_Reader
            from OCP.TCollection import TCollection_ExtendedString
            from OCP.TDocStd import TDocStd_Document
            from OCP.XCAFApp import XCAFApp_Application
            from OCP.XCAFDoc import XCAFDoc_DocumentTool, XCAFDoc_ShapeTool

            app = XCAFApp_Application.GetApplication_s()
            doc = TDocStd_Document(TCollection_ExtendedString("MDTV-XCAF"))
            app.InitDocument(doc)

            reader = STEPCAFControl_Reader()
            reader.SetColorMode(True)
            status = reader.ReadFile(step_path)
            if status == 1:
                reader.Transfer(doc)
                shape_tool = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
                color_tool = XCAFDoc_DocumentTool.ColorTool_s(doc.Main())
                from OCP.TDF import TDF_LabelSequence
                labels = TDF_LabelSequence()
                shape_tool.GetFreeShapes(labels)
                if labels.Length() > 0:
                    shape = XCAFDoc_ShapeTool.GetShape_s(labels.Value(1))
        except Exception:
            _logger.debug("XDE color reading failed, falling back to plain reader")

        # Fallback to basic reader if XDE failed
        if shape is None:
            from OCP.STEPControl import STEPControl_Reader as BasicReader
            basic_reader = BasicReader()
            status = basic_reader.ReadFile(step_path)
            if status != 1:
                _logger.error("Failed to read STEP file: %s (status %s)", step_path, status)
                return None
            basic_reader.TransferRoots()
            shape = basic_reader.OneShape()

        BRepMesh_IncrementalMesh(shape, linear_deflection, False, angular_deflection, True)

        # Build a map from solid → color by querying each solid in the shape
        solid_colors: dict[int, tuple[float, float, float]] = {}
        if color_tool is not None:
            from OCP.Quantity import Quantity_Color
            from OCP.XCAFDoc import XCAFDoc_ColorGen, XCAFDoc_ColorSurf

            solid_explorer = TopExp_Explorer(shape, TopAbs_SOLID)
            while solid_explorer.More():
                solid = TopoDS.Solid_s(solid_explorer.Current())
                c = Quantity_Color()
                if color_tool.GetColor(solid, XCAFDoc_ColorSurf, c):
                    solid_colors[id(solid_explorer.Current())] = (c.Red(), c.Green(), c.Blue())
                elif color_tool.GetColor(solid, XCAFDoc_ColorGen, c):
                    solid_colors[id(solid_explorer.Current())] = (c.Red(), c.Green(), c.Blue())
                solid_explorer.Next()

        # Tessellate per-solid to preserve color grouping
        all_verts: list[list[float]] = []
        all_faces: list[list[int]] = []
        all_colors: list[list[float]] = []
        vert_offset = 0

        # Default palette for solids without explicit color
        _default_palette = [
            (0.72, 0.72, 0.76),
            (0.62, 0.67, 0.72),
            (0.76, 0.73, 0.69),
            (0.67, 0.72, 0.67),
        ]

        def _get_solid_color(solid, solid_idx: int) -> tuple[float, float, float]:
            """Get color for a solid: try XDE lookup, then fallback to palette."""
            if color_tool is not None:
                from OCP.Quantity import Quantity_Color
                from OCP.XCAFDoc import XCAFDoc_ColorGen, XCAFDoc_ColorSurf
                c = Quantity_Color()
                if color_tool.GetColor(solid, XCAFDoc_ColorSurf, c):
                    return (c.Red(), c.Green(), c.Blue())
                if color_tool.GetColor(solid, XCAFDoc_ColorGen, c):
                    return (c.Red(), c.Green(), c.Blue())
            return _default_palette[solid_idx % len(_default_palette)]

        def _tessellate_shape(sub_shape, fallback_rgba: list[float]):
            """Tessellate all faces of a shape and append to result arrays."""
            nonlocal vert_offset
            face_explorer = TopExp_Explorer(sub_shape, TopAbs_FACE)
            while face_explorer.More():
                face = TopoDS.Face_s(face_explorer.Current())

                # Per-face color lookup (prefer face color over solid/default)
                face_rgba = fallback_rgba
                if color_tool is not None:
                    from OCP.Quantity import Quantity_Color
                    from OCP.XCAFDoc import XCAFDoc_ColorGen, XCAFDoc_ColorSurf
                    c = Quantity_Color()
                    if color_tool.GetColor(face, XCAFDoc_ColorSurf, c) or \
                       color_tool.GetColor(face, XCAFDoc_ColorGen, c):
                        face_rgba = [c.Red(), c.Green(), c.Blue(), 1.0]

                loc = TopLoc_Location()
                triangulation = BRep_Tool.Triangulation_s(face, loc)
                if triangulation is None:
                    face_explorer.Next()
                    continue

                trsf = loc.Transformation()
                n_nodes = triangulation.NbNodes()
                n_tris = triangulation.NbTriangles()

                for i in range(1, n_nodes + 1):
                    pnt = triangulation.Node(i)
                    pnt_transformed = pnt.Transformed(trsf)
                    all_verts.append(
                        [pnt_transformed.X(), pnt_transformed.Y(), pnt_transformed.Z()]
                    )

                for i in range(1, n_tris + 1):
                    tri = triangulation.Triangle(i)
                    n1, n2, n3 = tri.Get()
                    all_faces.append([
                        n1 - 1 + vert_offset,
                        n2 - 1 + vert_offset,
                        n3 - 1 + vert_offset,
                    ])
                    all_colors.append(face_rgba)

                vert_offset += n_nodes
                face_explorer.Next()

        # Iterate solids for proper color grouping
        solid_explorer = TopExp_Explorer(shape, TopAbs_SOLID)
        solid_idx = 0
        has_solids = False
        while solid_explorer.More():
            has_solids = True
            solid = TopoDS.Solid_s(solid_explorer.Current())
            rgb = _get_solid_color(solid, solid_idx)
            rgba = [rgb[0], rgb[1], rgb[2], 1.0]
            _tessellate_shape(solid, rgba)
            solid_idx += 1
            solid_explorer.Next()

        # Fallback: if no solids found, tessellate all faces directly
        if not has_solids:
            rgba = [0.7, 0.7, 0.75, 1.0]
            _tessellate_shape(shape, rgba)

        if not all_verts or not all_faces:
            _logger.error("STEP file produced empty mesh: %s", step_path)
            return None

        vertices = np.array(all_verts, dtype=np.float64)
        faces = np.array(all_faces, dtype=np.int32)
        face_colors = np.array(all_colors, dtype=np.float32)

        # Centre the mesh on its bounding-box midpoint
        bbox_min = vertices.min(axis=0)
        bbox_max = vertices.max(axis=0)
        centre = (bbox_min + bbox_max) / 2.0
        vertices -= centre

        return vertices, faces, face_colors

    except Exception:
        _logger.exception("Error loading STEP file: %s", step_path)
        return None


def mesh_bounding_box(vertices: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return (min_corner, max_corner) of an (N, 3) vertex array."""
    return vertices.min(axis=0), vertices.max(axis=0)


# ---------------------------------------------------------------------------
# 2-D orthographic projection (filled, colored)
# ---------------------------------------------------------------------------


def project_mesh_to_2d(
    vertices: np.ndarray,
    faces: np.ndarray,
    rotation: np.ndarray,
    face_colors: np.ndarray | None = None,
    height_px: int = 1000,
    margin_fraction: float = 0.05,
    bg_color: tuple[int, int, int, int] = (255, 255, 255, 0),
) -> QPixmap | None:
    """Render an orthographic 2-D projection of a mesh with per-face colors.

    Draws filled triangles using a painter's algorithm (back-to-front Z-sort).

    Args:
        vertices: ``(N, 3)`` mesh vertices (centred at origin).
        faces: ``(M, 3)`` triangle indices.
        rotation: ``(3, 3)`` rotation matrix applied to vertices before projection.
        face_colors: ``(M, 4)`` RGBA float32 (0-1) per face. If None, uses grey.
        height_px: Pixel height of the output image.
        margin_fraction: Fractional margin around the projected bounds.
        bg_color: RGBA background colour.

    Returns:
        ``QPixmap`` with the rendered image, or ``None`` on failure.
    """
    try:
        from PyQt6.QtCore import QPointF, Qt
        from PyQt6.QtGui import QBrush, QColor, QImage, QPainter, QPixmap, QPolygonF

        rotated = (rotation @ vertices.T).T  # (N, 3)

        # Project: drop Z, keep X (right) and Y (up)
        proj_x = rotated[:, 0]
        proj_y = rotated[:, 1]
        proj_z = rotated[:, 2]

        x_min, x_max = proj_x.min(), proj_x.max()
        y_min, y_max = proj_y.min(), proj_y.max()
        x_range = x_max - x_min or 1.0
        y_range = y_max - y_min or 1.0

        margin = max(x_range, y_range) * margin_fraction
        x_min -= margin
        x_max += margin
        y_min -= margin
        y_max += margin
        x_range = x_max - x_min
        y_range = y_max - y_min

        aspect = x_range / y_range
        height = height_px
        width = max(1, int(height * aspect))

        def to_px(x: float, y: float) -> tuple[float, float]:
            px = (x - x_min) / x_range * (width - 1)
            py = (1.0 - (y - y_min) / y_range) * (height - 1)
            return px, py

        img = QImage(width, height, QImage.Format.Format_ARGB32)
        img.fill(QColor(*bg_color))

        painter = QPainter(img)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        # Compute per-face average Z for depth sorting (painter's algorithm)
        face_z = np.mean(proj_z[faces], axis=1)
        sort_order = np.argsort(face_z)  # back to front

        # Default face color if none provided
        default_rgba = np.array([0.7, 0.7, 0.75, 1.0], dtype=np.float32)

        for fi in sort_order:
            f = faces[fi]

            if face_colors is not None and fi < len(face_colors):
                rgba = face_colors[fi]
            else:
                rgba = default_rgba

            # Simple shading: darken faces facing away from light
            # Compute face normal in rotated space
            v0, v1, v2 = rotated[f[0]], rotated[f[1]], rotated[f[2]]
            edge1 = v1 - v0
            edge2 = v2 - v0
            normal = np.cross(edge1, edge2)
            norm_len = np.linalg.norm(normal)
            if norm_len > 1e-12:
                normal /= norm_len
                # Light from upper-front-right
                light_dir = np.array([0.3, 0.4, 0.9])
                light_dir /= np.linalg.norm(light_dir)
                shade = max(0.0, float(np.dot(normal, light_dir)))
                # Ambient + diffuse
                brightness = 0.45 + 0.55 * shade
            else:
                brightness = 0.6

            r = int(min(255, rgba[0] * brightness * 255))
            g = int(min(255, rgba[1] * brightness * 255))
            b = int(min(255, rgba[2] * brightness * 255))
            a = int(rgba[3] * 255)

            color = QColor(r, g, b, a)
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.PenStyle.NoPen)

            # Draw filled triangle
            pts = [QPointF(*to_px(proj_x[f[i]], proj_y[f[i]])) for i in range(3)]
            polygon = QPolygonF(pts)
            painter.drawPolygon(polygon)

        painter.end()
        return QPixmap.fromImage(img)

    except Exception:
        _logger.exception("Error projecting mesh to 2D")
        return None


# ---------------------------------------------------------------------------
# Preset view rotations (matching pyqtgraph's viewMatrix for Z-up models)
# ---------------------------------------------------------------------------

# Front: looking along -Y, Z-up (elev=0, azim=90)
VIEW_FRONT = np.array([
    [-1, 0, 0],
    [0, 0, 1],
    [0, 1, 0],
], dtype=np.float64)

# Back: looking along +Y, Z-up (elev=0, azim=-90)
VIEW_BACK = np.array([
    [1, 0, 0],
    [0, 0, 1],
    [0, -1, 0],
], dtype=np.float64)

# Top: looking along -Z (elev=90, azim=0)
VIEW_TOP = np.array([
    [0, 1, 0],
    [-1, 0, 0],
    [0, 0, 1],
], dtype=np.float64)

# Bottom: looking along +Z (elev=-90, azim=0)
VIEW_BOTTOM = np.array([
    [0, 1, 0],
    [1, 0, 0],
    [0, 0, -1],
], dtype=np.float64)

# Left: looking along +X, Z-up (elev=0, azim=180)
VIEW_LEFT = np.array([
    [0, -1, 0],
    [0, 0, 1],
    [-1, 0, 0],
], dtype=np.float64)

# Right: looking along -X, Z-up (elev=0, azim=0)
VIEW_RIGHT = np.array([
    [0, 1, 0],
    [0, 0, 1],
    [1, 0, 0],
], dtype=np.float64)

PRESET_VIEWS: dict[str, np.ndarray] = {
    "Front": VIEW_FRONT,
    "Back": VIEW_BACK,
    "Top": VIEW_TOP,
    "Bottom": VIEW_BOTTOM,
    "Left": VIEW_LEFT,
    "Right": VIEW_RIGHT,
}

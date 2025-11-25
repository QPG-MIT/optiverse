"""
OpenGL-accelerated ray rendering widget.

Uses GPU vertex buffers and shaders to render rays at 60fps, even with thousands
of segments. This replaces Qt's slow software rasterizer with hardware acceleration.
"""
from __future__ import annotations

import logging
import numpy as np
from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtOpenGL import QOpenGLShaderProgram, QOpenGLShader, QOpenGLVertexArrayObject, QOpenGLBuffer

_logger = logging.getLogger(__name__)

try:
    from OpenGL import GL
    OPENGL_AVAILABLE = True
except ImportError:
    OPENGL_AVAILABLE = False
    _logger.debug("PyOpenGL not available. Install with: pip install PyOpenGL")


class RayOpenGLWidget(QOpenGLWidget):
    """
    Hardware-accelerated ray rendering using OpenGL.

    This widget overlays the QGraphicsView and renders rays using GPU vertex buffers.
    Achieves 60fps with 10,000+ segments by leveraging hardware acceleration.

    Performance:
    - Software rasterizer: 100ms per 500 segments (2.5 fps for 4 groups)
    - OpenGL: <1ms for all rays combined (1000+ fps, v-synced to 60fps)

    Architecture:
    - Transparent background (rays only, components rendered by QGraphicsView)
    - Syncs with view transform matrix for proper alignment
    - Single draw call for all rays (batched by vertex buffer)
    """

    def __init__(self, parent_view: QtWidgets.QGraphicsView):
        # Initialize parent class first
        super().__init__(parent=parent_view.viewport())

        # Configure OpenGL surface format (uses default format set in main.py)
        # The format is already configured globally, but we ensure transparency is enabled
        fmt = self.format()
        fmt.setAlphaBufferSize(8)  # CRITICAL: Enable alpha channel for transparency
        self.setFormat(fmt)

        self.view = parent_view
        self.ray_vertices = np.array([], dtype=np.float32)
        self.vertex_count = 0

        # OpenGL objects (created in initializeGL)
        self.vao = None
        self.vbo = None
        self.shader_program = None

        # View transform
        self.view_matrix = np.eye(3, dtype=np.float32)
        self.viewport_size = np.array([800, 600], dtype=np.float32)

        # Line width (in pixels)
        self.line_width = 2.0

        # Performance tracking
        self.frame_count = 0

        # Widget attributes for transparency
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_OpaquePaintEvent, False)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_NoSystemBackground, True)

    def initializeGL(self):
        """Initialize OpenGL context, shaders, and buffers."""
        if not OPENGL_AVAILABLE:
            _logger.debug("OpenGL not available - ray rendering will be disabled")
            return

        # Set clear color to FULLY TRANSPARENT (critical for overlay)
        GL.glClearColor(0.0, 0.0, 0.0, 0.0)  # RGBA = (0, 0, 0, 0) = transparent black

        # Enable blending for transparency
        GL.glEnable(GL.GL_BLEND)
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)

        # Enable line smoothing (antialiasing)
        GL.glEnable(GL.GL_LINE_SMOOTH)
        GL.glHint(GL.GL_LINE_SMOOTH_HINT, GL.GL_NICEST)

        # Create shader program
        self.shader_program = QOpenGLShaderProgram(self)

        # Vertex shader (GLSL 1.20 for macOS compatibility)
        vertex_shader_source = """
        #version 120
        attribute vec2 position;
        attribute vec4 color;

        uniform mat3 viewMatrix;
        uniform vec2 viewportSize;

        varying vec4 vertexColor;

        void main() {
            // Transform from scene coordinates to viewport coordinates
            vec3 viewPos = viewMatrix * vec3(position, 1.0);

            // Flip Y coordinate (Qt uses Y-down, OpenGL uses Y-up)
            viewPos.y = viewportSize.y - viewPos.y;

            // Normalize to NDC (-1 to 1)
            vec2 ndc = (viewPos.xy / viewportSize) * 2.0 - 1.0;

            gl_Position = vec4(ndc, 0.0, 1.0);
            vertexColor = color;
        }
        """

        # Fragment shader (GLSL 1.20 for macOS compatibility)
        fragment_shader_source = """
        #version 120
        varying vec4 vertexColor;

        void main() {
            gl_FragColor = vertexColor;
        }
        """

        # Compile shaders
        if not self.shader_program.addShaderFromSourceCode(QOpenGLShader.ShaderTypeBit.Vertex, vertex_shader_source):
            _logger.error("Vertex shader error: %s", self.shader_program.log())
            return

        if not self.shader_program.addShaderFromSourceCode(QOpenGLShader.ShaderTypeBit.Fragment, fragment_shader_source):
            _logger.error("Fragment shader error: %s", self.shader_program.log())
            return

        if not self.shader_program.link():
            _logger.error("Shader linking error: %s", self.shader_program.log())
            return

        # Create VAO (Vertex Array Object)
        self.vao = QOpenGLVertexArrayObject()
        if not self.vao.create():
            _logger.error("Failed to create VAO")
            return

        # Create VBO (Vertex Buffer Object)
        self.vbo = QOpenGLBuffer(QOpenGLBuffer.Type.VertexBuffer)
        if not self.vbo.create():
            _logger.error("Failed to create VBO")
            return

        _logger.info("OpenGL initialized: Shaders compiled, buffers created")

    def paintGL(self):
        """Render rays using OpenGL."""
        if not OPENGL_AVAILABLE:
            return

        # Always clear with transparent background (even if no rays)
        GL.glClear(GL.GL_COLOR_BUFFER_BIT)

        if self.vertex_count == 0:
            return  # Nothing to render, but background is transparent

        # Bind shader program
        if not self.shader_program.bind():
            return

        # Set uniforms
        self.shader_program.setUniformValue("viewMatrix",
                                           QtGui.QMatrix3x3(self.view_matrix.flatten().tolist()))
        self.shader_program.setUniformValue("viewportSize",
                                           QtCore.QPointF(self.viewport_size[0], self.viewport_size[1]))

        # Bind VAO
        self.vao.bind()

        # Set line width
        GL.glLineWidth(self.line_width)

        # Draw lines
        GL.glDrawArrays(GL.GL_LINES, 0, self.vertex_count)

        # Unbind
        self.vao.release()
        self.shader_program.release()

        # Track frames
        self.frame_count += 1
        if self.frame_count % 300 == 0:
            _logger.debug("OpenGL: Rendered %d frames, %d segments", self.frame_count, self.vertex_count // 2)

    def resizeGL(self, w: int, h: int):
        """Handle widget resize."""
        GL.glViewport(0, 0, w, h)
        self.viewport_size = np.array([w, h], dtype=np.float32)

    def update_rays(self, ray_paths: list, width_px: float):
        """
        Update ray data and upload to GPU.

        Args:
            ray_paths: List of RayPath objects
            width_px: Line width in pixels
        """
        if not OPENGL_AVAILABLE or not ray_paths:
            self.vertex_count = 0
            self.update()
            return

        self.line_width = width_px

        # Convert ray paths to vertex data
        # Format: [x1, y1, r1, g1, b1, a1, x2, y2, r2, g2, b2, a2, ...]
        vertex_data = []

        for ray_path in ray_paths:
            if len(ray_path.points) < 2:
                continue

            r, g, b, a = ray_path.rgba
            # Normalize colors to 0-1 range
            r_norm = r / 255.0
            g_norm = g / 255.0
            b_norm = b / 255.0
            a_norm = a / 255.0

            # Create line segments
            for i in range(len(ray_path.points) - 1):
                p1 = ray_path.points[i]
                p2 = ray_path.points[i + 1]

                # Vertex 1 (position + color)
                vertex_data.extend([
                    float(p1[0]), float(p1[1]),  # position
                    r_norm, g_norm, b_norm, a_norm  # color
                ])

                # Vertex 2 (position + color)
                vertex_data.extend([
                    float(p2[0]), float(p2[1]),  # position
                    r_norm, g_norm, b_norm, a_norm  # color
                ])

        # Convert to numpy array
        self.ray_vertices = np.array(vertex_data, dtype=np.float32)
        self.vertex_count = len(self.ray_vertices) // 6  # 6 floats per vertex

        # Upload to GPU
        self._upload_to_gpu()

        # Trigger repaint
        self.update()

        _logger.debug("Uploaded %d ray segments to GPU", self.vertex_count // 2)

    def _upload_to_gpu(self):
        """Upload vertex data to GPU buffer."""
        if not OPENGL_AVAILABLE or self.vertex_count == 0:
            return

        # Make context current
        self.makeCurrent()

        # Bind VAO
        self.vao.bind()

        # Bind and fill VBO
        self.vbo.bind()
        self.vbo.allocate(self.ray_vertices.tobytes(), self.ray_vertices.nbytes)

        # Get attribute locations from shader
        position_location = self.shader_program.attributeLocation("position")
        color_location = self.shader_program.attributeLocation("color")

        # Set up vertex attributes
        # Position attribute
        if position_location >= 0:
            GL.glEnableVertexAttribArray(position_location)
            GL.glVertexAttribPointer(position_location, 2, GL.GL_FLOAT, GL.GL_FALSE, 6 * 4, None)

        # Color attribute
        if color_location >= 0:
            GL.glEnableVertexAttribArray(color_location)
            GL.glVertexAttribPointer(color_location, 4, GL.GL_FLOAT, GL.GL_FALSE, 6 * 4, GL.ctypes.c_void_p(2 * 4))

        # Unbind
        self.vbo.release()
        self.vao.release()

        self.doneCurrent()

    def set_view_transform(self, transform: QtGui.QTransform):
        """
        Update view transform matrix for coordinate conversion.

        Args:
            transform: Qt transform from scene to viewport coordinates
        """
        # Extract 3x3 matrix from QTransform
        self.view_matrix = np.array([
            [transform.m11(), transform.m21(), transform.m31()],
            [transform.m12(), transform.m22(), transform.m32()],
            [transform.m13(), transform.m23(), transform.m33()]
        ], dtype=np.float32)

        # Trigger repaint with new transform
        self.update()

    def clear(self):
        """Clear all rays."""
        self.vertex_count = 0
        self.update()




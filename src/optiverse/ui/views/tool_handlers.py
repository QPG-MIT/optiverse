"""Tool mode handlers for inspect and path measure tools."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, List, Optional

import numpy as np
from PyQt6 import QtCore, QtGui, QtWidgets

if TYPE_CHECKING:
    from ...raytracing import RayPath
    from ...objects import GraphicsView
    from ...core.undo_stack import UndoStack


def point_to_segment_distance(point: np.ndarray, seg_start: np.ndarray, seg_end: np.ndarray) -> float:
    """
    Calculate the minimum distance from a point to a line segment.
    
    Args:
        point: The point to check (numpy array)
        seg_start: Start of line segment (numpy array)
        seg_end: End of line segment (numpy array)
        
    Returns:
        Minimum distance from point to the line segment
    """
    # Vector from seg_start to seg_end
    segment = seg_end - seg_start
    segment_len_sq = np.dot(segment, segment)
    
    # Handle degenerate case (segment is a point)
    if segment_len_sq < 1e-10:
        return float(np.linalg.norm(point - seg_start))
    
    # Project point onto the line defined by the segment
    # t = 0 means point projects to seg_start
    # t = 1 means point projects to seg_end
    t = np.dot(point - seg_start, segment) / segment_len_sq
    
    # Clamp t to [0, 1] to stay within the segment
    t = max(0.0, min(1.0, t))
    
    # Find the closest point on the segment
    closest_point = seg_start + t * segment
    
    # Return distance to the closest point
    return float(np.linalg.norm(point - closest_point))


class InspectToolHandler:
    """
    Handler for the ray inspect tool.
    
    Allows users to click on rays to view their properties (position, intensity,
    wavelength, polarization state).
    """
    
    def __init__(
        self,
        view: "GraphicsView",
        get_ray_data: Callable[[], List["RayPath"]],
        parent_widget: QtWidgets.QWidget,
    ):
        """
        Initialize the inspect tool handler.
        
        Args:
            view: The graphics view for zoom level calculation
            get_ray_data: Callable to get current ray data
            parent_widget: Parent widget for dialogs
        """
        self.view = view
        self._get_ray_data = get_ray_data
        self.parent_widget = parent_widget
    
    def handle_click(self, scene_pos: QtCore.QPointF) -> bool:
        """
        Handle click in inspect mode to display ray information.
        
        Args:
            scene_pos: Click position in scene coordinates
            
        Returns:
            True if a ray was found and info displayed, False otherwise
        """
        ray_data_list = self._get_ray_data()
        click_pt = np.array([scene_pos.x(), scene_pos.y()])
        
        # Find the nearest ray segment within tolerance
        # Use a tolerance that scales with zoom level for better UX
        transform = self.view.transform()
        scale_factor = transform.m11()  # Horizontal scale (zoom level)
        tolerance_px = 15.0  # pixels - generous click radius
        tolerance = tolerance_px / max(scale_factor, 0.01)  # Convert to scene units (mm)
        
        best_ray = None
        best_distance = float('inf')
        best_point_idx = None
        
        for i, ray_data in enumerate(ray_data_list):
            # Check each line segment in the ray path
            points = ray_data.points
            for j in range(len(points) - 1):
                # Calculate distance to the line segment between consecutive points
                dist = point_to_segment_distance(click_pt, points[j], points[j + 1])
                
                if dist < best_distance and dist < tolerance:
                    best_distance = dist
                    best_ray = ray_data
                    # Use the closest endpoint of the segment
                    dist_to_start = np.linalg.norm(click_pt - points[j])
                    dist_to_end = np.linalg.norm(click_pt - points[j + 1])
                    best_point_idx = j if dist_to_start < dist_to_end else j + 1
        
        if best_ray is not None:
            # Display the ray information
            self._show_ray_info_dialog(best_ray, best_point_idx)
            return True
        else:
            QtWidgets.QMessageBox.information(
                self.parent_widget,
                "No Ray Found",
                "No ray found near the clicked position.\nTry clicking closer to a ray."
            )
            return False
    
    def _show_ray_info_dialog(self, ray_data: "RayPath", point_idx: int) -> None:
        """Display a dialog with ray polarization and intensity information."""
        # Get position
        point = ray_data.points[point_idx]
        x_mm, y_mm = point[0], point[1]
        
        # Get intensity (from alpha channel)
        intensity = ray_data.rgba[3] / 255.0
        
        # Get polarization state
        pol = ray_data.polarization
        
        # Format polarization info
        if pol is not None:
            ex, ey = pol.jones_vector[0], pol.jones_vector[1]
            # Calculate Stokes parameters
            I_total = abs(ex)**2 + abs(ey)**2
            Q = abs(ex)**2 - abs(ey)**2
            U = 2 * np.real(ex * np.conj(ey))
            V = 2 * np.imag(ex * np.conj(ey))
            
            # Calculate degree of polarization
            pol_degree = np.sqrt(Q**2 + U**2 + V**2) / I_total if I_total > 0 else 0
            
            # Linear polarization angle
            pol_angle_rad = 0.5 * np.arctan2(U, Q)
            pol_angle_deg = np.degrees(pol_angle_rad)
            
            pol_text = f"""Jones Vector: [{ex:.4f}, {ey:.4f}]

Stokes Parameters:
  I = {I_total:.4f}
  Q = {Q:.4f}
  U = {U:.4f}
  V = {V:.4f}

Degree of Polarization: {pol_degree:.2%}
Linear Polarization Angle: {pol_angle_deg:.2f}°"""
        else:
            pol_text = "No polarization information available"
        
        # Get wavelength
        wavelength_text = f"{ray_data.wavelength_nm:.1f} nm" if ray_data.wavelength_nm > 0 else "Not specified"
        
        # Create info dialog
        dialog = QtWidgets.QDialog(self.parent_widget)
        dialog.setWindowTitle("Ray Information")
        dialog.setMinimumWidth(400)
        
        layout = QtWidgets.QVBoxLayout(dialog)
        
        # Position info
        pos_label = QtWidgets.QLabel(f"<b>Position:</b> ({x_mm:.2f}, {y_mm:.2f}) mm")
        layout.addWidget(pos_label)
        
        # Intensity info
        intensity_label = QtWidgets.QLabel(f"<b>Intensity:</b> {intensity:.2%}")
        layout.addWidget(intensity_label)
        
        # Wavelength info
        wl_label = QtWidgets.QLabel(f"<b>Wavelength:</b> {wavelength_text}")
        layout.addWidget(wl_label)
        
        layout.addSpacing(10)
        
        # Polarization info
        pol_title = QtWidgets.QLabel("<b>Polarization State:</b>")
        layout.addWidget(pol_title)
        
        pol_text_widget = QtWidgets.QTextEdit()
        pol_text_widget.setPlainText(pol_text)
        pol_text_widget.setReadOnly(True)
        pol_text_widget.setMaximumHeight(200)
        layout.addWidget(pol_text_widget)
        
        # Close button
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addStretch()
        close_btn = QtWidgets.QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        button_layout.addWidget(close_btn)
        layout.addLayout(button_layout)
        
        dialog.exec()


class PathMeasureToolHandler:
    """
    Handler for the path measure tool.
    
    Allows users to measure optical path length along rays with a two-click workflow.
    """
    
    def __init__(
        self,
        scene: QtWidgets.QGraphicsScene,
        view: "GraphicsView",
        undo_stack: "UndoStack",
        get_ray_data: Callable[[], List["RayPath"]],
        parent_widget: QtWidgets.QWidget,
        on_complete: Callable[[], None] = None,
    ):
        """
        Initialize the path measure tool handler.
        
        Args:
            scene: The graphics scene
            view: The graphics view for zoom level calculation
            undo_stack: Undo stack for adding measurement items
            get_ray_data: Callable to get current ray data
            parent_widget: Parent widget for dialogs
            on_complete: Optional callback when measurement is complete
        """
        self.scene = scene
        self.view = view
        self.undo_stack = undo_stack
        self._get_ray_data = get_ray_data
        self.parent_widget = parent_widget
        self.on_complete = on_complete
        
        # State for two-click workflow
        self._state: Optional[str] = None  # 'waiting_first_click' or 'waiting_second_click'
        self._ray_index: Optional[int] = None
        self._start_param: Optional[float] = None
        self._temp_item = None
    
    def activate(self) -> None:
        """Activate the path measure tool."""
        self._state = 'waiting_first_click'
        self._ray_index = None
        self._start_param = None
        self._temp_item = None
    
    def deactivate(self) -> None:
        """Deactivate the path measure tool and clean up."""
        self._state = None
        self._ray_index = None
        self._start_param = None
        # Remove temporary item if exists
        if self._temp_item and self.scene:
            self.scene.removeItem(self._temp_item)
            self._temp_item = None
    
    def is_active(self) -> bool:
        """Check if the tool is currently active."""
        return self._state is not None
    
    def handle_click(self, scene_pos: QtCore.QPointF) -> bool:
        """
        Handle click in path measure mode.
        
        Args:
            scene_pos: Click position in scene coordinates
            
        Returns:
            True if click was handled, False otherwise
        """
        from optiverse.objects.annotations.path_measure_item import PathMeasureItem
        from ...core.undo_commands import AddItemCommand, AddMultipleItemsCommand
        
        ray_data_list = self._get_ray_data()
        click_pt = np.array([scene_pos.x(), scene_pos.y()])
        
        # Find the nearest ray segment within tolerance
        transform = self.view.transform()
        scale_factor = transform.m11()
        tolerance_px = 25.0  # Generous tolerance for easy ray selection
        tolerance = tolerance_px / max(scale_factor, 0.01)
        
        best_ray_index = -1
        best_distance = float('inf')
        best_param = 0.0
        
        for i, ray_data in enumerate(ray_data_list):
            points = ray_data.points
            total_length = sum(np.linalg.norm(points[j + 1] - points[j]) for j in range(len(points) - 1))
            
            if total_length < 1e-6:
                continue
            
            accumulated = 0.0
            for j in range(len(points) - 1):
                p1, p2 = points[j], points[j + 1]
                segment_vec = p2 - p1
                segment_len_sq = np.dot(segment_vec, segment_vec)
                segment_len = np.sqrt(segment_len_sq)
                
                if segment_len < 1e-6:
                    continue
                
                # Calculate distance to segment
                to_click = click_pt - p1
                t = np.clip(np.dot(to_click, segment_vec) / segment_len_sq, 0.0, 1.0)
                closest_on_segment = p1 + t * segment_vec
                dist = np.linalg.norm(click_pt - closest_on_segment)
                
                if dist < best_distance and dist < tolerance:
                    best_distance = dist
                    best_ray_index = i
                    best_param = (accumulated + t * segment_len) / total_length
                
                accumulated += segment_len
        
        if best_ray_index < 0:
            QtWidgets.QMessageBox.information(
                self.parent_widget,
                "No Ray Found",
                "No ray found near the clicked position.\nTry clicking closer to a ray."
            )
            return False
        
        if self._state == 'waiting_first_click':
            return self._handle_first_click(best_ray_index, best_param, ray_data_list)
        elif self._state == 'waiting_second_click':
            return self._handle_second_click(best_ray_index, best_param, scene_pos, ray_data_list)
        
        return False
    
    def _handle_first_click(
        self, ray_index: int, param: float, ray_data_list: List["RayPath"]
    ) -> bool:
        """Handle the first click (set start point)."""
        from optiverse.objects.annotations.path_measure_item import PathMeasureItem
        
        self._ray_index = ray_index
        self._start_param = param
        self._state = 'waiting_second_click'
        
        ray_data = ray_data_list[ray_index]
        self._temp_item = PathMeasureItem(
            ray_path_points=ray_data.points,
            start_param=param,
            end_param=param,
            ray_index=ray_index
        )
        # Temp preview item added directly (not undoable, removed on second click)
        self.scene.addItem(self._temp_item)
        
        QtWidgets.QToolTip.showText(
            QtGui.QCursor.pos(),
            "Start point set. Click again on the SAME ray to set end point.\n\n"
            "⚠️ At beam splitters: Each path is separate."
        )
        return True
    
    def _handle_second_click(
        self,
        best_ray_index: int,
        best_param: float,
        scene_pos: QtCore.QPointF,
        ray_data_list: List["RayPath"],
    ) -> bool:
        """Handle the second click (set end point and create measurement)."""
        from optiverse.objects.annotations.path_measure_item import PathMeasureItem
        from ...core.undo_commands import AddItemCommand, AddMultipleItemsCommand
        
        # Smart ray matching with multiple strategies for dense bundles
        original_ray = ray_data_list[self._ray_index]
        clicked_ray = ray_data_list[best_ray_index]
        
        allow_ray = False
        use_clicked_ray = False
        
        if best_ray_index == self._ray_index:
            # Strategy 1: Same ray - always allowed
            allow_ray = True
        else:
            # Different ray - check if acceptable
            
            # Strategy 2: Beam splitter siblings (share starting point)
            if len(original_ray.points) > 0 and len(clicked_ray.points) > 0:
                if np.linalg.norm(original_ray.points[0] - clicked_ray.points[0]) < 1.0:
                    allow_ray = True
            
            # Strategy 3: Parallel bundle detection
            if not allow_ray and len(clicked_ray.points) > 1:
                first_click_pos = self._param_to_position(ray_data_list, self._ray_index, self._start_param)
                if first_click_pos is not None:
                    min_dist = float('inf')
                    for j in range(len(clicked_ray.points) - 1):
                        dist = point_to_segment_distance(
                            first_click_pos,
                            clicked_ray.points[j],
                            clicked_ray.points[j + 1]
                        )
                        min_dist = min(min_dist, dist)
                    
                    if min_dist < 15.0:
                        allow_ray = True
                        use_clicked_ray = True
        
        if not allow_ray:
            QtWidgets.QMessageBox.warning(
                self.parent_widget,
                "Different Ray",
                "Please click on the same ray or a nearby parallel ray for the end point."
            )
            return False
        
        # Calculate measurement parameters
        click_pt = np.array([scene_pos.x(), scene_pos.y()])
        
        if use_clicked_ray:
            end_param_on_original = self._find_param_on_ray(ray_data_list, self._ray_index, click_pt)
            start_param = min(self._start_param, end_param_on_original)
            end_param = max(self._start_param, end_param_on_original)
            best_ray_index = self._ray_index
        elif best_ray_index != self._ray_index:
            best_param = self._find_param_on_ray(ray_data_list, self._ray_index, click_pt)
            start_param = min(self._start_param, best_param)
            end_param = max(self._start_param, best_param)
            best_ray_index = self._ray_index
        else:
            start_param = min(self._start_param, best_param)
            end_param = max(self._start_param, best_param)
        
        # Remove temp preview item
        if self._temp_item:
            self.scene.removeItem(self._temp_item)
            self._temp_item = None
        
        # Create main path measure item
        ray_data = ray_data_list[best_ray_index]
        path_measure = PathMeasureItem(
            ray_path_points=ray_data.points,
            start_param=start_param,
            end_param=end_param,
            ray_index=best_ray_index
        )
        
        # Beam splitter auto-detection: collect all items to add
        items_to_add = [path_measure]
        if len(ray_data_list) > 1 and len(ray_data.points) > 0:
            start_pos = ray_data.points[0]
            for sibling_idx, sibling_ray in enumerate(ray_data_list):
                if sibling_idx != best_ray_index and len(sibling_ray.points) > 0:
                    if np.linalg.norm(start_pos - sibling_ray.points[0]) < 1.0:
                        sibling_measure = PathMeasureItem(
                            ray_path_points=sibling_ray.points,
                            start_param=start_param,
                            end_param=end_param,
                            ray_index=sibling_idx
                        )
                        items_to_add.append(sibling_measure)
        
        # Add items via undo stack
        if len(items_to_add) == 1:
            cmd = AddItemCommand(self.scene, items_to_add[0])
        else:
            cmd = AddMultipleItemsCommand(self.scene, items_to_add)
        
        self.undo_stack.push(cmd)
        
        # Select the main path measure item
        path_measure.setSelected(True)
        
        # Reset state
        self._state = None
        self._ray_index = None
        self._start_param = None
        
        # Show result tooltip
        tip_text = (
            f"Created {len(items_to_add)} measurements (beam splitter)"
            if len(items_to_add) > 1
            else f"Path measurement: {path_measure._segment_length:.2f} mm"
        )
        QtWidgets.QToolTip.showText(QtGui.QCursor.pos(), tip_text)
        
        # Call completion callback
        if self.on_complete:
            self.on_complete()
        
        return True
    
    def _param_to_position(
        self, ray_data_list: List["RayPath"], ray_index: int, param: float
    ) -> Optional[np.ndarray]:
        """Convert parameter [0, 1] on a ray to actual scene position."""
        if ray_index < 0 or ray_index >= len(ray_data_list):
            return None
        
        ray_data = ray_data_list[ray_index]
        points = ray_data.points
        
        if len(points) < 2:
            return points[0].copy() if len(points) == 1 else None
        
        total_length = sum(np.linalg.norm(points[j+1] - points[j]) for j in range(len(points)-1))
        if total_length < 1e-6:
            return points[0].copy()
        
        target_dist = param * total_length
        accumulated = 0.0
        
        for j in range(len(points) - 1):
            p1, p2 = points[j], points[j+1]
            segment_len = np.linalg.norm(p2 - p1)
            
            if accumulated + segment_len >= target_dist:
                t = (target_dist - accumulated) / segment_len if segment_len > 0 else 0
                return p1 + t * (p2 - p1)
            
            accumulated += segment_len
        
        return points[-1].copy()
    
    def _find_param_on_ray(
        self, ray_data_list: List["RayPath"], ray_index: int, click_pt: np.ndarray
    ) -> float:
        """Find the parameter [0, 1] on a specific ray closest to the clicked point."""
        ray_data = ray_data_list[ray_index]
        points = ray_data.points
        
        total_length = sum(np.linalg.norm(points[j + 1] - points[j]) for j in range(len(points) - 1))
        if total_length < 1e-6:
            return 0.0
        
        best_distance = float('inf')
        best_param = 0.0
        accumulated = 0.0
        
        for j in range(len(points) - 1):
            p1, p2 = points[j], points[j + 1]
            segment_vec = p2 - p1
            segment_len_sq = np.dot(segment_vec, segment_vec)
            segment_len = np.sqrt(segment_len_sq)
            
            if segment_len < 1e-6:
                continue
            
            to_click = click_pt - p1
            t = np.clip(np.dot(to_click, segment_vec) / segment_len_sq, 0.0, 1.0)
            closest_on_segment = p1 + t * segment_vec
            dist = np.linalg.norm(click_pt - closest_on_segment)
            
            if dist < best_distance:
                best_distance = dist
                best_param = (accumulated + t * segment_len) / total_length
            
            accumulated += segment_len
        
        return best_param


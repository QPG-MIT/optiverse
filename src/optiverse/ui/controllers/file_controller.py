"""
File controller for handling save/load/autosave operations.

Extracts file management UI logic from MainWindow.
"""
from __future__ import annotations

import os
from typing import TYPE_CHECKING, Optional, Callable

from PyQt6 import QtCore, QtWidgets

from ...services.scene_file_manager import SceneFileManager
from ...services.error_handler import ErrorContext
from ...core.constants import AUTOSAVE_DEBOUNCE_MS

if TYPE_CHECKING:
    from ...services.log_service import LogService
    from ...core.undo_stack import UndoStack


class FileController(QtCore.QObject):
    """
    Controller for file operations (save, open, autosave).
    
    Wraps SceneFileManager and provides UI interactions.
    """
    
    # Signal emitted when file operations complete and trace should be updated
    traceRequested = QtCore.pyqtSignal()
    # Signal emitted when window title should be updated
    windowTitleChanged = QtCore.pyqtSignal(str)
    
    def __init__(
        self,
        scene: QtWidgets.QGraphicsScene,
        undo_stack: "UndoStack",
        log_service: "LogService",
        get_ray_data: Callable,
        parent_widget: QtWidgets.QWidget,
    ):
        super().__init__(parent_widget)
        
        self._parent = parent_widget
        self._undo_stack = undo_stack
        self._is_modified = False
        
        # Create file manager
        self.file_manager = SceneFileManager(
            scene=scene,
            log_service=log_service,
            get_ray_data=get_ray_data,
            on_modified=self._on_modified_changed,
            parent_widget=parent_widget,
        )
        
        # Autosave timer
        self._autosave_timer = QtCore.QTimer()
        self._autosave_timer.setSingleShot(True)
        self._autosave_timer.setInterval(AUTOSAVE_DEBOUNCE_MS)
        self._autosave_timer.timeout.connect(self._do_autosave)
        
        # Connect undo stack to modification tracking
        undo_stack.commandPushed.connect(self._on_command_pushed)
    
    @property
    def saved_file_path(self) -> Optional[str]:
        """Get the current saved file path."""
        return self.file_manager.saved_file_path
    
    @saved_file_path.setter
    def saved_file_path(self, value: Optional[str]):
        """Set the saved file path."""
        self.file_manager.saved_file_path = value
    
    @property
    def is_modified(self) -> bool:
        """Check if there are unsaved changes."""
        return self._is_modified
    
    def _on_command_pushed(self):
        """Handle command pushed - mark modified and schedule autosave."""
        self.mark_modified()
        self._schedule_autosave()
    
    def mark_modified(self):
        """Mark the scene as having unsaved changes."""
        self.file_manager.mark_modified()
    
    def mark_clean(self):
        """Mark the scene as saved (no unsaved changes)."""
        self.file_manager.mark_clean()
    
    def _on_modified_changed(self, is_modified: bool):
        """Callback when file manager's modified state changes."""
        self._is_modified = is_modified
        self._update_window_title()
    
    def _update_window_title(self):
        """Update window title to show file name and modified state."""
        if self.saved_file_path:
            filename = os.path.basename(self.saved_file_path)
            filename_no_ext = os.path.splitext(filename)[0]
            title = filename_no_ext
        else:
            title = "Untitled"
        
        if self._is_modified:
            title = f"{title} — Edited"
        
        self.windowTitleChanged.emit(title)
    
    def _schedule_autosave(self):
        """Schedule autosave with debouncing."""
        if self._autosave_timer:
            self._autosave_timer.stop()
            self._autosave_timer.start()
    
    def _do_autosave(self):
        """Perform autosave (delegated to file manager)."""
        self.file_manager.do_autosave()
    
    def check_autosave_recovery(self) -> bool:
        """Check for autosave on startup."""
        if self.file_manager.check_autosave_recovery():
            self.traceRequested.emit()
            return True
        return False
    
    def prompt_save_changes(self) -> QtWidgets.QMessageBox.StandardButton:
        """
        Prompt user to save unsaved changes.
        
        Returns:
            User's response (Save, Discard, Cancel)
        """
        reply = self.file_manager.prompt_save_changes()
        if reply == QtWidgets.QMessageBox.StandardButton.Save:
            self.save_assembly()
            if self._is_modified:
                return QtWidgets.QMessageBox.StandardButton.Cancel
        return reply
    
    def save_assembly(self):
        """Quick save: save to current file or prompt if new."""
        with ErrorContext("while saving assembly", suppress=True):
            if self.saved_file_path:
                self.file_manager.save_to_file(self.saved_file_path)
            else:
                self.save_assembly_as()
    
    def save_assembly_as(self):
        """Save As: always prompt for new file location."""
        with ErrorContext("while saving assembly", suppress=True):
            path, _ = QtWidgets.QFileDialog.getSaveFileName(
                self._parent, "Save Assembly As", "", "Optics Assembly (*.json)"
            )
            if path:
                self.file_manager.save_to_file(path)
    
    def open_assembly(self) -> bool:
        """
        Load all elements from JSON file.
        
        Returns:
            True if file was opened successfully
        """
        with ErrorContext("while opening assembly", suppress=True):
            if self._is_modified:
                reply = self.prompt_save_changes()
                if reply == QtWidgets.QMessageBox.StandardButton.Cancel:
                    return False
            
            path, _ = QtWidgets.QFileDialog.getOpenFileName(
                self._parent, "Open Assembly", "", "Optics Assembly (*.json)"
            )
            if not path:
                return False
            
            if not self.file_manager.open_file(path):
                return False
        
        # Clear undo history after loading
        self._undo_stack.clear()
        self.traceRequested.emit()
        return True


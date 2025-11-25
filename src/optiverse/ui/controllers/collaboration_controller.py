"""
Collaboration controller for handling collaboration sessions.

Extracts collaboration management UI logic from MainWindow.
"""
from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING, Optional

from PyQt6 import QtCore, QtWidgets

from ...core.log_categories import LogCategory

if TYPE_CHECKING:
    from ...services.collaboration_manager import CollaborationManager
    from ...services.log_service import LogService


class CollaborationController(QtCore.QObject):
    """
    Controller for collaboration operations (host, join, disconnect).
    
    Handles the UI interactions for collaboration while delegating
    network operations to CollaborationManager.
    """
    
    # Signals for UI updates
    connectionChanged = QtCore.pyqtSignal(bool)  # True = connected, False = disconnected
    statusChanged = QtCore.pyqtSignal(str)  # Status message
    
    def __init__(
        self,
        collaboration_manager: "CollaborationManager",
        log_service: "LogService",
        parent_widget: QtWidgets.QWidget,
    ):
        super().__init__(parent_widget)
        
        self._parent = parent_widget
        self._collab_manager = collaboration_manager
        self._log_service = log_service
        self._server_process: Optional[subprocess.Popen] = None
        
        # Connect manager signals
        collaboration_manager.status_changed.connect(self._on_status_changed)
    
    @property
    def is_connected(self) -> bool:
        """Check if connected to a collaboration session."""
        return self._collab_manager.is_connected
    
    def open_dialog(self):
        """Open dialog to connect to or host a collaboration session."""
        from ..views.collaboration_dialog import CollaborationDialog
        
        dialog = CollaborationDialog(self._parent)
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            info = dialog.get_connection_info()
            mode = info.get("mode", "connect")
            
            if mode == "host":
                self._host_session(info, dialog.server_process)
            else:
                self._join_session(info)
            
            self.connectionChanged.emit(True)
    
    def _host_session(self, info: dict, server_process: Optional[subprocess.Popen]):
        """Host a new collaboration session."""
        session_id = info.get("session_id", "default")
        user_id = info.get("user_id", "host")
        use_current_canvas = info.get("use_current_canvas", True)
        port = info.get("port", 8765)
        
        # Store server process if hosted locally
        if server_process:
            self._server_process = server_process
        
        # Create session as host
        self._collab_manager.create_session(
            session_id=session_id,
            user_id=user_id,
            use_current_canvas=use_current_canvas
        )
        
        # Connect to local server
        server_url = f"ws://localhost:{port}"
        self._collab_manager.connect_to_session(server_url, session_id, user_id)
        
        self._log_service.info(
            f"Created session '{session_id}' as host (current_canvas={use_current_canvas})",
            LogCategory.COLLABORATION
        )
    
    def _join_session(self, info: dict):
        """Join an existing collaboration session."""
        server_url = info.get("server_url", "ws://localhost:8765")
        session_id = info.get("session_id", "default")
        user_id = info.get("user_id", "user")
        
        # Join session as client
        self._collab_manager.join_session(server_url, session_id, user_id)
        
        self._log_service.info(
            f"Joining session '{session_id}' as client",
            LogCategory.COLLABORATION
        )
    
    def disconnect(self):
        """Disconnect from collaboration session."""
        self._collab_manager.disconnect()
        self._stop_server()
        self.connectionChanged.emit(False)
        self.statusChanged.emit("Not connected")
    
    def _stop_server(self):
        """Stop the local server if running."""
        if self._server_process:
            try:
                self._server_process.terminate()
                try:
                    self._server_process.wait(timeout=3)
                except TimeoutError:
                    self._server_process.kill()
                self._log_service.info("Stopped collaboration server", LogCategory.COLLABORATION)
            except OSError as e:
                self._log_service.warning(f"Error stopping server: {e}", LogCategory.COLLABORATION)
            finally:
                self._server_process = None
    
    def _on_status_changed(self, status: str):
        """Handle status changes from collaboration manager."""
        self.statusChanged.emit(f"Collaboration: {status}")
    
    def cleanup(self):
        """Clean up resources on shutdown."""
        self.disconnect()


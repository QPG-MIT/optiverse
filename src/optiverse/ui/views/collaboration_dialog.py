"""
Collaboration Dialog - UI for connecting to or hosting collaboration sessions.

Provides options to:
- Connect to an existing server
- Host a new server locally
"""
from __future__ import annotations

import sys
import subprocess
import socket
from pathlib import Path
from typing import Optional

from PyQt6 import QtCore, QtWidgets


class CollaborationDialog(QtWidgets.QDialog):
    """
    Dialog for collaboration configuration.
    
    Allows user to:
    - Connect to an existing collaboration server
    - Host a server on the local machine
    """
    
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Collaboration")
        self.setModal(True)
        self.setMinimumSize(500, 520)  # Adequate size to avoid geometry warnings
        
        self.mode = "connect"  # "connect" or "host"
        self.server_process: Optional[subprocess.Popen] = None
        
        self._build_ui()
        self._update_mode()
    
    def _build_ui(self) -> None:
        """Build the dialog UI."""
        layout = QtWidgets.QVBoxLayout(self)
        
        # Mode selection
        mode_group = QtWidgets.QGroupBox("Mode")
        mode_layout = QtWidgets.QVBoxLayout(mode_group)
        
        self.radio_connect = QtWidgets.QRadioButton("Connect to server")
        self.radio_host = QtWidgets.QRadioButton("Host server")
        self.radio_connect.setChecked(True)
        
        self.radio_connect.toggled.connect(self._on_mode_changed)
        self.radio_host.toggled.connect(self._on_mode_changed)
        
        mode_layout.addWidget(self.radio_connect)
        mode_layout.addWidget(self.radio_host)
        
        layout.addWidget(mode_group)
        
        # Connection settings (for connect mode)
        self.connect_group = QtWidgets.QGroupBox("Connection Settings")
        connect_layout = QtWidgets.QFormLayout(self.connect_group)
        
        self.server_url_edit = QtWidgets.QLineEdit("ws://localhost:8765")
        self.server_url_edit.setPlaceholderText("ws://hostname:port")
        connect_layout.addRow("Server URL:", self.server_url_edit)
        
        self.session_id_edit = QtWidgets.QLineEdit()
        self.session_id_edit.setPlaceholderText("session-name")
        self.session_id_edit.setText("default")
        connect_layout.addRow("Session ID:", self.session_id_edit)
        
        self.user_id_edit = QtWidgets.QLineEdit()
        self.user_id_edit.setPlaceholderText("your-name")
        # Try to get computer name as default
        try:
            self.user_id_edit.setText(socket.gethostname())
        except:
            self.user_id_edit.setText("user")
        connect_layout.addRow("Your Name:", self.user_id_edit)
        
        layout.addWidget(self.connect_group)
        
        # Host settings (for host mode)
        self.host_group = QtWidgets.QGroupBox("Server Settings")
        host_layout = QtWidgets.QFormLayout(self.host_group)
        
        self.host_address_edit = QtWidgets.QLineEdit("0.0.0.0")
        self.host_address_edit.setToolTip("0.0.0.0 = all network interfaces (LAN accessible)")
        host_layout.addRow("Listen Address:", self.host_address_edit)
        
        self.host_port_spin = QtWidgets.QSpinBox()
        self.host_port_spin.setRange(1024, 65535)
        self.host_port_spin.setValue(8765)
        host_layout.addRow("Port:", self.host_port_spin)
        
        # Auto-connect after hosting
        self.auto_connect_check = QtWidgets.QCheckBox("Auto-connect after starting server")
        self.auto_connect_check.setChecked(True)
        host_layout.addRow("", self.auto_connect_check)
        
        # Server status
        self.server_status_label = QtWidgets.QLabel("Server not running")
        self.server_status_label.setStyleSheet("color: gray;")
        host_layout.addRow("Status:", self.server_status_label)
        
        # Server control buttons
        server_control_layout = QtWidgets.QHBoxLayout()
        self.start_server_btn = QtWidgets.QPushButton("Start Server")
        self.stop_server_btn = QtWidgets.QPushButton("Stop Server")
        self.stop_server_btn.setEnabled(False)
        self.start_server_btn.clicked.connect(self._on_start_server)
        self.stop_server_btn.clicked.connect(self._on_stop_server)
        server_control_layout.addWidget(self.start_server_btn)
        server_control_layout.addWidget(self.stop_server_btn)
        host_layout.addRow("", server_control_layout)
        
        layout.addWidget(self.host_group)
        
        # Info label
        self.info_label = QtWidgets.QLabel()
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet("QLabel { background-color: #f0f0f0; padding: 8px; border-radius: 4px; }")
        layout.addWidget(self.info_label)
        
        layout.addStretch()
        
        # Buttons
        button_box = QtWidgets.QDialogButtonBox()
        self.connect_btn = button_box.addButton("Connect", QtWidgets.QDialogButtonBox.ButtonRole.AcceptRole)
        self.cancel_btn = button_box.addButton("Cancel", QtWidgets.QDialogButtonBox.ButtonRole.RejectRole)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        
        layout.addWidget(button_box)
    
    def _on_mode_changed(self) -> None:
        """Handle mode change (connect vs host)."""
        if self.radio_connect.isChecked():
            self.mode = "connect"
        else:
            self.mode = "host"
        self._update_mode()
    
    def _update_mode(self) -> None:
        """Update UI based on selected mode."""
        is_connect = (self.mode == "connect")
        self.connect_group.setVisible(is_connect)
        self.host_group.setVisible(not is_connect)
        
        if is_connect:
            self.info_label.setText(
                "💡 Connect to an existing collaboration server. "
                "You can find the server URL from the person hosting the session."
            )
        else:
            local_ip = self._get_local_ip()
            self.info_label.setText(
                f"💡 Start a server on this computer for others to join. "
                f"Others on your network can connect to: ws://{local_ip}:{self.host_port_spin.value()}"
            )
    
    def _get_local_ip(self) -> str:
        """Get local IP address for LAN connectivity."""
        try:
            # Create a socket to determine local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except:
            return "localhost"
    
    def _on_start_server(self) -> None:
        """Start the collaboration server."""
        host = self.host_address_edit.text()
        port = self.host_port_spin.value()
        
        # Find the server script
        server_script = Path(__file__).parent.parent.parent.parent.parent / "tools" / "collaboration_server.py"
        
        if not server_script.exists():
            QtWidgets.QMessageBox.critical(
                self,
                "Server Not Found",
                f"Could not find collaboration server at:\n{server_script}\n\n"
                "Please ensure collaboration_server.py exists in the tools/ directory."
            )
            return
        
        try:
            # Start server process
            self.server_process = subprocess.Popen(
                [sys.executable, str(server_script), "--host", host, "--port", str(port)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            
            self.server_status_label.setText(f"Server running on {host}:{port}")
            self.server_status_label.setStyleSheet("color: green;")
            self.start_server_btn.setEnabled(False)
            self.stop_server_btn.setEnabled(True)
            self.host_address_edit.setEnabled(False)
            self.host_port_spin.setEnabled(False)
            
            # Update info with connection URL
            local_ip = self._get_local_ip()
            self.info_label.setText(
                f"✅ Server started! Others can connect to:\n"
                f"ws://{local_ip}:{port}\n\n"
                f"Session ID: {self.session_id_edit.text()}"
            )
            
            # Auto-connect if enabled
            if self.auto_connect_check.isChecked():
                # Switch to connect mode and populate fields
                self.server_url_edit.setText(f"ws://localhost:{port}")
                # Don't switch UI, just accept the dialog to connect
                QtCore.QTimer.singleShot(500, self.accept)
        
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self,
                "Server Start Failed",
                f"Failed to start server:\n{e}"
            )
    
    def _on_stop_server(self) -> None:
        """Stop the collaboration server."""
        if self.server_process:
            self.server_process.terminate()
            try:
                self.server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.server_process.kill()
            self.server_process = None
            
            self.server_status_label.setText("Server stopped")
            self.server_status_label.setStyleSheet("color: gray;")
            self.start_server_btn.setEnabled(True)
            self.stop_server_btn.setEnabled(False)
            self.host_address_edit.setEnabled(True)
            self.host_port_spin.setEnabled(True)
            
            self.info_label.setText("Server has been stopped.")
    
    def get_connection_info(self) -> dict:
        """Get connection information from the dialog."""
        return {
            "mode": self.mode,
            "server_url": self.server_url_edit.text(),
            "session_id": self.session_id_edit.text(),
            "user_id": self.user_id_edit.text(),
            "host": self.host_address_edit.text(),
            "port": self.host_port_spin.value(),
        }
    
    def closeEvent(self, event) -> None:
        """Handle dialog close event."""
        # Stop server if running
        if self.server_process:
            reply = QtWidgets.QMessageBox.question(
                self,
                "Stop Server?",
                "The collaboration server is still running. Stop it?",
                QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
                QtWidgets.QMessageBox.StandardButton.No
            )
            if reply == QtWidgets.QMessageBox.StandardButton.Yes:
                self._on_stop_server()
        
        super().closeEvent(event)


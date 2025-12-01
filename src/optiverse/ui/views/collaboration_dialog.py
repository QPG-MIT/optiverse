"""
Collaboration Dialog - UI for connecting to or hosting collaboration sessions.

Provides options to:
- Connect to an existing server
- Host a new server locally
"""

from __future__ import annotations

import logging
import socket
import subprocess
import sys
from pathlib import Path

from PyQt6 import QtCore, QtGui, QtWidgets

_logger = logging.getLogger(__name__)


class CollaborationDialog(QtWidgets.QDialog):
    """
    Dialog for collaboration configuration.

    Allows user to:
    - Connect to an existing collaboration server
    - Host a server on the local machine
    """

    def __init__(self, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Collaboration")
        self.setModal(True)
        self.setMinimumSize(500, 520)  # Adequate size to avoid geometry warnings

        self.mode = "connect"  # "connect" or "host"
        self.server_process: subprocess.Popen | None = None
        self._accepted = False  # Track if dialog was accepted

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
        self.connect_group = QtWidgets.QGroupBox("Join Session")
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
        except OSError:
            self.user_id_edit.setText("user")
        connect_layout.addRow("Your Name:", self.user_id_edit)

        # Info about joining
        join_info = QtWidgets.QLabel(
            "⚠️ Joining will replace your current canvas with the session's canvas."
        )
        join_info.setWordWrap(True)
        join_info.setStyleSheet("color: #888; font-style: italic; padding: 5px;")
        connect_layout.addRow("", join_info)

        layout.addWidget(self.connect_group)

        # Host settings (for host mode)
        self.host_group = QtWidgets.QGroupBox("Create Session")
        host_layout = QtWidgets.QFormLayout(self.host_group)

        # Session ID for host
        self.host_session_id_edit = QtWidgets.QLineEdit()
        self.host_session_id_edit.setPlaceholderText("session-name")
        self.host_session_id_edit.setText("default")
        host_layout.addRow("Session ID:", self.host_session_id_edit)

        # User name for host
        self.host_user_id_edit = QtWidgets.QLineEdit()
        self.host_user_id_edit.setPlaceholderText("your-name")
        try:
            self.host_user_id_edit.setText(socket.gethostname())
        except OSError:
            self.host_user_id_edit.setText("host")
        host_layout.addRow("Your Name:", self.host_user_id_edit)

        # Canvas options
        canvas_label = QtWidgets.QLabel("Canvas:")
        canvas_label.setStyleSheet("font-weight: bold;")
        host_layout.addRow("", canvas_label)

        self.radio_use_current = QtWidgets.QRadioButton(
            "Use current canvas (share my current work)"
        )
        self.radio_empty_canvas = QtWidgets.QRadioButton("Start with empty canvas")
        self.radio_use_current.setChecked(True)

        host_layout.addRow("", self.radio_use_current)
        host_layout.addRow("", self.radio_empty_canvas)

        # Server settings
        server_label = QtWidgets.QLabel("Server:")
        server_label.setStyleSheet("font-weight: bold;")
        host_layout.addRow("", server_label)

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
        self.server_status_label.setStyleSheet("color: #888;")
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

        # Info label (adapt to theme)
        self.info_label = QtWidgets.QLabel()
        self.info_label.setWordWrap(True)
        # Use palette colors to adapt to light/dark mode
        palette = self.palette()
        is_dark = palette.color(QtGui.QPalette.ColorRole.Window).lightness() < 128
        if is_dark:
            info_bg = "#2d2f36"
            info_border = "#3d3f46"
        else:
            info_bg = "#f0f0f0"
            info_border = "#d0d0d0"
        self.info_label.setStyleSheet(
            f"QLabel {{ background-color: {info_bg}; padding: 8px; "
            f"border-radius: 4px; border: 1px solid {info_border}; }}"
        )
        layout.addWidget(self.info_label)

        layout.addStretch()

        # Buttons
        button_box = QtWidgets.QDialogButtonBox()
        self.connect_btn = button_box.addButton(
            "Connect", QtWidgets.QDialogButtonBox.ButtonRole.AcceptRole
        )
        self.cancel_btn = button_box.addButton(
            "Cancel", QtWidgets.QDialogButtonBox.ButtonRole.RejectRole
        )
        button_box.accepted.connect(self._on_accept)
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
        is_connect = self.mode == "connect"
        self.connect_group.setVisible(is_connect)
        self.host_group.setVisible(not is_connect)

        if is_connect:
            self.info_label.setText(
                "💡 Connect to an existing collaboration server. "
                "You can find the server URL from the person hosting the session. "
                "Your canvas will be replaced with the session's canvas."
            )
        else:
            local_ip = self._get_local_ip()
            self.info_label.setText(
                f"💡 Start a server on this computer for others to join. "
                f"Choose whether to share your current canvas or start fresh. "
                f"Others can connect to: ws://{local_ip}:{self.host_port_spin.value()}"
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
        except OSError:
            return "localhost"

    def _check_port_listening(self, host: str, port: int) -> bool:
        """Check if a port is listening/accepting connections."""
        try:
            # Try to connect to the port
            test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_socket.settimeout(2)

            # Convert 0.0.0.0 to localhost for connection test
            test_host = "localhost" if host == "0.0.0.0" else host

            result = test_socket.connect_ex((test_host, port))
            test_socket.close()

            # If connect_ex returns 0, connection succeeded (port is listening)
            return result == 0
        except OSError as e:
            _logger.debug("Port check error: %s", e)
            return False

    def _on_start_server(self) -> None:
        """Start the collaboration server."""
        host = self.host_address_edit.text()
        port = self.host_port_spin.value()

        # Check if websockets is available
        try:
            result = subprocess.run(
                [sys.executable, "-c", "import websockets"], capture_output=True, timeout=5
            )
            if result.returncode != 0:
                QtWidgets.QMessageBox.critical(
                    self,
                    "Missing Dependency",
                    "The 'websockets' library is not installed.\n\n"
                    "Please install dependencies with:\n"
                    "pip install -e .\n\n"
                    "Or install websockets directly:\n"
                    "pip install websockets",
                )
                return
        except (subprocess.SubprocessError, OSError) as e:
            _logger.debug("Error checking websockets: %s", e)

        # Find the server script
        server_script = (
            Path(__file__).parent.parent.parent.parent.parent / "tools" / "collaboration_server.py"
        )

        if not server_script.exists():
            QtWidgets.QMessageBox.critical(
                self,
                "Server Not Found",
                f"Could not find collaboration server at:\n{server_script}\n\n"
                "Please ensure collaboration_server.py exists in the tools/ directory.",
            )
            return

        try:
            # Start server process with proper subprocess configuration
            # Don't pipe stdout/stderr to avoid blocking - let them go to console or DEVNULL
            kwargs = {
                "args": [sys.executable, str(server_script), "--host", host, "--port", str(port)],
                "stdout": subprocess.DEVNULL,  # Suppress output to prevent blocking
                "stderr": subprocess.DEVNULL,  # Suppress errors to prevent blocking
            }

            if sys.platform == "win32":
                # On Windows, detach from parent console and hide window
                # CREATE_NO_WINDOW = 0x08000000, DETACHED_PROCESS = 0x00000008
                kwargs["creationflags"] = 0x08000000 | 0x00000008
            else:
                # On Unix-like systems (Mac, Linux), start in background
                kwargs["start_new_session"] = True

            self.server_process = subprocess.Popen(**kwargs)

            # Give server a moment to start and verify it's actually listening
            import time

            time.sleep(1.5)

            # Check if process died
            if self.server_process.poll() is not None:
                raise Exception(
                    "Server crashed on startup. Please ensure:\n"
                    "1. websockets library is installed: pip install websockets\n"
                    "2. Port is not already in use\n"
                    "3. Python has network permissions"
                )

            # Verify server is actually listening on the port
            if not self._check_port_listening(host, port):
                self.server_process.terminate()
                self.server_process = None
                raise Exception(
                    f"Server started but not listening on port {port}.\n"
                    "The server process is running but may have errors.\n"
                    "Try running manually: python tools/collaboration_server.py"
                )

            self.server_status_label.setText(f"Server running on {host}:{port}")
            self.server_status_label.setStyleSheet("color: #6cc644;")
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

        except (subprocess.SubprocessError, OSError) as e:
            QtWidgets.QMessageBox.critical(
                self, "Server Start Failed", f"Failed to start server:\n{e}"
            )

    def _on_stop_server(self) -> None:
        """Stop the collaboration server."""
        if self.server_process:
            try:
                # First try graceful termination
                self.server_process.terminate()
                try:
                    self.server_process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    # Force kill if it doesn't stop
                    self.server_process.kill()
                    self.server_process.wait()
            except OSError as e:
                _logger.warning("Error stopping server: %s", e)
            finally:
                self.server_process = None

            self.server_status_label.setText("Server stopped")
            self.server_status_label.setStyleSheet("color: #888;")
            self.start_server_btn.setEnabled(True)
            self.stop_server_btn.setEnabled(False)
            self.host_address_edit.setEnabled(True)
            self.host_port_spin.setEnabled(True)

            self.info_label.setText("Server has been stopped.")

    def _on_accept(self) -> None:
        """Handle dialog acceptance (Connect button clicked)."""
        self._accepted = True
        self.accept()

    def get_connection_info(self) -> dict:
        """Get connection information from the dialog."""
        info = {
            "mode": self.mode,
        }

        if self.mode == "connect":
            # Client joining session
            info.update(
                {
                    "server_url": self.server_url_edit.text(),
                    "session_id": self.session_id_edit.text(),
                    "user_id": self.user_id_edit.text(),
                }
            )
        else:
            # Host creating session
            info.update(
                {
                    "session_id": self.host_session_id_edit.text(),
                    "user_id": self.host_user_id_edit.text(),
                    "use_current_canvas": self.radio_use_current.isChecked(),
                    "host": self.host_address_edit.text(),
                    "port": self.host_port_spin.value(),
                }
            )

        return info

    def closeEvent(self, event) -> None:
        """Handle dialog close event."""
        # Only stop server if dialog was not accepted (was canceled/closed)
        # If accepted, the main window will take ownership of the server process
        if self.server_process and not self._accepted:
            reply = QtWidgets.QMessageBox.question(
                self,
                "Stop Server?",
                "The collaboration server is still running. Stop it?",
                QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
                QtWidgets.QMessageBox.StandardButton.No,
            )
            if reply == QtWidgets.QMessageBox.StandardButton.Yes:
                self._on_stop_server()
            # If user chose No, server will keep running but won't be tracked
            # (This is an edge case - user started server but canceled connection)

        super().closeEvent(event)

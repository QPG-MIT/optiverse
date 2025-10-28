"""
Share dialog for creating and joining collaboration sessions.
"""
from __future__ import annotations

from PyQt6 import QtWidgets, QtCore, QtGui
import time
try:
    import requests
except ImportError:
    requests = None


class ShareDialog(QtWidgets.QDialog):
    """Dialog for creating or joining a collaboration session."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Share & Collaborate")
        self.setMinimumWidth(500)
        
        self.session_id: str | None = None
        self.user_id: str | None = None
        self.server_url = "http://localhost:8080"  # HTTP for REST, will become WS for WebSocket
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Create the dialog UI."""
        layout = QtWidgets.QVBoxLayout(self)
        
        # Tab widget for Create vs Join
        tabs = QtWidgets.QTabWidget()
        
        # ========== CREATE TAB ==========
        create_tab = QtWidgets.QWidget()
        create_layout = QtWidgets.QVBoxLayout(create_tab)
        
        create_layout.addWidget(QtWidgets.QLabel(
            "<b>Create a new session</b> to share with others:"
        ))
        create_layout.addSpacing(10)
        
        # User name input
        name_label = QtWidgets.QLabel("Your name:")
        self.user_name_input = QtWidgets.QLineEdit()
        self.user_name_input.setPlaceholderText("Enter your name")
        create_layout.addWidget(name_label)
        create_layout.addWidget(self.user_name_input)
        
        create_layout.addSpacing(10)
        
        # Create button
        create_btn = QtWidgets.QPushButton("🎯 Create New Session")
        create_btn.clicked.connect(self._create_session)
        create_layout.addWidget(create_btn)
        
        create_layout.addSpacing(10)
        
        # Share link display
        self.share_link_label = QtWidgets.QLabel("")
        self.share_link_label.setWordWrap(True)
        self.share_link_label.setTextInteractionFlags(
            QtCore.Qt.TextInteractionFlag.TextSelectableByMouse
        )
        # Use palette colors to adapt to light/dark mode
        palette = self.palette()
        is_dark = palette.color(QtWidgets.QPalette.ColorRole.Window).lightness() < 128
        if is_dark:
            bg_color = "#2d2f36"
            border_color = "#3d3f46"
        else:
            bg_color = "#f0f0f0"
            border_color = "#d0d0d0"
        self.share_link_label.setStyleSheet(
            f"QLabel {{ background-color: {bg_color}; padding: 10px; border-radius: 5px; border: 1px solid {border_color}; }}"
        )
        create_layout.addWidget(self.share_link_label)
        
        # Copy button
        self.copy_btn = QtWidgets.QPushButton("📋 Copy Session ID")
        self.copy_btn.clicked.connect(self._copy_link)
        self.copy_btn.setEnabled(False)
        create_layout.addWidget(self.copy_btn)
        
        create_layout.addStretch()
        tabs.addTab(create_tab, "Create")
        
        # ========== JOIN TAB ==========
        join_tab = QtWidgets.QWidget()
        join_layout = QtWidgets.QVBoxLayout(join_tab)
        
        join_layout.addWidget(QtWidgets.QLabel(
            "<b>Join an existing session</b> by entering the session ID:"
        ))
        join_layout.addSpacing(10)
        
        # Session ID input
        session_label = QtWidgets.QLabel("Session ID:")
        self.session_id_input = QtWidgets.QLineEdit()
        self.session_id_input.setPlaceholderText("Paste session ID here")
        join_layout.addWidget(session_label)
        join_layout.addWidget(self.session_id_input)
        
        join_layout.addSpacing(10)
        
        # User name input
        join_name_label = QtWidgets.QLabel("Your name:")
        self.join_name_input = QtWidgets.QLineEdit()
        self.join_name_input.setPlaceholderText("Enter your name")
        join_layout.addWidget(join_name_label)
        join_layout.addWidget(self.join_name_input)
        
        join_layout.addStretch()
        tabs.addTab(join_tab, "Join")
        
        layout.addWidget(tabs)
        
        # ========== DIALOG BUTTONS ==========
        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok |
            QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        # ========== INFO LABEL ==========
        info_label = QtWidgets.QLabel(
            "<i>Note: Make sure the collaboration server is running!</i>"
        )
        # Adapt color to theme
        palette = self.palette()
        is_dark = palette.color(QtWidgets.QPalette.ColorRole.Window).lightness() < 128
        info_label.setStyleSheet("color: #999;" if is_dark else "color: #666;")
        layout.addWidget(info_label)
    
    def _create_session(self):
        """Create a new session on the server."""
        if requests is None:
            QtWidgets.QMessageBox.warning(
                self,
                "Missing Dependency",
                "The 'requests' library is required for creating sessions.\n"
                "Install it with: pip install requests"
            )
            return
        
        try:
            response = requests.post(
                f"{self.server_url}/api/sessions",
                timeout=5
            )
            response.raise_for_status()
            data = response.json()
            
            self.session_id = data['session_id']
            
            # Display the session ID
            self.share_link_label.setText(
                f"<b>Session ID:</b><br/>"
                f"<code style='font-size: 14px;'>{self.session_id}</code><br/><br/>"
                f"<i>Share this ID with others to collaborate!</i>"
            )
            self.copy_btn.setEnabled(True)
            
            # Show success message
            QtWidgets.QMessageBox.information(
                self,
                "Session Created",
                f"Session created successfully!\n\n"
                f"Session ID: {self.session_id}\n\n"
                f"Share this ID with others so they can join."
            )
        
        except requests.exceptions.ConnectionError:
            QtWidgets.QMessageBox.critical(
                self,
                "Connection Error",
                "Failed to connect to collaboration server.\n\n"
                "Make sure the server is running:\n"
                "  python collaboration_server.py"
            )
        except requests.exceptions.Timeout:
            QtWidgets.QMessageBox.warning(
                self,
                "Timeout",
                "Server request timed out. Please try again."
            )
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self,
                "Error",
                f"Failed to create session:\n{str(e)}"
            )
    
    def _copy_link(self):
        """Copy session ID to clipboard."""
        if self.session_id:
            QtWidgets.QApplication.clipboard().setText(self.session_id)
            QtWidgets.QMessageBox.information(
                self,
                "Copied",
                "Session ID copied to clipboard!"
            )
    
    def _on_accept(self):
        """Handle OK button click."""
        # Determine which tab is active and get session ID
        if not self.session_id:
            # User is joining an existing session
            self.session_id = self.session_id_input.text().strip()
        
        if not self.session_id:
            QtWidgets.QMessageBox.warning(
                self,
                "Missing Information",
                "Please create a new session or enter a session ID to join."
            )
            return
        
        # Get user name
        self.user_id = (
            self.user_name_input.text().strip() or
            self.join_name_input.text().strip()
        )
        
        if not self.user_id:
            # Generate a default name
            self.user_id = f"User_{int(time.time())}"
        
        # Accept the dialog
        self.accept()


if __name__ == "__main__":
    # Test the dialog
    import sys
    app = QtWidgets.QApplication(sys.argv)
    
    dialog = ShareDialog()
    if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
        print(f"Session ID: {dialog.session_id}")
        print(f"User ID: {dialog.user_id}")
    
    sys.exit(0)


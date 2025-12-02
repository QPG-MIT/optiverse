"""
Log window for viewing application debug messages.
"""

from __future__ import annotations

from PyQt6 import QtGui, QtWidgets

from ...services.log_service import LogLevel, LogMessage, get_log_service


class LogWindow(QtWidgets.QDialog):
    """
    Window for displaying application logs with filtering and search.
    """

    def __init__(self, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Application Log")
        self.resize(900, 600)

        # Get log service
        self.log_service = get_log_service()

        # Build UI
        self._build_ui()

        # Load existing messages
        self._load_existing_messages()

        # Register for new messages
        self.log_service.add_listener(self._on_new_message)

    def _build_ui(self):
        """Build the log window UI."""
        layout = QtWidgets.QVBoxLayout(self)

        # Toolbar with filters and controls
        toolbar = QtWidgets.QHBoxLayout()

        # Level filter
        toolbar.addWidget(QtWidgets.QLabel("Level:"))
        self.level_combo = QtWidgets.QComboBox()
        self.level_combo.addItem("All", None)
        self.level_combo.addItem("DEBUG", LogLevel.DEBUG)
        self.level_combo.addItem("INFO", LogLevel.INFO)
        self.level_combo.addItem("WARNING", LogLevel.WARNING)
        self.level_combo.addItem("ERROR", LogLevel.ERROR)
        self.level_combo.currentIndexChanged.connect(self._apply_filters)
        toolbar.addWidget(self.level_combo)

        # Category filter
        toolbar.addWidget(QtWidgets.QLabel("Category:"))
        self.category_combo = QtWidgets.QComboBox()
        self.category_combo.addItem("All", None)
        self.category_combo.currentIndexChanged.connect(self._apply_filters)
        toolbar.addWidget(self.category_combo)

        # Search box
        toolbar.addWidget(QtWidgets.QLabel("Search:"))
        self.search_box = QtWidgets.QLineEdit()
        self.search_box.setPlaceholderText("Filter messages...")
        self.search_box.textChanged.connect(self._apply_filters)
        toolbar.addWidget(self.search_box)

        toolbar.addStretch()

        # Auto-scroll checkbox
        self.autoscroll_check = QtWidgets.QCheckBox("Auto-scroll")
        self.autoscroll_check.setChecked(True)
        toolbar.addWidget(self.autoscroll_check)

        # Clear button
        clear_btn = QtWidgets.QPushButton("Clear Log")
        clear_btn.clicked.connect(self._clear_log)
        toolbar.addWidget(clear_btn)

        # Export button
        export_btn = QtWidgets.QPushButton("Export...")
        export_btn.clicked.connect(self._export_log)
        toolbar.addWidget(export_btn)

        layout.addLayout(toolbar)

        # Log text display
        self.log_text = QtWidgets.QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QtGui.QFont("Consolas", 9))
        self.log_text.setLineWrapMode(QtWidgets.QTextEdit.LineWrapMode.NoWrap)
        layout.addWidget(self.log_text)

        # Status bar
        status_layout = QtWidgets.QHBoxLayout()
        self.status_label = QtWidgets.QLabel("0 messages")
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        layout.addLayout(status_layout)

        # Close button
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addStretch()
        close_btn = QtWidgets.QPushButton("Close")
        close_btn.clicked.connect(self.close)
        button_layout.addWidget(close_btn)
        layout.addLayout(button_layout)

    def _load_existing_messages(self):
        """Load all existing log messages."""
        messages = self.log_service.get_messages()
        for msg in messages:
            self._append_message(msg)

        # Update category combo
        self._update_category_combo()

        # Update status
        self._update_status()

    def _update_category_combo(self):
        """Update the category filter combo with available categories."""
        current = self.category_combo.currentData()
        self.category_combo.clear()
        self.category_combo.addItem("All", None)

        categories = self.log_service.get_categories()
        for cat in categories:
            self.category_combo.addItem(cat, cat)

        # Restore selection if possible
        if current is not None:
            index = self.category_combo.findData(current)
            if index >= 0:
                self.category_combo.setCurrentIndex(index)

    def _on_new_message(self, message: LogMessage):
        """Handle new log message from service."""
        # Update category combo if needed
        if message.category not in [
            self.category_combo.itemData(i) for i in range(self.category_combo.count())
        ]:
            self._update_category_combo()

        # Add message if it passes filters
        if self._message_passes_filters(message):
            self._append_message(message)

            # Auto-scroll to bottom if enabled
            if self.autoscroll_check.isChecked():
                self.log_text.moveCursor(QtGui.QTextCursor.MoveOperation.End)

        self._update_status()

    def _append_message(self, message: LogMessage):
        """Append a message to the log display with color coding."""
        cursor = self.log_text.textCursor()
        cursor.movePosition(QtGui.QTextCursor.MoveOperation.End)

        # Color code by level
        format = QtGui.QTextCharFormat()
        if message.level == LogLevel.ERROR:
            format.setForeground(QtGui.QColor("#FF4444"))
        elif message.level == LogLevel.WARNING:
            format.setForeground(QtGui.QColor("#FFA500"))
        elif message.level == LogLevel.INFO:
            format.setForeground(QtGui.QColor("#4444FF"))
        else:  # DEBUG
            format.setForeground(QtGui.QColor("#888888"))

        cursor.setCharFormat(format)
        cursor.insertText(message.format() + "\n")

    def _message_passes_filters(self, message: LogMessage) -> bool:
        """Check if message passes current filters."""
        # Level filter
        level_filter = self.level_combo.currentData()
        if level_filter is not None and message.level != level_filter:
            return False

        # Category filter
        category_filter = self.category_combo.currentData()
        if category_filter is not None and message.category != category_filter:
            return False

        # Search filter
        search_text = self.search_box.text().lower()
        if search_text and search_text not in message.message.lower():
            return False

        return True

    def _apply_filters(self):
        """Re-apply filters and refresh display."""
        self.log_text.clear()
        messages = self.log_service.get_messages()
        for msg in messages:
            if self._message_passes_filters(msg):
                self._append_message(msg)

        self._update_status()

    def _update_status(self):
        """Update status bar with message count."""
        total = len(self.log_service.get_messages())
        displayed = self.log_text.document().blockCount() - 1  # -1 for empty line at end

        if displayed < total:
            self.status_label.setText(f"Showing {displayed} of {total} messages")
        else:
            self.status_label.setText(f"{total} messages")

    def _clear_log(self):
        """Clear all log messages."""
        # Import here to avoid circular import
        from ...ui.theme_manager import question as theme_aware_question
        
        reply = theme_aware_question(
            self,
            "Clear Log",
            "Are you sure you want to clear all log messages?",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
        )

        if reply == QtWidgets.QMessageBox.StandardButton.Yes:
            self.log_service.clear()
            self.log_text.clear()
            self._update_status()

    def _export_log(self):
        """Export log to file."""
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Export Log", "optiverse_log.txt", "Text Files (*.txt);;All Files (*)"
        )

        if filename:
            try:
                with open(filename, "w", encoding="utf-8") as f:
                    messages = self.log_service.get_messages()
                    for msg in messages:
                        f.write(msg.format() + "\n")

                QtWidgets.QMessageBox.information(
                    self, "Export Successful", f"Log exported to:\n{filename}"
                )
            except OSError as e:
                QtWidgets.QMessageBox.critical(self, "Export Failed", f"Failed to export log:\n{e}")

    def closeEvent(self, event):
        """Clean up when window is closed."""
        # Unregister from log service
        self.log_service.remove_listener(self._on_new_message)
        super().closeEvent(event)

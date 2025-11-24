"""Smart spinbox with cursor-aware increments and live updates."""
from __future__ import annotations

from PyQt6 import QtCore, QtGui, QtWidgets


class SmartDoubleSpinBox(QtWidgets.QDoubleSpinBox):
    """
    Enhanced QDoubleSpinBox with:
    1. Cursor-aware increments: up/down arrows increment the digit to the LEFT of cursor
    2. Live update support via valueChanged signal
    
    Example:
        Value is 123.45, cursor at 12|3.45 → up arrow → 133.45 (increments the '2')
        Value is 123.45, cursor at 123|.45 → up arrow → 124.45 (increments the '3')
        Value is 123.45, cursor at 123.4|5 → up arrow → 123.55 (increments the '4')
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._use_cursor_step = True
        self._last_cursor_pos = 0
        
        # Set a very small singleStep to avoid any interference
        # (though we override stepBy completely, this ensures no edge cases)
        self.setSingleStep(0.001)
        
        # Track cursor position changes in the line edit
        line_edit = self.lineEdit()
        line_edit.cursorPositionChanged.connect(self._on_cursor_changed)
        line_edit.selectionChanged.connect(self._on_cursor_changed)
        
        # Install event filter to intercept keyboard Up/Down events
        line_edit.installEventFilter(self)
    
    def eventFilter(self, obj, event):
        """Intercept keyboard events from line edit to handle Up/Down with cursor awareness."""
        if obj == self.lineEdit() and event.type() == QtCore.QEvent.Type.KeyPress:
            key = event.key()
            # Intercept Up/Down arrow keys when line edit has focus
            if key == QtCore.Qt.Key.Key_Up:
                # Store current cursor position and call stepBy
                self._last_cursor_pos = self.lineEdit().cursorPosition()
                self.stepBy(1)
                return True  # Event handled, don't pass to default handler
            elif key == QtCore.Qt.Key.Key_Down:
                # Store current cursor position and call stepBy
                self._last_cursor_pos = self.lineEdit().cursorPosition()
                self.stepBy(-1)
                return True  # Event handled, don't pass to default handler
        
        # For all other events, use default handling
        return super().eventFilter(obj, event)
    
    def _on_cursor_changed(self):
        """Store the cursor position when it changes."""
        line_edit = self.lineEdit()
        # Only track if line edit has focus (user is actively editing)
        if line_edit.hasFocus():
            self._last_cursor_pos = line_edit.cursorPosition()
    
    def stepBy(self, steps: int):
        """Override to increment based on cursor position."""
        if not self._use_cursor_step:
            super().stepBy(steps)
            return
        
        line_edit = self.lineEdit()
        text = line_edit.text()
        
        # Use the last known cursor position (from when user was editing)
        # rather than current position (which may be invalid if buttons clicked)
        cursor_pos = self._last_cursor_pos
        
        # Remove suffix/prefix to get clean number text
        suffix = self.suffix()
        prefix = self.prefix()
        
        # Keep original text for length comparison
        original_text = text
        
        # Strip prefix
        prefix_len = 0
        if prefix and text.startswith(prefix):
            prefix_len = len(prefix)
            text = text[prefix_len:]
            cursor_pos -= prefix_len
        
        # Strip suffix
        suffix_len = 0
        if suffix and text.endswith(suffix):
            suffix_len = len(suffix)
            text = text[:-suffix_len]
        
        # Count and remove leading/trailing spaces
        leading_spaces = len(text) - len(text.lstrip())
        text = text.strip()
        cursor_pos -= leading_spaces
        
        # Bounds check cursor position
        cursor_pos = max(0, min(cursor_pos, len(text)))
        
        # We want to increment the digit to the LEFT of the cursor
        # So if cursor is at position N, we increment the digit at position N-1
        # If cursor is at position 0, treat it as if at position 1 (increment first digit)
        if cursor_pos == 0:
            digit_pos = 0
        else:
            digit_pos = cursor_pos - 1
        
        # Find decimal point position
        decimal_pos = text.find('.')
        
        # Determine step size based on the digit position (left of cursor)
        if decimal_pos == -1:
            # No decimal point - use integer steps based on distance from end
            digits_from_end = len(text) - digit_pos
            step = 10 ** max(0, digits_from_end - 1)
        else:
            if digit_pos < decimal_pos:
                # Digit is before decimal point (integer part)
                # Distance from decimal to digit position
                digits_from_decimal = decimal_pos - digit_pos
                step = 10 ** (digits_from_decimal - 1)
            else:
                # Digit is after decimal point (fractional part)
                # digit_pos > decimal_pos means we're past the decimal
                digits_after_decimal = digit_pos - decimal_pos - 1
                step = 10 ** (-digits_after_decimal - 1)
        
        # DO NOT clamp to singleStep() - that would defeat cursor-aware stepping!
        # We want to increment by exactly the step we calculated based on cursor position
        
        # Apply the step
        new_value = self.value() + (steps * step)
        
        # Respect min/max
        new_value = max(self.minimum(), min(self.maximum(), new_value))
        
        # Set value (this will reformat the text)
        self.setValue(new_value)
        
        # Restore cursor position accounting for prefix/suffix/spaces
        # Try to keep it in the same relative position
        new_text = line_edit.text()
        
        # Account for prefix and leading spaces in new text
        adjusted_pos = cursor_pos + prefix_len + leading_spaces
        adjusted_pos = max(0, min(adjusted_pos, len(new_text) - suffix_len))
        
        line_edit.setCursorPosition(adjusted_pos)
        self._last_cursor_pos = adjusted_pos


class SmartSpinBox(QtWidgets.QSpinBox):
    """
    Enhanced QSpinBox with cursor-aware increments.
    Similar to SmartDoubleSpinBox but for integers.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._use_cursor_step = True
        self._last_cursor_pos = 0
        
        # Set singleStep to 1 (for integers, this is the minimum)
        self.setSingleStep(1)
        
        # Track cursor position changes in the line edit
        line_edit = self.lineEdit()
        line_edit.cursorPositionChanged.connect(self._on_cursor_changed)
        line_edit.selectionChanged.connect(self._on_cursor_changed)
        
        # Install event filter to intercept keyboard Up/Down events
        line_edit.installEventFilter(self)
    
    def eventFilter(self, obj, event):
        """Intercept keyboard events from line edit to handle Up/Down with cursor awareness."""
        if obj == self.lineEdit() and event.type() == QtCore.QEvent.Type.KeyPress:
            key = event.key()
            # Intercept Up/Down arrow keys when line edit has focus
            if key == QtCore.Qt.Key.Key_Up:
                # Store current cursor position and call stepBy
                self._last_cursor_pos = self.lineEdit().cursorPosition()
                self.stepBy(1)
                return True  # Event handled, don't pass to default handler
            elif key == QtCore.Qt.Key.Key_Down:
                # Store current cursor position and call stepBy
                self._last_cursor_pos = self.lineEdit().cursorPosition()
                self.stepBy(-1)
                return True  # Event handled, don't pass to default handler
        
        # For all other events, use default handling
        return super().eventFilter(obj, event)
    
    def _on_cursor_changed(self):
        """Store the cursor position when it changes."""
        line_edit = self.lineEdit()
        # Only track if line edit has focus (user is actively editing)
        if line_edit.hasFocus():
            self._last_cursor_pos = line_edit.cursorPosition()
    
    def stepBy(self, steps: int):
        """Override to increment based on cursor position."""
        if not self._use_cursor_step:
            super().stepBy(steps)
            return
        
        line_edit = self.lineEdit()
        text = line_edit.text()
        
        # Use the last known cursor position (from when user was editing)
        cursor_pos = self._last_cursor_pos
        
        # Remove suffix/prefix to get clean number text
        suffix = self.suffix()
        prefix = self.prefix()
        
        # Strip prefix
        prefix_len = 0
        if prefix and text.startswith(prefix):
            prefix_len = len(prefix)
            text = text[prefix_len:]
            cursor_pos -= prefix_len
        
        # Strip suffix
        suffix_len = 0
        if suffix and text.endswith(suffix):
            suffix_len = len(suffix)
            text = text[:-suffix_len]
        
        # Count and remove leading/trailing spaces
        leading_spaces = len(text) - len(text.lstrip())
        text = text.strip()
        cursor_pos -= leading_spaces
        
        # Bounds check cursor position
        cursor_pos = max(0, min(cursor_pos, len(text)))
        
        # We want to increment the digit to the LEFT of the cursor
        # So if cursor is at position N, we increment the digit at position N-1
        # If cursor is at position 0, treat it as if at position 1 (increment first digit)
        if cursor_pos == 0:
            digit_pos = 0
        else:
            digit_pos = cursor_pos - 1
        
        # Determine step size based on the digit position (left of cursor)
        digits_from_end = len(text) - digit_pos
        step = 10 ** max(0, digits_from_end - 1)
        
        # DO NOT clamp to singleStep() - that would defeat cursor-aware stepping!
        # We want to increment by exactly the step we calculated based on cursor position
        
        # Apply the step
        new_value = self.value() + (steps * step)
        
        # Respect min/max
        new_value = max(self.minimum(), min(self.maximum(), new_value))
        
        # Set value (this will reformat the text)
        self.setValue(new_value)
        
        # Restore cursor position accounting for prefix/suffix/spaces
        new_text = line_edit.text()
        
        # Account for prefix and leading spaces in new text
        adjusted_pos = cursor_pos + prefix_len + leading_spaces
        adjusted_pos = max(0, min(adjusted_pos, len(new_text) - suffix_len))
        
        line_edit.setCursorPosition(adjusted_pos)
        self._last_cursor_pos = adjusted_pos


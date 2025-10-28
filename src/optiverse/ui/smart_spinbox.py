"""Smart spinbox with cursor-aware increments and live updates."""
from __future__ import annotations

from PyQt6 import QtCore, QtGui, QtWidgets


class SmartDoubleSpinBox(QtWidgets.QDoubleSpinBox):
    """
    Enhanced QDoubleSpinBox with:
    1. Cursor-aware increments: up/down arrows increment the digit at cursor position
    2. Live update support via valueChanged signal
    
    Example:
        Value is 123.45, cursor at position 2 (12|3.45) → up arrow → 133.45
        Value is 123.45, cursor at position 5 (123.4|5) → up arrow → 123.55
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._use_cursor_step = True
    
    def stepBy(self, steps: int):
        """Override to increment based on cursor position."""
        if not self._use_cursor_step:
            super().stepBy(steps)
            return
        
        # Get cursor position
        line_edit = self.lineEdit()
        cursor_pos = line_edit.cursorPosition()
        text = line_edit.text()
        
        # Remove suffix/prefix to get clean number text
        suffix = self.suffix()
        prefix = self.prefix()
        
        # Strip prefix and suffix
        if prefix and text.startswith(prefix):
            text = text[len(prefix):]
            cursor_pos -= len(prefix)
        if suffix and text.endswith(suffix):
            text = text[:-len(suffix)]
        
        # Strip spaces
        text = text.strip()
        
        # Find decimal point position
        decimal_pos = text.find('.')
        
        # Determine step size based on cursor position relative to decimal
        if decimal_pos == -1:
            # No decimal point - use integer steps based on distance from end
            digits_from_end = len(text) - cursor_pos
            step = 10 ** max(0, digits_from_end - 1)
        else:
            if cursor_pos <= decimal_pos:
                # Cursor before decimal point (integer part)
                digits_from_decimal = decimal_pos - cursor_pos
                step = 10 ** digits_from_decimal
            else:
                # Cursor after decimal point (fractional part)
                digits_after_decimal = cursor_pos - decimal_pos - 1
                step = 10 ** (-digits_after_decimal - 1)
        
        # Clamp step to single step size minimum
        step = max(step, self.singleStep())
        
        # Apply the step
        new_value = self.value() + (steps * step)
        
        # Respect min/max
        new_value = max(self.minimum(), min(self.maximum(), new_value))
        
        # Set value and preserve cursor position as much as possible
        old_text = line_edit.text()
        self.setValue(new_value)
        
        # Try to restore cursor position
        # If text length changed, adjust cursor proportionally
        new_text = line_edit.text()
        if len(old_text) != len(new_text):
            # Text length changed, try to keep cursor at similar relative position
            if prefix and new_text.startswith(prefix):
                cursor_pos += len(prefix)
            cursor_pos = min(cursor_pos, len(new_text) - len(suffix) if suffix else len(new_text))
        
        line_edit.setCursorPosition(cursor_pos)


class SmartSpinBox(QtWidgets.QSpinBox):
    """
    Enhanced QSpinBox with cursor-aware increments.
    Similar to SmartDoubleSpinBox but for integers.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._use_cursor_step = True
    
    def stepBy(self, steps: int):
        """Override to increment based on cursor position."""
        if not self._use_cursor_step:
            super().stepBy(steps)
            return
        
        # Get cursor position
        line_edit = self.lineEdit()
        cursor_pos = line_edit.cursorPosition()
        text = line_edit.text()
        
        # Remove suffix/prefix to get clean number text
        suffix = self.suffix()
        prefix = self.prefix()
        
        # Strip prefix and suffix
        if prefix and text.startswith(prefix):
            text = text[len(prefix):]
            cursor_pos -= len(prefix)
        if suffix and text.endswith(suffix):
            text = text[:-len(suffix)]
        
        # Strip spaces
        text = text.strip()
        
        # Determine step size based on distance from end
        digits_from_end = len(text) - cursor_pos
        step = 10 ** max(0, digits_from_end - 1)
        
        # Clamp step to single step size minimum
        step = max(step, self.singleStep())
        
        # Apply the step
        new_value = self.value() + (steps * step)
        
        # Respect min/max
        new_value = max(self.minimum(), min(self.maximum(), new_value))
        
        # Set value and preserve cursor position
        old_text = line_edit.text()
        self.setValue(new_value)
        
        # Try to restore cursor position
        new_text = line_edit.text()
        if len(old_text) != len(new_text):
            if prefix and new_text.startswith(prefix):
                cursor_pos += len(prefix)
            cursor_pos = min(cursor_pos, len(new_text) - len(suffix) if suffix else len(new_text))
        
        line_edit.setCursorPosition(cursor_pos)


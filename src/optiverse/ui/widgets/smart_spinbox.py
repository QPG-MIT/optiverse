"""Smart spinbox with cursor-aware increments and live updates."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6 import QtCore, QtWidgets
from PyQt6.QtCore import QLocale

if TYPE_CHECKING:
    from PyQt6.QtWidgets import QLineEdit


class _SmartSpinBoxMixin:
    """
    Mixin providing cursor-aware increment behavior for spinboxes.
    
    This mixin implements the core logic for incrementing values based on
    cursor position. When the up/down arrows are pressed, the digit to the
    LEFT of the cursor is incremented/decremented.
    
    Example:
        Value is 123.45, cursor at 12|3.45 → up arrow → 133.45 (increments the '2')
        Value is 123.45, cursor at 123|.45 → up arrow → 124.45 (increments the '3')
        Value is 123.45, cursor at 123.4|5 → up arrow → 123.55 (increments the '4')
    """
    
    _use_cursor_step: bool
    _last_cursor_pos: int
    
    def _init_smart_spinbox(self) -> None:
        """Initialize the smart spinbox mixin. Call from subclass __init__."""
        self._use_cursor_step = True
        self._last_cursor_pos = 0
        
        # Track cursor position changes in the line edit
        line_edit = self.lineEdit()  # type: ignore[attr-defined]
        if line_edit is not None:
            line_edit.cursorPositionChanged.connect(self._on_cursor_changed)
            line_edit.selectionChanged.connect(self._on_cursor_changed)
            # Install event filter to intercept keyboard Up/Down events
            line_edit.installEventFilter(self)  # type: ignore[arg-type]
    
    def _handle_key_event(self, event: QtCore.QEvent) -> bool:
        """
        Handle keyboard events for Up/Down arrow keys.
        
        Returns True if event was handled, False otherwise.
        """
        if event.type() != QtCore.QEvent.Type.KeyPress:
            return False
            
        key = event.key()  # type: ignore[attr-defined]
        line_edit = self.lineEdit()  # type: ignore[attr-defined]
        
        if line_edit is None:
            return False
            
        if key == QtCore.Qt.Key.Key_Up:
            self._last_cursor_pos = line_edit.cursorPosition()
            self.stepBy(1)  # type: ignore[attr-defined]
            return True
        elif key == QtCore.Qt.Key.Key_Down:
            self._last_cursor_pos = line_edit.cursorPosition()
            self.stepBy(-1)  # type: ignore[attr-defined]
            return True
            
        return False
    
    def _on_cursor_changed(self) -> None:
        """Store the cursor position when it changes."""
        line_edit = self.lineEdit()  # type: ignore[attr-defined]
        if line_edit is not None and line_edit.hasFocus():
            self._last_cursor_pos = line_edit.cursorPosition()
    
    def _get_clean_text_and_cursor(self) -> tuple[str, int, int, int]:
        """
        Get clean number text and adjusted cursor position.
        
        Returns:
            Tuple of (clean_text, cursor_pos, prefix_len, suffix_len)
        """
        line_edit = self.lineEdit()  # type: ignore[attr-defined]
        if line_edit is None:
            return "", 0, 0, 0
            
        text = line_edit.text()
        cursor_pos = self._last_cursor_pos
        
        # Remove suffix/prefix to get clean number text
        suffix = self.suffix()  # type: ignore[attr-defined]
        prefix = self.prefix()  # type: ignore[attr-defined]
        
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
        
        return text, cursor_pos, prefix_len, suffix_len
    
    def _calculate_digit_position(self, cursor_pos: int, text_len: int) -> int:
        """
        Calculate the digit position to increment.
        
        We want to increment the digit to the LEFT of the cursor.
        If cursor is at position 0, treat it as if at position 1.
        """
        if cursor_pos == 0:
            return 0
        return cursor_pos - 1
    
    def _restore_cursor_position(
        self, 
        offset_from_decimal: int | None,
        offset_from_end: int,
        prefix_len: int,
        suffix_len: int
    ) -> None:
        """Restore cursor position after value change."""
        line_edit = self.lineEdit()  # type: ignore[attr-defined]
        if line_edit is None:
            return
            
        new_text = line_edit.text()
        prefix = self.prefix()  # type: ignore[attr-defined]
        suffix = self.suffix()  # type: ignore[attr-defined]
        
        # Strip prefix/suffix from new text to find new decimal position
        new_clean = new_text
        if prefix and new_clean.startswith(prefix):
            new_clean = new_clean[prefix_len:]
        if suffix and new_clean.endswith(suffix):
            new_clean = new_clean[:-suffix_len]
        new_leading = len(new_clean) - len(new_clean.lstrip())
        new_clean = new_clean.strip()
        
        # Find decimal position in new text
        new_decimal_pos = new_clean.find(".")
        
        # Calculate new cursor position maintaining same offset from decimal
        if offset_from_decimal is not None and new_decimal_pos != -1:
            new_cursor_pos = new_decimal_pos + offset_from_decimal
        else:
            # Fallback: maintain position from end
            new_cursor_pos = len(new_clean) - offset_from_end
        
        new_cursor_pos = max(0, min(new_cursor_pos, len(new_clean)))
        adjusted_pos = new_cursor_pos + prefix_len + new_leading
        adjusted_pos = max(0, min(adjusted_pos, len(new_text) - suffix_len))
        
        line_edit.setCursorPosition(adjusted_pos)
        self._last_cursor_pos = adjusted_pos


class SmartDoubleSpinBox(_SmartSpinBoxMixin, QtWidgets.QDoubleSpinBox):
    """
    Enhanced QDoubleSpinBox with cursor-aware increments.
    
    Up/down arrows increment the digit to the LEFT of cursor position.
    Supports decimal values with proper cursor restoration.
    """

    def __init__(self, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)
        # Force period as decimal separator regardless of system locale
        self.setLocale(QLocale.c())
        
        # Set a very small singleStep to avoid interference
        self.setSingleStep(0.001)
        
        # Initialize mixin
        self._init_smart_spinbox()

    def eventFilter(self, obj: QtCore.QObject | None, event: QtCore.QEvent | None) -> bool:
        """Intercept keyboard events from line edit."""
        if obj is None or event is None:
            return False
        if obj == self.lineEdit() and self._handle_key_event(event):
            return True
        return super().eventFilter(obj, event)

    def stepBy(self, steps: int) -> None:
        """Override to increment based on cursor position."""
        if not self._use_cursor_step:
            super().stepBy(steps)
            return

        line_edit = self.lineEdit()
        if line_edit is None:
            return
            
        text, cursor_pos, prefix_len, suffix_len = self._get_clean_text_and_cursor()
        if not text:
            super().stepBy(steps)
            return
        
        digit_pos = self._calculate_digit_position(cursor_pos, len(text))
        
        # Find decimal point position
        decimal_pos = text.find(".")
        
        # Determine step size based on the digit position (left of cursor)
        if decimal_pos == -1:
            # No decimal point - use integer steps based on distance from end
            digits_from_end = len(text) - digit_pos
            step = 10 ** max(0, digits_from_end - 1)
        else:
            if digit_pos < decimal_pos:
                # Digit is before decimal point (integer part)
                digits_from_decimal = decimal_pos - digit_pos
                step = 10 ** (digits_from_decimal - 1)
            else:
                # Digit is after decimal point (fractional part)
                digits_after_decimal = digit_pos - decimal_pos - 1
                step = 10 ** (-digits_after_decimal - 1)
        
        # Save offset from decimal point BEFORE changing value
        offset_from_decimal = cursor_pos - decimal_pos if decimal_pos != -1 else None
        offset_from_end = len(text) - cursor_pos
        
        # Apply the step
        new_value = self.value() + (steps * step)
        new_value = max(self.minimum(), min(self.maximum(), new_value))
        self.setValue(new_value)
        
        # Restore cursor position
        self._restore_cursor_position(
            offset_from_decimal, offset_from_end, prefix_len, suffix_len
        )


class SmartSpinBox(_SmartSpinBoxMixin, QtWidgets.QSpinBox):
    """
    Enhanced QSpinBox with cursor-aware increments.
    
    Up/down arrows increment the digit to the LEFT of cursor position.
    Integer-only version of SmartDoubleSpinBox.
    """

    def __init__(self, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)
        # Force period as decimal separator regardless of system locale
        self.setLocale(QLocale.c())
        
        # Set singleStep to 1 (minimum for integers)
        self.setSingleStep(1)
        
        # Initialize mixin
        self._init_smart_spinbox()

    def eventFilter(self, obj: QtCore.QObject | None, event: QtCore.QEvent | None) -> bool:
        """Intercept keyboard events from line edit."""
        if obj is None or event is None:
            return False
        if obj == self.lineEdit() and self._handle_key_event(event):
            return True
        return super().eventFilter(obj, event)

    def stepBy(self, steps: int) -> None:
        """Override to increment based on cursor position."""
        if not self._use_cursor_step:
            super().stepBy(steps)
            return

        line_edit = self.lineEdit()
        if line_edit is None:
            return
            
        text, cursor_pos, prefix_len, suffix_len = self._get_clean_text_and_cursor()
        if not text:
            super().stepBy(steps)
            return
        
        digit_pos = self._calculate_digit_position(cursor_pos, len(text))
        
        # Determine step size based on the digit position (left of cursor)
        digits_from_end = len(text) - digit_pos
        step = 10 ** max(0, digits_from_end - 1)
        
        # Save offset from end BEFORE changing value
        offset_from_end = len(text) - cursor_pos
        
        # Apply the step
        new_value = self.value() + (steps * step)
        new_value = max(self.minimum(), min(self.maximum(), new_value))
        self.setValue(new_value)
        
        # Restore cursor position (no decimal for integers)
        self._restore_cursor_position(None, offset_from_end, prefix_len, suffix_len)

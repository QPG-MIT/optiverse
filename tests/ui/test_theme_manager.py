"""
Tests for ThemeManager.

These tests verify:
- Stylesheet loading from files and fallbacks
- Dark/light mode detection
- Theme application
- Question dialog helper
"""

from __future__ import annotations

from optiverse.ui.theme_manager import (
    _create_dark_palette,
    _create_light_palette,
    apply_theme,
    detect_system_dark_mode,
    get_dark_stylesheet,
    get_light_stylesheet,
    is_dark_mode,
)


class TestStylesheetLoading:
    """Tests for stylesheet loading."""

    def test_get_dark_stylesheet(self):
        """Test getting dark stylesheet returns non-empty string."""
        stylesheet = get_dark_stylesheet()
        assert isinstance(stylesheet, str)
        assert len(stylesheet) > 0
        assert "background" in stylesheet.lower()

    def test_get_light_stylesheet(self):
        """Test getting light stylesheet returns non-empty string."""
        stylesheet = get_light_stylesheet()
        assert isinstance(stylesheet, str)
        assert len(stylesheet) > 0
        assert "background" in stylesheet.lower()

    def test_dark_stylesheet_has_dark_colors(self):
        """Test that dark stylesheet contains dark color values."""
        stylesheet = get_dark_stylesheet()
        # Dark mode should have dark background colors
        assert "#1a1c21" in stylesheet or "#2d2f36" in stylesheet or "dark" in stylesheet.lower()

    def test_light_stylesheet_has_light_colors(self):
        """Test that light stylesheet contains light color values."""
        stylesheet = get_light_stylesheet()
        # Light mode should have light background colors
        assert "white" in stylesheet.lower() or "#f" in stylesheet.lower()


class TestPaletteCreation:
    """Tests for palette creation."""

    def test_create_dark_palette(self, qapp):
        """Test creating dark palette."""
        from PyQt6 import QtGui

        palette = _create_dark_palette()

        assert isinstance(palette, QtGui.QPalette)

        # Window color should be dark
        window_color = palette.color(QtGui.QPalette.ColorRole.Window)
        assert window_color.lightness() < 100

        # Text should be light
        text_color = palette.color(QtGui.QPalette.ColorRole.WindowText)
        assert text_color.lightness() > 200

    def test_create_light_palette(self, qapp):
        """Test creating light palette."""
        from PyQt6 import QtGui

        palette = _create_light_palette()

        assert isinstance(palette, QtGui.QPalette)

        # Window color should be light
        window_color = palette.color(QtGui.QPalette.ColorRole.Window)
        assert window_color.lightness() > 200

        # Text should be dark
        text_color = palette.color(QtGui.QPalette.ColorRole.WindowText)
        assert text_color.lightness() < 100


class TestThemeDetection:
    """Tests for theme detection."""

    def test_detect_system_dark_mode_returns_bool(self, qapp):
        """Test that detect_system_dark_mode returns a boolean."""
        result = detect_system_dark_mode()
        assert isinstance(result, bool)

    def test_is_dark_mode_returns_bool(self, qapp):
        """Test that is_dark_mode returns a boolean."""
        result = is_dark_mode()
        assert isinstance(result, bool)


class TestThemeApplication:
    """Tests for applying themes."""

    def test_apply_dark_theme(self, qapp):
        """Test applying dark theme."""
        from PyQt6 import QtGui

        apply_theme(dark_mode=True)

        # Check palette was set to dark
        palette = qapp.palette()
        window_color = palette.color(QtGui.QPalette.ColorRole.Window)
        assert window_color.lightness() < 100

    def test_apply_light_theme(self, qapp):
        """Test applying light theme."""
        from PyQt6 import QtGui

        apply_theme(dark_mode=False)

        # Check palette was set to light
        palette = qapp.palette()
        window_color = palette.color(QtGui.QPalette.ColorRole.Window)
        assert window_color.lightness() > 200

    def test_apply_theme_sets_stylesheet(self, qapp):
        """Test that applying theme sets stylesheet."""
        apply_theme(dark_mode=True)

        stylesheet = qapp.styleSheet()
        assert len(stylesheet) > 0

    def test_theme_toggle(self, qapp):
        """Test toggling between themes."""
        from PyQt6 import QtGui

        # Apply dark
        apply_theme(dark_mode=True)
        dark_window = qapp.palette().color(QtGui.QPalette.ColorRole.Window)

        # Apply light
        apply_theme(dark_mode=False)
        light_window = qapp.palette().color(QtGui.QPalette.ColorRole.Window)

        # Should be different
        assert dark_window != light_window


class TestIsDarkModeAfterApply:
    """Tests for is_dark_mode after theme application."""

    def test_is_dark_mode_after_dark_theme(self, qapp):
        """Test is_dark_mode returns True after applying dark theme."""
        apply_theme(dark_mode=True)
        assert is_dark_mode() is True

    def test_is_dark_mode_after_light_theme(self, qapp):
        """Test is_dark_mode returns False after applying light theme."""
        apply_theme(dark_mode=False)
        assert is_dark_mode() is False


class TestQuestionDialog:
    """Tests for question dialog helper."""

    def test_question_function_exists(self):
        """Test that question function can be imported."""
        from optiverse.ui.theme_manager import question

        assert callable(question)

    # Note: Can't test actual dialog display without user interaction
    # The question() function is tested indirectly through integration tests

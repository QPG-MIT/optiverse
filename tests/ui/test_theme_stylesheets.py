"""Tests for application theme stylesheet coverage."""

from __future__ import annotations

import pytest

try:
    from optiverse.ui.theme_manager import get_dark_stylesheet, get_light_stylesheet

    HAVE_PYQT6 = True
except ImportError:
    HAVE_PYQT6 = False


pytestmark = pytest.mark.skipif(not HAVE_PYQT6, reason="PyQt6 not available")


def test_file_dialog_toolbar_buttons_have_explicit_theme_styles():
    for stylesheet in (get_light_stylesheet(), get_dark_stylesheet()):
        assert "QFileDialog QToolButton" in stylesheet
        assert "min-width: 24px" in stylesheet
        assert "background-color: #2d2f36" in stylesheet

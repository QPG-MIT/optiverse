"""
Tests for application context and entry point.
"""

from __future__ import annotations


def test_app_context_create_default():
    """Test creating default AppContext."""
    from optiverse.app.app_context import AppContext

    ctx = AppContext.create_default()
    assert ctx.settings is not None
    assert ctx.storage is not None


def test_app_entry_imports():
    """Test that main entry point can be imported and is callable."""
    from optiverse.app.main import main

    assert callable(main)


def test_app_context_has_expected_services():
    """Test that AppContext provides expected services."""
    from optiverse.app.app_context import AppContext

    ctx = AppContext.create_default()

    # Check all expected services exist
    assert hasattr(ctx, "settings")
    assert hasattr(ctx, "storage")

    # Services should not be None
    assert ctx.settings is not None
    assert ctx.storage is not None

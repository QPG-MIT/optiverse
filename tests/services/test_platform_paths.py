"""
Tests for platform-specific path resolution.

These tests verify that:
- Library paths are correctly resolved
- Asset directories exist
- Paths work across different platforms
"""

from __future__ import annotations

import os


def test_platform_paths_exposes_core_dirs(tmp_path, monkeypatch):
    """Test that platform paths exposes core directory functions."""
    # Force HOME to tmp so paths resolve under it for the test
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))  # Windows

    from optiverse.platform.paths import assets_dir, get_library_path, library_root_dir

    root = library_root_dir()
    assets = assets_dir()
    lib = get_library_path()

    assert os.path.isdir(root)
    assert os.path.isdir(assets)
    assert os.path.dirname(lib) == root


def test_library_root_dir_exists(tmp_path, monkeypatch):
    """Test that library root directory is created if needed."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))

    from optiverse.platform.paths import library_root_dir

    root = library_root_dir()
    assert os.path.exists(root)
    assert os.path.isdir(root)


def test_assets_dir_exists(tmp_path, monkeypatch):
    """Test that assets directory exists."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))

    from optiverse.platform.paths import assets_dir

    assets = assets_dir()
    assert os.path.exists(assets)
    assert os.path.isdir(assets)


def test_library_path_is_valid(tmp_path, monkeypatch):
    """Test that library path is a valid path."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))

    from optiverse.platform.paths import get_library_path

    lib_path = get_library_path()
    # Path should be in the library root
    assert lib_path is not None
    assert len(lib_path) > 0

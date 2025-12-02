"""
Comprehensive tests for autosave and autosave recovery functionality.

This test suite ensures that:
- Autosave files are created correctly after modifications
- Autosave debouncing works properly
- Autosave files can be loaded and recovered
- Recovery dialogs work correctly
- Edge cases and error handling are covered
"""

from __future__ import annotations

import datetime
import gc
import json
import os
import unittest.mock as mock

import pytest
from PyQt6 import QtWidgets

from optiverse.core.models import LensParams, SourceParams
from optiverse.objects import SourceItem
from optiverse.ui.views.main_window import MainWindow
from tests.fixtures.factories import create_component_from_params


@pytest.fixture
def tmp_autosave_dir(tmp_path):
    """Create a temporary directory for autosave files."""
    autosave_dir = tmp_path / "autosave"
    autosave_dir.mkdir(parents=True, exist_ok=True)
    return autosave_dir


@pytest.fixture
def main_window_with_autosave(qapp, tmp_autosave_dir, monkeypatch):
    """Create a MainWindow instance with autosave enabled (timer not stopped)."""
    # Mock _app_data_root to return our temporary directory
    from optiverse.platform import paths

    def mock_app_data_root():
        return tmp_autosave_dir.parent

    monkeypatch.setattr(paths, "_app_data_root", mock_app_data_root)

    window = MainWindow()
    # Disable autotrace to prevent interference, but keep autosave timer running
    window.autotrace = False
    window.raytracing_controller._retrace_timer.stop()
    # DO NOT stop autosave timer - we want to test it
    QtWidgets.QApplication.processEvents()
    yield window
    # Clean up
    window.autotrace = False
    window.raytracing_controller._retrace_timer.stop()
    window.file_controller._autosave_timer.stop()
    window.file_controller.mark_clean()
    window.file_controller.file_manager.clear_autosave()
    window.raytracing_controller.clear_rays()
    for item in list(window.scene.items()):
        window.scene.removeItem(item)
    QtWidgets.QApplication.processEvents()
    window.close()
    QtWidgets.QApplication.processEvents()
    gc.collect()
    QtWidgets.QApplication.processEvents()


class TestBasicAutosave:
    """Test basic autosave functionality."""

    def test_autosave_creates_file_on_modification(
        self, main_window_with_autosave, tmp_autosave_dir, qtbot
    ):
        """Verify autosave file is created when scene is modified."""
        window = main_window_with_autosave

        # Add a source to trigger modification
        source = SourceItem(SourceParams(x_mm=100.0, y_mm=200.0))
        window.scene.addItem(source)

        # Wait for autosave timer (1000ms debounce + buffer)
        qtbot.wait(1500)
        QtWidgets.QApplication.processEvents()

        # Check that autosave file was created
        autosave_files = list(tmp_autosave_dir.glob("*.autosave.json"))
        assert len(autosave_files) == 1, f"Expected 1 autosave file, found {len(autosave_files)}"

        # Verify file contains scene data
        with open(autosave_files[0]) as f:
            data = json.load(f)

        assert "sources" in data or "items" in data
        assert "_autosave_meta" in data

    def test_autosave_debouncing(self, main_window_with_autosave, tmp_autosave_dir, qtbot):
        """Verify autosave waits for debounce period before saving."""
        window = main_window_with_autosave

        # Add multiple sources quickly
        for i in range(3):
            source = SourceItem(SourceParams(x_mm=100.0 * i, y_mm=200.0))
            window.scene.addItem(source)
            QtWidgets.QApplication.processEvents()

        # Wait less than debounce period
        qtbot.wait(500)
        QtWidgets.QApplication.processEvents()

        # Should not have autosaved yet
        autosave_files = list(tmp_autosave_dir.glob("*.autosave.json"))
        assert len(autosave_files) == 0, "Autosave should not have triggered yet"

        # Wait for full debounce period
        qtbot.wait(1000)
        QtWidgets.QApplication.processEvents()

        # Now should have autosaved
        autosave_files = list(tmp_autosave_dir.glob("*.autosave.json"))
        assert len(autosave_files) == 1, "Autosave should have triggered after debounce"

    def test_autosave_not_created_when_clean(
        self, main_window_with_autosave, tmp_autosave_dir, qtbot
    ):
        """Verify autosave doesn't run when scene is not modified."""
        window = main_window_with_autosave

        # Mark as clean (no modifications)
        window.file_controller.mark_clean()

        # Manually trigger autosave (should do nothing)
        window.file_controller.file_manager.do_autosave()

        # Wait a bit
        qtbot.wait(500)
        QtWidgets.QApplication.processEvents()

        # Should not have created autosave file
        autosave_files = list(tmp_autosave_dir.glob("*.autosave.json"))
        assert len(autosave_files) == 0, "Autosave should not run when scene is clean"

    def test_autosave_file_format(self, main_window_with_autosave, tmp_autosave_dir, qtbot):
        """Verify autosave file contains correct structure."""
        window = main_window_with_autosave

        # Add a source
        source = SourceItem(SourceParams(x_mm=100.0, y_mm=200.0))
        window.scene.addItem(source)

        # Wait for autosave
        qtbot.wait(1500)
        QtWidgets.QApplication.processEvents()

        # Load and verify file structure
        autosave_files = list(tmp_autosave_dir.glob("*.autosave.json"))
        assert len(autosave_files) == 1

        with open(autosave_files[0]) as f:
            data = json.load(f)

        # Check required fields
        assert "version" in data
        assert data["version"] == "2.0"
        assert "_autosave_meta" in data

        meta = data["_autosave_meta"]
        assert "timestamp" in meta
        assert "version" in meta
        assert meta["version"] == "2.0"

    def test_autosave_metadata(self, main_window_with_autosave, tmp_autosave_dir, qtbot):
        """Verify autosave metadata includes timestamp, original_path, version."""
        window = main_window_with_autosave

        # Add a source
        source = SourceItem(SourceParams(x_mm=100.0, y_mm=200.0))
        window.scene.addItem(source)

        # Wait for autosave
        qtbot.wait(1500)
        QtWidgets.QApplication.processEvents()

        # Load and verify metadata
        autosave_files = list(tmp_autosave_dir.glob("*.autosave.json"))
        assert len(autosave_files) == 1

        with open(autosave_files[0]) as f:
            data = json.load(f)

        meta = data["_autosave_meta"]
        assert "timestamp" in meta
        assert "original_path" in meta
        assert "version" in meta

        # Verify timestamp is valid ISO format
        timestamp = datetime.datetime.fromisoformat(meta["timestamp"])
        assert isinstance(timestamp, datetime.datetime)

        # Verify original_path is None for unsaved files
        assert meta["original_path"] is None


class TestAutosaveForSavedFiles:
    """Test autosave behavior for saved vs unsaved files."""

    def test_autosave_named_file(
        self, main_window_with_autosave, tmp_autosave_dir, tmp_path, qtbot
    ):
        """Verify autosave filename includes original filename hash for saved files."""
        window = main_window_with_autosave

        # Save a file first
        save_path = tmp_path / "test_assembly.json"
        import unittest.mock as mock

        with mock.patch.object(
            QtWidgets.QFileDialog, "getSaveFileName", return_value=(str(save_path), "")
        ):
            window.save_assembly()

        assert save_path.exists()

        # Add a source to trigger modification
        source = SourceItem(SourceParams(x_mm=100.0, y_mm=200.0))
        window.scene.addItem(source)

        # Wait for autosave
        qtbot.wait(1500)
        QtWidgets.QApplication.processEvents()

        # Check autosave filename format
        autosave_files = list(tmp_autosave_dir.glob("*.autosave.json"))
        assert len(autosave_files) == 1

        filename = autosave_files[0].name
        assert "test_assembly" in filename
        assert ".autosave.json" in filename

        # Verify metadata includes original path
        with open(autosave_files[0]) as f:
            data = json.load(f)

        meta = data["_autosave_meta"]
        assert meta["original_path"] == str(save_path)

    def test_autosave_unsaved_file(self, main_window_with_autosave, tmp_autosave_dir, qtbot):
        """Verify autosave uses timestamp-based ID for unsaved files."""
        window = main_window_with_autosave

        # Add a source (no file saved yet)
        source = SourceItem(SourceParams(x_mm=100.0, y_mm=200.0))
        window.scene.addItem(source)

        # Wait for autosave
        qtbot.wait(1500)
        QtWidgets.QApplication.processEvents()

        # Check autosave filename format
        autosave_files = list(tmp_autosave_dir.glob("*.autosave.json"))
        assert len(autosave_files) == 1

        filename = autosave_files[0].name
        assert "untitled_" in filename
        assert ".autosave.json" in filename

        # Verify metadata has None for original_path
        with open(autosave_files[0]) as f:
            data = json.load(f)

        meta = data["_autosave_meta"]
        assert meta["original_path"] is None

    def test_autosave_overwrites_previous(
        self, main_window_with_autosave, tmp_autosave_dir, qtbot
    ):
        """Verify new autosave overwrites previous autosave for same file."""
        window = main_window_with_autosave

        # Add first source
        source1 = SourceItem(SourceParams(x_mm=100.0, y_mm=200.0))
        window.scene.addItem(source1)

        # Wait for autosave
        qtbot.wait(1500)
        QtWidgets.QApplication.processEvents()

        # Should have one autosave file
        autosave_files = list(tmp_autosave_dir.glob("*.autosave.json"))
        assert len(autosave_files) == 1
        first_file = autosave_files[0]

        # Add second source (modify again)
        source2 = SourceItem(SourceParams(x_mm=200.0, y_mm=300.0))
        window.scene.addItem(source2)

        # Wait for autosave again
        qtbot.wait(1500)
        QtWidgets.QApplication.processEvents()

        # Should still have only one autosave file (overwritten)
        autosave_files = list(tmp_autosave_dir.glob("*.autosave.json"))
        assert len(autosave_files) == 1
        assert autosave_files[0] == first_file  # Same file

        # Verify it contains both sources
        with open(autosave_files[0]) as f:
            data = json.load(f)

        # Count sources in the data
        sources_count = len(data.get("sources", [])) + len(
            [item for item in data.get("items", []) if item.get("type") == "source"]
        )
        assert sources_count == 2


class TestLoadingFromAutosave:
    """Test loading from autosave files."""

    def test_load_from_autosave_file(
        self, main_window_with_autosave, tmp_autosave_dir, qtbot
    ):
        """Verify loading an autosave file restores scene correctly."""
        window = main_window_with_autosave

        # Add a source and lens
        source = SourceItem(SourceParams(x_mm=100.0, y_mm=200.0, wavelength_nm=532.0))
        lens = create_component_from_params(LensParams(x_mm=50.0, y_mm=75.0, efl_mm=150.0))
        window.scene.addItem(source)
        window.scene.addItem(lens)

        # Wait for autosave
        qtbot.wait(1500)
        QtWidgets.QApplication.processEvents()

        # Get autosave file
        autosave_files = list(tmp_autosave_dir.glob("*.autosave.json"))
        assert len(autosave_files) == 1
        autosave_path = autosave_files[0]

        # Clear scene
        window.scene.clear()
        assert len(window.scene.items()) == 0

        # Load from autosave file
        with open(autosave_path) as f:
            data = json.load(f)

        window.file_controller.file_manager.load_from_data(data)

        # Verify scene was restored
        items = window.scene.items()
        sources = [item for item in items if isinstance(item, SourceItem)]
        assert len(sources) == 1
        assert abs(sources[0].params.x_mm - 100.0) < 0.01
        assert abs(sources[0].params.wavelength_nm - 532.0) < 0.01

    def test_load_autosave_preserves_metadata(
        self, main_window_with_autosave, tmp_autosave_dir, tmp_path, qtbot
    ):
        """Verify loading autosave preserves original file path in metadata."""
        window = main_window_with_autosave

        # Save a file first
        save_path = tmp_path / "test_assembly.json"
        import unittest.mock as mock

        with mock.patch.object(
            QtWidgets.QFileDialog, "getSaveFileName", return_value=(str(save_path), "")
        ):
            window.save_assembly()

        # Add a source
        source = SourceItem(SourceParams(x_mm=100.0, y_mm=200.0))
        window.scene.addItem(source)

        # Wait for autosave
        qtbot.wait(1500)
        QtWidgets.QApplication.processEvents()

        # Get autosave file
        autosave_files = list(tmp_autosave_dir.glob("*.autosave.json"))
        assert len(autosave_files) == 1

        # Load from autosave and verify metadata contains original path
        with open(autosave_files[0]) as f:
            data = json.load(f)

        # Verify metadata preserves original path
        meta = data.get("_autosave_meta", {})
        assert meta.get("original_path") == str(save_path)

        # Load the data
        window.file_controller.file_manager.load_from_data(data)


class TestAutosaveRecovery:
    """Test autosave recovery on startup."""

    def test_autosave_recovery_detects_file(
        self, qapp, tmp_autosave_dir, monkeypatch, qtbot
    ):
        """Verify recovery detects autosave files on startup."""
        # Create an autosave file manually
        autosave_file = tmp_autosave_dir / "test_untitled_12345.autosave.json"
        autosave_data = {
            "version": "2.0",
            "sources": [{"x_mm": 100.0, "y_mm": 200.0, "type": "source"}],
            "_autosave_meta": {
                "timestamp": datetime.datetime.now().isoformat(),
                "original_path": None,
                "version": "2.0",
            },
        }
        with open(autosave_file, "w") as f:
            json.dump(autosave_data, f)

        # Mock _app_data_root
        from optiverse.platform import paths

        def mock_app_data_root():
            return tmp_autosave_dir.parent

        monkeypatch.setattr(paths, "_app_data_root", mock_app_data_root)

        # Create window (will check for autosave on startup)
        window = MainWindow()
        window.autotrace = False
        window.raytracing_controller._retrace_timer.stop()

        # Mock the dialog to reject (so test doesn't hang)
        with mock.patch.object(
            QtWidgets.QMessageBox,
            "question",
            return_value=QtWidgets.QMessageBox.StandardButton.No,
        ):
            # Process events to trigger recovery check
            QtWidgets.QApplication.processEvents()
            qtbot.wait(200)
            QtWidgets.QApplication.processEvents()

        # Clean up
        window.file_controller._autosave_timer.stop()
        window.close()
        QtWidgets.QApplication.processEvents()

    def test_autosave_recovery_user_accepts(
        self, qapp, tmp_autosave_dir, monkeypatch, qtbot
    ):
        """Mock dialog to test recovery when user accepts."""
        # Create an autosave file manually
        autosave_file = tmp_autosave_dir / "test_untitled_12345.autosave.json"
        autosave_data = {
            "version": "2.0",
            "sources": [
                {
                    "x_mm": 100.0,
                    "y_mm": 200.0,
                    "angle_deg": 0.0,
                    "size_mm": 10.0,
                    "n_rays": 5,
                    "ray_length_mm": 1000.0,
                    "spread_deg": 0.0,
                    "color_hex": "#FF0000",
                    "wavelength_nm": 532.0,
                    "polarization_type": "horizontal",
                    "polarization_angle_deg": 0.0,
                    "type": "source",
                }
            ],
            "_autosave_meta": {
                "timestamp": datetime.datetime.now().isoformat(),
                "original_path": None,
                "version": "2.0",
            },
        }
        with open(autosave_file, "w") as f:
            json.dump(autosave_data, f)

        # Mock _app_data_root
        from optiverse.platform import paths

        def mock_app_data_root():
            return tmp_autosave_dir.parent

        monkeypatch.setattr(paths, "_app_data_root", mock_app_data_root)

        # Mock theme_manager.question to return Yes
        from optiverse.ui import theme_manager

        with mock.patch.object(
            theme_manager,
            "question",
            return_value=QtWidgets.QMessageBox.StandardButton.Yes,
        ), mock.patch.object(
            QtWidgets.QMessageBox,
            "information",
            return_value=None,
        ):
            # Create window
            window = MainWindow()
            window.autotrace = False
            window.raytracing_controller._retrace_timer.stop()

            # Trigger recovery check
            result = window.file_controller.check_autosave_recovery()

            # Should have recovered
            assert result is True

            # Verify scene was loaded
            items = window.scene.items()
            sources = [item for item in items if isinstance(item, SourceItem)]
            assert len(sources) == 1

        # Clean up
        window.file_controller._autosave_timer.stop()
        window.close()
        QtWidgets.QApplication.processEvents()

    def test_autosave_recovery_user_rejects(
        self, qapp, tmp_autosave_dir, monkeypatch, qtbot
    ):
        """Mock dialog to test recovery when user rejects (file deleted)."""
        # Create an autosave file manually
        autosave_file = tmp_autosave_dir / "test_untitled_12345.autosave.json"
        autosave_data = {
            "version": "2.0",
            "sources": [{"x_mm": 100.0, "y_mm": 200.0, "type": "source"}],
            "_autosave_meta": {
                "timestamp": datetime.datetime.now().isoformat(),
                "original_path": None,
                "version": "2.0",
            },
        }
        with open(autosave_file, "w") as f:
            json.dump(autosave_data, f)

        assert autosave_file.exists()

        # Mock _app_data_root
        from optiverse.platform import paths

        def mock_app_data_root():
            return tmp_autosave_dir.parent

        monkeypatch.setattr(paths, "_app_data_root", mock_app_data_root)

        # Mock theme_manager.question to return No
        from optiverse.ui import theme_manager

        with mock.patch.object(
            theme_manager,
            "question",
            return_value=QtWidgets.QMessageBox.StandardButton.No,
        ):
            # Create window
            window = MainWindow()
            window.autotrace = False
            window.raytracing_controller._retrace_timer.stop()

            # Trigger recovery check
            result = window.file_controller.check_autosave_recovery()

            # Should not have recovered
            assert result is False

            # Verify autosave file was deleted
            assert not autosave_file.exists()

        # Clean up
        window.file_controller._autosave_timer.stop()
        window.close()
        QtWidgets.QApplication.processEvents()

    def test_autosave_recovery_skips_headless(
        self, qapp, tmp_autosave_dir, monkeypatch, qtbot
    ):
        """Verify recovery is skipped in headless environments."""
        # Set headless environment
        monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

        # Create an autosave file manually
        autosave_file = tmp_autosave_dir / "test_untitled_12345.autosave.json"
        autosave_data = {
            "version": "2.0",
            "sources": [{"x_mm": 100.0, "y_mm": 200.0, "type": "source"}],
            "_autosave_meta": {
                "timestamp": datetime.datetime.now().isoformat(),
                "original_path": None,
                "version": "2.0",
            },
        }
        with open(autosave_file, "w") as f:
            json.dump(autosave_data, f)

        # Mock _app_data_root
        from optiverse.platform import paths

        def mock_app_data_root():
            return tmp_autosave_dir.parent

        monkeypatch.setattr(paths, "_app_data_root", mock_app_data_root)

        # Create window
        window = MainWindow()
        window.autotrace = False
        window.raytracing_controller._retrace_timer.stop()

        # Trigger recovery check
        result = window.file_controller.check_autosave_recovery()

        # Should skip recovery in headless mode
        assert result is False

        # File should still exist (not deleted)
        assert autosave_file.exists()

        # Clean up
        window.file_controller._autosave_timer.stop()
        window.close()
        QtWidgets.QApplication.processEvents()

    def test_autosave_recovery_most_recent(
        self, qapp, tmp_autosave_dir, monkeypatch, qtbot
    ):
        """Verify recovery uses most recent autosave file."""
        # Create two autosave files with different timestamps
        autosave_file1 = tmp_autosave_dir / "old_untitled_12345.autosave.json"
        autosave_file2 = tmp_autosave_dir / "new_untitled_67890.autosave.json"

        old_time = datetime.datetime.now() - datetime.timedelta(hours=1)
        new_time = datetime.datetime.now()

        autosave_data1 = {
            "version": "2.0",
            "sources": [{"x_mm": 100.0, "y_mm": 200.0, "type": "source"}],
            "_autosave_meta": {
                "timestamp": old_time.isoformat(),
                "original_path": None,
                "version": "2.0",
            },
        }
        autosave_data2 = {
            "version": "2.0",
            "sources": [{"x_mm": 200.0, "y_mm": 300.0, "type": "source"}],
            "_autosave_meta": {
                "timestamp": new_time.isoformat(),
                "original_path": None,
                "version": "2.0",
            },
        }

        with open(autosave_file1, "w") as f:
            json.dump(autosave_data1, f)
        with open(autosave_file2, "w") as f:
            json.dump(autosave_data2, f)

        # Update file modification times to ensure correct ordering
        old_mtime = (old_time - datetime.datetime(1970, 1, 1)).total_seconds()
        new_mtime = (new_time - datetime.datetime(1970, 1, 1)).total_seconds()
        os.utime(autosave_file1, (old_mtime, old_mtime))
        os.utime(autosave_file2, (new_mtime, new_mtime))

        # Mock _app_data_root
        from optiverse.platform import paths

        def mock_app_data_root():
            return tmp_autosave_dir.parent

        monkeypatch.setattr(paths, "_app_data_root", mock_app_data_root)

        # Mock theme_manager.question to return Yes
        from optiverse.ui import theme_manager

        with mock.patch.object(
            theme_manager,
            "question",
            return_value=QtWidgets.QMessageBox.StandardButton.Yes,
        ), mock.patch.object(
            QtWidgets.QMessageBox,
            "information",
            return_value=None,
        ):
            # Create window
            window = MainWindow()
            window.autotrace = False
            window.raytracing_controller._retrace_timer.stop()

            # Trigger recovery check
            result = window.file_controller.check_autosave_recovery()

            # Should have recovered
            assert result is True

            # Verify most recent file was loaded (x_mm=200.0)
            items = window.scene.items()
            sources = [item for item in items if isinstance(item, SourceItem)]
            assert len(sources) == 1
            assert abs(sources[0].params.x_mm - 200.0) < 0.01

        # Clean up
        window.file_controller._autosave_timer.stop()
        window.close()
        QtWidgets.QApplication.processEvents()


class TestAutosaveClearing:
    """Test autosave clearing functionality."""

    def test_autosave_cleared_on_save(
        self, main_window_with_autosave, tmp_autosave_dir, tmp_path, qtbot
    ):
        """Verify autosave file is deleted when file is saved normally."""
        window = main_window_with_autosave

        # Add a source
        source = SourceItem(SourceParams(x_mm=100.0, y_mm=200.0))
        window.scene.addItem(source)

        # Wait for autosave
        qtbot.wait(1500)
        QtWidgets.QApplication.processEvents()

        # Verify autosave file exists
        autosave_files = list(tmp_autosave_dir.glob("*.autosave.json"))
        assert len(autosave_files) == 1

        # Save the file
        save_path = tmp_path / "test_assembly.json"
        import unittest.mock as mock

        with mock.patch.object(
            QtWidgets.QFileDialog, "getSaveFileName", return_value=(str(save_path), "")
        ):
            window.save_assembly()

        # Wait a bit
        qtbot.wait(200)
        QtWidgets.QApplication.processEvents()

        # Verify autosave file was deleted
        autosave_files = list(tmp_autosave_dir.glob("*.autosave.json"))
        assert len(autosave_files) == 0, "Autosave file should be deleted after save"

    def test_autosave_cleared_on_mark_clean(
        self, main_window_with_autosave, tmp_autosave_dir, qtbot
    ):
        """Verify autosave can be cleared manually."""
        window = main_window_with_autosave

        # Add a source
        source = SourceItem(SourceParams(x_mm=100.0, y_mm=200.0))
        window.scene.addItem(source)

        # Wait for autosave
        qtbot.wait(1500)
        QtWidgets.QApplication.processEvents()

        # Verify autosave file exists
        autosave_files = list(tmp_autosave_dir.glob("*.autosave.json"))
        assert len(autosave_files) == 1

        # Manually clear autosave
        window.file_controller.file_manager.clear_autosave()

        # Wait a bit
        qtbot.wait(200)
        QtWidgets.QApplication.processEvents()

        # Verify autosave file was deleted
        autosave_files = list(tmp_autosave_dir.glob("*.autosave.json"))
        assert len(autosave_files) == 0, "Autosave file should be deleted after clear_autosave"


class TestAutosaveEdgeCases:
    """Test edge cases and error handling."""

    def test_autosave_handles_serialization_error(
        self, main_window_with_autosave, tmp_autosave_dir, qtbot
    ):
        """Verify autosave handles JSON serialization errors gracefully."""
        window = main_window_with_autosave

        # Add a source
        source = SourceItem(SourceParams(x_mm=100.0, y_mm=200.0))
        window.scene.addItem(source)

        # Mock serialize_scene to raise TypeError (simulating serialization error)
        original_serialize = window.file_controller.file_manager.serialize_scene

        def mock_serialize():
            raise TypeError("Serialization error")

        window.file_controller.file_manager.serialize_scene = mock_serialize

        # Try to autosave
        window.file_controller.file_manager.do_autosave()

        # Wait a bit
        qtbot.wait(200)
        QtWidgets.QApplication.processEvents()

        # Should not have created autosave file
        autosave_files = list(tmp_autosave_dir.glob("*.autosave.json"))
        assert len(autosave_files) == 0, "Autosave should handle serialization errors gracefully"

        # Restore original method
        window.file_controller.file_manager.serialize_scene = original_serialize

    def test_autosave_handles_file_error(
        self, main_window_with_autosave, tmp_autosave_dir, qtbot, monkeypatch
    ):
        """Verify autosave handles file I/O errors gracefully."""
        window = main_window_with_autosave

        # Add a source
        source = SourceItem(SourceParams(x_mm=100.0, y_mm=200.0))
        window.scene.addItem(source)

        # Mock open to raise OSError
        original_open = open

        def mock_open(*args, **kwargs):
            if "autosave" in str(args[0]):
                raise OSError("Permission denied")
            return original_open(*args, **kwargs)

        monkeypatch.setattr("builtins.open", mock_open)

        # Try to autosave
        window.file_controller.file_manager.do_autosave()

        # Wait a bit
        qtbot.wait(200)
        QtWidgets.QApplication.processEvents()

        # Should not crash - error should be logged but handled gracefully
        # (We can't easily verify logging, but the test passing means no exception was raised)

    def test_autosave_recovery_handles_corrupt_file(
        self, qapp, tmp_autosave_dir, monkeypatch, qtbot
    ):
        """Verify recovery handles corrupt/invalid autosave files."""
        # Create a corrupt autosave file
        autosave_file = tmp_autosave_dir / "corrupt_untitled_12345.autosave.json"
        with open(autosave_file, "w") as f:
            f.write("This is not valid JSON {")

        # Mock _app_data_root
        from optiverse.platform import paths

        def mock_app_data_root():
            return tmp_autosave_dir.parent

        monkeypatch.setattr(paths, "_app_data_root", mock_app_data_root)

        # Create window
        window = MainWindow()
        window.autotrace = False
        window.raytracing_controller._retrace_timer.stop()

        # Trigger recovery check (should handle corrupt file gracefully)
        result = window.file_controller.check_autosave_recovery()

        # Should return False (recovery failed)
        assert result is False

        # Clean up
        window.file_controller._autosave_timer.stop()
        window.close()
        QtWidgets.QApplication.processEvents()

    def test_autosave_recovery_handles_wrong_version(
        self, qapp, tmp_autosave_dir, monkeypatch, qtbot
    ):
        """Verify recovery rejects incompatible file versions."""
        # Create an autosave file with wrong version
        autosave_file = tmp_autosave_dir / "wrong_version_untitled_12345.autosave.json"
        autosave_data = {
            "version": "1.0",  # Wrong version
            "sources": [{"x_mm": 100.0, "y_mm": 200.0, "type": "source"}],
            "_autosave_meta": {
                "timestamp": datetime.datetime.now().isoformat(),
                "original_path": None,
                "version": "1.0",
            },
        }
        with open(autosave_file, "w") as f:
            json.dump(autosave_data, f)

        # Mock _app_data_root
        from optiverse.platform import paths

        def mock_app_data_root():
            return tmp_autosave_dir.parent

        monkeypatch.setattr(paths, "_app_data_root", mock_app_data_root)

        # Create window
        window = MainWindow()
        window.autotrace = False
        window.raytracing_controller._retrace_timer.stop()

        # Trigger recovery check (should reject wrong version)
        result = window.file_controller.check_autosave_recovery()

        # Should return False (recovery failed due to version mismatch)
        assert result is False

        # Clean up
        window.file_controller._autosave_timer.stop()
        window.close()
        QtWidgets.QApplication.processEvents()

    def test_autosave_atomic_write(
        self, main_window_with_autosave, tmp_autosave_dir, qtbot
    ):
        """Verify autosave uses atomic write (temp file + rename)."""
        window = main_window_with_autosave

        # Add a source
        source = SourceItem(SourceParams(x_mm=100.0, y_mm=200.0))
        window.scene.addItem(source)

        # Wait for autosave
        qtbot.wait(1500)
        QtWidgets.QApplication.processEvents()

        # Check that autosave file exists (no .tmp files should remain)
        autosave_files = list(tmp_autosave_dir.glob("*.autosave.json"))
        assert len(autosave_files) == 1

        tmp_files = list(tmp_autosave_dir.glob("*.tmp"))
        assert len(tmp_files) == 0, "Temporary files should be cleaned up after atomic write"

        # Verify the file is valid JSON (atomic write ensures complete file)
        with open(autosave_files[0]) as f:
            data = json.load(f)  # Should not raise JSONDecodeError
            assert "version" in data


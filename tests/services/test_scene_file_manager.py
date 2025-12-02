"""
Tests for SceneFileManager.

These tests verify:
- Scene serialization and deserialization
- Save and load operations
- Autosave functionality
- Modified state tracking
"""

from __future__ import annotations

import json

from PyQt6 import QtWidgets

from optiverse.core.exceptions import AssemblyLoadError, AssemblySaveError
from optiverse.services.log_service import LogService
from optiverse.services.scene_file_manager import SceneFileManager


class TestSceneFileManager:
    """Tests for SceneFileManager class."""

    def test_create_manager(self, qapp, scene):
        """Test creating a SceneFileManager."""
        log_service = LogService()
        parent = QtWidgets.QWidget()

        manager = SceneFileManager(
            scene=scene,
            log_service=log_service,
            get_ray_data=lambda: [],
            on_modified=lambda x: None,
            parent_widget=parent,
        )

        assert manager is not None
        assert manager.scene is scene
        assert manager.is_modified is False

    def test_mark_modified(self, qapp, scene):
        """Test marking scene as modified."""
        log_service = LogService()
        parent = QtWidgets.QWidget()
        modified_states = []

        def on_modified(state):
            modified_states.append(state)

        manager = SceneFileManager(
            scene=scene,
            log_service=log_service,
            get_ray_data=lambda: [],
            on_modified=on_modified,
            parent_widget=parent,
        )

        manager.mark_modified()

        assert manager.is_modified is True
        assert modified_states == [True]

    def test_mark_modified_only_fires_once(self, qapp, scene):
        """Test that mark_modified only fires callback once."""
        log_service = LogService()
        parent = QtWidgets.QWidget()
        modified_states = []

        def on_modified(state):
            modified_states.append(state)

        manager = SceneFileManager(
            scene=scene,
            log_service=log_service,
            get_ray_data=lambda: [],
            on_modified=on_modified,
            parent_widget=parent,
        )

        manager.mark_modified()
        manager.mark_modified()
        manager.mark_modified()

        assert len(modified_states) == 1

    def test_mark_clean(self, qapp, scene):
        """Test marking scene as clean."""
        log_service = LogService()
        parent = QtWidgets.QWidget()
        modified_states = []

        def on_modified(state):
            modified_states.append(state)

        manager = SceneFileManager(
            scene=scene,
            log_service=log_service,
            get_ray_data=lambda: [],
            on_modified=on_modified,
            parent_widget=parent,
        )

        manager.mark_modified()
        manager.mark_clean()

        assert manager.is_modified is False
        assert modified_states == [True, False]

    def test_saved_file_path_property(self, qapp, scene):
        """Test saved_file_path property."""
        log_service = LogService()
        parent = QtWidgets.QWidget()

        manager = SceneFileManager(
            scene=scene,
            log_service=log_service,
            get_ray_data=lambda: [],
            on_modified=lambda x: None,
            parent_widget=parent,
        )

        assert manager.saved_file_path is None

        manager.saved_file_path = "/path/to/file.json"
        assert manager.saved_file_path == "/path/to/file.json"


class TestSceneSerialization:
    """Tests for scene serialization."""

    def test_serialize_empty_scene(self, qapp, scene):
        """Test serializing empty scene."""
        log_service = LogService()
        parent = QtWidgets.QWidget()

        manager = SceneFileManager(
            scene=scene,
            log_service=log_service,
            get_ray_data=lambda: [],
            on_modified=lambda x: None,
            parent_widget=parent,
        )

        data = manager.serialize_scene()

        assert data["version"] == "2.0"
        assert data["items"] == []
        assert data["rulers"] == []
        assert data["texts"] == []

    def test_serialize_scene_with_source(self, qapp, scene):
        """Test serializing scene with source."""
        from optiverse.core.models import SourceParams
        from optiverse.objects import SourceItem

        log_service = LogService()
        parent = QtWidgets.QWidget()

        manager = SceneFileManager(
            scene=scene,
            log_service=log_service,
            get_ray_data=lambda: [],
            on_modified=lambda x: None,
            parent_widget=parent,
        )

        # Add source to scene
        source = SourceItem(SourceParams(x_mm=100.0, y_mm=50.0, n_rays=5))
        scene.addItem(source)

        data = manager.serialize_scene()

        assert len(data["items"]) == 1
        assert data["items"][0]["type"] == "source"


class TestSaveLoad:
    """Tests for save and load operations."""

    def test_save_to_file(self, qapp, scene, tmp_path):
        """Test saving scene to file."""
        log_service = LogService()
        parent = QtWidgets.QWidget()

        manager = SceneFileManager(
            scene=scene,
            log_service=log_service,
            get_ray_data=lambda: [],
            on_modified=lambda x: None,
            parent_widget=parent,
        )

        manager.mark_modified()
        save_path = tmp_path / "test_save.json"

        result = manager.save_to_file(str(save_path))

        assert result is True
        assert save_path.exists()
        assert manager.is_modified is False
        assert manager.saved_file_path == str(save_path)

        # Verify content
        with open(save_path) as f:
            data = json.load(f)
        assert data["version"] == "2.0"

    def test_open_file(self, qapp, scene, tmp_path):
        """Test opening scene file."""
        log_service = LogService()
        parent = QtWidgets.QWidget()

        manager = SceneFileManager(
            scene=scene,
            log_service=log_service,
            get_ray_data=lambda: [],
            on_modified=lambda x: None,
            parent_widget=parent,
        )

        # Create a valid save file
        save_path = tmp_path / "test_open.json"
        data = {
            "version": "2.0",
            "items": [],
            "rulers": [],
            "texts": [],
            "rectangles": [],
            "path_measures": [],
        }
        with open(save_path, "w") as f:
            json.dump(data, f)

        result = manager.open_file(str(save_path))

        assert result is True
        assert manager.saved_file_path == str(save_path)
        assert manager.is_modified is False

    def test_open_invalid_file_raises(self, qapp, scene, tmp_path):
        """Test that opening invalid file raises AssemblyLoadError."""
        import pytest

        log_service = LogService()
        parent = QtWidgets.QWidget()

        manager = SceneFileManager(
            scene=scene,
            log_service=log_service,
            get_ray_data=lambda: [],
            on_modified=lambda x: None,
            parent_widget=parent,
        )

        # Create invalid JSON file
        save_path = tmp_path / "invalid.json"
        save_path.write_text("not valid json{{{")

        with pytest.raises(AssemblyLoadError):
            manager.open_file(str(save_path))

    def test_open_nonexistent_file_raises(self, qapp, scene, tmp_path):
        """Test that opening nonexistent file raises AssemblyLoadError."""
        import pytest

        log_service = LogService()
        parent = QtWidgets.QWidget()

        manager = SceneFileManager(
            scene=scene,
            log_service=log_service,
            get_ray_data=lambda: [],
            on_modified=lambda x: None,
            parent_widget=parent,
        )

        with pytest.raises(AssemblyLoadError):
            manager.open_file(str(tmp_path / "nonexistent.json"))

    def test_save_to_readonly_raises(self, qapp, scene, tmp_path):
        """Test that saving to readonly location raises AssemblySaveError."""
        import os

        import pytest

        log_service = LogService()
        parent = QtWidgets.QWidget()

        manager = SceneFileManager(
            scene=scene,
            log_service=log_service,
            get_ray_data=lambda: [],
            on_modified=lambda x: None,
            parent_widget=parent,
        )

        # Create readonly directory
        readonly_dir = tmp_path / "readonly"
        readonly_dir.mkdir()
        save_path = readonly_dir / "test.json"

        # Make directory readonly
        os.chmod(readonly_dir, 0o444)

        try:
            with pytest.raises(AssemblySaveError):
                manager.save_to_file(str(save_path))
        finally:
            # Restore permissions for cleanup
            os.chmod(readonly_dir, 0o755)


class TestAutosave:
    """Tests for autosave functionality."""

    def test_get_autosave_path_unsaved(self, qapp, scene, tmp_path, monkeypatch):
        """Test getting autosave path for unsaved file."""
        log_service = LogService()
        parent = QtWidgets.QWidget()

        manager = SceneFileManager(
            scene=scene,
            log_service=log_service,
            get_ray_data=lambda: [],
            on_modified=lambda x: None,
            parent_widget=parent,
        )

        # Mock the app data root
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("USERPROFILE", str(tmp_path))

        path = manager.get_autosave_path()

        assert "autosave" in path
        assert path.endswith(".autosave.json")

    def test_do_autosave_when_not_modified(self, qapp, scene, tmp_path, monkeypatch):
        """Test autosave does nothing when not modified."""
        log_service = LogService()
        parent = QtWidgets.QWidget()

        manager = SceneFileManager(
            scene=scene,
            log_service=log_service,
            get_ray_data=lambda: [],
            on_modified=lambda x: None,
            parent_widget=parent,
        )

        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("USERPROFILE", str(tmp_path))

        # Not modified, so autosave should do nothing
        manager.do_autosave()

        # Check no autosave was created
        autosave_dir = tmp_path / "Library" / "Application Support" / "Optiverse" / "autosave"
        if autosave_dir.exists():
            assert len(list(autosave_dir.glob("*.autosave.json"))) == 0

    def test_clear_autosave(self, qapp, scene, tmp_path, monkeypatch):
        """Test clearing autosave file."""
        log_service = LogService()
        parent = QtWidgets.QWidget()

        manager = SceneFileManager(
            scene=scene,
            log_service=log_service,
            get_ray_data=lambda: [],
            on_modified=lambda x: None,
            parent_widget=parent,
        )

        # Set autosave path and create a dummy file
        autosave_path = tmp_path / "test.autosave.json"
        autosave_path.write_text("{}")
        manager._autosave_path = str(autosave_path)

        assert autosave_path.exists()

        manager.clear_autosave()

        assert not autosave_path.exists()
        assert manager._autosave_path is None


class TestLoadFromData:
    """Tests for loading from data dict."""

    def test_load_empty_data(self, qapp, scene):
        """Test loading empty data."""
        log_service = LogService()
        parent = QtWidgets.QWidget()

        manager = SceneFileManager(
            scene=scene,
            log_service=log_service,
            get_ray_data=lambda: [],
            on_modified=lambda x: None,
            parent_widget=parent,
        )

        data = {
            "version": "2.0",
            "items": [],
            "rulers": [],
            "texts": [],
            "rectangles": [],
            "path_measures": [],
        }

        manager.load_from_data(data)

        # Should not have any items (besides grid/background)
        source_items = [it for it in scene.items() if hasattr(it, "params")]
        assert len(source_items) == 0

    def test_load_data_with_source(self, qapp, scene):
        """Test loading data with a source."""
        log_service = LogService()
        parent = QtWidgets.QWidget()

        manager = SceneFileManager(
            scene=scene,
            log_service=log_service,
            get_ray_data=lambda: [],
            on_modified=lambda x: None,
            parent_widget=parent,
        )

        data = {
            "version": "2.0",
            "items": [
                {
                    "type": "source",
                    "x_mm": 100.0,
                    "y_mm": 50.0,
                    "angle_deg": 0.0,
                    "n_rays": 5,
                    "wavelength_nm": 633.0,
                    "spread_deg": 0.0,
                    "size_mm": 10.0,
                    "ray_length_mm": 1000.0,
                    "color_hex": "#FF0000",
                    "z_value": 0.0,
                }
            ],
            "rulers": [],
            "texts": [],
            "rectangles": [],
            "path_measures": [],
        }

        manager.load_from_data(data)

        # Should have a source item
        from optiverse.objects import SourceItem

        sources = [it for it in scene.items() if isinstance(it, SourceItem)]
        assert len(sources) == 1

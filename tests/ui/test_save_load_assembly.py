"""
Comprehensive tests for save/load assembly functionality.

This test suite ensures that all component types and their parameters
are correctly saved to and loaded from JSON files.
"""

from __future__ import annotations

import gc
import json

import pytest
from PyQt6 import QtWidgets

from optiverse.core.models import (
    BeamsplitterParams,
    DichroicParams,
    LensParams,
    MirrorParams,
    SLMParams,
    SourceParams,
    WaveplateParams,
)
from optiverse.objects import ComponentItem, SourceItem
from optiverse.ui.views.main_window import MainWindow
from tests.fixtures.factories import create_component_from_params
from tests.helpers.ui_test_helpers import (
    is_beamsplitter_component,
    is_lens_component,
    is_mirror_component,
)


def is_dichroic_component(item):
    """Check if item is a dichroic component."""
    if not isinstance(item, ComponentItem):
        return False
    if not item.params.interfaces:
        return False
    return any(iface.element_type == "dichroic" for iface in item.params.interfaces)


def is_waveplate_component(item):
    """Check if item is a waveplate component."""
    if not isinstance(item, ComponentItem):
        return False
    if not item.params.interfaces:
        return False
    return any(iface.element_type == "waveplate" for iface in item.params.interfaces)


def is_slm_component(item):
    """Check if item is an SLM component."""
    if not isinstance(item, ComponentItem):
        return False
    if not item.params.interfaces:
        return False
    return any(iface.element_type == "slm" for iface in item.params.interfaces)


@pytest.fixture
def main_window(qapp):
    """Create a MainWindow instance for testing."""
    window = MainWindow()
    # Disable autotrace and stop timers to prevent hangs
    window.autotrace = False
    window.raytracing_controller._retrace_timer.stop()
    window.file_controller._autosave_timer.stop()
    QtWidgets.QApplication.processEvents()
    yield window
    # Clean up
    window.autotrace = False
    window.raytracing_controller._retrace_timer.stop()
    window.file_controller._autosave_timer.stop()
    window.file_controller.mark_clean()
    window.raytracing_controller.clear_rays()
    for item in list(window.scene.items()):
        window.scene.removeItem(item)
    QtWidgets.QApplication.processEvents()
    window.close()
    QtWidgets.QApplication.processEvents()
    gc.collect()
    QtWidgets.QApplication.processEvents()


class TestSaveLoadAssembly:
    """Test suite for save/load assembly functionality."""

    def test_save_load_sources(self, main_window, tmp_path, qtbot):
        """Test saving and loading sources with all parameters."""
        # Create source with all parameters set
        params = SourceParams(
            x_mm=100.0,
            y_mm=200.0,
            angle_deg=45.0,
            size_mm=15.0,
            n_rays=11,
            ray_length_mm=1500.0,
            spread_deg=10.0,
            color_hex="#00FF00",
            wavelength_nm=532.0,
            polarization_type="vertical",
            polarization_angle_deg=90.0,
        )
        source = SourceItem(params)
        main_window.scene.addItem(source)

        # Save assembly
        save_path = tmp_path / "test_source.json"

        # Mock the file dialog
        import unittest.mock as mock

        with mock.patch.object(
            QtWidgets.QFileDialog, "getSaveFileName", return_value=(str(save_path), "")
        ):
            main_window.save_assembly()

        assert save_path.exists()

        # Clear scene
        main_window.scene.clear()
        assert len(main_window.scene.items()) == 0

        # Load assembly
        with mock.patch.object(
            QtWidgets.QFileDialog, "getOpenFileName", return_value=(str(save_path), "")
        ):
            main_window.open_assembly()

        # Verify source was loaded
        sources = [item for item in main_window.scene.items() if isinstance(item, SourceItem)]
        assert len(sources) == 1

        loaded_source = sources[0]
        assert abs(loaded_source.params.x_mm - 100.0) < 0.01
        assert abs(loaded_source.params.y_mm - 200.0) < 0.01
        assert abs(loaded_source.params.angle_deg - 45.0) < 0.01
        assert abs(loaded_source.params.size_mm - 15.0) < 0.01
        assert loaded_source.params.n_rays == 11
        assert abs(loaded_source.params.ray_length_mm - 1500.0) < 0.01
        assert abs(loaded_source.params.spread_deg - 10.0) < 0.01
        assert loaded_source.params.color_hex == "#00FF00"
        assert abs(loaded_source.params.wavelength_nm - 532.0) < 0.01
        assert loaded_source.params.polarization_type == "vertical"
        assert abs(loaded_source.params.polarization_angle_deg - 90.0) < 0.01

    def test_save_load_lenses(self, main_window, tmp_path, qtbot):
        """Test saving and loading lenses with all parameters."""
        params = LensParams(
            x_mm=50.0,
            y_mm=75.0,
            angle_deg=90.0,
            efl_mm=150.0,
            object_height_mm=40.0,
            name="Test Lens",
        )
        lens = create_component_from_params(params)
        main_window.scene.addItem(lens)

        # Save and load
        save_path = tmp_path / "test_lens.json"
        import unittest.mock as mock

        with mock.patch.object(
            QtWidgets.QFileDialog, "getSaveFileName", return_value=(str(save_path), "")
        ):
            main_window.save_assembly()

        main_window.scene.clear()

        with mock.patch.object(
            QtWidgets.QFileDialog, "getOpenFileName", return_value=(str(save_path), "")
        ):
            main_window.open_assembly()

        # Verify lens was loaded
        lenses = [item for item in main_window.scene.items() if is_lens_component(item)]
        assert len(lenses) == 1

        loaded_lens = lenses[0]
        assert abs(loaded_lens.params.x_mm - 50.0) < 0.01
        assert abs(loaded_lens.params.y_mm - 75.0) < 0.01
        assert abs(loaded_lens.params.angle_deg - 90.0) < 0.01
        assert len(loaded_lens.params.interfaces) > 0
        assert abs(loaded_lens.params.interfaces[0].efl_mm - 150.0) < 0.01
        assert abs(loaded_lens.params.object_height_mm - 40.0) < 0.01
        assert loaded_lens.params.name == "Test Lens"

    def test_save_load_mirrors(self, main_window, tmp_path, qtbot):
        """Test saving and loading mirrors with all parameters."""
        params = MirrorParams(
            x_mm=-50.0,
            y_mm=-75.0,
            angle_deg=45.0,
            object_height_mm=50.0,
            name="Test Mirror",
        )
        mirror = create_component_from_params(params)
        main_window.scene.addItem(mirror)

        # Save and load
        save_path = tmp_path / "test_mirror.json"
        import unittest.mock as mock

        with mock.patch.object(
            QtWidgets.QFileDialog, "getSaveFileName", return_value=(str(save_path), "")
        ):
            main_window.save_assembly()

        main_window.scene.clear()

        with mock.patch.object(
            QtWidgets.QFileDialog, "getOpenFileName", return_value=(str(save_path), "")
        ):
            main_window.open_assembly()

        # Verify mirror was loaded
        mirrors = [item for item in main_window.scene.items() if is_mirror_component(item)]
        assert len(mirrors) == 1

        loaded_mirror = mirrors[0]
        assert abs(loaded_mirror.params.x_mm - (-50.0)) < 0.01
        assert abs(loaded_mirror.params.y_mm - (-75.0)) < 0.01
        assert abs(loaded_mirror.params.angle_deg - 45.0) < 0.01
        assert abs(loaded_mirror.params.object_height_mm - 50.0) < 0.01
        assert loaded_mirror.params.name == "Test Mirror"

    def test_save_load_beamsplitters(self, main_window, tmp_path, qtbot):
        """Test saving and loading beamsplitters with PBS parameters."""
        # Test regular beamsplitter
        params = BeamsplitterParams(
            x_mm=0.0,
            y_mm=0.0,
            angle_deg=45.0,
            object_height_mm=30.0,
            split_T=70.0,
            split_R=30.0,
            is_polarizing=False,
            name="Test BS",
        )
        bs = create_component_from_params(params)
        main_window.scene.addItem(bs)

        # Test PBS
        pbs_params = BeamsplitterParams(
            x_mm=100.0,
            y_mm=100.0,
            angle_deg=45.0,
            object_height_mm=50.0,
            split_T=0.0,
            split_R=0.0,
            is_polarizing=True,
            pbs_transmission_axis_deg=30.0,
            name="Test PBS",
        )
        pbs = create_component_from_params(pbs_params)
        main_window.scene.addItem(pbs)

        # Save and load
        save_path = tmp_path / "test_beamsplitters.json"
        import unittest.mock as mock

        with mock.patch.object(
            QtWidgets.QFileDialog, "getSaveFileName", return_value=(str(save_path), "")
        ):
            main_window.save_assembly()

        main_window.scene.clear()

        with mock.patch.object(
            QtWidgets.QFileDialog, "getOpenFileName", return_value=(str(save_path), "")
        ):
            main_window.open_assembly()

        # Verify beamsplitters were loaded
        beamsplitters = [
            item for item in main_window.scene.items() if is_beamsplitter_component(item)
        ]
        assert len(beamsplitters) == 2

    def test_save_load_complete_assembly(self, main_window, tmp_path, qtbot):
        """Test saving and loading a complete assembly with all component types."""
        # Add one of each component type
        source = SourceItem(SourceParams(x_mm=-400.0, y_mm=0.0))
        lens = create_component_from_params(LensParams(x_mm=-200.0, y_mm=0.0))
        mirror = create_component_from_params(MirrorParams(x_mm=0.0, y_mm=100.0))
        bs = create_component_from_params(BeamsplitterParams(x_mm=100.0, y_mm=0.0))
        dichroic = create_component_from_params(DichroicParams(x_mm=200.0, y_mm=100.0))
        waveplate = create_component_from_params(WaveplateParams(x_mm=300.0, y_mm=0.0))
        slm = create_component_from_params(SLMParams(x_mm=400.0, y_mm=0.0))

        for item in [source, lens, mirror, bs, dichroic, waveplate, slm]:
            main_window.scene.addItem(item)

        # Save and load
        save_path = tmp_path / "test_complete.json"
        import unittest.mock as mock

        with mock.patch.object(
            QtWidgets.QFileDialog, "getSaveFileName", return_value=(str(save_path), "")
        ):
            main_window.save_assembly()

        # Verify JSON file structure
        with open(save_path) as f:
            data = json.load(f)

        assert "sources" in data
        assert len(data["sources"]) == 1

        main_window.scene.clear()

        with mock.patch.object(
            QtWidgets.QFileDialog, "getOpenFileName", return_value=(str(save_path), "")
        ):
            main_window.open_assembly()

        # Verify all components were loaded
        items = main_window.scene.items()
        sources = [item for item in items if isinstance(item, SourceItem)]
        lenses = [item for item in items if is_lens_component(item)]
        mirrors = [item for item in items if is_mirror_component(item)]
        beamsplitters = [item for item in items if is_beamsplitter_component(item)]

        assert len(sources) == 1
        assert len(lenses) == 1
        assert len(mirrors) == 1
        assert len(beamsplitters) == 1

    def test_save_cancel_does_nothing(self, main_window, tmp_path, qtbot):
        """Test that canceling save dialog doesn't create a file."""
        source = SourceItem(SourceParams())
        main_window.scene.addItem(source)

        # Mock the file dialog to return empty path (cancel)
        import unittest.mock as mock

        with mock.patch.object(QtWidgets.QFileDialog, "getSaveFileName", return_value=("", "")):
            main_window.save_assembly()

        # No file should be created
        assert not (tmp_path / "anything.json").exists()

    def test_load_cancel_does_nothing(self, main_window, tmp_path, qtbot):
        """Test that canceling load dialog doesn't affect scene."""
        source = SourceItem(SourceParams())
        main_window.scene.addItem(source)
        initial_count = len(main_window.scene.items())

        # Mock the file dialog to return empty path (cancel)
        import unittest.mock as mock

        with mock.patch.object(QtWidgets.QFileDialog, "getOpenFileName", return_value=("", "")):
            main_window.open_assembly()

        # Scene should be unchanged
        assert len(main_window.scene.items()) == initial_count

    def test_backward_compatibility_missing_fields(self, main_window, tmp_path, qtbot):
        """Test that loading old files without new fields works (backward compatibility)."""
        # Create a JSON file without new fields (simulating old format)
        old_format_data = {
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
                    # Missing new fields: wavelength_nm, polarization_type, etc.
                }
            ],
            "lenses": [],
            "mirrors": [],
            "beamsplitters": [
                {
                    "x_mm": 0.0,
                    "y_mm": 0.0,
                    "angle_deg": 45.0,
                    "object_height_mm": 30.0,
                    "split_T": 50.0,
                    "split_R": 50.0,
                    # Missing: is_polarizing, pbs_transmission_axis_deg
                }
            ],
            "dichroics": [],
            "waveplates": [],
            # Missing: slms (old format didn't have this)
            "rulers": [],
            "texts": [],
        }

        save_path = tmp_path / "old_format.json"
        with open(save_path, "w") as f:
            json.dump(old_format_data, f, indent=2)

        # Load the old format file
        import unittest.mock as mock

        with mock.patch.object(
            QtWidgets.QFileDialog, "getOpenFileName", return_value=(str(save_path), "")
        ):
            main_window.open_assembly()

        # Verify components were loaded with default values for missing fields
        sources = [item for item in main_window.scene.items() if isinstance(item, SourceItem)]
        beamsplitters = [
            item for item in main_window.scene.items() if is_beamsplitter_component(item)
        ]

        assert len(sources) == 1
        assert len(beamsplitters) == 1

        # Check that default values are used for missing fields
        source = sources[0]
        assert hasattr(source.params, "wavelength_nm")
        assert hasattr(source.params, "polarization_type")

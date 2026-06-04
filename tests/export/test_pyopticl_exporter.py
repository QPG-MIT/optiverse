"""Tests for the PyOpticL exporter module."""

import json
import runpy
import shutil
import sys
import types
from pathlib import Path

from optiverse.export.pyopticl_exporter import (
    BaseplateOptions,
    ExportItem,
    _compute_baseplate_bounds,
    _interface_to_pyopticl,
    _optiverse_angle_to_pyopticl,
    _sanitize_stem,
    analyse_scene,
    export_scene,
    generate_script,
)

# ---------------------------------------------------------------------------
# Interface mapping
# ---------------------------------------------------------------------------


class TestInterfaceMapping:
    def test_mirror_interface(self):
        result = _interface_to_pyopticl({
            "element_type": "mirror",
            "x1_mm": 0.0, "y1_mm": -15.0,
            "x2_mm": 0.0, "y2_mm": 15.0,
        })
        assert result is not None
        assert "Reflection" in result
        assert "30.0" in result  # diameter = 30mm

    def test_lens_interface(self):
        result = _interface_to_pyopticl({
            "element_type": "lens",
            "x1_mm": 0.0, "y1_mm": -10.0,
            "x2_mm": 0.0, "y2_mm": 10.0,
            "efl_mm": 75.0,
        })
        assert result is not None
        assert "Lens" in result
        assert "75.0" in result

    def test_beam_splitter_interface(self):
        result = _interface_to_pyopticl({
            "element_type": "beam_splitter",
            "x1_mm": 0.0, "y1_mm": -12.0,
            "x2_mm": 0.0, "y2_mm": 12.0,
            "split_R": 30.0,
            "is_polarizing": False,
        })
        assert result is not None
        assert "Reflection" in result
        assert "0.300" in result

    def test_beam_splitter_uses_precomputed_diagonal(self):
        """dim(diag, 'mm') should appear directly, not dim(...) * 1.414."""
        result = _interface_to_pyopticl({
            "element_type": "beam_splitter",
            "x1_mm": 0.0, "y1_mm": -12.0,
            "x2_mm": 0.0, "y2_mm": 12.0,
            "split_R": 50.0,
            "is_polarizing": False,
        })
        assert result is not None
        assert "* 1.414" not in result
        assert 'dim(33.9, "mm")' in result  # 24 * sqrt(2) ≈ 33.9

    def test_dichroic_longpass(self):
        result = _interface_to_pyopticl({
            "element_type": "dichroic",
            "x1_mm": 0.0, "y1_mm": -12.0,
            "x2_mm": 0.0, "y2_mm": 12.0,
            "cutoff_wavelength_nm": 550.0,
            "pass_type": "longpass",
        })
        assert result is not None
        assert "550" in result
        assert "None" in result

    def test_waveplate_interface(self):
        result = _interface_to_pyopticl({
            "element_type": "polarizing_interface",
            "x1_mm": 0.0, "y1_mm": -10.0,
            "x2_mm": 0.0, "y2_mm": 10.0,
            "polarizer_subtype": "waveplate",
            "phase_shift_deg": 90.0,
            "fast_axis_deg": 45.0,
        })
        assert result is not None
        assert "Waveplate" in result
        assert "0.2500" in result  # 90/360

    def test_beam_block_interface(self):
        result = _interface_to_pyopticl({
            "element_type": "beam_block",
            "x1_mm": 0.0, "y1_mm": -5.0,
            "x2_mm": 0.0, "y2_mm": 5.0,
        })
        assert result is not None
        assert "Stop" in result
        assert "10.0" in result  # diameter = 10mm

    def test_unknown_type_returns_none(self):
        assert _interface_to_pyopticl({"element_type": "unknown"}) is None

    def test_empty_type_returns_none(self):
        assert _interface_to_pyopticl({}) is None


# ---------------------------------------------------------------------------
# Coordinate transforms
# ---------------------------------------------------------------------------


class TestCoordinateTransforms:
    def test_angle_conversion_zero(self):
        assert _optiverse_angle_to_pyopticl(0.0) == 0.0

    def test_angle_conversion_45(self):
        assert _optiverse_angle_to_pyopticl(45.0) == -45.0

    def test_angle_conversion_negative(self):
        assert _optiverse_angle_to_pyopticl(-30.0) == 30.0

    def test_baseplate_bounds_empty(self):
        x, y, w, h = _compute_baseplate_bounds([], 3.175)
        assert w > 0
        assert h > 0

    def test_baseplate_bounds_single_item(self):
        items = [ExportItem(
            label="M", x_mm=50, y_mm=50, angle_deg=0,
            step_file_path=None, step_filename=None, interfaces=[],
        )]
        x_off, y_off, w, h = _compute_baseplate_bounds(items, 3.175)
        # Must be >= 1 inch
        assert w >= 25.4
        assert h >= 25.4

    def test_baseplate_bounds_multiple_items(self):
        items = [
            ExportItem(label="A", x_mm=0, y_mm=0, angle_deg=0,
                       step_file_path=None, step_filename=None, interfaces=[]),
            ExportItem(label="B", x_mm=200, y_mm=100, angle_deg=0,
                       step_file_path=None, step_filename=None, interfaces=[]),
        ]
        _, _, w, h = _compute_baseplate_bounds(items, 3.175)
        assert w >= 200
        assert h >= 100


# ---------------------------------------------------------------------------
# Scene analysis
# ---------------------------------------------------------------------------


class TestAnalyseScene:
    def test_empty_scene(self):
        items, warnings = analyse_scene({"items": []})
        assert items == []
        assert warnings == []

    def test_source_extraction(self):
        scene = {"items": [{
            "_type": "source",
            "x_mm": 10.0, "y_mm": 20.0, "angle_deg": 0.0,
            "wavelength_nm": 780.0,
        }]}
        items, warnings = analyse_scene(scene)
        assert len(items) == 1
        assert items[0].is_source
        assert items[0].wavelength_nm == 780.0

    def test_component_with_step(self):
        scene = {"items": [{
            "_type": "component",
            "name": "Mirror Mount",
            "x_mm": 50.0, "y_mm": 30.0, "angle_deg": 45.0,
            "step_file_path": "/path/to/mount.step",
            "interfaces": [{"element_type": "mirror", "x1_mm": 0, "y1_mm": -10,
                            "x2_mm": 0, "y2_mm": 10}],
        }]}
        items, warnings = analyse_scene(scene)
        assert len(items) == 1
        assert not items[0].is_source
        assert items[0].step_file_path == "/path/to/mount.step"
        assert warnings == []

    def test_component_without_step_warns(self):
        scene = {"items": [{
            "_type": "component",
            "name": "Bare Mirror",
            "x_mm": 50.0, "y_mm": 30.0, "angle_deg": 45.0,
        }]}
        items, warnings = analyse_scene(scene)
        assert len(items) == 1
        assert warnings == ["Bare Mirror"]


# ---------------------------------------------------------------------------
# Script generation
# ---------------------------------------------------------------------------


class TestGenerateScript:
    def test_script_has_imports(self):
        items = [ExportItem(
            label="Source (633 nm)", x_mm=0, y_mm=0, angle_deg=0,
            step_file_path=None, step_filename=None, interfaces=[],
            is_source=True, wavelength_nm=633.0,
        )]
        script = generate_script(items, BaseplateOptions())
        assert "from PyOpticL" in script
        assert "import_model" in script
        assert "BeamPath" in script
        assert "fix_relative_imports" in script
        assert "Stop" in script

    def test_script_has_layout_function(self):
        items = [ExportItem(
            label="Source", x_mm=0, y_mm=0, angle_deg=0,
            step_file_path=None, step_filename=None, interfaces=[],
            is_source=True,
        )]
        script = generate_script(items, BaseplateOptions())
        assert "def exported_layout" in script
        assert "if __name__" in script

    def test_component_with_step_uses_mesh_class_var(self):
        """STEP-imported components must use `mesh = import_model(...)` class var."""
        items = [
            ExportItem(
                label="Source", x_mm=0, y_mm=0, angle_deg=0,
                step_file_path=None, step_filename=None, interfaces=[],
                is_source=True,
            ),
            ExportItem(
                label="Mirror 1", x_mm=80, y_mm=0, angle_deg=45,
                step_file_path="/models/mirror.step",
                step_filename="mirror.step",
                interfaces=[{"element_type": "mirror",
                             "x1_mm": 0, "y1_mm": -15,
                             "x2_mm": 0, "y2_mm": 15}],
            ),
        ]
        script = generate_script(items, BaseplateOptions(label="Test Layout"))
        assert "class component_1_def" in script
        assert 'mesh = import_model("mirror"' in script
        assert "def shape(self):" not in script or "no 3D model" in script
        assert "Reflection" in script
        assert "Test Layout" in script

    def test_component_without_step_but_with_interfaces_generates_class(self):
        """Components without STEP but with interfaces get primitive geometry."""
        items = [
            ExportItem(
                label="Source", x_mm=0, y_mm=0, angle_deg=0,
                step_file_path=None, step_filename=None, interfaces=[],
                is_source=True,
            ),
            ExportItem(
                label="Thin Lens", x_mm=50, y_mm=0, angle_deg=0,
                step_file_path=None, step_filename=None,
                interfaces=[{"element_type": "lens",
                             "x1_mm": 0, "y1_mm": -12.7,
                             "x2_mm": 0, "y2_mm": 12.7,
                             "efl_mm": 100.0}],
            ),
        ]
        script = generate_script(items, BaseplateOptions())
        assert "class component_1_def" in script
        assert "no 3D model" in script
        assert "cylinder_shape" in script
        assert "Lens" in script
        assert "SKIPPED" not in script

    def test_missing_step_and_no_interfaces_shows_skip(self):
        items = [ExportItem(
            label="No Step", x_mm=10, y_mm=10, angle_deg=0,
            step_file_path=None, step_filename=None, interfaces=[],
        )]
        script = generate_script(items, BaseplateOptions())
        assert "SKIPPED" in script

    def test_metric_option_generates_settings_call(self):
        items = [ExportItem(
            label="Source", x_mm=0, y_mm=0, angle_deg=0,
            step_file_path=None, step_filename=None, interfaces=[],
            is_source=True,
        )]
        script = generate_script(items, BaseplateOptions(metric=True))
        assert "set_measurement_system" in script
        assert '"metric"' in script

    def test_imperial_option_omits_settings_call(self):
        items = [ExportItem(
            label="Source", x_mm=0, y_mm=0, angle_deg=0,
            step_file_path=None, step_filename=None, interfaces=[],
            is_source=True,
        )]
        script = generate_script(items, BaseplateOptions(metric=False))
        assert "set_measurement_system" not in script

    def test_step_orientation_note_present(self):
        items = [
            ExportItem(
                label="Mirror", x_mm=0, y_mm=0, angle_deg=0,
                step_file_path="/m.step", step_filename="m.step",
                interfaces=[],
            ),
        ]
        script = generate_script(items, BaseplateOptions())
        assert "Get Orientation" in script

    def test_script_is_valid_python(self):
        """The generated script should be syntactically valid Python."""
        items = [
            ExportItem(
                label="Source", x_mm=0, y_mm=0, angle_deg=0,
                step_file_path=None, step_filename=None, interfaces=[],
                is_source=True, wavelength_nm=633.0,
            ),
            ExportItem(
                label="Mirror", x_mm=80, y_mm=50, angle_deg=45,
                step_file_path="/m.step", step_filename="m.step",
                interfaces=[{"element_type": "mirror",
                             "x1_mm": 0, "y1_mm": -10,
                             "x2_mm": 0, "y2_mm": 10}],
            ),
        ]
        script = generate_script(items, BaseplateOptions())
        compile(script, "<pyopticl_export>", "exec")

    def test_script_with_no_step_interfaces_is_valid_python(self):
        """Script with primitive-geometry components must also be valid Python."""
        items = [
            ExportItem(
                label="Source", x_mm=0, y_mm=0, angle_deg=0,
                step_file_path=None, step_filename=None, interfaces=[],
                is_source=True, wavelength_nm=633.0,
            ),
            ExportItem(
                label="Lens", x_mm=50, y_mm=0, angle_deg=0,
                step_file_path=None, step_filename=None,
                interfaces=[{"element_type": "lens",
                             "x1_mm": 0, "y1_mm": -10,
                             "x2_mm": 0, "y2_mm": 10,
                             "efl_mm": 100.0}],
            ),
        ]
        script = generate_script(items, BaseplateOptions())
        compile(script, "<pyopticl_export>", "exec")

    def test_script_with_metric_is_valid_python(self):
        items = [ExportItem(
            label="Source", x_mm=0, y_mm=0, angle_deg=0,
            step_file_path=None, step_filename=None, interfaces=[],
            is_source=True,
        )]
        script = generate_script(items, BaseplateOptions(metric=True))
        compile(script, "<pyopticl_export>", "exec")


# ---------------------------------------------------------------------------
# ComponentRecord step_file_path round-trip
# ---------------------------------------------------------------------------


class TestComponentRecordStepPath:
    def test_step_field_defaults_empty(self):
        from optiverse.core.models import ComponentRecord
        rec = ComponentRecord(name="Test")
        assert rec.step_file_path == ""

    def test_step_field_serialization(self):
        from optiverse.core.models import (
            ComponentRecord,
            serialize_component,
        )

        rec = ComponentRecord(
            name="Mirror Mount",
            step_file_path="/tmp/mount.step",
        )
        data = serialize_component(rec)
        assert data.get("step_file_path") is not None

    def test_step_field_deserialization(self):
        from optiverse.core.models import deserialize_component

        data = {
            "name": "Mount",
            "step_file_path": "/tmp/mount.step",
        }
        rec = deserialize_component(data)
        assert rec is not None
        assert rec.step_file_path != ""


# ---------------------------------------------------------------------------
# Folder-based export (matches PyOpticL.utils.import_model layout)
# ---------------------------------------------------------------------------


class TestExportSceneFolderLayout:
    def _scene_with_one_step(self, step_src: str) -> dict:
        return {
            "items": [
                {
                    "_type": "source",
                    "x_mm": 0.0, "y_mm": 0.0, "angle_deg": 0.0,
                    "wavelength_nm": 633.0,
                },
                {
                    "_type": "component",
                    "name": "Mirror Mount",
                    "x_mm": 50.0, "y_mm": 30.0, "angle_deg": 0.0,
                    "step_file_path": step_src,
                    "interfaces": [{"element_type": "mirror",
                                    "x1_mm": 0, "y1_mm": -10,
                                    "x2_mm": 0, "y2_mm": 10}],
                },
            ]
        }

    def test_writes_script_and_per_model_step_and_json(self, tmp_path):
        step_src = tmp_path / "Thorlabs KM05.STEP"
        step_src.write_bytes(b"ISO-10303-21 fake step content")

        export_dir = tmp_path / "my_layout"
        success, _ = export_scene(
            self._scene_with_one_step(str(step_src)),
            str(export_dir),
            BaseplateOptions(),
        )
        assert success is True

        assert (export_dir / "my_layout.py").is_file()

        stem = "Thorlabs_KM05"
        model_dir = export_dir / "models" / stem
        assert model_dir.is_dir()
        assert (model_dir / f"{stem}.step").is_file()
        assert (model_dir / f"{stem}.json").is_file()

        info = json.loads((model_dir / f"{stem}.json").read_text())
        assert info["translation"] == [0.0, 0.0, 0.0]
        assert info["rotation"] == [0.0, 0.0, 0.0]
        assert "_note" in info

        script = (export_dir / "my_layout.py").read_text()
        assert f'import_model("{stem}"' in script
        assert f'mesh = import_model("{stem}"' in script

    def test_exported_script_runs_after_folder_is_moved(self, tmp_path, monkeypatch):
        step_src = tmp_path / "Thorlabs KM05.STEP"
        step_src.write_bytes(b"ISO-10303-21 fake step content")

        export_dir = tmp_path / "my_layout"
        success, _ = export_scene(
            self._scene_with_one_step(str(step_src)),
            str(export_dir),
            BaseplateOptions(),
        )
        assert success is True

        moved_dir = tmp_path / "relocated" / "my_layout"
        shutil.copytree(export_dir, moved_dir)

        script_path = moved_dir / "my_layout.py"
        script_text = script_path.read_text(encoding="utf-8")
        assert str(step_src) not in script_text
        assert str(export_dir) not in script_text
        assert 'import_model("Thorlabs_KM05", directory="models")' in script_text

        import_calls: list[tuple[str, str]] = []
        _install_pyopticl_stubs(monkeypatch, import_calls)

        monkeypatch.chdir(moved_dir)
        runpy.run_path(str(script_path), run_name="__main__")

        assert import_calls == [("Thorlabs_KM05", "models")]

    def test_missing_step_file_does_not_fail_export(self, tmp_path):
        scene = self._scene_with_one_step("/nonexistent/file.step")
        export_dir = tmp_path / "out"
        success, _ = export_scene(scene, str(export_dir), BaseplateOptions())
        assert success is True
        assert (export_dir / "out.py").is_file()
        assert not (export_dir / "models").exists()

    def test_sanitize_stem_handles_dodgy_names(self):
        assert _sanitize_stem("foo bar/baz") == "foo_bar_baz"
        assert _sanitize_stem("") == "part"
        assert _sanitize_stem("OK-name_1.0") == "OK-name_1.0"


def _install_pyopticl_stubs(monkeypatch, import_calls: list[tuple[str, str]]) -> None:
    class _Component:
        def __init__(self, *args, **kwargs):
            pass

        def add(self, item, *args, **kwargs):
            return item

        def recompute(self):
            pass

    class _BeamPath:
        def __init__(self, *args, **kwargs):
            pass

    class _Interface:
        def __init__(self, *args, **kwargs):
            pass

    def _dim(value, unit):
        return (value, unit)

    def _import_model(name, directory="models"):
        model_dir = Path.cwd() / directory / name
        assert model_dir.is_dir()
        assert (model_dir / f"{name}.step").is_file()
        assert (model_dir / f"{name}.json").is_file()
        import_calls.append((name, directory))
        return object()

    def _fix_relative_imports():
        pass

    pyopticl = types.ModuleType("PyOpticL")
    beam_path = types.ModuleType("PyOpticL.beam_path")
    beam_path.BeamPath = _BeamPath
    beam_path.Lens = _Interface
    beam_path.Reflection = _Interface
    beam_path.Stop = _Interface
    beam_path.Waveplate = _Interface

    layout = types.ModuleType("PyOpticL.layout")
    layout.Component = _Component

    library = types.ModuleType("PyOpticL.library")
    library.baseplate = lambda *args, **kwargs: object()

    utils = types.ModuleType("PyOpticL.utils")
    utils.Dimension = _dim
    utils.import_model = _import_model
    utils.fix_relative_imports = _fix_relative_imports
    utils.cylinder_shape = lambda *args, **kwargs: object()
    utils.box_shape = lambda *args, **kwargs: object()

    monkeypatch.setitem(sys.modules, "PyOpticL", pyopticl)
    monkeypatch.setitem(sys.modules, "PyOpticL.beam_path", beam_path)
    monkeypatch.setitem(sys.modules, "PyOpticL.layout", layout)
    monkeypatch.setitem(sys.modules, "PyOpticL.library", library)
    monkeypatch.setitem(sys.modules, "PyOpticL.utils", utils)

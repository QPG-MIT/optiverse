"""Tests for the STEP renderer module (parts that don't require OCP)."""

import numpy as np

from optiverse.cad.step_renderer import (
    PRESET_VIEWS,
    is_cad_available,
    is_viewer_available,
    mesh_bounding_box,
    missing_dependency_message,
)


class TestDependencyProbing:
    def test_is_cad_available_returns_bool(self):
        result = is_cad_available()
        assert isinstance(result, bool)

    def test_is_viewer_available_returns_bool(self):
        result = is_viewer_available()
        assert isinstance(result, bool)

    def test_missing_dependency_message_type(self):
        msg = missing_dependency_message()
        assert isinstance(msg, str)


class TestMeshBoundingBox:
    def test_simple_cube(self):
        verts = np.array([
            [0, 0, 0],
            [1, 0, 0],
            [0, 1, 0],
            [0, 0, 1],
            [1, 1, 1],
        ], dtype=np.float64)
        bb_min, bb_max = mesh_bounding_box(verts)
        np.testing.assert_array_equal(bb_min, [0, 0, 0])
        np.testing.assert_array_equal(bb_max, [1, 1, 1])

    def test_centred_mesh(self):
        verts = np.array([
            [-5, -5, -5],
            [5, 5, 5],
        ], dtype=np.float64)
        bb_min, bb_max = mesh_bounding_box(verts)
        np.testing.assert_array_equal(bb_min, [-5, -5, -5])
        np.testing.assert_array_equal(bb_max, [5, 5, 5])


class TestPresetViews:
    def test_all_presets_are_3x3(self):
        for name, mat in PRESET_VIEWS.items():
            assert mat.shape == (3, 3), f"{name} has wrong shape"

    def test_all_presets_are_orthogonal(self):
        for name, mat in PRESET_VIEWS.items():
            product = mat @ mat.T
            np.testing.assert_allclose(
                product, np.eye(3), atol=1e-10,
                err_msg=f"{name} is not orthogonal",
            )

    def test_all_presets_have_det_plus_or_minus_one(self):
        for name, mat in PRESET_VIEWS.items():
            det = np.linalg.det(mat)
            assert abs(abs(det) - 1.0) < 1e-10, f"{name} det = {det}"

    def test_preset_dict_has_six_views(self):
        assert len(PRESET_VIEWS) == 6
        assert set(PRESET_VIEWS.keys()) == {"Front", "Back", "Top", "Bottom", "Left", "Right"}

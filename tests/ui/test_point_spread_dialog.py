import numpy as np
import pytest

from optiverse.core.models import Polarization
from optiverse.raytracing import RayPath


def _ray_path(y_mm: float) -> RayPath:
    return RayPath(
        points=[np.array([0.0, y_mm]), np.array([10.0, y_mm])],
        rgba=(255, 0, 0, 255),
        polarization=Polarization.horizontal(),
        wavelength_nm=633.0,
        intensities=[1.0, 1.0],
    )


def test_raytracing_controller_computes_geometric_psf(qapp, scene):
    from unittest.mock import MagicMock

    from optiverse.ui.controllers.raytracing_controller import RaytracingController

    controller = RaytracingController(
        scene=scene,
        ray_renderer=MagicMock(),
        log_service=MagicMock(),
    )
    controller._ray_data = [_ray_path(-1.0), _ray_path(1.0)]

    psf = controller.compute_geometric_psf(plane_x_mm=5.0, bin_count=3, extent_mm=2.0)

    assert psf.sample_count == 2
    assert psf.centroid_mm == pytest.approx(0.0)


def test_point_spread_dialog_computes_and_displays_result(qtbot, qapp, scene):
    from unittest.mock import MagicMock

    from optiverse.ui.controllers.raytracing_controller import RaytracingController
    from optiverse.ui.views.point_spread_dialog import PointSpreadFunctionDialog

    controller = RaytracingController(
        scene=scene,
        ray_renderer=MagicMock(),
        log_service=MagicMock(),
    )
    controller._ray_data = [_ray_path(-1.0), _ray_path(1.0)]

    dialog = PointSpreadFunctionDialog(controller)
    qtbot.addWidget(dialog)

    assert dialog.last_result is not None
    assert dialog.last_result.sample_count == 2
    assert "Samples: 2" in dialog._result.toPlainText()
    dialog.close()


def test_main_window_has_point_spread_action(qtbot, monkeypatch):
    from PyQt6 import QtWidgets

    from optiverse.ui.views.main_window import MainWindow

    monkeypatch.setattr(QtWidgets.QMessageBox, "information", lambda *a, **kw: None)

    window = MainWindow()
    qtbot.addWidget(window)
    window.autotrace = False
    window.raytracing_controller._retrace_timer.stop()
    window.file_controller._autosave_timer.stop()

    assert window.act_point_spread.text() == "Point Spread Function..."
    window.show_point_spread_function_dialog()

    window.close()

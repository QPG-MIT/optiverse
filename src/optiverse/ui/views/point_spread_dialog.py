"""
Point-spread-function dialog.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6 import QtCore, QtWidgets

if TYPE_CHECKING:
    from ...raytracing import PointSpreadFunction
    from ..controllers.raytracing_controller import RaytracingController


class PointSpreadFunctionDialog(QtWidgets.QDialog):
    """Dialog for computing a geometric PSF from current traced rays."""

    def __init__(
        self,
        raytracing_controller: RaytracingController,
        parent: QtWidgets.QWidget | None = None,
    ):
        super().__init__(parent)
        self._raytracing_controller = raytracing_controller
        self._last_result: PointSpreadFunction | None = None

        self.setWindowTitle("Point Spread Function")
        self.setMinimumWidth(420)

        layout = QtWidgets.QVBoxLayout(self)

        form = QtWidgets.QFormLayout()
        form.setFieldGrowthPolicy(QtWidgets.QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        self._plane_x = QtWidgets.QDoubleSpinBox()
        self._plane_x.setRange(-1_000_000.0, 1_000_000.0)
        self._plane_x.setDecimals(3)
        default_x, default_y = _default_plane_origin(raytracing_controller)
        self._plane_x.setValue(default_x)
        self._plane_x.setSuffix(" mm")
        form.addRow("Plane X", self._plane_x)

        self._plane_y = QtWidgets.QDoubleSpinBox()
        self._plane_y.setRange(-1_000_000.0, 1_000_000.0)
        self._plane_y.setDecimals(3)
        self._plane_y.setValue(default_y)
        self._plane_y.setSuffix(" mm")
        form.addRow("Plane Y", self._plane_y)

        self._normal_angle = QtWidgets.QDoubleSpinBox()
        self._normal_angle.setRange(-360.0, 360.0)
        self._normal_angle.setDecimals(3)
        self._normal_angle.setValue(0.0)
        self._normal_angle.setSuffix(" deg")
        form.addRow("Normal angle", self._normal_angle)

        self._extent = QtWidgets.QDoubleSpinBox()
        self._extent.setRange(0.0, 1_000_000.0)
        self._extent.setDecimals(3)
        self._extent.setSpecialValueText("Auto")
        self._extent.setValue(0.0)
        self._extent.setSuffix(" mm")
        form.addRow("Half-width", self._extent)

        self._bin_count = QtWidgets.QSpinBox()
        self._bin_count.setRange(1, 10_000)
        self._bin_count.setValue(101)
        form.addRow("Bins", self._bin_count)

        layout.addLayout(form)

        self._result = QtWidgets.QTextEdit()
        self._result.setReadOnly(True)
        self._result.setMinimumHeight(160)
        layout.addWidget(self._result)

        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Close)
        compute_button = buttons.addButton(
            "Compute", QtWidgets.QDialogButtonBox.ButtonRole.ActionRole
        )
        if compute_button is None:
            raise RuntimeError("Could not create point-spread-function compute button")
        self._compute_button = compute_button
        self._compute_button.clicked.connect(self.compute)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.compute()

    @property
    def last_result(self) -> PointSpreadFunction | None:
        """Return the most recent computed PSF."""
        return self._last_result

    def compute(self) -> None:
        """Compute and display the PSF."""
        extent = self._extent.value() if self._extent.value() > 0 else None
        self._last_result = self._raytracing_controller.compute_geometric_psf(
            plane_x_mm=self._plane_x.value(),
            plane_y_mm=self._plane_y.value(),
            normal_angle_deg=self._normal_angle.value(),
            bin_count=self._bin_count.value(),
            extent_mm=extent,
        )
        self._result.setPlainText(self._format_result(self._last_result))

    @staticmethod
    def _format_result(psf: PointSpreadFunction) -> str:
        if psf.sample_count == 0:
            return "No ray intersections found at the selected image plane."

        centroid = _format_optional_mm(psf.centroid_mm)
        rms = _format_optional_mm(psf.rms_radius_mm)
        fwhm = _format_optional_mm(psf.fwhm_mm)
        histogram_note = ""
        if psf.histogram_weight < psf.total_weight:
            missing = psf.total_weight - psf.histogram_weight
            histogram_note = f"\nOut-of-range weight: {missing:.4g}"

        return (
            f"Samples: {psf.sample_count}\n"
            f"Total weight: {psf.total_weight:.4g}\n"
            f"Centroid: {centroid}\n"
            f"RMS radius: {rms}\n"
            f"FWHM: {fwhm}"
            f"{histogram_note}"
        )

    def keyPressEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        if event.key() in (QtCore.Qt.Key.Key_Return, QtCore.Qt.Key.Key_Enter):
            self.compute()
            return
        super().keyPressEvent(event)


def _format_optional_mm(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.6g} mm"


def _default_plane_origin(raytracing_controller: RaytracingController) -> tuple[float, float]:
    endpoints = [path.points[-1] for path in raytracing_controller.ray_data if path.points]
    if not endpoints:
        return 100.0, 0.0

    x_mm = max(float(point[0]) for point in endpoints)
    y_mm = sum(float(point[1]) for point in endpoints) / len(endpoints)
    return x_mm, y_mm

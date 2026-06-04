"""
Dialogs for PyOpticL export: pre-flight warnings and baseplate configuration.
"""

from __future__ import annotations

from PyQt6 import QtWidgets

from .pyopticl_exporter import BaseplateOptions


class MissingStepWarningDialog(QtWidgets.QDialog):
    """Warn the user about components that lack STEP files."""

    def __init__(self, missing_names: list[str], parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Missing STEP Files")
        self.resize(420, 300)

        layout = QtWidgets.QVBoxLayout(self)

        label = QtWidgets.QLabel(
            f"<b>{len(missing_names)} component(s)</b> do not have STEP files "
            "attached and will be <b>skipped</b> in the 3-D model."
        )
        label.setWordWrap(True)
        layout.addWidget(label)

        list_widget = QtWidgets.QListWidget()
        for name in missing_names:
            list_widget.addItem(name)
        layout.addWidget(list_widget)

        hint = QtWidgets.QLabel(
            "To fix: open each component in the Component Editor and use "
            "<i>File &gt; Import STEP\u2026</i> to attach a 3-D model."
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)

        btn_box = QtWidgets.QDialogButtonBox()
        btn_box.addButton("Export Anyway", QtWidgets.QDialogButtonBox.ButtonRole.AcceptRole)
        btn_box.addButton(QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)


class BaseplateOptionsDialog(QtWidgets.QDialog):
    """Configure baseplate dimensions and export settings."""

    def __init__(
        self,
        defaults: BaseplateOptions,
        parent: QtWidgets.QWidget | None = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("PyOpticL Export – Baseplate Options")
        self.resize(380, 280)

        form = QtWidgets.QFormLayout(self)

        self._label_edit = QtWidgets.QLineEdit(defaults.label)
        form.addRow("Layout name:", self._label_edit)

        form.addRow(self._separator())

        self._width = self._mm_spin(defaults.width_mm)
        form.addRow("Width:", self._width)

        self._height = self._mm_spin(defaults.height_mm)
        form.addRow("Height:", self._height)

        self._thickness = self._mm_spin(defaults.thickness_mm)
        form.addRow("Thickness:", self._thickness)

        self._optical_height = self._mm_spin(defaults.optical_height_mm)
        form.addRow("Optical height:", self._optical_height)

        self._gap = self._mm_spin(defaults.gap_mm)
        form.addRow("Gap:", self._gap)

        form.addRow(self._separator())

        self._metric = QtWidgets.QCheckBox("Metric (25 mm grid, M6 bolts)")
        self._metric.setChecked(defaults.metric)
        form.addRow("Grid:", self._metric)

        btn_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        ok_btn = btn_box.button(QtWidgets.QDialogButtonBox.StandardButton.Ok)
        if ok_btn:
            ok_btn.setText("Export")
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        form.addRow(btn_box)

    @staticmethod
    def _mm_spin(value: float) -> QtWidgets.QDoubleSpinBox:
        spin = QtWidgets.QDoubleSpinBox()
        spin.setRange(0.1, 1e6)
        spin.setDecimals(2)
        spin.setSuffix(" mm")
        spin.setValue(value)
        return spin

    @staticmethod
    def _separator() -> QtWidgets.QFrame:
        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        return line

    def get_options(self) -> BaseplateOptions:
        return BaseplateOptions(
            width_mm=self._width.value(),
            height_mm=self._height.value(),
            thickness_mm=self._thickness.value(),
            optical_height_mm=self._optical_height.value(),
            gap_mm=self._gap.value(),
            metric=self._metric.isChecked(),
            label=self._label_edit.text().strip() or "Optiverse Export",
        )

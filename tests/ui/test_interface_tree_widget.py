"""Tests for the component-editor interface tree widget."""

from __future__ import annotations

import pytest

try:
    from PyQt6 import QtCore, QtWidgets

    HAVE_PYQT6 = True
except ImportError:
    HAVE_PYQT6 = False


pytestmark = pytest.mark.skipif(not HAVE_PYQT6, reason="PyQt6 not available")


def test_double_click_does_not_trigger_tree_scroll(qtbot, monkeypatch):
    from optiverse.ui.widgets.interface_widgets import InterfaceTreeWidget

    tree = InterfaceTreeWidget()
    qtbot.addWidget(tree)
    tree.addTopLevelItem(QtWidgets.QTreeWidgetItem(["Interface"]))
    tree.resize(240, 120)
    tree.show()

    scroll_calls = []
    monkeypatch.setattr(tree, "scrollTo", lambda *args, **kwargs: scroll_calls.append(args))

    qtbot.mouseDClick(
        tree.viewport(),
        QtCore.Qt.MouseButton.LeftButton,
        pos=tree.visualItemRect(tree.topLevelItem(0)).center(),
    )

    assert scroll_calls == []

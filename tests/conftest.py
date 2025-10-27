import os
import sys
import pytest


@pytest.fixture(scope="session", autouse=True)
def _ensure_src_on_path():
    root = os.path.dirname(os.path.dirname(__file__))
    src = os.path.join(root, "src")
    if os.path.isdir(src) and src not in sys.path:
        sys.path.insert(0, src)
    yield


@pytest.fixture(scope="session")
def qapp():
    """Create a QApplication instance for tests."""
    # Import here to avoid issues if PyQt6 is not installed
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def qtbot():
    """Provides a QtBot object for tests."""
    from pytestqt.qtbot import QtBot
    from PyQt6.QtWidgets import QApplication
    bot = QtBot(QApplication.instance())
    yield bot



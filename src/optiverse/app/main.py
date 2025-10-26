from __future__ import annotations

import sys
from PyQt6 import QtCore, QtWidgets
from ..ui.views.main_window import MainWindow


def main() -> int:
    # Minimal app that opens the main window (Qt6 enables high DPI by default)
    app = QtWidgets.QApplication(sys.argv)
    w = MainWindow()
    w.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())



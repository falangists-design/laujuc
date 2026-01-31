"""Application entrypoint for laujuc."""

from __future__ import annotations

import logging
import sys

from PySide6 import QtWidgets

from laujuc.gui_layer import LaujucWindow, apply_theme


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    app = QtWidgets.QApplication(sys.argv)
    apply_theme(app)
    window = LaujucWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

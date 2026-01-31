"""Application entrypoint for laujuc."""

from __future__ import annotations

import logging
import sys

from PySide6 import QtCore, QtGui, QtWidgets

from laujuc.gui_layer import LaujucWindow, LauncherWindow, apply_theme
from laujuc.settings_manager import SettingsManager


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    app = QtWidgets.QApplication(sys.argv)
    manager = SettingsManager()
    settings = manager.load()
    apply_theme(app, settings.theme)

    window = LaujucWindow()

    splash_pixmap = QtGui.QPixmap(360, 180)
    splash_pixmap.fill(QtGui.QColor("#0A0A0C"))
    painter = QtGui.QPainter(splash_pixmap)
    painter.setPen(QtGui.QColor("#0080FF"))
    painter.setFont(QtGui.QFont("Segoe UI", 24, QtGui.QFont.Bold))
    painter.drawText(splash_pixmap.rect(), QtCore.Qt.AlignCenter, "laujuc")
    painter.end()
    splash = QtWidgets.QSplashScreen(splash_pixmap)
    splash.showMessage(
        "laujuc",
        QtCore.Qt.AlignCenter | QtCore.Qt.AlignBottom,
        QtGui.QColor("#0080FF"),
    )
    splash.show()

    if settings.auth_enabled and not manager.is_activation_valid(settings):
        launcher = LauncherWindow(settings, manager)

        def show_launcher() -> None:
            launcher.show()
            splash.finish(launcher)

        def show_main() -> None:
            launcher.close()
            window.show()

        launcher.authenticated.connect(show_main)
        QtCore.QTimer.singleShot(700, show_launcher)
    else:
        def show_main() -> None:
            window.show()
            splash.finish(window)

        QtCore.QTimer.singleShot(700, show_main)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

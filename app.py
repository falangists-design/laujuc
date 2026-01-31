"""Application entrypoint for laujuc."""

from __future__ import annotations

import logging
import sys

from PySide6 import QtWidgets

from laujuc.gui_layer import LaujucWindow, LauncherWindow, apply_theme
from laujuc.settings_manager import SettingsManager


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    app = QtWidgets.QApplication(sys.argv)
    manager = SettingsManager()
    settings = manager.load()
    apply_theme(app, settings.theme)

    window = LaujucWindow()

    if settings.auth_enabled and not manager.is_activation_valid(settings):
        launcher = LauncherWindow(settings, manager)

        def show_main() -> None:
            launcher.close()
            window.show()

        launcher.authenticated.connect(show_main)
        launcher.show()
    else:
        window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

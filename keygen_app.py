"""Standalone activation key generator for laujuc."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from PySide6 import QtWidgets

from laujuc.gui_layer import AnimatedButton, NotificationBar, apply_theme
from laujuc.settings_manager import LaujucSettings, SettingsManager


class KeygenWindow(QtWidgets.QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("laujuc keygen")
        self.setMinimumSize(520, 340)
        self.manager = SettingsManager(app_name="laujuc_keygen")
        self.settings = self.manager.load()
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QtWidgets.QLabel("Key Generator")
        title.setObjectName("launcherTitle")
        subtitle = QtWidgets.QLabel(
            "Сгенерируйте ключ и экспортируйте его в файл для передачи команде."
        )
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)

        self.key_output = QtWidgets.QLineEdit()
        self.key_output.setReadOnly(True)
        self.key_output.setPlaceholderText("Новый ключ появится здесь")
        layout.addWidget(self.key_output)

        button_row = QtWidgets.QHBoxLayout()
        self.generate_button = AnimatedButton("Сгенерировать ключ")
        self.export_button = QtWidgets.QPushButton("Экспортировать JSON")
        self.copy_button = QtWidgets.QPushButton("Скопировать")
        button_row.addWidget(self.generate_button)
        button_row.addWidget(self.export_button)
        button_row.addWidget(self.copy_button)
        button_row.addStretch()
        layout.addLayout(button_row)

        self.notification = NotificationBar()
        layout.addWidget(self.notification)

        self.generate_button.clicked.connect(self._generate_key)
        self.export_button.clicked.connect(self._export_keys)
        self.copy_button.clicked.connect(self._copy_key)

    def _generate_key(self) -> None:
        key = self.manager.generate_one_time_key(self.settings)
        self.manager.save(self.settings)
        self.key_output.setText(key)
        self._show_notification("Ключ создан.", True)

    def _export_keys(self) -> None:
        if not self.key_output.text():
            self._show_notification("Сначала сгенерируйте ключ.", False)
            return
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Export Keys", "laujuc_keys.json"
        )
        if path:
            self.manager.export_keys(self.settings, Path(path))
            self._show_notification("Ключи экспортированы.", True)

    def _copy_key(self) -> None:
        if not self.key_output.text():
            self._show_notification("Ключ не создан.", False)
            return
        QtWidgets.QApplication.clipboard().setText(self.key_output.text())
        self._show_notification("Ключ скопирован.", True)

    def _show_notification(self, message: str, success: bool) -> None:
        self.notification.show_message(message, success)
        QtWidgets.QApplication.instance().processEvents()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    app = QtWidgets.QApplication(sys.argv)
    apply_theme(app, "dark")
    window = KeygenWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

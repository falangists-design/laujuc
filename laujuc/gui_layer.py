"""GUI layer for laujuc."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import logging

from PySide6 import QtCore, QtGui, QtWidgets

from laujuc.input_core import (
    AutomationScenario,
    InputCore,
    InputProfiler,
    IntegrationBridge,
    MouseButton,
    ScenarioAction,
)
from laujuc.settings_manager import LaujucSettings, SettingsManager


LOGGER = logging.getLogger(__name__)

ACCENT = "#0080FF"
BACKGROUND = "#0A0A0C"
SURFACE = "#14161A"
TEXT = "#E6E6E6"


class TitleBar(QtWidgets.QFrame):
    def __init__(self, parent: QtWidgets.QWidget) -> None:
        super().__init__(parent)
        self.setObjectName("titleBar")
        self.setFixedHeight(48)
        self._drag_pos: QtCore.QPoint | None = None

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 8, 0)

        self.title_label = QtWidgets.QLabel("laujuc")
        self.title_label.setObjectName("titleLabel")
        layout.addWidget(self.title_label)
        layout.addStretch()

        self.minimize_button = QtWidgets.QToolButton()
        self.minimize_button.setText("—")
        self.minimize_button.setObjectName("minimizeButton")
        layout.addWidget(self.minimize_button)

        self.close_button = QtWidgets.QToolButton()
        self.close_button.setText("×")
        self.close_button.setObjectName("closeButton")
        layout.addWidget(self.close_button)

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == QtCore.Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        if self._drag_pos and event.buttons() & QtCore.Qt.LeftButton:
            delta = event.globalPosition().toPoint() - self._drag_pos
            self.window().move(self.window().pos() + delta)
            self._drag_pos = event.globalPosition().toPoint()
        super().mouseMoveEvent(event)


class StatusPill(QtWidgets.QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("statusPill")
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(12, 4, 12, 4)
        self.indicator = QtWidgets.QLabel("●")
        self.label = QtWidgets.QLabel("Inactive")
        layout.addWidget(self.indicator)
        layout.addWidget(self.label)
        self.set_active(False)

    def set_active(self, active: bool) -> None:
        self.label.setText("Active" if active else "Inactive")
        self.indicator.setStyleSheet(
            f"color: {ACCENT};" if active else "color: #505050;"
        )


class LaujucWindow(QtWidgets.QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("laujuc")
        self.setWindowFlags(
            QtCore.Qt.WindowType.FramelessWindowHint
            | QtCore.Qt.WindowType.WindowSystemMenuHint
        )
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMinimumSize(1024, 680)

        self.input_core = InputCore()
        self.profiler = InputProfiler()
        self.settings_manager = SettingsManager()
        self.settings = self.settings_manager.load()
        self.integration_bridge = IntegrationBridge()

        self._setup_ui()
        self._setup_tray()
        self._apply_settings()
        self._setup_shortcuts()

    def _setup_ui(self) -> None:
        self.shadow = QtWidgets.QGraphicsDropShadowEffect(self)
        self.shadow.setBlurRadius(30)
        self.shadow.setColor(QtGui.QColor(0, 0, 0, 180))
        self.shadow.setOffset(0, 8)
        self.setGraphicsEffect(self.shadow)

        outer_layout = QtWidgets.QVBoxLayout(self)
        outer_layout.setContentsMargins(16, 16, 16, 16)

        container = QtWidgets.QFrame()
        container.setObjectName("mainContainer")
        container_layout = QtWidgets.QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)

        self.title_bar = TitleBar(self)
        container_layout.addWidget(self.title_bar)

        content = QtWidgets.QFrame()
        content_layout = QtWidgets.QVBoxLayout(content)
        content_layout.setContentsMargins(24, 16, 24, 24)

        header_layout = QtWidgets.QHBoxLayout()
        header_label = QtWidgets.QLabel("Input Automation Framework")
        header_label.setObjectName("headerLabel")
        header_layout.addWidget(header_label)
        header_layout.addStretch()
        self.status_pill = StatusPill()
        header_layout.addWidget(self.status_pill)
        content_layout.addLayout(header_layout)

        self.tab_widget = QtWidgets.QTabWidget()
        self.tab_widget.setObjectName("tabWidget")
        self.tab_widget.addTab(self._build_scenarios_tab(), "Сценарии")
        self.tab_widget.addTab(self._build_profiles_tab(), "Профили")
        self.tab_widget.addTab(self._build_settings_tab(), "Настройки")
        self.tab_widget.addTab(self._build_docs_tab(), "Документация")
        content_layout.addWidget(self.tab_widget)
        self.tab_widget.currentChanged.connect(self._animate_tabs)

        self._tab_opacity = QtWidgets.QGraphicsOpacityEffect(self.tab_widget)
        self.tab_widget.setGraphicsEffect(self._tab_opacity)
        self._tab_animation = QtCore.QPropertyAnimation(self._tab_opacity, b"opacity")
        self._tab_animation.setDuration(220)
        self._tab_animation.setStartValue(0.6)
        self._tab_animation.setEndValue(1.0)

        footer_layout = QtWidgets.QHBoxLayout()
        self.session_timer_label = QtWidgets.QLabel("Session: 00:00:00")
        self.click_counter_label = QtWidgets.QLabel("Clicks: 0")
        footer_layout.addWidget(self.session_timer_label)
        footer_layout.addStretch()
        footer_layout.addWidget(self.click_counter_label)
        content_layout.addLayout(footer_layout)

        container_layout.addWidget(content)
        outer_layout.addWidget(container)

        self.title_bar.close_button.clicked.connect(self._handle_close)
        self.title_bar.minimize_button.clicked.connect(self.showMinimized)

        self._session_seconds = 0
        self._click_count = 0
        self._timer = QtCore.QTimer(self)
        self._timer.timeout.connect(self._tick_session)
        self._timer.start(1000)

        self.resize_grip = QtWidgets.QSizeGrip(self)
        self.resize_grip.setFixedSize(16, 16)
        outer_layout.addWidget(self.resize_grip, 0, QtCore.Qt.AlignBottom | QtCore.Qt.AlignRight)

    def _build_scenarios_tab(self) -> QtWidgets.QWidget:
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setSpacing(16)

        info = QtWidgets.QLabel(
            "Создавайте сценарии автоматизации, записывайте действия и запускайте их для тестов."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        controls = QtWidgets.QHBoxLayout()
        self.record_button = QtWidgets.QPushButton("Запись")
        self.play_button = QtWidgets.QPushButton("Воспроизвести")
        self.export_button = QtWidgets.QPushButton("Экспорт в Selenium")
        controls.addWidget(self.record_button)
        controls.addWidget(self.play_button)
        controls.addWidget(self.export_button)
        controls.addStretch()
        layout.addLayout(controls)

        self.scenario_list = QtWidgets.QListWidget()
        self.scenario_list.addItem("Demo: Web Form Test")
        self.scenario_list.addItem("Demo: Accessibility Macro")
        layout.addWidget(self.scenario_list)

        self.record_button.clicked.connect(self._toggle_recording)
        self.play_button.clicked.connect(self._play_selected_scenario)
        self.export_button.clicked.connect(self._export_selected_scenario)

        return widget

    def _build_profiles_tab(self) -> QtWidgets.QWidget:
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setSpacing(16)

        info = QtWidgets.QLabel(
            "Профилирование фиксирует паттерны ввода для анализа производительности UI."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        actions = QtWidgets.QHBoxLayout()
        self.profile_start_button = QtWidgets.QPushButton("Старт профиля")
        self.profile_stop_button = QtWidgets.QPushButton("Стоп профиля")
        actions.addWidget(self.profile_start_button)
        actions.addWidget(self.profile_stop_button)
        actions.addStretch()
        layout.addLayout(actions)

        self.profile_output = QtWidgets.QTextEdit()
        self.profile_output.setReadOnly(True)
        layout.addWidget(self.profile_output)

        self.profile_start_button.clicked.connect(self._start_profile)
        self.profile_stop_button.clicked.connect(self._stop_profile)

        return widget

    def _build_settings_tab(self) -> QtWidgets.QWidget:
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setSpacing(18)

        hotkey_layout = QtWidgets.QHBoxLayout()
        hotkey_layout.addWidget(QtWidgets.QLabel("Горячая клавиша"))
        self.hotkey_input = QtWidgets.QLineEdit()
        hotkey_layout.addWidget(self.hotkey_input)
        layout.addLayout(hotkey_layout)

        cps_layout = QtWidgets.QHBoxLayout()
        cps_layout.addWidget(QtWidgets.QLabel("Скорость (CPS)"))
        self.cps_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.cps_slider.setRange(1, 100)
        self.cps_value = QtWidgets.QLabel("10")
        self.cps_slider.valueChanged.connect(lambda v: self.cps_value.setText(str(v)))
        cps_layout.addWidget(self.cps_slider)
        cps_layout.addWidget(self.cps_value)
        layout.addLayout(cps_layout)

        mode_layout = QtWidgets.QHBoxLayout()
        self.hold_mode_toggle = QtWidgets.QCheckBox("Hold режим")
        self.toggle_mode_toggle = QtWidgets.QCheckBox("Toggle режим")
        mode_layout.addWidget(self.hold_mode_toggle)
        mode_layout.addWidget(self.toggle_mode_toggle)
        mode_layout.addStretch()
        layout.addLayout(mode_layout)

        self.hold_mode_toggle.toggled.connect(self._sync_mode_toggles)
        self.toggle_mode_toggle.toggled.connect(self._sync_mode_toggles)

        button_layout = QtWidgets.QHBoxLayout()
        self.left_button_toggle = QtWidgets.QCheckBox("Левая кнопка")
        self.right_button_toggle = QtWidgets.QCheckBox("Правая кнопка")
        self.middle_button_toggle = QtWidgets.QCheckBox("Средняя кнопка")
        button_layout.addWidget(self.left_button_toggle)
        button_layout.addWidget(self.right_button_toggle)
        button_layout.addWidget(self.middle_button_toggle)
        button_layout.addStretch()
        layout.addLayout(button_layout)

        process_layout = QtWidgets.QHBoxLayout()
        process_layout.addWidget(QtWidgets.QLabel("Процесс"))
        self.process_combo = QtWidgets.QComboBox()
        self.process_combo.addItems(["", "chrome.exe", "code.exe", "app_under_test.exe"])
        process_layout.addWidget(self.process_combo)
        layout.addLayout(process_layout)

        sound_layout = QtWidgets.QHBoxLayout()
        self.sound_toggle = QtWidgets.QCheckBox("Звуковые уведомления")
        sound_layout.addWidget(self.sound_toggle)
        sound_layout.addStretch()
        layout.addLayout(sound_layout)

        export_layout = QtWidgets.QHBoxLayout()
        self.save_button = QtWidgets.QPushButton("Сохранить")
        self.export_json_button = QtWidgets.QPushButton("Экспорт JSON")
        self.export_xml_button = QtWidgets.QPushButton("Экспорт XML")
        export_layout.addWidget(self.save_button)
        export_layout.addWidget(self.export_json_button)
        export_layout.addWidget(self.export_xml_button)
        export_layout.addStretch()
        layout.addLayout(export_layout)

        self.save_button.clicked.connect(self._save_settings)
        self.export_json_button.clicked.connect(self._export_json)
        self.export_xml_button.clicked.connect(self._export_xml)

        return widget

    def _build_docs_tab(self) -> QtWidgets.QWidget:
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)

        self.docs_browser = QtWidgets.QTextBrowser()
        docs_path = Path(__file__).resolve().parents[1] / "docs" / "user_guide.md"
        if docs_path.exists():
            self.docs_browser.setMarkdown(docs_path.read_text(encoding="utf-8"))
        else:
            self.docs_browser.setPlainText("Documentation not found.")
        layout.addWidget(self.docs_browser)
        return widget

    def _apply_settings(self) -> None:
        self.hotkey_input.setText(self.settings.hotkey_toggle)
        self.cps_slider.setValue(self.settings.cps)
        self.hold_mode_toggle.setChecked(self.settings.hold_mode)
        self.toggle_mode_toggle.setChecked(not self.settings.hold_mode)
        self.process_combo.setCurrentText(self.settings.target_process)
        self.left_button_toggle.setChecked(self.settings.left_button_enabled)
        self.right_button_toggle.setChecked(self.settings.right_button_enabled)
        self.middle_button_toggle.setChecked(self.settings.middle_button_enabled)
        self.sound_toggle.setChecked(self.settings.play_sound)

    def _sync_mode_toggles(self) -> None:
        sender = self.sender()
        if sender is self.hold_mode_toggle and self.hold_mode_toggle.isChecked():
            self.toggle_mode_toggle.setChecked(False)
        elif sender is self.toggle_mode_toggle and self.toggle_mode_toggle.isChecked():
            self.hold_mode_toggle.setChecked(False)
        if not self.hold_mode_toggle.isChecked() and not self.toggle_mode_toggle.isChecked():
            self.hold_mode_toggle.setChecked(True)

    def _setup_tray(self) -> None:
        icon_path = Path(__file__).resolve().parent / "resources" / "laujuc_icon.svg"
        self.tray_icon = QtWidgets.QSystemTrayIcon(QtGui.QIcon(str(icon_path)), self)
        menu = QtWidgets.QMenu()
        restore_action = menu.addAction("Restore")
        quit_action = menu.addAction("Quit")
        restore_action.triggered.connect(self.showNormal)
        quit_action.triggered.connect(QtWidgets.QApplication.quit)
        self.tray_icon.setContextMenu(menu)
        self.tray_icon.show()

    def _setup_shortcuts(self) -> None:
        self.toggle_shortcut = QtGui.QShortcut(
            QtGui.QKeySequence(self.settings.hotkey_toggle),
            self,
            activated=self._toggle_visibility,
        )

    def _toggle_visibility(self) -> None:
        if self.isVisible():
            self.hide()
        else:
            self.showNormal()
            self.raise_()

    def _save_settings(self) -> None:
        self.settings = self._collect_settings()
        self.settings_manager.save(self.settings)
        self.status_pill.set_active(True)

    def _export_json(self) -> None:
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Export JSON", "laujuc.json")
        if path:
            settings = self._collect_settings()
            Path(path).write_text(json_dump(asdict(settings)), encoding="utf-8")

    def _export_xml(self) -> None:
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Export XML", "laujuc.xml")
        if path:
            settings = self._collect_settings()
            self.settings_manager.export_xml(settings, Path(path))

    def _handle_close(self) -> None:
        self.hide()
        self.tray_icon.showMessage(
            "laujuc",
            "Приложение свернуто в трей.",
            QtWidgets.QSystemTrayIcon.MessageIcon.Information,
            2000,
        )

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        event.ignore()
        self._handle_close()

    def _toggle_recording(self) -> None:
        if self.record_button.text() == "Запись":
            self.record_button.setText("Стоп")
            self.status_pill.set_active(True)
        else:
            self.record_button.setText("Запись")
            self.status_pill.set_active(False)

    def _play_selected_scenario(self) -> None:
        scenario = AutomationScenario(name="Demo")
        scenario.add_action(ScenarioAction.CLICK, {"button": MouseButton.LEFT.value})
        scenario.add_action(ScenarioAction.PAUSE, {"seconds": 0.3})
        scenario.add_action(ScenarioAction.KEY_PRESS, {"key": "A"})
        scenario.add_action(ScenarioAction.KEY_RELEASE, {"key": "A"})
        scenario.play(self.input_core)
        self._click_count += 1
        self.click_counter_label.setText(f"Clicks: {self._click_count}")

    def _export_selected_scenario(self) -> None:
        scenario = AutomationScenario(name="Demo")
        scenario.add_action(ScenarioAction.CLICK, {"button": MouseButton.LEFT.value})
        script = self.integration_bridge.to_selenium_script(scenario)
        dialog = QtWidgets.QMessageBox(self)
        dialog.setWindowTitle("Selenium Export")
        dialog.setText("Скрипт экспортирован:")
        dialog.setDetailedText(script)
        dialog.exec()

    def _start_profile(self) -> None:
        self.profiler.start("Session profile")
        self.profile_output.append("Профилирование запущено...")

    def _stop_profile(self) -> None:
        profile = self.profiler.stop()
        if not profile:
            self.profile_output.append("Профиль не найден.")
            return
        summary = profile.summary()
        self.profile_output.append(f"Summary: {summary}")

    def _tick_session(self) -> None:
        self._session_seconds += 1
        hours, remainder = divmod(self._session_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        self.session_timer_label.setText(f"Session: {hours:02d}:{minutes:02d}:{seconds:02d}")

    def _animate_tabs(self) -> None:
        self._tab_animation.stop()
        self._tab_animation.start()

    def _collect_settings(self) -> LaujucSettings:
        return LaujucSettings(
            hotkey_toggle=self.hotkey_input.text(),
            cps=self.cps_slider.value(),
            hold_mode=self.hold_mode_toggle.isChecked(),
            target_process=self.process_combo.currentText(),
            left_button_enabled=self.left_button_toggle.isChecked(),
            right_button_enabled=self.right_button_toggle.isChecked(),
            middle_button_enabled=self.middle_button_toggle.isChecked(),
            play_sound=self.sound_toggle.isChecked(),
        )


def json_dump(data: dict) -> str:
    import json

    return json.dumps(data, indent=2, ensure_ascii=False)


def apply_theme(app: QtWidgets.QApplication) -> None:
    palette = QtGui.QPalette()
    palette.setColor(QtGui.QPalette.Window, QtGui.QColor(BACKGROUND))
    palette.setColor(QtGui.QPalette.WindowText, QtGui.QColor(TEXT))
    palette.setColor(QtGui.QPalette.Base, QtGui.QColor(SURFACE))
    palette.setColor(QtGui.QPalette.Text, QtGui.QColor(TEXT))
    palette.setColor(QtGui.QPalette.Button, QtGui.QColor(SURFACE))
    palette.setColor(QtGui.QPalette.ButtonText, QtGui.QColor(TEXT))
    palette.setColor(QtGui.QPalette.Highlight, QtGui.QColor(ACCENT))
    app.setPalette(palette)

    app.setStyleSheet(
        f"""
        #mainContainer {{
            background-color: {BACKGROUND};
            border-radius: 16px;
        }}
        #titleBar {{
            background-color: {SURFACE};
            border-top-left-radius: 16px;
            border-top-right-radius: 16px;
        }}
        #titleLabel {{
            color: {TEXT};
            font-size: 18px;
            font-weight: 600;
        }}
        #headerLabel {{
            font-size: 20px;
            font-weight: 600;
            color: {TEXT};
        }}
        #minimizeButton, #closeButton {{
            color: {TEXT};
            font-size: 18px;
            padding: 4px 12px;
            border-radius: 10px;
            background-color: transparent;
        }}
        #minimizeButton:hover, #closeButton:hover {{
            background-color: rgba(0, 128, 255, 0.2);
        }}
        #statusPill {{
            background-color: {SURFACE};
            border-radius: 14px;
            color: {TEXT};
        }}
        QTabWidget::pane {{
            border: 1px solid rgba(0, 128, 255, 0.2);
            border-radius: 12px;
            padding: 8px;
        }}
        QTabBar::tab {{
            background: {SURFACE};
            padding: 8px 18px;
            border-top-left-radius: 10px;
            border-top-right-radius: 10px;
            margin-right: 4px;
        }}
        QTabBar::tab:selected {{
            background: rgba(0, 128, 255, 0.2);
        }}
        QPushButton {{
            background-color: {ACCENT};
            color: white;
            padding: 8px 16px;
            border-radius: 10px;
        }}
        QPushButton:hover {{
            background-color: #2d95ff;
        }}
        QSlider::groove:horizontal {{
            height: 6px;
            background: #1f2228;
            border-radius: 3px;
        }}
        QSlider::handle:horizontal {{
            background: {ACCENT};
            width: 16px;
            margin: -5px 0;
            border-radius: 8px;
        }}
        QLineEdit, QTextEdit, QTextBrowser, QComboBox {{
            background-color: #101217;
            border: 1px solid rgba(0, 128, 255, 0.2);
            border-radius: 8px;
            padding: 6px 8px;
        }}
        QCheckBox {{
            spacing: 6px;
        }}
        """
    )

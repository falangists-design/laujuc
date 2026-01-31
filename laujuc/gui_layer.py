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
ACCENT_HOVER = "#0066CC"
BACKGROUND = "#0A0A0C"
SURFACE = "#14161A"
TEXT = "#E6E6E6"
LIGHT_BACKGROUND = "#F5F7FA"
LIGHT_SURFACE = "#FFFFFF"
LIGHT_TEXT = "#202124"


class AnimatedButton(QtWidgets.QPushButton):
    def __init__(self, label: str) -> None:
        super().__init__(label)
        self._bg_color = QtGui.QColor(ACCENT)
        self._target_color = QtGui.QColor(ACCENT)
        self._animation = QtCore.QPropertyAnimation(self, b"bgColor")
        self._animation.setDuration(140)
        self._animation.setEasingCurve(QtCore.QEasingCurve.InOutQuad)
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setMinimumHeight(36)

    def enterEvent(self, event: QtCore.QEvent) -> None:
        self._animate_to(QtGui.QColor(ACCENT_HOVER))
        super().enterEvent(event)

    def leaveEvent(self, event: QtCore.QEvent) -> None:
        self._animate_to(QtGui.QColor(ACCENT))
        super().leaveEvent(event)

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        self._animate_to(QtGui.QColor("#0057B3"))
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        target = QtGui.QColor(ACCENT_HOVER if self.underMouse() else ACCENT)
        self._animate_to(target)
        super().mouseReleaseEvent(event)

    def _animate_to(self, color: QtGui.QColor) -> None:
        if self._target_color == color:
            return
        self._target_color = color
        self._animation.stop()
        self._animation.setStartValue(self._bg_color)
        self._animation.setEndValue(color)
        self._animation.start()

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        rect = self.rect().adjusted(1, 1, -1, -1)
        painter.setBrush(QtGui.QBrush(self._bg_color))
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawRoundedRect(rect, 10, 10)
        painter.setPen(QtGui.QColor("white"))
        painter.drawText(rect, QtCore.Qt.AlignCenter, self.text())

    def get_bg_color(self) -> QtGui.QColor:
        return self._bg_color

    def set_bg_color(self, color: QtGui.QColor) -> None:
        self._bg_color = color
        self.update()

    bgColor = QtCore.Property(QtGui.QColor, get_bg_color, set_bg_color)


class NotificationBar(QtWidgets.QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("notificationBar")
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        self.icon = QtWidgets.QLabel("●")
        self.label = QtWidgets.QLabel("")
        layout.addWidget(self.icon)
        layout.addWidget(self.label)
        self.setVisible(False)

    def show_message(self, text: str, success: bool = True) -> None:
        self.label.setText(text)
        self.icon.setStyleSheet(f"color: {'#35c759' if success else '#ff453a'};")
        self.setVisible(True)

    def clear(self) -> None:
        self.setVisible(False)


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


class LauncherWindow(QtWidgets.QWidget):
    authenticated = QtCore.Signal()

    def __init__(self, settings: LaujucSettings, manager: SettingsManager) -> None:
        super().__init__()
        self.settings = settings
        self.manager = manager
        self.setWindowTitle("laujuc launcher")
        self.setWindowFlags(
            QtCore.Qt.WindowType.FramelessWindowHint
            | QtCore.Qt.WindowType.WindowSystemMenuHint
        )
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(520, 360)
        self._setup_ui()
        self._update_activation_timer()

    def _setup_ui(self) -> None:
        outer_layout = QtWidgets.QVBoxLayout(self)
        outer_layout.setContentsMargins(18, 18, 18, 18)

        container = QtWidgets.QFrame()
        container.setObjectName("launcherContainer")
        layout = QtWidgets.QVBoxLayout(container)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QtWidgets.QLabel("laujuc launcher")
        title.setObjectName("launcherTitle")
        subtitle = QtWidgets.QLabel(
            "Введите ключ активации для доступа к инструментам тестирования."
        )
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)

        self.key_input = QtWidgets.QLineEdit()
        self.key_input.setPlaceholderText("Ключ активации")
        layout.addWidget(self.key_input)

        self.validation_label = QtWidgets.QLabel("Ключ не проверен")
        self.validation_label.setObjectName("validationLabel")
        layout.addWidget(self.validation_label)

        button_row = QtWidgets.QHBoxLayout()
        self.auth_button = AnimatedButton("Активировать")
        self.import_button = QtWidgets.QPushButton("Импортировать ключи")
        button_row.addWidget(self.auth_button)
        button_row.addWidget(self.import_button)
        button_row.addStretch()
        layout.addLayout(button_row)

        self.timer_label = QtWidgets.QLabel("Сессия: 00:00:00")
        layout.addWidget(self.timer_label)

        self.notification = NotificationBar()
        layout.addWidget(self.notification)

        outer_layout.addWidget(container)

        self.auth_button.clicked.connect(self._attempt_auth)
        self.import_button.clicked.connect(self._import_keys)

        self._timer = QtCore.QTimer(self)
        self._timer.timeout.connect(self._update_activation_timer)
        self._timer.start(1000)

    def _attempt_auth(self) -> None:
        key = self.key_input.text().strip()
        if not key:
            self._set_validation(False, "Введите ключ.")
            LOGGER.warning("Activation attempt without key.")
            return
        if self.manager.activate_key(self.settings, key):
            self.manager.save(self.settings)
            self._set_validation(True, "Ключ принят.")
            self.notification.show_message("Активация прошла успешно.", True)
            LOGGER.info("Activation success.")
            self.authenticated.emit()
        else:
            self._set_validation(False, "Неверный ключ.")
            self.notification.show_message("Ошибка активации.", False)
            LOGGER.warning("Activation failed.")

    def _import_keys(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Import Keys", "", "JSON Files (*.json)"
        )
        if path:
            self.manager.import_keys(self.settings, Path(path))
            self.manager.save(self.settings)
            self.notification.show_message("Ключи импортированы.", True)

    def _set_validation(self, valid: bool, message: str) -> None:
        color = "#35c759" if valid else "#ff453a"
        self.validation_label.setText(message)
        self.validation_label.setStyleSheet(f"color: {color};")

    def _update_activation_timer(self) -> None:
        if not self.settings.activation_valid_until:
            self.timer_label.setText("Сессия: 00:00:00")
            return
        expires_at = QtCore.QDateTime.fromString(
            self.settings.activation_valid_until, QtCore.Qt.ISODate
        )
        if not expires_at.isValid():
            self.timer_label.setText("Сессия: 00:00:00")
            return
        remaining = QtCore.QDateTime.currentDateTimeUtc().secsTo(expires_at)
        remaining = max(0, remaining)
        hours = remaining // 3600
        minutes = (remaining % 3600) // 60
        seconds = remaining % 60
        self.timer_label.setText(f"Сессия: {hours:02d}:{minutes:02d}:{seconds:02d}")
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
        content_layout.setSpacing(16)

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
        self.tab_widget.setDocumentMode(True)
        self.tab_widget.tabBar().setDrawBase(False)
        self.tab_widget.addTab(self._build_scenarios_tab(), "Сценарии")
        self.tab_widget.addTab(self._build_profiles_tab(), "Профили")
        self.tab_widget.addTab(self._build_settings_tab(), "Настройки")
        self.tab_widget.addTab(self._build_docs_tab(), "Документация")
        content_layout.addWidget(self.tab_widget)

        self.notification_bar = NotificationBar()
        content_layout.addWidget(self.notification_bar)

        footer_layout = QtWidgets.QHBoxLayout()
        self.session_timer_label = QtWidgets.QLabel("Session: 00:00:00")
        self.activation_timer_label = QtWidgets.QLabel("Activation: 00:00:00")
        self.click_counter_label = QtWidgets.QLabel("Clicks: 0")
        footer_layout.addWidget(self.session_timer_label)
        footer_layout.addWidget(self.activation_timer_label)
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
        widget.setAutoFillBackground(True)
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setSpacing(16)

        info = QtWidgets.QLabel(
            "Создавайте сценарии автоматизации, записывайте действия и запускайте их для тестов."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        controls = QtWidgets.QHBoxLayout()
        self.record_button = AnimatedButton("Запись")
        self.play_button = AnimatedButton("Воспроизвести")
        self.export_button = AnimatedButton("Экспорт в Selenium")
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
        widget.setAutoFillBackground(True)
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setSpacing(16)

        info = QtWidgets.QLabel(
            "Профилирование фиксирует паттерны ввода для анализа производительности UI."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        actions = QtWidgets.QHBoxLayout()
        self.profile_start_button = AnimatedButton("Старт профиля")
        self.profile_stop_button = AnimatedButton("Стоп профиля")
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
        widget.setAutoFillBackground(True)
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
        self.save_button = AnimatedButton("Сохранить")
        self.export_json_button = QtWidgets.QPushButton("Экспорт JSON")
        self.export_xml_button = QtWidgets.QPushButton("Экспорт XML")
        export_layout.addWidget(self.save_button)
        export_layout.addWidget(self.export_json_button)
        export_layout.addWidget(self.export_xml_button)
        export_layout.addStretch()
        layout.addLayout(export_layout)

        auth_layout = QtWidgets.QHBoxLayout()
        self.auth_toggle = QtWidgets.QCheckBox("Требовать активацию при запуске")
        auth_layout.addWidget(self.auth_toggle)
        auth_layout.addStretch()
        layout.addLayout(auth_layout)

        theme_layout = QtWidgets.QHBoxLayout()
        theme_layout.addWidget(QtWidgets.QLabel("Тема"))
        self.theme_combo = QtWidgets.QComboBox()
        self.theme_combo.addItems(["dark", "light"])
        theme_layout.addWidget(self.theme_combo)
        theme_layout.addStretch()
        layout.addLayout(theme_layout)

        key_layout = QtWidgets.QHBoxLayout()
        self.export_keys_button = QtWidgets.QPushButton("Экспорт ключей")
        self.import_keys_button = QtWidgets.QPushButton("Импорт ключей")
        key_layout.addWidget(self.export_keys_button)
        key_layout.addWidget(self.import_keys_button)
        key_layout.addStretch()
        layout.addLayout(key_layout)

        self.save_button.clicked.connect(self._save_settings)
        self.export_json_button.clicked.connect(self._export_json)
        self.export_xml_button.clicked.connect(self._export_xml)
        self.export_keys_button.clicked.connect(self._export_keys)
        self.import_keys_button.clicked.connect(self._import_keys)

        return widget

    def _build_docs_tab(self) -> QtWidgets.QWidget:
        widget = QtWidgets.QWidget()
        widget.setAutoFillBackground(True)
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
        self.auth_toggle.setChecked(self.settings.auth_enabled)
        self.theme_combo.setCurrentText(self.settings.theme)

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
        self.toggle_shortcut.setContext(QtCore.Qt.ApplicationShortcut)

    def _toggle_visibility(self) -> None:
        if self.isVisible():
            self.hide()
        else:
            self.showNormal()
            self.raise_()

    def _save_settings(self) -> None:
        settings = self._collect_settings()
        if not self._validate_settings(settings):
            return
        self.settings = settings
        self.settings_manager.save(self.settings)
        self.status_pill.set_active(True)
        self._show_notification("Настройки сохранены.", True)
        apply_theme(QtWidgets.QApplication.instance(), self.settings.theme)
        self.toggle_shortcut.setKey(QtGui.QKeySequence(self.settings.hotkey_toggle))

    def _export_json(self) -> None:
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Export JSON", "laujuc.json")
        if path:
            settings = self._collect_settings()
            if not self._validate_settings(settings):
                return
            Path(path).write_text(json_dump(asdict(settings)), encoding="utf-8")
            self._show_notification("Настройки экспортированы в JSON.", True)

    def _export_xml(self) -> None:
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Export XML", "laujuc.xml")
        if path:
            settings = self._collect_settings()
            if not self._validate_settings(settings):
                return
            self.settings_manager.export_xml(settings, Path(path))
            self._show_notification("Настройки экспортированы в XML.", True)

    def _export_keys(self) -> None:
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Export Keys", "laujuc_keys.json"
        )
        if path:
            self.settings_manager.export_keys(self.settings, Path(path))
            self._show_notification("Ключи экспортированы.", True)

    def _import_keys(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Import Keys", "", "JSON Files (*.json)"
        )
        if path:
            self.settings_manager.import_keys(self.settings, Path(path))
            self.settings_manager.save(self.settings)
            self._show_notification("Ключи импортированы.", True)

    def _handle_close(self) -> None:
        self.hide()
        self.tray_icon.showMessage(
            "laujuc",
            "Приложение свернуто в трей.",
            QtWidgets.QSystemTrayIcon.MessageIcon.Information,
            2000,
        )
        self._show_notification("Приложение свернуто в трей.", True)

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        event.ignore()
        self._handle_close()

    def _toggle_recording(self) -> None:
        if self.record_button.text() == "Запись":
            self.record_button.setText("Стоп")
            self.status_pill.set_active(True)
            self._show_notification("Запись начата.", True)
        else:
            self.record_button.setText("Запись")
            self.status_pill.set_active(False)
            self._show_notification("Запись остановлена.", True)

    def _play_selected_scenario(self) -> None:
        scenario = AutomationScenario(name="Demo")
        scenario.add_action(ScenarioAction.CLICK, {"button": MouseButton.LEFT.value})
        scenario.add_action(ScenarioAction.PAUSE, {"seconds": 0.3})
        scenario.add_action(ScenarioAction.KEY_PRESS, {"key": "A"})
        scenario.add_action(ScenarioAction.KEY_RELEASE, {"key": "A"})
        scenario.play(self.input_core)
        self._click_count += 1
        self.click_counter_label.setText(f"Clicks: {self._click_count}")
        self._show_notification("Сценарий воспроизведен.", True)

    def _export_selected_scenario(self) -> None:
        scenario = AutomationScenario(name="Demo")
        scenario.add_action(ScenarioAction.CLICK, {"button": MouseButton.LEFT.value})
        script = self.integration_bridge.to_selenium_script(scenario)
        dialog = QtWidgets.QMessageBox(self)
        dialog.setWindowTitle("Selenium Export")
        dialog.setText("Скрипт экспортирован:")
        dialog.setDetailedText(script)
        dialog.exec()
        self._show_notification("Скрипт Selenium подготовлен.", True)

    def _start_profile(self) -> None:
        self.profiler.start("Session profile")
        self.profile_output.append("Профилирование запущено...")
        self._show_notification("Профилирование запущено.", True)

    def _stop_profile(self) -> None:
        profile = self.profiler.stop()
        if not profile:
            self.profile_output.append("Профиль не найден.")
            return
        summary = profile.summary()
        self.profile_output.append(f"Summary: {summary}")
        self._show_notification("Профилирование завершено.", True)

    def _tick_session(self) -> None:
        self._session_seconds += 1
        hours, remainder = divmod(self._session_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        self.session_timer_label.setText(f"Session: {hours:02d}:{minutes:02d}:{seconds:02d}")
        self._update_activation_timer()

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
            auth_enabled=self.auth_toggle.isChecked(),
            activation_key=self.settings.activation_key,
            activation_valid_until=self.settings.activation_valid_until,
            known_keys=self.settings.known_keys,
            theme=self.theme_combo.currentText(),
            activation_session_minutes=self.settings.activation_session_minutes,
        )

    def _validate_settings(self, settings: LaujucSettings) -> bool:
        if not settings.hotkey_toggle:
            self._show_notification("Горячая клавиша не задана.", False)
            return False
        if not (1 <= settings.cps <= 100):
            self._show_notification("CPS должен быть от 1 до 100.", False)
            return False
        return True

    def _show_notification(self, message: str, success: bool) -> None:
        self.notification_bar.show_message(message, success)
        QtCore.QTimer.singleShot(2400, self.notification_bar.clear)

    def _update_activation_timer(self) -> None:
        if not self.settings.activation_valid_until:
            self.activation_timer_label.setText("Activation: 00:00:00")
            return
        expires_at = QtCore.QDateTime.fromString(
            self.settings.activation_valid_until, QtCore.Qt.ISODate
        )
        if not expires_at.isValid():
            self.activation_timer_label.setText("Activation: 00:00:00")
            return
        remaining = QtCore.QDateTime.currentDateTimeUtc().secsTo(expires_at)
        remaining = max(0, remaining)
        hours = remaining // 3600
        minutes = (remaining % 3600) // 60
        seconds = remaining % 60
        self.activation_timer_label.setText(
            f"Activation: {hours:02d}:{minutes:02d}:{seconds:02d}"
        )


def json_dump(data: dict) -> str:
    import json

    return json.dumps(data, indent=2, ensure_ascii=False)


def apply_theme(app: QtWidgets.QApplication, theme: str = "dark") -> None:
    dark_mode = theme != "light"
    bg = BACKGROUND if dark_mode else LIGHT_BACKGROUND
    surface = SURFACE if dark_mode else LIGHT_SURFACE
    text = TEXT if dark_mode else LIGHT_TEXT
    palette = QtGui.QPalette()
    palette.setColor(QtGui.QPalette.Window, QtGui.QColor(bg))
    palette.setColor(QtGui.QPalette.WindowText, QtGui.QColor(text))
    palette.setColor(QtGui.QPalette.Base, QtGui.QColor(surface))
    palette.setColor(QtGui.QPalette.Text, QtGui.QColor(text))
    palette.setColor(QtGui.QPalette.Button, QtGui.QColor(surface))
    palette.setColor(QtGui.QPalette.ButtonText, QtGui.QColor(text))
    palette.setColor(QtGui.QPalette.Highlight, QtGui.QColor(ACCENT))
    app.setPalette(palette)

    app.setStyleSheet(
        f"""
        #mainContainer {{
            background-color: {bg};
            border-radius: 16px;
        }}
        QFrame {{
            background-color: transparent;
        }}
        #titleBar {{
            background-color: {surface};
            border-top-left-radius: 16px;
            border-top-right-radius: 16px;
        }}
        #titleLabel {{
            color: {text};
            font-size: 18px;
            font-weight: 600;
        }}
        #headerLabel {{
            font-size: 20px;
            font-weight: 600;
            color: {text};
        }}
        #minimizeButton, #closeButton {{
            color: {text};
            font-size: 18px;
            padding: 4px 12px;
            border-radius: 10px;
            background-color: transparent;
        }}
        #minimizeButton:hover, #closeButton:hover {{
            background-color: rgba(0, 128, 255, 0.2);
        }}
        #minimizeButton:pressed, #closeButton:pressed {{
            background-color: rgba(0, 128, 255, 0.35);
        }}
        #statusPill {{
            background-color: {surface};
            border-radius: 14px;
            color: {text};
            border: 1px solid rgba(0, 128, 255, 0.25);
        }}
        #notificationBar {{
            background-color: {surface};
            border-radius: 10px;
            border: 1px solid rgba(0, 128, 255, 0.25);
            color: {text};
        }}
        #launcherContainer {{
            background-color: {bg};
            border-radius: 18px;
            border: 1px solid rgba(0, 128, 255, 0.2);
        }}
        #launcherTitle {{
            font-size: 22px;
            font-weight: 600;
            color: {text};
        }}
        #validationLabel {{
            font-weight: 600;
        }}
        QTabWidget::pane {{
            border: 1px solid rgba(0, 128, 255, 0.2);
            border-radius: 12px;
            padding: 8px;
            background-color: {surface};
        }}
        QTabWidget {{
            background-color: {bg};
        }}
        QStackedWidget {{
            background-color: {surface};
            border-radius: 10px;
        }}
        QTabWidget QWidget {{
            background-color: {surface};
        }}
        QTabBar {{
            background-color: transparent;
        }}
        QTabBar::tab {{
            background: {surface};
            padding: 8px 18px;
            border-top-left-radius: 10px;
            border-top-right-radius: 10px;
            margin-right: 4px;
            color: {text};
        }}
        QTabBar::tab:selected {{
            background: rgba(0, 128, 255, 0.22);
            color: {text};
        }}
        QTabBar::tab:hover {{
            background: rgba(0, 128, 255, 0.16);
            color: {text};
        }}
        QPushButton {{
            background-color: transparent;
            color: {text};
            padding: 8px 14px;
            border-radius: 10px;
            border: 1px solid rgba(0, 128, 255, 0.3);
        }}
        QPushButton:hover {{
            border: 1px solid {ACCENT};
            color: {ACCENT};
        }}
        QPushButton:pressed {{
            background-color: rgba(0, 128, 255, 0.2);
        }}
        QSlider::groove:horizontal {{
            height: 6px;
            background: {'#1f2228' if dark_mode else '#d2d6df'};
            border-radius: 3px;
        }}
        QSlider::handle:horizontal {{
            background: {ACCENT};
            width: 16px;
            margin: -5px 0;
            border-radius: 8px;
        }}
        QLineEdit, QTextEdit, QTextBrowser, QComboBox, QListWidget {{
            background-color: {'#101217' if dark_mode else '#F0F2F5'};
            border: 1px solid rgba(0, 128, 255, 0.2);
            border-radius: 8px;
            padding: 6px 10px;
            color: {text};
        }}
        QLineEdit:focus, QTextEdit:focus, QComboBox:focus {{
            border: 1px solid {ACCENT};
            outline: none;
        }}
        QComboBox::drop-down {{
            border: none;
        }}
        QComboBox:focus {{
            background-color: {surface};
        }}
        QComboBox::down-arrow {{
            image: none;
            border: none;
        }}
        QComboBox QAbstractItemView {{
            background-color: {surface};
            color: {text};
            border: 1px solid rgba(0, 128, 255, 0.3);
            selection-background-color: rgba(0, 128, 255, 0.2);
            selection-color: {text};
            outline: none;
        }}
        QTabWidget::tab-bar {{
            left: 0px;
        }}
        QCheckBox {{
            spacing: 6px;
        }}
        """
    )

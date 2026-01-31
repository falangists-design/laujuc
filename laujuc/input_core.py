"""Input core: simulation, profiling, and scenarios."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import ctypes
import logging
import time
import platform
from typing import Callable


LOGGER = logging.getLogger(__name__)


class MouseButton(str, Enum):
    LEFT = "left"
    RIGHT = "right"
    MIDDLE = "middle"
    X1 = "x1"
    X2 = "x2"


@dataclass
class InputEvent:
    timestamp: float
    event_type: str
    payload: dict


@dataclass
class InputProfile:
    name: str
    events: list[InputEvent] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def summary(self) -> dict:
        duration = (self.events[-1].timestamp - self.events[0].timestamp) if self.events else 0
        return {
            "name": self.name,
            "total_events": len(self.events),
            "duration_seconds": round(duration, 2),
        }


class InputCore:
    def __init__(self) -> None:
        self.platform = platform.system().lower()

    def click_mouse(self, button: MouseButton) -> None:
        LOGGER.info("Click mouse: %s", button)
        if self.platform != "windows":
            LOGGER.warning("Mouse click simulation is stubbed on %s", self.platform)
            return
        self._windows_click(button)

    def press_key(self, key: str) -> None:
        LOGGER.info("Press key: %s", key)
        if self.platform != "windows":
            LOGGER.warning("Key press simulation is stubbed on %s", self.platform)
            return
        self._windows_key(key, True)

    def release_key(self, key: str) -> None:
        LOGGER.info("Release key: %s", key)
        if self.platform != "windows":
            LOGGER.warning("Key release simulation is stubbed on %s", self.platform)
            return
        self._windows_key(key, False)

    def type_text(self, text: str, delay: float = 0.01) -> None:
        for char in text:
            self.press_key(char)
            self.release_key(char)
            time.sleep(delay)

    def _windows_click(self, button: MouseButton) -> None:
        flags = {
            MouseButton.LEFT: (0x0002, 0x0004),
            MouseButton.RIGHT: (0x0008, 0x0010),
            MouseButton.MIDDLE: (0x0020, 0x0040),
            MouseButton.X1: (0x0080, 0x0100),
            MouseButton.X2: (0x0080, 0x0100),
        }
        down, up = flags[button]

        class INPUT(ctypes.Structure):
            _fields_ = [("type", ctypes.c_ulong), ("mi", ctypes.c_ulong * 6)]

        def send(flag: int) -> None:
            mi = (ctypes.c_ulong * 6)(0, 0, 0, flag, 0, 0)
            inp = INPUT(0, mi)
            ctypes.windll.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))

        send(down)
        send(up)

    def _windows_key(self, key: str, key_down: bool) -> None:
        vk = ord(key.upper()) if len(key) == 1 else 0
        if vk == 0:
            LOGGER.warning("Unknown key mapping for %s", key)
            return
        flag = 0 if key_down else 0x0002

        class INPUT(ctypes.Structure):
            _fields_ = [("type", ctypes.c_ulong), ("ki", ctypes.c_ulong * 6)]

        ki = (ctypes.c_ulong * 6)(vk, 0, flag, 0, 0, 0)
        inp = INPUT(1, ki)
        ctypes.windll.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))


class ScenarioAction(Enum):
    CLICK = "click"
    KEY_PRESS = "key_press"
    KEY_RELEASE = "key_release"
    PAUSE = "pause"


@dataclass
class AutomationScenario:
    name: str
    actions: list[dict] = field(default_factory=list)

    def add_action(self, action: ScenarioAction, payload: dict) -> None:
        self.actions.append({"action": action.value, "payload": payload})

    def play(self, engine: InputCore, delay: float = 0.05) -> None:
        for action in self.actions:
            action_type = action["action"]
            payload = action["payload"]
            if action_type == ScenarioAction.CLICK.value:
                engine.click_mouse(MouseButton(payload.get("button", "left")))
            elif action_type == ScenarioAction.KEY_PRESS.value:
                engine.press_key(payload.get("key", ""))
            elif action_type == ScenarioAction.KEY_RELEASE.value:
                engine.release_key(payload.get("key", ""))
            elif action_type == ScenarioAction.PAUSE.value:
                time.sleep(payload.get("seconds", 0))
            time.sleep(delay)


class InputProfiler:
    def __init__(self) -> None:
        self.active_profile: InputProfile | None = None

    def start(self, name: str) -> None:
        self.active_profile = InputProfile(name=name)

    def record(self, event_type: str, payload: dict) -> None:
        if not self.active_profile:
            return
        event = InputEvent(timestamp=time.time(), event_type=event_type, payload=payload)
        self.active_profile.events.append(event)

    def stop(self) -> InputProfile | None:
        profile = self.active_profile
        self.active_profile = None
        return profile


class IntegrationBridge:
    def to_selenium_script(self, scenario: AutomationScenario) -> str:
        lines = ["from selenium.webdriver import ActionChains", "", "actions = ActionChains(driver)"]
        for action in scenario.actions:
            if action["action"] == ScenarioAction.CLICK.value:
                lines.append("actions.click()")
            elif action["action"] == ScenarioAction.KEY_PRESS.value:
                key = action["payload"].get("key", "")
                lines.append(f"actions.key_down('{key}')")
            elif action["action"] == ScenarioAction.KEY_RELEASE.value:
                key = action["payload"].get("key", "")
                lines.append(f"actions.key_up('{key}')")
        lines.append("actions.perform()")
        return "\n".join(lines)

    def to_appium_script(self, scenario: AutomationScenario) -> str:
        return "\n".join(
            [
                "# Appium integration placeholder",
                f"# Scenario: {scenario.name}",
                "# Convert actions to TouchAction or W3C Actions here.",
            ]
        )


class ScenarioRecorder:
    def __init__(self, on_event: Callable[[InputEvent], None] | None = None) -> None:
        self.is_recording = False
        self.events: list[InputEvent] = []
        self._on_event = on_event

    def start(self) -> None:
        self.is_recording = True
        self.events.clear()

    def stop(self) -> list[InputEvent]:
        self.is_recording = False
        return list(self.events)

    def capture(self, event_type: str, payload: dict) -> None:
        if not self.is_recording:
            return
        event = InputEvent(timestamp=time.time(), event_type=event_type, payload=payload)
        self.events.append(event)
        if self._on_event:
            self._on_event(event)

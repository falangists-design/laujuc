"""Settings manager for laujuc."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import json
import os
import xml.etree.ElementTree as ET


DEFAULT_CONFIG_NAME = "settings.json"


@dataclass
class LaujucSettings:
    hotkey_toggle: str = "Insert"
    cps: int = 10
    hold_mode: bool = True
    target_process: str = ""
    left_button_enabled: bool = True
    right_button_enabled: bool = False
    middle_button_enabled: bool = False
    play_sound: bool = True


class SettingsManager:
    def __init__(self, app_name: str = "laujuc") -> None:
        self.app_name = app_name
        self.base_path = self._resolve_base_path()
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.settings_path = self.base_path / DEFAULT_CONFIG_NAME

    def _resolve_base_path(self) -> Path:
        if os.name == "nt":
            root = Path(os.environ.get("APPDATA", Path.home()))
        else:
            root = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
        return root / self.app_name

    def load(self) -> LaujucSettings:
        if not self.settings_path.exists():
            return LaujucSettings()
        with self.settings_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        return LaujucSettings(**data)

    def save(self, settings: LaujucSettings) -> None:
        with self.settings_path.open("w", encoding="utf-8") as handle:
            json.dump(asdict(settings), handle, indent=2)

    def export_xml(self, settings: LaujucSettings, target: Path) -> None:
        root = ET.Element("laujuc_settings")
        for key, value in asdict(settings).items():
            child = ET.SubElement(root, key)
            child.text = str(value)
        tree = ET.ElementTree(root)
        tree.write(target, encoding="utf-8", xml_declaration=True)

    def import_xml(self, source: Path) -> LaujucSettings:
        tree = ET.parse(source)
        root = tree.getroot()
        data: dict[str, str] = {child.tag: child.text or "" for child in root}
        normalized = {
            "hotkey_toggle": data.get("hotkey_toggle", "Insert"),
            "cps": int(data.get("cps", 10)),
            "hold_mode": data.get("hold_mode", "True") == "True",
            "target_process": data.get("target_process", ""),
            "left_button_enabled": data.get("left_button_enabled", "True") == "True",
            "right_button_enabled": data.get("right_button_enabled", "False") == "True",
            "middle_button_enabled": data.get("middle_button_enabled", "False") == "True",
            "play_sound": data.get("play_sound", "True") == "True",
        }
        return LaujucSettings(**normalized)

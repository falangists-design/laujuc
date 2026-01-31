"""Settings manager for laujuc."""

from __future__ import annotations

from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import os
import uuid
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
    auth_enabled: bool = True
    activation_key: str = ""
    activation_valid_until: str = ""
    known_keys: list[str] = field(default_factory=list)
    theme: str = "dark"
    activation_session_minutes: int = 10080


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
        try:
            known_keys = json.loads(data.get("known_keys", "[]"))
        except json.JSONDecodeError:
            known_keys = []
        normalized = {
            "hotkey_toggle": data.get("hotkey_toggle", "Insert"),
            "cps": int(data.get("cps", 10)),
            "hold_mode": data.get("hold_mode", "True") == "True",
            "target_process": data.get("target_process", ""),
            "left_button_enabled": data.get("left_button_enabled", "True") == "True",
            "right_button_enabled": data.get("right_button_enabled", "False") == "True",
            "middle_button_enabled": data.get("middle_button_enabled", "False") == "True",
            "play_sound": data.get("play_sound", "True") == "True",
            "auth_enabled": data.get("auth_enabled", "True") == "True",
            "activation_key": data.get("activation_key", ""),
            "activation_valid_until": data.get("activation_valid_until", ""),
            "known_keys": known_keys,
            "theme": data.get("theme", "dark"),
            "activation_session_minutes": int(data.get("activation_session_minutes", 10080)),
        }
        return LaujucSettings(**normalized)

    def generate_one_time_key(self, settings: LaujucSettings) -> str:
        key = uuid.uuid4().hex.upper()
        while key in settings.known_keys:
            key = uuid.uuid4().hex.upper()
        settings.known_keys.append(key)
        settings.activation_key = key
        return key

    def activate_key(self, settings: LaujucSettings, key: str) -> bool:
        if key in settings.known_keys:
            settings.activation_key = key
            expires_at = datetime.now(tz=timezone.utc) + timedelta(
                minutes=settings.activation_session_minutes
            )
            settings.activation_valid_until = expires_at.isoformat()
            return True
        return False

    def is_activation_valid(self, settings: LaujucSettings) -> bool:
        if not settings.activation_valid_until:
            return False
        try:
            expires_at = datetime.fromisoformat(settings.activation_valid_until)
        except ValueError:
            return False
        return datetime.now(tz=timezone.utc) < expires_at

    def export_keys(self, settings: LaujucSettings, target: Path) -> None:
        payload = {
            "known_keys": settings.known_keys,
            "activation_session_minutes": settings.activation_session_minutes,
        }
        target.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def import_keys(self, settings: LaujucSettings, source: Path) -> None:
        payload = json.loads(source.read_text(encoding="utf-8"))
        keys = payload.get("known_keys", [])
        session_minutes = payload.get("activation_session_minutes")
        for key in keys:
            if key not in settings.known_keys:
                settings.known_keys.append(key)
        if isinstance(session_minutes, int):
            settings.activation_session_minutes = session_minutes

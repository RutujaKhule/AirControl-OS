import json
import os
import sys
from copy import deepcopy
from dataclasses import asdict, is_dataclass
from typing import Any, Dict, Optional, Type

from .config import AppConfig, GestureConfig, VoiceConfig, CONFIG, GESTURE_CONFIG, VOICE_CONFIG


def _app_data_dir() -> str:
    if sys.platform.startswith("win"):
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        if not base:
            base = os.path.expanduser("~")
        return os.path.join(base, "AirControl OS")
    if sys.platform == "darwin":
        return os.path.join(os.path.expanduser("~"), "Library", "Application Support", "AirControl OS")
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")
    return os.path.join(base, "aircontrol-os")


SETTINGS_DIR = _app_data_dir()
SETTINGS_PATH = os.path.join(SETTINGS_DIR, "settings.json")


def _field_types(dc: Any) -> Dict[str, type]:
    if not is_dataclass(dc):
        raise TypeError("Expected a dataclass instance")
    types: Dict[str, type] = {}
    for field_name, field_def in dc.__dataclass_fields__.items():
        types[field_name] = field_def.type
    return types


def _coerce_value(value: Any, target_type: type) -> Optional[Any]:
    if value is None:
        return None
    origin = getattr(target_type, "__origin__", None)
    args = getattr(target_type, "__args__", ())
    try:
        if origin is tuple:
            if isinstance(value, (list, tuple)):
                out = []
                for i, v in enumerate(value):
                    sub_type = args[i] if i < len(args) else type(v)
                    out.append(sub_type(v))
                return tuple(out)
            return None
        return target_type(value)
    except (TypeError, ValueError):
        return None


def _merge_into_dataclass(dc_instance: Any, raw: Dict[str, Any]) -> None:
    if not is_dataclass(dc_instance):
        return
    types = _field_types(dc_instance)
    for key, raw_value in raw.items():
        if key not in types:
            continue
        coerced = _coerce_value(raw_value, types[key])
        if coerced is None and raw_value is not None:
            try:
                coerced = types[key](raw_value)
            except Exception:
                continue
        if coerced is None:
            continue
        setattr(dc_instance, key, coerced)


def to_flat_dict() -> Dict[str, Any]:
    d: Dict[str, Any] = {}
    d["app"] = asdict(CONFIG)
    d["gesture"] = asdict(GESTURE_CONFIG)
    d["voice"] = asdict(VOICE_CONFIG)
    return d


def apply_flat_dict(data: Dict[str, Any]) -> None:
    if isinstance(data.get("app"), dict):
        _merge_into_dataclass(CONFIG, data["app"])
    if isinstance(data.get("gesture"), dict):
        _merge_into_dataclass(GESTURE_CONFIG, data["gesture"])
    if isinstance(data.get("voice"), dict):
        _merge_into_dataclass(VOICE_CONFIG, data["voice"])


def ensure_dir() -> str:
    if not os.path.isdir(SETTINGS_DIR):
        os.makedirs(SETTINGS_DIR, exist_ok=True)
    return SETTINGS_DIR


def save_settings(extra: Optional[Dict[str, Any]] = None) -> str:
    ensure_dir()
    payload = to_flat_dict()
    if isinstance(extra, dict):
        for k, v in extra.items():
            payload[k] = v
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=True)
    return SETTINGS_PATH


def load_settings() -> Dict[str, Any]:
    if not os.path.isfile(SETTINGS_PATH):
        return {}
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def load_and_apply() -> Dict[str, Any]:
    data = load_settings()
    apply_flat_dict(data)
    return data


def reset_defaults() -> None:
    for k, v in _field_defaults(AppConfig).items():
        setattr(CONFIG, k, v)
    for k, v in _field_defaults(GestureConfig).items():
        setattr(GESTURE_CONFIG, k, v)
    for k, v in _field_defaults(VoiceConfig).items():
        setattr(VOICE_CONFIG, k, v)
    if os.path.isfile(SETTINGS_PATH):
        try:
            os.remove(SETTINGS_PATH)
        except Exception:
            pass


def _field_defaults(dc_type: Type[Any]) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for name, field_def in dc_type.__dataclass_fields__.items():
        if field_def.default is not type(field_def):
            result[name] = deepcopy(field_def.default)
        elif field_def.default_factory is not type(field_def.default_factory):
            result[name] = field_def.default_factory()
    return result

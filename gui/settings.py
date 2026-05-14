"""Persistent user settings (resolution, display mode, auto-equip).

Stored as a small JSON file at the project root so settings survive across
runs without touching the version-controlled ``config.py``.
"""

from __future__ import annotations

import json
from pathlib import Path


RESOLUTIONS: list[tuple[int, int]] = [
    (1024, 640),
    (1280, 800),
    (1366, 768),
    (1440, 900),
    (1600, 900),
    (1600, 1000),
    (1680, 1050),
    (1920, 1080),
    (1920, 1200),
    (2048, 1152),
    (2304, 1440),
    (2500, 1600),
    (2560, 1440),
    (2560, 1600),
]

DISPLAY_MODES: tuple[str, ...] = ("windowed", "borderless", "fullscreen")

DEFAULT_SETTINGS: dict = {
    "resolution": [1280, 800],
    "fullscreen": False,
    "display_mode": "windowed",
    "auto_equip_gear": True,
}


def _settings_path() -> Path:
    return Path(__file__).resolve().parent.parent / "settings.json"


def load_settings() -> dict:
    path = _settings_path()
    if not path.exists():
        return dict(DEFAULT_SETTINGS)
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return dict(DEFAULT_SETTINGS)

    if not isinstance(data, dict):
        return dict(DEFAULT_SETTINGS)

    merged = dict(DEFAULT_SETTINGS)
    merged.update({k: v for k, v in data.items() if k in DEFAULT_SETTINGS})

    res = merged.get("resolution")
    if (
        not isinstance(res, (list, tuple))
        or len(res) != 2
        or not all(isinstance(n, int) and n > 0 for n in res)
    ):
        merged["resolution"] = list(DEFAULT_SETTINGS["resolution"])
    else:
        merged["resolution"] = [int(res[0]), int(res[1])]

    merged["fullscreen"] = bool(merged.get("fullscreen", False))
    merged["auto_equip_gear"] = bool(merged.get("auto_equip_gear", True))

    if "display_mode" not in data:
        merged["display_mode"] = "fullscreen" if merged["fullscreen"] else "windowed"
    else:
        dm = merged.get("display_mode")
        if not isinstance(dm, str) or dm not in DISPLAY_MODES:
            merged["display_mode"] = "fullscreen" if merged["fullscreen"] else "windowed"
    merged["fullscreen"] = merged["display_mode"] == "fullscreen"
    return merged


def save_settings(data: dict) -> None:
    payload = dict(DEFAULT_SETTINGS)
    payload.update({k: v for k, v in data.items() if k in DEFAULT_SETTINGS})
    res = payload.get("resolution") or DEFAULT_SETTINGS["resolution"]
    payload["resolution"] = [int(res[0]), int(res[1])]
    dm = payload.get("display_mode")
    if dm not in DISPLAY_MODES:
        dm = "windowed"
    payload["display_mode"] = dm
    payload["fullscreen"] = dm == "fullscreen"
    payload["auto_equip_gear"] = bool(payload.get("auto_equip_gear", True))
    path = _settings_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
    except OSError:
        pass


def current_resolution(settings: dict) -> tuple[int, int]:
    res = settings.get("resolution") or DEFAULT_SETTINGS["resolution"]
    return (int(res[0]), int(res[1]))

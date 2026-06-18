"""Tests for gui.settings resolution defaults."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from gui import settings as gui_settings


def _mock_display_info(monkeypatch: pytest.MonkeyPatch, width: int, height: int) -> None:
    monkeypatch.setattr(
        "gui.settings.pygame.display.Info",
        lambda: SimpleNamespace(current_w=width, current_h=height),
    )


def test_first_run_uses_desktop_resolution(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    missing = tmp_path / "settings.json"
    monkeypatch.setattr(gui_settings, "_settings_path", lambda: missing)
    _mock_display_info(monkeypatch, 1920, 1080)

    loaded = gui_settings.load_settings()

    assert loaded["resolution"] == [1920, 1080]


def test_saved_settings_keep_resolution(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    path = tmp_path / "settings.json"
    path.write_text(
        json.dumps({"resolution": [1280, 800], "display_mode": "windowed"}),
        encoding="utf-8",
    )
    monkeypatch.setattr(gui_settings, "_settings_path", lambda: path)
    _mock_display_info(monkeypatch, 3840, 2160)

    loaded = gui_settings.load_settings()

    assert loaded["resolution"] == [1280, 800]


def test_desktop_fallback_when_invalid_size(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    missing = tmp_path / "settings.json"
    monkeypatch.setattr(gui_settings, "_settings_path", lambda: missing)
    _mock_display_info(monkeypatch, 0, 0)

    loaded = gui_settings.load_settings()

    assert loaded["resolution"] == list(gui_settings.DEFAULT_SETTINGS["resolution"])


def test_resolution_choices_includes_current() -> None:
    current = (3440, 1440)
    choices = gui_settings.resolution_choices(current)

    assert current in choices
    assert choices == sorted(choices, key=lambda size: (size[0], size[1]))

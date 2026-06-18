from __future__ import annotations

from unittest.mock import MagicMock, patch

from gui import clipboard


def test_copy_text_returns_false_on_failure() -> None:
    with patch.object(clipboard.pygame.scrap, "put", side_effect=RuntimeError("no clipboard")):
        assert clipboard.copy_text("goblin") is False


def test_paste_text_returns_empty_on_failure() -> None:
    with patch.object(clipboard.pygame.scrap, "get", side_effect=RuntimeError("no clipboard")):
        assert clipboard.paste_text() == ""


def test_copy_and_paste_round_trip() -> None:
    store: dict[str, bytes] = {}

    def put(_fmt: str, data: bytes) -> None:
        store["text"] = data

    def get(_fmt: str) -> bytes:
        return store.get("text", b"")

    scrap = MagicMock()
    scrap.put = put
    scrap.get = get
    with patch.object(clipboard.pygame, "scrap", scrap), patch.object(
        clipboard.pygame, "SCRAP_TEXT", "text/plain"
    ):
        assert clipboard.copy_text("iron key") is True
        assert clipboard.paste_text() == "iron key"

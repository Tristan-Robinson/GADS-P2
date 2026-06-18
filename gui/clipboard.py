"""System clipboard helpers via pygame.scrap."""

from __future__ import annotations

import pygame


def init_clipboard() -> None:
    try:
        pygame.scrap.init()
    except Exception:  # pragma: no cover - clipboard optional
        pass


def copy_text(text: str) -> bool:
    try:
        pygame.scrap.put(pygame.SCRAP_TEXT, text.encode("utf-8"))
        return True
    except Exception:  # pragma: no cover
        return False


def paste_text() -> str:
    try:
        raw = pygame.scrap.get(pygame.SCRAP_TEXT)
        if not raw:
            return ""
        return raw.decode("utf-8", errors="ignore")
    except Exception:  # pragma: no cover
        return ""

from __future__ import annotations

from unittest.mock import patch

import pygame
from pygame.event import Event

from gui import widgets
from gui.widgets import InputBox, NarrationPanel


def test_drag_exceeded_below_threshold() -> None:
    assert widgets._drag_exceeded((0, 0), (3, 3), 6) is False


def test_drag_exceeded_above_threshold() -> None:
    assert widgets._drag_exceeded((0, 0), (10, 0), 6) is True


def test_insert_fragment_at_places_text_at_click() -> None:
    pygame.init()
    font = pygame.font.SysFont("arial", 16)
    box = InputBox(pygame.Rect(0, 0, 400, 40), font, font)
    box.text = "attack "
    box._cursor = len(box.text)
    area = box._text_area_rect()
    click_x = area.left + font.size("attack")[0] + 4
    assert box.insert_fragment_at("goblin", (click_x, area.centery)) is True
    assert "goblin" in box.text
    assert box.text.startswith("attack")


def test_insert_fragment_with_explicit_cursor() -> None:
    pygame.init()
    font = pygame.font.SysFont("arial", 16)
    box = InputBox(pygame.Rect(0, 0, 400, 40), font, font)
    box.text = "go north"
    box.insert_fragment("east ", cursor=3)
    assert box.text == "go east north"
    assert box._cursor == len("go east ")


def test_context_menu_paste_inserts_clipboard_text() -> None:
    pygame.init()
    font = pygame.font.SysFont("arial", 16)
    box = InputBox(pygame.Rect(0, 0, 400, 40), font, font)
    box.text = "look "
    box._cursor = len(box.text)

    box._open_menu((box.rect.centerx, box.rect.centery))
    assert box._menu_open is True
    assert box._menu_item_rect is not None

    with patch("gui.widgets.paste_text", return_value="goblin"):
        box.handle_event(Event(pygame.MOUSEBUTTONDOWN, {"pos": box._menu_item_rect.center, "button": 1}))

    assert box.text == "look goblin"
    assert box._menu_open is False


def test_finish_pointer_returns_text_on_click_release() -> None:
    pygame.init()
    font = pygame.font.SysFont("arial", 16)
    panel = NarrationPanel(pygame.Rect(0, 0, 400, 300), font, font)
    panel._start_pointer((10, 10), "key")
    text = panel.finish_pointer(Event(pygame.MOUSEBUTTONUP, {"pos": (10, 10), "button": 1}))
    assert text == "key"
    assert panel.pointer_was_click() is True
    assert panel.pointer_active() is False


def test_finish_pointer_marks_drag_when_moved() -> None:
    pygame.init()
    font = pygame.font.SysFont("arial", 16)
    panel = NarrationPanel(pygame.Rect(0, 0, 400, 300), font, font)
    panel._start_pointer((0, 0), "torch")
    panel._dragging = True
    text = panel.finish_pointer(Event(pygame.MOUSEBUTTONUP, {"pos": (80, 40), "button": 1}))
    assert text == "torch"
    assert panel.pointer_was_click() is False

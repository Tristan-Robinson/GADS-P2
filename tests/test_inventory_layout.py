from __future__ import annotations

import pygame

from gui.inventory_overlay import (
    NAME_SUMMARY_GAP,
    ROW_GAP,
    ROW_H,
    ROW_PAD_Y,
    ROW_STRIDE,
    _row_index_from_click,
    _row_rect,
)


def _inventory_fonts() -> dict[str, pygame.font.Font]:
    return {
        "body": pygame.font.SysFont("georgia", 25),
        "caption": pygame.font.SysFont("verdana", 15),
    }


def test_row_h_fits_name_and_summary() -> None:
    pygame.init()
    fonts = _inventory_fonts()
    name_h = fonts["body"].get_height()
    summary_h = fonts["caption"].get_height()
    content_h = ROW_PAD_Y + name_h + NAME_SUMMARY_GAP + summary_h
    assert content_h <= ROW_H


def test_row_rect_stride_leaves_gap_between_rows() -> None:
    list_rect = pygame.Rect(10, 20, 300, 400)
    row0 = _row_rect(list_rect, 0)
    row1 = _row_rect(list_rect, 1)
    assert row1.top - row0.bottom == ROW_GAP
    assert row1.top - row0.top == ROW_STRIDE


def test_row_index_from_click_hits_row_not_gap() -> None:
    list_rect = pygame.Rect(0, 100, 280, 300)
    row0_mid = list_rect.top + ROW_H // 2
    row1_mid = list_rect.top + ROW_STRIDE + ROW_H // 2
    gap_y = list_rect.top + ROW_H + ROW_GAP // 2

    assert _row_index_from_click(list_rect, row0_mid) == 0
    assert _row_index_from_click(list_rect, row1_mid) == 1
    assert _row_index_from_click(list_rect, gap_y) is None

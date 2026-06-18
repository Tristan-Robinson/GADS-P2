from __future__ import annotations

from gui.input_text import (
    INPUT_MAX_LEN,
    clamp_cursor,
    delete_after,
    delete_before,
    insert_at,
    move_cursor,
)


def test_clamp_cursor() -> None:
    assert clamp_cursor(-3, 5) == 0
    assert clamp_cursor(10, 5) == 5
    assert clamp_cursor(2, 5) == 2


def test_insert_at_middle() -> None:
    text, cursor = insert_at("hello world", 6, "brave ")
    assert text == "hello brave world"
    assert cursor == 12


def test_insert_at_respects_max_len() -> None:
    base = "a" * INPUT_MAX_LEN
    text, cursor = insert_at(base, INPUT_MAX_LEN, "more")
    assert text == base
    assert cursor == INPUT_MAX_LEN


def test_delete_before_and_after() -> None:
    text, cursor = delete_before("abcd", 2)
    assert text == "acd"
    assert cursor == 1
    text, cursor = delete_after("abcd", 2)
    assert text == "abd"
    assert cursor == 2


def test_move_cursor_bounds() -> None:
    assert move_cursor(0, 4, -1) == 0
    assert move_cursor(3, 4, 5) == 4


def test_paste_strips_newlines() -> None:
    text, cursor = insert_at("go ", 3, "north\nsouth")
    assert text == "go north south"
    assert cursor == len("go north south")

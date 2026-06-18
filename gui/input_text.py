"""Pure text-editing helpers for the command input bar."""

from __future__ import annotations

INPUT_MAX_LEN = 200


def clamp_cursor(cursor: int, text_len: int) -> int:
    return max(0, min(cursor, text_len))


def insert_at(text: str, cursor: int, fragment: str, max_len: int = INPUT_MAX_LEN) -> tuple[str, int]:
    cursor = clamp_cursor(cursor, len(text))
    cleaned = fragment.replace("\n", " ").replace("\r", " ")
    if not cleaned:
        return text, cursor
    room = max_len - len(text)
    if room <= 0:
        return text, cursor
    cleaned = cleaned[:room]
    new_text = text[:cursor] + cleaned + text[cursor:]
    return new_text, cursor + len(cleaned)


def delete_before(text: str, cursor: int) -> tuple[str, int]:
    cursor = clamp_cursor(cursor, len(text))
    if cursor <= 0:
        return text, 0
    return text[: cursor - 1] + text[cursor:], cursor - 1


def delete_after(text: str, cursor: int) -> tuple[str, int]:
    cursor = clamp_cursor(cursor, len(text))
    if cursor >= len(text):
        return text, cursor
    return text[:cursor] + text[cursor + 1 :], cursor


def move_cursor(cursor: int, text_len: int, delta: int) -> int:
    return clamp_cursor(cursor + delta, text_len)

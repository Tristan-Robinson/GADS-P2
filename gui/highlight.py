"""Client-side keyword highlighting for narration text.

The narrator returns plain prose; this module turns that prose into a list of
coloured spans based on entities known to the current ``GameState``. Doing the
work on the client (rather than asking the LLM to tag tokens) makes the
highlights deterministic and robust against narration drift.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from game.models import GameState


Color = tuple[int, int, int]


@dataclass(frozen=True)
class Span:
    text: str
    color: Color


DEFAULT: Color = (235, 230, 220)
ENEMY: Color = (255, 110, 110)
ITEM: Color = (255, 210, 110)
INVENTORY: Color = (255, 235, 175)
DIRECTION: Color = (140, 220, 255)
DAMAGE: Color = (255, 235, 120)
LOCK: Color = (220, 170, 255)
ROOM: Color = (255, 255, 255)


DIRECTION_WORDS: tuple[str, ...] = (
    "north",
    "south",
    "east",
    "west",
    "door",
    "doorway",
    "exit",
    "gate",
    "stair",
    "stairs",
    "arch",
    "archway",
    "vault",
)

DAMAGE_WORDS: tuple[str, ...] = (
    "damage",
    "HP",
    "hp",
    "heal",
    "heals",
    "healed",
    "health",
    "wound",
    "wounds",
    "recover",
    "recovers",
    "recovered",
    "strike",
    "strikes",
    "attack",
    "attacks",
    "defeat",
    "defeats",
    "defeated",
)

LOCK_WORDS: tuple[str, ...] = (
    "locked",
    "unlocked",
    "unlock",
    "unlocks",
    "lock",
    "key",
)


def _add(
    matches: list[tuple[int, int, Color, int]],
    pattern: re.Pattern[str],
    text: str,
    color: Color,
    priority: int,
) -> None:
    for m in pattern.finditer(text):
        if m.end() > m.start():
            matches.append((m.start(), m.end(), color, priority))


def _word(literal: str) -> re.Pattern[str]:
    return re.compile(rf"\b{re.escape(literal)}\b", re.IGNORECASE)


def highlight(text: str, state: GameState | None) -> list[Span]:
    """Return ``text`` split into colored spans driven by current entities."""

    if not text:
        return []

    matches: list[tuple[int, int, Color, int]] = []
    seen_literals: set[str] = set()

    if state is not None:
        room = state.current_room()
        for enemy in room.enemies:
            literal = enemy.name.lower()
            if literal in seen_literals:
                continue
            seen_literals.add(literal)
            _add(matches, _word(enemy.name), text, ENEMY, 6)
        for item in room.items:
            literal = item.name.lower()
            if literal in seen_literals:
                continue
            seen_literals.add(literal)
            _add(matches, _word(item.name), text, ITEM, 5)
        for item in state.player.inventory:
            literal = item.name.lower()
            if literal in seen_literals:
                continue
            seen_literals.add(literal)
            _add(matches, _word(item.name), text, INVENTORY, 5)
        for known in state.rooms.values():
            literal = known.name.lower()
            if literal in seen_literals:
                continue
            seen_literals.add(literal)
            _add(matches, _word(known.name), text, ROOM, 4)

    for word in LOCK_WORDS:
        _add(matches, _word(word), text, LOCK, 3)
    for word in DAMAGE_WORDS:
        _add(matches, _word(word), text, DAMAGE, 3)
    for word in DIRECTION_WORDS:
        _add(matches, _word(word), text, DIRECTION, 2)

    _add(matches, re.compile(r"\b\d+\b"), text, DAMAGE, 1)

    if not matches:
        return [Span(text, DEFAULT)]

    matches.sort(key=lambda m: (m[0], -(m[1] - m[0]), -m[3]))
    chosen: list[tuple[int, int, Color]] = []
    last_end = 0
    for start, end, color, _priority in matches:
        if start < last_end:
            continue
        chosen.append((start, end, color))
        last_end = end

    spans: list[Span] = []
    cursor = 0
    for start, end, color in chosen:
        if cursor < start:
            spans.append(Span(text[cursor:start], DEFAULT))
        spans.append(Span(text[start:end], color))
        cursor = end
    if cursor < len(text):
        spans.append(Span(text[cursor:], DEFAULT))
    return spans


def split_paragraphs(text: str) -> Iterable[str]:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            yield stripped

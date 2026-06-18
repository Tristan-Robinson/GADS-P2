"""Natural-language imperative parsing for player commands."""

from __future__ import annotations

import re

from game.actions import ActionType, PlayerAction
from game.engine import normalize_direction
from game.targeting import normalize_target_name

_COMBINE_LINE = re.compile(r"^combine\s+.+\s+and\s+.+", re.IGNORECASE)
_SPLIT_DELIMITERS = re.compile(r"(?:;|\n|\s+and then\s+|\s+then\s+)", re.IGNORECASE)

_POLITE_PREFIXES = (
    "please ",
    "i want to ",
    "i'd like to ",
    "id like to ",
    "let me ",
    "could i ",
    "can i ",
    "i will ",
    "i'll ",
    "ill ",
    "maybe ",
)

_TAKE_VERBS = (
    "pick up",
    "pick",
    "take",
    "grab",
    "get",
    "collect",
    "loot",
    "swipe",
    "snatch",
)

_MOVE_VERBS = (
    "go",
    "walk",
    "run",
    "move",
    "head",
    "step",
    "travel",
    "sprint",
    "hurry",
)

_USE_VERBS = (
    "use",
    "drink",
    "quaff",
    "apply",
    "equip",
)

_ATTACK_VERBS = (
    "attack",
    "fight",
    "hit",
    "strike",
    "kill",
)

_LOOK_VERBS = (
    "look",
    "examine",
    "inspect",
    "search",
)


def strip_polite_prefix(text: str) -> str:
    lowered = text.strip().lower()
    changed = True
    while changed:
        changed = False
        for prefix in _POLITE_PREFIXES:
            if lowered.startswith(prefix):
                lowered = lowered[len(prefix) :].strip()
                changed = True
    return lowered


def split_player_commands(text: str) -> list[str]:
    """Split compound player input into individual commands."""

    stripped = text.strip()
    if not stripped:
        return []
    if _COMBINE_LINE.match(stripped):
        return [stripped]
    parts = _SPLIT_DELIMITERS.split(stripped)
    return [part.strip() for part in parts if part.strip()]


def _strip_articles(rest: str) -> str:
    return normalize_target_name(rest)


def _match_verb_prefix(text: str, verbs: tuple[str, ...]) -> tuple[str, str] | None:
    for verb in sorted(verbs, key=len, reverse=True):
        if text == verb:
            return verb, ""
        prefix = verb + " "
        if text.startswith(prefix):
            return verb, text[len(prefix) :].strip()
    return None


def _parse_take(rest: str) -> PlayerAction | None:
    if rest in {"all", "everything", "*"}:
        return PlayerAction(action=ActionType.TAKE, target="__ALL__")
    if rest.startswith("all ") or rest.startswith("everything "):
        return PlayerAction(action=ActionType.TAKE, target="__ALL__")
    if not rest:
        return None
    return PlayerAction(action=ActionType.TAKE, target=_strip_articles(rest))


def _parse_go(rest: str) -> PlayerAction | None:
    if not rest:
        return None
    for filler in ("to the ", "to ", "the "):
        if rest.startswith(filler):
            rest = rest[len(filler) :].strip()
            break
    direction = normalize_direction(rest)
    if direction in {"north", "south", "east", "west"}:
        return PlayerAction(action=ActionType.GO, direction=direction)
    return None


def parse_imperative(user_input: str) -> PlayerAction | None:
    text = strip_polite_prefix(user_input)
    if not text:
        return None

    if text in {"look", "l"}:
        return PlayerAction(action=ActionType.LOOK)

    look_match = _match_verb_prefix(text, _LOOK_VERBS)
    if look_match is not None:
        verb, rest = look_match
        if not rest or rest in {"around", "here"}:
            return PlayerAction(action=ActionType.LOOK)

    bare = normalize_direction(text)
    if bare in {"north", "south", "east", "west"}:
        return PlayerAction(action=ActionType.GO, direction=bare)

    move_match = _match_verb_prefix(text, _MOVE_VERBS)
    if move_match is not None:
        action = _parse_go(move_match[1])
        if action is not None:
            return action

    take_match = _match_verb_prefix(text, _TAKE_VERBS)
    if take_match is not None:
        action = _parse_take(take_match[1])
        if action is not None:
            return action

    use_match = _match_verb_prefix(text, _USE_VERBS)
    if use_match is not None:
        rest = use_match[1]
        if rest and " on " in rest:
            left, right = rest.split(" on ", 1)
            return PlayerAction(
                action=ActionType.COMBINE,
                target=_strip_articles(left),
                secondary_target=_strip_articles(right),
            )
        if rest:
            return PlayerAction(action=ActionType.USE, target=_strip_articles(rest))

    attack_match = _match_verb_prefix(text, _ATTACK_VERBS)
    if attack_match is not None:
        rest = attack_match[1]
        if rest:
            return PlayerAction(action=ActionType.ATTACK, target=_strip_articles(rest))

    return None

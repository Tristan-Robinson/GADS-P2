"""Shared fuzzy name matching for player command targets."""

from __future__ import annotations

from typing import Any, TypeVar

T = TypeVar("T")


def normalize_target_name(target: str) -> str:
    text = target.strip().lower().rstrip(".,!?")
    while True:
        stripped = False
        for prefix in ("the ", "a ", "an ", "my "):
            if text.startswith(prefix):
                text = text[len(prefix) :]
                stripped = True
        if not stripped:
            break
    return text.strip()


def fuzzy_find_entity(target: str, candidates: list[tuple[str, str, T]]) -> T | None:
    normalized = normalize_target_name(target)
    if not normalized:
        return None

    for cid, name, entity in candidates:
        if normalized == cid.lower() or normalized == name.lower():
            return entity

    substring_matches: list[tuple[int, T]] = []
    for _cid, name, entity in candidates:
        nl = name.lower()
        if normalized in nl or nl in normalized:
            substring_matches.append((len(nl), entity))
    if substring_matches:
        substring_matches.sort(key=lambda pair: -pair[0])
        return substring_matches[0][1]

    target_tokens = set(normalized.split())
    best: T | None = None
    best_score = 0
    for _cid, name, entity in candidates:
        overlap = len(target_tokens & set(name.lower().split()))
        if overlap > best_score:
            best_score = overlap
            best = entity
    if best_score > 0:
        return best
    return None


def entity_candidates(entities: list[Any]) -> list[tuple[str, str, Any]]:
    return [(e.id, e.name, e) for e in entities]

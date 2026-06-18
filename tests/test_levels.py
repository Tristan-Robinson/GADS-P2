from __future__ import annotations

import random

from game.levels import DUNGEON, generate_level


def test_feature_count_varies_by_room() -> None:
    counts: set[int] = set()
    for seed in range(80):
        rooms, _ = generate_level(2, random.Random(seed), theme=DUNGEON, force_first=False)
        for rid in ("entrance", "hall", "armory"):
            counts.add(len(rooms[rid].features))
    assert 0 in counts
    assert max(counts) >= 1


def test_feature_sets_differ_across_seeds() -> None:
    signatures: set[tuple[tuple[str, tuple[str, ...]], ...]] = set()
    for seed in range(60):
        rooms, _ = generate_level(3, random.Random(seed), theme=DUNGEON, force_first=False)
        sig = tuple(
            (rid, tuple(f.name for f in rooms[rid].features))
            for rid in ("entrance", "hall", "armory")
        )
        signatures.add(sig)
    assert len(signatures) >= 3

"""Backwards-compatible entry point for the initial level.

Level construction now lives in :mod:`game.levels`. This module remains so
existing imports and tests keep working unchanged.
"""

from __future__ import annotations

import random

from game.levels import initial_state
from game.models import GameState


def build_initial_state(seed: int | None = None) -> GameState:
    rng = random.Random(seed) if seed is not None else random.Random()
    return initial_state(rng)

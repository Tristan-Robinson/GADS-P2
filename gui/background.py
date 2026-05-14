"""Procedural per-theme background rendering.

No image assets ship with the game; each theme is built from its 3-colour
palette plus a static stone tile pattern and a slow drift of bright motes.
The static layer is rendered once per level and cached, so per-frame work
is limited to advancing and drawing a few dozen particles.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

import pygame

from game.levels import LevelTheme


Color = tuple[int, int, int]


@dataclass
class Mote:
    x: float
    y: float
    vx: float
    vy: float
    radius: float
    base_alpha: int
    phase: float


def _lerp(a: int, b: int, t: float) -> int:
    return int(a + (b - a) * t)


def _lerp_color(c1: Color, c2: Color, t: float) -> Color:
    return (_lerp(c1[0], c2[0], t), _lerp(c1[1], c2[1], t), _lerp(c1[2], c2[2], t))


def _vertical_gradient(size: tuple[int, int], top: Color, bottom: Color) -> pygame.Surface:
    width, height = size
    surface = pygame.Surface(size).convert()
    for y in range(height):
        t = y / max(1, height - 1)
        pygame.draw.line(surface, _lerp_color(top, bottom, t), (0, y), (width, y))
    return surface


def _stone_tiles(
    size: tuple[int, int],
    base: Color,
    rng: random.Random,
    tile: int = 64,
) -> pygame.Surface:
    width, height = size
    surface = pygame.Surface(size, pygame.SRCALPHA).convert_alpha()
    light = (min(255, base[0] + 22), min(255, base[1] + 22), min(255, base[2] + 22), 28)
    dark = (max(0, base[0] - 28), max(0, base[1] - 28), max(0, base[2] - 28), 70)
    for ty in range(-1, height // tile + 2):
        offset = (tile // 2) if ty % 2 else 0
        for tx in range(-1, width // tile + 2):
            x = tx * tile + offset
            y = ty * tile
            rect = pygame.Rect(x, y, tile - 2, tile - 2)
            pygame.draw.rect(surface, light, rect, 1, border_radius=4)
            for _ in range(2):
                speckx = x + rng.randint(4, tile - 6)
                specky = y + rng.randint(4, tile - 6)
                pygame.draw.circle(surface, dark, (speckx, specky), rng.randint(1, 2))
    vignette = pygame.Surface(size, pygame.SRCALPHA).convert_alpha()
    for i in range(80):
        alpha = int(2 + i * 1.5)
        pygame.draw.rect(
            vignette,
            (0, 0, 0, alpha),
            pygame.Rect(i, i, width - i * 2, height - i * 2),
            1,
        )
    surface.blit(vignette, (0, 0))
    return surface


class ThemeBackground:
    def __init__(
        self,
        theme: LevelTheme,
        size: tuple[int, int],
        *,
        seed: int | None = None,
    ) -> None:
        self.theme = theme
        self.size = size
        self._rng = random.Random(seed)
        deep, mid, accent = theme.palette
        self._gradient = _vertical_gradient(size, deep, mid)
        self._tiles = _stone_tiles(size, mid, self._rng)
        self._accent: Color = accent
        self._motes: list[Mote] = [self._spawn_mote() for _ in range(48)]
        self._t = 0.0

    def _spawn_mote(self, *, from_bottom: bool = True) -> Mote:
        width, height = self.size
        return Mote(
            x=self._rng.uniform(0, width),
            y=self._rng.uniform(height * 0.3, height) if from_bottom else self._rng.uniform(0, height),
            vx=self._rng.uniform(-8, 8),
            vy=self._rng.uniform(-22, -6),
            radius=self._rng.uniform(1.2, 2.6),
            base_alpha=self._rng.randint(70, 170),
            phase=self._rng.uniform(0, math.tau),
        )

    def update(self, dt: float) -> None:
        self._t += dt
        width, height = self.size
        for mote in self._motes:
            mote.x += mote.vx * dt
            mote.y += mote.vy * dt
            mote.phase += dt * 1.6
            if mote.y < -10 or mote.x < -20 or mote.x > width + 20:
                fresh = self._spawn_mote(from_bottom=False)
                mote.x = fresh.x
                mote.y = height + 5
                mote.vx = fresh.vx
                mote.vy = fresh.vy
                mote.radius = fresh.radius
                mote.base_alpha = fresh.base_alpha
                mote.phase = fresh.phase

    def draw(self, target: pygame.Surface) -> None:
        target.blit(self._gradient, (0, 0))
        target.blit(self._tiles, (0, 0))
        mote_layer = pygame.Surface(self.size, pygame.SRCALPHA).convert_alpha()
        for mote in self._motes:
            shimmer = 0.5 + 0.5 * math.sin(mote.phase)
            alpha = max(0, min(255, int(mote.base_alpha * shimmer)))
            color = (*self._accent, alpha)
            pygame.draw.circle(
                mote_layer,
                color,
                (int(mote.x), int(mote.y)),
                max(1, int(mote.radius)),
            )
        target.blit(mote_layer, (0, 0))

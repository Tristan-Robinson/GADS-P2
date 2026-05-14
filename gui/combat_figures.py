"""Procedural combat silhouettes (enemy + player) for the battle overlay."""

from __future__ import annotations

import math

import pygame

from gui.highlight import Color


def _pulse(ticks: int, speed: float = 0.004) -> float:
    return 0.5 + 0.5 * math.sin(ticks * speed)


def draw_player_stance(
    surf: pygame.Surface,
    rect: pygame.Rect,
    accent: Color,
    ticks: int,
) -> None:
    """Simple adventurer silhouette facing left (toward the foe)."""

    ox = rect.centerx
    oy = rect.centery + int(( _pulse(ticks, 0.003) - 0.5) * 4)
    scale = min(rect.width, rect.height) / 120.0
    s = lambda v: int(v * scale)

    body = pygame.Rect(ox - s(14), oy - s(28), s(28), s(52))
    pygame.draw.ellipse(surf, (52, 58, 72), body)
    pygame.draw.ellipse(surf, accent, body, 2)

    head_r = s(16)
    pygame.draw.circle(surf, (210, 200, 190), (ox, oy - s(46)), head_r)
    pygame.draw.circle(surf, accent, (ox, oy - s(46)), head_r, 2)

    arm = pygame.Rect(ox - s(36), oy - s(22), s(32), s(10))
    pygame.draw.ellipse(surf, (70, 75, 90), arm)
    leg_l = pygame.Rect(ox - s(12), oy + s(22), s(10), s(28))
    leg_r = pygame.Rect(ox + s(2), oy + s(22), s(10), s(28))
    pygame.draw.ellipse(surf, (55, 60, 75), leg_l)
    pygame.draw.ellipse(surf, (55, 60, 75), leg_r)


def draw_hostile_figure(
    surf: pygame.Surface,
    rect: pygame.Rect,
    kind: str,
    accent: Color,
    ticks: int,
) -> None:
    """Draw a themed hostile silhouette inside ``rect``."""

    k = (kind or "default").lower()
    if k in ("rat", "beast", "beast_small"):
        _draw_rat(surf, rect, accent, ticks)
    elif k in ("goblin", "orc"):
        _draw_goblin(surf, rect, accent, ticks)
    elif k in ("kobold", "lizard"):
        _draw_kobold(surf, rect, accent, ticks)
    elif k in ("skeleton", "skull", "wraith", "ghost"):
        _draw_skeleton(surf, rect, accent, ticks)
    elif k in ("cultist", "mage", "warlock"):
        _draw_cultist(surf, rect, accent, ticks)
    elif k in ("slime", "ooze"):
        _draw_slime(surf, rect, accent, ticks)
    elif k in ("demon", "devil", "imp"):
        _draw_demon(surf, rect, accent, ticks)
    elif k in ("wisp", "sprite", "spark"):
        _draw_wisp(surf, rect, accent, ticks)
    elif k in ("dragon", "drake", "wyvern"):
        _draw_dragon(surf, rect, accent, ticks)
    else:
        _draw_brute(surf, rect, accent, ticks)


def _scale_rect(rect: pygame.Rect, ticks: int) -> tuple[int, int, float]:
    cx, cy = rect.centerx, rect.centery
    bob = int((_pulse(ticks) - 0.5) * 6)
    sc = min(rect.width, rect.height) / 130.0
    return cx, cy + bob, sc


def _draw_goblin(surf: pygame.Surface, rect: pygame.Rect, accent: Color, ticks: int) -> None:
    cx, cy, sc = _scale_rect(rect, ticks)
    s = lambda v: int(v * sc)
    skin = (72, 120, 72)
    body = pygame.Rect(cx - s(22), cy - s(10), s(44), s(56))
    pygame.draw.ellipse(surf, skin, body)
    pygame.draw.ellipse(surf, accent, body, 2)
    head = pygame.Rect(cx - s(26), cy - s(58), s(52), s(44))
    pygame.draw.ellipse(surf, skin, head)
    pygame.draw.ellipse(surf, accent, head, 2)
    ear_l = [(cx - s(34), cy - s(48)), (cx - s(44), cy - s(62)), (cx - s(28), cy - s(56))]
    ear_r = [(cx + s(34), cy - s(48)), (cx + s(44), cy - s(62)), (cx + s(28), cy - s(56))]
    pygame.draw.polygon(surf, skin, ear_l)
    pygame.draw.polygon(surf, skin, ear_r)
    pygame.draw.polygon(surf, accent, ear_l, 2)
    pygame.draw.polygon(surf, accent, ear_r, 2)
    pygame.draw.circle(surf, (240, 240, 60), (cx - s(12), cy - s(42)), s(5))
    pygame.draw.circle(surf, (240, 240, 60), (cx + s(12), cy - s(42)), s(5))


def _draw_kobold(surf: pygame.Surface, rect: pygame.Rect, accent: Color, ticks: int) -> None:
    cx, cy, sc = _scale_rect(rect, ticks)
    s = lambda v: int(v * sc)
    col = (90, 130, 140)
    snout = pygame.Rect(cx + s(8), cy - s(36), s(36), s(18))
    pygame.draw.ellipse(surf, col, snout)
    body = pygame.Rect(cx - s(20), cy - s(8), s(40), s(52))
    pygame.draw.ellipse(surf, col, body)
    pygame.draw.ellipse(surf, accent, body, 2)
    tail = [(cx - s(28), cy + s(30)), (cx - s(52), cy + s(44)), (cx - s(18), cy + s(40))]
    pygame.draw.lines(surf, col, False, tail, s(6))


def _draw_skeleton(surf: pygame.Surface, rect: pygame.Rect, accent: Color, ticks: int) -> None:
    cx, cy, sc = _scale_rect(rect, ticks)
    s = lambda v: int(v * sc)
    bone = (210, 210, 200)
    pygame.draw.circle(surf, bone, (cx, cy - s(48)), s(20), s(3))
    spine = pygame.Rect(cx - s(4), cy - s(32), s(8), s(52))
    pygame.draw.rect(surf, bone, spine, border_radius=s(3))
    pygame.draw.rect(surf, accent, spine, 2, border_radius=s(3))
    for dx in (-s(22), s(22)):
        pygame.draw.line(surf, bone, (cx, cy - s(20)), (cx + dx, cy + s(8)), s(5))


def _draw_rat(surf: pygame.Surface, rect: pygame.Rect, accent: Color, ticks: int) -> None:
    cx, cy, sc = _scale_rect(rect, ticks)
    s = lambda v: int(v * sc)
    fur = (110, 90, 100)
    body = pygame.Rect(cx - s(30), cy - s(8), s(60), s(32))
    pygame.draw.ellipse(surf, fur, body)
    nose = pygame.Rect(cx + s(28), cy - s(10), s(22), s(16))
    pygame.draw.ellipse(surf, fur, nose)
    pygame.draw.ellipse(surf, accent, body, 2)
    tail = [(cx - s(36), cy + s(8)), (cx - s(56), cy - s(4)), (cx - s(40), cy + s(4))]
    pygame.draw.lines(surf, (90, 70, 80), False, tail, s(4))


def _draw_cultist(surf: pygame.Surface, rect: pygame.Rect, accent: Color, ticks: int) -> None:
    cx, cy, sc = _scale_rect(rect, ticks)
    s = lambda v: int(v * sc)
    robe = (48, 42, 72)
    hood = pygame.Rect(cx - s(24), cy - s(62), s(48), s(40))
    pygame.draw.ellipse(surf, robe, hood)
    body = pygame.Rect(cx - s(28), cy - s(28), s(56), s(70))
    pygame.draw.ellipse(surf, robe, body)
    pygame.draw.ellipse(surf, accent, body, 2)
    pygame.draw.circle(surf, (200, 60, 60), (cx, cy - s(44)), s(6))


def _draw_slime(surf: pygame.Surface, rect: pygame.Rect, accent: Color, ticks: int) -> None:
    cx, cy, sc = _scale_rect(rect, ticks)
    s = lambda v: int(v * sc)
    wobble = s(4) * math.sin(ticks * 0.005)
    blob = pygame.Rect(cx - s(40) + int(wobble), cy - s(20), s(80), s(56))
    pygame.draw.ellipse(surf, (60, 160, 110), blob)
    pygame.draw.ellipse(surf, accent, blob, 2)
    eye_l = (cx - s(16), cy - s(8))
    eye_r = (cx + s(16), cy - s(8))
    pygame.draw.circle(surf, (20, 40, 30), eye_l, s(8))
    pygame.draw.circle(surf, (20, 40, 30), eye_r, s(8))


def _draw_demon(surf: pygame.Surface, rect: pygame.Rect, accent: Color, ticks: int) -> None:
    cx, cy, sc = _scale_rect(rect, ticks)
    s = lambda v: int(v * sc)
    skin = (140, 50, 55)
    head = pygame.Rect(cx - s(22), cy - s(58), s(44), s(40))
    pygame.draw.ellipse(surf, skin, head)
    horns = [(cx - s(28), cy - s(70)), (cx - s(18), cy - s(58)), (cx - s(24), cy - s(52))]
    pygame.draw.polygon(surf, (60, 50, 50), horns)
    horns_r = [(cx + s(28), cy - s(70)), (cx + s(18), cy - s(58)), (cx + s(24), cy - s(52))]
    pygame.draw.polygon(surf, (60, 50, 50), horns_r)
    body = pygame.Rect(cx - s(26), cy - s(18), s(52), s(62))
    pygame.draw.ellipse(surf, skin, body)
    pygame.draw.ellipse(surf, accent, body, 2)


def _draw_wisp(surf: pygame.Surface, rect: pygame.Rect, accent: Color, ticks: int) -> None:
    cx, cy, sc = _scale_rect(rect, ticks)
    s = lambda v: int(v * sc)
    for i in range(3):
        r = s(36 - i * 10)
        a = 80 - i * 22
        surf2 = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(surf2, (*accent[:3], a), (r, r), r)
        surf.blit(surf2, (cx - r, cy - s(30) - r))


def _draw_dragon(surf: pygame.Surface, rect: pygame.Rect, accent: Color, ticks: int) -> None:
    cx, cy, sc = _scale_rect(rect, ticks)
    s = lambda v: int(v * sc)
    body = pygame.Rect(cx - s(40), cy - s(12), s(80), s(40))
    pygame.draw.ellipse(surf, (90, 40, 40), body)
    neck = pygame.Rect(cx + s(24), cy - s(36), s(40), s(20))
    pygame.draw.ellipse(surf, (90, 40, 40), neck)
    pygame.draw.ellipse(surf, accent, body, 2)
    pygame.draw.polygon(surf, (120, 60, 50), [(cx + s(60), cy - s(32)), (cx + s(88), cy - s(28)), (cx + s(64), cy - s(18))])


def _draw_brute(surf: pygame.Surface, rect: pygame.Rect, accent: Color, ticks: int) -> None:
    cx, cy, sc = _scale_rect(rect, ticks)
    s = lambda v: int(v * sc)
    body = pygame.Rect(cx - s(32), cy - s(16), s(64), s(68))
    pygame.draw.ellipse(surf, (88, 78, 92), body)
    pygame.draw.ellipse(surf, accent, body, 2)
    pygame.draw.circle(surf, (200, 190, 200), (cx, cy - s(48)), s(22))
    pygame.draw.circle(surf, accent, (cx, cy - s(48)), s(22), 2)

"""Modal UIs for quest offers (parchment) and merchant (coin/teal)."""

from __future__ import annotations

from collections.abc import Callable

import pygame

from game.actions import ActionResult
from game.models import GameState
from gui.widgets import Button, LABEL_BRIGHT, LABEL_DIM, draw_panel, fit_text


def _wrap_lines(font: pygame.font.Font, text: str, max_width: int) -> list[str]:
    lines: list[str] = []
    for paragraph in text.strip().split("\n"):
        words = paragraph.split()
        if not words:
            continue
        cur = words[0]
        for w in words[1:]:
            cand = f"{cur} {w}"
            if font.size(cand)[0] <= max_width:
                cur = cand
            else:
                lines.append(cur)
                cur = w
        lines.append(cur)
    return lines


class QuestOfferOverlay:
    """Parchment-styled accept / decline for ``state.draft_quest_offer``."""

    def __init__(
        self,
        fonts: dict[str, pygame.font.Font],
        *,
        on_accept: Callable[[GameState], ActionResult],
        on_decline: Callable[[GameState], ActionResult],
        on_close: Callable[[], None],
    ) -> None:
        self.fonts = fonts
        self._on_accept = on_accept
        self._on_decline = on_decline
        self._on_close = on_close
        self._panel = pygame.Rect(0, 0, 0, 0)
        self._accept_btn = Button(
            pygame.Rect(0, 0, 1, 1),
            "Accept quest",
            self.fonts["button"],
            on_click=None,
        )
        self._decline_btn = Button(
            pygame.Rect(0, 0, 1, 1),
            "Decline",
            self.fonts["button"],
            on_click=None,
        )
        self._close_btn = Button(
            pygame.Rect(0, 0, 1, 1),
            "Close",
            self.fonts["button"],
            on_click=self._on_close,
        )
        self._accent = (165, 120, 70)
        self._fill = (38, 32, 26, 250)

    def _layout(self, screen: pygame.Rect) -> None:
        w, h = min(520, screen.width - 40), min(380, screen.height - 40)
        self._panel = pygame.Rect(screen.centerx - w // 2, screen.centery - h // 2, w, h)
        inner = self._panel.inflate(-24, -24)
        by = inner.bottom - 48
        bw = (inner.width - 16) // 3
        self._accept_btn.rect = pygame.Rect(inner.left, by, bw, 42)
        self._decline_btn.rect = pygame.Rect(inner.left + bw + 8, by, bw, 42)
        self._close_btn.rect = pygame.Rect(inner.left + 2 * (bw + 8), by, bw - 16, 42)
        for b in (self._accept_btn, self._decline_btn, self._close_btn):
            b.set_border(self._accent)

    def handle_event(
        self,
        event: pygame.event.Event,
        state: GameState,
        screen: pygame.Rect,
    ) -> ActionResult | None:
        self._layout(screen)
        if self._accept_btn.handle_event(event):
            return self._on_accept(state)
        if self._decline_btn.handle_event(event):
            return self._on_decline(state)
        if self._close_btn.handle_event(event):
            return None
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._on_close()
            return None
        return None

    def draw(self, surface: pygame.Surface, state: GameState) -> None:
        offer = state.draft_quest_offer
        if offer is None:
            return
        screen = surface.get_rect()
        self._layout(screen)
        veil = pygame.Surface(screen.size, pygame.SRCALPHA)
        veil.fill((15, 10, 8, 200))
        surface.blit(veil, (0, 0))
        draw_panel(surface, self._panel, border_color=self._accent, fill=self._fill)
        inner = self._panel.inflate(-28, -28)
        y = inner.top
        title = self.fonts["heading"].render(offer.title, True, (240, 210, 160))
        surface.blit(title, (inner.left, y))
        y += title.get_height() + 10
        for line in _wrap_lines(self.fonts["body"], offer.body, inner.width - 8):
            sf = self.fonts["body"].render(line, True, LABEL_DIM)
            surface.blit(sf, (inner.left, y))
            y += sf.get_height() + 2
        y += 8
        reward = self.fonts["label"].render(f"Reward: {offer.reward_gold} gold", True, (220, 190, 120))
        surface.blit(reward, (inner.left, y))
        if self._accept_btn:
            self._accept_btn.draw(surface)
        if self._decline_btn:
            self._decline_btn.draw(surface)
        if self._close_btn:
            self._close_btn.draw(surface)


class MerchantOverlay:
    """Teal trade UI: buy from stock / sell from pack."""

    def __init__(
        self,
        fonts: dict[str, pygame.font.Font],
        *,
        on_buy: Callable[[GameState, int], ActionResult],
        on_sell: Callable[[GameState, int], ActionResult],
        on_close: Callable[[], None],
    ) -> None:
        self.fonts = fonts
        self._on_buy = on_buy
        self._on_sell = on_sell
        self._on_close = on_close
        self._panel = pygame.Rect(0, 0, 0, 0)
        self._buy_btn = Button(
            pygame.Rect(0, 0, 1, 1),
            "Buy selected",
            self.fonts["button"],
            on_click=None,
        )
        self._sell_btn = Button(
            pygame.Rect(0, 0, 1, 1),
            "Sell selected",
            self.fonts["button"],
            on_click=None,
        )
        self._close_btn = Button(
            pygame.Rect(0, 0, 1, 1),
            "Leave",
            self.fonts["button"],
            on_click=self._on_close,
        )
        self._accent = (80, 170, 175)
        self._fill = (12, 28, 32, 248)
        self._sel_buy: int | None = None
        self._sel_sell: int | None = None
        self._list_left = pygame.Rect(0, 0, 0, 0)
        self._list_right = pygame.Rect(0, 0, 0, 0)
        self._row_h = 28

    def _merchant_stock(self, state: GameState) -> list:
        for n in state.current_room().npcs:
            if n.kind == "merchant":
                return n.stock
        return []

    def _layout(self, screen: pygame.Rect) -> None:
        w, h = min(720, screen.width - 32), min(460, screen.height - 32)
        self._panel = pygame.Rect(screen.centerx - w // 2, screen.centery - h // 2, w, h)
        inner = self._panel.inflate(-20, -20)
        mid = inner.left + inner.width // 2 + 6
        self._list_left = pygame.Rect(inner.left, inner.top + 72, (inner.width // 2) - 14, inner.height - 130)
        self._list_right = pygame.Rect(mid, inner.top + 72, (inner.width // 2) - 14, inner.height - 130)
        by = inner.bottom - 46
        self._buy_btn.rect = pygame.Rect(self._list_right.left, by, 140, 40)
        self._sell_btn.rect = pygame.Rect(self._list_left.left, by, 140, 40)
        self._close_btn.rect = pygame.Rect(inner.right - 120, by, 110, 40)
        for b in (self._buy_btn, self._sell_btn, self._close_btn):
            b.set_border(self._accent)

    def reset_selection(self) -> None:
        self._sel_buy = None
        self._sel_sell = None

    def handle_event(
        self,
        event: pygame.event.Event,
        state: GameState,
        screen: pygame.Rect,
    ) -> ActionResult | None:
        self._layout(screen)
        if self._close_btn.handle_event(event):
            return None
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._on_close()
            return None
        stock = self._merchant_stock(state)
        inv = state.player.inventory
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._list_left.collidepoint(event.pos):
                row = (event.pos[1] - self._list_left.top) // self._row_h
                if 0 <= row < len(inv):
                    self._sel_sell = row
                return None
            if self._list_right.collidepoint(event.pos):
                row = (event.pos[1] - self._list_right.top) // self._row_h
                if 0 <= row < len(stock):
                    self._sel_buy = row
                return None
        if self._sell_btn.handle_event(event):
            if self._sel_sell is not None:
                return self._on_sell(state, self._sel_sell)
            return None
        if self._buy_btn.handle_event(event):
            if self._sel_buy is not None:
                return self._on_buy(state, self._sel_buy)
            return None
        return None

    def draw(self, surface: pygame.Surface, state: GameState) -> None:
        screen = surface.get_rect()
        self._layout(screen)
        veil = pygame.Surface(screen.size, pygame.SRCALPHA)
        veil.fill((5, 18, 22, 195))
        surface.blit(veil, (0, 0))
        draw_panel(surface, self._panel, border_color=self._accent, fill=self._fill)
        inner = self._panel.inflate(-24, -24)
        t = self.fonts["heading"].render("Traveling merchant", True, (200, 240, 240))
        surface.blit(t, (inner.left, inner.top))
        g = self.fonts["body"].render(f"Your gold: {state.player.gold}", True, (240, 220, 140))
        surface.blit(g, (inner.right - g.get_width(), inner.top + 4))
        sub = self.fonts["label"].render(
            "Select an item in your pack to sell, or a ware to buy. Prices are on each line.",
            True,
            LABEL_DIM,
        )
        surface.blit(sub, (inner.left, inner.top + t.get_height() + 6))

        inv = state.player.inventory
        stock = self._merchant_stock(state)
        clip = surface.get_clip()
        surface.set_clip(self._list_left)
        y = self._list_left.top
        for i, it in enumerate(inv):
            row = pygame.Rect(self._list_left.left, y, self._list_left.width, self._row_h - 2)
            if self._sel_sell == i:
                pygame.draw.rect(surface, (*self._accent[:3], 40), row, border_radius=6)
            price = max(1, (it.gold_value if it.gold_value > 0 else 3) // 2)
            line = fit_text(self.fonts["body"], f"{it.name}  (sell ~{price}g)", self._list_left.width - 8)
            sf = self.fonts["body"].render(line, True, LABEL_BRIGHT)
            surface.blit(sf, (row.left + 4, row.centery - sf.get_height() // 2))
            y += self._row_h
        surface.set_clip(clip)

        surface.set_clip(self._list_right)
        y = self._list_right.top
        for i, it in enumerate(stock):
            row = pygame.Rect(self._list_right.left, y, self._list_right.width, self._row_h - 2)
            if self._sel_buy == i:
                pygame.draw.rect(surface, (*self._accent[:3], 40), row, border_radius=6)
            price = max(1, it.gold_value)
            line = fit_text(self.fonts["body"], f"{it.name}  ({price}g)", self._list_right.width - 8)
            sf = self.fonts["body"].render(line, True, LABEL_BRIGHT)
            surface.blit(sf, (row.left + 4, row.centery - sf.get_height() // 2))
            y += self._row_h
        surface.set_clip(clip)

        lab_l = self.fonts["label"].render("Your pack", True, self._accent)
        lab_r = self.fonts["label"].render("Merchant wares", True, self._accent)
        surface.blit(lab_l, (self._list_left.left, self._list_left.top - 22))
        surface.blit(lab_r, (self._list_right.left, self._list_right.top - 22))

        if self._sell_btn:
            self._sell_btn.draw(surface)
        if self._buy_btn:
            self._buy_btn.draw(surface)
        if self._close_btn:
            self._close_btn.draw(surface)

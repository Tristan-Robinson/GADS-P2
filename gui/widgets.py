"""Reusable Pygame widgets for the dungeon UI."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Callable

import pygame

from game.battle import BattleChoice
from game.models import GameState
from game.spells import get_spell
from gui.combat_figures import draw_hostile_figure, draw_player_stance
from gui.highlight import DEFAULT as DEFAULT_TEXT_COLOR
from gui.highlight import Color, Span


PANEL_FILL = (10, 10, 14, 200)
PANEL_BORDER_FALLBACK: Color = (230, 220, 200)
LABEL_DIM: Color = (190, 190, 200)
LABEL_BRIGHT: Color = (245, 240, 230)
HP_BG: Color = (45, 15, 18)
HP_HIGH: Color = (90, 220, 110)
HP_LOW: Color = (235, 75, 70)
MANA_BG: Color = (22, 28, 52)
MANA_LOW: Color = (80, 110, 200)
MANA_HIGH: Color = (140, 210, 255)

STATUS_BAR_HEIGHT: int = 152


def fit_text(font: pygame.font.Font, text: str, max_width: int) -> str:
    """Truncate ``text`` so it fits inside ``max_width`` pixels, appending
    an ellipsis when it does not fit. Trims whole tokens first, then
    characters, so the visible head of the string stays readable."""

    if max_width <= 0 or not text:
        return ""
    if font.size(text)[0] <= max_width:
        return text
    ellipsis = "..."
    parts = text.split(" ")
    while len(parts) > 1:
        parts.pop()
        candidate = " ".join(parts) + ellipsis
        if font.size(candidate)[0] <= max_width:
            return candidate
    trimmed = text
    while trimmed and font.size(trimmed + ellipsis)[0] > max_width:
        trimmed = trimmed[:-1]
    return (trimmed + ellipsis) if trimmed else ellipsis


def draw_panel(
    target: pygame.Surface,
    rect: pygame.Rect,
    *,
    border_color: Color,
    radius: int = 14,
    border: int = 2,
    fill: tuple[int, int, int, int] = PANEL_FILL,
) -> None:
    panel = pygame.Surface(rect.size, pygame.SRCALPHA).convert_alpha()
    pygame.draw.rect(panel, fill, panel.get_rect(), border_radius=radius)
    if border > 0:
        pygame.draw.rect(panel, border_color, panel.get_rect(), border, border_radius=radius)
    target.blit(panel, rect.topleft)


def _lerp_color(a: Color, b: Color, t: float) -> Color:
    t = max(0.0, min(1.0, t))
    return (
        int(a[0] + (b[0] - a[0]) * t),
        int(a[1] + (b[1] - a[1]) * t),
        int(a[2] + (b[2] - a[2]) * t),
    )


def _wrap_spans(
    spans: list[Span],
    font: pygame.font.Font,
    max_width: int,
) -> list[list[tuple[str, Color]]]:
    lines: list[list[tuple[str, Color]]] = []
    current: list[tuple[str, Color]] = []
    current_w = 0
    for span in spans:
        for piece in re.split(r"(\s+)", span.text):
            if not piece:
                continue
            piece_w = font.size(piece)[0]
            if current_w + piece_w > max_width and current:
                lines.append(current)
                current = []
                current_w = 0
                if piece.isspace():
                    continue
            if not current and piece.isspace():
                continue
            current.append((piece, span.color))
            current_w += piece_w
    if current:
        lines.append(current)
    return lines


@dataclass
class NarrationEntry:
    heading: str | None
    spans: list[Span]
    accent: Color = PANEL_BORDER_FALLBACK
    wrapped: list[list[tuple[str, Color]]] = field(default_factory=list)
    wrapped_width: int = 0
    heading_height: int = 0


class NarrationPanel:
    def __init__(
        self,
        rect: pygame.Rect,
        font: pygame.font.Font,
        heading_font: pygame.font.Font,
    ) -> None:
        self.rect = rect
        self.font = font
        self.heading_font = heading_font
        self.entries: list[NarrationEntry] = []
        self.border_color: Color = PANEL_BORDER_FALLBACK
        self.scroll_offset = 0
        self._padding = 18
        self._line_gap = 4
        self._entry_gap = 14

    def set_border(self, color: Color) -> None:
        self.border_color = color

    def clear(self) -> None:
        self.entries.clear()
        self.scroll_offset = 0

    def append(
        self,
        spans: list[Span],
        *,
        heading: str | None = None,
        accent: Color | None = None,
    ) -> None:
        entry = NarrationEntry(
            heading=heading,
            spans=spans,
            accent=accent or self.border_color,
        )
        self._rewrap_entry(entry)
        self.entries.append(entry)
        self.scroll_offset = 0

    def _inner_width(self) -> int:
        return self.rect.width - self._padding * 2 - 8

    def _rewrap_entry(self, entry: NarrationEntry) -> None:
        inner_width = self._inner_width()
        entry.wrapped = _wrap_spans(entry.spans, self.font, inner_width)
        entry.wrapped_width = inner_width
        entry.heading_height = (
            self.heading_font.get_height() + 6 if entry.heading else 0
        )

    def _ensure_wrap(self) -> None:
        inner_width = self._inner_width()
        for entry in self.entries:
            if entry.wrapped_width != inner_width:
                self._rewrap_entry(entry)

    def _entry_height(self, entry: NarrationEntry) -> int:
        body = len(entry.wrapped) * (self.font.get_height() + self._line_gap)
        return entry.heading_height + body

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEWHEEL:
            self.scroll_offset = max(0, self.scroll_offset + event.y * 40)
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_PAGEUP:
                self.scroll_offset = max(0, self.scroll_offset + 200)
            elif event.key == pygame.K_PAGEDOWN:
                self.scroll_offset = max(0, self.scroll_offset - 200)

    def draw(self, target: pygame.Surface) -> None:
        draw_panel(target, self.rect, border_color=self.border_color)
        self._ensure_wrap()
        clip_rect = self.rect.inflate(-self._padding * 2, -self._padding * 2)
        prev_clip = target.get_clip()
        target.set_clip(clip_rect)

        line_step = self.font.get_height() + self._line_gap
        total_height = 0
        for entry in self.entries:
            total_height += self._entry_height(entry)
            total_height += self._entry_gap
        if self.entries:
            total_height -= self._entry_gap

        cursor_bottom = clip_rect.bottom + self.scroll_offset

        for entry in reversed(self.entries):
            body_height = len(entry.wrapped) * line_step
            entry_total = body_height + entry.heading_height
            entry_top = cursor_bottom - entry_total
            y = entry_top
            if entry.heading:
                heading_surface = self.heading_font.render(
                    entry.heading, True, entry.accent
                )
                target.blit(heading_surface, (clip_rect.left, y))
                y += entry.heading_height
            for line in entry.wrapped:
                self._draw_line(target, line, y)
                y += line_step
            cursor_bottom = entry_top - self._entry_gap
            if cursor_bottom < clip_rect.top - 400:
                break

        target.set_clip(prev_clip)

        viewport_h = clip_rect.height
        max_scroll = max(0, total_height - viewport_h)
        if max_scroll > 0:
            track_h = viewport_h
            thumb_h = max(28, int(track_h * (viewport_h / total_height)))
            scroll_t = min(1.0, self.scroll_offset / max_scroll)
            thumb_y = clip_rect.bottom - thumb_h - int(
                scroll_t * (track_h - thumb_h)
            )
            thumb_rect = pygame.Rect(
                self.rect.right - 10,
                thumb_y,
                4,
                thumb_h,
            )
            pygame.draw.rect(
                target,
                self.border_color,
                thumb_rect,
                border_radius=2,
            )

    def _draw_line(
        self,
        target: pygame.Surface,
        line: list[tuple[str, Color]],
        y: int,
    ) -> None:
        x = self.rect.left + self._padding
        for text, color in line:
            surface = self.font.render(text, True, color)
            target.blit(surface, (x, y))
            x += surface.get_width()

    def scroll_to_bottom(self) -> None:
        self.scroll_offset = 0


class StatusBar:
    def __init__(
        self,
        rect: pygame.Rect,
        title_font: pygame.font.Font,
        label_font: pygame.font.Font,
        value_font: pygame.font.Font,
    ) -> None:
        self.rect = rect
        self.title_font = title_font
        self.label_font = label_font
        self.value_font = value_font
        self.border_color: Color = PANEL_BORDER_FALLBACK
        self._padding = 14
        self._row_gap = 10
        self._hp_bar_width = 200
        self._hp_bar_height = 16

    def set_border(self, color: Color) -> None:
        self.border_color = color

    def draw(
        self,
        target: pygame.Surface,
        state: GameState,
        *,
        thinking: bool = False,
    ) -> None:
        draw_panel(target, self.rect, border_color=self.border_color)
        inner = self.rect.inflate(-self._padding * 2, -self._padding * 2)

        hp_value_text = f"{state.player.hp}/{state.player.max_hp}"
        hp_value_surface = self.value_font.render(hp_value_text, True, LABEL_BRIGHT)
        hp_label_surface = self.label_font.render("HP", True, LABEL_DIM)

        mp_value_text = f"{state.player.mana}/{state.player.max_mana}"
        mp_value_surface = self.value_font.render(mp_value_text, True, LABEL_BRIGHT)
        mp_label_surface = self.label_font.render("MP", True, LABEL_DIM)

        bar_height = self._hp_bar_height
        bar_width = self._hp_bar_width
        bar_x = inner.right - bar_width
        row1_top = inner.top
        bar_stack_h = bar_height * 2 + 6
        row1_height = max(
            self.title_font.get_height(),
            hp_value_surface.get_height(),
            bar_stack_h,
        )
        hp_bar_y = row1_top + (row1_height - bar_stack_h) // 2
        mana_bar_y = hp_bar_y + bar_height + 6

        hp_bar_rect = pygame.Rect(bar_x, hp_bar_y, bar_width, bar_height)
        pygame.draw.rect(target, HP_BG, hp_bar_rect, border_radius=8)
        ratio = 0.0
        if state.player.max_hp > 0:
            ratio = max(0.0, min(1.0, state.player.hp / state.player.max_hp))
        if ratio > 0:
            fill_color = _lerp_color(HP_LOW, HP_HIGH, ratio)
            fill_rect = pygame.Rect(bar_x, hp_bar_y, int(bar_width * ratio), bar_height)
            pygame.draw.rect(target, fill_color, fill_rect, border_radius=8)
        pygame.draw.rect(target, self.border_color, hp_bar_rect, 1, border_radius=8)

        mana_bar_rect = pygame.Rect(bar_x, mana_bar_y, bar_width, bar_height)
        pygame.draw.rect(target, MANA_BG, mana_bar_rect, border_radius=8)
        mr = 0.0
        if state.player.max_mana > 0:
            mr = max(0.0, min(1.0, state.player.mana / state.player.max_mana))
        if mr > 0:
            mfill = _lerp_color(MANA_LOW, MANA_HIGH, mr)
            mfill_rect = pygame.Rect(bar_x, mana_bar_y, int(bar_width * mr), bar_height)
            pygame.draw.rect(target, mfill, mfill_rect, border_radius=8)
        pygame.draw.rect(target, self.border_color, mana_bar_rect, 1, border_radius=8)

        hp_value_x = bar_x - hp_value_surface.get_width() - 8
        hp_value_y = hp_bar_y + (bar_height - hp_value_surface.get_height()) // 2
        target.blit(hp_value_surface, (hp_value_x, hp_value_y))

        hp_label_x = hp_value_x - hp_label_surface.get_width() - 8
        hp_label_y = hp_bar_y + (bar_height - hp_label_surface.get_height()) // 2
        target.blit(hp_label_surface, (hp_label_x, hp_label_y))

        mp_value_x = bar_x - mp_value_surface.get_width() - 8
        mp_value_y = mana_bar_y + (bar_height - mp_value_surface.get_height()) // 2
        target.blit(mp_value_surface, (mp_value_x, mp_value_y))

        mp_label_x = mp_value_x - mp_label_surface.get_width() - 8
        mp_label_y = mana_bar_y + (bar_height - mp_label_surface.get_height()) // 2
        target.blit(mp_label_surface, (mp_label_x, mp_label_y))

        title_max_width = max(40, min(hp_label_x, mp_label_x) - inner.left - 20)
        title_text = fit_text(self.title_font, state.current_room().name, title_max_width)
        title_surface = self.title_font.render(title_text, True, LABEL_BRIGHT)
        title_y = row1_top + (row1_height - title_surface.get_height()) // 2
        target.blit(title_surface, (inner.left, title_y))

        if thinking:
            indicator = self.label_font.render("Narrating...", True, self.border_color)
            ind_x = inner.left + title_surface.get_width() + 20
            label_edge = min(hp_label_x, mp_label_x)
            ind_x = min(ind_x, label_edge - indicator.get_width() - 10)
            if ind_x > inner.left + title_surface.get_width() + 8:
                target.blit(
                    indicator,
                    (ind_x, row1_top + (row1_height - indicator.get_height()) // 2),
                )

        row2_top = row1_top + row1_height + self._row_gap
        depth_text = f"Depth {state.level_depth} - {state.theme_name}"
        depth_surface = self.label_font.render(depth_text, True, self.border_color)
        target.blit(depth_surface, (inner.left, row2_top))
        gold_sf = self.label_font.render(f"Gold {state.player.gold}", True, (230, 200, 120))
        target.blit(gold_sf, (inner.left + depth_surface.get_width() + 16, row2_top))

        stats_text = (
            f"ATK {state.effective_attack()}  DEF {state.effective_armor()}  "
            f"AGI {state.effective_agility()}"
        )
        stats_surface = self.label_font.render(stats_text, True, LABEL_DIM)
        target.blit(stats_surface, (inner.right - stats_surface.get_width(), row2_top))

        row3_top = row2_top + self.label_font.get_height() + 8
        names = [item.name for item in state.player.inventory]
        inv_label_text = "Inventory: " + (", ".join(names) if names else "empty")
        inv_max_width = max(40, inner.right - inner.left)
        inv_text = fit_text(self.label_font, inv_label_text, inv_max_width)
        inv_surface = self.label_font.render(inv_text, True, LABEL_BRIGHT)
        target.blit(inv_surface, (inner.left, row3_top))


class InputBox:
    def __init__(
        self,
        rect: pygame.Rect,
        font: pygame.font.Font,
        prompt_font: pygame.font.Font,
    ) -> None:
        self.rect = rect
        self.font = font
        self.prompt_font = prompt_font
        self.border_color: Color = PANEL_BORDER_FALLBACK
        self.text = ""
        self.enabled = True
        self.history: list[str] = []
        self._history_index: int | None = None
        self._cursor_visible = True
        self._cursor_timer = 0.0
        self._padding = 16
        self._max_history = 50

    def set_border(self, color: Color) -> None:
        self.border_color = color

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = enabled

    def update(self, dt: float) -> None:
        self._cursor_timer += dt
        if self._cursor_timer >= 0.55:
            self._cursor_timer = 0.0
            self._cursor_visible = not self._cursor_visible

    def handle_event(self, event: pygame.event.Event) -> str | None:
        if not self.enabled:
            return None
        if event.type != pygame.KEYDOWN:
            return None
        if event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER:
            submitted = self.text.strip()
            if submitted:
                self.history.append(submitted)
                if len(self.history) > self._max_history:
                    self.history.pop(0)
            self.text = ""
            self._history_index = None
            return submitted if submitted else None
        if event.key == pygame.K_BACKSPACE:
            self.text = self.text[:-1]
            return None
        if event.key == pygame.K_UP:
            if self.history:
                if self._history_index is None:
                    self._history_index = len(self.history) - 1
                else:
                    self._history_index = max(0, self._history_index - 1)
                self.text = self.history[self._history_index]
            return None
        if event.key == pygame.K_DOWN:
            if self._history_index is None:
                return None
            self._history_index += 1
            if self._history_index >= len(self.history):
                self._history_index = None
                self.text = ""
            else:
                self.text = self.history[self._history_index]
            return None
        if event.unicode and event.unicode.isprintable():
            if len(self.text) < 200:
                self.text += event.unicode
        return None

    def draw(self, target: pygame.Surface, *, thinking: bool = False) -> None:
        draw_panel(target, self.rect, border_color=self.border_color)
        inner = self.rect.inflate(-self._padding * 2, -self._padding * 2)
        prompt_color = self.border_color if not thinking else LABEL_DIM
        prompt_text = ">" if not thinking else "..."
        prompt_surface = self.prompt_font.render(prompt_text, True, prompt_color)
        target.blit(
            prompt_surface,
            (inner.left, inner.top + (inner.height - prompt_surface.get_height()) // 2),
        )

        text_x = inner.left + prompt_surface.get_width() + 12
        text_y = inner.top + (inner.height - self.font.get_height()) // 2

        display = self.text if not thinking else "thinking"
        display_color = LABEL_BRIGHT if not thinking else LABEL_DIM
        text_surface = self.font.render(display, True, display_color)
        target.blit(text_surface, (text_x, text_y))

        if not thinking and self.enabled and self._cursor_visible:
            cursor_x = text_x + text_surface.get_width() + 2
            pygame.draw.line(
                target,
                self.border_color,
                (cursor_x, text_y + 3),
                (cursor_x, text_y + self.font.get_height() - 3),
                2,
            )

        if thinking:
            dot_count = int(pygame.time.get_ticks() / 250) % 4
            dots = "." * dot_count
            dot_surface = self.font.render(dots, True, self.border_color)
            target.blit(
                dot_surface,
                (text_x + text_surface.get_width() + 6, text_y),
            )


class BattlePanel:
    """Full-screen turn-based combat: actions, spell book, and battle log."""

    def __init__(
        self,
        rect: pygame.Rect,
        heading_font: pygame.font.Font,
        body_font: pygame.font.Font,
        button_font: pygame.font.Font,
        accent: Color,
        on_choice: Callable[[BattleChoice, str | None], None],
    ) -> None:
        self.rect = rect
        self.heading_font = heading_font
        self.body_font = body_font
        self.button_font = button_font
        self.accent = accent
        self.on_choice = on_choice
        self.log_lines: list[str] = []
        self._max_log = 48
        self._padding = 16
        self._spell_mode = False
        self._spell_scroll = 0
        self._main_buttons: list[Button] = []
        self._btn_back: Button | None = None
        self._spell_hitboxes: list[tuple[pygame.Rect, str]] = []
        self._spell_list_rect = pygame.Rect(0, 0, 0, 0)
        self._spell_back_rect = pygame.Rect(0, 0, 0, 0)
        self._spell_max_scroll = 0
        self._layout_buttons()

    def _layout_buttons(self) -> None:
        inner = self.rect.inflate(-self._padding * 2, -self._padding * 2)
        gap = 10
        btn_h = 44
        bottom = inner.bottom - 8
        bw = (inner.width - gap * 3) // 4
        self._main_buttons.clear()
        specs = (
            ("Attack", lambda: self.on_choice(BattleChoice.ATTACK, None)),
            ("Defend", lambda: self.on_choice(BattleChoice.DEFEND, None)),
            ("Spells", self._open_spells),
            ("Surrender", lambda: self.on_choice(BattleChoice.SURRENDER, None)),
        )
        for i, (label, fn) in enumerate(specs):
            r = pygame.Rect(inner.left + i * (bw + gap), bottom - btn_h, bw, btn_h)
            b = Button(r, label, self.button_font, on_click=fn)
            b.set_border(self.accent)
            self._main_buttons.append(b)

        back_r = pygame.Rect(inner.left, bottom - btn_h, min(160, inner.width // 3), btn_h)
        self._btn_back = Button(back_r, "Back", self.button_font, on_click=self._close_spells)
        self._btn_back.set_border(self.accent)

    def _open_spells(self) -> None:
        self._spell_mode = True
        self._spell_scroll = 0

    def _close_spells(self) -> None:
        self._spell_mode = False
        self._spell_scroll = 0

    def clear_log(self) -> None:
        self.log_lines.clear()
        self._close_spells()

    def push_log(self, line: str) -> None:
        self.log_lines.append(line)
        self.log_lines = self.log_lines[-self._max_log :]

    def handle_event(self, event: pygame.event.Event, state: GameState) -> None:
        if self._spell_mode:
            self._update_spell_layout(state)
            if event.type == pygame.MOUSEWHEEL and self._spell_list_rect.collidepoint(
                pygame.mouse.get_pos()
            ):
                self._spell_scroll = max(
                    0,
                    min(
                        self._spell_max_scroll,
                        self._spell_scroll - event.y * 24,
                    ),
                )
            if self._btn_back:
                self._btn_back.rect = self._spell_back_rect
                if self._btn_back.handle_event(event):
                    return
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for row_rect, sid in self._spell_hitboxes:
                    if row_rect.collidepoint(event.pos):
                        self._cast(sid)
                        return
            return

        for b in self._main_buttons:
            b.handle_event(event)

    def _update_spell_layout(self, state: GameState) -> None:
        inner2 = self.rect.inflate(-self._padding * 2, -self._padding * 2)
        panel = pygame.Rect(
            inner2.left,
            inner2.top + 58,
            inner2.width,
            max(80, inner2.height - 175),
        )
        self._spell_list_rect = pygame.Rect(
            panel.left + 8,
            panel.top + 36,
            panel.width - 16,
            max(40, panel.height - 100),
        )
        self._spell_back_rect = pygame.Rect(
            panel.left + panel.width // 2 - 70,
            panel.bottom - 52,
            140,
            40,
        )
        row_h = 40
        gap = 8
        ids = [sid for sid in state.player.known_spell_ids if get_spell(sid) is not None]
        total_h = len(ids) * (row_h + gap) - (gap if ids else 0)
        self._spell_max_scroll = max(0, total_h - self._spell_list_rect.height)
        self._spell_scroll = min(self._spell_scroll, self._spell_max_scroll)

        self._spell_hitboxes.clear()
        y = self._spell_list_rect.top - self._spell_scroll
        for sid in ids:
            spec = get_spell(sid)
            assert spec is not None
            row = pygame.Rect(self._spell_list_rect.left, y, self._spell_list_rect.width, row_h)
            clipped = row.clip(self._spell_list_rect)
            if clipped.width > 0 and clipped.height > 0:
                self._spell_hitboxes.append((clipped, sid))
            y += row_h + gap

    def _cast(self, spell_id: str) -> None:
        self.on_choice(BattleChoice.SPELL, spell_id)
        self._close_spells()

    def set_button_borders(self, color: Color) -> None:
        self.accent = color
        for b in self._main_buttons:
            b.set_border(color)
        if self._btn_back:
            self._btn_back.set_border(color)

    def _enemy_for_battle(self, state: GameState):
        eid = state.pending_battle_enemy_id
        if not eid:
            return None
        for enemy in state.current_room().enemies:
            if enemy.id == eid and enemy.alive:
                return enemy
        return None

    def draw(self, target: pygame.Surface, state: GameState) -> None:
        ticks = pygame.time.get_ticks()
        veil = pygame.Surface(self.rect.size, pygame.SRCALPHA)
        veil.fill((0, 0, 0, 210))
        target.blit(veil, self.rect.topleft)

        draw_panel(target, self.rect, border_color=self.accent, fill=(12, 12, 18, 245))
        inner = self.rect.inflate(-self._padding * 2, -self._padding * 2)

        cx = inner.centerx
        title = self.heading_font.render("Combat", True, self.accent)
        target.blit(title, (cx - title.get_width() // 2, inner.top))
        flow = self.body_font.render(
            "Turn order: your action, then the enemy strikes.",
            True,
            LABEL_DIM,
        )
        target.blit(flow, (cx - flow.get_width() // 2, inner.top + title.get_height() + 4))

        btn_h = 52
        row_top = inner.top + title.get_height() + flow.get_height() + 14
        main_bottom = inner.bottom - btn_h - 8
        main_h = max(100, main_bottom - row_top)

        gap = 10
        left_w = max(128, int(inner.width * 0.27))
        right_w = max(136, min(248, int(inner.width * 0.23)))
        mid_w = max(120, inner.width - left_w - right_w - 2 * gap)
        left_rect = pygame.Rect(inner.left, row_top, left_w, main_h)
        mid_rect = pygame.Rect(left_rect.right + gap, row_top, mid_w, main_h)
        right_rect = pygame.Rect(mid_rect.right + gap, row_top, right_w, main_h)

        enemy = self._enemy_for_battle(state)
        if enemy:
            vis = (enemy.combat_visual or enemy.id or "default").lower()
            nm = self.heading_font.render(enemy.name.title(), True, LABEL_BRIGHT)
            target.blit(nm, (left_rect.centerx - nm.get_width() // 2, left_rect.top))
            ty = left_rect.top + nm.get_height() + 6
            atk_e = self.body_font.render(f"Foe ATK {enemy.attack}", True, LABEL_DIM)
            target.blit(atk_e, (left_rect.centerx - atk_e.get_width() // 2, ty))
            ty += atk_e.get_height() + 4
            bar_w = max(40, left_rect.width - 10)
            bar_h = 12
            bar = pygame.Rect(left_rect.centerx - bar_w // 2, ty, bar_w, bar_h)
            pygame.draw.rect(target, HP_BG, bar, border_radius=6)
            ratio = enemy.hp / enemy.max_hp if enemy.max_hp > 0 else 0
            if ratio > 0:
                fill_w = max(1, int(bar_w * ratio))
                pygame.draw.rect(
                    target,
                    _lerp_color(HP_LOW, HP_HIGH, ratio),
                    pygame.Rect(bar.left, bar.top, fill_w, bar_h),
                    border_radius=6,
                )
            pygame.draw.rect(target, self.accent, bar, 1, border_radius=6)
            ty += bar_h + 10
            fig = pygame.Rect(
                left_rect.left + 6,
                ty,
                left_rect.width - 12,
                max(72, left_rect.bottom - ty - 6),
            )
            floor = fig.inflate(-8, -fig.height // 2).move(0, fig.height // 3)
            pygame.draw.ellipse(target, (26, 22, 32), floor)
            draw_hostile_figure(target, fig, vis, self.accent, ticks)

        log_head = self.body_font.render("Battle log", True, LABEL_DIM)
        target.blit(log_head, (mid_rect.left, mid_rect.top))
        log_top = mid_rect.top + log_head.get_height() + 4
        clip = target.get_clip()
        log_rect = pygame.Rect(mid_rect.left, log_top, mid_rect.width, mid_rect.bottom - log_top)
        target.set_clip(log_rect)
        ly = log_top
        line_h = self.body_font.get_height() + 3
        for line in self.log_lines:
            if ly > log_rect.bottom:
                break
            surf = self.body_font.render(fit_text(self.body_font, line, log_rect.width - 8), True, LABEL_DIM)
            target.blit(surf, (log_rect.left + 4, ly))
            ly += line_h
        target.set_clip(clip)

        you = self.heading_font.render("You", True, self.accent)
        target.blit(you, (right_rect.centerx - you.get_width() // 2, right_rect.top))
        ry = right_rect.top + you.get_height() + 6
        hp_txt = self.body_font.render(f"HP {state.player.hp}/{state.player.max_hp}", True, LABEL_DIM)
        target.blit(hp_txt, (right_rect.left + 2, ry))
        ry += hp_txt.get_height() + 2
        bw = max(36, right_rect.width - 4)
        hp_bar = pygame.Rect(right_rect.left + 2, ry, bw, 11)
        pygame.draw.rect(target, HP_BG, hp_bar, border_radius=5)
        pr = state.player.hp / state.player.max_hp if state.player.max_hp > 0 else 0
        if pr > 0:
            fw = max(1, int(bw * pr))
            pygame.draw.rect(
                target,
                _lerp_color(HP_LOW, HP_HIGH, pr),
                pygame.Rect(hp_bar.left, hp_bar.top, fw, hp_bar.height),
                border_radius=5,
            )
        pygame.draw.rect(target, self.accent, hp_bar, 1, border_radius=5)
        ry += hp_bar.height + 6
        mp_txt = self.body_font.render(f"MP {state.player.mana}/{state.player.max_mana}", True, LABEL_DIM)
        target.blit(mp_txt, (right_rect.left + 2, ry))
        ry += mp_txt.get_height() + 2
        mp_bar = pygame.Rect(right_rect.left + 2, ry, bw, 11)
        pygame.draw.rect(target, MANA_BG, mp_bar, border_radius=5)
        mr = state.player.mana / state.player.max_mana if state.player.max_mana > 0 else 0
        if mr > 0:
            mw = max(1, int(bw * mr))
            pygame.draw.rect(
                target,
                _lerp_color(MANA_LOW, MANA_HIGH, mr),
                pygame.Rect(mp_bar.left, mp_bar.top, mw, mp_bar.height),
                border_radius=5,
            )
        pygame.draw.rect(target, self.accent, mp_bar, 1, border_radius=5)
        ry += mp_bar.height + 8
        for label, val in (
            ("ATK", state.effective_attack()),
            ("DEF", state.effective_armor()),
            ("AGI", state.effective_agility()),
        ):
            ln = self.body_font.render(f"{label} {val}", True, LABEL_BRIGHT)
            target.blit(ln, (right_rect.left + 2, ry))
            ry += ln.get_height() + 2

        pfig_h = min(130, max(72, right_rect.bottom - ry - 6))
        if pfig_h >= 48:
            pfig = pygame.Rect(right_rect.left + 4, right_rect.bottom - pfig_h, right_rect.width - 8, pfig_h)
            draw_player_stance(target, pfig, self.accent, ticks)

        if self._spell_mode:
            self._update_spell_layout(state)
            inner2 = self.rect.inflate(-self._padding * 2, -self._padding * 2)
            panel = pygame.Rect(
                inner2.left,
                inner2.top + 58,
                inner2.width,
                max(80, inner2.height - 175),
            )
            draw_panel(target, panel, border_color=self.accent, fill=(16, 18, 28, 230))
            hint = self.body_font.render("Choose a spell (mana is spent when cast).", True, LABEL_DIM)
            target.blit(hint, (panel.left + 12, panel.top + 8))

            clip = target.get_clip()
            target.set_clip(self._spell_list_rect)
            row_h = 40
            gap = 8
            y = self._spell_list_rect.top - self._spell_scroll
            drew_any = False
            for sid in state.player.known_spell_ids:
                spec = get_spell(sid)
                if spec is None:
                    continue
                row = pygame.Rect(self._spell_list_rect.left, y, self._spell_list_rect.width, row_h)
                clip_row = row.clip(self._spell_list_rect)
                if clip_row.width > 0 and clip_row.height > 0:
                    drew_any = True
                    mp_ok = state.player.mana >= spec.mana_cost
                    row_fill = (22, 26, 38, 220) if mp_ok else (38, 22, 22, 210)
                    draw_panel(target, row, border_color=self.accent, fill=row_fill)
                    label = f"{spec.name}  ({spec.mana_cost} MP)"
                    if spec.heal > 0 and spec.damage <= 0:
                        label += f"  heal {spec.heal}"
                    elif spec.damage > 0:
                        label += f"  {spec.damage} dmg"
                    surf = self.body_font.render(fit_text(self.body_font, label, row.width - 12), True, LABEL_BRIGHT)
                    target.blit(surf, (row.left + 8, row.centery - surf.get_height() // 2))
                y += row_h + gap
            target.set_clip(clip)

            if not drew_any:
                empty = self.body_font.render(
                    "No spells learned yet. Find cantrip primers in the dungeon.",
                    True,
                    LABEL_DIM,
                )
                target.blit(empty, (panel.left + 12, panel.top + 44))

            if self._btn_back:
                self._btn_back.rect = self._spell_back_rect
                self._btn_back.draw(target)
            return

        for b in self._main_buttons:
            b.draw(target)


class Button:
    def __init__(
        self,
        rect: pygame.Rect,
        label: str,
        font: pygame.font.Font,
        *,
        on_click: Callable[[], None] | None = None,
    ) -> None:
        self.rect = rect
        self.label = label
        self.font = font
        self.on_click = on_click
        self.border_color: Color = PANEL_BORDER_FALLBACK
        self.hovered = False

    def set_border(self, color: Color) -> None:
        self.border_color = color

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                if self.on_click is not None:
                    self.on_click()
                return True
        return False

    def draw(self, target: pygame.Surface) -> None:
        fill_alpha = 230 if self.hovered else 200
        fill = (18, 18, 24, fill_alpha)
        draw_panel(target, self.rect, border_color=self.border_color, fill=fill)
        surface = self.font.render(self.label, True, LABEL_BRIGHT)
        target.blit(
            surface,
            (
                self.rect.centerx - surface.get_width() // 2,
                self.rect.centery - surface.get_height() // 2,
            ),
        )


def heart_pulse(t: float) -> float:
    """Helper for subtle pulsing UI elements (used by scenes)."""
    return 0.5 + 0.5 * math.sin(t * 3.2)

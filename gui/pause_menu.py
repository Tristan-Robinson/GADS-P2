"""In-game pause overlay: resume, how to play, quit to menu, quit to desktop."""

from __future__ import annotations

import pygame

from game import engine
from gui.highlight import LEGEND_MARKER, Color, legend_block_height, legend_rows
from gui.widgets import LABEL_BRIGHT, LABEL_DIM, Button, draw_panel

LEGEND_SWATCH_SIZE = 12


def _wrap_paragraph(font: pygame.font.Font, text: str, max_width: int) -> list[str]:
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


def _how_to_play_lines(body_font: pygame.font.Font, heading_font: pygame.font.Font, text_width: int):
    """Build (text, is_section_heading) lines for the help view."""

    sections: list[tuple[str, str]] = [
        (
            "Commands",
            "Type natural language in the command bar: look, go north, take the iron key, "
            "take all, use the healing potion, attack the goblin, talk quest, talk hooded watcher, "
            "talk merchant, inventory, help, or quit. "
            "Directions work as north, south, east, west, or forward, back, left, right.",
        ),
        (
            "Command bar",
            "Click in the bar to place the cursor; use arrow keys, Home, End, Backspace, and "
            "Delete (hold Backspace or Delete to repeat). Ctrl+C and Ctrl+V copy and paste. "
            "Up and Down recall recent commands. "
            "Chain several actions in one line with semicolons, a new line, or then / and then "
            "(example: go north; take torch). While the AI is thinking you can still type — "
            "your next command queues and the status bar shows how many are waiting. "
            "The bar shows Thinking... while your queued turn runs. "
            "A chain stops if a step starts combat, opens a quest or merchant dialog, makes you "
            "descend, or ends the game.",
        ),
        (
            "Story log and keywords",
            "Colored words in the narration mark enemies, items, exits, locks, and more — "
            "hover a highlighted word for its meaning (see the color key below). "
            "Drag a highlighted word into the command bar to insert it. Click a word to copy it; "
            "right-click the command bar and choose Paste, or use Ctrl+V. "
            "Scroll the story log with the mouse wheel or Page Up / Page Down. "
            "When you walk into a new room, the story automatically includes a survey of what "
            "you see there.",
        ),
        (
            "Color key",
            "Highlighted words in the story log use these colors:",
        ),
        (
            "Combat",
            "When you attack an enemy, use the Combat panel: Attack, Defend, Improvise, Spells, "
            "or Surrender. Surrender deals heavy damage but lets you break away and keep exploring "
            "while that foe hangs back.",
        ),
        (
            "Backpack and gear",
            "Click Pack next to Pause, or type inventory / inv when not in combat, to open your "
            "backpack. Tabs sort items: All, Gear, Use, Other, and Info for full descriptions. "
            "Select a row, then Use / Equip for potions, keys, buffs, weapons, armor, rings, "
            "and amulets. Equipped gear raises attack, defense, and agility in combat. "
            "Use Close inventory or Esc to hide the panel. Remove clears a gear slot without "
            "using the item. In the world, try take all or pick up all to grab every loose item here.",
        ),
        (
            "Quests and merchants",
            "Talk to hooded figures or curators in any chamber for a quest (try talk quest when "
            "they are present). Accept or decline in the parchment "
            "dialog. Completing quests pays gold. Every fifth dungeon depth, the entrance room has "
            "a merchant: buy stock with gold or sell rows from your backpack in the teal trade panel.",
        ),
        (
            "Pause",
            "Press Esc or the Pause button to open this menu. From here you can resume, read "
            "how to play, return to the title screen, or exit the game entirely.",
        ),
        (
            "Reference",
            engine.HELP_TEXT,
        ),
    ]
    out: list[tuple[str, bool]] = []
    for title, body in sections:
        for tline in _wrap_paragraph(heading_font, title, text_width):
            out.append((tline, True))
        for ln in _wrap_paragraph(body_font, body, text_width):
            out.append((ln, False))
        if title == "Color key":
            out.append((LEGEND_MARKER, False))
        out.append(("", False))
    while out and out[-1] == ("", False):
        out.pop()
    return out


def _draw_highlight_legend(
    surface: pygame.Surface,
    x: int,
    y: int,
    max_w: int,
    body_font: pygame.font.Font,
    accent: tuple[int, int, int],
) -> int:
    """Draw color swatches and labels; return total height used."""

    row_h = 22
    swatch = LEGEND_SWATCH_SIZE
    text_x = x + swatch + 10
    cy = y
    for color, label, description in legend_rows():
        swatch_rect = pygame.Rect(x, cy + (row_h - swatch) // 2, swatch, swatch)
        pygame.draw.rect(surface, color, swatch_rect)
        pygame.draw.rect(surface, accent, swatch_rect, 1)
        label_sf = body_font.render(f"{label} — ", True, LABEL_BRIGHT)
        desc_sf = body_font.render(description, True, LABEL_DIM)
        surface.blit(label_sf, (text_x, cy + (row_h - label_sf.get_height()) // 2))
        surface.blit(
            desc_sf,
            (text_x + label_sf.get_width(), cy + (row_h - desc_sf.get_height()) // 2),
        )
        cy += row_h
    return cy - y + 8


def _help_content_height(
    lines: list[tuple[str, bool]],
    body_font: pygame.font.Font,
    heading_font: pygame.font.Font,
) -> int:
    h = 0
    for text, is_heading in lines:
        if text == LEGEND_MARKER:
            h += legend_block_height()
            continue
        if not text.strip() and not is_heading:
            h += 8
            continue
        font = heading_font if is_heading else body_font
        h += font.get_height() + (12 if is_heading else 5)
    return h


class PauseOverlay:
    """Centered menu; Esc resumes from main view, returns to main from How to play."""

    def __init__(self, fonts: dict[str, pygame.font.Font]) -> None:
        self.fonts = fonts
        self.accent: Color = (200, 190, 170)
        self._view: str = "main"
        self._help_scroll_px = 0
        self._choice: str | None = None
        self._panel = pygame.Rect(0, 0, 320, 360)
        self._help_panel = pygame.Rect(0, 0, 400, 420)
        self._help_clip = pygame.Rect(0, 0, 1, 1)

        def pick(value: str):
            def inner() -> None:
                self._choice = value

            return inner

        self._btn_resume = Button(
            pygame.Rect(0, 0, 1, 1),
            "Resume",
            fonts["button"],
            on_click=pick("resume"),
        )
        self._btn_help = Button(
            pygame.Rect(0, 0, 1, 1),
            "How to play",
            fonts["button"],
            on_click=self._open_help,
        )
        self._btn_menu = Button(
            pygame.Rect(0, 0, 1, 1),
            "Quit to menu",
            fonts["button"],
            on_click=pick("quit_menu"),
        )
        self._btn_quit = Button(
            pygame.Rect(0, 0, 1, 1),
            "Quit to desktop",
            fonts["button"],
            on_click=pick("quit_desktop"),
        )
        self._btn_back = Button(
            pygame.Rect(0, 0, 1, 1),
            "Back",
            fonts["button"],
            on_click=self._close_help,
        )
        self._main_buttons = (
            self._btn_resume,
            self._btn_help,
            self._btn_menu,
            self._btn_quit,
        )

    def _open_help(self) -> None:
        self._view = "help"
        self._help_scroll_px = 0

    def _close_help(self) -> None:
        self._view = "main"

    def open(self) -> None:
        self._view = "main"
        self._help_scroll_px = 0
        self._choice = None

    def take_choice(self) -> str | None:
        c = self._choice
        self._choice = None
        return c

    def set_accent(self, accent: Color) -> None:
        self.accent = accent
        for b in (self._btn_resume, self._btn_help, self._btn_menu, self._btn_quit, self._btn_back):
            b.set_border(accent)

    def _layout_main(self, screen: pygame.Rect) -> None:
        w, btn_h = 280, 48
        gap = 12
        self._panel = pygame.Rect(0, 0, w, btn_h * 4 + gap * 3 + 56)
        self._panel.center = screen.center
        x = self._panel.left
        y = self._panel.top + 44
        for btn in self._main_buttons:
            btn.rect = pygame.Rect(x, y, w, btn_h)
            y += btn_h + gap

    def _layout_help(self, screen: pygame.Rect) -> None:
        margin = 36
        self._help_panel = screen.inflate(-margin * 2, -margin * 2)
        self._help_panel.clamp_ip(screen)
        pad = 18
        title_sf = self.fonts["heading"].render("How to play", True, LABEL_BRIGHT)
        title_top = self._help_panel.top + pad
        self._btn_back.rect = pygame.Rect(
            self._help_panel.left + pad,
            title_top + title_sf.get_height() + 10,
            120,
            40,
        )
        self._help_clip = pygame.Rect(
            self._help_panel.left + pad,
            self._btn_back.rect.bottom + 12,
            self._help_panel.width - 2 * pad,
            self._help_panel.bottom - pad - self._btn_back.rect.bottom - 36,
        )

    def _help_lines(self, max_w: int) -> list[tuple[str, bool]]:
        return _how_to_play_lines(
            self.fonts["body"],
            self.fonts["heading"],
            max_w,
        )

    def handle_event(self, event: pygame.event.Event, screen: pygame.Rect) -> None:
        if self._view == "help":
            self._layout_help(screen)
            max_w = max(80, self._help_clip.width - 12)
            lines = self._help_lines(max_w)
            content_h = _help_content_height(lines, self.fonts["body"], self.fonts["heading"])
            max_scroll = max(0, content_h - self._help_clip.height)

            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self._close_help()
                return
            if event.type == pygame.MOUSEWHEEL and self._help_clip.collidepoint(
                pygame.mouse.get_pos()
            ):
                self._help_scroll_px = max(
                    0,
                    min(max_scroll, self._help_scroll_px - event.y * 28),
                )
                return
            self._btn_back.handle_event(event)
            return

        self._layout_main(screen)
        for btn in self._main_buttons:
            btn.handle_event(event)

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._choice = "resume"

    def draw(self, surface: pygame.Surface, screen: pygame.Rect) -> None:
        veil = pygame.Surface(screen.size, pygame.SRCALPHA)
        veil.fill((0, 0, 0, 175))
        surface.blit(veil, (0, 0))

        if self._view == "help":
            self._layout_help(screen)
            draw_panel(surface, self._help_panel, border_color=self.accent)
            title = self.fonts["heading"].render("How to play", True, LABEL_BRIGHT)
            tx = self._help_panel.centerx - title.get_width() // 2
            surface.blit(title, (tx, self._help_panel.top + 18))
            self._btn_back.draw(surface)

            max_w = max(80, self._help_clip.width - 12)
            lines = self._help_lines(max_w)
            content_h = _help_content_height(lines, self.fonts["body"], self.fonts["heading"])
            max_scroll = max(0, content_h - self._help_clip.height)
            self._help_scroll_px = min(self._help_scroll_px, max_scroll)

            clip = surface.get_clip()
            surface.set_clip(self._help_clip)
            y = float(self._help_clip.top - self._help_scroll_px)
            x0 = self._help_clip.left + 6
            for text, is_heading in lines:
                if y > self._help_clip.bottom:
                    break
                if text == LEGEND_MARKER:
                    block_h = _draw_highlight_legend(
                        surface,
                        x0,
                        int(y),
                        max_w,
                        self.fonts["body"],
                        self.accent,
                    )
                    y += block_h
                    continue
                if not text.strip() and not is_heading:
                    y += 8
                    continue
                font = self.fonts["heading"] if is_heading else self.fonts["body"]
                color = self.accent if is_heading else LABEL_BRIGHT
                surf = font.render(text, True, color)
                bottom = y + surf.get_height()
                if bottom >= self._help_clip.top:
                    surface.blit(surf, (x0, int(y)))
                y += surf.get_height() + (12 if is_heading else 5)
            surface.set_clip(clip)

            hint = self.fonts["label"].render(
                "Mouse wheel scrolls · Esc returns to pause menu",
                True,
                LABEL_DIM,
            )
            surface.blit(hint, (self._help_panel.left + 18, self._help_panel.bottom - 28))
            return

        self._layout_main(screen)
        draw_panel(surface, self._panel, border_color=self.accent)
        paused = self.fonts["heading"].render("Paused", True, LABEL_BRIGHT)
        surface.blit(
            paused,
            (self._panel.centerx - paused.get_width() // 2, self._panel.top + 12),
        )
        for btn in self._main_buttons:
            btn.draw(surface)
